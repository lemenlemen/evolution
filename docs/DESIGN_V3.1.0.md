# Evolution Design Document v3.1.0

> **Version**: 3.1.0
> **Date**: 2026-07-29
> **Status**: Design complete

---

## Core Design Principle

> **Evolution dispatches to sub agents at runtime, minimizing pollution of the main session**

---

## Architecture Design

### Document Responsibilities

| File | Purpose | Reader |
|------|------|------|
| `CLAUDE.md` | Project configuration | AI |
| `.claude/skills/evolution/SKILL.md` | Execution instructions | AI |
| `docs/` | Design documents | Human |

---

## Execution Command Design

### Initialization Command

```bash
/evolution init
```

**Design considerations**:
- Used after first-time installation
- Analyzes all historical conversations
- Builds the initial knowledge base
- All entries marked as `[D]` (draft)

**Execution flow**:
```
User inputs /evolution init
    ↓
Main agent triggers sub agent
    ↓
Sub agent in background:
  1. Analyzes all historical conversations
  2. Extracts all key facts
  3. Records all pitfalls
  4. Generates initial knowledge base
  5. Marks all entries as [D]
    ↓
Returns summary to main agent
    ↓
Main agent displays summary
```

---

## Conversation Export Mechanism Design

### Method A: AI Memory (default)

**Design considerations**:
- Simple and direct
- No extra files required
- Main session is barely polluted

**Applicable scenarios**:
- Short-term projects
- Single-session usage
- Most daily scenarios

### Method B: File Logging (optional)

**Design considerations**:
- Persistent storage
- Traceable history
- Supports cross-session analysis

**Applicable scenarios**:
- Long-term projects
- Requires full historical traceability
- Requires cross-session analysis

**Implementation**:
```
.claude/.tmp/conversation-20260729-001.md
.claude/.tmp/conversation-20260729-002.md
...
```

---

## Sub Agent Execution Design

### Why Use Sub Agents?

**Core principle**:
> Minimize pollution of the main session

**Benefits**:
1. ✅ Main session is barely polluted
2. ✅ Main session stays fluid
3. ✅ Knowledge base operations run in the background
4. ✅ Better user experience

### Responsibility Division

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

---

## Write Review Mechanism Design

### Status Markers

| Status | Marker | Meaning |
|------|------|------|
| draft | `[D]` | Extracted by AI, not verified by user |
| verified | `[V]` | Explicitly confirmed by user or verified by tool output |
| deprecated | `[X]` | Deprecated or proven incorrect |

### Design Considerations

**Why default to `[D]`?**
- Ensures all knowledge goes through manual review
- Prevents AI errors from polluting the knowledge base
- User retains final control

**Why need a `[V]` status?**
- User-confirmed knowledge can be used directly
- Improves usage efficiency
- Builds a trust mechanism

---

## Progressive Disclosure Read Design

### Why Progressive Disclosure Reads?

**Problem**:
- Knowledge base has 8 files
- Loading everything pollutes the context
- Wastes tokens

**Solution**:
1. Read the index first (`kb-index.md`)
2. Determine what is needed
3. Only read the relevant files (1-2)

**Benefits**:
- ✅ Reduces context pollution
- ✅ Saves tokens
- ✅ Improves efficiency

---

## Version History

| Version | Date | Changes |
|------|------|------|
| v3.1.0 | 2026-07-29 | Added initialization command, conversation export mechanism |
| v3.0.0 | 2026-07-28 | Simplified system, removed auto version |
| v2.1.0 | 2026-07-28 | Write review mechanism |
| v2.0.0 | 2026-07-28 | Migrated to Skill system |
| v1.0.0 | 2026-07-24 | Initial version |

---

## Reference Documents

- [SKILL.md](.claude/skills/evolution/SKILL.md) - Execution instructions
- [CLAUDE.md](CLAUDE.md) - Project configuration
- [README.md](README.md) - User documentation
