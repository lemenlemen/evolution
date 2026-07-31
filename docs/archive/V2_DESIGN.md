# Evolution V3 - 系统简化设计文档

> **版本**：3.1.0（2026-07-29）  
> **状态**：设计完成，已实施  
> **基于**：V2 版本的经验教训和简化需求

> **版本历史**：详见 [`VERSION_HISTORY.md`](./VERSION_HISTORY.md)

---

## 1. 重构背景

### 1.1 V1 版本的问题

| 问题 | 说明 | 影响 |
|------|------|------|
| **使用 Slash Command** | 只在用户输入时加载 | AI 不知道知识库存在，无法主动参考 |
| **全量读取指令** | 命令指示 AI 读取整个目录 | 上下文消耗大，扩展性差 |
| **无法自我进化** | AI 不能主动参考历史知识 | 违背"自我进化"设计目标 |
| **路径硬编码** | 命令文件写死项目路径 | 不可移植 |

### 1.2 核心发现

通过官方文档研究，发现 Claude Code 的 **Skill 系统支持渐进式披露**：

```
启动时：加载 frontmatter 描述（~1 行）
    ↓
每轮对话：AI 看到描述，判断是否需要
    ↓
按需加载：完整内容只在需要时加载
```

这正是 Evolution 需要的机制！

---

## 2. V2 架构设计

### 2.1 核心变更

| 组件 | V1 | V2 |
|------|-----|-----|
| **触发机制** | Slash Command | Skill（带 frontmatter） |
| **加载方式** | 手动触发时全量加载 | 渐进式披露 |
| **AI 感知** | 不知道知识库存在 | 知道（通过描述） |
| **自动触发** | 不支持 | 支持（AI 自主判断） |
| **读取策略** | 全量读取目录 | 先读索引，按需读取详情 |

### 2.2 目录结构

```
<project-root>\
├── .claude/
│   └── skills/
│       └── evolution/
│           └── SKILL.md              # V2 Skill 定义（带 frontmatter）
│
├── evolution-manual/                  # 保持不变（知识库模板）
│   ── knowledge-base/
│       ├── kb-index.md
│       ├── facts.md
│       └── ...
│
└── docs/                              # 设计文档（新增）
    ├── V1_REVIEW.md                   # V1 版本回顾
    ├── SKILL_LOADING_MECHANISM.md     # Skill 加载机制研究
    └── V2_DESIGN.md                   # 本文档
```

---

## 3. Skill 定义设计

### 3.1 Frontmatter 设计

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
context: fork
---
```

**关键配置说明**：

| 字段 | 值 | 说明 |
|------|-----|------|
| `disable-model-invocation` | `false` | 允许 AI 自动触发（实现自我进化） |
| `context` | `fork` | 在隔离的 sub-agent 中执行（可选） |

---

### 3.2 SKILL.md 正文设计

```markdown
# Evolution System

## 知识库位置
`evolution-manual/knowledge-base/`

## 渐进式读取规则

**重要**：不要一次性读取所有文件！遵循渐进式披露原则。

### 步骤 1：读取索引
读取 `evolution-manual/knowledge-base/kb-index.md`

### 步骤 2：判断需求
基于索引中的分类摘要，判断当前任务需要哪些信息：
- 如果用户问环境配置 → 读取 facts.md
- 如果用户问历史错误 → 读取 pitfalls.md
- 如果需要更新状态 → 读取 state.md
- 如果用户问学习知识 → 读取 growth-notes.md

### 步骤 3：按需读取
只读取相关的 1-2 个文件，不要全量加载

### 步骤 4：执行任务
基于读取的信息执行知识提取或回答问题

## 执行命令

### 手动触发
- `/evolution` - 执行完整同步
- `/kb-sync` - 只同步知识库
- `/growth-sync` - 只生成学习笔记
- `/alignment-sync` - 只检查对齐项

### 自动触发
AI 根据 `when_to_use` 描述自主判断是否需要触发

## 去重策略

1. 基于 kb-index.md 的摘要判断是否可能重复
2. 如果不确定，读取对应详情文件精确去重
3. 相同信息更新时间戳，新信息追加
```

---

## 4. 渐进式披露流程

### 4.1 完整流程

```
启动时：
  ↓
加载 SKILL.md frontmatter（~20 tokens）
"Evolution: 人机共生进化系统，管理项目知识库"
    ↓
每轮对话：
  ↓
AI 看到 evolution 的描述
    ↓
判断："用户问的是技术问题，可能需要参考知识库"
    ↓
加载完整 SKILL.md 内容（~100 行）
    ↓
执行步骤 1：读取 kb-index.md（~150 行）
    ↓
基于索引判断："WSL 配置在 facts.md 中"
    ↓
执行步骤 2：只读取 facts.md（~60 行）
    ↓
执行步骤 3：回答问题或执行同步
    ↓
总计：~320 行（而非全量 1000+ 行）✅
```

### 4.2 上下文消耗对比

| 阶段 | V1（全量） | V2（渐进式） |
|------|-----------|------------|
| **启动时** | 0 tokens | ~20 tokens |
| **触发时** | ~1000 tokens | ~320 tokens |
| **总消耗** | ~1000 tokens | ~340 tokens |
| **节省** | - | **~66%** |

---

## 5. 安装位置设计

### 5.1 项目级安装（推荐）

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

### 5.2 全局安装（可选）

**位置**：`~/.claude/skills/evolution/`

**挑战**：
- 需要动态路径（当前项目）
- 知识库路径需要适配

**不推荐原因**：
- 路径复杂
- 难以调试
- 项目间可能冲突

---

## 6. 实施路线图

### Phase 1：创建 Skill（30 分钟）

| 任务 | 说明 |
|------|------|
| 创建 `.claude/skills/evolution/SKILL.md` | 带 frontmatter |
| 编写渐进式读取规则 | 明确指令 |
| 测试 Skill 加载 | 验证 frontmatter 加载 |

### Phase 2：优化读取策略（30 分钟）

| 任务 | 说明 |
|------|------|
| 增强 kb-index.md | 添加分类摘要 |
| 测试按需读取 | 验证只读相关文件 |
| 测量上下文消耗 | 确认节省 66% |

### Phase 3：保留向后兼容（15 分钟）

| 任务 | 说明 |
|------|------|
| 保留 `.claude/commands/` | 向后兼容 |
| 命令文件指向 Skill | 简化内容 |
| 测试手动触发 | 验证 `/evolution` 正常 |

### Phase 4：测试自动触发（30 分钟）

| 任务 | 说明 |
|------|------|
| 日常对话测试 | 验证 AI 主动参考 |
| 调整 when_to_use | 优化触发条件 |
| 记录测试结果 | 文档化 |

**总计**：1.75 小时

---

## 7. 验收标准

### 7.1 功能验收

| 功能 | 验收标准 |
|------|---------|
| **Skill 加载** | 启动时只加载 frontmatter（~20 tokens） |
| **渐进式披露** | 完整内容按需加载 |
| **按需读取** | AI 基于索引判断，不读全部 |
| **自动触发** | AI 能在日常对话中主动参考 |
| **手动触发** | `/evolution` 命令正常工作 |
| **向后兼容** | 保留的 Slash Command 仍可用 |

### 7.2 性能验收

| 指标 | V1 | V2 目标 |
|------|-----|--------|
| **启动消耗** | 0 tokens | < 50 tokens |
| **触发消耗** | ~1000 tokens | < 400 tokens |
| **节省比例** | - | > 60% |

### 7.3 用户体验验收

| 场景 | 验收标准 |
|------|---------|
| **新用户** | 能快速理解并使用 |
| **日常使用** | AI 能主动参考历史知识 |
| **知识增长** | 支持 1000+ 条目 |

---

## 8. 风险与缓解

### 8.1 技术风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| **Skill 不被识别** | 功能失效 | 低 | 遵循官方 frontmatter 规范 |
| **AI 误判触发** | 不必要的加载 | 中 | 优化 `when_to_use` 描述 |
| **全量读取问题** | 性能差 | 中 | 明确指令"先读索引" |
| **disable-model-invocation bug** | Skill 完全隐藏 | 低 | 使用 `false`（已知 bug 是 `true`） |

### 8.2 用户体验风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| **AI 过度参考** | 响应慢 | 低 | 设置触发阈值 |
| **知识库过时** | 误导 AI | 中 | 定期清理机制 |

---

## 9. 测试计划

### 9.1 测试用例

| 测试 | 步骤 | 预期结果 |
|------|------|---------|
| **T1: Skill 加载** | `/context` | 显示 `evolution: < 20 tokens` |
| **T2: 手动触发** | `/evolution` | 正常执行同步 |
| **T3: 渐进式读取** | 观察 AI 行为 | 先读索引，按需读取 |
| **T4: 自动触发** | 日常对话 | AI 主动参考知识库 |
| **T5: 上下文消耗** | `/context` | 总消耗 < 400 tokens |

### 9.2 测试环境

- **项目**：`<project-root>\`（当前项目）
- **模型**：Claude model
- **上下文窗口**：1M tokens

---

## 10. 参考资料

### 10.1 官方文档

- [Extend Claude with skills](https://code.claude.com/docs/en/skills)
- [How Claude remembers your project](https://code.claude.com/docs/en/memory)
- [Commands](https://code.claude.com/docs/en/commands)

### 10.2 社区文章

- [Claude Agent Skills: A First Principles Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/)
- [Claude Skills Solve the Context Window Problem](https://tylerfolkman.substack.com/p/the-complete-guide-to-claude-skills)

---

## 11. 附录

### 11.1 术语表

| 术语 | 说明 |
|------|------|
| **Skill** | Claude Code 的技能系统，支持渐进式披露 |
| **Frontmatter** | Skill 文件头部的 YAML 元数据 |
| **Progressive Disclosure** | 渐进式披露，按需加载内容 |
| **Slash Command** | 传统的斜杠命令（V1 使用） |

### 11.2 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2026-07-21 | 初始版本（Slash Command） |
| 2.0 | 2026-07-28 | 重构为 Skill 系统（渐进式披露） |

---

**文档结束**
