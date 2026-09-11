# Evolution V4.0.0 — Knowledge Layer Design (Knowledge Quality Defense Line + Command Protocol)

🌐 **Language / 语言**: [English](design-v4-knowledge.md) | [中文](design-v4-knowledge.zh-CN.md)

> ⚠️ **Rollback banner (v4.1.2 note)**: **Most of the knowledge-layer design described in this document was rolled back in v4.1.0 and does not exist in the current implementation**:
> `[P]` quarantine and pending.md, the four-tier status model (`[P]/[D]/[V]/[X]/[C]/blocked`), the `kb-manager.py` sole write entry point,
> the knowledge lifecycle, the sensitive-data scan gate, the transaction-lock write path, and the proactive review flow.
> The current system uses the V3 lightweight rules: three-tier status `[D]/[V]/[X]` + manual review via `read.md` / `write.md` / `dedup.md`.
> This document is a design-history reference only; do not implement it.

> **Version**: 4.0.0-draft v2 (initial draft 2026-08-16; v2 revision 2026-08-21)
> **Status**: Implemented (implementation date 2026-08-24)
> **Positioning**: Resolve the 6 knowledge-layer issues found by adversarial review (1/2/3/4/5/6)
> **Scope**: Four-tier status model and [P] quarantine, knowledge lifecycle, transactions and concurrency, command protocol and proactive review, privacy and security
>
> **v2 revision (N-7 systematic revision)**: The initial draft was written before the F-4/F-5/F-7 decisions in master outline v2 were finalized, and lagged in several places. v2 has been aligned:
> - **F-5 sole write entry point**: The write.md draft and Sequence 1 are changed so that the LLM only submits candidate text to `kb-manager.py add`; the script is responsible for sensitive-data scan / deduplication / conflict determination / lock-held transaction / atomic replacement — the LLM never directly edits knowledge base markdown
> - **#23 command unification**: D.1 deletes `/kb-sync` `/growth-sync` `/alignment-sync` (removed in V4.0.0)
> - **B.5 manifest schema aligned with engine A.2**: `batch_id/chunks[].file` (no longer `run_id/files[].name`)
> - **N-10/N-11/E.3 regex unification**: `local_path` defaults to `enabled: false`; regexes are consistent with the engine-layer references
> - **N-13 kb-meta escaping rules**: free-text fields such as scope are encoded as JSON strings
> - **N-14**: kb-index line limit unified to 500
> - **N-6**: blocked entries are persisted only in redacted form; the original value is never written to disk

---

## 0. Problem Mapping and Design Goals

| # | Adversarial review issue | This design module | Core countermeasure |
|---|----------------|-----------|----------|
| 1 | [D] drafts usable by default → self-reinforcing loop | Module A | New entries always enter the quarantine area `[P]` (pending.md) and by default do not participate in decisions |
| 2 | [V] verification semantics too broad | Module A | Evidence-type classification + freshness + scope binding; tighten [V] conditions |
| 3 | Unverified new knowledge can eliminate verified facts | Module A | Forbid [P]/[D] from eliminating [V]; keep conflicts side by side marked `[C]` for human arbitration |
| 4 | Writes have no transaction protection | Module C | `.kb.lock` + temporary copy + validation + atomic replacement |
| 5 | Knowledge base has no lifecycle | Module B | Health scan, stale archiving, capacity monitoring, chunk GC |
| 6 | Sensitive conversations persisted before review | Module E | Export scan (report) + write gate (intercept/redact; blocked persisted only in redacted form, N-6) + README disclosure |

Overall design principle (continuing V3): **All knowledge base operations are performed by a sub agent in the background; all writes go through the kb-manager.py sole write entry point (F-5), transactional under lock; humans only do "minimum-cost batch review"; default is archive-only, never auto-delete**.

---

## Module A: Four-Tier Status Model + [P] Quarantine (fixing the self-reinforcing loop)

### A.1 Status Model Definition (decision)

**Key decision 1: Add `[P]` pending; the first stop for all AI-auto-extracted entries must be `[P]`, physically isolated.**
**Key decision 2: Keep `[D]`, but tighten its semantics — `[D]` = entries that have passed human review but lack sufficient evidence (no tool output / explicit confirmation / external document). The old semantics ("AI-extracted, unverified") overlap with `[P]` and are abolished; existing old `[D]` entries go through migration (A.6).**
**Key decision 3: `[C]` conflict is not stored separately but is an overlay marker — both conflicting sides keep their original file and original status, their titles are marked side by side with `[C]`, and they enter the human arbitration queue.**

| Status | Marker | Meaning | Assigned by | Participates in decisions |
|------|------|------|--------|----------|
| pending | `[P]` | Quarantine area: AI-extracted, not reviewed by anyone | Automatically at extraction | No (candidate) |
| draft | `[D]` | Human-reviewed, content correct, but evidence insufficient | At user review | No (default) → usable with warning when no [V] substitute exists |
| verified | `[V]` | Sufficient evidence (explicit user confirmation / tool output / authoritative external document) | User review or later verification | Yes (normal weight) |
| deprecated | `[X]` | Deprecated / proven wrong | User review / human arbitration | Not read |
| conflict | `[C]` | Contradicts another entry, kept side by side pending arbitration | Overlaid when conflict is detected | Low weight before arbitration |
| blocked | `blocked=secret` (sub-marker of [P]) | Sensitive-data scan hit; forbidden to leave the quarantine area; **persisted only in redacted form (N-6)** | Automatically by the write gate | No |

State machine (legal transitions):

```
auto_extract ──► [P] ──review──► [D] ──tool/explicit verification──► [V]
                 │  ├─reject──► [X]                      │
                 │  ├─strong-evidence review──► [V]     ├─staleness expiry──► re-verify prompt (no auto-downgrade)
                 │  └─conflict──► [C]（both sides side by side）  ├─arbitration loss──► [X]
                 └─overdue unreviewed──► archive (must be re-reviewed to return to [P])
```

**Forbidden transition (write red line)**: `[P]/[D]/[C]` → marking some `[V]` as `[X]`.

### A.2 Entry Data Structure

Each entry = title line + metadata line + body. The metadata line must be the **first blockquote line** after the title line, starting with `> kb-meta:`, machine-parsable:

```markdown
### [D] WSL 网络配置（kb: KB-014）

> kb-meta: id=KB-014; state=D; file=facts; created=2026-08-16T10:12:00; reviewed=2026-08-16T20:00:00; source=session:abc123@line452; confidence=0.5; evidence=conversation_inference; last_used=2026-08-16; scope="Windows 11；截至 2026-08"; sensitive=0

正文……（1-5 行，控制单条体积）
```

| Field | Required | Value | Description |
|------|------|------|------|
| `id` | Yes | `KB-###` globally incrementing | Derived after acquiring the lock from "max id over the whole library (including archive) + 1"; unique and stable across files; migration does not change the id |
| `state` | Yes | `P/D/V/X/C` | [C] is an overlay: `state=D` + title prefix `[C]` |
| `file` | Yes | `facts/pitfalls/state/growth-notes/prompt-improvements/alignment/decisions/pending` | File where the entry lives; updated on migration |
| `created` | Yes | ISO 8601 | Extraction time |
| `reviewed` | On review | ISO 8601 | Empty = not reviewed |
| `source` | Yes | `session:<session id>@<line number>` or `legacy` or `user` or `manual` | Source binding, traceable |
| `confidence` | Yes | `0.9/0.7/0.5/0.3` | Coarse four-tier |
| `evidence` | Yes | `auto_extract / conversation_inference / tool_output / user_explicit / external_doc` | Evidence type (A.5) |
| `last_used` | During lifecycle scan | ISO 8601 | Updated when the entry is read for a decision (F-7: recorded automatically by kb-manager.py during read operations, e.g. `--mode touch --id KB-0xx`, not relying on LLM reporting-layer diligence) |
| `scope` | No | Free text | Applicable scope: platform/version/time window. **Escaping rules (N-13)**: free-text fields containing reserved characters such as `;`, `=`, `"` (scope and any future free-text fields) must be written encoded as JSON strings, i.e. the inner part of `scope="…"` is JSON-escaped (`\"` `\\`), and parsers decode it as a JSON string; when it contains no reserved characters the quotes may be omitted and it written bare |
| `sensitive` | Yes | `0/1` | 1 = sensitive entry; index lists only the id, not the summary |
| `archived_at` | On archive | ISO 8601 | Archived entries retain all metadata |

**Evidence type and confidence binding** (tightening [V] semantics, fixing issue 2):

| Evidence type | Default confidence | Can alone support [V] | Freshness requirement |
|----------|-----------|-----------------|----------|
| `tool_output` | 0.9 | Yes, but must record scope ("measured on Windows 11"), and must belong to the re-verifiable class (version numbers, command output) | Version-class entries must be re-verifiable; `verify_refresh_days`(365) prompts re-verification on expiry |
| `user_explicit` | 0.9 | Yes | The user's explicit affirmation of "is this right?" **within the review flow** (a casual "yeah" in conversation does not count; it must be a response to a direct question) |
| `external_doc` | 0.7 | Yes (record document name and version) | Invalidated as soon as the document is updated |
| `conversation_inference` | 0.5 | **No** (can only reach [D]) | — |
| `auto_extract` | 0.3 | **No** (can only reach [P]) | — |

### A.3 File Layout ([P] Storage Decision)

**Decision: A separate `pending.md` file serves as the quarantine area (quarantine file); do not use "in-file [P] marker" and do not create a separate directory.**

Rationale:
- Physical isolation is the key to the defense line: read.md's normal read path (index → 1-2 detail files on demand) **can never reach pending.md**, mechanically eliminating "[P] being casually used as knowledge";
- An "in-file [P] marker" shares the screen with `[V]`, so the model sees quarantined entries in its context and the isolation fails;
- A separate directory (quarantine/) is too heavy at the current 8-file scale; `pending.md` is itself a single-file quarantine area, to be upgraded to a directory only when the volume grows (>100 entries) in the future.

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

The head of pending.md carries a prominent warning to prevent any misreading:

```markdown
# Pending 隔离区（未审核候选）

> ⚠️ 本文件内容**未经人工审阅，禁止用于任何决策**。仅 /kb-review 可读取本文件。
> 读取指南：见 rules/read.md 状态表。敏感扫描命中条目以打码形态标记 `blocked=secret`
> 永驻此处（仅含模式类型与来源定位，不含原始敏感值）。

---
```

### A.4 Read Rule Changes (decision weight)

| Marker | Read behavior | Decision weight |
|------|----------|----------|
| `[V]` | Read and used normally | High; when conflicting with another [V], the newer `reviewed` time wins, recorded in the status report |
| `[D]` | Readable, but **by default does not participate in decisions**; used with a "(unverified)" annotation only when no [V] substitute exists for the same topic; not the sole basis for high-risk decisions | Low |
| `[P]` | **Not read** (only /kb-review); in an emergency it may be referenced temporarily only with the user's explicit permission for that instance | None |
| `[C]` | Both sides read side by side, each annotated "contradiction exists, pending human arbitration"; does not constitute a decision basis before arbitration | Suspended |
| `[X]` | Skipped | None |
| archive/ | Not read (can be restored via /kb-restore) | None |

### A.5 Conflict Handling Changes (fixing issue 3)

Old rule: "a new entry conflicts with an existing entry → mark the old entry [X]" — this allowed an unverified [D] to unilaterally kill a [V]. New rules:

1. **Conflict determination at write time** (after the deduplication step): if the new candidate semantically contradicts any `[V]` → **elimination is forbidden**, the candidate stays `[P]` (marked `conflict=KB-0xx`), and at the same time the old `[V]` entry's title is overlaid with `[C]` (including the id of the conflicting entry); both are kept side by side and added to the `/kb-review` arbitration queue;
2. **Conflicts between `[D]` entries**: same as 1, both are marked [C] pending human arbitration;
3. **Arbitration** (within the /kb-review flow): the user rules one side correct → the correct side has its [C] marker removed, the loser is marked `[X]` (annotated `superseded_by=KB-0xx`); once only one side remains after arbitration, [C] is cleared automatically;
4. Arbitration **does not retroactively rewrite history**: the loser is only marked [X] + explanation, and its body is deleted.

### A.6 Migration of Existing Knowledge Base

| Existing type | Handling | Trigger |
|----------|------|------|
| Existing `[V]` entries | Mechanically fill in metadata (`id` auto-assigned, `created`=file mtime, `source=legacy`, evidence determined by file: facts/decisions default to `external_doc` or `user_explicit`, pitfalls default to `conversation_inference` but retain [V] (compatibility), status not downgraded) | Migration script, one pass |
| Existing `[D]` entries (old semantics) | **Not processed automatically**; enter the `/kb-review` batch review queue marked `legacy=1`; the user batch-approves `all v` / `all d` / rejects individually. Rejected ones are marked [X] | At the first /kb-review |
| Entries with no status marker | Treated as unreviewed → moved into pending.md marked `[P]` | Migration script |
| Missing metadata / no id | Filled in as above | Migration script |

Migration is performed by the new script `kb-manager.py migrate` (under lock), producing a before/after comparison report.

### A.7 Module A Edge Cases

- After migration the knowledge base "shrinks" in the short term (old [D] cannot be used for decisions until reviewed) → expected behavior; a single `/kb-review` catch-up review restores it;
- Existing `[V]` entries that oppose each other (legacy data) → likewise marked [C] and sent to arbitration, with no automatic choosing of sides;
- The same fact extracted repeatedly within pending.md → dedup rules apply to pending (module D's dedup.md);
- The user asks to force a blocked entry into the library → not allowed; it can only be redacted and resubmitted; a blocked entry itself exists in pending.md only in redacted form (N-6), and the original value exists in no file;
- The user gives weak confirmation during review ("seems right") → classified as [D], not [V].

### A.8 Module A Acceptance Criteria

1. 100% of new entries first land in pending.md; the normal read flow reaches pending.md 0 times (verify by script that the read path does not include that file);
2. Construct an "erroneous inference → stored → referenced by a later task" scenario and verify that after isolation the erroneous entry is not referenced;
3. `[P]/[D]` cannot mark any `[V]` as `[X]` (rule test case); in a conflict scenario both sides are kept side by side, marked [C], and enter the arbitration queue;
4. Every entry has a legal `kb-meta:` line (unique id, legal evidence, legal state), and script validation passes;
5. After migrating existing data, the kb-index count matches the actual entry count in the detail files.

---

## Module B: Knowledge Lifecycle (birth, aging, death)

### B.1 Threshold Configuration (config.yaml delta)

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

### B.2 Health Scan (run alongside every /evolution, sub agent step 0.5)

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

stale marker = the entry appears in the report and in /kb-status, while **the archive action is performed alongside the next lock-held write** (avoiding a separate lock for the scan). See B.3 for the archiving flow.

### B.3 Archive Mechanism

- Directory: `archive/YYYY-MM/<source file name>-<YYYY-MM>.md` (aggregated by month, e.g. `facts-2026-08.md`);
- Archive format: the entry retains the **complete original text + all kb-meta**, appending `archived_at=<ISO>`;
- Each archive is recorded in that month's `kb-manifest-<YYYY-MM>.json`: `{id, source file, target file, archive time, original line number}` — restoration depends on this manifest;
- **Recoverability**: `/kb-restore <id>` → locate via manifest → put the entry back into the corresponding detail file in its original status (if the status is P/D, after restoration it is always reset to `[P]` for re-review, unless the user explicitly asks to keep the original status) → lock-held transactional write → remove from the archive file and manifest;
- **Archive-only by default, never delete**; the archive/ directory is not counted in kb-index and is not read; deletion is performed manually by the user only (documented as `archive_policy: keep`);
- Archive file header comment: "This file is generated by /kb-archive and the lifecycle scan, can be restored via /kb-restore; do not edit by hand".

### B.4 kb-index Capacity Monitoring

- **The index is derived data**: each write transaction updates the index; each health scan checks index-vs-detail-file consistency (id-level reconciliation), and on mismatch **regenerates from the detail files** (index lag self-heals, supporting module C's crash recovery);
- Index line count > **500** (`index_max_lines: 500`, N-14: unified with the SKILL.md description as 500) → compression strategy (choose one, prefer 1):
  1. Regenerate the index: include only entries among the 6 statuses that are not [X] and whose `last_used` is < 180 days ago; excluded entries leave a one-line summary pointer in the index (`KB-0xx → archive/2026-08/facts-2026-08.md`, not occupying body lines);
  2. If still over the limit → append to the archive starting with the oldest `created` (via B.3);
- Compression is deterministic regeneration, not per-entry editing, so the line count predictably falls back (target < 300 lines).

### B.5 Chunk Lifecycle (interfacing with the engine-layer batch protocol)

Current state: `.evolution/chunks/` stores `chunk-*.md` (full), `chunk-inc-*.md` (incremental), and `sync-state.json`; v3.8.0 already has the discipline of "clean up only per the allowlist, never rmtree".

Change: evolution-export.py records a **batch manifest** in sync-state.json (schema consistent with engine layer A.2, N-7 revision — the old draft's `run_id/files[].name` structure is abolished):

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

GC rules (health scan step g):
1. Only chunk files that **appear in a manifest and are not within the most recent `chunk_keep_rounds` batches** may be deleted (exact match by `chunks[].file`; glob wildcard deletion is forbidden, continuing the v3.8.0 discipline);
2. `*.bak-*` files are deleted by mtime older than `chunk_bak_keep_days` (only within `.evolution/chunks/`);
3. `sync-state.json` is never deleted;
4. Orphan chunks (in no manifest) are only **reported, not deleted**, to avoid killing a file that is currently being written.

### B.6 Module B Edge Cases

- If the user does not trigger /evolution for a long time → the health scan does not run → /kb-status is the fallback (this command forces a scan to run first);
- After archiving, a new entry on the same topic is written → no automatic comparison (to avoid "archive ghosts" interfering); the user runs /kb-restore when needed;
- [C] entries are not archived on expiry (arbitration takes priority over lifecycle);
- sensitive=1 entries are archived under the same rules, not redacted (the archive area is local anyway and should be excluded by git, see E.4);
- Index regeneration conflicts with a user currently reviewing → compression is completed inside a lock-held transaction, serialized.

### B.7 Module B Acceptance Criteria

1. Construct a [P] from 31 days ago → after one /evolution it enters archive/ and the report shows a stale count;
2. Construct an overdue [D] → auto-archived after 180 days; after restoration its status is [P] and requires re-review;
3. kb-index reaches 501 lines → after compression < 300 lines and id-level consistent with detail files (script validation);
4. Construct old-batch chunks + .bak files → correctly deleted while sync-state.json and current-batch files are retained;
5. Zero deletion of KB body text throughout the flow (archive_policy=keep in effect, asserted by file count).

---

## Module C: Knowledge Base Transactions and Concurrency

### C.1 `.kb.lock` File Lock Protocol

> **F-5 ownership**: Locks are acquired and held by kb-manager.py; the sub agent / LLM never directly holds this lock to write knowledge base files.

- Lock file: `evolution/knowledge-base/.kb.lock`;
- Mechanism: reuse evolution-export.py's `file_lock` (Windows `msvcrt.locking` / Linux `fcntl.flock`, non-blocking polling + timeout, lock released automatically on process exit — the lock is bound to the file handle, leaving no lingering deadlock);
- Timeout: KB write operations use `lock_timeout: 30s` (the export script uses 120s; the two are independent), polling interval 100ms;
- The writer who acquires the lock **self-identifies inside it** (writing into the lock file: `pid + operation name + time`), for diagnostics when a timeout error occurs;
- **Read-only operations do not need the lock** (atomic replacement guarantees readers see only the complete old version or the complete new version, never a torn file).

### C.2 Write Transaction Protocol (a single knowledge base write = one transaction)

> **F-5 ownership**: This protocol is implemented by kb-manager.py — the sub agent triggers transactions via `kb-manager.py add/promote/deprecate/resolve/restore`, and **never holds the lock or writes files itself**. All the steps below occur inside the script process.

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

**Crash safety**: the write order guarantees that the worst case is "index lag" (detail files new, index old), and the index is derived data (B.4) — the next health scan regenerates it from the detail files and self-heals; `.<name>.kb.bak` provides the most recent manual rollback point.

### C.3 Behavior Specification for Concurrent Triggers

| Scenario | Behavior |
|------|------|
| /evolution and /kb-review triggered at the same time | Queued serially: the latter waits for the lock ≤ 30s, times out with an error and does not write |
| Two sub agents writing at the same time (each calling kb-manager.py) | Same as left; reading the current state inside the lock ensures neither loses the other's committed content |
| Read-only (normal knowledge retrieval) concurrent with a write | No conflict; a reader may see either the new or old version, never torn |
| Writer timeout | Report the error + in-lock identity info (pid/operation), prompt to retry later |
| Process crashes while holding the lock | The handle closes with the process and the lock is released automatically; .tmp residue is cleaned by the next health scan (only files with the .kb.tmp- prefix and mtime > 24h) |

### C.4 Module C Edge Cases

- The lock file is manually deleted → harmless (the lock is on the handle; deleting the file does not affect the holder; a new acquirer recreates the file);
- An 8-file batch write fails midway → already-replaced files are retained, unreplaced ones are aborted; `.kb.bak` rollback plan;
- Written content conflicts with the on-disk current state (external manual edit during the transaction) → validation fails and aborts, reporting the difference for the user to confirm;
- On Windows a file is occupied (open in an editor) and replacement fails → error out and give the .bak path; never silently discard.

### C.5 Module C Acceptance Criteria

1. Concurrency stress test: two writers submit different entries at the same time → both contents are retained, with no lost update;
2. Inject an index/detail inconsistency → the health scan self-heals to consistency;
3. While the lock is held, a second writer reports "knowledge base busy" within 30s, with no file corruption;
4. Reading at any moment (including during a write) never yields half a file's content;
5. Simulate a mid-way crash → after restart the health scan self-heals, with no orphan .tmp residue (>24h cleaned).

---

## Module D: Command Protocol and Proactive Review Flow

### D.1 Command List

| Command | Purpose | New/Existing |
|------|------|-----------|
| `/evolution` | Incremental sync + health scan + review queue prompt | Existing, changed |
| `/evolution-init` | Initialization | Existing, changed (all output lands in pending) |
| `/kb-review` | **Batch review** of pending + legacy [D] + [C] arbitration | New |
| `/kb-status` | Knowledge base health report | New |
| `/kb-archive` | Manual archive | New |
| `/kb-restore <id>` | Restore from archive (returns to [P] for re-review) | New |

> **#23 command unification (N-7 revision)**: The `/kb-sync`, `/growth-sync`, and `/alignment-sync` retained in the old draft are phantom commands (documented but implemented out of place), contradicting the #23 "command unification" decision — **removed and deprecated in V4.0.0**. Local sync needs are handled uniformly by `/evolution`; the three entries are removed from the SKILL.md command table as well.

### D.2 Command Definition (frontmatter draft, style aligned with existing commands)

```markdown
---
name: kb-review
version: 4.0.0
description: 批量审核待定条目。列出 pending 队列、遗留 [D]、[C] 冲突待仲裁项，用户批量确认/驳回，sub agent 调用 kb-manager.py 持锁执行状态迁移。
disable-model-invocation: true
---
```

`/kb-review` execution flow:
1. The sub agent reads pending.md + entries with `legacy=1` [D] in the detail files + entries whose title carries [C] (read-only, no lock needed);
2. Generates a **one-screen preview** (about 1 line per entry, see D.3);
3. The user enters batch instructions; the sub agent submits the batch instructions to kb-manager.py (promote/deprecate/resolve), and the script performs the migration under lock:
   - `v <ids>` or `all v` → mark [V] and move into the detail file (strong evidence)
   - `d <ids>` → mark [D] and move into the detail file (weak evidence)
   - `x <ids>` → mark [X] (stay in place, optional rejection reason)
   - `a <ids>` → view the full entry text before deciding
   - `c <id> 选 <id>` → arbitrate [C]: the winner has its [C] marker removed, the loser is marked [X] + `superseded_by`
4. On completion, output a diff summary: `✅ KB-014 facts (P→V) · KB-015 pending (P→D) · KB-002 pitfalls (P→X)`;
5. Everything is completed within **one transaction** of module C (batch atomicity).

`/kb-status` output template:

```
📊 知识库健康报告
- 条目：V 12 / D 3 / P 5（其中 blocked 1）/ X 4 / C 2
- 待审核：5（P）· 遗留旧 [D]：6 · 待仲裁：2
- 生命周期：stale [P] 2 · 闲置 [D] 1 · 待复验 [V] 3
- 容量：kb-index 412/500 行 · archive 1.2KB · chunks 3 批次（孤儿 0）
- 敏感扫描：chunks 疑似密钥 2 处（仅报告）· KB 正文 0
```

### D.3 Review UX (minimum-cost principle)

- **One-screen preview**, one line each: `[序号] KB-014 [P] WSL 网络配置 | 会话#452 08-10 | 置信 0.5 | 摘要 12 字`; for sensitive=1 entries only the id and source are shown, not the content summary;
- **Default action up front**: for entries with no evidence conflict, `v` is recommended by default (review means trust) — but the recommendation label is shown by evidence type: `tool_output` recommends `v`, `conversation_inference` recommends `d`;
- **Batch**: `all v` / `v 1-5` / `d 2 4` etc.; after confirmation, a one-time diff preview, and the user's `y` executes it;
- **Zero-review** path: do nothing → stale after 30 days → archived; the system keeps itself clean automatically (it neither forces review nor lets entries pile up and pollute long-term);
- At the end of each `/evolution` summary, one prompt line is appended: `📋 5 条待审核（/kb-review）· 2 条 30 天后过期（/kb-status）` — the prompt does not block and never auto-executes review.

### D.4 Integration with Existing Commands

- `sync.md`: add step 0.5 health scan + step 4 review queue prompt; append "health report line" to the completion criteria; change the write step to call `kb-manager.py add` (F-5, see Sequence 1);
- `init.md`: the generated knowledge base all lands in pending.md (no longer [D]); change the completion criterion to "pending.md entry count > 0"; add a suggested step "recommend running /kb-review once to batch-review the initial entries";
- `SKILL.md`: command table + the 4 new commands; **delete the three rows /kb-sync /growth-sync /alignment-sync (#23 command unification)**; the rule table is unchanged (pointing to the updated 3 rule files); add `pending.md` and `archive/` to the knowledge base path description; unify the kb-index line limit description to 500 (N-14).

### D.5 Module D Edge Cases

- A review instruction contains a non-existent id → ignore and report it, without rolling back the entire batch after a partial failure (per-entry fault tolerance; successful items are retained);
- During review the user runs /evolution again and writes to pending → lock serializes them, and the second write deduplicates naturally;
- During [C] arbitration the user chooses neither → stay [C] into the next round, not auto-deprecated;
- The /kb-restore target status conflicts with an existing entry → after restoration it automatically enters the arbitration queue (marked [C]);
- Review interrupted (user does not reply) → the sub agent times out and exits, producing no write operation; the preview can be regenerated.

### D.6 Module D Acceptance Criteria

1. 10 pending + 6 legacy [D], the user enters one `all v` → all migrate within one transaction, the summary is correct, and the index count is synced;
2. Entering an illegal id mid-review → errors out but the already-legal items take effect;
3. `/kb-status` is consistent with the health scan results (same data source);
4. After /kb-restore restores an entry its status is [P] and it appears in the review queue;
5. The complete flow (sync → prompt → review → status), left unattended with no action for 30 days, keeps the knowledge base healthy (stale archives instead of bloating).

---

## Module E: Privacy and Security

### E.1 Problem Localization

Current state: Both conversation export (evolution-export.py's chunk files) and knowledge base writes happen **before any human review**, so sensitive content (keys, tokens, paths, personal information) is already on disk without the user's consent; pitfalls#3 has recorded the "sensitive information leakage risk" but there is no mechanism as a defense line.

### E.2 Three Defense Lines

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

### E.3 Sensitive Field Pattern List (config.yaml `sensitive_patterns`)

> **N-7/N-10 regex unification**: This list is the single authoritative source; the engine layer (evolution-export.py defense line 1) and the knowledge layer (kb-manager.py defense line 2) reference the same config and must not inline their own regexes. `local_path` defaults to `enabled: false` (N-10: paths appear frequently in knowledge entries, and interception would cause many false positives on normal entries; the user can enable it as needed).

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

Hit strategy: after interception, show a **redacted preview** (`key=sk-***（已拦截）`), eliminating the "it errored but the content was already stored" problem.

### E.4 README Privacy Section Draft

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

### E.5 Module E Acceptance Criteria

1. Construct candidate entries containing `sk-ant-...`, `ghp_...`, `password=...` → all are intercepted into blocked, with zero hits in the KB body; the persisted content of blocked entries is in redacted form (pattern type + source location), containing no original value;
2. After redacted resubmission they are stored normally and contain no original value;
3. The chunk scan report can point out the files and line numbers containing keys;
4. `.evolution/` is in .gitignore, and `git status` does not show chunks;
5. Both the English and Chinese READMEs have the privacy section, and it is consistent with the control commands (documentation-behavior consistency check);
6. **N-6**: assertion on the persisted content of blocked entries — no file contains any original value matching sensitive_patterns; only the secret_type and source location fields exist.

---

## Rule File Before/After Comparison (full-text draft)

### write.md (after changes, v2 revision — aligned with the F-5 sole write entry point)

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

### read.md (after changes)

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

### dedup.md (after changes)

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

### config.yaml delta (appended in v4.0.0)

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

## Process Sequences

### Sequence 1: Write (sync → extract → isolate) (v2 revision — aligned with the F-5 sole write entry point)

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

### Sequence 2: Review (/kb-review)

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

### Sequence 3: Lifecycle (alongside /evolution step 0.5 + /kb-status fallback)

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

## Consolidated Edge Case List

| # | Scenario | Handling |
|---|------|------|
| 1 | Lock timeout (another writer holds the lock) | Report "knowledge base busy (pid/operation)", do not write, prompt to retry |
| 2 | Writer process crashes | Lock is released with the handle; .tmp- residue >24h is cleaned by the health scan; .kb.bak provides rollback |
| 3 | Partial failure replacing multiple files in a transaction | Abort the remainder; writing the index last guarantees worst case = index lag, self-healed by the health scan |
| 4 | Knowledge base temporarily slimmed after migration | Expected behavior; one /kb-review catch-up review restores it |
| 5 | Existing [V] entries oppose each other | Mark [C] and enter arbitration; no automatic choosing of sides |
| 6 | Same fact extracted repeatedly within pending | dedup merge (keep the earlier created, append source) |
| 7 | Duplicate vs conflict hard to determine | Treat as conflict; prefer arbitration over merging |
| 8 | [P]/[D] attempts to eliminate [V] | Rule red line + transaction validation, double interception |
| 9 | User does not review for a long time | Stale after 30 days → archived; not deleted, not bloated |
| 10 | [C] arbitration with neither side chosen | Stay [C] into the next round, not auto-deprecated |
| 11 | Sensitive scan hit | Intercept + redacted preview; blocked entries persisted only in redacted form (pattern type + source location), original value never written to disk (N-6) |
| 12 | Sensitive scan false positive (e.g. a path containing the word token) | Offer redaction/rejection; hit log is visible (/kb-status) |
| 13 | /kb-restore target conflicts with an existing entry | After restoration it is automatically marked [C] and enters arbitration |
| 14 | Evidence expired after archive restoration | Always returns to [P] for re-review |
| 15 | chunk GC races with an in-progress sync | Only old batches outside the manifest are deleted; orphans are only reported |
| 16 | sync-state.json | Never deleted |
| 17 | Index manually corrupted | Health scan checks id-level consistency, and regenerates on mismatch (annotated "self-healed") |
| 18 | User review instruction contains an illegal id | Per-entry fault tolerance: illegal items error out, legal items take effect |
| 19 | pending.md empty / file missing | Treated as an empty quarantine area; normal initialization |
| 20 | Windows file occupied by an editor | Replacement fails, error out and give the .bak path; never silently discard |

---

## Acceptance Criteria Summary (module level)

| Module | Key acceptance items |
|------|-----------|
| A | 100% of new entries first land in pending.md; the normal read reaches pending 0 times; [P]/[D] cannot eliminate [V]; all entries have legal meta (including N-13 escaping rule validation); after migration the index and detail files are consistent |
| B | 31-day [P] auto-archived; 180-day [D] auto-archived; index over 500 lines compresses to <300 and is consistent; chunk batch GC is correct (manifest schema consistent with engine A.2); zero body deletion throughout the flow |
| C | Two writers, no lost updates; inconsistent index self-heals; lock timeout errors without corruption; reads never torn; recoverable after a crash |
| D | Batch review completes in one transaction; illegal id fault tolerance; /kb-status consistent with the health scan; after restoration returns to [P] and joins the queue; healthy after 30 days of zero action |
| E | All key/password/path candidates intercepted; blocked persisted only in redacted form with the original value never on disk; redacted resubmission works normally; chunk scan can locate; .evolution excluded by git; README bilingually consistent with behavior |

---

## Implementation Order and Effort Estimate

| Phase | Content | Dependency | Effort (single person) | Verifiable output |
|------|------|------|---------------|-----------|
| P0 Inventory & migration | kb-manager.py skeleton (migrate/validate); fill meta for existing [V], move unmarked ones to pending | None | 2-3h | Migrated library passes validate |
| P1 Status model | config.yaml extension; write.md/read.md/dedup.md changes; pending.md introduction; **sole write entry point `kb-manager.py add` CLI (F-5)** | P0 | 3-4h | Rule file review + write path switched to pending |
| P2 Transactions | .kb.lock protocol; kb-manager.py's lock/commit primitives; write order and validation | P1 | 4-5h | Concurrency stress test passes (C.5 criteria) |
| P3 Lifecycle | Health scan; archive/restore; index compression; chunk batch manifest + GC (manifest schema aligned with engine A.2) | P2 | 4-5h | B.7 standard scenario tests pass |
| P4 Commands & review | /kb-review /kb-status /kb-archive /kb-restore command files + sync/init/SKILL integration; **delete /kb-sync /growth-sync /alignment-sync (#23)** | P1 | 4-5h | Full-command manual acceptance script |
| P5 Security | Sensitive-data scan gate (script-enforced, blocked persisted in redacted form, N-6); chunk scan report; .gitignore; README privacy section (EN & zh-CN) | P1 | 2-3h | E.5 standard tests pass |
| P6 Regression | Full rule consistency test; VERSION_HISTORY/CLAUDE.md version update | All | 2-3h | v4.0.0 release checklist |

**Total about 21-28 hours**; it is recommended to land it in 5-6 commits by phase, with each phase independently verifiable, and P0/P1 first (breaking the self-reinforcing loop is the highest priority).

### Affected File List

| File | Action |
|------|------|
| `.claude/skills/evolution/config.yaml` | Change (status marker extension + lifecycle + lock + sensitive_patterns) |
| `.claude/skills/evolution/rules/write.md` | Rewrite (draft in this section) |
| `.claude/skills/evolution/rules/read.md` | Rewrite (draft in this section) |
| `.claude/skills/evolution/rules/dedup.md` | Rewrite (draft in this section) |
| `.claude/skills/evolution/commands/sync.md` | Change (step 0.5 health scan + step 4 prompt) |
| `.claude/skills/evolution/commands/init.md` | Change (output lands in pending + suggest catch-up review) |
| `.claude/skills/evolution/commands/kb-review.md` | New |
| `.claude/skills/evolution/commands/kb-status.md` | New |
| `.claude/skills/evolution/commands/kb-archive.md` | New |
| `.claude/skills/evolution/commands/kb-restore.md` | New |
| `.claude/skills/evolution/commands/kb-sync.md` / `growth-sync.md` / `alignment-sync.md` | **Delete (#23 command unification, removed in V4.0.0)** |
| `.claude/skills/evolution/SKILL.md` | Change (command table + knowledge base description; delete the three deprecated command rows) |
| `.claude/skills/evolution/evolution-export.py` | Change (batch manifest recording + chunk sensitive scan report) |
| `.claude/skills/evolution/kb-manager.py` | New (validate/migrate/lock/commit/scan/compress/restore + **add/promote/deprecate/resolve/touch sole write entry point CLI, F-5/F-7**) |
| `evolution/knowledge-base/pending.md` | New |
| `evolution/knowledge-base/archive/` | New (as needed) |
| `evolution/knowledge-base/` 8 detail files | Migration (meta completion + [C] marker opportunities) |
| `.gitignore` | Change (`.evolution/`, `*.kb.bak`, `*.kb.tmp-*`) |
| `README.md` / `README.zh-CN.md` | Change (privacy and security section) |
| `docsV3/VERSION_HISTORY.md` | Change (v4.0.0 release record) |
| `CLAUDE.md` | Change (version number and knowledge base description) |
| `.claude/settings.json` | Suggested change (if chunk scan hooks are enabled) |

---

**End of document**
