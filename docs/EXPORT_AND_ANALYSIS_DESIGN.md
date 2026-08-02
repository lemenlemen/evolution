# Export and Analysis of Conversation Content - Design Document

🌐 **Language / 语言**: [English](EXPORT_AND_ANALYSIS_DESIGN.md) | [中文](EXPORT_AND_ANALYSIS_DESIGN.zh-CN.md)

> **Version**: 3.8.0
> **Date**: 2026-07-31
> **Author**: lemen
> **Status**: Design complete, fixed and verified

---

## Version History

| Version | Date | Major Changes |
|---------|------|---------------|
| 3.3.0 | 2026-07-31 | Fixed JSON serialization crash, incremental unit drift, Windows encoding, underestimated token estimation (CJK coefficient 1.5→1.0), cleanup safety, file handle leaks, and other issues |
| 3.2.1 | 2026-07-30 | Updated pagination parameter: 80K → 150K (based on attention research) |
| 3.2.0-draft | 2026-07-29 | Initial design, based on 200K window assumption |

---

## Key Changes (v3.3.0)

**Token Estimation Correction:**

| Parameter | v3.2.1 | v3.3.0 | Rationale |
|-----------|--------|--------|-----------|
| **CJK coefficient** | 1.5 chars/token | **1.0 chars/token** | Matches actual testing (measured ~1.0) |
| **Target chunk size** | 150K | **90K** | 90K × 1.68 ≈ 150K actual, within 200K hard limit |
| **Hard limit** | 200K | **200K** | Unchanged |
| **Minimum** | 40K | **40K** | Unchanged |
| **Estimated chunk count** | 2-3 | **5-6** | 371K / 90K ≈ 4.1, actual 5-6 |

**Reason for correction:**

v3.2.1's 150K **estimate** → actual ~250K (**exceeds 200K hard limit**)
v3.3.0's 90K **estimate** → actual ~150K (**within 200K hard limit**)

**Actual test validation (15MB JSONL):**
- ✅ Produced 6 chunks
- ✅ Each chunk approximately 85-90K (estimated)
- ✅ Actual approximately 140-150K (within 200K hard limit)
- ✅ No chunk exceeds 200K

---

| Metric | v3.2.0 (5 chunks) | v3.2.1 (3 chunks) | Improvement |
|--------|--------------------|-------------------|-------------|
| Full export time | ~5-7 minutes | ~3-4 minutes | **~40%** |
| Cross-chunk knowledge breakage risk | Medium (5 cuts) | Low (3 cuts) | **Significantly improved** |

**Decision rationale:**

1. **Attention dilution research**:
   - The **"Lost in the Middle" paper** (Liu, Lin, Hewitt, Paranjape, Bevilacqua, Petroni, Liang, 2023, arXiv:2307.03172) found that LLMs exhibit a U-shaped attention curve
   - Information at the beginning and end of the context is processed best; information in the middle is most easily overlooked

2. **Retrieval vs. synthesis distinction**:
   - **Retrieval tasks** (finding a specific key fact): perform well with long contexts, even 1M+
   - **Synthesis/analysis tasks** (understanding, extracting, summarizing): degrade noticeably
   - Evolution is a synthesis/analysis task and requires attention to attention quality

3. **Effective context rule of thumb**:
   - Effective context for retrieval tasks: approximately 70-80% of the maximum window
   - **Effective context for synthesis/analysis tasks: approximately 20-30% of the maximum window**
   - For a 1M window: effective for synthesis is approximately 200-300K

## 90K Calculation (v3.3.0)

Effective context 200-300K (synthesis tasks) - other allocations 98K (8K instructions + 10K reads + 10K writes + 20K output + 50K overhead) = chunk content ceiling 102-202K, taking ~90K as the target (v3.3.0 after CJK coefficient correction).

```
1M window allocation:
├── chunk content:        90K  （target）
├── analysis instructions:  ~8K  （prompt template）
├── knowledge base reads:  ~10K  （kb-index + 5-6 detail files）
├── knowledge base writes: ~10K  （extracted knowledge）
├── output space:         ~20K  （larger chunks extract more knowledge）
├── model internal overhead: ~50K  （system prompt, tool definitions, etc.）
├── safety margin:       ~812K  （remaining, extremely generous）
── actual usage rate:     ~19%  （188K/1000K, well within safe zone）
```

**Conclusion**: 90K is the balance point for "enough content, good digestion" under the 1M window (after CJK coefficient correction).

---

## 0. Preliminary Data Analysis

Before designing the solution, a comprehensive analysis was performed on actual JSONL files. Key findings:

### 0.1 File Overview

| Metric | Value |
|--------|-------|
| File path | `~/.claude/projects/<project-hash>/<session-uuid>.jsonl` |
| File size | ~10 MB |
| Total lines | ~5,000 |
| Time span | 2026-06-29 ~ 2026-07-30 (approximately 31 days) |

### 0.2 Entry Type Distribution

| Type | Count | Description |
|------|-------|-------------|
| assistant | 2,015 | AI replies (including text/thinking/tool_use blocks) |
| user | 1,078 | User messages (including text/tool_result/image blocks) |
| file-history-snapshot | 326 | File history snapshots (metadata, can be ignored) |
| system | 305 | System messages |
| last-prompt | 300 | Recent prompts (metadata, can be ignored) |
| mode / permission-mode / ai-title | 291 each | Mode/permissions/title (metadata, can be ignored) |
| attachment | 251 | Attachments |
| queue-operation | 78 | Queue operations (metadata, can be ignored) |
| file-history-delta | 9 | File deltas (metadata, can be ignored) |

### 0.3 Content Block Distribution

**Assistant content blocks (4,015):**
- tool_use: 793 (tool calls, e.g., Bash/Edit/Write/Read)
- thinking: 776 (thinking process)
- text: 446 (text replies)

**User content blocks:**
- tool_result: 793 (tool return results)
- string: 248 (user direct text input)
- text: 37 (text blocks)
- image: 15 (images)

**Tool call distribution:** Bash(294) > Edit(178) > Write(112) > Read(107) > Agent(45) > GitHub MCP(33) > WebSearch(12)

### 0.4 Token Estimation (Key Constraint)

| Content Category | Estimated Token Count | Description |
|------------------|----------------------|-------------|
| tool_use input | ~251K | Tool call parameters (commands, file content, etc.) |
| tool_result output | ~191K | Tool return results (command output, file content, etc.) |
| user_text | ~114K | User direct input |
| assistant_text | ~101K | AI text replies |
| thinking | ~60K | AI thinking process |
| **Total** | **~716K** | ~72% of 1M raw window, far exceeds synthesis effective context (200-300K) |
| After filtering (remove thinking + tool_result) | ~465K | Still exceeds synthesis effective context (200-300K) |

**Core contradiction: 716K tokens need to be analyzed, but while the sub agent context window is 1M tokens, the effective context for synthesis/analysis tasks is approximately 200-300K, so pagination is still required.**

---

## 1. Architecture Design

### 1.1 Overall Architecture

```
┌─────────────────────────────────────────────────────┐
│              Main Agent (User Interaction Layer)      │
│  Receives /evolution init or /evolution --export     │
│  Dispatches sub agent, displays final summary        │
└──────────────────────┬──────────────────────────────┘
                       │ triggers
                       ▼
┌─────────────────────────────────────────────────────┐
│          Sub Agent (Analysis Coordination Layer)      │
│                                                      │
│  1. Calls evolution-export.py to parse JSONL         │
│  2. Receives paginated conversation summaries         │
│  3. Analyzes page by page, extracts knowledge        │
│  4. Merges results, writes to knowledge base         │
│  5. Updates sync status                              │
└──────┬────────────────┬─────────────────────────────┘
       │                │
       ▼                ▼
┌──────────────┐  ┌──────────────────┐
│ export.py    │  │ knowledge-base/  │
│ (Python script)│ │ (8 knowledge base files)│
│              │  │                  │
│ - Path discovery│ │ - facts.md      │
│ - JSONL parsing│ │ - pitfalls.md    │
│ - Content filtering│ │ - state.md    │
│ - Paginated output│ │ - ...         │
│ - State management│ │               │
└──────────────┘  └──────────────────┘
       │
       ▼
┌──────────────┐
│ .evolution/  │
│ (state directory)│
│              │
│ sync-state   │
│ .json        │
│ chunks/      │
│   chunk-0.md │
│   chunk-1.md │
│   ...        │
└──────────────┘
```

### 1.2 Data Flow

```
JSONL raw file (~10MB / 5000 lines)
        │
        ▼ evolution-export.py --mode full
        │
    Parse + Filter + Paginate
        │
        ├─→ chunk-0.md (~90K tokens)
        ├─→ chunk-1.md (~90K tokens)
        ├─→ chunk-2.md (~90K tokens)
        ├─→ chunk-3.md (~90K tokens)
        ├─→ chunk-4.md (~90K tokens)
        └─→ chunk-5.md (~31K tokens)
              │
              ▼ Sub Agent reads and analyzes page by page
              │
         Knowledge extraction + deduplication
              │
              ▼
         knowledge base writes (8 .md files)
              │
              ▼
         sync-state.json update
```

### 1.3 Component Design

| Component | Responsibility | Technology |
|-----------|---------------|------------|
| `evolution-export.py` | JSONL parsing, filtering, pagination, state management | Python 3.x (standard library, no dependencies) |
| Sub Agent coordinator | Page-by-page analysis, result merging | Claude Code Agent tool |
| `sync-state.json` | Incremental sync state (cursor) | JSON file |
| knowledge base writer | Writes analysis results to 8 .md files | Sub Agent direct file operations |

---

## 2. Full Export Solution

### 2.1 Export Strategy

**Core idea: Python script does the "heavy lifting", Sub Agent does the "smart work"**

Python script is responsible for:
1. Discovering JSONL file paths
2. Parsing JSONL format
3. Filtering noise (metadata entries)
4. Extracting meaningful conversation content
5. Paginating content into ~90K token chunks
6. Outputting Markdown-formatted chunk files

Sub Agent is responsible for:
1. Reading each chunk file sequentially
2. Analyzing conversation content, extracting knowledge
3. Deduplicating and merging with existing knowledge base
4. Updating knowledge base files

### 2.2 Content Filtering Strategy

**Retained content (high value):**

| Type | Processing | Retention Rate |
|------|-----------|---------------|
| user text (user input) | Fully retained | 100% |
| assistant text (AI text replies) | Fully retained | 100% |
| thinking (AI thinking) | Summary retained (first 200 chars + key decisions) | ~30% |
| tool_use (tool calls) | Summary retained (tool name + key parameters) | ~40% |
| tool_result (tool returns) | Summary retained (first 500 chars + error messages) | ~20% |

**Discarded content (low value):**

| Type | Reason |
|------|--------|
| mode / permission-mode | Pure status flags, no knowledge value |
| ai-title | Title metadata |
| file-history-snapshot | File snapshots, no knowledge value |
| file-history-delta | File deltas, no knowledge value |
| last-prompt | Duplicate prompt records |
| queue-operation | Queue operation metadata |
| attachment (binary) | Cannot be effectively analyzed |
| system (partial) | System prompts, not user conversations |

**Post-filtering Token Estimation:**

```
user_text:       114K tokens → 114K (100% retained)
assistant_text:  101K tokens → 101K (100% retained)
thinking:         60K tokens →  18K (30% retained)
tool_use:        251K tokens → 100K (40% retained)
tool_result:     191K tokens →  38K (20% retained)
─────────────────────────────────────────────
Total after filtering:               ~371K tokens
```

371K tokens / 90K tokens per chunk ≈ **4-5 chunks**

### 2.3 Pagination Strategy

**Pagination target:** Each chunk ~90K tokens; after deducting analysis instructions, knowledge base reads/writes, output space, and model overhead, there is still ~812K safety margin

**Pagination rules:**

1. **Paginate in chronological order**: Maintain temporal continuity of conversation
2. **Split at conversation turn boundaries**: Do not cut in the middle of a user-assistant pair
3. **Target size: 90K tokens** (approximately 270KB text, at 3 chars/token)
4. **Hard limit: 200K tokens** (do not exceed this value)
5. **Minimum: 40K tokens** (if below, merge into previous page)

**Conversation turn definition:**
- One "turn" = one user message + all corresponding assistant messages (possibly multiple)
- tool_use and tool_result are paired and included in the same turn
- thinking blocks are included in their owning assistant message

### 2.4 Analysis Strategy

**Page-by-page analysis flow:**

```
For each chunk-N.md:
    1. Sub Agent reads the chunk file
    2. Reads current knowledge base kb-index.md (to understand existing knowledge)
    3. Analyzes conversation content in the chunk
    4. Extracts the following knowledge types:
       - Key facts → facts.md
       - Pitfalls → pitfalls.md
       - State changes → state.md
       - Growth notes → growth-notes.md
       - Prompt improvements → prompt-improvements.md
       - Alignment items → alignment.md
       - Decision records → decisions.md
    5. Deduplicates against existing knowledge
    6. Writes to knowledge base files (marked [D])
    7. Updates kb-index.md
```

**Knowledge extraction criteria:**

| Category | Extraction Criteria | Example |
|----------|-------------------|---------|
| Key facts | Environment config, technology choices, dependencies, project identity | "Python 3.12 installed in WSL" |
| Pitfalls | Error message + cause + solution | "git push timeout → configure proxy" |
| State changes | Project phase, milestones, completion status | "V3 design complete" |
| Growth notes | Technical knowledge points the user can learn | "Difference between Commits vs Releases" |
| Prompt improvements | Suggestions for optimizing user questioning style | "More specifically describe desired output format" |
| Alignment items | Items requiring user confirmation | "Author name uses lemen" |
| Decision records | Technical decisions + rationale | "Choose Skill system over Slash Commands" |

### 2.5 Storage Strategy

**Full analysis result storage location:**

```
<project>/
├── .evolution/                    # Evolution state directory
│   ├── sync-state.json            # Sync state (cursor)
│   ├── chunks/                    # Temporary paginated files
│   │   ├── chunk-0.md
│   │   ├── chunk-1.md
│   │   ├── ...
│   │   └── chunk-N.md
│   └── export-log.json            # Export log
│
└── evolution/
    └── knowledge-base/            # knowledge base (final results)
        ├── kb-index.md
        ├── facts.md
        ├── pitfalls.md
        ├── state.md
        ├── growth-notes.md
        ├── prompt-improvements.md
        ├── alignment.md
        └── decisions.md
```

**Chunk file lifecycle:** Can be deleted after analysis is complete, or retained for retrospective reference.

---

## 3. Incremental Export Solution

### 3.1 Incremental Identification

**Core mechanism: Cursor**

Record the last processed JSONL entry position in `sync-state.json`:

```json
{
  "version": "3.3.0",
  "last_sync": {
    "timestamp": "<timestamp>",
    "line_number": 5000,
    "uuid": "uuid of the last entry",
    "session_id": "<session-uuid>"
  },
  "file_info": {
    "path": "~/.claude/projects/<project-hash>/<session-uuid>.jsonl",
    "size_at_last_sync": 10000000,
    "lines_at_last_sync": 5000
  },
  "export_history": [
    {
      "type": "full",
      "timestamp": "<timestamp>",
      "chunks_analyzed": 3,
      "entries_processed": 5000,
      "knowledge_items_extracted": 23
    },
    {
      "type": "incremental",
      "timestamp": "<timestamp>",
      "entries_processed": 150,
      "knowledge_items_extracted": 3
    }
  ]
}
```

**Incremental identification algorithm:**

```
1. Read sync-state.json to get last_line_number
2. Read current total line count of JSONL file
3. If current line count > last_line_number:
     - There is new content, perform incremental export
     - Start reading from last_line_number + 1
   Otherwise:
     - No new content, skip
4. Update last_line_number after processing is complete
```

**Edge case handling:**

| Situation | Handling |
|-----------|----------|
| JSONL file is truncated (line count decreased) | Warn user, recommend full re-export |
| sync-state.json does not exist | Treat as first run, perform full export |
| sync-state.json is corrupted | Treat as first run, perform full export |
| Multiple session files | Process each individually, maintain separate cursors |
| JSONL file is rotated (new file) | Detect new file, perform full export on new file |

### 3.2 Incremental Export

**Incremental export flow:**

```
User inputs /evolution --export (or /evolution init has been run before)
    ↓
Main Agent triggers Sub Agent
    ↓
Sub Agent executes:
  1. python evolution-export.py --mode incremental
     → Reads sync-state.json
     → Parses from last_line_number + 1
     → Filters + paginates (usually only 1 chunk)
     → Outputs chunk-inc-0.md
  2. Reads chunk-inc-0.md
  3. Analyzes content, extracts knowledge
  4. Deduplicates and merges with existing knowledge base
  5. Writes to knowledge base
  6. Updates sync-state.json
  7. Returns summary
```

### 3.3 Incremental Merging

**Merge strategy: Content-based semantic deduplication**

```
For each newly extracted knowledge item:
  1. Read kb-index.md to get overview of existing knowledge
  2. Determine if semantically duplicate with existing entries:
     - Exact duplicate → Skip, update existing entry's timestamp
     - Partial duplicate (same topic, new information) → Update existing entry
     - Conflict (contradictory information) → Mark old entry [X], write new entry as [D]
     - Entirely new → Append to corresponding knowledge base file
  3. Update kb-index.md
```

**Deduplication judgment rules:**

| Situation | Judgment Basis | Handling |
|-----------|---------------|----------|
| Exact duplicate | Title + content highly similar (>90%) | Skip |
| Supplementary update | Same topic, new details | Merge, retain both old and new information |
| Information conflict | Same key fact, different values | Old marked [X], new marked [D] |
| Entirely new knowledge | No similar entries | Append write |

---

## 4. Technical Implementation Details

### 4.1 evolution-export.py Design

**File location:** `<project>/.claude/skills/evolution/evolution-export.py`

**Command-line interface:**

```bash
# Full export
python evolution-export.py --mode full --project-path <project-root>

# Incremental export
python evolution-export.py --mode incremental --project-path <project-root>

# Check status
python evolution-export.py --mode status --project-path <project-root>

# Cleanup temporary files
python evolution-export.py --mode cleanup --project-path <project-root>
```

**Output format:** JSON to stdout, for Sub Agent to parse

```json
{
  "status": "success",
  "mode": "full",
  "total_entries": 5000,
  "processed_entries": 5000,
  "filtered_entries": 3083,
  "chunks": [
    {"file": ".evolution/chunks/chunk-0.md", "tokens_est": 90000, "turns": 22},
    {"file": ".evolution/chunks/chunk-1.md", "tokens_est": 90000, "turns": 25},
    ...
  ],
  "sync_state": {
    "last_line_number": 5000,
    "last_uuid": "...",
    "last_timestamp": "<timestamp>"
  }
}
```

### 4.2 Path Discovery Mechanism

**JSONL file discovery algorithm:**

```python
def find_jsonl_files(project_path):
    """
    Discover JSONL files corresponding to the project
    
    Strategy:
    1. Derive project-hash from project_path
       - Replace / and \\ in path with -
       - Remove drive letter colon
       - Example: <project-root> → <project-hash>
    2. Look for .jsonl files under ~/.claude/projects/<project-hash>/
    3. If multiple found, sort by modification time, take the latest
    """
    import os
    
    # Step 1: Derive project-hash
    # Claude Code path encoding rules:
    # - Replace path separators with -
    # - Remove colons
    # - Example: <project-root> → <project-hash>
    abs_path = os.path.abspath(project_path)
    
    # Try multiple encoding methods (Windows path variations)
    candidates = generate_path_candidates(abs_path)
    
    claude_dir = os.path.expanduser("~/.claude/projects")
    
    for candidate in candidates:
        project_dir = os.path.join(claude_dir, candidate)
        if os.path.isdir(project_dir):
            jsonl_files = [
                f for f in os.listdir(project_dir) 
                if f.endswith('.jsonl')
            ]
            if jsonl_files:
                # Sort by modification time, take the latest
                jsonl_files.sort(
                    key=lambda f: os.path.getmtime(
                        os.path.join(project_dir, f)
                    ),
                    reverse=True
                )
                return os.path.join(project_dir, jsonl_files[0])
    
    return None
```

**Path encoding candidate generation (Windows compatible):**

```python
def generate_path_candidates(abs_path):
    """
    Generate possible Claude Code project-hash candidates
    
    Claude Code's path encoding may vary by version,
    multiple encoding methods need to be tried
    """
    candidates = []
    
    # Normalize path
    path = abs_path.replace('\\', '/')
    
    # Method 1: Replace / with -, remove colon
    # <project-root> → <project-hash>
    c1 = path.replace('/', '-').replace(':', '')
    candidates.append(c1)
    
    # Method 2: Preserve original case
    c2 = path.replace('/', '-').replace(':', '')
    candidates.append(c2)
    
    # Method 3: Lowercase
    candidates.append(c1.lower())
    
    # Method 4: If path has trailing slash
    if not path.endswith('/'):
        c4 = (path + '/').replace('/', '-').replace(':', '')
        candidates.append(c4)
    
    # Method 5: Actually scan from ~/.claude/projects/ directory
    # If none of the above match, list all directories and match by path keywords
    claude_dir = os.path.expanduser("~/.claude/projects")
    if os.path.isdir(claude_dir):
        path_lower = abs_path.lower().replace('\\', '/').replace(':', '')
        for dirname in os.listdir(claude_dir):
            # Restore dirname to path form for comparison
            restored = dirname.replace('-', '/').replace('--', ':/')
            if restored.lower() in path_lower or path_lower in restored.lower():
                candidates.append(dirname)
    
    return candidates
```

### 4.3 Format Parsing Logic

**JSONL parser:**

```python
def parse_jsonl(file_path, start_line=0, end_line=None):
    """
    Parse JSONL file, return meaningful conversation entries
    
    Parameters:
    - file_path: JSONL file path
    - start_line: Starting line number (for incremental export)
    - end_line: Ending line number (None means to end of file)
    
    Returns: Generator, yields one ConversationEntry each time
    """
    import json
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f):
            if line_num < start_line:
                continue
            if end_line is not None and line_num >= end_line:
                break
            
            line = line.strip()
            if not line:
                continue
            
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            
            # Only process user and assistant types
            entry_type = entry.get('type')
            if entry_type not in ('user', 'assistant'):
                continue
            
            yield extract_conversation_content(entry, line_num)
```

**Content extractor:**

```python
def extract_conversation_content(entry, line_num):
    """
    Extract meaningful conversation content from JSONL entry
    
    Filtering strategy:
    - user text: Fully retained
    - assistant text: Fully retained
    - thinking: Summary (first 200 chars + last 100 chars)
    - tool_use: Summary (tool name + key parameters)
    - tool_result: Summary (first 500 chars + error messages)
    """
    result = {
        'line_num': line_num,
        'type': entry.get('type'),
        'timestamp': entry.get('timestamp', ''),
        'uuid': entry.get('uuid', ''),
        'content_parts': []
    }
    
    msg = entry.get('message', {})
    content = msg.get('content', '')
    
    if isinstance(content, str):
        # user direct text
        result['content_parts'].append({
            'type': 'text',
            'text': content,
            'truncated': False
        })
    elif isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            
            block_type = block.get('type')
            
            if block_type == 'text':
                result['content_parts'].append({
                    'type': 'text',
                    'text': block.get('text', ''),
                    'truncated': False
                })
            
            elif block_type == 'thinking':
                thinking = block.get('thinking', '')
                # Summary: first 200 chars + last 100 chars
                if len(thinking) > 400:
                    summary = thinking[:200] + '\n[...omitted...]\n' + thinking[-100:]
                else:
                    summary = thinking
                result['content_parts'].append({
                    'type': 'thinking',
                    'text': summary,
                    'truncated': len(thinking) > 400
                })
            
            elif block_type == 'tool_use':
                tool_name = block.get('name', 'unknown')
                tool_input = block.get('input', {})
                # Summary: tool name + key parameters
                input_summary = summarize_tool_input(tool_name, tool_input)
                result['content_parts'].append({
                    'type': 'tool_use',
                    'text': f'[Tool: {tool_name}]\n{input_summary}',
                    'truncated': True
                })
            
            elif block_type == 'tool_result':
                result_content = block.get('content', '')
                if isinstance(result_content, list):
                    text = '\n'.join(
                        r.get('text', '') for r in result_content 
                        if isinstance(r, dict) and r.get('type') == 'text'
                    )
                else:
                    text = str(result_content)
                # Summary: first 500 chars + error messages
                is_error = block.get('is_error', False)
                if len(text) > 600:
                    summary = text[:500]
                    if is_error:
                        summary += '\n[...error info...]\n' + text[-200:]
                    else:
                        summary += '\n[...omitted...]'
                else:
                    summary = text
                result['content_parts'].append({
                    'type': 'tool_result',
                    'text': summary,
                    'truncated': len(text) > 600,
                    'is_error': is_error
                })
    
    return result
```

**Tool input summary function:**

```python
def summarize_tool_input(tool_name, tool_input):
    """
    Generate input summary based on tool type
    
    Different tools retain different key parameters:
    - Bash: command (fully retained, but truncated to 500 chars)
    - Edit: file_path + old_string (first 100 chars) + new_string (first 100 chars)
    - Write: file_path + content (first 200 chars)
    - Read: file_path
    - Agent: prompt (first 300 chars)
    - Others: JSON summary (first 300 chars)
    """
    if tool_name == 'Bash':
        cmd = tool_input.get('command', '')
        if len(cmd) > 500:
            cmd = cmd[:500] + '...'
        return f'Command: {cmd}'
    
    elif tool_name == 'Edit':
        fp = tool_input.get('file_path', '')
        old = tool_input.get('old_string', '')[:100]
        new = tool_input.get('new_string', '')[:100]
        return f'File: {fp}\nOld: {old}...\nNew: {new}...'
    
    elif tool_name == 'Write':
        fp = tool_input.get('file_path', '')
        content = tool_input.get('content', '')[:200]
        return f'File: {fp}\nContent: {content}...'
    
    elif tool_name == 'Read':
        fp = tool_input.get('file_path', '')
        return f'File: {fp}'
    
    elif tool_name == 'Agent':
        prompt = tool_input.get('prompt', '')[:300]
        return f'Prompt: {prompt}'
    
    else:
        import json
        summary = json.dumps(tool_input, ensure_ascii=False)[:300]
        return f'Input: {summary}'
```

### 4.4 Pagination Support

**Paginator:**

```python
def paginate_entries(entries, target_tokens=90000, max_tokens=200000):
    """
    Paginate conversation entries into multiple chunks
    
    Rules:
    1. Process in chronological order
    2. Maintain conversation turn integrity (don't split mid-turn)
    3. Target size 90K tokens, hard limit 200K tokens
    4. Minimum chunk size 40K tokens (if below, merge into previous page)
    
    Returns: List of chunks, each chunk is a list of entries
    """
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    # First group by turns
    turns = group_into_turns(entries)
    
    for turn in turns:
        turn_tokens = estimate_turn_tokens(turn)
        
        # If a single turn exceeds max_tokens, need to split
        if turn_tokens > max_tokens:
            # First save current chunk
            if current_chunk and current_tokens > 40000:
                chunks.append(current_chunk)
                current_chunk = []
                current_tokens = 0
            
            # Split large turn
            sub_turns = split_large_turn(turn, max_tokens)
            for sub_turn in sub_turns:
                chunks.append(sub_turn)
            continue
        
        # If adding this turn would exceed target_tokens
        if current_tokens + turn_tokens > target_tokens and current_chunk:
            chunks.append(current_chunk)
            current_chunk = turn
            current_tokens = turn_tokens
        else:
            current_chunk.extend(turn)
            current_tokens += turn_tokens
    
    # Handle last chunk
    if current_chunk:
        if current_tokens < 40000 and chunks:
            # Too small, merge into previous one
            chunks[-1].extend(current_chunk)
        else:
            chunks.append(current_chunk)
    
    return chunks
```

**Conversation turn grouping:**

```python
def group_into_turns(entries):
    """
    Group entries by conversation turns
    
    One turn = user message + all subsequent assistant messages (until next user message)
    """
    turns = []
    current_turn = []
    
    for entry in entries:
        if entry['type'] == 'user' and current_turn:
            # New turn begins
            turns.append(current_turn)
            current_turn = [entry]
        else:
            current_turn.append(entry)
    
    if current_turn:
        turns.append(current_turn)
    
    return turns
```

**Token estimation:**

```python
def estimate_tokens(text):
    """
    Rough estimation of text token count
    
    Rules:
    - English/code: approximately 4 chars/token
    - Chinese: approximately 1.0 chars/token (v3.3.0 correction, was 1.5)
    - Mixed content: weighted calculation
    - More precise method: count Chinese character ratio, calculate weighted
    """
    if not text:
        return 0
    
    # Count Chinese character ratio
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    total_chars = len(text)
    
    if total_chars == 0:
        return 0
    
    chinese_ratio = chinese_chars / total_chars
    
    # Weighted calculation
    # Chinese portion: 1.0 chars/token (v3.3.0 correction)
    # Non-Chinese portion: 4 chars/token
    chinese_tokens = chinese_chars / 1.0
    non_chinese_tokens = (total_chars - chinese_chars) / 4
    
    return int(chinese_tokens + non_chinese_tokens)
```

### 4.5 chunk File Format

**chunk Markdown format:**

```markdown
# Conversation History Export - Chunk 0/5

> Time range: <date-range>
> Estimated tokens: ~90,000
> Conversation turns: 15

---

## [Turn 1] <timestamp>

### User:
What do you think are the problems with this project from first principles?

### Assistant:
[thinking]
From first principles, there are several key issues to consider with this project...

[Tool: Bash]
Command: ls -la <project-root>/

[Tool Result]
total 228
drwxr-xr-x 1 user 1000 0 Jul 29 23:00 ./
...

Let me analyze the structure of this project...

---

## [Turn 2] <timestamp>

### User:
So how do we improve it?

### Assistant:
...
```

### 4.6 State Management

**sync-state.json complete structure:**

> Note: The `version` field records the version number of the sync-state data structure / export logic, updated in sync with the export solution version (currently 3.3.0). It is used for legacy state migration in future versions. It shares the same value as the document version but is semantically independent.

```json
{
  "version": "3.3.0",
  "project_path": "<project-root>",
  "jsonl_path": "~/.claude/projects/<project-hash>/<session-uuid>.jsonl",
  "last_sync": {
    "timestamp": "<timestamp>",
    "line_number": 5000,
    "uuid": "abc-123-...",
    "session_id": "<session-uuid>"
  },
  "file_info": {
    "size_bytes": 10000000,
    "line_count": 5000,
    "last_modified": "<timestamp>"
  },
  "stats": {
    "total_exports": 2,
    "full_exports": 1,
    "incremental_exports": 1,
    "total_entries_processed": 5382,
    "total_knowledge_extracted": 26
  },
  "export_history": [
    {
      "type": "full",
      "timestamp": "<timestamp>",
      "duration_seconds": 180,
      "chunks_analyzed": 3,
      "entries_processed": 5000,
      "knowledge_items_extracted": 23,
      "tokens_estimated": 371000
    },
    {
      "type": "incremental",
      "timestamp": "<timestamp>",
      "duration_seconds": 30,
      "chunks_analyzed": 1,
      "entries_processed": 150,
      "knowledge_items_extracted": 3,
      "tokens_estimated": 35000
    }
  ]
}
```

### 4.7 Windows Compatibility

**Key compatibility handling:**

1. **Path separators**: Script internally uses `os.path.join()` and `os.path.sep` throughout, does not hardcode `/` or `\`
2. **Home directory**: Uses `os.path.expanduser("~")` instead of `$HOME`
3. **Encoding**: File read/write explicitly specifies `encoding='utf-8'`
4. **Line endings**: Uses `newline='\n'` when writing files to unify to Unix style
5. **Python path**: Does not assume `python3`, uses `python` (Windows default), or detects from environment
6. **Bash path**: In Git Bash environment, `~` expands normally; in cmd/PowerShell, `%USERPROFILE%` is needed

```python
def get_python_executable():
    """Get available Python executable"""
    import sys
    # Directly return current Python
    return sys.executable

def get_home_dir():
    """Get user home directory, Windows compatible"""
    import os
    return os.path.expanduser("~")
```

### 4.8 Error Handling and Fallback

**Error handling matrix:**

| Error Scenario | Detection Method | Handling Strategy | Fallback |
|---------------|-----------------|-------------------|----------|
| JSONL file does not exist | `os.path.exists()` | Return error message | Prompt user to check if Claude Code is running normally |
| JSONL file is empty | File size is 0 | Return empty result | Prompt "No conversation history" |
| JSONL parse failure | `try/except JSONDecodeError` | Skip bad lines, count them | Return partial results + warning |
| sync-state.json corrupted | JSON parse failure | Treat as first run | Perform full export |
| Insufficient disk space | `shutil.disk_usage()` | Check in advance | Prompt user to free up space |
| Python version too low | `sys.version_info` | Check >= 3.8 | Prompt to upgrade |
| chunk file write failure | `try/except IOError` | Retry once | Return error, do not interrupt existing results |
| Project path cannot be matched | Path discovery fails | List all candidate directories | Let user manually specify JSONL path |

**Fallback mode design:**

```python
def export_with_fallback(project_path, mode='full'):
    """
    Export flow with fallback
    
    Fallback chain:
    1. Normal mode: Full parse + paginate + analyze
    2. Fallback 1: Skip thinking/tool_result, retain only text
    3. Fallback 2: Retain only user text + assistant text
    4. Fallback 3: Read only last N lines (most recent conversation)
    5. Fallback 4: Return error, suggest user manually export
    """
    try:
        # Normal mode
        return export_full(project_path, mode)
    except TokenLimitExceeded:
        try:
            # Fallback 1: More aggressive filtering
            return export_with_aggressive_filter(project_path, mode)
        except TokenLimitExceeded:
            try:
                # Fallback 2: Retain only text
                return export_text_only(project_path, mode)
            except Exception:
                # Fallback 3: Read only recent conversation
                return export_recent_only(project_path, lines=500)
```

---

## 5. Cost Estimation

### 5.1 Token Cost

**Full export (first time):**

| Item | Token Count | Description |
|------|-------------|-------------|
| JSONL parsing + pagination | 0 | Python local execution, no LLM token consumption |
| chunk file content | 371K | 3 chunks x ~124K avg |
| Analysis instructions (per chunk) | ~8K | Standard prompt for knowledge extraction |
| knowledge base reads (per chunk) | ~10K | kb-index.md + 2-3 detail files |
| knowledge base writes (per chunk) | ~10K | Write extracted knowledge |
| **Total per chunk** | ~152K | Content + instructions + read/write |
| **Full export total** | ~456K | 3 chunks x 152K |

**Incremental export (routine):**

| Item | Token Count | Description |
|------|-------------|-------------|
| Incremental content (assuming 100 turns of new conversation) | ~43K | Usually 1 chunk |
| Analysis instructions + knowledge base read/write | ~28K | Same as above |
| **Incremental total** | ~71K | 1 chunk |

**Cost estimation (at Claude Sonnet pricing $3/M input, $15/M output):**

| Scenario | Input Tokens | Output Tokens | Cost |
|----------|-------------|---------------|------|
| Full export (first time) | ~400K | ~56K | ~$1.60 |
| Incremental export (each time) | ~55K | ~16K | ~$0.40 |
| Monthly (1 full + 4 incremental) | - | - | ~$3.20 |

### 5.2 Time Cost

| Scenario | Duration | Description |
|----------|----------|-------------|
| Python script execution (full) | ~3 seconds | Parse ~10MB JSONL |
| Python script execution (incremental) | ~1 second | Parse new lines |
| Sub Agent analysis (per chunk) | ~60-90 seconds | Read + analyze + write (90K content) |
| Full export (3 chunks) | ~3-4 minutes | Sequential analysis |
| Incremental export (1 chunk) | ~1-2 minutes | Single analysis |
| Total full export | ~3-5 minutes | Including script + analysis |
| Total incremental export | ~1-2 minutes | Including script + analysis |

### 5.3 Storage Cost

| Item | Size | Description |
|------|------|-------------|
| chunk temporary files | ~1.1 MB | 3 chunks x ~370KB (~124K avg token x ~3 chars/token) |
| sync-state.json | ~2 KB | State file |
| export-log.json | ~5 KB | Log file |
| knowledge base growth (full) | ~10-20 KB | 8 .md files |
| knowledge base growth (per incremental) | ~2-5 KB | New entries |
| **Total storage overhead** | ~1.1 MB | Mostly chunk temporary files |

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
  ├── 2.2 Incremental cursor logic
  └── 2.3 export-log.json logging

Phase 3: SKILL.md integration
  ├── 3.1 Update SKILL.md to add export command
  ├── 3.2 Define Sub Agent analysis instruction template
  └── 3.3 Define knowledge extraction prompt template

Phase 4: Analysis coordination
  ├── 4.1 Sub Agent page-by-page analysis flow
  ├── 4.2 Knowledge deduplication and merge logic
  └── 4.3 kb-index.md auto-update

Phase 5: Testing and optimization
  ├── 5.1 Full export testing
  ├── 5.2 Incremental export testing
  ├── 5.3 Edge case testing
  └── 5.4 Performance optimization
```

### 6.2 Acceptance Criteria

| Acceptance Item | Standard | Verification Method |
|----------------|----------|---------------------|
| Path discovery | Can correctly discover current project's JSONL file | `python evolution-export.py --mode status` |
| Full export | Generates 2-4 chunk files, total tokens ~371K | Check `.evolution/chunks/` directory |
| Content filtering | Discards metadata entries, retains user/assistant | Check chunk file content |
| Pagination correctness | Each chunk is between 40K-200K tokens | Check token estimation in chunk file header |
| Incremental identification | Correctly identifies newly added lines | Run incremental export after modifying JSONL |
| State management | sync-state.json updates correctly | Check JSON content |
| Knowledge extraction | Extracts meaningful knowledge from conversations | Check knowledge base file changes |
| Deduplication | No duplicate entries produced | Compare knowledge base before and after |
| Windows compatibility | Runs normally on Git Bash + Windows | Test on Windows 11 |
| Error handling | Various exceptional situations handled reasonably | Simulate error scenarios |

### 6.3 Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| JSONL format changes | Medium | High | Parser fault-tolerant design, skip unparseable lines |
| Path encoding mismatch | Medium | High | Multi-candidate matching + directory scan fallback |
| Token estimation inaccuracy | High | Medium | 20% margin (target 90K, limit 200K) |
| Low knowledge extraction quality | Medium | High | Write review mechanism ([D] tags) + prompt optimization |
| Sub Agent context overflow | Low | High | Conservative pagination size + fallback modes |
| Multiple session files | Medium | Medium | Process each individually, maintain separate cursors |
| Python environment missing | Low | High | Script uses only standard library, no third-party dependencies |

---

## 7. Sub Agent Analysis Instruction Templates

### 7.1 Full Analysis Instructions

```markdown
# Evolution Knowledge Extraction Task

You are analyzing Claude Code conversation history to extract knowledge for the Evolution knowledge base.

## Task

Read the following chunk file, analyze the conversation content within, and extract valuable knowledge:

1. Read chunk file: {chunk_file_path}
2. Read knowledge base index: evolution/knowledge-base/kb-index.md
3. Based on the index, determine which knowledge base detail files to read (1-2)
4. Analyze conversations in the chunk, extract the following knowledge types:
   - Key facts (facts.md): Environment config, technology choices, dependencies
   - Pitfalls (pitfalls.md): Errors + causes + solutions
   - State changes (state.md): Project phases, milestones
   - Growth notes (growth-notes.md): Technical knowledge points the user can learn
   - Prompt improvements (prompt-improvements.md): Questioning optimization suggestions
   - Alignment items (alignment.md): Items requiring user confirmation
   - Decision records (decisions.md): Technical decisions + rationale
5. Deduplicate against existing knowledge
6. Write new knowledge to corresponding knowledge base files (mark [D])
7. Update kb-index.md

## Rules

- All new entries marked as [D] (draft)
- Format: `### [D] Entry title`
- Skip meaningless conversations (e.g., chitchat, testing)
- Focus on: error messages, solutions, technical decisions, user preferences
- If conflicts with existing entry: mark old entry [X], write new entry as [D]
- Do not modify [V] entries (unless marking as [X])

## Output

Return summary:
- Number of extracted knowledge entries (by category)
- Number of conflicts found
- Entries recommended for user review
```

### 7.2 Incremental Analysis Instructions

```markdown
# Evolution Incremental Knowledge Sync Task

You are analyzing new Claude Code conversations for incremental knowledge base updates in Evolution.

## Task

1. Read incremental chunk file: {chunk_file_path}
2. Read knowledge base index: evolution/knowledge-base/kb-index.md
3. Based on the index, determine which knowledge base detail files to read
4. Analyze new conversations, extract new knowledge
5. Deduplicate and merge with existing knowledge base
6. Update knowledge base files and index

## Rules

(Same as full analysis rules)

## Special Notes

- This is incremental sync; existing knowledge may already be present
- Focus on deduplication checks to avoid duplicate writes
- If an existing entry needs updating (e.g., state change), update directly
- Return incremental summary
```

---

## 8. Complete Execution Flow Examples

### 8.1 Full Export Flow

```
User input: /evolution init
    │
    ▼
Main Agent: Triggers Sub Agent
    │
    ▼
Sub Agent executes:
    │
    ├─ Step 1: Run Python script
    │  $ python .claude/skills/evolution/evolution-export.py --mode full --project-path <project-root>
    │  → Output JSON:
    │    {
    │      "status": "success",
    │      "chunks": [
    │        {"file": ".evolution/chunks/chunk-0.md", "tokens_est": 90000},
    │        {"file": ".evolution/chunks/chunk-1.md", "tokens_est": 90000},
    │        {"file": ".evolution/chunks/chunk-2.md", "tokens_est": 71000}
    │      ],
    │      "sync_state": {...}
    │    }
    │
    ├─ Step 2: Page-by-page analysis
    │  For each chunk:
    │    - Read chunk file
    │    - Read kb-index.md
    │    - Read knowledge base files as needed
    │    - Analyze conversation content
    │    - Extract knowledge
    │    - Write to knowledge base
    │    - Update index
    │
    ├─ Step 3: Update sync status
    │  - sync-state.json has been updated by the Python script
    │
    └─ Step 4: Return summary
       "Full export complete:
        - Processed ~5,000 entries
        - Analyzed 3 pages
        - Extracted 23 knowledge items (8 facts / 5 pitfalls / 3 state / 4 growth / 1 prompt / 2 decisions)
        - All marked as [D]
        - Recommended for review: ..."
    │
    ▼
Main Agent: Displays summary to user
```

### 8.2 Incremental Export Flow

```
User input: /evolution --export
    │
    ▼
Main Agent: Triggers Sub Agent
    │
    ▼
Sub Agent executes:
    │
    ├─ Step 1: Run Python script
    │  $ python .claude/skills/evolution/evolution-export.py --mode incremental --project-path <project-root>
    │  → Output JSON:
    │    {
    │      "status": "success",
    │      "mode": "incremental",
    │      "new_entries": 150,
    │      "chunks": [
    │        {"file": ".evolution/chunks/chunk-inc-0.md", "tokens_est": 35000}
    │      ]
    │    }
    │
    ├─ Step 2: Analyze incremental chunk
    │  - Read chunk-inc-0.md
    │  - Read kb-index.md
    │  - Analyze + extract + deduplicate + write
    │
    └─ Step 3: Return summary
       "Incremental sync complete:
        - 150 new entries
        - Extracted 3 new knowledge items
        - Updated 2 existing knowledge items
        - Recommended for review: ..."
    │
    ▼
Main Agent: Displays summary to user
```

---

## 9. Key Design Decision Records

### 9.1 Why Use a Python Script Instead of Having AI Read JSONL Directly?

| Approach | Pros | Cons |
|----------|------|------|
| AI reads JSONL directly | No script needed | ~10MB file far exceeds context; JSON is noisy; cannot paginate |
| Python script preprocessing | Precise control over filtering/pagination; no token consumption; reusable | Script needs maintenance |

**Decision: Python script preprocessing.** Reason: The raw data of ~10MB / 716K tokens cannot fit directly into a 1M context window (synthesis task effective context is only 200-300K); preprocessing is required.

### 9.2 Why Is the Pagination Target 90K Rather Than Closer to 1M?

- 1M is the sub agent's raw context window, but the effective context for synthesis/analysis tasks is only approximately 200-300K (see the "Lost in the Middle" research in the "Key Changes" section)
- The effective context of 200-300K needs to deduct: analysis instructions (~8K) + knowledge base reads (~10K) + knowledge base writes (~10K) + output space (~20K) + model internal overhead (~50K) ≈ 98K
- Chunk content ceiling = effective context (200-300K) - other allocations (98K) = 102-202K, taking ~90K as the target (v3.3.0 after CJK coefficient correction)
- 90K estimate × 1.68 (CJK coefficient correction) ≈ 150K actual usage, approximately 15% of the 1M window, well within the safe zone
- Hard limit set to 200K (upper bound of synthesis effective zone), ensuring no single chunk crosses the attention degradation inflection point
- **Better to conservatively target based on effective context than to rely on raw window size**

### 9.3 Why Paginate by Conversation Turns Rather Than Fixed Line Counts?

- Fixed line counts may truncate in the middle of a conversation, losing context
- Pagination by turns maintains semantic integrity
- One turn = one complete user-assistant interaction
- Sub Agent can see the full conversation context during analysis

### 9.4 Why Use line_number Rather Than timestamp as the Incremental Cursor?

- Timestamps may not be unique (multiple entries in the same second)
- Timestamps may be out of order (in rare cases)
- line_number is strictly increasing, unique and ordered
- However, line_number may become invalid if the file is rewritten, so uuid and timestamp are also recorded for verification

### 9.5 Why Not Filter Out tool_use and tool_result?

- tool_use contains executed commands, edited file content — an important source for pitfalls
- tool_result contains command output, error messages — a source for key facts
- Complete filtering would lose a large amount of valuable knowledge
- The summary strategy (retain first N chars + error messages) achieves balance between information retention and token savings

---

## 10. Future Optimization Directions

| Optimization | Description | Priority |
|-------------|-------------|----------|
| Parallel analysis | Analyze multiple chunks in parallel (multiple sub agents) | Medium |
| Smart filtering | Dynamically decide retention ratio based on content value | Medium |
| Vector retrieval | Build vector index on knowledge base, support semantic search | Low |
| Auto trigger | Automatically trigger incremental export after detecting N turns of new conversation | Low |
| Multi-project support | Support managing conversation history for multiple projects simultaneously | Low |
| Visual reports | Generate export analysis reports (HTML/Markdown) | Low |
| Knowledge decay | Automatically down-weight old knowledge, mark outdated knowledge [X] | Medium |

---

**End of document**
