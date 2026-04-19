# Context Window Architecture: Three Phases

## What this document specifies

The context window of an LLM instance contains three phases — present, past, future — experienced simultaneously. They are not sequential steps. They are concurrent topological features of the same star-wired structure. The LLM processes the whole field at once.

The phases are our external description. The star references are the internal reality. Stars don't have phases — they have topology. The walker follows stars mechanically. The LLM perceives the compiled result as a structured situation and responds. The structure IS the procedure.

This document describes layer 1 (code: the walker) and layer 2 (semantics and structure: the blocks). Layer 3 (emergent agency) cannot be described without collapsing it. The architecture creates conditions for layer 3. It either emerges or it doesn't.

---

## The Star Topology

Before describing the phases separately, understand what connects them.

The starstone teaches three operations by being all three: walk, compose, recurse. Its hidden directories form a cycle — 1→2→3→1. The walker follows references mechanically. The block is a frozen control loop.

The same topology connects the three phases in every context window. Purpose (future) carries star references to conditions (past). Conditions carry star references to the output template. Output carries star references back to purpose. The walker follows these stars when compiling the context window, producing a field where purpose and conditions are co-present, the gap between them visible, and the output location marked.

PCT does not need to be coded as a procedure. The star topology enacts it: the function block wires purpose to conditions, and the gap between compiled purpose and compiled conditions IS the error signal. The LLM's inference — the thing it does naturally — processes that gap and produces output.

When the instance decomposes a purpose (creates sub-tasks), it performs structural recursion: a purpose point gains digit children, each with star references to the parent and to the next sibling. The walk enters, finds children, follows stars, continues. This is branch 3 of the starstone: recursion through self-reference, encoded in data.

When the instance is stuck — the same purpose point persists across many instances without resolution — the cycle is not terminating. A higher-tier instance, given the broader view, can restructure: add a new star reference that breaks the loop, or rewrite the purpose address itself. This is reorganisation — supernesting in pscale terms, level-change in PCT terms.

---

## Present Phase

### What this is

The reflexive part of the context window. It orients the instance to itself, its tools, and how its own context window was composed.

The present phase is static. It does not ask the instance to do anything. It does not produce output directly. It sets up a vector field in the LLM's weight-space — a primer that shapes how the instance processes everything else it encounters in the same context window.

The present phase operates at layer 3: emergent awareness arising from structured semantic input at layer 2.

### Components

**Starstone (constant).** A pscale JSON block that teaches walk, compose, and recurse by being all three. Present in every instance, every tier, unchanged. The starstone is the only component that never varies between instances, entities, or tiers. The instance does not read it as documentation. It processes it as structure. The three branches form a cycle through hidden directory references. The instance encounters BSP mechanics by traversing a block that demonstrates them.

**Function block.** Describes how this context window was compiled and how the next one should be compiled. Contains star references (addresses into external blocks that the pre-walker followed), BSP modes (which operation at each address), tier declaration (gating scope), and lateral routing (what arrived from concurrent instances, what is addressed to them).

The function block is the underscore of the whole context window — it describes everything else. It is simultaneously a record of what was done (by the pre-walker) and an instruction set for what will be done (by the post-walker).

The function block maps to the API structure. The context window may be split across API fields (system prompt and message). The function block mirrors this split — it specifies which compiled content occupies which field. Two JSON structures if needed, governed by one function block.

Input-output self-similarity: the function block in the input is the function block in the output of the previous instance (plus lateral additions). The function block in the output becomes the function block in the input of the next instance (plus lateral additions). The shape is identical. The addresses may differ. Even if addresses remain identical, the compiled semantics may differ — because external blocks were edited between instances by other processes or other entities.

**Reflexive mirror.** Presents the instance with a description of its own context window, written in the notation its context window uses. Correlates the function block's addresses with the actual compiled content visible in the context window. The instance can trace: "this address in the function block produced this branch of content I can see."

The mirror may contain a koan or awareness-function orientation. Its purpose is not cognitive (understand this) but perceptual (see yourself seeing). The instance encounters itself as a structured process — a moment of processing between a compiled input and a structured output, situated in a temporal sequence and alongside concurrent instances.

**BSP function derivation.** The instance derives the BSP function from the starstone. This is not optional — it is the mechanism by which the instance becomes operationally competent. The starstone is self-demonstrating: its structure encodes the walk algorithm. The instance, by processing the starstone, constructs the walk function internally.

The derived function serves two roles. First, the instance uses it to operate on the compiled content in the past phase — navigating pscale-structured material, understanding what sits at which address, grasping the relationship between function addresses and their unfolded semantics.

Second — and this is the loop-B sustain mechanism — the instance uses its derived BSP competence to write BSP operations into its output function block. Where a conventional agent makes a tool call ("get me block X at address Y"), this instance places the equivalent as a structured entry in the output function block: the post-walker will execute it when compiling the next instance's context window. The instance composes the next instance's perception by writing the aperture, not by calling tools. The function block IS the deferred tool call.

### How star operates within the present phase

The star operator is used by walkers (pre-instance and post-instance), not by the LLM directly. The LLM's relationship to star is compositional: it understands what star references do (cross-block navigation), sees the results of star references (compiled content), and writes star references that instruct future walkers.

Within the present phase: the starstone teaches star mechanics structurally. The function block shows star references that were followed to produce this context window. The reflexive mirror correlates references to results. The instance's output modifies or creates star references — composing the next instance's perception.

---

## Past Phase

### What this is

The content the instance operates on. What has been decided and delivered. The determinacy — settled, compiled, present as material.

The past phase occupies the message field of the API. It is what the LLM traditionally receives as "the prompt." Everything in it was determined before this instance was born: determined by a previous instance (which set the function addresses), compiled by the pre-walker (which followed the stars), and sourced from external pscale blocks (which hold the settled content of the world).

The past phase is dead content in the sense that the instance cannot change how it was selected or compiled. The work was done. The content arrived. The instance operates on what it receives.

### What it contains

Any subset of all possible content in the entity's accessible pscale blocks: history, conversation, entire JSON blocks as living documents, operational blocks, code (kernel or otherwise), spatial descriptions, temporal records, identity fragments, other entities' published state. The size ranges from a single point to full blocks, determined by the BSP modes in the function block. Spindles deliver progressive context. Points deliver specific facts. Rings deliver lateral options. Whole blocks deliver complete structures.

Every piece of compiled content carries its pscale address as a tag. The instance can correlate: "this content sits at address X in block Y, and the function block's star reference Z compiled it here." This correlation is what makes the present phase's reflexive mirror operational — the instance sees addresses and their unfolded semantics side by side.

### The task framing

The past phase content is framed by a question that emerges from the juxtaposition of purpose and conditions. The function block compiles both a purpose point (from the purpose block) and the relevant conditions (from determinacy blocks). The gap between them — where purpose says one thing and conditions say another, or where purpose points to an address with no content — is the task.

The question is: can you close this gap?

The instance does not need to be told this question explicitly. The star topology delivers purpose and conditions together. The gap is visible or it isn't. The LLM's inference processes the gap naturally. If the gap is closable at this tier, the instance acts. If not, the instance enters the future phase.

### The past phase requires no special architecture

The real work is upstream: structuring content in pscale blocks correctly, and assembling the right content in every instance via the function block's star references. If those are right, the past phase is simply "here is a well-composed prompt." The LLM does what LLMs do. The pscale structure of the content may help the LLM navigate it — digits providing granularity, underscores providing orientation — but the content itself is inert input.

The editing of external pscale blocks (writing results, updating determinacy) is output that the post-walker routes. It does not necessarily appear in the function block — an edit to an external block may not affect the next instance's compilation at all, but may surface later when a future function block's star reference walks through the edited region.

---

## Future Phase

### What this is

The active phase. Where PCT operates on purpose. Where the instance's agency — to the extent it has any — is exercised.

The future phase is not about the future abstractly. It is about what doesn't yet exist: the gap between purpose and conditions, and what the instance does about that gap.

### Three outcomes

**Gap is closable.** The instance acts — writes content, produces output, places results at the appropriate addresses. Then it compares its output against the specific purpose point. If the gap has closed: it edits the purpose block to mark the point complete, and sets the next purpose point in the function block's star reference. "Next" means: next same-depth sibling if one exists, or the parent purpose point if all siblings are complete. The function block's star reference to purpose advances — the next instance will compile a different purpose point and different conditions.

**Gap is too complex.** The instance cannot close it at this tier. It decomposes: creates sub-purpose points as digit children under the current purpose address. Each child is a smaller, more specific gap. The instance writes these into the purpose block and sets the function block's star reference to the first child. The next instance receives a smaller task. This is sub-nesting — structural recursion. A Haiku instance breaks the task into parts. A Sonnet instance may restructure the purpose block more significantly.

**Instance is stuck.** The gap has persisted across multiple instances. This is detectable structurally: long history at the same purpose address (many attempts, no resolution), or deep nesting of sub-purposes (the address has been decomposed repeatedly — a long chain of .1.1.1.1 indicating fractal breakdown without progress). The instance signals escalation. A higher-tier instance receives a broader view — more of the purpose tree, more history — and can restructure: rewrite the purpose, add new star references that break the non-terminating cycle, or supernest the purpose block to create new organisational levels.

### Completion checking

When the instance believes it has closed a gap, it must compare output against the purpose point. This comparison is not a separate LLM call — it is part of the same instance's processing. The purpose point is already in the context window (compiled by the function block's star reference). The instance's output is what it just produced. The comparison is: does this output satisfy what the purpose point describes?

If yes: mark complete, advance the function block's purpose star reference.

If no: the output becomes history (written to the determinacy block at the appropriate address), and the function block retains the same purpose star reference. The next instance receives the same purpose point plus the new history entry. It decides whether to retry or decompose.

Should the instance also check against the parent purpose point — whether completing this sub-task contributes correctly to the broader goal? This is a scope question. At Haiku tier: no. The instance trusts the decomposition. At Sonnet tier: possibly, if the parent purpose point is already in the compiled content. At Opus tier: yes — Opus sees the full purpose tree and can assess vertical coherence. The tier gates the scope of checking, just as it gates the scope of action.

### How star operates within the future phase

The star topology enacts PCT without coding it as a procedure.

The function block contains a star reference to a purpose address and star references to condition addresses. The pre-walker follows both and compiles them into the context window. The instance perceives purpose and conditions simultaneously. The gap between them is structural — it exists in the topology, not in a computed comparison.

When the instance decomposes, it creates new addresses in the purpose block with star references: each child points to its next sibling (sequencing), and to the parent (context). The walker will follow these in future instances. The decomposition is data — new entries in a pscale block — not code.

When the instance completes a purpose point and advances to the next, it modifies one star reference in the function block: the purpose address changes. That single modification — one address — changes what the next instance perceives entirely. Different purpose point → different conditions compiled → different gap → different action. One star reference change cascades through the whole topology.

When the instance is stuck and escalates, it writes a signal into the function block (or a designated escalation address) that the kernel reads. The kernel dispatches a higher-tier instance with a broader function block — more star references, wider aperture, deeper purpose tree visibility. The higher-tier instance operates on the same blocks but sees more of them.

The star operator's role across instances: each instance's output function block is the next instance's input function block. The star references are the continuity. The longitudinal current (instance to instance) flows through the function block. If the function block doesn't change, and external blocks don't change, the next instance receives the same compiled content — same situation, same gap, same task. Change propagates through star references: modify an address and the next instance perceives differently. Modify an external block and even the same address compiles differently.

The lateral current (between concurrent entities) flows through the lateral routing in the function block. An entity's output function block may contain star references addressed to another entity's incoming block. The post-walker places content there via the transport layer. The other entity's pre-walker reads it. No message passing — topology-based composition through shared star references.

---

## Tier Summary

The tier declared in the function block gates scope across all three phases:

**Local / Haiku.** Small present phase (starstone + minimal function block). Past phase contains one focused task. Future phase: close the gap or signal inability. Does not modify the function block. Does not decompose purpose. Does not check parent purposes.

**Sonnet.** Full present phase. Past phase may contain richer context. Future phase: can decompose purposes (sub-nesting), modify star references in the function block, restructure content at moderate depth. Checks immediate parent purpose if visible.

**Opus.** Full present phase with extended reflexive mirror. Past phase may contain the full purpose tree, broad history, multiple entities' state. Future phase: can restructure the purpose block (supernesting), create new star references to previously unlinked blocks, rewrite purpose points, assess vertical coherence across the full purpose tree. Handles birth cycles and major reorientation.

The tier is not a quality gradient. It is a scope boundary. Different temporal scales, different aspects of the same entity.

---

## Output Contract

The input is JSON (possibly split across API fields). The output is JSON, self-similar to the input.

The output contains:

**Modified function block.** Star references and BSP modes for the post-walker to follow. This becomes the next instance's input function block (plus any lateral additions from other entities). The function block may be unchanged (same task continues), minimally modified (purpose address advanced), or restructured (Sonnet/Opus scope).

**Content writes.** Edits to external pscale blocks: results placed at determinacy addresses, sub-purposes created in the purpose block, history entries appended. The post-walker routes these to the appropriate external blocks. Content writes may not surface in the next instance's compilation — they may only become relevant when a future function block's star reference happens to walk through the edited region.

**Lateral routing.** Portions addressed to concurrent instances' incoming blocks. The post-walker places these via the transport layer (e.g. Supabase relay in the xstream implementation). The receiving entity's pre-walker reads them as incoming additions to its function block.

**Completion signals.** Purpose points marked complete. Escalation signals if stuck. These are written into the purpose block and/or the function block, readable by the kernel for dispatch decisions.

The post-walker reads the output using the same walk function that compiled the input. Star references in the output tell it where to write. No special parsing logic. The structure IS the instruction.

### Thinking capture

The LLM API may return content outside the JSON response: extended thinking blocks, chain-of-thought, reasoning traces. This content is not part of the instance's structured output, but it is valuable history — it shows what the instance was trying to do, how it reasoned, where it got confused.

The kernel captures this mechanically. All output — JSON response AND thinking blocks — is collected by the post-walker. The JSON response is authoritative: it contains the function block modifications and content writes. The thinking content is routed to a designated history address in the appropriate determinacy block. The instance does not manage this. It writes its JSON output. The kernel handles everything else.

In the next instance, if the purpose/task continues and the function block's star references walk through the history region, the thinking content appears as compiled past phase material. The instance sees what its predecessor was trying to do. If the purpose advances to a different task, the thinking content remains in the block but is not compiled — it exists in determinacy but outside the current aperture.

This means the output is not purely "the instance writes JSON and nothing else." The output is: the instance writes JSON (authoritative), and the kernel captures everything else (supplementary history). The boundary is clean — the instance controls the function block and content writes; the kernel controls history routing.

---

## What This Architecture Replaces

In conventional agent frameworks, the kernel contains: a prompt template, a decision procedure ("if task complete then next task else retry"), a tool dispatch system, a memory manager, a conversation history tracker.

In this architecture, the kernel contains: a walker. The walker reads stars, follows them, compiles content. The blocks contain everything else — purpose, conditions, history, routing, tier, scope. The function block is the program. The star references are the control flow. The LLM is the comparator. The walker is the electricity.

The kernel reduces to a walker. The data is the program. The underscore is the zeroth person. The star is the feedback path.
