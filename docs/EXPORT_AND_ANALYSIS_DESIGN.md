# Export and Analysis of Conversation Content - Design Document

🌐 **Language / 语言**: [English](EXPORT_AND_ANALYSIS_DESIGN.md) | [中文](EXPORT_AND_ANALYSIS_DESIGN.zh-CN.md)

> ⚠️ **Outdated document (v4.1.5 addendum)**: This document describes the V3.x engine design (single cursor `processed_lines`, schema 3.4.0, 4 CLI modes).
> Since V4.0.0 it has changed to dual cursors (`exported_lines`/`committed_lines`), schema 3.5.0, 7 CLI modes. All source line-number references are now invalid.
> The current system behavior is governed by `CLAUDE.md` + `.claude/skills/evolution/` + `docsV3/VERSION_HISTORY.md`.

> **Version**: 3.9.0
> **Date**: 2026-08-01
> **Author**: lemen
> **Status**: Design complete, fixed and verified

---

## Version History

| Version | Date | Main changes |
|---------|------|--------------|
| 3.9.0 | 2026-08-01 | Added `/evolution-init` pre-check to prevent an accidental reset |
| 3.8.0 | 2026-08-01 | Removed inline code in favor of referencing source; added the v3.8.0 verification mechanisms (file consumption consistency check + cross-process file lock); corrected multiple descriptions that did not match the code, including `find_jsonl_file`/`compute_project_hash`/`estimate_tokens`/`parse_jsonl`/`ConversationEntry`/`sync-state.json` and others |
| 3.3.0 | 2026-07-31 | Fixed JSON serialization crash, incremental unit drift, Windows encoding, underestimated token counts (CJK coefficient 1.5→1.0), cleanup safety, file handle leaks, and other issues |
| 3.2.1 | 2026-07-30 | Updated pagination parameter: 80K → 150K (based on attention research) |
| 3.2.0-draft | 2026-07-29 | Initial design, based on the 200K window assumption |

---

## Key Changes (v3.3.0)

**Token estimation correction:**

| Parameter | v3.2.1 | v3.3.0 | Rationale |
|-----------|--------|--------|-----------|
| **CJK coefficient** | 1.5 chars/token | **1.0 chars/token** | Matches actual testing (measured ~1.0) |
| **Target chunk size** | 150K | **90K** | 90K × 1.68 ≈ 150K actual, within the 200K hard cap |
| **Hard cap** | 200K | **200K** | Unchanged |
| **Minimum** | 40K | **40K** | Unchanged |
| **Estimated chunk count** | 2-3 | **5-6** | Filtered total ~371K (estimate basis); split at a 90K target and constrained by turn boundaries, actually 5-6 |

**Basis notes (unified terminology):**

- **Estimated tokens**: `estimate_tokens` computes a weighted value at 4 chars/token for English/code and 1.0 chars/token for CJK,
  and is the metric the paginator actually uses. Target chunk size 90K and hard cap 200K both refer to this estimated value.
- **Actual consumed tokens**: the number of tokens the model truly bills/occupies, empirically about 1.5-1.7 times the estimate
  (for CJK-dense content, 90K estimated ≈ 140-150K actual). Use the actual value when planning the sub agent window.
- All "90K / 371K" in this document are on the estimate basis; "140-150K" is on the actual basis. The two are no longer mixed.

**Reason for the correction:**

v3.2.1's 150K **estimate** → ~250K actual (**exceeds the 200K hard cap**)
v3.3.0's 90K **estimate** → ~150K actual (**within the 200K hard cap**)

**Actual test verification (15MB JSONL):**
- ✅ Each chunk is about 85-90K (estimated)
- ✅ About 140-150K actual (within the 200K hard cap)
- ✅ No chunk exceeds 200K

---

| Metric | v3.2.0 (5 chunks) | v3.2.1 (3 chunks) | Improvement |
|--------|-------------------|-------------------|-------------|
| Full export time | ~5-7 minutes | ~3-4 minutes | **~40%** |
| Cross-chunk knowledge fragmentation risk | Medium (5 cuts) | Low (3 cuts) | **Significantly improved** |

**Decision rationale:**

1. **Attention dilution research**:
   - The **"Lost in the Middle" paper** (Liu, Lin, Hewitt, Paranjape, Bevilacqua, Petroni, Liang, 2023, arXiv:2307.03172) found that LLMs exhibit a U-shaped attention curve
   - Information at the beginning and end of the context is processed best, while information in the middle is most easily ignored

2. **Distinction between retrieval and synthesis**:
   - **Retrieval tasks** (finding a specific fact): long context performs very well, even at 1M+
   - **Synthesis/analysis tasks** (understanding, extracting, summarizing): degrade noticeably
   - Evolution is a synthesis/analysis task and needs to care about attention quality

3. **Rule of thumb for effective context**:
   - Effective context for retrieval tasks: about 70-80% of the maximum window
   - **Effective context for synthesis/analysis tasks: about 20-30% of the maximum window**
   - For a 1M window: synthesis effective is about 200-300K

## The 90K calculation (v3.3.0)

Effective context 200-300K (synthesis task) - other allocations 98K (8K instructions + 10K read + 10K write + 20K output + 50K overhead) = chunk content cap 102-202K, take ~90K as the target (after the v3.3.0 CJK coefficient correction).

```
1M window allocation:
├── chunk content:         90K  (target)
├── Analysis instructions: ~8K  (prompt template)
├── Knowledge base reads:  ~10K (kb-index + 5-6 detail files)
├── Knowledge base writes: ~10K (extracted knowledge)
├── Output space:          ~20K (larger chunks extract more knowledge)
├── Model internal overhead: ~50K (system prompt, tool definitions, etc.)
├── Safety margin:         ~812K (remaining, extremely ample)
── Actual utilization:     ~19% (188K/1000K, well within the safe zone)
```

**Conclusion**: 90K is the balance point under a 1M window where "enough fits and it digests well" (after the CJK coefficient correction).

---

## 0. Preliminary Data Analysis

Before designing the solution, a comprehensive analysis of the actual JSONL file was performed. The key findings follow:

### 0.1 File Overview

| Metric | Value |
|--------|-------|
| File path | `~/.claude/projects/<project-hash>/<session-uuid>.jsonl` |
| File size | 14 MB |
| Total lines | 5,232 lines |
| Time span | 2026-06-29 ~ 2026-07-30 (about 31 days) |

### 0.2 Entry Type Distribution

| Type | Count | Description |
|------|-------|-------------|
| assistant | 2,015 | AI replies (including text/thinking/tool_use blocks) |
| user | 1,078 | User messages (including text/tool_result/image blocks) |
| file-history-snapshot | 326 | File history snapshots (metadata, ignorable) |
| system | 305 | System messages |
| last-prompt | 300 | Most recent prompt (metadata, ignorable) |
| mode / permission-mode / ai-title | 291 each | Mode/permission/title (metadata, ignorable) |
| attachment | 251 | Attachments |
| queue-operation | 78 | Queue operations (metadata, ignorable) |
| file-history-delta | 9 | File deltas (metadata, ignorable) |

### 0.3 Content Block Distribution

**assistant content blocks (4,015):**
- tool_use: 793 (tool calls, such as Bash/Edit/Write/Read)
- thinking: 776 (reasoning process)
- text: 446 (text replies)

**user content blocks:**
- tool_result: 793 (tool return results)
- string: 248 (user directly-entered text)
- text: 37 (text blocks)
- image: 15 (images)

**Tool call distribution:** Bash(294) > Edit(178) > Write(112) > Read(107) > Agent(45) > GitHub MCP(33) > WebSearch(12)

### 0.4 Token Estimation (key constraint)

| Content category | Estimated tokens | Description |
|------------------|------------------|-------------|
| tool_use input | ~251K | Tool call arguments (commands, file contents, etc.) |
| tool_result output | ~191K | Tool return results (command output, file contents, etc.) |
| user_text | ~114K | User direct input |
| assistant_text | ~101K | AI text replies |
| thinking | ~60K | AI reasoning process |
| **Total** | **~716K** | About 72% of the 1M raw window, far exceeding the synthesis effective context (200-300K) |
| After filtering (drop thinking + tool_result) | ~465K | Still exceeds the synthesis effective context (200-300K) |

**Core contradiction: 716K tokens need to be analyzed, but the sub agent context window is 1M tokens, while the effective context for synthesis/analysis tasks is about 200-300K, so pagination is still required.**

---

## 1. Architecture Design

### 1.1 Overall Architecture

```
┌─────────────────────────────────────────────────────┐
│                Main Agent (User Interaction Layer)    │
│  Receives /evolution-init or /evolution              │
│  Dispatches sub agent, displays final summary        │
└──────────────────────┬──────────────────────────────┘
                       │ triggers
                       ▼
┌─────────────────────────────────────────────────────┐
│           Sub Agent (Analysis Coordination Layer)     │
│                                                      │
│  1. Calls evolution-export.py to parse JSONL         │
│  2. Obtains the paginated conversation summaries     │
│  3. Analyzes page by page, extracts knowledge        │
│  4. Merges results, writes to the knowledge base     │
│  5. Updates the sync state                           │
└──────┬────────────────┬─────────────────────────────┘
       │                │
       ▼                ▼
┌──────────────┐  ┌──────────────────┐
│ export.py    │  │ knowledge-base/  │
│ (Python script) │ │ (8 KB files)    │
│              │  │                  │
│ - Path discovery │ │ - facts.md    │
│ - JSONL parse│  │ - pitfalls.md    │
│ - Content filter │ │ - state.md    │
│ - Paginated output │ │ - ...       │
│ - State mgmt │  │                  │
└──────────────┘  └──────────────────┘
       │
       ▼
┌──────────────┐
│ .evolution/  │
│ (state dir)  │
│              │
│ sync-state   │
│ .json        │
│ chunks/      │
│   chunk-00.md│
│   chunk-01.md│
│   ...        │
└──────────────┘
```

### 1.2 Data Flow

```
JSONL raw file (14MB / 5232 lines)
        │
        ▼ evolution-export.py --mode full
        │
    Parse + Filter + Paginate
        │
        ├─→ chunk-00.md (~90K tokens estimated)
        ├─→ chunk-01.md (~90K tokens estimated)
        ├─→ chunk-02.md (~90K tokens estimated)
        ├─→ chunk-03.md (~90K tokens estimated)
        └─→ chunk-04.md (~11K tokens estimated)
              │
              ▼ Sub Agent reads and analyzes page by page
              │
         Knowledge extraction + deduplication
              │
              ▼
         Knowledge base write (8 .md files)
              │
              ▼
         sync-state.json update
```

### 1.3 Component Design

| Component | Responsibility | Technology choice |
|-----------|----------------|-------------------|
| `evolution-export.py` | JSONL parsing, filtering, pagination, state management | Python 3.x (standard library, no dependencies) |
| Sub Agent coordinator | Invoke analysis page by page, merge results | Claude Code Agent tool |
| `sync-state.json` | Incremental sync state (cursor) | JSON file |
| Knowledge base writer | Write analysis results into 8 .md files | Sub Agent direct file operations |

---

## 2. Full Export Solution

### 2.1 Export Strategy

**Core idea: the Python script does the "heavy work", and the Sub Agent does the "smart work"**

The Python script is responsible for:
1. Discovering the JSONL file path
2. Parsing the JSONL format
3. Filtering noise (metadata entries)
4. Extracting meaningful conversation content
5. Paginating content into ~90K-token chunks
6. Outputting Markdown-format chunk files

The Sub Agent is responsible for:
1. Reading chunk files one by one
2. Analyzing conversation content and extracting knowledge
3. Deduplicating and merging with the existing knowledge base
4. Updating knowledge base files

### 2.2 Content Filtering Strategy

**Content kept (high value):**

| Type | Handling | Retention ratio |
|------|----------|-----------------|
| user text (user input) | Keep in full | 100% |
| assistant text (AI text replies) | Keep in full | 100% |
| thinking (AI reasoning) | Keep summarized (first 200 chars + key decisions) | ~30% |
| tool_use (tool calls) | Keep summarized (tool name + key arguments) | ~40% |
| tool_result (tool returns) | Keep summarized (first 500 chars + error info) | ~20% |

**Content discarded (low value):**

| Type | Reason |
|------|--------|
| mode / permission-mode | Pure state markers, no knowledge value |
| ai-title | Title metadata |
| file-history-snapshot | File snapshots, no knowledge value |
| file-history-delta | File deltas, no knowledge value |
| last-prompt | Duplicate prompt records |
| queue-operation | Queue operation metadata |
| attachment (binary) | Cannot be effectively analyzed |
| system (partial) | System prompts, not user conversation |

**Post-filter token estimate:**

```
user_text:       114K tokens → 114K (100% retained)
assistant_text:  101K tokens → 101K (100% retained)
thinking:         60K tokens →  18K (30% retained)
tool_use:        251K tokens → 100K (40% retained)
tool_result:     191K tokens →  38K (20% retained)
─────────────────────────────────────────────
Total after filtering:            ~371K tokens
```

371K tokens (estimate basis) split at a 90K target ≈ **a mathematical lower bound of 4.1 chunks; in practice 5-6 are produced**——
because pagination must keep conversation turns intact (no cutting in the middle of a turn), and trailing turns below the 40K minimum are merged into the previous page,
so the turn-boundary constraint makes the chunk count higher than the pure division result.

### 2.3 Pagination Strategy

**Pagination goal:** each chunk ~90K tokens; after deducting analysis instructions, knowledge base reads/writes, output space, and model overhead, there is still ~812K of safety margin

**Pagination rules:**

1. **Paginate in chronological order**: preserve the temporal continuity of the conversation
2. **Split at conversation turn boundaries**: do not cut in the middle of a user-assistant pair
3. **Target size: 90K tokens** (estimate basis; actual consumption about 140-150K tokens)
4. **Hard cap: 200K tokens** (do not exceed this value)
5. **Minimum: 40K tokens** (if less, merge into the previous page)

**Conversation turn definition:**
- A "turn" = one user message + all corresponding assistant messages (possibly several)
- tool_use and tool_result pairs belong to the same turn
- thinking blocks belong to the assistant message they are part of

### 2.4 Analysis Strategy

**Page-by-page analysis flow:**

```
For each chunk-N.md:
    1. Sub Agent reads the chunk file
    2. Reads the current knowledge base kb-index.md (to learn the existing knowledge)
    3. Analyzes the conversation content in the chunk
    4. Extracts the following types of knowledge:
       - Key facts → facts.md
       - Pitfall records → pitfalls.md
       - State changes → state.md
       - Learning points → growth-notes.md
       - Prompt improvements → prompt-improvements.md
       - Alignment items → alignment.md
       - Decision records → decisions.md
    5. Deduplicates against existing knowledge
    6. Writes to knowledge base files (marked [D])
    7. Updates kb-index.md
```

**Knowledge extraction criteria:**

| Category | Extraction criteria | Example |
|----------|---------------------|---------|
| Key facts | Environment config, technology choices, dependencies, project identity | "Python 3.12 is installed in WSL" |
| Pitfall records | Error message + cause + solution | "git push timeout → configure a proxy" |
| State changes | Project phase, milestones, completion status | "V3 design complete" |
| Learning points | Technical knowledge points the user can learn | "The difference between Commits vs Releases" |
| Prompt improvements | Suggestions for improving how the user asks questions | "Describe the expected output format more specifically" |
| Alignment items | Items requiring user confirmation | "Use lemen as the author name" |
| Decision records | Technical decisions + rationale | "Choose the Skill system over Slash Command" |

### 2.5 Storage Strategy

**Full analysis result storage location:**

```
<project>/
├── .evolution/                    # Evolution state directory
│   ├── sync-state.json            # Sync state (cursor)
│   ├── export.lock                # Cross-process file lock (v3.8.0)
│   └── chunks/                    # Temporary paginated files
│       ├── chunk-00.md
│       ├── chunk-01.md
│       ├── ...
│       └── chunk-N.md
│
└── evolution/
    └── knowledge-base/            # Knowledge base (final result)
        ├── kb-index.md
        ├── facts.md
        ├── pitfalls.md
        ├── state.md
        ├── growth-notes.md
        ├── prompt-improvements.md
        ├── alignment.md
        └── decisions.md
```

**chunk file lifecycle:** can be deleted after analysis, or kept for traceability.

---

## 3. Incremental Export Solution

### 3.1 Incremental Identification

**Core mechanism: cursor**

Record the position of the last processed JSONL entry in `sync-state.json`:

```json
{
  "version": "3.4.0",
  "last_full_sync": "2026-07-30T11:38:00",
  "last_incremental_sync": "2026-07-30T15:00:00",
  "project_hash": "<project-hash>",
  "files": {
    "~/.claude/projects/<project-hash>/xxx.jsonl": {
      "path": "~/.claude/projects/<project-hash>/xxx.jsonl",
      "sha256": "abc123...",
      "mtime": 1753867200.0,
      "total_lines": 5232,
      "processed_lines": 5232,
      "processed_bytes": 14227502,
      "last_event_timestamp": "2026-07-30T03:39:21.771Z"
    }
  }
}
```

> For the complete structure definition see `evolution-export.py` lines 648-679 (`file_info_to_dict` / `state_to_dict` / `_empty_state`); for field semantics see 4.6.

**Incremental identification algorithm:**

```
1. Read sync-state.json, get each file's processed_lines (physical line number)
2. Parse the subsequent lines of that file starting from processed_lines + 1
3. If there are new entries -> perform incremental export; otherwise skip the file
4. After processing, update processed_lines to the real line number of the last entry
```

**Edge case handling:**

| Case | Handling |
|------|----------|
| JSONL file truncated (line count decreases) | Warn the user, recommend a full re-export |
| sync-state.json does not exist | Treat as a first run, perform full export |
| sync-state.json corrupted | Treat as a first run, perform full export |
| Multiple session files | Process one by one, each maintains its own cursor |
| JSONL file rotated (new file) | Detect the new file, full-export the new file |

### 3.2 Incremental Export

**Incremental export flow:**

```
User inputs /evolution (or /evolution-init has already been executed)
    ↓
Main Agent triggers Sub Agent
    ↓
Sub Agent executes:
  1. python evolution-export.py --mode incremental
     → reads sync-state.json
     → parses starting from processed_lines + 1
     → filter + paginate (usually only 1 chunk)
     → outputs chunk-inc-00.md
  2. Reads chunk-inc-00.md
  3. Analyzes content, extracts knowledge
  4. Deduplicates and merges with the existing knowledge base
  5. Writes to the knowledge base
  6. Updates sync-state.json
  7. Returns a summary
```

### 3.3 Incremental Merge

**Merge strategy: content-based semantic deduplication**

```
For each newly extracted piece of knowledge:
  1. Read kb-index.md to get an overview of the existing knowledge
  2. Determine whether it semantically duplicates an existing entry:
     - Exact duplicate → skip, update the existing entry's timestamp
     - Partial duplicate (same topic, new information) → update the existing entry
     - Conflict (contradictory information) → mark the old entry [X], write the new entry with [D]
     - Entirely new → append to the corresponding knowledge base file
  3. Update kb-index.md
```

**Deduplication judgment rules:**

| Case | Basis | Handling |
|------|-------|----------|
| Exact duplicate | Title + content highly similar (>90%) | Skip |
| Supplementary update | Same topic, new details | Merge, keep both old and new information |
| Information conflict | Same fact, different values | Mark old [X], mark new [D] |
| Entirely new knowledge | No similar entry | Append |

---

## 4. Technical Implementation Details

### 4.1 evolution-export.py Design

**File location:** `<project>/.claude/skills/evolution/evolution-export.py`

**Command-line interface:**

```bash
# Full export
python evolution-export.py --mode full --project-path <project-root> --output .evolution/chunks

# Incremental export
python evolution-export.py --mode incremental --project-path <project-root> --output .evolution/chunks

# View status
python evolution-export.py --mode status --project-path <project-root> --output .evolution/chunks

# Clean up temporary files
python evolution-export.py --mode cleanup --project-path <project-root> --output .evolution/chunks
```

> Command-line arguments: `--mode` (full/incremental/status/cleanup, required), `--project-path` (default `.`), `--output` (output directory, default `.evolution/chunks`). Source: `evolution-export.py` lines 1068-1118 (`main`).

**Output format:** JSON to stdout, for the Sub Agent to parse

```json
{
  "status": "success",
  "mode": "full",
  "total_entries": 5232,
  "processed_entries": 5232,
  "discovered_files": ["~/.claude/projects/<project-hash>/xxx.jsonl"],
  "parsed_files": ["~/.claude/projects/<project-hash>/xxx.jsonl"],
  "chunks": [
    {"file": ".evolution/chunks/chunk-00.md", "tokens_est": 90000, "turns": 22},
    {"file": ".evolution/chunks/chunk-01.md", "tokens_est": 90000, "turns": 25}
  ],
  "sync_state": {
    "version": "3.4.0",
    "last_full_sync": "2026-07-30T11:38:00",
    "last_incremental_sync": null,
    "project_hash": "<project-hash>",
    "files": { "...": { "processed_lines": 5232 } }
  }
}
```

> Field definitions see `evolution-export.py` lines 894-903 (`export_full` return value). Since v3.8.0, `filtered_entries` is no longer output; instead `discovered_files`/`parsed_files` are used for consistency checking; for the `sync_state` structure see 4.6.

### 4.2 Path Discovery Mechanism

Path discovery is done by two functions:

**`compute_project_hash(project_root) -> str`**

Computes the Claude Code project hash. It first replaces `:\` (or `:/`) with `--` (handling Windows drive letters), then replaces the remaining `\` and `/` with `-`.

Example: `<project-root>` -> `<project-hash>`

> Source: `evolution-export.py` lines 138-150

**`find_jsonl_file(project_root) -> list[Path]`**

Discovers all **top-level** JSONL files for the project, returning a list (sorted by modification time ascending, old -> new).

Strategy:
1. Use `compute_project_hash` to compute the project hash
2. Under `~/.claude/projects/<hash>/` use `glob("*.jsonl")` to match `.jsonl` files in the current directory (it does not enter the `subagents` subdirectory, so no extra filtering is needed)
3. Return the list of all discovered JSONL files; return an empty list if none are found

> Source: `evolution-export.py` lines 153-179

> Note: the `generate_path_candidates` (multi-candidate path generation) described in the old document no longer exists in the actual code; v3.8.0 switched to a single `compute_project_hash` encoding + direct directory match.

### 4.3 Format Parsing Logic

**Data structure: `ConversationEntry` (dataclass)**

Each conversation entry is a dataclass with fields: `session`, `line_no` (1-based physical line number), `timestamp`, `role` (`user`/`assistant`), `content` (`list[ContentBlock]`). `ContentBlock` contains `type` (`text`/`thinking`/`tool_use`/`tool_result`), `text`, `truncated`, `is_error`.

> Source: `evolution-export.py` lines 90-109 (`ContentBlock` + `ConversationEntry`)

**`parse_jsonl(file_path, start_line=0) -> Iterator[ConversationEntry]`**

Streaming parse of the JSONL file; the generator yields one `ConversationEntry` per call.

- Signature: `(file_path, start_line=0)`, **no `end_line` parameter** (the old document's `end_line` has been removed)
- Line numbers are **1-based**: `enumerate(f, start=1)`, and parsing starts after `start_line`
- Skips blank lines, lines that fail JSON parsing, and entries that are not of `user`/`assistant` type

> Source: `evolution-export.py` line 201 (signature), lines 186-217 (including the `_try_extract_entry` helper)

**`extract_conversation_content(entry, line_num) -> ConversationEntry`**

Extracts meaningful conversation content from a single JSONL entry; the filtering strategy is:

| Block type | Handling |
|------------|----------|
| text | Keep in full |
| thinking | Summary (first 200 chars + last 100 chars) |
| tool_use | Summary (tool name + key arguments, via `summarize_tool_input`) |
| tool_result | Summary (first 500 chars + last 200 chars of error info) |

> Source: `evolution-export.py` lines 245-306

**`summarize_tool_input(tool_name, tool_input) -> str`**

Generates an input summary by tool type: Bash keeps `command` (truncated to 500 chars), Edit keeps `file_path` + `old_string`/`new_string` (100 chars each), Write keeps `file_path` + `content` (200 chars), Read keeps `file_path`, Agent keeps `prompt` (300 chars), and the rest are JSON-summarized (300 chars). It appends `...` only when truncation actually occurs.

> Source: `evolution-export.py` lines 309-355

### 4.4 Pagination/Truncation Support

**`paginate_entries(entries, target_tokens=90000, max_tokens=200000, min_tokens=40000) -> list[list[ConversationEntry]]`**

Paginates conversation entries into multiple chunks.

Rules:
1. Process in chronological order, first grouping by turn (`group_into_turns`)
2. Keep conversation turns intact (no splitting in the middle of a turn)
3. Target size 90K tokens, hard cap 200K tokens, minimum 40K tokens
4. When a single turn exceeds `max_tokens`, call `split_large_turn` to split it
5. **M1 fix**: when the last chunk is below `min_tokens`, try to merge it into the previous page, **checking first that it does not exceed `max_tokens`**; if over the limit, keep it as an independent chunk
6. **`truncate_entry` fallback**: when a single entry exceeds `max_tokens`, truncate its text block according to the token budget (retention ratio + `[...truncated...]` marker)

> Source: `evolution-export.py` lines 511-574 (`paginate_entries`), lines 438-471 (`truncate_entry`), lines 474-508 (`split_large_turn`)

**`group_into_turns(entries) -> list[list[ConversationEntry]]`**

Groups entries by conversation turn: one turn = user message + all subsequent assistant messages (until the next user message).

> Source: `evolution-export.py` lines 415-435

**`estimate_tokens(text) -> int`**

Roughly estimates the token count of text.

- English/code: about 4 chars/token
- CJK/full-width: about 1.0 chars/token (lowered from 1.5 in v3.3.0 to fix a systematic underestimate)
- **`is_wide_char()` coverage** (extended in v3.8.0): CJK unified ideographs, CJK Extension A, CJK compatibility ideographs, Japanese kana, Korean syllables, full-width characters, with `unicodedata.east_asian_width()` as a fallback for `W`/`F`
- Weighted calculation: `wide_tokens + narrow_tokens`

> Source: `evolution-export.py` lines 362-399 (`is_wide_char` + `estimate_tokens`)

### 4.5 chunk File Format

**chunk Markdown format (v3.8.0):**

- Title: `# Conversation History Export - Chunk {idx}/{total}`
- Meta block: time range, estimated tokens, conversation entry count
- Each entry: `## [Entry N] {timestamp}` + `### {Role}:`
- **All raw text is wrapped in fenced code** (`_wrap_code_block`) to prevent markdown injection (M11); the fence length is dynamically determined by the longest backtick sequence in the text (`_fence`, at least 3 backticks)
- Block type labels: `[text]`, `[thinking]`, `[tool_result]` (errors get `(error)` appended); `tool_use` is wrapped directly without a label

> The old format `## [Turn N]` + `### User:` + raw text has been deprecated; v3.8.0 changed it to `## [Entry N]` and wraps all text in fenced code.

Example:

````markdown
# Conversation History Export - Chunk 0/5

> Time range: 2026-06-29 14:41 ~ 2026-07-01 10:30
> Estimated tokens: ~90,000
> Conversation entries: 15

---

## [Entry 1] 2026-06-29 14:41:58

### User:

[text]
```text
From first principles, what problems do you see with this project?
```

---

## [Entry 2] 2026-06-29 14:42:30

### Assistant:

[thinking]
```text
From first principles, this project has several key issues that need consideration...
```

[tool_use]
```text
[Tool: Bash]
Command: ls -la <project-root>/
```

[text]
```text
Now I'll analyze the structure of this project...
```

---
````

> Source: `evolution-export.py` lines 596-641 (`turn_to_markdown`), lines 581-593 (`_fence` + `_wrap_code_block`)

### 4.6 State Management

**sync-state.json full structure (v3.8.0):**

> Note: the `version` field records the version number of the sync-state data structure / export logic (currently 3.4.0), used for migrating old state in later versions; its semantics are independent of the document version number.

```json
{
  "version": "3.4.0",
  "last_full_sync": "2026-07-30T11:38:00",
  "last_incremental_sync": "2026-07-30T15:00:00",
  "project_hash": "<project-hash>",
  "files": {
    "~/.claude/projects/<project-hash>/xxx.jsonl": {
      "path": "~/.claude/projects/<project-hash>/xxx.jsonl",
      "sha256": "abc123...",
      "mtime": 1753867200.0,
      "total_lines": 5232,
      "processed_lines": 5232,
      "processed_bytes": 14227502,
      "last_event_timestamp": "2026-07-30T03:39:21.771Z"
    }
  }
}
```

Field descriptions:

| Field | Description |
|-------|-------------|
| `version` | Data structure version number |
| `last_full_sync` | Time of the most recent full export (ISO, `null` the first time) |
| `last_incremental_sync` | Time of the most recent incremental export (ISO, `null` if no increment) |
| `project_hash` | Project hash computed by `compute_project_hash` |
| `files` | Dictionary of `FileInfo` keyed by file path |
| `files[k].sha256` | File content SHA256 |
| `files[k].mtime` | File modification time |
| `files[k].total_lines` | Total number of physical lines in the file |
| `files[k].processed_lines` | Real line number of the last processed entry (incremental cursor) |
| `files[k].processed_bytes` | Number of processed bytes |
| `files[k].last_event_timestamp` | Timestamp of the last entry |

> The old structure (`last_sync` / `file_info` / `stats` / `export_history`) has been deprecated. `export-log.json` is no longer maintained; export statistics are aggregated by the caller (Sub Agent).

> Source: `evolution-export.py` lines 648-679 (`file_info_to_dict` / `state_to_dict` / `_empty_state`), lines 112-131 (`FileInfo` / `SyncState` dataclasses), lines 682-727 (`load_sync_state`, including schema validation)

### 4.7 Windows Compatibility

**Key compatibility handling:**

1. **Path separators**: use `pathlib.Path` / `os.path` for joining; do not hardcode `/` or `\`
2. **home directory**: use `Path.home()` to locate `~/.claude/projects`
3. **Encoding**: explicitly specify `encoding='utf-8'` for file reads/writes, with `errors='replace'` for fault tolerance
4. **stdout/stderr encoding**: on Windows, `_reconfigure_stdio()` forces stdout/stderr to use UTF-8 to avoid GBK encoding crashes
5. **Python path**: do not assume `python3`; use `python` (the Windows default)
6. **Cross-platform file lock**: Windows uses `msvcrt.locking`, Linux/macOS uses `fcntl.flock` (see 4.9)

> Source: `evolution-export.py` lines 1059-1065 (`_reconfigure_stdio`), lines 750-800 (cross-platform file lock)

### 4.8 Error Handling and Fallback

**Error handling matrix:**

| Error scenario | Handling strategy |
|----------------|-------------------|
| Project path does not exist / not a string | `--mode full/incremental` performs an `os.path.isdir` pre-check + `_validate_str` raises `ValueError` |
| JSONL file does not exist | `find_jsonl_file` returns an empty list; export returns `{"status":"error","message":"JSONL file not found"}` |
| A single JSONL line fails to parse | Skip the bad line, print `[WARN]` to stderr |
| sync-state.json corrupted / wrong type | `load_sync_state` falls back to an empty state (`_empty_state`) |
| Inconsistent file consumption | Returns an error when `discovered_files != parsed_files` (see 4.9) |
| Timeout acquiring the file lock | `file_lock` raises `TimeoutError` (default 120s) |
| Uncaught exception | `main` catches it as a fallback, outputs structured JSON error + `[ERROR]` to stderr, exit code 1 |

> Source: `evolution-export.py` lines 807-811 (`_validate_str`), lines 682-727 (`load_sync_state` fault tolerance), lines 1109-1118 (`main` fallback exception)

> Note: the old document's `export_with_fallback` multi-level fallback chain (progressively discarding content when tokens exceed the limit) does not exist in the actual code; in practice single-chunk size is controlled via `paginate_entries` pagination + `truncate_entry` truncation fallback, with no runtime fallback needed.

### 4.9 Verification and Concurrency Safety (new in v3.8.0)

v3.8.0 introduces two correctness guarantees:

**1. File consumption consistency check**

After full / incremental export finishes parsing all JSONL files, it verifies that the sets `discovered_files` (discovered by `find_jsonl_file`) and `parsed_files` (actually parsed) are equal. On a mismatch it returns `status=error` (including `discovered_files` / `parsed_files` fields), avoiding silently skipping files.

> Source: `evolution-export.py` lines 858-865 (`export_full`), lines 976-983 (`export_incremental`)

**2. Cross-process file lock `file_lock`**

The entire export process holds `.evolution/chunks/export.lock` to prevent multiple concurrent export processes from corrupting `sync-state.json` or conflicting over chunk files.

- Windows: `msvcrt.locking` (`LK_NBLCK` non-blocking attempt, looping until timeout)
- Linux/macOS: `fcntl.flock` (`LOCK_EX | LOCK_NB`)
- Timeout defaults to 120s (`LOCK_TIMEOUT`); on timeout raises `TimeoutError`
- `contextmanager` ensures automatic release when the process exits

> Source: `evolution-export.py` lines 750-800 (`file_lock`), line 83 (`LOCK_TIMEOUT` constant), lines 830 / 923 / 1041 (the three `with file_lock(...)` call sites)

---

## 5. Cost Estimation

### 5.1 Token Cost

**Full export (first time):**

| Item | Tokens | Description |
|------|--------|-------------|
| JSONL parsing + pagination | 0 | Executed locally in Python, consumes no LLM tokens |
| chunk file content (actual consumption) | ~371K estimated / about 600K-900K actual | 5-6 chunks × 90K estimated (140-150K actual) |
| Analysis instructions (per chunk) | ~8K | The standard prompt for extracting knowledge |
| Knowledge base reads (per chunk) | ~10K | kb-index.md + 2-3 detail files |
| Knowledge base writes (per chunk) | ~10K | Write the extracted knowledge |
| **Total per chunk** | ~152K (on the estimate basis) | Content + instructions + reads/writes |
| **Total for full export** | ~760K-912K | 5-6 chunks x ~152K |

**Incremental export (daily):**

| Item | Tokens | Description |
|------|--------|-------------|
| Incremental content (assume 100 new turns) | ~43K | Usually 1 chunk |
| Analysis instructions + knowledge base reads/writes | ~28K | Same as above |
| **Total for incremental** | ~71K | 1 chunk |

**Cost estimate (at Claude Sonnet pricing $3/M input, $15/M output):**

| Scenario | Input tokens | Output tokens | Cost |
|----------|--------------|---------------|------|
| Full export (first time) | ~651K-803K | ~109K | ~$3.56 |
| Incremental export (each time) | ~55K | ~16K | ~$0.40 |
| Monthly (1 full + 4 incremental) | - | - | ~$5.16 |

### 5.2 Time Cost

| Scenario | Duration | Description |
|----------|----------|-------------|
| Python script execution (full) | ~3 seconds | Parse 14MB JSONL |
| Python script execution (incremental) | ~1 second | Parse the new lines |
| Sub Agent analysis (per chunk) | ~60-90 seconds | Read + analyze + write (90K estimated / 140-150K actual content) |
| Full export (5-6 chunks) | ~5-9 minutes | Serial analysis |
| Incremental export (1 chunk) | ~1-2 minutes | Single analysis |
| Total full export | ~5-10 minutes | Including script + analysis |
| Total incremental export | ~1-2 minutes | Including script + analysis |

### 5.3 Storage Cost

| Item | Size | Description |
|------|------|-------------|
| chunk temporary files | ~2 MB | 5-6 chunks x ~300-400KB (90K estimated tokens; CJK-dense content is about 1.0 chars/estimated token) |
| sync-state.json | ~2 KB | State file |
| Knowledge base growth (full) | ~10-20 KB | 8 .md files |
| Knowledge base growth (each incremental) | ~2-5 KB | New entries |
| **Total storage overhead** | ~2 MB | Mainly chunk temporary files |

---

## 6. Implementation Steps

### 6.1 Implementation Order

```
Phase 1: Core script (evolution-export.py)
  ├── 1.1 Path discovery mechanism
  ├── 1.2 JSONL parser
  ├── 1.3 Content filtering + extraction
  ├── 1.4 Paginator
  ├── 1.5 chunk file output
  └── 1.6 Command-line interface (--mode full/incremental/status/cleanup)

Phase 2: State management
  ├── 2.1 sync-state.json read/write
  ├── 2.2 Incremental cursor logic (per-file processed_lines)
  └── 2.3 File lock and consistency check (v3.8.0)

Phase 3: SKILL.md integration
  ├── 3.1 Update SKILL.md to add the export command
  ├── 3.2 Define the Sub Agent analysis instruction template
  └── 3.3 Define the knowledge extraction prompt template

Phase 4: Analysis coordination
  ├── 4.1 Sub Agent page-by-page analysis flow
  ├── 4.2 Knowledge deduplication and merge logic
  └── 4.3 Automatic kb-index.md update

Phase 5: Testing and optimization
  ├── 5.1 Full export test
  ├── 5.2 Incremental export test
  ├── 5.3 Edge case test
  └── 5.4 Performance optimization
```

### 6.2 Acceptance Criteria

| Acceptance item | Criterion | Verification method |
|-----------------|-----------|---------------------|
| Path discovery | Can correctly discover the current project's JSONL file | `python evolution-export.py --mode status` |
| Full export | Generates 5-6 chunk files, total tokens ~371K (estimate basis) | Check the `.evolution/chunks/` directory |
| Content filtering | Discards metadata entries, keeps user/assistant | Check chunk file contents |
| Pagination correctness | Each chunk is between 40K-200K tokens | Check the token estimate in each chunk file header |
| Incremental identification | Correctly identify the number of new lines | Run incremental export after modifying the JSONL |
| State management | sync-state.json is updated correctly | Check the JSON content |
| Knowledge extraction | Extract meaningful knowledge from the conversation | Check changes in the knowledge base files |
| Deduplication | No duplicate entries are produced | Compare the knowledge base before and after |
| Windows compatibility | Runs normally on Git Bash + Windows | Test on Windows 11 |
| Error handling | Various exceptional cases are handled reasonably | Simulate error scenarios |

### 6.3 Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| JSONL format changes | Medium | High | Parser fault-tolerant design, skips unparseable lines |
| Path encoding mismatch | Low | High | compute_project_hash encoding match + return an empty list and warn when not found |
| Inaccurate token estimation | High | Medium | Leave a 20% margin (target 90K, cap 200K) |
| Low knowledge extraction quality | Medium | High | Human review mechanism ([D] marker) + prompt optimization |
| Sub Agent context overflow | Low | High | Conservative pagination size + fallback mode |
| Multiple session files | Medium | Medium | Process one by one, each maintains its own cursor |
| Missing Python environment | Low | High | The script uses only the standard library, no third-party dependencies |

---

## 7. Sub Agent Analysis Instruction Templates

### 7.1 Full Analysis Instruction

```markdown
# Evolution Knowledge Extraction Task

You are analyzing Claude Code conversation history to extract knowledge for the Evolution knowledge base.

## Task

Read the following chunk file, analyze the conversation content in it, and extract valuable knowledge:

1. Read the chunk file: {chunk_file_path}
2. Read the knowledge base index: evolution/knowledge-base/kb-index.md
3. Based on the index, decide which knowledge base detail files to read (1-2)
4. Analyze the conversation in the chunk and extract the following types of knowledge:
   - Key facts (facts.md): environment config, technology choices, dependencies
   - Pitfall records (pitfalls.md): error + cause + solution
   - State changes (state.md): project phase, milestones
   - Learning points (growth-notes.md): knowledge points the user can learn
   - Prompt improvements (prompt-improvements.md): suggestions for improving questions
   - Alignment items (alignment.md): items requiring user confirmation
   - Decision records (decisions.md): technical decisions + rationale
5. Deduplicate against existing knowledge
6. Write new knowledge into the corresponding knowledge base files (marked [D])
7. Update kb-index.md

## Rules

- Mark all new entries as [D] (draft)
- Format: `### [D] entry title`
- Skip meaningless conversation (such as chit-chat, tests)
- Focus on: error messages, solutions, technical decisions, user preferences
- If it conflicts with an existing entry: mark the old entry [X], write the new entry with [D]
- Do not modify [V] entries (unless marked [X])

## Output

Return a summary:
- Number of knowledge entries extracted (by category)
- Number of conflicts found
- Entries recommended for user review
```

### 7.2 Incremental Analysis Instruction

```markdown
# Evolution Incremental Knowledge Sync Task

You are analyzing new Claude Code conversation to incrementally update knowledge in the Evolution knowledge base.

## Task

1. Read the incremental chunk file: {chunk_file_path}
2. Read the knowledge base index: evolution/knowledge-base/kb-index.md
3. Based on the index, decide which knowledge base detail files to read
4. Analyze the new conversation and extract new knowledge
5. Deduplicate and merge with the existing knowledge base
6. Update the knowledge base files and index

## Rules

(Same as the full analysis rules)

## Special Notes

- This is an incremental sync; existing knowledge may already be present
- Focus on deduplication to avoid duplicate writes
- If an existing entry needs updating (such as a state change), update it directly
- Return an incremental summary
```

---

## 8. Complete Execution Flow Example

### 8.1 Full Export Flow

```
User inputs: /evolution-init
    │
    ▼
Main Agent: triggers Sub Agent
    │
    ▼
Sub Agent executes:
    │
    ├─ Step 1: Run the Python script
    │  $ python .claude/skills/evolution/evolution-export.py --mode full --project-path <project-root>
    │  → outputs JSON:
    │    {
    │      "status": "success",
    │      "chunks": [
    │        {"file": ".evolution/chunks/chunk-00.md", "tokens_est": 90000},
    │        {"file": ".evolution/chunks/chunk-01.md", "tokens_est": 90000},
    │        {"file": ".evolution/chunks/chunk-02.md", "tokens_est": 90000},
    │        {"file": ".evolution/chunks/chunk-03.md", "tokens_est": 90000},
    │        {"file": ".evolution/chunks/chunk-04.md", "tokens_est": 11000}
    │      ],
    │      "sync_state": {...}
    │    }
    │
    ├─ Step 2: Page-by-page analysis
    │  For each chunk:
    │    - Read the chunk file
    │    - Read kb-index.md
    │    - Read knowledge base files as needed
    │    - Analyze conversation content
    │    - Extract knowledge
    │    - Write to the knowledge base
    │    - Update the index
    │
    ├─ Step 3: Update sync state
    │  - sync-state.json has already been updated by the Python script
    │
    └─ Step 4: Return a summary
       "Full export complete:
        - Processed 5,232 records
        - Analyzed 5-6 pages
        - Extracted 23 knowledge entries (8 facts / 5 pitfalls / 3 state / 4 learning / 1 Prompt / 2 decisions)
        - All marked as [D]
        - Recommended for review: ..."
    │
    ▼
Main Agent: displays the summary to the user
```

### 8.2 Incremental Export Flow

```
User inputs: /evolution
    │
    ▼
Main Agent: triggers Sub Agent
    │
    ▼
Sub Agent executes:
    │
    ├─ Step 1: Run the Python script
    │  $ python .claude/skills/evolution/evolution-export.py --mode incremental --project-path <project-root>
    │  → outputs JSON:
    │    {
    │      "status": "success",
    │      "mode": "incremental",
    │      "new_entries": 150,
    │      "chunks": [
    │        {"file": ".evolution/chunks/chunk-inc-00.md", "tokens_est": 35000}
    │      ]
    │    }
    │
    ├─ Step 2: Analyze the incremental chunk
    │  - Read chunk-inc-00.md
    │  - Read kb-index.md
    │  - Analyze + extract + deduplicate + write
    │
    └─ Step 3: Return a summary
       "Incremental sync complete:
        - 150 new records
        - 3 new knowledge entries extracted
        - 2 existing knowledge entries updated
        - Recommended for review: ..."
    │
    ▼
Main Agent: displays the summary to the user
```

---

## 9. Record of Key Design Decisions

### 9.1 Why use a Python script instead of letting the AI read the JSONL directly?

| Approach | Advantages | Disadvantages |
|----------|------------|---------------|
| AI reads the JSONL directly | No script needed | The 14MB file far exceeds the context; lots of JSON noise; cannot paginate |
| Python script preprocessing | Precise control over filtering/pagination; consumes no tokens; reusable | Requires maintaining the script |

**Decision: Python script preprocessing.** Reason: the raw data of 14MB / 716K tokens cannot fit directly into a 1M context window (the effective context for synthesis tasks is only 200-300K), so preprocessing is mandatory.

### 9.2 Why is the pagination target 90K instead of closer to 1M?

- 1M is the sub agent's raw context window, but the effective context for synthesis/analysis tasks is only about 200-300K (see the "Lost in the Middle" research in the "Key Changes" section)
- The 200-300K effective context must deduct: analysis instructions (~8K) + knowledge base reads (~10K) + knowledge base writes (~10K) + output space (~20K) + model internal overhead (~50K) ≈ 98K
- chunk content cap = effective context (200-300K) - other allocations (98K) = 102-202K, take ~90K as the target (after the v3.3.0 CJK coefficient correction)
- 90K estimated × 1.68 (CJK coefficient correction) ≈ 150K actual usage, about 15% of the 1M window, well within the safe zone
- The hard cap is set to 200K (the upper bound of the synthesis effective zone) to ensure a single chunk does not cross the attention degradation inflection point
- **It is better to pick a conservative value based on effective context than to rely on the raw window size**

### 9.3 Why paginate by conversation turn instead of by fixed line count?

- A fixed line count might cut in the middle of a conversation, losing context
- Paginating by turn preserves semantic integrity
- One turn = one complete user-assistant interaction
- The Sub Agent can see the complete conversation context when analyzing

### 9.4 Why use line_number instead of timestamp as the incremental cursor?

- timestamp may not be unique (multiple records in the same second)
- timestamp may be out of order (in rare cases)
- Line numbers are strictly increasing, unique and ordered (the actual field is `FileInfo.processed_lines`, which records the real line number of the last entry per file)
- A single line number may become invalid when the file is rewritten as a whole, so `sha256` / `mtime` / `last_event_timestamp` are also recorded as checks (see 4.6)

### 9.5 Why not filter out tool_use and tool_result?

- tool_use contains executed commands and edited file contents, an important source of pitfall records
- tool_result contains command output and error messages, a source of key facts
- Filtering them out completely would lose a large amount of valuable knowledge
- The summary strategy (keep the first N chars + error info) balances information retention and token savings

---

## 10. Future Optimization Directions

| Optimization item | Description | Priority |
|-------------------|-------------|----------|
| Parallel analysis | Analyze multiple chunks in parallel (multiple sub agents) | Medium |
| Smart filtering | Dynamically decide the retention ratio based on content value | Medium |
| Vector retrieval | Build a vector index for the knowledge base to support semantic search | Low |
| Auto trigger | Automatically trigger incremental export after detecting N turns of new conversation | Low |
| Multi-project support | Support managing conversation history for multiple projects simultaneously | Low |
| Visual reports | Generate export analysis reports (HTML/Markdown) | Low |
| Knowledge decay | Automatically down-weight old knowledge, mark outdated knowledge [X] | Medium |

---

**End of document**
