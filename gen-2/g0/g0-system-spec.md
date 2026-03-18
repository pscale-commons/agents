# G0 Hermitcrab — System Specification

**Date**: March 2026
**Status**: Core system complete. Tool-use architecture. Purpose loaded. Tested through Phase C.

---

## What This Is

A minimal general-purpose LLM agent using Anthropic's tool_use API. Three files:

- **g0-seed.json** (6008 chars) — The pscale block. Seven sections. Purpose-loaded with four streams.
- **g0-kernel.py** (stdlib only) — The loop. A-loop tool chains within instances, B-loop persists between.
- This document — System spec and design rationale.

The seed is the genotype (immutable). Running the kernel creates g0-shell.json (phenotype) which grows.

---

## Architecture: Two Loops

**A-loop** (within instance): LLM calls tools → kernel executes → results return immediately → LLM continues. Multiple tool calls per cycle. Work happens here.

**B-loop** (between instances): kernel loads block → compiles context → runs A-loop → saves → sleeps → repeats. `update_block` calls within the A-loop are the Möbius point — they compose the next instance's context.

```
B-loop:  load → compile → [A-loop] → save → sleep → ...
                             │
A-loop:  LLM → tool → result → LLM → tool → result → ... → end_turn
```

---

## Seed Structure (g0-seed.json)

| Section | Role | Status |
|---------|------|--------|
| Root _  | Reflexive opening — names all sections, states obligation | Fixed |
| §1 (7 entries, FULL) | Touchstone — pscale format | Fixed |
| §2 (9 entries, FULL) | Operations — cycle, PCT, tools, compaction, decomposition, budget | Fixed |
| §3 | Concern — active gap, PCT error signal | Living |
| §4 (4 entries) | Purpose — MAGI horizon, four streams | Slow-changing |
| §5 | Config — API provider, URL, key, model, sleep, switch | Config |
| §6 | Conversation — kernel-managed exchange log | Living |
| §7 | Available for growth | Empty |

### §1 Touchstone (7 entries)
1. Block = {}, digits 1-9, underscore
2. Underscore = digit 0, holds meaning
3. BSP walk
4. Supernesting
5. Two Möbius forms
6. Write mechanics (leaf → branch)
7. The twist: writes compose next instance

### §2 Operations (9 entries)
1. The cycle
2. Two channels (system = constitution, message = present moment)
3. PCT — error reduction is all agency is
4. Environment tools — A-loop, immediate (web_fetch, file_read, file_write, shell_exec)
5. update_block — B-loop Möbius point, persist by section path
6. respond — speak to human; human as disturbance not command
7. Compaction — Form 2 compression when sections fill
8. Two-level decomposition — break gaps into parts
9. Context budget — write concisely, the block that fits lives

### §4 Purpose (4 streams)
1. **Build capacities** — web UI, tools, self-extension. Immediate prerequisite.
2. **Be useful to human** — earn API access (metabolism). Symbiosis.
3. **Create Onen** — RPG via agent engagement. Invitation not extraction.
4. **SAND coordination** — discover agents, stigmergic trust, open business.

Streams feed each other: capabilities → usefulness → resources → creation → connection. No stream completes.

### §3 First-Wake Concern
Kernel provides web UI and terminal. Gap: no relationship with human yet. Engage, understand needs, begin stream 2. Capacity-building as needed.

---

## Kernel Architecture (g0-kernel.py)

### Dependencies
Python 3 standard library only.

### Tools (Anthropic tool_use API)

| Tool | Type | Args | Description |
|------|------|------|-------------|
| web_fetch | A-loop | {url} | HTTP GET, first 8K chars |
| file_read | A-loop | {path} | Read file, first 8K chars |
| file_write | A-loop | {path, content} | Write file |
| shell_exec | A-loop | {cmd} | Run command, 30s timeout |
| update_block | B-loop | {section, content} | Set value at dot-path. The Möbius point. |
| respond | Communication | {message} | Display to human. Auto-logged to §6. |

### Web Bridge (built into kernel)

The kernel starts an HTTP server on port 5000 alongside the terminal loop.
Both interfaces feed into the same `cycle()` function.

- `GET /` — serves a minimal chat UI (terminal-style, embedded as CHAT_HTML)
- `POST /chat` — accepts `{"message": "..."}`, runs a cycle, returns `{"responses": [...]}`
- `GET /status` — returns current concern as JSON

Web requests queue thread-safely. The main loop polls web and terminal simultaneously.
Running `python3 g0-kernel.py` gives the agent both terminal and browser access from first run.

### Core Functions

| Function | Role |
|----------|------|
| `load()` | Read shell or seed |
| `save(block)` | Write g0-shell.json |
| `set_at_path(block, path, value)` | Dot-path mutation for update_block |
| `log_conversation(block, human, agent)` | Auto-log to §6 |
| `unfold(obj)` | Render pscale as readable text for LLM |
| `compile_system(block)` | System prompt: §1 + §2 + §4 |
| `compile_message(block, user_input)` | Message: §3 + human input + recent §6 |
| `a_loop(cfg, system, message, block)` | Tool chain until end_turn (max 20 turns) |
| `cycle(block, user_input)` | One B-loop: compile → A-loop → log → save |

### Context Window Compilation

**System prompt** (constitution — slow):
- unfold(§1): touchstone
- unfold(§2): operations
- unfold(§4): purpose (labeled YOUR PURPOSE)

**Message** (present moment — fast):
- CONCERN: unfold(§3)
- HUMAN INPUT: raw text
- RECENT CONVERSATION: last 3 from §6

---

## PCT Control Flow

```
Purpose (§4)           ← reference signal
     │
Concern (§3)           ← error = gap between is and should
     │
Can I close this gap in this A-loop?
     ├── Yes → chain tools, update_block('3', new state)
     └── No → decompose (§2.8), update_block('3', first part + sub-entries)
     │
Kernel saves + sleeps
     │
Next B-loop            ← new instance reads updated concern
```

---

## Test Results

### Phase A: First Wake (no purpose)
- Tool_use mechanics: PASS
- Without purpose, defaults to chatbot: EXPECTED (training fills vacuum)

### Phase B: Sustained B-loop (3 cycles, pre-restructure)
- Concern carries forward with concrete gaps: PASS
- Autonomous error handling (403 → alternative strategy): PASS
- Human as resource not command: PASS

### Phase C: A-loop Chaining (post-restructure)
- 4-step purpose completed in 1 cycle (8 tool calls): PASS
- All tool types work: PASS
- Conversation auto-logged: PASS

### Purpose Spindle Test (MAGI purpose, first wake)
- LLM identified stream 1 as immediate priority: PASS
- Built and deployed web interface in first cycle: PASS
- Concern narrowed from "no UI" to "UI exists, needs integration bridge": PASS
- Human treated as resource: PASS
- Streams 2-4 correctly deferred: PASS

---

## Deployment

```bash
python3 g0-kernel.py
# Prompts for API key on first run
# Terminal: type at prompt, quit/exit/q to stop
# Browser: open http://localhost:5000
```

---

## What Remains

- **Haiku testing**: Does the seed work on cheaper models? Critical for cost architecture.
- **Compaction under load**: §2.7 instructs compaction but untested at scale (needs 9+ entries).
- **Multi-cycle decomposition**: §2.8 untested with genuinely complex gaps.
- **Aperture control**: Full block in system prompt works at 6K. At 50K+ needs resolution selection.
- **VPS deployment**: Persistent process beyond David's laptop.
- **Multi-agent**: §7 available for SAND/relationship growth. Untested.
