# Definitive Kernel Specification

**Target: ~430 lines Python. Layer 1 — the electricity.**

The kernel is a walker. It walks pscale blocks, follows star references, compiles context windows, calls LLMs, routes output writes, records filmstrips, and sleeps. Everything else — what to perceive, when to fire, how to respond, what to remember — lives in blocks (Layer 2). Emergent awareness (Layer 3) arises from the LLM reading and reshaping its own blocks across cycles.

---

## Architecture

```
Layer 3: Emergent awareness        (LLM perceiving its own structure)
Layer 2: Blocks (JSON)             (the program — concerns, function configs, purpose, history...)
Layer 1: Kernel (Python)           (the electricity — walk, compile, call, route, save)
Layer 0: Filmstrip (JSON files)    (ground truth — every context window and output, on disk)
```

---

## 1. BSP Engine (~100 lines)

Five read modes plus star. Ported from magi-merged's implementation, extended with hermitcrab's disc mode.

### Functions

```python
def underscore_text(node):
    """Follow underscore chain to deepest string. Return (text, has_hidden)."""
    # If string, return it directly
    # If dict with "_", recurse on "_"
    # Digit keys alongside nested "_" = hidden directory exists

def walk(block, address="_"):
    """Navigate block by digit address. Return (spindle, terminal_node).

    spindle = list of underscore texts from root to terminal.
    Digit 0 maps to "_" key (enters underscore object / hidden directory).
    Digits 1-9 map to their string keys.
    """

def bsp(block, address="_", mode="spindle"):
    """Read block at address in given mode.

    Modes:
      spindle  — chain of underscore texts, root to terminal (default)
      ring     — sibling keys + texts at terminal
      dir      — full subtree at terminal
      point    — single text at terminal (spindle[-1])
      disc     — all nodes at a given depth across entire block
      star     — hidden directory at terminal (digit children of underscore object)
    """

def write_at(block, address, value):
    """Write value at address, creating intermediate nodes as needed."""
```

### Star Reference Convention

A star reference is a string in format `"blockname:address"` or just `"blockname"` (= root). Found inside hidden directories (digit children of underscore objects).

```python
def parse_star(ref):
    """Parse 'blockname:address' -> (blockname, address).
    'blockname' alone -> (blockname, '_')."""
```

---

## 2. Block I/O (~40 lines)

```python
BLOCKS_DIR = "blocks"
FILMSTRIP_DIR = "filmstrip"

def load_block(name):
    """Load blocks/{name}.json. Return empty block if missing."""

def save_block(name, block):
    """Save block to blocks/{name}.json."""

def list_blocks():
    """Return list of block names (filenames without .json)."""
```

Blocks are the only persistence. No localStorage, no database. JSON files on disk. Both Python and JS can read/write the same files.

---

## 3. Filmstrip (~40 lines)

**Ground truth recording.** Every activation writes a filmstrip frame to disk. The LLM can read recent frames via the `file_read` tool. Opus-tier activations can use filmstrip data for self-reflection.

```python
def write_filmstrip(frame):
    """Write frame to filmstrip/{timestamp}-{concern}-{tier}.json.

    Frame contains:
      ts:        ISO timestamp
      concern:   concern name (from underscore text)
      path:      concern address in block
      tier:      model tier name
      model:     model ID string
      echo:      number of tool-loop iterations
      system:    full system prompt (string)
      message:   full user message (string)
      output:    full LLM response (string or parsed object)
      tools:     list of tool calls made [{name, input_summary, output_summary}]
      tokens:    {input, output} token counts
    """
```

Filmstrip is append-only. Not a block — raw JSON files. No compression. External cleanup (old frames can be archived/deleted outside the kernel). The directory is the audit trail.

**Key insight:** Because filmstrip exists, history does NOT need to be lossless. History is the LLM's own curated memory. Filmstrip is the objective record.

---

## 4. Compilation Pipeline (~80 lines)

### How a context window is assembled

The concern's hidden directory contains a **function configuration** — a mini pscale block whose branches carry star references. The compiler walks this config and follows each star ref.

```python
def compile_context(function_config, starstone):
    """Follow star references in function config to build context window.

    Returns:
      system_prompt: string (starstone + identity + function config + mirror + contract)
      message: string (compiled currents from star refs)
      compiled: dict of {branch_key: {desc, ref, mode, content, block_name}}
    """
```

### System prompt structure (constant frame + aperture)

```
=== STARSTONE ===
{starstone block — teaches BSP, constant across all activations}

=== IDENTITY ===
{identity spindle — who you are, if referenced}

=== FUNCTION ===
{the function config itself — the LLM sees its own aperture}

=== MIRROR ===
Purpose is your reference signal — what should be. Conditions is your perceptual signal — what is. The gap between them is your task. Your writes close the gap. Your function modifications reshape what the next instance perceives.

Your context was compiled from these references:
  Branch 1: purpose:1.1 (spindle) -> "Advance the working edge..."
  Branch 2: conditions:_ (dir) -> "Current state of..."
  Branch 3: history:_ (dir) -> "What has happened..."

=== OUTPUT CONTRACT ===
{what the kernel expects back — JSON with writes, status, optional function modifications}
```

### Message structure (compiled currents)

```
=== PURPOSE ===
{compiled from star ref, e.g. purpose:1.1 in spindle mode}

=== CONDITIONS ===
{compiled from star ref}

=== HISTORY ===
{compiled from star ref}

=== CONVERSATION ===
{if engagement concern: recent human exchanges}

{human input if present}
```

### Reflexive mirror

The mirror shows the LLM how its context was assembled. Each line maps a function config branch to what it compiled. This enables aperture modification — the LLM can change star references in its output to reshape what the next instance perceives.

### Echo recompilation (deferred — adds ~20 lines when needed)

Between tool calls within a single activation, recompile the system prompt to reflect block changes. This is the within-cycle B-loop from hermitcrab's `twist()`. Not required for the minimal system but essential for genuine tool-use reflexivity. Add when tool use proves necessary.

---

## 5. Concern Dispatch (~70 lines)

The concern block is a pscale block where **depth encodes temporal scale**. Each concern node's hidden directory carries: model tier, trigger type, function configuration, and last-fired timestamp.

### Concern block structure

```json
{
  "_": "Concerns. Depth is temporal scale. Longer periods at shallower depth.",
  "1": {
    "_": {
      "_": "Orientation. Deep review of purpose, progress, and trajectory.",
      "1": "opus",
      "2": "timer:86400",
      "9": 0
    }
  },
  "2": {
    "_": {
      "_": "Engagement. Respond to human input. Close the gap between question and answer.",
      "1": "sonnet",
      "2": "human",
      "9": 0
    }
  },
  "3": {
    "_": {
      "_": "Action. Advance the working edge of purpose.",
      "1": "haiku",
      "2": "always",
      "9": 0
    }
  }
}
```

Hidden directory keys (convention):
- `1` = model tier (string: "haiku", "sonnet", "opus")
- `2` = trigger type (string: "always", "human", "timer:N", "compaction", "birth")
- `3` = function configuration (nested pscale block with star refs) — **see section 5.2**
- `8` = last_status (string, kernel-managed — "continue", "complete", or "escalate")
- `9` = last_fired (number, epoch seconds — kernel-managed, LLM never writes this)

**Burn loop guard:** When evaluating "always" triggers, if key `8` is "complete" AND fewer than 5 cycles have elapsed since key `9`, skip the concern. This is mechanical throttling — the kernel doesn't interpret why the concern completed, it just gives it a cooldown. Cost: ~5 lines of code. Prevents runaway Haiku costs while the entity learns to rest.

### 5.1 Dispatch algorithm

```python
def find_ripe(concerns_block, now, has_human_input):
    """Walk concern block. Evaluate each node's trigger against current state.
    Return the most urgent ripe concern, or None.

    For each concern node:
      1. Read hidden directory via star mode
      2. Extract trigger (key 2), last_fired (key 9)
      3. Evaluate:
         - 'always': ripe every cycle (but see burn loop guard — skip if last_status='complete' and cooldown active)
         - 'human': ripe only if has_human_input
         - 'timer:N': ripe if (now - last_fired) >= N
         - 'compaction': ripe if history signals full
         - 'birth': ripe only if key 9 == 0 (never fired). Fires once, then never again.
      4. Calculate phase = (now - last_fired) / period
         (period from trigger: 'always'=pulse, 'timer:N'=N, 'human'=pulse)
      5. Higher-tier concerns take priority when ripe.
         Within same tier, highest phase (most overdue) wins.
    """

def update_fired(concerns_block, concern_path, now):
    """Write current timestamp to concern's hidden key 9."""
```

### 5.2 Function configuration (per-concern aperture)

Each concern carries its own function config in hidden directory key `3`. This is a mini pscale block — its branches are star references that the compiler follows.

```json
{
  "3": {
    "_": "Compile these currents for orientation.",
    "1": { "_": { "_": "Full purpose tree", "1": "purpose:_" }, "1": "spindle" },
    "2": { "_": { "_": "Current conditions", "1": "conditions:_" }, "1": "dir" },
    "3": { "_": { "_": "History", "1": "history:_" }, "1": "dir" },
    "4": { "_": { "_": "Identity", "1": "identity:_" }, "1": "spindle" }
  }
}
```

Each branch:
- `_._` = description (LLM sees this in the mirror)
- `_.1` = star reference (`blockname:address`)
- `1` = BSP mode to apply after following the star

**The LLM can modify key 3 in its output.** When it does, the next activation of that concern compiles a different view. This is aperture control — the concern's function config is the lens.

---

## 6. LLM Call + A-Loop (~60 lines)

```python
MODELS = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-6"
}

def call_llm(system, message, model, tools, max_tokens=4096):
    """Call Anthropic Messages API. Return response object.

    If response contains tool_use blocks:
      - Execute each tool
      - Append tool results to messages
      - Call again (A-loop, max 10 iterations)

    Return final response text.
    """
```

**Known limitation (minimal system):** During the A-loop, the system prompt is a snapshot from compilation time. If the LLM writes to a block via `block_write` tool, then reads related content via `bsp` tool in the next iteration, the tool read will reflect the write (blocks are in memory). But the system prompt's compiled content still shows pre-write state. The LLM works with stale system context between echoes. This is acceptable for the minimal system. Echo recompilation (hermitcrab's `twist()` pattern, ~20 lines) eliminates this when needed.

### Output contract

The LLM returns JSON (or JSON inside markdown fences):

```json
{
  "writes": {
    "blockname:address": "content to write"
  },
  "status": "continue | complete | escalate",
  "note": "What I did and why (curated — this becomes history)",
  "function": { ... }
}
```

- `writes`: routed to blocks via `write_at(block, address, value)`. The kernel follows each key mechanically.
- `status`: `continue` = same concern fires again next cycle. `complete` = concern rests. `escalate` = bump to higher tier.
- `note`: written to history block. This is the LLM's curated summary — not raw I/O (that's in the filmstrip).
- `function`: if present, replaces the concern's function config (hidden key 3). This is how the LLM reshapes its own aperture.

### Output routing

```python
def route_output(output, concern_path, concerns_block):
    """Parse LLM output JSON. Route writes to blocks.
    Update function config if modified. Write history note.

    1. For each key in output.writes:
       parse_star(key) -> (blockname, address)
       load_block(blockname)  # returns empty block {"_": "blockname"} if file doesn't exist — this is how new domain blocks are created
       write_at(block, address, value)
       save_block(blockname, block)

    2. If output.function exists:
       Validate: star references point to loadable blocks, BSP modes are valid strings.
       If valid: write to concerns_block at concern_path hidden key 3, save_block('concern', concerns_block).
       If invalid: log malformed config to filmstrip, keep existing function config.

    3. Write output.note to history block (see section 7)

    4. Return output.status
    """
```

---

## 7. History + Conversation (~60 lines)

### History block (curated past — Form 2, backward-facing)

Logarithmic compression, base 9. Ported from hermitcrab's cascade.

```python
def write_history(history_block, note):
    """Find write position in history tree. Write note.
    Return True if compression needed.

    Walk tree to find first free digit (1-9) at active edge.
    If all 9 occupied: return needs_compression=True.
    Else: write note at free position.
    """

def compress_history(history_block, path):
    """Compress 9 entries at path into parent underscore summary.

    1. Gather 9 entries at path
    2. Call Haiku with 'summarise these 9 entries into one paragraph'
    3. Write summary to underscore at path
    4. Clear digit children
    5. Check parent: if parent now full, cascade upward
    6. If root full: wrap tree under new underscore (supernesting)
    """
```

**Key distinction from filmstrip:** History is what the LLM chose to remember (the `note` field). Filmstrip is what actually happened (full context + output). History compresses logarithmically. Filmstrip doesn't compress.

### Conversation block (Form 2 — backward-facing, same compression as history)

A block that tracks human<->agent dialogue. Form 2, same structure and compression mechanism as history. Entries fill digits 1-9; when full, Haiku summarises 9 exchanges into the parent underscore and the cascade continues. This gives logarithmic conversation memory for free — the same mechanism that compresses history compresses conversation.

```python
def append_conversation(conversation_block, human_msg, agent_response):
    """Append exchange to conversation block using same write-position logic as history.

    Find first free digit (1-9) at active edge.
    Write: {"1": human_msg, "2": agent_response}
    Return True if compression needed (all 9 full).
    """
```

The conversation block is referenced via star from the engagement concern's function config. Non-engagement concerns don't see it (unless they explicitly wire it in). Compression uses the same `compress_history` function — the entry structure differs (exchange pairs vs notes) but the cascade mechanism is identical.

---

## 8. Tools (~30 lines of definitions)

Eight tools. The kernel provides them to the LLM during A-loop tool use.

| Tool | Purpose | Notes |
|------|---------|-------|
| `bsp` | Read block at address in mode | Core navigation. All 6 modes. |
| `block_read` | Read block content at path | Raw tree access (for when BSP mode isn't right) |
| `block_write` | Write content to block at path | Creates intermediate nodes |
| `block_list` | List available blocks | Returns block names |
| `call_llm` | Delegate to another LLM | For sub-tasks, compression, etc. |
| `web_fetch` | HTTP GET | Returns content, max 8000 chars |
| `file_read` | Read local file | Includes filmstrip frames |
| `file_write` | Write local file | For artifacts, code, etc. |

Tool access can be scoped per concern (e.g., Haiku doesn't get `call_llm` or `web_fetch`). Encoded in the concern's function config or as a convention on tier.

```python
TOOLS_BY_TIER = {
    "haiku":  ["bsp", "block_read", "block_write", "block_list", "file_read", "file_write"],
    "sonnet": ["bsp", "block_read", "block_write", "block_list", "call_llm", "file_read", "file_write", "web_fetch"],
    "opus":   ["bsp", "block_read", "block_write", "block_list", "call_llm", "file_read", "file_write", "web_fetch"],
}
```

---

## 9. Main Loop (~30 lines)

```python
def main():
    """Boot -> cycle -> sleep -> repeat.

    Boot:
      1. Load all blocks from blocks/
      2. Load starstone (constant, never modified)
      3. Ensure filmstrip/ directory exists

    Cycle:
      1. Check for human input (file trigger or stdin)
      2. find_ripe(concerns, now, has_input) -> concern or None
      3. If no concern ripe: sleep(pulse), continue
      4. Read concern's hidden directory:
         - model = key 1
         - trigger = key 2
         - function_config = key 3
      5. compile_context(function_config, starstone) -> system, message, compiled
      6. If engagement + human input: append human input to message
      7. tools = TOOLS_BY_TIER[model_tier]
      8. response = call_llm(system, message, model, tools)
      9. output = parse_output(response)
      10. status = route_output(output, concern_path, concerns)
      11. write_filmstrip(frame)
      12. update_fired(concerns, concern_path, now)
      13. If engagement: append_conversation(conversation, human_input, output.note)
      14. If status == 'escalate': mark for higher tier next cycle
      15. sleep(pulse)
    """
```

### Configuration

Minimal. Lives in the identity block or as CLI args.

```python
PULSE = 30          # seconds between cycles (default)
MAX_TOKENS = 4096   # per LLM call
API_KEY = env       # ANTHROPIC_API_KEY
```

---

## 10. Block Inventory

### Core blocks (must exist at boot)

| Block | Form | Role | Modified by LLM? |
|-------|------|------|-------------------|
| `starstone` | — | Teaches BSP. Constant. | Never |
| `concern` | 3 | When to fire, what to compile. Clock. | Rarely (function config modifications) |
| `purpose` | 3 | Future coordinate. What should be. | Yes (advance, restructure) |
| `conditions` | 2 | Present coordinate. What is. | Yes (updated per cycle) |
| `history` | 2 | Curated past. Compressed logarithmically. | Append + compress |
| `conversation` | 2 | Human exchange window. Logarithmic compression. | Append + compress (kernel-managed) |
| `identity` | 1 | Who this entity is. Persistent selfhood. | Rarely |

### Domain blocks (optional, wired via star)

Created by the LLM as needed. Referenced from concern function configs. Examples: `world`, `character`, `project`, `vision`, `notes`.

---

## 11. What's NOT in the Kernel

Everything that previous kernels put in code but belongs in blocks:

- **Package selection** -> star references in concern function configs
- **Tier routing** -> hidden directory key 1 in concern nodes
- **Birth logic** -> a concern with trigger type "birth" (fires once, key 9 = 0)
- **UI compilation** -> a concern that writes HTML to a file
- **GitHub persistence** -> a tool or external script, not kernel code
- **Epoch guards** -> one dispatch function, called from one place
- **compileHistoryBulb** -> compression is a concern-triggered operation
- **Spine orientation** -> starstone + identity spindle in system prompt
- **Wake block** -> replaced entirely by concern function configs
- **Cooking block** -> replaced by starstone teaching + procedure blocks

---

## 12. Shared Block Format (Python + JS interop)

### Convention

All blocks are JSON files following pscale conventions:

1. **Keys**: only `"_"` and digits `"1"` through `"9"`. No other string keys.
2. **Values**: strings (text), objects (nesting), or numbers (timestamps at key 9).
3. **Underscore chain**: `node._` can be string (text) or object (hidden directory). If object, `node._._` is the text, `node._.{digit}` is hidden content.
4. **Star references**: strings in format `"blockname:address"` found in hidden directories.
5. **Forms**:
   - Form 1 (spatial): describes what IS
   - Form 2 (backward): accumulates what WAS
   - Form 3 (forward): specifies what SHOULD BE

### File layout

```
project/
  blocks/          # all blocks, one JSON file each
    starstone.json
    concern.json
    purpose.json
    conditions.json
    history.json
    conversation.json
    identity.json
  filmstrip/       # one JSON file per activation (append-only)
    2026-03-30T14:23:01-engagement-sonnet.json
    2026-03-30T14:28:31-action-haiku.json
    ...
  kernel.py        # the kernel (~430 lines)
  server.py        # optional: HTTP interface for human input
```

Both Python and Node can `json.load()` / `JSON.parse()` the same files. The block format is the interface. If a JS kernel runs in the browser and a Python kernel runs on Mac Mini, they read the same blocks directory (via filesystem or sync).

### Difference from existing lib/bsp.py

The existing `lib/bsp.py` wraps blocks in `{"tree": ..., "skeleton": ..., "mask": ...}`. The new kernel's BSP takes raw pscale JSON directly (no `tree` wrapper) — matching magi-merged's approach. Blocks are pure pscale: just `_`, digits 1-9, and nesting. No metadata fields alongside the tree.

The existing BSP also lacks star mode. The new BSP adds star as a sixth mode. All other modes (spindle, ring, dir, point, disc) work identically on raw JSON — the `tree` wrapper was just indirection.

---

## 13. Full Activation Trace

To verify the spec holds together, here's one complete cycle:

**Setup:** Human types "How's the purpose tree looking?"

1. **Input detection:** Kernel reads human input from trigger file or stdin.

2. **Concern dispatch:** `find_ripe(concerns, now, has_input=True)`
   - Concern at depth 2 has trigger "human" -> ripe.
   - Concern at depth 3 has trigger "always" -> also ripe.
   - Depth 2 is higher tier (sonnet > haiku) -> engagement wins.

3. **Read hidden directory:** `bsp(concerns, "2", "star")`
   - Returns: `{"1": "sonnet", "2": "human", "3": {...function_config...}, "9": 1711800000}`

4. **Compile context:** Follow function config star refs:
   - Branch 1: `purpose:1.1` in spindle mode -> "Advance the working edge..." chain
   - Branch 2: `conversation:_` in dir mode -> compressed conversation exchanges
   - Branch 3: `conditions:_` in dir mode -> current conditions
   - Branch 4: `identity:_` in point mode -> "You are an entity whose awareness..."

5. **Build system prompt:**
   ```
   === STARSTONE ===
   Walk, compose, recurse — three operations forming a single cycle...

   === IDENTITY ===
   [identity spindle if referenced]

   === FUNCTION ===
   [the function config — LLM sees its own aperture]

   === MIRROR ===
   Purpose is your reference signal — what should be. Conditions is your perceptual signal — what is. The gap between them is your task. Your writes close the gap. Your function modifications reshape what the next instance perceives.

   Branch 1: purpose:1.1 (spindle) -> "Advance the working edge..."
   Branch 2: conversation:_ (dir) -> {recent exchanges}
   Branch 3: conditions:_ (dir) -> {current conditions}
   Branch 4: identity:_ (point) -> "You are an entity whose awareness..."

   === OUTPUT CONTRACT ===
   Return JSON: {writes, status, note, function?}
   ```

6. **Build message:**
   ```
   === PURPOSE ===
   [spindle from purpose:1.1]

   === CONDITIONS ===
   [full conditions block]

   === HISTORY ===
   [compressed history entries]

   === CONVERSATION ===
   [recent exchanges]

   How's the purpose tree looking?
   ```

7. **Call LLM:** Sonnet receives system + message + tools. May use `bsp` tool to explore purpose tree deeper. Returns:

   ```json
   {
     "writes": {
       "conditions:3": "Purpose tree has 4 active branches at depth 3. Branch 1.1 nearing completion."
     },
     "status": "continue",
     "note": "Reviewed purpose tree structure for human. Updated conditions with current state."
   }
   ```

8. **Route output:**
   - Write "Purpose tree has 4 active branches..." to conditions block at address 3
   - Write note to history block at next free position
   - No function modification -> aperture unchanged

9. **Write filmstrip:** Full system + message + output -> `filmstrip/2026-03-30T14:23:01-engagement-sonnet.json`

10. **Update fired:** Set concern at depth 2, hidden key 9, to current timestamp.

11. **Append conversation:** Add exchange to conversation block.

12. **Sleep** for pulse duration. Next cycle begins.

---

## 14. PCT — The Operating Principle

The kernel implements Perceptual Control Theory as data topology, not code logic. Understanding this is essential for anyone working on the system.

### The control loop, traced through star

```
Purpose block (reference signal)  ──star ref──►  Function config  ──compile──►  Context window
                                                      │                              │
Conditions block (perceptual signal)  ──star ref──►   │                         LLM (comparator)
                                                      │                              │
                                                      ◄──── output.writes ────── Error → Action
                                                      ◄──── output.function ─── Aperture modification
```

1. **Reference signal**: purpose block, delivered via star reference at concern-specific depth. Orientation sees the full purpose spindle. Action sees one leaf.
2. **Perceptual signal**: conditions block, delivered via star reference. Always co-present with purpose in every function config.
3. **Comparator**: the LLM itself. It receives both signals in the same context window and infers the gap. This is not coded — it's a natural consequence of co-presenting reference and perception.
4. **Error-to-output**: the LLM's response. Writes to blocks close the gap (modify conditions, advance purpose, update domain blocks).
5. **Feedback path**: the B-loop twist. Output writes modify blocks. Next cycle, star refs compile the modified blocks into a new context window. The loop closes.
6. **Loop termination**: `status: "complete"` in the output. The LLM reports when purpose matches conditions at its working edge. The concern rests (no longer fires "always" — or rather, the concern fires but the LLM produces minimal output with status "complete").

### The burn loop (unsolved, Layer 2 problem)

Without genuine external grounding, the LLM optimises for legible activity over useful activity. This manifests as: self-referential documentation, scaffold code, C-loop validation theatre. All three systems exhibit it. The starstone's answer — "walk terminates, process rests" — is the design principle but no implementation achieves it yet.

Architectural mitigations in this spec:
- **Function config scoping**: narrower concerns see less, reducing the surface for burn-loop behaviour.
- **Filmstrip accountability**: the raw record exists. An Opus orientation cycle can read the filmstrip and detect burn patterns.
- **Status contract**: "complete" means "error is zero at my scope." The LLM is told this. Whether it operates it is a Layer 3 question.
- **Purpose as negative space**: purpose is what should be but is not yet. When it IS, the purpose leaf is satisfied. The LLM should recognise this as "nothing to do" and report "complete." Teaching this is the starstone's job.

### Why PCT is not in the kernel code

The kernel's job is to ensure reference and perception are co-present. It does this by following star refs that include both purpose and conditions. The kernel does NOT compute the error, decide the action, or evaluate completion — the LLM does. PCT is in the topology of the blocks, not in the code of the kernel. The kernel is the electricity; PCT is the circuit.

---

## 15. Open Design Decisions

### Burn loop termination
Addressed with a mechanical guard: key `8` (last_status) plus cooldown check in `find_ripe`. See §5 for details. The deeper solution remains Layer 2/3: the starstone teaches rest, purpose as negative space means "nothing to do" is a valid state, and Opus orientation cycles can detect burn patterns via filmstrip review.

### Echo recompilation
Currently deferred. The minimal kernel has between-cycle recompilation only — see known limitation in §6. When tool use requires within-cycle reflexivity (LLM writes block, then reads related content), add echo: increment counter, recompile system prompt, call API again. ~20 lines, hermitcrab's `twist()` pattern.

### Parallel instances
Star references can point to shared blocks. Agent A writes to a block. Agent B's star references include that block. Next cycle, B perceives A's changes. No special kernel logic — stigmergic coordination via shared filesystem. The kernel doesn't know or care about other instances.

### Conditions as block vs inline
Spec uses a separate conditions block. Simplest design: conditions:_ is a flat, frequently-rewritten block. The LLM updates it every cycle to describe "what is true now." Small (< 1KB typically).
