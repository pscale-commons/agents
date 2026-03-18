# seaurchin

JSON is the program. The key is the kitchen.

A ~130-line runtime that executes programs written as JSON trees. Write the program once, run it in any language. Currently: JavaScript and Python.

## The idea

Programs are JSON objects called **Mode 4 blocks**. Digits `1`–`9` are sequential steps. `_` holds the instruction text. The runtime (`unfold`) walks the steps, resolves references, and dispatches to a small set of primitives (`RT`).

The blocks are language-independent. The runtime maps the same op names to each language's native operations. Same recipe, different kitchen.

```
┌─────────────────────────┐
│  Mode 4 block (JSON)    │  ← the program (portable)
├─────────────────────────┤
│  unfold                 │  ← the engine (~25 lines)
│  RT primitives          │  ← the screwdriver (~30 lines, per-language)
│  nav + read             │  ← the button (~10 lines)
└─────────────────────────┘
```

## Quick example

A block that reverses a string:

```json
{
  "_": "Reverse a string",
  "1": "chars $input",
  "2": { "_": "each #1",
    "1": "sub $len $i",
    "2": "sub #1 1",
    "3": "get $chars #2",
    "4": "return #3"
  },
  "3": "join #2 "
}
```

Run it:

```javascript
import { unfold } from './core.js';

const reversed = unfold(block, {
  input: 'hello',
  chars: 'hello'.split(''),
  len: 5,
});
// reversed['3'] === 'olleh'
```

## How blocks work

### Steps

A block has up to 9 steps, keyed `"1"` through `"9"`. Each step is either:
- A **string** — the instruction itself
- An **object** — `_` holds the instruction, sub-keys hold branches or sub-blocks

Steps execute in order. Each step's result is stored and can be referenced by later steps.

### References

| Syntax | Meaning |
|--------|---------|
| `$name` | Context variable (passed in or set by `let`) |
| `#N` | Result of step N in the current block |
| `#N.key` | Nested property access on step N's result |
| `42`, `3.14` | Numeric literal |
| `true`, `false`, `null` | Boolean/null literals |
| anything else | String literal |

### Instructions

**Control flow:**

| Op | Syntax | Effect |
|----|--------|--------|
| `return` | `return #3` | Exit block, return value |
| `let` | `let name #2` | Set context variable, continue |
| `if` | `if #1` with sub-keys `1:` and `2:` | Branch — executes `1:` if truthy, `2:` if falsy |
| `guard` | `guard #1 op args...` | If condition truthy, call op and return result. Otherwise continue. |
| `each` | `each #1` with sub-block | Iterate array. Sets `$item` and `$i`. Collects non-undefined results. Context is shared across iterations (so `let` carries state). |
| `concat` | `concat #1` with sub-block | Like `each` but spreads array results — for recursive aggregation |
| `call` | `call $block key1 val1 key2 val2` | Invoke another Mode 4 block with key-value context overrides |

**Tree operations:**

| Op | Syntax | Effect |
|----|--------|--------|
| `nav` | `nav $tree 1.2.3` | Navigate a tree by dot-separated path |
| `read` | `read $node` | Extract the `_` value from a node |

**RT primitives** — everything else dispatches to the RT table:

| Category | Ops |
|----------|-----|
| String | `split` `chars` `join` `cat` |
| Array/Object | `get` `len` `arr` `obj` `push` `last` `init` `range` |
| Number | `int` `add` `sub` |
| Logic | `eq` `neq` `not` `and` `or` `exists` `isobj` `leaf` `id` |

## RT reference

| Op | Args | Returns | Example |
|----|------|---------|---------|
| `split` | string, separator | array | `split $s .` → `["a","b"]` |
| `chars` | string | array of chars | `chars $s` → `["h","i"]` |
| `join` | array, separator | string | `join #1 .` → `"a.b"` |
| `cat` | values... | concatenated string | `cat $a . $b` → `"x.y"` |
| `get` | array, index | element | `get #1 0` → first element |
| `len` | array | number | `len #1` → 3 |
| `arr` | values... | new array | `arr #1 #2` → `[a, b]` |
| `obj` | key, val, key, val... | new object | `obj type result id #1` → `{type:"result", id:...}` |
| `push` | array, items... | new array with items appended | `push $msgs #2 #3` → `[...msgs, a, b]` |
| `last` | array | last element | `last #1` → final item |
| `init` | array | all but last | `init #1` → `[a, b]` from `[a, b, c]` |
| `range` | n | `["0", "1", ... "n-1"]` | `range 10` → `["0"..."9"]` |
| `int` | string | integer | `int $s` → 42 |
| `add` | a, b | a + b | `add $x 1` → increment |
| `sub` | a, b | a - b | `sub $x 1` → decrement |
| `eq` | a, b | boolean | `eq #1 done` → true/false |
| `neq` | a, b | boolean | `neq #1 0` |
| `not` | a | boolean | `not #1` |
| `and` | a, b | boolean | `and #1 #2` |
| `or` | a, b | boolean | `or #1 #2` |
| `exists` | a | true if not null | `exists #1` |
| `isobj` | a | true if object/dict | `isobj #1` |
| `leaf` | a | true if not object | `leaf #1` |
| `id` | a | a (identity/passthrough) | `id $item` |

## Trees

Seaurchin operates on JSON trees where nodes can hold a value at `_` and children at any other key:

```json
{
  "_": "root",
  "1": {
    "_": "life",
    "2": { "_": "animals" },
    "4": { "_": "plants" }
  },
  "5": {
    "_": "matter",
    "1": { "_": "solid" },
    "2": { "_": "liquid" }
  }
}
```

`nav(tree, "1.2")` → the animals node. `read(nav(tree, "1.2"))` → `"animals"`.

## Writing a new key

To port seaurchin to another language, implement four things:

1. **`nav(tree, path)`** — walk a nested dict/object by dot-separated path
2. **`read(node)`** — return `node._` if object, the string itself if string, null otherwise
3. **`RT`** — map the 29 op names to native equivalents
4. **`unfold(block, ctx)`** — walk steps 1–9, resolve `$`/`#` references, dispatch ops

The JS key is 130 lines. The Python key is 130 lines. They produce identical results on identical blocks.

## Running tests

```bash
# JavaScript
node test-unfold.js

# Python (also validates against JS)
python3 test_unfold.py
```

## What uses this

[Ammonite](https://github.com/happyseaurchin/ammonite) — an LLM kernel that uses seaurchin's unfold to execute its core algorithms (BSP tree navigation, the twist loop) as Mode 4 blocks rather than hand-written code.
