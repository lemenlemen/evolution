# Evolution V4.0.0 Sync Engine Layer Design

🌐 **Language / 语言**: [English](design-v4-engine.md) | [中文](design-v4-engine.zh-CN.md)

> ⚠️ **Rollback banner (v4.1.2 addendum)**: The engine-layer design (dual cursors, batch state machine, integrity check, atomic write + three-tier recovery chain,
> streaming two-pass scan + k-way merge, token safety factor) **is still valid and in use**.
> However, the `migration.trust_committed` escape valve in this document's migration-related design is **not implemented**:
> `evolution-export.py` has no CLI path that produces a migration batch, and `config.yaml` has no `migration:` config section,
> this switch is future planning only. Knowledge-layer designs such as `[P]` isolation were rolled back in v4.1.0.
> ⚠️ The `state-version-newer` rejection mechanism is **not implemented** (the code has no version-comparison logic; future-version state will be silently downgraded). Future planning only.

> **Version**: draft v2 (V4.0.0 sync engine layer)
> **Date**: 2026-08-16 (v2 revision 2026-08-21)
> **Scope**: Data integrity (Critical 1/2/3) + code robustness (parse defense, streaming, sorting, token estimation, observability)
> **Status**: Implemented (implementation date 2026-08-24)
>
> **v2 revision**: Fixes protocol defects found in review — N-2 resume path "commit before analysis", N-3 migration/failed batch recovery path contradiction, N-4 analysis-failure count CLI placement (F-3)

---

## 0. Current State and Root-Cause Comparison

This document is based on an analysis of `evolution-export.py` (v3.9.0, `VERSION = "3.4.0"`), `config.yaml`, `docsV3/EXPORT_AND_ANALYSIS_DESIGN.md`, and the live `.evolution/chunks/sync-state.json`.

**Measured finding**: The `version` field of the online `sync-state.json` is `"3.2.1"`, but its structure is already the structure described in the v3.4.0 doc (containing `processed_lines`/`processed_bytes`). That is, the version label and schema drifted apart—migration logic must treat `3.2.1` and `3.4.0` as the same structure.

| # | Problem | Root cause | Fix module |
|---|------|------|---------|
| C1 | The incremental cursor is committed before knowledge extraction; a sub agent interruption → history permanently lost | `export_incremental` advances `processed_lines` and saves state before the sub agent analyzes | A |
| C2 | The cursor has no integrity check; truncation/rotation → start_line jumps past all lines → silent data loss | `sha256/mtime/processed_bytes` stored but never compared | B |
| C3 | `save_sync_state` is not an atomic write; a mid-way crash → half-written JSON → load silently falls back to empty state → repeated full export | `open(w)+json.dump`; `load_sync_state` returns `_empty_state()` with no warning on corruption | C |
| D1 | Wrong-shaped lines (null/[]/123) → `entry.get` raises AttributeError → the entire export crashes | `_try_extract_entry` only catches `JSONDecodeError` | D |
| D2 | token estimate low by 1.3–2x; estimated 200K actual 260K–400K | estimation coefficient has no safety factor, no character-count fallback | D |
| D3 | Full export loads all entries of all files at once → OOM | `all_entries` accumulates across files | D |
| D4 | Oversized-turn chunks out of time order | `paginate_entries` large-turn branch only flushes the current chunk when `current_tokens > min_tokens`, so a small tail is dragged by later turns to after the large-turn chunk (see D.3) | D |
| D5 | Multi-session aggregation does not guarantee time order | concatenated by file mtime; sessions interleave and go out of order | D |

**System-wide invariants (from V4.0.0, design goal)**:

1. At most one uncommitted batch (in-flight) per file; while an uncommitted batch exists, incremental export for that file is blocked (when the chunk is intact).
2. Per file `exported_lines >= committed_lines`; `committed_lines` is monotonically non-decreasing.
3. No line may be silently skipped by an uncommitted/failed batch—a failed batch must be regenerated or explicitly downgraded.
4. All state-file changes are written atomically in one shot (tmp + fsync + os.replace).
5. The incremental export start point is `committed_lines + 1` (not `exported_lines + 1`).
6. The script is not responsible for verifying that knowledge has been persisted—commit is the sub agent's declaration; reliability is backed by the protocol (module E) + human review of `[D]` markers (trust boundary, see E.4).

---

## Module A: Dual Cursors + Batch Manifest (Fix Critical 1)

### A.1 Goals

- Decouple "script has exported" from "knowledge has been persisted" into two cursors: `exported_lines` and `committed_lines`.
- Each export produces a **batch** record (chunk manifest + state machine); after finishing analysis the sub agent explicitly confirms via `--mode commit`.
- Incremental export starts from `committed_lines`; on finding an uncommitted batch it **prioritizes resuming analysis** rather than re-exporting; failed batches are automatically regenerated and cannot be skipped.
- Data-structure version `3.4.0 → 3.5.0`, with old-state migration.

### A.2 Data Structure (JSON Schema level)

**Top-level `sync-state.json` (version 3.5.0)**:

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

**Field descriptions and change comparison**:

| Field | Old (3.4.0) | New (3.5.0) | Semantics |
|------|------------|------------|------|
| `version` | `"3.4.0"` | `"3.5.0"` | Data-format version (bump policy see A.4) |
| `schema` | — | `"sync-state"` | Top-level marker to prevent misreading other JSON |
| `batch_seq` | — | integer | Monotonic source for batch numbers |
| `files[k].processed_lines` | advanced on export | **renamed `exported_lines`** | Last entry line number the script has written into a chunk (1-based) |
| `files[k].processed_bytes` | same as above | **renamed `exported_bytes`** | File byte count at export time |
| `files[k].committed_lines` | — | new | Last entry line number the sub agent confirmed as persisted |
| `files[k].committed_bytes` | — | new | File byte count at commit time |
| `files[k].size` | — | new | Physical file size at last verification (semantically separate from `exported_bytes`) |
| `files[k].first_event_timestamp` | — | new | Timestamp of the file's first entry (for range determination and global sorting) |
| `files[k].integrity_warnings` | — | new | Cumulative integrity-warning count (observability) |
| `batches` | — | new | Batch manifest, keyed by `batch_id` |
| `batches[k].analysis_failures` | — | new (F-3/N-4) | Analysis-failure count, incremented by `--mode analyze-failed`; reaching `max_analysis_failures` → `failed(analysis-exhausted)` |

**Batch state machine**:

```
                 ┌─────────────┐
     export done ─▶│  exported   │── commit ──▶ committed (idempotent)
                 │             │
                 └──────┬──────┘
                    resume/start
                        ▼
                 ┌─────────────┐── commit ──▶ committed
                 │  analyzing  │
                 └──────┬──────┘
                        │ retries exhausted / explicit failure
                        ▼
                 ┌─────────────┐── regenerate (new batch, reason records old batch) ──▶ exported
                 │   failed    │
                 └─────────────┘
```

- `exported`: the script has written chunks to disk and atomically saved state (exported_lines advanced).
- `analyzing`: the sub agent has started (`--mode start --batch-id`, or set when resuming an old batch during an incremental run; informational only).
- `committed`: the sub agent finished analysis and confirmed via `--mode commit`, advancing `committed_lines`.
- `failed`: retries exceeded (default 3) or explicit failure; the `reason` field is required (`chunks-missing` / `retry-exhausted` / `superseded` / `deleted` / `migration-unverified` / `analysis-exhausted` (F-3) / other).
- **in-flight determination for failed batches (N-3)**: a failed (non-retry-exhausted) batch **does not count as in-flight**—it does not block incremental export of its file; the lines it covers are regenerated as a new batch in the next round by A.3's failed-regeneration loop (the old batch is marked superseded), and are never silently skipped. retry-exhausted is terminal, awaiting human intervention. `analysis-exhausted` is likewise terminal and can be explicitly confirmed via `--mode commit --force` (F-3/N-4).
- **Committed-batch pruning**: `committed` batches retain the most recent `keep_committed_batches` (default 20) for auditing; earlier ones are removed from `batches` (does not affect cursors, which live in `files`).

**Receipt returned by `--mode commit` (A.3)**:

```json
{
  "status": "success",
  "mode": "commit",
  "batch_id": "inc-20260101-000000-0001",
  "committed_at": "2026-01-02T00:35:11+00:00",
  "committed_lines": { "…jsonl": 5200 },
  "receipt_hash": "sha256(canonical JSON of {batch_id, committed_lines, committed_at})"
}
```

### A.3 Flow

**Incremental export (reworked `export_incremental`)**:

```
with file_lock(export.lock):
    state = load_sync_state(state_file)            # C: corrupted → explicit failure, never silently empty state
    jsonl_files = find_jsonl_file(project_root)
    integrity = check_integrity(state, jsonl_files) # B: run the integrity check first

    # ── B-triggered files for re-export: whole file re-exported as a new batch ──
    for f in integrity.need_full_reexport:
        batch = export_file_to_batch(f)             # full export from line 1, new batch status=exported
        state.files[f].committed_lines = 0          # line numbers meaningless for old content, set 0 (conservative)
        state.files[f].exported_lines = batch covered line numbers
        mark_old_inflight_batches(f, failed, reason="superseded")
        warnings.append(integrity_warning(f))

    for f in integrity.deleted:
        mark_old_inflight_batches(f, failed, reason="deleted")
        del state.files[f]                          # committed knowledge is in the KB, no recovery needed
        warnings.append(...)

    for f in integrity.new_files:
        batch = export_file_to_batch(f)             # new file: full export from line 1

    # ── A: uncommitted batches resumed first, failed batches regenerated ──
    result.pending_batches = []
    for b in state.pending_batches():               # status ∈ {exported, analyzing}
        if batch_chunks_intact(b):
            b.status = "analyzing"                  # resume: chunks intact → hand to orchestrator to continue analysis
            result.pending_batches.append(b.batch_id)
        else:
            nb = regenerate_batch(b)                # chunks missing → regenerate from line_ranges
            b.status, b.reason = "failed", "chunks-missing"
            state.batches[nb.batch_id] = nb
            warnings.append(...)

    # ── N-3: dedicated regeneration loop for failed (non-retry-exhausted) batches ──
    # failed batches do not count as in-flight (do not block new incremental export of their file),
    # but the lines they cover must never be silently skipped:
    for b in state.batches where status == "failed" and reason not in ("retry-exhausted", "deleted"):
        nb = regenerate_batch(b)                    # migration batches use the whole-file re-export special case; normal batches precisely re-parse by line_ranges
        b.status = "failed"; b.reason = "superseded"   # old batch marked superseded, no longer enters this loop
        state.batches[nb.batch_id] = nb             # new batch status=exported → becomes the file's only in-flight batch
        result.pending_batches.append(nb.batch_id)  # handed to the sub agent for analysis this round
        warnings.append(...)
        # Note: if the file also has new incremental content, incremental export still runs this round (failed does not count as in-flight);
        # the new incremental batch and the regenerated batch are independent, and their line ranges do not overlap
        # (regenerated ≤ exported_lines, incremental > exported_lines)

    # ── New incremental content: only for files without an in-flight batch ──
    delta = []
    for f in jsonl_files where no_inflight_batch(f):
        entries = parse_jsonl(f, start_line = committed_lines + 1)
        delta.extend(entries)
        # Note: this file does not advance exported_lines this round — advancement happens when the batch is built and saved

    if not delta and not result.pending_batches and no reexports:
        return success(new_entries=0, action_hint=None)   # "no new content"
    if not delta and result.pending_batches:
        return success(new_entries=0, action_hint="analyze_pending", pending_batches=[…])

    chunks = paginate_stream(global_timestamp_sort(delta))  # D
    batch = create_batch(mode="incremental", chunks, line_ranges, time_range, status="exported")
    for f in batch.line_ranges:                     # advance exported cursor (same atomic save as the batch)
        state.files[f].exported_lines = batch.line_ranges[f][1]
        state.files[f].exported_bytes = stat_size(f)
    state.batch_seq += 1
    save_sync_state_atomic(state)                   # C: chunks already written to disk, state persisted last
    return success(batch_id, new_entries, chunks, pending_batches, warnings)
```

**Core semantics**:

- **The incremental start point is `committed_lines + 1`**. Lines between `exported` and `committed` (covered by an uncommitted batch) are not re-exported—unless the batch chunks are missing or the batch failed, in which case it is **regenerated** (precisely re-parsed by the batch `line_ranges`; byte-identical chunk content if the source file is unchanged), and the old batch is marked `failed`. **A failed batch's chunks and cursors must not be skipped by the normal incremental path**.
- **Failed-batch semantics (clarified by N-3)**: a failed (non-retry-exhausted) batch **does not count as in-flight**—it does not block incremental export of its file; its unconfirmed lines enter regeneration in the next round via A.3's dedicated regeneration loop (new batch `status=exported`), and the old batch is marked `superseded`. A retry-exhausted batch stays in the failed terminal state, awaiting manual full re-export or explicit forced confirmation (F-3). Regenerated line ranges ≤ exported_lines, new incremental line ranges > exported_lines; the two do not overlap, and each commit advances the cursor independently.
- **`--mode commit --batch-id <id>`**:

```
with file_lock:
    state = load(...)
    b = state.batches.get(id)
    if b is None:                       → error "batch-not-found"
    if b.status == "committed":         → success (idempotent), return existing receipt
    if b.status == "failed":            → error "batch-failed" (hint: regenerate first)
    for f, [start, end] in b.line_ranges.items():
        assert end >= state.files[f].committed_lines     # forward only
        state.files[f].committed_lines = end
        state.files[f].committed_bytes = size(f)
    b.status = "committed"; b.commit_receipt = {…}
    save_sync_state_atomic(state)
    return receipt
```

- **Full export also creates a batch** (mode="full", one batch containing all chunks): `committed_lines` keeps its old value (0 for new files), `exported_lines = last entry line number`. A mid-way full-export failure → the next incremental sees the uncommitted full batch → resume; missing chunks → regenerate. The old batch is marked `superseded`.

**Subprocedure `regenerate_batch(b)`**: for each chunk, re-parse by `chunk.line_ranges` (per-file closed interval) (`parse_jsonl` needs a new `end_line` parameter), rewrite the chunk file (atomic write), and produce a new batch (new `batch_id`, `retry_count = b.retry_count + 1`). If `retry_count >= max_batch_retries` (default 3) → the new batch is set to `failed, reason="retry-exhausted"`, the export result is `status=partial` with a WARN that the file needs a full re-export or human intervention.
**migration special case**: when `b.mode == "migration"` the batch `line_ranges` is null and cannot be re-parsed by chunk.line_ranges → instead **re-export the whole file from line 1** (equivalent to a full-file re-export), producing `line_ranges: {f: [1, exported_lines]}`, with all chunks re-paginated.

**Migration batch** (produced when upgrading old state, see "Migration Path"): `mode="migration"`, chunks reference legacy `chunk-*.md` on disk (`line_ranges` unknown, set to null); if a chunk is missing it goes through regeneration—`regenerate_batch` special-cases migration batches as a **whole-file re-export from line 1** (producing `line_ranges: {f: [1, exported_lines]}`, see above), never parsing by the null chunk.line_ranges.

**Migration-batch commit special semantics (v2 revision, F-1)**: for a migration batch with null `line_ranges`, `--mode commit` cannot iterate line ranges to advance the cursor—define a special branch: `if b.mode == "migration": committed_lines = exported_lines (confirm all exported lines as-is)`, with the receipt noting `migration_commit: true`. This branch does not roll back or verify file-by-file; its semantics are "old history confirmed as-is" (pairing with the migration default goal of "re-analyze once": after the migration batch analysis completes, all old lines are confirmed in one shot).

### A.4 Version Bump Policy

- `VERSION` constant `"3.4.0" → "3.5.0"`. Bump rules:
  - **minor (3.4→3.5)**: new optional fields, field renames the loader can tolerate—`load_sync_state` reads explicitly by field name and supplies defaults for missing fields + a migration function chain.
  - **major**: incompatible structure (e.g. changed batches index structure)—a `MIGRATIONS` migration function must be written, and the state must be saved once immediately after migration.
- `MIGRATIONS` registry: `{"3.2.1": migrate_34x_to_350, "3.4.0": migrate_34x_to_350}` (the online file's actual label is `3.2.1` while its structure equals 3.4.0, so both must use the same function).
- Migration execution: on `load`, if `version < VERSION` → apply the migration chain in order → set `"3.5.0"` → **persist on the first save of this run** (the migration itself does not write immediately, avoiding writes on no-op; but the export flow necessarily saves afterward).
- `version > VERSION` (a future version running the old script) → **reject modification**, `status=failed, code=state-version-newer`; read-only operations (status) still work. Never interpret new state under the old schema.
- Unknown version → `failed, code=state-version-unknown`, prompting manual handling.

### A.5 Edge Cases

| Scenario | Behavior |
|------|------|
| sub agent interrupted after export, before commit | Batch status `exported`, chunks intact → next incremental returns `action_hint=analyze_pending` + batch manifest; **does not re-export** |
| Same as above but chunk deleted by cleanup | Regenerate batch (precise re-parse by line_ranges), old batch `failed(chunks-missing)` |
| Does a failed batch (non-retry-exhausted) block the file's incremental export | **Does not block** (not counted as in-flight); handled next round by the failed regeneration loop, old batch marked superseded |
| Migration-batch chunk missing / migration-unverified batch recovery | `regenerate_batch` special-cases mode="migration": whole-file re-export from line 1 (line_ranges: {f: [1, exported_lines]}) |
| A second uncommitted batch for the same file | Impossible: files with an in-flight batch are skipped (invariant 1); new lines for the same file wait until after commit for the next export round |
| Repeated commit call | Idempotent success, returns the existing receipt |
| Commit a failed batch | error `batch-failed`, guiding to regenerate first |
| Regeneration repeatedly fails (retry ≥ 3) | `failed(retry-exhausted)` + `partial` + WARN, prompting manual full re-export |
| Full export interrupted | full batch uncommitted → next incremental resumes; missing chunks → regenerate |
| Batch time range missing (no timestamp entries) | `time_range: null`, sorting falls back to a tie-breaker |
| Batch count growth | committed batches retain the most recent 20, the rest pruned (cursors unaffected) |
| `batch_seq` conflict | batch_id contains seq + timestamp + 4 random digits, conflict probability negligible; on conflict retry with a new random number |

### A.6 Acceptance Criteria

1. **Interruption recovery**: run incremental export (producing batch B) → do not commit before deleting chunks → run incremental export again → assert: `committed_lines` unchanged; return value contains `pending_batches=[B]` and no new chunk was produced (when chunks are intact).
2. **Failed regeneration**: delete one of B's chunk files → run incremental again → assert: new batch B' produced, B marked `failed(chunks-missing)`, B' chunk content identical to B (byte-identical when the source file is unchanged).
3. **commit semantics**: `--mode commit --batch-id B` → returns a receipt (with `receipt_hash`); `files[f].committed_lines == exported_lines`; run incremental again → only lines after committed are exported.
4. **Blocking semantics**: while B is uncommitted, append 10 lines to the same file → incremental export → assert new_entries=0 + pending; after commit B, incremental → exactly 10 entries.
5. **resume does not skip analysis** (N-2): run incremental producing batch B → set analyzing (simulate interruption) → run incremental again → assert: the returned pending_batches contains B, and sub agent protocol step 2 handles this batch (analyzing not filtered out); after commit committed_lines advances.
6. **failed batch does not block** (N-3): mark batch B failed(chunks-missing) → append 10 lines to the same file → incremental export → assert: new lines are normally exported as a new batch, and B is handled by the regeneration loop (new batch covers B's line range, old B marked superseded).
7. **analyze-failed counting** (N-4): call `--mode analyze-failed` on the batch 3 times in a row → assert after the 3rd the status becomes `failed(analysis-exhausted)` with WARN; `--mode commit --force` can confirm but outputs a prominent warning and the receipt contains `forced: true`.
8. **Idempotency**: commit the same batch twice → both success, receipts identical.
9. **Batch pruning**: create 25 committed batches in a row → committed batches in `batches` ≤ 20, cursors correct.
10. **Migration** (see "Migration Path" acceptance).

---

## Module B: File Integrity Check (Fix Critical 2)

### B.1 Goals

- Before incremental export, verify the authenticity of files already present in state: **mtime + size fast signal → skip hash if unchanged; if changed, recompute sha256 and compare against state**.
- File got shorter (truncation/rotation) → **full re-export** of that file + WARN; hash changed but longer → **conservative full re-export** + WARN.
- Interaction with module A is explicit: exported/committed cursor reset policy on re-export.

### B.2 Verification Decision Table

| Signal | hash | Determination | Handling |
|------|------|------|------|
| mtime same and size same | (not computed) | unchanged (fast path) | normal incremental logic |
| either mtime/size changed | same | content unchanged (mtime jitter/granularity) | refresh mtime/size, normal incremental |
| either mtime/size changed | different, size < recorded `size` | **truncation / rotation** | full re-export of that file + WARN |
| either mtime/size changed | different, size ≥ recorded `size` | **replacement / rewrite** | conservative: full re-export of that file + WARN |
| file in state but missing on disk | — | deletion / rotation | uncommitted batch marked `failed(deleted)`; removed from `files`; WARN (committed knowledge is in the KB, no recovery needed) |
| on disk but not in state | — | new file | full export of that file from line 1 (create batch) |

> The determination basis uniformly uses the new field `size` (physical size), no longer mixing in `exported_bytes` (different semantics: it is "the byte count at export time"; if a file is replaced by a smaller file after export, `exported_bytes` would misjudge).

### B.3 Flow (`check_integrity` pseudocode)

> **N-12**: The ownership of defense line 1 (chunk sensitive-pattern scan, report-only on hit) is the **export script evolution-export.py**—after the batch is built and chunks written to disk, the script runs a `sensitive_patterns` scan on each chunk file, and hits are written to the export result's `warnings` array (`code: "sensitive-content"`, including the chunk file and line number). It is not done in the sync step (sub agent): the script is the only reliable execution point, and the report is returned structurally with the export result, not relying on the LLM's self-discipline.

```
def check_integrity(state, jsonl_files) -> IntegrityReport:
    discovered = {str(f) for f in jsonl_files}
    for key, fi in state.files.items():
        if key not in discovered:
            report.deleted.append(key); continue
        st = Path(key).stat()
        if st.st_mtime == fi.mtime and st.st_size == fi.size:
            continue                                  # fast path, skip hash
        h = compute_file_sha256(key)
        if h == fi.sha256:
            fi.mtime, fi.size = st.st_mtime, st.st_size   # refresh metadata
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

**Re-export handling (interaction with A)**: re-export of a truncated/replaced file `f` = parse the whole file from line 1 → self-contained pagination (the file internally sorted by timestamp) → new batch (mode=`full-file`, `line_ranges` covering 1..last line) → set `committed_lines=0, exported_lines=last line` → the file's old in-flight batch becomes `failed(superseded)`.

- Why re-export covers from line 1 rather than `committed+1`: after truncation old line numbers are meaningless, and a replaced file may contain new content; **the knowledge for already-committed parts is in the KB (`[D]` entries)**, duplicate content is caught by dedup—better to read more than to miss.
- Why not do "re-paginate all files for global order consistency", cost trade-off: re-paginating all files on any file change would shift **all** chunk boundaries → sub agent re-analyzes everything, high token cost (~$4). Compromise: only the changed file is self-containedly re-exported; batch-level global order is handled by the orchestrator sorting analysis by `time_range.start`, with KB dedup covering quality. `config.sync_engine.full_repaginate_on_integrity` (default false) can enable strong-consistency mode.

### B.4 Edge Cases

| Scenario | Behavior |
|------|------|
| Claude Code keeps appending to the file during export | The export holds its own lock, which cannot stop Claude Code writing JSONL. The snapshot may be inconsistent → the next integrity check (hash changed) auto-re-exports that file, self-healing |
| Coarse mtime granularity (FAT/network drive) | The fast path is only an optimization; even if "unchanged" is misjudged, the hash-comparison fallback still triggers when mtime/size change; if mtime is completely unchanged but content changed (rare) → the next append changes size, still triggering |
| After truncation the line `committed_lines` points to no longer exists | committed knowledge is already in the KB; re-export re-analyzes from line 1, dedup covers it |
| File rotated to a new file with the same name (Claude Code long-session behavior) | Falls into the replaced/truncated branch (determined by hash+size), auto re-export |
| New file is a rotation product (old file deleted) | Old file goes to the deleted branch (WARN + cleanup), new file goes to the new_files branch (full export) |
| hash computation cost (14MB ≈ tens of ms) | Computed only when mtime/size change; normal incremental (append-only) computes once per run, acceptable |

### B.5 Acceptance Criteria

1. **Truncation detection**: back up the JSONL → truncate with `head -n 500` → incremental export → assert: `status=partial`, WARN contains the file, the file is fully re-exported (new batch line_ranges starts from 1), `committed_lines=0`.
2. **Replacement detection**: rewrite the file content entirely (same length) → incremental export → assert as above (conservative full re-export).
3. **Fast path**: file untouched → incremental export computes no hash (can use a monkeypatch counter to assert `compute_file_sha256` was not called).
4. **Append path**: normally append N lines (hash changes, size grows) → incremental export → no full re-export, only an incremental batch.
5. **Deletion detection**: move a file in state elsewhere → incremental export → WARN + removal from `files` + related uncommitted batch `failed(deleted)`.
6. **New file**: place a new session JSONL → incremental export → the new file is fully exported from line 1 as a new batch.
7. **Self-healing**: manually rewrite the source file mid-export → the next incremental must trigger re-export and WARN.

---

## Module C: Atomic State Write (Fix Critical 3)

### C.1 Goals

- Change `save_sync_state` to tmp + flush + fsync + `os.replace` atomic mode.
- Include `.tmp` residue in `CLEANUP_PATTERNS`.
- `load_sync_state` **no longer silently falls back to empty state** on a corrupt state: explicit WARN + tiered recovery strategy.

### C.2 Write Flow (reworked `save_sync_state`)

```
def save_sync_state(state, state_file):
    # 1. keep the previous good state (for recovery)
    if state_file.exists():
        shutil.copy2(state_file, state_file.with_suffix(".json.bak"))   # best effort, failure does not block
    # 2. write tmp (same directory as target → same filesystem → atomic rename precondition)
    tmp = state_file.with_name(state_file.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state_to_dict(state), f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())                  # data persisted to disk
    # 3. atomic replace
    os.replace(tmp, state_file)
    # 4. best-effort fsync of the directory on POSIX; Windows has no such API, skip (NTFS rename atomicity suffices)
    try:
        dfd = os.open(state_file.parent, os.O_RDONLY); os.fsync(dfd); os.close(dfd)
    except OSError:
        pass
```

- Called within the same `export.lock`; write failure (disk full/permissions) → raises → `main` outputs `failed, code=state-write-failed`, **cursor not advanced** (ordering guarantee: chunks written first, state last; if the state write fails → chunks become orphans, removed by cleanup, no data-loss semantics).
- The chunk files themselves are also atomically written (`chunk-….md.tmp` + `os.replace`), preventing the sub agent from reading a half-written chunk.

### C.3 Load and Recovery (reworked `load_sync_state`)

```
def load_sync_state(state_file) -> SyncState:
    if not state_file.exists():
        print INFO "first run, no state file"
        return _empty_state()                     # normal first-run path, not a silent fallback
    try:
        data = json.load(open(state_file, encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        # —— no longer silently fall back to empty state ——
        bak = state_file.with_suffix(".json.bak")
        if bak.exists() and bak parseable:
            print WARN f"state file corrupt ({e}), recovered from {bak}; corrupt file renamed and kept: sync-state.json.corrupt-{ts}"
            os.replace(state_file, state_file.with_name("sync-state.json.corrupt-" + ts))
            return load_from(bak)                 # with recovered_from_backup marker
        raise StateCorruptError(
            f"state file corrupt and no usable backup: {state_file}. Repair and retry, or explicitly run --mode full to re-initialize (will re-export all history and will not silently lose data)."
        )
    # schema validation (v3.5.0)
    if not isinstance(data, dict) or data.get("schema") not in (None, "sync-state"):
        → WARN + handle via the recovery chain above
    # field-level tolerance preserved (v3.4.0's M3 behavior unchanged): per-field get + type validation, bad fields skipped with WARN
```

**Recovery strategy tiers**:

| Corruption case | Recovery action | Silent? |
|----------|---------|---------|
| file missing | first run, empty state + INFO | normal path (with a hint) |
| parse failure, `.bak` exists and is intact | recover from `.bak` + WARN + corrupt file renamed and kept | WARN, no data loss |
| parse failure, no `.bak` | **fail and exit** (`failed, code=state-corrupt`), prompting explicit full re-export | never silent (preserves v3.9.0's "forbid accidental reset" principle) |
| schema field abnormal | per-field tolerance + WARN summary | WARN |

> Note: `.bak` is the previous state version (may lag a batch). After recovering from `.bak`, the missing batch causes the next incremental to regenerate chunks (module A), with no data loss.

### C.4 Cleanup

`CLEANUP_PATTERNS` adds a temp-file pattern:

```python
CLEANUP_PATTERNS = ("chunk-*.md", "chunk-inc-*.md", "sync-state.json", "*.tmp")
```

> ⚠️ **Note (v4.1.6 addendum, V4.1.2 change)**: `sync-state.json` has been removed from `CLEANUP_PATTERNS`
> (to prevent accidentally deleting the state file). The current implementation (`evolution-export.py`) is
> `("chunk-*.md", "chunk-inc-*.md", "*.tmp")`; the above code block including `sync-state.json` is the initial draft design;
> the implementation is authoritative.

- `*.tmp` covers `sync-state.json.tmp`, `chunk-….md.tmp`.
- `sync-state.json.bak` and `sync-state.json.corrupt-*` are kept out of cleanup (for recovery / audit), and their existence is reported in `--mode status` output.
- The new naming `chunk-<batch_id>-<i>.md` still has the `chunk-` prefix, so existing pattern matching is unchanged.

### C.5 Edge Cases

| Scenario | Behavior |
|------|------|
| kill -9 mid-save | tmp residue; original file intact; next cleanup deletes tmp; next save overwrites tmp |
| `os.replace` across volumes | tmp and target are in the same directory → same volume, no cross-volume issue |
| Disk full | save raises → `failed, state-write-failed`, cursor not advanced, orphan chunks can be cleaned |
| Permissions/read-only directory | same as above, explicit failure |
| `.bak` copy failure | does not block the main flow (recovery chain degrades to the "no .bak" branch) |
| State file corrupted by external edit | parse failure → recovery chain |
| `--mode status` reads a corrupt file | also goes through the recovery chain (read-only command does not write, only reports) |

### C.6 Acceptance Criteria

1. **Atomicity**: loop 200 saves (each writing a large JSON), interrupt at random moments with a child-process kill -9 → after each, `json.load` succeeds, or the file is absent but `.bak` is recoverable (no half JSON may remain under the main filename).
2. **tmp cleanup**: manually place `sync-state.json.tmp` and `chunk-x.md.tmp` → `--mode cleanup` → both deleted; `.bak`/`.corrupt-*` kept.
3. **Corruption recovery**: manually corrupt sync-state.json (truncate half) and keep `.bak` → run incremental → assert WARN + `recovered_from_backup=true` + normal behavior.
4. **No-backup failure**: delete `.bak` then corrupt the main file → run incremental → assert `status=failed, code=state-corrupt`, exit code 1, **no chunk/state modification produced**.
5. **Orphan chunk**: manually place `chunk-foo.md` (not referenced by any batch) → cleanup deletes it.

---

## Module D: Parse Defense and Streaming (Robustness)

### D.1 Parse Defense (Fix D1)

**Before**:

```python
def _try_extract_entry(raw_line, line_num, file_name):
    line = raw_line.strip()
    if not line: return None
    try:
        entry = json.loads(line)
    except json.JSONDecodeError:
        print(WARN); return None
    if entry.get('type') not in ('user', 'assistant'):   # ← null/[]/123 AttributeError here
        return None
    return extract_conversation_content(entry, line_num) # ← entry is a dict but abnormal message/content shape also blows up
```

**After**:

```python
def _try_extract_entry(raw_line, line_num, file_name, stats: ParseStats) -> Optional[ConversationEntry]:
    line = raw_line.strip()
    if not line:
        stats.blank += 1; return None
    try:
        entry = json.loads(line)
    except json.JSONDecodeError:
        stats.json_decode_errors += 1
        warn_rate_limited(file_name, line_num, "JSON parse failed"); return None
    if not isinstance(entry, dict):                      # ← new: null/[]/123/true
        stats.not_dict += 1
        warn_rate_limited(file_name, line_num, f"abnormal entry shape ({type(entry).__name__}), skipped"); return None
    try:
        if entry.get('type') not in ('user', 'assistant'):
            stats.wrong_type += 1; return None
        return extract_conversation_content(entry, line_num)
    except (AttributeError, TypeError, KeyError, ValueError) as e:
        stats.extract_errors += 1
        warn_rate_limited(file_name, line_num, f"content extraction failed: {e}"); return None
```

Supporting hardening of `extract_conversation_content`:

- `msg = entry.get('message')`; `if not isinstance(msg, dict): msg = {}`.
- `content = msg.get('content', '')` not str and not list → treat as empty.
- `block.get('thinking'/'text'/'content')` not str → `str()` coercion (`errors='replace'` semantics), eliminating `len(non-str)` TypeError.
- `timestamp` not str → take `str()`, otherwise set to empty string.
- Per-file error-line counts go into `ParseStats`, and the export result carries `parse_stats` (observability, see E).

**`ParseStats` structure**:

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

`wrong_type` exceeding a threshold share (e.g. > 50%) → result `status=partial` + WARN "file may not be in Claude Code session format".

### D.2 Streaming Full Export (Fix D3)

**Memory model**: at any moment only (a) **one generator per file** (streaming parse, O(1)), (b) the current turn buffer, (c) the current chunk + the previous chunk (tail merge with lookbehind=1, **a buffered chunk is not written to disk until it is confirmed it will not be merged**—see the N-11 note in the D.2 pseudocode). There is no longer a cross-file `all_entries` accumulation.

**Two-pass scan + k-way merge (preserving global time order, see D.5)**:

```
pass 1 (metadata, O(1) memory):
    for f in files:                       # mtime order
        stream-count total_lines / entry count / first_ts / last_ts / whether timestamps are monotonic
pass 2 (merge export):
    gens = [parse_jsonl(f, 0) for f in files]          # N generators, N file handles (Windows limit 512, sufficient)
    heap = heapq.merge(*gens, key=lambda e: sort_key(e))   # key = (normalized_ts, file_index, line_no)
    paginate_stream(heap) → chunk full → atomically write chunk-<batch_id>-<i>.md → continue
    after the batch is built, atomically save state (module C)
```

- If a source file is appended between pass1/pass2 → the snapshot is slightly inconsistent → the next integrity check self-heals (B.4).
- A single file may still be large: in pass 2 the entries of a single file flow through the generator without residing in memory; if a single file is unacceptably large (e.g. >200MB), record it as a known extension item (external sort), not implemented this cycle.

**Streaming paginator `paginate_stream(entry_iter, ...)` (reworking `paginate_entries`)**:

```
cur_chunk, cur_turn, cur_session = [], [], None
last_chunk = None                                    # lookbehind=1 buffer (used by M1 tail merge);
                                                     # ★ N-11: the buffered chunk is not yet written to disk,
                                                     # it is atomically written only when confirmed it will not be merged

for e in entry_iter:                                 # already globally time-ordered
    if e.session != cur_session:                     # session change → close the current turn (D.5 key point)
        flush_turn()
    elif e.role == 'user' and cur_turn:
        flush_turn()                                 # same session new user → close the current turn
    cur_turn.append(e)

flush_turn():
    if cur_chunk and chunk_tokens(cur_chunk) + turn_tokens(cur_turn) > target:
        flush_chunk()
    if turn_tokens(cur_turn) > max_tokens:
        flush_chunk(force=True)                      # ★ unconditional flush first (fixes D4 time disorder)
        for st in split_large_turn(cur_turn, max_tokens):
            emit_chunk(st)                           # each sub_turn becomes its own chunk
    else:
        cur_chunk.extend(cur_turn)

flush_chunk(force=False):
    if not cur_chunk: return
    emit_chunk(cur_chunk)

emit_chunk(c):
    if last_chunk and tokens(last_chunk)+tokens(c) <= max_tokens
       and tokens(last_chunk) < min_tokens:          # M1: merge the small tail into the previous block (only if the merge stays under the limit)
        last_chunk.extend(c)                         # only mutate the in-memory buffer, no disk write (N-11)
    else:
        if last_chunk is not None:
            write_chunk(last_chunk)                  # buffer confirmed it will not be merged → only now atomically write to disk
        last_chunk = c

finalize():                                          # must be called after the stream ends
    if last_chunk is not None:
        write_chunk(last_chunk)                      # flush the last buffered chunk
```

> **N-11 note**: the old pseudocode called `write_chunk(c)` immediately inside `emit_chunk`, while a later chunk could still be merged into `last_chunk` via M1—an already-written file would be rewritten, breaking the batch invariant that "a chunk is immutable once written to disk" (manifest sha256 invalidated). Fix: **buffer one chunk before writing to disk**—only when the next chunk arrives and no merge occurs is the buffer written to disk; at stream end `finalize()` flushes the tail. The cost is one extra chunk held in memory at any time (bounded).

### D.3 Oversized-Turn Time Disorder Fix (D4) — Root Cause and Fix

**Root cause** (current `paginate_entries` large-turn branch):

```python
if turn_tokens > max_tokens:
    if current_chunk and current_tokens > min_tokens:   # ← small tail not flushed
        chunks.append(current_chunk); current_chunk = []
    sub_turns = split_large_turn(...)
    for st in sub_turns: chunks.append(st)              # large-turn chunks enqueued first
```

When a large turn arrives, `current_chunk` has less than `min_tokens` and is **not flushed**, so it keeps being filled by later turns' content and ends up placed **after the large-turn chunk**—the last chunk's time range (containing old entries before the large turn) inverts to before the preceding chunk. **Fix**: on encountering a large turn **unconditionally** flush first (`force=True`); the `min_tokens` merge logic is kept only in `emit_chunk`'s lookbehind tail merge (the merge target is "the immediately preceding block", constrained by `max_tokens`, so order is not broken—see the D.2 pseudocode).

**Acceptance assertion**: for any export result, `chunk[i].time_range.end <= chunk[i+1].time_range.start` (closed-interval endpoints), including oversized-turn samples.

### D.4 Token Estimation Correction (D2)

- Introduce `sync_engine.estimate_safety_factor` (default **1.5**, configurable). All pagination decisions use `tokens_effective = estimate × factor` (the 90K target and the 200K hard cap both act on effective).
- Rationale: adversarial review measured a 1.3–2x underestimate; under a 1.5 factor, effective 200K ≈ the middle of the actual 260K–400K, still within the 1M sub agent window (the cap is a quality soft constraint, not a crash threshold).
- Second safeguard: `max_chunk_chars = max_chunk_tokens × 4` (default 800K characters, derived from the worst case of 4 chars/token for English) as a hard guard for when the estimator fails completely—the chunk is immediately truncated at a turn boundary when its character count exceeds the limit.
- The chunk records `tokens_est` (raw estimate), `tokens_effective` (after the factor), and `chars`, for later calibration of the coefficient with a real tokenizer.
- The budgets of `truncate_entry` / `split_large_turn` likewise use effective.

### D.5 Global Timestamp Sorting (D5)

- **Sort key**: `(normalized_timestamp, file_index, line_no)`.
- `normalized_timestamp`: prefer `datetime.fromisoformat` (compatible with `Z` and `+08:00`, unified to a microsecond integer); parse failure/missing → goes into the "unknown time" bucket, placed at the tail of the same batch while preserving (file_index, line_no) relative order (deterministic).
- **No longer relies on file mtime concatenation order** (mtime is only used for file discovery order and pass1).
- **Turn grouping must be session-aware** (after global sorting, entries from different sessions interleave; the old `group_into_turns` would stitch session A's user with session B's assistant into one turn—the current code has this hazard too): the turn-switch condition = a new user entry (same session) **or** a session change (see D.2 `flush_turn`).
- The incremental path likewise globally sorts delta (guaranteeing intra-chunk time order when multiple sessions each contribute a few lines).

### D.6 Edge Cases

| Scenario | Behavior |
|------|------|
| null/[]/123/true lines | skipped + counted (`not_dict`), no crash |
| `message` not dict / `content` neither str nor list | treated as empty, no crash |
| `timestamp` missing/non-str/mixed formats (Z vs offset) | normalized; unparseable goes to the unknown bucket |
| Single entry > max_tokens | `truncate_entry` fallback (existing M2, switched to effective budget) |
| Oversized turn (>max) | unconditional flush + sub_turns as independent chunks (D.3) |
| Turn spanning sessions | session-aware grouping (D.5) |
| All-bad-lines file | all skipped, shown in `parse_stats`; too high a share → `partial` + WARN |
| Multiple entries with the same timestamp | tie-breaker (file_index, line_no) for deterministic order |
| Non-UTF-8 bytes | `errors='replace'` (existing) |
| Small tail chunk | lookbehind merge, not exceeding max (M1 semantics preserved); the merge target is the **not-yet-written buffered chunk** (N-11), immutable once written |
| Single file very large (>200MB) | accepted this cycle (generator streaming), extension item: external sort |

### D.7 Acceptance Criteria

1. **Bad lines do not crash**: construct a JSONL containing `null`, `[]`, `123`, `{"type":1}`, `{"message":"x"}` lines → full export succeeds (or partial), `parse_stats` counts correct, no exception stack.
2. **Memory upper bound**: use `tracemalloc` or `/proc` peak RSS to assert the full-export peak memory is independent of file count (two-pass scan + single chunk); for 3 15MB files vs 1 15MB file the peak memory difference is < 2×.
3. **Time order**: construct two time-interleaved session files (A's later segment earlier than B's earlier segment) → full export → assert intra-chunk entry timestamps are globally non-decreasing, and inter-chunk time ranges do not overlap or regress.
4. **Oversized turn**: construct a single turn of 500K tokens → export → assert all chunk time ranges are monotonic (D.3 assertion).
5. **Cross-session turns**: interleave a session's user/assistant messages → assert no chunk mixes turns from different sessions.
6. **token factor**: pure-CJK large-text chunk → assert `tokens_effective ≤ 200K` and `chars ≤ 800K`; adjust the config factor → behavior follows.
7. **Incremental global sorting**: two sessions each append lines, time-interleaved → intra-chunk incremental time non-decreasing.
8. **Chunk immutable after write** (N-11): construct a sample that triggers the M1 tail merge (a small-tail chunk followed by a normal chunk) → assert each chunk file is written only once, and the manifest sha256 matches the final file content.

---

## Module E: Command and Observability Protocol

### E.1 Goals

- Extend the script's return status to explicit `success / partial / failed` semantics + structured `warnings`.
- Define the batch lifecycle protocol between the main agent ↔ sub agent: **the sub agent must report a commit receipt to count as success**.
- Normalize user-visible error messages (symptom/cause/impact/recovery action), no more silent success.

### E.2 Script Return Protocol

**Exit code**: `0 = success`; `1 = failed` (abort); `2 = partial` (completed with data-quality warnings; the sub agent must convey the warnings to the main agent and report to the user).

> ⚠️ **Note (v4.1.6 addendum, V4.1.2 change)**: The exit-code protocol has been simplified to 0/1—`partial` also exits 0
> (distinguished by the returned JSON's `status` field), and `2 = partial` is no longer used.
> The authoritative definition is in the "exit code protocol" of `.claude/skills/evolution/commands/sync.md`; the above `2 = partial`
> and the "assert 2" in the E.6 acceptance criteria are the initial draft design; the implementation is authoritative.

**`status` field semantics**:

| status | Meaning | sub agent action |
|--------|------|---------------|
| `success` | data complete, batch created (or no new content), no warnings | continue analyzing the batch (if any) → commit |
| `success` + `new_entries: 0` | no new content | report "no updates" (including the pending hint) |
| `partial` | export completed but with integrity/parse warnings (re-export, bad-line share, retry-exhausted, etc.) | must report warnings to the main agent, then continue analysis |
| `failed` | abort (lock timeout, state-corrupt, no JSONL, validation failure) | stop and report, must not continue |

**New export-result fields**:

```json
{
  "status": "success",
  "mode": "incremental",
  "new_entries": 215,
  "parse_stats": { "...": "see D.1" },
  "warnings": [
    { "code": "file-truncated", "file": "…jsonl", "detail": "size 15000000 → 180000, fully re-exported", "action": "recommend manually confirming whether this session was rotated" }
  ],
  "batches": [
    { "batch_id": "inc-20260101-000000-0001", "status": "exported", "chunks": 1, "entries": 215,
      "time_range": { "start": "…", "end": "…" }, "retry_count": 0 }
  ],
  "pending_batches": [],
  "action_hint": "analyze_and_commit" | "analyze_pending" | null,
  "sync_state": { "version": "3.5.0", "...": "summary" }
}
```

**New/changed CLI**:

| Mode | Description |
|------|------|
| `--mode incremental` | incremental export (automatically handles pending/failed batch regeneration) |
| `--mode full` | full export (creates a full batch) |
| `--mode commit --batch-id <id>` | batch confirmed persisted, advances the committed cursor, returns a receipt (A.3) |
| `--mode commit --batch-id <id> --force` | **forced confirmation (F-3/N-4)**: skip analysis and directly confirm the batch. Outputs a prominent warning "forced confirmation will permanently skip the unanalyzed content of this batch", and requires the receipt to record `forced: true` for auditing. Only for `failed(analysis-exhausted)` or scenarios the user explicitly directs |
| `--mode analyze-failed --batch-id <id>` | **(F-3/N-4)**: report one analysis failure—increments the batch's `analysis_failures` count; on reaching the limit (`max_analysis_failures`, default 3) the status is set to `failed(analysis-exhausted)` with a WARN prompting human intervention (`--force` forced confirmation or wait for the failed regeneration loop) |
| `--mode start --batch-id <id>` | (optional) mark analyzing, informational only |
| `--mode status [--verify]` | status + batch summary; `--verify` additionally runs an integrity check (read-only hash comparison); output includes each batch's `analysis_failures` count (F-3 observability) |
| `--mode cleanup` | cleanup (including `*.tmp`, see C.4) |

> F-3 liveness protocol: each time the sub agent fails to analyze a batch (chunk unreadable, context over limit, before a mid-way crash) it should call `--mode analyze-failed --batch-id <id>` to record the count; the main agent warns "batch X unconfirmed for 2 consecutive rounds" when the summary lacks a receipt for 2 rounds; `analysis_failures >= 3` → the batch automatically turns `failed(analysis-exhausted)`, exiting the blocking loop (liveness guarantee).

### E.3 Main Agent ↔ Sub Agent Protocol (sync.md / SKILL.md need synchronized updates)

```
main agent triggers /evolution
    ↓
sub agent:
  1. python evolution-export.py --mode incremental
     ├─ exit 0 + status=success, new_entries=0  → if pending_batches is non-empty → go to 2 (continue analysis for pending batches, N-2)
     ├─ exit 0 + status=success, action_hint=analyze_and_commit → go to 2
     ├─ exit 0/2 + partial → first relay warnings to the main agent, then go to 2/3
     └─ exit 1 + failed → stop, report {code, message, action} to the main agent
  2. for each batch in result.batches ∪ result.pending_batches with status ∈ {exported, analyzing}
     analyze (do not filter by status—after resume sets it, the batch status is analyzing;
     handling only exported would "commit before analysis", fixed by N-2):
     a. read the batch chunks one by one (paths taken only from the batch manifest, manual globbing forbidden)
     b. analyze chunk by chunk → write into the knowledge base via kb-manager.py add ([P] isolation, F-5 sole write entry)
  3. python evolution-export.py --mode commit --batch-id <id>
     ├─ exit 0 → record receipt {batch_id, receipt_hash}
     └─ non-0 → treat the batch as incomplete, report to the main agent (auto-recovers on the next /evolution round)
  4. the final summary must include: batch id, chunk count, extracted knowledge count (by category), commit receipt (batch_id + receipt_hash)
    ↓
main agent:
  - if the summary lacks a receipt or receipt verification fails → judge this sync as incomplete, prompt the user to re-run or check
```

**Error message specification** (all user-visible `failed/partial` output follows):

```
[Symptom] state file corrupt: .evolution/chunks/sync-state.json (JSON parse failed)
[Cause] the previous write was interrupted or a disk anomaly occurred
[Impact] cannot safely advance the sync cursor; this export was aborted and made no modifications
[Recovery] automatically attempted .bak recovery but failed; please check the file and retry, or explicitly run:
       python evolution-export.py --mode full   (will re-export all history, will not silently lose data)
```

`warnings` array elements uniformly contain the four fields `code / file / detail / action`.

### E.4 Trust Boundary (must be documented)

- The script **cannot verify** that knowledge was actually written into the KB—commit is the sub agent's declaration of "persisted" (protocol constraint), and reliability is backed by: ① the receipt must be reported to the main agent (protocol); ② knowledge entries are marked `[D]` pending human review (existing mechanism); ③ batch regeneration/re-analysis is idempotent (KB dedup).
- Once a batch is committed the cursor advances; if the sub agent falsely commits (analysis not done), data is still lost—this risk is mitigated by `[D]` review + main agent summary verification; stronger script-side verification is not accepted (not implementable).

### E.5 Edge Cases

| Scenario | Behavior |
|------|------|
| sub agent does not report a receipt | the main agent judges the sync incomplete, recovers next round (the batch remains) |
| sub agent analysis repeatedly fails | `--mode analyze-failed` increments `analysis_failures`; on reaching the limit → `failed(analysis-exhausted)` + WARN (F-3/N-4) |
| User force-confirms an analysis-exhausted batch | `--mode commit --force`: outputs a prominent warning "forced confirmation will permanently skip the unanalyzed content of this batch", receipt records `forced: true` |
| Commit when the batch is already committed | idempotent success |
| Commit when the batch is failed | error `batch-failed` + recovery guidance |
| Script invoked concurrently (two sub agents running at once) | `export.lock` timeout → failed(lock-timeout), explicit error |
| `--mode status` shows an uncommitted batch | `pending_batches` highlighted, prompting continued analysis; batches unconfirmed for 2 consecutive rounds get a prominent WARN (F-3) |
| cleanup deletes an uncommitted batch's chunks | next incremental auto-regenerates (A.3) |
| `parse_stats` abnormal share high | `partial` + WARN, sub agent relays to the user |

### E.6 Acceptance Criteria

1. **Protocol end-to-end**: script a simulated sub agent (bash: incremental → read batch → commit → status) → assert exit code and JSON fields throughout.
2. **Exit codes**: each error scenario (no JSONL, lock timeout, state-corrupt, batch-not-found) asserts exit code 1; scenarios with warnings (truncation) assert 2; normal asserts 0.
3. **receipt idempotency**: commit twice → identical `receipt_hash`.
4. **Missing-report detection**: run incremental without commit → `--mode status`'s `pending_batches` is non-empty and contains the batch.
5. **Four-element error message**: artificially produce state-corrupt and file-truncated → assert the output contains symptom/cause/impact/recovery and `code/file/detail/action`.

---

## Migration Path (old sync-state.json → v3.5.0)

### Input (measured online sample: version label `"3.2.1"`, structure = v3.4.0 doc structure)

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

### Migration function `migrate_34x_to_350(old) -> new` (shared by 3.2.1 and 3.4.0)

```
new.version = "3.5.0"; new.schema = "sync-state"
new.batch_seq = 1
for k, f in old.files:
    new.files[k] = {
        path, sha256, mtime, total_lines,
        exported_lines = f.processed_lines,
        exported_bytes = f.processed_bytes,
        committed_lines = 0,                  # ★ old cursor was advanced before analysis, untrustworthy → conservatively set 0
        committed_bytes = 0,
        size = f.processed_bytes,             # no independent size record, approximate with processed_bytes
        first_event_timestamp = null,         # old state did not store the first timestamp, backfilled on re-export
        last_event_timestamp = original value,
        integrity_warnings = 0
    }
# ★ migration batch: let the next incremental re-confirm all exported lines (re-analyze once, KB dedup covers it)
if the output directory has chunk-*.md files (not referenced by any batch):
    batches["mig-<ts>-<seq>"] = {
        batch_id, mode="migration", status="exported", reason=null,
        line_ranges = null,                   # old chunks have no line-range info
        chunks = [legacy chunk-*.md referenced in filename order, line_ranges all null],
        time_range = null, commit_receipt = null, retry_count = 0
    }
else:
    # no legacy chunks → create a placeholder batch; the next incremental handles it via the failed regeneration loop (N-3):
    # migration batch regeneration is special-cased as whole-file re-export from line 1 (line_ranges: {f: [1, exported_lines]})
    batches["mig-<ts>-<seq>"] = { …, status="failed", reason="migration-unverified" }
```

**Recovery path for failed migration batches (clarified by N-3)**: a migration batch with `status=failed, reason=migration-unverified` **does not count as in-flight** (does not block its file's incremental export); A.3's dedicated failed-batch regeneration loop will `regenerate_batch` it in the next round (migration special case: whole-file re-export from line 1), the old batch is marked `superseded`, and the new batch normally enters analysis.

**Cost of the conservative default and the escape valve**:

- Default (`config.sync_engine.migration.trust_committed = false`): after migration **the next incremental sync re-analyzes the entire history once** (chunks reuse legacy files or are regenerated), costing ≈ one full analysis (~$4, with few new entries after KB dedup). Safe and bounded.
- Escape valve: after the user confirms the knowledge base is complete, set `migration.trust_committed: true` → on migration `committed_lines = exported_lines`, and no migration batch is created (zero extra cost). This switch must be set explicitly, and the migration report outputs `migration_mode: "trusted"` for auditing.

> ⚠️ **Implementation status (verified in v4.1.2)**: The above `migration.trust_committed` escape valve is **not implemented**—
> `evolution-export.py` has no CLI path that produces a `mode="migration"` batch (only `full` / `incremental` create batches),
> and `config.yaml` has no `migration:` config section. This paragraph is a design promise not yet landed; do not configure based on it.

**Downgrade migration (completely different structure, e.g. the `last_sync/file_info/stats/export_history` era)**: `MIGRATIONS` has no corresponding function → `failed, code=state-version-unknown` + explicit guidance (back up, then `--mode full`).

**Migration acceptance**:

1. Use the online sample (3.2.1 label) → first incremental run → assert: version becomes 3.5.0; `committed_lines=0`; a migration batch exists; the export result references the migration batch and the chunk content matches the legacy files (or is regenerated).
2. After migration, commit the migration batch → `committed_lines` advances to the old processed_lines; incremental again → only truly new lines are exported.
3. `trust_committed: true` → migration creates no batch, committed = exported, zero re-analysis.
4. Simulate a future-version (version 4.0.0) state → old script runs → reject modification (`state-version-newer`).
5. Migration does not lose `last_full_sync / last_incremental_sync / project_hash`.
6. **failed migration batch recovery** (N-3): construct a migration with no legacy chunks → assert a `failed(migration-unverified)` batch is produced → next incremental does not block the file, the failed regeneration loop produces a new batch (whole-file line_ranges from 1), old batch marked superseded.

---

## Implementation Order and Effort Estimate

| Phase | Content | Dependency | Effort |
|------|------|------|--------|
| P0 | Test scaffolding: build JSONL fixtures, state-file fixtures, bad-line/truncation/interruption simulation tools, end-to-end scripted sub agent simulation | — | 0.5 person-days |
| P1 | Module C: atomic write, load recovery chain, `.bak`/`.tmp`/cleanup, chunk atomic write | P0 | 0.5 person-days |
| P2 | Module D-1: `_try_extract_entry` defense + `ParseStats` + extraction-function hardening | — | 0.5 person-days |
| P3 | Module A: schema 3.5.0, dual cursors, batch state machine, `--mode commit/start`, regeneration, migration function and migration batch | P1 | 1.5–2 person-days |
| P4 | Module B: `check_integrity` + re-export interaction + decision-table implementation | P3 | 1 person-day |
| P5 | Module D-2/D-3/D-4/D-5: streaming pagination, large-turn fix, global sorting (k-way), session-aware turns, token factor | P2 (independent) | 1.5–2 person-days |
| P6 | Module E: exit codes, warnings, protocol documentation, sync.md/SKILL.md updates (including F-3 analyze-failed / commit --force CLI) | P3/P4 | 0.5 person-days |
| P7 | Full acceptance: run every module's acceptance criteria one by one + regression on real online data | all | 1 person-day |

**Total: about 6–8 person-days.** Recommended order P0 → P1 → P2 → P3 → P4 → P5 → P6 → P7; P2 and P5 can be parallel.

**Risks and mitigations**:

| Risk | Mitigation |
|------|------|
| The default one-time full re-analysis cost after migration (~$4) causing user dissatisfaction | Escape valve `trust_committed` + explicit WARN explaining why |
| k-way merge handle pressure with many session files (>100) | Measure the limit; fall back to chunked merge when exceeded (extension item) |
| Single file >200MB | Accepted (generator streaming), listed as an external-sort extension item |
| `estimate_safety_factor` value deviation | The factor is configurable; the chunk records `tokens_est/effective/chars` for calibration against a real tokenizer |
| Windows `os.replace` vs a writer holding the file open | The state file has no long-term holder (read/written within the script process), small conflict surface |

---

## Appendix A: New config.yaml Items

```yaml
# Sync engine (V4.0.0)
sync_engine:
  estimate_safety_factor: 1.5        # token estimation safety factor (adversarial review measured a 1.3–2x underestimate)
  max_chunk_chars: 800000            # character hard guard = max_chunk_tokens × 4
  max_batch_retries: 3               # batch regeneration limit; exceeded → failed(retry-exhausted)
  max_analysis_failures: 3           # batch analysis failure limit; exceeded → failed(analysis-exhausted) (F-3/N-4)
  keep_committed_batches: 20         # number of committed batches retained for audit
  full_repaginate_on_integrity: false# whether to fully re-paginate on integrity re-export (strong consistency, expensive)
  migration:
    trust_committed: false           # trust that old processed_lines were persisted during migration (skip re-analysis)
```

## Appendix B: CLEANUP_PATTERNS / File Naming Changes

```python
CLEANUP_PATTERNS = ("chunk-*.md", "chunk-inc-*.md", "sync-state.json", "*.tmp")
# retained: sync-state.json.bak, sync-state.json.corrupt-*
# chunk naming: chunk-<batch_id>-<i:02d>.md (the batch_id prefix pattern is still covered by chunk-*.md)
```

> ⚠️ **Note (v4.1.6 addendum, V4.1.2 change)**: Same as the C.4 note, `sync-state.json` has been removed from
> `CLEANUP_PATTERNS`; the current implementation is `("chunk-*.md", "chunk-inc-*.md", "*.tmp")`.

## Appendix C: Interface Change List with Existing Docs/Commands

- `docsV3/EXPORT_AND_ANALYSIS_DESIGN.md`: sections 4.6 State Management, 4.8 Error Matrix, 8.x Execution Flow need updating with V4 (a later-version task).
- `.claude/skills/evolution/commands/sync.md`: add the batch commit step and receipt-reporting requirement (module E.3, including the N-2 revision: step 2 handles all exported/analyzing batches; F-3: call `--mode analyze-failed` on analysis failure).
- `.claude/skills/evolution/SKILL.md`: add to the rules table "a batch must be committed to count as complete".

---

**End of document**
