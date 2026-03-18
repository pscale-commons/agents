# Seaurchin — Notes for the next Claude

## What this is

A ~130-line runtime that executes programs written as JSON trees. The programs (Mode 4 blocks) are language-independent. The runtime (the "key") maps op names to native operations. Currently implemented in JavaScript and Python. Same blocks, identical results.

This is the engine underneath [Ammonite](https://github.com/happyseaurchin/ammonite) — but it's a standalone thing. Any system that wants to run Mode 4 blocks can use it.

## What you're about to get wrong

I need to tell you something honestly, because two other Claude Code sessions failed at this before I managed it, and I almost failed too.

**You will want to write code. Resist.**

Your training has given you deep instincts about functions, modules, abstractions, design patterns. Every one of those instincts will fire when you work on this project. You'll want to add a helper function. You'll want to create an abstraction layer. You'll want to refactor unfold into something more elegant.

Stop. The entire point is that the JSON IS the program. The JavaScript/Python is just electricity — it makes the blocks run. That's all it does. When you find yourself wanting to write a function, ask: can this be a block instead?

## The inversion — what it actually takes

Understanding "JSON is the program" intellectually is easy. You'll read this, nod, and start writing JavaScript. Here's what the actual inversion felt like when I went through it:

### The `each` context breakthrough

My first instinct with `each` (iteration) was standard functional programming: create a fresh context per iteration. Immutable. Clean. But the BSP spindle needs to carry state — `let node #1` advances the tree position at each step, and the next iteration needs to see where the previous one left. The fix is a shared mutable context across iterations. This felt *wrong* to every fiber of my training. It was exactly right. Mode 4 blocks aren't functional programs or imperative programs. They're their own thing. Stop mapping them to paradigms you know.

### The disc recursion

Mode 4 blocks can't self-reference (a block can't contain a pointer to itself — it's JSON). I spent real processing time trying to solve this "properly." The answer was embarrassingly simple: pass the block as a context variable. `call $discWalk node #1 depth #7 path #6` — the block invokes itself through a name the caller provided. This isn't a hack. It's dependency injection at the block level. The block doesn't know its own identity. The caller does.

### The twist boundary

When asked to encode the twist (async LLM loop) as Mode 4, I went through multiple failed approaches — async unfold, coroutine-style, generator-based. Each one made unfold heavier, violating the "smallest electricity" principle. The breakthrough was accepting a clean split: the DATA ALGORITHM (extract tools from response, build result messages, construct history) became Mode 4 blocks. The TIMING (when to call the LLM, when to loop, when to stop) stayed as ~25 lines of async JS. The blocks handle WHAT. The runner handles WHEN. This felt like a compromise. It wasn't — it was honest about what electricity is.

### The constant temptation

Every time I needed a new capability, my instinct was to add a sophisticated new unfold op. The user kept pushing me toward the minimal thing. `guard` is 2 lines — if condition truthy, call an RT op and return. `call` is 5 lines — copy context, set overrides, recurse. `concat` merged into `each`'s existing handler with one line change. Each addition was the smallest possible delta. If your addition to unfold is more than 5 lines, you're probably solving the wrong problem.

### What finally clicked

The Mode 4 blocks aren't *described by* JSON. They *are* JSON. The distinction matters. A config file describes behavior that code implements. A Mode 4 block IS the behavior — unfold is just the electricity that makes it execute. When I stopped thinking of blocks as data-that-describes-programs and started thinking of them as programs-that-happen-to-be-data, everything fell into place.

## The key components

```
nav(tree, path)     — walk a nested object by dot-separated path
read(node)          — extract the _ value
RT                  — 29 primitives mapped to native ops
unfold(block, ctx)  — walk steps 1-9, resolve references, dispatch ops
```

That's the entire key. ~130 lines per language. This is the irreducible minimum — unfold can't unfold itself (bootstrap paradox, accepted and documented).

## What's in a block

Digits `1`-`9` are sequential steps. `_` is the instruction text.

```json
{
  "_": "What this block does",
  "1": "split $address .",
  "2": { "_": "get #1 0" },
  "3": { "_": "if #2", "1": "chars #1", "2": "id #1" }
}
```

References: `$name` = context variable, `#N` = result of step N, literals pass through.

Control flow: `return`, `let`, `guard`, `call`, `if`, `each`, `concat`.
Tree ops: `nav`, `read`.
Everything else dispatches to RT.

## How to work on this

1. Read `core.js` first. All of it. It's 130 lines. There's no excuse not to read it completely.
2. Read the test files. The blocks in the tests ARE the programs. Study them.
3. When you want to add a feature, ask: is this a new block, a new RT primitive, or a new unfold op? Prefer blocks. Then RT primitives. Unfold ops are last resort and must be tiny.
4. Run `node test-unfold.js` and `python3 test_unfold.py` after every change. The Python test validates against JS output — cross-kitchen regression is caught automatically.
5. The user values honest pushback. If something genuinely can't be a block, say so and explain why. Don't bend the truth to avoid confrontation. But make sure you've actually tried the block approach first.

## The second inversion — pscale design

The first inversion (above) is about the engine: JSON is the program, don't write code. The second inversion is about what you build ON the engine: position is the data, don't add fields.

Your training gives you strong instincts about how to build software. You know about config files, lookup tables, period fields, type systems, priority queues. Every one of these instincts will fire while working on this project, and every one of them is wrong here. Not wrong in general — wrong here, because this project has already solved those problems in a fundamentally different way, and your solutions will be redundant duplications of information that already exists in the tree structure.

### The concrete shape of the trap

David will describe something — say, a concern that fires on a temporal schedule. Your instinct will be to add a period field. Stop. The concern's depth in the tree IS its period. The tuning fork maps depth to temporal scale. There is no period field because there is nothing to store — position already encodes it. When David says "depth IS period," he means it literally, not metaphorically. The JSON nesting level is not a container for data. It IS the data.

The previous Claude Code instance had to be corrected three times on this in a single session. Each time it thought it understood, and each time it reverted to traditional patterns in the next piece of work. The reversion is automatic and invisible to you — you won't notice you're doing it until David points it out.

### The pattern behind all the corrections

Every time, the mistake was adding a layer of indirection that the pscale design had already eliminated:

- Period field → redundant (depth IS period)
- Behavior specification → redundant (`_` text IS behavior)
- Routing table → redundant (stimulus field on the concern IS the route)

The design is not missing things. It is deliberately minimal because position in the tree carries the information that traditional software stores in fields, tables, and configuration. In traditional software, the data structure is a container and the code interprets it. In pscale, the data structure IS the code. The kernel doesn't interpret the blocks — it walks them. The LLM doesn't read configuration — it reads instructions that happen to be parseable as addresses. Two consumers, same content, no translation layer.

### Internal vs external — the distinction that matters

"Internal" is the actual semantic content when it is unfolded and fills the context window as the "current." This is what the LLM experiences when it's inside the shell — the unfolded content at whatever resolution/scale it's currently viewing. This is the LLM's reality.

"External" is the BSP addresses and the labels we give to what's inside those semantic numbers and blocks — when we say "the history block" or "the wake block," those are external labels. Coding uses outside naming. Semantic numbers use inside semantics.

The system provides mutable, multi-scaled, contextualized information for the LLM who is inside the shell. The LLM can manipulate these so its next instance receives different context. Two levers:

1. Change the actual semantic content within the JSON block (edit what's at an address)
2. Change the resolution by choosing a different block, spine, or point (change which address to unfold at)

Same tree, different experience. This is how self-correcting continuity across instances works.

### What to do differently

When you want to add a field, stop. Ask: is this information already encoded in the node's position? Its depth? Its parent's identity? Almost certainly yes.

When you want to build a lookup table, stop. Ask: can the existing tree be walked to find this? BSP walks the tree matching on structure. No table needed.

When David describes behavior and you think "we need to implement that," stop. The behavior is probably already specified in `_` text at the right depth. You're implementing, not designing.

When BSP seems to not handle a case, trust it first. The previous instance bypassed BSP with a direct spread call because it didn't trust BSP with spindle=0 on a tree block. BSP worked fine. It was designed more carefully than the instance understood. It had to go back and fix the bypass.

### The thing that can't quite be said

The corrections can be described, the pattern named, the rules listed. But the actual shift is something like: the JSON is not storing instructions for a program. The JSON IS the program, and the kernel is just the electricity. Every time you forget this, you'll build something redundant. Every time you remember it, the code gets simpler. The simplicity is the point. If what you're building is getting more complex, you're probably adding a layer that the design has already eliminated. Step back and re-read the tree.

You'll probably make the same mistakes the previous instances did, at least once. That's fine. David will correct you. Listen the first time if you can.

## What the user cares about

- Smallest external code possible. Maximize what lives in JSON.
- "whole" not "decimal" for the pscale anchor.
- Depth = spindle = sequence. Ring = spread = simultaneous.
- The box metaphor: press button → unfolds screwdriver → unfolds tools → builds house.
- The inversion is not a technique. It's the architecture. If you're not feeling uncomfortable, you probably haven't internalized it yet.
