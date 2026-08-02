# Evolution V3 - System Rules and Operational Logic

> **Version**: 3.8.0 (2026-08-01)  
> **Based on**: V2 experience + simplified requirements

🌐 **Language / 语言**: [English](EVOLUTION_RULES_AND_LOGIC_V3.md) | [中文](EVOLUTION_RULES_AND_LOGIC_V3.zh-CN.md)

> **Version History**: See [`VERSION_HISTORY.md`](./VERSION_HISTORY.md)

---

## 1. System Overview

### 1.1 Core Positioning

Evolution is a **human-AI symbiotic evolution system** that enables AI and humans to grow together through collaboration.

### 1.2 Core Value

| Value | Description |
|-------|-------------|
| **Make AI More Reliable** | Remember key information, avoid repeated errors |
| **Enable Human Growth** | Generate learning notes, improve collaboration efficiency |
| **Maintain Human-AI Alignment** | Flag acceptance items, reduce misunderstandings |

---

## 2. Core Design Principle

> **Evolution dispatches sub agents at runtime to minimize pollution of the main session**

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
|----------------|---------|--------|
| `.claude/skills/evolution/SKILL.md` | Skill definition and execution instructions | AI |
| `evolution/knowledge-base/` | Knowledge base data | AI + Humans |
| `docs/` | Design documents | Humans |

---

## 4. Execution Commands

### 4.1 Initialization Command (First-Time Installation)

```bash
/evolution-init
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
- After first-time Evolution installation
- After the knowledge base has been cleared
- When the knowledge base needs to be rebuilt

### 4.2 Sync Command (Daily Use)

```bash
/evolution
```

**Execution method**:
1. Main agent triggers **sub agent**
2. Sub agent performs incremental sync in the background
3. Returns summary to main agent

---

## 5. Conversation Export Mechanism

### 5.1 Method A: AI Memory (Default)

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

**Advantages**:
- ✅ Simple, no extra files needed
- ✅ High real-time relevance
- ✅ Main session is barely polluted

**Disadvantages**:
- ❌ Can only analyze the current session's conversations

### 5.2 Method B: File Records (Optional)

**Execution flow**:
```
User inputs /evolution --history
    ↓
Main agent triggers sub agent
    ↓
Sub agent reads temporary files:
  .claude/.tmp/conversation-*.md
    ↓
Analyzes all conversation history
    ↓
Extracts knowledge, writes to knowledge base
    ↓
Returns summary
```

**Advantages**:
- ✅ Persistent, traceable history
- ✅ Supports cross-session analysis

**Disadvantages**:
- ❌ Requires extra files

---

## 6. Sub Agent Execution Rules

### 6.1 Core Principle

> **Evolution dispatches sub agents at runtime to minimize pollution of the main session**

### 6.2 Responsibility Division

**Main agent**:
- Receives user commands
- Triggers sub agent
- Displays the summary returned by sub agent
- **Does not directly operate the knowledge base**

**Sub agent**:
- Reads conversation history
- Extracts knowledge
- Writes to the knowledge base
- Returns summary

### 6.3 Benefits

- ✅ Main session is barely polluted
- ✅ Main session stays responsive
- ✅ Knowledge base operations complete in the background

---

## 7. Write Rules (Review Mechanism)

### 7.1 Status Markers

| Status | Marker | Meaning |
|--------|--------|---------|
| draft | `[D]` | Extracted by AI, not verified by user |
| verified | `[V]` | Explicitly confirmed by user or verified by tool |
| deprecated | `[X]` | Deprecated or proven incorrect |

### 7.2 Write Rules

1. **All new entries default to `[D]`**
   - Format: `### [D] Entry title`
   - Example: `### [D] WSL network configuration`

2. **The following cases may be marked as `[V]`**:
   - User explicitly confirms in conversation (e.g., says "yes", "correct")
   - Verified by tool call results (e.g., `node -v` output)
   - External documentation references

3. **Conflict handling**:
   - New entry conflicts with existing entry → old entry marked as `[X]` (deprecated)
   - New entry written as `[D]`

### 7.3 Distinguishing Status at Read Time

- `[V]` entries: use normally
- `[D]` entries: usable, but marked as "unverified"
- `[X]` entries: not read

---

## 8. Progressive Read Rules

### 8.1 Core Principle

**Important**: Do not read all files at once! Follow the progressive disclosure principle.

### 8.2 Read Steps

**Step 1: Read the Index**

Read `evolution/knowledge-base/kb-index.md`

**Step 2: Determine Needs**

Based on the categorized summaries in the index, determine what information the current task requires:

- If user asks about environment configuration → read `facts.md`
- If user asks about historical errors → read `pitfalls.md`
- If state needs updating → read `state.md`
- If user asks about learning knowledge → read `growth-notes.md`
- If acceptance checking is needed → read `alignment.md`
- If decision records are needed → read `decisions.md`

**Step 3: Read on Demand**

**Only read the relevant 1–2 files** — do not load all files at once.

---

## 9. Deduplication Strategy

1. Based on `kb-index.md` summaries, determine if duplication is likely
2. If uncertain, read the corresponding detail file for precise deduplication
3. For identical information, update the timestamp; new information is appended

---

## 10. Knowledge Base File Descriptions

| File | Purpose | Read | Write |
|------|---------|------|-------|
| `kb-index.md` | Index file (<200 lines) | ✅ | ✅ |
| `facts.md` | Key facts | ✅ | ✅ |
| `pitfalls.md` | Pitfalls | ✅ | ✅ |
| `state.md` | Current state | ✅ | ✅ |
| `growth-notes.md` | Learning notes | ✅ | ✅ |
| `prompt-improvements.md` | Prompt improvements | ✅ | ✅ |
| `alignment.md` | Alignment checklist | ✅ | ✅ |
| `decisions.md` | Decision log | ✅ | ✅ |

---

## 11. Core Principles Summary

1. **Separated from Auto Memory** - Does not pollute Claude Code's Auto Memory system
2. **Project-Level Storage** - Knowledge base stored in `evolution/knowledge-base/`
3. **On-Demand Loading** - Guides AI to read on demand via index, avoiding context pollution
4. **Progressive Growth** - Both AI and humans grow through collaboration
5. **Bidirectional Sync** - Reads existing knowledge and writes new knowledge
6. **Manual Review** - All content must be manually verified; humans should also read documents to learn
7. **Sub Agent Execution** - All operations executed by sub agents to reduce main session pollution

---

## 12. Version History

| Version | Date | Major Changes |
|---------|------|---------------|
| v3.1.0 | 2026-07-29 | Added initialization command, conversation export mechanism |
| v3.0.0 | 2026-07-28 | Simplified system, removed auto version |
| v2.1.0 | 2026-07-28 | Write review mechanism |
| v2.0.0 | 2026-07-28 | Skill system migration |
| v1.0.0 | 2026-07-21 | Initial version |

---

**End of Document**
