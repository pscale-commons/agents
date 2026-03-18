#!/usr/bin/env node
// Seaurchin boot — headless.
// Assembles: shell (from file) + echo LLM → kernel.
// Usage:
//   node boot.js                    # default "Hello"
//   node boot.js "What can you do?" # custom message
//   node boot.js --stimulus heartbeat  # different concern

import { createKernel } from './kernel.js';
import { readFileSync, writeFileSync } from 'fs';

// ---- Adapters (inline, minimal) ----

const shellPath = 'shell.json';

const storage = {
  load: () => JSON.parse(readFileSync(shellPath, 'utf8')),
  save: (d) => writeFileSync(shellPath, JSON.stringify(d, null, 2)),
};

const echoLLM = {
  call: async (params) => ({
    content: [{ type: 'text', text: `[echo] System prompt: ${params.system.length} chars. Message: ${(params.messages[0]?.content || '').slice(0, 100)}` }],
    stop_reason: 'end_turn',
  }),
};

// ---- Parse args ----

const args = process.argv.slice(2);
let stimulus = 'user';
let message = 'Hello';

for (let i = 0; i < args.length; i++) {
  if (args[i] === '--stimulus' && args[i + 1]) { stimulus = args[++i]; }
  else { message = args[i]; }
}

// ---- Boot ----

const kernel = createKernel({ storage, llm: echoLLM, log: console });
kernel.load();

console.log(`[boot] Activating: stimulus="${stimulus}", message="${message}"`);

kernel.activate(stimulus, message).then(result => {
  if (result.error) console.log('[boot] Error:', result.error);
  else {
    console.log('[boot] Response:', result.text);
    console.log('[boot] Echoes:', result.echo);
  }
}).catch(e => console.error('[boot] Failed:', e));
