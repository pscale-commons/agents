# G0 Seed Testing

**Origin**: Claude chat thread (project context)
**Architecture**: Python standalone, Anthropic tool_use API, stdlib only
**Kernel**: g0-kernel.py (~628 lines)
**Seed**: g0-seed.json (6008 chars, 7 sections, MAGI purpose)

## Directory Structure

```
tests/g0/
  g0-kernel.py          ← source kernel (with logging patch)
  g0-seed.json          ← original seed (genotype, never modified)
  g0-system-spec.md     ← design spec from the Claude chat that created it
  g0-current-mapping.md ← how blocks map to LLM context
  run-1/
    shell.json          ← entity's state after run (phenotype)
    log.md              ← observer analysis: what happened, what it means
    g0-test.log         ← raw kernel log (if logging patch was active)
  run-2/
    ...
```

## How to run an experiment

1. Copy kernel + seed to a working directory (e.g. ~/tests/g0/)
2. Delete any existing shell: `rm g0-shell.json`
3. Run: `python3 g0-kernel.py`
4. Interact, observe
5. Copy shell.json and g0-test.log back to the next `run-N/` directory
6. Write analysis in `run-N/log.md`

## Who reviews what

- **Claude Code**: reads log files and shell state, makes surgical kernel patches, proposes changes
- **Claude chat**: reviews analysis and proposals, guards against traditional coding patterns (the inversion), provides design direction
- **David**: runs experiments, bridges the two Claudes, makes final calls

## Runs

| Run | Date | Changes from previous | Key finding |
|-----|------|----------------------|-------------|
| 1 | 17 Mar 2026 | First test (unpatched, then logging added) | No B-loop, runaway A-loop cost, chatbot not agent. Score: 2/5 |
