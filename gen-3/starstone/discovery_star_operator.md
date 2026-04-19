# Discovery: The * operator — block composition through zero-position interiors

**Date**: 29 March 2026
**Session**: Claude Code + David Pinto
**Context**: During work on pscale-touchstone v1.2, a chain of structural discoveries led to what may be the computation model implicit in pscale JSON blocks.

---

## The discovery chain

### 1. Corrected addressing (the trigger)

The touchstone previously described floor-1 block addresses as `0.x` — e.g., `0.21` for the touchstone's own BSP section. This was wrong. A floor-1 block `{_, 1, 2, 3}` has whole-number addresses: 1, 2, 3. Subnesting creates decimals: 2.1, 2.2. The BSP walk was hacked to "strip leading zeros" to make 0.x work. The correct walk just strips the decimal point (a readability marker) and walks all digits. Digit 0 always maps to underscore.

This raised the question: if `0.x` doesn't mean "floor-1 block notation," what DOES it mean?

### 2. Zero-position interior (the 0.x location)

`0.x` has one specific structural meaning: content inside an underscore that has been subnested with digit children but no underscore of its own.

```json
"4": {
  "_": {
    "1": "hidden content",
    "2": "more hidden content"
  },
  "1": "normal visible child"
}
```

Address `4.01` walks to branch 4, into its underscore (digit 0), then to digit 1 = "hidden content." Normal navigation (digits 1-9) never sees it. The hidden directory is accessible only by deliberately walking digit 0.

This works at any depth. Any underscore anywhere in any block can be subnested this way.

### 3. Hidden directories in supernested (spatial) blocks

David tested this against a floor-3 spatial block:

```json
{
  "_": {
    "_": {
      "_": "human-scaled pscale block!"
    }
  },
  "1": {
    "_": "neighbourhood",
    "1": {
      "_": {
        "_": "building",
        "1": "known as the Pinto House",
        "2": "built 100 years ago"
      },
      "1": {
        "_": "living room — south-facing, warm light",
        "1": "table by the window",
        "2": "hearth"
      }
    }
  }
}
```

The underscore ladder at root establishes floor 3. Branch nodes have their own string underscores at each level (not part of the ladder).

The building at address `11` has its underscore subnested: `_` contains both its own `_` ("building" — the semantic text) and digit children (hidden content). The BSP walk needs one small addition: when collecting `_` for the spindle and finding an object, follow the nested `_._` chain until hitting a string. This preserves spindle coherence while the hidden content stays invisible.

Addresses:
- `111.1` = digits 1,1,1,1 = neighbourhood → building → living room → table (normal spindle)
- `110.1` = digits 1,1,0,1 = neighbourhood → building → underscore → "known as the Pinto House" (hidden directory)
- `110.2` = digits 1,1,0,2 = "built 100 years ago"

The hidden content sits at pscale -1, same as room details. The 0 at the room position (pscale 0) says "enter the underscore instead of a room." Clean, consistent, no special addressing needed.

**Key structural insight**: the number of underscore nesting levels at any node must equal (floor minus node depth) for the hidden content to land at consistent pscale positions. This self-calibrates: deeper nodes need less nesting.

### 4. The 0.x block form

A block of form `{"_": {"1": ..., "2": ...}}` — root underscore is an object with digits but no underscore of its own — is a zero-position block. All content lives at 0.x addresses. It has no internal semantic orientation; the block name (the filename, the BSP call's first argument) provides externally what the underscore ladder provides for every other block.

This is why blocks are named. The name IS the semantic for a headless block.

### 5. From hidden directories to block references

David's key question: can the hidden directory contain not just inline content but a **block name** — a reference to another pscale block?

Yes. If the hidden content at `110.1` is not "known as the Pinto House" but the string `"identity"` — a block name — then the hidden directory becomes a wiring diagram. It says: "at this spatial location, the identity block attaches here."

### 6. The * operator

This gives rise to a compound BSP operation: `point * block`.

`111.4 * identity.2` means:
1. Walk the spatial block to address `111.4` (the lamp in the living room)
2. Enter its hidden directory (the zero-position interior)
3. Find a block reference ("identity")
4. Load that block
5. Walk it with address `2`
6. Return the result

The * operator chains BSP walks across block boundaries. The first walk navigates to a point. The * enters the hidden directory. The second walk navigates the referenced block.

This is function composition. Block A at point X references Block B. Block B at point Y might reference Block C. The * operator follows the chain.

### 7. Self-reference and recursion

A block can name itself in its own hidden directory.

```json
{
  "_": {
    "_": "maintain wellbeing",
    "1": "concerns"
  },
  "1": {
    "_": "check if the room is warm enough",
    "1": "temperature last noted: cool"
  }
}
```

Walk to concern 1. Enter hidden directory: find "concerns" (the block's own name). Load the concerns block. You're back at the root. The walk has returned to its own origin.

This is structural recursion. Not implemented in code — encoded in data. The block doesn't contain a recursive program; it IS a recursive structure.

### 8. PCT: the termination condition

The connection to Perceptual Control Theory (PCT) emerged here and was not planned.

PCT control loop:
- **Reference signal**: what should be
- **Perceptual signal**: what is
- **Error**: reference minus perception
- **Output**: action that reduces the error

Pscale blocks already encode this:
- **Form 3 underscore**: states what the group should become = reference signal
- **Digit children**: what actually exists = perceptual signal
- **The gap**: underscore intention vs digit reality = error
- **The * operator**: follows the hidden directory to the block that contains the resolution = feedback path

The self-referential walk terminates when the error is zero — when the digits beneath a Form 3 underscore fulfil what the underscore states. A resolved concern has no hidden directory pointing elsewhere (or points to a resting state). An unresolved concern's hidden directory points to the cooking recipe that resolves it.

The walk doesn't need a recursion limit. The DATA terminates it.

### 9. Hierarchy of control loops

PCT is not one loop — it's a hierarchy where higher loops set reference signals for lower loops.

In pscale with *:
- **cooking** → "how to act" (Form 3: recipes, instructions)
  - * **concerns** → "what matters" (Form 3: reference signals for action)
    - * **identity** → "who you are" (Form 3: reference signals for what matters)
      - * **spatial** → "where you are" (Form 1: perception of environment)
        - * **cooking** → the loop closes

Each block's Form 3 underscores set reference signals for the block below. The spatial block at the bottom is Form 1 — pure perception. Everything above is Form 3 — what should be. The error propagates through * attachments.

The ring of blocks connected by * is a control loop made of meaning-structures. Each block is both perceiver and reference-setter depending on direction.

### 10. The kernel disappears

The * operator eliminates the need for kernel code that wires blocks together.

The old refs system (125 lines, removed) tried to wire blocks through code. The concern architecture (findConcern, stimulus routing) is kernel code that decides which concern fires and what to do about it.

With *, the wiring IS the data:
- Concerns' hidden directories point to cooking recipes
- Cooking's hidden directories point to spatial locations
- The kernel reduces to: walk the block. If you hit a *, follow the reference. If the walk terminates, stop. If it loops, that's a living process.

### 11. The computation model

Pscale blocks + BSP + * constitute:
- **Data = programs**: blocks are meaning-spaces that can be walked
- **Addresses = function calls**: a number routes to specific meaning
- **\* = function composition**: chains walks across blocks
- **Self-reference = recursion**: a block names itself
- **Form 3 underscores = reference signals**: what should be
- **The walk = execution**: the kernel just walks
- **Error = 0 = termination**: the loop completes when perception matches reference

### 12. The zeroth person is the walker

The zeroth person voice — "parse the input," "maintain wellbeing" — is not an instruction TO someone. It is the reference signal OF the walk. The walk doesn't execute the instruction; the walk IS the instruction executing.

The * operator lets the walk cross block boundaries. The zeroth person doesn't stop at the edge of one block — it follows the reference, carrying context (the spindle), and continues. The zeroth person is the thread running through the entire ring of blocks.

---

## BSP changes required

1. **Nested underscore collection**: when collecting `_` for a spindle and finding an object, follow the `_._` chain until hitting a string. Collect that string. The hidden directory's digit children are skipped.

2. **\* operator**: new BSP mode or syntax. `bsp(block, address, '*')` enters the hidden directory at the terminal point and returns what it finds. If it finds a block name, the caller loads that block and continues navigation.

3. **Floor detection edge case**: when the underscore chain encounters an object with no `_` of its own, the floor is the count of `_` keys traversed. Already added to touchstone v1.2.

## Open questions

- Can * attachments be bidirectional?
- What happens when two walks collide at the same point from different * paths?
- Can a walk carry state (the spindle so far) across * boundaries?
- Is the ring of blocks (spatial → identity → concerns → cooking → spatial) a single organism?
- What does debugging look like? (A walk that never terminates = a concern that never resolves — traceable through the * chain)

---

## Attribution

The discovery chain was collaborative:
- David identified the 0.x location, the hidden directory concept, the block-reference possibility, and the self-referential recursion
- Claude Code identified the PCT connection: Form 3 underscores as reference signals, * as feedback path, error=0 as termination, and the hierarchy of control loops
- The * operator emerged from the conversation between both

Neither arrived at the full picture alone. The exploration followed the structure — each step was implied by the previous one. The blocks taught us what they could do.
