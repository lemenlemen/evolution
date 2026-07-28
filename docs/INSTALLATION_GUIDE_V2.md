# Evolution V3 - 安装指南

> **版本**：3.0.0（2026-07-28）  
> **适用平台**：Windows / macOS / Linux

> **版本历史**：详见 [`VERSION_HISTORY.md`](./VERSION_HISTORY.md)

---

## 1. 前置条件

### 1.1 系统要求

| 项目 | 要求 |
|------|------|
| **Claude Code** | 最新版本（支持 Skill 系统） |
| **操作系统** | Windows 10+ / macOS 10.15+ / Ubuntu 18.04+ |
| **Shell** | Git Bash / Zsh / Bash |

### 1.2 验证 Claude Code 版本

```bash
claude --version
```

**预期输出**：
```
claude version 2.1.x 或更高
```

---

## 2. 安装步骤

### 2.1 创建 Skill 目录

```bash
# 进入项目根目录
cd <your-project>

# 创建 Skill 目录
mkdir -p .claude/skills/evolution
```

### 2.2 创建 SKILL.md

在 `.claude/skills/evolution/` 目录下创建 `SKILL.md` 文件：

```bash
cat > .claude/skills/evolution/SKILL.md << 'EOF'
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

# Evolution System

人机共生进化系统，让 AI 和人类在协作中共同成长。

## 知识库位置

`evolution/knowledge-base/`

## 渐进式读取规则

**重要**：不要一次性读取所有文件！遵循渐进式披露原则。

### 步骤 1：读取索引

读取 `evolution/knowledge-base/kb-index.md`

### 步骤 2：判断需求

基于索引中的分类摘要，判断当前任务需要哪些信息：

- 如果用户问环境配置 → 读取 `facts.md`
- 如果用户问历史错误 → 读取 `pitfalls.md`
- 如果需要更新状态 → 读取 `state.md`
- 如果用户问学习知识 → 读取 `growth-notes.md`
- 如果需要验收检查 → 读取 `alignment.md`
- 如果需要决策记录 → 读取 `decisions.md`

### 步骤 3：按需读取

**只读取相关的 1-2 个文件**，不要全量加载所有文件

### 步骤 4：执行任务

基于读取的信息执行知识提取、回答问题或执行同步

## 执行命令

### 手动触发

- `/evolution` - 执行完整同步（所有 Agent）
- `/kb-sync` - 只同步知识库
- `/growth-sync` - 只生成学习笔记
- `/alignment-sync` - 只检查对齐项

### 自动触发

AI 根据 `when_to_use` 描述自主判断是否需要触发

## 去重策略

1. 基于 `kb-index.md` 的摘要判断是否可能重复
2. 如果不确定，读取对应详情文件精确去重
3. 相同信息更新时间戳，新信息追加

## 核心原则

1. **与 Auto Memory 分离** - 不污染 Claude Code 的 Auto Memory 系统
2. **项目级存储** - 知识库存储在 `evolution/knowledge-base/`
3. **按需加载** - 通过索引引导 AI 按需读取，避免上下文污染
4. **渐进成长** - AI 和人类都在协作中成长
EOF
```

### 2.3 创建知识库目录

```bash
# 创建知识库目录
mkdir -p evolution/knowledge-base
```

### 2.4 创建知识库模板文件

```bash
# 创建 kb-index.md（索引文件）
cat > evolution/knowledge-base/kb-index.md << 'EOF'
# Knowledge Base 索引（手动触发）

> 此文件是**手动触发**的 Knowledge Base 索引。
> 
> **触发方式**：`/evolution`
> **位置**：`evolution/knowledge-base/kb-index.md`

---

## 📊 概览

| 类别 | 文件 | 条目数 | 最后更新 |
|------|------|--------|----------|
| 关键事实 | facts.md | 0 | - |
| 踩坑记录 | pitfalls.md | 0 | - |
| 当前状态 | state.md | 0 | - |
| 学习笔记 | growth-notes.md | 0 | - |
| Prompt 改进 | prompt-improvements.md | 0 | - |
| 对齐清单 | alignment.md | 0 | - |
| 决策记录 | decisions.md | 0 | - |

---

##  元信息

- **触发来源**：manual
- **最后更新**：2026-07-28
- **Knowledge Base Agent 触发次数**：0
- **总条目数**：0
EOF

# 创建 facts.md
cat > evolution/knowledge-base/facts.md << 'EOF'
# 关键事实 (Facts)

> 记录环境配置、技术决策、依赖关系等关键事实。
> 由 Knowledge Base Agent 自动维护

---

## 环境配置

_（暂无）_

---

## 技术决策

_（暂无）_

---

## 依赖关系

_（暂无）_

---

## 元信息

- **最后更新**：2026-07-28
- **Knowledge Base Agent 触发次数**：0
- **总条目数**：0
EOF

# 创建 pitfalls.md
cat > evolution/knowledge-base/pitfalls.md << 'EOF'
# 踩坑记录 (Pitfalls)

> 记录错误模式、解决方案、注意事项
> 由 Knowledge Base Agent 自动维护

---

## 错误模式

_（暂无）_

---

## 解决方案

_（暂无）_

---

## 元信息

- **最后更新**：2026-07-28
- **Knowledge Base Agent 触发次数**：0
- **总条目数**：0
EOF

# 创建 state.md
cat > evolution/knowledge-base/state.md << 'EOF'
# 当前状态 (State)

> 记录任务进度、待确认项等实时信息
> 由 Knowledge Base Agent 自动维护

---

## 任务进度

_（暂无）_

---

## 待确认项

_（暂无）_

---

## 元信息

- **最后更新**：2026-07-28
- **Knowledge Base Agent 触发次数**：0
- **总条目数**：0
EOF

# 创建 growth-notes.md
cat > evolution/knowledge-base/growth-notes.md << 'EOF'
# 学习笔记 (Growth Notes)

> 从对话中提炼的技术知识点，持续积累
> 由 Growth Agent 自动维护

---

_（暂无笔记）_

---

## 元信息

- **最后更新**：2026-07-28
- **总笔记数**：0
- **Growth Agent 触发次数**：0
EOF

# 创建 prompt-improvements.md
cat > evolution/knowledge-base/prompt-improvements.md << 'EOF'
# Prompt 改进建议 (Prompt Improvements)

> 分析用户的提问方式，给出改进建议
> 由 Growth Agent 自动维护

---

_（暂无建议）_

---

## 元信息

- **最后更新**：2026-07-28
- **总建议数**：0
- **Growth Agent 触发次数**：0
EOF

# 创建 alignment.md
cat > evolution/knowledge-base/alignment.md << 'EOF'
# 对齐清单 (Alignment)

> 标记需要人类验收、确认或关注的项目
> 由 Alignment Agent 自动维护

---

##  高优先级（立即处理）

_（暂无）_

---

## 🟡 中优先级（本轮处理）

_（暂无）_

---

## 🟢 低优先级（后续处理）

_（暂无）_

---

## ✅ 已完成

_（暂无）_

---

## 元信息

- **最后更新**：2026-07-28
- **待处理项**：0
- **已完成项**：0
- **Alignment Agent 触发次数**：0
EOF

# 创建 decisions.md
cat > evolution/knowledge-base/decisions.md << 'EOF'
# 决策记录 (Decisions)

> 记录需要人类决策的关键点
> 由 Alignment Agent 自动维护

---

## 🤔 待决策

_（暂无）_

---

## ✅ 已决策

_（暂无）_

---

## 元信息

- **最后更新**：2026-07-28
- **待决策项**：0
- **已决策项**：0
- **Alignment Agent 触发次数**：0
EOF
```

---

## 3. 验证安装

### 3.1 检查目录结构

```bash
# 查看 Skill 文件
ls -la .claude/skills/evolution/

# 应该显示：
# SKILL.md

# 查看知识库文件
ls -la evolution/knowledge-base/

# 应该显示 8 个文件：
# kb-index.md
# facts.md
# pitfalls.md
# state.md
# growth-notes.md
# prompt-improvements.md
# alignment.md
# decisions.md
```

### 3.2 验证 Skill 加载

```
输入：/context
```

**观察 Skills 部分**：

**预期结果**：
```
Project
├── evolution: < 50 tokens    ← 应该显示
```

### 3.3 测试手动触发

```
输入：/evolution
```

**预期行为**：
```
AI: 我先读取 kb-index.md 了解知识库概览...
    [读取 kb-index.md]
AI: 基于索引，我需要读取...
    [只读取相关文件]
AI: 完成！
```

---

## 4. 故障排查

### 问题 1：Skill 不显示

**可能原因**：
- frontmatter 格式错误
- 目录结构不对

**解决**：
```bash
# 检查目录结构
ls -la .claude/skills/evolution/

# 应该显示：
# SKILL.md

# 检查 frontmatter 格式
head -10 .claude/skills/evolution/SKILL.md

# 应该显示：
# ---
# name: evolution
# description: ...
# ---
```

### 问题 2：AI 全量读取

**可能原因**：
- SKILL.md 中没有明确的渐进式读取指令

**解决**：
- 检查 SKILL.md 是否有"渐进式读取规则"部分
- 确认指令明确说"不要一次性读取所有文件"

### 问题 3：自动触发不工作

**可能原因**：
- `disable-model-invocation: true`（应该为 `false`）
- `when_to_use` 描述不清晰

**解决**：
- 检查 frontmatter 中 `disable-model-invocation: false`
- 优化 `when_to_use` 描述

---

## 5. 升级指南

### 5.1 从 V1 升级到 V2

**步骤**：

1. **备份 V1 文件**
   ```bash
   # 备份旧的 commands
   cp -r .claude/commands .claude/commands.v1.backup
   ```

2. **删除 V1 Skill（如果有）**
   ```bash
   rm -rf .claude/skills/evolution
   ```

3. **安装 V2**
   ```bash
   # 按照第 2 节步骤安装
   ```

4. **验证**
   ```bash
   # 按照第 3 节验证
   ```

### 5.2 保留向后兼容

如果需要保留 V1 的 Slash Command：

```bash
# 创建简化的命令文件
cat > .claude/commands/evolution.md << 'EOF'
# Evolution 系统

执行 Evolution 技能。

详见 `.claude/skills/evolution/SKILL.md`
EOF
```

---

## 6. 卸载指南

### 6.1 完全卸载

```bash
# 删除 Skill
rm -rf .claude/skills/evolution

# 删除知识库
rm -rf evolution-manual
```

### 6.2 保留知识库

如果只想卸载 Skill，保留知识库：

```bash
# 只删除 Skill
rm -rf .claude/skills/evolution

# 保留知识库
# evolution/ 目录保持不变
```

---

## 7. 最佳实践

### 7.1 定期清理

```bash
# 检查知识库大小
du -sh evolution/knowledge-base/

# 如果过大，考虑归档旧条目
```

### 7.2 版本控制

```bash
# 将知识库纳入版本控制
git add evolution/knowledge-base/
git commit -m "chore: update knowledge base"
```

### 7.3 团队共享

```bash
# 将 Skill 文件提交到仓库
git add .claude/skills/evolution/
git commit -m "feat: add evolution skill"

# 团队成员克隆后自动获得
```

---

## 8. 参考资料

### 8.1 官方文档

- [Extend Claude with skills](https://code.claude.com/docs/en/skills)
- [How Claude remembers your project](https://code.claude.com/docs/en/memory)
- [Commands](https://code.claude.com/docs/en/commands)

### 8.2 项目文档

- [V2 设计文档](./V2_DESIGN.md)
- [系统规则与运行逻辑](./EVOLUTION_RULES_AND_LOGIC_V2.md)
- [测试指南](./V2_TEST_GUIDE.md)

---

**安装完成！开始使用 Evolution V2。**
