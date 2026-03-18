#!/usr/bin/env python3
"""Test: the key in Python.
Same Mode 4 blocks as JS — proves language independence."""

import json, os
from core import nav, read, unfold, RT

# ============ TOUCHSTONE ============
# Blocks loaded from JSON — single source of truth.

_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_dir, 'touchstone.json')) as f:
    touchstone = json.load(f)

BSP_PARSE      = nav(touchstone, '1.1')
BSP_SPINDLE    = nav(touchstone, '1.2')
BSP_RING       = nav(touchstone, '1.3')
BSP_DIR        = nav(touchstone, '1.4')
BSP_POINT      = nav(touchstone, '1.5')
BSP_DISC_WALK  = nav(touchstone, '1.6')
TWIST_CHECK    = nav(touchstone, '2.1')
TWIST_EXTRACT  = nav(touchstone, '2.2')
TWIST_MESSAGES = nav(touchstone, '2.3')

# ============ TEST TREE ============
# A small pscale tree for self-contained testing.

tree = {
    '_': 'root',
    '1': {
        '_': 'life',
        '2': {
            '_': 'animals',
            '1': {'_': 'mammals'},
            '3': {'_': 'birds'},
        },
        '4': {'_': 'plants'},
    },
    '5': {
        '_': 'matter',
        '1': {'_': 'solid'},
        '2': {'_': 'liquid'},
        '3': {'_': 'gas'},
    },
}

# ============ HELPERS ============

passed = 0
failed = 0

def check(label, match):
    global passed, failed
    if match:
        print(f'  ✓ {label}')
        passed += 1
    else:
        print(f'  ✗ {label}')
        failed += 1

def parse(addr):
    r = unfold(BSP_PARSE, {'address': str(addr)})
    return r['5'], r['6']

def do_spindle(addr):
    walk_digits, whole = parse(addr)
    r = unfold(BSP_SPINDLE, {
        'walkDigits': walk_digits, 'whole': whole,
        'tree': tree, 'node': tree,
    })
    walked = r['2'] or []
    nodes = []
    rt = read(tree)
    if rt:
        nodes.append([whole, rt])
    for x in walked:
        if isinstance(x, list) and len(x) == 2:
            nodes.append(x)
    return nodes

# ============ TEST: NAV + READ ============

print('=== NAV + READ ===')
check('nav root', nav(tree, '') is tree)
check('nav null path', nav(tree, None) is tree)
check('nav depth 1', read(nav(tree, '1')) == 'life')
check('nav depth 2', read(nav(tree, '1.2')) == 'animals')
check('nav depth 3', read(nav(tree, '1.2.1')) == 'mammals')
check('nav miss', nav(tree, '9') is None)
check('read string', read('hello') == 'hello')
check('read obj', read({'_': 'test'}) == 'test')
check('read null', read(None) is None)

# ============ TEST: RT ============

print('\n=== RT ===')
check('split', RT['split']('a.b.c', '.') == ['a','b','c'])
check('chars', RT['chars']('abc') == ['a','b','c'])
check('join', RT['join'](['a','b'], '.') == 'a.b')
check('cat', RT['cat']('a','b','c') == 'abc')
check('arr', len(RT['arr'](1,2,3)) == 3)
check('obj', RT['obj']('a', 1, 'b', 2)['b'] == 2)
check('push', len(RT['push']([1,2], 3, 4)) == 4)
check('get', RT['get']([10,20,30], 1) == 20)
check('len', RT['len']([1,2]) == 2)
check('last', RT['last']([1,2,3]) == 3)
check('init', len(RT['init']([1,2,3])) == 2)
check('range', RT['range'](3) == ['0','1','2'])
check('int', RT['int']('42') == 42)
check('add', RT['add'](2, 3) == 5)
check('sub', RT['sub'](5, 3) == 2)
check('eq', RT['eq'](1, 1) == True)
check('neq', RT['neq'](1, 2) == True)
check('not', RT['not'](False) == True)
check('and', RT['and'](True, True) == True)
check('or', RT['or'](False, True) == True)
check('exists', RT['exists'](0) == True)
check('exists null', RT['exists'](None) == False)
check('isobj', RT['isobj']({}) == True)
check('leaf', RT['leaf']('x') == True)
check('id', RT['id'](42) == 42)

# ============ TEST: SPINDLE ============

print('\n=== SPINDLE ===')
sp = do_spindle('0.121')
check('spindle(0.121) — 4 nodes', len(sp) == 4)
check('first is root', sp[0][1] == 'root')
check('second is life', sp[1][1] == 'life')
check('third is animals', sp[2][1] == 'animals')
check('fourth is mammals', sp[3][1] == 'mammals')

sp2 = do_spindle('0.52')
check('spindle(0.52) — 3 nodes', len(sp2) == 3)
check('walks matter→liquid', sp2[2][1] == 'liquid')

# ============ TEST: RING ============

print('\n=== RING ===')
walk_digits, _ = parse('0.52')
r = unfold(BSP_RING, {'walkDigits': walk_digits, 'tree': tree})
siblings = [x for x in (r.get('8') or []) if isinstance(x, list) and len(x) == 3]
check('ring(0.52) — 2 siblings', len(siblings) == 2)
names = sorted(s[1] for s in siblings)
check('ring has solid + gas', 'solid' in names and 'gas' in names)

# ============ TEST: DIR ============

print('\n=== DIR ===')
walk_digits, _ = parse('0.12')
r = unfold(BSP_DIR, {'walkDigits': walk_digits, 'tree': tree})
subtree = r['2']
check('dir(0.12) is animals', read(subtree) == 'animals')
check('dir has children', subtree.get('1') is not None)

# ============ TEST: POINT ============

print('\n=== POINT ===')
walked = do_spindle('0.121')
for ps, expected in [(-1, 'life'), (-2, 'animals'), (0, 'root')]:
    r = unfold(BSP_POINT, {'walked': walked, 'pscale': ps})
    check(f'point(0.121, {ps}) = {expected}', r['3'][1] == expected)

# ============ TEST: DISC ============

print('\n=== DISC ===')
nodes = unfold(BSP_DISC_WALK, {
    'node': tree, 'depth': 0, 'target': 1, 'path': '', 'discWalk': BSP_DISC_WALK,
})
check('disc depth 1 — 2 nodes', isinstance(nodes, list) and len(nodes) == 2)
texts = sorted(n[1] for n in nodes)
check('disc has life + matter', 'life' in texts and 'matter' in texts)

d2 = unfold(BSP_DISC_WALK, {
    'node': tree, 'depth': 0, 'target': 2, 'path': '', 'discWalk': BSP_DISC_WALK,
})
check('disc depth 2 — 5 nodes', isinstance(d2, list) and len(d2) == 5)

# ============ TEST: TWIST ============

print('\n=== TWIST_CHECK ===')
check('tool_use → continue',
    unfold(TWIST_CHECK, {'response': {'stop_reason': 'tool_use'}})['4'] == True)
check('pause_turn → continue',
    unfold(TWIST_CHECK, {'response': {'stop_reason': 'pause_turn'}})['4'] == True)
check('end_turn → stop',
    unfold(TWIST_CHECK, {'response': {'stop_reason': 'end_turn'}})['4'] == False)

print('\n=== TWIST_EXTRACT ===')
content = [
    {'type': 'text', 'text': 'hi'},
    {'type': 'tool_use', 'id': 'tu_1', 'name': 'read', 'input': {}},
    {'type': 'tool_use', 'id': 'tu_2', 'name': 'write', 'input': {}},
]
tools = unfold(TWIST_EXTRACT, {'content': content})['1']
check('extracts 2 tools', len(tools) == 2)
check('first id', tools[0]['id'] == 'tu_1')

print('\n=== TWIST_MESSAGES ===')
tools = [
    {'type': 'tool_use', 'id': 'tu_1', 'name': 'read'},
    {'type': 'tool_use', 'id': 'tu_2', 'name': 'write'},
]
results = ['result_1', 'result_2']
messages = [{'role': 'user', 'content': 'go'}]
built = unfold(TWIST_MESSAGES, {
    'tools': tools, 'results': results,
    'content': content, 'messages': messages,
})
check('2 tool_results', len(built['1']) == 2)
check('tool_result type', built['1'][0]['type'] == 'tool_result')
check('3 messages', len(built['4']) == 3)
check('assistant + user', built['4'][1]['role'] == 'assistant' and built['4'][2]['role'] == 'user')

# ============ CROSS-KITCHEN ============

print('\n=== CROSS-KITCHEN ===')
import subprocess
js_out = subprocess.run(['node', 'test-unfold.js'], capture_output=True, text=True, cwd='/Users/davidpinto/Projects/seaurchin').stdout
# If JS tests pass, both kitchens agree on the same tree with the same blocks
js_pass = '0 failed' in js_out.split('SUMMARY')[1] if 'SUMMARY' in js_out else False
import re
m = re.search(r'(\d+) passed', js_out)
js_count = int(m.group(1)) if m else 0
check(f'JS kitchen passes ({js_count} tests)', js_pass and js_count > 0)

# ============ SUMMARY ============

print(f'\n=== SUMMARY: {passed} passed, {failed} failed ===')
