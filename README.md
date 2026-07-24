# Evolution System

> **Human-AI Symbiosis Evolution System** - Growing together through collaboration
> **人机共生进化系统** - 让 AI 和人类在协作中共同成长

![Evolution Banner](https://img.shields.io/badge/Evolution-Human--AI_Symbiosis-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Claude Code](https://img.shields.io/badge/Claude_Code-Skill-purple)

---

##  Table of Contents / 目录

- [Pain Points & Vision / 痛点与初衷](#pain-points--vision--痛点与初衷)
- [Core Principles / 核心原理](#core-principles--核心原理)
- [System Architecture / 系统架构](#system-architecture--系统架构)
- [Three Background Agents / 三个后台 Agent](#three-background-agents--三个后台-agent)
- [Workflow / 工作流程](#workflow--工作流程)
- [Quick Start / 快速开始](#quick-start--快速开始)
- [Design Philosophy / 设计理念](#design-philosophy--设计理念)
- [Contributing / 贡献](#contributing--贡献)
- [License / 许可证](#license--许可证)

---

## 🎯 Pain Points & Vision / 痛点与初衷

### Problem 1: AI's "Amnesia" / AI 的"失忆症"

**The Problem / 问题**：

```
┌─────────────────────────────────────────────────────────────┐
│  Traditional AI Collaboration / 传统 AI 协作模式             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Round 1: User says "Project uses Python 3.11"              │
│           用户说"项目用 Python 3.11"                         │
│     ↓                                                       │
│  Round 10: AI asks "What's your Python version?" ← Forgot! │
│            AI 问"你的 Python 版本是多少？"  ← 忘记了！        │
│     ↓                                                       │
│  Round 15: User repeats "It's 3.11"                         │
│            用户重复"是 3.11"                                 │
│     ↓                                                       │
│  Round 20: AI asks "Python version?" ← Forgot again!       │
│            AI 又问"Python 版本？"           ← 又忘了！        │
│                                                             │
│  Result: Users repeatedly answer the same questions         │
│  结果：用户反复回答相同问题，效率低下                         │
└─────────────────────────────────────────────────────────────┘
```

**Evolution's Solution / Evolution 的解决方案**：

```
┌─────────────────────────────────────────────────────────────┐
│  Evolution Collaboration Mode / Evolution 协作模式           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Round 1: User says "Project uses Python 3.11"              │
│           用户说"项目用 Python 3.11"                         │
│     ↓                                                       │
│  [Background] Knowledge Base Agent records to facts.md      │
│  [后台] Knowledge Base Agent 记录到 facts.md                 │
│     ↓                                                       │
│  Round 10: AI reads facts.md, knows it's 3.11               │
│            AI 自动读取 facts.md，知道是 3.11                 │
│     ↓                                                       │
│  Round 15: AI continues using 3.11 correctly                │
│            AI 继续正确使用 3.11                              │
│                                                             │
│  Result: AI remembers key info, users don't repeat          │
│  结果：AI 记住关键信息，用户无需重复                          │
└─────────────────────────────────────────────────────────────┘
```

### Problem 2: Human's "Growth Gap" / 人类的"成长缺失"

**The Problem / 问题**：

```
┌─────────────────────────────────────────────────────────────┐
│  Traditional Mode: Human is just the "Client"               │
│  传统模式：人类只是"甲方"                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User: Help me fix this bug / 帮我修这个 bug                 │
│     ↓                                                       │
│  AI: Fixed (user doesn't know why)                          │
│      修复了（用户不知道为什么这样修）                        │
│     ↓                                                       │
│  User: Still can't do it next time / 下次还是不会           │
│     ↓                                                       │
│  Result: Humans don't grow, always depend on AI             │
│  结果：人类没有成长，永远依赖 AI                              │
└─────────────────────────────────────────────────────────────┘
```

**Evolution's Solution / Evolution 的解决方案**：

```
┌─────────────────────────────────────────────────────────────┐
│  Evolution Mode: Human-AI Co-Growth                         │
│  Evolution 模式：人机共同成长                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User: Help me fix this bug / 帮我修这个 bug                 │
│     ↓                                                       │
│  AI: Fixed / 修复了                                          │
│     ↓                                                       │
│  [Background] Growth Agent generates learning notes         │
│  [后台] Growth Agent 生成学习笔记到 growth-notes.md          │
│     ↓                                                       │
│  AI: Explains "This bug is because XXX, fixed by YYY"       │
│      顺便解释"这个 bug 是因为 XXX，修复原理是 YYY"           │
│     ↓                                                       │
│  Result: Humans learn, can solve independently next time    │
│  结果：人类学到知识，下次可以独立解决                         │
└─────────────────────────────────────────────────────────────┘
```

### Problem 3: Human-AI "Cognitive Misalignment" / 人机"认知错位"

**The Problem / 问题**：

```
┌─────────────────────────────────────────────────────────────┐
│  Traditional: AI thinks it's right, human finds it wrong    │
│  传统模式：AI 以为做对了，人类发现是错的                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  AI: I modified the login page styles                       │
│      我修改了登录页面样式                                    │
│     ↓                                                       │
│  AI: ✅ Done (verified at code level)                       │
│      ✅ 完成（从代码层面验证）                               │
│     ↓                                                       │
│  User: Opens browser, styles are completely wrong!          │
│        打开浏览器发现样式完全不对！                          │
│     ↓                                                       │
│  Result: Rework, wasted time / 结果：返工，浪费时间          │
└─────────────────────────────────────────────────────────────┘
```

**Evolution's Solution / Evolution 的解决方案**：

```
┌─────────────────────────────────────────────────────────────┐
│  Evolution Mode: Maintain Human-AI Alignment                │
│  Evolution 模式：保持人机对齐                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  AI: I modified the login page styles                       │
│      我修改了登录页面样式                                    │
│     ↓                                                       │
│  [Background] Alignment Agent detects GUI changes           │
│  [后台] Alignment Agent 识别到 GUI 修改                      │
│     ↓                                                       │
│  AI: ️ Modified styles, but I can't verify visuals,        │
│      please check in browser                                │
│      ⚠️ 修改了样式，但我无法验证视觉效果，请你检查浏览器      │
│     ↓                                                       │
│  User: Opens browser, confirms, finds issues                │
│        打开浏览器确认，发现有问题                            │
│     ↓                                                       │
│  Result: Catch issues early, avoid rework                   │
│  结果：及时发现，避免返工                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧠 Core Principles / 核心原理

### Principle 1: Index + Detail File Architecture / 索引 + 详情文件架构

```
┌─────────────────────────────────────────────────────────────┐
│              Knowledge Base Architecture                    │
│                        知识库架构                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐                                        │
│  │   kb-index.md   │  ← Auto-loaded at conversation start  │
│  │                 │     AI 对话开始时自动读取（索引）       │
│  │   Overview    │  ← Tells AI what info is available    │
│  │  📁 Summary     │     告诉 AI 有哪些信息可用             │
│  ────────────────┘                                        │
│           │                                                 │
│           ↓ Load on demand / 按需读取                        │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │    facts.md     │  │  pitfalls.md    │  ← Detail files │
│  │                 │  │                 │     详情文件     │
│  │  • Env config   │  │  • Error modes  │                  │
│  │  • Decisions    │  │  • Solutions    │                  │
│  │  • Dependencies │  │  • Notes        │                  │
│  └─────────────────┘  └─────────────────┘                  │
│                                                             │
│  Benefits / 优势：                                           │
│  ✅ Small index (<200 lines), fast loading                  │
│     索引小（<200 行），快速加载                              │
│  ✅ Details loaded on demand, saves tokens                  │
│     详情按需读取，节省 token                                 │
│  ✅ Clear structure, easy to maintain                       │
│     结构清晰，易于维护                                       │
└─────────────────────────────────────────────────────────────┘
```

### Principle 2: Incremental Write + Deduplication / 增量写入 + 去重机制

```
┌─────────────────────────────────────────────────────────────┐
│                 Data Write Strategy                         │
│                    数据写入策略                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  First /evolution / 第一次 /evolution                       │
│     ↓                                                       │
│  facts.md:                                                  │
│  - [10:00] WSL network must use mirrored mode               │
│                                                             │
│  Second /evolution (2 hours later) / 第二次（2 小时后）       │
│     ↓                                                       │
│  facts.md:                                                  │
│  - [10:00] WSL network must use mirrored mode               │
│    ← Update timestamp, no new entry / 更新时间戳，不新增     │
│  - [12:00] Python version must be 3.11                      │
│    ← New entry / 新增条目                                    │
│                                                             │
│  Rules / 规则：                                              │
│  ✅ Same info → Update timestamp / 相同信息 → 更新时间戳     │
│  ✅ New info → Append / 新信息 → 追加写入                   │
│  ✅ Status update → Mark as "Done" / 状态更新 → 标记完成    │
└─────────────────────────────────────────────────────────────┘
```

### Principle 3: Dual System Comparison (A/B Testing) / 双系统对比（A/B 测试）

```
┌─────────────────────────────────────────────────────────────┐
│                  Dual System Design                         │
│                      双系统设计                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  evolution-manual/              evolution-auto/             │
│  ──────────────────┐          ┌──────────────────┐         │
│  │ Manual Trigger   │          │ Auto Trigger     │         │
│  │ 手动触发系统       │          │ 自动触发系统       │         │
│  │                  │          │                  │         │
│  │ Trigger: /evolution│        │ Trigger: Every 5 rounds│   │
│  │ 触发：/evolution  │          │ 触发：每 5 轮      │         │
│  │ Tag: manual      │          │ Tag: auto        │         │
│  │ 标记：manual      │          │ 标记：auto        │         │
│  └──────────────────┘          └──────────────────┘         │
│                                                             │
│  Comparison Dimensions / 对比维度：                          │
│  ──────────────┬──────────────┬──────────────┐            │
│  │ Dimension    │ Manual       │ Auto         │            │
│  │ 维度         │ 手动触发     │ 自动触发     │            │
│  ├──────────────┼──────────────┼──────────────┤            │
│  │ Frequency    │ User decides │ Fixed 5 rnds │            │
│  │ 触发频率     │ 用户决定     │ 固定每 5 轮   │            │
│  │ Quality      │ Selective    │ Fixed logic  │            │
│  │ 提取质量     │ 可选择时机   │ 固定逻辑     │            │
│  │ Completeness │ May miss     │ More systematic│          │
│  │ 信息完整性   │ 可能遗漏     │ 更系统       │            │
│  │ Awareness    │ Aware        │ Unaware      │            │
│  │ 用户感知     │ 有感知       │ 无感知       │            │
│  └──────────────┴──────────────┴──────────────┘            │
│                                                             │
│  Goal: Find optimal solution through comparison             │
│  目标：通过对比找到最优方案                                  │
─────────────────────────────────────────────────────────────┘
```

---

## 🏗️ System Architecture / 系统架构

### Directory Structure / 目录结构

```
evolution-manual/
├── agents/                          # Agent specifications / Agent 规格说明
│   ├── knowledge-base-agent.md      # Knowledge extraction / 知识提取
│   ├── growth-agent.md              # Human growth / 人类成长
│   └── alignment-agent.md           # Human-AI alignment / 人机对齐
│
└── knowledge-base/                  # Knowledge base data / 知识库数据
    ├── kb-index.md                  # Index file (auto-loaded) / 索引文件
    ├── facts.md                     # Key facts / 关键事实
    ├── pitfalls.md                  # Pitfalls / 踩坑记录
    ├── state.md                     # Current state / 当前状态
    ├── growth-notes.md              # Learning notes / 学习笔记
    ├── prompt-improvements.md       # Prompt improvements / Prompt 改进
    ├── alignment.md                 # Alignment checklist / 对齐清单
    └── decisions.md                 # Decision log / 决策记录
```

### File Responsibilities / 文件职责

| File / 文件 | Consumer / 消费者 | Description / 说明 |
|-------------|-------------------|---------------------|
| `kb-index.md` | AI | Index file, tells AI what's available / 索引文件 |
| `facts.md` | AI | Key facts (env config, decisions) / 关键事实 |
| `pitfalls.md` | AI | Pitfalls (error modes, solutions) / 踩坑记录 |
| `state.md` | AI | Current state (progress, pending) / 当前状态 |
| `growth-notes.md` | Human | Learning notes (concept explanations) / 学习笔记 |
| `prompt-improvements.md` | Human | Prompt improvement suggestions / Prompt 改进建议 |
| `alignment.md` | Human+AI | Alignment checklist (pending reviews) / 对齐清单 |
| `decisions.md` | Human+AI | Decision log (pending decisions) / 决策记录 |

---

## 🤖 Three Background Agents / 三个后台 Agent

### 1. Knowledge Base Agent / 知识提取 Agent

```
┌─────────────────────────────────────────────────────────────┐
│              Knowledge Base Agent                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Trigger: Every 5 rounds / 触发频率：每 5 轮对话             │
│                                                             │
│  Input: Last 5 rounds of conversation / 输入：最近 5 轮对话  │
│     ↓                                                       │
│  Processing / 处理：                                         │
│  ├── Extract key facts → facts.md / 提取关键事实             │
│  ├── Extract pitfalls → pitfalls.md / 提取踩坑记录          │
│  ├── Update state → state.md / 更新当前状态                 │
│  └── Update index → kb-index.md / 更新索引                  │
│                                                             │
│  Output: 1-line summary / 输出：1 行摘要                     │
│  `KB: +3 facts, +1 pitfall, +2 state updates`               │
│                                                             │
│  Dedup Rules / 去重规则：                                    │
│  - Same info → Update timestamp / 相同信息 → 更新时间戳      │
│  - New info → Append / 新信息 → 追加写入                    │
└─────────────────────────────────────────────────────────────┘
```

### 2. Growth Agent / 人类成长 Agent

```
┌─────────────────────────────────────────────────────────────┐
│                  Growth Agent                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Trigger: Every 10 rounds / 触发频率：每 10 轮对话           │
│                                                             │
│  Input: Last 10 rounds of conversation / 输入：最近 10 轮    │
│     ↓                                                       │
│  Processing / 处理：                                         │
│  ├── Identify teaching opportunities → growth-notes.md      │
│  │   识别教学机会 → 学习笔记                                 │
│  └── Analyze questioning style → prompt-improvements.md     │
│      分析提问方式 → Prompt 改进建议                          │
│                                                             │
│  Output: 1-line summary / 输出：1 行摘要                     │
│  `Growth: +2 notes, +1 prompt tip`                          │
│                                                             │
│  Teaching Value Assessment / 教学价值评估：                  │
│  🔴 High: User explicitly asks, recurring concepts          │
│     高优先级：用户明确询问、反复出现                          │
│  🟡 Medium: Related but not core / 中优先级：相关但非核心   │
│  🟢 Low: Edge concepts (skip) / 低优先级：边缘概念（跳过）  │
─────────────────────────────────────────────────────────────┘
```

### 3. Alignment Agent / 人机对齐 Agent

```
┌─────────────────────────────────────────────────────────────┐
│                 Alignment Agent                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Trigger: Every 5 rounds + Instant / 每 5 轮 + 即时触发      │
│                                                             │
│  Input: Last 5 rounds of conversation / 输入：最近 5 轮对话  │
│     ↓                                                       │
│  Processing / 处理：                                         │
│  ├── Identify review items → alignment.md                   │
│  │   识别验收项 → 对齐清单                                   │
│  ├── Identify decision points → decisions.md                │
│  │   识别决策点 → 决策记录                                   │
│  └── Flag high-risk operations → Instant alert              │
│      标记高风险操作 → 即时提醒                               │
│                                                             │
│  Output: 1-line summary / 输出：1 行摘要                     │
│  `Alignment: +1 audit, +0 decisions`                        │
│                                                             │
│  Priority Classification / 优先级分类：                      │
│  🔴 High: Security, irreversible (handle immediately)       │
│     高优先级：安全相关、不可逆操作（立即处理）                │
│  🟡 Medium: Feature review, decisions (this round)          │
│     中优先级：功能验收、技术决策（本轮处理）                  │
│  🟢 Low: Optimization suggestions (later)                   │
│     低优先级：优化建议（后续处理）                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Workflow / 工作流程

### Complete Flow / 完整流程图

```
User inputs /evolution / 用户输入 /evolution
    ↓
┌─────────────────────────────────────────────────────────────┐
│  Main Agent (Scheduler) / 主 Agent（调度器）                 │
│                                                             │
│  1. Export full conversation to temp file                   │
│     导出全量对话到临时文件                                   │
│     `.claude/.tmp/conv-export-{timestamp}.md`               │
│                                                             │
│  2. Launch 3 Sub-Agents in parallel / 并行启动 3 个 Sub-Agent│
│     ├── Knowledge Base Sub-Agent                            │
│     ├── Growth Sub-Agent                                    │
│     └── Alignment Sub-Agent                                 │
│                                                             │
│  3. Wait for completion, collect summaries                  │
│     等待完成，收集摘要                                       │
│                                                             │
│  4. Report to user / 向用户报告                              │
└─────────────────────────────────────────────────────────────┘
    ↓
Evolution sync complete / Evolution 同步完成：
- KB: +3 facts, +1 pitfall, +2 state updates
- Growth: +2 notes, +1 prompt tip
- Alignment: +1 audit, +0 decisions
```

### Information Flow / 信息流向图

```
┌─────────────────────────────────────────────────────────────┐
│                    Conversation Process                     │
│                        对话过程                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
              ┌──────────────────────┐
              │  Conversation History│
              │   对话历史记录        │
              │  (Last 5/10 rounds)  │
              │   (最近 5/10 轮)      │
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
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
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
              │   (索引文件)          │
              └──────────┬───────────┘
                         │
                         ↓
              ┌──────────────────────┐
              │  AI reads index on   │
              │  next conversation   │
              │  AI 下次对话时        │
              │  自动读取索引         │
              └──────────────────────┘
```

---

##  Quick Start / 快速开始

### 1. Installation / 安装

Copy `evolution-manual/` and `.claude/` directories to your project root:

将 `evolution-manual/` 和 `.claude/` 目录复制到你的项目根目录：

```bash
# Copy to your project / 复制到你的项目
cp -r evolution-manual/ <your-project>/
cp -r .claude/ <your-project>/
cp CLAUDE.md <your-project>/
```

### 2. Usage / 使用

Open Claude Code in your project, then:

在你的项目中打开 Claude Code，然后：

```bash
/evolution          # Execute all three Agents / 执行所有三个 Agent
/kb-sync            # Sync knowledge base only / 只同步知识库
/growth-sync        # Generate learning notes only / 只生成学习笔记
/alignment-sync     # Check alignment only / 只检查对齐项
```

### 3. View Results / 查看结果

After Agent execution, check `evolution-manual/knowledge-base/` directory:

Agent 执行后，查看 `evolution-manual/knowledge-base/` 目录：

- `kb-index.md` - Index file / 索引文件
- `facts.md` - Key facts / 关键事实
- `pitfalls.md` - Pitfalls / 踩坑记录
- `state.md` - Current state / 当前状态
- `growth-notes.md` - Learning notes / 学习笔记
- `alignment.md` - Alignment checklist / 对齐清单
- `decisions.md` - Decision log / 决策记录

---

##  Design Philosophy / 设计理念

> **Don't create artificial friction. The primary goal is to complete the task perfectly, then naturally do the meaningful things.**
>
> **不要人为制造摩擦。首要目标是把任务完美完成，然后自然而然地把有意义的事情做了。**

Evolution is not an additional burden, but a natural byproduct of task execution.

Evolution 不是额外的负担，而是任务执行过程中的自然副产品。

### Core Principles / 核心原则

| Principle / 原则 | Description / 说明 |
|------------------|---------------------|
| **Task First** / **任务优先** | Primary goal is task completion, not running the system / 首要目标是完成任务，不是运行系统 |
| **Natural Occurrence** / **自然发生** | Learning and sedimentation happen naturally during task execution / 学习和沉淀在任务执行中自然发生 |
| **Human Unaware** / **人类无感** | Run in background, don't interfere with main conversation / 后台运行，不干扰主对话 |
| **Gradual Growth** / **渐进成长** | Both AI and human grow through collaboration / AI 和人类都在协作中成长 |

---

## 🤝 Contributing / 贡献

Contributions are welcome! Submit Issues and Pull Requests!

欢迎提交 Issue 和 Pull Request！

### Contribution Areas / 贡献方向

- 🐛 **Bug Fixes** / **Bug 修复**
- ✨ **New Features** / **新功能**
- 📚 **Documentation Improvements** / **文档改进**
- 💡 **Use Case Sharing** / **使用案例分享**

---

## 📄 License / 许可证

MIT License - See [LICENSE](LICENSE) for details

MIT 许可证 - 详见 [LICENSE](LICENSE)

---

## 👤 Author / 作者

**lemen**

- Project Inspiration: Real pain points in human-AI collaboration / 项目灵感：人机协作中的真实痛点
- Design Philosophy: Growing together through collaboration / 设计哲学：让 AI 和人类在协作中共同成长

---

## 🌟 Star History

If this project helps you, please give us a ⭐ Star!

如果这个项目对你有帮助，请给我们一个 ⭐ Star！

---

<p align="center">
  <strong>Making Human-AI Collaboration More Valuable</strong><br/>
  <strong>让人机协作更有价值</strong>
</p>