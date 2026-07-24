# Evolution System

> **Human-AI Symbiosis Evolution System** - Growing together through collaboration

🌐 **Language / 语言**: [English](README.md) | [中文](README.zh-CN.md)

![Evolution Banner](https://img.shields.io/badge/Evolution-Human--AI_Symbiosis-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Claude Code](https://img.shields.io/badge/Claude_Code-Skill-purple)

---

## Table of Contents

- [Pain Points & Vision](#pain-points--vision)
- [Core Principles](#core-principles)
- [System Architecture](#system-architecture)
- [Three Background Agents](#three-background-agents)
- [Workflow](#workflow)
- [Quick Start](#quick-start)
- [Design Philosophy](#design-philosophy)
- [Contributing](#contributing)
- [License](#license)

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
│  [Background] Knowledge Base Agent records to facts.md      │
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
│  [Background] Growth Agent generates learning notes         │
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
│  AI: ✅ Done (verified at code level)                       │
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
─────────────────────────────────────────────────────────────┤
│                                                             │
│  AI: I modified the login page styles                       │
│     ↓                                                       │
│  [Background] Alignment Agent detects GUI changes           │
│     ↓                                                       │
│  AI: ️ Modified styles, but I can't verify visuals,        │
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
│  │   kb-index.md   │  ← Auto-loaded at conversation start  │
│  │                 │                                        │
│  │  📊 Overview    │  ← Tells AI what info is available    │
│  │  📁 Summary     │  ← Guides AI to load details on demand│
│  ────────────────┘                                        │
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

### Principle 3: Dual System Comparison (A/B Testing)

```
┌─────────────────────────────────────────────────────────────┐
│                  Dual System Design                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  evolution-manual/              evolution-auto/             │
│  ──────────────────┐          ┌──────────────────┐         │
│  │ Manual Trigger   │          │ Auto Trigger     │         │
│  │                  │          │                  │         │
│  │ Trigger: /evolution│        │ Trigger: Every 5 rounds│   │
│  │ Tag: manual      │          │ Tag: auto        │         │
│  └──────────────────┘          └──────────────────┘         │
│                                                             │
│  Comparison Dimensions:                                     │
│  ┌────────────────────────────┬──────────────┐            │
│  │ Dimension    │ Manual       │ Auto         │            │
│  ├────────────────────────────┼──────────────┤            │
│  │ Frequency    │ User decides │ Fixed 5 rnds │            │
│  │ Quality      │ Selective    │ Fixed logic  │            │
│  │ Completeness │ May miss     │ More systematic│          │
│  │ Awareness    │ Aware        │ Unaware      │            │
│  └──────────────┴──────────────┴──────────────┘            │
│                                                             │
│  Goal: Find optimal solution through comparison             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🏗️ System Architecture

### Directory Structure

```
evolution-manual/
├── agents/                          # Agent specifications
│   ├── knowledge-base-agent.md      # Knowledge extraction
│   ├── growth-agent.md              # Human growth
│   └── alignment-agent.md           # Human-AI alignment
│
└── knowledge-base/                  # Knowledge base data
    ├── kb-index.md                  # Index file (auto-loaded)
    ├── facts.md                     # Key facts
    ├── pitfalls.md                  # Pitfalls
    ├── state.md                     # Current state
    ├── growth-notes.md              # Learning notes
    ├── prompt-improvements.md       # Prompt improvements
    ├── alignment.md                 # Alignment checklist
    ── decisions.md                 # Decision log
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

## 🤖 Three Background Agents

### 1. Knowledge Base Agent

```
┌─────────────────────────────────────────────────────────────┐
│              Knowledge Base Agent                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Trigger: Every 5 rounds                                    │
│                                                             │
│  Input: Last 5 rounds of conversation                       │
│     ↓                                                       │
│  Processing:                                                │
│  ├── Extract key facts → facts.md                           │
│  ├── Extract pitfalls → pitfalls.md                         │
│  ├── Update state → state.md                                │
│  └── Update index → kb-index.md                             │
│                                                             │
│  Output: 1-line summary                                     │
│  `KB: +3 facts, +1 pitfall, +2 state updates`               │
│                                                             │
│  Dedup Rules:                                               │
│  - Same info → Update timestamp                             │
│  - New info → Append                                        │
└─────────────────────────────────────────────────────────────┘
```

### 2. Growth Agent

```
┌─────────────────────────────────────────────────────────────┐
│                  Growth Agent                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Trigger: Every 10 rounds                                   │
│                                                             │
│  Input: Last 10 rounds of conversation                      │
│     ↓                                                       │
│  Processing:                                                │
│  ├── Identify teaching opportunities → growth-notes.md      │
│  └── Analyze questioning style → prompt-improvements.md     │
│                                                             │
│  Output: 1-line summary                                     │
│  `Growth: +2 notes, +1 prompt tip`                          │
│                                                             │
│  Teaching Value Assessment:                                 │
│  🔴 High: User explicitly asks, recurring concepts          │
│  🟡 Medium: Related but not core                            │
│  🟢 Low: Edge concepts (skip)                               │
└─────────────────────────────────────────────────────────────┘
```

### 3. Alignment Agent

```
┌─────────────────────────────────────────────────────────────┐
│                 Alignment Agent                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Trigger: Every 5 rounds + Instant                          │
│                                                             │
│  Input: Last 5 rounds of conversation                       │
│     ↓                                                       │
│  Processing:                                                │
│  ├── Identify review items → alignment.md                   │
│  ├── Identify decision points → decisions.md                │
│  └── Flag high-risk operations → Instant alert              │
│                                                             │
│  Output: 1-line summary                                     │
│  `Alignment: +1 audit, +0 decisions`                        │
│                                                             │
│  Priority Classification:                                   │
│  🔴 High: Security, irreversible (handle immediately)       │
│  🟡 Medium: Feature review, decisions (this round)          │
│  🟢 Low: Optimization suggestions (later)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Workflow

### Complete Flow

```
User inputs /evolution
    ↓
┌─────────────────────────────────────────────────────────────┐
│  Main Agent (Scheduler)                                     │
│                                                             │
│  1. Export full conversation to temp file                   │
│     `.claude/.tmp/conv-export-{timestamp}.md`               │
│                                                             │
│  2. Launch 3 Sub-Agents in parallel                         │
│     ├── Knowledge Base Sub-Agent                            │
│     ├── Growth Sub-Agent                                    │
│     └── Alignment Sub-Agent                                 │
│                                                             │
│  3. Wait for completion, collect summaries                  │
│                                                             │
│  4. Report to user                                          │
└─────────────────────────────────────────────────────────────┘
    ↓
Evolution sync complete:
- KB: +3 facts, +1 pitfall, +2 state updates
- Growth: +2 notes, +1 prompt tip
- Alignment: +1 audit, +0 decisions
```

### Information Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Conversation Process                     │
└────────────────────────────────────────────────────────────┘
                         │
                         ↓
              ┌──────────────────────┐
              │  Conversation History│
              │  (Last 5/10 rounds)  │
              └──────────┬───────────┘
                         │
         ┌───────────────┼───────────────┐
         ↓               ↓               ↓
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Knowledge    │ │   Growth     │ │  Alignment   │
│ Base Agent   │ │   Agent      │ │   Agent      │
└──────┬───────┘ └──────┬───────┘ └──────┬───────
       │                │                │
       ↓                ↓                ↓
┌──────────────┐ ──────────────┐ ┌──────────────┐
│  facts.md    │ │ growth-      │ │ alignment.md │
│ pitfalls.md  │ │ notes.md     │ │ decisions.md │
│ state.md     │ │ prompt-      │ │              │
│              │ │ improvements │ │              │
└──────────────┘ └──────────────┘ └──────────────┘
       │                │                │
       └────────────────┼────────────────┘
                        ↓
              ┌──────────────────────┐
              │   kb-index.md        │
              │   (Index file)       │
              └──────────┬───────────┘
                         │
                         ↓
              ┌──────────────────────┐
              │  AI reads index on   │
              │  next conversation   │
              └──────────────────────┘
```

---

##  Quick Start

### 1. Installation

Copy `evolution-manual/` and `.claude/` directories to your project root:

```bash
# Copy to your project
cp -r evolution-manual/ <your-project>/
cp -r .claude/ <your-project>/
cp CLAUDE.md <your-project>/
```

### 2. Usage

Open Claude Code in your project, then:

```bash
/evolution          # Execute all three Agents
/kb-sync            # Sync knowledge base only
/growth-sync        # Generate learning notes only
/alignment-sync     # Check alignment only
```

### 3. View Results

After Agent execution, check `evolution-manual/knowledge-base/` directory:

- `kb-index.md` - Index file
- `facts.md` - Key facts
- `pitfalls.md` - Pitfalls
- `state.md` - Current state
- `growth-notes.md` - Learning notes
- `alignment.md` - Alignment checklist
- `decisions.md` - Decision log

---

## 💡 Design Philosophy

> **Don't create artificial friction. The primary goal is to complete the task perfectly, then naturally do the meaningful things.**

Evolution is not an additional burden, but a natural byproduct of task execution.

### Core Principles

| Principle | Description |
|-----------|-------------|
| **Task First** | Primary goal is task completion, not running the system |
| **Natural Occurrence** | Learning and sedimentation happen naturally during task execution |
| **Human Unaware** | Run in background, don't interfere with main conversation |
| **Gradual Growth** | Both AI and human grow through collaboration |

---

## 🤝 Contributing

Contributions are welcome! Submit Issues and Pull Requests!

### Contribution Areas

-  **Bug Fixes**
- ✨ **New Features**
- 📚 **Documentation Improvements**
- 💡 **Use Case Sharing**

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details

---

##  Author

**Evolution Team**

- Project Inspiration: Real pain points in human-AI collaboration
- Design Philosophy: Growing together through collaboration

---

## 🌟 Star History

If this project helps you, please give us a ⭐ Star!

---

<p align="center">
  <strong>Making Human-AI Collaboration More Valuable</strong>
</p>
