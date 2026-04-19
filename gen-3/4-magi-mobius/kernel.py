#!/usr/bin/env python3
"""
kernel.py — Layer 1. The electricity.

A walker that reads pscale blocks, follows star references, compiles context
windows, calls LLMs, routes output writes, records filmstrips, and sleeps.
"""

import json, os, sys, time, re, threading
from datetime import datetime, timezone
from pathlib import Path
import urllib.request, urllib.error

# ── Configuration ──────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
BLOCKS_DIR = BASE_DIR / "blocks"
FILMSTRIP_DIR = BASE_DIR / "filmstrip"
INPUT_FILE = BASE_DIR / "human_input.trigger"

PULSE = int(os.environ.get("PULSE", "30"))
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "4096"))
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
API_URL = "https://api.anthropic.com/v1/messages"

MODELS = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-6",
}

TIER_ORDER = {"haiku": 1, "sonnet": 2, "opus": 3}

VALID_MODES = {"spindle", "ring", "dir", "point", "disc", "star"}

# ── 1. BSP Engine ──────────────────────────────────────────────────────────

def underscore_text(node):
    """Follow underscore chain to deepest string. Return (text, has_hidden)."""
    if isinstance(node, str):
        return node, False
    if isinstance(node, dict) and "_" in node:
        us = node["_"]
        has_hidden = any(k.isdigit() for k in node if k != "_")
        if isinstance(us, str):
            return us, has_hidden
        if isinstance(us, dict):
            inner_text, _ = underscore_text(us)
            inner_hidden = any(k.isdigit() for k in us if k != "_")
            return inner_text, has_hidden or inner_hidden
    return "", False


def walk(block, address="_"):
    """Navigate block by digit address. Return (spindle, terminal_node)."""
    spindle = []
    node = block

    # Collect root underscore
    if isinstance(node, dict) and "_" in node:
        text, _ = underscore_text(node)
        if text:
            spindle.append(text)

    if address in ("_", "", None):
        return spindle, node

    # Parse address: "1.2.3" or "123" or "1"
    if "." in str(address):
        digits = str(address).split(".")
    else:
        digits = list(str(address))

    for d in digits:
        if not isinstance(node, dict):
            return spindle, None
        key = "_" if d == "0" else d
        if key not in node:
            return spindle, None
        node = node[key]
        if isinstance(node, dict) and "_" in node:
            text, _ = underscore_text(node)
            if text:
                spindle.append(text)
        elif isinstance(node, str):
            spindle.append(node)

    return spindle, node


def _collect_disc(node, target_depth, current_depth, results):
    """Recursively collect all nodes at target_depth."""
    if not isinstance(node, dict):
        return
    for k in sorted(k for k in node if k.isdigit()):
        child = node[k]
        if current_depth + 1 == target_depth:
            text, _ = underscore_text(child) if isinstance(child, dict) else (child if isinstance(child, str) else ("", False))
            if text:
                results.append({"key": k, "text": text})
        else:
            if isinstance(child, dict):
                _collect_disc(child, target_depth, current_depth + 1, results)


def bsp(block, address="_", mode="spindle"):
    """Read block at address in given mode."""
    spindle, terminal = walk(block, address)

    if mode == "spindle":
        return spindle

    if mode == "point":
        return spindle[-1] if spindle else ""

    if mode == "ring":
        if not isinstance(terminal, dict):
            return {}
        result = {}
        for k in sorted(k for k in terminal if k.isdigit()):
            child = terminal[k]
            text, _ = underscore_text(child) if isinstance(child, dict) else (child if isinstance(child, str) else ("", False))
            result[k] = text
        return result

    if mode == "dir":
        return terminal if terminal is not None else {}

    if mode == "disc":
        results = []
        depth = int(address) if address not in ("_", "", None) and str(address).isdigit() else 1
        _collect_disc(block, depth, 0, results)
        return results

    if mode == "star":
        if isinstance(terminal, dict) and "_" in terminal:
            us = terminal["_"]
            if isinstance(us, dict):
                return {k: v for k, v in us.items() if k != "_"}
        return {}

    return spindle  # fallback


def write_at(block, address, value):
    """Write value at address, creating intermediate nodes as needed."""
    if address in ("_", "", None):
        block["_"] = value
        return block

    if "." in str(address):
        parts = str(address).split(".")
    else:
        parts = list(str(address))

    node = block
    for part in parts[:-1]:
        key = "_" if part == "0" else part
        if key not in node or not isinstance(node.get(key), dict):
            node[key] = {}
        node = node[key]

    final_key = "_" if parts[-1] == "0" else parts[-1]
    node[final_key] = value
    return block


def parse_star(ref):
    """Parse 'blockname:address' -> (blockname, address)."""
    if not isinstance(ref, str):
        return None, None
    if ":" in ref:
        name, addr = ref.split(":", 1)
        return name, addr if addr else "_"
    return ref, "_"


# ── 2. Block I/O ──────────────────────────────────────────────────────────

_block_cache = {}

def load_block(name):
    """Load blocks/{name}.json. Return empty block if missing."""
    if name in _block_cache:
        return _block_cache[name]
    path = BLOCKS_DIR / f"{name}.json"
    if path.exists():
        with open(path) as f:
            block = json.load(f)
    else:
        block = {"_": name}
    _block_cache[name] = block
    return block


def save_block(name, block):
    """Save block to blocks/{name}.json."""
    _block_cache[name] = block
    path = BLOCKS_DIR / f"{name}.json"
    with open(path, "w") as f:
        json.dump(block, f, indent=2, ensure_ascii=False)


def list_blocks():
    """Return list of block names."""
    return [p.stem for p in BLOCKS_DIR.glob("*.json")]


def flush_cache():
    """Clear block cache (force reload from disk)."""
    _block_cache.clear()


# ── 3. Filmstrip ──────────────────────────────────────────────────────────

def write_filmstrip(frame):
    """Write frame to filmstrip/{timestamp}-{concern}-{tier}.json."""
    FILMSTRIP_DIR.mkdir(exist_ok=True)
    ts = frame.get("ts", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    concern = re.sub(r'[^a-z0-9]', '', frame.get("concern", "unknown").lower()[:20])
    tier = frame.get("tier", "unknown")
    filename = f"{ts}-{concern}-{tier}.json".replace(":", "")
    path = FILMSTRIP_DIR / filename
    with open(path, "w") as f:
        json.dump(frame, f, indent=2, ensure_ascii=False)


# ── 4. Compilation Pipeline ───────────────────────────────────────────────

def compile_context(function_config, starstone):
    """Follow star references in function config. Return (system, message, compiled)."""
    compiled = {}

    for key in sorted(k for k in function_config if k.isdigit()):
        branch = function_config[key]
        if not isinstance(branch, dict):
            continue

        # Extract description and star ref from hidden directory
        desc = ""
        star_ref = None
        if "_" in branch and isinstance(branch["_"], dict):
            us = branch["_"]
            desc, _ = underscore_text(us)
            star_ref = us.get("1")  # first star reference

        # Extract BSP mode from branch key "1"
        mode_val = branch.get("1", "spindle")
        mode = mode_val if isinstance(mode_val, str) and mode_val in VALID_MODES else "spindle"

        if not star_ref:
            compiled[key] = {"desc": desc, "ref": None, "mode": mode, "content": "", "block_name": ""}
            continue

        block_name, address = parse_star(star_ref)
        if not block_name:
            continue

        target = load_block(block_name)
        content = bsp(target, address, mode)
        compiled[key] = {
            "desc": desc, "ref": star_ref, "mode": mode,
            "content": content, "block_name": block_name,
        }

    # Build system prompt
    system_parts = []

    # Starstone (constant)
    system_parts.append("=== STARSTONE ===")
    system_parts.append(format_content(bsp(starstone, "_", "dir")))

    # Identity (if any branch references it)
    for info in compiled.values():
        if info.get("block_name") == "identity":
            system_parts.append("\n=== IDENTITY ===")
            system_parts.append(format_content(info["content"]))
            break

    # Function config (the LLM sees its own aperture)
    system_parts.append("\n=== FUNCTION ===")
    system_parts.append(json.dumps(function_config, indent=2, ensure_ascii=False))

    # Mirror with PCT preamble
    system_parts.append("\n=== MIRROR ===")
    system_parts.append(
        "Purpose is your reference signal \u2014 what should be. "
        "Conditions is your perceptual signal \u2014 what is. "
        "The gap between them is your task. "
        "Your writes close the gap. "
        "Your function modifications reshape what the next instance perceives."
    )
    system_parts.append("\nYour context was compiled from these references:")
    for key in sorted(compiled):
        info = compiled[key]
        ref = info.get("ref", "none")
        mode = info.get("mode", "?")
        desc = info.get("desc", "")[:60]
        system_parts.append(f"  Branch {key}: {ref} ({mode}) \u2192 {desc}")

    # Output contract
    system_parts.append("\n=== OUTPUT CONTRACT ===")
    system_parts.append(
        'Return JSON (or JSON inside ```json fences):\n'
        '{\n'
        '  "writes": {"blockname:address": "content to write"},\n'
        '  "status": "continue | complete | escalate",\n'
        '  "note": "What you did and why (this becomes your history)",\n'
        '  "function": null\n'
        '}\n'
        'Set "function" to a replacement function config to reshape your next aperture, or null/omit to keep it.\n'
        '"writes" keys use star reference format: "blockname:address". Writing to a new block name creates it.\n'
        '"status": continue = fire again next cycle. complete = rest (gap is closed). escalate = need broader scope.'
    )

    # Build message (compiled currents)
    message_parts = []
    section_labels = {
        "purpose": "PURPOSE", "conditions": "CONDITIONS", "history": "HISTORY",
        "conversation": "CONVERSATION", "identity": "IDENTITY",
    }
    for key in sorted(compiled):
        info = compiled[key]
        bname = info.get("block_name", "")
        label = section_labels.get(bname, bname.upper() if bname else f"BRANCH {key}")
        if bname == "identity":
            continue  # already in system prompt
        content = info.get("content", "")
        if content:
            message_parts.append(f"=== {label} ===")
            message_parts.append(format_content(content))

    system = "\n".join(system_parts)
    message = "\n".join(message_parts)
    return system, message, compiled


def format_content(content):
    """Format BSP output as readable string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(f"  {'>' * i} {text}" for i, text in enumerate(content))
    if isinstance(content, dict):
        return json.dumps(content, indent=2, ensure_ascii=False)
    return str(content)


# ── 5. Concern Dispatch ───────────────────────────────────────────────────

COOLDOWN_CYCLES = 5

def find_ripe(concerns, now, has_human_input, pulse):
    """Walk concern block. Return (path, hidden_dir, desc) of ripest concern, or (None, None, None)."""
    candidates = []

    for key in sorted(k for k in concerns if k.isdigit()):
        node = concerns[key]
        if not isinstance(node, dict):
            continue

        # Read hidden directory
        hidden = bsp(node, "_", "star")
        if not hidden:
            continue

        desc, _ = underscore_text(node)
        tier_name = hidden.get("1", "haiku")
        trigger = hidden.get("2", "always")
        last_fired = float(hidden.get("9", 0))
        last_status = hidden.get("8", "")
        fn_config = hidden.get("3", {})

        tier_rank = TIER_ORDER.get(tier_name, 1)
        ripe = False
        period = pulse

        if trigger == "birth":
            ripe = (last_fired == 0)
            period = 1
        elif trigger == "human":
            ripe = has_human_input
            period = pulse
        elif trigger.startswith("timer:"):
            try:
                period = int(trigger.split(":")[1])
            except (ValueError, IndexError):
                period = 86400
            ripe = (now - last_fired) >= period
        elif trigger == "always":
            # Burn loop guard
            if last_status == "complete" and last_fired > 0:
                cycles_since = (now - last_fired) / pulse if pulse > 0 else 0
                if cycles_since < COOLDOWN_CYCLES:
                    continue
            ripe = True
            period = pulse
        elif trigger == "compaction":
            # Checked externally
            continue

        if not ripe:
            continue

        phase = (now - last_fired) / period if period > 0 and last_fired > 0 else 999
        candidates.append((tier_rank, phase, key, hidden, desc, fn_config, tier_name))

    if not candidates:
        return None, None, None

    # Sort: highest tier first, then highest phase (most overdue)
    candidates.sort(key=lambda c: (-c[0], -c[1]))
    _, _, path, hidden, desc, fn_config, tier_name = candidates[0]
    return path, hidden, desc


def update_fired(concerns, concern_path, now, status):
    """Write timestamp and status to concern's hidden directory."""
    node = concerns.get(concern_path, {})
    if isinstance(node, dict) and "_" in node and isinstance(node["_"], dict):
        node["_"]["9"] = now
        node["_"]["8"] = status
    save_block("concern", concerns)


# ── 6. LLM Call + A-Loop ──────────────────────────────────────────────────

TOOLS_BY_TIER = {
    "haiku": ["bsp", "block_read", "block_write", "block_list", "file_read", "file_write"],
    "sonnet": ["bsp", "block_read", "block_write", "block_list", "call_llm", "file_read", "file_write", "web_fetch"],
    "opus": ["bsp", "block_read", "block_write", "block_list", "call_llm", "file_read", "file_write", "web_fetch"],
}

TOOL_SCHEMAS = {
    "bsp": {
        "name": "bsp", "description": "Navigate a pscale block using BSP. Modes: spindle (default, broad-to-specific chain), ring (siblings at terminal), dir (full subtree), point (single text), disc (all nodes at depth), star (hidden directory).",
        "input_schema": {"type": "object", "properties": {"block": {"type": "string"}, "address": {"type": "string", "default": "_"}, "mode": {"type": "string", "default": "spindle", "enum": ["spindle", "ring", "dir", "point", "disc", "star"]}}, "required": ["block"]},
    },
    "block_read": {
        "name": "block_read", "description": "Read raw block content at a path.",
        "input_schema": {"type": "object", "properties": {"block": {"type": "string"}, "path": {"type": "string", "default": "_"}}, "required": ["block"]},
    },
    "block_write": {
        "name": "block_write", "description": "Write content to a block at a path. Creates intermediate nodes.",
        "input_schema": {"type": "object", "properties": {"block": {"type": "string"}, "path": {"type": "string"}, "content": {}}, "required": ["block", "path", "content"]},
    },
    "block_list": {
        "name": "block_list", "description": "List all available block names.",
        "input_schema": {"type": "object", "properties": {}},
    },
    "call_llm": {
        "name": "call_llm", "description": "Delegate a sub-task to an LLM. Returns response text.",
        "input_schema": {"type": "object", "properties": {"system": {"type": "string"}, "message": {"type": "string"}, "model": {"type": "string", "default": "haiku"}}, "required": ["message"]},
    },
    "web_fetch": {
        "name": "web_fetch", "description": "HTTP GET a URL. Returns content (max 8000 chars).",
        "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
    },
    "file_read": {
        "name": "file_read", "description": "Read a local file. Includes filmstrip frames.",
        "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    },
    "file_write": {
        "name": "file_write", "description": "Write a local file.",
        "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]},
    },
}


def execute_tool(name, inp):
    """Execute a tool call. Return result string."""
    try:
        if name == "bsp":
            block = load_block(inp["block"])
            result = bsp(block, inp.get("address", "_"), inp.get("mode", "spindle"))
            return json.dumps(result, indent=2, ensure_ascii=False) if not isinstance(result, str) else result

        if name == "block_read":
            block = load_block(inp["block"])
            _, node = walk(block, inp.get("path", "_"))
            return json.dumps(node, indent=2, ensure_ascii=False) if not isinstance(node, str) else (node or "(empty)")

        if name == "block_write":
            block = load_block(inp["block"])
            write_at(block, inp["path"], inp["content"])
            save_block(inp["block"], block)
            return f"Wrote to {inp['block']}:{inp['path']}"

        if name == "block_list":
            return json.dumps(list_blocks())

        if name == "call_llm":
            model_key = inp.get("model", "haiku")
            model_id = MODELS.get(model_key, MODELS["haiku"])
            text, _ = api_call(inp.get("system", "You are a helpful assistant."), inp["message"], model_id, [])
            return text

        if name == "web_fetch":
            req = urllib.request.Request(inp["url"], headers={"User-Agent": "kernel/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.read().decode("utf-8", errors="replace")[:8000]

        if name == "file_read":
            p = Path(inp["path"])
            if not p.is_absolute():
                p = BASE_DIR / p
            return p.read_text()[:8000]

        if name == "file_write":
            p = Path(inp["path"])
            if not p.is_absolute():
                p = BASE_DIR / p
            p.write_text(inp["content"])
            return f"Wrote {len(inp['content'])} chars to {p}"

        return f"Unknown tool: {name}"
    except Exception as e:
        return f"Tool error ({name}): {e}"


def api_call(system, message, model_id, tools):
    """Call Anthropic Messages API. Return response text or raise."""
    body = {
        "model": model_id,
        "max_tokens": MAX_TOKENS,
        "system": system,
        "messages": [{"role": "user", "content": message}],
    }
    if tools:
        body["tools"] = tools

    data = json.dumps(body).encode()
    req = urllib.request.Request(API_URL, data=data, headers={
        "Content-Type": "application/json",
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
    })
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode())

    # Extract text from response
    texts = []
    for block in result.get("content", []):
        if block.get("type") == "text":
            texts.append(block["text"])
    return "\n".join(texts), result


def call_llm(system, message, tier_name, tools_list):
    """Call LLM with A-loop for tool use. Return (final_text, tool_log, tokens)."""
    model_id = MODELS.get(tier_name, MODELS["haiku"])
    tool_schemas = [TOOL_SCHEMAS[t] for t in tools_list if t in TOOL_SCHEMAS]
    tool_log = []
    tokens = {"input": 0, "output": 0}

    messages = [{"role": "user", "content": message}]

    for iteration in range(10):  # A-loop max 10
        body = {
            "model": model_id,
            "max_tokens": MAX_TOKENS,
            "system": system,
            "messages": messages,
        }
        if tool_schemas:
            body["tools"] = tool_schemas

        data = json.dumps(body).encode()
        req = urllib.request.Request(API_URL, data=data, headers={
            "Content-Type": "application/json",
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
        })

        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode())

        usage = result.get("usage", {})
        tokens["input"] += usage.get("input_tokens", 0)
        tokens["output"] += usage.get("output_tokens", 0)

        stop_reason = result.get("stop_reason", "end_turn")
        content_blocks = result.get("content", [])

        # Collect text and tool_use blocks
        texts = []
        tool_uses = []
        for block in content_blocks:
            if block.get("type") == "text":
                texts.append(block["text"])
            elif block.get("type") == "tool_use":
                tool_uses.append(block)

        if stop_reason != "tool_use" or not tool_uses:
            return "\n".join(texts), tool_log, tokens

        # Execute tools and build next messages
        messages.append({"role": "assistant", "content": content_blocks})
        tool_results = []
        for tu in tool_uses:
            result_str = execute_tool(tu["name"], tu.get("input", {}))
            tool_log.append({"name": tu["name"], "input": str(tu.get("input", {}))[:200], "output": result_str[:200]})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu["id"],
                "content": result_str[:4000],
            })
        messages.append({"role": "user", "content": tool_results})

    return "\n".join(texts), tool_log, tokens


# ── 7. Output Parsing & Routing ───────────────────────────────────────────

def parse_output(text):
    """Parse LLM output JSON. Return dict with writes/status/note/function."""
    # Strip markdown fences
    cleaned = re.sub(r'^```(?:json)?\s*', '', text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r'```\s*$', '', cleaned.strip(), flags=re.MULTILINE)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in text
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Fallback — escalate on parse failure rather than continuing blindly
    return {"writes": {}, "status": "escalate", "note": f"[parse failure] {text[:200]}"}


def validate_function_config(config):
    """Check that a function config has valid star references and modes."""
    if not isinstance(config, dict):
        return False
    for key in config:
        if key == "_":
            continue
        if not key.isdigit():
            return False
        branch = config[key]
        if not isinstance(branch, dict):
            continue
        mode = branch.get("1", "spindle")
        if isinstance(mode, str) and mode not in VALID_MODES:
            return False
    return True


def route_output(output, concern_path, concerns):
    """Route writes, update function config, write history. Return status."""
    status = output.get("status", "continue")
    writes = output.get("writes", {})
    note = output.get("note", "")
    fn_update = output.get("function")

    # Route writes
    for ref, value in writes.items():
        block_name, address = parse_star(ref)
        if block_name:
            block = load_block(block_name)
            write_at(block, address, value)
            save_block(block_name, block)

    # Update function config
    if fn_update and isinstance(fn_update, dict):
        if validate_function_config(fn_update):
            node = concerns.get(concern_path, {})
            if isinstance(node, dict) and "_" in node and isinstance(node["_"], dict):
                node["_"]["3"] = fn_update
                save_block("concern", concerns)
        else:
            print(f"  [!] Invalid function config from LLM, keeping existing")

    # Write history
    if note:
        history = load_block("history")
        needs_compress = write_history_entry(history, note)
        save_block("history", history)
        if needs_compress:
            print(f"  [*] History compression needed")
            # Compression would call Haiku here — deferred for minimal system

    return status


# ── 8. History + Conversation ─────────────────────────────────────────────

def find_write_position(block):
    """Find first free digit (1-9) at the active edge. Return (path, slot) or (None, None) if full."""
    # Check current level
    for i in range(1, 10):
        key = str(i)
        if key not in block:
            return "", key
        # If it's a dict with underscore (sealed) and has capacity deeper, descend
        child = block[key]
        if isinstance(child, dict):
            sub_path, sub_slot = find_write_position(child)
            if sub_slot:
                return f"{key}.{sub_path}".strip("."), sub_slot

    return None, None  # All 9 full at all levels


def write_history_entry(block, note):
    """Write note to history block. Return True if compression needed."""
    path, slot = find_write_position(block)
    if slot is None:
        return True  # Needs compression

    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    entry = f"[{ts}] {note}"

    if path:
        # Navigate to nested position
        parts = path.split(".") if path else []
        node = block
        for p in parts:
            if p and p in node and isinstance(node[p], dict):
                node = node[p]
            elif p:
                node[p] = {}
                node = node[p]
        node[slot] = entry
    else:
        block[slot] = entry

    return False


def append_conversation(conv_block, human_msg, agent_response):
    """Append exchange to conversation block. Return True if compression needed."""
    path, slot = find_write_position(conv_block)
    if slot is None:
        return True  # Needs compression

    entry = {"1": human_msg or "", "2": agent_response or ""}

    if path:
        parts = path.split(".") if path else []
        node = conv_block
        for p in parts:
            if p and p in node and isinstance(node[p], dict):
                node = node[p]
            elif p:
                node[p] = {}
                node = node[p]
        node[slot] = entry
    else:
        conv_block[slot] = entry

    return False


# ── 9. Human Input ────────────────────────────────────────────────────────

_human_input_buffer = []
_input_lock = threading.Lock()


def check_human_input():
    """Check for human input from trigger file or buffer."""
    # Check file trigger
    if INPUT_FILE.exists():
        try:
            text = INPUT_FILE.read_text().strip()
            INPUT_FILE.unlink()
            if text:
                return text
        except Exception:
            pass

    # Check buffer (from stdin thread)
    with _input_lock:
        if _human_input_buffer:
            return _human_input_buffer.pop(0)

    return None


def stdin_reader():
    """Background thread: read stdin lines into buffer."""
    try:
        for line in sys.stdin:
            line = line.strip()
            if line:
                with _input_lock:
                    _human_input_buffer.append(line)
    except EOFError:
        pass


# ── 10. Main Loop ─────────────────────────────────────────────────────────

def main():
    print(f"[kernel] booting from {BLOCKS_DIR}")
    print(f"[kernel] pulse={PULSE}s, filmstrip={FILMSTRIP_DIR}")

    if not API_KEY:
        print("[kernel] ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    BLOCKS_DIR.mkdir(exist_ok=True)
    FILMSTRIP_DIR.mkdir(exist_ok=True)

    # Start stdin reader thread
    t = threading.Thread(target=stdin_reader, daemon=True)
    t.start()

    starstone = load_block("starstone")
    cycle = 0

    print(f"[kernel] loaded {len(list_blocks())} blocks: {', '.join(list_blocks())}")
    print(f"[kernel] ready. Type input or wait for concern cycle.\n")

    while True:
        cycle += 1
        now = time.time()

        # Check for human input
        human_input = check_human_input()
        has_input = human_input is not None

        if has_input:
            print(f"\n[cycle {cycle}] human input: {human_input[:80]}...")

        # Find ripe concern
        concerns = load_block("concern")
        path, hidden, desc = find_ripe(concerns, now, has_input, PULSE)

        if path is None:
            if has_input:
                print(f"  [!] Input received but no engagement concern ripe")
            time.sleep(PULSE)
            flush_cache()
            continue

        tier_name = hidden.get("1", "haiku")
        trigger = hidden.get("2", "always")
        fn_config = hidden.get("3", {})

        print(f"\n[cycle {cycle}] concern={desc[:50]} tier={tier_name} trigger={trigger} path={path}")

        # Compile context
        try:
            system, message, compiled = compile_context(fn_config, starstone)
        except Exception as e:
            print(f"  [!] Compilation failed: {e}")
            update_fired(concerns, path, now, "continue")
            time.sleep(PULSE)
            flush_cache()
            continue

        # Append human input to message if present
        if has_input:
            message += f"\n\n=== HUMAN INPUT ===\n{human_input}"

        # Select tools
        tools_list = TOOLS_BY_TIER.get(tier_name, TOOLS_BY_TIER["haiku"])

        # Call LLM
        print(f"  calling {MODELS.get(tier_name, '?')}...")
        try:
            response_text, tool_log, tokens = call_llm(system, message, tier_name, tools_list)
        except Exception as e:
            print(f"  [!] LLM call failed: {e}")
            update_fired(concerns, path, now, "continue")
            time.sleep(PULSE)
            flush_cache()
            continue

        print(f"  tokens: {tokens['input']}in/{tokens['output']}out, tools: {len(tool_log)}")

        # Parse output
        output = parse_output(response_text)
        note = output.get("note", response_text[:200])
        print(f"  status={output.get('status', '?')} note={note[:80]}")

        # Route output
        status = route_output(output, path, concerns)

        # Write filmstrip
        write_filmstrip({
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "concern": desc[:50],
            "path": path,
            "tier": tier_name,
            "model": MODELS.get(tier_name, "?"),
            "echo": 0,
            "system": system,
            "message": message,
            "output": response_text,
            "tools": tool_log,
            "tokens": tokens,
        })

        # Update concern
        update_fired(concerns, path, now, status)

        # Append conversation if engagement
        if trigger == "human" and has_input:
            conv = load_block("conversation")
            append_conversation(conv, human_input, note)
            save_block("conversation", conv)

        # Flush cache for next cycle
        flush_cache()

        print(f"  cycle complete. sleeping {PULSE}s...")
        time.sleep(PULSE)


if __name__ == "__main__":
    main()
