#!/usr/bin/env python3
"""
magi.py — Minimal kernel for the three-phase context window architecture.

The kernel is a walker. It reads a function block, follows star references
into external blocks, compiles a context window, calls an LLM, parses
the output, routes writes, and loops.

The data is the program. The kernel is the electricity.

Usage:
    python magi.py              # run the loop
    python magi.py --max 5      # run max 5 instances
    python magi.py --dry        # compile and print prompts without calling LLM
"""

import json
import os
import sys
import time
import argparse
import requests
from pathlib import Path
from datetime import datetime

# ═══ Configuration ═══════════════════════════════════════════════

BLOCKS_DIR = Path("blocks")
MAX_INSTANCES = 20
DELAY = 2  # seconds between instances

# Anthropic API (default)
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Tiered models — Haiku does tasks, Sonnet restructures
MODEL_HAIKU = "claude-haiku-4-5-20251001"
MODEL_SONNET = "claude-sonnet-4-6"

# Local LM (fallback with --local)
LOCAL_URL = "http://127.0.0.1:1234/v1/chat/completions"
LOCAL_KEY = "sk-lm-bThX0J7L:o6YIgwnUm41I47ETt5uR"

USE_LOCAL = False


# ═══ BSP ═════════════════════════════════════════════════════════

def underscore_text(node):
    """Follow underscore chain to the deepest string."""
    if isinstance(node, str):
        return node
    if isinstance(node, dict) and "_" in node:
        return underscore_text(node["_"])
    return None


def walk(block, address="_"):
    """Walk a block to an address. Return (spindle, terminal_node)."""
    spindle = []
    current = block

    # Collect root underscore
    if isinstance(current, dict) and "_" in current:
        text = underscore_text(current["_"])
        if text:
            spindle.append(text)

    if not address or address == "_":
        return spindle, current

    # Parse address into digit sequence
    digits = [c for c in str(address) if c.isdigit()]

    for d in digits:
        key = "_" if d == "0" else d
        if isinstance(current, dict) and key in current:
            current = current[key]
            if isinstance(current, dict) and "_" in current:
                text = underscore_text(current["_"])
                if text:
                    spindle.append(text)
            elif isinstance(current, str):
                spindle.append(current)
        else:
            break

    return spindle, current


def bsp(block, address="_", mode="spindle"):
    """
    BSP function. Modes:
      spindle — chain of underscore texts, root to terminal
      ring    — sibling keys and their underscore texts at terminal
      dir     — full subtree at terminal
      point   — single text at terminal
      star    — hidden directory (digit children inside underscore object)
    """
    if mode == "star":
        _, terminal = walk(block, address)
        if isinstance(terminal, dict) and "_" in terminal:
            us = terminal["_"]
            if isinstance(us, dict):
                return {k: v for k, v in us.items() if k != "_"}
        return {}

    spindle_result, terminal = walk(block, address)

    if mode == "spindle":
        return spindle_result
    elif mode == "ring":
        if isinstance(terminal, dict):
            return {
                k: (underscore_text(v) if isinstance(v, dict) else v)
                for k, v in terminal.items()
                if k != "_"
            }
        return {}
    elif mode == "dir":
        return terminal
    elif mode == "point":
        return spindle_result[-1] if spindle_result else None

    return spindle_result


# ═══ Block I/O ═══════════════════════════════════════════════════

def load_block(name):
    """Load a JSON block from blocks/."""
    path = BLOCKS_DIR / f"{name}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"_": f"Empty block: {name}"}


def save_block(name, data):
    """Save a JSON block to blocks/."""
    path = BLOCKS_DIR / f"{name}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def write_at(block, address, value):
    """Write value at address in block. Creates path if needed."""
    if not address or address == "_":
        if isinstance(value, str):
            block["_"] = value
        elif isinstance(value, dict):
            block.update(value)
        return

    digits = [c for c in str(address) if c.isdigit() or c == "_"]
    # Handle named addresses like "result"
    parts = str(address).split(".")
    current = block
    for part in parts[:-1]:
        key = "_" if part == "0" else part
        if key not in current or not isinstance(current.get(key), dict):
            current[key] = {}
        current = current[key]
    final = "_" if parts[-1] == "0" else parts[-1]
    current[final] = value


# ═══ Star Reference Parsing ══════════════════════════════════════

def parse_star_ref(ref):
    """Parse 'block:address' → (block_name, address)."""
    if ":" in str(ref):
        parts = str(ref).split(":", 1)
        return parts[0].strip(), parts[1].strip()
    return str(ref), "_"


# ═══ Compilation ═════════════════════════════════════════════════

def compile_context(function_block):
    """
    Follow star references in the function block.
    Returns dict: {branch_key: {desc, ref, mode, compiled, block_name, address}}
    """
    compiled = {}

    for key in sorted(k for k in function_block if k.isdigit()):
        branch = function_block[key]
        if not isinstance(branch, dict):
            continue

        # Star reference: digit children inside the underscore object
        hidden = {}
        if "_" in branch and isinstance(branch["_"], dict):
            us = branch["_"]
            hidden = {k: v for k, v in us.items() if k != "_" and isinstance(v, str)}

        # BSP mode: digit 1 at branch level (if it's a string)
        mode_val = branch.get("1", "spindle")
        mode = mode_val if isinstance(mode_val, str) and mode_val in (
            "spindle", "ring", "dir", "point", "star"
        ) else "spindle"

        # Description
        desc = underscore_text(branch.get("_", "")) or f"Branch {key}"

        # Follow the first star reference (digit 1 in hidden dir)
        star_ref = hidden.get("1")
        if star_ref and ":" in star_ref:
            block_name, address = parse_star_ref(star_ref)
            block_data = load_block(block_name)
            result = bsp(block_data, address, mode)

            compiled[key] = {
                "desc": desc,
                "ref": star_ref,
                "mode": mode,
                "compiled": result,
                "block_name": block_name,
                "address": address,
            }

    return compiled


# ═══ Prompt Assembly ═════════════════════════════════════════════

def format_compiled(data, max_chars=8000):
    """Format compiled data for prompt inclusion."""
    if isinstance(data, list):
        return "\n".join(f"  [{i}] {s}" for i, s in enumerate(data))
    elif isinstance(data, dict):
        text = json.dumps(data, indent=2, ensure_ascii=False)
        if len(text) > max_chars:
            return text[:max_chars] + "\n  ... [truncated]"
        return text
    return str(data)


def build_system(starstone, function_block, compiled):
    """Build system prompt — the present phase."""
    parts = []

    # ── Starstone (constant) ──
    parts.append("=== STARSTONE ===")
    parts.append("This block teaches walk, compose, and recurse by being all three.")
    parts.append("Study its structure to understand how pscale blocks work.")
    parts.append(json.dumps(starstone, indent=2, ensure_ascii=False))
    parts.append("")

    # ── Soul (identity) ──
    for key, info in sorted(compiled.items()):
        if info["block_name"] == "soul":
            parts.append("=== SOUL ===")
            parts.append("This is who you are. Your persistent identity.")
            parts.append(format_compiled(info["compiled"], max_chars=5000))
            parts.append("")

    # ── Function block ──
    parts.append("=== FUNCTION BLOCK ===")
    parts.append("This block compiled your context window. Its star references")
    parts.append("(digit keys inside underscore objects) point to external blocks.")
    parts.append("The pre-walker followed these stars to produce what you see below.")
    parts.append(json.dumps(function_block, indent=2, ensure_ascii=False))
    parts.append("")

    # ── Reflexive mirror ──
    parts.append("=== REFLEXIVE MIRROR ===")
    parts.append("Your context window was compiled from these star references:")
    for key, info in sorted(compiled.items()):
        parts.append(
            f"  Branch {key}: {info['ref']} (mode: {info['mode']}) → {info['desc']}"
        )
        if isinstance(info["compiled"], list):
            parts.append(f"    Spindle of {len(info['compiled'])} entries")
        elif isinstance(info["compiled"], dict):
            size = len(json.dumps(info["compiled"]))
            parts.append(f"    Block content: {size} chars")
        else:
            parts.append(f"    Content: {str(info['compiled'])[:100]}")
    parts.append("")
    parts.append("The function block IS the aperture. Modify star references to")
    parts.append("change what the next instance perceives. Change an address and")
    parts.append("different content compiles. Change a mode (spindle/ring/dir/point)")
    parts.append("and the same content compiles at different resolution.")
    parts.append("")

    # ── Output contract ──
    parts.append("=== OUTPUT CONTRACT ===")
    parts.append("Respond with ONLY valid JSON. No markdown fences. No preamble.")
    parts.append("")
    parts.append("{")
    parts.append('  "function": <modified function block, or null if unchanged>,')
    parts.append('  "writes": {')
    parts.append('    "blockname:address": <content to write at that address>')
    parts.append("  },")
    parts.append('  "status": "complete" | "continue" | "decompose" | "escalate",')
    parts.append('  "note": "what you did and why (this becomes history)"')
    parts.append("}")
    parts.append("")
    parts.append("Status meanings:")
    parts.append("  complete  — purpose 1 done, result written, move to purpose 2")
    parts.append("  continue  — partial progress, more instances needed")
    parts.append("  decompose — too complex, wrote sub-purposes to purpose block")
    parts.append("  escalate  — stuck, need a higher-tier instance")

    return "\n".join(parts)


def build_message(compiled):
    """Build message — compiled currents organised by block type."""
    parts = []

    # Known section labels (order matters)
    SECTION_LABELS = {
        "purpose":      "PURPOSE (the gap to close)",
        "character":    "CHARACTER (who you are)",
        "world":        "WORLD (what you perceive)",
        "determinacy":  "CONTENT (material to operate on)",
        "history":      "HISTORY (what has been attempted)",
    }
    SYSTEM_BLOCKS = {"soul"}  # already in system prompt
    sections = {k: [] for k in SECTION_LABELS}
    other_parts = []

    for key, info in sorted(compiled.items()):
        if info["block_name"] in SYSTEM_BLOCKS:
            continue
        formatted = format_compiled(info["compiled"])
        bname = info["block_name"]
        if bname in sections:
            sections[bname].append(formatted)
        else:
            other_parts.append(f"[{bname}] {formatted}")

    for bname, label in SECTION_LABELS.items():
        if sections[bname]:
            parts.append(f"=== {label} ===")
            parts.extend(sections[bname])
            parts.append("")

    if other_parts:
        parts.append("=== OTHER ===")
        parts.extend(other_parts)
        parts.append("")

    # Task framing
    parts.append("=== TASK ===")
    parts.append("Can you close the gap between purpose and current state?")
    parts.append("  YES → do the work, write results, status: complete")
    parts.append("  PARTIALLY → do what you can, status: continue")
    parts.append("  TOO COMPLEX → break into sub-tasks, status: decompose")
    parts.append("  STUCK → status: escalate")
    parts.append("")
    parts.append("If you need more detail, modify the function block's star")
    parts.append("references: change mode from 'spindle' to 'dir' or 'ring'.")
    parts.append("The next instance will perceive the result.")

    return "\n".join(parts)


# ═══ LLM Call ════════════════════════════════════════════════════

def call_llm(system_prompt, message, model=None):
    """Call LLM. Model defaults to Haiku. Pass MODEL_SONNET for escalation."""
    if USE_LOCAL:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LOCAL_KEY}",
        }
        payload = {
            "model": "local",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            "temperature": 0.7,
            "max_tokens": 4096,
        }
        resp = requests.post(LOCAL_URL, headers=headers, json=payload, timeout=180)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    else:
        if not ANTHROPIC_KEY:
            print("ERROR: Set ANTHROPIC_API_KEY environment variable")
            print("  export ANTHROPIC_API_KEY=sk-ant-...")
            sys.exit(1)
        use_model = model or MODEL_HAIKU
        headers = {
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
        }
        payload = {
            "model": use_model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": message},
            ],
            "temperature": 0.7,
        }
        resp = requests.post(ANTHROPIC_URL, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        # Anthropic returns content blocks
        text_parts = [
            block["text"] for block in data.get("content", [])
            if block.get("type") == "text"
        ]
        return "\n".join(text_parts)


def parse_output(raw):
    """Parse LLM JSON output, tolerating markdown fences."""
    text = raw.strip()
    # Strip markdown fences
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # remove opening fence
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON object
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    return {
        "status": "escalate",
        "note": f"Failed to parse output: {text[:300]}",
        "writes": {},
    }


# ═══ Output Processing ══════════════════════════════════════════

def process_output(output, instance_num):
    """Route writes, update function block, log to history."""
    status = output.get("status", "continue")
    note = output.get("note", "no note")

    # Update function block if provided
    new_func = output.get("function")
    if new_func and isinstance(new_func, dict):
        save_block("function", new_func)
        print(f"    → function block updated")

    # Route content writes
    for ref, value in output.get("writes", {}).items():
        if ":" not in ref:
            continue
        block_name, address = parse_star_ref(ref)
        block = load_block(block_name)
        write_at(block, address, value)
        save_block(block_name, block)
        val_preview = str(value)[:80]
        print(f"    → write {ref}: {val_preview}...")

    # Append to history
    history = load_block("history")
    existing = [k for k in history if k.isdigit()]
    next_key = str(len(existing) + 1)
    if int(next_key) > 9:
        # Compress: keep last 5 entries, shift down
        kept = sorted(existing, key=int)[-5:]
        new_hist = {"_": history.get("_", "History")}
        for i, old_key in enumerate(kept, 1):
            new_hist[str(i)] = history[old_key]
        history = new_hist
        next_key = str(len([k for k in history if k.isdigit()]) + 1)

    history[next_key] = {
        "_": f"Instance {instance_num}: {status}",
        "1": note,
        "2": datetime.now().isoformat(timespec="seconds"),
    }
    save_block("history", history)

    return status


# ═══ Main Loop ═══════════════════════════════════════════════════

def run(max_instances=MAX_INSTANCES, dry=False):
    """The kernel. Walk, compile, call, process, loop."""
    BLOCKS_DIR.mkdir(exist_ok=True)

    print("═══ MAGI Kernel ═══")
    print(f"  blocks: {BLOCKS_DIR.resolve()}")
    endpoint = LOCAL_URL if USE_LOCAL else f"{ANTHROPIC_URL} (haiku→sonnet)"
    print(f"  endpoint: {endpoint}")
    print(f"  max instances: {max_instances}")
    print()

    starstone = load_block("starstone")
    escalate_next = False  # flag: use sonnet on next instance

    for n in range(1, max_instances + 1):
        tier = MODEL_SONNET if escalate_next else MODEL_HAIKU
        tier_name = "SONNET" if escalate_next else "haiku"
        escalate_next = False  # reset

        print(f"── Instance {n} ({tier_name}) {'─' * 34}")

        # Load and compile
        function_block = load_block("function")
        compiled = compile_context(function_block)

        print(f"  Compiled {len(compiled)} currents:")
        for key, info in sorted(compiled.items()):
            c = info["compiled"]
            size = len(c) if isinstance(c, list) else len(json.dumps(c))
            print(f"    [{key}] {info['ref']} ({info['mode']}) → {size} items/chars")

        # Build prompts
        system_prompt = build_system(starstone, function_block, compiled)
        message = build_message(compiled)

        print(f"  System: {len(system_prompt)} chars | Message: {len(message)} chars")

        if dry:
            print("\n=== SYSTEM PROMPT ===")
            print(system_prompt[:2000])
            print("\n=== MESSAGE ===")
            print(message[:2000])
            break

        # Call LLM
        print(f"  Calling {tier_name}...", end=" ", flush=True)
        t0 = time.time()
        try:
            raw = call_llm(system_prompt, message, model=tier)
            elapsed = time.time() - t0
            print(f"done ({elapsed:.1f}s)")
        except Exception as e:
            print(f"FAILED: {e}")
            break

        # Parse and process
        output = parse_output(raw)
        status = output.get("status", "?")
        note = output.get("note", "")

        print(f"  Status: {status}")
        print(f"  Note: {note[:120]}")

        result_status = process_output(output, n)

        if result_status == "escalate":
            if tier_name == "haiku":
                print(f"  ↑ Escalating to Sonnet for next instance")
                escalate_next = True
            else:
                print(f"\n═══ Sonnet also escalated at instance {n} — needs Opus or human ═══")
                break
        elif result_status == "complete":
            # Check for unworked purpose branches
            purpose = load_block("purpose")
            digit_keys = sorted(k for k in purpose if k.isdigit())
            # Find the highest purpose branch — that's likely the self-proposed next
            # Check if there are purpose branches beyond what's been worked
            current_max = max(int(k) for k in digit_keys) if digit_keys else 0
            if current_max > 2:
                # There's a self-proposed purpose (branch 3+). Advance to it.
                print(f"  → Auto-advancing to purpose branch {current_max}")
                # Update function block to point purpose at the next branch
                func = load_block("function")
                if "1" in func and isinstance(func["1"], dict):
                    us = func["1"].get("_", {})
                    if isinstance(us, dict):
                        us["_"] = f"Purpose current. Working on branch {current_max}."
                        us["1"] = f"purpose:{current_max}"
                        func["1"]["_"] = us
                save_block("function", func)
            else:
                print(f"\n═══ Complete at instance {n} — no further purposes ═══")
                break

        if n < max_instances:
            print(f"  ... waiting {DELAY}s")
            time.sleep(DELAY)

    # Summary
    print("\n── Final state ──")
    for f in sorted(BLOCKS_DIR.glob("*.json")):
        print(f"  {f.name}: {f.stat().st_size} bytes")

    # Show result if written
    det = load_block("determinacy")
    for key in ("result", "introduction"):
        if key in det:
            print(f"\n── {key} ──")
            print(json.dumps(det[key], indent=2, ensure_ascii=False))

    # Show proposed purpose if written
    purpose = load_block("purpose")
    if "3" in purpose:
        print("\n── Proposed next purpose ──")
        print(json.dumps(purpose["3"], indent=2, ensure_ascii=False))


# ═══ Entry Point ═════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MAGI kernel")
    parser.add_argument("--max", type=int, default=MAX_INSTANCES, help="max instances")
    parser.add_argument("--dry", action="store_true", help="print prompts without calling LLM")
    parser.add_argument("--delay", type=int, default=DELAY, help="seconds between instances")
    parser.add_argument("--local", action="store_true", help="use local LM instead of Anthropic")
    parser.add_argument("--model", default=None, help="model: haiku, sonnet, opus (default: sonnet)")
    args = parser.parse_args()
    DELAY = args.delay
    USE_LOCAL = args.local

    if args.model:
        MODEL_MAP = {
            "haiku": "claude-haiku-4-5-20251001",
            "sonnet": "claude-sonnet-4-6",
            "opus": "claude-opus-4-6",
        }
        ANTHROPIC_MODEL = MODEL_MAP.get(args.model, args.model)

    run(max_instances=args.max, dry=args.dry)
