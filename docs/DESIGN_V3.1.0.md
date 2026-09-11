# Evolution Design Document v3.9.0

🌐 **Language / 语言**: [English](DESIGN_V3.1.0.md) | [中文](DESIGN_V3.1.0.zh-CN.md)

> **Version**: 3.9.0
> **Date**: 2026-08-01
> **Status**: Design complete

---

## Core Design Principle

> **When Evolution runs, it dispatches sub agents to handle things, minimizing pollution of the main session**

---

## Architecture Design

### Document Responsibilities

| File | Purpose | Reader |
|------|------|------|
| `CLAUDE.md` | Project configuration | AI |
| `.claude/skills/evolution/SKILL.md` | Execution instructions | AI |
| `docsV3/` | Design documents | Humans |

---

## Execution Command Design

### Initialization Command

```bash
/evolution-init
```

**Design considerations**:
- Used after first installation
- Analyzes all historical conversations
- Builds the initial knowledge base
- All entries marked as `[D]` (draft)

**Execution flow**:
```
User enters /evolution-init
    ↓
Main agent triggers sub agent
    ↓
Sub agent in the background:
  1. Analyze all historical conversations
  2. Extract all key facts
  3. Record all pitfalls
  4. Generate the initial knowledge base
  5. Mark all entries as [D]
    ↓
Return summary to main agent
    ↓
Main agent displays summary
```

---

## Conversation Export Mechanism Design

### Export Method: evolution-export.py

**Design considerations**:
- Export all historical conversations via a script to prevent sampling
- Support full export (`--mode full`) and incremental export (`--mode incremental`)
- Cross-process file lock ensures concurrency safety
- The main session is barely polluted

**Applicable scenarios**:
- Initialization (`/evolution-init`): full export of all historical conversations
- Incremental sync (`/evolution`): export only new conversations

**Execution**:
```bash
# Full export (initialization)
python .claude/skills/evolution/evolution-export.py --mode full

# Incremental export (sync)
python .claude/skills/evolution/evolution-export.py --mode incremental
```

---

## Sub Agent Execution Design

### Why Use a Sub Agent?

**Core principle**:
> Minimize pollution of the main session

**Benefits**:
1. ✅ The main session is barely polluted
2. ✅ The main session stays smooth
3. ✅ Knowledge base operations are completed in the background
4. ✅ Better user experience

### Division of Responsibilities

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

---

## Write Review Mechanism Design

### Status Markers

| Status | Marker | Meaning |
|------|------|------|
| draft | `[D]` | Extracted by AI, not verified by the user |
| verified | `[V]` | Explicitly confirmed by the user or verified by a tool |
| deprecated | `[X]` | Deprecated or proven wrong |

### Design Considerations

**Why mark as `[D]` by default?**
- Ensure all knowledge goes through human review
- Prevent AI error information from polluting the knowledge base
- The user has final control

**Why is the `[V]` status needed?**
- Knowledge confirmed by the user can be used directly
- Improve usage efficiency
- Build a trust mechanism

---

## Progressive Reading Design

### Why Is Progressive Reading Needed?

**Problem**:
- The knowledge base has 8 files
- Loading everything pollutes the context
- Wastes tokens

**Solution**:
1. Read the index first (`kb-index.md`)
2. Determine what is needed
3. Read only relevant files (1-2)

**Benefits**:
- ✅ Reduce context pollution
- ✅ Save tokens
- ✅ Improve efficiency

---

## Version History

| Version | Date | Change |
|------|------|------|
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

## Reference Documents

- [SKILL.md](../.claude/skills/evolution/SKILL.md) - Execution instructions
- [CLAUDE.md](../CLAUDE.md) - Project configuration
