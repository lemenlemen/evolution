# Evolution 版本历史

> **当前版本**：3.8.0
> **发布日期**：2026-08-01

---

## 版本变更概览

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v3.8.0 | 2026-08-01 | 修复三个 bug：强制脚本 + 禁止手动 glob、修复 find_jsonl_file 返回所有文件、增加验证机制 |
| v3.7.0 | 2026-08-01 | 修复 `/evolution-init` 命令，调用 `evolution-export.py` 导出全部历史，防止采样 |
| v3.6.0 | 2026-08-01 | 修复 `/evolution init` 为独立命令 `/evolution-init`，区分初始化和增量同步 |
| v3.5.0 | 2026-07-31 | 基于 writing-great-skills 规则重构，SKILL.md 从 96 行缩减至 37 行 |
| v3.4.0 | 2026-07-31 | 模块化重构，SKILL.md 拆分，config.yaml 统一配置 |
| v3.3.0 | 2026-07-30 | 修复 JSON 序列化崩溃、增量单位漂移、Windows 编码、token 估算偏低（CJK 系数 1.5→1.0）、cleanup 安全、文件句柄泄漏等多项问题 |
| v3.2.1 | 2026-07-30 | 更新分页参数：80K → 150K（基于注意力研究） |
| v3.2.0-draft | 2026-07-29 | 初始设计，基于 200K 窗口假设 |
| v3.1.0 | 2026-07-29 | 添加初始化命令、对话导出机制、sub agent 执行设计 |
| v3.0.0 | 2026-07-28 | 简化系统，删除 auto 版本，添加写入审核机制 |
| v2.1.0 | 2026-07-28 | 写入审核机制（状态标记） |
| v2.0.0 | 2026-07-28 | Skill 系统迁移 |
| v1.0.0 | 2026-07-21 | 初始版本 |

---

## v3.1.0 (2026-07-29)

### 新增功能

1. **初始化命令**
   - 添加 `/evolution init` 命令
   - 首次安装后分析全部历史对话
   - 生成初始知识库

2. **对话导出机制**
   - 方法 A：AI 记忆（默认）
   - 方法 B：文件记录（可选）

3. **Sub Agent 执行设计**
   - 所有操作由 sub agent 执行
   - 减少对主 session 的污染

### 设计文档变更

1. **CLAUDE.md**
   - 创建项目配置文件
   - 定义知识库位置

2. **SKILL.md**
   - 更新到 v3.1.0
   - 添加初始化命令
   - 添加对话导出机制
   - 强调 sub agent 执行原则

3. **DESIGN_V3.1.0.md**
   - 新建设计文档
   - 详细说明设计考虑
   - 说明文档职责分工

---

## v3.0.0 (2026-07-28)

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
|------|------|------|----------|
| 1.0.0 | 2026-07-21 | 初始 | Slash Command |
| 2.0.0 | 2026-07-28 | MAJOR | 迁移到 Skill 系统 |
| 2.1.0 | 2026-07-28 | MINOR | 写入审核机制 |
| 3.0.0 | 2026-07-28 | MAJOR | 删除 auto 版本，简化系统 |
| 3.1.0 | 2026-07-29 | MINOR | 添加初始化命令、对话导出机制 |
| 3.2.0 | 2026-07-29 | MINOR | 基于 200K 窗口的分页设计 |
| 3.2.1 | 2026-07-30 | PATCH | 更新分页参数：80K → 150K |
| 3.3.0 | 2026-07-30 | PATCH | 修复 JSON 序列化、Windows 编码、token 估算、文件句柄泄漏 |
| 3.4.0 | 2026-07-31 | MINOR | 模块化重构，SKILL.md 拆分，config.yaml |
| 3.5.0 | 2026-07-31 | MINOR | 基于 writing-great-skills 规则重构 |
| 3.6.0 | 2026-08-01 | MINOR | 将 `/evolution init` 拆分为 `/evolution-init` |
| 3.7.0 | 2026-08-01 | PATCH | 修复 `/evolution-init`，防止采样 |
| 3.8.0 | 2026-08-01 | PATCH | 修复三个 bug：强制脚本、find_jsonl_file、验证机制 |

---

## 未来规划

### [4.0.0] - 规划中
- 完整的四级状态模型
- 证据类型分类
- 主动审核流程

---

## 相关文档

| 文档 | 说明 |
|------|------|
| `docs/archive/FABLE_REVIEW.md` | AI reviewer 的深度评审 |
| `docs/PROJECT_BACKGROUND.md` | 项目背景 |
| `docs/archive/V2_DESIGN.md` | V2 设计文档 |
| `docs/archive/EVOLUTION_RULES_AND_LOGIC_V2.md` | V2 系统规则 |

---

**文档结束**
