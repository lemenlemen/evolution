# Evolution V3 - 系统规则与运行逻辑

> ⚠️ **过时文档（v4.1.6 补记）**：本文档描述的是 V3.x 系统规则（单文件结构、无模块化）。
> V4.0.0 起已改为模块化结构（SKILL.md + config.yaml + commands/ + rules/ + evolution-export.py）。
> 文件树、命令列表、状态模型均与当前实现不符。
> 当前系统行为以 `CLAUDE.md` + `.claude/skills/evolution/` + `docsV3/VERSION_HISTORY.md` 为准。

> **版本**：3.9.0（2026-08-01）  
> **基于**：V2 版本经验 + 简化需求

> **版本历史**：详见 [`VERSION_HISTORY.md`](./VERSION_HISTORY.md)

---

## 1. 系统概述

### 1.1 核心定位

Evolution 是一个**人机共生进化系统**，让 AI 和人类在协作中共同成长。

### 1.2 核心价值

| 价值 | 说明 |
|------|------|
| **让 AI 更可靠** | 记住关键信息，避免重复错误 |
| **让人类成长** | 生成学习笔记，提升协作效率 |
| **保持人机对齐** | 标记验收项，减少误解 |

---

## 2. 核心设计原则

> **Evolution 运行时派 sub agents 处理，尽量减少对主会话的污染**

所有操作（初始化、同步、历史分析）都由 **sub agent** 在后台执行。

---

## 3. 系统架构

### 3.1 文件结构

```
<project>/
├── .claude/
│   └── skills/
│       └── evolution/
│           └── SKILL.md              # Skill 定义
│
└── evolution/                        # 知识库
    └── knowledge-base/
        ├── kb-index.md               # 索引
        ├── facts.md                  # 关键事实
        ├── pitfalls.md               # 踩坑记录
        ├── state.md                  # 当前状态
        ├── growth-notes.md           # 学习笔记
        ├── prompt-improvements.md    # Prompt 改进
        ├── alignment.md              # 对齐清单
        └── decisions.md              # 决策记录
```

### 3.2 目录职责

| 目录/文件 | 用途 | 读者 |
|----------|------|------|
| `.claude/skills/evolution/SKILL.md` | Skill 定义和执行指令 | AI |
| `evolution/knowledge-base/` | 知识库数据 | AI + 人类 |
| `docsV3/` | 设计文档 | 人类 |

---

## 4. 执行命令

### 4.1 初始化命令（首次安装）

```bash
/evolution-init
```

**执行方式**：
1. 主 agent 触发 **sub agent**
2. Sub agent 在后台分析**全部**历史主会话对话（见第 5 节导出范围说明）
3. 提取所有关键事实
4. 记录所有踩坑记录
5. 生成初始知识库
6. 标记所有条目为 `[D]` (draft)
7. 返回摘要给主 agent

**使用场景**：
- 首次安装 Evolution 后
- 知识库被清空后
- 需要重新建立知识库时

### 4.2 同步命令（日常使用）

```bash
/evolution
```

**执行方式**：
1. 主 agent 触发 **sub agent**
2. Sub agent 在后台执行增量同步
3. 返回摘要给主 agent

---

## 5. 对话导出机制

Evolution 通过 `evolution-export.py` 脚本导出 Claude Code 的对话历史（JSONL 格式）。这是唯一的数据导出方式。

### 5.1 导出脚本

**脚本位置**：`.claude/skills/evolution/evolution-export.py`

**功能**：
1. 发现 JSONL 文件路径（`~/.claude/projects/<hash>/`）
2. 解析 JSONL 格式，过滤噪声条目
3. 提取有意义的对话内容（user/assistant 文本、工具调用、思考等）
4. 分页为 ~90K token 的 chunk
5. 输出 chunk 文件到 `.evolution/chunks/`
6. 管理 `sync-state.json` 增量同步状态

**导出范围与保真度（如实说明）**：

- **覆盖范围**：只导出主会话的顶层 `*.jsonl` 文件；`subagents/` 子目录下的
  sub agent 转录默认排除——避免 Evolution 自我摄取形成强化循环。因此
  sub agent 会话中的内容不会进入知识库。
- **内容截断**：为控制 chunk 体积，导出按设计做了摘要截断，并非原文完整保留：
  - thinking：超过 400 字符时保留前 200 + 后 100 字符
  - tool_use：仅保留工具名与关键参数摘要（如 Bash 命令前 500 字符）
  - tool_result：超过 600 字符时保留前 500 字符（错误信息额外保留尾部 200 字符）
  - 单个超大 entry 超出 chunk 预算时会整体截断兜底
- **噪声过滤**：非 user/assistant 类型条目（进度、元数据等）不导出

### 5.2 执行流程

```
用户输入 /evolution-init（初始化）或 /evolution（增量同步）
    ↓
主 agent 触发 sub agent
    ↓
Sub agent 执行 evolution-export.py
    ↓
脚本输出分页 chunk 文件（~90K token/chunk）
    ↓
Sub agent 逐 chunk 读取分析，提取知识
    ↓
写入知识库（evolution/knowledge-base/）
    ↓
更新 sync-state.json
```

### 5.3 优势与局限

- ✅ 主会话对话全量分块导出，不做随机采样
- ✅ 分页处理，避免上下文溢出
- ✅ 增量同步，只处理新增内容
- ✅ 主 session 几乎不被污染
- ⚠️ **并非逐字完整导出**：内容按上述策略摘要截断，subagent 转录默认排除，
  噪声条目被过滤——知识库覆盖的是主会话中有意义的对话信息，不是原始记录的全量镜像

---

## 6. Sub Agent 执行规则

### 6.1 核心原则

> **Evolution 运行时派 sub agents 处理，尽量减少对主会话的污染**

### 6.2 职责分工

**主 agent**：
- 接收用户命令
- 触发 sub agent
- 显示 sub agent 返回的摘要
- **不直接操作知识库**

**Sub agent**：
- 读取对话历史
- 提取知识
- 写入知识库
- 返回摘要

### 6.3 好处

- ✅ 主 session 几乎不被污染
- ✅ 主 session 保持流畅
- ✅ 知识库操作在后台完成

---

## 7. 写入规则（审核机制）

### 7.1 状态标记

| 状态 | 标记 | 含义 |
|------|------|------|
| draft | `[D]` | AI 提取，未经用户验证 |
| verified | `[V]` | 用户明确确认或工具验证 |
| deprecated | `[X]` | 已废弃或已证实错误 |

### 7.2 写入规则

1. **所有新条目默认标记为 `[D]`**
   - 格式：`### [D] 条目标题`
   - 示例：`### [D] WSL 网络配置`

2. **以下情况可标记为 `[V]`**：
   - 用户在对话中明确确认（如说"对"、"是的"）
   - 工具调用结果验证（如 `node -v` 输出）
   - 外部文档引用

3. **冲突处理**：
   - 新条目与已有条目冲突 → 旧条目标记为 `[X]`（deprecated）
   - 新条目以 `[D]` 写入

### 7.3 读取时区分状态

- `[V]` 条目：正常使用
- `[D]` 条目：可使用，但标注"未验证"
- `[X]` 条目：不读取

---

## 8. 渐进式读取规则

### 8.1 核心原则

**重要**：不要一次性读取所有文件！遵循渐进式披露原则。

### 8.2 读取步骤

**步骤 1：读取索引**

读取 `evolution/knowledge-base/kb-index.md`

**步骤 2：判断需求**

基于索引中的分类摘要，判断当前任务需要哪些信息：

- 如果用户问环境配置 → 读取 `facts.md`
- 如果用户问历史错误 → 读取 `pitfalls.md`
- 如果需要更新状态 → 读取 `state.md`
- 如果用户问学习知识 → 读取 `growth-notes.md`
- 如果需要验收检查 → 读取 `alignment.md`
- 如果需要决策记录 → 读取 `decisions.md`

**步骤 3：按需读取**

**只读取相关的 1-2 个文件**，不要全量加载所有文件

---

## 9. 去重策略

1. 基于 `kb-index.md` 的摘要判断是否可能重复
2. 如果不确定，读取对应详情文件精确去重
3. 相同信息更新时间戳，新信息追加

---

## 10. 知识库文件说明

| 文件 | 用途 | 读取 | 写入 |
|------|------|------|------|
| `kb-index.md` | 索引文件（<200 行） | ✅ | ✅ |
| `facts.md` | 关键事实 | ✅ | ✅ |
| `pitfalls.md` | 踩坑记录 | ✅ | ✅ |
| `state.md` | 当前状态 | ✅ | ✅ |
| `growth-notes.md` | 学习笔记 | ✅ | ✅ |
| `prompt-improvements.md` | Prompt 改进 | ✅ | ✅ |
| `alignment.md` | 对齐清单 | ✅ | ✅ |
| `decisions.md` | 决策记录 | ✅ | ✅ |

---

## 11. 核心原则总结

1. **与 Auto Memory 分离** - 不污染 Claude Code 的 Auto Memory 系统
2. **项目级存储** - 知识库存储在 `evolution/knowledge-base/`
3. **按需加载** - 通过索引引导 AI 按需读取，避免上下文污染
4. **渐进成长** - AI 和人类都在协作中成长
5. **双向同步** - 既读取已有知识，也写入新知识
6. **人工审核** - 所有内容必须人工核对，人类也要读取文档学习
7. **Sub Agent 执行** - 所有操作由 sub agent 执行，减少主 session 污染

---

## 12. 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v3.9.0 | 2026-08-01 | 添加 `/evolution-init` 前置检查，防止误触重置 |
| v3.8.0 | 2026-08-01 | 修复三个 bug：强制脚本 + 禁止手动 glob、修复 find_jsonl_file 返回所有文件、增加验证机制 |
| v3.7.0 | 2026-08-01 | 修复 `/evolution-init` 命令，调用 `evolution-export.py` 导出全部历史，防止采样 |
| v3.6.0 | 2026-08-01 | 修复 `/evolution init` 为独立命令 `/evolution-init`，区分初始化和增量同步 |
| v3.5.0 | 2026-07-31 | 基于 writing-great-skills 规则重构，SKILL.md 从 96 行缩减至 37 行 |
| v3.4.0 | 2026-07-31 | 模块化重构，SKILL.md 拆分，config.yaml 统一配置 |
| v3.3.0 | 2026-07-30 | 修复 JSON 序列化崩溃、增量单位漂移、Windows 编码、token 估算偏低 |
| v3.2.1 | 2026-07-30 | 更新分页参数：80K → 150K（基于注意力研究） |
| v3.2.0-draft | 2026-07-29 | 初始设计，基于 200K 窗口假设（已被 v3.2.1 取代） |
| v3.1.0 | 2026-07-29 | 添加初始化命令、对话导出机制 |
| v3.0.0 | 2026-07-28 | 简化系统，删除 auto 版本 |
| v2.1.0 | 2026-07-28 | 写入审核机制 |
| v2.0.0 | 2026-07-28 | Skill 系统迁移 |
| v1.0.0 | 2026-07-21 | 初始版本 |

---

**文档结束**
