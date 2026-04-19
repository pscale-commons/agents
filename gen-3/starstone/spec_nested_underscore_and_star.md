# Implementation spec: nested underscore collection and * operator

**Purpose**: Precise specification for implementing two additions to BSP. Sufficient for any Claude Code session to implement and test without prior context.

---

## Part 1: Nested underscore collection (`_._` chain)

### The problem

Current BSP walk collects `_` at each node for the spindle. It assumes `_` is always a string. When `_` is an object (a hidden directory with its own `_`), the walk breaks.

### The rule

When collecting `_` at any node during a walk:

```
function collectUnderscore(node):
    val = node["_"]
    if val is a string:
        return val                    # normal case
    if val is an object:
        if val has key "_":
            return collectUnderscore(val)  # follow the chain
        else:
            return null               # zero-position interior, no text
```

This is recursive. It follows `_` → `_` → `_` until hitting a string. Any digit children alongside the `_` keys are ignored — they are hidden directory content, not spindle text.

### Three cases

**Case A — normal (current behavior)**:
```json
{"_": "building", "1": "room"}
```
collectUnderscore returns "building". Walk continues normally.

**Case B — hidden directory with semantic text**:
```json
{"_": {"_": "building", "1": "Pinto House", "2": "built 100 years ago"}, "1": "room"}
```
collectUnderscore follows `_` → finds object → has `_` → follows → finds "building" (string) → returns "building". The spindle gets "building". Keys 1, 2 inside the underscore are invisible to normal navigation.

**Case C — zero-position interior (headless)**:
```json
{"_": {"1": "hidden", "2": "content"}, "1": "room"}
```
collectUnderscore follows `_` → finds object → no `_` key → returns null. The spindle skips this level (or marks it as "interior present, no text").

### Impact on floor detection

Floor detection already follows the `_` chain. The same logic applies: follow `_` → `_` until string (count = floor) or until an object with no `_` (zero-position interior, terminate count).

Floor detection and spindle collection use the SAME chain-following logic. Factor it out.

### Impact on existing blocks

None. All existing blocks have string underscores at every node. The change only activates when `_` is an object, which no current block uses. Backward compatible.

---

## Part 2: The * operator

### What it is

A compound BSP operation that chains walks across block boundaries via hidden directory references.

### Syntax

```
bsp(block, address, '*')
```

Returns the contents of the hidden directory at the terminal node of the walk.

### Full compound syntax

```
bsp(block1, address1, '*', block2_name, address2)
```

Means: walk block1 to address1, enter its hidden directory, find block2_name, load block2, walk block2 to address2.

But this can be simplified. The hidden directory CONTAINS the block reference. So:

```
result = bsp(block1, address1, '*')
# result includes the block name(s) and/or inline content in the hidden directory
# caller decides whether to load and walk the referenced block
```

### How the hidden directory is accessed

When BSP reaches the terminal node of a walk and mode is '*':

1. Get the terminal node (the object at the end of the walk)
2. Look at its `_` value
3. If `_` is a string → no hidden directory exists at this point. Return null.
4. If `_` is an object → this IS the hidden directory. Return its digit children as the result.
   - If the object has its own `_` (Case B): the `_._` is the semantic text; digits 1-9 are hidden content
   - If the object has no `_` (Case C): all digit children are hidden content

### What the hidden directory contains

Three possibilities for each digit child:

1. **Inline text**: `"1": "known as the Pinto House"` — literal content, returned as-is
2. **Block reference**: `"1": "identity"` — a block name (string matching a loadable block). The caller loads this block and can navigate it.
3. **Inline block**: `"1": {"_": "...", "1": "..."}` — a pscale block embedded directly. Navigable with BSP without loading.

The BSP function doesn't distinguish between these. It returns the content. The CALLER interprets: is this a block name to load? Inline content? An embedded block to navigate? That decision belongs to the consumer (kernel, agent, tool), not the walk function.

### The walk across *

In practice, a full * walk looks like this (pseudocode):

```
function starWalk(block1, address1, address2):
    # Phase 1: walk to the attachment point
    node = walkTo(block1, address1)

    # Phase 2: enter hidden directory
    underscore = node["_"]
    if underscore is not an object:
        return error("no hidden directory at this address")

    hidden = underscore  # the hidden directory object

    # Phase 3: navigate the hidden directory
    if address2 is provided:
        return bsp(hidden, address2)  # treat hidden dir as a block
    else:
        return hidden  # return the whole directory
```

### Relationship to existing modes

The * is not a replacement for spindle/ring/dir/point/disc. It's orthogonal. After entering a hidden directory via *, all existing modes work on the content found there:

- `bsp(block, address, '*')` — returns the hidden directory (like dir)
- `bsp(block, address, '*', sub_address)` — spindle within the hidden directory
- `bsp(block, address, '*', sub_address, 'ring')` — ring within the hidden directory

### Self-reference

When a hidden directory contains the name of its own block:

```json
{
  "_": {
    "_": "maintain wellbeing",
    "1": "concerns"          // ← references itself
  },
  "1": { ... }
}
```

`bsp("concerns", 0, '*')` returns `{"1": "concerns"}`. The caller sees the block name "concerns," loads it, and re-enters. This IS recursion. Termination is the caller's responsibility — check if the walk returns to a previously visited point, or if the error condition (Form 3 reference vs digit reality) is resolved.

---

## Part 3: Test blocks

### Block: `test-spatial`

A floor-3 spatial block with hidden directories at neighbourhood and building levels.

```json
{
  "_": {
    "_": {
      "_": "a small coastal town"
    }
  },
  "1": {
    "_": {
      "_": {
        "_": "the harbour district",
        "1": "oldest part of town",
        "2": "fishing heritage"
      }
    },
    "1": {
      "_": {
        "_": "the blue house",
        "1": "known as the Pinto House",
        "2": "built 100 years ago",
        "3": "test-identity"
      },
      "1": {
        "_": "living room — south-facing, warm light",
        "1": "table by the window",
        "2": "hearth",
        "3": "grandmother's lamp"
      },
      "2": {
        "_": "kitchen — narrow, north-facing",
        "1": "stove",
        "2": "sink"
      }
    },
    "2": {
      "_": "the red house",
      "1": {
        "_": "workshop",
        "1": "lathe",
        "2": "workbench"
      }
    }
  }
}
```

### Block: `test-identity`

A floor-1 rendition block describing who lives in the blue house.

```json
{
  "_": "Identity of the residents of the blue house — who lives here, what matters to them, how they relate to the space.",
  "1": "David — has lived here since 2019. Morning person. Starts the day at the hearth.",
  "2": "The living room is the centre of daily life. The lamp was grandmother's — it stays on.",
  "3": {
    "_": "What matters here — the concerns that shape daily rhythm.",
    "1": "warmth — the house is old and loses heat; the hearth is not decorative",
    "2": "light — south-facing is everything; the table is placed for morning light",
    "3": "quiet — the harbour district is noisy in summer; the kitchen faces north for a reason"
  }
}
```

---

## Part 4: Expected results

### Normal spindles (nested underscore collection)

**`bsp(test-spatial, 111.1)`** — digits 1,1,1,1:
```
Spindle:
  [+2] "the harbour district"       ← collected via _._._
  [+1] "the blue house"             ← collected via _._
  [ 0] "living room — south-facing, warm light"
  [-1] "table by the window"
```

**`bsp(test-spatial, 111.3)`** — digits 1,1,1,3:
```
Spindle:
  [+2] "the harbour district"
  [+1] "the blue house"
  [ 0] "living room — south-facing, warm light"
  [-1] "grandmother's lamp"
```

**`bsp(test-spatial, 121.1)`** — digits 1,2,1,1:
```
Spindle:
  [+2] "the harbour district"
  [+1] "the red house"              ← normal string _, no hidden dir
  [ 0] "workshop"
  [-1] "lathe"
```

**`bsp(test-spatial, 0)`** — digit 0:
```
Spindle:
  follows root._ → root._._ → root._._._ = "a small coastal town"
```

### Hidden directory access via *

**`bsp(test-spatial, 11, '*')`** — hidden directory at the blue house:
```
Returns: {
  "1": "known as the Pinto House",
  "2": "built 100 years ago",
  "3": "test-identity"
}
```

**`bsp(test-spatial, 1, '*')`** — hidden directory at the harbour district:
```
Returns: {
  "1": "oldest part of town",
  "2": "fishing heritage"
}
```

**`bsp(test-spatial, 12, '*')`** — hidden directory at the red house:
```
Returns: null (_.is a string "the red house", no hidden directory)
```

**`bsp(test-spatial, 111, '*')`** — hidden directory at the living room:
```
Returns: null (_ is a string, no hidden directory)
```

### Cross-block walk via *

**`bsp(test-spatial, 11, '*', 'test-identity', 3.1)`**:
1. Walk test-spatial to address 11 (the blue house)
2. Enter hidden directory → find "test-identity" at key 3
3. Load test-identity block
4. Walk test-identity to address 3.1

```
Spindle from test-identity 3.1:
  [ 0] "Identity of the residents of the blue house..."
  [-1] "What matters here — the concerns that shape daily rhythm."
  [-2] "warmth — the house is old and loses heat; the hearth is not decorative"
```

### Pscale-consistent hidden directory access

**`bsp(test-spatial, 110.1)`** — digits 1,1,0,1 — walk INTO the hidden directory via normal addressing:
```
  digit 1 → root[1] (harbour district)
  digit 1 → root[1][1] (blue house node)
  digit 0 → root[1][1]._ (the underscore object — the hidden directory)
  digit 1 → root[1][1]._[1] = "known as the Pinto House"
```

This is the SAME content as `bsp(test-spatial, 11, '*')` key 1, accessed through normal digit-0 navigation rather than the * operator. Both paths reach the same data. The * operator is syntactic sugar for digit-0 entry, but with the added capability of following block references.

**`bsp(test-spatial, 100.1)`** — digits 1,0,0,1 — neighbourhood hidden directory:
```
  digit 1 → root[1]
  digit 0 → root[1]._ (neighbourhood underscore object)
  digit 0 → root[1]._._ (inner underscore object with "the harbour district" and digits)
  digit 1 → root[1]._._[1] = "oldest part of town"
```

---

## Part 5: Implementation checklist

### Minimum viable implementation

1. **BSP function** (~150 lines):
   - [ ] `collectUnderscore(node)` — recursive chain follower
   - [ ] Modify walk to use `collectUnderscore` instead of direct `node["_"]`
   - [ ] Add `*` mode: return hidden directory contents at terminal node
   - [ ] All existing modes (spindle, ring, dir, point, disc) unchanged except using `collectUnderscore`

2. **Block loader** (~20 lines):
   - [ ] Given a block name, load from filesystem (JSON file)
   - [ ] Cache loaded blocks

3. **Test harness** (~50 lines):
   - [ ] Load test-spatial and test-identity blocks
   - [ ] Run all expected results from Part 4
   - [ ] Assert spindle contents match
   - [ ] Assert * returns match
   - [ ] Assert cross-block walk works

4. **Star walker** (~30 lines):
   - [ ] `starWalk(block, address, targetBlock, targetAddress)`
   - [ ] Composes: walk → enter hidden dir → find reference → load block → walk
   - [ ] Handles inline content (no second walk needed)
   - [ ] Handles block references (loads and walks)

### What NOT to build yet

- Recursion detection (self-referencing blocks). Note it, don't solve it.
- Bidirectional * (both blocks referencing each other). Test it, observe what happens.
- Kernel integration. This is standalone BSP + test blocks.
- Any concern system, timing, or agent loop. Pure navigation first.

---

## Part 6: File locations

All test files should go in: `tidy-up/star-tests/`

```
tidy-up/star-tests/
  bsp.py              ← new BSP implementation with nested _ and *
  test-spatial.json    ← floor-3 spatial block with hidden dirs
  test-identity.json   ← floor-1 identity block
  test_star.py         ← test harness, runs all assertions
  README.md            ← points to this spec
```

---

## Notes for the implementing session

- Read `tidy-up/pscale-touchstone.json` first. It is the v1.2 spec with corrected addressing (whole numbers, not 0.x), Form 3, zeroth person, and zero-position interior.
- Read `tidy-up/pscale-touchstone-lean.json` for the operational (Form 3) version.
- Read `tidy-up/discovery_star_operator.md` for the full discovery narrative.
- The existing `lib/bsp.py` handles wrapped blocks (with `tree` key). The tidy-up `bsp.py` handles pure-form blocks. Build from the tidy-up version.
- The `*` operator is the most important thing. Get nested underscore collection working first (it's prerequisite), then `*`, then cross-block walks.
- Do NOT integrate with hermitcrab kernel. This is standalone.
