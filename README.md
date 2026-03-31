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

## What changed between generations

Gen-1 agents run in a browser with a JS kernel that manages conversation, concerns, and rendering. The BSP function and block format predate the formal specification.

Gen-2 agents are headless Python processes that call the Anthropic API directly. The block format follows the touchstone specification (see [pscale-commons/pscale](https://github.com/pscale-commons/pscale)). The kernel is minimal — boot, B-loop cycle, tool dispatch — because the block structure carries the behaviour.

## Gen-3 — Star-operator agents (private)

Gen-3 uses the starstone and `*` operator (recursive BSP). These agents are in a private repo while the format stabilises. Contact [David Pinto](https://hermitcrab.me) for access.

## Related repos

- [pscale-commons/pscale](https://github.com/pscale-commons/pscale) — format spec (touchstone/guidelines/design) and BSP tools
- [pscale-commons/seed-spore](https://github.com/pscale-commons/seed-spore) — the pscale seed and its teaching companion

## Author

Created by [David Pinto](https://hermitcrab.me).

## License

[MIT](LICENSE)
