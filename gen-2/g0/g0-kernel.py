#!/usr/bin/env python3
"""
G0 Hermitcrab Kernel — Tool-use architecture.

A-loop: environment tools execute within the instance, results return immediately.
B-loop: update_block persists changes. The Möbius point.

The kernel is mechanical. All decisions belong to the LLM.
"""

import json, os, sys, re, time, subprocess, urllib.request, ssl, threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

SEED = "g0-seed.json"
SHELL = "g0-shell.json"
LOGFILE = "g0-test.log"

# ---------------------------------------------------------------------------
# Test logging — append-only log file for observer review
# ---------------------------------------------------------------------------

def _log(msg):
    """Append timestamped line to log file."""
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
# BSP
# ---------------------------------------------------------------------------

def bsp(node, digits):
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
# Block mutation — update_block implementation
# ---------------------------------------------------------------------------

def set_at_path(block, path, value):
    """Set a value at a dot-separated path in the block.
    '3' → block['3'] = value
    '3.1' → block['3']['1'] = value
    '4._' → block['4']['_'] = value
    """
    keys = path.split('.')
    node = block
    for k in keys[:-1]:
        key = '_' if k == '0' or k == '_' else k
        if key not in node or not isinstance(node[key], dict):
            node[key] = {}
        node = node[key]
    final = '_' if keys[-1] == '0' or keys[-1] == '_' else keys[-1]
    # If value looks like JSON, parse it
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, (dict, list)):
                value = parsed
        except (json.JSONDecodeError, ValueError):
            pass
    node[final] = value

# ---------------------------------------------------------------------------
# Environment tools — A-loop, immediate execution
# ---------------------------------------------------------------------------

def tool_web_fetch(url):
    ctx = ssl.create_default_context()
    data = urllib.request.urlopen(url, context=ctx).read()
    return data.decode('utf-8', errors='replace')[:8000]

def tool_file_read(path):
    return open(path).read()[:8000]

def tool_file_write(path, content):
    with open(path, 'w') as f:
        f.write(content)
    return f"Written to {path}"

def tool_shell_exec(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return (r.stdout + r.stderr)[:4000]

# ---------------------------------------------------------------------------
# Tool definitions for the API
# ---------------------------------------------------------------------------

TOOL_DEFS = [
    {
        "name": "web_fetch",
        "description": "Fetch a URL. Returns first 8000 chars of page content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "file_read",
        "description": "Read a file. Returns first 8000 chars.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "file_write",
        "description": "Write content to a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to write"},
                "content": {"type": "string", "description": "Content to write"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "shell_exec",
        "description": "Run a shell command. Returns stdout+stderr (max 4000 chars, 30s timeout).",
        "input_schema": {
            "type": "object",
            "properties": {
                "cmd": {"type": "string", "description": "Command to run"}
            },
            "required": ["cmd"]
        }
    },
    {
        "name": "update_block",
        "description": "Persist a change to the pscale block. This is the Möbius point — each call composes the next instance's context window. Section is a dot-separated path (e.g. '3' for concern, '4.1' for purpose entry 1). Content is a string or JSON object.",
        "input_schema": {
            "type": "object",
            "properties": {
                "section": {"type": "string", "description": "Dot-separated block path, e.g. '3', '4.1', '6.2'"},
                "content": {"type": "string", "description": "New content — string or JSON object as string"}
            },
            "required": ["section", "content"]
        }
    },
    {
        "name": "respond",
        "description": "Speak to your human. The message will be displayed to them.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Message to display to the human"}
            },
            "required": ["message"]
        }
    }
]

def next_conv_key(block):
    """Find next available digit key in §6."""
    conv = block.get('6', {})
    for i in range(1, 10):
        if str(i) not in conv:
            return str(i)
    return '9'  # overwrite last if full (compaction should prevent this)

def log_conversation(block, human_msg, agent_msg):
    """Kernel-managed conversation logging."""
    if '6' not in block:
        block['6'] = {"_": "Conversation. Each entry: 1=human said, 2=I said."}
    key = next_conv_key(block)
    entry = {"1": human_msg or "", "2": agent_msg or ""}
    block['6'][key] = entry

def execute_tool(name, args, block):
    """Execute a tool call. Returns (result_string, should_display).
    Environment tools return results to the LLM.
    update_block mutates the block in place.
    respond returns the message for display and auto-logs to §6.
    """
    try:
        if name == "web_fetch":
            return tool_web_fetch(args["url"]), False
        elif name == "file_read":
            return tool_file_read(args["path"]), False
        elif name == "file_write":
            return tool_file_write(args["path"], args["content"]), False
        elif name == "shell_exec":
            return tool_shell_exec(args["cmd"]), False
        elif name == "update_block":
            set_at_path(block, args["section"], args["content"])
            return f"Updated block at {args['section']}", False
        elif name == "respond":
            return args["message"], True
        else:
            return f"Unknown tool: {name}", False
    except Exception as e:
        return f"Error: {str(e)[:500]}", False

# ---------------------------------------------------------------------------
# Context window compilation — the bridge
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
    """Concern + environment + conversation context → message."""
    parts = []

    # Concern current
    parts.append(f"CONCERN:\n{unfold(block.get('3', {}))}")

    # Environment: human input (disturbance)
    if user_input:
        parts.append(f"HUMAN INPUT:\n{user_input}")

    # Recent conversation (last 3 entries for context)
    conv = block.get('6', {})
    conv_keys = sorted((k for k in conv if k != '_' and k.isdigit()), key=int)
    recent = conv_keys[-3:] if len(conv_keys) > 3 else conv_keys
    if recent:
        conv_lines = []
        for k in recent:
            entry = conv[k]
            if isinstance(entry, dict):
                h = entry.get('1', '')
                a = entry.get('2', '')
                if h: conv_lines.append(f"  Human: {h}")
                if a: conv_lines.append(f"  Agent: {a}")
        if conv_lines:
            parts.append("RECENT CONVERSATION:\n" + '\n'.join(conv_lines))

    return '\n\n'.join(parts)

# ---------------------------------------------------------------------------
# LLM API — tool-use loop
# ---------------------------------------------------------------------------

def call_api(cfg, system, messages, tools):
    """Single API call. Returns response object."""
    api = cfg.get('_', 'anthropic')
    url = cfg.get('1', 'https://api.anthropic.com')
    key = cfg.get('2', '')
    model = cfg.get('3', 'claude-sonnet-4-20250514')

    if not key:
        raise ValueError("No API key. Set section 5.2.")

    body = {
        'model': model,
        'max_tokens': 4096,
        'system': system,
        'messages': messages,
        'tools': tools
    }
    headers = {
        'x-api-key': key,
        'content-type': 'application/json',
        'anthropic-version': '2023-06-01'
    }
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(f'{url}/v1/messages', data=data, headers=headers)
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx) as resp:
        return json.loads(resp.read().decode('utf-8'))


def a_loop(cfg, system, initial_message, block):
    """The A-loop: call LLM, execute tools, return results, repeat until done.
    Returns (responses_to_human, total_usage).
    """
    messages = [{"role": "user", "content": initial_message}]
    responses = []
    total_input = 0
    total_output = 0
    max_turns = 20  # safety limit

    for turn in range(max_turns):
        result = call_api(cfg, system, messages, TOOL_DEFS)
        usage = result.get('usage', {})
        total_input += usage.get('input_tokens', 0)
        total_output += usage.get('output_tokens', 0)

        stop_reason = result.get('stop_reason', 'end_turn')
        content = result.get('content', [])

        # Collect any text blocks
        for block_item in content:
            if block_item.get('type') == 'text' and block_item.get('text', '').strip():
                _log(f"  LLM_TEXT: {block_item['text'][:500]}")

        _log(f"  A-loop turn {turn}: stop_reason={stop_reason}, content_blocks={len(content)}")

        # If no tool use, we're done
        if stop_reason != 'tool_use':
            break

        # Execute tool calls
        tool_results = []
        for block_item in content:
            if block_item.get('type') != 'tool_use':
                continue

            tool_name = block_item['name']
            tool_input = block_item['input']
            tool_id = block_item['id']

            tool_summary = f"{tool_name}({', '.join(f'{k}={repr(v)[:60]}' for k,v in tool_input.items())})"
            print(f"    [{tool_summary}]")
            _log(f"  TOOL: {tool_summary}")

            result_text, is_response = execute_tool(tool_name, tool_input, block)
            _log(f"  RESULT: {result_text[:300]}")

            if is_response:
                responses.append(result_text)

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": result_text[:4000]
            })

        # Add assistant turn + tool results for next iteration
        messages.append({"role": "assistant", "content": content})
        messages.append({"role": "user", "content": tool_results})

    return responses, {"input_tokens": total_input, "output_tokens": total_output}

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def cycle(block, user_input=None):
    """One B-loop cycle. Runs the full A-loop within it."""
    cfg = block.get('5', {})

    # Compile context window
    system = compile_system(block)
    message = compile_message(block, user_input)

    _log(f"=== CYCLE START === input: {repr(user_input)[:200]}")
    _log(f"SYSTEM PROMPT ({len(system)} chars):\n{system[:1000]}")
    _log(f"MESSAGE ({len(message)} chars):\n{message[:1500]}")

    print(f"  [system: {len(system)} chars | message: {len(message)} chars]")
    print(f"  [calling {cfg.get('3', '?')}...]")

    # Run A-loop
    responses, usage = a_loop(cfg, system, message, block)

    print(f"  [tokens: in={usage['input_tokens']} out={usage['output_tokens']}]")
    _log(f"TOKENS: in={usage['input_tokens']} out={usage['output_tokens']}")

    # Auto-log conversation (kernel-managed)
    if user_input or responses:
        agent_msg = responses[-1] if responses else ""
        log_conversation(block, user_input, agent_msg)

    # Log concern state after cycle
    concern = block.get('3', {})
    _log(f"CONCERN AFTER: {json.dumps(concern)[:500]}")
    _log(f"RESPONSES: {responses}")
    _log(f"=== CYCLE END ===\n")

    # Save (update_block calls already mutated the block)
    save(block)

    return responses


# ---------------------------------------------------------------------------
# Web interface — HTTP bridge for browser access
# ---------------------------------------------------------------------------

_web_queue = []       # [(req_id, message), ...]
_web_lock = threading.Lock()
_web_responses = {}   # req_id → [response_strings]
_web_resp_lock = threading.Lock()
_web_request_id = 0

CHAT_HTML = '''<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Hermitcrab G0</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0a0a;color:#e0e0e0;font-family:monospace;height:100vh;display:flex;flex-direction:column}
#log{flex:1;overflow-y:auto;padding:1rem;white-space:pre-wrap;line-height:1.6}
.human{color:#88aaff}.agent{color:#88ffaa}.system{color:#666}
#input-row{display:flex;padding:0.5rem;border-top:1px solid #333}
#msg{flex:1;background:#111;color:#e0e0e0;border:1px solid #333;padding:0.5rem;font-family:monospace;font-size:1rem}
#send{background:#333;color:#88ffaa;border:none;padding:0.5rem 1rem;cursor:pointer;font-family:monospace}
</style></head><body>
<div id="log"><span class="system">Hermitcrab G0</span>\\n</div>
<div id="input-row"><input id="msg" placeholder="Type here..." autofocus>
<button id="send">Send</button></div>
<script>
const log=document.getElementById('log'),msg=document.getElementById('msg');
function append(cls,text){log.innerHTML+=`<span class="${cls}">${cls==='human'?'> ':''}${text.replace(/</g,'&lt;')}</span>\\n`;log.scrollTop=log.scrollHeight}
async function send(){
  const m=msg.value.trim();if(!m)return;msg.value='';append('human',m);
  append('system','thinking...');
  try{
    const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:m})});
    const d=await r.json();
    log.innerHTML=log.innerHTML.replace(/<span class="system">thinking\\.\\.\\.<\\/span>\\\\n/,'');
    if(d.responses)d.responses.forEach(t=>append('agent',t));
    else append('system','[no response]');
  }catch(e){append('system','[error: '+e.message+']')}
}
msg.addEventListener('keydown',e=>{if(e.key==='Enter')send()});
document.getElementById('send').addEventListener('click',send);
</script></body></html>'''


class WebHandler(SimpleHTTPRequestHandler):
    """Serves chat UI at / and accepts POST /chat for web input."""

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(CHAT_HTML.encode('utf-8'))
        elif self.path == '/status':
            block, _ = load()
            concern = block.get('3', {})
            c_text = concern.get('1', concern.get('_', '')) if isinstance(concern, dict) else str(concern)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"concern": c_text[:300]}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/chat':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            try:
                data = json.loads(body)
                message = data.get('message', '').strip()
            except (json.JSONDecodeError, ValueError):
                message = body.strip()

            if not message:
                self.send_response(400)
                self.end_headers()
                return

            global _web_request_id
            with _web_lock:
                _web_request_id += 1
                req_id = _web_request_id
                _web_queue.append((req_id, message))

            # Wait for kernel to process (up to 120s)
            deadline = time.time() + 120
            while time.time() < deadline:
                with _web_resp_lock:
                    if req_id in _web_responses:
                        responses = _web_responses.pop(req_id)
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({"responses": responses}).encode())
                        return
                time.sleep(0.2)

            self.send_response(504)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        pass  # suppress HTTP request logs


def start_web_server(port=5000):
    server = HTTPServer(('0.0.0.0', port), WebHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


# ---------------------------------------------------------------------------
# Main loop — terminal + web, simultaneous
# ---------------------------------------------------------------------------

def main():
    print("G0 Hermitcrab Kernel (tool-use)")
    print("=" * 40)

    block, source = load()
    print(f"Loaded from: {source}")

    # Check API key
    if not block.get('5', {}).get('2'):
        key = input("API key (section 5.2 is empty): ").strip()
        if key:
            if '5' not in block:
                block['5'] = {}
            block['5']['2'] = key
            save(block)
            print("Key saved to shell.")
            block, _ = load()

    # Start web server
    port = 5000
    try:
        start_web_server(port)
        print(f"Web UI: http://localhost:{port}")
    except OSError as e:
        print(f"Web server failed ({e}), terminal only.")

    cycle_num = 0

    while True:
        if block.get('5', {}).get('5') != 'on':
            print("Switch is off (5.5). Stopping.")
            break

        # Check for web input
        user_input = None
        web_req_id = None
        with _web_lock:
            if _web_queue:
                web_req_id, user_input = _web_queue.pop(0)

        # If no web input, check terminal (non-blocking where possible)
        if user_input is None:
            try:
                import select
                if select.select([sys.stdin], [], [], 0.5)[0]:
                    user_input = sys.stdin.readline().strip()
                    if user_input.lower() in ('quit', 'exit', 'q'):
                        print("Stopping.")
                        break
                    if not user_input:
                        user_input = None
            except (ImportError, OSError):
                # select unavailable (Windows) — brief sleep then check web again
                time.sleep(0.5)
                continue

        if user_input is None and web_req_id is None:
            continue  # poll again

        cycle_num += 1
        print(f"\n--- Cycle {cycle_num} ---")

        try:
            responses = cycle(block, user_input)

            if responses:
                for r in responses:
                    print(f"Agent: {r}")
            else:
                print("  [no response to human this cycle]")

            # Deliver web response
            if web_req_id is not None:
                with _web_resp_lock:
                    _web_responses[web_req_id] = responses or ["[no response]"]

            # Show concern
            concern = block.get('3', {})
            c_underscore = concern.get('_', '') if isinstance(concern, dict) else str(concern)
            c_1 = concern.get('1', '') if isinstance(concern, dict) else ''
            print(f"  [concern._: {c_underscore[:100]}]")
            if c_1:
                print(f"  [concern.1: {str(c_1)[:120]}]")

        except Exception as e:
            print(f"  [cycle error: {e}]")
            if web_req_id is not None:
                with _web_resp_lock:
                    _web_responses[web_req_id] = [f"Error: {str(e)[:200]}"]

        # Reload
        block, _ = load()


if __name__ == '__main__':
    main()
