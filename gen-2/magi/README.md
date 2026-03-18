# Magi Seed Testing

**Origin**: Claude chat thread (Magi Plex 1 project context)
**Architecture**: Python standalone, Anthropic tool_use API, requires `requests`
**Kernel**: seed.py (~250 lines original, ~290 with logging)
**Seed**: seed.json (6 sections, purpose empty, Haiku default)
**Key difference from G0**: Has real B-loop (sleep between cycles), update_block ends instance, agent controls sleep duration, reads ANTHROPIC_API_KEY from env.

## Directory Structure

```
tests/magi/
  seed.py               ← kernel (with logging patch)
  seed.json             ← original seed (genotype)
  systemic-development.md ← design spec and test history
  run-1/
    shell.json          ← entity's state after run
    analysis.md         ← observer analysis
    magi-test.log       ← raw kernel log
  run-2/
    ...
```

## Runs

| Run | Date | Changes from previous | Key finding |
|-----|------|----------------------|-------------|
| 1 | 17 Mar 2026 | First test (with logging) | 3.5/5 — 53 cycles, $0.55. Working B-loop, PCT confirmed. Haiku update_block reliability is bottleneck. |
| 2 | 17 Mar 2026 | Sonnet model, trajectory+koan in §2, initial direction in §4, seed/shell separation, max_tokens from §5.6 (8192), "waiting is not a concern" principle | 3/5 — 7 cycles, $0.77. 100% update_block. Burn loop persists (wrote 7 self-referential files). Trajectory narrated not internalised. Pulse change broken (file_write overwritten by kernel). |
