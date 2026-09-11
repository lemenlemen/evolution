# Evolution

> **Human-AI Symbiosis Evolution System** — let AI and humans grow together through collaboration

**Version**: v4.1.6 (2026-09-11)

🌐 **Language / 语言**: [English](README.md) | [中文](README.zh-CN.md)

![Evolution Banner](https://img.shields.io/badge/Evolution-Human--AI_Symbiosis-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Claude Code](https://img.shields.io/badge/Claude_Code-Skill-purple)
![Version](https://img.shields.io/badge/version-4.1.6-blue)

---

## Why

**Problem 1 — AI's amnesia.** Over a long task, the AI forgets key facts it was told, repeats the same mistakes, and can even feed its own earlier errors back into context as if they were true.

**Problem 2 — The human doesn't grow.** Across N rounds of back-and-forth, the user ends up as nothing more than a requester and a reviewer. They learn nothing, and the next task starts from the same place.

Evolution is a project-level knowledge base that runs in the background, so the AI remembers what matters — and the human picks up real knowledge along the way.

---

## Features

- Automatically extracts key knowledge from conversation history
- Progressive knowledge base growth — the AI gets smarter with use
- Three-tier status markers (`[D]` / `[V]` / `[X]`) with human review
- Dual cursors + batch commit protocol — prevents data loss
- Integrity check (sha256), atomic writes, and a three-tier recovery chain
- Streaming export with global time ordering (handles multi-session histories)

---

## Quick Start

```bash
# First-time initialization (analyzes full conversation history)
/evolution-init

# Daily incremental sync
/evolution
```

Install by copying `.claude/skills/evolution/` and `evolution/` into your project root.
See the [Installation Guide](docs/INSTALLATION_GUIDE.md) for details.

---

## How It Works

```
User runs /evolution
        │
        ▼
Main agent triggers a sub agent (background)
        │
        ▼
Sub agent:
  1. Calls evolution-export.py → parses JSONL history into chunks
  2. Analyzes each chunk, extracts knowledge
  3. Deduplicates against the existing knowledge base
  4. Writes entries as [D] (draft), then commits the batch
        │
        ▼
Main agent shows a one-line summary
```

| Command | Purpose |
|---------|---------|
| `/evolution-init` | Initialize the knowledge base from the full history |
| `/evolution` | Incremental sync of new conversation |

---

## Documentation

Full bilingual documentation lives in [`docs/`](docs/).

### Getting started
1. [Project Background](docs/PROJECT_BACKGROUND.md) — the pain points behind the system
2. [Installation Guide](docs/INSTALLATION_GUIDE.md) — install and verify
3. [Version History](docs/VERSION_HISTORY.md) — what changed, version by version

### Design
- [V4 Design Document](docs/v4/DESIGN_V4.0.0.md) — current architecture (master)
- [V4 Sync Engine Design](docs/v4/design-v4-engine.md) — data integrity and robustness
- [V4 Knowledge Layer Design](docs/v4/design-v4-knowledge.md) — knowledge quality (historical; rolled back)
- [V3 System Rules](docs/EVOLUTION_RULES_AND_LOGIC_V3.md) — V3-era rules and logic
- [Export & Analysis Design](docs/EXPORT_AND_ANALYSIS_DESIGN.md) — conversation export pipeline
- [Adversarial Audit](docs/ADVERSARIAL_AUDIT_v3.9.0.md) — the audit that drove V4 (Chinese only)

### Archive
V1/V2-era documents are kept in [`docs/archive/`](docs/archive/).

---

## Privacy

Knowledge base files are public with this repository. Please review for sensitive information before writing.

Raw conversation history (`.evolution/chunks/`, `sync-state.json`) is excluded via `.gitignore` and is never uploaded.

Before any release, run a privacy scan over the whole repository for: employer/personal names, local absolute paths (four forms: backslash, upper-case drive with forward slash, WSL lower-case drive, bare parent directory), project hashes, session UUIDs, known sha256 prefixes, and raw state snapshot values.

---

## Knowledge Base Layout

```
evolution/knowledge-base/
├── kb-index.md              # Index (entry point, <200 lines)
├── facts.md                 # Key facts
├── pitfalls.md              # Pitfalls
├── state.md                 # Current state
├── growth-notes.md          # Learning notes
├── prompt-improvements.md   # Prompt improvement suggestions
├── alignment.md             # Alignment checklist
└── decisions.md             # Decision log
```

---

## License

MIT — see [LICENSE](LICENSE).
