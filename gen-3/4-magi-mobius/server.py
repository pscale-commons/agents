#!/usr/bin/env python3
"""
server.py — HTTP interface for the kernel.

Serves a chat UI, accepts human input, polls for responses.
Run alongside kernel.py (or start kernel as subprocess).
"""

import json, os, re, time, threading, subprocess, sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

BASE_DIR = Path(__file__).parent
BLOCKS_DIR = BASE_DIR / "blocks"
FILMSTRIP_DIR = BASE_DIR / "filmstrip"
INPUT_FILE = BASE_DIR / "human_input.trigger"

PORT = int(os.environ.get("PORT", "8080"))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(HTML.encode())

        elif self.path == "/poll":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            # Gather filmstrip frames with full output parsing
            frames = []
            if FILMSTRIP_DIR.exists():
                files = sorted(FILMSTRIP_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)
                for f in files[-30:]:
                    try:
                        frame = json.loads(f.read_text())
                        # Extract human input from message if present
                        human_input = _extract_human_input(frame.get("message", ""))
                        # Parse the output to get note and full response
                        parsed = _parse_frame_output(frame.get("output", ""))

                        frames.append({
                            "ts": frame.get("ts", ""),
                            "concern": frame.get("concern", ""),
                            "tier": frame.get("tier", ""),
                            "tokens": frame.get("tokens", {}),
                            "tools": len(frame.get("tools", [])),
                            "human_input": human_input,
                            "note": parsed.get("note", ""),
                            "status": parsed.get("status", ""),
                            "response": parsed.get("response", ""),
                            "writes": list(parsed.get("writes", {}).keys()),
                        })
                    except Exception:
                        pass

            # Conversation block — extract as ordered exchanges
            conversation = _read_conversation()

            # Block summaries
            conditions = _block_summary("conditions")
            purpose = _block_summary("purpose")

            self.wfile.write(json.dumps({
                "frames": frames,
                "conversation": conversation,
                "conditions": conditions,
                "purpose": purpose,
                "pending": INPUT_FILE.exists(),
            }).encode())

        elif self.path == "/blocks":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            blocks = {}
            if BLOCKS_DIR.exists():
                for f in sorted(BLOCKS_DIR.glob("*.json")):
                    try:
                        blocks[f.stem] = json.loads(f.read_text())
                    except Exception:
                        blocks[f.stem] = {"_": "(read error)"}
            self.wfile.write(json.dumps(blocks, indent=2).encode())

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/send":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode()
            try:
                data = json.loads(body)
                text = data.get("text", "").strip()
            except Exception:
                text = body.strip()

            if text:
                INPUT_FILE.write_text(text)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode())
        else:
            self.send_response(404)
            self.end_headers()


def _read_block(name):
    path = BLOCKS_DIR / f"{name}.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}
    return {}


def _extract_human_input(message_text):
    """Extract human input from compiled message."""
    if not isinstance(message_text, str):
        return ""
    match = re.search(r'=== HUMAN INPUT ===\s*(.+?)(?:\s*$)', message_text, re.DOTALL)
    return match.group(1).strip() if match else ""


def _parse_frame_output(output_text):
    """Parse LLM output to extract note, status, response text, writes."""
    if not isinstance(output_text, str) or not output_text.strip():
        return {"note": "", "status": "", "response": "", "writes": {}}

    # Try to parse as JSON (possibly inside markdown fences)
    cleaned = re.sub(r'^```(?:json)?\s*', '', output_text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r'```\s*$', '', cleaned.strip(), flags=re.MULTILINE)

    # There might be prose before the JSON
    prose = ""
    obj = None

    try:
        obj = json.loads(cleaned)
    except json.JSONDecodeError:
        # Try finding JSON object in text
        match = re.search(r'\{[\s\S]*\}', output_text)
        if match:
            try:
                obj = json.loads(match.group())
                # Everything before the JSON is prose/response
                prose = output_text[:match.start()].strip()
            except json.JSONDecodeError:
                pass

    if obj and isinstance(obj, dict):
        note = obj.get("note", "")
        status = obj.get("status", "")
        writes = obj.get("writes", {})
        # The "response" is either prose before JSON, or the note, or full text
        response = prose if prose else note
        return {"note": note, "status": status, "response": response, "writes": writes}

    return {"note": output_text[:300], "status": "", "response": output_text[:300], "writes": {}}


def _read_conversation():
    """Read conversation block and return ordered list of exchanges."""
    block = _read_block("conversation")
    exchanges = []
    _collect_exchanges(block, exchanges)
    return exchanges


def _collect_exchanges(node, exchanges):
    """Recursively collect exchanges from conversation block."""
    if not isinstance(node, dict):
        return
    for k in sorted(k for k in node if k.isdigit()):
        child = node[k]
        if isinstance(child, dict) and "1" in child:
            # This is an exchange entry
            exchanges.append({
                "human": child.get("1", ""),
                "entity": child.get("2", ""),
            })
        elif isinstance(child, dict):
            # Nested level — recurse
            _collect_exchanges(child, exchanges)


def _block_summary(name):
    """Format a block as readable text."""
    block = _read_block(name)
    return _format_block(block, 0)


def _format_block(node, depth):
    """Recursively format a pscale block."""
    if isinstance(node, str):
        return node
    if not isinstance(node, dict):
        return str(node)

    lines = []
    # Underscore text
    us = node.get("_")
    if isinstance(us, str):
        lines.append(us)
    elif isinstance(us, dict) and isinstance(us.get("_"), str):
        lines.append(us["_"])

    for i in range(1, 10):
        k = str(i)
        if k in node:
            child = node[k]
            indent = "  " * depth
            if isinstance(child, str):
                lines.append(f"{indent}{k}. {child}")
            elif isinstance(child, dict):
                child_text = _format_block(child, depth + 1)
                lines.append(f"{indent}{k}. {child_text}")

    return "\n".join(lines)


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>kernel</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #0a0a0a; color: #c8c8c8;
    display: flex; flex-direction: column; height: 100vh;
  }

  header {
    padding: 10px 20px; background: #111; border-bottom: 1px solid #222;
    display: flex; align-items: center; gap: 16px; flex-shrink: 0;
  }
  header h1 { font-size: 14px; color: #888; font-weight: 500; }
  .status { font-size: 11px; color: #555; }
  .status .live { color: #4a4; }

  .tabs {
    display: flex; border-bottom: 1px solid #222; background: #111;
    padding: 0 20px; flex-shrink: 0;
  }
  .tab {
    padding: 8px 16px; font-size: 12px; color: #666; cursor: pointer;
    border-bottom: 2px solid transparent; font-family: inherit;
    background: none; border-top: none; border-left: none; border-right: none;
  }
  .tab:hover { color: #aaa; }
  .tab.active { color: #ddd; border-bottom-color: #60a5fa; }

  .panels { flex: 1; overflow: hidden; position: relative; }
  .panel { position: absolute; inset: 0; overflow-y: auto; padding: 16px 20px; display: none; }
  .panel.active { display: flex; flex-direction: column; }

  /* Chat panel */
  .chat { gap: 12px; }
  .msg { max-width: 80%; padding: 10px 14px; border-radius: 10px; font-size: 13px; line-height: 1.5; }
  .msg.human { align-self: flex-end; background: #1a3a5c; color: #ddd; border-bottom-right-radius: 2px; }
  .msg.entity { align-self: flex-start; background: #1a1a1a; color: #ccc; border-bottom-left-radius: 2px; border: 1px solid #222; }
  .msg.entity .meta { font-size: 10px; color: #666; margin-bottom: 4px; }
  .msg.entity .meta .tier { font-weight: 600; }
  .msg.entity .meta .tier.opus { color: #c084fc; }
  .msg.entity .meta .tier.sonnet { color: #60a5fa; }
  .msg.entity .meta .tier.haiku { color: #4ade80; }
  .msg.pending { align-self: flex-end; background: #2a2a1a; color: #aa8; border-bottom-right-radius: 2px; font-style: italic; }
  .msg .writes { font-size: 10px; color: #555; margin-top: 6px; }

  /* Activity panel */
  .activity { gap: 6px; }
  .frame {
    padding: 8px 12px; border-radius: 6px;
    border-left: 3px solid #333; background: #111;
    font-size: 11px; line-height: 1.4;
  }
  .frame .fmeta { color: #555; font-size: 10px; display: flex; gap: 10px; margin-bottom: 3px; }
  .frame .fmeta .tier { font-weight: 600; }
  .frame .fmeta .tier.opus { color: #c084fc; }
  .frame .fmeta .tier.sonnet { color: #60a5fa; }
  .frame .fmeta .tier.haiku { color: #4ade80; }
  .frame .fnote { color: #999; }
  .frame.engagement { border-left-color: #60a5fa; }
  .frame.birth { border-left-color: #c084fc; }
  .frame.orientation { border-left-color: #c084fc; }
  .frame.action { border-left-color: #4ade80; }

  /* State panel */
  .state { gap: 16px; font-size: 12px; }
  .state h3 { color: #666; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }
  .state pre {
    color: #999; white-space: pre-wrap; word-break: break-word; line-height: 1.4;
    background: #111; padding: 10px; border-radius: 6px; font-size: 11px;
    font-family: 'SF Mono', Menlo, monospace; max-height: 300px; overflow-y: auto;
  }

  /* Input bar */
  .input-bar {
    padding: 12px 20px; background: #111; border-top: 1px solid #222;
    display: flex; gap: 10px; flex-shrink: 0;
  }
  .input-bar input {
    flex: 1; background: #1a1a1a; border: 1px solid #333;
    border-radius: 8px; padding: 10px 14px;
    color: #ddd; font-family: inherit; font-size: 13px; outline: none;
  }
  .input-bar input:focus { border-color: #555; }
  .input-bar input.pending { border-color: #f59e0b; }
  .input-bar button {
    background: #1a3a5c; border: none; border-radius: 8px; padding: 10px 20px;
    color: #8bb8e8; font-family: inherit; font-size: 12px; cursor: pointer;
  }
  .input-bar button:hover { background: #254a6c; color: #aad; }
</style>
</head>
<body>

<header>
  <h1>kernel</h1>
  <span class="status"><span class="live" id="status">polling...</span></span>
</header>

<div class="tabs">
  <button class="tab active" onclick="switchTab('chat')">Chat</button>
  <button class="tab" onclick="switchTab('activity')">Activity</button>
  <button class="tab" onclick="switchTab('state')">Blocks</button>
</div>

<div class="panels">
  <div class="panel chat active" id="panel-chat"></div>
  <div class="panel activity" id="panel-activity"></div>
  <div class="panel state" id="panel-state">
    <div><h3>conditions</h3><pre id="sb-conditions">loading...</pre></div>
    <div><h3>purpose</h3><pre id="sb-purpose">loading...</pre></div>
  </div>
</div>

<div class="input-bar">
  <input type="text" id="input" placeholder="Type a message..." autocomplete="off">
  <button onclick="send()">send</button>
</div>

<script>
let lastConvHash = '';
let lastFrameHash = '';
let pendingMessage = null;
let pendingCleared = false;

function switchTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelector('.tab[onclick*="' + name + '"]').classList.add('active');
  document.getElementById('panel-' + name).classList.add('active');
}

function send() {
  const input = document.getElementById('input');
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  input.classList.add('pending');
  pendingMessage = text;
  pendingCleared = false;
  appendPending();
  fetch('/send', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({text})
  });
}

function appendPending() {
  // Add pending bubble without rebuilding everything
  const panel = document.getElementById('panel-chat');
  let el = document.getElementById('pending-msg');
  if (!el && pendingMessage) {
    el = document.createElement('div');
    el.id = 'pending-msg';
    el.className = 'msg pending';
    panel.appendChild(el);
  }
  if (el && pendingMessage) {
    el.innerHTML = escHtml(pendingMessage) + ' <span style="opacity:0.5">(thinking...)</span>';
    panel.scrollTop = panel.scrollHeight;
  }
}

document.getElementById('input').addEventListener('keydown', e => {
  if (e.key === 'Enter') send();
});

function escHtml(s) {
  return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');
}

function concernClass(name) {
  name = (name || '').toLowerCase();
  if (name.includes('birth')) return 'birth';
  if (name.includes('orientation')) return 'orientation';
  if (name.includes('engagement')) return 'engagement';
  if (name.includes('action')) return 'action';
  return '';
}

function isNearBottom(el) {
  return el.scrollHeight - el.scrollTop - el.clientHeight < 80;
}

function renderChat(data) {
  if (!data) return;
  const panel = document.getElementById('panel-chat');

  // Build new content hash to avoid unnecessary re-renders
  const convHash = JSON.stringify(data.conversation || []);
  if (convHash === lastConvHash && !pendingCleared) return;
  lastConvHash = convHash;

  const wasAtBottom = isNearBottom(panel);

  let html = '';

  // Conversation exchanges from block
  if (data.conversation) {
    for (const ex of data.conversation) {
      if (ex.human) {
        html += '<div class="msg human">' + escHtml(ex.human) + '</div>';
      }
      if (ex.entity) {
        html += '<div class="msg entity">' + escHtml(ex.entity) + '</div>';
      }
    }
  }

  // Check if pending message now appears in conversation
  if (pendingMessage && data.conversation) {
    for (const ex of data.conversation) {
      if (ex.human === pendingMessage && ex.entity) {
        pendingMessage = null;
        pendingCleared = true;
        document.getElementById('input').classList.remove('pending');
        break;
      }
    }
  }

  // Show pending if still waiting
  if (pendingMessage) {
    html += '<div class="msg pending" id="pending-msg">' + escHtml(pendingMessage) + ' <span style="opacity:0.5">(thinking...)</span></div>';
  }

  panel.innerHTML = html;

  // Only auto-scroll if user was already at the bottom
  if (wasAtBottom) {
    panel.scrollTop = panel.scrollHeight;
  }
}

function renderActivity(data) {
  if (!data || !data.frames) return;
  const panel = document.getElementById('panel-activity');
  const wasAtBottom = isNearBottom(panel);

  let html = '';
  for (const f of data.frames) {
    let cls = concernClass(f.concern);
    html += '<div class="frame ' + cls + '">';
    html += '<div class="fmeta">';
    html += '<span class="tier ' + f.tier + '">' + f.tier + '</span>';
    html += '<span>' + (f.concern || '').substring(0, 35) + '</span>';
    html += '<span>' + (f.ts || '').substring(11, 19) + '</span>';
    html += '<span>' + (f.tokens.input||0) + '/' + (f.tokens.output||0) + 'tok</span>';
    if (f.tools) html += '<span>' + f.tools + ' tools</span>';
    if (f.status) html += '<span>(' + f.status + ')</span>';
    html += '</div>';
    if (f.human_input) html += '<div style="color:#f59e0b;margin-bottom:3px">human: ' + escHtml(f.human_input).substring(0,100) + '</div>';
    html += '<div class="fnote">' + escHtml((f.note || '').substring(0, 200)) + '</div>';
    if (f.writes && f.writes.length) html += '<div style="color:#555;font-size:10px;margin-top:2px">writes: ' + f.writes.join(', ') + '</div>';
    html += '</div>';
  }
  panel.innerHTML = html;
  if (wasAtBottom) {
    panel.scrollTop = panel.scrollHeight;
  }
}

async function poll() {
  try {
    const res = await fetch('/poll');
    const data = await res.json();

    document.getElementById('status').textContent = data.pending ? 'thinking...' : 'live';

    // Always try to update chat — renderChat checks hash internally
    renderChat(data);

    // Update activity only when frames change
    let frameHash = JSON.stringify(data.frames.map(f => f.ts));
    if (frameHash !== lastFrameHash) {
      lastFrameHash = frameHash;
      renderActivity(data);
    }

    // State tab
    document.getElementById('sb-conditions').textContent = data.conditions || '(empty)';
    document.getElementById('sb-purpose').textContent = data.purpose || '(empty)';

  } catch (e) {
    document.getElementById('status').textContent = 'disconnected';
  }
}

setInterval(poll, 3000);
poll();
document.getElementById('input').focus();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    kernel_proc = None
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if api_key:
        env = os.environ.copy()
        kernel_proc = subprocess.Popen(
            [sys.executable, str(BASE_DIR / "kernel.py")],
            env=env,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        print(f"[server] kernel started (pid {kernel_proc.pid})")

    print(f"[server] http://localhost:{PORT}")

    try:
        server = HTTPServer(("", PORT), Handler)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[server] shutting down")
        if kernel_proc:
            kernel_proc.terminate()
            kernel_proc.wait()
