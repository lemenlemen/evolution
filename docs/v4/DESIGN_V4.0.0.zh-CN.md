# Evolution V4.0.0 设计文档（总纲）

> ⚠️ **回退横幅（v4.1.2 补记）**：本文档是 V4.0.0 设计历史稿。**知识层设计已在 v4.1.0 回退**——
> `[P]` 隔离 / pending.md、四级状态模型（`[P]/[D]/[V]/[X]/[C]/blocked`）、`kb-manager.py` 唯一写入口、
> 知识生命周期、敏感闸门均**未在当前实现中保留**；状态标记已恢复为 `[D]/[V]/[X]` 三级。
> §7 迁移模式的 `migration.trust_committed` 逃逸阀亦**未实现**（代码中无产生 migration 批次的 CLI 路径，
> `config.yaml` 无 `migration:` 配置节），仅作未来规划。
> ⚠️ `state-version-newer` 拒绝机制**未实现**（代码无版本比较逻辑，未来版本状态会被静默降级）。仅作未来规划。
> 引擎层设计（双游标、批次 commit 协议、完整性校验、原子写入、流式导出）仍有效并在用。
> 当前系统行为以 `CLAUDE.md` + `.claude/skills/evolution/` + `docsV3/VERSION_HISTORY.md` 为准。

> **版本**：4.0.0（设计稿 v2.2，整合独立评审；v2.2 修订 2026-08-22）
> **日期**：2026-08-16
> **性质**：已实施
> **实施日期**：2026-08-24
> **依据**：对抗性审核（54 agents，39 条确认发现）+ VERSION_HISTORY 中 v4.0.0 规划（清理机制、容量监控、四级状态模型、证据类型分类、主动审核流程）+ 独立评审
> **细节文档**：
> - [同步引擎层设计（草稿）](./design-v4-engine.md)
> - [知识管理层设计（草稿）](./design-v4-knowledge.md)
>
> **修订记录**：
> - v2（2026-08-16）：整合独立评审——新增审计覆盖矩阵（§14.3）、修复 6 项方案缺陷（§14.4）、纳入 13 条遗漏发现（§14.3 标 🔴 项）、更新实施计划（§14.5）。**决策：完整实施，不做成本削减**（用户指令：不在乎成本，关键准确）
> - v2.1（2026-08-21）：二轮评审修复 8 项必须问题——§14.3 覆盖统计数字（N-1）、F-2 回滚手册按实测行为重写（N-5）、F-6 路径锚定公式修正（N-8）、F-3 CLI 落点（N-4）；引擎层 N-2 resume 协议、N-3 迁移/failed 批次恢复路径；知识层 N-6 blocked 打码形态、N-7 系统性对齐 F-5/#23/manifest schema/正则统一
> - v2.2（2026-08-22）：M0 遗漏修复包批次 2 执行——#23 删除幻影命令、#24 路径锚定文档化（代码 M1 E4）、#25 当前会话过滤语义定案、#30 手动触发表述修正、#32 token 口径统一、#39 README 知识库维护章节；§14.3/§14.5 同步更新执行状态

---

## 1. 背景与目标

### 1.1 为什么是 V4.0.0（MAJOR）

对抗性审核确认 39 个真实问题，其中 3 个 Critical 会导致**数据永久丢失**。修复需要改变行为语义（双游标、commit 协议、[P] 隔离），按语义化版本规则属 **MAJOR** 升级。

### 1.2 设计目标（四不）

| 目标 | 对应防线 |
|------|---------|
| **不丢数据** | 双游标 + sha256 完整性校验 + 原子写入（引擎层） |
| **不崩解析** | 解析防御 + 流式化 + 时间排序（引擎层） |
| **不积垃圾** | [P] 隔离 + 知识生命周期 + 事务锁（知识层） |
| **不泄敏感** | 敏感扫描闸门 + 隐私知情（知识层） |

### 1.3 设计原则（延续 V3）

1. 所有操作由 sub agent 后台执行，持锁事务化
2. 人类只做**最小成本的批量审核**
3. **默认只归档、永不自动删除**知识正文
4. 失败可重试、幂等；绝不静默丢数据、绝不静默回退

---

## 2. 版本与数据格式策略

| 项 | 值 | 说明 |
|----|-----|------|
| 系统版本 | **4.0.0** | MAJOR（行为改变） |
| sync-state 数据格式 | **3.4.0 → 3.5.0** | 字段改名 + 新增，loader 可迁移 |
| 知识库条目格式 | 新增 `kb-meta:` 元数据行 | 机器可解析，向后兼容 |
| 迁移模式 | 保守默认 + 逃逸阀 | 详见 §7 |

**版本回退保护**：`version > VERSION`（用旧脚本读新状态）→ 拒绝修改，只读可用。绝不按旧 schema 解释新状态。

---

## 3. 总体架构（V4）

```
┌─────────────────────────────────────────────────────────────┐
│                      主 Agent（用户交互层）                    │
│   /evolution · /evolution-init · /kb-review · /kb-status    │
└──────────────────────────┬──────────────────────────────────┘
                           │ 触发 + receipt 回报协议
┌──────────────────────────▼──────────────────────────────────┐
│              Sub Agent（分析协调层）                          │
│  ① 引擎：export → 批次 → 逐 chunk 分析                        │
│  ② 知识：敏感扫描 → .kb.lock 事务 → pending 隔离 → 状态迁移     │
│  ③ 体检：生命周期扫描（只读）→ 报告                           │
│  ④ 完成：--mode commit 回报 receipt（批次闭环）                │
└──────────┬───────────────────────────────┬──────────────────┘
           │                               │
┌──────────▼──────────┐        ┌───────────▼──────────────────┐
│  同步引擎层（v3.5.0） │        │  知识管理层（V4）              │
│  · 双游标+批次清单     │        │  · [P]隔离区 pending.md       │
│  · sha256 完整性校验  │        │  · 四级状态+[C]+blocked        │
│  · 原子状态写入       │        │  · .kb.lock 事务协议           │
│  · 流式解析+全局排序  │        │  · 生命周期归档 archive/       │
│  · success/partial/ │        │  · 敏感扫描闸门                │
│    failed 协议       │        │  · kb-manager.py              │
└─────────────────────┘        └──────────────────────────────┘
```

**信任边界**：脚本无法验证知识已入库——commit 是 sub agent 的声明，可靠性由三层兜底：① receipt 回报协议；② 新条目一律 [P] 隔离等人工审核；③ 批次重生成幂等。

---

## 4. 同步引擎层（细节见 design-v4-engine.md）

### 4.1 双游标 + 批次清单（修复 Critical 1）

**核心变化**：`processed_lines` → 拆分为 `exported_lines`（脚本已导出）与 `committed_lines`（sub agent 确认入库）。

```
增量导出起点 = committed_lines + 1        （不是 exported_lines + 1）
```

**批次状态机**：

```
导出完成 ──▶ exported ──commit──▶ committed（幂等）
                │
           resume/start
                ▼
           analyzing ──commit──▶ committed
                │
          重试超限/显式失败
                ▼
            failed ──重生成（新批次）──▶ exported
```

- 未提交批次（chunk 完好）→ 下次同步 `action_hint=analyze_pending`，**不重新导出**
- 失败批次（chunk 缺失）→ 按 `line_ranges` **精确重生成**，绝不跳过
- 新增 `--mode commit --batch-id <id>` → 返回带 `receipt_hash` 的收据
- 批次修剪：committed 批次保留最近 20 个，游标不受影响

### 4.2 文件完整性校验（修复 Critical 2）

**决策表**：

| 信号 | hash | 判定 | 处置 |
|------|------|------|------|
| mtime+size 未变 | 不计算 | 快速路径 | 正常增量 |
| 变化 | 相同 | 仅 mtime 抖动 | 刷新元数据 |
| 变化 | 不同，size 变小 | **截断/轮换** | 该文件全量重导 + WARN |
| 变化 | 不同，size 变大 | **替换/重写** | 保守全量重导 + WARN |
| state 有、磁盘无 | — | 删除 | 批次 failed(deleted)，files 移除 |
| 磁盘有、state 无 | — | 新文件 | 从行 1 全量导出 |

**重导交互**：重导文件置 `committed_lines=0`，建新批次，旧 in-flight 批次 `failed(superseded)`。只重导变动文件（避免全量重分页导致所有 chunk 边界漂移 + sub agent 全量重分析 ~$4）；强一致模式由 config 开关 `full_repaginate_on_integrity`（默认 false）。

### 4.3 原子状态写入（修复 Critical 3）

```
tmp 写 → flush → fsync → os.replace（原子）→ 目录 fsync（POSIX）
```

- 写前保留 `.json.bak`（恢复点）
- **load 不再静默回退空状态**，三级恢复链：`.bak` 恢复（WARN）→ 显式失败 `state-corrupt`（提示 `--mode full`）
- chunk 文件同样原子写
- `CLEANUP_PATTERNS` 增加 `*.tmp`；保留 `.bak`/`.corrupt-*` 不进清理

### 4.4 解析防御与流式化（健壮性）

| 问题 | 修复 |
|------|------|
| null/[]/123 行 AttributeError 整次崩溃 | `isinstance(entry, dict)` 防御 + 三异常整体捕获 + `ParseStats` 计数；坏行占比 >50% → partial + WARN |
| token 估算偏低 1.3~2 倍 | `estimate_safety_factor: 1.5` 作用于分页决策 + 字符数硬守卫 `max_chunk_chars: 800K` |
| 全量导出 OOM | 两遍扫描 + k-way 归并流式导出（O(1) 内存） |
| 超大轮次 chunk 时间乱序 | 遇大轮次**无条件先 flush** 当前 chunk（根因：小尾巴被拖到大轮次 chunk 之后） |
| 多 session 聚合乱序 | 全局 `(timestamp, file_index, line_no)` 排序；轮次分组 **session 感知**（防止跨 session 拼轮） |

### 4.5 命令与可观测性协议

- **退出码**：0=success，1=failed（中止），2=partial（有数据质量警告）
- **warnings 四要素**：`code / file / detail / action`
- **错误信息规范**：`[现象] [原因] [影响] [恢复]`
- **主↔sub 协议**：sub agent 必须回报 commit receipt，主 agent 摘要缺 receipt 即判定未完成

---

## 5. 知识管理层（细节见 design-v4-knowledge.md）

### 5.1 状态模型与 [P] 隔离（修复自强化闭环）

**关键决策**：

| 决策 | 内容 |
|------|------|
| 新增 `[P]` pending | 所有 AI 提取条目 100% 首落独立 `pending.md` 隔离文件，正常读取路径**永远读不到** |
| 保留 `[D]` 改语义 | `[D]` = 已人工审阅但证据不足；旧语义（AI 提取未验证）废除 |
| `[C]` 是叠加标记 | 冲突双方并列保留原文件，标题标 [C]，进仲裁队列 |
| `blocked=secret` | 敏感扫描命中，永驻隔离区 |

**状态机（合法转移）**：

```
auto_extract ─▶ [P] ─审核─▶ [D] ─强证据─▶ [V]
                  │ ├驳回─▶ [X]            ├时效─▶ 复验提示（不自动降级）
                  │ └冲突─▶ [C]（双方并列） ├败诉─▶ [X]
                  └超期─▶ 归档（恢复回 [P]）
```

**写入红线**：`[P]/[D]/[C]` 一律不得淘汰 `[V]`。

**证据类型绑定**（收紧 [V] 语义）：

| 证据 | 置信 | 可否支撑 [V] |
|------|------|-------------|
| `tool_output` | 0.9 | 可（记 scope，365 天复验） |
| `user_explicit` | 0.9 | 可（须是审核流程中的明确确认） |
| `external_doc` | 0.7 | 可（记文档名版本） |
| `conversation_inference` | 0.5 | **否**（只能到 [D]） |
| `auto_extract` | 0.3 | **否**（只能到 [P]） |

**条目格式**：标题 + `> kb-meta: id/state/file/created/reviewed/source/confidence/evidence/last_used/scope/sensitive/archived_at` 元数据行（机器可解析）。

### 5.2 知识生命周期（生老死）

| 阈值（config） | 默认 | 动作 |
|----------------|------|------|
| `pending_stale_days` | 30 | [P] 超期 → stale 标记 → 归档 |
| `draft_stale_days` | 90 | [D] 闲置 → 降级提示 |
| `draft_archive_days` | 180 | [D] 仍闲置 → 自动归档 |
| `verify_refresh_days` | 365 | [V] → 复验提示（不自动降级） |
| `index_max_lines` | 500 | kb-index 超限 → 确定性重生成压缩（目标 <300 行） |
| `archive_policy` | keep | **只归档不删除** |

- 归档：`archive/YYYY-MM/<文件>-<月>.md` + manifest JSON，`/kb-restore <id>` 可恢复（一律回 [P] 重审）
- **索引是派生数据**：体检扫描 id 级校验，不一致时从详情文件重生成（自愈）
- chunk GC：只删 manifest 中且不在最近 3 轮批次内的文件（精确名匹配，禁止 glob 通配删除）；孤儿仅报告不删除

### 5.3 知识库事务与并发

- `.kb.lock`：复用 file_lock 机制（30s 超时，进程退出自动释放），锁内自报身份（pid+操作）
- **写入事务**：取锁 → 读现状 → 内存合并（去重→冲突判定→状态转移）→ 逐文件临时副本 → 校验（可解析/索引一致性/meta 合法性）→ 原子替换（详情文件 → pending.md → **索引最后**）→ 释放锁
- 崩溃安全：最坏情况 = 索引滞后（派生数据，体检自愈）；`.<name>.kb.bak` 滚动回滚点
- 只读不需要锁（原子替换保证不撕裂）

### 5.4 命令协议与主动审核

| 命令 | 用途 | 状态 |
|------|------|------|
| `/evolution` | 增量同步 + 体检扫描 + 审核队列提示 | 改 |
| `/evolution-init` | 初始化（产出全部落 pending） | 改 |
| `/kb-review` | 批量审核：pending + 遗留 [D] + [C] 仲裁 | **新增** |
| `/kb-status` | 知识库健康报告 | **新增** |
| `/kb-archive` | 手动归档 | **新增** |
| `/kb-restore <id>` | 从归档恢复（回 [P] 重审） | **新增** |

**审核 UX（最小成本）**：
- 一屏预览（每行 1 条：id/状态/来源/置信/摘要；sensitive 只显 id）
- 批量指令：`all v` / `v 1-5` / `d 2` / `x 4` / `c 3 选 1`
- 默认动作按证据推荐（tool_output → v，conversation_inference → d）
- **零审核路径**：什么都不做 → 30 天 stale → 自动归档（不强迫、不膨胀）
- /evolution 摘要末尾附提示行，永不自动执行审核

### 5.5 隐私与安全

**三道防线**：

```
防线 1（导出层）：chunk 敏感模式扫描（N-12：归属为导出脚本 evolution-export.py，非 sync 步骤），命中只报告（文件+行号）
防线 2（写入层）：候选含敏感模式 → 不写入详情，blocked 条目仅以打码形态落 pending（模式类型+来源定位），原始值零落盘
                  （出路：打码重提交 <REDACTED:api_key> / 驳回）
防线 3（知情层）：README 隐私章节 + .gitignore 排除 .evolution/
```

敏感模式清单：github_token / anthropic_api_key / openai_api_key / aws_access_key / slack_token / private_key / generic_secret_assignment / local_path（**默认关闭**，N-10）/ contact_info（默认关闭）。

---

## 6. 两层衔接点

| 衔接 | 机制 |
|------|------|
| 批次 manifest ↔ chunk GC | 引擎层 sync-state 记录批次 → 知识层体检按 manifest 精确清理 |
| commit 信任边界 ↔ [P] 兜底 | 脚本不验证入库 → 新条目一律 [P] 等人工审核 |
| 体检扫描 ↔ 同步 | 步骤 0.5 顺带执行（只读 + 状态更新，<2s），归档动作在下次持锁写入时执行 |
| 完整重导 ↔ 去重 | 重导产生重复候选 → dedup 合并（重复≠冲突，语义矛盾进仲裁） |

---

## 7. 迁移路径

### 7.1 状态文件（3.2.1 / 3.4.0 → 3.5.0）

> 实测：线上 `version` 标签是 "3.2.1" 但结构已是 v3.4.0 —— 两个标签必须同函数处理。

```
exported_lines = 旧 processed_lines
committed_lines = 0        ← 保守：旧游标在分析前已推进，不可信
迁移批次：引用遗留 chunk-*.md（或 failed(migration-unverified) 触发重生成）
```

- **默认**：迁移后下一次增量对全量历史重新分析一次（~$4，KB 去重后新增少）——安全、有界
- **逃逸阀** `migration.trust_committed: true`：确认知识库完整时跳过重分析，迁移报告标 `migration_mode: trusted`
  - ⚠️ **未实现（v4.1.2 核实）**：代码无产生 `mode="migration"` 批次的入口，`config.yaml` 无 `migration:` 配置节；此开关仅为设计承诺，尚未落地
- 降级迁移（结构完全不同）→ `state-version-unknown` + 备份后 `--mode full` 指引

### 7.2 知识库（存量条目）

| 存量 | 处理 |
|------|------|
| 已有 `[V]` | 机械补齐元数据（id 分配、source=legacy、evidence 按文件判定），**状态不降级** |
| 已有 `[D]` | 不自动处理，进 `/kb-review` 批量审核队列（legacy=1） |
| 无标记条目 | 移入 pending.md 标 [P] |

由 `kb-manager.py migrate` 执行（持锁），产出迁移前后对比报告。

---

## 8. 边界情况总清单（合并去重，35 条精选）

| # | 场景 | 处置 |
|---|------|------|
| 1 | sub agent 导出后、commit 前中断 | 批次 exported，下次 `analyze_pending`，不重导出 |
| 2 | 批次 chunk 被 cleanup 删除 | 按 line_ranges 重生成，旧批次 failed(chunks-missing) |
| 2a | resume 后批次状态为 analyzing | 协议步骤 2 处理 exported/analyzing 全部批次，analyzing 不被过滤（N-2） |
| 2b | 迁移批次 / failed(migration-unverified) 批次恢复 | regenerate 对 mode="migration" 特判：整文件从行 1 重导出（line_ranges: {f: [1, exported_lines]}）；failed（非 retry-exhausted）不算 in-flight、不阻塞文件，下轮进专门重生成循环，旧批次标 superseded（N-3） |
| 3 | commit 重复调用 | 幂等 success，返回已有 receipt |
| 3a | sub agent 分析反复失败 | `--mode analyze-failed` 递增计数；达上限 `failed(analysis-exhausted)`；`--mode commit --force` 显著警告后强制确认（N-4/F-3） |
| 4 | 重生成反复失败（≥3 次） | failed(retry-exhausted) + partial + WARN，提示人工全量重导 |
| 5 | JSONL 被 Claude Code 轮换/截断 | 完整性校验自动检测 → 该文件全量重导 + WARN |
| 6 | 状态文件损坏且有 .bak | 从 .bak 恢复 + WARN + 损坏文件改名留存 |
| 7 | 状态文件损坏且无 .bak | **显式失败** state-corrupt，绝不静默空状态 |
| 8 | save 中途 kill -9 | tmp 残留；原文件完好；cleanup 清理 |
| 9 | null/[]/123 行 | 跳过 + ParseStats 计数，不崩溃 |
| 10 | 超大轮次（>200K） | 无条件 flush + sub_turns 独立 chunk，时间序保持 |
| 11 | 轮次跨 session | session 感知分组，不拼轮 |
| 12 | 未知时间戳条目 | 归"未知桶"置批次尾部，tie-breaker 确定性 |
| 13 | 单文件 >200MB | 接受（生成器流式），外部排序列为扩展项 |
| 14 | [P]/[D] 试图淘汰 [V] | 规则红线 + 事务校验双重拦截 |
| 15 | 用户长期不审核 | 30 天 stale → 归档，不删除、不膨胀 |
| 16 | [C] 仲裁双方都不选 | 保持 [C] 进入下轮 |
| 17 | 敏感扫描命中 | 拦截 + 打码预览；blocked 条目仅以打码形态持久化（模式类型+来源定位），原始值零落盘 |
| 18 | 敏感扫描误报 | 提供打码/驳回；命中日志可见 |
| 19 | 两个写者并发 | .kb.lock 串行，30s 超时报"知识库忙（pid/操作）" |
| 20 | 写者进程崩溃持锁中 | 锁随句柄释放；.tmp 残留 >24h 由体检清理 |
| 21 | 事务中多文件替换部分失败 | 索引最后写 → 最坏=索引滞后，体检自愈 |
| 22 | 索引被手工改坏 | 体检 id 级校验 → 重生成（标注"已自愈"） |
| 23 | /kb-restore 与现有冲突 | 恢复后自动标 [C] 进仲裁 |
| 24 | 归档恢复后证据过期 | 一律回 [P] 重新审核 |
| 25 | 用户审核指令含非法 id | 逐条容错：非法项报错，合法项生效 |
| 26 | pending.md 缺失 | 视为空隔离区，正常初始化 |
| 27 | Windows 文件被编辑器占用 | 替换失败报错并给 .bak 路径，不静默丢弃 |
| 28 | 锁文件被手工删除 | 无碍（锁在句柄上），新锁者重建 |
| 29 | 导出进行中 Claude Code 继续追加 | 快照轻微不一致 → 下轮完整性校验自愈 |
| 30 | mtime 粒度粗（FAT/网络盘） | 快速路径只是优化，hash 兜底 |
| 31 | 批次时间范围缺失 | time_range: null，排序 tie-breaker 兜底 |
| 32 | 迁移后知识库短期"缩水" | 预期行为，/kb-review 一次性补审恢复 |
| 33 | 存量 [V] 之间互相对立 | 标 [C] 进仲裁，不自动取舍 |
| 34 | pending 内同事实重复提取 | dedup 合并（保留更早 created，追加 source） |
| 35 | 重复 vs 冲突难判定 | 按冲突处理，宁进仲裁不进合并 |

---

## 9. 验收标准（合并，模块级）

| 层 | 关键验收项 |
|----|-----------|
| 引擎-批次 | 中断恢复（committed 不变 + pending 提示）；失败重生成（chunk 字节级一致）；commit 幂等；未提交阻塞语义；resume 不跳过分析（N-2）；failed 批次不阻塞且被重生成（N-3）；analyze-failed 计数与 force 确认（N-4） |
| 引擎-完整性 | 截断检测触发全量重导；替换检测；快速路径不计算 hash；自愈（改写源文件下轮触发） |
| 引擎-原子 | 200 次随机 kill -9 后状态文件可解析或 .bak 可恢复；无备份损坏时显式失败零修改 |
| 引擎-解析 | 坏行不崩 + ParseStats 正确；峰值内存与文件数无关（3×15MB vs 1×15MB 差 <2×）；全局时间序断言；超大轮次单调 |
| 引擎-协议 | 端到端（incremental → 读批次 → commit → status）退出码与 JSON 断言；错误信息四要素 |
| 知识-状态 | 新条目 100% 首落 pending；正常读取 0 次触达 pending；[P]/[D] 无法淘汰 [V]；全条目 meta 合法 |
| 知识-生命周期 | 31 天 [P] 归档；180 天 [D] 归档；索引 501→<300 行一致；chunk GC 正确；全流程零正文删除 |
| 知识-事务 | 双写者无覆盖丢失；不一致索引自愈；锁超时报错无写坏；崩溃可恢复 |
| 知识-命令 | 批量审核一次事务完成；/kb-status 与体检一致；恢复回 [P] 入队；30 天零操作仍健康 |
| 知识-安全 | 密钥/密码/路径候选全部拦截，blocked 仅打码形态落盘、原始值零落盘；打码重提交正常；.evolution 被 git 排除；README 双语文档一致 |

---

## 10. 实施计划

### 10.1 阶段与里程碑

| 里程碑 | 阶段 | 内容 | 依赖 | 工作量 |
|--------|------|------|------|--------|
| **M1 引擎可靠** | E1 | 测试脚手架（JSONL/状态 fixture、坏行/截断/中断模拟） | — | 0.5 人日 |
| | E2 | 模块 C 原子写入 + 恢复链 | E1 | 0.5 人日 |
| | E3 | 模块 D-1 解析防御 + ParseStats | — | 0.5 人日 |
| | E4 | 模块 A 双游标 + 批次 + commit + 迁移 | E2 | 1.5~2 人日 |
| | E5 | 模块 B 完整性校验 + 重导交互 | E4 | 1 人日 |
| | E6 | 模块 D-2~D-5 流式化 + 排序 + token 因子 | E3 | 1.5~2 人日 |
| | E7 | 模块 E 协议 + sync.md/SKILL.md 更新 | E4/E5 | 0.5 人日 |
| **M2 知识防线** | K1 | kb-manager.py 骨架 + 存量迁移 | — | 2-3h |
| | K2 | 状态模型（config 扩展 + 规则文件重写 + pending.md） | K1 | 3-4h |
| | K3 | .kb.lock 事务协议 | K2 | 4-5h |
| **M3 命令与安全** | K4 | 生命周期（体检/归档/索引压缩/chunk GC） | K3 | 4-5h |
| | K5 | /kb-review 等 4 命令 + sync/init/SKILL 集成 | K2 | 4-5h |
| | K6 | 敏感扫描闸门 + .gitignore + README 隐私章节 | K2 | 2-3h |
| **M4 发布** | R1 | 全量验收（§9 逐条）+ 线上数据回归 | 全部 | 1 人日 + 2-3h |

**合计：引擎层 6~8 人日 + 知识层 21~28 小时 ≈ 9~12 人日。**

### 10.2 建议落地顺序

```
E1 → E2 → E3 → E4 → E5 → E6 → E7 ─┐
                                   ├→ R1（先发 v4.0.0 引擎部分，再知识部分）
K1 → K2 → K3 → K4 → K5 → K6 ──────┘
```

先 M1（数据完整性，风险最高）→ 再 M2/M3（知识防线）。每阶段独立可验收、独立提交。

---

## 11. 受影响文件清单（21 个）

| 文件 | 动作 |
|------|------|
| `.claude/skills/evolution/evolution-export.py` | 改（双游标/批次/校验/原子写/流式/协议） |
| `.claude/skills/evolution/kb-manager.py` | **新建**（migrate/validate/lock/commit/scan/compress/restore） |
| `.claude/skills/evolution/config.yaml` | 改（sync_engine + lifecycle + lock + sensitive_patterns + 状态标记扩展） |
| `.claude/skills/evolution/rules/write.md` | 重写 |
| `.claude/skills/evolution/rules/read.md` | 重写 |
| `.claude/skills/evolution/rules/dedup.md` | 重写 |
| `.claude/skills/evolution/commands/sync.md` | 改（步骤 0.5 体检 + commit 协议） |
| `.claude/skills/evolution/commands/init.md` | 改（产出落 pending） |
| `.claude/skills/evolution/commands/kb-review.md` | **新建** |
| `.claude/skills/evolution/commands/kb-status.md` | **新建** |
| `.claude/skills/evolution/commands/kb-archive.md` | **新建** |
| `.claude/skills/evolution/commands/kb-restore.md` | **新建** |
| `.claude/skills/evolution/SKILL.md` | 改（命令表 + 知识库描述） |
| `evolution/knowledge-base/pending.md` | **新建** |
| `evolution/knowledge-base/archive/` | **新建** |
| `evolution/knowledge-base/` 8 个详情文件 | 迁移（meta 补齐 + [C] 机会） |
| `.gitignore` | 改（`.evolution/`、`*.kb.bak`、`*.kb.tmp-*`） |
| `README.md` / `README.zh-CN.md` | 改（隐私与安全章节 + 导出机制诚实表述） |
| `docsV3/INSTALLATION_GUIDE.md` | **改（M0：#26 卸载命令 `rm -rf evolution` 修复 + #27 迁移指南矛盾）** |
| `docsV3/EVOLUTION_RULES_AND_LOGIC_V3.md` | 改（#28"无遗漏"虚假承诺 + #30 文档矛盾表述修正） |
| `docsV3/EXPORT_AND_ANALYSIS_DESIGN.md` | 改（#32 chunk 数量矛盾 + 状态管理/错误矩阵/流程章节随 V4 更新） |
| `docsV3/PROJECT_BACKGROUND.md` | 改（#30 矛盾表述修正） |
| `docsV3/VERSION_HISTORY.md` | 改（v4.0.0 记录） |
| `CLAUDE.md` | 改（版本号与描述） |
| `evolution-manual/`（如存在） | **删除或归档（M0：#22 双知识库树）** |

---

## 12. 风险与开放问题（需要用户拍板）

> **v2 更新**：独立评审已确认核心方案正确；下述决策点均已由用户拍板（完整实施，不做成本削减），仅保留技术性开放项。

| # | 决策点 | 状态 |
|---|--------|------|
| 1 | **迁移成本**：升级后默认重分析一次全量历史（~$4） | ✅ 已定：默认保守重分析；`trust_committed` 逃逸阀保留 |
| 2 | **[D] 隔离的审核负担**：存量 [D] 冻结需批量补审 | ✅ 已定：接受，/kb-review 批量补审 |
| 3 | **contact_info 敏感模式**：高误报 | ✅ 已定：默认关闭，按需开启；其余模式全保留 |
| 4 | **先发范围** | ✅ 已定：M0 遗漏修复包先行 → M1 引擎 → M2/M3 知识防线 → M4 发布（§14.5） |
| 5 | **.openclaw / evolution-github 同步**：设计文档何时同步 | ✅ 已定：v2.1 修订后同步至两处（docsV4/ 三份文档） |
| 6 | **审计遗漏修复包**（#26/#22/#4/#21/#27/#23/#24/#25） | ✅ 已纳入（§14.3 🔴 项），列为 M0 先行 |
| 7 | **独立评审建议的"砍掉奢侈品"**（k-way 归并、receipt_hash、归档体系等） | ✅ 已否决：**完整实施**（用户指令：不在乎成本，关键准确） |

---

## 13. 附录

### 13.1 设计草稿索引

| 文档 | 内容 | 行数 |
|------|------|------|
| `design-v4-engine.md` | 引擎层全细节（模块 A-E、迁移、验收、风险；v2.1 含 N-2/N-3/N-4/N-11/N-12 修订） | ~950 |
| `design-v4-knowledge.md` | 知识层全细节（模块 A-E、规则全文草案、时序、边界 20 条；v2 含 N-6/N-7/N-10/N-13/N-14 系统性修订） | ~800 |

### 13.2 对抗性审核报告

- [`../docsV3/ADVERSARIAL_AUDIT_v3.9.0.md`](../docsV3/ADVERSARIAL_AUDIT_v3.9.0.md) — 39 条确认发现全文（含失败场景与建议方案）

---

**文档结束（总纲）**

---

## 14. 独立评审与修订（v2，2026-08-16）

### 14.1 独立评审结论

独立评审逐行核对了代码（C1/C2/C3/D1/D4 与审计描述全部吻合）、实测了线上数据（16 条知识、1×15MB JSONL、sync-state version "3.2.1" 漂移属实），结论：

1. **核心架构正确且必要**：双游标/完整性校验/原子写不是锦上添花，是真实存在的数据安全漏洞
2. **方案漏掉了最便宜的修复**：39 条只覆盖 ~26 条，漏 1 个 CRITICAL + 5 个 HIGH
3. **约 1/3 模块被判定为"为不存在的规模买单"**（k-way 归并、归档体系、receipt_hash 等）
4. **发现 3 个方案自身缺陷**：迁移批次 commit 语义矛盾、回滚路径缺失、分析失败无 liveness

> v2.1 补充（二轮评审）：F-2 回滚手册中"旧脚本返回 state-version-newer"的声明经实测不成立——v3.9.0 `load_sync_state` 不检查 version 字段，回滚手册已按真实行为重写（见 F-2）。

### 14.2 决策：完整实施（用户拍板）

> **用户指令：不在乎成本，关键是要准确。**

- ❌ **否决 独立评审的成本削减建议**：k-way 归并、receipt_hash、analyzing 状态、归档恢复体系、last_used 生命周期、索引压缩、敏感模式 9 项、keep_committed_batches=20 —— **全部保留完整实施**
- ✅ **接受 独立评审的准确性修复**：覆盖矩阵（§14.3）、方案缺陷修复（§14.4）、遗漏发现纳入（§14.3 🔴 项）
- ✅ **接受 独立评审的架构改进**：kb-manager.py 唯一写入口、敏感闸门脚本强制、知识库路径锚定 `__file__`

### 14.3 审计覆盖矩阵（39 条 → 模块 → 状态）

> 🔴 = v1 遗漏、v2 纳入。每一条都有明确处置，无悬空发现。

| # | 发现 | 严重度 | 处置模块 | 状态 |
|---|------|--------|---------|------|
| 1 | 同步游标先于知识提取提交 | HIGH | 引擎 A 双游标+批次 | ✅ |
| 2 | 知识库写入无跨 sub agent 事务 | MEDIUM | 知识 C .kb.lock | ✅ |
| 3 | 草稿知识被读取形成自强化闭环 | HIGH | 知识 A [P] 隔离 | ✅ |
| 4 | 内容摘要策略静默丢关键证据 | HIGH | 🔴 **新增：chunk 头声明截断 + 条目 meta `truncated=1` + 源行号可回溯** | 🔴 |
| 5 | 多 session 聚合不保证时间顺序 | MEDIUM | 引擎 D5 全局排序 | ✅ |
| 6 | [V] 验证语义过宽 | MEDIUM | 知识 A 证据绑定 | ✅ |
| 7 | sub agent 无完成协议 | MEDIUM | 引擎 E receipt 协议 | ✅ |
| 8 | 增量游标无完整性校验 | CRITICAL | 引擎 B sha256 | ✅ |
| 9 | save_sync_state 非原子写入 | HIGH | 引擎 C 原子写 | ✅ |
| 10 | 错误形状行 AttributeError 崩溃 | HIGH | 引擎 D1 解析防御 | ✅ |
| 11 | 超大轮次 chunk 时间乱序 | MEDIUM | 引擎 D3 force flush | ✅ |
| 12 | token 估算偏低 | MEDIUM | 引擎 D4 安全因子 | ✅ |
| 13 | 全量导出 OOM | MEDIUM | 引擎 D2 k-way 流式 | ✅ |
| 14 | 游标在知识消费前提交 | HIGH | 引擎 A | ✅ |
| 15 | 文件重写/截断绕过游标校验 | MEDIUM | 引擎 B | ✅ |
| 16 | 状态丢失绕过 init 防护 | MEDIUM | 🔴 **新增：init 前置检查检测知识库完整性（含 state 完好但 KB 被清空的反向场景）** | 🔴 |
| 17 | 导出锁未覆盖知识库事务 | MEDIUM | 知识 C（V4 起 KB 写入经 kb-manager.py 唯一写入口，锁在脚本内） | ✅ |
| 18 | 大规模输入内存爆炸 | MEDIUM | 引擎 D2 | ✅ |
| 19 | 可变 chunk 路径批次交叉污染 | MEDIUM | 引擎 A manifest 精确路径 | ✅ |
| 20 | 增量游标先提交后提取 | CRITICAL | 引擎 A | ✅ |
| 21 | init 前置检查读取错误信号源 | HIGH | 🔴 **新增：改为检测知识库本体 + last_full_sync 双信号** | 🔴 |
| 22 | 双知识库树、索引自指旧路径 | HIGH | 🔴 **新增：迁移 M0 删除 evolution-manual/ 旧树 + 修复自指路径** | 🔴 |
| 23 | 幻影命令 /kb-sync 等、命令名错位 | MEDIUM | 🔴 **新增：命令统一（M0 已执行：SKILL.md 与 sync.md 删除 /kb-sync /growth-sync /alignment-sync 三个幻影命令，只保留 /evolution 与 /evolution-init；V4 的 /kb-review 等 kb-* 命令按 K5 计划另行新增）** | 🔴 |
| 24 | 相对路径依赖 sub agent cwd | MEDIUM | 🔴 **新增：路径锚定脚本 `__file__`（F-6：project_root = parents[3]；M0 已在 init.md/sync.md 文档标注，代码修改由 M1 E4 实施）** | 🔴 |
| 25 | 导出包含当前会话自身 | MEDIUM | 🔴 **新增：导出排除当前运行会话。明确语义（M0 定案）：以导出开始时刻为界，排除同步触发时刻之后的尾部条目——只处理该时刻之前已完整落盘的条目；当前会话在触发后新产生的尾部条目留待下轮增量，不按内容过滤元记录（避免误伤正常对话）。代码落地在 M1 E4** | 🔴 |
| 26 | 卸载命令 `rm -rf evolution` | CRITICAL | 🔴 **新增：M0 文档修复（备份+精确删除+确认）** | 🔴 |
| 27 | V2→V3 迁移文档矛盾 | HIGH | 🔴 **新增：M0 文档统一** | 🔴 |
| 28 | "导出全部对话无遗漏"虚假承诺 | HIGH | 🔴 **新增：文档诚实表述（声明截断策略与排除范围）** | 🔴 |
| 29 | sync-state version 冻结未迁移 | MEDIUM | 引擎 A.4 bump + MIGRATIONS | ✅ |
| 30 | "静默运行/人类无感"与手动触发矛盾 | MEDIUM | 🔴 **新增：文档修正（M0 已执行：PROJECT_BACKGROUND.md §4 明确为手动触发系统，删除静默运行/人类无感/不需要干预表述）** | 🔴 |
| 31 | 增量截断检测未落地 | MEDIUM | 引擎 B | ✅ |
| 32 | chunk 数量与 token 估算矛盾 | LOW | 🔴 **新增：文档修正（M0 已执行：EXPORT_AND_ANALYSIS_DESIGN.md 统一"估算/实际"双口径，修正 ~136K avg 与 3 chars/token 矛盾数字）** | 🔴 |
| 33 | 日志重写造成增量漏读 | MEDIUM | 引擎 B sha256 | ✅ |
| 34 | 旧 chunk 残留无界膨胀 | HIGH | 引擎批次修剪 + 知识 B chunk GC（manifest schema 对齐引擎 A.2） | ✅ |
| 35 | 未验证新知识淘汰已验证事实 | HIGH | 知识 A 冲突红线 | ✅ |
| 36 | 敏感对话在审核前持久化 | HIGH | 知识 E 三道防线（blocked 仅打码形态落盘，N-6） | ✅ |
| 37 | 知识库写入无并发保护 | MEDIUM | 知识 C | ✅ |
| 38 | 知识库无有效期 | MEDIUM | 知识 B 生命周期 | ✅ |
| 39 | 移除 skill 后知识库失维护 | MEDIUM | 🔴 **新增：README 文档化说明（M0 已执行：README.md / README.zh-CN.md 新增"知识库维护"章节）** | 🔴 |

**覆盖统计**：39/39 全部有处置（v1 覆盖 26，v2 纳入 13 条遗漏：🔴 编号 4/16/21/22/23/24/25/26/27/28/30/32/39，其中含 1 CRITICAL + 5 HIGH——#4/#21/#22/#27/#28）。

### 14.4 方案缺陷修复（独立评审 发现，v2 修订）

**F-1：迁移批次 commit 语义缺口（设计内部矛盾）**

问题：迁移批次 `line_ranges: null`，而 commit 流程遍历 `line_ranges` 推进 committed_lines——null 无法推进。
修订：迁移批次定义特殊 commit 语义——`--mode commit` 检测批次 `mode="migration"` 时，直接 `committed_lines = exported_lines`（不回退、按现状确认），receipt 中注明 `migration_commit: true`。

**F-2：回滚路径缺失（v2 修订——按实测行为重写）**

问题：初稿声称"旧脚本对 version=3.5.0 状态返回 state-version-newer（只读可用、拒绝修改）"。**实测推翻该声明**：v3.9.0 的 `load_sync_state` 根本不检查 version 字段，该保护只存在于 V4 自己的新 loader 里。真实行为是：旧脚本找不到 `processed_lines` 字段 → 按缺失回退 0 → **全量重导 + 覆盖状态文件**。

修订后的回滚手册（实施时写入 INSTALLATION_GUIDE 或独立文档）：

- V4 → V3.9 回滚步骤：
  1. 备份并**移除** `.evolution/chunks/sync-state.json`（连同 `.bak`/`.tmp`/批次 chunk 一并归档保存，勿留在原位）——否则旧脚本会按"游标 0"解释 V4 状态，触发全量重导并覆盖状态文件；
  2. 替换 skill 文件为 v3.9 版本（evolution-export.py / SKILL.md / commands/ / rules/）；
  3. 接受一次全量重导（`--mode full` 或下次同步自动触发）：旧历史重新导出、重新分析；KB 去重兜底，已入库知识不会重复堆积；
  4. 知识库 kb-meta 行与 pending.md 由 V3 规则忽略（未知标记不读取，[V]/[D] 照常可用）；blocked 打码条目对 V3 是普通 [P] 文本，无副作用。
- 迁移前强制备份：`sync-state.json.bak` + 知识库 `*.kb.bak` + 迁移 dry-run 校验。
- 明示代价：回滚 = 丢掉双游标保护 + 一次全量分析成本（~$4），非零成本操作，手册需写明。

**F-3：分析失败无重试上限（liveness 缺口）**

问题：retry_count 只在 chunk 重生成时递增；"chunk 完好但 sub agent 反复分析失败"会无限阻塞（不变式保证不丢数据但不保证前进）。
修订：协议层增加**分析失败计数**——批次新增 `analysis_failures` 字段；sub agent 开始分析时 `--mode start` 置 analyzing；主 agent 摘要连续 2 轮缺 receipt → 在摘要显著位置 WARN"批次 X 连续未确认，请检查 sub agent 是否持续失败"；`analysis_failures >= 3` → 批次标记 `failed(analysis-exhausted)`，提示人工介入（可显式 `--mode commit --force` 强制确认或重生成）。
**CLI 落点（N-4）**：新增 `--mode analyze-failed --batch-id <id>`（递增 `analysis_failures`，达上限置 `failed(analysis-exhausted)`）；`--mode commit --force` 输出显著警告"强制确认将永久跳过该批次未分析内容"，receipt 记录 `forced: true`。详见 design-v4-engine.md E.2。

**F-4：敏感闸门归属不明**

问题：write.md 让 LLM 写 pending.md 时"按模式扫描"——LLM 自查正则不可靠。
修订：**敏感扫描是 kb-manager.py 事务内的强制步骤**，LLM 只提交候选条目文本，脚本扫描命中才落 pending（blocked=secret），规则文件中明确"扫描在脚本里，不在规则里"。

**F-5：kb-manager.py 唯一写入口（独立评审 架构改进，采纳）**

修订：sub agent 永不直接编辑知识库 markdown——只通过 `kb-manager.py add/promote/deprecate/resolve/restore/touch` 提交结构化操作（JSON stdin 或 `--payload <file>`）；kb-manager 持锁执行：敏感扫描 → 去重 → 冲突判定 → 状态转移 → 校验 → 原子替换。同时消灭：LLM 写坏 markdown 风险、事务校验负担、敏感闸门歧义、大部分"读现状→合并"规则复杂度。知识库文件头声明"此文件由 kb-manager.py 管理，勿手工编辑"。知识层设计文档（design-v4-knowledge.md v2）的 write.md 草案与时序 1/2 已按本决策重写。

**F-6：知识库路径锚定（与 #24 联动；v2 修订——修正拼接公式）**

问题：初稿公式 `Path(__file__).parent / location` 有误——`__file__` = `.claude/skills/evolution/kb-manager.py`，`parent` = `.claude/skills/evolution/`，拼接 `evolution/knowledge-base/` 会得到不存在的 `.claude/skills/evolution/evolution/knowledge-base/`。
修订：锚定到**项目根**再拼 location——

```python
project_root = Path(__file__).resolve().parents[3]   # kb-manager.py → evolution → skills → .claude → 项目根
kb_dir = project_root / location                     # location 默认 "evolution/knowledge-base"
assert (project_root / "CLAUDE.md").exists() or (project_root / ".git").exists(), \
    f"路径锚定失败：{project_root} 不是项目根"
```

（`parents[3]`：`parents[0]`=skills/evolution、`[1]`=skills、`[2]`=.claude、`[3]`=项目根。）不再依赖调用方 cwd；sub agent 协议规定使用脚本输出的绝对路径。

**F-7：last_used 可靠维护（独立评审 指出 LLM 不可靠）**

修订：保留 last_used 字段，但**由 kb-manager.py 在读取操作时自动记录**（`--mode touch --id KB-0xx`，或读取摘要时批量更新），不依赖 LLM 报告层自觉。知识层 A.2 字段表已同步。

**F-8：截断可回溯（#4 落地）**

修订：chunk 头部声明"本 chunk 内容按策略截断（tool_result 保留前 500 字+错误尾部）"；条目 meta 支持 `truncated=1` + `source_line`（源 JSONL 行号）；/kb-review 或专用命令可定位源行二次取原文。

**F-9（v2.1 新增）：N-13 kb-meta 转义规则**

kb-meta 行以 `;` 与 `=` 分隔字段，自由文本字段（`scope` 及未来新增自由文本字段）若含保留字符，必须以 JSON 字符串编码写入（`scope="…"` 内层 JSON 转义），解析方按 JSON 字符串解码。详见 design-v4-knowledge.md A.2。

**F-10（v2.1 新增）：N-14 索引上限统一**

kb-index 行数上限统一为 **500**（`lifecycle.index_max_lines: 500`）；SKILL.md、read.md 草案、B.4 三处描述一致。

### 14.5 修订后实施计划（v2）

| 里程碑 | 内容 | 工作量 |
|--------|------|--------|
| **M0 遗漏修复包**（先行） | #26 rm -rf 文档、#27 迁移指南、#22 删旧树修自指、#21 init 双信号、#23 命令统一（✅ 已执行：删除三个幻影命令）、#24 路径锚定（F-6 修正公式；文档已标注，代码 M1 E4）、#25 当前会话过滤（N-9 语义已定案并写入命令文档）、#28/#30/#32 文档诚实化（✅ #30/#32 已执行）、#39 README 说明（✅ 已执行） | 1 人日 |
| M1 引擎 | E1 测试脚手架 → E2 原子写 → E3 解析防御 → E4 双游标+批次+commit（含 F-1 迁移 commit + N-3 failed 恢复循环）→ E5 完整性校验 → E6 流式+排序+token 因子（含 N-11 缓冲落盘）→ E7 协议（含 F-3/N-4 analyze-failed 与 commit --force、N-2 resume 协议） | 6~8 人日 |
| M2 知识防线 | K1 kb-manager 骨架+存量迁移（含 F-6 路径锚定）→ K2 状态模型+规则重写+唯一写入口（F-5，write.md/时序 1 已按 v2 修订对齐）→ K3 .kb.lock 事务 | 21~28h |
| M3 命令与安全 | K4 生命周期（含 F-7 last_used 脚本维护）→ K5 四命令+集成（含 #23 删除三个废弃命令）→ K6 敏感闸门（F-4 脚本强制；blocked 打码形态落盘 N-6）+隐私文档 | 21~28h |
| M4 发布 | 全量验收（§9 + §14.3 覆盖矩阵逐条确认）+ 线上数据回归 + 回滚手册（F-2 实测行为版） | 1.5 人日 |

**总工作量：约 11~14 人日**（完整实施，无削减）。

**独立评审原文**：见 task a1b92a7eb6d946095 输出（已归档于对抗性审核会话记录）。
