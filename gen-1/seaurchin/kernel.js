// SEAURCHIN KERNEL — The electricity.
//
// Blocks do the algorithms. Native code does I/O and async timing.
// The hands: tree mutation, tool dispatch.
// The twist: async LLM loop.
// Everything else unfolds from blocks.

import { nav, read, unfold } from './core.js';
import { readFileSync } from 'fs';

const touchstone = JSON.parse(readFileSync(new URL('./touchstone.json', import.meta.url), 'utf8'));
const BSP_PARSE      = nav(touchstone, '1.1');
const BSP_SPINDLE    = nav(touchstone, '1.2');
const BSP_RING       = nav(touchstone, '1.3');
const BSP_DIR        = nav(touchstone, '1.4');
const TWIST_CHECK    = nav(touchstone, '2.1');
const TWIST_EXTRACT  = nav(touchstone, '2.2');
const TWIST_MESSAGES = nav(touchstone, '2.3');
const CONCERN_FIND   = nav(touchstone, '3.1');
const COMPILE_CHAIN  = nav(touchstone, '3.2');
const COMPILE_SECTION = nav(touchstone, '3.3');

const TOOLS = [
  { name: 'read', description: 'Read a node. Returns content + children.', input_schema: { type: 'object', properties: { address: { type: 'string', description: 'Dot path, e.g. "3" or "5.1"' } }, required: ['address'] } },
  { name: 'write', description: 'Write content to an address.', input_schema: { type: 'object', properties: { address: { type: 'string' }, content: { type: 'string' } }, required: ['address', 'content'] } },
  { name: 'bsp', description: 'Semantic navigation. bsp(root) = subtree. bsp(root, address) = spindle. bsp(root, address, "ring") = siblings. bsp(root, address, "dir") = subtree from endpoint.', input_schema: { type: 'object', properties: { root: { type: 'string' }, address: { type: 'string' }, point: { type: 'string' } }, required: ['root'] } },
  { name: 'append', description: 'Add content at next free digit under an address.', input_schema: { type: 'object', properties: { address: { type: 'string' }, content: { type: 'string' } }, required: ['address', 'content'] } },
];

export function createKernel({ storage, llm, log }) {
  const L = log || { info() {}, error: console.error };
  let shell = null;
  const load = () => (shell = storage.load());
  const save = () => storage.save(shell);

  // ---- Hands: tree mutation ----

  function writeNode(path, content) {
    const keys = String(path).split('.'), last = keys.pop();
    let node = shell.tree;
    for (const k of keys) {
      if (typeof node[k] === 'string') node[k] = { _: node[k] };
      if (!node[k]) node[k] = {};
      node = node[k];
    }
    if (node[last] && typeof node[last] === 'object') node[last]._ = content;
    else node[last] = content;
  }

  function readNode(path) {
    const node = nav(shell.tree, path);
    if (node == null) return { error: 'not found' };
    if (typeof node === 'string') return { content: node };
    const r = { content: node._ || null, children: {} };
    for (const [k, v] of Object.entries(node)) {
      if (k !== '_') r.children[k] = typeof v === 'string' ? v : (v?._ || '(branch)');
    }
    return r;
  }

  function findFree(path) {
    const node = nav(shell.tree, path);
    if (!node || typeof node === 'string') return '1';
    for (let d = 1; d <= 9; d++) if (node[String(d)] === undefined) return String(d);
    return null;
  }

  // ---- Hands: BSP for tool ----

  function runBsp(root, address, point) {
    const sub = nav(shell.tree, root);
    if (!sub || typeof sub === 'string') return { error: 'not found' };
    if (!address && !point) return { mode: 'dir', tree: sub };
    const p = unfold(BSP_PARSE, { address: address || '0' });
    const walkDigits = p['5'], whole = p['6'];
    const rootText = read(sub);
    const sp = unfold(BSP_SPINDLE, { walkDigits, whole, tree: sub, node: sub });
    const walked = [];
    if (rootText) walked.push([whole, rootText]);
    for (const x of (sp['2'] || [])) if (Array.isArray(x) && x.length === 2) walked.push(x);
    if (point === 'ring') {
      const r = unfold(BSP_RING, { walkDigits, tree: sub });
      return { mode: 'ring', siblings: (r['8'] || []).filter(x => Array.isArray(x) && x.length === 3).map(s => ({ digit: s[0], text: s[1], branch: s[2] })) };
    }
    if (point === 'dir') return { mode: 'dir', subtree: unfold(BSP_DIR, { walkDigits, tree: sub })['2'] };
    return { mode: 'spindle', nodes: walked.map(([ps, t]) => ({ pscale: ps, text: t })) };
  }

  // ---- Hands: tool dispatch ----

  async function executeTool(name, input) {
    L.info(`[kernel] tool: ${name} ${JSON.stringify(input)}`);
    if (name === 'read') return JSON.stringify(readNode(input.address));
    if (name === 'write') { writeNode(input.address, input.content); save(); return JSON.stringify({ ok: true }); }
    if (name === 'bsp') return JSON.stringify(runBsp(input.root, input.address, input.point));
    if (name === 'append') {
      const free = findFree(input.address);
      if (!free) return JSON.stringify({ error: 'full' });
      writeNode(input.address + '.' + free, input.content); save();
      return JSON.stringify({ ok: true, address: input.address + '.' + free });
    }
    return JSON.stringify({ error: 'unknown tool' });
  }

  // ---- Compile: blocks extract, hands format ----

  function compile(concernPath) {
    const concerns = nav(shell.tree, '2');
    const rootText = read(concerns);
    const chain = unfold(COMPILE_CHAIN, { node: concerns, path: concernPath })['2'] || [];
    const parts = ['[concern]\n' + [rootText, ...chain].filter(Boolean).map(t => '  ' + t).join('\n')];
    for (const [label, addr] of [['purpose', '5'], ['stash', '4'], ['history', '3']]) {
      const node = nav(shell.tree, addr);
      if (!node) continue;
      const sec = unfold(COMPILE_SECTION, { node });
      const children = (sec['4'] || []).filter(x => x.length);
      if (sec['1'] || children.length) {
        const lines = [`[${label}]`];
        if (sec['1']) lines.push('  ' + sec['1']);
        for (const [d, t] of children) lines.push(`  ${d}: ${t}`);
        parts.push(lines.join('\n'));
      }
    }
    parts.push('Tools: read, write, bsp, append. Navigate and modify your shell.');
    return parts.join('\n\n');
  }

  // ---- The twist ----

  async function activate(stimulus, message) {
    if (!shell) load();
    // Concern — block walks the tree
    const paths = unfold(CONCERN_FIND, { node: nav(shell.tree, '2'), stimulus, path: '', findConcern: CONCERN_FIND });
    if (!Array.isArray(paths) || !paths.length) return { error: 'no matching concern for: ' + stimulus };
    const concernPath = paths[0];
    // Mask
    let m = shell.mask || (shell.mask = {});
    for (const k of concernPath.split('.')) { if (!m[k]) m[k] = {}; m = m[k]; }
    m.last = Math.floor(Date.now() / 1000);
    // Invocation
    const inv = nav(shell.tree, '1.1.1');
    const maxTokens = typeof inv === 'string' ? parseInt(inv.split(' ')[1]) || 2048 : 2048;
    // Twist
    let system = compile(concernPath);
    let messages = [{ role: 'user', content: message }];
    let echo = 0;
    while (true) {
      const response = await llm.call({ system, messages, max_tokens: maxTokens, tools: TOOLS });
      if (!unfold(TWIST_CHECK, { response })['4']) {
        // History
        const texts = (response.content || []).filter(b => b.type === 'text');
        if (texts.length) {
          const free = findFree('3');
          if (free) writeNode('3.' + free, `[${new Date().toISOString()}] ${texts.map(b => b.text).join(' ').slice(0, 300)}`);
        }
        save();
        return { text: texts.map(b => b.text).join('\n'), echo };
      }
      // Tool loop — blocks extract and build, hands execute
      const tools = unfold(TWIST_EXTRACT, { content: response.content })['1'];
      const results = [];
      for (const t of tools) results.push(await executeTool(t.name, t.input));
      messages = unfold(TWIST_MESSAGES, { tools, results, content: response.content, messages })['4'];
      system = compile(concernPath); // Möbius twist — recompile after mutation
      echo++;
    }
  }

  return { load, save, activate, shell: () => shell, compile };
}
