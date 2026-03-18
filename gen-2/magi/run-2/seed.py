#!/usr/bin/env python3
"""seed.py — pscale kernel v3.1. Tool_use API + two-channel compilation.
Run-2 patches: Sonnet, seed/shell separation, max_tokens from §5.6."""

import json, time, os, sys, subprocess, threading, urllib.request
import requests

# --- Test logging ---
LOGFILE = "magi-test.log"

def _log(msg):
    ts = time.strftime('%H:%M:%S')
    with open(LOGFILE, 'a') as f:
        f.write(f"[{ts}] {msg}\n")

# --- BSP ---
def bsp(node, digits):
    """Walk tree by digits, collecting text at each step."""
    chain = []
    for d in digits:
        k = '_' if d == '0' else d
        if isinstance(node, dict) and k in node:
            node = node[k]
            chain.append(node.get('_', node) if isinstance(node, dict) else node)
    return chain

# --- Unfold ---
def unfold(obj, depth=0):
    """Render a pscale section as readable numbered text."""
    if isinstance(obj, str):
        return obj
    if not isinstance(obj, dict):
        return str(obj)
    lines = []
    # Underscore first (the section header)
    if '_' in obj:
        lines.append(obj['_'])
    # Then digit keys in order
    for k in sorted(k for k in obj if k != '_'):
        val = obj[k]
        prefix = '  ' * depth + f'{k}.'
        if isinstance(val, str):
            if val:  # skip empty strings
                lines.append(f'{prefix} {val}')
        elif isinstance(val, dict):
            sub = unfold(val, depth + 1)
            if sub:
                lines.append(f'{prefix} {sub}')
    return '\n'.join(lines)

# --- Environment tools (A-loop) ---
def tool_shell_exec(args):
    r = subprocess.run(args['cmd'], shell=True, capture_output=True, text=True, timeout=30)
    out = r.stdout[:4000]
    if r.stderr:
        out += f'\nSTDERR: {r.stderr[:1000]}'
    return out

def tool_web_fetch(args):
    req = urllib.request.Request(args['url'])
    return urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='replace')[:8000]

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

# --- Tool definitions for Anthropic API ---
TOOL_DEFS = [
    {
        "name": "shell_exec",
        "description": "Run a shell command. Returns stdout (and stderr if any).",
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
        "description": "Persist your state for the next instance. Call LAST, after all other tools. Concern is required — your thread of continuity.",
        "input_schema": {
            "type": "object",
            "properties": {
                "concern": {
                    "type": "string",
                    "description": "Next instance's concern: current state and next gap. Compress, don't accumulate."
                },
                "purpose": {
                    "type": "object",
                    "description": "Updated purpose (keys: '1','2','3' etc). Only if changed."
                },
                "response": {
                    "type": "string",
                    "description": "Text for the human. Only if communicating."
                },
                "history": {
                    "type": "string",
                    "description": "Compressed summary of what happened. Appended to history log."
                },
                "sleep": {
                    "type": "integer",
                    "description": "Seconds until next cycle. Use longer values (120-600) when idle with no gap to close. Default is the configured pulse."
                }
            },
            "required": ["concern"]
        }
    }
]

# --- Context compilation (two-channel) ---
def compile_system(block):
    """System prompt = constitution. Sections 1 (format), 2 (operations), 4 (purpose).
    Unfolded into readable text. No config, no conversation."""
    parts = []

    # Root underscore — the reflexive opening
    root = block.get('_', '')
    if root:
        parts.append(root)

    # Section 1: format
    s1 = block.get('1', {})
    parts.append(f"\n== FORMAT ==\n{unfold(s1)}")

    # Section 2: operations
    s2 = block.get('2', {})
    parts.append(f"\n== OPERATIONS ==\n{unfold(s2)}")

    # Section 4: purpose (if populated)
    s4 = block.get('4', {})
    has_purpose = isinstance(s4, dict) and any(v for k, v in s4.items() if k != '_' and v)
    if has_purpose:
        parts.append(f"\n== PURPOSE ==\n{unfold(s4)}")
    else:
        parts.append("\n== PURPOSE ==\nNot yet defined.")

    return '\n'.join(parts)

def compile_message(block, user_input=None):
    """Message = concern + environment (human input) + recent conversation + history."""
    parts = []

    # Concern (section 3)
    concern = block.get('3', '')
    if isinstance(concern, dict):
        concern = unfold(concern)
    parts.append(f"CONCERN:\n{concern}")

    # Human input (disturbance)
    if user_input:
        parts.append(f"HUMAN:\n{user_input}")

    # History summary (section 6.9)
    history = block.get('6', {}).get('9', '')
    if history and isinstance(history, str):
        parts.append(f"HISTORY:\n{history}")

    # Recent conversation (last 3 from section 6)
    conv = block.get('6', {})
    recent = []
    keys = sorted([k for k in conv if k != '_' and k != '9' and k.isdigit()], key=int)
    for k in keys[-3:]:
        entry = conv[k]
        if isinstance(entry, dict):
            h = entry.get('1', '')
            a = entry.get('2', '')
            if h or a:
                if h: recent.append(f"  Human: {h}")
                if a: recent.append(f"  Agent: {a}")
    if recent:
        parts.append("RECENT:\n" + "\n".join(recent))

    return "\n\n".join(parts)

# --- LLM call with A-loop tool execution ---
def call_llm_with_tools(config, system, message):
    """Call Anthropic API. A-loop: execute tools, return results, repeat
    until update_block or end_turn. Returns (update_args, text_parts)."""

    url = config.get('1', 'https://api.anthropic.com')
    key = os.environ.get('ANTHROPIC_API_KEY') or config.get('2', '')
    model = config.get('3', 'claude-sonnet-4-20250514')
    max_tokens = int(config.get('6', 8192))

    messages = [{'role': 'user', 'content': message}]
    text_parts = []
    update_args = None

    for iteration in range(10):  # A-loop safety limit
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
        }, timeout=60)

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
                _log(f"  LLM_TEXT: {blk['text'][:300]}")
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

            if name == 'update_block':
                update_args = args
                _log(f"  TOOL: update_block concern={repr(args.get('concern',''))[:200]}")
                _log(f"  TOOL: update_block response={repr(args.get('response',''))[:200]}")
                _log(f"  TOOL: update_block sleep={args.get('sleep')}, history={repr(args.get('history',''))[:200]}")
                if args.get('purpose'):
                    _log(f"  TOOL: update_block purpose={json.dumps(args['purpose'])[:200]}")
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
                print(f"  [TOOL] {name}: {str(result)[:200]}")
            else:
                tool_results.append({
                    'type': 'tool_result',
                    'tool_use_id': tid,
                    'content': f"Unknown tool: {name}"
                })

        messages.append({'role': 'user', 'content': tool_results})

        if update_args:
            break
        if data.get('stop_reason') == 'end_turn':
            break

    return update_args, text_parts

# --- Apply update_block ---
def apply_update(block, update_args):
    """Apply update_block to the block. Returns (response_text, sleep_seconds)."""
    if not update_args:
        return None, None

    # Concern (required) — section 3
    block['3'] = update_args.get('concern', block.get('3', ''))

    # Purpose (optional) — section 4
    purpose = update_args.get('purpose')
    if purpose and isinstance(purpose, dict):
        # Preserve underscore if not provided
        if '_' not in purpose:
            purpose['_'] = block.get('4', {}).get('_', 'Purpose.')
        block['4'] = purpose

    # History (optional) — append to section 6.9, compact if too long
    history = update_args.get('history')
    if history:
        existing = block.get('6', {}).get('9', '')
        if existing:
            combined = existing + ' | ' + history
        else:
            combined = history
        # Compact: keep last 500 chars if over 800
        if len(combined) > 800:
            # Find a pipe boundary near the 500-char-from-end mark
            cut = combined[-(500):]
            pipe = cut.find(' | ')
            if pipe > 0:
                combined = '...' + cut[pipe+3:]
            else:
                combined = '...' + cut
        block.setdefault('6', {})['9'] = combined

    sleep = update_args.get('sleep')
    return update_args.get('response'), sleep

# --- Conversation management ---
def add_conversation(block, human_msg, agent_msg):
    """Add exchange to section 6. Keep last 8. Key 9 reserved for history."""
    conv = block.setdefault('6', {'_': 'Conversation and history.'})
    keys = sorted([k for k in conv if k != '_' and k != '9' and k.isdigit()], key=int)
    next_key = str(int(keys[-1]) + 1) if keys else '1'
    if next_key == '9':
        next_key = '10'
    conv[next_key] = {'1': human_msg or '', '2': agent_msg or ''}
    keys = sorted([k for k in conv if k != '_' and k != '9' and k.isdigit()], key=int)
    while len(keys) > 8:
        del conv[keys.pop(0)]

# --- Input thread ---
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

# --- Main loop ---
def main():
    seed_path = sys.argv[1] if len(sys.argv) > 1 else 'seed.json'
    shell_path = seed_path.replace('seed.json', 'shell.json')
    if shell_path == seed_path:
        shell_path = 'shell.json'

    # Load shell if it exists (resume), otherwise load seed (first boot)
    if os.path.exists(shell_path):
        with open(shell_path) as f:
            block = json.load(f)
        print(f"[KERNEL] Resumed from {shell_path}")
    else:
        with open(seed_path) as f:
            block = json.load(f)
        print(f"[KERNEL] First boot from {seed_path}")

    config = block.get('5', {})
    model = config.get('3', 'unknown')
    max_tokens = config.get('6', '8192')
    pulse = int(config.get('4', 30))

    print(f"[KERNEL] Model: {model}")
    print(f"[KERNEL] Max tokens: {max_tokens}")
    print(f"[KERNEL] Pulse: {pulse}s")
    print(f"[KERNEL] Shell: {shell_path}")
    print(f"[KERNEL] Type messages. 'quit' to stop.\n")

    t = threading.Thread(target=input_thread, daemon=True)
    t.start()

    cycle = 0

    while True:
        # Check switch
        if block.get('5', {}).get('5') == 'off':
            print("[KERNEL] Switch off. Stopping.")
            break

        cycle += 1

        # Collect user input
        user_input = None
        with input_lock:
            if input_buffer:
                user_input = input_buffer.pop(0)
        if user_input and user_input.strip().lower() == 'quit':
            print("[KERNEL] Quit.")
            with open(shell_path, 'w') as f:
                json.dump(block, f, indent=1)
            break

        # Compile context
        system = compile_system(block)
        message = compile_message(block, user_input)

        print(f"--- Cycle {cycle} ---")
        _log(f"=== CYCLE {cycle} === input: {repr(user_input)[:200]}")
        _log(f"SYSTEM ({len(system)} chars):\n{system[:800]}")
        _log(f"MESSAGE ({len(message)} chars):\n{message[:800]}")
        if user_input:
            print(f"  [HUMAN] {user_input}")

        # Call LLM
        try:
            update_args, text_parts = call_llm_with_tools(config, system, message)
        except Exception as e:
            _log(f"CYCLE ERROR: {e}")
            print(f"  [KERNEL] Error: {e}")
            time.sleep(pulse)
            continue

        # Show thinking
        for tp in text_parts:
            if tp.strip():
                print(f"  [THINKING] {tp.strip()[:500]}")

        # Apply update
        if update_args:
            agent_response, sleep_override = apply_update(block, update_args)
            if agent_response:
                print(f"\n  [AGENT] {agent_response}\n")
            add_conversation(block, user_input, agent_response or '')
            print(f"  [CONCERN] {block.get('3', '')[:200]}")
        else:
            print(f"  [KERNEL] No update_block call.")
            sleep_override = None

        # Save to shell (never overwrites seed)
        with open(shell_path, 'w') as f:
            json.dump(block, f, indent=1)

        # Determine sleep duration
        if sleep_override and isinstance(sleep_override, (int, float)) and sleep_override > 0:
            actual_sleep = min(int(sleep_override), 3600)  # Cap at 1 hour
            print(f"  [KERNEL] Saved. Agent requested {actual_sleep}s sleep.\n")
        else:
            actual_sleep = pulse
            print(f"  [KERNEL] Saved. Next in {actual_sleep}s.\n")

        _log(f"CONCERN AFTER: {block.get('3', '')[:300]}")
        _log(f"SLEEP: {actual_sleep}s")
        _log(f"=== CYCLE {cycle} END ===\n")

        time.sleep(actual_sleep)

if __name__ == '__main__':
    main()
