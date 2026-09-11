# Evolution V4.0.0 同步引擎层设计方案

> ⚠️ **回退横幅（v4.1.2 补记）**：引擎层设计（双游标、批次状态机、完整性校验、原子写入 + 三级恢复链、
> 流式两遍扫描 + k-way 归并、token 安全因子）**仍有效并在用**。
> 但本文档迁移（migration）相关设计中的 `migration.trust_committed` 逃逸阀**未实现**：
> `evolution-export.py` 无产生 migration 批次的 CLI 路径，`config.yaml` 亦无 `migration:` 配置节，
> 该开关仅为未来规划。知识层的 `[P]` 隔离等设计已在 v4.1.0 回退。
> ⚠️ `state-version-newer` 拒绝机制**未实现**（代码无版本比较逻辑，未来版本状态会被静默降级）。仅作未来规划。

> **版本**：draft v2（V4.0.0 同步引擎层）
> **日期**：2026-08-16（v2 修订 2026-08-21）
> **范围**：数据完整性（Critical 1/2/3）+ 代码健壮性（解析防御、流式化、排序、token 估算、可观测性）
> **状态**：已实施（实施日期 2026-08-24）
>
> **v2 修订**：修复评审发现的协议缺陷——N-2 resume 路径"未分析先 commit"、N-3 迁移/failed 批次恢复路径矛盾、N-4 分析失败计数 CLI 落点（F-3）

---

## 0. 现状与根因对照

本文基于 `evolution-export.py`（v3.9.0，`VERSION = "3.4.0"`）、`config.yaml`、`docsV3/EXPORT_AND_ANALYSIS_DESIGN.md`、实际运行中的 `.evolution/chunks/sync-state.json` 分析。

**实测发现**：线上 `sync-state.json` 的 `version` 字段为 `"3.2.1"`，但其结构已是 v3.4.0 文档所述结构（含 `processed_lines`/`processed_bytes`）。即版本标签与 schema 曾发生漂移——迁移逻辑必须把 `3.2.1` 与 `3.4.0` 视为同一结构。

| # | 问题 | 根因 | 修复模块 |
|---|------|------|---------|
| C1 | 增量游标先于知识提取提交，sub agent 中断 → 历史永久丢失 | `export_incremental` 在 sub agent 分析前就推进 `processed_lines` 并保存状态 | A |
| C2 | 游标无完整性校验，截断/轮换 → start_line 越过所有行 → 静默丢数据 | `sha256/mtime/processed_bytes` 存储但不比对 | B |
| C3 | `save_sync_state` 非原子写入，半途崩溃 → 半截 JSON → load 静默回退空状态 → 重复全量导出 | `open(w)+json.dump`；`load_sync_state` 损坏时 `return _empty_state()` 无提示 | C |
| D1 | 错误形状行（null/[]/123）→ `entry.get` 抛 AttributeError → 整次导出崩溃 | `_try_extract_entry` 只捕获 `JSONDecodeError` | D |
| D2 | token 估算偏低 1.3~2 倍，估算 200K 实际 260K~400K | 估算系数无安全系数、无字符数兜底 | D |
| D3 | 全量导出一次性载入全部文件全部条目 → OOM | `all_entries` 跨文件累积 | D |
| D4 | 超大轮次 chunk 时间乱序 | `paginate_entries` 大轮次分支仅当 `current_tokens > min_tokens` 才 flush 当前 chunk，小尾巴被后续轮次拖到大轮次 chunk 之后（详见 D.3） | D |
| D5 | 多 session 聚合不保证时间顺序 | 按文件 mtime 拼接，session 交错时乱序 | D |

**全系统不变式（V4.0.0 起，设计目标）**：

1. 每文件最多一个未提交批次（in-flight）；有未提交批次时该文件增量导出被阻塞（chunk 完好时）。
2. 每文件 `exported_lines >= committed_lines`；`committed_lines` 单调不减。
3. 任何行不允许被未提交/失败批次静默跳过——失败批次必须重生成或显式降级处理。
4. 状态文件所有变更一次原子写入（tmp + fsync + os.replace）。
5. 增量导出起点为 `committed_lines + 1`（不是 `exported_lines + 1`）。
6. 脚本不负责验证知识已入库——commit 是 sub agent 的声明，可靠性由协议（模块 E）+ 人工审核 `[D]` 标记兜底（信任边界，见 E.4）。

---

## 模块 A：双游标 + 批次清单（修复 Critical 1）

### A.1 目标

- 把"脚本已导出"与"知识已入库"解耦为两个游标：`exported_lines` 与 `committed_lines`。
- 每次导出产生一个**批次（batch）**记录（chunk 清单 + 状态机），sub agent 完成分析后通过 `--mode commit` 显式确认。
- 增量导出从 `committed_lines` 起步；发现未提交批次时**优先恢复分析**而非重新导出；失败批次自动重生成，不可被跳过。
- 数据结构版本 `3.4.0 → 3.5.0`，带旧状态迁移。

### A.2 数据结构（JSON Schema 级）

**顶层 `sync-state.json`（version 3.5.0）**：

```json
{
  "version": "3.5.0",
  "schema": "sync-state",
  "last_full_sync": "2026-01-01T00:00:00.000000",
  "last_incremental_sync": null,
  "project_hash": "<project-hash>",
  "batch_seq": 1,
  "files": {
    "<project-hash>/<session-uuid>.jsonl": {
      "path": "…",
      "sha256": "abc123def456…",
      "mtime": 1700000000.0000000,
      "size": 15000000,
      "total_lines": 5000,
      "exported_lines": 5000,
      "exported_bytes": 15000000,
      "committed_lines": 5000,
      "committed_bytes": 15000000,
      "first_event_timestamp": "2026-01-01T00:00:00.000Z",
      "last_event_timestamp": "2026-01-02T00:00:00.000Z",
      "integrity_warnings": 0
    }
  },
  "batches": {
    "inc-20260101-000000-0001": {
      "batch_id": "inc-20260101-000000-0001",
      "mode": "incremental",
      "status": "exported",
      "created_at": "2026-01-02T00:00:00+00:00",
      "updated_at": "2026-01-02T00:00:00+00:00",
      "reason": null,
      "retry_count": 0,
      "analysis_failures": 0,
      "time_range": { "start": "2026-01-02T00:00:00.000Z", "end": "2026-01-03T00:00:00.000Z" },
      "line_ranges": {
        "<project-hash>/<session-uuid>.jsonl": [5001, 5200]
      },
      "chunks": [
        {
          "file": ".evolution/chunks/chunk-inc-20260101-000000-0001-00.md",
          "tokens_est": 60000,
          "tokens_effective": 90000,
          "chars": 180000,
          "entries": 15,
          "time_range": { "start": "…", "end": "…" },
          "line_ranges": { "…jsonl": [5001, 5100] }
        }
      ],
      "commit_receipt": null
    }
  }
}
```

**字段说明与变更对照**：

| 字段 | 旧（3.4.0） | 新（3.5.0） | 语义 |
|------|------------|------------|------|
| `version` | `"3.4.0"` | `"3.5.0"` | 数据格式版本（bump 策略见 A.4） |
| `schema` | — | `"sync-state"` | 顶层标识，防止误读其他 JSON |
| `batch_seq` | — | 整数 | 批次号单调源 |
| `files[k].processed_lines` | 导出即推进 | **改名 `exported_lines`** | 脚本已写入 chunk 的最后 entry 行号（1-based） |
| `files[k].processed_bytes` | 同上 | **改名 `exported_bytes`** | 导出时文件字节数 |
| `files[k].committed_lines` | — | 新增 | sub agent 确认入库的最后 entry 行号 |
| `files[k].committed_bytes` | — | 新增 | commit 时文件字节数 |
| `files[k].size` | — | 新增 | 最近一次校验时的物理文件大小（与 `exported_bytes` 语义分离） |
| `files[k].first_event_timestamp` | — | 新增 | 文件首条 entry 时间戳（便于范围判定与全局排序） |
| `files[k].integrity_warnings` | — | 新增 | 累计完整性警告次数（可观测性） |
| `batches` | — | 新增 | 批次清单，键为 `batch_id` |
| `batches[k].analysis_failures` | — | 新增（F-3/N-4） | 分析失败计数，由 `--mode analyze-failed` 递增；达 `max_analysis_failures` → `failed(analysis-exhausted)` |

**批次状态机**：

```
                 ┌─────────────┐
     导出完成 ──▶│  exported   │── commit ──▶ committed（幂等）
                 │             │
                 └──────┬──────┘
                    resume/start
                        ▼
                 ┌─────────────┐── commit ──▶ committed
                 │  analyzing  │
                 └──────┬──────┘
                        │ 重试达上限 / 显式失败
                        ▼
                 ┌─────────────┐── 重生成（新批次，reason 记录旧批次）──▶ exported
                 │   failed    │
                 └─────────────┘
```

- `exported`：脚本已写盘 chunk 并原子保存状态（exported_lines 已推进）。
- `analyzing`：sub agent 已开始（`--mode start --batch-id` 或增量运行时对旧批次 resume 时置位，仅信息性）。
- `committed`：sub agent 分析完成并通过 `--mode commit` 确认，已推进 `committed_lines`。
- `failed`：重试超限（默认 3 次）或显式失败；`reason` 字段必填（`chunks-missing` / `retry-exhausted` / `superseded` / `deleted` / `migration-unverified` / `analysis-exhausted`（F-3）/ 其他）。
- **failed 批次的 in-flight 判定（N-3）**：failed（非 retry-exhausted）批次**不算 in-flight**——不阻塞其文件的增量导出；其覆盖的行由 A.3 的 failed 重生成循环在下轮重生成新批次（旧批次标 superseded），绝不被静默跳过。retry-exhausted 为终态，等待人工介入。`analysis-exhausted` 同为终态，可经 `--mode commit --force` 显式确认（F-3/N-4）。
- **提交批次修剪**：`committed` 批次保留最近 `keep_committed_batches`（默认 20）个用于审计，更早的从 `batches` 移除（不影响游标，游标在 `files` 中）。

**`--mode commit` 返回的 receipt（A.3）**：

```json
{
  "status": "success",
  "mode": "commit",
  "batch_id": "inc-20260101-000000-0001",
  "committed_at": "2026-01-02T00:35:11+00:00",
  "committed_lines": { "…jsonl": 5200 },
  "receipt_hash": "sha256(规范化 JSON of {batch_id, committed_lines, committed_at})"
}
```

### A.3 流程

**增量导出（改造后 `export_incremental`）**：

```
with file_lock(export.lock):
    state = load_sync_state(state_file)            # C：损坏 → 显式失败，绝不静默空状态
    jsonl_files = find_jsonl_file(project_root)
    integrity = check_integrity(state, jsonl_files) # B：先做完整性校验

    # ── B 触发重导的文件：整文件重导出为新批次 ──
    for f in integrity.need_full_reexport:
        batch = export_file_to_batch(f)             # 从行 1 起全量导出，新批次 status=exported
        state.files[f].committed_lines = 0          # 行号对旧内容已无意义，置 0（保守）
        state.files[f].exported_lines = batch 覆盖行号
        mark_old_inflight_batches(f, failed, reason="superseded")
        warnings.append(integrity_warning(f))

    for f in integrity.deleted:
        mark_old_inflight_batches(f, failed, reason="deleted")
        del state.files[f]                          # 已提交知识在 KB 中，无需恢复
        warnings.append(...)

    for f in integrity.new_files:
        batch = export_file_to_batch(f)             # 新文件：从行 1 全量导出

    # ── A：未提交批次优先恢复，失败批次重生成 ──
    result.pending_batches = []
    for b in state.pending_batches():               # status ∈ {exported, analyzing}
        if batch_chunks_intact(b):
            b.status = "analyzing"                  # resume：chunk 完好 → 交给 orchestrator 继续分析
            result.pending_batches.append(b.batch_id)
        else:
            nb = regenerate_batch(b)                # chunk 缺失 → 按 line_ranges 重新生成
            b.status, b.reason = "failed", "chunks-missing"
            state.batches[nb.batch_id] = nb
            warnings.append(...)

    # ── N-3：failed（非 retry-exhausted）批次的专门重生成循环 ──
    # failed 批次不算 in-flight（不阻塞其文件的新增量导出），但绝不允许其覆盖的行被静默跳过：
    for b in state.batches where status == "failed" and reason not in ("retry-exhausted", "deleted"):
        nb = regenerate_batch(b)                    # migration 批次走整文件重导特判；普通批次按 line_ranges 精确重解析
        b.status = "failed"; b.reason = "superseded"   # 旧批次标 superseded，不再进入本循环
        state.batches[nb.batch_id] = nb             # 新批次 status=exported → 成为该文件唯一 in-flight 批次
        result.pending_batches.append(nb.batch_id)  # 本轮交给 sub agent 分析
        warnings.append(...)
        # 注意：若该文件同时有新增量，增量导出在本轮仍会执行（failed 不算 in-flight）；
        # 新增量的批次与重生成的批次各自独立，行范围不重叠（重生成 ≤ exported_lines，增量 > exported_lines）

    # ── 新增量：仅对【无 in-flight 批次】的文件 ──
    delta = []
    for f in jsonl_files where no_inflight_batch(f):
        entries = parse_jsonl(f, start_line = committed_lines + 1)
        delta.extend(entries)
        # 注意：此文件本轮不推进 exported_lines —— 推进发生在批次建成并保存时

    if not delta and not result.pending_batches and no reexports:
        return success(new_entries=0, action_hint=None)   # “无新内容”
    if not delta and result.pending_batches:
        return success(new_entries=0, action_hint="analyze_pending", pending_batches=[…])

    chunks = paginate_stream(global_timestamp_sort(delta))  # D
    batch = create_batch(mode="incremental", chunks, line_ranges, time_range, status="exported")
    for f in batch.line_ranges:                     # 推进 exported 游标（与批次同一次原子保存）
        state.files[f].exported_lines = batch.line_ranges[f][1]
        state.files[f].exported_bytes = stat_size(f)
    state.batch_seq += 1
    save_sync_state_atomic(state)                   # C：chunk 已写盘，最后落状态
    return success(batch_id, new_entries, chunks, pending_batches, warnings)
```

**核心语义**：

- **增量起点是 `committed_lines + 1`**。`exported` 与 `committed` 之间（未提交批次覆盖）的行不会重新导出——除非批次 chunk 缺失或批次失败，此时**重生成**（按批次 `line_ranges` 精确重解析，源文件未变则 chunk 内容字节级一致），旧批次标记 `failed`。**失败批次的 chunk 与游标不可被正常增量路径跳过**。
- **failed 批次语义（N-3 明确）**：failed（非 retry-exhausted）批次**不算 in-flight**——不阻塞其文件的增量导出；其未确认的行由 A.3 的专门重生成循环在下轮进入重生成（新批次 `status=exported`），旧批次标 `superseded`。retry-exhausted 批次保持 failed 终态，等待人工全量重导或显式强制确认（F-3）。重生成的行范围 ≤ exported_lines、新增量行范围 > exported_lines，二者不重叠，commit 各自独立推进游标。
- **`--mode commit --batch-id <id>`**：

```
with file_lock:
    state = load(...)
    b = state.batches.get(id)
    if b is None:                       → error "batch-not-found"
    if b.status == "committed":         → success（幂等），返回已有 receipt
    if b.status == "failed":            → error "batch-failed"（提示先重生成）
    for f, [start, end] in b.line_ranges.items():
        assert end >= state.files[f].committed_lines     # 只前进
        state.files[f].committed_lines = end
        state.files[f].committed_bytes = size(f)
    b.status = "committed"; b.commit_receipt = {…}
    save_sync_state_atomic(state)
    return receipt
```

- **全量导出也建批次**（mode="full"，一个批次含全部 chunk）：`committed_lines` 保留旧值（新文件为 0），`exported_lines = 末条 entry 行号`。全量导出中途失败 → 下次增量看到未提交 full 批次 → resume；chunk 缺失 → 重生成。旧批次标记 `superseded`。

**子过程 `regenerate_batch(b)`**：对每个 chunk，按 `chunk.line_ranges`（每文件闭区间）重解析（`parse_jsonl` 需新增 `end_line` 参数），重写 chunk 文件（原子写），生成新批次（新 `batch_id`，`retry_count = b.retry_count + 1`）。若 `retry_count >= max_batch_retries`（默认 3）→ 新批次置 `failed, reason="retry-exhausted"`，导出结果 `status=partial` 且 WARN 提示该文件需要全量重导或人工介入。
**migration 特判**：`b.mode == "migration"` 时批次 `line_ranges` 为 null、无法按 chunk.line_ranges 重解析 → 改为**整文件从行 1 重导出**（等价 full-file 重导），生成 `line_ranges: {f: [1, exported_lines]}`，chunk 全部重新分页。

**迁移批次**（旧状态升级产生，见"迁移路径"）：`mode="migration"`，chunk 引用磁盘上遗留的 `chunk-*.md`（`line_ranges` 未知，置 null）；chunk 缺失则走重生成——`regenerate_batch` 对 migration 批次特判为**整文件从行 1 重导出**（生成 `line_ranges: {f: [1, exported_lines]}`，见上），绝不按 null 的 chunk.line_ranges 解析。

**迁移批次 commit 特殊语义（v2 修订，F-1）**：`line_ranges` 为 null 的迁移批次，`--mode commit` 无法遍历行范围推进游标——定义特殊分支：`if b.mode == "migration": committed_lines = exported_lines（按现状确认全部已导出行）`，receipt 中注明 `migration_commit: true`。此分支不回退、不逐文件校验，语义为"旧历史按现状确认入库"（与迁移默认"重分析一次"的目的配合：迁移批次分析完成后一次性确认全部旧行）。

### A.4 版本 bump 策略

- `VERSION` 常量 `"3.4.0" → "3.5.0"`。bump 规则：
  - **minor（3.4→3.5）**：新增可选字段、字段改名但 loader 可容忍——`load_sync_state` 按字段名显式读取并对缺失字段给出默认值 + 迁移函数链。
  - **major**：结构不兼容（如 batches 索引结构改变）——必须写 `MIGRATIONS` 迁移函数，且迁移后立即保存一次。
- `MIGRATIONS` 注册表：`{"3.2.1": migrate_34x_to_350, "3.4.0": migrate_34x_to_350}`（线上文件实际标签是 `3.2.1` 而结构等同 3.4.0，必须同函数处理）。
- 迁移执行：`load` 时若 `version < VERSION` → 依次应用迁移链 → 置 `"3.5.0"` → **在本次运行首次保存时落盘**（迁移本身不立即写盘，避免无操作也写盘；但导出流程必然随后保存）。
- `version > VERSION`（未来版本回退运行旧脚本）→ **拒绝修改**，`status=failed, code=state-version-newer`，只读操作（status）可用。绝不按旧 schema 解释新状态。
- 未知版本 → `failed, code=state-version-unknown`，提示人工处理。

### A.5 边界情况

| 场景 | 行为 |
|------|------|
| sub agent 在 export 后、commit 前中断 | 批次状态 `exported`，chunk 完好 → 下次增量返回 `action_hint=analyze_pending` + 批次清单；**不重新导出** |
| 同上但 chunk 被 cleanup 删除 | 重生成批次（line_ranges 精确重解析），旧批次 `failed(chunks-missing)` |
| failed 批次（非 retry-exhausted）是否阻塞文件增量 | **不阻塞**（不算 in-flight）；下轮由 failed 重生成循环处理，旧批次标 superseded |
| 迁移批次 chunk 缺失 / migration-unverified 批次恢复 | `regenerate_batch` 对 mode="migration" 特判：整文件从行 1 重导出（line_ranges: {f: [1, exported_lines]}） |
| 同一文件出现第二个未提交批次 | 不可能：有 in-flight 批次的文件被跳过（不变式 1）；同文件新行等 commit 后下一轮导出 |
| commit 重复调用 | 幂等 success，返回已有 receipt |
| commit 一个 failed 批次 | error `batch-failed`，指引先重生成 |
| 重生成反复失败（retry ≥ 3） | `failed(retry-exhausted)` + `partial` + WARN，提示人工全量重导 |
| 全量导出中断 | full 批次未提交 → 下次增量 resume；chunk 缺失 → 重生成 |
| 批次时间范围缺失（无 timestamp 条目） | `time_range: null`，排序用 tie-breaker 兜底 |
| 批次数量增长 | committed 批次保留最近 20 个，其余修剪（游标不受影响） |
| `batch_seq` 冲突 | batch_id 含 seq + 时间戳 + 随机 4 位，冲突概率可忽略；冲突时重试新随机数 |

### A.6 验收标准

1. **中断恢复**：跑增量导出（产生批次 B）→ 删除 chunk 之前不 commit → 再跑增量导出 → 断言：`committed_lines` 未变；返回值含 `pending_batches=[B]` 且未生成新 chunk（chunk 完好时）。
2. **失败重生成**：对 B 删除其一个 chunk 文件 → 再跑增量 → 断言：新批次 B' 生成，B 标记 `failed(chunks-missing)`，B' 的 chunk 内容与 B 一致（源文件未变时字节级相同）。
3. **commit 语义**：`--mode commit --batch-id B` → 返回 receipt（含 `receipt_hash`）；`files[f].committed_lines == exported_lines`；再跑增量 → 只导出 committed 之后的新行。
4. **阻塞语义**：B 未 commit 时，同文件追加 10 行 → 增量导出 → 断言 new_entries=0 + pending；commit B 后再增量 → 恰好 10 条。
5. **resume 不跳过分析**（N-2）：跑增量产生批次 B → 置 analyzing（模拟中断）→ 再跑增量 → 断言：返回 pending_batches 含 B，sub agent 协议步骤 2 处理该批次（analyzing 不被过滤），commit 后 committed_lines 前进。
6. **failed 批次不阻塞**（N-3）：批次 B 标 failed(chunks-missing) → 同文件追加 10 行 → 增量导出 → 断言：新行正常导出新批次，且 B 被重生成循环处理（新批次覆盖 B 的行范围，旧 B 标 superseded）。
7. **analyze-failed 计数**（N-4）：对批次连续调用 3 次 `--mode analyze-failed` → 断言第 3 次后状态变 `failed(analysis-exhausted)` 且 WARN；`--mode commit --force` 可确认但输出显著警告且 receipt 含 `forced: true`。
8. **幂等**：重复 commit 同一批次两次 → 两次 success，receipt 一致。
9. **批次修剪**：连续制造 25 个已提交批次 → `batches` 中 committed 批次 ≤ 20，游标正确。
10. **迁移**（见"迁移路径"验收）。

---

## 模块 B：文件完整性校验（修复 Critical 2）

### B.1 目标

- 增量导出前对 state 中已存在的文件做真实性校验：**mtime + size 快速信号 → 未变则跳过 hash；变化则重算 sha256 与 state 比对**。
- 文件变短（截断/轮换）→ 该文件**全量重导** + WARN；hash 变但长度更长 → **保守全量重导** + WARN。
- 与模块 A 交互明确：重导时 exported/committed 游标重置策略。

### B.2 校验决策表

| 信号 | hash | 判定 | 处置 |
|------|------|------|------|
| mtime 同 且 size 同 | （不计算） | 未变（快速路径） | 正常增量逻辑 |
| mtime/size 任一变 | 相同 | 内容未变（mtime 抖动/粒度） | 刷新 mtime/size，正常增量 |
| mtime/size 任一变 | 不同，size < 记录 `size` | **截断 / 轮换** | 该文件全量重导 + WARN |
| mtime/size 任一变 | 不同，size ≥ 记录 `size` | **替换 / 重写** | 保守：该文件全量重导 + WARN |
| 文件在 state 但磁盘不存在 | — | 删除 / 轮换 | 未提交批次标记 `failed(deleted)`；从 `files` 移除；WARN（已提交知识在 KB，无需恢复） |
| 磁盘存在但不在 state | — | 新文件 | 从行 1 全量导出该文件（建批次） |

> 判断依据统一用新字段 `size`（物理大小），不再混用 `exported_bytes`（语义不同：它是"导出时的字节数"，若文件在导出后被替换为更小文件，`exported_bytes` 会误判）。

### B.3 流程（`check_integrity` 伪代码）

> **N-12**：防线 1（chunk 敏感模式扫描，命中只报告）的归属是**导出脚本 evolution-export.py**——批次建成、chunk 落盘后由脚本对每个 chunk 文件执行 `sensitive_patterns` 扫描，命中写入导出结果的 `warnings` 数组（`code: "sensitive-content"`，含 chunk 文件与行号）。不放在 sync 步骤（sub agent）里做：脚本是唯一可靠的执行点，且报告随导出结果结构化返回，不依赖 LLM 自觉。

```
def check_integrity(state, jsonl_files) -> IntegrityReport:
    discovered = {str(f) for f in jsonl_files}
    for key, fi in state.files.items():
        if key not in discovered:
            report.deleted.append(key); continue
        st = Path(key).stat()
        if st.st_mtime == fi.mtime and st.st_size == fi.size:
            continue                                  # 快速路径，跳过 hash
        h = compute_file_sha256(key)
        if h == fi.sha256:
            fi.mtime, fi.size = st.st_mtime, st.st_size   # 刷新元数据
            continue
        fi.integrity_warnings += 1
        if st.st_size < fi.size:
            report.truncated.append(key)
        else:
            report.replaced.append(key)
    for p in discovered:
        if p not in state.files:
            report.new_files.append(p)
    return report
```

**重导处置（与 A 的交互）**：截断/替换文件 `f` 的重导 = 整文件从行 1 解析 → 自包含分页（该文件内部按 timestamp 排序）→ 新批次（mode=`full-file`，`line_ranges` 覆盖 1..末行）→ 置 `committed_lines=0, exported_lines=末行` → 该文件旧 in-flight 批次 `failed(superseded)`。

- 为何重导覆盖行 1 而非 `committed+1`：截断后旧行号无意义，且替换文件可能包含新内容；**已提交部分的知识在 KB 中（`[D]` 条目）**，重复内容由去重兜底，宁可多读不可漏。
- 为何不做"全量重分页所有文件"（全局顺序一致性）代价权衡：任何文件变动都重分页全部文件会让**所有** chunk 边界漂移 → sub agent 全量重分析，token 成本高（~$4）。折中：仅变动文件自包含重导；批次级全局顺序由 orchestrator 按 `time_range.start` 排序分析，KB 去重兜底质量。`config.sync_engine.full_repaginate_on_integrity`（默认 false）可开启强一致性模式。

### B.4 边界情况

| 场景 | 行为 |
|------|------|
| 导出进行中 Claude Code 继续追加文件 | 导出持有的是自建锁，无法阻止 Claude Code 写 JSONL。快照可能不一致 → 下一轮完整性校验（hash 变）自动重导该文件，自愈 |
| mtime 粒度粗（FAT/网络盘） | 快速路径只是优化；即便误判"未变"，hash 比对兜底逻辑在 mtime/size 变化时仍触发；mtime 完全不变但内容变了（罕见）→ 下轮 append 会改变 size，仍会触发 |
| 截断后 `committed_lines` 指向的行已不存在 | committed 知识已在 KB；重导从行 1 重新分析，去重兜底 |
| 文件被轮换为同名新文件（Claude Code 长 session 行为） | 归入 replaced/truncated 分支（按 hash+size 判定），自动重导 |
| 新文件是轮换产物（旧文件已删） | 旧文件 deleted 分支（WARN+清理），新文件 new_files 分支（全量导出） |
| hash 计算耗时（14MB ≈ 数十 ms） | 仅在 mtime/size 变化时计算；正常增量（仅追加）每次都要算一次，可接受 |

### B.5 验收标准

1. **截断检测**：备份 JSONL → 用 `head -n 500` 截断 → 增量导出 → 断言：`status=partial`，WARN 含该文件，文件被全量重导（新批次 line_ranges 从 1 起），`committed_lines=0`。
2. **替换检测**：文件内容整体改写（同长度）→ 增量导出 → 断言同上（保守全量重导）。
3. **快速路径**：文件未动 → 增量导出不计算 hash（可用 monkeypatch 计数器断言 `compute_file_sha256` 未被调用）。
4. **追加路径**：正常追加 N 行（hash 变、size 增）→ 增量导出 → 不触发全量重导，仅增量批次。
5. **删除检测**：state 中的文件移到别处 → 增量导出 → WARN + `files` 中移除 + 相关未提交批次 `failed(deleted)`。
6. **新文件**：放置新 session JSONL → 增量导出 → 新文件从行 1 全量导出为新批次。
7. **自愈**：导出中途手动改写源文件 → 下一轮增量必须触发重导并 WARN。

---

## 模块 C：原子状态写入（修复 Critical 3）

### C.1 目标

- `save_sync_state` 改为 tmp + flush + fsync + `os.replace` 原子模式。
- `.tmp` 残留纳入 `CLEANUP_PATTERNS`。
- `load_sync_state` 对损坏状态**不再静默回退空状态**：明确 WARN + 分级恢复策略。

### C.2 写入流程（改造后 `save_sync_state`）

```
def save_sync_state(state, state_file):
    # 1. 保留上一份好状态（供恢复）
    if state_file.exists():
        shutil.copy2(state_file, state_file.with_suffix(".json.bak"))   # 尽力而为，失败不阻断
    # 2. 写 tmp（与目标同目录 → 同文件系统 → 原子 rename 前提）
    tmp = state_file.with_name(state_file.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state_to_dict(state), f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())                  # 数据落盘
    # 3. 原子替换
    os.replace(tmp, state_file)
    # 4. POSIX 下尽力 fsync 目录；Windows 无此 API，跳过（NTFS rename 原子性足够）
    try:
        dfd = os.open(state_file.parent, os.O_RDONLY); os.fsync(dfd); os.close(dfd)
    except OSError:
        pass
```

- 同一把 `export.lock` 内调用；写失败（磁盘满/权限）→ 抛异常 → `main` 输出 `failed, code=state-write-failed`，**游标不推进**（顺序保证：chunk 先写盘、state 最后写；state 写失败 → chunk 成为孤儿，由 cleanup 删除，无数据丢失语义）。
- chunk 文件本身也原子写（`chunk-….md.tmp` + `os.replace`），防止 sub agent 读到半截 chunk。

### C.3 加载与恢复（改造后 `load_sync_state`）

```
def load_sync_state(state_file) -> SyncState:
    if not state_file.exists():
        print INFO "首次运行，无状态文件"
        return _empty_state()                     # 这是正常首次路径，不是静默回退
    try:
        data = json.load(open(state_file, encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        # —— 不再静默回退空状态 ——
        bak = state_file.with_suffix(".json.bak")
        if bak.exists() and bak 可解析:
            print WARN f"状态文件损坏（{e}），已从 {bak} 恢复；损坏文件已改名保留：sync-state.json.corrupt-{ts}"
            os.replace(state_file, state_file.with_name("sync-state.json.corrupt-" + ts))
            return load_from(bak)                 # 带 recovered_from_backup 标记
        raise StateCorruptError(
            f"状态文件损坏且无可用备份：{state_file}。请修复后重试，或显式执行 --mode full 重新初始化（会重导全部历史，不会静默丢数据）。"
        )
    # schema 校验（v3.5.0）
    if not isinstance(data, dict) or data.get("schema") not in (None, "sync-state"):
        → WARN + 按上述恢复链处理
    # 字段级容错保持（v3.4.0 的 M3 行为不变）：逐字段 get + 类型校验，坏字段跳过并 WARN
```

**恢复策略分级**：

| 损坏情形 | 恢复动作 | 是否静默 |
|----------|---------|---------|
| 文件不存在 | 首次运行，空状态 + INFO | 正常路径（有提示） |
| 解析失败，`.bak` 存在且完好 | 从 `.bak` 恢复 + WARN + 损坏文件改名留存 | 有 WARN，数据不丢 |
| 解析失败，无 `.bak` | **失败退出**（`failed, code=state-corrupt`），提示显式全量重导 | 绝不静默（保留 v3.9.0"禁止误触重置"原则） |
| schema 字段异常 | 逐字段容错 + WARN 汇总 | 有 WARN |

> 注意：`.bak` 是上一版状态（可能落后一个批次）。从 `.bak` 恢复后，丢失的批次会让下一轮增量重生成 chunk（模块 A），不丢数据。

### C.4 清理

`CLEANUP_PATTERNS` 增加临时文件模式：

```python
CLEANUP_PATTERNS = ("chunk-*.md", "chunk-inc-*.md", "sync-state.json", "*.tmp")
```

> ⚠️ **注记（v4.1.6 补记，V4.1.2 变更）**：`CLEANUP_PATTERNS` 已移除 `sync-state.json`
> （防止误删状态文件）。当前实现（`evolution-export.py`）为
> `("chunk-*.md", "chunk-inc-*.md", "*.tmp")`，以上含 `sync-state.json` 的代码块为设计初稿，
> 以实现为准。

- `*.tmp` 覆盖 `sync-state.json.tmp`、`chunk-….md.tmp`。
- 保留 `sync-state.json.bak` 与 `sync-state.json.corrupt-*` 不进清理（恢复用 / 审计用），在 `--mode status` 输出中提示存在。
- 新命名 `chunk-<batch_id>-<i>.md` 前缀仍为 `chunk-`，现有模式匹配不变。

### C.5 边界情况

| 场景 | 行为 |
|------|------|
| save 中途 kill -9 | tmp 残留；原文件完好；下次 cleanup 删除 tmp；下次 save 覆盖 tmp |
| `os.replace` 跨卷 | tmp 与目标同目录 → 同卷，不存在跨卷问题 |
| 磁盘满 | save 抛异常 → `failed, state-write-failed`，游标不推进，chunk 孤儿可清理 |
| 权限/只读目录 | 同上，显式失败 |
| `.bak` 复制失败 | 不阻断主流程（恢复链降级为"无 .bak"分支） |
| 状态文件被外部编辑破坏 | 解析失败 → 恢复链 |
| `--mode status` 读损坏文件 | 同样走恢复链（只读命令不写盘，仅报告） |

### C.6 验收标准

1. **原子性**：循环 200 次 save（每次写入大 JSON），在随机时刻用子进程 kill -9 打断 → 每次结束后 `json.load` 成功，或文件不存在但 `.bak` 可恢复（不允许半截 JSON 留在主文件名下）。
2. **tmp 清理**：手工放置 `sync-state.json.tmp` 与 `chunk-x.md.tmp` → `--mode cleanup` → 均被删除；`.bak`/`.corrupt-*` 保留。
3. **损坏恢复**：手工写坏 sync-state.json（截断一半）且保留 `.bak` → 运行增量 → 断言 WARN + `recovered_from_backup=true` + 行为正常。
4. **无备份失败**：删除 `.bak` 再写坏主文件 → 运行增量 → 断言 `status=failed, code=state-corrupt`，退出码 1，**不产生任何 chunk/状态修改**。
5. **孤儿 chunk**：手工放 `chunk-foo.md`（无批次引用）→ cleanup 删除。

---

## 模块 D：解析防御与流式化（健壮性）

### D.1 解析防御（修复 D1）

**改造前**：

```python
def _try_extract_entry(raw_line, line_num, file_name):
    line = raw_line.strip()
    if not line: return None
    try:
        entry = json.loads(line)
    except json.JSONDecodeError:
        print(WARN); return None
    if entry.get('type') not in ('user', 'assistant'):   # ← null/[]/123 在此处 AttributeError
        return None
    return extract_conversation_content(entry, line_num) # ← entry 为 dict 但 message/content 形状异常也会炸
```

**改造后**：

```python
def _try_extract_entry(raw_line, line_num, file_name, stats: ParseStats) -> Optional[ConversationEntry]:
    line = raw_line.strip()
    if not line:
        stats.blank += 1; return None
    try:
        entry = json.loads(line)
    except json.JSONDecodeError:
        stats.json_decode_errors += 1
        warn_rate_limited(file_name, line_num, "JSON 解析失败"); return None
    if not isinstance(entry, dict):                      # ← 新：null/[]/123/true
        stats.not_dict += 1
        warn_rate_limited(file_name, line_num, f"条目形状异常（{type(entry).__name__}），已跳过"); return None
    try:
        if entry.get('type') not in ('user', 'assistant'):
            stats.wrong_type += 1; return None
        return extract_conversation_content(entry, line_num)
    except (AttributeError, TypeError, KeyError, ValueError) as e:
        stats.extract_errors += 1
        warn_rate_limited(file_name, line_num, f"内容提取失败：{e}"); return None
```

配套加固 `extract_conversation_content`：

- `msg = entry.get('message')`；`if not isinstance(msg, dict): msg = {}`。
- `content = msg.get('content', '')` 非 str 且非 list → 按空处理。
- `block.get('thinking'/'text'/'content')` 非 str → `str()` 强转（`errors='replace'` 语义），杜绝 `len(non-str)` TypeError。
- `timestamp` 非 str → 取 `str()`，否则置空串。
- 每文件错误行数统计进 `ParseStats`，导出结果携带 `parse_stats`（可观测性，见 E）。

**`ParseStats` 结构**：

```json
{
  "total_lines_read": 5200,
  "blank": 2,
  "json_decode_errors": 0,
  "not_dict": 0,
  "wrong_type": 402,
  "extract_errors": 0,
  "extracted_entries": 215
}
```

`wrong_type` 占总量超过阈值（如 > 50%）→ 结果 `status=partial` + WARN"文件可能不是 Claude Code 会话格式"。

### D.2 流式全量导出（修复 D3）

**内存模型**：任一时刻仅持有（a）每个文件的**一个生成器**（流式解析，O(1)），（b）当前轮次缓冲，（c）当前 chunk + 上一个 chunk（尾部合并用 lookbehind=1，**缓冲中的 chunk 在确认不被合并前不落盘**——见 D.2 伪代码 N-11 说明）。不再有跨文件 `all_entries` 累积。

**两遍扫描 + k-way 合并（保持全局时间序，见 D.5）**：

```
pass 1（元数据，O(1) 内存）:
    for f in files:                       # mtime 序
        流式统计 total_lines / entry 数 / first_ts / last_ts / 时间戳是否单调
pass 2（合并导出）:
    gens = [parse_jsonl(f, 0) for f in files]          # N 个生成器，文件句柄 N 个（Windows 上限 512，够用）
    heap = heapq.merge(*gens, key=lambda e: sort_key(e))   # key = (normalized_ts, file_index, line_no)
    paginate_stream(heap) → chunk 满 → 原子写 chunk-<batch_id>-<i>.md → 继续
    批次建成后原子保存 state（模块 C）
```

- 源文件在 pass1/pass2 之间被追加 → 快照轻微不一致 → 下一轮完整性校验自愈（B.4）。
- 单文件仍可能很大：pass 2 中单文件条目在生成器内流转，不驻留内存；若单个文件大到无法接受（如 >200MB），记录为已知扩展项（外部排序），本期不实现。

**流式分页器 `paginate_stream(entry_iter, ...)`（改造 `paginate_entries`）**：

```
cur_chunk, cur_turn, cur_session = [], [], None
last_chunk = None                                    # lookbehind=1 缓冲（M1 尾部合并用）；
                                                     # ★ N-11：缓冲中的 chunk 尚未落盘，
                                                     # 只有确认不再被合并时才原子写盘

for e in entry_iter:                                 # 已全局时间序
    if e.session != cur_session:                     # 换 session → 关闭当前轮次（D.5 关键）
        flush_turn()
    elif e.role == 'user' and cur_turn:
        flush_turn()                                 # 同 session 新 user → 关闭当前轮次
    cur_turn.append(e)

flush_turn():
    if cur_chunk and chunk_tokens(cur_chunk) + turn_tokens(cur_turn) > target:
        flush_chunk()
    if turn_tokens(cur_turn) > max_tokens:
        flush_chunk(force=True)                      # ★ 无条件先 flush（修复 D4 时间乱序）
        for st in split_large_turn(cur_turn, max_tokens):
            emit_chunk(st)                           # 每个 sub_turn 独立成 chunk
    else:
        cur_chunk.extend(cur_turn)

flush_chunk(force=False):
    if not cur_chunk: return
    emit_chunk(cur_chunk)

emit_chunk(c):
    if last_chunk and tokens(last_chunk)+tokens(c) <= max_tokens
       and tokens(last_chunk) < min_tokens:          # M1：小尾巴并入上一块（仅当合并不超限）
        last_chunk.extend(c)                         # 只改内存缓冲，不落盘（N-11）
    else:
        if last_chunk is not None:
            write_chunk(last_chunk)                  # 缓冲确认不再被合并 → 此时才原子写盘
        last_chunk = c

finalize():                                          # 流结束后必须调用
    if last_chunk is not None:
        write_chunk(last_chunk)                      # 冲刷最后一个缓冲 chunk
```

> **N-11 说明**：旧伪代码在 `emit_chunk` 中立即 `write_chunk(c)`，而后续 chunk 仍可能通过 M1 合并进 `last_chunk`——已落盘文件会被二次改写，破坏"chunk 一旦落盘即不可变"的批次不变式（manifest sha256 失效）。修复：**缓冲一个 chunk 再落盘**——仅当下一个 chunk 到来且不发生合并时才把缓冲写入磁盘；流结束时 `finalize()` 冲刷尾部。代价是任一时刻多驻留一个 chunk 的内存（有界）。

### D.3 超大轮次时间乱序修复（D4）——根因与改法

**根因**（现 `paginate_entries` 大轮次分支）：

```python
if turn_tokens > max_tokens:
    if current_chunk and current_tokens > min_tokens:   # ← 小尾巴不 flush
        chunks.append(current_chunk); current_chunk = []
    sub_turns = split_large_turn(...)
    for st in sub_turns: chunks.append(st)              # 大轮次 chunk 先入列
```

当大轮次到来时 `current_chunk` 不足 `min_tokens` 而**不 flush**，它被后续轮次内容继续填充，最终排在**大轮次 chunk 之后**——最后一个 chunk 的时间范围（含大轮次之前的旧条目）倒挂于前面 chunk 之前。**修复**：遇大轮次**无条件**先 flush（`force=True`），`min_tokens` 合并逻辑只保留在 `emit_chunk` 的 lookbehind 尾部合并中（合并目标是"紧跟其后的前一块"，且受 `max_tokens` 约束，不会破坏顺序——见 D.2 伪代码）。

**验收断言**：对任意导出结果，`chunk[i].time_range.end <= chunk[i+1].time_range.start`（闭区间首尾），含超大轮次样本。

### D.4 Token 估算修正（D2）

- 引入 `sync_engine.estimate_safety_factor`（默认 **1.5**，config 可调）。分页决策一律使用 `tokens_effective = estimate × factor`（目标 90K、硬上限 200K 均作用在 effective 上）。
- 依据：对抗性审核测得 1.3~2 倍低估；1.5 因子下 effective 200K ≈ 实际 260K~400K 中段，仍在 1M sub agent 窗口内（上限是质量软约束而非崩溃阈值）。
- 第二道保险：`max_chunk_chars = max_chunk_tokens × 4`（默认 800K 字符，英文最坏 4 字符/token 推导）作为估算器彻底失效时的硬守卫——chunk 字符数超限立即按轮次边界截断。
- chunk 记录 `tokens_est`（原始估算）与 `tokens_effective`（乘因子后）与 `chars`，供后续用真实 tokenizer 标定系数。
- `truncate_entry` / `split_large_turn` 的预算同样使用 effective。

### D.5 全局时间戳排序（D5）

- **排序键**：`(normalized_timestamp, file_index, line_no)`。
- `normalized_timestamp`：优先 `datetime.fromisoformat`（兼容 `Z` 与 `+08:00`，统一为微秒整数）；解析失败/缺失 → 归入"未知时间"桶，置于同批次尾部且保持 (file_index, line_no) 相对序（确定性）。
- **不再依赖文件 mtime 拼接顺序**（mtime 仅用于文件发现顺序和 pass1）。
- **轮次分组必须 session 感知**（全局排序后不同 session 条目交错，旧 `group_into_turns` 会把 A session 的 user 与 B session 的 assistant 拼成一轮——现代码亦有此隐患）：轮次切换条件 = 新 user 条目（同 session）**或** session 变化（见 D.2 `flush_turn`）。
- 增量路径同样全局排序 delta（多 session 各推少量行时保证 chunk 内时间序）。

### D.6 边界情况

| 场景 | 行为 |
|------|------|
| null/[]/123/true 行 | 跳过 + 计数（`not_dict`），不崩溃 |
| `message` 非 dict / `content` 非 str 非 list | 空处理，不崩溃 |
| `timestamp` 缺失/非 str/格式混用（Z vs 偏移） | 规范化；无法解析进未知桶 |
| 单 entry > max_tokens | `truncate_entry` 兜底（已有 M2，改用 effective 预算） |
| 超大轮次（>max） | 无条件 flush + sub_turns 独立 chunk（D.3） |
| 轮次跨 session | session 感知分组（D.5） |
| 全坏行文件 | 全部跳过，`parse_stats` 显示；占比过高 → `partial` + WARN |
| 同 timestamp 多条 | tie-breaker (file_index, line_no) 确定有序 |
| 非 UTF-8 字节 | `errors='replace'`（现有） |
| 尾部小 chunk | lookbehind 合并，不超 max（M1 语义保留）；合并目标为**尚未落盘的缓冲 chunk**（N-11），落盘后不可变 |
| 单文件超大（>200MB） | 本期接受（生成器流转），扩展项：外部排序 |

### D.7 验收标准

1. **坏行不崩**：构造含 `null`、`[]`、`123`、`{"type":1}`、`{"message":"x"}` 行的 JSONL → 全量导出 success（或 partial），`parse_stats` 计数正确，无异常栈。
2. **内存上界**：用 `tracemalloc` 或 `/proc` 峰值 RSS 断言全量导出峰值内存与文件数无关（两遍扫描 + 单 chunk），对 3 个 15MB 文件与 1 个 15MB 文件峰值内存差 < 2×。
3. **时间序**：构造两个时间交错的 session 文件（A 后段时间早于 B 前段）→ 全量导出 → 断言 chunk 内 entry timestamp 全局非降序，且 chunk 间时间范围不重叠回退。
4. **超大轮次**：构造单轮 500K token 的会话 → 导出 → 断言所有 chunk 时间范围单调（D.3 断言）。
5. **跨 session 轮次**：交错 session 的用户/助手消息 → 断言任何 chunk 内的轮次不混 session。
6. **token 因子**：纯 CJK 大文本 chunk → 断言 `tokens_effective ≤ 200K` 且 `chars ≤ 800K`；调整 config 因子 → 行为随之变化。
7. **增量全局排序**：两 session 各追加行，时间交错 → 增量 chunk 内时间非降序。
8. **chunk 落盘后不可变**（N-11）：构造触发 M1 尾部合并的样本（小尾巴 chunk 后跟正常 chunk）→ 断言每个 chunk 文件只被写入一次，manifest 中 sha256 与最终文件内容一致。

---

## 模块 E：命令与可观测性协议

### E.1 目标

- 脚本返回状态扩展为明确的 `success / partial / failed` 语义 + 结构化 `warnings`。
- 定义主 agent ↔ sub agent 的批次生命周期协议：**sub agent 必须回报 commit receipt 才算成功**。
- 用户可见错误信息规范化（现象/原因/影响/恢复动作），不再静默成功。

### E.2 脚本返回协议

**退出码**：`0 = success`；`1 = failed`（中止）；`2 = partial`（完成但有数据质量警告，sub agent 必须把 warnings 带给主 agent 并报告用户）。

> ⚠️ **注记（v4.1.6 补记，V4.1.2 变更）**：退出码协议已简化为 0/1——`partial` 亦以 0 退出
> （由返回 JSON 的 `status` 字段区分），`2 = partial` 不再使用。
> 权威定义见 `.claude/skills/evolution/commands/sync.md` 的"退出码协议"，以上 `2 = partial`
> 与 E.6 验收标准中的"断言 2"为设计初稿，以实现为准。

**`status` 字段语义**：

| status | 含义 | sub agent 动作 |
|--------|------|---------------|
| `success` | 数据完整，批次已建（或无新内容），无警告 | 继续分析批次（如有）→ commit |
| `success` + `new_entries: 0` | 无新内容 | 报告"无更新"（含 pending 提示） |
| `partial` | 导出完成但含完整性/解析警告（重导、坏行占比、retry-exhausted 等） | 必须向主 agent 报告 warnings，再继续分析 |
| `failed` | 中止（锁超时、state-corrupt、无 JSONL、校验失败） | 停止并报告，不得继续 |

**导出结果新增字段**：

```json
{
  "status": "success",
  "mode": "incremental",
  "new_entries": 215,
  "parse_stats": { "...": "见 D.1" },
  "warnings": [
    { "code": "file-truncated", "file": "…jsonl", "detail": "size 15000000 → 180000, 已全量重导", "action": "建议人工确认该 session 是否被轮换" }
  ],
  "batches": [
    { "batch_id": "inc-20260101-000000-0001", "status": "exported", "chunks": 1, "entries": 215,
      "time_range": { "start": "…", "end": "…" }, "retry_count": 0 }
  ],
  "pending_batches": [],
  "action_hint": "analyze_and_commit" | "analyze_pending" | null,
  "sync_state": { "version": "3.5.0", "...": "摘要" }
}
```

**新增/变更 CLI**：

| 模式 | 说明 |
|------|------|
| `--mode incremental` | 增量导出（自动处理 pending/failed 批次重生成） |
| `--mode full` | 全量导出（建 full 批次） |
| `--mode commit --batch-id <id>` | 批次确认入库，推进 committed 游标，返回 receipt（A.3） |
| `--mode commit --batch-id <id> --force` | **强制确认（F-3/N-4）**：跳过分析直接确认批次。输出显著警告"强制确认将永久跳过该批次未分析内容"，要求 receipt 中记录 `forced: true` 供审计。仅用于 `failed(analysis-exhausted)` 或用户明确指示的场景 |
| `--mode analyze-failed --batch-id <id>` | **（F-3/N-4）**：报告一次分析失败——递增该批次 `analysis_failures` 计数；达到上限（`max_analysis_failures`，默认 3）时状态置为 `failed(analysis-exhausted)` 并 WARN 提示人工介入（`--force` 强制确认或等 failed 重生成循环） |
| `--mode start --batch-id <id>` | （可选）标记 analyzing，仅信息性 |
| `--mode status [--verify]` | 状态 + 批次摘要；`--verify` 额外执行完整性检查（只读 hash 比对）；输出含各批次 `analysis_failures` 计数（F-3 可观测性） |
| `--mode cleanup` | 清理（含 `*.tmp`，见 C.4） |

> F-3 liveness 协议：sub agent 每次对某批次分析失败（chunk 读不到、上下文超限、中途崩溃前）都应调用 `--mode analyze-failed --batch-id <id>` 落计数；主 agent 摘要连续 2 轮缺 receipt → WARN"批次 X 连续未确认"；`analysis_failures >= 3` → 批次自动转 `failed(analysis-exhausted)`，退出阻塞循环（liveness 保证）。

### E.3 主 agent ↔ sub agent 协议（sync.md / SKILL.md 需同步更新）

```
主 agent 触发 /evolution
    ↓
sub agent:
  1. python evolution-export.py --mode incremental
     ├─ exit 0 + status=success, new_entries=0  → 若 pending_batches 非空 → 跳到 2（针对 pending 批次继续分析，N-2）
     ├─ exit 0 + status=success, action_hint=analyze_and_commit → 进入 2
     ├─ exit 0/2 + partial → 先向主 agent 转述 warnings，再进入 2/3
     └─ exit 1 + failed → 停止，向主 agent 报告 {code, message, action}
  2. 对 result.batches ∪ result.pending_batches 中 status ∈ {exported, analyzing} 的每个批次
     分析（不按 status 过滤——resume 置位后的批次状态是 analyzing，
     若只处理 exported 会"未分析先 commit"，N-2 已修复）：
     a. 逐个读取批次 chunks（路径只取自批次 manifest，禁止手动 glob）
     b. 逐 chunk 分析 → 经 kb-manager.py add 写入知识库（[P] 隔离，F-5 唯一写入口）
  3. python evolution-export.py --mode commit --batch-id <id>
     ├─ exit 0 → 记录 receipt {batch_id, receipt_hash}
     └─ 非 0 → 该批次视为未完成，报告主 agent（下轮 /evolution 自动恢复）
  4. 最终摘要必须包含：批次 id、chunk 数、提取知识数（按类别）、commit receipt（batch_id + receipt_hash）
    ↓
主 agent：
  - 摘要中缺 receipt 或 receipt 校验失败 → 判定本次同步未完成，提示用户重跑或检查
```

**错误信息规范**（所有 `failed/partial` 的用户可见输出遵循）：

```
[现象] 状态文件损坏：.evolution/chunks/sync-state.json（JSON 解析失败）
[原因] 上一次写入被中断或磁盘异常
[影响] 无法安全推进同步游标，本次导出已中止，未做任何修改
[恢复] 自动尝试了 .bak 恢复但失败；请检查该文件后重试，或显式执行：
       python evolution-export.py --mode full   （将全量重导历史，不会静默丢数据）
```

`warnings` 数组元素统一含 `code / file / detail / action` 四字段。

### E.4 信任边界（必须文档化）

- 脚本**无法验证**知识已真实写入 KB——commit 是 sub agent 对"已入库"的声明（协议约束），可靠性由以下兜底：① receipt 必须回报给主 agent（协议）；② 知识条目标记 `[D]` 等待人工审核（现有机制）；③ 批次重生成/重分析是幂等的（KB 去重）。
- 批次提交后游标即前进；若 sub agent 虚假 commit（分析未做），数据仍会丢失——该风险用 `[D]` 审核 + 主 agent 摘要核对缓解，不接受脚本侧更强的验证（无法实现）。

### E.5 边界情况

| 场景 | 行为 |
|------|------|
| sub agent 未回报 receipt | 主 agent 判定同步未完成，下轮恢复（批次仍在） |
| sub agent 分析反复失败 | `--mode analyze-failed` 递增 `analysis_failures`；达上限 → `failed(analysis-exhausted)` + WARN（F-3/N-4） |
| 用户对 analysis-exhausted 批次强制确认 | `--mode commit --force`：输出显著警告"强制确认将永久跳过该批次未分析内容"，receipt 记录 `forced: true` |
| commit 时批次已是 committed | 幂等 success |
| commit 时批次 failed | error `batch-failed` + 恢复指引 |
| 脚本被并发调用（两个 sub agent 同时跑） | `export.lock` 超时 → failed(lock-timeout)，明确报错 |
| `--mode status` 显示未提交批次 | `pending_batches` 高亮，提示继续分析；连续 2 轮未确认的批次显著 WARN（F-3） |
| cleanup 删除未提交批次 chunk | 下轮增量自动重生成（A.3） |
| `parse_stats` 异常占比高 | `partial` + WARN，sub agent 转述用户 |

### E.6 验收标准

1. **协议端到端**：脚本化模拟 sub agent（bash：incremental → 读批次 → commit → status）→ 全程断言 exit code 与 JSON 字段。
2. **退出码**：各错误场景（无 JSONL、锁超时、state-corrupt、batch-not-found）断言退出码 1；含警告场景（截断）断言 2；正常断言 0。
3. **receipt 幂等**：commit 两次 → 相同 `receipt_hash`。
4. **未回报检测**：跑 incremental 不 commit → `--mode status` 的 `pending_batches` 非空且含该批次。
5. **错误信息四要素**：人为制造 state-corrupt 与 file-truncated → 断言输出含 现象/原因/影响/恢复 与 `code/file/detail/action`。

---

## 迁移路径（旧 sync-state.json → v3.5.0）

### 输入（实测线上样例：version 标签 `"3.2.1"`，结构 = v3.4.0 文档结构）

```json
{
  "version": "3.2.1",
  "last_full_sync": "2026-01-01T00:00:00.000000",
  "last_incremental_sync": null,
  "project_hash": "<project-hash>",
  "files": { "<project-hash>/<session-uuid>.jsonl": {
      "path": "…", "sha256": "abc123def456...", "mtime": 1700000000.0,
      "total_lines": 5000, "processed_lines": 5000,
      "processed_bytes": 15000000, "last_event_timestamp": "…" } }
}
```

### 迁移函数 `migrate_34x_to_350(old) -> new`（3.2.1 与 3.4.0 共用）

```
new.version = "3.5.0"; new.schema = "sync-state"
new.batch_seq = 1
for k, f in old.files:
    new.files[k] = {
        path, sha256, mtime, total_lines,
        exported_lines = f.processed_lines,
        exported_bytes = f.processed_bytes,
        committed_lines = 0,                  # ★ 旧游标在分析前已推进，不可信 → 保守置 0
        committed_bytes = 0,
        size = f.processed_bytes,             # 无独立 size 记录，以 processed_bytes 近似
        first_event_timestamp = null,         # 旧状态未存首条时间戳，重导时回填
        last_event_timestamp = 原值,
        integrity_warnings = 0
    }
# ★ 迁移批次：让下一次增量对全部已导出行重新确认（重分析一次，KB 去重兜底）
if 输出目录存在 chunk-*.md 文件（且未被批次引用）:
    batches["mig-<ts>-<seq>"] = {
        batch_id, mode="migration", status="exported", reason=null,
        line_ranges = null,                   # 旧 chunk 无行范围信息
        chunks = [遗留 chunk-*.md 按文件名序引用, line_ranges 全 null],
        time_range = null, commit_receipt = null, retry_count = 0
    }
else:
    # 无遗留 chunk → 建占位批次，下轮增量由 failed 重生成循环处理（N-3）：
    # migration 批次重生成特判为整文件从行 1 重导出（line_ranges: {f: [1, exported_lines]}）
    batches["mig-<ts>-<seq>"] = { …, status="failed", reason="migration-unverified" }
```

**failed 迁移批次的恢复路径（N-3 明确）**：`status=failed, reason=migration-unverified` 的迁移批次**不算 in-flight**（不阻塞其文件增量导出）；A.3 的 failed 批次专门重生成循环会在下一轮将其 `regenerate_batch`（migration 特判：整文件从行 1 重导出），旧批次标 `superseded`，新批次正常进入分析。

**保守默认的代价与逃逸阀**：

- 默认（`config.sync_engine.migration.trust_committed = false`）：迁移后**下一次增量同步会对全量历史重新分析一次**（chunk 复用遗留文件或重生成），成本 ≈ 一次全量分析（~$4，KB 去重后新增条目少）。安全、有界。
- 逃逸阀：用户在确认知识库已完整的情况下，设 `migration.trust_committed: true` → 迁移时 `committed_lines = exported_lines`，且不建迁移批次（零额外成本）。此开关必须显式设置，且迁移报告输出 `migration_mode: "trusted"` 供审计。

> ⚠️ **实现状态（v4.1.2 核实）**：上述 `migration.trust_committed` 逃逸阀**未实现**——
> `evolution-export.py` 中不存在产生 `mode="migration"` 批次的 CLI 路径（仅 `full` / `incremental` 会建批次），
> `config.yaml` 也无 `migration:` 配置节。本段属设计承诺，尚未落地，勿据以配置。

**降级迁移（结构完全不同，如 `last_sync/file_info/stats/export_history` 时代）**：`MIGRATIONS` 无对应函数 → `failed, code=state-version-unknown` + 明确指引（备份后 `--mode full`）。

**迁移验收**：

1. 用线上样张（3.2.1 标签）→ 首次运行增量 → 断言：版本变 3.5.0；`committed_lines=0`；迁移批次存在；导出结果引用迁移批次且 chunk 内容与遗留文件一致（或重生成）。
2. 迁移后 commit 迁移批次 → `committed_lines` 前进至旧 processed_lines；再增量 → 只导出真正新增行。
3. `trust_committed: true` → 迁移不建批次，committed = exported，零重分析。
4. 模拟未来版本（version 4.0.0）状态 → 旧脚本运行 → 拒绝修改（`state-version-newer`）。
5. 迁移不丢 `last_full_sync / last_incremental_sync / project_hash`。
6. **failed 迁移批次恢复**（N-3）：构造无遗留 chunk 的迁移 → 断言产生 `failed(migration-unverified)` 批次 → 下一轮增量该文件不被阻塞、failed 重生成循环产出新批次（整文件 line_ranges 从 1 起）、旧批次标 superseded。

---

## 实施顺序与工作量评估

| 阶段 | 内容 | 依赖 | 工作量 |
|------|------|------|--------|
| P0 | 测试脚手架：构造 JSONL fixture、状态文件 fixture、坏行/截断/中断模拟工具、端到端脚本化 sub agent 模拟 | — | 0.5 人日 |
| P1 | 模块 C：原子写入、load 恢复链、`.bak`/`.tmp`/cleanup、chunk 原子写 | P0 | 0.5 人日 |
| P2 | 模块 D-1：`_try_extract_entry` 防御 + `ParseStats` + 提取函数加固 | — | 0.5 人日 |
| P3 | 模块 A：schema 3.5.0、双游标、批次状态机、`--mode commit/start`、重生成、迁移函数与迁移批次 | P1 | 1.5~2 人日 |
| P4 | 模块 B：`check_integrity` + 重导交互 + 决策表实现 | P3 | 1 人日 |
| P5 | 模块 D-2/D-3/D-4/D-5：流式分页、大轮次修复、全局排序（k-way）、session 感知轮次、token 因子 | P2（独立） | 1.5~2 人日 |
| P6 | 模块 E：退出码、warnings、协议文档化、sync.md/SKILL.md 更新（含 F-3 analyze-failed / commit --force CLI） | P3/P4 | 0.5 人日 |
| P7 | 全量验收：每个模块验收标准逐条跑通 + 线上真实数据回归 | 全部 | 1 人日 |

**总计：约 6~8 人日。** 建议顺序 P0 → P1 → P2 → P3 → P4 → P5 → P6 → P7；P2 与 P5 可并行。

**风险与缓解**：

| 风险 | 缓解 |
|------|------|
| 迁移后默认重分析一次的全量成本（~$4）引发用户不满 | 逃逸阀 `trust_committed` + 明确 WARN 说明原因 |
| k-way 合并对大量 session 文件（>100）句柄压力 | 实测上限；超限回退为分块合并（扩展项） |
| 单文件 >200MB | 接受（生成器流式），列为外部排序扩展项 |
| `estimate_safety_factor` 取值偏差 | 因子可配置；chunk 记录 `tokens_est/effective/chars` 供真实 tokenizer 标定 |
| Windows `os.replace` 对打开文件的写入者 | 状态文件无长期持有者（脚本进程内读写），冲突面小 |

---

## 附录 A：config.yaml 新增项

```yaml
# 同步引擎（V4.0.0）
sync_engine:
  estimate_safety_factor: 1.5        # token 估算安全系数（对抗性审核测得低估 1.3~2 倍）
  max_chunk_chars: 800000            # 字符数硬守卫 = max_chunk_tokens × 4
  max_batch_retries: 3               # 批次重生成上限，超限 failed(retry-exhausted)
  max_analysis_failures: 3           # 批次分析失败上限，超限 failed(analysis-exhausted)（F-3/N-4）
  keep_committed_batches: 20         # 已提交批次审计保留数
  full_repaginate_on_integrity: false# 完整性重导时是否全量重分页（强一致，贵）
  migration:
    trust_committed: false           # 迁移时信任旧 processed_lines 已入库（跳过重分析）
```

## 附录 B：CLEANUP_PATTERNS / 文件命名变更

```python
CLEANUP_PATTERNS = ("chunk-*.md", "chunk-inc-*.md", "sync-state.json", "*.tmp")
# 保留：sync-state.json.bak、sync-state.json.corrupt-*
# chunk 命名：chunk-<batch_id>-<i:02d>.md（batch_id 前缀模式仍被 chunk-*.md 覆盖）
```

> ⚠️ **注记（v4.1.6 补记，V4.1.2 变更）**：同 C.4 注记，`sync-state.json` 已从
> `CLEANUP_PATTERNS` 移除，当前实现为 `("chunk-*.md", "chunk-inc-*.md", "*.tmp")`。

## 附录 C：与现有文档/命令的接口变更清单

- `docsV3/EXPORT_AND_ANALYSIS_DESIGN.md`：4.6 状态管理章节、4.8 错误矩阵、8.x 执行流程需随 V4 更新（后续版本任务）。
- `.claude/skills/evolution/commands/sync.md`：加入批次 commit 步骤与 receipt 回报要求（模块 E.3，含 N-2 修订：步骤 2 处理 exported/analyzing 全部批次；F-3：分析失败调用 `--mode analyze-failed`）。
- `.claude/skills/evolution/SKILL.md`：规则表补充"批次必须 commit 才算完成"。

---

**文档结束**
