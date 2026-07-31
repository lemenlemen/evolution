# V2 Skill 测试指南

> **创建日期**：2026-07-28  
> **目的**：验证 V2 Skill 是否正常工作

---

##  测试步骤

### 测试 1：验证 Skill 文件创建

```bash
# 检查文件是否存在
ls -la .claude/skills/evolution/SKILL.md

# 查看 frontmatter
head -10 .claude/skills/evolution/SKILL.md
```

**预期结果**：
- ✅ 文件存在
- ✅ frontmatter 包含 `name: evolution`
- ✅ `disable-model-invocation: false`

---

### 测试 2：验证 Skill 加载

```
输入：/context
```

**观察 Skills 部分**：

**预期结果**：
```
Project
├── evolution: < 50 tokens    ← 应该显示（frontmatter 描述）
```

**错误结果**：
- ❌ 不显示（Skill 未被识别）
- ❌ 显示 >100 tokens（加载了完整内容）

---

### 测试 3：验证手动触发

```
输入：/evolution
```

**观察 AI 行为**：

**预期结果**：
```
AI: 我先读取 kb-index.md 了解知识库概览...
    [读取 kb-index.md]
AI: 基于索引，我需要读取 facts.md...
    [只读取 facts.md]
AI: 完成！
```

**错误结果**：
- ❌ 读取所有 8 个文件
- ❌ 不读取索引直接读详情

---

### 测试 4：验证渐进式读取

```
输入：/evolution

然后观察 AI 实际读取了哪些文件
```

**检查方法**：
1. 观察 AI 的回复
2. 看它是否先提到"读取索引"
3. 看它是否只读取了相关文件

**预期上下文消耗**：
- kb-index.md: ~150 行
- facts.md: ~60 行
- **总计**: ~210 行（< 400 行 ✅）

---

### 测试 5：验证自动触发（高级）

**步骤**：
1. 开始日常对话
2. 问一个技术问题（如"我们之前用的是什么 Python 版本？"）
3. 观察 AI 是否主动参考知识库

**预期结果**：
```
用户：我们之前用的是什么 Python 版本？
AI: 让我查一下知识库...
    [读取 kb-index.md]
    [读取 facts.md]
AI: 根据记录，你们使用的是 Python 3.11
```

---

##  故障排查

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
```

---

### 问题 2：AI 全量读取

**可能原因**：
- SKILL.md 中没有明确的渐进式读取指令

**解决**：
- 检查 SKILL.md 是否有"渐进式读取规则"部分
- 确认指令明确说"不要一次性读取所有文件"

---

### 问题 3：自动触发不工作

**可能原因**：
- `disable-model-invocation: true`（应该为 `false`）
- `when_to_use` 描述不清晰

**解决**：
- 检查 frontmatter 中 `disable-model-invocation: false`
- 优化 `when_to_use` 描述

---

##  成功指标

| 指标 | 目标 | 测量方法 |
|------|------|---------|
| **Skill 加载** | 显示 < 50 tokens | `/context` |
| **手动触发** | 正常工作 | `/evolution` |
| **渐进式读取** | 只读相关文件 | 观察 AI 行为 |
| **上下文消耗** | < 400 tokens | `/context` |
| **自动触发** | AI 主动参考 | 日常对话测试 |

---

**测试完成！记录结果并调整。**
