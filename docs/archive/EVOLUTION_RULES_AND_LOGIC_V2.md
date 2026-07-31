# Evolution V3 - 系统规则与运行逻辑

> **版本**：3.1.0（2026-07-29）  
> **基于**：V2 版本经验 + 简化需求

> **版本历史**：详见 [`VERSION_HISTORY.md`](./VERSION_HISTORY.md)

---

## 1. 系统概述

### 1.1 核心定位

**Evolution 是一个 Skill**，而非简单的 Slash Command。

| 特性 | Slash Command（V1） | Skill（V2） |
|------|---------------------|-----------|
| **触发方式** | 仅手动 (`/evolution`) | 自动（Claude 判断）或手动 |
| **启动时加载** | ❌ 完全不加载 | ✅ 加载一行描述 |
| **AI 是否知道** | ❌ 不知道 | ✅ 知道（通过描述） |
| **上下文成本** | 0（直到使用） | 极小（一行描述） |
| **日常参考** | ❌ 无法主动参考 | ✅ 可以主动参考 |

### 1.2 核心目标

| 目标 | 说明 | 优先级 |
|------|------|--------|
| **让 AI 更可靠** | 记住关键信息，避免重复错误 | P0 |
| **让人类成长** | 生成学习笔记，提升协作效率 | P1 |
| **保持人机对齐** | 标记验收项，减少误解 | P1 |

---

## 1.3 双向功能

**Evolution 是一个双向同步系统**：

| 功能 | 说明 |
|------|------|
| **📖 读取** | 让 AI 知道"已经知道什么" |
| **️ 写入** | 让 AI 记录"新学到什么" |

### 读取功能（Read）

**读取什么**：
- `kb-index.md` - 了解知识库概览
- `facts.md` - 环境配置、技术决策、依赖关系
- `pitfalls.md` - 错误模式、解决方案
- `state.md` - 当前任务进度
- `growth-notes.md` - 学习笔记
- `alignment.md` - 待验收项
- `decisions.md` - 决策记录

**什么时候读**：
- 日常对话中，用户问到历史知识时
- AI 需要参考过去的经验时
- 执行 `/evolution` 同步前，先读索引

### 写入功能（Write）

**写入什么**：
- 新的事实（如新的环境配置）
- 新的踩坑记录（如新发现的错误和解决方案）
- 更新状态（任务进度、待确认项）
- 更新索引（条目数、最后更新时间）
- 学习笔记（如果是 Growth Agent）

**什么时候写**：
- 执行 `/evolution` 同步时
- 对话中检测到新知识点时
- 每 5 轮自动触发时（未来）

### 完整同步流程

```
用户输入 /evolution
    ↓
📖 读取阶段：
  1. 读取 kb-index.md（索引）
  2. 基于索引判断需要哪些文件
  3. 读取相关的详情文件（facts.md 等）
    ↓
✍️ 写入阶段：
  1. 提取对话中的新知识
  2. 与已有知识去重
  3. 追加/更新到对应文件
  4. 更新索引（kb-index.md）
    ↓
报告摘要
```

---

## 2. 架构设计

### 2.1 目录结构

```
<project>/
├── .claude/
│   └── skills/
│       └── evolution/
│           └── SKILL.md              # V2 Skill 定义（带 frontmatter）
│
├── evolution-manual/                  # 手动触发版本
│   └── knowledge-base/
│       ├── kb-index.md               # 索引文件（<200 行）
│       ├── facts.md                  # 关键事实
│       ├── pitfalls.md               # 踩坑记录
│       ├── state.md                  # 当前状态
│       ├── growth-notes.md           # 学习笔记
│       ├── prompt-improvements.md    # Prompt 改进
│       ├── alignment.md              # 对齐清单
│       └── decisions.md              # 决策记录
│
└── evolution-auto/                    # 自动触发版本（未来）
    └── knowledge-base/
```

### 2.2 Skill 定义（Frontmatter）

```yaml
---
name: evolution
description: 人机共生进化系统，管理项目知识库
when_to_use: |
  - 用户询问环境配置、技术决策等历史知识
  - 检测到重复错误或相似问题
  - 需要执行知识同步
  - 用户手动输入 /evolution
disable-model-invocation: false
---
```

**关键字段说明**：

| 字段 | 值 | 说明 |
|------|-----|------|
| `name` | `evolution` | Skill 名称（用于 `/evolution` 触发） |
| `description` | 一行描述 | 启动时加载，让 AI 知道 Skill 存在 |
| `when_to_use` | 触发条件列表 | 帮助 AI 判断何时自动触发 |
| `disable-model-invocation` | `false` | 允许自动触发（实现自我进化） |

---

## 3. 加载机制：渐进式披露

### 3.1 什么是渐进式披露？

**核心原则**：
> "Your skill.md should describe what to do, not contain all the material needed to do it."
> 
> （你的 skill.md 应该描述做什么，而不是包含做这件事所需的所有材料。）

**机制**：
1. **Phase 1（启动时）**：只加载 frontmatter（一行描述）
2. **Phase 2（每轮对话）**：Claude 看到所有 skill 的描述列表
3. **Phase 3（按需加载）**：Claude 判断是否需要加载完整 skill 内容
4. **Phase 4（执行时）**：加载完整指令，但数据文件仍按需读取

### 3.2 Evolution 的渐进式披露流程

```
启动时：
  ↓
加载 frontmatter:
  name: evolution
  description: 人机共生进化系统，管理项目知识库
  上下文成本：~20 tokens
    ↓
日常对话（每轮）：
  ↓
Claude 看到 evolution 的描述
  ↓
判断："用户问的是技术问题，可能需要参考知识库"
    ↓
Phase 2: 读取完整 SKILL.md（~100 行）
  ↓
执行指令：读取 kb-index.md（索引）
    ↓
基于索引判断："WSL 配置在 facts.md 中"
    ↓
Phase 3: 只读取 facts.md（~60 行）
    ↓
回答问题
    ↓
总计：~180 行（而非全量 1000+ 行）✅
```

### 3.3 上下文消耗对比

| 阶段 | V1（Slash Command） | V2（Skill） |
|------|---------------------|-----------|
| **启动时** | 0 tokens | ~20 tokens |
| **触发时** | ~1000 tokens（全量） | ~320 tokens（按需） |
| **总消耗** | ~1000 tokens | ~340 tokens |
| **节省** | - | **~66%** |

---

## 4. 触发机制

### 4.1 手动触发

**触发方式**：用户输入 slash command

| 命令 | 功能 | 触发频率 |
|------|------|---------|
| `/evolution` | 执行所有 Agent | 用户决定 |
| `/kb-sync` | 只执行 Knowledge Base Agent | 用户决定 |
| `/growth-sync` | 只执行 Growth Agent | 用户决定 |
| `/alignment-sync` | 只执行 Alignment Agent | 用户决定 |

**执行流程**：
```
用户输入 /evolution
    ↓
Claude Code 加载 SKILL.md 完整内容
    ↓
AI 接收指令（包含路径和任务说明）
    ↓
AI 先读取 kb-index.md（索引）
    ↓
基于索引判断需要哪些详情文件
    ↓
按需读取 1-2 个详情文件
    ↓
执行提取、去重、更新操作
    ↓
AI 向用户报告摘要
```

### 4.2 自动触发

**触发方式**：AI 根据 `when_to_use` 描述自主判断

**触发条件**：
- 用户询问环境配置、技术决策等历史知识
- 检测到重复错误或相似问题
- 需要执行知识同步（每 5 轮对话）

**优势**：
- ✅ AI 知道知识库存在
- ✅ 可以主动参考历史知识
- ✅ 实现真正的"自我进化"

---

## 5. 读取策略

### 5.1 渐进式读取规则

**重要**：不要一次性读取所有文件！遵循渐进式披露原则。

#### 步骤 1：读取索引

读取 `evolution-manual/knowledge-base/kb-index.md`

#### 步骤 2：判断需求

基于索引中的分类摘要，判断当前任务需要哪些信息：

- 如果用户问环境配置 → 读取 `facts.md`
- 如果用户问历史错误 → 读取 `pitfalls.md`
- 如果需要更新状态 → 读取 `state.md`
- 如果用户问学习知识 → 读取 `growth-notes.md`
- 如果需要验收检查 → 读取 `alignment.md`
- 如果需要决策记录 → 读取 `decisions.md`

#### 步骤 3：按需读取

**只读取相关的 1-2 个文件**，不要全量加载

#### 步骤 4：执行任务

基于读取的信息执行知识提取或回答问题

### 5.2 错误行为 vs 正确行为

#### ❌ 错误行为（全量读取）

```
AI: 让我读取所有知识库文件...
    [读取 kb-index.md]
    [读取 facts.md]
    [读取 pitfalls.md]
    [读取 state.md]
    [读取 growth-notes.md]
    [读取 prompt-improvements.md]
    [读取 alignment.md]
    [读取 decisions.md]
AI: 完成！消耗了 ~1000 行上下文
```

#### ✅ 正确行为（渐进式读取）

```
AI: 我先读取 kb-index.md 了解知识库概览...
    [读取 kb-index.md]
AI: 基于索引，我需要读取 facts.md...
    [只读取 facts.md]
AI: 完成！只消耗了 ~200 行上下文
```

---

## 6. 安装位置

### 6.1 项目级安装（推荐）

**位置**：`.claude/skills/evolution/`

**理由**：
- 知识库是项目级的
- 路径简单（相对路径）
- 可以提交到版本控制
- 项目隔离

**结构**：
```
<project>/.claude/skills/evolution/SKILL.md
<project>/evolution-manual/knowledge-base/
```

### 6.2 全局安装（可选）

**位置**：`~/.claude/skills/evolution/`

**挑战**：
- 需要动态路径（当前项目）
- 知识库路径需要适配

**不推荐原因**：
- 路径复杂
- 难以调试
- 项目间可能冲突

---

## 7. 去重机制

### 7.1 去重策略

1. **基于索引判断**
   - 读取 `kb-index.md` 的摘要
   - 判断新信息是否可能重复

2. **精确去重**
   - 如果不确定，读取对应详情文件
   - 比较内容是否相同

3. **更新策略**
   - 相同信息 → 更新时间戳
   - 新信息 → 追加写入
   - 状态更新 → 标记为"已完成"

### 7.2 示例

```markdown
# facts.md

## 环境配置
- [2026-07-28 10:00] WSL 网络配置（镜像模式）  ← 更新时间戳
- [2026-07-28 11:00] Python 版本要求（3.11）   ← 新条目
```

---

## 8. 核心原则

### 8.1 与 Auto Memory 分离

**Evolution 的知识库必须存储在 `evolution-manual/knowledge-base/`，绝对不能使用 `~/.claude/projects/<project>/memory/`！**

**原因**：
- Claude Code 会在每次会话启动时**自动加载** `~/.claude/projects/<project>/memory/` 目录
- 如果 Evolution 的知识库放在那里，会**污染** Claude Code 的 Auto Memory 系统
- 这违反了 Evolution "与 Auto Memory 完全独立"的核心设计原则

### 8.2 项目级存储

知识库存储在 `evolution-manual/knowledge-base/`，每个项目独立。

### 8.3 按需加载

通过索引引导 AI 按需读取，避免上下文污染。

### 8.4 渐进成长

AI 和人类都在协作中成长。

---

## 9. 常见问题

### Q1: Evolution 是否必须依赖 CLAUDE.md？

**A**: 
- **手动触发模式**：不必须（Skill 文件包含路径）
- **自动触发模式**：必须（AI 需要知道任务）
- **建议**：即使是手动触发，也建议在 CLAUDE.md 中说明，以便 AI 在日常对话中参考知识库

### Q2: kb-index.md 和 MEMORY.md 有什么区别？

**A**:

| 文件 | 位置 | 自动加载？ | 用途 |
|------|------|-----------|------|
| `MEMORY.md` | `~/.claude/projects/<project>/memory/` | ✅ 是 | Claude Code 内部记忆 |
| `kb-index.md` | `evolution-manual/knowledge-base/` | ❌ 否 | Evolution 系统索引 |

**关系**：两者应该**完全独立**，不应混用。

### Q3: 为什么不用 Claude Code 的 Auto Memory？

**A**: 
- Auto Memory 会**污染** Claude Code 的内部记忆系统
- Evolution 需要**独立控制**知识库的结构和更新逻辑
- 违反"与 Auto Memory 完全分离"的核心设计原则

### Q4: Auto 版本一定要用 Hook 吗？

**A**: 不一定。

- **Hook**：适合精确控制触发时机（如每 5 轮）
- **AI 自主**：适合灵活触发（如检测到重复错误时）
- **混合模式**：Hook 触发 + AI 自主判断是否执行

**推荐**：先实现 AI 自主模式（在 SKILL.md 的 `when_to_use` 中写规则），验证效果后再考虑 Hook。

---

## 10. 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2026-07-21 | 初始版本（Slash Command） |
| 2.0 | 2026-07-28 | 重构为 Skill 系统（渐进式披露） |

---

**文档结束**
