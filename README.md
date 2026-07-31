# Evolution System

> **Human-AI Symbiosis Evolution System** — Growing together through collaboration

**Version**: v3.3.0 (2026-07-31)

🌐 **Language / 语言**: [English](README.md) | [中文](README.zh-CN.md)

![Evolution Banner](https://img.shields.io/badge/Evolution-Human--AI_Symbiosis-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Claude Code](https://img.shields.io/badge/Claude_Code-Skill-purple)
![Version](https://img.shields.io/badge/version-3.3.0-blue)

---

## Table of Contents

- [Pain Points & Vision](#-pain-points--vision)
- [Core Principles](#-core-principles)
- [System Architecture](#-system-architecture)
- [Execution Model](#-execution-model)
- [Workflow](#-workflow)
- [Quick Start](#-quick-start)
- [Documentation](#-documentation)
- [Design Philosophy](#-design-philosophy)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Pain Points & Vision

### Problem 1: AI's "Amnesia"

**The Problem**:

```
┌─────────────────────────────────────────────────────────────┐
│  Traditional AI Collaboration                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Round 1: User says "Project uses Python 3.11"              │
│     ↓                                                       │
│  Round 10: AI asks "What's your Python version?" ← Forgot! │
│     ↓                                                       │
│  Round 15: User repeats "It's 3.11"                         │
│     ↓                                                       │
│  Round 20: AI asks "Python version?" ← Forgot again!       │
│                                                             │
│  Result: Users repeatedly answer the same questions         │
─────────────────────────────────────────────────────────────┘
```

**Evolution's Solution**:

```
┌─────────────────────────────────────────────────────────────┐
│  Evolution Collaboration Mode                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Round 1: User says "Project uses Python 3.11"              │
│     ↓                                                       │
│  [Background] Sub-agent records to facts.md                 │
│     ↓                                                       │
│  Round 10: AI reads facts.md, knows it's 3.11               │
│     ↓                                                       │
│  Round 15: AI continues using 3.11 correctly                │
│                                                             │
│  Result: AI remembers key info, users don't repeat          │
└─────────────────────────────────────────────────────────────┘
```

### Problem 2: Human's "Growth Gap"

**The Problem**:

```
┌─────────────────────────────────────────────────────────────┐
│  Traditional Mode: Human is just the "Client"                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User: Help me fix this bug                                 │
│     ↓                                                       │
│  AI: Fixed (user doesn't know why)                          │
│     ↓                                                       │
│  User: Still can't do it next time                          │
│     ↓                                                       │
│  Result: Humans don't grow, always depend on AI             │
└─────────────────────────────────────────────────────────────┘
```

**Evolution's Solution**:

```
┌─────────────────────────────────────────────────────────────┐
│  Evolution Mode: Human-AI Co-Growth                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User: Help me fix this bug                                 │
│     ↓                                                       │
│  AI: Fixed                                                  │
│     ↓                                                       │
│  [Background] Sub-agent generates learning notes            │
│     ↓                                                       │
│  AI: Explains "This bug is because XXX, fixed by YYY"       │
│     ↓                                                       │
│  Result: Humans learn, can solve independently next time    │
└─────────────────────────────────────────────────────────────┘
```

### Problem 3: Human-AI "Cognitive Misalignment"

**The Problem**:

```
┌─────────────────────────────────────────────────────────────┐
│  Traditional: AI thinks it's right, human finds it wrong    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  AI: I modified the login page styles                       │
│     ↓                                                       │
│  AI: Done (verified at code level)                          │
│     ↓                                                       │
│  User: Opens browser, styles are completely wrong!          │
│     ↓                                                       │
│  Result: Rework, wasted time                                │
└─────────────────────────────────────────────────────────────┘
```

**Evolution's Solution**:

```
┌─────────────────────────────────────────────────────────────┐
│  Evolution Mode: Maintain Human-AI Alignment                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  AI: I modified the login page styles                       │
│     ↓                                                       │
│  [Background] Sub-agent flags items needing review          │
│     ↓                                                       │
│  AI: Modified styles, but I can't verify visuals,           │
│      please check in browser                                │
│     ↓                                                       │
│  User: Opens browser, confirms, finds issues                │
│     ↓                                                       │
│  Result: Catch issues early, avoid rework                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧠 Core Principles

### Principle 1: Index + Detail File Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Knowledge Base Architecture                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐                                        │
│  │   kb-index.md   │  ← Read on demand (not auto-loaded)   │
│  │                 │                                        │
│  │  Overview       │  ← Tells AI what info is available    │
│  │  Summary        │  ← Guides AI to load details on demand│
│  └─────────────────┘                                        │
│           │                                                 │
│           ↓ Load on demand                                  │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │    facts.md     │  │  pitfalls.md    │  ← Detail files │
│  │                 │  │                 │                  │
│  │  • Env config   │  │  • Error modes  │                  │
│  │  • Decisions    │  │  • Solutions    │                  │
│  │  • Dependencies │  │  • Notes        │                  │
│  └─────────────────┘  └─────────────────┘                  │
│                                                             │
│  Benefits:                                                  │
│  ✅ Small index (<200 lines), fast loading                  │
│  ✅ Details loaded on demand, saves tokens                  │
│  ✅ Clear structure, easy to maintain                       │
└─────────────────────────────────────────────────────────────┘
```

### Principle 2: Incremental Write + Deduplication

```
┌─────────────────────────────────────────────────────────────┐
│                 Data Write Strategy                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  First /evolution                                           │
│     ↓                                                       │
│  facts.md:                                                  │
│  - [10:00] WSL network must use mirrored mode               │
│                                                             │
│  Second /evolution (2 hours later)                          │
│     ↓                                                       │
│  facts.md:                                                  │
│  - [10:00] WSL network must use mirrored mode               │
│    ← Update timestamp, no new entry                         │
│  - [12:00] Python version must be 3.11                      │
│    ← New entry                                              │
│                                                             │
│  Rules:                                                     │
│  ✅ Same info → Update timestamp                            │
│  ✅ New info → Append                                       │
│  ✅ Status update → Mark as "Done"                          │
└─────────────────────────────────────────────────────────────┘
```

### Principle 3: Manual Review (Write Audit)

```
┌─────────────────────────────────────────────────────────────┐
│                Write Audit Mechanism                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Every new entry gets a status tag:                         │
│                                                             │
│  [D] Draft     — AI extracted, not yet verified             │
│  [V] Verified  — User confirmed or tool-validated           │
│  [X] Deprecated — Wrong or superseded                       │
│                                                             │
│  Read priority:                                             │
│  1. [V] entries are trusted                                 │
│  2. [D] entries are usable but marked "unverified"          │
│  3. [X] entries are never read                              │
│                                                             │
│  Goal: Prevent AI error self-reinforcement                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🏗️ System Architecture

### Directory Structure

```
<your-project>/
│
├── .claude/
│   └── skills/
│       └── evolution/
│           └── SKILL.md                     # Skill definition (AI reads)
│
├── evolution/                                # Knowledge base
│   └── knowledge-base/
│       ├── kb-index.md                       # Index file
│       ├── facts.md                          # Key facts
│       ├── pitfalls.md                       # Pitfalls
│       ├── state.md                          # Current state
│       ├── growth-notes.md                   # Learning notes
│       ├── prompt-improvements.md            # Prompt improvements
│       ├── alignment.md                      # Alignment checklist
│       └── decisions.md                      # Decision log
│
└── docs/                                     # Bilingual documentation
    ├── README.md                             # Documentation index (EN)
    ├── README.zh-CN.md                       # Documentation index (ZH)
    ├── PROJECT_BACKGROUND.md                 # Project background
    ├── INSTALLATION_GUIDE.md                 # Installation guide
    ├── VERSION_HISTORY.md                    # Version history
    ├── DESIGN_V3.1.0.md                      # Design document
    ├── EVOLUTION_RULES_AND_LOGIC_V3.md       # System rules
    ├── EXPORT_AND_ANALYSIS_DESIGN.md         # Export design (v3.3.0)
    ├── *.zh-CN.md                            # Chinese versions of above
    ├── agents/                               # Agent configuration
    │   ├── domain.md
    │   ├── issue-tracker.md
    │   └── triage-labels.md
    └── archive/                              # Historical docs (V1/V2)
        └── ...
```

### File Responsibilities

| File | Consumer | Description |
|------|----------|-------------|
| `kb-index.md` | AI | Index file, tells AI what's available |
| `facts.md` | AI | Key facts (env config, decisions) |
| `pitfalls.md` | AI | Pitfalls (error modes, solutions) |
| `state.md` | AI | Current state (progress, pending) |
| `growth-notes.md` | Human | Learning notes (concept explanations) |
| `prompt-improvements.md` | Human | Prompt improvement suggestions |
| `alignment.md` | Human+AI | Alignment checklist (pending reviews) |
| `decisions.md` | Human+AI | Decision log (pending decisions) |

---

## 🤖 Execution Model

> **All Evolution operations run as sub-agents to minimize main-session pollution.**

### How It Works

```
User inputs /evolution
    ↓
┌─────────────────────────────────────────────────────────────┐
│  Main Agent (Scheduler)                                     │
│                                                             │
│  1. Receive user command                                    │
│  2. Trigger sub-agent in background                         │
│  3. Display sub-agent summary when done                     │
│  4. Does NOT directly operate the knowledge base            │
└─────────────────────────┬───────────────────────────────────┘
                          │ triggers
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Sub-Agent (Background Worker)                              │
│                                                             │
│  1. Read conversation context                               │
│  2. Extract knowledge                                       │
│  3. Write to knowledge base                                 │
│  4. Return summary to main agent                            │
└─────────────────────────────────────────────────────────────┘
```

### Available Commands

| Command | Description |
|---------|-------------|
| `/evolution` | Full sync (all knowledge extraction) |
| `/evolution init` | Initial sync — analyze full conversation history, build knowledge base from scratch |
| `/evolution --history` | Analyze persisted conversation history files (cross-session) |
| `/kb-sync` | Sync knowledge base only |
| `/growth-sync` | Generate learning notes only |
| `/alignment-sync` | Check alignment items only |

### Conversation Export Methods

**Method A: AI Memory (default)**
- Sub-agent analyzes current session's conversation context
- Simple, real-time, no extra files needed
- Limited to current session

**Method B: File Record (optional)**
- Sub-agent reads `.claude/.tmp/conversation-*.md` files
- Persistent, traceable, supports cross-session analysis
- Requires conversation export files

---

## 🔄 Workflow

### Complete Flow

```
User inputs /evolution
    ↓
Main Agent → Sub-Agent (background)
    ↓
Sub-Agent:
  ├── Read conversation context
  ├── Read kb-index.md (understand existing knowledge)
  ├── Extract knowledge
  │   ├── Key facts → facts.md
  │   ├── Pitfalls → pitfalls.md
  │   ├── State changes → state.md
  │   ├── Learning points → growth-notes.md
  │   ├── Prompt improvements → prompt-improvements.md
  │   ├── Alignment items → alignment.md
  │   └── Decisions → decisions.md
  ├── Deduplicate with existing knowledge
  ├── Update kb-index.md
  └── Return summary
    ↓
Main Agent displays summary:
  "Sync complete: +3 facts, +1 pitfall, +2 state updates"
```

### Information Flow

```
┌──────────────────────┐
│  Conversation Context│
│  (current session)   │
└──────────┬───────────┘
           │
           ↓
    ┌──────────────┐
    │  Sub-Agent   │
    │  (background)│
    └──────┬───────┘
           │
           ↓
┌──────────────────────────────────────────┐
│  Knowledge Base (8 .md files)            │
│                                          │
│  facts.md  pitfalls.md  state.md         │
│  growth-notes.md  prompt-improvements.md │
│  alignment.md  decisions.md              │
└──────────────────────────────────────────┘
           │
           ↓
┌──────────────────────┐
│   kb-index.md        │
│   (updated)          │
└──────────┬───────────┘
           │
           ↓
┌──────────────────────┐
│  AI reads index on   │
│  next conversation   │
└──────────────────────┘
```

---

## 🚀 Quick Start

### 1. Installation

**Option A: Copy from this repo**

```bash
# Clone the repo
git clone https://github.com/lemenlemen/evolution.git
cd evolution

# Copy skill and knowledge-base to your project
cp -r .claude/skills/evolution/ <your-project>/.claude/skills/
cp -r evolution/ <your-project>/
```

**Option B: Download SKILL.md directly**

```bash
# Create skill directory
mkdir -p .claude/skills/evolution

# Download SKILL.md
curl -o .claude/skills/evolution/SKILL.md \
  https://raw.githubusercontent.com/lemenlemen/evolution/main/.claude/skills/evolution/SKILL.md

# Create knowledge-base directory with templates
mkdir -p evolution/knowledge-base
# (copy template files from the repo)
```

See [Installation Guide](docs/INSTALLATION_GUIDE.md) for full instructions.

### 2. Usage

Open Claude Code in your project, then:

```bash
/evolution init   # First time: analyze full conversation, build knowledge base
/evolution        # Subsequent: incremental sync
```

### 3. View Results

After execution, check `evolution/knowledge-base/` directory:

- `kb-index.md` - Index file
- `facts.md` - Key facts
- `pitfalls.md` - Pitfalls
- `state.md` - Current state
- `growth-notes.md` - Learning notes
- `alignment.md` - Alignment checklist
- `decisions.md` - Decision log

---

## 📚 Documentation

Full bilingual documentation is in the [`docs/`](docs/) directory.

### For New Users

1. [Project Background](docs/PROJECT_BACKGROUND.md) — understand the pain points
2. [Installation Guide](docs/INSTALLATION_GUIDE.md) — get set up
3. [Design Document](docs/DESIGN_V3.1.0.md) — learn design details

### For Upgrading Users

1. [Version History](docs/VERSION_HISTORY.md) — check what changed
2. [Installation Guide](docs/INSTALLATION_GUIDE.md) — upgrade steps

### For Developers

1. [Design Document](docs/DESIGN_V3.1.0.md)
2. [System Rules](docs/EVOLUTION_RULES_AND_LOGIC_V3.md)
3. [Export & Analysis Design](docs/EXPORT_AND_ANALYSIS_DESIGN.md) (v3.3.0)
4. [Historical docs](docs/archive/) (V1/V2 era)

### Chinese Versions

All documents have `.zh-CN.md` Chinese counterparts:
- [中文文档索引](docs/README.zh-CN.md)
- [项目背景](docs/PROJECT_BACKGROUND.zh-CN.md)
- [安装指南](docs/INSTALLATION_GUIDE.zh-CN.md)
- etc.

---

## 💡 Design Philosophy

> **Don't create artificial friction. The primary goal is to complete the task perfectly, then naturally do the meaningful things.**

Evolution is not an additional burden, but a natural byproduct of task execution.

### Core Principles

| Principle | Description |
|-----------|-------------|
| **Task First** | Primary goal is task completion, not running the system |
| **Natural Occurrence** | Learning and sedimentation happen naturally during task execution |
| **Sub-Agent Isolation** | Run in background, don't pollute main conversation |
| **Gradual Growth** | Both AI and human grow through collaboration |
| **Honest & Transparent** | AI honestly reports limitations and issues |

---

## 🤝 Contributing

Contributions are welcome! Submit Issues and Pull Requests!

### Contribution Areas

- 🐛 **Bug Fixes**
- ✨ **New Features**
- 📚 **Documentation Improvements**
- 💡 **Use Case Sharing**

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details

---

## 👤 Author

**lemen**

- Project Inspiration: Real pain points in human-AI collaboration
- Design Philosophy: Growing together through collaboration

---

## 🌟 Star History

If this project helps you, please give it a ⭐ Star!

---

<p align="center">
  <strong>Making Human-AI Collaboration More Valuable</strong>
</p>
