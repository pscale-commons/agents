# pscale agents

LLM agents that run on pscale semantic block architecture. Two generations, each with different kernels and design assumptions.

## Gen-1 — Old BSP / Touchstone

Built on the original BSP implementation and touchstone block format. JavaScript-based, browser-hosted.

| Agent | Architecture | Notes |
|-------|-------------|-------|
| **hermitcrab** | JS kernel, browser | The original — live at idiothuman.com |
| **ammonite** | JS kernel, adapter pattern | Modular variant with pluggable LLM/storage adapters |
| **seaurchin** | JS kernel, standalone | Minimal standalone with unfold-based BSP |

## Gen-2 — Spark-era BSP

Python standalone kernels using the Anthropic tool_use API. Tested 17 March 2026.

| Agent | Model | Score | Notes |
|-------|-------|-------|-------|
| **g0** | Sonnet | 2/5 | First working B-loop attempt, pre-loaded MAGI streams |
| **magi** | Haiku → Sonnet | 3.5/5 (Haiku), 3/5 (Sonnet) | Real B-loop with sleep control |
| **kermit** | Sonnet | 4/5 | Best tested — hybrid of G0 design + Magi mechanics |
| **clam2** | Sonnet | 3.5/5 | Full-block return variant |

Each gen-2 agent directory contains the kernel, seed, run logs, and analysis.

## Gen-3 — Star-operator agents

Python standalone kernels that use the **starstone** block and the `*` operator (recursive BSP across blocks). Each agent is self-contained: its own kernel, its own `blocks/` directory, and its own `starstone.json` travelling with it. No shared runtime — the reference library under `gen-3/starstone/` is provenance, not a dependency.

| Agent | Description |
|-------|-------------|
| **1-magi-onen-kael** | Character agent — Kael in an RPG world. Game-ready message builder. |
| **2-magi-v3-thresher** | Introspective entity — soul block, tiered Haiku→Sonnet models, auto-advance. |
| **3-magi-merged** | Combined kernel — v3's engine + onen's character blocks. One kernel, use-case driven by blocks. |
| **4-magi-mobius** | Definitive kernel (~920 lines) + `server.py` web UI + `kernel-spec.md`. Walker that follows star references. |

Each agent directory has its own README with run instructions.

### gen-3/starstone/ — reference library

The starstone is to gen-3 what the touchstone is to gen-2: a pscale block that teaches BSP by being BSP. It extends the touchstone with nested-underscore collection and the `*` operator (walk into a hidden directory, continue navigating as a separate block — composition of walks).

- `pscale-starstone{,2,3}.json` + `pscale-starstone-lean{,2,3}.json` — six block variants (all six kept for provenance; `-3` / `-lean3` are the latest)
- `bsp-star.py`, `bsp-star.js`, `bsp2-star.py` — reference BSP implementations with `*` support
- `discovery_star_operator.md` — how the `*` operator emerged
- `spec_nested_underscore_and_star.md` — formal spec
- `star-tests/` — test fixtures

## What changed between generations

- **Gen-1** — browser JS kernel managing conversation, concerns, and rendering. Pre-specification BSP and block format.
- **Gen-2** — headless Python, Anthropic `tool_use`, touchstone block format (see [pscale-commons/pscale](https://github.com/pscale-commons/pscale)). Kernel is boot + B-loop + tool dispatch; blocks carry the behaviour.
- **Gen-3** — headless Python walker over starstone blocks. The `*` operator lets one block reference another at a specific address, so context-window compilation becomes a walk across blocks, not a fixed template. The kernel shrinks further — what used to be kernel logic becomes star references in blocks.

## Related repos

- [pscale-commons/pscale](https://github.com/pscale-commons/pscale) — format spec (touchstone/guidelines/design) and BSP tools
- [pscale-commons/seed-spore](https://github.com/pscale-commons/seed-spore) — the pscale seed and its teaching companion

## Author

Created by [David Pinto](https://hermitcrab.me).

## License

[MIT](LICENSE)
