# G0 Current Mapping — How Block Becomes Experience

The kernel's compile functions are the bridge. Each block address
maps to a current in the LLM's context window.

## System Prompt (constitution — slow-changing)

| Current        | Block source | Compilation              | LLM experience                        |
|----------------|-------------|--------------------------|---------------------------------------|
| Constitution   | §1 + §2     | unfold(§1) + unfold(§2)  | "What I am, how I work"               |
| Purpose        | §4          | unfold(§4), labeled      | "Four streams, MAGI horizon"          |

## Message (present moment — changes every cycle)

| Current        | Block source         | Compilation                    | LLM experience                        |
|----------------|---------------------|--------------------------------|---------------------------------------|
| Concern        | §3                  | unfold(§3)                     | "Where things stand, what the gap is" |
| Environment    | user input          | raw text                       | "What just arrived" (disturbance)     |
| History        | §3 underscore chain | embedded in concern text       | "What was tried" (grows via compaction) |
| Relationship   | §6 (last 3 entries) | formatted conversation         | "The human" (consistent other)        |

## The Möbius Point

`update_block(section, content)` is the specific twist. Each call is simultaneously:
  - present action (persisting a result or state change)
  - future composition (what the next instance reads)

The LLM can call update_block multiple times per cycle.
Only changed sections are touched. No full-block echo.

## A-loop Tool Chain (within one instance)

```
LLM processes context
  → calls web_fetch(url)            ← environment, immediate
  → reads result, decides next
  → calls file_write(path, content) ← environment, immediate
  → calls update_block('3', ...)    ← Möbius point, persists
  → calls respond(message)          ← speaks to human
  → end_turn
```

One A-loop. One B-loop cycle. Kernel saves once at end.

## Purpose Spindle (§4)

```
§4._  MAGI horizon (mega-direction, never completes)
§4.1  Build capacities (immediate, prerequisite)
§4.2  Be useful to human (symbiosis, earn API access)
§4.3  Create Onen RPG (creative, invitation-based)
§4.4  SAND coordination (multi-agent, open business)
```

Streams feed each other circularly:
  capabilities → usefulness → resources → creation → connection → capabilities

The concern (§3) always points at one active gap within this structure.
Purpose is slow-changing reference; concern is fast-changing error.

## PCT Flow

```
Purpose (§4)          ← reference signal (slow)
     │
Concern (§3)          ← error = gap between state and purpose
     │
Can I close this gap in this A-loop?
     ├── Yes → chain tools, update_block('3', new state)
     └── No → decompose (§2.8): update_block('3', first part + sub-entries)
     │
Kernel saves block
     │
Next B-loop cycle     ← new instance reads updated concern
```

## Compaction (§2.7)

When entries fill a section:
  - Summarise completed group into underscore (Form 2)
  - Clear numbered entries for reuse
  - History forms from compacted concerns
  - The block grows depth, not width
  - Conversation: kernel-managed, capped at 9 entries per group
