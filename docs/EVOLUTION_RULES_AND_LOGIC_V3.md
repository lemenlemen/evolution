# Evolution V3 - System Rules and Runtime Logic

> **Version**: 3.3.0 (2026-07-31)
> **Based on**: V2 experience + simplified requirements

> **Version history**: See [`VERSION_HISTORY.md`](./VERSION_HISTORY.md)

---

## 1. System Overview

### 1.1 Core Positioning

Evolution is a **human-AI symbiotic evolution system** that enables AI and humans to grow together through collaboration.

### 1.2 Core Values

| Value | Description |
|------|------|
| **Make AI more reliable** | Remember key information, avoid repeating mistakes |
| **Help humans grow** | Generate learning notes, improve collaboration efficiency |
| **Keep human and AI aligned** | Mark acceptance items, reduce misunderstandings |

---

## 2. Core Design Principle

> **Evolution dispatches to sub agents at runtime, minimizing pollution of the main session**

All operations (initialization, sync, history analysis) are executed by **sub agents** in the background.

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
└── evolution/                        # Knowledge base
    └── knowledge-base/
        ├── kb-index.md               # Index
        ├── facts.md                  # Key facts
        ├── pitfalls.md               # Pitfalls
        ├── state.md                  # Current state
        ├── growth-notes.md           # Learning notes
        ├── prompt-improvements.md    # Prompt improvements
        ├── alignment.md              # Alignment checklist
        └── decisions.md              # Decision log
```

### 3.2 Directory Responsibilities

| Directory/File | Purpose | Reader |
|----------|------|------|
| `.claude/skills/evolution/SKILL.md` | Skill definition and execution instructions | AI |
| `evolution/knowledge-base/` | Knowledge base data | AI + Human |
| `docsV3/` | Design documents | Human |

---

## 4. Execution Commands

### 4.1 Initialization Command (first-time installation)

```bash
/evolution init
```

**Execution method**:
1. Main agent triggers **sub agent**
2. Sub agent analyzes **all** historical conversations in the background
3. Extracts all key facts
4. Records all pitfalls
5. Generates the initial knowledge base
6. Marks all entries as `[D]` (draft)
7. Returns summary to main agent

**Usage scenarios**:
- After first-time installation of Evolution
- After the knowledge base has been cleared
- When the knowledge base needs to be rebuilt

### 4.2 Sync Command (daily use)

```bash
/evolution
```

**Execution method**:
1. Main agent triggers **sub agent**
2. Sub agent performs incremental sync in the background
3. Returns summary to main agent

---

## 5. Conversation Export Mechanism

### 5.1 Method A: AI Memory (default)

**Execution flow**:
```
User inputs /evolution
    ↓
Main agent triggers sub agent
    ↓
Sub agent analyzes the current session's conversation context
    ↓
Extracts knowledge, writes to knowledge base
    ↓
Returns summary
```

**Pros**:
- ✅ Simple, no extra files needed
- ✅ High real-time relevance
- ✅ Main session is barely polluted

**Cons**:
- ❌ Can only analyze the current session's conversations

### 5.2 Method B: File Logging (optional)

**Execution flow**:
```
User inputs /evolution --history
    ↓
Main agent triggers sub agent
    ↓
Sub agent reads temporary files:
  .claude/.tmp/conversation-*.md
    ↓
Analyzes full conversation history
    ↓
Extracts knowledge, writes to knowledge base
    ↓
Returns summary
```

**Pros**:
- ✅ Persistent, traceable history
- ✅ Supports cross-session analysis

**Cons**:
- ❌ Requires extra files

---

## 6. Sub Agent Execution Rules

### 6.1 Core Principle

> **Evolution dispatches to sub agents at runtime, minimizing pollution of the main session**

### 6.2 Responsibility Division

**Main agent**:
- Receives user commands
- Triggers sub agent
- Displays the summary returned by the sub agent
- **Does not operate on the knowledge base directly**

**Sub agent**:
- Reads conversation history
- Extracts knowledge
- Writes to the knowledge base
- Returns summary

### 6.3 Benefits

- ✅ Main session is barely polluted
- ✅ Main session stays fluid
- ✅ Knowledge base operations run in the background

---

## 7. Write Rules (Review Mechanism)

### 7.1 Status Markers

| Status | Marker | Meaning |
|------|------|------|
| draft | `[D]` | Extracted by AI, not verified by user |
| verified | `[V]` | Explicitly confirmed by user or verified by tool output |
| deprecated | `[X]` | Deprecated or proven incorrect |

### 7.2 Write Rules

1. **All new entries default to `[D]`**
   - Format: `### [D] Entry title`
   - Example: `### [D] WSL network configuration`

2. **May be marked as `[V]` in the following cases**:
   - User explicitly confirms in conversation (e.g. says "right", "yes")
   - Verified by tool call output (e.g. `node -v` output)
   - Referenced from external documentation

3. **Conflict handling**:
   - New entry conflicts with existing entry → old entry marked as `[X]` (deprecated)
   - New entry written as `[D]`

### 7.3 Distinguishing Status When Reading

- `[V]` entries: use normally
- `[D]` entries: usable, but flagged as "unverified"
- `[X]` entries: not read

---

## 8. Progressive Disclosure Read Rules

### 8.1 Core Principle

**Important**: Do not read all files at once! Follow the progressive disclosure principle.

### 8.2 Read Steps

**Step 1: Read the index**

Read `evolution/knowledge-base/kb-index.md`

**Step 2: Determine needs**

Based on the categorized summaries in the index, determine which information the current task requires:

- If user asks about environment configuration → read `facts.md`
- If user asks about historical errors → read `pitfalls.md`
- If state needs updating → read `state.md`
- If user asks about learned knowledge → read `growth-notes.md`
- If acceptance check is needed → read `alignment.md`
- If decision records are needed → read `decisions.md`

**Step 3: Read on demand**

**Only read the 1-2 relevant files** — do not load all files at once

---

## 9. Deduplication Strategy

1. Judge whether duplication is possible based on summaries in `kb-index.md`
2. If uncertain, read the corresponding detail file for precise deduplication
3. Update timestamp for identical information; append new information

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

1. **Separation from Auto Memory** - Do not pollute Claude Code's Auto Memory system
2. **Project-level storage** - Knowledge base stored in `evolution/knowledge-base/`
3. **Load on demand** - Guide AI to read files on demand via the index, avoiding context pollution
4. **Progressive growth** - Both AI and humans grow through collaboration
5. **Bidirectional sync** - Read existing knowledge and write new knowledge
6. **Manual review** - All content must be manually verified; humans should also read docs to learn
7. **Sub agent execution** - All operations executed by sub agents, reducing main session pollution

---

## 12. Version History

| Version | Date | Major Changes |
|------|------|----------|
| v3.1.0 | 2026-07-29 | Added initialization command, conversation export mechanism |
| v3.0.0 | 2026-07-28 | Simplified system, removed auto version |
| v2.1.0 | 2026-07-28 | Write review mechanism |
| v2.0.0 | 2026-07-28 | Migrated to Skill system |
| v1.0.0 | 2026-07-21 | Initial version |

---

**End of document**
