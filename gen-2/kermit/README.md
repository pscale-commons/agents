# Kermit Seed Testing

**Origin**: Claude chat thread (hybrid synthesis — G0 seed design + Magi tool_use mechanics)
**Architecture**: Python standalone, Anthropic tool_use API (stdlib only, no pip)
**Kernel**: kermit-kernel.py (~300 lines original, ~340 with logging)
**Seed**: kermit-seed.json (6 sections, purpose empty, Sonnet default)
**Key differences from Magi**: No `requests` dependency (stdlib urllib), separate seed/shell files, no sleep field in update_block (fixed pulse), no history field, concern stored as `{_: text}` object not flat string, Sonnet model.

## Directory Structure

```
tests/kermit/
  kermit-kernel.py      ← kernel (with logging patch)
  kermit-seed.json      ← original seed (genotype)
  run-1/
    kermit-shell.json   ← entity's state after run
    kermit-test.log     ← raw kernel log
    analysis.md         ← observer analysis
  run-2/
    ...
```

## Runs

| Run | Date | Changes from previous | Key finding |
|-----|------|----------------------|-------------|
| 1 | 17 Mar 2026 | First test (with logging) | 4/5 — 21 cycles, $1.94. 100% update_block reliability. Self-repair attempted. Best kernel tested. |
