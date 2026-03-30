# magi — Merged Kernel

Combined kernel: v3's engine (tiered models, soul block, local+anthropic)
with onen's game-ready message builder and character blocks.

## What it is

The merged magi kernel handles any use case depending on the blocks you give it:
- **Introspective entity** — soul + vision in determinacy + self-proposed purposes
- **Game character** — character + world + narrative purpose
- **Task agent** — purpose + determinacy content + history

The blocks determine the use case. The kernel doesn't change.

## What's merged from where

From **magi-v3**:
- Tiered models (Haiku -> Sonnet escalation)
- Soul block in system prompt (persistent identity)
- Local + Anthropic API support (`--local` flag)
- Auto-advance on purpose completion

From **magi-onen**:
- Generic message builder (handles character/world/determinacy/any block type)
- Character and world blocks (Kael at the Thornkeep crossroads)

## Run

```bash
# Anthropic API (default)
export ANTHROPIC_API_KEY=sk-ant-...
python magi.py --max 5

# Local LM Studio
python magi.py --local --max 5

# Dry run
python magi.py --dry

# Force model
python magi.py --model sonnet --max 3
```

## Switching use cases

The function block determines what gets compiled. To run as a character agent,
edit `blocks/function.json` to point at character/world blocks. To run as an
introspective entity, point at soul/determinacy. Same kernel, different aperture.

## Architecture

```
Present phase (system prompt):
  Starstone — constant, teaches BSP
  Soul — persistent identity (if soul block exists)
  Function block — the aperture
  Reflexive mirror — correlates references to content

Past phase (message):
  Compiled currents — organised by block type:
    PURPOSE, CHARACTER, WORLD, CONTENT, HISTORY, OTHER
  Task framing — can you close the gap?

Output (JSON):
  function — modified function block (or null)
  writes — content routed to blocks by address
  status — complete/continue/decompose/escalate
  note — captured as history
```

## Files

```
magi.py                    # The kernel (~400 lines)
blocks/
  starstone.json           # Constant. Teaches walk/compose/recurse.
  soul.json                # Entity identity (in system prompt).
  function.json            # The aperture. Modified by each instance.
  purpose.json             # The goal.
  determinacy.json         # Vision document / content to operate on.
  history.json             # Instance log. Appended each cycle.
  walker.json              # Walker implementation (from v3 entity).
  character.json           # Kael (from onen). Personality + memories.
  world.json               # Scene state (from onen). Updated by actions.
```

## Design notes

See `context-window-three-phases.md` for the full architectural spec.
Key insights pending implementation:
- Purpose as pscale spindle (depth = decomposition, ascent = completion)
- Output contract split (structured envelope + free content body)
- Kernel uses BSP on itself (walks purpose/history, not sequential scan)
