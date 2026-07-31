# Evolution Version History

> **Current Version**: 3.3.0
> **Release Date**: 2026-07-31

---

## Version Changes Overview

| Version | Date | Major Changes |
|---------|------|---------------|
| v3.3.0 | 2026-07-31 | Fixed JSON serialization crash, incremental unit drift, Windows encoding, token estimation bias (CJK coefficient 1.5→1.0), cleanup safety, file handle leaks, and other issues |
| v3.2.1 | 2026-07-30 | Updated pagination parameter: 80K → 150K (based on attention research) |
| v3.2.0-draft | 2026-07-29 | Initial design, based on 200K window assumption |
| v3.1.0 | 2026-07-29 | Added init command, conversation export mechanism, sub agent execution design |
| v3.0.0 | 2026-07-28 | Simplified system, removed auto version, added write review mechanism |
| v2.1.0 | 2026-07-28 | Write review mechanism (status markers) |
| v2.0.0 | 2026-07-28 | Skill system migration |
| v1.0.0 | 2026-07-21 | Initial release |

---

## v3.1.0 (2026-07-29)

### New Features

1. **Init Command**
   - Added `/evolution init` command
   - Analyzes all historical conversations after first installation
   - Generates initial knowledge base

2. **Conversation Export Mechanism**
   - Method A: AI memory (default)
   - Method B: File recording (optional)

3. **Sub Agent Execution Design**
   - All operations executed by sub agents
   - Reduces pollution to the main session

### Design Document Changes

1. **CLAUDE.md**
   - Created project configuration file
   - Defined knowledge base location

2. **SKILL.md**
   - Updated to v3.1.0
   - Added init command
   - Added conversation export mechanism
   - Emphasized sub agent execution principle

3. **DESIGN_V3.1.0.md**
   - Created new design document
   - Detailed design considerations
   - Described document responsibility division

---

## v3.0.0 (2026-07-28)

**Breaking Changes**:
- Removed `evolution-auto/` directory (auto-trigger version)
- Renamed knowledge base directory from `evolution-manual/` to `evolution/`
- Simplified system, keeping only the manual trigger version

**Reason for Changes**:
- All content must be manually verified
- Humans also need to read documents for learning
- Auto-trigger version was not battle-tested
- Simplify the system and reduce complexity

**Modified Files**:
- Deleted `evolution-auto/` directory
- Renamed `evolution-manual/` → `evolution/`
- `.claude/skills/evolution/SKILL.md`
  - Version number: 2.1.0 → 3.0.0
  - Removed "auto trigger" section
  - Removed "manual trigger" heading (only one version now)
  - Updated knowledge base location: `evolution-manual/` → `evolution/`
  - Added core principle: manual review
- `evolution/knowledge-base/kb-index.md`
  - Version number: 2.1.0 → 3.0.0
  - Removed "manual trigger" markers
  - Updated location information

**Backward Compatibility**:
- ❌ Not compatible (directory structure changes)
- ️ Existing knowledge base needs migration

**Migration Guide**:
```bash
# 1. Rename directory
mv evolution-manual evolution

# 2. Update path references in SKILL.md (done automatically)

# 3. Verify
/evolution
```

---

### [2.1.0] - 2026-07-28

**New Features**:
- Added write review mechanism (status markers)
- New entries default to `[D]` (draft)
- User-confirmed entries marked as `[V]` (verified)
- Deprecated entries marked as `[X]` (deprecated)

**Modified Files**:
- `.claude/skills/evolution/SKILL.md`
  - Added "Write Rules (Review Mechanism)" section
  - Defined three-tier status model (draft/verified/deprecated)
  - Clarified write rules and conflict handling
  
- `evolution-manual/knowledge-base/kb-index.md`
  - Added "Read Guide (AI Must Follow)" section
  - Defined status marker descriptions
  - Clarified usage rules (priority, conflict handling)

- `evolution-manual/knowledge-base/facts.md`
  - Added status marker descriptions
  - Added `[V]` markers to existing entries

**Design Documents**:
- `docs/FABLE_REVIEW.md` - AI reviewer's in-depth review
- `docs/PROJECT_BACKGROUND.md` - Project background (original user requirements)

**Reason for Improvements**:
- AI reviewer's review identified "missing write review mechanism" as a fatal flaw
- Erroneous information can form a self-reinforcing loop
- A simple review mechanism is needed to break the loop

**Scope of Impact**:
- All knowledge base files (facts.md, pitfalls.md, etc.)
- AI's read and write behavior
- Users may need to review new entries

**Backward Compatibility**:
- ✅ Fully compatible with V2.0
- ✅ Old entries have no markers, default to `[D]`
- ✅ Read rules are friendly to entries without markers

---

### [2.0.0] - 2026-07-28

**Breaking Changes**:
- Migrated from Slash Command to Skill system
- Supports progressive disclosure
- Supports auto-trigger (AI judgment)

**New Features**:
- Bidirectional capability (read + write)
- Progressive read rules
- Separated from Auto Memory

**Modified Files**:
- `.claude/skills/evolution/SKILL.md` - Created
- `CLAUDE.md` - Deleted (Skill works independently)

**Design Documents**:
- `docs/V2_DESIGN.md` - V2 design document
- `docs/EVOLUTION_RULES_AND_LOGIC_V2.md` - System rules
- `docs/INSTALLATION_GUIDE_V2.md` - Installation guide
- `docs/V2_TEST_GUIDE.md` - Test guide
- `docs/UPDATE_NOTES_V2.md` - Update notes
- `docs/PROJECT_BACKGROUND.md` - Project background
- `docs/FABLE_REVIEW.md` - AI review

**Reason for Improvements**:
- V1 used Slash Command; AI was unaware of the knowledge base
- V2 uses Skill; AI knows and can auto-trigger
- Saves 66% context consumption

---

### [1.0.0] - 2026-07-21

**Initial Release**:
- Used Slash Command trigger
- Basic knowledge base structure
- Unidirectional capability (read-only)

**Files**:
- `.claude/commands/evolution.md` - Command definition
- `evolution-manual/knowledge-base/` - Knowledge base directory

**Known Issues**:
- AI was unaware of the knowledge base
- Could not auto-trigger
- High context consumption (full read)

---

## Change Statistics

| Version | Date | Type | Major Changes |
|---------|------|------|---------------|
| 1.0.0 | 2026-07-21 | Initial | Slash Command |
| 2.0.0 | 2026-07-28 | MAJOR | Migrated to Skill system |
| 2.1.0 | 2026-07-28 | MINOR | Write review mechanism |
| 3.0.0 | 2026-07-28 | MAJOR | Removed auto version, simplified system |
| 3.1.0 | 2026-07-29 | MINOR | Added init command, conversation export mechanism |

---

## Future Plans

### [3.2.0] - Planned
- Cleanup mechanism (stale markers + auto-archiving)
- File capacity monitoring

### [4.0.0] - Under Consideration
- Complete four-tier status model
- Evidence type classification
- Proactive review workflow

---

## Related Documents

| Document | Description |
|----------|-------------|
| `docs/FABLE_REVIEW.md` | AI reviewer's in-depth review |
| `docs/PROJECT_BACKGROUND.md` | Project background |
| `docs/V2_DESIGN.md` | V2 design document |
| `docs/EVOLUTION_RULES_AND_LOGIC_V2.md` | System rules |
| `docs/INSTALLATION_GUIDE_V2.md` | Installation guide |

---

**End of Document**
