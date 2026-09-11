# Evolution V4.0.0 Design Document (Master Outline)

🌐 **Language / 语言**: [English](DESIGN_V4.0.0.md) | [中文](DESIGN_V4.0.0.zh-CN.md)

> ⚠️ **Rollback Banner (v4.1.2 addendum)**: This document is the V4.0.0 design historical draft. **The knowledge-layer design was rolled back in v4.1.0**——
> `[P]` quarantine / pending.md, the four-tier status model (`[P]/[D]/[V]/[X]/[C]/blocked`), `kb-manager.py` as the sole write entry point,
> knowledge lifecycle, and the sensitive-data gate are **not retained in the current implementation**; status markers have reverted to the three tiers `[D]/[V]/[X]`.
> The escape valve `migration.trust_committed` of the §7 migration mode is also **not implemented** (there is no CLI path in the code that produces a migration batch,
> and `config.yaml` has no `migration:` config section); it is only future planning.
> ⚠️ The `state-version-newer` rejection mechanism is **not implemented** (the code has no version-comparison logic, so a future-version state will be silently downgraded). It is only future planning.
> The engine-layer design (dual cursors, batch commit protocol, integrity check, atomic write, streaming export) is still valid and in use.
> Current system behavior is governed by `CLAUDE.md` + `.claude/skills/evolution/` + `docsV3/VERSION_HISTORY.md`.

> **Version**: 4.0.0 (design draft v2.2, incorporating independent review; v2.2 revised 2026-08-22)
> **Date**: 2026-08-16
> **Nature**: Implemented
> **Implementation date**: 2026-08-24
> **Basis**: Adversarial audit (54 agents, 39 confirmed findings) + the v4.0.0 plan in VERSION_HISTORY (cleanup mechanism, capacity monitoring, four-tier status model, evidence-type classification, proactive review process) + independent review
> **Detailed documents**:
> - [Sync Engine Layer Design (draft)](./design-v4-engine.md)
> - [Knowledge Management Layer Design (draft)](./design-v4-knowledge.md)
>
> **Revision record**:
> - v2 (2026-08-16): Incorporated independent review——added the audit coverage matrix (§14.3), fixed 6 design defects (§14.4), included 13 missed findings (§14.3 🔴 items), updated the implementation plan (§14.5). **Decision: full implementation, no cost reduction** (user instruction: cost is not a concern, accuracy is key)
> - v2.1 (2026-08-21): Second-round review fixed 8 must-fix issues——§14.3 coverage statistics (N-1), F-2 rollback manual rewritten per measured behavior (N-5), F-6 path-anchoring formula corrected (N-8), F-3 CLI landing point (N-4); engine layer N-2 resume protocol, N-3 migration/failed batch recovery path; knowledge layer N-6 blocked redacted form, N-7 systematic alignment of F-5/#23/manifest schema/regex
> - v2.2 (2026-08-22): M0 missed-fix package batch 2 executed——#23 removed phantom commands, #24 path anchoring documented (code M1 E4), #25 current-session filtering semantics finalized, #30 manual-trigger wording corrected, #32 token accounting unified, #39 README knowledge-base maintenance section; §14.3/§14.5 execution status updated in sync

---

## 1. Background and Goals

### 1.1 Why V4.0.0 (MAJOR)

The adversarial audit confirmed 39 real issues, 3 of which are Critical and would cause **permanent data loss**. The fix requires changing behavioral semantics (dual cursors, commit protocol, [P] quarantine), which under semantic versioning rules is a **MAJOR** upgrade.

### 1.2 Design Goals (The Four Nevers)

| Goal | Corresponding defense |
|------|---------|
| **Never lose data** | Dual cursors + sha256 integrity check + atomic write (engine layer) |
| **Never crash parsing** | Parse defenses + streaming + time sorting (engine layer) |
| **Never accumulate garbage** | [P] quarantine + knowledge lifecycle + transaction lock (knowledge layer) |
| **Never leak sensitive data** | Sensitive scan gate + privacy awareness (knowledge layer) |

### 1.3 Design Principles (Continuing V3)

1. All operations are executed in the background by a sub agent, transactional under lock
2. Humans only perform **minimum-cost batch review**
3. **Archive only by default, never auto-delete** knowledge body text
4. Failures are retryable and idempotent; never silently drop data, never silently roll back

---

## 2. Version and Data Format Strategy

| Item | Value | Description |
|----|-----|------|
| System version | **4.0.0** | MAJOR (behavior change) |
| sync-state data format | **3.4.0 → 3.5.0** | Field renames + additions, loader can migrate |
| Knowledge base entry format | New `kb-meta:` metadata line | Machine-parsable, backward compatible |
| Migration mode | Conservative default + escape valve | See §7 |

**Version rollback protection**: `version > VERSION` (reading new state with an old script) → reject modification, read-only remains available. Never interpret new state under the old schema.

---

## 3. Overall Architecture (V4)

```
┌─────────────────────────────────────────────────────────────┐
│                      Main Agent (user interaction layer)      │
│   /evolution · /evolution-init · /kb-review · /kb-status    │
└──────────────────────────┬──────────────────────────────────┘
                           │ trigger + receipt reporting protocol
┌──────────────────────────▼──────────────────────────────────┐
│              Sub Agent (analysis coordination layer)          │
│  ① Engine: export → batch → per-chunk analysis                │
│  ② Knowledge: sensitive scan → .kb.lock transaction → pending quarantine → state transition │
│  ③ Checkup: lifecycle scan (read-only) → report               │
│  ④ Complete: --mode commit reports receipt (batch closure)    │
└──────────┬───────────────────────────────┬──────────────────┘
           │                               │
┌──────────▼──────────┐        ┌───────────▼──────────────────┐
│  Sync Engine Layer (v3.5.0) │        │  Knowledge Management Layer (V4) │
│  · dual cursors + batch manifest │        │  · [P] quarantine pending.md │
│  · sha256 integrity check  │        │  · four-tier status + [C] + blocked │
│  · atomic state write       │        │  · .kb.lock transaction protocol │
│  · streaming parse + global sort  │        │  · lifecycle archive archive/ │
│  · success/partial/ │        │  · sensitive scan gate                │
│    failed protocol       │        │  · kb-manager.py              │
└─────────────────────┘        └──────────────────────────────┘
```

**Trust boundary**: The script cannot verify that knowledge has been ingested——commit is the sub agent's declaration, and reliability is backstopped by three layers: ① the receipt reporting protocol; ② new entries are always quarantined as [P] pending manual review; ③ batch regeneration is idempotent.

---

## 4. Sync Engine Layer (see design-v4-engine.md for details)

### 4.1 Dual Cursors + Batch Manifest (fixes Critical 1)

**Core change**: `processed_lines` → split into `exported_lines` (already exported by the script) and `committed_lines` (confirmed ingested by the sub agent).

```
Incremental export start = committed_lines + 1        (not exported_lines + 1)
```

**Batch state machine**:

```
Export complete ──▶ exported ──commit──▶ committed (idempotent)
                │
           resume/start
                ▼
           analyzing ──commit──▶ committed
                │
          retry limit exceeded / explicit failure
                ▼
            failed ──regenerate (new batch)──▶ exported
```

- Uncommitted batch (chunk intact) → next sync uses `action_hint=analyze_pending`, **does not re-export**
- Failed batch (chunk missing) → **precisely regenerated** from `line_ranges`, never skipped
- New `--mode commit --batch-id <id>` → returns a receipt carrying `receipt_hash`
- Batch pruning: the most recent 20 committed batches are retained; the cursor is unaffected

### 4.2 File Integrity Check (fixes Critical 2)

**Decision table**:

| Signal | hash | Verdict | Handling |
|------|------|------|------|
| mtime+size unchanged | not computed | fast path | normal incremental |
| changed | same | only mtime jitter | refresh metadata |
| changed | different, size smaller | **truncation/rotation** | full re-export of that file + WARN |
| changed | different, size larger | **replacement/rewrite** | conservative full re-export + WARN |
| in state, not on disk | — | deletion | batch failed(deleted), files removed |
| on disk, not in state | — | new file | full export from line 1 |

**Re-export interaction**: a re-exported file gets `committed_lines=0`, a new batch is created, and old in-flight batches are marked `failed(superseded)`. Only changed files are re-exported (to avoid full re-pagination shifting all chunk boundaries + full sub-agent re-analysis ~$4); strict-consistency mode is controlled by the config switch `full_repaginate_on_integrity` (default false).

### 4.3 Atomic State Write (fixes Critical 3)

```
tmp write → flush → fsync → os.replace (atomic) → directory fsync (POSIX)
```

- Retain `.json.bak` before writing (recovery point)
- **load no longer silently falls back to empty state**; three-tier recovery chain: `.bak` recovery (WARN) → explicit failure `state-corrupt` (suggests `--mode full`)
- Chunk files are likewise written atomically
- `CLEANUP_PATTERNS` adds `*.tmp`; `.bak`/`.corrupt-*` are retained and excluded from cleanup

### 4.4 Parse Defenses and Streaming (robustness)

| Problem | Fix |
|------|------|
| null/[]/123 lines cause AttributeError and a whole-run crash | `isinstance(entry, dict)` defense + overall capture of the three exceptions + `ParseStats` counting; bad-line ratio >50% → partial + WARN |
| token estimate too low by 1.3~2× | `estimate_safety_factor: 1.5` applied to pagination decisions + character-count hard guard `max_chunk_chars: 800K` |
| Full export OOM | two-pass scan + k-way merge streaming export (O(1) memory) |
| Huge turn causes chunk time disorder | on encountering a huge turn, **unconditionally flush** the current chunk first (root cause: a small tail being dragged after the huge-turn chunk) |
| Multi-session aggregation disorder | global `(timestamp, file_index, line_no)` sort; turn grouping is **session-aware** (prevents stitching turns across sessions) |

### 4.5 Command and Observability Protocol

- **Exit codes**: 0=success, 1=failed (aborted), 2=partial (data-quality warnings present)
- **Four elements of warnings**: `code / file / detail / action`
- **Error message specification**: `[symptom] [cause] [impact] [recovery]`
- **Main↔sub protocol**: the sub agent must report a commit receipt; if the main agent's summary lacks a receipt, the work is judged incomplete

---

## 5. Knowledge Management Layer (see design-v4-knowledge.md for details)

### 5.1 Status Model and [P] Quarantine (fixes the self-reinforcing loop)

**Key decisions**:

| Decision | Content |
|------|------|
| New `[P]` pending | 100% of AI-extracted entries first land in the separate `pending.md` quarantine file, which the normal read path **can never reach** |
| Retain `[D]`, change semantics | `[D]` = manually reviewed but insufficient evidence; the old semantics (AI-extracted, unverified) are abolished |
| `[C]` is an overlay marker | Both conflicting sides are kept in parallel in their original files, titled [C], and enter the arbitration queue |
| `blocked=secret` | Sensitive scan hit, permanently quarantined |

**State machine (legal transitions)**:

```
auto_extract ─▶ [P] ─review─▶ [D] ─strong evidence─▶ [V]
                  │ ├reject─▶ [X]            ├stale─▶ re-verification prompt (no auto-downgrade)
                  │ └conflict─▶ [C] (both sides in parallel) ├loses─▶ [X]
                  └expired─▶ archive (restore to [P])
```

**Write red line**: `[P]/[D]/[C]` may never displace `[V]` under any circumstances.

**Evidence-type binding** (tightens [V] semantics):

| Evidence | Confidence | Can support [V] |
|------|------|-------------|
| `tool_output` | 0.9 | Yes (records scope, 365-day re-verification) |
| `user_explicit` | 0.9 | Yes (must be an explicit confirmation within the review process) |
| `external_doc` | 0.7 | Yes (records document name and version) |
| `conversation_inference` | 0.5 | **No** (can only reach [D]) |
| `auto_extract` | 0.3 | **No** (can only reach [P]) |

**Entry format**: title + `> kb-meta: id/state/file/created/reviewed/source/confidence/evidence/last_used/scope/sensitive/archived_at` metadata line (machine-parsable).

### 5.2 Knowledge Lifecycle (birth, aging, death)

| Threshold (config) | Default | Action |
|----------------|------|------|
| `pending_stale_days` | 30 | [P] expired → stale marker → archive |
| `draft_stale_days` | 90 | [D] idle → downgrade prompt |
| `draft_archive_days` | 180 | [D] still idle → auto-archive |
| `verify_refresh_days` | 365 | [V] → re-verification prompt (no auto-downgrade) |
| `index_max_lines` | 500 | kb-index over limit → deterministic regeneration and compression (target <300 lines) |
| `archive_policy` | keep | **archive only, never delete** |

- Archive: `archive/YYYY-MM/<file>-<month>.md` + manifest JSON; `/kb-restore <id>` can restore (always back to [P] for re-review)
- **The index is derived data**: the checkup scan validates at id level and regenerates from detail files on inconsistency (self-healing)
- chunk GC: only delete files that are in the manifest and not within the most recent 3 batches (exact name matching, glob wildcard deletion forbidden); orphans are reported only, not deleted

### 5.3 Knowledge Base Transactions and Concurrency

- `.kb.lock`: reuses the file_lock mechanism (30s timeout, auto-released on process exit); identity (pid+operation) is self-reported while holding the lock
- **Write transaction**: acquire lock → read current state → in-memory merge (dedup→conflict determination→state transition) → per-file temporary copy → validation (parsable / index consistency / meta legality) → atomic replace (detail files → pending.md → **index last**) → release lock
- Crash safety: worst case = index lag (derived data, self-healed by checkup); `.<name>.kb.bak` rolling rollback point
- Read-only needs no lock (atomic replace guarantees no tearing)

### 5.4 Command Protocol and Proactive Review

| Command | Purpose | Status |
|------|------|------|
| `/evolution` | Incremental sync + checkup scan + review-queue prompt | modified |
| `/evolution-init` | Initialization (all output lands in pending) | modified |
| `/kb-review` | Batch review: pending + legacy [D] + [C] arbitration | **new** |
| `/kb-status` | Knowledge base health report | **new** |
| `/kb-archive` | Manual archive | **new** |
| `/kb-restore <id>` | Restore from archive (back to [P] for re-review) | **new** |

**Review UX (minimum cost)**:
- One-screen preview (one entry per line: id/status/source/confidence/summary; for sensitive, show only the id)
- Batch commands: `all v` / `v 1-5` / `d 2` / `x 4` / `c 3 choose 1`
- Default action recommended by evidence (tool_output → v, conversation_inference → d)
- **Zero-review path**: do nothing → 30-day stale → auto-archive (no forcing, no bloat)
- The /evolution summary appends a prompt line at the end and never auto-executes review

### 5.5 Privacy and Security

**Three lines of defense**:

```
Defense 1 (export layer): chunk sensitive-pattern scan (N-12: attributed to the export script evolution-export.py, not the sync step); hits are reported only (file + line number)
Defense 2 (write layer): candidate contains a sensitive pattern → not written to detail; blocked entry lands in pending only in redacted form (pattern type + source location), with zero raw-value persistence
                  (ways out: redacted resubmission <REDACTED:api_key> / rejection)
Defense 3 (awareness layer): README privacy section + .gitignore excludes .evolution/
```

Sensitive pattern list: github_token / anthropic_api_key / openai_api_key / aws_access_key / slack_token / private_key / generic_secret_assignment / local_path (**disabled by default**, N-10) / contact_info (disabled by default).

---

## 6. Interface Points Between the Two Layers

| Interface | Mechanism |
|------|------|
| Batch manifest ↔ chunk GC | Engine-layer sync-state records batches → knowledge-layer checkup precisely cleans up per the manifest |
| commit trust boundary ↔ [P] backstop | The script does not verify ingestion → new entries are always [P] pending manual review |
| Checkup scan ↔ sync | Executed incidentally at step 0.5 (read-only + status update, <2s); archive actions execute on the next write under lock |
| Full re-export ↔ dedup | Re-export produces duplicate candidates → dedup merges them (duplicate ≠ conflict; semantic contradictions enter arbitration) |

---

## 7. Migration Path

### 7.1 State File (3.2.1 / 3.4.0 → 3.5.0)

> Measured: the live `version` label is "3.2.1" but the structure is already v3.4.0 —— both labels must be handled by the same function.

```
exported_lines = old processed_lines
committed_lines = 0        ← conservative: the old cursor had already advanced before analysis, so it is not trustworthy
Migration batch: references the legacy chunk-*.md (or failed(migration-unverified) triggers regeneration)
```

- **Default**: after migration, the next incremental run re-analyzes the full history once (~$4; after KB dedup there are few additions)——safe and bounded
- **Escape valve** `migration.trust_committed: true`: skips re-analysis when the knowledge base is confirmed complete; the migration report is marked `migration_mode: trusted`
  - ⚠️ **Not implemented (verified in v4.1.2)**: the code has no entry point that produces a `mode="migration"` batch, and `config.yaml` has no `migration:` config section; this switch is only a design promise and has not been landed
- Degraded migration (completely different structure) → `state-version-unknown` + backup followed by `--mode full` guidance

### 7.2 Knowledge Base (Existing Entries)

| Existing | Handling |
|------|------|
| Already `[V]` | Mechanically fill in metadata (id assignment, source=legacy, evidence determined per file), **status not downgraded** |
| Already `[D]` | Not processed automatically; enters the `/kb-review` batch review queue (legacy=1) |
| Unmarked entries | Moved into pending.md and marked [P] |

Executed by `kb-manager.py migrate` (under lock), producing a before/after migration comparison report.

---

## 8. Consolidated Edge-Case List (merged and deduplicated, 35 selected)

| # | Scenario | Handling |
|---|------|------|
| 1 | Sub agent interrupted after export, before commit | Batch exported; next run `analyze_pending`, no re-export |
| 2 | Batch chunk deleted by cleanup | Regenerated from line_ranges; old batch failed(chunks-missing) |
| 2a | Batch status is analyzing after resume | Protocol step 2 handles all batches in exported/analyzing; analyzing is not filtered out (N-2) |
| 2b | Migration batch / failed(migration-unverified) batch recovery | regenerate special-cases mode="migration": full-file re-export from line 1 (line_ranges: {f: [1, exported_lines]}); failed (non-retry-exhausted) is not counted as in-flight and does not block the file; the next round enters a dedicated regeneration loop, old batch marked superseded (N-3) |
| 3 | Duplicate commit call | Idempotent success, returns the existing receipt |
| 3a | Sub agent analysis repeatedly fails | `--mode analyze-failed` increments the counter; on reaching the limit `failed(analysis-exhausted)`; `--mode commit --force` forces confirmation after a prominent warning (N-4/F-3) |
| 4 | Regeneration repeatedly fails (≥3 times) | failed(retry-exhausted) + partial + WARN, prompting manual full re-export |
| 5 | JSONL rotated/truncated by Claude Code | Integrity check auto-detects → full re-export of that file + WARN |
| 6 | State file corrupted but .bak exists | Restore from .bak + WARN + rename and retain the corrupted file |
| 7 | State file corrupted and no .bak | **Explicit failure** state-corrupt, never a silent empty state |
| 8 | save killed with kill -9 mid-way | tmp residue left; original file intact; cleanup clears it |
| 9 | null/[]/123 lines | Skipped + ParseStats counting, no crash |
| 10 | Huge turn (>200K) | Unconditional flush + sub_turns as independent chunks, time order preserved |
| 11 | Turn crossing sessions | Session-aware grouping, no turn stitching |
| 12 | Entry with unknown timestamp | Placed in the "unknown bucket" at the batch tail, deterministic tie-breaker |
| 13 | Single file >200MB | Accepted (the generator streams); external sort column is an extension item |
| 14 | [P]/[D] attempts to displace [V] | Intercepted by both the rule red line and transaction validation |
| 15 | User does not review for a long time | 30-day stale → archive, no deletion, no bloat |
| 16 | [C] arbitration where neither side is chosen | Stays [C] into the next round |
| 17 | Sensitive scan hit | Intercept + redacted preview; the blocked entry persists only in redacted form (pattern type + source location), with zero raw-value persistence |
| 18 | Sensitive scan false positive | Redaction/rejection provided; hit log visible |
| 19 | Two concurrent writers | .kb.lock serializes; 30s timeout reports "knowledge base busy (pid/operation)" |
| 20 | Writer process crashes while holding the lock | Lock released with the handle; .tmp residue older than 24h cleaned by the checkup |
| 21 | Partial failure of multi-file replace in a transaction | Index written last → worst case = index lag, self-healed by checkup |
| 22 | Index manually corrupted | Checkup id-level validation → regeneration (annotated "self-healed") |
| 23 | /kb-restore conflicts with existing | Automatically marked [C] into arbitration after restore |
| 24 | Evidence expired after restore from archive | Always back to [P] for re-review |
| 25 | User review command contains an illegal id | Per-item fault tolerance: illegal items error, legal items take effect |
| 26 | pending.md missing | Treated as an empty quarantine area, normally initialized |
| 27 | Windows file locked by an editor | Replace fails with an error and gives the .bak path; never silently discarded |
| 28 | Lock file manually deleted | Harmless (the lock is on the handle); the next locker recreates it |
| 29 | Claude Code keeps appending during export | Slightly inconsistent snapshot → self-healed by the next round's integrity check |
| 30 | Coarse mtime granularity (FAT/network drive) | The fast path is only an optimization; hash backstops it |
| 31 | Batch time range missing | time_range: null, sort tie-breaker backstops it |
| 32 | Knowledge base briefly "shrinks" after migration | Expected behavior; a one-time catch-up review via /kb-review restores it |
| 33 | Existing [V] entries contradict each other | Marked [C] into arbitration, no automatic choice |
| 34 | Same fact extracted repeatedly within pending | dedup merges them (keeps the earlier created, appends source) |
| 35 | Duplicate vs conflict hard to judge | Treated as a conflict; prefer arbitration over merging |

---

## 9. Acceptance Criteria (merged, module level)

| Layer | Key acceptance items |
|----|-----------|
| Engine-batch | Interruption recovery (committed unchanged + pending prompt); failure regeneration (byte-identical chunks); idempotent commit; uncommitted blocking semantics; resume does not skip analysis (N-2); failed batches do not block and are regenerated (N-3); analyze-failed counting and force confirmation (N-4) |
| Engine-integrity | Truncation detection triggers full re-export; replacement detection; fast path does not compute hash; self-healing (rewriting the source file triggers it next round) |
| Engine-atomic | After 200 random kill -9 events the state file is parsable or .bak-recoverable; explicit failure with zero modification when there is no backup and the file is corrupted |
| Engine-parse | Bad lines do not crash + ParseStats correct; peak memory independent of file count (3×15MB vs 1×15MB differ by <2×); global time-order assertion; huge turns monotonic |
| Engine-protocol | End-to-end (incremental → read batch → commit → status) exit-code and JSON assertions; four elements of error messages |
| Knowledge-status | New entries 100% first land in pending; normal reads touch pending 0 times; [P]/[D] cannot displace [V]; all entries have legal meta |
| Knowledge-lifecycle | 31-day [P] archived; 180-day [D] archived; index 501→<300 lines consistent; chunk GC correct; zero body-text deletion throughout |
| Knowledge-transaction | No lost updates with two writers; inconsistent index self-healed; lock-timeout error without corruption; crash recoverable |
| Knowledge-commands | Batch review completes in a single transaction; /kb-status consistent with checkup; restore goes back to [P] into the queue; still healthy after 30 days of zero operations |
| Knowledge-security | Key/password/path candidates all intercepted; blocked persisted only in redacted form with zero raw-value persistence; redacted resubmission works; .evolution excluded by git; README bilingual docs consistent |

---

## 10. Implementation Plan

### 10.1 Phases and Milestones

| Milestone | Phase | Content | Depends on | Effort |
|--------|------|------|------|--------|
| **M1 Engine reliability** | E1 | Test scaffolding (JSONL/state fixtures, bad-line/truncation/interruption simulation) | — | 0.5 person-day |
| | E2 | Module C atomic write + recovery chain | E1 | 0.5 person-day |
| | E3 | Module D-1 parse defenses + ParseStats | — | 0.5 person-day |
| | E4 | Module A dual cursors + batch + commit + migration | E2 | 1.5~2 person-days |
| | E5 | Module B integrity check + re-export interaction | E4 | 1 person-day |
| | E6 | Modules D-2~D-5 streaming + sorting + token factor | E3 | 1.5~2 person-days |
| | E7 | Module E protocol + sync.md/SKILL.md updates | E4/E5 | 0.5 person-day |
| **M2 Knowledge defense** | K1 | kb-manager.py skeleton + existing-data migration | — | 2-3h |
| | K2 | Status model (config extension + rule-file rewrite + pending.md) | K1 | 3-4h |
| | K3 | .kb.lock transaction protocol | K2 | 4-5h |
| **M3 Commands and security** | K4 | Lifecycle (checkup/archive/index compression/chunk GC) | K3 | 4-5h |
| | K5 | /kb-review and 3 other commands + sync/init/SKILL integration | K2 | 4-5h |
| | K6 | Sensitive scan gate + .gitignore + README privacy section | K2 | 2-3h |
| **M4 Release** | R1 | Full acceptance (§9 item by item) + live-data regression | all | 1 person-day + 2-3h |

**Total: engine layer 6~8 person-days + knowledge layer 21~28 hours ≈ 9~12 person-days.**

### 10.2 Suggested Landing Order

```
E1 → E2 → E3 → E4 → E5 → E6 → E7 ─┐
                                   ├→ R1 (ship the v4.0.0 engine part first, then the knowledge part)
K1 → K2 → K3 → K4 → K5 → K6 ──────┘
```

M1 first (data integrity, highest risk) → then M2/M3 (knowledge defense). Each phase is independently acceptable and independently committable.

---

## 11. List of Affected Files (21)

| File | Action |
|------|------|
| `.claude/skills/evolution/evolution-export.py` | modify (dual cursors/batch/validation/atomic write/streaming/protocol) |
| `.claude/skills/evolution/kb-manager.py` | **new** (migrate/validate/lock/commit/scan/compress/restore) |
| `.claude/skills/evolution/config.yaml` | modify (sync_engine + lifecycle + lock + sensitive_patterns + status-marker extension) |
| `.claude/skills/evolution/rules/write.md` | rewrite |
| `.claude/skills/evolution/rules/read.md` | rewrite |
| `.claude/skills/evolution/rules/dedup.md` | rewrite |
| `.claude/skills/evolution/commands/sync.md` | modify (step 0.5 checkup + commit protocol) |
| `.claude/skills/evolution/commands/init.md` | modify (output lands in pending) |
| `.claude/skills/evolution/commands/kb-review.md` | **new** |
| `.claude/skills/evolution/commands/kb-status.md` | **new** |
| `.claude/skills/evolution/commands/kb-archive.md` | **new** |
| `.claude/skills/evolution/commands/kb-restore.md` | **new** |
| `.claude/skills/evolution/SKILL.md` | modify (command table + knowledge base description) |
| `evolution/knowledge-base/pending.md` | **new** |
| `evolution/knowledge-base/archive/` | **new** |
| `evolution/knowledge-base/` 8 detail files | migrate (meta completion + [C] opportunities) |
| `.gitignore` | modify (`.evolution/`, `*.kb.bak`, `*.kb.tmp-*`) |
| `README.md` / `README.zh-CN.md` | modify (privacy and security section + honest description of the export mechanism) |
| `docsV3/INSTALLATION_GUIDE.md` | **modify (M0: #26 uninstall command `rm -rf evolution` fix + #27 migration guide contradiction)** |
| `docsV3/EVOLUTION_RULES_AND_LOGIC_V3.md` | modify (#28 "no omissions" false promise + #30 contradictory wording fix) |
| `docsV3/EXPORT_AND_ANALYSIS_DESIGN.md` | modify (#32 chunk-count contradiction + state management/error matrix/flow sections updated with V4) |
| `docsV3/PROJECT_BACKGROUND.md` | modify (#30 contradictory wording fix) |
| `docsV3/VERSION_HISTORY.md` | modify (v4.0.0 record) |
| `CLAUDE.md` | modify (version number and description) |
| `evolution-manual/` (if present) | **delete or archive (M0: #22 dual knowledge-base trees)** |

---

## 12. Risks and Open Questions (require user decision)

> **v2 update**: The independent review has confirmed the core approach is correct; all decision points below have been decided by the user (full implementation, no cost reduction), leaving only technical open items.

| # | Decision point | Status |
|---|--------|------|
| 1 | **Migration cost**: after upgrade, re-analyze the full history once by default (~$4) | ✅ Decided: conservative re-analysis by default; the `trust_committed` escape valve is retained |
| 2 | **[D] quarantine review burden**: existing [D] frozen entries need a batch catch-up review | ✅ Decided: accept, batch catch-up via /kb-review |
| 3 | **contact_info sensitive pattern**: high false-positive rate | ✅ Decided: disabled by default, enable on demand; all other patterns retained |
| 4 | **Initial ship scope** | ✅ Decided: M0 missed-fix package first → M1 engine → M2/M3 knowledge defense → M4 release (§14.5) |
| 5 | **.openclaw / evolution-github sync**: when to sync the design doc | ✅ Decided: sync to both places after the v2.1 revision (three docs in docsV4/) |
| 6 | **Audit missed-fix package** (#26/#22/#4/#21/#27/#23/#24/#25) | ✅ Included (§14.3 🔴 items), scheduled as M0 upfront |
| 7 | **The "cut the luxuries" suggested by the independent review** (k-way merge, receipt_hash, archive system, etc.) | ✅ Rejected: **full implementation** (user instruction: cost is not a concern, accuracy is key) |

---

## 13. Appendix

### 13.1 Design Draft Index

| Document | Content | Lines |
|------|------|------|
| `design-v4-engine.md` | Full engine-layer details (modules A-E, migration, acceptance, risks; v2.1 includes N-2/N-3/N-4/N-11/N-12 revisions) | ~950 |
| `design-v4-knowledge.md` | Full knowledge-layer details (modules A-E, full rule drafts, timing, 20 edge cases; v2 includes N-6/N-7/N-10/N-13/N-14 systematic revisions) | ~800 |

### 13.2 Adversarial Audit Report

- [`../docsV3/ADVERSARIAL_AUDIT_v3.9.0.md`](../docsV3/ADVERSARIAL_AUDIT_v3.9.0.md) — full text of the 39 confirmed findings (including failure scenarios and recommended solutions)

---

**End of document (master outline)**

---

## 14. Independent Review and Revision (v2, 2026-08-16)

### 14.1 Independent Review Conclusion

The independent review checked the code line by line (C1/C2/C3/D1/D4 all matched the audit description) and measured the live data (16 knowledge entries, 1×15MB JSONL, sync-state version "3.2.1" drift confirmed). Conclusions:

1. **The core architecture is correct and necessary**: dual cursors/integrity check/atomic write are not nice-to-haves, they address real data-safety vulnerabilities
2. **The plan missed the cheapest fixes**: the 39 items covered only ~26, missing 1 CRITICAL + 5 HIGH
3. **About 1/3 of the modules were judged to be "paying for a scale that does not exist"** (k-way merge, archive system, receipt_hash, etc.)
4. **Found 3 defects in the plan itself**: migration-batch commit semantics contradiction, missing rollback path, no liveness on analysis failure

> v2.1 addendum (second-round review): the claim in the F-2 rollback manual that "the old script returns state-version-newer" did not hold up under measurement——v3.9.0's `load_sync_state` does not check the version field, so the rollback manual was rewritten per the real behavior (see F-2).

### 14.2 Decision: Full Implementation (user-decided)

> **User instruction: cost is not a concern, accuracy is the key.**

- ❌ **Rejected the independent review's cost-reduction suggestions**: k-way merge, receipt_hash, analyzing status, archive/restore system, last_used lifecycle, index compression, the 9 sensitive patterns, keep_committed_batches=20 —— **all retained for full implementation**
- ✅ **Accepted the independent review's accuracy fixes**: coverage matrix (§14.3), plan-defect fixes (§14.4), inclusion of missed findings (§14.3 🔴 items)
- ✅ **Accepted the independent review's architectural improvements**: kb-manager.py as the sole write entry point, sensitive-gate enforced by script, knowledge-base path anchoring via `__file__`

### 14.3 Audit Coverage Matrix (39 items → module → status)

> 🔴 = missed in v1, included in v2. Every item has a clear disposition; no dangling findings.

| # | Finding | Severity | Disposition module | Status |
|---|------|--------|---------|------|
| 1 | Sync cursor commits before knowledge extraction | HIGH | Engine A dual cursors+batch | ✅ |
| 2 | Knowledge base writes lack cross-sub-agent transactions | MEDIUM | Knowledge C .kb.lock | ✅ |
| 3 | Draft knowledge being read forms a self-reinforcing loop | HIGH | Knowledge A [P] quarantine | ✅ |
| 4 | Content-summary strategy silently drops key evidence | HIGH | 🔴 **New: chunk-header truncation declaration + entry meta `truncated=1` + source line number traceability** | 🔴 |
| 5 | Multi-session aggregation does not guarantee time order | MEDIUM | Engine D5 global sort | ✅ |
| 6 | [V] verification semantics too broad | MEDIUM | Knowledge A evidence binding | ✅ |
| 7 | Sub agent has no completion protocol | MEDIUM | Engine E receipt protocol | ✅ |
| 8 | Incremental cursor has no integrity check | CRITICAL | Engine B sha256 | ✅ |
| 9 | save_sync_state is not an atomic write | HIGH | Engine C atomic write | ✅ |
| 10 | Error-shaped lines crash with AttributeError | HIGH | Engine D1 parse defenses | ✅ |
| 11 | Huge turn causes chunk time disorder | MEDIUM | Engine D3 force flush | ✅ |
| 12 | token estimate too low | MEDIUM | Engine D4 safety factor | ✅ |
| 13 | Full export OOM | MEDIUM | Engine D2 k-way streaming | ✅ |
| 14 | Cursor commits before knowledge consumption | HIGH | Engine A | ✅ |
| 15 | File rewrite/truncation bypasses cursor validation | MEDIUM | Engine B | ✅ |
| 16 | State loss bypasses init protection | MEDIUM | 🔴 **New: init pre-check detects knowledge base integrity (including the reverse case where state is intact but the KB is emptied)** | 🔴 |
| 17 | Export lock does not cover knowledge base transactions | MEDIUM | Knowledge C (since V4, KB writes go through the sole write entry point kb-manager.py; the lock is inside the script) | ✅ |
| 18 | Large-scale input memory explosion | MEDIUM | Engine D2 | ✅ |
| 19 | Mutable chunk paths cause batch cross-contamination | MEDIUM | Engine A manifest exact paths | ✅ |
| 20 | Incremental cursor commits before extraction | CRITICAL | Engine A | ✅ |
| 21 | init pre-check reads the wrong signal source | HIGH | 🔴 **New: changed to detect the knowledge base body + last_full_sync dual signal** | 🔴 |
| 22 | Dual knowledge-base trees, index self-referencing old paths | HIGH | 🔴 **New: migration M0 deletes the old evolution-manual/ tree + fixes self-referencing paths** | 🔴 |
| 23 | Phantom commands such as /kb-sync, misplaced command names | MEDIUM | 🔴 **New: command unification (M0 executed: SKILL.md and sync.md removed the three phantom commands /kb-sync /growth-sync /alignment-sync, keeping only /evolution and /evolution-init; V4's /kb-review and other kb-* commands are added separately per the K5 plan)** | 🔴 |
| 24 | Relative paths depend on the sub agent cwd | MEDIUM | 🔴 **New: path anchoring to the script `__file__` (F-6: project_root = parents[3]; M0 has annotated init.md/sync.md, code change implemented in M1 E4)** | 🔴 |
| 25 | Export includes the current session itself | MEDIUM | 🔴 **New: export excludes the currently running session. Explicit semantics (finalized in M0): use the export start time as the boundary and exclude tail entries after the sync trigger time——only process entries fully persisted before that time; tail entries newly produced by the current session after the trigger are left for the next incremental round, without content-based filtering of meta records (to avoid harming normal conversation). Code lands in M1 E4** | 🔴 |
| 26 | Uninstall command `rm -rf evolution` | CRITICAL | 🔴 **New: M0 doc fix (backup + precise deletion + confirmation)** | 🔴 |
| 27 | V2→V3 migration doc contradiction | HIGH | 🔴 **New: M0 doc unification** | 🔴 |
| 28 | "Export all conversations without omission" false promise | HIGH | 🔴 **New: honest doc wording (declares the truncation strategy and exclusion scope)** | 🔴 |
| 29 | sync-state version frozen and not migrated | MEDIUM | Engine A.4 bump + MIGRATIONS | ✅ |
| 30 | "Silent operation/humans unaware" contradicts manual trigger | MEDIUM | 🔴 **New: doc correction (M0 executed: PROJECT_BACKGROUND.md §4 clarifies it is a manually triggered system and removes the silent-operation/humans-unaware/no-intervention wording)** | 🔴 |
| 31 | Incremental truncation detection not landed | MEDIUM | Engine B | ✅ |
| 32 | chunk count contradicts token estimate | LOW | 🔴 **New: doc correction (M0 executed: EXPORT_AND_ANALYSIS_DESIGN.md unified the "estimated/actual" dual accounting and fixed the contradictory ~136K avg vs 3 chars/token figures)** | 🔴 |
| 33 | Log rewrite causes missed incremental reads | MEDIUM | Engine B sha256 | ✅ |
| 34 | Old chunk residue unbounded bloat | HIGH | Engine batch pruning + Knowledge B chunk GC (manifest schema aligned with Engine A.2) | ✅ |
| 35 | Unverified new knowledge displaces verified facts | HIGH | Knowledge A conflict red line | ✅ |
| 36 | Sensitive conversations persisted before review | HIGH | Knowledge E three lines of defense (blocked persisted only in redacted form, N-6) | ✅ |
| 37 | Knowledge base writes have no concurrency protection | MEDIUM | Knowledge C | ✅ |
| 38 | Knowledge base has no validity period | MEDIUM | Knowledge B lifecycle | ✅ |
| 39 | Knowledge base left unmaintained after removing the skill | MEDIUM | 🔴 **New: README documentation (M0 executed: README.md / README.zh-CN.md added a "Knowledge Base Maintenance" section)** | 🔴 |

**Coverage statistics**: 39/39 all have a disposition (v1 covered 26; v2 included 13 missed items: 🔴 numbers 4/16/21/22/23/24/25/26/27/28/30/32/39, including 1 CRITICAL + 5 HIGH——#4/#21/#22/#27/#28).

### 14.4 Plan Defect Fixes (found by independent review, v2 revision)

**F-1: Migration-batch commit semantics gap (internal design contradiction)**

Problem: a migration batch has `line_ranges: null`, but the commit flow iterates `line_ranges` to advance committed_lines——null cannot advance.
Revision: define special commit semantics for migration batches——when `--mode commit` detects a batch with `mode="migration"`, it directly sets `committed_lines = exported_lines` (no rollback, confirm as-is), and the receipt notes `migration_commit: true`.

**F-2: Missing rollback path (v2 revision——rewritten per measured behavior)**

Problem: the initial draft claimed "the old script returns state-version-newer for a version=3.5.0 state (read-only available, modification rejected)". **Measurement overturned that claim**: v3.9.0's `load_sync_state` does not check the version field at all; that protection exists only in V4's own new loader. The real behavior is: the old script cannot find the `processed_lines` field → falls back to 0 on missing → **full re-export + overwrite of the state file**.

Revised rollback manual (to be written into INSTALLATION_GUIDE or a standalone document at implementation time):

- V4 → V3.9 rollback steps:
  1. Back up and **remove** `.evolution/chunks/sync-state.json` (archive it along with `.bak`/`.tmp`/batch chunks; do not leave them in place)——otherwise the old script interprets the V4 state as "cursor 0", triggering a full re-export and overwriting the state file;
  2. Replace the skill files with the v3.9 version (evolution-export.py / SKILL.md / commands/ / rules/);
  3. Accept one full re-export (`--mode full` or auto-triggered by the next sync): old history is re-exported and re-analyzed; KB dedup backstops it, so already-ingested knowledge will not pile up as duplicates;
  4. The knowledge base kb-meta lines and pending.md are ignored by V3 rules (unknown markers are not read; [V]/[D] remain usable as usual); blocked redacted entries are ordinary [P] text to V3, with no side effects.
- Mandatory backup before migration: `sync-state.json.bak` + knowledge base `*.kb.bak` + migration dry-run validation.
- Explicit cost: rollback = losing dual-cursor protection + one full analysis cost (~$4); it is a non-zero-cost operation and the manual must state this.

**F-3: No retry limit on analysis failure (liveness gap)**

Problem: retry_count only increments on chunk regeneration; "chunk intact but the sub agent repeatedly fails to analyze" blocks indefinitely (the invariants guarantee no data loss but not forward progress).
Revision: add an **analysis-failure counter** at the protocol layer——the batch gains an `analysis_failures` field; when the sub agent starts analysis, `--mode start` sets analyzing; if the main agent's summary lacks a receipt for 2 consecutive rounds → WARN prominently in the summary "batch X has been unconfirmed for consecutive rounds, check whether the sub agent keeps failing"; when `analysis_failures >= 3` → the batch is marked `failed(analysis-exhausted)`, prompting manual intervention (an explicit `--mode commit --force` can force confirmation or regenerate).
**CLI landing point (N-4)**: add `--mode analyze-failed --batch-id <id>` (increments `analysis_failures`, sets `failed(analysis-exhausted)` at the limit); `--mode commit --force` prints a prominent warning "forced confirmation will permanently skip the unanalyzed content of this batch", and the receipt records `forced: true`. See design-v4-engine.md E.2.

**F-4: Sensitive gate ownership unclear**

Problem: write.md has the LLM "scan by pattern" when writing pending.md——LLM self-checking regex is unreliable.
Revision: **sensitive scanning is a mandatory step inside the kb-manager.py transaction**; the LLM only submits candidate entry text, and the script lands it in pending (blocked=secret) only on a scan hit; the rule files explicitly state "scanning is in the script, not in the rules".

**F-5: kb-manager.py as the sole write entry point (independent review architectural improvement, adopted)**

Revision: the sub agent never directly edits knowledge base markdown——it only submits structured operations through `kb-manager.py add/promote/deprecate/resolve/restore/touch` (JSON stdin or `--payload <file>`); kb-manager executes under lock: sensitive scan → dedup → conflict determination → state transition → validation → atomic replace. At the same time it eliminates: the risk of the LLM corrupting markdown, the transaction-validation burden, sensitive-gate ambiguity, and most of the complexity of the "read current state → merge" rules. The knowledge base file header declares "this file is managed by kb-manager.py, do not edit by hand". The write.md draft and timing 1/2 of the knowledge-layer design document (design-v4-knowledge.md v2) have been rewritten per this decision.

**F-6: Knowledge base path anchoring (linked with #24; v2 revision——corrects the concatenation formula)**

Problem: the initial-draft formula `Path(__file__).parent / location` was wrong——`__file__` = `.claude/skills/evolution/kb-manager.py`, `parent` = `.claude/skills/evolution/`, so concatenating `evolution/knowledge-base/` yields the nonexistent `.claude/skills/evolution/evolution/knowledge-base/`.
Revision: anchor to the **project root**, then append location——

```python
project_root = Path(__file__).resolve().parents[3]   # kb-manager.py → evolution → skills → .claude → project root
kb_dir = project_root / location                     # location default "evolution/knowledge-base"
assert (project_root / "CLAUDE.md").exists() or (project_root / ".git").exists(), \
    f"path anchoring failed: {project_root} is not the project root"
```

(`parents[3]`: `parents[0]`=skills/evolution, `[1]`=skills, `[2]`=.claude, `[3]`=project root.) No longer depends on the caller's cwd; the sub agent protocol stipulates using absolute paths emitted by the script.

**F-7: Reliable last_used maintenance (the independent review pointed out the LLM is unreliable)**

Revision: keep the last_used field, but have **kb-manager.py record it automatically on read operations** (`--mode touch --id KB-0xx`, or batch-update when reading summaries), without relying on the LLM report layer's self-discipline. The knowledge-layer A.2 field table has been updated in sync.

**F-8: Truncation traceability (#4 landing)**

Revision: the chunk header declares "this chunk's content is truncated by policy (tool_result keeps the first 500 chars + error tail)"; entry meta supports `truncated=1` + `source_line` (source JSONL line number); /kb-review or a dedicated command can locate the source line to fetch the original text again.

**F-9 (new in v2.1): N-13 kb-meta escaping rules**

The kb-meta line separates fields with `;` and `=`; if a free-text field (`scope` and any free-text fields added in the future) contains a reserved character, it must be written encoded as a JSON string (inner JSON escaping inside `scope="…"`), and the parser decodes it as a JSON string. See design-v4-knowledge.md A.2.

**F-10 (new in v2.1): N-14 index limit unified**

The kb-index line limit is unified to **500** (`lifecycle.index_max_lines: 500`); SKILL.md, the read.md draft, and B.4 are consistent in all three places.

### 14.5 Revised Implementation Plan (v2)

| Milestone | Content | Effort |
|--------|------|--------|
| **M0 missed-fix package** (upfront) | #26 rm -rf doc, #27 migration guide, #22 delete old tree and fix self-reference, #21 init dual signal, #23 command unification (✅ executed: removed three phantom commands), #24 path anchoring (F-6 corrected formula; documented, code M1 E4), #25 current-session filtering (N-9 semantics finalized and written into the command doc), #28/#30/#32 doc honesty (✅ #30/#32 executed), #39 README note (✅ executed) | 1 person-day |
| M1 engine | E1 test scaffolding → E2 atomic write → E3 parse defenses → E4 dual cursors+batch+commit (including F-1 migration commit + N-3 failed recovery loop) → E5 integrity check → E6 streaming+sorting+token factor (including N-11 buffered persistence) → E7 protocol (including F-3/N-4 analyze-failed and commit --force, N-2 resume protocol) | 6~8 person-days |
| M2 knowledge defense | K1 kb-manager skeleton + existing-data migration (including F-6 path anchoring) → K2 status model + rule rewrite + sole write entry point (F-5, write.md/timing 1 already aligned with the v2 revision) → K3 .kb.lock transaction | 21~28h |
| M3 commands and security | K4 lifecycle (including F-7 last_used script maintenance) → K5 four commands + integration (including #23 removing three deprecated commands) → K6 sensitive gate (F-4 script-enforced; blocked persisted in redacted form N-6) + privacy docs | 21~28h |
| M4 release | Full acceptance (§9 + §14.3 coverage matrix item-by-item confirmation) + live-data regression + rollback manual (F-2 measured-behavior version) | 1.5 person-days |

**Total effort: about 11~14 person-days** (full implementation, no reduction).

**Original independent-review text**: see the output of task a1b92a7eb6d946095 (archived in the adversarial audit session record).
