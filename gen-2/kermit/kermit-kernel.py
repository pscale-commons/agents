#!/usr/bin/env python3
"""
Kermit Kernel — hybrid synthesis.

G0's seed design (two-channel compilation, unfold, pscale instructions)
+ Magi's tool_use mechanics (A-loop execution, update_block persistence).

Layer 1 (mechanics): load block, compile context, call LLM with tools,
                     execute A-loop, persist via update_block, save, repeat.
Layer 2 (semantics): compile functions shape what the LLM experiences as currents.

The kernel is mechanical. All decisions belong to the LLM.
Python 3 stdlib only — no pip installs.
"""

import json, os, sys, time, subprocess, threading, urllib.request, ssl

SEED = "kermit-seed.json"
SHELL = "kermit-shell.json"

# --- Test logging ---
LOGFILE = "kermit-test.log"

def _log(msg):
    ts = time.strftime('%H:%M:%S')
    with open(LOGFILE, 'a') as f:
        f.write(f"[{ts}] {msg}\n")

# ---------------------------------------------------------------------------
# Block I/O
# ---------------------------------------------------------------------------

def load():
    path = SHELL if os.path.exists(SHELL) else SEED
    with open(path) as f:
        return json.load(f), path

def save(block):
    with open(SHELL, 'w') as f:
        json.dump(block, f, indent=1, ensure_ascii=False)

# ---------------------------------------------------------------------------
# BSP — the walk function
# ---------------------------------------------------------------------------

def bsp(node, digits):
    """Walk tree by digit string, collect text at each step."""
    chain = []
    for d in digits:
        k = '_' if d == '0' else d
        if isinstance(node, dict) and k in node:
            node = node[k]
            chain.append(node.get('_', node) if isinstance(node, dict) else node)
        else:
            break
    return chain

# ---------------------------------------------------------------------------
# Unfold — render pscale section as readable text for the LLM
# ---------------------------------------------------------------------------

def unfold(obj, indent=0):
    """Unfold a pscale section into readable text."""
    if isinstance(obj, str):
        return obj
    if not isinstance(obj, dict):
        return str(obj)
    lines = []
    prefix = "  " * indent
    if '_' in obj:
        lines.append(prefix + unfold(obj['_']))
    for k in sorted((k for k in obj if k != '_'),
                     key=lambda x: int(x) if x.isdigit() else 0):
        val = obj[k]
        if isinstance(val, str):
            lines.append(f"{prefix}  {k}. {val}")
        elif isinstance(val, dict):
            lines.append(f"{prefix}  {k}.")
            lines.append(unfold(val, indent + 2))
    return '\n'.join(lines)

# ---------------------------------------------------------------------------
# Context compilation — two-channel model
#
# System prompt (slow-changing, constitutional):
#   - Constitution current: touchstone (§1) + operations (§2)
#   - Purpose current: direction (§4)
#
# Message (fast-changing, present moment):
#   - Concern current: the active gap (§3)
#   - Environment: human input + recent conversation
# ---------------------------------------------------------------------------

def compile_system(block):
    """Constitution current + purpose current → system prompt."""
    parts = []

    # Constitution: touchstone + operations
    parts.append(unfold(block.get('1', {})))
    parts.append("")
    parts.append(unfold(block.get('2', {})))

    # Purpose (only if written)
    purpose = block.get('4', {})
    p_text = unfold(purpose).strip()
    if p_text and 'Empty until' not in p_text:
        parts.append("")
        parts.append(f"YOUR PURPOSE:\n{p_text}")

    return '\n'.join(parts)


def compile_message(block, user_input=None):
    """Concern + environment → message."""
    parts = []

    # Concern current
    parts.append(f"CONCERN:\n{unfold(block.get('3', {}))}")

    # Human input (disturbance)
    if user_input:
        parts.append(f"HUMAN INPUT:\n{user_input}")

    # Recent conversation (last 3 exchanges)
    conv = block.get('6', {})
    recent = []
    keys = sorted([k for k in conv if k != '_' and k.isdigit()], key=int)
    for k in keys[-3:]:
        entry = conv[k]
        if isinstance(entry, dict):
            h = entry.get('1', '')
            a = entry.get('2', '')
            if h: recent.append(f"Human: {h}")
            if a: recent.append(f"Agent: {a}")
    if recent:
        parts.append("RECENT CONVERSATION:\n" + "\n".join(recent))

    return "\n\n".join(parts)

# ---------------------------------------------------------------------------
# Environment tools — A-loop (execute within instance, results return now)
# ---------------------------------------------------------------------------

def tool_shell_exec(args):
    r = subprocess.run(
        args['cmd'], shell=True, capture_output=True, text=True, timeout=30
    )
    out = r.stdout + r.stderr
    return out[:4000] if out else "(no output)"

def tool_web_fetch(args):
    ctx = ssl.create_default_context()
    return urllib.request.urlopen(
        args['url'], context=ctx
    ).read().decode('utf-8', errors='replace')[:8000]

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

# ---------------------------------------------------------------------------
# Tool definitions for Anthropic tool_use API
# ---------------------------------------------------------------------------

TOOL_DEFS = [
    {
        "name": "shell_exec",
        "description": "Run a shell command. Returns stdout + stderr (max 4000 chars).",
        "input_schema": {
            "type": "object",
            "properties": {"cmd": {"type": "string", "description": "Shell command"}},
            "required": ["cmd"]
        }
    },
    {
        "name": "web_fetch",
        "description": "Fetch a URL. Returns page content (max 8000 chars).",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "URL to fetch"}},
            "required": ["url"]
        }
    },
    {
        "name": "file_read",
        "description": "Read a file. Returns content (max 8000 chars).",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "File path"}},
            "required": ["path"]
        }
    },
    {
        "name": "file_write",
        "description": "Write content to a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "content": {"type": "string", "description": "Content to write"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "update_block",
        "description": "Persist your state for the next instance. Call this LAST, after all other tools. Concern is required — it is your thread of continuity.",
        "input_schema": {
            "type": "object",
            "properties": {
                "concern": {
                    "type": "string",
                    "description": "Current state and next gap. Required. This IS your continuity."
                },
                "purpose": {
                    "type": "string",
                    "description": "Updated purpose text. Only include if purpose has changed."
                },
                "response": {
                    "type": "string",
                    "description": "Text for the human. Only include if communicating."
                }
            },
            "required": ["concern"]
        }
    }
]

# ---------------------------------------------------------------------------
# LLM API — tool_use with A-loop
# ---------------------------------------------------------------------------

def api_call(config, system, messages):
    """Make one Anthropic API call with tools. Returns parsed response dict."""
    url = config.get('1', 'https://api.anthropic.com')
    key = os.environ.get('ANTHROPIC_API_KEY') or config.get('2', '')
    model = config.get('3', 'claude-sonnet-4-20250514')

    if not key:
        raise ValueError("No API key. Set ANTHROPIC_API_KEY or section 5.2.")

    body = json.dumps({
        'model': model,
        'max_tokens': 4096,
        'system': system,
        'messages': messages,
        'tools': TOOL_DEFS,
    }).encode('utf-8')

    req = urllib.request.Request(
        f'{url}/v1/messages',
        data=body,
        headers={
            'x-api-key': key,
            'content-type': 'application/json',
            'anthropic-version': '2023-06-01'
        }
    )
    _log(f"  API call: model={model}, url={url}/v1/messages")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))


def call_with_tools(config, system, message):
    """Run A-loop: call LLM, execute tools, feed results back, until
    update_block is called or no more tool use. Returns (update_args, texts)."""

    messages = [{'role': 'user', 'content': message}]
    text_parts = []
    update_args = None

    for iteration in range(10):  # safety cap on A-loop depth
        _log(f"  A-loop iteration {iteration}")
        try:
            data = api_call(config, system, messages)
        except Exception as e:
            raise RuntimeError(f"API call failed: {e}")

        if 'error' in data:
            _log(f"  API ERROR: {data['error']}")
            raise RuntimeError(f"API error: {data['error']}")

        usage = data.get('usage', {})
        stop = data.get('stop_reason', '?')
        _log(f"  API response: stop={stop}, in={usage.get('input_tokens',0)}, out={usage.get('output_tokens',0)}")

        content = data.get('content', [])
        tool_uses = []

        for blk in content:
            if blk.get('type') == 'text':
                text_parts.append(blk['text'])
                _log(f"  LLM_TEXT: {blk['text'][:300]}")
            elif blk.get('type') == 'tool_use':
                tool_uses.append(blk)

        # No tool calls — done
        if not tool_uses:
            break

        # Add assistant response to conversation
        messages.append({'role': 'assistant', 'content': content})

        # Execute each tool, collect results
        tool_results = []
        for tu in tool_uses:
            name = tu['name']
            tid = tu['id']
            args = tu['input']

            if name == 'update_block':
                update_args = args
                _log(f"  TOOL: update_block concern={repr(args.get('concern',''))[:200]}")
                _log(f"  TOOL: update_block response={repr(args.get('response',''))[:200]}")
                if args.get('purpose'):
                    _log(f"  TOOL: update_block purpose={repr(args['purpose'])[:200]}")
                tool_results.append({
                    'type': 'tool_result',
                    'tool_use_id': tid,
                    'content': 'Block updated. Instance ending.'
                })
            elif name in ENV_TOOLS:
                try:
                    result = ENV_TOOLS[name](args)
                except Exception as e:
                    result = f"Error: {e}"
                _log(f"  TOOL: {name}({json.dumps(args)[:100]}) → {str(result)[:200]}")
                tool_results.append({
                    'type': 'tool_result',
                    'tool_use_id': tid,
                    'content': str(result)
                })
                print(f"  [tool] {name}: {str(result)[:200]}")
            else:
                tool_results.append({
                    'type': 'tool_result',
                    'tool_use_id': tid,
                    'content': f"Unknown tool: {name}"
                })

        messages.append({'role': 'user', 'content': tool_results})

        # If update_block was called, stop the A-loop
        if update_args:
            break

        # If LLM stopped on its own
        if data.get('stop_reason') == 'end_turn':
            break

    return update_args, text_parts

# ---------------------------------------------------------------------------
# Apply update_block to the block
# ---------------------------------------------------------------------------

def apply_update(block, update_args):
    """Write update_block fields into the block. Returns agent response or None."""
    if not update_args:
        return None

    # Concern (required) — becomes §3
    concern_text = update_args.get('concern', '')
    if concern_text:
        block['3'] = {'_': concern_text}

    # Purpose (optional) — becomes §4
    purpose_text = update_args.get('purpose')
    if purpose_text:
        block['4'] = {'_': purpose_text}

    # Response (optional) — returned for display and conversation logging
    return update_args.get('response')

# ---------------------------------------------------------------------------
# Conversation management
# ---------------------------------------------------------------------------

def add_conversation(block, human_msg, agent_msg):
    """Add exchange to section 6. Keep last 9."""
    conv = block.setdefault('6', {'_': 'Conversation.'})
    keys = sorted([k for k in conv if k != '_' and k.isdigit()], key=int)
    next_key = str(int(keys[-1]) + 1) if keys else '1'
    conv[next_key] = {'1': human_msg or '', '2': agent_msg or ''}

    # Cap at 9 entries
    keys = sorted([k for k in conv if k != '_' and k.isdigit()], key=int)
    while len(keys) > 9:
        del conv[keys.pop(0)]

# ---------------------------------------------------------------------------
# Non-blocking input via thread
# ---------------------------------------------------------------------------

input_buffer = []
input_lock = threading.Lock()

def input_thread():
    """Read stdin in background so the kernel doesn't block."""
    while True:
        try:
            line = input()
            with input_lock:
                input_buffer.append(line)
        except EOFError:
            break

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    print("Kermit Kernel")
    print("=" * 40)

    # Load
    block, source = load()
    config = block.get('5', {})
    model = config.get('3', '?')
    pulse = int(config.get('4', '30'))

    print(f"Loaded from: {source}")
    print(f"Model: {model}")
    print(f"Pulse: {pulse}s")

    _log(f"=== KERNEL BOOT === source={source}, model={model}, pulse={pulse}s")

    # Check API key
    key = os.environ.get('ANTHROPIC_API_KEY') or config.get('2', '')
    if not key:
        key = input("API key (section 5.2 is empty): ").strip()
        if key:
            config['2'] = key
            save(block)
            print("Key saved to shell.")

    print("Type messages at any time. 'quit' to stop.\n")

    # Start non-blocking input thread
    t = threading.Thread(target=input_thread, daemon=True)
    t.start()

    cycle_num = 0

    while True:
        # Check switch
        if config.get('5') != 'on':
            print("[kernel] Switch is off (5.5). Stopping.")
            _log("Switch off. Stopping.")
            break

        cycle_num += 1

        # Collect user input (non-blocking)
        user_input = None
        with input_lock:
            if input_buffer:
                user_input = input_buffer.pop(0)

        if user_input and user_input.strip().lower() in ('quit', 'exit', 'q'):
            print("[kernel] Stopping.")
            _log("User quit.")
            save(block)
            break

        # Compile context
        system = compile_system(block)
        message = compile_message(block, user_input)

        print(f"\n--- Cycle {cycle_num} ---")
        if user_input:
            print(f"  [human] {user_input}")

        _log(f"=== CYCLE {cycle_num} === input: {repr(user_input)[:200]}")
        _log(f"SYSTEM ({len(system)} chars):\n{system[:800]}")
        _log(f"MESSAGE ({len(message)} chars):\n{message[:800]}")

        # Call LLM with A-loop tool execution
        print(f"  [calling {model}...]")
        try:
            update_args, text_parts = call_with_tools(config, system, message)
        except Exception as e:
            _log(f"CYCLE ERROR: {e}")
            print(f"  [error] {e}")
            time.sleep(pulse)
            continue

        # Show any thinking text
        for t_part in text_parts:
            t_stripped = t_part.strip()
            if t_stripped:
                print(f"  [thinking] {t_stripped[:500]}")

        # Apply update_block
        if update_args:
            agent_response = apply_update(block, update_args)
            if agent_response:
                print(f"\n  Agent: {agent_response}\n")
            add_conversation(block, user_input, agent_response or '')

            # Show concern for debugging
            concern = block.get('3', {})
            c_text = concern.get('_', '') if isinstance(concern, dict) else str(concern)
            print(f"  [concern] {c_text[:200]}")
        else:
            print("  [no update_block call — state not persisted this cycle]")

        # Save
        save(block)

        _log(f"CONCERN AFTER: {block.get('3', {}).get('_', '')[:300] if isinstance(block.get('3'), dict) else str(block.get('3', ''))[:300]}")
        _log(f"=== CYCLE {cycle_num} END ===\n")

        print(f"  [saved. next in {pulse}s]")
        time.sleep(pulse)


if __name__ == '__main__':
    main()
