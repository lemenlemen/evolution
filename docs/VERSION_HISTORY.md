# Evolution 版本历史

> 本文档记录 Evolution 系统的所有版本变更

---

## 版本格式

采用**语义化版本（Semantic Versioning 2.0.0）**：

```
MAJOR.MINOR.PATCH
```

- **MAJOR**：重大架构变化（不兼容的变更）
- **MINOR**：新功能（向下兼容）
- **PATCH**：小修补、bug 修复

---

## 版本记录

### [3.0.0] - 2026-07-28

**重大变更**：
- 删除 `evolution-auto/` 目录（自动触发版本）
- 知识库目录从 `evolution-manual/` 改为 `evolution/`
- 简化系统，只保留手动触发版本

**修改原因**：
- 所有内容都必须人工核对
- 人类也要读取文档学习
- 自动触发版本未经实战检验
- 简化系统，减少复杂度

**修改文件**：
- 删除 `evolution-auto/` 目录
- 重命名 `evolution-manual/` → `evolution/`
- `.claude/skills/evolution/SKILL.md`
  - 版本号：2.1.0 → 3.0.0
  - 去掉"自动触发"章节
  - 去掉"手动触发"标题（只有一种了）
  - 更新知识库位置：`evolution-manual/` → `evolution/`
  - 新增核心原则：人工审核
- `evolution/knowledge-base/kb-index.md`
  - 版本号：2.1.0 → 3.0.0
  - 去掉"手动触发"标记
  - 更新位置信息

**向后兼容**：
- ❌ 不兼容（目录结构变化）
- ️ 需要迁移现有知识库

**迁移指南**：
```bash
# 1. 重命名目录
mv evolution-manual evolution

# 2. 更新 SKILL.md 中的路径引用（已自动完成）

# 3. 验证
/evolution
```

---

### [2.1.0] - 2026-07-28

**新增功能**：
- 添加写入审核机制（状态标记）
- 新条目默认标记为 `[D]`（draft）
- 用户确认后标记为 `[V]`（verified）
- 废弃条目标记为 `[X]`（deprecated）

**修改文件**：
- `.claude/skills/evolution/SKILL.md`
  - 新增"写入规则（审核机制）"章节
  - 定义三级状态模型（draft/verified/deprecated）
  - 明确写入规则和冲突处理
  
- `evolution-manual/knowledge-base/kb-index.md`
  - 新增"读取指南（AI 必须遵守）"章节
  - 定义状态标记说明
  - 明确使用规则（优先级、冲突处理）

- `evolution-manual/knowledge-base/facts.md`
  - 添加状态标记说明
  - 现有条目添加 `[V]` 标记

**设计文档**：
- `docs/FABLE_REVIEW.md` - AI reviewer 的深度评审
- `docs/PROJECT_BACKGROUND.md` - 项目背景（用户原始需求）

**改进原因**：
- AI review指出"写入审核机制缺失"是致命缺陷
- 错误信息会形成自我强化循环
- 需要简单的审核机制打破循环

**影响范围**：
- 所有知识库文件（facts.md、pitfalls.md 等）
- AI 的读取和写入行为
- 用户可能需要审核新条目

**向后兼容**：
- ✅ 完全兼容 V2.0
- ✅ 旧条目无标记，默认为 `[D]`
- ✅ 读取规则对无标记条目友好

---

### [2.0.0] - 2026-07-28

**重大变更**：
- 从 Slash Command 迁移到 Skill 系统
- 支持渐进式披露
- 支持自动触发（AI 判断）

**新增功能**：
- 双向功能（读取 + 写入）
- 渐进式读取规则
- 与 Auto Memory 分离

**修改文件**：
- `.claude/skills/evolution/SKILL.md` - 新建
- `CLAUDE.md` - 已删除（Skill 独立工作）

**设计文档**：
- `docs/V2_DESIGN.md` - V2 设计文档
- `docs/EVOLUTION_RULES_AND_LOGIC_V2.md` - 系统规则
- `docs/INSTALLATION_GUIDE_V2.md` - 安装指南
- `docs/V2_TEST_GUIDE.md` - 测试指南
- `docs/UPDATE_NOTES_V2.md` - 更新说明
- `docs/PROJECT_BACKGROUND.md` - 项目背景
- `docs/FABLE_REVIEW.md` - AI review

**改进原因**：
- V1 使用 Slash Command，AI 不知道知识库存在
- V2 使用 Skill，AI 知道且可自动触发
- 节省 66% 上下文消耗

---

### [1.0.0] - 2026-07-21

**初始版本**：
- 使用 Slash Command 触发
- 基础知识库结构
- 单向功能（只读取）

**文件**：
- `.claude/commands/evolution.md` - 命令定义
- `evolution-manual/knowledge-base/` - 知识库目录

**已知问题**：
- AI 不知道知识库存在
- 无法自动触发
- 上下文消耗大（全量读取）

---

## 变更统计

| 版本 | 日期 | 类型 | 主要变更 |
|------|------|------|---------|
| 1.0.0 | 2026-07-21 | 初始 | Slash Command |
| 2.0.0 | 2026-07-28 | MAJOR | 迁移到 Skill 系统 |
| 2.1.0 | 2026-07-28 | MINOR | 写入审核机制 |
| 3.0.0 | 2026-07-28 | MAJOR | 删除 auto 版本，简化系统 |

---

## 未来规划

### [3.1.0] - 计划中
- 被动审核机制（对话中自然验证）
- 自动提升状态（draft → verified）

### [3.2.0] - 计划中
- 清理机制（stale 标记 + 自动归档）
- 文件容量监控

### [4.0.0] - 规划中
- 完整的四级状态模型
- 证据类型分类
- 主动审核流程

---

## 相关文档

| 文档 | 说明 |
|------|------|
| `docs/FABLE_REVIEW.md` | AI reviewer 的深度评审 |
| `docs/PROJECT_BACKGROUND.md` | 项目背景 |
| `docs/V2_DESIGN.md` | V2 设计文档 |
| `docs/EVOLUTION_RULES_AND_LOGIC_V2.md` | 系统规则 |
| `docs/INSTALLATION_GUIDE_V2.md` | 安装指南 |

---

**文档结束**
