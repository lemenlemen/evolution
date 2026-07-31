# Claude Code Skill 加载机制研究

> **创建日期**：2026-07-28  
> **来源**：官方文档 + 社区文章  
> **目的**：为 V2 重构提供技术依据

---

## 1. 官方文档核心内容

### 1.1 Skill 的层级结构

| 层级 | 位置 | 范围 |
|------|------|------|
| **全局/个人** | `~/.claude/skills/` | 所有项目可用 |
| **项目级** | `.claude/skills/` | 仅该项目 |
| **企业级** | 管理员部署 | 组织范围 |

**优先级**：企业 > 个人 > 项目

### 1.2 Skill 的结构

```
skill-folder/
└── SKILL.md
    ├── YAML frontmatter
    ── Markdown body
```

### 1.3 Frontmatter 字段

```yaml
---
name: my-skill
description: 一句话描述
when_to_use: |
  - 触发条件 1
  - 触发条件 2
disable-model-invocation: false
context: fork
---
```

| 字段 | 说明 | 必填 |
|------|------|------|
| `name` | Skill 名称（用于 `/name` 触发） | ✅ |
| `description` | 一句话描述（启动时加载） | ✅ |
| `when_to_use` | 触发条件列表 |  推荐 |
| `disable-model-invocation` | 是否禁用自动触发 | ❌ 默认 false |
| `context` | 执行上下文（`fork` = 隔离） | ❌ 可选 |

---

## 2. 加载机制详解

### 2.1 渐进式披露流程

```
Phase 1（启动时）：
  扫描所有 Skill 目录
  加载每个 Skill 的 frontmatter
  特别是 description 字段（~1 行）
  上下文成本：每个 Skill ~20 tokens
  
Phase 2（每轮对话）：
  AI 看到所有 Skill 的描述列表
  根据当前任务上下文判断
  "这个 Skill 与当前任务相关吗？"
  
Phase 3（按需加载）：
  如果判断需要 → 加载完整 SKILL.md
  如果不需要 → 保持 unloaded
  完整内容只在触发时注入
```

### 2.2 关键特性

| 特性 | 说明 |
|------|------|
| **懒加载** | 完整内容只在需要时加载 |
| **Token 预算** | 每个 Skill 的描述有字符上限 |
| **Live Reload** | 修改 Skill 文件后自动检测 |
| **Symlink 支持** | 可以链接到其他位置 |

---

## 3. 两种触发方式对比

### 3.1 自动触发（Claude-Triggered）

**Frontmatter**：
```yaml
disable-model-invocation: false
```

**行为**：
- 启动时：加载描述
- 对话中：AI 自主判断是否需要
- 触发时：加载完整内容

**适用场景**：
- AI 应该主动参考的知识库
- 需要根据上下文触发的功能

---

### 3.2 手动触发（User-Only）

**Frontmatter**：
```yaml
disable-model-invocation: true
```

**行为**：
- 启动时：加载描述（⚠️ 可能有 bug 会完全隐藏）
- 对话中：AI 不会自动触发
- 触发时：只有用户输入 `/name` 才加载

**适用场景**：
- 不希望 AI 误触发的功能
- 纯用户命令

---

### 3.3 对比表

| 特性 | 自动触发 | 手动触发 |
|------|---------|---------|
| **启动时加载** | ✅ 描述 | ✅ 描述（⚠️ 可能不加载） |
| **AI 能看到** | ✅ 是 | ✅ 是（通常） |
| **AI 可以触发** | ✅ 是 | ❌ 否 |
| **用户可以触发** | ✅ 是（`/name`） | ✅ 是（`/name`） |
| **已知 Bug** | 无 | `true` 可能完全隐藏 |

---

## 4. 与 Slash Command 的对比

### 4.1 Slash Command（传统方式）

**位置**：`.claude/commands/name.md`

**加载机制**：
```
启动时：不加载任何内容
    ↓
用户输入 /name
    ↓
完整内容注入到对话
    ↓
AI 执行指令
```

**特点**：
- ✅ 零上下文成本（直到使用）
- ❌ AI 不知道它的存在
-  无法自动触发

---

### 4.2 Skill（现代方式）

**位置**：`.claude/skills/name/SKILL.md`

**加载机制**：
```
启动时：加载 frontmatter 描述（~1 行）
    ↓
每轮对话：AI 看到描述，判断是否需要
    ↓
按需加载：完整内容只在需要时
    ↓
AI 执行指令
```

**特点**：
- ✅ AI 知道它的存在
- ✅ 可以自动触发
- ✅ 渐进式披露
- ⚠️ 启动时有小成本（~20 tokens）

---

### 4.3 对比表

| 特性 | Slash Command | Skill |
|------|--------------|-------|
| **位置** | `.claude/commands/` | `.claude/skills/` |
| **文件格式** | 纯 Markdown | YAML frontmatter + Markdown |
| **启动时加载** | ❌ 不加载 | ✅ 加载描述 |
| **AI 是否知道** | ❌ 不知道 | ✅ 知道 |
| **自动触发** | ❌ 不支持 | ✅ 支持 |
| **手动触发** | ✅ `/name` | ✅ `/name` |
| **上下文成本** | 0（直到使用） | 极小（描述） |
| **完整加载** | 用户触发时 | AI 判断需要时 |

---

## 5. 已知问题和 Bug

### 5.1 disable-model-invocation: true 的 Bug

**问题**：设置为 `true` 可能会让 Skill 完全从会话中隐藏

**影响**：
- AI 看不到描述
- 用户手动触发也可能失败

**来源**：[GitHub Issue #43875](https://github.com/anthropics/claude-code/issues/43875)

**建议**：
- 暂时使用 `false`
- 通过 `when_to_use` 控制触发条件

---

### 5.2 项目级 Skill 不被发现

**问题**：某些情况下项目级 Skill 不被发现

**来源**：[GitHub Issue #33733](https://github.com/anthropics/claude-code/issues/33733)

**建议**：
- 确保目录结构正确
- 确保 SKILL.md 有正确的 frontmatter

---

## 6. 最佳实践

### 6.1 Frontmatter 设计

```yaml
---
name: evolution
description: 人机共生进化系统，管理项目知识库。当需要参考项目历史知识、避免重复错误、或执行知识同步时触发。
when_to_use: |
  - 用户询问环境配置、技术决策等历史知识
  - 检测到重复错误或相似问题
  - 需要执行知识同步（每 5 轮对话）
  - 用户手动输入 /evolution
disable-model-invocation: false
---
```

**要点**：
- `description` 要清晰说明用途
- `when_to_use` 要具体列出触发条件
- `disable-model-invocation` 推荐 `false`

---

### 6.2 渐进式读取指令

```markdown
## 知识库读取规则

**重要**：不要一次性读取所有文件！遵循渐进式披露原则。

### 步骤 1：读取索引
读取 `evolution-manual/knowledge-base/kb-index.md`

### 步骤 2：判断需求
基于索引中的分类摘要，判断需要哪些信息

### 步骤 3：按需读取
只读取相关的 1-2 个文件

### 步骤 4：执行任务
基于读取的信息执行操作
```

---

### 6.3 安装位置选择

| 场景 | 推荐位置 | 理由 |
|------|---------|------|
| **项目特定** | `.claude/skills/` | 路径简单，可版本控制 |
| **个人通用** | `~/.claude/skills/` | 所有项目可用 |
| **团队共享** | Git 仓库 + symlink | 团队统一 |

---

## 7. 对 Evolution V2 的启示

### 7.1 核心决策

1. **使用 Skill 系统**（而非 Slash Command）
2. **项目级安装**（`.claude/skills/evolution/`）
3. **允许自动触发**（`disable-model-invocation: false`）
4. **渐进式读取**（明确指令"先读索引"）

### 7.2 预期收益

| 指标 | V1（Slash Command） | V2（Skill） | 改进 |
|------|---------------------|-------------|------|
| **启动消耗** | 0 | ~20 tokens | AI 知道了 |
| **触发消耗** | ~1000 tokens | ~320 tokens | **-68%** |
| **自动触发** | ❌ | ✅ | 质的飞跃 |
| **自我进化** | ❌ | ✅ | 核心目标达成 |

---

## 8. 参考资料

### 8.1 官方文档

- [Extend Claude with skills](https://code.claude.com/docs/en/skills)
- [Explore the .claude directory](https://code.claude.com/docs/en/claude-directory)
- [Commands](https://code.claude.com/docs/en/commands)

### 8.2 社区文章

- [Claude Agent Skills: A First Principles Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/)
- [Claude Skills Solve the Context Window Problem](https://tylerfolkman.substack.com/p/the-complete-guide-to-claude-skills)
- [Inside Claude Code Skills](https://mikhail.io/2025/10/claude-code-skills/)

### 8.3 GitHub Issues

- [disable-model-invocation: true hides skill](https://github.com/anthropics/claude-code/issues/43875)
- [Project-level skills not discovered](https://github.com/anthropics/claude-code/issues/33733)

---

**文档结束**
