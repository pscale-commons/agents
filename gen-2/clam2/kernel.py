#!/usr/bin/env python3
"""Clam 2 Kernel — A-loop tools, full-block persistence, compiled currents.

Layer 1 (mechanics): load block, compile context, call LLM with tools,
    execute environment tools within instance, persist via update_block, repeat.
Layer 2 (semantics): the compile functions shape what the LLM experiences
    as currents in its context window.

The kernel is mechanical. All decisions belong to the LLM.
Stdlib only — no pip installs.
"""

import json, os, sys, re, time, threading, subprocess, urllib.request, urllib.error, ssl

SEED = "seed.json"
SHELL = "shell.json"

# --- Test logging ---
LOGFILE = "clam2-test.log"

def _log(msg):
    ts = time.strftime('%H:%M:%S')
    with open(LOGFILE, 'a') as f:
        f.write(f"[{ts}] {msg}\n")

# ---------------------------------------------------------------------------
# .env loader
# ---------------------------------------------------------------------------

def load_dotenv():
    """Load .env file into os.environ if present."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

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
# Unfold — render pscale section as readable text for the LLM
# ---------------------------------------------------------------------------

def unfold(obj, indent=0):
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
# Compile context window — the bridge between block and LLM experience
#
# System prompt (slow-changing, constitutional):
#   - Constitution current: touchstone (§1) + operations (§2)
#   - Purpose current: direction (§4)
#
# Message (fast-changing, present moment):
#   - Concern current: the active gap (§3)
#   - Environment current: human input + recent conversation
#   - The full block: so the LLM can read its body and return it modified
# ---------------------------------------------------------------------------

def compile_system(block):
    """Constitution + purpose + format instruction → system prompt."""
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

    # Format instruction — reinforced so it frames all processing
    parts.append("")
    parts.append(
        "RESPONSE: Use the provided tools. Call environment tools first "
        "(shell_exec, web_fetch, file_read, file_write) to gather information "
        "and act. Then call update_block LAST with the complete updated block. "
        "Everything you want to persist goes in the block. "
        "Words for the human go in section 6."
    )

    return '\n'.join(parts)


def compile_message(block, user_input=None):
    """Concern + environment + full block → message."""
    parts = []

    # Concern current
    parts.append(f"CONCERN:\n{unfold(block.get('3', {}))}")

    # Environment: human input (disturbance)
    if user_input:
        parts.append(f"HUMAN INPUT:\n{user_input}")

    # Environment: recent conversation (last 3 exchanges)
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
        parts.append("RECENT:\n" + "\n".join(recent))

    # Full block — the body the LLM reads and returns modified via update_block
    parts.append(f"BLOCK:\n{json.dumps(block, indent=1, ensure_ascii=False)}")

    return "\n\n".join(parts)

# ---------------------------------------------------------------------------
# Environment tools — A-loop, execute within instance
# ---------------------------------------------------------------------------

ENV_TOOLS = {
    'shell_exec': lambda a: subprocess.run(
        a['cmd'], shell=True, capture_output=True, text=True, timeout=30
    ).stdout[:4000],

    'web_fetch': lambda a: urllib.request.urlopen(
        a['url'], context=ssl.create_default_context()
    ).read().decode('utf-8', errors='replace')[:8000],

    'file_read': lambda a: open(a['path']).read()[:8000],

    'file_write': lambda a: (
        open(a['path'], 'w').write(a['content']),
        f"Written to {a['path']}"
    )[1],
}

# ---------------------------------------------------------------------------
# Tool definitions for Anthropic API
# ---------------------------------------------------------------------------

TOOL_DEFS = [
    {
        "name": "shell_exec",
        "description": "Run a shell command. Returns stdout (max 4000 chars).",
        "input_schema": {
            "type": "object",
            "properties": {"cmd": {"type": "string", "description": "Shell command"}},
            "required": ["cmd"]
        }
    },
    {
        "name": "web_fetch",
        "description": "Fetch a URL via HTTP GET. Returns content (max 8000 chars).",
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
        "description": "Write content to a file. Returns confirmation.",
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
        "description": "Persist the updated block for the next instance. Call this LAST, after all environment tools. The block you pass becomes the next instance's body. Section 3 (concern) must reflect where things now stand. Section 5 (config) is preserved by the kernel automatically.",
        "input_schema": {
            "type": "object",
            "properties": {
                "block": {
                    "type": "object",
                    "description": "The complete updated block with all sections."
                }
            },
            "required": ["block"]
        }
    }
]

# ---------------------------------------------------------------------------
# Anthropic API call (stdlib only)
# ---------------------------------------------------------------------------

def api_post(url, key, body):
    """POST to Anthropic messages endpoint. Returns parsed JSON."""
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(
        f'{url}/v1/messages',
        data=data,
        headers={
            'x-api-key': key,
            'content-type': 'application/json',
            'anthropic-version': '2023-06-01'
        }
    )
    _log(f"  API call: model={body.get('model','?')}, url={url}/v1/messages")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode('utf-8', errors='replace')
        return {'error': {'type': 'http', 'message': f'{e.code}: {body_text[:500]}'}}
    except Exception as e:
        return {'error': {'type': 'network', 'message': str(e)}}

# ---------------------------------------------------------------------------
# A-loop — call LLM, execute tools, repeat until update_block or done
# ---------------------------------------------------------------------------

def call_with_tools(config, system, message):
    """Run the A-loop. Returns the block from update_block, or None."""
    url = config.get('1', 'https://api.anthropic.com')
    key = os.environ.get('ANTHROPIC_API_KEY') or config.get('2', '')
    model = config.get('3', 'claude-sonnet-4-20250514')

    if not key:
        print("  [no API key — set ANTHROPIC_API_KEY or section 5.2]")
        return None

    messages = [{'role': 'user', 'content': message}]
    update_data = None

    for iteration in range(10):  # safety limit
        print(f"  [calling {model}... (turn {iteration + 1})]")
        _log(f"  A-loop iteration {iteration}")

        resp = api_post(url, key, {
            'model': model,
            'max_tokens': 8192,
            'system': system,
            'messages': messages,
            'tools': TOOL_DEFS,
        })

        if 'error' in resp:
            _log(f"  API ERROR: {resp['error']}")
            print(f"  [API error: {resp['error']}]")
            return None

        usage = resp.get('usage', {})
        stop = resp.get('stop_reason', '?')
        _log(f"  API response: stop={stop}, in={usage.get('input_tokens',0)}, out={usage.get('output_tokens',0)}")

        content = resp.get('content', [])
        tool_uses = [b for b in content if b.get('type') == 'tool_use']

        # Show any text blocks (thinking)
        for b in content:
            if b.get('type') == 'text' and b.get('text', '').strip():
                _log(f"  LLM_TEXT: {b['text'][:300]}")
                print(f"  [thinking] {b['text'][:400]}")

        # No tool calls — LLM finished without update_block
        if not tool_uses:
            break

        # Append assistant response to conversation
        messages.append({'role': 'assistant', 'content': content})

        # Execute each tool
        tool_results = []
        for tu in tool_uses:
            name = tu['name']
            tid = tu['id']
            args = tu.get('input', {})

            if name == 'update_block':
                update_data = args.get('block')
                # Log key fields from the returned block
                if update_data:
                    concern = update_data.get('3', {})
                    c_text = concern.get('_', '') if isinstance(concern, dict) else str(concern)
                    _log(f"  TOOL: update_block concern={repr(c_text)[:200]}")
                    purpose = update_data.get('4', {})
                    p_text = purpose.get('_', '') if isinstance(purpose, dict) else str(purpose)
                    _log(f"  TOOL: update_block purpose={repr(p_text)[:200]}")
                    # Log conversation changes
                    conv = update_data.get('6', {})
                    keys = sorted([k for k in conv if k != '_' and k.isdigit()], key=int)
                    if keys:
                        latest = conv[keys[-1]]
                        if isinstance(latest, dict):
                            _log(f"  TOOL: update_block latest_conv: human={repr(latest.get('1',''))[:100]}, agent={repr(latest.get('2',''))[:200]}")
                    # Log block size
                    block_str = json.dumps(update_data)
                    _log(f"  TOOL: update_block block_size={len(block_str)} chars, sections={list(update_data.keys())}")
                tool_results.append({
                    'type': 'tool_result',
                    'tool_use_id': tid,
                    'content': 'Block persisted. Instance ending.'
                })
            elif name in ENV_TOOLS:
                try:
                    result = ENV_TOOLS[name](args)
                except Exception as e:
                    result = f"Error: {e}"
                _log(f"  TOOL: {name}({json.dumps(args)[:100]}) → {str(result)[:200]}")
                print(f"  [{name}] {str(result)[:200]}")
                tool_results.append({
                    'type': 'tool_result',
                    'tool_use_id': tid,
                    'content': str(result)[:4000]
                })
            else:
                tool_results.append({
                    'type': 'tool_result',
                    'tool_use_id': tid,
                    'content': f"Unknown tool: {name}"
                })

        messages.append({'role': 'user', 'content': tool_results})

        # If update_block was called, end the A-loop
        if update_data:
            break

        # If LLM signalled end_turn, stop
        if resp.get('stop_reason') == 'end_turn':
            break

    return update_data

# ---------------------------------------------------------------------------
# Display — extract latest response from conversation section
# ---------------------------------------------------------------------------

def latest_response(block):
    conv = block.get('6', {})
    keys = sorted((k for k in conv if k != '_' and k.isdigit()), key=int)
    if keys:
        entry = conv[keys[-1]]
        if isinstance(entry, dict):
            return entry.get('2', '')
    return ''

# ---------------------------------------------------------------------------
# Non-blocking input thread
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    load_dotenv()

    print("Clam 2 Kernel")
    print("=" * 40)

    block, source = load()
    print(f"Loaded: {source}")

    # API key check
    key = os.environ.get('ANTHROPIC_API_KEY') or block.get('5', {}).get('2', '')
    if not key:
        key = input("API key (ANTHROPIC_API_KEY not set, §5.2 empty): ").strip()
        if key:
            block.setdefault('5', {})['2'] = key
            save(block)
            print("Key saved to shell.")

    config = block.get('5', {})
    model = config.get('3', '?')
    pulse = int(config.get('4', '30'))
    print(f"Model: {model}")
    print(f"Pulse: {pulse}s")

    _log(f"=== KERNEL BOOT === source={source}, model={model}, pulse={pulse}s")

    print(f"Type messages at any time. 'quit' to stop.\n")

    # Start input thread
    t = threading.Thread(target=input_thread, daemon=True)
    t.start()

    cycle_num = 0

    while True:
        # Check switch
        if block.get('5', {}).get('5') != 'on':
            print("Switch off (§5.5). Stopping.")
            _log("Switch off. Stopping.")
            break

        cycle_num += 1
        config = block.get('5', {})
        pulse = int(config.get('4', '30'))

        # Collect user input (non-blocking)
        user_input = None
        with input_lock:
            if input_buffer:
                user_input = input_buffer.pop(0)
        if user_input and user_input.strip().lower() in ('quit', 'exit', 'q'):
            print("Stopping.")
            _log("User quit.")
            break

        # Compile context window
        system = compile_system(block)
        message = compile_message(block, user_input)

        print(f"\n--- Cycle {cycle_num} ---")
        if user_input:
            print(f"  [human] {user_input}")

        _log(f"=== CYCLE {cycle_num} === input: {repr(user_input)[:200]}")
        _log(f"SYSTEM ({len(system)} chars):\n{system[:800]}")
        _log(f"MESSAGE ({len(message)} chars):\n{message[:800]}")

        # Run A-loop
        new_block = call_with_tools(config, system, message)

        if new_block:
            # Preserve config — kernel manages §5
            new_block['5'] = block.get('5', {})
            block = new_block
            save(block)

            # Display agent response
            resp = latest_response(block)
            if resp:
                print(f"\n  Agent: {resp}\n")

            # Show concern for debugging
            concern = block.get('3', {})
            c_text = concern.get('_', '') if isinstance(concern, dict) else str(concern)
            print(f"  [concern] {c_text[:200]}")
        else:
            print("  [no update_block call — state unchanged]")

        _log(f"CONCERN AFTER: {block.get('3', {}).get('_', '') if isinstance(block.get('3'), dict) else str(block.get('3', ''))[:300]}")
        _log(f"PULSE: {pulse}s")
        _log(f"=== CYCLE {cycle_num} END ===\n")

        print(f"  [next cycle in {pulse}s]")
        time.sleep(pulse)


if __name__ == '__main__':
    main()
