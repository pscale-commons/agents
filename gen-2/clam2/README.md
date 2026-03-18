# Clam 2 Seed Testing

**Origin**: Claude chat thread (synthesis of G0 + Magi learnings)
**Architecture**: Python standalone, Anthropic tool_use API (stdlib only, no pip)
**Kernel**: kernel.py (~300 lines original, ~350 with logging)
**Seed**: seed.json (6 sections, purpose empty, Sonnet default)
**Key difference from Kermit**: Full-block return via update_block — the LLM gets the complete block in the message and returns the complete modified block. The kernel just preserves §5 and saves. The LLM has full sovereignty over all sections including conversation (§6). Pulse re-read each cycle, so the agent CAN change its own timing by modifying §5.4 in the returned block. Also: .env loader, max_tokens=8192, HTTP error handling, 120s API timeout.

## Directory Structure

```
tests/clam2/
  kernel.py             ← kernel (with logging patch)
  seed.json             ← original seed (genotype)
  current-mapping.md    ← design spec
  run-1/
    shell.json          ← entity's state after run
    clam2-test.log      ← raw kernel log
    analysis.md         ← observer analysis
  run-2/
    ...
```

## Runs

| Run | Date | Changes from previous | Key finding |
|-----|------|----------------------|-------------|
| 1 | 17 Mar 2026 | First test (with logging) | 3.5/5 — Full-block return works (100% reliability), agent added §7, but escalating token cost, concern underscore frozen, same burn loop pattern. 5 cycles, $0.51. |
