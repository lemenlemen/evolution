# Evolution V3 - System Rules and Runtime Logic

🌐 **Language / 语言**: [English](EVOLUTION_RULES_AND_LOGIC_V3.md) | [中文](EVOLUTION_RULES_AND_LOGIC_V3.zh-CN.md)

> ⚠️ **Outdated document (noted in v4.1.6)**: This document describes the V3.x system rules (single-file structure, no modularization).
> Since V4.0.0 it has changed to a modular structure (SKILL.md + config.yaml + commands/ + rules/ + evolution-export.py).
> The file tree, command list, and state model are all inconsistent with the current implementation.
> Current system behavior is governed by `CLAUDE.md` + `.claude/skills/evolution/` + `docsV3/VERSION_HISTORY.md`.

> **Version**: 3.9.0 (2026-08-01)  
> **Based on**: V2 experience + simplified requirements

> **Version history**: see [`VERSION_HISTORY.md`](./VERSION_HISTORY.md)

---

## 1. System Overview

### 1.1 Core Positioning

Evolution is a **human-AI symbiotic evolution system** that lets AI and humans grow together through collaboration.

### 1.2 Core Value

| Value | Description |
|------|------|
| **Make AI more reliable** | Remember key information, avoid repeated mistakes |
| **Let humans grow** | Generate learning notes, improve collaboration efficiency |
| **Keep human-AI alignment** | Mark acceptance items, reduce misunderstandings |

---

## 2. Core Design Principle

> **When Evolution runs, it dispatches sub agents to handle things, minimizing pollution of the main session**

All operations (initialization, synchronization, history analysis) are executed by **sub agents** in the background.

---

## 3. System Architecture

### 3.1 File Structure

```
<project>/
├── .claude/
│   └── skills/
│       └── evolution/
│           └── SKILL.md              # Skill definition
│
└── evolution/                        # knowledge base
    └── knowledge-base/
        ├── kb-index.md               # index
        ├── facts.md                  # key facts
        ├── pitfalls.md               # pitfalls
        ├── state.md                  # current state
        ├── growth-notes.md           # learning notes
        ├── prompt-improvements.md    # Prompt improvements
        ├── alignment.md              # alignment checklist
        └── decisions.md              # decision log
```

### 3.2 Directory Responsibilities

| Directory/File | Purpose | Reader |
|----------|------|------|
| `.claude/skills/evolution/SKILL.md` | Skill definition and execution instructions | AI |
| `evolution/knowledge-base/` | Knowledge base data | AI + humans |
| `docsV3/` | Design documents | Humans |

---

## 4. Execution Commands

### 4.1 Initialization Command (First Installation)

```bash
/evolution-init
```

**Execution method**:
1. Main agent triggers a **sub agent**
2. Sub agent analyzes **all** historical main session conversations in the background (see the export scope notes in section 5)
3. Extract all key facts
4. Record all pitfalls
5. Generate the initial knowledge base
6. Mark all entries as `[D]` (draft)
7. Return a summary to the main agent

**Use cases**:
- After first installing Evolution
- After the knowledge base is cleared
- When the knowledge base needs to be rebuilt

### 4.2 Sync Command (Daily Use)

```bash
/evolution
```

**Execution method**:
1. Main agent triggers a **sub agent**
2. Sub agent performs incremental sync in the background
3. Return a summary to the main agent

---

## 5. Conversation Export Mechanism

Evolution exports Claude Code conversation history (JSONL format) via the `evolution-export.py` script. This is the only data export method.

### 5.1 Export Script

**Script location**: `.claude/skills/evolution/evolution-export.py`

**Features**:
1. Discover the JSONL file path (`~/.claude/projects/<hash>/`)
2. Parse the JSONL format, filtering out noise entries
3. Extract meaningful conversation content (user/assistant text, tool calls, thinking, etc.)
4. Paginate into ~90K token chunks
5. Output chunk files to `.evolution/chunks/`
6. Manage incremental sync state in `sync-state.json`

**Export scope and fidelity (stated truthfully)**:

- **Coverage**: only top-level `*.jsonl` files of the main session are exported; sub agent
  transcripts under the `subagents/` subdirectory are excluded by default—to avoid Evolution
  self-ingesting and forming a reinforcing loop. Therefore, content from sub agent sessions
  does not enter the knowledge base.
- **Content truncation**: to control chunk size, the export performs summary truncation by design rather than preserving the full original text:
  - thinking: when over 400 characters, keep the first 200 + last 100 characters
  - tool_use: keep only the tool name and a summary of key parameters (e.g., the first 500 characters of a Bash command)
  - tool_result: when over 600 characters, keep the first 500 characters (for error messages, additionally keep the last 200 characters)
  - A single oversized entry that exceeds the chunk budget is truncated as a whole as a fallback
- **Noise filtering**: non user/assistant type entries (progress, metadata, etc.) are not exported

### 5.2 Execution Flow

```
User enters /evolution-init (initialization) or /evolution (incremental sync)
    ↓
Main agent triggers sub agent
    ↓
Sub agent executes evolution-export.py
    ↓
Script outputs paginated chunk files (~90K token/chunk)
    ↓
Sub agent reads and analyzes chunk by chunk, extracting knowledge
    ↓
Writes to the knowledge base (evolution/knowledge-base/)
    ↓
Updates sync-state.json
```

### 5.3 Advantages and Limitations

- ✅ Full main session conversations are exported in chunks, without random sampling
- ✅ Paginated processing avoids context overflow
- ✅ Incremental sync processes only new content
- ✅ The main session is barely polluted
- ⚠️ **Not a verbatim, complete export**: content is summary-truncated per the strategies above, subagent transcripts are excluded by default,
  and noise entries are filtered—what the knowledge base covers is the meaningful conversation information in the main session, not a full mirror of the raw record

---

## 6. Sub Agent Execution Rules

### 6.1 Core Principle

> **When Evolution runs, it dispatches sub agents to handle things, minimizing pollution of the main session**

### 6.2 Division of Responsibilities

**Main agent**:
- Receives user commands
- Triggers sub agents
- Displays the summary returned by the sub agent
- **Does not directly operate on the knowledge base**

**Sub agent**:
- Reads conversation history
- Extracts knowledge
- Writes to the knowledge base
- Returns a summary

### 6.3 Benefits

- ✅ The main session is barely polluted
- ✅ The main session stays smooth
- ✅ Knowledge base operations are completed in the background

---

## 7. Write Rules (Review Mechanism)

### 7.1 Status Markers

| Status | Marker | Meaning |
|------|------|------|
| draft | `[D]` | Extracted by AI, not verified by the user |
| verified | `[V]` | Explicitly confirmed by the user or verified by a tool |
| deprecated | `[X]` | Deprecated or proven wrong |

### 7.2 Write Rules

1. **All new entries are marked as `[D]` by default**
   - Format: `### [D] Entry title`
   - Example: `### [D] WSL network configuration`

2. **The following cases can be marked as `[V]`**:
   - The user explicitly confirms in the conversation (e.g., saying "right", "yes")
   - Verified by a tool call result (e.g., `node -v` output)
   - External document citation

3. **Conflict handling**:
   - New entry conflicts with an existing entry → the old entry is marked as `[X]` (deprecated)
   - The new entry is written as `[D]`

### 7.3 Distinguish Status When Reading

- `[V]` entries: use normally
- `[D]` entries: can be used, but marked "unverified"
- `[X]` entries: do not read

---

## 8. Progressive Reading Rules

### 8.1 Core Principle

**Important**: Do not read all files at once! Follow the progressive disclosure principle.

### 8.2 Reading Steps

**Step 1: Read the index**

Read `evolution/knowledge-base/kb-index.md`

**Step 2: Determine the need**

Based on the categorized summaries in the index, determine what information the current task needs:

- If the user asks about environment configuration → read `facts.md`
- If the user asks about historical errors → read `pitfalls.md`
- If the state needs updating → read `state.md`
- If the user asks about learning knowledge → read `growth-notes.md`
- If acceptance check is needed → read `alignment.md`
- If a decision log is needed → read `decisions.md`

**Step 3: Read on demand**

**Read only the relevant 1-2 files**, do not load all files at once

---

## 9. Deduplication Strategy

1. Determine whether duplication is possible based on the summaries in `kb-index.md`
2. If unsure, read the corresponding detail file for precise deduplication
3. For identical information, update the timestamp; for new information, append

---

## 10. Knowledge Base File Descriptions

| File | Purpose | Read | Write |
|------|------|------|------|
| `kb-index.md` | Index file (<200 lines) | ✅ | ✅ |
| `facts.md` | Key facts | ✅ | ✅ |
| `pitfalls.md` | Pitfalls | ✅ | ✅ |
| `state.md` | Current state | ✅ | ✅ |
| `growth-notes.md` | Learning notes | ✅ | ✅ |
| `prompt-improvements.md` | Prompt improvements | ✅ | ✅ |
| `alignment.md` | Alignment checklist | ✅ | ✅ |
| `decisions.md` | Decision log | ✅ | ✅ |

---

## 11. Summary of Core Principles

1. **Separated from Auto Memory** - Does not pollute Claude Code's Auto Memory system
2. **Project-level storage** - The knowledge base is stored in `evolution/knowledge-base/`
3. **On-demand loading** - Guide AI to read on demand through the index, avoiding context pollution
4. **Progressive growth** - Both AI and humans grow through collaboration
5. **Bidirectional sync** - Both read existing knowledge and write new knowledge
6. **Human review** - All content must be checked by humans; humans must also read the documents to learn
7. **Sub Agent execution** - All operations are executed by sub agents, reducing main session pollution

---

## 12. Version History

| Version | Date | Main Changes |
|------|------|----------|
| v3.9.0 | 2026-08-01 | Added `/evolution-init` pre-check to prevent accidental reset |
| v3.8.0 | 2026-08-01 | Fixed three bugs: forced script + prohibiting manual glob, fixed find_jsonl_file returning all files, added verification mechanism |
| v3.7.0 | 2026-08-01 | Fixed the `/evolution-init` command to call `evolution-export.py` to export all history, preventing sampling |
| v3.6.0 | 2026-08-01 | Fixed `/evolution init` as the independent command `/evolution-init`, distinguishing initialization from incremental sync |
| v3.5.0 | 2026-07-31 | Refactored based on writing-great-skills rules; SKILL.md reduced from 96 lines to 37 lines |
| v3.4.0 | 2026-07-31 | Modular refactor; SKILL.md split; unified configuration via config.yaml |
| v3.3.0 | 2026-07-30 | Fixed JSON serialization crash, incremental unit drift, Windows encoding, underestimation of tokens |
| v3.2.1 | 2026-07-30 | Updated pagination parameter: 80K → 150K (based on attention research) |
| v3.2.0-draft | 2026-07-29 | Initial design, based on the 200K window assumption (superseded by v3.2.1) |
| v3.1.0 | 2026-07-29 | Added initialization command, conversation export mechanism |
| v3.0.0 | 2026-07-28 | Simplified the system, removed the auto version |
| v2.1.0 | 2026-07-28 | Write review mechanism |
| v2.0.0 | 2026-07-28 | Skill system migration |
| v1.0.0 | 2026-07-21 | Initial version |

---

**End of document**
