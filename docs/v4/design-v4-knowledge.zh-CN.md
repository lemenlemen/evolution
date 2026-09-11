# Evolution V4.0.0 — 知识管理层设计（知识质量防线 + 命令协议）

> ⚠️ **回退横幅（v4.1.2 补记）**：**本文档描述的知识层设计绝大部分已在 v4.1.0 回退，当前实现中不存在**：
> `[P]` 隔离与 pending.md、四级状态模型（`[P]/[D]/[V]/[X]/[C]/blocked`）、`kb-manager.py` 唯一写入口、
> 知识生命周期、敏感扫描闸门、事务锁写路径、主动审核流程。
> 当前采用 V3 轻量规则：三级状态 `[D]/[V]/[X]` + `read.md` / `write.md` / `dedup.md` 人工审核。
> 本文档仅作设计历史参考，勿据以实现。

> **版本**：4.0.0-draft v2（2026-08-16 初稿；v2 修订 2026-08-21）
> **状态**：已实施（实施日期 2026-08-24）
> **定位**：解决对抗性审核发现的 6 个知识管理层问题（1/2/3/4/5/6）
> **范围**：四级状态模型与 [P] 隔离、知识生命周期、事务与并发、命令协议与主动审核、隐私与安全
>
> **v2 修订（N-7 系统性修订）**：本文初稿成文于总纲 v2 的 F-4/F-5/F-7 决策定案之前，多处滞后。v2 已对齐：
> - **F-5 唯一写入口**：write.md 草案与时序 1 改为 LLM 只提交候选文本到 `kb-manager.py add`，脚本负责敏感扫描/去重/冲突判定/持锁事务/原子替换——LLM 永不直接编辑知识库 markdown
> - **#23 命令统一**：D.1 删除 `/kb-sync` `/growth-sync` `/alignment-sync`（V4.0.0 移除）
> - **B.5 manifest schema 与引擎 A.2 对齐**：`batch_id/chunks[].file`（不再是 `run_id/files[].name`）
> - **N-10/N-11/E.3 正则统一**：`local_path` 默认 `enabled: false`，正则与引擎层引用一致
> - **N-13 kb-meta 转义规则**：scope 等自由文本字段用 JSON 字符串编码
> - **N-14**：kb-index 行数上限统一为 500
> - **N-6**：blocked 条目仅以打码形态持久化，原始值零落盘

---

## 0. 问题映射与设计目标

| # | 对抗性审核问题 | 本设计模块 | 核心对策 |
|---|----------------|-----------|----------|
| 1 | [D] 草稿默认可用 → 自我强化闭环 | 模块 A | 新条目一律进入隔离区 `[P]`（pending.md），默认不参与决策 |
| 2 | [V] 验证语义过宽 | 模块 A | 证据类型分类 + 时效 + 适用范围绑定；收紧 [V] 条件 |
| 3 | 未验证新知识可淘汰已验证事实 | 模块 A | 禁止 [P]/[D] 淘汰 [V]；冲突并列保留标 `[C]`，人工裁决 |
| 4 | 写入无事务保护 | 模块 C | `.kb.lock` + 临时副本 + 校验 + 原子替换 |
| 5 | 知识库无生命周期 | 模块 B | 体检扫描、stale 归档、容量监控、chunk GC |
| 6 | 敏感对话在审核前持久化 | 模块 E | 导出扫描（报告）+ 写入闸门（拦截/打码，blocked 仅打码形态落盘 N-6）+ README 知情 |


设计总原则（延续 V3）：**所有知识库操作由 sub agent 在后台执行；写入一律经 kb-manager.py 唯一写入口（F-5），持锁事务化；人类只做"最小成本的批量审核"；默认只归档、永不自动删除**。

---

## 模块 A：四级状态模型 + [P] 隔离（修复自强化闭环）

### A.1 状态模型定义（决策）

**关键决策 1：新增 `[P]` pending，所有 AI 自动提取的条目第一站必须是 `[P]`，物理隔离。**
**关键决策 2：保留 `[D]`，但语义收紧 —— `[D]` = 已通过人工审阅、但证据不足（无工具输出/显式确认/外部文档）的条目。旧语义（"AI 提取未验证"）与 `[P]` 重叠，废除；存量旧 `[D]` 走迁移（A.6）。**
**关键决策 3：`[C]` conflict 不是独立存放，而是叠加标记 —— 冲突双方各自保持原文件原状态，标题并列标 `[C]`，进入人工裁决队列。**

| 状态 | 标记 | 含义 | 谁赋予 | 参与决策 |
|------|------|------|--------|----------|
| pending | `[P]` | 隔离区：AI 提取，未经任何人审阅 | 提取时自动 | 否（候选） |
| draft | `[D]` | 已人工审阅，内容无误，但证据不足 | 用户审核时 | 否（默认）→ 无 [V] 替代时带警告可用 |
| verified | `[V]` | 证据充分（用户显式确认 / 工具输出 / 权威外部文档） | 用户审核或事后验证 | 是（正常权重） |
| deprecated | `[X]` | 已废弃 / 已证实错误 | 用户审核 / 人工裁决 | 不读取 |
| conflict | `[C]` | 与另一条目矛盾，并列保留待仲裁 | 检测到冲突时叠加 | 裁决前低权重 |
| blocked | `blocked=secret`（[P] 的子标记） | 敏感扫描命中，禁止出隔离区；**仅以打码形态持久化（N-6）** | 写入闸门自动 | 否 |

状态机（合法转移）：

```
auto_extract ──► [P] ──审核──► [D] ──工具/显式验证──► [V]
                 │  ├─驳回──► [X]                      │
                 │  ├─强证据审核──► [V]                 ├─时效过期──► 复验提示（不自动降级）
                 │  └─冲突──► [C]（双方并列）            ├─仲裁败诉──► [X]
                 └─超期未审──► 归档（回到 [P] 需重新审核）
```

**禁止的转移（写入红线）**：`[P]/[D]/[C]` → 将某个 `[V]` 标为 `[X]`。

### A.2 条目数据结构

每个条目 = 标题行 + 元数据行 + 正文。元数据行必须是标题行后的**第一个 blockquote 行**，以 `> kb-meta:` 开头，机器可解析：

```markdown
### [D] WSL 网络配置（kb: KB-014）

> kb-meta: id=KB-014; state=D; file=facts; created=2026-08-16T10:12:00; reviewed=2026-08-16T20:00:00; source=session:abc123@line452; confidence=0.5; evidence=conversation_inference; last_used=2026-08-16; scope="Windows 11；截至 2026-08"; sensitive=0

正文……（1-5 行，控制单条体积）
```

| 字段 | 必填 | 取值 | 说明 |
|------|------|------|------|
| `id` | 是 | `KB-###` 全局递增 | 取锁后由"全库（含 archive）最大 id + 1"派生，跨文件唯一且稳定，迁移文件不换 id |
| `state` | 是 | `P/D/V/X/C` | [C] 为叠加：`state=D` + 标题前缀 `[C]` |
| `file` | 是 | `facts/pitfalls/state/growth-notes/prompt-improvements/alignment/decisions/pending` | 条目所在文件；迁移时更新 |
| `created` | 是 | ISO 8601 | 提取时间 |
| `reviewed` | 审核时 | ISO 8601 | 空 = 未审核 |
| `source` | 是 | `session:<会话id>@<行号>` 或 `legacy` 或 `user` 或 `manual` | 来源绑定，可回溯 |
| `confidence` | 是 | `0.9/0.7/0.5/0.3` | 粗粒度四档 |
| `evidence` | 是 | `auto_extract / conversation_inference / tool_output / user_explicit / external_doc` | 证据类型（A.5） |
| `last_used` | 生命周期扫描时 | ISO 8601 | 条目被读取用于决策时更新（F-7：由 kb-manager.py 在读取操作时自动记录，如 `--mode touch --id KB-0xx`，不依赖 LLM 报告层自觉） |
| `scope` | 否 | 自由文本 | 适用范围：平台/版本/时间窗口。**转义规则（N-13）**：含 `;`、`=`、`"` 等保留字符的自由文本字段（scope 及未来新增自由文本字段）必须以 JSON 字符串编码写入，即 `scope="…"` 内层用 JSON 转义（`\"` `\\`），解析方按 JSON 字符串解码；不含保留字符时可省略引号裸写 |
| `sensitive` | 是 | `0/1` | 1 = 敏感条目，索引只列 id 不列摘要 |
| `archived_at` | 归档时 | ISO 8601 | 归档条目保留全元数据 |

**证据类型与置信度绑定**（收紧 [V] 语义，修复问题 2）：

| 证据类型 | 默认置信度 | 可否单独支撑 [V] | 时效要求 |
|----------|-----------|-----------------|----------|
| `tool_output` | 0.9 | 可，但必须记 scope（"实测于 Windows 11"），且属于可复验类（版本号、命令输出） | 版本类条目需可复验；`verify_refresh_days`(365) 到期提示复验 |
| `user_explicit` | 0.9 | 可 | 用户在**审核流程**中对"这条对吗？"的明确肯定（对话中顺口的"对"不算，须是对直接提问的回应） |
| `external_doc` | 0.7 | 可（记录文档名称与版本） | 文档更新即失效 |
| `conversation_inference` | 0.5 | **否**（只能到 [D]） | — |
| `auto_extract` | 0.3 | **否**（只能到 [P]） | — |

### A.3 文件布局（[P] 的存放决策）

**决策：独立 `pending.md` 文件作为隔离区（quarantine 文件），不用"同文件 [P] 标记"，不单独建目录。**

理由：
- 物理隔离是防线的关键：read.md 的正常读取路径（索引 → 按需 1-2 个详情文件）**永远读不到 pending.md**，从机制上杜绝"[P] 被顺手当知识用"；
- "同文件 [P] 标记"与 `[V]` 同屏，模型在上下文里看到隔离条目，隔离失效；
- 独立目录（quarantine/）在当前 8 文件规模下过重，`pending.md` 即单文件隔离区，未来量级增大（>100 条）再升级为目录。

```
evolution/knowledge-base/
├── kb-index.md               # 索引（上限 500 行，index_max_lines，见 B.4；N-14 与 SKILL.md 统一）
├── pending.md                # 新增：隔离区，所有 [P] + blocked 条目（blocked 仅打码形态，N-6）
├── facts.md / pitfalls.md / state.md / growth-notes.md
├── prompt-improvements.md / alignment.md / decisions.md
├── .kb.lock                  # 新增：事务锁（模块 C）
└── archive/                  # 新增：归档区（模块 B）
    └── 2026-08/
        ├── facts-2026-08.md
        ├── pending-2026-08.md
        └── kb-manifest-2026-08.json   # 可恢复索引
```

pending.md 头部带醒目警示，防止任何误读：

```markdown
# Pending 隔离区（未审核候选）

> ⚠️ 本文件内容**未经人工审阅，禁止用于任何决策**。仅 /kb-review 可读取本文件。
> 读取指南：见 rules/read.md 状态表。敏感扫描命中条目以打码形态标记 `blocked=secret`
> 永驻此处（仅含模式类型与来源定位，不含原始敏感值）。

---
```

### A.4 读取规则改造（决策权重）

| 标记 | 读取行为 | 决策权重 |
|------|----------|----------|
| `[V]` | 正常读取使用 | 高；与另一 [V] 冲突时按 `reviewed` 时间新者优先，记入状态报告 |
| `[D]` | 可读取，但**默认不参与决策**；仅当同主题无任何 [V] 替代时，带"（未验证）"标注使用；不作为高风险决策唯一依据 | 低 |
| `[P]` | **不读取**（仅 /kb-review）；紧急情况需用户当次显式许可才可临时引用 | 无 |
| `[C]` | 双方并列读取，均标注"存在矛盾，待人工裁决"；裁决前不构成决策依据 | 暂缓 |
| `[X]` | 跳过 | 无 |
| archive/ | 不读取（可 /kb-restore 恢复） | 无 |

### A.5 冲突处理改造（修复问题 3）

旧规则："新条目与已有条目冲突 → 旧条目标为 [X]" —— 这允许未经验证的 [D] 单方面杀死 [V]。新规则：

1. **写入时冲突判定**（去重步骤完成后）：新候选与任一 `[V]` 语义矛盾 → **禁止淘汰**，候选保持 `[P]`（打 `conflict=KB-0xx` 标记），同时旧 `[V]` 条目标题叠加 `[C]`（含冲突者 id），二者并列保留，计入 `/kb-review` 仲裁队列；
2. **`[D]` 之间的冲突**：同 1，二者都标 [C]，待人工裁决；
3. **仲裁**（/kb-review 流程内）：用户裁决一方正确 → 正确方去 [C] 标，败方标 `[X]`（注明 `superseded_by=KB-0xx`）；裁决后仅剩一方时自动清 [C]；
4. 裁决**不回溯改写历史**：败方仅标 [X] + 说明，删除正文。

### A.6 存量知识库迁移

| 存量类型 | 处理 | 触发 |
|----------|------|------|
| 已有 `[V]` 条目 | 机械补齐元数据（`id` 自动分配、`created`=文件 mtime、`source=legacy`、evidence 按文件判定：facts/decisions 默认 `external_doc` 或 `user_explicit`，pitfalls 默认 `conversation_inference` 但保留 [V]（兼容），状态不降级） | 迁移脚本一次完成 |
| 已有 `[D]` 条目（旧语义） | **不自动处理**，进入 `/kb-review` 批量审核队列，标记 `legacy=1`；用户批量 `all v` / `all d` / 逐个驳回。拒绝者标 [X] | 首次 /kb-review 时 |
| 无状态标记条目 | 视为未审阅 → 移入 pending.md 标 `[P]` | 迁移脚本 |
| 无 id 的元数据缺失 | 同上补齐 | 迁移脚本 |

迁移由新脚本 `kb-manager.py migrate` 执行（持锁），产出迁移前后对比报告。

### A.7 模块 A 边界情况

- 迁移后知识库短期"缩水"（旧 [D] 未审核前不可用于决策）→ 预期行为，/kb-review 一次性补审即恢复；
- 已有 `[V]` 之间互相对立（存量数据）→ 同样标 [C] 进入仲裁，不自动取舍；
- pending.md 中同事实被重复提取 → 去重规则对 pending 生效（模块 D 的 dedup.md）；
- blocked 条目用户要求强行入库 → 不允许，只可打码后重新提交；blocked 条目本身仅以打码形态存在于 pending.md（N-6），原始值在任何文件中都不存在；
- 用户审核时给了弱确认（"好像对"）→ 归为 [D] 而非 [V]。

### A.8 模块 A 验收标准

1. 新条目 100% 首落 pending.md，正常读取流程 0 次读到 pending.md（用脚本验证 read 路径不包含该文件）；
2. 构造"错误推断 → 入库 → 被后续任务引用"场景，验证隔离后错误条目不被引用；
3. `[P]/[D]` 无法将任何 `[V]` 标记为 `[X]`（规则测试用例）；冲突场景下双方并列、标 [C]、进入仲裁队列；
4. 每个条目都有合法 `kb-meta:` 行（id 唯一、evidence 合法、state 合法），脚本校验通过；
5. 存量迁移后 kb-index 计数与详情文件实际条目数一致。

---

## 模块 B：知识生命周期（生老死）

### B.1 阈值配置（config.yaml 增量）

```yaml
# 知识生命周期（v4.0.0 新增）
lifecycle:
  pending_stale_days: 30        # [P] 超期未审核 → stale 标记 → 归档
  draft_stale_days: 90          # [D] 90 天未使用 → 降级提示（列入 /kb-status）
  draft_archive_days: 180       # [D] 降级后 180 天仍未使用 → 自动归档
  verify_refresh_days: 365      # [V] 365 天未复验 → 复验提示（不自动降级）
  index_max_lines: 500          # kb-index 容量阈值
  chunk_keep_rounds: 3          # 保留最近 N 轮导出批次
  chunk_bak_keep_days: 7        # *.bak-* 保留天数
  archive_policy: keep          # keep=默认只归档不删除
```

### B.2 体检扫描（每次 /evolution 顺带执行，sub agent 步骤 0.5）

```
0. 前置检查（现有）
0.5 体检扫描（新增，只读 + 状态更新，耗时 < 2s）：
    a. 遍历详情文件 + pending.md，解析 kb-meta
    b. [P] 且 created + pending_stale_days < now → 状态报告标 stale
    c. [D] 且 last_used 为空/超 draft_stale_days → 标"闲置"；超 draft_archive_days → 自动归档
       （last_used 由 kb-manager.py touch 维护，F-7）
    d. [V] 且超 verify_refresh_days 未复验 → 标"待复验"（仅提示）
    e. 标题带 [C] 的条目 → 加入"待仲裁"报告
    f. 检查 kb-index 行数 > index_max_lines (500) → 触发压缩（B.4）
    g. 检查 .evolution/chunks/ 孤儿文件（B.5）
    h. 输出一行体检报告并入同步摘要
```

stale 标记 = 条目在报告与 /kb-status 中出现，同时**归档动作在下次持锁写入时顺带执行**（避免扫描单独持锁）。归档流程见 B.3。

### B.3 归档机制

- 目录：`archive/YYYY-MM/<源文件名>-<YYYY-MM>.md`（按月聚合，如 `facts-2026-08.md`）；
- 归档格式：条目保留**完整原文 + 全部 kb-meta**，追加 `archived_at=<ISO>`；
- 每次归档在当月的 `kb-manifest-<YYYY-MM>.json` 记录：`{id, 源文件, 目标文件, 归档时间, 原文行号}` —— 恢复依赖此 manifest；
- **可恢复性**：`/kb-restore <id>` → 按 manifest 定位 → 将条目按原状态放回对应详情文件（若状态为 P/D，恢复后一律重置为 `[P]` 重新审核，除非用户显式要求保留原状态）→ 持锁事务写入 → 从 archive 文件与 manifest 中移除；
- **默认只归档不删除**；archive/ 目录不计入 kb-index、不被读取；删除行为仅由用户手工执行（文档注明 `archive_policy: keep`）；
- 归档文件头部注释："此文件由 /kb-archive 与生命周期扫描生成，可经 /kb-restore 恢复，勿手工编辑"。

### B.4 kb-index 容量监控

- **索引是派生数据**：写入事务每次更新索引；体检扫描每次校验索引与详情文件一致性（id 级核对），不一致时**从详情文件重新生成**（索引滞后可自愈，支撑模块 C 的崩溃恢复）；
- 索引行数 > **500**（`index_max_lines: 500`，N-14：与 SKILL.md 描述统一为 500）→ 压缩策略（择一执行，优先 1）：
  1. 重新生成索引：仅含 6 个状态非 [X] 且 `last_used` 距今 < 180 天的条目；被剔除条目在索引中留一行摘要指针（`KB-0xx → archive/2026-08/facts-2026-08.md`，不占正文行数）；
  2. 仍超限 → 按 `created` 最旧优先追加归档（走 B.3）；
- 压缩是确定性重生成，非逐条编辑，行数可预期回落（目标 < 300 行）。

### B.5 chunk 生命周期（与引擎层批次协议衔接）

现状：`.evolution/chunks/` 存 `chunk-*.md`（全量）、`chunk-inc-*.md`（增量）、`sync-state.json`；v3.8.0 已有"仅按白名单清理、禁止 rmtree"纪律。

改造：evolution-export.py 在 sync-state.json 中记录**批次 manifest**（schema 与引擎层 A.2 一致，N-7 修订——旧稿的 `run_id/files[].name` 结构废弃）：

```json
{
  "batches": {
    "inc-20260816-103002-0047": {
      "batch_id": "inc-20260816-103002-0047",
      "mode": "incremental",
      "status": "exported",
      "chunks": [
        {"file": ".evolution/chunks/chunk-inc-20260816-103002-0047-00.md", "entries": 15}
      ]
    }
  }
}
```

GC 规则（体检步骤 g）：
1. 只允许删除**出现在 manifest 中且不在最近 `chunk_keep_rounds` 批次内**的 chunk 文件（按 `chunks[].file` 精确匹配，禁止 glob 通配删除，延续 v3.8.0 纪律）；
2. `*.bak-*` 文件按 mtime 超 `chunk_bak_keep_days` 删除（仅 `.evolution/chunks/` 内）；
3. `sync-state.json` 永不删除；
4. 孤儿 chunk（不在任何 manifest 中）仅**报告不删除**，防止误杀正在写入的文件。

### B.6 模块 B 边界情况

- 用户长期不触发 /evolution → 体检不运行 → 由 /kb-status 兜底（该命令强制先跑一次扫描）；
- 归档后同主题新条目写入 → 不自动比较（避免"归档幽灵"干扰），用户需要时 /kb-restore；
- [C] 条目不因超期归档（仲裁优先级高于生命周期）；
- sensitive=1 条目归档时同规则，不打码（归档区本就在本地且 git 应排除，见 E.4）；
- 索引重生成与用户正在审核冲突 → 压缩在持锁事务内完成，串行化。

### B.7 模块 B 验收标准

1. 构造 31 天前的 [P] → 一次 /evolution 后进入 archive/ 且报告出现 stale 计数；
2. 构造超期 [D] → 180 天后自动归档，恢复后状态为 [P] 需重新审核；
3. kb-index 达到 501 行 → 压缩后 < 300 行且与详情文件 id 级一致（脚本校验）；
4. 构造旧批次 chunk + .bak 文件 → 正确删除且 sync-state.json 保留、当前批次文件保留；
5. 全流程零删除 KB 正文（archive_policy=keep 生效，用文件数量断言）。

---

## 模块 C：知识库事务与并发

### C.1 `.kb.lock` 文件锁协议

> **F-5 归属**：锁由 kb-manager.py 获取与持有；sub agent / LLM 永不直接持此锁写知识库文件。

- 锁文件：`evolution/knowledge-base/.kb.lock`；
- 机制：复用 evolution-export.py 的 `file_lock`（Windows `msvcrt.locking` / Linux `fcntl.flock`，非阻塞轮询 + 超时，进程退出自动释放锁 —— 锁绑定文件句柄，不残留死锁）；
- 超时：KB 写操作用 `lock_timeout: 30s`（导出脚本用 120s，两者独立），轮询间隔 100ms；
- 获取锁的写入方在锁内**自报身份**（写入锁文件内容：`pid + 操作名 + 时间`），供超时报错时诊断；
- **只读操作不需要锁**（原子替换保证读者只会看到完整旧版或完整新版，不会读到撕裂文件）。

### C.2 写入事务协议（单次知识库写入 = 一次事务）

> **F-5 归属**：本协议由 kb-manager.py 实现——sub agent 通过 `kb-manager.py add/promote/deprecate/resolve/restore` 触发事务，**永不自己持锁写文件**。以下步骤全部发生在脚本进程内。

```
1. 获取 .kb.lock（超时 30s → 中止，报"知识库忙（pid=xxx 正在执行 yyy），请稍后重试"，绝不覆盖写入）
2. 读取全部相关文件的现状（详情文件 + pending.md + 索引）
3. 在内存中合并（新条目去重 → 冲突判定 → 状态转移）
4. 逐文件写入临时副本：.<name>.kb.tmp-<pid>（同目录、同文件系统，保证 replace 原子性）
5. 校验：
   a. 每个临时文件可解析（标题/元数据/正文三段式），条目数 = 内存模型计数
   b. 索引一致性：索引内每个 id 在详情文件中存在；详情文件条目数 = 索引计数（有压缩豁免时校验豁免集）
   c. kb-meta 合法性（id 唯一、state 合法、evidence 合法）
6. 原子替换（写序：详情文件 → pending.md → kb-index 最后）
   - 替换前将现有文件轮转为 .<name>.kb.bak（滚动保留最近 1 份）
   - Windows: os.replace 同卷内原子；替换失败 → 中止剩余文件，报告并可回滚（用 .bak 恢复）
7. finally: 释放锁
```

**崩溃安全**：写序保证最坏情况是"索引滞后"（详情文件新、索引旧），而索引是派生数据（B.4）—— 下次体检扫描从详情文件重生成即自愈；`.<name>.kb.bak` 提供最近一次人工回滚点。

### C.3 并发触发的行为规范

| 场景 | 行为 |
|------|------|
| /evolution 与 /kb-review 同时触发 | 排队串行：后者等锁 ≤ 30s，超时报错不写 |
| 两个 sub agent 同时写（各自调用 kb-manager.py） | 同左；锁内读现状保证不丢失对方已提交内容 |
| 只读（正常知识检索）与写并发 | 不冲突，读者可能看到新旧两版之一，绝不撕裂 |
| 写者超时 | 报告错误 + 锁内身份信息（pid/操作），提示稍后重试 |
| 进程崩溃持锁中 | 句柄随进程关闭，锁自动释放；.tmp 残留由下一次体检扫描清理（仅清理带 .kb.tmp- 前缀且 mtime > 24h 的文件） |

### C.4 模块 C 边界情况

- 锁文件被手工删除 → 无碍（锁在句柄上，文件删除不影响持锁者；新锁者重建文件）；
- 8 文件批写中途失败 → 已替换文件保留、未替换中止；`.kb.bak` 回滚预案；
- 写入内容与磁盘现状冲突（事务期间外部手工编辑）→ 校验失败中止，报告差异让用户确认；
- Windows 上被占用文件（编辑器打开）替换失败 → 报错并给出 .bak 路径，不静默丢弃。

### C.5 模块 C 验收标准

1. 并发压测：两个写者同时提交不同条目 → 两者内容都保留，无覆盖丢失；
2. 注入索引与详情不一致 → 体检扫描自愈为一致；
3. 持锁期间第二写者 30s 内报"知识库忙"，无写坏文件；
4. 任意时刻读取（含写中）不出现半个文件内容；
5. 模拟中途崩溃 → 重启后体检自愈，无孤儿 .tmp 残留（>24h 被清理）。

---

## 模块 D：命令协议与主动审核流程

### D.1 命令清单

| 命令 | 用途 | 新增/现有 |
|------|------|-----------|
| `/evolution` | 增量同步 + 体检扫描 + 审核队列提示 | 现有，改 |
| `/evolution-init` | 初始化 | 现有，改（产出全部落 pending） |
| `/kb-review` | **批量审核** pending + 遗留 [D] + [C] 仲裁 | 新增 |
| `/kb-status` | 知识库健康报告 | 新增 |
| `/kb-archive` | 手动归档 | 新增 |
| `/kb-restore <id>` | 从归档恢复（回到 [P] 重新审核） | 新增 |

> **#23 命令统一（N-7 修订）**：旧稿保留的 `/kb-sync`、`/growth-sync`、`/alignment-sync` 为幻影命令（文档存在、实现错位），与 #23"命令统一"决策矛盾——**V4.0.0 移除，废弃**。局部同步需求由 `/evolution` 统一承担；SKILL.md 命令表同步删除这三项。

### D.2 命令定义（frontmatter 草案，风格对齐现有命令）

```markdown
---
name: kb-review
version: 4.0.0
description: 批量审核待定条目。列出 pending 队列、遗留 [D]、[C] 冲突待仲裁项，用户批量确认/驳回，sub agent 调用 kb-manager.py 持锁执行状态迁移。
disable-model-invocation: true
---
```

`/kb-review` 执行流程：
1. sub agent 读取 pending.md + 详情文件中 `legacy=1` 的 [D] + 标题带 [C] 的条目（只读，无需锁）；
2. 生成**一屏预览**（每条约 1 行，见 D.3）；
3. 用户输入批量指令；sub agent 将批量指令提交给 kb-manager.py（promote/deprecate/resolve），脚本持锁执行迁移：
   - `v <ids>` 或 `all v` → 标 [V] 移入详情文件（强证据）
   - `d <ids>` → 标 [D] 移入详情文件（弱证据）
   - `x <ids>` → 标 [X]（留原地，注明驳回原因可选）
   - `a <ids>` → 查看条目全文后再决定
   - `c <id> 选 <id>` → 裁决 [C]：胜者去 [C] 标，败者标 [X] + `superseded_by`
4. 迁移完成输出 diff 摘要：`✅ KB-014 facts (P→V) · KB-015 pending (P→D) · KB-002 pitfalls (P→X)`；
5. 全部在模块 C 的**一个事务**内完成（批量原子）。

`/kb-status` 输出模板：

```
📊 知识库健康报告
- 条目：V 12 / D 3 / P 5（其中 blocked 1）/ X 4 / C 2
- 待审核：5（P）· 遗留旧 [D]：6 · 待仲裁：2
- 生命周期：stale [P] 2 · 闲置 [D] 1 · 待复验 [V] 3
- 容量：kb-index 412/500 行 · archive 1.2KB · chunks 3 批次（孤儿 0）
- 敏感扫描：chunks 疑似密钥 2 处（仅报告）· KB 正文 0
```

### D.3 审核 UX（最小成本原则）

- **一屏预览**，每行：`[序号] KB-014 [P] WSL 网络配置 | 会话#452 08-10 | 置信 0.5 | 摘要 12 字`；sensitive=1 的条目只显示 id 与来源，不显示内容摘要；
- **默认动作前置**：无证据冲突的条目，默认推荐 `v`（审核即信任）—— 但推荐标签按证据类型显示：`tool_output` 推荐 `v`，`conversation_inference` 推荐 `d`；
- **批量**：`all v` / `v 1-5` / `d 2 4` 等；确认后一次性 diff 预览，用户 `y` 即执行；
- **零审核**路径：什么都不做 → 30 天后 stale → 归档，系统自动保持干净（不强迫审核，也不让它长期堆积污染）；
- 每次 `/evolution` 摘要末尾附一行提示：`📋 5 条待审核（/kb-review）· 2 条 30 天后过期（/kb-status）` —— 提示不阻塞，永不自动执行审核。

### D.4 与现有命令的集成

- `sync.md`：新增步骤 0.5 体检扫描 + 步骤 4 审核队列提示；完成标准追加"体检报告行"；写入步骤改为调用 `kb-manager.py add`（F-5，见时序 1）；
- `init.md`：生成的知识库全部落 pending.md（不再是 [D]），完成标准改为"pending.md 条目数 > 0"；新增建议步骤"建议执行一次 /kb-review 批量审核初始条目"；
- `SKILL.md`：命令表 + 4 个新命令；**删除 /kb-sync /growth-sync /alignment-sync 三行（#23 命令统一）**；规则表不变（指向更新后的 3 个规则文件）；知识库路径描述加 `pending.md` 与 `archive/`；kb-index 行数上限描述统一为 500（N-14）。

### D.5 模块 D 边界情况

- 用户审核指令中夹杂不存在的 id → 忽略并报告，不部分失败后回滚整个批次（逐条容错，成功项保留）；
- 审核期间用户又跑了 /evolution 写入 pending → 锁串行，第二次写自然去重；
- [C] 仲裁时用户两个都不选 → 保持 [C] 进入下轮，不自动废弃；
- /kb-restore 的目标状态与现有条目冲突 → 恢复后自动进仲裁队列（标 [C]）；
- 审核中断（用户不回复）→ sub agent 超时退出，不产生任何写操作，预览可重新生成。

### D.6 模块 D 验收标准

1. 10 条 pending + 6 条遗留 [D]，用户一条 `all v` → 一次事务内全部迁移，摘要正确，索引计数同步；
2. 审核中途输入非法 id → 报错但已合法项生效；
3. `/kb-status` 与体检扫描结果一致（同一数据源）；
4. /kb-restore 恢复条目后状态为 [P] 且出现在审核队列；
5. 完整流程（同步 → 提示 → 审核 → 状态）在无人值守下 30 天不操作，知识库仍健康（stale 归档而非膨胀）。

---

## 模块 E：隐私与安全

### E.1 问题定位

现状：对话导出（evolution-export.py 的 chunk 文件）与知识库写入都在**任何人工审核之前**发生，敏感内容（密钥、token、路径、个人信息）在用户未同意时已落盘；pitfalls#3 已记录"敏感信息泄漏风险"但没有机制防线。

### E.2 三道防线

```
防线 1（导出层，报告型）：evolution-export.py 对落盘 chunk 做敏感模式扫描（N-12：归属为
     导出脚本，非 sync 步骤），命中只报告（含文件与行号），不拦截 —— 导出是功能必须，
     先让用户知道存在。

防线 2（写入层，拦截型）：知识库写入闸门 —— 由 kb-manager.py 在事务内强制执行（F-4）：
     候选条目正文含敏感模式 → 不写入详情文件，条目以【打码形态】落 pending.md 并打
     blocked=secret，通知用户两种出路：
        a) 打码后重新提交（值替换为 <REDACTED:类型>，例如 <REDACTED:api_key>）
        b) 确认无需入库，直接 x 驳回

     ★ N-6 明确——blocked 条目的持久化形态：
        - 落盘内容 = 打码形态：仅含 模式类型（如 secret_type=api_key）+ 来源定位
          （source=session:<id>@<line>，可回 chunk 定位原文）+ 标题（若标题本身无敏感值）；
          正文中的原始敏感值一律丢弃，绝不写入。
        - "被拦截的原始内容绝不写入知识库任何文件（包括 archive/）"指的就是这个形态约束：
          blocked 条目可以持久化，但只能是打码形态；原始值零落盘。
        - 用户后续打码重提交 = 提交替换后的 <REDACTED:*> 文本，走正常 [P] 流程。

防线 3（知情层，文档型）：README / README.zh-CN 新增"隐私与安全"章节（D.4 草案）；
     .gitignore 增加 .evolution/（chunk 与 sync-state 永不入库）。
```

### E.3 敏感字段模式清单（config.yaml `sensitive_patterns`）

> **N-7/N-10 正则统一**：本清单是唯一权威来源；引擎层（evolution-export.py 防线 1）与知识层（kb-manager.py 防线 2）引用同一份 config，不得各自内联正则。`local_path` 默认 `enabled: false`（N-10：路径在知识条目中出现频率高、拦截会大量误伤正常条目，用户可按需开启）。

```yaml
sensitive_patterns:
  - name: github_token
    pattern: "ghp_[A-Za-z0-9]{36}"
    enabled: true
  - name: anthropic_api_key
    pattern: "sk-ant-[A-Za-z0-9_-]{20,}"
    enabled: true
  - name: openai_api_key
    pattern: "sk-[A-Za-z0-9]{20,}"
    enabled: true
  - name: aws_access_key
    pattern: "AKIA[0-9A-Z]{16}"
    enabled: true
  - name: slack_token
    pattern: "xox[baprs]-[A-Za-z0-9-]{10,}"
    enabled: true
  - name: private_key
    pattern: "-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----"
    enabled: true
  - name: generic_secret_assignment
    pattern: "(password|passwd|pwd|token|secret|api[_-]?key)\\s*[=:：]\\s*[^\\s]{8,}"
    enabled: true
  - name: local_path
    pattern: "[A-Za-z]:\\\\[^\\s\"']+|/home/[^\\s\"']+"
    enabled: false        # N-10：默认关闭（高误报），按需开启
  - name: contact_info
    pattern: "(?<![\\d])\\d{11}(?![\\d])|[\\w.+-]+@[\\w-]+\\.[\\w.]+"
    enabled: false        # 高误报，按需打开
```

命中策略：拦截后展示**打码预览**（`key=sk-***（已拦截）`），杜绝"报错但内容已入库"。

### E.4 README 隐私章节草案

```
## 隐私与安全

- Evolution 会从你的 Claude Code 会话历史中提取知识（首次 /evolution-init 全量，
  之后增量）。提取的原始语料保存在项目内 .evolution/chunks/（已被 .gitignore 排除），
  提取结果写入 evolution/knowledge-base/。
- 所有自动提取的条目先进入隔离区（pending.md），在你审核（/kb-review）之前
  不会被任何决策使用。
- 写入知识库前会对候选条目做敏感信息扫描（密钥/密码/token/本地路径/联系方式），
  命中的条目被拦截，仅以打码形态（模式类型 + 来源定位）记录在隔离区，
  原始敏感值不会写入任何文件；原始语料中的敏感内容请用 /kb-status 查看扫描报告后
  自行清理或删除对应 chunk。
- 知识库目录在 git 仓库内 —— 提交前请确认无敏感内容（/kb-status 可复查）。
  归档区（archive/）默认只归档不删除；彻底删除请手动执行。
- 你的控制权：/kb-review（审核）、/kb-archive（归档）、/kb-restore（恢复）、
  直接删除文件。系统不会在你未参与的情况下把任何未审核内容用于决策。
```

### E.5 模块 E 验收标准

1. 构造含 `sk-ant-...`、`ghp_...`、`password=...` 的候选条目 → 全部被拦截入 blocked，KB 正文零命中；blocked 条目落盘内容为打码形态（模式类型 + 来源定位），不含原始值；
2. 打码重提交后正常入库且不含原始值；
3. chunk 扫描报告能指出含密钥的文件与行号；
4. `.evolution/` 在 .gitignore 中，`git status` 不显示 chunk；
5. README 中英文两版均有隐私章节，且与控制权命令一致（文档-行为一致性检查）；
6. **N-6**：blocked 条目持久化内容断言——文件中不存在任何匹配 sensitive_patterns 的原始值，仅存在 secret_type 与 source 定位字段。

---

## 规则文件改造前后对比（全文草案）

### write.md（改造后，v2 修订——对齐 F-5 唯一写入口）

```markdown
# 写入规则（v4.0.0）

## 唯一写入口（F-5）

**LLM 永不直接编辑知识库 markdown 文件。** 所有写入通过 `kb-manager.py add` 提交：

- 提交方式：候选条目以 JSON 经 stdin 传入（或 `--payload <file>`），
  字段：{title, body, source, evidence, confidence, scope, sensitive_hint}
- 脚本在事务内负责：敏感扫描 → 去重 → 冲突判定 → 状态转移 → 持锁 → 校验 → 原子替换
- LLM 的职责止于"提交结构化候选文本"；扫描、落盘、索引更新全部由脚本完成
- 知识库文件头声明"此文件由 kb-manager.py 管理，勿手工编辑"

## 状态标记

| 状态 | 标记 | 含义 |
|------|------|------|
| pending | `[P]` | 隔离区：AI 提取，未经人工审阅，默认不参与决策 |
| draft | `[D]` | 已人工审阅、内容无误，但证据不足（仅对话推断），无 [V] 替代时带警告使用 |
| verified | `[V]` | 证据充分：用户显式确认 / 工具输出 / 权威外部文档 |
| deprecated | `[X]` | 已废弃或已证实错误 |
| conflict | `[C]` | 与另一条目矛盾，双方并列保留，待人工裁决（叠加标记，不单独存放） |
| blocked | `[P]` + `blocked=secret` | 敏感扫描命中，以打码形态永驻隔离区，禁止移出 |

## 写入规则

1. **所有新条目一律先入 `pending.md`，标记 `[P]`，禁止直接进入详情文件**
   - 由 `kb-manager.py add` 自动完成；格式（标题 + kb-meta 元数据行）由脚本生成，
     LLM 无需手写 meta 行
   - id 分配、created 时间戳、去重、冲突判定均在脚本事务内完成

2. **以下情况可标 `[V]`**（审核流程经 `kb-manager.py promote` 执行）：
   - 用户在审核流程中对条目明确确认（`user_explicit`，默认置信 0.9）
   - 工具调用输出可复验（`tool_output`，必须记录 scope 如"实测于 Windows 11"）
   - 权威外部文档（`external_doc`，记录文档名与版本）
   - 仅对话推断（`conversation_inference`）**不得**标 [V]，只能标 [D]

3. **冲突处理**（脚本自动判定，LLM 不参与执行）：
   - 新候选与 `[V]` 矛盾 → **禁止把旧条目标 [X]**；候选留 pending 并注 `conflict=KB-0xx`，旧 [V] 标题叠加 `[C]`，计入 /kb-review 仲裁
   - 两个 [D] 矛盾 → 同左，并列标 [C]
   - 仲裁由用户执行：胜方去 [C]，败方标 `[X]` 并注 `superseded_by=KB-0xx`
   - 红线：`[P]/[D]/[C]` 一律不得淘汰 `[V]`

4. **敏感扫描（写入闸门，F-4：扫描在脚本里，不在规则里）**：
   - `kb-manager.py add` 在事务内按 config.yaml `sensitive_patterns` 强制扫描每条候选
   - 命中 → 条目以打码形态落 pending 标 `blocked=secret`
     （仅存模式类型 + 来源 session@line 定位，原始敏感值丢弃，绝不写入任何文件）
   - 通知用户打码重提交（<REDACTED:类型>）或驳回
   - LLM 不做自查正则——不可靠，也不需要

5. **事务要求**（全部由 kb-manager.py 保证，LLM 无感知）：
   - `.kb.lock` 锁内完成（读现状 → 合并 → 临时副本 → 校验 → 原子替换 → 释放）
   - 单次写入 = 单个事务；多个文件同时修改时索引最后写

## 配置文件
- 参数配置：见 ../config.yaml（lifecycle / sensitive_patterns / lock_timeout）
```

### read.md（改造后）

```markdown
# 读取规则（v4.0.0）

## 渐进式读取

**重要**：不要一次性读取所有文件！遵循渐进式披露原则。

### 步骤 0：审核队列提示（不读取内容）

- 若 /evolution 摘要或用户任务涉及知识，提示：`📋 N 条待审核（/kb-review）`
- **禁止读取 pending.md 内容**（除非用户在 /kb-review 流程内）

### 步骤 1：读取索引

读取 `evolution/knowledge-base/kb-index.md`（上限 500 行，超限会被自动压缩，见 B.4）

### 步骤 2：判断需求

基于索引中的分类摘要判断所需文件（facts/pitfalls/state/growth-notes/prompt-improvements/alignment/decisions）

### 步骤 3：按需读取（只读相关的 1-2 个文件）

### 状态权重（决策依据）

| 标记 | 使用规则 |
|------|----------|
| `[V]` | 正常使用；两个 [V] 冲突时按 reviewed 新者优先并报告 |
| `[D]` | 默认不参与决策；仅同主题无 [V] 时带"（未验证）"标注使用，不作高风险决策唯一依据 |
| `[P]` | 不读取、不使用；紧急情况需用户当次显式许可 |
| `[C]` | 双方并列读取，均标注"矛盾待裁决"，裁决前不构成依据 |
| `[X]` | 跳过 |
| archive/ | 不读取；恢复用 /kb-restore |

## 配置文件
- 参数配置：见 ../config.yaml
```

### dedup.md（改造后）

```markdown
# 去重规则（v4.0.0）

> F-5 修订：去重由 kb-manager.py 在事务内自动执行；本文件是脚本实现的规格说明，
> 也是 /kb-review 中人工判断重复/冲突时的参考。

## 去重策略

1. 基于 `kb-index.md` 摘要 + **`pending.md` 索引头部的 pending 条目清单**判断可能重复
   （pending 同样需要去重，防止同事实重复堆积）
2. 不确定时读取对应详情文件精确去重
3. 重复处理：
   - 与详情文件重复 → 丢弃新候选（若新候选证据更强，更新原条目 evidence/last_used，状态不升）
   - 与 pending 重复 → 合并：保留 `created` 更早者，`source` 追加新来源
4. **重复 ≠ 冲突**：
   - 语义相同 → 重复 → 合并
   - 语义矛盾 → 冲突 → 走 write.md 规则 3（标 [C]，禁止淘汰 [V]）
   - 判断不了 → 视为冲突候选，宁进仲裁不进合并

## 配置文件
- 参数配置：见 ../config.yaml
```

### config.yaml 增量（v4.0.0 追加）

```yaml
# 状态标记（扩展）
status_markers:
  pending: "[P]"
  draft: "[D]"
  verified: "[V]"
  deprecated: "[X]"
  conflict: "[C]"

# 知识生命周期
lifecycle:
  pending_stale_days: 30
  draft_stale_days: 90
  draft_archive_days: 180
  verify_refresh_days: 365
  index_max_lines: 500
  chunk_keep_rounds: 3
  chunk_bak_keep_days: 7
  archive_policy: keep

# 事务
lock:
  kb_lock_timeout: 30
  kb_lock_path: "evolution/knowledge-base/.kb.lock"

# 敏感模式（E.3，唯一权威来源；local_path 默认关闭 N-10）
sensitive_patterns:
  - {name: github_token, pattern: "ghp_[A-Za-z0-9]{36}", enabled: true}
  - {name: anthropic_api_key, pattern: "sk-ant-[A-Za-z0-9_-]{20,}", enabled: true}
  - {name: openai_api_key, pattern: "sk-[A-Za-z0-9]{20,}", enabled: true}
  - {name: aws_access_key, pattern: "AKIA[0-9A-Z]{16}", enabled: true}
  - {name: slack_token, pattern: "xox[baprs]-[A-Za-z0-9-]{10,}", enabled: true}
  - {name: private_key, pattern: "-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----", enabled: true}
  - {name: generic_secret_assignment, pattern: "(password|passwd|pwd|token|secret|api[_-]?key)\\s*[=:：]\\s*[^\\s]{8,}", enabled: true}
  - {name: local_path, pattern: "[A-Za-z]:\\\\[^\\s\"']+|/home/[^\\s\"']+", enabled: false}
  - {name: contact_info, pattern: "1[3-9]\\d{9}|[\\w.+-]+@[\\w-]+\\.[\\w.]+", enabled: false}
```

---

## 流程时序

### 时序 1：写入（同步 → 提取 → 隔离）（v2 修订——对齐 F-5 唯一写入口）

```
用户 /evolution
  → 主 agent 触发 sub agent
  → sub agent: evolution-export.py --mode incremental（引擎锁，自管）
  → 逐 chunk 提取候选条目（auto_extract, confidence 0.3）
  → sub agent 调用 kb-manager.py add（候选 JSON 经 stdin / --payload 提交）
      以下全部在脚本事务内完成，sub agent 不持锁、不写文件：
      · 敏感扫描（E.3 模式）→ 命中者以打码形态落 pending 标 blocked=secret（N-6）
      · 持 .kb.lock（30s 超时）
      · 读 pending.md 现状 + 去重合并（dedup.md 规则由脚本实现）
      · 冲突判定（与 [V]/[D] 矛盾 → 双方标 [C]，候选留 pending）
      · 写临时副本 → 校验（索引一致性、meta 合法性）
      · 原子替换 pending.md（必要时详情文件加 [C] 标记）→ 释放锁
  → 脚本返回结构化结果（新增 id / 去重丢弃 / blocked 清单）
  → sub agent 返回摘要 + 体检报告 + 审核队列提示（N 条待审核）
```

### 时序 2：审核（/kb-review）

```
用户 /kb-review
  → sub agent 读取 pending.md + 遗留 [D] + [C] 条目（只读）
  → 生成一屏预览（每行 1 条，含 id/状态/来源/置信/摘要；sensitive 只显 id）
  → 用户: `v 1-4 6` / `all v` / `d 2` / `x 5` / `c 3 选 1`（C 仲裁）
  → sub agent 调用 kb-manager.py promote/deprecate/resolve（批量操作一次提交）
      以下在脚本事务内完成：
      · 持 .kb.lock
      · 校验逐条状态转移合法性（禁 [P]/[D]→杀 [V]；blocked 拒绝移出）
      · 写临时副本（详情文件 + pending.md + 索引）→ 校验 → 原子替换 → 释放锁
  → 输出 diff 摘要：KB-014 facts (P→V) · KB-015 pitfalls (P→X) …
```

### 时序 3：生命周期（/evolution 步骤 0.5 顺带 + /kb-status 兜底）

```
体检扫描（只读解析 kb-meta）
  → [P] 超 pending_stale_days → 列 stale
  → [D] 超 draft_archive_days → 列归档候选
  → [V] 超 verify_refresh_days → 列待复验
  → [C] 标题 → 列待仲裁
  → kb-index > 500 行 → 列压缩
  → chunks 批次 manifest 核对 → 列孤儿/可删文件
  → 下一次持锁写入时顺带执行：stale 归档（移入 archive/YYYY-MM/ + manifest 记录）
    与索引压缩（派生重生成）
  → 报告并入同步摘要 / /kb-status 全文
```

---

## 边界情况总清单

| # | 场景 | 处置 |
|---|------|------|
| 1 | 锁超时（另一写者持锁） | 报"知识库忙（pid/操作）"，不写，提示重试 |
| 2 | 写者进程崩溃 | 锁随句柄释放；.tmp- 残留 >24h 由体检清理；.kb.bak 提供回滚 |
| 3 | 事务中多文件替换部分失败 | 中止剩余；索引最后写保证最坏=索引滞后，体检自愈 |
| 4 | 迁移后知识库短期瘦身 | 预期行为，/kb-review 一次补审恢复 |
| 5 | 存量 [V] 之间互相对立 | 标 [C] 进仲裁，不自动取舍 |
| 6 | pending 内同事实重复提取 | dedup 合并（保留更早 created，追加 source） |
| 7 | 重复 vs 冲突难判定 | 按冲突处理，宁进仲裁不进合并 |
| 8 | [P]/[D] 试图淘汰 [V] | 规则红线 + 事务校验双重拦截 |
| 9 | 用户长期不审核 | 30 天 stale → 归档，不删除、不膨胀 |
| 10 | [C] 仲裁双方都不选 | 保持 [C] 进入下轮，不自动废弃 |
| 11 | 敏感扫描命中 | 拦截 + 打码预览；blocked 条目仅以打码形态持久化（模式类型 + 来源定位），原始值零落盘（N-6） |
| 12 | 敏感扫描误报（如路径含 token 字样） | 提供打码/驳回；命中日志可见（/kb-status） |
| 13 | /kb-restore 目标与现有冲突 | 恢复后自动标 [C] 进仲裁 |
| 14 | 归档恢复后证据过期 | 一律回 [P] 重新审核 |
| 15 | chunk GC 与正在进行的同步竞争 | 只删 manifest 外旧批次；孤儿仅报告 |
| 16 | sync-state.json | 永不删除 |
| 17 | 索引被手工改坏 | 体检校验 id 级一致，不一致则重生成（标注"已自愈"） |
| 18 | 用户审核指令含非法 id | 逐条容错：非法项报错，合法项生效 |
| 19 | pending.md 为空 / 文件缺失 | 视为空隔离区，正常初始化 |
| 20 | Windows 文件被编辑器占用 | 替换失败报错并给 .bak 路径，不静默丢弃 |

---

## 验收标准汇总（模块级）

| 模块 | 关键验收项 |
|------|-----------|
| A | 新条目 100% 首落 pending.md；正常读取 0 次触达 pending；[P]/[D] 无法淘汰 [V]；全条目 meta 合法（含 N-13 转义规则校验）；迁移后索引与详情一致 |
| B | 31 天 [P] 自动归档；180 天 [D] 自动归档；索引超 500 行压缩至 <300 且一致；chunk 批次 GC 正确（manifest schema 与引擎 A.2 一致）；全流程零正文删除 |
| C | 双写者无覆盖丢失；不一致索引自愈；锁超时报错无写坏；任意读不撕裂；崩溃后可恢复 |
| D | 批量审核一次事务完成；非法 id 容错；/kb-status 与体检一致；恢复后回 [P] 入队；30 天零操作仍健康 |
| E | 密钥/密码/路径候选全部拦截，blocked 仅打码形态落盘、原始值零落盘；打码重提交正常；chunk 扫描可定位；.evolution 被 git 排除；README 双语文档与行为一致 |

---

## 实施顺序与工作量评估

| 阶段 | 内容 | 依赖 | 工作量（单人） | 可验收产出 |
|------|------|------|---------------|-----------|
| P0 盘点迁移 | kb-manager.py 骨架（migrate/validate）；存量 [V] 补 meta、无标记移 pending | 无 | 2-3h | 迁移后库可被 validate 通过 |
| P1 状态模型 | config.yaml 扩展；write.md/read.md/dedup.md 改造；pending.md 引入；**唯一写入口 `kb-manager.py add` CLI（F-5）** | P0 | 3-4h | 规则文件评审 + 写入路径改走 pending |
| P2 事务 | .kb.lock 协议；kb-manager.py 的 lock/commit 原语；写序与校验 | P1 | 4-5h | 并发压测通过（C.5 标准） |
| P3 生命周期 | 体检扫描；归档/恢复；索引压缩；chunk 批次 manifest + GC（manifest schema 对齐引擎 A.2） | P2 | 4-5h | B.7 标准场景测试通过 |
| P4 命令与审核 | /kb-review /kb-status /kb-archive /kb-restore 命令文件 + sync/init/SKILL 集成；**删除 /kb-sync /growth-sync /alignment-sync（#23）** | P1 | 4-5h | 全命令手动验收脚本 |
| P5 安全 | 敏感扫描闸门（脚本强制，blocked 打码形态落盘 N-6）；chunk 扫描报告；.gitignore；README 隐私章节（中英） | P1 | 2-3h | E.5 标准测试通过 |
| P6 回归 | 全量规则一致性测试；VERSION_HISTORY/CLAUDE.md 版本更新 | 全部 | 2-3h | v4.0.0 发布清单 |

**合计约 21-28 小时**，建议分 5-6 个提交按阶段落地，每阶段独立可验收，P0/P1 先行（打破自强化闭环是最高优先）。

### 受影响文件清单

| 文件 | 动作 |
|------|------|
| `.claude/skills/evolution/config.yaml` | 改（状态标记扩展 + lifecycle + lock + sensitive_patterns） |
| `.claude/skills/evolution/rules/write.md` | 重写（本节草案） |
| `.claude/skills/evolution/rules/read.md` | 重写（本节草案） |
| `.claude/skills/evolution/rules/dedup.md` | 重写（本节草案） |
| `.claude/skills/evolution/commands/sync.md` | 改（步骤 0.5 体检 + 步骤 4 提示） |
| `.claude/skills/evolution/commands/init.md` | 改（产出落 pending + 建议补审） |
| `.claude/skills/evolution/commands/kb-review.md` | 新建 |
| `.claude/skills/evolution/commands/kb-status.md` | 新建 |
| `.claude/skills/evolution/commands/kb-archive.md` | 新建 |
| `.claude/skills/evolution/commands/kb-restore.md` | 新建 |
| `.claude/skills/evolution/commands/kb-sync.md` / `growth-sync.md` / `alignment-sync.md` | **删除（#23 命令统一，V4.0.0 移除）** |
| `.claude/skills/evolution/SKILL.md` | 改（命令表 + 知识库描述；删除三个废弃命令行） |
| `.claude/skills/evolution/evolution-export.py` | 改（批次 manifest 记录 + chunk 敏感扫描报告） |
| `.claude/skills/evolution/kb-manager.py` | 新建（validate/migrate/lock/commit/scan/compress/restore + **add/promote/deprecate/resolve/touch 唯一写入口 CLI，F-5/F-7**） |
| `evolution/knowledge-base/pending.md` | 新建 |
| `evolution/knowledge-base/archive/` | 新建（按需） |
| `evolution/knowledge-base/` 8 个详情文件 | 迁移（meta 补齐 + [C] 标记机会） |
| `.gitignore` | 改（`.evolution/`、`*.kb.bak`、`*.kb.tmp-*`） |
| `README.md` / `README.zh-CN.md` | 改（隐私与安全章节） |
| `docsV3/VERSION_HISTORY.md` | 改（v4.0.0 发布记录） |
| `CLAUDE.md` | 改（版本号与知识库描述） |
| `.claude/settings.json` | 建议改（若启用 chunk 扫描 hooks） |

---

**文档结束**
