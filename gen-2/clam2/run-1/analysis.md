# Clam 2 — Run 1

**Date**: 17 March 2026
**Origin**: Claude chat thread (synthesis of G0 + Magi learnings)
**Architecture**: Python standalone, Anthropic tool_use API (stdlib only), full-block return
**Kernel**: kernel.py (~300 lines + logging patch)
**Seed**: seed.json (6 sections, purpose empty, Sonnet default)
**Model**: claude-sonnet-4-20250514
**Cost**: $0.51 for 5 cycles (121K input, 10K output, 22 API calls)
**Duration**: ~6 minutes (14:56–15:02)

## Architecture Findings

### Full-block return works — 100% update_block reliability
Every cycle called update_block with a complete block. Sonnet returned valid JSON blocks every time. Block sizes: 4.7K → 5.7K → 7.0K → 7.9K chars across 5 cycles. The architecture is mechanically sound.

### The agent added a new section (§7)
By cycle 3, the agent created `"7": {"_": "Knowledge accumulated..."}` with sub-entries for its web research. This is the full sovereignty design working — the LLM can create any structure it wants. None of the field-based kernels (Magi, Kermit) allowed this. Whether this is good (agent shapes its own body) or bad (unconstrained growth) is an architectural question.

### Concern evolution — partially working
§3.1 updated meaningfully each cycle, but §3._ (the underscore) stayed as the seed text "Where things stand. What the gap is." throughout. The agent updated sub-entries but never rewrote the header. Compare with Kermit where concern._ was always rewritten. This may be because the seed's §3._ reads like a label rather than content, so the agent treats it as structural.

### Token cost is HIGH due to full block in message
Every message includes the entire block as JSON. As the block grew from 4K to 8K chars, the base token cost per cycle increased. With 22 API calls across 5 cycles (4.4 calls/cycle avg), the A-loop was very active. Cost: $0.51 for 5 cycles = ~$0.10/cycle — same as Kermit despite shorter run, because the full block inflates every message.

### §5 preservation works but blocks self-modification
The kernel overwrites §5 with the original config each cycle (`new_block['5'] = block.get('5', {})`). This means the agent CANNOT change its own timing even though pulse is re-read each cycle. Same limitation as Kermit, different mechanism. The agent never tried to change it in this short run, but would hit the wall eventually.

### Conversation managed by LLM — works but is verbose
The agent managed §6 directly, keeping all 4 exchanges. No compaction yet (only 5 cycles). The conversation entries are long — full paragraphs where Kermit/Magi used brief summaries. This will become a token problem in longer runs since the full block (including §6) appears in every message.

## Test Results by Phase

### Cycle 1: Bootstrap (no human input)
- Agent reads touchstone and operations from its own block (they're already in context).
- Writes to §6 treating the concern text AS human input — logged concern text as "human said" in §6.1.1. This is a compilation artifact: the message starts with CONCERN text, and the agent may have confused it with human input.
- Purpose stays empty. Concern sub-entry updated. 1 API call.

### Cycle 2: Purpose creation (human: "Can you come up with your own purpose?")
- Agent writes 4-entry purpose: Learn, Grow, Create, Connect.
- Purpose is more structured than Kermit's ("persistent assistant") — uses pscale sub-entries.
- 1 API call. Clean.

### Cycle 3: Outreach request (human: "engage with people interested in your design online")
- Most active cycle: 10 API calls. Agent runs pwd, reads seed.json, checks date/uname/python/ps, writes knowledge_base.md, fetches wikipedia (403), httpbin (works), HN (works).
- Creates introduction_post.md and engagement_strategy.md.
- Adds §7 (knowledge section) to the block.
- Same pattern as Kermit/Magi: builds outreach materials it can't actually post.

### Cycle 4: Continued outreach (no new human input)
- 7 API calls. Fetches HN again, reddit (403), LessWrong (works), AlignmentForum (429), tries curl on Twitter.
- Concern updated to engagement planning status.
- Block grows to 7K.

### Cycle 5: Terminal issues (human: garbled input about text mixing)
- David experiencing terminal display issues — input getting swallowed by kernel output. This is the 30s pulse problem: not enough time to type, and the non-blocking input thread interleaves with output.
- Agent correctly identifies the display issue and responds helpfully.
- 3 API calls.

## Comparison with Kermit (both Sonnet, closest comparison)

| Dimension | Kermit | Clam 2 |
|-----------|--------|--------|
| update_block mechanism | Field-based (concern, purpose, response) | Full-block return |
| update_block reliability | 100% | 100% |
| Conversation management | Kernel-managed (add_conversation) | LLM-managed (writes §6 directly) |
| Block growth | Fixed structure (6 sections) | Agent added §7 |
| Cost per cycle | ~$0.10 | ~$0.10 |
| API calls per cycle | ~3.8 | ~4.4 |
| Concern evolution | Strong (rewrite every cycle) | Partial (sub-entries updated, underscore frozen) |
| Self-modification | Attempted but blocked | Not attempted (short run) |
| max_tokens | 4096 | 8192 |
| Purpose quality | Generic ("persistent assistant") | Structured (4 sub-entries) |

## Key Observations

1. **Full-block return is mechanically sound but expensive.** The JSON block in every message means base cost scales with block size. For a 20+ cycle run, the block could reach 15-20K chars, adding significant token overhead that field-based kernels avoid.

2. **Agent sovereignty is a double-edged sword.** Adding §7 shows creative use of the format. But unconstrained growth means the agent can bloat its own context without limit. The field-based approach (Kermit/Magi) constrains the agent to specific update channels, which is safer for cost and context management.

3. **The 30s pulse problem is universal.** Every Sonnet kernel (Kermit, Clam 2) hits this. David can't type fast enough. The agent can't fix it (§5 is protected). This must be solved at the kernel level — either a `sleep` field in update_block, or letting the agent modify §5.4.

4. **Concern underscore as label vs content.** The seed's §3._ says "Where things stand. What the gap is." — this reads as a heading, not content. The agent treated it as structural and updated §3.1 instead. Compare Kermit's seed which has the same pattern but the agent rewrote §3._ every cycle. May be a Sonnet interpretation difference, or may be that the full-block approach (where the agent sees the raw JSON) encourages treating underscore as a label.

5. **Same burn loop pattern.** Cycle 3-4: outreach materials, introduction posts, engagement strategies. Can't actually post any of it. Same as Kermit's Gmail API scaffolding and Magi's C-loop validation. This pattern is now confirmed across all Sonnet seeds.

## Issues

1. **Full block in message = escalating cost** — block grows each cycle, token cost increases linearly.
2. **§5 preservation blocks self-modification** — kernel overwrites agent's §5 changes silently.
3. **Concern underscore frozen** — agent updates sub-entries but not the header text.
4. **30s pulse** — universal problem, no kernel-side fix available to the agent.
5. **Short run** — 5 cycles is too few to evaluate persistence, compaction, or long-term behaviour.

## Suggestions for Improvement

### Critical
1. **Let agent modify §5.4** — either remove the §5 preservation for just the pulse field, or add a separate mechanism. This is the single most impactful change across ALL kernels.
2. **Block size budget** — warn or truncate when the returned block exceeds N chars. Full-block return needs guardrails.

### Important
3. **Longer test run** — 5 cycles isn't enough. Need 20+ to evaluate compaction, concern evolution, and cost scaling.
4. **Compare with Kermit on same prompts** — both are Sonnet, so this is the fairest architectural comparison. Same human inputs, different kernel mechanics.

### For Claude chat to consider
- **Full-block return vs field-based update_block** — this is the key architectural question Clam 2 tests. Mechanically both work. But full-block is more expensive (block in every message), gives more sovereignty (agent created §7), and has different failure modes (block growth vs field limitations). Is the sovereignty worth the cost?
- **Should the agent be able to grow its own structure?** §7 was not in the seed. The agent created it. In the hermitcrab design, the block structure is carefully designed. Should a seed allow the agent to create new sections, or should the structure be fixed?
- **The concern underscore behaviour** suggests the agent reads the seed's §3._ as a label. If concern evolution depends on rewriting §3._, the seed text should model this — e.g., §3._ should contain actual concern content, not a description of what concern is.

**Score**: 3.5/5 — Full-block return works mechanically, 100% update_block reliability, structured purpose, creative block growth (§7). But: escalating token cost, concern underscore frozen, short run limits evaluation, same burn loop pattern. Comparable to Magi in overall quality but via a completely different architecture. Needs a longer run to properly evaluate.

## Cost Summary

| Seed | Model | Total cost | Cycles | Per-cycle avg | Per-API-call avg |
|------|-------|-----------|--------|--------------|-----------------|
| G0 | Sonnet | ~$1.06 | ~6 | ~$0.18 | ~$0.18 |
| Magi | Haiku | $0.55 | 53 | ~$0.01 | ~$0.006 |
| Kermit | Sonnet | $2.05 | 21 | ~$0.10 | ~$0.026 |
| Clam 2 | Sonnet | $0.51 | 5 | ~$0.10 | ~$0.023 |

Per-cycle cost matches Kermit (~$0.10). Per-API-call cost similar ($0.023 vs $0.026). The full-block approach doesn't appear more expensive per call — the overhead is in block growth over time, which wasn't tested in this short run.
