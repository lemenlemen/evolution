# Evolution V3 Documentation

🌐 **Language / 语言**: [English](README.md) | [中文](README.zh-CN.md)

> **Version**: 3.8.0
> **Last updated**: 2026-07-31

---

## Document Structure

```
docs/
├── README.md                      # This document (index)
├── PROJECT_BACKGROUND.md          # Project background
├── DESIGN_V3.1.0.md               # V3.1.0 design document (historical)
├── INSTALLATION_GUIDE.md          # Installation guide
├── VERSION_HISTORY.md             # Version history
├── EXPORT_AND_ANALYSIS_DESIGN.md  # Export and analysis design (v3.8.0)
├── EVOLUTION_RULES_AND_LOGIC_V3.md  # System rules (v3)
└── archive/                       # Historical document archive
    ├── V1_REVIEW.md               # V1 review
    ├── V2_DESIGN.md               # V2 design
    ├── V2_TEST_GUIDE.md           # V2 testing
    ├── UPDATE_NOTES_V2.md         # V2 update notes
    ├── EVOLUTION_RULES_AND_LOGIC_V2.md  # V2 rules
    ├── FABLE_REVIEW.md            # AI review
    ├── SKILL_LOADING_MECHANISM.md # Skill loading mechanism
    ├── IMPLEMENTATION_PLAN.md     # V2 implementation plan
    └── STATUS.md                  # V2 status
```

---

## Reading Order

### New users
1. [PROJECT_BACKGROUND.md](./PROJECT_BACKGROUND.md) - Understand the project background and pain points
2. [INSTALLATION_GUIDE.md](./INSTALLATION_GUIDE.md) - Install and verify
3. [DESIGN_V3.1.0.md](./DESIGN_V3.1.0.md) - Learn design details (optional)

### Upgrading users
1. [VERSION_HISTORY.md](./VERSION_HISTORY.md) - Check version changes
2. [INSTALLATION_GUIDE.md](./INSTALLATION_GUIDE.md) - Upgrade guide

### Developers
1. [DESIGN_V3.1.0.md](./DESIGN_V3.1.0.md) - Complete design document
2. [VERSION_HISTORY.md](./VERSION_HISTORY.md) - Version history
3. [archive/](./archive/) - Historical documents

---

## Core Documents

| Document | Description | Audience |
|----------|-------------|----------|
| [CLAUDE.md](../CLAUDE.md) | Project configuration | AI |
| [.claude/skills/evolution/SKILL.md](../.claude/skills/evolution/SKILL.md) | Execution instructions | AI |
| [PROJECT_BACKGROUND.md](./PROJECT_BACKGROUND.md) | Project background | Humans |
| [INSTALLATION_GUIDE.md](./INSTALLATION_GUIDE.md) | Installation guide | Humans |
| [DESIGN_V3.1.0.md](./DESIGN_V3.1.0.md) | Design document | Humans |
| [VERSION_HISTORY.md](./VERSION_HISTORY.md) | Version history | Humans |

---

## Version Information

| Version | Date | Major changes |
|---------|------|---------------|
| v3.8.0 | 2026-08-01 | Fixed three bugs: enforced script + disabled manual glob, fixed find_jsonl_file to return all files, added validation mechanism |
| v3.7.0 | 2026-08-01 | Fixed `/evolution-init` command, call `evolution-export.py` to export full history, prevent sampling |
| v3.6.0 | 2026-08-01 | Split `/evolution init` into standalone command `/evolution-init`, distinguish initialization from incremental sync |
| v3.5.0 | 2026-07-31 | Refactored based on writing-great-skills rules, SKILL.md reduced from 96 lines to 37 lines |
| v3.4.0 | 2026-07-31 | Modular refactoring, SKILL.md split, config.yaml unified configuration |
| v3.3.0 | 2026-07-30 | Fixed JSON serialization crash, incremental unit drift, Windows encoding, token estimation bias, cleanup safety, file handle leaks |
| v3.2.1 | 2026-07-30 | Updated pagination parameter: 80K → 150K (based on attention research) |
| v3.2.0-draft | 2026-07-29 | Initial design, based on 200K window assumption |
| v3.1.0 | 2026-07-29 | Added initialization command, conversation export mechanism |
| v3.0.0 | 2026-07-28 | Simplified system, removed auto version |
| v2.1.0 | 2026-07-28 | Write review mechanism |
| v2.0.0 | 2026-07-28 | Skill system migration |
| v1.0.0 | 2026-07-21 | Initial release |

---

**Welcome to Evolution v3.8.0!**
