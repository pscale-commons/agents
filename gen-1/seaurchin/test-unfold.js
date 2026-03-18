#!/usr/bin/env node
// Test: the key in JavaScript.
// Mode 4 blocks executed by unfold — same blocks work in any kitchen.

import { nav, read, unfold, RT } from './core.js';
import { readFileSync } from 'fs';

// ============ TOUCHSTONE ============
// Blocks loaded from JSON — single source of truth.

const touchstone = JSON.parse(readFileSync(new URL('./touchstone.json', import.meta.url), 'utf8'));
const BSP_PARSE     = nav(touchstone, '1.1');
const BSP_SPINDLE   = nav(touchstone, '1.2');
const BSP_RING      = nav(touchstone, '1.3');
const BSP_DIR       = nav(touchstone, '1.4');
const BSP_POINT     = nav(touchstone, '1.5');
const BSP_DISC_WALK = nav(touchstone, '1.6');
const TWIST_CHECK   = nav(touchstone, '2.1');
const TWIST_EXTRACT = nav(touchstone, '2.2');
const TWIST_MESSAGES = nav(touchstone, '2.3');

// ============ TEST TREE ============
// A small pscale tree for self-contained testing.

const tree = {
  _: 'root',
  1: {
    _: 'life',
    2: {
      _: 'animals',
      1: { _: 'mammals' },
      3: { _: 'birds' },
    },
    4: { _: 'plants' },
  },
  5: {
    _: 'matter',
    1: { _: 'solid' },
    2: { _: 'liquid' },
    3: { _: 'gas' },
  },
};

// ============ HELPERS ============

let pass = 0, fail = 0;
function check(label, match) {
  if (match) { console.log(`  ✓ ${label}`); pass++; }
  else { console.log(`  ✗ ${label}`); fail++; }
}

function parse(addr) {
  const r = unfold(BSP_PARSE, { address: String(addr) });
  return { walkDigits: r['5'], whole: r['6'] };
}

function spindle(addr) {
  const { walkDigits, whole } = parse(addr);
  const r = unfold(BSP_SPINDLE, { walkDigits, whole, tree, node: tree });
  const walked = r['2'] || [];
  const nodes = [];
  const rt = read(tree);
  if (rt) nodes.push([whole, rt]);
  for (const x of walked) if (Array.isArray(x) && x.length === 2) nodes.push(x);
  return nodes;
}

// ============ TEST: NAV + READ ============

console.log('=== NAV + READ ===');
check('nav root', nav(tree, '') === tree);
check('nav null path', nav(tree, null) === tree);
check('nav depth 1', read(nav(tree, '1')) === 'life');
check('nav depth 2', read(nav(tree, '1.2')) === 'animals');
check('nav depth 3', read(nav(tree, '1.2.1')) === 'mammals');
check('nav miss', nav(tree, '9') === undefined);
check('read string', read('hello') === 'hello');
check('read obj', read({ _: 'test' }) === 'test');
check('read null', read(null) === null);

// ============ TEST: RT ============

console.log('\n=== RT ===');
check('split', RT.split('a.b.c', '.').join(',') === 'a,b,c');
check('chars', RT.chars('abc').join(',') === 'a,b,c');
check('join', RT.join(['a','b'], '.') === 'a.b');
check('cat', RT.cat('a', 'b', 'c') === 'abc');
check('arr', RT.arr(1,2,3).length === 3);
check('obj', RT.obj('a', 1, 'b', 2).b === 2);
check('push', RT.push([1,2], 3, 4).length === 4);
check('get', RT.get([10,20,30], 1) === 20);
check('len', RT.len([1,2]) === 2);
check('last', RT.last([1,2,3]) === 3);
check('init', RT.init([1,2,3]).length === 2);
check('range', RT.range(3).join(',') === '0,1,2');
check('int', RT.int('42') === 42);
check('add', RT.add(2, 3) === 5);
check('sub', RT.sub(5, 3) === 2);
check('eq', RT.eq(1, 1) === true);
check('neq', RT.neq(1, 2) === true);
check('not', RT.not(false) === true);
check('and', RT.and(true, true) === true);
check('or', RT.or(false, true) === true);
check('exists', RT.exists(0) === true);
check('exists null', RT.exists(null) === false);
check('isobj', RT.isobj({}) === true);
check('leaf', RT.leaf('x') === true);
check('id', RT.id(42) === 42);

// ============ TEST: SPINDLE ============

console.log('\n=== SPINDLE ===');
const sp = spindle('0.121');
check('spindle(0.121) — 4 nodes', sp.length === 4);
check('first is root', sp[0][1] === 'root');
check('second is life', sp[1][1] === 'life');
check('third is animals', sp[2][1] === 'animals');
check('fourth is mammals', sp[3][1] === 'mammals');

const sp2 = spindle('0.52');
check('spindle(0.52) — 3 nodes', sp2.length === 3);
check('walks matter→liquid', sp2[2][1] === 'liquid');

// ============ TEST: RING ============

console.log('\n=== RING ===');
{
  const { walkDigits } = parse('0.52');
  const r = unfold(BSP_RING, { walkDigits, tree });
  const siblings = (r['8'] || []).filter(x => Array.isArray(x) && x.length === 3);
  check('ring(0.52) — 2 siblings', siblings.length === 2);
  const names = siblings.map(s => s[1]).sort();
  check('ring has solid + gas', names.includes('solid') && names.includes('gas'));
}

// ============ TEST: DIR ============

console.log('\n=== DIR ===');
{
  const { walkDigits } = parse('0.12');
  const r = unfold(BSP_DIR, { walkDigits, tree });
  const subtree = r['2'];
  check('dir(0.12) is animals', read(subtree) === 'animals');
  check('dir has children', subtree['1'] !== undefined);
}

// ============ TEST: POINT ============

console.log('\n=== POINT ===');
{
  const walked = spindle('0.121');
  for (const [ps, expected] of [[-1, 'life'], [-2, 'animals'], [0, 'root']]) {
    const r = unfold(BSP_POINT, { walked, pscale: ps });
    check(`point(0.121, ${ps}) = ${expected}`, r['3']?.[1] === expected);
  }
}

// ============ TEST: DISC ============

console.log('\n=== DISC ===');
{
  // Depth 1: all children of root (return from step 9 yields array directly)
  const nodes = unfold(BSP_DISC_WALK, {
    node: tree, depth: 0, target: 1, path: '', discWalk: BSP_DISC_WALK,
  });
  check('disc depth 1 — 2 nodes', Array.isArray(nodes) && nodes.length === 2);
  const texts = nodes.map(n => n[1]).sort();
  check('disc has life + matter', texts.includes('life') && texts.includes('matter'));

  // Depth 2: grandchildren
  const d2 = unfold(BSP_DISC_WALK, {
    node: tree, depth: 0, target: 2, path: '', discWalk: BSP_DISC_WALK,
  });
  check('disc depth 2 — 5 nodes', Array.isArray(d2) && d2.length === 5);
}

// ============ TEST: TWIST_CHECK ============

console.log('\n=== TWIST_CHECK ===');
check('tool_use → continue',
  unfold(TWIST_CHECK, { response: { stop_reason: 'tool_use' } })['4'] === true);
check('pause_turn → continue',
  unfold(TWIST_CHECK, { response: { stop_reason: 'pause_turn' } })['4'] === true);
check('end_turn → stop',
  unfold(TWIST_CHECK, { response: { stop_reason: 'end_turn' } })['4'] === false);

// ============ TEST: TWIST_EXTRACT ============

console.log('\n=== TWIST_EXTRACT ===');
{
  const content = [
    { type: 'text', text: 'hi' },
    { type: 'tool_use', id: 'tu_1', name: 'read', input: {} },
    { type: 'tool_use', id: 'tu_2', name: 'write', input: {} },
  ];
  const tools = unfold(TWIST_EXTRACT, { content })['1'];
  check('extracts 2 tools', tools.length === 2);
  check('first id', tools[0].id === 'tu_1');
  check('empty when none', unfold(TWIST_EXTRACT, { content: [{ type: 'text' }] })['1'].length === 0);
}

// ============ TEST: TWIST_MESSAGES ============

console.log('\n=== TWIST_MESSAGES ===');
{
  const tools = [
    { type: 'tool_use', id: 'tu_1', name: 'read' },
    { type: 'tool_use', id: 'tu_2', name: 'write' },
  ];
  const content = [{ type: 'text' }, ...tools];
  const results = ['result_1', 'result_2'];
  const messages = [{ role: 'user', content: 'go' }];
  const built = unfold(TWIST_MESSAGES, { tools, results, content, messages });

  check('2 tool_results', built['1'].length === 2);
  check('tool_result type', built['1'][0].type === 'tool_result');
  check('tool_use_id', built['1'][0].tool_use_id === 'tu_1');
  check('3 messages', built['4'].length === 3);
  check('assistant + user appended', built['4'][1].role === 'assistant' && built['4'][2].role === 'user');
}

// ============ SUMMARY ============

console.log(`\n=== SUMMARY: ${pass} passed, ${fail} failed ===`);
