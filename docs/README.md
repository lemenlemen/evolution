# Evolution Documentation

🌐 **Language / 语言**: [English](README.md) | [中文](README.zh-CN.md)

> **Version**: 4.1.6
> **Last updated**: 2026-09-11

---

## Document Structure

```
docs/
├── README.md                        # This document (index)
├── PROJECT_BACKGROUND.md            # Project background and pain points
├── INSTALLATION_GUIDE.md            # Installation guide
├── VERSION_HISTORY.md               # Version history
├── DESIGN_V3.1.0.md                 # V3.1.0 design document (historical)
├── EVOLUTION_RULES_AND_LOGIC_V3.md  # V3 system rules and logic (outdated)
├── EXPORT_AND_ANALYSIS_DESIGN.md    # Export and analysis design
├── ADVERSARIAL_AUDIT_v3.9.0.md      # Adversarial audit that drove V4 (Chinese only)
├── v4/                              # V4 design documents (current)
│   ├── DESIGN_V4.0.0.md             # V4 master design
│   ├── design-v4-engine.md          # V4 sync engine layer
│   └── design-v4-knowledge.md       # V4 knowledge layer (rolled back)
└── archive/                         # Historical document archive
    ├── V1_REVIEW.md                 # V1 review
    ├── V2_DESIGN.md                 # V2 design
    ├── V2_TEST_GUIDE.md             # V2 test guide
    ├── UPDATE_NOTES_V2.md           # V2 update notes
    ├── EVOLUTION_RULES_AND_LOGIC_V2.md # V2 rules
    ├── EARLY_REVIEW.md              # Early deep review
    ├── SKILL_LOADING_MECHANISM.md   # Skill loading mechanism study
    ├── IMPLEMENTATION_PLAN.md       # V2 implementation plan
    ├── STATUS.md                    # V2 status
    └── evolution-manual-v2/         # Raw V2 knowledge base snapshot
```

Every document above has a `.zh-CN.md` Chinese counterpart, except the two marked Chinese-only.

---

## Reading Order

### New users
1. [PROJECT_BACKGROUND.md](./PROJECT_BACKGROUND.md) — understand the pain points
2. [INSTALLATION_GUIDE.md](./INSTALLATION_GUIDE.md) — install and verify
3. [VERSION_HISTORY.md](./VERSION_HISTORY.md) — see what changed

### Upgrading users
1. [VERSION_HISTORY.md](./VERSION_HISTORY.md) — version changes
2. [INSTALLATION_GUIDE.md](./INSTALLATION_GUIDE.md) — upgrade steps

### Developers
1. [v4/DESIGN_V4.0.0.md](./v4/DESIGN_V4.0.0.md) — current architecture
2. [v4/design-v4-engine.md](./v4/design-v4-engine.md) — data integrity layer
3. [EXPORT_AND_ANALYSIS_DESIGN.md](./EXPORT_AND_ANALYSIS_DESIGN.md) — export pipeline
4. [ADVERSARIAL_AUDIT_v3.9.0.md](./ADVERSARIAL_AUDIT_v3.9.0.md) — the audit behind V4

---

## Core Documents

| Document | Description | Audience |
|----------|-------------|----------|
| [.claude/skills/evolution/SKILL.md](../.claude/skills/evolution/SKILL.md) | Execution instructions (the actual skill) | AI |
| [PROJECT_BACKGROUND.md](./PROJECT_BACKGROUND.md) | Project background | Human |
| [INSTALLATION_GUIDE.md](./INSTALLATION_GUIDE.md) | Installation guide | Human |
| [VERSION_HISTORY.md](./VERSION_HISTORY.md) | Version history | Human |
| [v4/DESIGN_V4.0.0.md](./v4/DESIGN_V4.0.0.md) | Current design | Human |
| [EXPORT_AND_ANALYSIS_DESIGN.md](./EXPORT_AND_ANALYSIS_DESIGN.md) | Export and analysis design | Human |

> Historical documents (`DESIGN_V3.1.0.md`, `EVOLUTION_RULES_AND_LOGIC_V3.md`) describe V3-era behavior. They are kept for reference; the V4 documents above supersede them.

---

## Version Information

See [VERSION_HISTORY.md](./VERSION_HISTORY.md) for the full changelog.

| Version | Date | Major changes |
|---------|------|---------------|
| v4.1.6 | 2026-09-11 | Privacy generalization, version unification, design doc annotations, installation guide completion |
| v4.1.5 | 2026-09-10 | sha256 regression test rewrite, Python version fix, archive dead-link fix |
| v4.1.4 | 2026-09-10 | Release rules, sha256 regression test, version unification |
| v4.1.3 | 2026-09-10 | sha256 refresh fix (incremental false `file-replaced`), README, KB privacy cleanup, LICENSE |
| v4.1.2 | 2026-09-10 | Adversarial review fixes (cleanup state protection, lock path, read-only status, exit codes) |
| v4.1.1 | 2026-09-10 | Path anchoring, version labeling, kb-manager archival |
| v4.1.0 | 2026-09-10 | Kept engine-layer fixes, rolled back knowledge-layer over-engineering |
| v4.0.0 | 2026-08-24 | MAJOR: dual cursors + batch commit, integrity check, atomic writes |
| v3.9.0 | 2026-08-01 | Added `/evolution-init` pre-check |

---

**Welcome to Evolution v4.1.6!**
