# Systemic Development — Magi Plex 1 Seed

**Thread**: Synthesise minimal general-purpose agent (G0 hermitcrab). B-loop-sustained, purpose-driven, human input as disturbance.

**Foundation**: `magi-two-layers.md`

**Runtime**: Python kernel (seed.py) + Anthropic API. Model: Haiku.

---

## Artefacts (v3.2 — final)

| File | Description |
|------|-------------|
| `seed.json` | 6-section seed. §1 format (6 entries), §2 operations (9 entries), §3 concern, §4 purpose, §5 config, §6 conversation+history |
| `seed.py` | Python kernel ~250 lines. Tool_use API, A-loop tools, update_block B-loop, two-channel unfold compilation, history compaction, sleep support |

Run: `ANTHROPIC_API_KEY=sk-... python3 seed.py seed.json`

Dependencies: `requests` (`pip install requests`)

---

## Architecture

| Decision | Rationale |
|----------|-----------|
| Tool_use API, not text parsing | Text markers failed (quoting, malformation, training resistance). Structured output. |
| A-loop tools (immediate) | Multi-step tasks in one cycle. |
| update_block as Möbius point | Structured persistence. Calling it IS the B-loop twist. |
| Two-channel unfold compilation | System = constitution (§1-2, §4 unfolded as text). Message = concern + environment + conversation. Config excluded. |
| Haiku primary | Tests the floor. |
| Concern required, rest optional | Forces continuity every cycle. |
| Sleep field in update_block | Agent controls its own cycle frequency. Idle = longer sleep. |
| History compaction at 800 chars | Kernel truncates to last 500 chars at pipe boundary. |
| Conversation capped at 8, key 9 reserved for history | Prevents key collision in §6. |

---

## Test Results (30+ cycles across 6 tests)

### Passed

| Test | Cycles | What it proved |
|------|--------|---------------|
| Trivial purpose (time monitoring) | 5 | B-loop continuity, tool use, concern carry |
| Multi-step completion (system report) | 6 | A-loop capability (3 tools in 1 instance) |
| Forced B-loop decomposition (3 files) | 4 | Concern decomposes across instances when constrained |
| Disturbance with cancellation ("never mind") | 4 | Agent correctly drops purpose on explicit cancel |
| Pure disturbance ("by the way, 7×8?") | 4 | Agent answers AND continues to purpose. PCT behaviour. |
| File monitoring (status.txt changes) | 5 | Self-decomposition — agent monitors across cycles without being told "one step per cycle". Detects changes, logs to changelog. |
| History compaction | 11 | History stays under 800 chars, compacts with "..." prefix |
| Idle/sleep recognition | 11 | Agent requests 120-300s sleep when no gap. 9 of 10 idle cycles set sleep. |
| Key collision | 11 | Conversation keys skip 9, history survives. Verified after 11 cycles. |

### Key finding: disturbance handling

With §2.2 ("respond, then return to reference signal") and §2.9 ("purpose persists until YOU determine it complete or human explicitly changes it"):
- "By the way, 7×8?" → agent answers 56, then continues creating countup.txt. Purpose maintained.
- "Never mind the files" → agent drops purpose. Correct — explicit cancellation.

This is the PCT distinction: disturbance moves perception without replacing the reference signal. Only explicit purpose change replaces the reference.

### What wasn't tested

- **50+ cycle endurance**: Longest single run was 11 cycles. Long-duration stability unknown.
- **Self-decomposition without monitoring framing**: The file-monitoring test naturally decomposed, but it was framed as "each cycle." A task like "write a 5000-word report" that exceeds single-instance output hasn't been tested.
- **Multi-agent**: No second hermitcrab running alongside.
- **Web tools**: Container restricted web access. web_fetch has 10s timeout but no real-world URLs tested.
- **Interactive human conversation**: All tests used scripted input. Natural conversation flow untested.

---

## Seed Structure (v3.2)

```
§_ : Reflexive opening (self-describing, names all sections, states obligation)
§1 : Format — pscale block mechanics (6 entries: JSON, BSP, floor, supernesting, underscore forms, twist)
§2 : Operations — persistence and agency (9 entries: loop, PCT, decomposition, loops, tools, compaction, budget, update_block fields, purpose persistence)  
§3 : Concern — PCT error signal, continuity thread (string, updated every cycle)
§4 : Purpose — direction not tasks (object with entries, agent writes)
§5 : Config — API provider, URL, key, model, pulse, switch
§6 : Conversation + history — entries at keys 1-8, history at key 9
```

Constitution (§1-2) is immutable. Working state (§3-6) is mutable.

System prompt unfolds §_, §1, §2, §4 as readable text (~3600 chars).
Message carries §3 (concern) + human input + §6.9 (history) + recent conversation from §6.

---

## Kernel Mechanics (seed.py)

```
Main loop:
  check switch (§5.5) → 
  collect human input → 
  compile_system (unfold §1, §2, §4) → 
  compile_message (§3 + human + history + recent) → 
  call_llm_with_tools (A-loop: execute env tools, return results, repeat until update_block) → 
  apply_update (write §3, §4, §6.9, extract sleep) → 
  add_conversation (§6, cap at 8, skip key 9) → 
  save block → 
  sleep (agent-requested or default pulse) → 
  repeat
```

Tool definitions sent to API: shell_exec, web_fetch, file_read, file_write, update_block.

Environment tools execute within instance (A-loop). update_block ends the instance (B-loop).

---

## G0 → G1 Path

What would make this G1:

1. **Model tiering**: Haiku for gap-detection cycles, Sonnet for resolution, Opus for purpose-setting. Kernel selects based on concern complexity or explicit agent request.

2. **Block growth**: update_block currently writes §3, §4, §6.9 only. For the agent to grow its own block (add new sections), needs either additional fields or a separate block_write tool.

3. **BSP compilation**: System prompt currently unfolds full sections. As block grows, needs spindle-level compilation — select specific addresses at specific resolutions. The aperture mechanism.

4. **Concern quality tuning**: Move from task-description style to PCT error-signal style. Example: not "file written, task done" but "2 of 3 files created; file 3 depends on file 2 content."

5. **Wake block**: Separate trigger logic — cron, webhook, SAND mark arrival. Currently just timer.

6. **SAND integration**: Passport publication, beach discovery, grain exchange. Requires working single-instance first (done).

---

## For CC / Repo Push

Files to push:
- `seed.json` → target location TBD by David
- `seed.py` → same location
- `systemic-development.md` → docs/ or specs/

No dependencies beyond `requests`.

API key via `ANTHROPIC_API_KEY` env var or seed §5.2.

---

*March 2026. Thread complete for G0.*
