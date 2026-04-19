# magi-v3 — Introspective Entity

Magi kernel where the entity explores its own vision document,
writes about itself, and proposes its own next purposes.

## What it is

Three-phase context window architecture with:
- **Soul block** in system prompt (persistent identity, not compiled content)
- **Tiered models** — Haiku does tasks, Sonnet restructures on escalation
- **Local + Anthropic API** support (`--local` flag)
- **Auto-advance** — when purpose 1 completes, advances to self-proposed purpose 3

The entity wrote a walker implementation and a self-introduction.

## Run

```bash
# Anthropic API (default — needs ANTHROPIC_API_KEY)
python magi.py --dry
python magi.py --max 5

# Local LM Studio
python magi.py --local --max 5

# Force a specific model
python magi.py --model sonnet --max 3
```

## Architectural observations (from experiment)

- **Purpose should be a spindle**, not flat. Depth = decomposition, ascent = completion.
  The kernel should walk purpose with BSP, not scan keys sequentially.
- **The aperture mechanism wasn't used organically.** Tasks didn't force navigation.
  A character in a game world WOULD need it — the world is larger than any context window.
- **Output contract too rigid.** Everything squeezed through JSON. Parse failures
  cascaded into fake escalations. Need structured envelope + free content body.
- **Kernel doesn't use BSP on itself.** Auto-advance logic scans keys like conventional
  code. The kernel is supposed to be a walker — it should walk purpose with BSP.

## Architecture

```
Present phase (system prompt):
  Starstone — constant, teaches BSP
  Soul — persistent identity (NOT in message)
  Function block — the aperture
  Reflexive mirror — correlates references to content

Past phase (message):
  Purpose — the gap to close
  Content — compiled determinacy (vision document)
  History — what was attempted

Output (JSON):
  function — modified function block (or null)
  writes — content to write to blocks
  status — complete/continue/decompose/escalate
  note — captured as history
```

## Files

```
magi.py                    # The kernel (~400 lines, tiered models)
blocks/
  starstone.json           # Constant. Teaches walk/compose/recurse.
  soul.json                # Entity identity. In system prompt, not message.
  function.json            # The aperture. Modified by each instance.
  purpose.json             # The goal. Entity can propose its own next purpose.
  determinacy.json         # Vision document (32K chars of nested meaning).
  history.json             # Instance log. Appended each cycle.
  walker.json              # Walker implementation (written by the entity).
```
