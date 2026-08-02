# Evolution Design Document v3.1.0

> **Version**: 3.1.0
> **Date**: 2026-07-29
> **Status**: Design Complete

🌐 **Language / 语言**: [English](DESIGN_V3.1.0.md) | [中文](DESIGN_V3.1.0.zh-CN.md)

---

## Core Design Principle

> **Evolution dispatches sub agents at runtime to minimize pollution of the main session**

---

## Architecture Design

### Document Responsibilities

| File | Purpose | Reader |
|------|---------|--------|
| `.claude/skills/evolution/SKILL.md` | Skill definition | AI |
| `docs/` | Design documents | Humans |

---

## Initialization Command Design

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
  1. Analyze all historical conversations
  2. Extract all key facts
  3. Record all pitfalls
  4. Generate initial knowledge base
  5. Mark all entries as [D]
    ↓
Return summary to main agent
    ↓
Main agent displays summary
```

---

## Conversation Export Mechanism Design

### Method A: AI Memory (Default)

**Design considerations**:
- Simple and direct
- No extra files needed
- Main session is barely polluted

**Applicable scenarios**:
- Short-term projects
- Single-session usage
- Most daily scenarios

### Method B: File Records (Optional)

**Design considerations**:
- Persistent storage
- Traceable history
- Supports cross-session analysis

**Applicable scenarios**:
- Long-term projects
- When full history traceability is needed
- When cross-session analysis is needed

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
> Minimize pollution of the main session as much as possible

**Benefits**:
1. ✅ Main session is barely polluted
2. ✅ Main session stays responsive
3. ✅ Knowledge base operations complete in the background
4. ✅ Better user experience

### Responsibility Division

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

---

## Write Review Mechanism Design

### Status Markers

| Status | Marker | Meaning |
|--------|--------|---------|
| draft | `[D]` | Extracted by AI, not verified by user |
| verified | `[V]` | Explicitly confirmed by user or verified by tool |
| deprecated | `[X]` | Deprecated or proven incorrect |

### Design Considerations

**Why default to `[D]`?**
- Ensures all knowledge goes through manual review
- Prevents AI errors from polluting the knowledge base
- Users have ultimate control

**Why need the `[V]` status?**
- User-confirmed knowledge can be used directly
- Improves usage efficiency
- Establishes a trust mechanism

---

## Progressive Read Design

### Why Is Progressive Reading Needed?

**Problem**:
- The knowledge base has 8 files
- Loading everything would pollute the context
- Wastes tokens

**Solution**:
1. Read the index first (`kb-index.md`)
2. Determine what is needed
3. Only read the relevant files (1–2)

**Benefits**:
- ✅ Reduces context pollution
- ✅ Saves tokens
- ✅ Improves efficiency

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v3.1.0 | 2026-07-29 | Added initialization command, conversation export mechanism |
| v3.0.0 | 2026-07-28 | Simplified system, removed auto version |
| v2.1.0 | 2026-07-28 | Write review mechanism |
| v2.0.0 | 2026-07-28 | Skill system migration |
| v1.0.0 | 2026-07-21 | Initial version |

---

## Reference Documents

- [SKILL.md](.claude/skills/evolution/SKILL.md) - Execution instructions
- [SKILL.md](../.claude/skills/evolution/SKILL.md) - Skill definition
- [README.md](README.md) - User documentation
