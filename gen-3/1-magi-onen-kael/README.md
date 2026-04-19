# magi-onen — Character Agent

Magi kernel driving a character (Kael) through a narrative RPG scene.
Target use case: plugging into the Onen game as a player or NPC.

## What it is

Same three-phase context window architecture as magi, but pointed at a
character in a game world. The function block compiles: purpose (what the
character intends), character (who they are), world (what they perceive),
history (what has happened). Each instance produces an action and a memory.

## Use cases for Onen

1. **Soft-LLM** (player companion) — receives game state, returns inner life
   (thoughts, feelings, intentions). The player drives. The LLM generates texture.
2. **Character-LLM** (autonomous player) — receives world state + action results,
   returns decisions + actions. Has its own purpose spindle. Plays the game.
3. **NPC reference** (interrogated by game) — holds accumulated state in blocks.
   The game's medium/hard LLM queries it for authentic behaviour.

## Run

```bash
# Requires local LLM at http://127.0.0.1:1234 (LM Studio)
python magi.py --dry            # see compiled prompts
python magi.py --max 3          # run 3 instances
python magi.py --max 5 --delay 1
```

## What happens

Each instance sees what the character perceives (world block), acts in
character (writes action to world:4), and updates memory (writes to
character:4). The next instance sees the updated world and accumulated
history. The story generates itself through the compile-call-write loop.

## Architecture

```
Present phase (system prompt):
  Starstone — constant, teaches BSP
  Function block — the aperture, modified by each instance
  Reflexive mirror — correlates references to compiled content

Past phase (message):
  Purpose — what the character intends
  Character — who they are (spindle: root description)
  World — what they perceive (dir: full scene)
  History — what has happened

Output (JSON):
  function — modified function block (or null)
  writes — narrative action + character memory
  status — continue (story goes on) or complete (character rests)
  note — captured as history
```

## Files

```
magi.py                    # The kernel (~300 lines, local LLM only)
blocks/
  starstone.json           # Constant. Teaches walk/compose/recurse.
  function.json            # The aperture. Points to character/world/purpose/history.
  character.json           # Kael — personality, drives, style, capabilities, memories.
  world.json               # Scene state. Updated by each instance's action.
  purpose.json             # What Kael intends. May evolve through play.
  history.json             # Instance log. Appended each cycle.
  determinacy.json         # Legacy from original magi. Not used by onen.
```

## Next

- Plug into Onen game as an endpoint (game POSTs world state, kernel returns action)
- Merge v3 kernel improvements (tiered models, soul block, anthropic API)
- Purpose as pscale spindle (depth = decomposition, ascent = completion)
