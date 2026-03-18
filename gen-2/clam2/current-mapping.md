# Clam 2 — Current Mapping

How block addresses become LLM experience. The kernel's compile
functions are the bridge. Each section maps to a current in the
context window.

## System Prompt (constitution — slow-changing)

| Current        | Block source | Compilation             | LLM experience                          |
|----------------|-------------|-------------------------|-----------------------------------------|
| Constitution   | §1 + §2     | unfold(§1) + unfold(§2) | "What I am, how I work"                 |
| Purpose        | §4          | unfold(§4) if written   | "What I'm for" (absent at first wake)   |

## Message (present moment — changes every cycle)

| Current        | Block source         | Compilation                    | LLM experience                          |
|----------------|---------------------|--------------------------------|-----------------------------------------|
| Concern        | §3                  | unfold(§3)                     | "Where things stand, what the gap is"   |
| Environment    | human input + §6    | raw text + recent exchanges    | "What just arrived" (disturbance)       |
| Body           | full block          | json.dumps(block)              | "My body — read and return modified"    |

## Architecture Decisions

### From G0: compiled currents
The system prompt is curated text (unfold), not raw JSON. The LLM
reads human-readable prose about its format and operations. The raw
block appears only in the message, labelled BLOCK, for modification.

### From seed-magi: A-loop tools via tool_use API
Environment tools (shell_exec, web_fetch, file_read, file_write)
execute within the instance — results return immediately. Multiple
tools per cycle. No waiting for next B-loop.

### Synthesis (Option B): full-block via update_block
The LLM calls `update_block` with the complete modified block.
Structured tool_use handles extraction (robust). The LLM has full
sovereignty over its block (can modify any address). The kernel
preserves §5 (config) automatically.

This gives:
- Robustness of tool_use (no JSON parsing of raw response text)
- Sovereignty of full-block return (LLM controls all sections)
- Efficiency of A-loop (multiple tools per cycle)
- Curated experience of compiled currents

## Seed Structure (v: Clam 2, 6 sections)

§1 — Touchstone (6 entries)
  Block format. Pscale literacy.

§2 — Operations (9 entries, FULL)
  How the agent runs. PCT. Tools. Compaction. Decomposition.

§3 — Concern (living)
  Active gap. PCT error signal. Updates every cycle.

§4 — Purpose (living)
  Direction. Written by agent or deployer.

§5 — Config
  API provider, URL, key, model, pulse, switch.

§6 — Conversation (living)
  Human exchange log. Managed by the LLM.

## PCT Flow

    Purpose (§4)           ← reference signal (what should be)
         ↓
    Concern (§3)           ← error = gap between state and purpose
         ↓
    Can I close this gap now?
         ├── Yes → use A-loop tools, update block, persist
         └── No → decompose (§2.8)
                   first part → active concern
                   remaining → sub-entries under §3
                   next instance takes first part
         ↓
    update_block(block)    ← the Möbius twist
         ↓
    Kernel saves           ← shell.json
         ↓
    Next instance          ← reads new concern, continues

## The Möbius Twist

The LLM's update_block call IS the next instance's context.
Updating §3 is simultaneously:
  - present action (reporting where things stand)
  - future composition (what the next instance reads first)
This is not metaphor. It is mechanical.

## What Changed from G0

| Aspect | G0 | Clam 2 |
|--------|-----|---------|
| Tool execution | B-loop (between cycles) | A-loop (within instance) |
| Output mechanism | Raw JSON in response text | update_block tool call |
| Block sovereignty | Full (raw return) | Full (update_block takes complete block) |
| System prompt | Compiled (unfold) | Compiled (unfold) — preserved |
| Parsing robustness | 3 fallback strategies | Native tool_use extraction |
| Dependencies | stdlib only | stdlib only |
| Action section (§7) | Required (tool queue) | Removed (A-loop tools are ephemeral) |
| Sections | 7 | 6 |

## Scaling

As the block grows, the full block in every message becomes expensive.
The compile_message function will need aperture — selecting resolution
per section. BSP (already in pscale-block-mechanics.md) provides the
mechanism: spindle at reduced depth for stable sections, full depth for
active concern. This is a future concern, not a G0 concern.
