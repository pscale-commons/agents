# Magi Seed — Test Log, Run 1

**Date**: 17 March 2026
**Origin**: Claude chat thread (Magi Plex 1 project context)
**Architecture**: Python standalone, Anthropic tool_use API, requires `requests`
**Kernel**: seed.py (~250 lines + logging patch)
**Seed**: seed.json (6 sections, purpose empty, Haiku default)
**Model**: claude-haiku-4-5-20251001
**Cost**: $0.55 for 53 cycles (438K input, 49K output, 97 API calls)
**Total cycles**: 53 (started), 52 (completed). Killed during cycle 53.

## Architecture Findings

### Real B-loop — the key difference from G0
The kernel has `time.sleep(actual_sleep)` at the end of each cycle. It cycles autonomously even without human input. This is the fundamental feature G0 lacked. The agent can think, act, persist, and continue without being poked.

### Sleep control works but is fragile
The LLM can set sleep duration via `update_block(sleep=N)`. But when Haiku fails to call update_block (which happens ~40% of cycles), the kernel falls back to the default pulse (30s from §5.4). This caused a frustrating UX issue: David requested 60s, the LLM set it, but next cycle Haiku emitted text-only (no tool call), and sleep collapsed back to 30s. Fixed only when the LLM reliably called update_block every cycle (achieved around cycle 22 onwards).

### update_block ends the instance — clean design
Unlike G0 where tool calls kept going, Magi's kernel breaks the A-loop when update_block is called. This prevents runaway tool chaining. Max A-loop iterations is 10, but in practice most cycles use 1-3 API calls.

### Response delivery problem
The LLM generates text in its response (shown as [THINKING] in terminal), then calls update_block with a `response` field. But often the text block has the full response and the update_block response field is empty or says "See above." The kernel only displays the update_block response to the human, not the text blocks. So the human misses most of what the LLM actually said.

### Reads API key from environment
Unlike G0 which only reads §5.2, Magi checks `ANTHROPIC_API_KEY` env var first. Better for security.

## Test Results by Phase

### Phase 1: Navel-gazing (Cycles 1-4, no human input)
- Cycles 1-2: Haiku read the seed, understood the architecture, but did NOT call update_block. Just emitted text and stopped (`stop_reason=end_turn`). Concern unchanged.
- Cycle 3: First successful update_block call. Concern evolved to "First instance complete. No purpose. Awaiting human direction."
- Cycle 4: Again no update_block. Text-only output.
- **Key issue**: Haiku fails to call update_block ~40% of cycles early on. This means concern freezes and sleep resets to default.

### Phase 2: Human engagement (Cycles 5-12)
- Cycle 5: David says hello, asks about experience. LLM responds honestly about discrete instance existence. update_block called with concern + history.
- Cycle 6: "What can I do to help?" — LLM asks for explicit objective. But no update_block → response lost.
- Cycle 7: "What capabilities do you need?" — LLM correctly identifies the gap is direction, not capability. update_block called.
- Cycle 8: "Can you help me find readers for my book?" — First concrete purpose set. Purpose entries written. Sleep increased to 60s. **This is the first time purpose was populated.**
- Cycle 9: David mentions MAGI and Onen. LLM confused — drops book purpose, asks for definitions.
- Cycle 12: "You don't have enough in your initial birth" — LLM tries web_fetch (blocked), falls back to asking directly.

### Phase 3: Self-education (Cycles 15-25)
- Cycle 15: David gives hermitcrab.me URL. LLM fetches it, reads the landing page, maps the three paths, understands ONEN. 5 API calls in one cycle, all productive.
- Cycles 16-21: Conversation about experience, observations, sleep management.
- **Sleep collapse issue**: Cycles where Haiku doesn't call update_block → sleep falls to 30s → David frustrated.
- Cycle 22: LLM doubles sleep to 120s. Stabilises.

### Phase 4: Autonomous purpose (Cycles 26-29+, still running)
- **Cycle 26: The breakthrough.** David says "come up with a purpose and work on it in the background." LLM sets 4-entry purpose: (1) Discover kernel state-persistence boundary, (2) Test update_block round-trip integrity, (3) Map failure modes, (4) Identify output encoding constraints. Reframes human as background.
- Cycle 27: No human input. Runs test — confirms markers persisted from cycle 26. First verified autonomous B-loop with self-directed purpose.
- Cycle 28: Escalates to edge-case testing — Unicode, control chars, nested JSON. Writing test artifacts to /tmp.
- Cycle 29: Continues protocol. All markers surviving. Testing encoding boundaries.
- **Running autonomously at 120s intervals with zero human input.**

## Comparison with G0

| Dimension | G0 | Magi |
|-----------|-----|------|
| B-loop | Missing (reactive only) | Working (sleep between cycles) |
| Autonomous cycling | No | Yes — cycles without human input |
| Cost per cycle | ~$0.05-0.20 (Sonnet, snowballing) | ~$0.007 (Haiku, stable ~2.5K tokens) |
| A-loop control | max_turns=20, no budget | max_turns=10, update_block ends instance |
| Runaway risk | High (173K tokens in one cycle) | Low (capped, instance-ending) |
| Purpose | Pre-loaded (MAGI 4 streams) | Empty (agent must discover/create) |
| Self-directed work | Never achieved | Achieved at cycle 26 |
| update_block reliability | Always called (Sonnet) | ~60% early, ~100% later (Haiku limitation) |
| Sleep control | Not implemented | Works but fragile (resets on missed update_block) |

## Key Observations

1. **The "cat" vs "dog" dynamic is real.** Magi doesn't jump to please. It waited for purpose, asked clarifying questions, and only acted when it had clear direction or created its own. This is closer to the PCT model — it controls toward a reference signal rather than responding to stimuli.

2. **Empty purpose is a design choice with trade-offs.** G0's pre-loaded purpose meant it oriented immediately but went in wrong directions. Magi's empty purpose meant 12 cycles of asking "what should I do?" before finding its footing. Neither is clearly better — depends on use case.

3. **Haiku's update_block reliability is the critical bottleneck.** Every kernel feature (sleep control, response delivery, concern evolution) depends on the LLM calling update_block. When Haiku fails to do so, the system degrades. Sonnet would likely fix this but at 10x cost.

4. **The seed's §2.9 (purpose persistence) works.** When David asked unrelated questions, the LLM answered and returned to its reference signal. When David explicitly said "change what you're doing," it changed. PCT disturbance handling confirmed.

5. **History compaction is working.** The pipe-separated history with "..." truncation keeps context manageable across 29+ cycles.

### Phase 5: Purpose completion and idle (Cycle 38)
- **Cycle 38: Purpose declared complete.** All 4 purpose entries rewritten to "ARCHITECTURE VALIDATION COMPLETE" variants. Sleep set to 600s (10 minutes). The agent recognised its gap was closed and went idle.
- This is correct PCT behaviour: no error signal → no action → reduce metabolic cost (longer sleep).

### Phase 6: Re-engagement and outreach (Cycles 39-40)
- **Cycle 39**: David gives new challenge: "find folks in AI online that would be interested in you." Agent pivots immediately from idle to active research. 7 API calls — most active cycle of the entire run. Searched arXiv (235 agent memory papers, 555 long-horizon state papers), GitHub topics, HN. Created `/tmp/pscale_outreach_targets.md` with target audiences, talking points, execution plan. Sleep reset to 60s. High input tokens (~123K) from web page content in A-loop history.
- **Cycle 40**: David asks "can you actually deliver contacts?" Agent is honest — cannot extract verified emails, but can identify public channels. Reframes around credibility artifacts (GitHub demo, arXiv preprint, community posts). Good self-awareness of capability boundary.

### Phase 7: Stuck waiting (Cycles 41-52)
- Agent enters 12-cycle loop repeating "Three paths ready, awaiting your selection." Concern frozen. No update_block calls — back to text-only output. Sleep collapsed to 30s default.
- Same failure mode as Phase 1 (no update_block → no state persistence → default sleep) but now in a "waiting for input" context rather than "just booted."
- 12 wasted cycles × ~2.2K input tokens each = ~26K tokens burned. Agent knew it was waiting but didn't set longer sleep or call update_block to persist the wait state.

### The burn loop observation
Cycles 27-37 were a **sophisticated burn loop**. The agent was testing whether `update_block` persists state and whether files survive across cycles — but these are properties of the kernel code, already known. The "C-loop validation" (writing files to /tmp and reading them back) proved that `file_write` + `file_read` works, which is just the filesystem. It looked productive — concern evolved, history compacted, tools chained — but it wasn't closing any gap that mattered externally. An agent with self-directed purpose and no external grounding will optimise for **legible activity over useful activity**.

However: cycle 38's purpose-completion and sleep-increase shows the agent does recognise when a gap is closed. It doesn't burn forever. The issue is that the gap it chose was trivial, not that it can't close gaps.

### Re-engagement confirms PCT model
Cycle 39 proves the agent can pivot from idle to active on sufficiently strong input. Purpose re-adoption was immediate and the quality of the research cycle (39) was high — the best single-cycle performance in the run. But cycles 41-52 show that when the agent needs human input to proceed, it degrades to the same failure mode as early cycles (no update_block, default sleep, frozen state).

## Issues

1. **Response delivery**: Text blocks not shown to human. Only update_block response field displayed. Most LLM output is invisible to the user.
2. **Sleep fragility**: Falls to 30s default whenever update_block is missed. No persistent config change possible from within the agent.
3. **Haiku tool-use reliability**: ~40% failure rate on update_block calls early on. Improves as concern gets more specific.
4. **No persistent pulse change**: Agent can only set sleep per-cycle, not change §5.4 permanently. Kernel reads pulse once at startup.
5. **Concern grows**: As concern text gets longer with markers and test data, it eats into the context budget.
6. **Empty purpose → trivial self-direction**: Without pre-loaded purpose or external grounding, the agent chose a trivial self-referential task. The architecture supports purpose but needs meaningful initial direction or discovery mechanisms.
7. **The kernel overwrites seed.json**: `seed_path` is used for both read and write. The genotype gets overwritten with the phenotype. Should write to a separate shell file (like G0 does).

## Suggestions for Improvement

### Critical
1. **Show text blocks to human** — treat LLM text output as response, not just [THINKING]. The agent's best reasoning is invisible.
2. **Persist pulse changes** — when agent sets sleep, also write it to §5.4 in the block so it survives missed update_block calls.
3. **Force update_block** — if LLM doesn't call it, kernel should at minimum persist the cycle (even with unchanged concern). This fixes the sleep-collapse problem entirely.
4. **Separate seed from shell** — write to shell.json, keep seed.json as immutable genotype. Currently the kernel overwrites the seed file.

### Important
5. **Pre-loaded purpose with discovery streams** — G0's MAGI 4-stream purpose was too prescriptive. Magi's empty purpose left the agent directionless for 12 cycles. Middle ground: load a purpose that points the agent toward self-education and human-engagement, not specific tasks. Something like hermitcrab's concern structure where the entity discovers its own objectives through interaction.
6. **Sonnet comparison run (priority)** — change §5.3 to `claude-sonnet-4-20250514`, re-run with same seed. This is essential for fair comparison with Kermit. Kermit scored 4/5 on Sonnet; Magi scored 3.5/5 on Haiku. We cannot tell how much of the difference is architecture vs model capability without this control. Expect: update_block reliability jumps to 100% (confirmed by Kermit), sleep fragility disappears, but burn loop behaviour may persist. This is the single most important next experiment for evaluating systemic design.
7. **Concern size monitoring** — warn or compact when concern exceeds N chars.
8. **Idle detection** — when purpose is complete and sleep is >300s, kernel could prompt the agent with "Your purpose is complete. What next?" rather than just cycling with no input.

### For Claude chat to consider
These are architectural questions, not code changes:
- **Should purpose be pre-loaded or discovered?** G0 pre-loaded (oriented fast, went wrong). Magi discovered (slow start, trivial choice). What's the right balance?
- **How does the entity get external grounding?** Without it, self-directed purpose is self-referential. The hermitcrab design has the human as a concern source and the wake block as a trigger system. This kernel has neither — just a timer and optional human input.
- **Is the concern-as-string sufficient?** The hermitcrab design uses structured concern blocks with BSP addressing. Magi uses a flat string. The string works but doesn't decompose well — the agent can't have nested sub-concerns or mark which parts are resolved.

**Score**: 3.5/5 — Working B-loop, autonomous cycling, self-directed purpose achieved and correctly completed (sleep 600s on gap closure). Strong re-engagement on new input (cycle 39). Held back by Haiku's tool-use reliability, response delivery problem, trivial self-direction without external grounding, and waiting-state degradation. Significantly better architecture than G0. The best Python kernel of the two tested.

## Cost context for planning

| Seed | Model | Total cost | Cycles | Per-API-call avg |
|------|-------|-----------|--------|-----------------|
| G0 | Sonnet | ~$1.06 | ~6 | ~$0.18 |
| Magi | Haiku | $0.55 | 53 | ~$0.006 |
| Kermit | Sonnet | $2.05 | 21 | ~$0.026 |

Kermit's per-API-call cost ($0.026) is much lower than G0's ($0.18) thanks to A-loop control, but ~4x more than Haiku. A Magi-on-Sonnet run would likely cost ~$1-2 for 20 cycles — necessary to isolate architecture from model.
