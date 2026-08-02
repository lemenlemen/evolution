# Evolution Version History

🌐 **Language / 语言**: [English](VERSION_HISTORY.md) | [中文](VERSION_HISTORY.zh-CN.md)

> **Current version**: 3.8.0
> **Release date**: 2026-08-01

---

## Version Change Overview

| Version | Date | Major changes |
|---------|------|---------------|
| v3.8.0 | 2026-08-01 | Fixed three bugs: enforced script + disabled manual glob, fixed find_jsonl_file to return all files, added validation mechanism |
| v3.7.0 | 2026-08-01 | Fixed `/evolution-init` command, call `evolution-export.py` to export full history, prevent sampling |
| v3.6.0 | 2026-08-01 | Split `/evolution init` into standalone command `/evolution-init`, distinguish initialization from incremental sync |
| v3.5.0 | 2026-07-31 | Refactored based on writing-great-skills rules, SKILL.md reduced from 96 lines to 37 lines |
| v3.4.0 | 2026-07-31 | Modular refactoring, SKILL.md split, config.yaml unified configuration |
| v3.3.0 | 2026-07-30 | Fixed JSON serialization crash, incremental unit drift, Windows encoding, token estimation bias (CJK coefficient 1.5→1.0), cleanup safety, file handle leaks, and other issues |
| v3.2.1 | 2026-07-30 | Updated pagination parameter: 80K → 150K (based on attention research) |
| v3.2.0-draft | 2026-07-29 | Initial design, based on 200K window assumption |
| v3.1.0 | 2026-07-29 | Added initialization command, conversation export mechanism, sub agent execution design |
| v3.0.0 | 2026-07-28 | Simplified system, removed auto version, added write review mechanism |
| v2.1.0 | 2026-07-28 | Write review mechanism (status markers) |
| v2.0.0 | 2026-07-28 | Skill system migration |
| v1.0.0 | 2026-07-21 | Initial release |

---

## v3.1.0 (2026-07-29)

### New Features

1. **Initialization command**
   - Added `/evolution init` command
   - Analyzes all historical conversations after first installation
   - Generates initial knowledge base

2. **Conversation export mechanism**
   - Method A: AI memory (default)
   - Method B: File recording (optional)

3. **Sub Agent execution design**
   - All operations executed by sub agent
   - Reduces pollution to main session

### Design Document Changes

1. **CLAUDE.md**
   - Created project configuration file
   - Defined knowledge base location

2. **SKILL.md**
   - Updated to v3.1.0
   - Added initialization command
   - Added conversation export mechanism
   - Emphasized sub agent execution principles

3. **DESIGN_V3.1.0.md**
   - Created new design document
   - Detailed design considerations
   - Documented document responsibility division

---

## v3.0.0 (2026-07-28)

**Major changes**:
- Removed `evolution-auto/` directory (auto-trigger version)
- Knowledge base directory changed from `evolution-manual/` to `evolution/`
- Simplified system, kept only manual trigger version

**Reason for changes**:
- All content must be manually reviewed
- Humans also need to read documents for learning
- Auto-trigger version was not battle-tested
- Simplify system, reduce complexity

**Modified files**:
- Deleted `evolution-auto/` directory
- Renamed `evolution-manual/` → `evolution/`
- `.claude/skills/evolution/SKILL.md`
  - Version number: 2.1.0 → 3.0.0
  - Removed "auto trigger" section
  - Removed "manual trigger" heading (only one version left)
  - Updated knowledge base location: `evolution-manual/` → `evolution/`
  - Added core principle: manual review
- `evolution/knowledge-base/kb-index.md`
  - Version number: 2.1.0 → 3.0.0
  - Removed "manual trigger" label
  - Updated location information

**Backward compatibility**:
- ❌ Not compatible (directory structure changes)
- ️ Requires migrating existing knowledge base

**Migration guide**:
```bash
# 1. Rename directory
mv evolution-manual evolution

# 2. Update path references in SKILL.md (done automatically)

# 3. Verify
/evolution
```

---

### [2.1.0] - 2026-07-28

**New features**:
- Added write review mechanism (status markers)
- New entries are marked as `[D]` (draft) by default
- User-confirmed entries are marked as `[V]` (verified)
- Deprecated entries are marked as `[X]` (deprecated)

**Modified files**:
- `.claude/skills/evolution/SKILL.md`
  - Added "Write rules (review mechanism)" section
  - Defined three-tier status model (draft/verified/deprecated)
  - Clarified write rules and conflict handling

- `evolution-manual/knowledge-base/kb-index.md`
  - Added "Reading guide (AI must follow)" section
  - Defined status marker descriptions
  - Clarified usage rules (priority, conflict handling)

- `evolution-manual/knowledge-base/facts.md`
  - Added status marker descriptions
  - Added `[V]` markers to existing entries

**Design documents**:
- `docs/FABLE_REVIEW.md` - AI reviewer's in-depth review
- `docs/PROJECT_BACKGROUND.md` - Project background (original user requirements)

**Reason for improvement**:
- AI review identified "missing write review mechanism" as a fatal flaw
- Erroneous information can form a self-reinforcing loop
- A simple review mechanism is needed to break the loop

**Impact scope**:
- All knowledge base files (facts.md, pitfalls.md, etc.)
- AI's reading and writing behavior
- Users may need to review new entries

**Backward compatibility**:
- ✅ Fully compatible with V2.0
- ✅ Old entries have no markers, default to `[D]`
- ✅ Reading rules are friendly to unmarked entries

---

### [2.0.0] - 2026-07-28

**Major changes**:
- Migrated from Slash Command to Skill system
- Supports progressive disclosure
- Supports auto trigger (AI judgment)

**New features**:
- Bidirectional capability (read + write)
- Progressive reading rules
- Separated from Auto Memory

**Modified files**:
- `.claude/skills/evolution/SKILL.md` - Created new
- `CLAUDE.md` - Deleted (Skill works independently)

**Design documents**:
- `docs/V2_DESIGN.md` - V2 design document
- `docs/EVOLUTION_RULES_AND_LOGIC_V2.md` - System rules
- `docs/INSTALLATION_GUIDE_V2.md` - Installation guide
- `docs/V2_TEST_GUIDE.md` - Test guide
- `docs/UPDATE_NOTES_V2.md` - Update notes
- `docs/PROJECT_BACKGROUND.md` - Project background
- `docs/FABLE_REVIEW.md` - AI review

**Reason for improvement**:
- V1 used Slash Command, AI was unaware of the knowledge base
- V2 uses Skill, AI knows and can auto trigger
- Saves 66% context consumption

---

### [1.0.0] - 2026-07-21

**Initial release**:
- Used Slash Command trigger
- Basic knowledge base structure
- Unidirectional capability (read only)

**Files**:
- `.claude/commands/evolution.md` - Command definition
- `evolution-manual/knowledge-base/` - Knowledge base directory

**Known issues**:
- AI is unaware of the knowledge base
- Cannot auto trigger
- High context consumption (full read)

---

## Change Statistics

| Version | Date | Type | Major changes |
|---------|------|------|---------------|
| 1.0.0 | 2026-07-21 | Initial | Slash Command |
| 2.0.0 | 2026-07-28 | MAJOR | Migrated to Skill system |
| 2.1.0 | 2026-07-28 | MINOR | Write review mechanism |
| 3.0.0 | 2026-07-28 | MAJOR | Removed auto version, simplified system |
| 3.1.0 | 2026-07-29 | MINOR | Added initialization command, conversation export mechanism |
| 3.2.0 | 2026-07-29 | MINOR | Pagination design based on 200K window |
| 3.2.1 | 2026-07-30 | PATCH | Updated pagination parameter: 80K → 150K |
| 3.3.0 | 2026-07-30 | PATCH | Fixed JSON serialization, Windows encoding, token estimation, file handle leaks |
| 3.4.0 | 2026-07-31 | MINOR | Modular refactoring, SKILL.md split, config.yaml |
| 3.5.0 | 2026-07-31 | MINOR | Refactored based on writing-great-skills rules |
| 3.6.0 | 2026-08-01 | MINOR | Split `/evolution init` into `/evolution-init` |
| 3.7.0 | 2026-08-01 | PATCH | Fixed `/evolution-init`, prevent sampling |
| 3.8.0 | 2026-08-01 | PATCH | Fixed three bugs: enforced script, find_jsonl_file, validation |

---

## Future Plans

### [4.0.0] - In planning
- Complete four-tier status model
- Evidence type classification
- Proactive review process

---

## Related Documents

| Document | Description |
|----------|-------------|
| `docs/archive/FABLE_REVIEW.md` | AI reviewer's in-depth review |
| `docs/PROJECT_BACKGROUND.md` | Project background |
| `docs/archive/V2_DESIGN.md` | V2 design document |
| `docs/archive/EVOLUTION_RULES_AND_LOGIC_V2.md` | V2 system rules |

---

**End of document**
