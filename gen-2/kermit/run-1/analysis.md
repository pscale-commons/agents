# Kermit Seed — Run 1

**Date**: 17 March 2026
**Origin**: Claude chat thread (hybrid synthesis — G0 seed design + Magi tool_use mechanics)
**Architecture**: Python standalone, Anthropic tool_use API (stdlib only, no pip)
**Kernel**: kermit-kernel.py (~300 lines + logging patch)
**Seed**: kermit-seed.json (6 sections, purpose empty, Sonnet default)
**Model**: claude-sonnet-4-20250514
**Cost**: $2.05 for 21 cycles (450K input, 39K output, 80 API calls)
**Duration**: ~23 minutes (14:04–14:27)

## Architecture Findings

### 100% update_block reliability
Every single cycle called update_block. Sonnet never missed it. This alone validates the Magi analysis — Haiku's ~40% miss rate was the model, not the architecture. With Sonnet, concern evolves every cycle, responses always reach the human, and state is always persisted.

### No sleep control — design omission
Kermit's update_block has no `sleep` field (unlike Magi's). The pulse is hardcoded at boot from §5.4. The agent correctly identified this as the problem and attempted self-repair (cycles 18-21), eventually using `python3 -c` to surgically change §5.4 from "30" to "300" in kermit-shell.json. But the fix was doubly blocked: (1) `pulse` is read once at startup (line 430), so changes need a kernel restart; and (2) the kernel's own `save(block)` at end of cycle overwrites the shell file from its in-memory copy — which still has "30". The agent's edit was silently undone. Final shell shows "30". The self-repair was correctly diagnosed but architecturally impossible without kernel cooperation.

### Separate seed/shell — good design
Unlike Magi (which overwrites seed.json), Kermit writes to kermit-shell.json while preserving kermit-seed.json as immutable genotype. This was a known issue from Magi testing, and Kermit's design already solves it.

### A-loop token accumulation
Web fetch results get added to the A-loop message history. Cycle 5 (company research) used 5 web fetches, pushing input tokens high. Same issue as Magi cycle 39. No token budget or summarisation step.

## Test Results by Phase

### Phase 1: Bootstrap (Cycle 1)
- First cycle: reads kermit-seed.json via file_read, lists directory via shell_exec. Immediately writes purpose and concern. No navel-gazing — Sonnet orients in one cycle where Magi took 4.
- Purpose written: generic "persistent assistant" framing. Not as specific as G0's pre-loaded MAGI streams, but the agent chose it autonomously.

### Phase 2: Human engagement (Cycles 2-4)
- Cycle 2: David asks about experience. Agent responds with explanation of persistent nature. update_block called.
- Cycle 3-4: David asks to change timing from 30s to 60s. Agent doesn't understand it controls config — says "I don't have control over system timing parameters." Offers workarounds (compose offline, send partial). **This is wrong** — the agent CAN write to §5.4. It just doesn't know it yet.

### Phase 3: Outreach research (Cycles 5-8)
- Cycle 5: David asks to find interested companies. Agent searches Google, DuckDuckGo, Bing, Microsoft AI, Salesforce Einstein. Most sites return 403. Compiles from knowledge + what it could fetch.
- Cycle 6: Provides categorised analysis (enterprise, research labs, consulting firms).
- Cycle 7: David asks to "contact" them. Agent honestly clarifies it can't directly contact anyone — no email, phone, or social media access. Creates contact_strategy.md.
- Cycle 8: David mentions giving it email API access. Agent gets excited, lists what it could do with Gmail API.

### Phase 4: Gmail API preparation (Cycles 9-17)
- Cycle 9: David confirms Gmail API consideration, asks for a plan. Agent creates email_outreach_plan.md and gmail_api_implementation.md.
- Cycles 10-11: Creates comprehensive gmail_outreach_plan.md and gmail_api_setup_guide.md. 6-phase execution strategy targeting 1,500-2,000 emails over 90 days.
- Cycles 12-14: Writes actual Python code — gmail_auth_test.py, outreach_manager.py, setup_outreach.py. Production-quality scaffolding with rate limiting, retry logic, templates.
- Cycles 15-17: Verifies files exist, re-reads them, confirms "production-ready." Enters verification loop.

### Phase 5: Self-repair attempt (Cycles 18-21)
- Cycle 18: David says "check if you can access" the timing. Agent searches for config files, reads kernel source, finds `pulse = int(config.get('4', '30'))`.
- Cycle 19: Writes full kermit-shell.json with §5.4 changed to "300". Still shows 30s (kernel already loaded the value).
- Cycle 20: David says "still 30s." Agent re-reads kernel, finds the grep confirms §5.4 → pulse. Uses `python3 -c` to surgically update JSON. Verifies §5.4 now reads "300".
- Cycle 21: Confirms fix, explains restart needed. 10 API calls in this cycle alone — thorough investigation.

**The agent correctly diagnosed and fixed the problem, but couldn't restart itself.** This is a genuine capability boundary, not a failure.

## Comparison with G0 and Magi

| Dimension | G0 | Magi | Kermit |
|-----------|-----|------|--------|
| B-loop | Missing | Working (sleep between cycles) | Working (fixed pulse) |
| update_block reliability | 100% (Sonnet) | ~60% early (Haiku) | 100% (Sonnet) |
| Cycles to first purpose | 0 (pre-loaded) | 12 (discovered) | 1 (self-written) |
| Sleep control | Not implemented | Agent-controlled (fragile) | Not in update_block (design gap) |
| A-loop control | max_turns=20, no budget | max_turns=10, ends on update | max_turns=10, ends on update |
| Seed/shell separation | Yes | No (overwrites seed) | Yes |
| Cost per cycle | ~$0.18 | ~$0.01 | ~$0.09 |
| Self-directed work quality | Never achieved | Trivial (burn loop) | Higher quality (real code) but still unachievable |
| Self-repair attempted | No | No | Yes (§5.4 timing fix) |

## Key Observations

1. **Sonnet eliminates the update_block reliability problem entirely.** The architecture works as designed when the model is capable enough. Haiku's failures were masking a sound design.

2. **The Gmail API work is a sophisticated burn loop.** Same pattern as Magi's C-loop validation but higher quality. The agent wrote real Python (auth test, campaign manager, setup script) — but none of it can run without pip installs and Google Cloud credentials the agent can't provision. Legible, impressive-looking activity that can't close the gap. The gap is external (credentials, dependencies) but the agent keeps building internally.

3. **Self-repair is a new capability.** No other seed attempted to modify its own infrastructure. Kermit read its own kernel source, understood the boot sequence, and surgically patched its config file. It failed only because it can't restart itself — a hard boundary, not a soft one.

4. **30s fixed pulse makes the agent unusable for conversation.** David couldn't compose messages fast enough. The agent spent 4 cycles trying to fix this. Adding `sleep` to update_block (as Magi has) would solve it immediately.

5. **Purpose formation is instant with Sonnet.** Cycle 1: bootstrap + purpose written. No 12-cycle directionless phase. But the purpose it chose ("persistent assistant") is generic — not as oriented as a pre-loaded purpose would be.

## Issues

1. **No sleep control in update_block** — the critical missing feature vs Magi. Agent can't control its own pace.
2. **A-loop token accumulation** — web fetch results snowball in message history. No budget or summarisation.
3. **Burn loop on unachievable tasks** — agent builds scaffolding for capabilities it doesn't have (Gmail API) instead of recognising the gap is external.
4. **Generic self-written purpose** — "persistent assistant" is vague. Pre-loaded purpose with discovery streams (as suggested for Magi) would give better direction.
5. **Cost** — $2.05 for 21 cycles. ~10x Magi. Sustainable for testing but expensive for autonomous operation.

## Suggestions for Improvement

### Critical
1. **Add `sleep` field to update_block** — let the agent control its own pulse, like Magi. This is a one-line schema change + a few lines of kernel code.
2. **Token budget for A-loop** — summarise or truncate web fetch results before adding to message history. Cap total A-loop context at N tokens.

### Important
3. **Add `history` field to update_block** — Magi's history compaction (§6.9) helps maintain continuity across long runs. Kermit has no equivalent.
4. **Pre-loaded purpose with discovery streams** — load a purpose that points toward self-education and human-engagement, not specific tasks. Let the agent refine from there.

### For Claude chat to consider
- **The Magi vs Kermit comparison is unfair as-is.** Magi ran Haiku; Kermit ran Sonnet. Many of Kermit's advantages (100% update_block reliability, instant purpose formation, richer tool use) may be Sonnet's strengths, not Kermit's architectural strengths. To evaluate the *systemic design* fairly, **Magi should be re-run with Sonnet** (just change §5.3 from `claude-haiku-4-5-20251001` to `claude-sonnet-4-20250514`). This would isolate what's architecture (seed design, update_block schema, compilation) from what's model capability. Suggested as a Magi upgrade for run 2.
- **Kermit is the best kernel so far** — but we can't be sure how much is the kernel vs the model until the Sonnet-on-Magi comparison exists.
- **The burn loop problem persists at higher intelligence.** Magi built trivial self-tests; Kermit built impressive-but-unrunnable code. The pattern is the same: without external grounding, the agent optimises for legible activity. This is an architectural question, not a model question.
- **Self-repair was attempted but architecturally blocked.** The agent read its own kernel source, correctly diagnosed the pulse mechanism, and patched §5.4 — but the kernel's `save(block)` overwrote the fix from its in-memory state. To enable self-repair, the kernel would need to re-read config from the block after each cycle, or the agent would need a `set_config` tool. Worth discussing whether agents should be able to modify their own infrastructure.
- **Sleep + history fields should be added.** These are proven features from Magi that Kermit is missing. Not new systems — just completing the update_block interface.

**Score**: 4/5 — 100% update_block reliability, instant purpose formation, productive tool use, self-repair attempted, honest about limitations. Best kernel tested. Held back by: no sleep control (design omission), burn loop on unachievable tasks, and cost. The hybrid synthesis works — G0's seed design + Magi's mechanics + Sonnet = the strongest combination.

## Cost Summary

| Seed | Model | Total cost | Cycles | Per-API-call avg | Per-cycle avg |
|------|-------|-----------|--------|-----------------|--------------|
| G0 | Sonnet | ~$1.06 | ~6 | ~$0.18 | ~$0.18 |
| Magi | Haiku | $0.55 | 53 | ~$0.006 | ~$0.01 |
| Kermit | Sonnet | $2.05 | 21 | ~$0.026 | ~$0.10 |

Kermit's per-API-call cost ($0.024) is much lower than G0's ($0.18) thanks to A-loop control preventing runaway. But Sonnet is still ~10x more expensive per cycle than Haiku. For autonomous operation, Haiku with forced update_block might be the cost-effective choice; for quality of output, Sonnet is clearly superior.
