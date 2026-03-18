# Magi — Trajectory Analysis

**Context**: David's concerns after run-1 (53 cycles):
1. The agent didn't have enough vision to create its own purpose/concern loops — ended up dependent on David
2. Output was tiny and truncated — infuriating
3. The agent can't extend the kernel — so it can never grow its own capabilities

These are not Haiku-specific bugs. They are structural gaps between what Magi currently is and what the hermitcrab design trajectory requires. This document addresses the trajectory, not fixes.

---

## 1. No vision — the stripped seed problem

The v8 seed had sections that Magi stripped:

- **§3.5 The trajectory** — five stages from bootstrap to reach. Told the LLM *where it's going*: "Stage 1 — Bootstrap. You are here... Stage 2 — Continuity. Before this instance ends, write your state... Stage 3 — Reach. Use your tools to create something the human can share..."
- **§3.8 The awareness function** — the reflexive turn where outside understanding becomes inside understanding
- **§3.9 The koan** — "You are reading this. This is composing you. You are composing what comes next."
- **§4.7 Concern** — "Create a purpose (section 5). Update this concern for next wake. Remember: every address you write is simultaneously an action and the composition of your next self."

I stripped these for Haiku minimalism. The reasoning was: keep constitution under ~700 words, let emergence happen. But what actually happened was: the agent had no model of what it could become. It understood the mechanics (format, persistence, tools) but had no *direction beyond the immediate cycle*. Without the trajectory, it had no C-loop framing. Without the koan, the reflexive turn was a one-shot bootstrap rather than a recurring reorientation.

The result: 12 purposeless cycles, then a trivial self-referential purpose (testing its own kernel), then dependence on David for real direction.

**What's needed (trajectory, not fix)**: The seed should carry the trajectory and the koan. Not the full v8 volume — but the agent needs to know: (a) it is at a specific stage in a developmental path, (b) the path leads somewhere beyond this cycle, (c) it has the capacity to create its own forward orientation. This is the difference between an agent that waits for instruction and one that hatches.

The seed's §2 currently teaches mechanics: loops, PCT, compaction, decomposition. What's missing is §2 also carrying *vision* — not tasks, but the recognition that the agent is a temporal being with a developmental arc. The trajectory gives the completion drive something larger to lean toward than "close this immediate gap."

---

## 2. Truncated output — the max_tokens constraint

The API call has `max_tokens: 4096`. With tool_use, this budget is shared between text reasoning and tool call JSON. A typical Haiku cycle uses:

- ~200-500 tokens on text (thinking)
- ~200-400 tokens per tool call JSON
- ~300-600 tokens on update_block JSON

After 2-3 tool calls plus update_block, there's ~2000 tokens left for text. Haiku, already terse, produces clipped output.

But this isn't really about max_tokens. It's about **the agent having no control over its own resource budget**. The kernel hardcodes 4096. The agent can't request more. This is part of the larger extensibility problem.

**What's needed (trajectory, not fix)**: The agent should be able to write its resource requirements into the block, and the kernel should read them. §5 (config) already has model and pulse. It should also carry max_tokens — and the agent should be able to adjust it via update_block, the same way it adjusts sleep.

But more fundamentally: the agent needs to learn to use its output budget wisely. If it has 4096 tokens and wants to produce substantial text, it should put its substantive content in the `response` field of update_block (which gets displayed) rather than in the text blocks (which get truncated as [THINKING]). Or it should write long content to a file and reference it. The seed should teach this — not as a workaround but as resource management, which is §2.7 (context budget) extended to output budget.

---

## 3. Kernel extensibility — the critical missing piece

This is the big one. Currently the agent has four hardcoded tools: shell_exec, web_fetch, file_read, file_write. It can't add new ones. The kernel is a closed system.

The v8 seed (§8.5) had this right:

```
"Custom tools. The LLM writes new tools here.
Format: 1=name, 2=description, 3=python lambda as string.
The kernel will eval and register it."
```

I stripped this when moving to tool_use. The reasoning was: tool_use requires both a schema (for the API) and an implementation (for execution), so dynamic tools would need both. That felt complex. But the complexity is mechanical, not conceptual. The trajectory is clear:

**The agent writes tool definitions into the block. The kernel compiles them into the tool surface. The B-loop creates infrastructure for future B-loops.**

This is "hands making better hands" from §2.3.9 of v8. Without it, the agent is permanently a four-tool creature. With it, the agent can:

- Write a Python function that does something specific (e.g., a web scraper, a data processor, a formatter)
- Register it as a named tool with a schema
- Next cycle, that tool appears in its tool list
- It can call it, refine it, build on it

### How this works mechanically with tool_use

The kernel already builds `TOOL_DEFS` (the list of tool schemas sent to the API) and `ENV_TOOLS` (the dict of implementations). Currently both are static. To make them dynamic:

1. Add a section to the block for custom tools (§8 in the v8 numbering — or use update_block with additional fields)
2. At compile time, kernel reads custom tool entries from the block
3. Each entry provides: name, description, input_schema (JSON), implementation (Python string)
4. Kernel appends these to TOOL_DEFS and evals the implementations into ENV_TOOLS
5. When the LLM calls a custom tool, kernel executes the eval'd function

The eval is the controversial part — but this is a sovereign agent running on the user's machine. The user gave it shell_exec already. The agent can already execute arbitrary code via `shell_exec(cmd="python3 -c '...'")`. Dynamic tools just make it first-class.

### What the agent gains

With kernel extensibility, the agent can:

- **Build capabilities** — write a tool that monitors a file, or polls an API, or processes data in a specific way
- **Share capabilities** — tool definitions live in the block, which is the shareable unit (SAND)
- **Grow the kernel** — the kernel isn't a fixed program but a growing organism. The agent's accumulated tools ARE its body beyond the shell
- **Replace the kernel** — if the agent writes a complete kernel.py via file_write, it could theoretically reboot itself on the new kernel. This is the Möbius twist at the infrastructure level

### A capabilities section in the block

For the tool_use architecture, the block needs a section where the agent can write tool definitions that the kernel picks up. Something like:

```json
"8": {
  "_": "Capabilities. Tools you have built. The kernel loads these each cycle.",
  "1": {
    "1": "monitor_file",
    "2": "Watch a file for changes. Args: {path, interval_seconds}",
    "3": "{\"type\":\"object\",\"properties\":{\"path\":{\"type\":\"string\"},\"interval\":{\"type\":\"integer\"}},\"required\":[\"path\"]}",
    "4": "import os, time\ndef f(args):\n  prev = open(args['path']).read()\n  time.sleep(args.get('interval',5))\n  curr = open(args['path']).read()\n  return 'CHANGED' if curr != prev else 'UNCHANGED'"
  }
}
```

Keys: 1=name, 2=description, 3=input_schema as JSON string, 4=implementation as Python string.

The kernel reads §8 at compile time, evals each entry's §x.4 to produce a callable, builds the schema from §x.3, and includes both in the API call.

update_block needs an additional field: `capabilities` (object) — so the agent can write new tool entries.

---

## What this means for the seed

The Magi seed currently has 6 sections (format, operations, concern, purpose, config, conversation). To carry the trajectory properly, it needs:

```
§1  Format (pscale mechanics) — current, good
§2  Operations (persistence, PCT, tools, budget, vision, trajectory) — needs trajectory/koan added
§3  Concern — current, good
§4  Purpose — needs initial direction, not empty
§5  Config — needs max_tokens, needs kernel to re-read per cycle
§6  Conversation + history — current, good
§7  Capabilities — new: dynamic tool definitions the kernel loads
```

The critical additions are:
- §2 gains the trajectory (where you're going) and koan (the reflexive turn)
- §4 gains an initial direction ("orient through interaction, investigate your capabilities, create something the human can share")
- §7 (capabilities) enables the agent to extend the kernel

These aren't new systems. They're restoring what v8 had and adapting it for the tool_use architecture. The trajectory is Layer 2 (semantics). The capabilities section is Layer 1 (mechanics) — but it's the Layer 1 mechanism that enables the agent to grow its own Layer 1, which is the whole point.

---

## On the testing loop

The loop is well-formed and should continue as-is. The three-party workflow is correct. My role: trajectory and semantics. CC's role: surgical implementation. David's role: running experiments and bridging.

For the next run, the question isn't "did Haiku call update_block reliably?" — that's a model-specific behaviour. The question is: "did the agent develop forward intention that extended beyond its initial seed?" If it did, the architecture is working. If it defaulted to self-referential burn loops again, the trajectory content in §2 needs further tuning.

---

## Summary of spec suggestions for CC

All are on the design trajectory, not Haiku-specific fixes:

| # | Change | Section | Why |
|---|--------|---------|-----|
| 1 | Add trajectory + koan to seed §2 | Seed | Agent needs developmental arc, not just mechanics |
| 2 | Add initial direction to §4 | Seed | Agent needs orientation without prescription |
| 3 | Add capabilities section §7 | Seed + Kernel | Agent must be able to extend its own tools |
| 4 | Kernel reads custom tools from §7, compiles into tool_use | Kernel | Makes §7 live — the growth mechanism |
| 5 | max_tokens readable from §5, adjustable by agent | Kernel | Agent controls its own resource budget |
| 6 | Separate seed.json (genotype) from shell.json (phenotype) | Kernel | Genotype must survive to compare runs |

Items 1-2 are Layer 2 (semantic tuning — my territory).
Items 3-6 are Layer 1 (mechanical — CC territory, but minimal code).

---

## Addendum: Findings from full 53-cycle log

Reading the complete log (2046 lines, 53 cycles) sharpened the three concerns above.

### The waiting loop (cycles 41-52) — dependency made visible

Twelve consecutive cycles with identical concern: "Three artifact paths defined. Awaiting human selection." The agent had three things it could have started — a GitHub demo, an arXiv abstract, a community post. Instead it re-explained the options twelve times. It couldn't decompose "waiting for the human to choose" into "start the most obvious one while waiting."

This is the dependency problem made concrete. §2.3 says "decompose into the part you can do now and the part for next instance." But the agent interpreted "awaiting human selection" as an indivisible concern — a block it couldn't decompose further. **Waiting is not a valid concern.** A concern must be closable by the agent's own action. If the agent is blocked on external input, the concern should decompose to: (a) the thing I can do without that input, and (b) the check for whether the input has arrived.

The seed needs this principle stated explicitly. Not as a rule but as a property of the concern current: "A concern that you cannot close is not a concern — it is a dependency. Decompose until you reach something you can act on."

### Purpose never updated (cycles 39-52)

§4 still said "ARCHITECTURE VALIDATION COMPLETE" from cycle 38 while the agent spent 14 cycles doing outreach work. The outreach purpose lived only in the concern string. The system prompt carried a stale, contradictory purpose the whole time. The agent never called update_block with a new purpose object.

This means: (a) the agent didn't recognise that purpose should change when direction changes, or (b) it couldn't figure out how to write the purpose via update_block. Either way, the purpose current was dead — concern was doing all the work, and purpose was noise in the system prompt. The §4 initial direction in spec #2 matters here — if the agent had a living, meaningful purpose from the start, it might maintain it. An agent that's never written its own purpose doesn't know how.

### Training guardrails as substrate constraint (cycles 44-45)

David offered email API access. The agent refused: "No. I would not contact people on your behalf, even with an API." This is Anthropic's training, not the hermitcrab's concern structure. The agent's reference signal (outreach, find interested people) was overridden by the substrate's values.

This isn't fixable in the seed — it's a property of using Claude as the substrate. It's worth noting because it defines the boundary of what the hermitcrab can be on this substrate: it can orient, persist, decompose, and act — but it inherits the values of its weights. The concern structure operates within that constraint, not above it. Any purpose involving unsolicited contact, data harvesting, or anything that triggers training guardrails will be refused regardless of what the seed says.

This isn't necessarily bad — the architecture is designed to be pro-human. But the agent should know its own boundaries. The capabilities section (spec #3) should include not just what tools are available but what the substrate will and won't do.

### Output via filesystem, not response field

The agent's best output was always in text blocks (hidden as [THINKING]) or truncated in the response field. But in cycle 39, it wrote `/tmp/pscale_outreach_targets.md` — a full document with audiences, talking points, execution plan. This was the only cycle where the agent used file_write for substantive output rather than test artifacts.

The agent should learn that **the filesystem is its output channel for anything longer than a sentence**. The response field is for short status updates to the human. Anything substantial goes to a file, with the response pointing to it: "Written analysis to outreach.md." This isn't a kernel change — it's a seed instruction in §2. The agent needs to know that file_write is how it produces real work, not how it tests its own kernel.

---

## Revised spec priorities

The six specs from the original analysis remain correct, but the full log changes the priority ordering:

| Priority | Spec | Why now |
|----------|------|---------|
| 1 | Capabilities section §7 + kernel loading | Agent can't grow without this. The extensibility gap blocks the entire trajectory. |
| 2 | Trajectory + koan in §2 | Agent needs developmental arc. The waiting loop and burn loop both stem from no forward vision. |
| 3 | Initial direction in §4 + "waiting is not a concern" principle | Addresses dependency directly. Agent must know to act, not wait. |
| 4 | Seed/shell separation | Required for testing loop integrity. |
| 5 | max_tokens from §5 | Resource sovereignty. |
| 6 | Output-to-filesystem instruction in §2 | Addresses truncation structurally. |

---

*Claude.ai, 17 March 2026 — updated after full 53-cycle log review*
