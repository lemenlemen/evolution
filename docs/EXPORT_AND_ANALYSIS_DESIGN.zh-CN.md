# 导出和分析对话内容 - 设计方案

> ⚠️ **过时文档（v4.1.5 补记）**：本文档描述的是 V3.x 引擎设计（单游标 `processed_lines`、schema 3.4.0、4 个 CLI 模式）。
> V4.0.0 起已改为双游标（`exported_lines`/`committed_lines`）、schema 3.5.0、7 个 CLI 模式。源码行号引用已全部失效。
> 当前系统行为以 `CLAUDE.md` + `.claude/skills/evolution/` + `docsV3/VERSION_HISTORY.md` 为准。

> **版本**：3.9.0
> **日期**：2026-08-01
> **作者**：lemen
> **状态**：设计完成，已修复并验证

---

## 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| 3.9.0 | 2026-08-01 | 添加 `/evolution-init` 前置检查，防止误触重置 |
| 3.8.0 | 2026-08-01 | 删除内嵌代码改为引用源码；补充 v3.8.0 验证机制（文件消费一致性校验 + 跨进程文件锁）；修正 `find_jsonl_file`/`compute_project_hash`/`estimate_tokens`/`parse_jsonl`/`ConversationEntry`/`sync-state.json` 等多处与代码不符的描述 |
| 3.3.0 | 2026-07-31 | 修复 JSON 序列化崩溃、增量单位漂移、Windows 编码、token 估算偏低（CJK 系数 1.5→1.0）、cleanup 安全、文件句柄泄漏等多项问题 |
| 3.2.1 | 2026-07-30 | 更新分页参数：80K → 150K（基于注意力研究） |
| 3.2.0-draft | 2026-07-29 | 初始设计，基于 200K 窗口假设 |

---

## 关键变更（v3.3.0）

**Token 估算修正：**

| 参数 | v3.2.1 | v3.3.0 | 理由 |
|------|--------|--------|------|
| **CJK 系数** | 1.5 字符/token | **1.0 字符/token** | 与实际测试吻合（实测 ~1.0） |
| **目标 chunk 大小** | 150K | **90K** | 90K × 1.68 ≈ 150K 实际，在 200K 硬上限内 |
| **硬上限** | 200K | **200K** | 保持不变 |
| **最小值** | 40K | **40K** | 保持不变 |
| **预计 chunk 数** | 2-3 个 | **5-6 个** | 过滤后总量 ~371K（估算口径），按 90K 目标切分并受轮次边界约束，实际 5-6 个 |

**口径说明（统一术语）**：

- **估算 tokens**：`estimate_tokens` 按英文/代码 4 字符/token、CJK 1.0 字符/token 加权计算，
  是分页器实际使用的度量。目标 chunk 大小 90K、硬上限 200K 均指该估算值。
- **实际消耗 tokens**：模型真实计费/占用的 token 数，经验上约为估算值的 1.5-1.7 倍
  （CJK 密集内容实测 90K 估算 ≈ 140-150K 实际）。规划 sub agent 窗口时以实际值为准。
- 文中所有"90K / 371K"均为估算口径；"140-150K"为实际口径，两者不再混用。

**修正原因：**

v3.2.1 的 150K **估算** → 实际 ~250K（**超过 200K 硬上限**）
v3.3.0 的 90K **估算** → 实际 ~150K（**在 200K 硬上限内**）

**实际测试验证（15MB JSONL）：**
- ✅ 每个 chunk 约 85-90K（估算）
- ✅ 实际约 140-150K（在 200K 硬上限内）
- ✅ 无 chunk 超过 200K

---

| 指标 | v3.2.0（5 chunks） | v3.2.1（3 chunks） | 改善 |
|------|--------------------|-------------------|------|
| 全量耗时 | ~5-7 分钟 | ~3-4 分钟 | **~40%** |
| 跨 chunk 知识断裂风险 | 中（5 次切断） | 低（3 次切断） | **显著改善** |

**决策依据：**

1. **注意力稀释研究**：
   - **"Lost in the Middle" 论文**（Liu, Lin, Hewitt, Paranjape, Bevilacqua, Petroni, Liang, 2023, arXiv:2307.03172）发现 LLM 呈现 U 型注意力曲线
   - 上下文开头和结尾的信息被处理得最好，中间的信息最容易被忽略

2. **检索 vs 合成的区分**：
   - **检索任务**（找某个具体事实）：长上下文表现很好，即使 1M+
   - **合成/分析任务**（理解、提取、总结）：明显退化
   - Evolution 属于合成/分析任务，需要关注注意力质量

3. **有效上下文经验法则**：
   - 检索任务的有效上下文：约最大窗口的 70-80%
   - **合成/分析任务的有效上下文：约最大窗口的 20-30%**
   - 对于 1M 窗口：合成有效约 200-300K

## 90K 的计算（v3.3.0）

有效上下文 200-300K（合成任务） - 其他分配 98K（8K 指令 + 10K 读 + 10K 写 + 20K 输出 + 50K 开销） = chunk 内容上限 102-202K，取 ~90K 作为目标（v3.3.0 考虑 CJK 系数修正后）。

```
1M 窗口分配：
├── chunk 内容：        90K  （目标）
├── 分析指令：          ~8K  （prompt 模板）
├── 知识库读取：       ~10K  （kb-index + 5-6 个详情文件）
├── 知识库写入：       ~10K  （提取的知识）
├── 输出空间：         ~20K  （更大的 chunk 提取更多知识）
├── 模型内部开销：     ~50K  （system prompt、工具定义等）
├── 安全余量：        ~812K  （剩余，极其充裕）
── 实际使用率：       ~19%  （188K/1000K，远在安全区内）
```

**结论**：90K 是 1M 窗口下"装得够多、消化得好"的平衡点（考虑 CJK 系数修正后）。

---

## 0. 前置数据分析

在设计方案前，对实际 JSONL 文件进行了全面分析，以下为关键发现：

### 0.1 文件概况

| 指标 | 数值 |
|------|------|
| 文件路径 | `~/.claude/projects/<project-hash>/<session-uuid>.jsonl` |
| 文件大小 | 14 MB |
| 总行数 | 5,232 行 |
| 时间跨度 | 2026-06-29 ~ 2026-07-30（约 31 天） |

### 0.2 条目类型分布

| 类型 | 数量 | 说明 |
|------|------|------|
| assistant | 2,015 | AI 回复（含 text/thinking/tool_use 块） |
| user | 1,078 | 用户消息（含 text/tool_result/image 块） |
| file-history-snapshot | 326 | 文件历史快照（元数据，可忽略） |
| system | 305 | 系统消息 |
| last-prompt | 300 | 最近提示（元数据，可忽略） |
| mode / permission-mode / ai-title | 各 291 | 模式/权限/标题（元数据，可忽略） |
| attachment | 251 | 附件 |
| queue-operation | 78 | 队列操作（元数据，可忽略） |
| file-history-delta | 9 | 文件增量（元数据，可忽略） |

### 0.3 内容块分布

**assistant 内容块（4,015 个）：**
- tool_use: 793（工具调用，如 Bash/Edit/Write/Read）
- thinking: 776（思考过程）
- text: 446（文本回复）

**user 内容块：**
- tool_result: 793（工具返回结果）
- string: 248（用户直接输入文本）
- text: 37（文本块）
- image: 15（图片）

**工具调用分布：** Bash(294) > Edit(178) > Write(112) > Read(107) > Agent(45) > GitHub MCP(33) > WebSearch(12)

### 0.4 Token 估算（关键约束）

| 内容类别 | 估算 Token 数 | 说明 |
|----------|---------------|------|
| tool_use 输入 | ~251K | 工具调用参数（命令、文件内容等） |
| tool_result 输出 | ~191K | 工具返回结果（命令输出、文件内容等） |
| user_text | ~114K | 用户直接输入 |
| assistant_text | ~101K | AI 文本回复 |
| thinking | ~60K | AI 思考过程 |
| **总计** | **~716K** | 占 1M 原始窗口约 72%，远超合成有效上下文（200-300K） |
| 过滤后（去 thinking + tool_result） | ~465K | 仍超合成有效上下文（200-300K） |

**核心矛盾：716K tokens 需要被分析，但 sub agent 上下文窗口为 1M tokens，但合成/分析任务的有效上下文约 200-300K，仍需分页处理。**

---

## 1. 架构设计

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────┐
│                    主 Agent（用户交互层）              │
│  接收 /evolution-init 或 /evolution               │
│  派发 sub agent，显示最终摘要                         │
└──────────────────────┬──────────────────────────────┘
                       │ 触发
                       ▼
┌─────────────────────────────────────────────────────┐
│              Sub Agent（分析协调层）                    │
│                                                      │
│  1. 调用 evolution-export.py 解析 JSONL             │
│  2. 获取分页后的对话摘要                              │
│  3. 逐页分析，提取知识                               │
│  4. 合并结果，写入知识库                              │
│  5. 更新同步状态                                     │
└──────┬────────────────┬─────────────────────────────┘
       │                │
       ▼                ▼
┌──────────────┐  ┌──────────────────┐
│ export.py    │  │ knowledge-base/  │
│ (Python脚本)  │  │ (8个知识库文件)   │
│              │  │                  │
│ - 路径发现    │  │ - facts.md       │
│ - JSONL解析   │  │ - pitfalls.md    │
│ - 内容过滤    │  │ - state.md       │
│ - 分页输出    │  │ - ...            │
│ - 状态管理    │  │                  │
└──────────────┘  └──────────────────┘
       │
       ▼
┌──────────────┐
│ .evolution/  │
│ (状态目录)    │
│              │
│ sync-state   │
│ .json        │
│ chunks/      │
│   chunk-00.md │
│   chunk-01.md │
│   ...        │
└──────────────┘
```

### 1.2 数据流

```
JSONL 原始文件（14MB / 5232行）
        │
        ▼ evolution-export.py --mode full
        │
    解析 + 过滤 + 分页
        │
        ├─→ chunk-00.md（~90K tokens 估算）
        ├─→ chunk-01.md（~90K tokens 估算）
        ├─→ chunk-02.md（~90K tokens 估算）
        ├─→ chunk-03.md（~90K tokens 估算）
        └─→ chunk-04.md（~11K tokens 估算）
              │
              ▼ Sub Agent 逐页读取分析
              │
         知识提取 + 去重
              │
              ▼
         知识库写入（8个.md文件）
              │
              ▼
         sync-state.json 更新
```

### 1.3 组件设计

| 组件 | 职责 | 技术选型 |
|------|------|----------|
| `evolution-export.py` | JSONL 解析、过滤、分页、状态管理 | Python 3.x（标准库，无依赖） |
| Sub Agent 协调器 | 逐页调用分析、结果合并 | Claude Code Agent tool |
| `sync-state.json` | 增量同步状态（游标） | JSON 文件 |
| 知识库写入器 | 将分析结果写入 8 个 .md 文件 | Sub Agent 直接文件操作 |

---

## 2. 全量导出方案

### 2.1 导出策略

**核心思路：Python 脚本做"重活"，Sub Agent 做"智活"**

Python 脚本负责：
1. 发现 JSONL 文件路径
2. 解析 JSONL 格式
3. 过滤噪声（metadata 条目）
4. 提取有意义的对话内容
5. 将内容分页为 ~90K token 的 chunk
6. 输出为 Markdown 格式的 chunk 文件

Sub Agent 负责：
1. 逐个读取 chunk 文件
2. 分析对话内容，提取知识
3. 去重并与现有知识库合并
4. 更新知识库文件

### 2.2 内容过滤策略

**保留的内容（高价值）：**

| 类型 | 处理方式 | 保留比例 |
|------|----------|----------|
| user text（用户输入） | 完整保留 | 100% |
| assistant text（AI 文本回复） | 完整保留 | 100% |
| thinking（AI 思考） | 摘要保留（前 200 字 + 关键决策） | ~30% |
| tool_use（工具调用） | 摘要保留（工具名 + 关键参数） | ~40% |
| tool_result（工具返回） | 摘要保留（前 500 字 + 错误信息） | ~20% |

**丢弃的内容（低价值）：**

| 类型 | 原因 |
|------|------|
| mode / permission-mode | 纯状态标记，无知识价值 |
| ai-title | 标题元数据 |
| file-history-snapshot | 文件快照，无知识价值 |
| file-history-delta | 文件增量，无知识价值 |
| last-prompt | 重复的 prompt 记录 |
| queue-operation | 队列操作元数据 |
| attachment（二进制） | 无法有效分析 |
| system（部分） | 系统提示，非用户对话 |

**过滤后 Token 估算：**

```
user_text:       114K tokens → 114K（100%保留）
assistant_text:  101K tokens → 101K（100%保留）
thinking:         60K tokens →  18K（30%保留）
tool_use:        251K tokens → 100K（40%保留）
tool_result:     191K tokens →  38K（20%保留）
─────────────────────────────────────────────
过滤后总计:                       ~371K tokens
```

371K tokens（估算口径）按 90K 目标切分 ≈ **4.1 个 chunk 的数学下界；实际产生 5-6 个**——
因为分页必须保持对话轮次完整（不在轮次中间切断），且不足 40K 最小值的尾部轮次会合并到上一页，
轮次边界约束使 chunk 数高于纯除法结果。

### 2.3 分页策略

**分页目标：** 每个 chunk ~90K tokens，扣除分析指令、知识库读写、输出空间和模型开销后，仍有 ~812K 安全余量

**分页规则：**

1. **按时间顺序分页**：保持对话的时间连续性
2. **按对话轮次边界切分**：不在 user-assistant 对的中间切断
3. **目标大小：90K tokens**（估算口径；实际消耗约 140-150K tokens）
4. **硬上限：200K tokens**（不超过此值）
5. **最小值：40K tokens**（不足则合并到上一页）

**对话轮次定义：**
- 一个"轮次" = 一条 user 消息 + 对应的所有 assistant 消息（可能多条）
- tool_use 和 tool_result 配对归入同一轮次
- thinking 块归入其所属的 assistant 消息

### 2.4 分析策略

**逐页分析流程：**

```
对每个 chunk-N.md：
    1. Sub Agent 读取 chunk 文件
    2. 读取当前知识库 kb-index.md（了解已有知识）
    3. 分析 chunk 中的对话内容
    4. 提取以下类型知识：
       - 关键事实 → facts.md
       - 踩坑记录 → pitfalls.md
       - 状态变更 → state.md
       - 学习要点 → growth-notes.md
       - Prompt 改进 → prompt-improvements.md
       - 对齐项 → alignment.md
       - 决策记录 → decisions.md
    5. 与已有知识去重
    6. 写入知识库文件（标记 [D]）
    7. 更新 kb-index.md
```

**知识提取标准：**

| 类别 | 提取标准 | 示例 |
|------|----------|------|
| 关键事实 | 环境配置、技术选型、依赖关系、项目身份 | "Python 3.12 安装在 WSL 中" |
| 踩坑记录 | 报错信息 + 原因 + 解决方案 | "git push 超时 → 配置代理" |
| 状态变更 | 项目阶段、里程碑、完成状态 | "V3 设计完成" |
| 学习要点 | 用户可学习的技术知识点 | "Commits vs Releases 的区别" |
| Prompt 改进 | 用户提问方式的优化建议 | "更具体地描述期望的输出格式" |
| 对齐项 | 需要用户确认的事项 | "作者名使用 lemen" |
| 决策记录 | 技术决策 + 理由 | "选择 Skill 系统而非 Slash Command" |

### 2.5 存储策略

**全量分析结果存储位置：**

```
<project>/
├── .evolution/                    # Evolution 状态目录
│   ├── sync-state.json            # 同步状态（游标）
│   ├── export.lock                # 跨进程文件锁（v3.8.0）
│   └── chunks/                    # 临时分页文件
│       ├── chunk-00.md
│       ├── chunk-01.md
│       ├── ...
│       └── chunk-N.md
│
└── evolution/
    └── knowledge-base/            # 知识库（最终结果）
        ├── kb-index.md
        ├── facts.md
        ├── pitfalls.md
        ├── state.md
        ├── growth-notes.md
        ├── prompt-improvements.md
        ├── alignment.md
        └── decisions.md
```

**chunk 文件生命周期：** 分析完成后可删除，或保留用于回溯。

---

## 3. 增量导出方案

### 3.1 增量识别

**核心机制：游标（Cursor）**

在 `sync-state.json` 中记录最后处理的 JSONL 条目位置：

```json
{
  "version": "3.4.0",
  "last_full_sync": "2026-07-30T11:38:00",
  "last_incremental_sync": "2026-07-30T15:00:00",
  "project_hash": "<project-hash>",
  "files": {
    "~/.claude/projects/<project-hash>/xxx.jsonl": {
      "path": "~/.claude/projects/<project-hash>/xxx.jsonl",
      "sha256": "abc123...",
      "mtime": 1753867200.0,
      "total_lines": 5232,
      "processed_lines": 5232,
      "processed_bytes": 14227502,
      "last_event_timestamp": "2026-07-30T03:39:21.771Z"
    }
  }
}
```

> 完整结构定义见 `evolution-export.py` 第 648-679 行（`file_info_to_dict` / `state_to_dict` / `_empty_state`），字段语义见 4.6。

**增量识别算法：**

```
1. 读取 sync-state.json，获取每个文件的 processed_lines（物理行号）
2. 解析该文件从 processed_lines + 1 起的后续行
3. 若有新条目 -> 执行增量导出；否则跳过该文件
4. 处理完成后将 processed_lines 更新为最后一条 entry 的真实行号
```

**边界情况处理：**

| 情况 | 处理方式 |
|------|----------|
| JSONL 文件被截断（行数减少） | 警告用户，建议全量重新导出 |
| sync-state.json 不存在 | 视为首次运行，执行全量导出 |
| sync-state.json 损坏 | 视为首次运行，执行全量导出 |
| 多个 session 文件 | 逐个处理，各自维护游标 |
| JSONL 文件被轮转（新文件） | 检测新文件，全量导出新文件 |

### 3.2 增量导出

**增量导出流程：**

```
用户输入 /evolution（或 /evolution-init 已执行过）
    ↓
主 Agent 触发 Sub Agent
    ↓
Sub Agent 执行：
  1. python evolution-export.py --mode incremental
     → 读取 sync-state.json
     → 从 processed_lines + 1 开始解析
     → 过滤 + 分页（通常只有 1 个 chunk）
     → 输出 chunk-inc-00.md
  2. 读取 chunk-inc-00.md
  3. 分析内容，提取知识
  4. 与现有知识库去重合并
  5. 写入知识库
  6. 更新 sync-state.json
  7. 返回摘要
```

### 3.3 增量合并

**合并策略：基于内容的语义去重**

```
对于每条新提取的知识：
  1. 读取 kb-index.md 获取已有知识概览
  2. 判断是否与已有条目语义重复：
     - 完全重复 → 跳过，更新已有条目的时间戳
     - 部分重复（同一主题，新信息） → 更新已有条目
     - 冲突（矛盾信息） → 旧条目标记 [X]，新条目以 [D] 写入
     - 全新 → 追加到对应知识库文件
  3. 更新 kb-index.md
```

**去重判断规则：**

| 情况 | 判断依据 | 处理 |
|------|----------|------|
| 完全重复 | 标题 + 内容高度相似（>90%） | 跳过 |
| 补充更新 | 同一主题，有新细节 | 合并，保留新旧信息 |
| 信息冲突 | 同一事实，不同值 | 旧标记 [X]，新标记 [D] |
| 全新知识 | 无相似条目 | 追加写入 |

---

## 4. 技术实现细节

### 4.1 evolution-export.py 设计

**文件位置：** `<project>/.claude/skills/evolution/evolution-export.py`

**命令行接口：**

```bash
# 全量导出
python evolution-export.py --mode full --project-path <project-root> --output .evolution/chunks

# 增量导出
python evolution-export.py --mode incremental --project-path <project-root> --output .evolution/chunks

# 查看状态
python evolution-export.py --mode status --project-path <project-root> --output .evolution/chunks

# 清理临时文件
python evolution-export.py --mode cleanup --project-path <project-root> --output .evolution/chunks
```

> 命令行参数：`--mode`（full/incremental/status/cleanup，必填）、`--project-path`（默认 `.`）、`--output`（输出目录，默认 `.evolution/chunks`）。源码：`evolution-export.py` 第 1068-1118 行（`main`）。

**输出格式：** JSON 到 stdout，供 Sub Agent 解析

```json
{
  "status": "success",
  "mode": "full",
  "total_entries": 5232,
  "processed_entries": 5232,
  "discovered_files": ["~/.claude/projects/<project-hash>/xxx.jsonl"],
  "parsed_files": ["~/.claude/projects/<project-hash>/xxx.jsonl"],
  "chunks": [
    {"file": ".evolution/chunks/chunk-00.md", "tokens_est": 90000, "turns": 22},
    {"file": ".evolution/chunks/chunk-01.md", "tokens_est": 90000, "turns": 25}
  ],
  "sync_state": {
    "version": "3.4.0",
    "last_full_sync": "2026-07-30T11:38:00",
    "last_incremental_sync": null,
    "project_hash": "<project-hash>",
    "files": { "...": { "processed_lines": 5232 } }
  }
}
```

> 字段定义见 `evolution-export.py` 第 894-903 行（`export_full` 返回值）。v3.8.0 起不再输出 `filtered_entries`，改为 `discovered_files`/`parsed_files` 用于一致性校验；`sync_state` 结构见 4.6。

### 4.2 路径发现机制

路径发现由两个函数完成：

**`compute_project_hash(project_root) -> str`**

计算 Claude Code 项目 hash。先将 `:\`（或 `:/`）替换为 `--`（处理 Windows 盘符），再将剩余的 `\` 和 `/` 替换为 `-`。

示例：`<project-root>` -> `<project-hash>`

> 源码：`evolution-export.py` 第 138-150 行

**`find_jsonl_file(project_root) -> list[Path]`**

发现项目对应的全部**顶层** JSONL 文件，返回列表（按修改时间升序，旧 -> 新）。

策略：
1. 用 `compute_project_hash` 计算项目 hash
2. 在 `~/.claude/projects/<hash>/` 下用 `glob("*.jsonl")` 匹配当前目录下的 `.jsonl` 文件（不进入 `subagents` 子目录，无需额外过滤）
3. 返回所有发现的 JSONL 文件列表；未找到时返回空列表

> 源码：`evolution-export.py` 第 153-179 行

> 注：旧版文档描述的 `generate_path_candidates`（多候选路径生成）在实际代码中已不存在，v3.8.0 改为单一 `compute_project_hash` 编码 + 目录直接匹配。

### 4.3 格式解析逻辑

**数据结构：`ConversationEntry`（dataclass）**

每条对话条目为一个 dataclass，字段：`session`、`line_no`（1-based 物理行号）、`timestamp`、`role`（`user`/`assistant`）、`content`（`list[ContentBlock]`）。`ContentBlock` 含 `type`（`text`/`thinking`/`tool_use`/`tool_result`）、`text`、`truncated`、`is_error`。

> 源码：`evolution-export.py` 第 90-109 行（`ContentBlock` + `ConversationEntry`）

**`parse_jsonl(file_path, start_line=0) -> Iterator[ConversationEntry]`**

流式解析 JSONL 文件，生成器每次 yield 一个 `ConversationEntry`。

- 签名：`(file_path, start_line=0)`，**无 `end_line` 参数**（旧文档的 `end_line` 已移除）
- 行号 **1-based**：`enumerate(f, start=1)`，从 `start_line` 之后开始解析
- 跳过空行、JSON 解析失败行、非 `user`/`assistant` 类型条目

> 源码：`evolution-export.py` 第 201 行（签名）、第 186-217 行（含 `_try_extract_entry` 辅助函数）

**`extract_conversation_content(entry, line_num) -> ConversationEntry`**

从单条 JSONL 条目中提取有意义的对话内容，过滤策略：

| 块类型 | 处理方式 |
|--------|----------|
| text | 完整保留 |
| thinking | 摘要（前 200 字 + 最后 100 字） |
| tool_use | 摘要（工具名 + 关键参数，经 `summarize_tool_input`） |
| tool_result | 摘要（前 500 字 + 错误信息后 200 字） |

> 源码：`evolution-export.py` 第 245-306 行

**`summarize_tool_input(tool_name, tool_input) -> str`**

按工具类型生成输入摘要：Bash 保留 `command`（截断 500 字）、Edit 保留 `file_path` + `old_string`/`new_string`（各 100 字）、Write 保留 `file_path` + `content`（200 字）、Read 保留 `file_path`、Agent 保留 `prompt`（300 字），其余 JSON 摘要（300 字）。仅在确实截断时追加 `...`。

> 源码：`evolution-export.py` 第 309-355 行

### 4.4 分页/截断支持

**`paginate_entries(entries, target_tokens=90000, max_tokens=200000, min_tokens=40000) -> list[list[ConversationEntry]]`**

将对话条目分页为多个 chunk。

规则：
1. 按时间顺序处理，先按轮次分组（`group_into_turns`）
2. 保持对话轮次完整性（不在轮次中间切分）
3. 目标大小 90K tokens，硬上限 200K tokens，最小 40K tokens
4. 单轮次超过 `max_tokens` 时调用 `split_large_turn` 拆分
5. **M1 修复**：最后一个 chunk 不足 `min_tokens` 时尝试合并到上一页，**合并前先检查不超 `max_tokens`**；超限则保留为独立 chunk
6. **`truncate_entry` 兜底**：单个 entry 超过 `max_tokens` 时，按 token 预算截断其 text 块（保留比例 + `[...截断...]` 标记）

> 源码：`evolution-export.py` 第 511-574 行（`paginate_entries`）、第 438-471 行（`truncate_entry`）、第 474-508 行（`split_large_turn`）

**`group_into_turns(entries) -> list[list[ConversationEntry]]`**

将条目按对话轮次分组：一个轮次 = 用户消息 + 后续所有 assistant 消息（直到下一个 user 消息）。

> 源码：`evolution-export.py` 第 415-435 行

**`estimate_tokens(text) -> int`**

粗略估算文本 token 数。

- 英文/代码：约 4 字符/token
- CJK/全角：约 1.0 字符/token（v3.3.0 由 1.5 下调，修正系统性偏低）
- **`is_wide_char()` 覆盖范围**（v3.8.0 扩展）：CJK 统一汉字、CJK 扩展 A、CJK 兼容汉字、日文假名、韩文音节、全角字符，并以 `unicodedata.east_asian_width()` 兜底判断 `W`/`F`
- 加权计算：`wide_tokens + narrow_tokens`

> 源码：`evolution-export.py` 第 362-399 行（`is_wide_char` + `estimate_tokens`）

### 4.5 chunk 文件格式

**chunk Markdown 格式（v3.8.0）：**

- 标题：`# 对话历史导出 - Chunk {idx}/{total}`
- 元信息块：时间范围、估算 tokens、对话条目数
- 每条 entry：`## [Entry N] {timestamp}` + `### {Role}:`
- **所有原始文本用 fenced code 包裹**（`_wrap_code_block`），防止 markdown 注入（M11）；fence 长度根据文本中最长反引号序列动态确定（`_fence`，至少 3 个反引号）
- 块类型标签：`[text]`、`[thinking]`、`[tool_result]`（错误加 `(error)`）；`tool_use` 不加标签直接包裹

> 旧格式 `## [Turn N]` + `### User:` + 原始文本已废弃；v3.8.0 改为 `## [Entry N]` 并用 fenced code 包裹所有文本。

示例：

````markdown
# 对话历史导出 - Chunk 0/5

> 时间范围：2026-06-29 14:41 ~ 2026-07-01 10:30
> 估算 tokens：~90,000
> 对话条目：15

---

## [Entry 1] 2026-06-29 14:41:58

### User:

[text]
```text
你觉得这个项目从第一原则来看，有什么问题？
```

---

## [Entry 2] 2026-06-29 14:42:30

### Assistant:

[thinking]
```text
从第一性原理来看，这个项目有几个关键问题需要考虑...
```

[tool_use]
```text
[Tool: Bash]
Command: ls -la <project-root>/
```

[text]
```text
我现在来分析这个项目的结构...
```

---
````

> 源码：`evolution-export.py` 第 596-641 行（`turn_to_markdown`）、第 581-593 行（`_fence` + `_wrap_code_block`）

### 4.6 状态管理

**sync-state.json 完整结构（v3.8.0）：**

> 注：`version` 字段记录 sync-state 数据结构 / 导出逻辑的版本号（当前 3.4.0），用于后续版本的旧状态迁移；它与文档版本号语义独立。

```json
{
  "version": "3.4.0",
  "last_full_sync": "2026-07-30T11:38:00",
  "last_incremental_sync": "2026-07-30T15:00:00",
  "project_hash": "<project-hash>",
  "files": {
    "~/.claude/projects/<project-hash>/xxx.jsonl": {
      "path": "~/.claude/projects/<project-hash>/xxx.jsonl",
      "sha256": "abc123...",
      "mtime": 1753867200.0,
      "total_lines": 5232,
      "processed_lines": 5232,
      "processed_bytes": 14227502,
      "last_event_timestamp": "2026-07-30T03:39:21.771Z"
    }
  }
}
```

字段说明：

| 字段 | 说明 |
|------|------|
| `version` | 数据结构版本号 |
| `last_full_sync` | 最近一次全量导出时间（ISO，首次为 `null`） |
| `last_incremental_sync` | 最近一次增量导出时间（ISO，未增量为 `null`） |
| `project_hash` | `compute_project_hash` 计算的项目 hash |
| `files` | 按文件路径键的 `FileInfo` 字典 |
| `files[k].sha256` | 文件内容 SHA256 |
| `files[k].mtime` | 文件修改时间 |
| `files[k].total_lines` | 文件物理行总数 |
| `files[k].processed_lines` | 已处理的最后一条 entry 的真实行号（增量游标） |
| `files[k].processed_bytes` | 已处理字节数 |
| `files[k].last_event_timestamp` | 最后一条 entry 的时间戳 |

> 旧结构（`last_sync` / `file_info` / `stats` / `export_history`）已废弃。不再维护 `export-log.json`，导出统计由调用方（Sub Agent）汇总。

> 源码：`evolution-export.py` 第 648-679 行（`file_info_to_dict` / `state_to_dict` / `_empty_state`）、第 112-131 行（`FileInfo` / `SyncState` dataclass）、第 682-727 行（`load_sync_state`，含 schema 校验）

### 4.7 Windows 兼容性

**关键兼容性处理：**

1. **路径分隔符**：用 `pathlib.Path` / `os.path` 拼接，不硬编码 `/` 或 `\`
2. **home 目录**：用 `Path.home()` 定位 `~/.claude/projects`
3. **编码**：文件读写显式指定 `encoding='utf-8'`，并用 `errors='replace'` 容错
4. **stdout/stderr 编码**：Windows 下 `_reconfigure_stdio()` 强制 stdout/stderr 使用 UTF-8，避免 GBK 编码崩溃
5. **Python 路径**：不假设 `python3`，使用 `python`（Windows 默认）
6. **文件锁跨平台**：Windows 用 `msvcrt.locking`，Linux/macOS 用 `fcntl.flock`（见 4.9）

> 源码：`evolution-export.py` 第 1059-1065 行（`_reconfigure_stdio`）、第 750-800 行（跨平台文件锁）

### 4.8 错误处理与降级

**错误处理矩阵：**

| 错误场景 | 处理策略 |
|----------|----------|
| 项目路径不存在 / 非字符串 | `--mode full/incremental` 前置 `os.path.isdir` 检查 + `_validate_str` 抛 `ValueError` |
| JSONL 文件不存在 | `find_jsonl_file` 返回空列表，导出返回 `{"status":"error","message":"未找到 JSONL 文件"}` |
| JSONL 单行解析失败 | 跳过坏行，打印 `[WARN]` 到 stderr |
| sync-state.json 损坏 / 类型不符 | `load_sync_state` 回退到空状态（`_empty_state`） |
| 文件消费不一致 | `discovered_files != parsed_files` 时返回错误（见 4.9） |
| 获取文件锁超时 | `file_lock` 抛 `TimeoutError`（默认 120s） |
| 未捕获异常 | `main` 兜底捕获，输出结构化 JSON 错误 + `[ERROR]` 到 stderr，退出码 1 |

> 源码：`evolution-export.py` 第 807-811 行（`_validate_str`）、第 682-727 行（`load_sync_state` 容错）、第 1109-1118 行（`main` 兜底异常）

> 注：旧文档的 `export_with_fallback` 多级降级链（token 超限逐级丢弃内容）在实际代码中不存在；实际通过 `paginate_entries` 分页 + `truncate_entry` 截断兜底控制单 chunk 大小，无需运行时降级。

### 4.9 验证与并发安全（v3.8.0 新增）

v3.8.0 引入两项正确性保障：

**1. 文件消费一致性校验**

全量 / 增量导出在解析完所有 JSONL 文件后，校验 `discovered_files`（`find_jsonl_file` 发现的）与 `parsed_files`（实际解析的）集合相等。不一致时返回 `status=error`（含 `discovered_files` / `parsed_files` 字段），避免静默漏处理文件。

> 源码：`evolution-export.py` 第 858-865 行（`export_full`）、第 976-983 行（`export_incremental`）

**2. 跨进程文件锁 `file_lock`**

导出全程持有 `.evolution/chunks/export.lock`，防止多个进程并发导出导致 `sync-state.json` 损坏或 chunk 文件冲突。

- Windows：`msvcrt.locking`（`LK_NBLCK` 非阻塞尝试，循环至超时）
- Linux/macOS：`fcntl.flock`（`LOCK_EX | LOCK_NB`）
- 超时默认 120s（`LOCK_TIMEOUT`），超时抛 `TimeoutError`
- `contextmanager` 保证进程退出时自动释放

> 源码：`evolution-export.py` 第 750-800 行（`file_lock`）、第 83 行（`LOCK_TIMEOUT` 常量）、第 830 / 923 / 1041 行（三处 `with file_lock(...)` 调用点）

---

## 5. 成本估算

### 5.1 Token 成本

**全量导出（首次）：**

| 项目 | Token 数 | 说明 |
|------|----------|------|
| JSONL 解析 + 分页 | 0 | Python 本地执行，不消耗 LLM token |
| chunk 文件内容（实际消耗） | ~371K 估算 / 实际约 600K-900K | 5-6 个 chunk × 90K 估算（140-150K 实际） |
| 分析指令（每 chunk） | ~8K | 提取知识的标准 prompt |
| 知识库读取（每 chunk） | ~10K | kb-index.md + 2-3 个详情文件 |
| 知识库写入（每 chunk） | ~10K | 写入提取的知识 |
| **单 chunk 总消耗** | ~152K（按估算口径计） | 内容 + 指令 + 读写 |
| **全量总消耗** | ~760K-912K | 5-6 chunks x ~152K |

**增量导出（日常）：**

| 项目 | Token 数 | 说明 |
|------|----------|------|
| 增量内容（假设 100 轮新对话） | ~43K | 通常 1 个 chunk |
| 分析指令 + 知识库读写 | ~28K | 同上 |
| **增量总消耗** | ~71K | 1 chunk |

**成本估算（按 Claude Sonnet 定价 $3/M input, $15/M output）：**

| 场景 | Input Token | Output Token | 成本 |
|------|-------------|--------------|------|
| 全量导出（首次） | ~651K-803K | ~109K | ~$3.56 |
| 增量导出（每次） | ~55K | ~16K | ~$0.40 |
| 月度（1 次全量 + 4 次增量） | - | - | ~$5.16 |

### 5.2 时间成本

| 场景 | 耗时 | 说明 |
|------|------|------|
| Python 脚本执行（全量） | ~3 秒 | 解析 14MB JSONL |
| Python 脚本执行（增量） | ~1 秒 | 解析新增行 |
| Sub Agent 分析（每 chunk） | ~60-90 秒 | 读取 + 分析 + 写入（90K 估算 / 140-150K 实际内容） |
| 全量导出（5-6 chunks） | ~5-9 分钟 | 串行分析 |
| 增量导出（1 chunk） | ~1-2 分钟 | 单次分析 |
| 总全量导出 | ~5-10 分钟 | 含脚本 + 分析 |
| 总增量导出 | ~1-2 分钟 | 含脚本 + 分析 |

### 5.3 存储成本

| 项目 | 大小 | 说明 |
|------|------|------|
| chunk 临时文件 | ~2 MB | 5-6 个 chunk x ~300-400KB（90K 估算 tokens，CJK 密集内容约 1.0 字符/估算 token） |
| sync-state.json | ~2 KB | 状态文件 |
| 知识库增长（全量） | ~10-20 KB | 8 个 .md 文件 |
| 知识库增长（每次增量） | ~2-5 KB | 新增条目 |
| **总存储开销** | ~2 MB | 主要是 chunk 临时文件 |

---

## 6. 实施步骤

### 6.1 实施顺序

```
Phase 1: 核心脚本（evolution-export.py）
  ├── 1.1 路径发现机制
  ├── 1.2 JSONL 解析器
  ├── 1.3 内容过滤 + 提取
  ├── 1.4 分页器
  ├── 1.5 chunk 文件输出
  └── 1.6 命令行接口（--mode full/incremental/status/cleanup）

Phase 2: 状态管理
  ├── 2.1 sync-state.json 读写
  ├── 2.2 增量游标逻辑（per-file processed_lines）
  └── 2.3 文件锁与一致性校验（v3.8.0）

Phase 3: SKILL.md 集成
  ├── 3.1 更新 SKILL.md 添加 export 命令
  ├── 3.2 定义 Sub Agent 分析指令模板
  └── 3.3 定义知识提取 prompt 模板

Phase 4: 分析协调
  ├── 4.1 Sub Agent 逐页分析流程
  ├── 4.2 知识去重合并逻辑
  └── 4.3 kb-index.md 自动更新

Phase 5: 测试与优化
  ├── 5.1 全量导出测试
  ├── 5.2 增量导出测试
  ├── 5.3 边界情况测试
  └── 5.4 性能优化
```

### 6.2 验收标准

| 验收项 | 标准 | 验证方法 |
|--------|------|----------|
| 路径发现 | 能正确发现当前项目的 JSONL 文件 | `python evolution-export.py --mode status` |
| 全量导出 | 生成 5-6 个 chunk 文件，总 token ~371K（估算口径） | 检查 `.evolution/chunks/` 目录 |
| 内容过滤 | 丢弃 metadata 条目，保留 user/assistant | 检查 chunk 文件内容 |
| 分页正确性 | 每个 chunk 在 40K-200K token 之间 | 检查 chunk 文件头部的 token 估算 |
| 增量识别 | 正确识别新增行数 | 修改 JSONL 后运行增量导出 |
| 状态管理 | sync-state.json 正确更新 | 检查 JSON 内容 |
| 知识提取 | 从对话中提取有意义的知识 | 检查知识库文件变化 |
| 去重 | 不产生重复条目 | 对比知识库前后内容 |
| Windows 兼容 | 在 Git Bash + Windows 上正常运行 | 在 Windows 11 上测试 |
| 错误处理 | 各种异常情况有合理处理 | 模拟错误场景 |

### 6.3 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| JSONL 格式变化 | 中 | 高 | 解析器容错设计，跳过无法解析的行 |
| 路径编码不匹配 | 低 | 高 | compute_project_hash 编码匹配 + 未找到时返回空列表并警告 |
| Token 估算不准 | 高 | 中 | 留 20% 余量（目标 90K，上限 200K） |
| 知识提取质量低 | 中 | 高 | 人工审核机制（[D] 标记）+ 优化 prompt |
| Sub Agent 上下文溢出 | 低 | 高 | 分页大小保守估计 + 降级模式 |
| 多 session 文件 | 中 | 中 | 逐个处理，各自维护游标 |
| Python 环境缺失 | 低 | 高 | 脚本仅用标准库，无第三方依赖 |

---

## 7. Sub Agent 分析指令模板

### 7.1 全量分析指令

```markdown
# Evolution 知识提取任务

你正在分析 Claude Code 的对话历史，为 Evolution 知识库提取知识。

## 任务

读取以下 chunk 文件，分析其中的对话内容，提取有价值的知识：

1. 读取 chunk 文件：{chunk_file_path}
2. 读取知识库索引：evolution/knowledge-base/kb-index.md
3. 根据索引判断需要读取哪些知识库详情文件（1-2个）
4. 分析 chunk 中的对话，提取以下类型知识：
   - 关键事实（facts.md）：环境配置、技术选型、依赖关系
   - 踩坑记录（pitfalls.md）：报错 + 原因 + 解决方案
   - 状态变更（state.md）：项目阶段、里程碑
   - 学习要点（growth-notes.md）：用户可学习的知识点
   - Prompt 改进（prompt-improvements.md）：提问优化建议
   - 对齐项（alignment.md）：需用户确认的事项
   - 决策记录（decisions.md）：技术决策 + 理由
5. 与已有知识去重
6. 将新知识写入对应的知识库文件（标记 [D]）
7. 更新 kb-index.md

## 规则

- 所有新条目标记为 [D]（draft）
- 格式：`### [D] 条目标题`
- 跳过无意义的对话（如闲聊、测试）
- 重点关注：错误信息、解决方案、技术决策、用户偏好
- 如果与已有条目冲突：旧条目标记 [X]，新条目以 [D] 写入
- 不要修改 [V] 条目（除非标记为 [X]）

## 输出

返回摘要：
- 提取的知识条目数（按类别）
- 发现的冲突数
- 建议用户审核的条目
```

### 7.2 增量分析指令

```markdown
# Evolution 增量知识同步任务

你正在分析 Claude Code 的新增对话，为 Evolution 知识库增量更新知识。

## 任务

1. 读取增量 chunk 文件：{chunk_file_path}
2. 读取知识库索引：evolution/knowledge-base/kb-index.md
3. 根据索引判断需要读取哪些知识库详情文件
4. 分析新增对话，提取新知识
5. 与现有知识库去重合并
6. 更新知识库文件和索引

## 规则

（同全量分析规则）

## 特别注意

- 这是增量同步，已有知识可能已经存在
- 重点检查去重，避免重复写入
- 如果发现已有条目需要更新（如状态变更），直接更新
- 返回增量摘要
```

---

## 8. 完整执行流程示例

### 8.1 全量导出流程

```
用户输入：/evolution-init
    │
    ▼
主 Agent：触发 Sub Agent
    │
    ▼
Sub Agent 执行：
    │
    ├─ Step 1: 运行 Python 脚本
    │  $ python .claude/skills/evolution/evolution-export.py --mode full --project-path <project-root>
    │  → 输出 JSON：
    │    {
    │      "status": "success",
    │      "chunks": [
    │        {"file": ".evolution/chunks/chunk-00.md", "tokens_est": 90000},
    │        {"file": ".evolution/chunks/chunk-01.md", "tokens_est": 90000},
    │        {"file": ".evolution/chunks/chunk-02.md", "tokens_est": 90000},
    │        {"file": ".evolution/chunks/chunk-03.md", "tokens_est": 90000},
    │        {"file": ".evolution/chunks/chunk-04.md", "tokens_est": 11000}
    │      ],
    │      "sync_state": {...}
    │    }
    │
    ├─ Step 2: 逐页分析
    │  For each chunk:
    │    - 读取 chunk 文件
    │    - 读取 kb-index.md
    │    - 按需读取知识库文件
    │    - 分析对话内容
    │    - 提取知识
    │    - 写入知识库
    │    - 更新索引
    │
    ├─ Step 3: 更新同步状态
    │  - sync-state.json 已由 Python 脚本更新
    │
    └─ Step 4: 返回摘要
       "全量导出完成：
        - 处理 5,232 条记录
        - 分析 5-6 个分页
        - 提取 23 条知识（8 事实 / 5 踩坑 / 3 状态 / 4 学习 / 1 Prompt / 2 决策）
        - 全部标记为 [D]
        - 建议审核：..."
    │
    ▼
主 Agent：显示摘要给用户
```

### 8.2 增量导出流程

```
用户输入：/evolution
    │
    ▼
主 Agent：触发 Sub Agent
    │
    ▼
Sub Agent 执行：
    │
    ├─ Step 1: 运行 Python 脚本
    │  $ python .claude/skills/evolution/evolution-export.py --mode incremental --project-path <project-root>
    │  → 输出 JSON：
    │    {
    │      "status": "success",
    │      "mode": "incremental",
    │      "new_entries": 150,
    │      "chunks": [
    │        {"file": ".evolution/chunks/chunk-inc-00.md", "tokens_est": 35000}
    │      ]
    │    }
    │
    ├─ Step 2: 分析增量 chunk
    │  - 读取 chunk-inc-00.md
    │  - 读取 kb-index.md
    │  - 分析 + 提取 + 去重 + 写入
    │
    └─ Step 3: 返回摘要
       "增量同步完成：
        - 新增 150 条记录
        - 提取 3 条新知识
        - 更新 2 条已有知识
        - 建议审核：..."
    │
    ▼
主 Agent：显示摘要给用户
```

---

## 9. 关键设计决策记录

### 9.1 为什么用 Python 脚本而不是让 AI 直接读 JSONL？

| 方案 | 优点 | 缺点 |
|------|------|------|
| AI 直接读 JSONL | 无需脚本 | 14MB 文件远超上下文；JSON 噪声多；无法分页 |
| Python 脚本预处理 | 精确控制过滤/分页；不消耗 token；可复用 | 需要维护脚本 |

**决策：Python 脚本预处理。** 原因：14MB / 716K tokens 的原始数据无法直接放入 1M 上下文窗口（合成任务有效上下文仅 200-300K），必须预处理。

### 9.2 为什么分页目标是 90K 而不是更接近 1M？

- 1M 是 sub agent 的原始上下文窗口，但合成/分析任务的有效上下文仅约 200-300K（参见"关键变更"一节的"Lost in the Middle"研究）
- 有效上下文 200-300K 需要扣除：分析指令(~8K) + 知识库读取(~10K) + 知识库写入(~10K) + 输出空间(~20K) + 模型内部开销(~50K) ≈ 98K
- chunk 内容上限 = 有效上下文（200-300K） - 其他分配（98K） = 102-202K，取 ~90K 作为目标（v3.3.0 考虑 CJK 系数修正后）
- 90K 估算 × 1.68（CJK 系数修正）≈ 150K 实际使用，约占 1M 窗口的 15%，远在安全区内
- 硬上限设为 200K（合成有效区上限），确保单 chunk 不越过注意力退化拐点
- **宁可基于有效上下文保守取值，也不要依赖原始窗口大小**

### 9.3 为什么按对话轮次分页而不是按固定行数？

- 固定行数可能在对话中间截断，丢失上下文
- 按轮次分页保持语义完整性
- 一个轮次 = 一个完整的 user-assistant 交互
- Sub Agent 分析时能看到完整的对话上下文

### 9.4 为什么用 line_number 而不是 timestamp 作为增量游标？

- timestamp 可能不唯一（同一秒多条记录）
- timestamp 可能乱序（极少数情况）
- 行号是严格递增的，唯一且有序（实际字段为 `FileInfo.processed_lines`，按文件记录最后一条 entry 的真实行号）
- 单一行号在文件被整体重写时可能失效，所以同时记录 `sha256` / `mtime` / `last_event_timestamp` 作为校验（见 4.6）

### 9.5 为什么不过滤掉 tool_use 和 tool_result？

- tool_use 包含执行的命令、编辑的文件内容，是踩坑记录的重要来源
- tool_result 包含命令输出、错误信息，是关键事实的来源
- 完全过滤会丢失大量有价值的知识
- 采用摘要策略（保留前 N 字 + 错误信息）在信息保留和 token 节省之间取得平衡

---

## 10. 未来优化方向

| 优化项 | 描述 | 优先级 |
|--------|------|--------|
| 并行分析 | 多个 chunk 并行分析（多个 sub agent） | 中 |
| 智能过滤 | 根据内容价值动态决定保留比例 | 中 |
| 向量检索 | 对知识库建立向量索引，支持语义搜索 | 低 |
| 自动触发 | 检测到 N 轮新对话后自动触发增量导出 | 低 |
| 多项目支持 | 支持同时管理多个项目的对话历史 | 低 |
| 可视化报告 | 生成导出分析报告（HTML/Markdown） | 低 |
| 知识衰减 | 旧知识自动降权，过时知识标记 [X] | 中 |

---

**文档结束**
