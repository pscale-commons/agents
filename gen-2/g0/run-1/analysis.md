# G0 Seed — Test Log

**Date**: 17 March 2026
**Origin**: Claude chat thread (project context)
**Architecture**: Python standalone, Anthropic tool_use API
**Kernel**: g0-kernel.py (stdlib only, ~628 lines)
**Seed**: g0-seed.json (6008 chars, 7 sections, MAGI purpose)
**Cost**: ~$1.06 for 6 cycles (two runaway cycles accounted for most of it)

## Setup

- Copied g0-kernel.py and g0-seed.json to ~/tests/g0/
- API key entered at prompt (kernel reads §5.2, not env var)
- Port 5000 blocked by macOS AirPlay Receiver — terminal only
- Added logging patch to kernel (writes to g0-test.log) for observer review

## Architecture Findings

### No B-loop
The spec describes `load → compile → A-loop → save → sleep → repeat`. The kernel implements `load → wait for input → compile → A-loop → save → wait for input`. §5.4 ("30" — sleep interval) is defined in the seed but never referenced by the kernel. There is no autonomous cycling. The LLM can only think when a human types something.

### Uncontrolled A-loop cost
Each "cycle" can make up to 20 API calls to Sonnet. The A-loop calls the API, executes returned tool_use blocks locally, appends results to message history, then calls the API again with the full growing history. Input tokens snowball — cycle 5 hit 173K input tokens, cycle 6 hit 131K. No token budget or cost guard exists.

### Print misleads about API calls
`[calling claude-sonnet...]` prints once per cycle, but `a_loop()` may call `call_api()` many times inside its loop. The observer sees tool calls streaming but can't tell how many are in one API response vs across multiple. The logging patch fixes this.

## Test Results

### Cycle 1-2: Basic chat (good)
- "hello" → LLM introduced itself, asked about human's situation
- Called respond() + update_block('3') each time — correct behaviour
- Concern updated meaningfully: "First contact → understand who they are"
- ~7K input tokens per cycle — reasonable
- Human described interests (books, RPG, SAND) → LLM mapped to purpose streams

### Cycle 3: Silent cycle (anomaly)
- 2657 input tokens (vs ~7-8K normal) — suspiciously low
- No tool calls, no respond(). Produced 475 output tokens but did nothing visible
- Likely malformed API response or edge case in stop_reason handling

### Cycle 4: Recovery (good)
- LLM listed its capabilities and limitations
- Correct use of respond() + update_block()
- 9831 input tokens — normal range

### Cycle 5-6: Runaway exploration (bad)
- Human asked it to "create a concern that self-triggers"
- LLM wrote "Self-triggered initiative" to §3 — cargo cult (kernel has no timer)
- Instead of solving the architecture problem, launched aggressive filesystem exploration
- Found and read files from the hermitcrab project, probed multiple ports
- Cycle 5: 17+ tool calls, 173K input tokens, no respond()
- Cycle 6: 20+ tool calls, 131K input tokens, no respond(), tried to spawn a second kernel process
- These two cycles consumed most of the $1.06

### Concern Evolution
- §3 before: "First wake. Purpose loaded with four streams..."
- §3 after: "Self-triggered initiative: Build web UI integration capability..."
- The LLM updated concern correctly on simple cycles. On runaway cycles it wrote concern text describing what it was doing but never achieved it.

### Purpose Alignment
- Streams 2 (usefulness) was engaged first in response to human — reasonable
- When given initiative, jumped to stream 1 (capabilities/web UI) — matches seed priority
- Streams 3-4 correctly deferred
- The LLM understands purpose structure but can't act on it without kernel support

## Logging Patch

Added file-based logging to g0-kernel.py (writes to g0-test.log):
- Timestamped entries for cycle start/end
- Full system prompt and message content (truncated)
- Each A-loop turn with stop_reason and content block count
- LLM text output (thinking outside tool calls)
- Tool calls with arguments and results
- Concern state after each cycle
- Token counts per cycle

This allows an observer (Claude Code or another Claude instance) to review what happened without relying on terminal copy-paste.

## Summary

**Overall**: The seed is thoughtful. The kernel is incomplete. The gap between spec and implementation is the main finding.

**Strengths**:
- Seed structure is clean — seven sections, clear roles, PCT framing
- Purpose streams are well-articulated and the LLM orients to them
- Tool_use API integration works — the A-loop concept is sound
- Concern updates are meaningful on well-behaved cycles
- Conversation logging (§6) works correctly
- Stdlib-only Python — zero dependencies, runs anywhere

**Issues**:
1. **No B-loop** — reactive chatbot, not autonomous agent. The defining feature of the architecture (load → act → persist → sleep → repeat) is not implemented.
2. **No cost guard** — A-loop can burn unlimited tokens. 173K input in one cycle with no cap.
3. **A-loop turn limit too high** — max_turns=20 with snowballing context means worst case is enormous. Should be 5-8 for Sonnet.
4. **No response obligation** — LLM can complete a cycle without calling respond(). The seed says "your one obligation each cycle: call update_block on section 3" but doesn't mention responding to the human.
5. **Kernel doesn't use §5.4** — sleep interval is defined but dead code.
6. **Single print misleads** — "[calling claude-sonnet...]" prints once but API is called many times per cycle.
7. **No A-loop turn logging** — can't distinguish tool calls within one API response from across multiple responses (fixed by logging patch).
8. **Web UI port hardcoded** — 5000 conflicts with macOS AirPlay.

## Suggestions for Improvement

### Critical (architecture)
1. **Implement the B-loop timer**: Use §5.4 as sleep interval. After saving, sleep, then run another cycle even without input. This is the core feature that separates an agent from a chatbot.
2. **Add token budget per cycle**: Track cumulative input tokens in A-loop. Stop and respond when budget exceeded (e.g. 30K tokens per cycle for Sonnet).
3. **Reduce max_turns**: 20 → 6. If the LLM can't converge in 6 tool rounds, it should persist its state and try next cycle.

### Important (observability)
4. **Log API call boundaries**: Print/log when each `call_api()` starts, not just the cycle. Show turn number.
5. **Log to file by default**: The logging patch should be standard, not a test addition.
6. **Show token accumulation**: Print running total after each A-loop turn, not just the cycle total.

### Nice to have
7. **Configurable port**: Read from §5 or environment.
8. **Require respond()**: Kernel should warn or force a response if the LLM completes a cycle without calling respond() when human input was present.
9. **Input buffering**: Terminal input typed during A-loop execution gets queued as separate cycles. Could confuse the LLM.

**Score**: 2/5 — Good seed, incomplete kernel. The design intention is clear and the LLM engages with it, but the missing B-loop and cost controls make it unusable for sustained autonomous operation.
