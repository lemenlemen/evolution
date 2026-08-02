# Evolution 安装指南

> **版本**：3.8.0（2026-08-01）  
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

在 `.claude/skills/evolution/` 目录下创建 `SKILL.md` 文件，内容参考：
[SKILL.md](https://github.com/lemenlemen/evolution/blob/main/.claude/skills/evolution/SKILL.md)

或从 GitHub 复制：
```bash
curl -o .claude/skills/evolution/SKILL.md https://raw.githubusercontent.com/lemenlemen/evolution/main/.claude/skills/evolution/SKILL.md
```

### 2.3 创建知识库目录

```bash
# 创建知识库目录
mkdir -p evolution/knowledge-base
```

### 2.4 创建知识库模板文件

复制以下 8 个文件到 `evolution/knowledge-base/`：

- `kb-index.md` - 索引文件
- `facts.md` - 关键事实
- `pitfalls.md` - 踩坑记录
- `state.md` - 当前状态
- `growth-notes.md` - 学习笔记
- `prompt-improvements.md` - Prompt 改进
- `alignment.md` - 对齐清单
- `decisions.md` - 决策记录

模板文件参考：[knowledge-base](https://github.com/lemenlemen/evolution/tree/main/evolution/knowledge-base)

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
── evolution: < 50 tokens    ← 应该显示
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
- `description` 触发关键词不清晰

**解决**：
- 检查 frontmatter 中 `disable-model-invocation: false`
- 优化 `description` 字段的触发关键词

---

## 5. 升级指南

### 5.1 从 V2 升级到 V3

**步骤**：

1. **备份 V2 文件**
   ```bash
   # 备份旧的知识库
   cp -r evolution-manual/knowledge-base evolution-manual/knowledge-base.v2.backup
   ```

2. **迁移知识库**
   ```bash
   # 将文件从旧目录移到新目录
   mv evolution-manual/knowledge-base/*.md evolution/knowledge-base/
   ```

3. **删除旧目录**
   ```bash
   # 删除空的旧目录
   rmdir evolution-manual/knowledge-base/
   rmdir evolution-manual/
   ```

4. **验证**
   ```bash
   # 按照第 3 节验证
   ```

---

## 6. 卸载指南

### 6.1 完全卸载

```bash
# 删除 Skill
rm -rf .claude/skills/evolution

# 删除知识库
rm -rf evolution
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

- [设计文档](./DESIGN_V3.1.0.md)
- [项目背景](./PROJECT_BACKGROUND.md)
- [版本历史](./VERSION_HISTORY.md)

---

**安装完成！开始使用 Evolution v3.8.0。**
