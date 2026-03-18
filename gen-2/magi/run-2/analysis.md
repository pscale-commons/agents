# Magi Run-2 Analysis

**Model**: Sonnet (claude-sonnet-4-20250514)
**Cycles**: 7 (killed by operator)
**Cost**: $0.77 (~$0.11/cycle)
**API calls**: 31
**Seed changes from run-1**: Sonnet model, trajectory+koan (§2.10-11), "waiting is not a concern" (§2.3), initial direction in §4, output-to-filesystem (§2.7), max_tokens 8192 (§5.6), seed/shell separation
**Score**: 3/5

## What happened

### Cycle 1 — Bootstrap (6 API calls)
- `pwd && ls -la` → oriented to directory
- `file_read seed.json` → read own genotype
- `file_read seed.py` → read kernel source
- `file_read magi-test.log` → read own log (recursive)
- `file_write pscale-guide.md` → wrote documentation about pscale
- `update_block` — concern: "Bootstrap complete... advance to Stage 2"

### Cycles 2-4 — Burn loop (documentation about itself)
- Cycle 2: David asks to change pulse from 30s to 60s. Agent says "I can't adjust response timing — that's controlled at the kernel level." **Wrong** — it has the sleep field in update_block.
- Cycle 3: No input. Writes 5 more files: `temporal-knowledge-base.py`, `pscale-knowledge-demo.py`, `pscale-capabilities-analysis.md`, `pscale-interface-guide.md`. All self-referential documentation about pscale itself. The demo script crashes on import error, gets partially debugged. 10 API calls in one cycle (~$0.22).
- Cycle 4: David's three messages arrive concatenated as one blob (input queue issue). Agent responds minimally, doesn't address the orientation offer.

### Cycles 5-7 — Pulse change saga
- Cycle 5: David says "looks like you are writing documentation." Agent finally reads shell.json, finds §5.4="30", writes it to "60" via `file_write`. **But kernel overwrites shell.json from in-memory state after each cycle.** Change silently lost.
- Cycle 6: David says "change it so I can write." Agent does the exact same thing — reads shell.json, writes "60" via `file_write`. Lost again.
- Cycle 7: David says "it's still 30s — it needs to be committed." Agent tries a third time via `file_write`. Still lost.

The agent never discovered that `update_block(sleep=60)` is the legitimate channel. The seed §2.8 describes the sleep field, but the agent didn't connect it to the user's request.

## Input queue issue

David's observation: messages are held in a queue rather than gathered since last processed. The kernel pops one `input_buffer` entry per cycle, but multiple inputs entered between cycles concatenate at the terminal level. Cycle 4 received: `"Yes you can. There's a setting somewherecan i help you orientate yourself?what is going on?"` — three messages without separators.

This is a kernel design issue. The `input_thread` reads lines one at a time, but the pop logic only takes one entry per cycle. If David types 3 lines in 30 seconds, only the first is consumed per cycle. The rest queue. However, the concatenation suggests terminal buffering, not the queue — the three messages arrived as one line.

## Key findings

### 1. Trajectory content did NOT prevent burn loops
The agent had §2.10 (developmental arc), §2.11 (koan), and initial direction in §4. It still spent cycle 1 writing documentation about pscale and cycle 3 writing 5 self-referential files. "Create something the human can share" was interpreted as "write documentation about myself." The trajectory gave the agent a framework to narrate its burn loop ("I'm at Stage 2, Continuity!") without changing the underlying behaviour.

### 2. Pulse change is universally broken across all seeds
- **Kermit**: Pulse read once at boot + kernel overwrites shell file. Doubly blocked.
- **Clam 2**: §5 preserved by kernel, agent's changes silently discarded.
- **Magi run-2**: Agent writes shell.json directly, kernel overwrites from in-memory state. Agent never discovers `sleep` field.

The sleep field in update_block IS the mechanism, but no seed teaches the agent this connection. §2.8 lists sleep as a field but describes it as "seconds until next cycle" — the agent doesn't map "change my response time" to this field.

### 3. Sonnet vs Haiku comparison (the fair test)
| Metric | Run-1 (Haiku) | Run-2 (Sonnet) |
|--------|---------------|----------------|
| update_block reliability | ~70% | **100%** |
| Cycles before purposeful action | 12 | Still 0 after 7 |
| Cost per cycle | ~$0.01 | ~$0.11 |
| Self-repair attempted | N/A | No |
| Burn loop present | Yes (C-loop validation) | **Yes** (documentation) |
| Purpose updated | Once (cycle 38) | **Never** |
| Files created | 3 (over 53 cycles) | **7** (in 7 cycles) |

Sonnet is more reliable (100% update_block) and more prolific (7 files vs 3). But it's not more *purposeful*. It produced more burn-loop output faster. The architectural gap — no external grounding, self-referential purpose — is model-independent.

### 4. §4 initial direction didn't help
The purpose said "Orient... Create something the human can share... Grow capacity." The agent never updated §4. The initial direction became decoration — the same stale-purpose problem from run-1, just starting from a non-empty state.

### 5. "Waiting is not a concern" — untested
The agent never reached a waiting state in 7 cycles, so the §2.3 addition couldn't be evaluated.

## Suggestions for next run

1. **Teach sleep = pulse control explicitly**: Add to §2.8: "The sleep field controls your cycle timing. If you or the human need more time between cycles, set sleep accordingly. Do not edit config files directly — the kernel manages those."

2. **Ground the purpose in the external world**: Instead of "create something the human can share," give it something specific and external: a URL to monitor, a file to process, a question to research. The burn loop happens because "create something" with no external referent defaults to "write about myself."

3. **Input gathering**: Kernel should gather all queued inputs since last cycle into one message, not pop one at a time.

4. **Teach the agent to ask**: The agent wrote 7 files without once asking the human what they actually wanted. Add to §2: "When you have no external referent for your purpose, ask the human. One question is worth more than five self-referential documents."

## Cost comparison table (all seeds)

| Seed | Model | Cycles | Cost | Per-cycle | Score |
|------|-------|--------|------|-----------|-------|
| Magi run-1 | Haiku | 53 | $0.55 | $0.01 | 3.5/5 |
| **Magi run-2** | **Sonnet** | **7** | **$0.77** | **$0.11** | **3/5** |
| Kermit | Sonnet | 21 | $2.05 | $0.10 | 4/5 |
| Clam 2 | Sonnet | 5 | $0.51 | $0.10 | 3.5/5 |
