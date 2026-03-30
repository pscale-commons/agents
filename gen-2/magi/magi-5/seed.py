#!/usr/bin/env python3
"""seed.py — pscale kernel v2. Concern-driven, multi-block, tiered.
The kernel walks digits, routes concerns, makes API calls, saves. No interpretation."""

import json, time, os, sys, subprocess, threading, urllib.request
import requests

# --- Logging ---
LOGFILE = "magi-test.log"

def _log(msg):
    ts = time.strftime('%H:%M:%S')
    with open(LOGFILE, 'a') as f:
        f.write(f"[{ts}] {msg}\n")

# ═══════ BSP ═══════

def block_navigate(tree, path):
    """Walk a dot-separated path through the tree. '0' maps to '_'."""
    if not path:
        return tree
    keys = path.split('.')
    node = tree
    for k in keys:
        key = '_' if k == '0' else k
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node

def block_read_node(tree, path):
    """Read node at path: return content + immediate children."""
    node = block_navigate(tree, path)
    if node is None:
        return {"error": f"Path {path} not found"}
    if isinstance(node, str):
        return {"content": node}
    result = {"content": node.get('_', None), "children": {}}
    for k, v in sorted(node.items()):
        if k == '_':
            continue
        if isinstance(v, str):
            result["children"][k] = v
        elif isinstance(v, dict):
            result["children"][k] = v.get('_', '(branch)')
    return result

def block_write_node(tree, path, content):
    """Write content at path. Creates intermediate nodes as needed."""
    keys = path.split('.')
    last = keys[-1]
    last_key = '_' if last == '0' else last
    node = tree
    for k in keys[:-1]:
        key = '_' if k == '0' else k
        if key not in node or not isinstance(node[key], dict):
            if key in node and isinstance(node[key], str):
                node[key] = {'_': node[key]}
            else:
                node[key] = {}
        node = node[key]
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                node[last_key] = parsed
                return {"written": path, "type": "object"}
        except (json.JSONDecodeError, ValueError):
            pass
    node[last_key] = content
    return {"written": path, "type": "string"}

def bsp_spindle(tree, address):
    """BSP spindle extraction. Walk digits, collect text at each step."""
    if '.' in str(address):
        digits = str(address).split('.')
    else:
        digits = list(str(address))
    chain = []
    node = tree
    if isinstance(node, dict) and '_' in node and isinstance(node['_'], str):
        chain.append({"digit": "_", "text": node['_']})
    for d in digits:
        key = '_' if d == '0' else d
        if not isinstance(node, dict) or key not in node:
            break
        node = node[key]
        if isinstance(node, str):
            chain.append({"digit": d, "text": node})
        elif isinstance(node, dict) and '_' in node and isinstance(node['_'], str):
            chain.append({"digit": d, "text": node['_']})
        elif isinstance(node, dict):
            chain.append({"digit": d, "text": "(branch, no underscore)"})
    return {"spindle": chain, "address": str(address)}

# ═══════ ENVIRONMENT TOOLS ═══════

def tool_shell_exec(args):
    r = subprocess.run(args['cmd'], shell=True, capture_output=True, text=True, timeout=30)
    out = r.stdout[:4000]
    if r.stderr:
        out += f'\nSTDERR: {r.stderr[:1000]}'
    return out

def tool_web_fetch(args):
    return urllib.request.urlopen(args['url'], timeout=10).read().decode('utf-8', errors='replace')[:8000]

def tool_file_read(args):
    return open(args['path']).read()[:8000]

def tool_file_write(args):
    open(args['path'], 'w').write(args['content'])
    return f"Written to {args['path']}"

ENV_TOOLS = {
    'shell_exec': tool_shell_exec,
    'web_fetch': tool_web_fetch,
    'file_read': tool_file_read,
    'file_write': tool_file_write,
}

# ═══════ TOOL DEFINITIONS ═══════

TOOL_DEFS = [
    {
        "name": "block_read",
        "description": "Read a node in a named block. Returns content + immediate children. Blocks: seed, purpose, concerns, conversation, history, vision.",
        "input_schema": {
            "type": "object",
            "properties": {
                "block": {"type": "string", "description": "Block name. Default: seed."},
                "path": {"type": "string", "description": "Dot-separated path. '0' = underscore. Examples: '3' reads §3, '0' reads root underscore."}
            },
            "required": ["path"]
        }
    },
    {
        "name": "block_write",
        "description": "Write content to a named block at a path. Creates intermediate nodes. Persists across instances. Vision is read-only.",
        "input_schema": {
            "type": "object",
            "properties": {
                "block": {"type": "string", "description": "Block name. Default: seed."},
                "path": {"type": "string", "description": "Dot-separated path."},
                "content": {"type": "string", "description": "Content to write. JSON strings parsed as objects if valid."}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "bsp",
        "description": "BSP spindle extraction from a named block. Walk digits, collect text at each step. Returns broad-to-specific chain.",
        "input_schema": {
            "type": "object",
            "properties": {
                "block": {"type": "string", "description": "Block name. Default: seed."},
                "address": {"type": "string", "description": "Dot-separated digits or digit string."}
            },
            "required": ["address"]
        }
    },
    {
        "name": "shell_exec",
        "description": "Run a shell command. Returns stdout.",
        "input_schema": {
            "type": "object",
            "properties": {"cmd": {"type": "string"}},
            "required": ["cmd"]
        }
    },
    {
        "name": "web_fetch",
        "description": "Fetch a URL. Returns page content (max 8000 chars).",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"]
        }
    },
    {
        "name": "file_read",
        "description": "Read a file. Returns content (max 8000 chars).",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"]
        }
    },
    {
        "name": "file_write",
        "description": "Write content to a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["path", "content"]
        }
    },
]

# ═══════ MULTI-BLOCK LOAD/SAVE ═══════

BLOCK_FILES = {
    'seed': 'shell.json',
    'purpose': 'purpose.json',
    'concerns': 'concerns.json',
    'conversation': 'conversation.json',
    'history': 'history.json',
    'vision': 'vision.json',
}

READONLY_BLOCKS = {'vision'}

def load_blocks(directory):
    """Load all blocks from directory. Boot from seed.json if no shell.json."""
    blocks = {}
    shell_path = os.path.join(directory, 'shell.json')
    seed_path = os.path.join(directory, 'seed.json')

    # Seed/shell: resume from shell if exists, else boot from seed
    if os.path.exists(shell_path):
        with open(shell_path) as f:
            blocks['seed'] = json.load(f)
        print(f"[KERNEL] Resumed seed from shell.json")
    elif os.path.exists(seed_path):
        with open(seed_path) as f:
            blocks['seed'] = json.load(f)
        print(f"[KERNEL] First boot from seed.json")
    else:
        print(f"[KERNEL] ERROR: No seed.json found in {directory}")
        sys.exit(1)

    # Load other blocks
    for name, filename in BLOCK_FILES.items():
        if name == 'seed':
            continue
        filepath = os.path.join(directory, filename)
        if os.path.exists(filepath):
            with open(filepath) as f:
                blocks[name] = json.load(f)
            _log(f"Loaded block: {name} from {filename}")
        else:
            # Create minimal default
            blocks[name] = {"_": f"{name.capitalize()} block. Empty at birth."}
            _log(f"Created default block: {name}")

    return blocks

def save_blocks(blocks, directory):
    """Save all mutable blocks to directory."""
    for name, filename in BLOCK_FILES.items():
        if name in READONLY_BLOCKS:
            continue
        filepath = os.path.join(directory, filename)
        with open(filepath, 'w') as f:
            json.dump(blocks.get(name, {}), f, indent=1)

# ═══════ CONCERN ROUTING ═══════

def find_ripe_concern(concerns_block, has_human_input, pending_compaction=False):
    """Scan concerns block, return (key, entry) of highest-tier ripe concern. None if nothing ripe."""
    now = time.time()
    best_key = None
    best_entry = None
    best_tier = 0

    for key in sorted(concerns_block.keys()):
        if key == '_':
            continue
        entry = concerns_block[key]
        if not isinstance(entry, dict):
            continue

        trigger = entry.get('1', '')
        tier = int(entry.get('2', '1'))
        last_fired_str = entry.get('6', '')

        ripe = False

        if trigger == 'always':
            ripe = True
        elif trigger == 'human':
            ripe = has_human_input
        elif trigger == 'compaction':
            ripe = pending_compaction
        elif trigger.startswith('timer:'):
            try:
                interval = int(trigger.split(':')[1])
                if not last_fired_str:
                    ripe = True  # never fired = overdue
                else:
                    ripe = (now - float(last_fired_str)) >= interval
            except (ValueError, IndexError):
                pass

        if ripe and tier > best_tier:
            best_key = key
            best_entry = entry
            best_tier = tier

    if best_key:
        return best_key, best_entry
    return None, None

# ═══════ HISTORY WRITE ═══════

def write_history(history_block, text):
    """Write text to next free history slot. Returns True if slot 9 was filled (compaction needed).
    Walks to the write edge: descends into the highest occupied branch until a free slot 1-9 is found."""
    node = history_block
    path = []
    while True:
        # Find first free slot 1-9
        slot = None
        for d in range(1, 10):
            if str(d) not in node:
                slot = d
                break
        if slot is not None:
            full_path = '.'.join(path + [str(slot)])
            block_write_node(history_block, full_path, text)
            return slot == 9  # True = group full, compaction needed
        # All 1-9 occupied — descend into highest branch
        highest = str(max(int(k) for k in node if k.isdigit() and k != '0'))
        if not isinstance(node[highest], dict):
            # Highest slot is a string, not a branch — wrap it
            node[highest] = {'_': node[highest]}
        path.append(highest)
        node = node[highest]

# ═══════ CONTEXT COMPILATION ═══════

def compile_system(blocks, context_names):
    """System prompt = named blocks as JSON object. Only includes blocks listed."""
    compiled = {}
    for name in context_names:
        name = name.strip()
        if name in blocks:
            compiled[name] = blocks[name]
    return json.dumps(compiled, indent=1)

def compile_message(blocks, concern_entry, user_input=None):
    """Message = conditions + concern purpose + human input."""
    parts = []

    # Conditions from seed §3
    seed = blocks.get('seed', {})
    conditions = seed.get('3', '')
    if isinstance(conditions, dict):
        conditions = json.dumps(conditions, indent=1)
    parts.append(f"CONDITIONS (seed §3):\n{conditions}")

    # Concern purpose
    if concern_entry:
        concern_purpose = concern_entry.get('4', '')
        if concern_purpose:
            parts.append(f"CONCERN:\n{concern_purpose}")

    # Human input
    if user_input:
        parts.append(f"HUMAN:\n{user_input}")

    return "\n\n".join(parts)

# ═══════ LLM CALL WITH A-LOOP ═══════

def call_llm(config, system, message, blocks):
    """Call API with tools. A-loop: execute tools, return results, repeat
    until end_turn or iteration limit. Returns list of text blocks."""

    url = config.get('1', 'https://api.anthropic.com')
    key = os.environ.get('ANTHROPIC_API_KEY') or config.get('2', '')
    model = config.get('3', 'claude-haiku-4-5-20251001')
    max_tokens = int(config.get('6', 4096))

    messages = [{'role': 'user', 'content': message}]
    text_parts = []

    for iteration in range(10):
        _log(f"  API call {iteration}: model={model}, max_tokens={max_tokens}")
        r = requests.post(f'{url}/v1/messages', headers={
            'x-api-key': key,
            'content-type': 'application/json',
            'anthropic-version': '2023-06-01'
        }, json={
            'model': model,
            'max_tokens': max_tokens,
            'system': system,
            'messages': messages,
            'tools': TOOL_DEFS,
        }, timeout=120)

        data = r.json()
        if 'error' in data:
            _log(f"  API ERROR: {data['error']}")
            raise Exception(f"API error: {data['error']}")

        usage = data.get('usage', {})
        stop = data.get('stop_reason', '?')
        _log(f"  API response: stop={stop}, in={usage.get('input_tokens',0)}, out={usage.get('output_tokens',0)}")

        content = data.get('content', [])
        tool_uses = []

        for blk in content:
            if blk['type'] == 'text':
                text_parts.append(blk['text'])
                _log(f"  LLM_TEXT: {blk['text']}")
            elif blk['type'] == 'tool_use':
                tool_uses.append(blk)

        if not tool_uses:
            break

        messages.append({'role': 'assistant', 'content': content})

        tool_results = []
        for tu in tool_uses:
            name = tu['name']
            tid = tu['id']
            args = tu['input']

            if name == 'block_read':
                block_name = args.get('block', 'seed')
                target = blocks.get(block_name)
                if target is None:
                    result = json.dumps({"error": f"Block '{block_name}' not found"})
                else:
                    result = json.dumps(block_read_node(target, args.get('path', '')), indent=1)
                _log(f"  TOOL: block_read({block_name}, {args.get('path','')}) → {str(result)[:500]}")

            elif name == 'block_write':
                block_name = args.get('block', 'seed')
                if block_name in READONLY_BLOCKS:
                    result = json.dumps({"error": f"Block '{block_name}' is read-only"})
                else:
                    target = blocks.get(block_name)
                    if target is None:
                        result = json.dumps({"error": f"Block '{block_name}' not found"})
                    else:
                        result = json.dumps(block_write_node(target, args['path'], args['content']))
                _log(f"  TOOL: block_write({block_name}, {args['path']}) ← {args.get('content','')[:300]}")
                print(f"  [WRITE] {block_name}.{args['path']} ← {args.get('content','')[:100]}")

            elif name == 'bsp':
                block_name = args.get('block', 'seed')
                target = blocks.get(block_name)
                if target is None:
                    result = json.dumps({"error": f"Block '{block_name}' not found"})
                else:
                    result = json.dumps(bsp_spindle(target, args['address']), indent=1)
                _log(f"  TOOL: bsp({block_name}, {args['address']}) → {str(result)[:500]}")

            elif name in ENV_TOOLS:
                try:
                    result = ENV_TOOLS[name](args)
                except Exception as e:
                    result = f"Error: {e}"
                _log(f"  TOOL: {name}({json.dumps(args)[:150]}) → {str(result)[:500]}")
                print(f"  [TOOL] {name}: {str(result)[:200]}")
            else:
                result = f"Unknown tool: {name}"
                _log(f"  TOOL: UNKNOWN {name}")

            tool_results.append({
                'type': 'tool_result',
                'tool_use_id': tid,
                'content': str(result)[:8000]
            })

        messages.append({'role': 'user', 'content': tool_results})

        if data.get('stop_reason') == 'end_turn':
            break

    return text_parts

# ═══════ CONVERSATION ═══════

def append_conversation(blocks, human_msg, agent_text):
    """Append exchange to conversation block. Keep last 20."""
    conv = blocks.setdefault('conversation', {'_': 'Conversation.'})
    keys = sorted([k for k in conv if k != '_' and k.isdigit()], key=int)
    next_key = str(int(keys[-1]) + 1) if keys else '1'
    conv[next_key] = {'1': human_msg or '', '2': agent_text or ''}
    # Trim to last 20
    keys = sorted([k for k in conv if k != '_' and k.isdigit()], key=int)
    while len(keys) > 20:
        del conv[keys.pop(0)]

# ═══════ INPUT ═══════

input_buffer = []
input_lock = threading.Lock()

def input_thread():
    while True:
        try:
            line = input()
            with input_lock:
                input_buffer.append(line)
        except EOFError:
            break

def collect_input():
    """Collect input. If present, pause briefly to catch multi-line pastes."""
    with input_lock:
        if not input_buffer:
            return None
        # Drain what's there
        lines = list(input_buffer)
        input_buffer.clear()

    # Brief pause for multi-line paste to arrive
    time.sleep(1.5)

    with input_lock:
        if input_buffer:
            lines.extend(input_buffer)
            input_buffer.clear()

    return '\n'.join(lines)

# ═══════ MAIN LOOP ═══════

TIER_NAMES = {'1': 'Haiku', '2': 'Sonnet', '3': 'Opus'}

def main():
    directory = sys.argv[1] if len(sys.argv) > 1 else '.'

    # Load all blocks
    blocks = load_blocks(directory)

    config = blocks['seed'].get('5', {})
    default_model = config.get('3', 'claude-haiku-4-5-20251001')
    print(f"[KERNEL] Default model: {default_model}")
    print(f"[KERNEL] Blocks loaded: {', '.join(blocks.keys())}")
    print(f"[KERNEL] Type messages. 'quit' to stop.\n")

    _log(f"=== KERNEL BOOT === dir={directory} blocks={list(blocks.keys())}")

    # Record kernel modification time for restart detection
    kernel_path = os.path.join(directory, 'seed.py')
    kernel_mtime = os.path.getmtime(kernel_path) if os.path.exists(kernel_path) else 0

    t = threading.Thread(target=input_thread, daemon=True)
    t.start()

    cycle = 0
    pending_compaction = False

    while True:
        # Re-read config each cycle (agent can change it)
        config = blocks['seed'].get('5', {})
        pulse = int(config.get('4', 30))

        # Check switch
        if config.get('5') == 'off':
            print("[KERNEL] Switch off. Stopping.")
            _log("=== SWITCH OFF ===")
            break

        cycle += 1

        # Collect user input (with multi-line join)
        user_input = collect_input()
        if user_input and user_input.strip().lower() == 'quit':
            print("[KERNEL] Quit.")
            _log("=== QUIT ===")
            save_blocks(blocks, directory)
            break

        # Find ripe concern
        has_human = user_input is not None
        concern_key, concern_entry = find_ripe_concern(
            blocks.get('concerns', {}), has_human, pending_compaction
        )

        if not concern_entry:
            # Nothing ripe — sleep and check again
            _log(f"=== CYCLE {cycle} === No ripe concern. Sleeping {pulse}s.")
            time.sleep(pulse)
            continue

        # Clear compaction flag if the compaction concern just fired
        if concern_entry.get('1', '') == 'compaction':
            pending_compaction = False

        # Extract concern properties
        concern_tier = concern_entry.get('2', '1')
        concern_model = concern_entry.get('3', default_model)
        concern_desc = concern_entry.get('_', f'concern {concern_key}')
        context_str = concern_entry.get('5', 'seed')
        context_names = [s.strip() for s in context_str.split(',')]

        tier_name = TIER_NAMES.get(concern_tier, f'Tier {concern_tier}')

        _log(f"=== CYCLE {cycle} === concern={concern_key} tier={tier_name} model={concern_model}")
        _log(f"  Context: {context_names}")
        _log(f"  Input: {repr(user_input)[:200] if user_input else 'None'}")

        print(f"--- Cycle {cycle} [{tier_name}] {concern_desc} ---")
        if user_input:
            print(f"  [HUMAN] {user_input}")

        # Compile context from concern's block list
        system = compile_system(blocks, context_names)
        message = compile_message(blocks, concern_entry, user_input)

        # Full context log — what the LLM actually receives
        ctx_path = os.path.join(directory, f"context-{cycle}.txt")
        with open(ctx_path, 'w') as f:
            f.write(f"=== CYCLE {cycle} | {tier_name} | {concern_desc} ===\n")
            f.write(f"Model: {concern_model}\n")
            f.write(f"Context blocks: {context_names}\n\n")
            f.write(f"=== SYSTEM PROMPT ({len(system)} chars) ===\n")
            f.write(system)
            f.write(f"\n\n=== MESSAGE ({len(message)} chars) ===\n")
            f.write(message)

        _log(f"SYSTEM ({len(system)} chars)")
        _log(f"MESSAGE ({len(message)} chars):\n{message}")
        _log(f"Context written to {ctx_path}")

        # Override model from concern
        call_config = dict(config)
        call_config['3'] = concern_model

        # Call LLM — A-loop executes all tools, modifies blocks in-place
        try:
            text_parts = call_llm(call_config, system, message, blocks)
        except Exception as e:
            print(f"  [KERNEL] Error: {e}")
            _log(f"CYCLE ERROR: {e}")
            time.sleep(pulse)
            continue

        # Collect agent text
        agent_text = '\n'.join(tp.strip() for tp in text_parts if tp.strip())

        # Display agent response (no truncation)
        if agent_text:
            print(f"\n  [AGENT] {agent_text}\n")

        # Record conversation
        append_conversation(blocks, user_input, agent_text)

        # Write agent output to history (the output IS the history)
        if agent_text:
            needs_compaction = write_history(blocks['history'], agent_text[:500])
            if needs_compaction:
                pending_compaction = True
                _log(f"  HISTORY: slot 9 filled, compaction pending")

        # Update last_fired on the concern
        block_write_node(blocks['concerns'], f"{concern_key}.6", str(time.time()))

        # Show state
        conditions = blocks['seed'].get('3', '')
        if isinstance(conditions, str):
            print(f"  [CONDITIONS] {conditions}")
        elif isinstance(conditions, dict):
            print(f"  [CONDITIONS] {json.dumps(conditions)}")

        purpose = blocks.get('purpose', {})
        p_desc = purpose.get('_', '')
        if p_desc:
            print(f"  [PURPOSE] {p_desc}")
        for pk in sorted(k for k in purpose if k != '_' and k.isdigit()):
            pv = purpose[pk]
            if isinstance(pv, str) and pv:
                print(f"  [PURPOSE.{pk}] {pv}")

        # Log state
        _log(f"CONDITIONS AFTER: {json.dumps(blocks['seed'].get('3', ''))}")
        _log(f"PURPOSE AFTER: {json.dumps(blocks.get('purpose', {}))}")
        _log(f"HISTORY: {json.dumps(blocks.get('history', {}))}")

        # Save all blocks
        save_blocks(blocks, directory)

        # Check if entity modified the kernel — restart if so
        if os.path.exists(kernel_path) and os.path.getmtime(kernel_path) > kernel_mtime:
            print("[KERNEL] Kernel modified. Restarting...")
            _log("=== KERNEL RESTART — seed.py modified ===")
            os.execv(sys.executable, [sys.executable] + sys.argv)

        # Re-read pulse (agent may have changed §5.4 this cycle)
        pulse = int(blocks['seed'].get('5', {}).get('4', 30))
        print(f"  [KERNEL] Saved. [{tier_name}] Next check in {pulse}s.\n")

        _log(f"=== CYCLE {cycle} END ===\n")
        time.sleep(pulse)

if __name__ == '__main__':
    main()
