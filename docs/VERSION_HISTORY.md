# Evolution Version History

🌐 **Language / 语言**: [English](VERSION_HISTORY.md) | [中文](VERSION_HISTORY.zh-CN.md)

> **Current version**: 4.1.6
> **Release date**: 2026-09-11

---

## Version Change Overview

| Version | Date | Major changes |
|---------|------|---------------|
| v4.1.6 | 2026-09-11 | Fixed release: privacy generalization, version number unification, design document notes, outdated banners, installation guide completion, release rule self-check |
| v4.1.5 | 2026-09-10 | Fixed release: sha256 regression test rewritten (locking the incremental sha256 refresh path), installation guide Python version, removal of the three template sections, archived dead links, .gitignore archive ruling |
| v4.1.4 | 2026-09-10 | Review wrap-up: release rules, sha256 regression test, V2 archive KB privacy cleanup gap fix, version number unification, export script version header clarification |
| v4.1.3 | 2026-09-10 | Fixed release: five-perspective review sha256 refresh (incremental false positive file-replaced), root directory cleanup, English README, KB privacy cleanup, LICENSE |
| v4.1.2 | 2026-09-10 | Fixed release: 10 adversarial review fixes (cleanup protects state file, unified lock path, read-only status, exit code, README, rollback banner) |
| v4.1.1 | 2026-09-10 | Fixed release: path anchoring, version labeling, kb-manager archiving, documentation cleanup |
| v4.1.0 | 2026-09-10 | Fixed release: kept engine-layer fixes, rolled back knowledge-layer over-engineering, restored knowledge base usability |
| v4.0.0 | 2026-08-24 | MAJOR: dual cursors + batch + commit, integrity check, atomic write, [P] isolation, transaction lock, lifecycle, sensitive gate |
| v3.9.0 | 2026-08-01 | Added `/evolution-init` pre-check to prevent accidental reset |
| v3.8.0 | 2026-08-01 | Fixed three bugs: enforced script + disabled manual glob, fixed find_jsonl_file returning all files, added validation mechanism |
| v3.7.0 | 2026-08-01 | Fixed `/evolution-init` command, call `evolution-export.py` to export full history, prevent sampling |
| v3.6.0 | 2026-08-01 | Split `/evolution init` into standalone command `/evolution-init`, distinguish initialization from incremental sync |
| v3.5.0 | 2026-07-31 | Refactored based on writing-great-skills rules, SKILL.md reduced from 96 lines to 37 lines |
| v3.4.0 | 2026-07-31 | Modular refactoring, SKILL.md split, config.yaml unified configuration |
| v3.3.0 | 2026-07-30 | Fixed JSON serialization crash, incremental unit drift, Windows encoding, token estimation bias (CJK coefficient 1.5→1.0), cleanup safety, file handle leaks, and other issues |
| v3.2.0-draft | 2026-07-29 | Initial design based on 200K window assumption (superseded by v3.2.1) |
| v3.2.1 | 2026-07-30 | Updated pagination parameter: 80K → 150K (based on attention research) |
| v3.1.0 | 2026-07-29 | Added initialization command, conversation export mechanism, sub agent execution design |
| v3.0.0 | 2026-07-28 | Simplified system, removed auto version, added write review mechanism |
| v2.1.0 | 2026-07-28 | Write review mechanism (status markers) |
| v2.0.0 | 2026-07-28 | Skill system migration |
| v1.0.0 | 2026-07-21 | Initial release |

---

## v4.1.6 (2026-09-11)

### Fixed Release

Based on an independent review's 8-item fix list, completed issues left over from multiple rounds of review:

**Privacy generalization**:
- docsV4/design-v4-engine.md: all example JSON synthesized (project_hash/mtime/size/lines/timestamps)
- evolution-export.py:248: docstring example path generalized to a neutral example `C:\Projects\demo -> C--Projects-demo`

**Version number unification**:
- All file version numbers uniformly upgraded to 4.1.6 (CLAUDE.md/SKILL.md/config/commands/kb-index/evolution-export.py)
- rules/*.md upgraded from 4.1.4 to 4.1.6 (fixing version drift)
- INSTALLATION_GUIDE header and footer upgraded from 3.9.0 to 4.1.6

**Design document notes**:
- design-v4-engine.md: CLEANUP_PATTERNS removes sync-state.json (V4.1.2 change note)
- design-v4-engine.md: exit code protocol simplified to 0/1 (V4.1.2 change note)

**Outdated document handling**:
- EVOLUTION_RULES_AND_LOGIC_V3.md: added outdated banner (V3 single-file structure; V4 has changed to modular)

**Installation guide completion**:
- INSTALLATION_GUIDE §3.1/§4: verification checklist supplemented with tests/ + .claude/commands/

**Release rule reinforcement**:
- CLAUDE.md: release rules add grep self-check (consistency verification of the latest version row across the three tables)

### Modified Files

- `CLAUDE.md` - version number 4.1.6 + release rule grep self-check
- `.claude/skills/evolution/SKILL.md` - version number 4.1.6
- `.claude/skills/evolution/config.yaml` - version number 4.1.6
- `.claude/skills/evolution/commands/init.md` - version number 4.1.6
- `.claude/skills/evolution/commands/sync.md` - version number 4.1.6
- `.claude/skills/evolution/evolution-export.py` - version number 4.1.6 + docstring generalization
- `.claude/skills/evolution/rules/write.md` - version number 4.1.6
- `.claude/skills/evolution/rules/read.md` - version number 4.1.6
- `.claude/skills/evolution/rules/dedup.md` - version number 4.1.6
- `evolution/knowledge-base/kb-index.md` - version number 4.1.6
- `docsV3/VERSION_HISTORY.md` - v4.1.6 section + statistics table row
- `docsV3/INSTALLATION_GUIDE.md` - version number 4.1.6 + verification checklist completion
- `docsV3/EVOLUTION_RULES_AND_LOGIC_V3.md` - outdated banner
- `docsV4/design-v4-engine.md` - privacy generalization + V4.1.2 change notes
- `docsV3/ADVERSARIAL_AUDIT_v3.9.0.md` - 16 real local paths generalized (follow-up)
- `docsV3/EXPORT_AND_ANALYSIS_DESIGN.md` - 18 real local paths/project hashes generalized (follow-up)
- `docsV3/archive/STATUS.md` - 1 real local path generalized (follow-up)
- `docsV3/archive/V2_DESIGN.md` - 2 real local paths generalized (follow-up)
- `docsV3/PRIVACY_SCAN_v4.1.6.txt` - privacy scan self-check result record (follow-up, new file)
- `docsV3/privacy_scan_paths.txt` - raw output of path-type scan (2 false positives, ruled as placeholders) (follow-up, new file)
- `docsV3/privacy_scan_hash.txt` - raw output of project hash-type scan (0 hits) (follow-up, new file)
- `docsV3/privacy_scan_uuid.txt` - raw output of UUID-type scan (0 hits) (follow-up, new file)

**Follow-up records** (after the v4.1.6 entry): ① §3.1 verification checklist actually completed (tests/ expected lines + `.claude/commands/` verification step) — the original entry claimed it was done, but the file had not actually been modified at the time; this follow-up makes that claim true; ② the statistics table at the bottom gains a v4.1.6 row; ③ 37 real local paths/project hashes in four docsV3 files generalized (the original entry only covered the docsV4 examples and the export.py docstring); ④ CLAUDE.md release rules add a "privacy scan self-check" (checklist of six identifier patterns). ⑤ (follow-up after the four-perspective review) the review found 8 missed items: 7 WSL lowercase drive-letter paths (`/e/…` form) in EXPORT_AND_ANALYSIS_DESIGN.md + 1 bare parent-directory form (`E:\…\`, without the project name) in ADVERSARIAL_AUDIT_v3.9.0.md — the sed in ③ only covered two forms: backslashes and uppercase drive letters with forward slashes; moreover the "final verification 0 residue" at the time was a false negative (a content-level `grep -v` filter removed entire leaked lines containing the string `evolution/`). Now all 8 have been generalized (both files fully cleaned, 16/18 cumulative in total; ③'s statistics hold under the cumulative count); the CLAUDE.md privacy scan rule is changed to directory-level exclusion + a checklist of four path forms; the second expected checklist in INSTALLATION_GUIDE §4 is supplemented with tests/ and `.claude/commands/` verification (the original entry's "§3.1/§4" claim is now fully delivered); correct full-scan result under directory-level exclusion: 0 real hits across the six identifier categories (2026-09-11). Privacy scan self-check results are kept in `docsV3/PRIVACY_SCAN_v4.1.6.txt` (the three types of raw output are in `privacy_scan_paths.txt` / `privacy_scan_hash.txt` / `privacy_scan_uuid.txt` in the same directory).

## v4.1.5 (2026-09-10)

### Fixed Release

Implemented several fixes left over from the previous round of review:

**Test rewrite**:
- sha256 regression test 1 rewritten as a real incremental flow (`export_full` → `commit` →
  append → `export_incremental` → assert state sha256 == actual file sha256 →
  `commit` → append again → `export_incremental` → assert no `file-replaced` false positive),
  truly locking down the sha256 refresh path of `export_incremental` (the original test manually
  constructed FileInfo and only covered the pure-append branch of `check_integrity`, never reaching
  the refresh code). During the test, `find_jsonl_file` is injected via monkeypatch to isolate the
  real `~/.claude/projects/` environment.

**Documentation fixes**:
- Installation guide: Section 1.3 of `INSTALLATION_GUIDE.md` changed from "Python 3.8.x or higher"
  to "Python 3.9.x or higher" (consistent with the 3.9+ system requirement in Section 1.1)
- `CLAUDE.md` removes the three template sections (Issue tracker / Triage labels / Domain docs,
  left over from the scaffolding template; this repository has not adopted `.scratch/`,
  `CONTEXT.md`, or `docs/adr/`)
- Archived dead links: `./VERSION_HISTORY.md` in `docsV3/archive/EVOLUTION_RULES_AND_LOGIC_V2.md`
  and `docsV3/archive/V2_DESIGN.md` changed to `../VERSION_HISTORY.md` (relative paths broke after
  the archive subdirectory moved up)

**won't-fix** (explicitly ruled per the `CLAUDE.md` release rules):
- The `evolution/knowledge-base/archive/` ignore rule in `.gitignore` is kept as-is and not removed.
  Reason: that directory holds large files such as `v4.0.0-kb-manager` archived in V4.1.0, and the
  on-demand commit strategy is unchanged; archived content can still be brought under version control
  via an explicit `git add -f`, so there is no functional blocker, hence recorded as won't-fix.

### Modified Files

- `.claude/skills/evolution/tests/test_sha256_invariant.py` - test 1 rewritten as a real incremental flow (3/3 passing)
- `docsV3/INSTALLATION_GUIDE.md` - Python version 3.8.x → 3.9.x
- `CLAUDE.md` - version number 4.1.5 + removal of the three template sections
- `docsV3/archive/{EVOLUTION_RULES_AND_LOGIC_V2,V2_DESIGN}.md` - dead link fixes
- `docsV3/EXPORT_AND_ANALYSIS_DESIGN.md` - session UUID generalization + outdated banner
- `.claude/skills/evolution/evolution-export.py` - system version 4.1.5
- `.claude/skills/evolution/{SKILL.md,config.yaml,commands/init.md,commands/sync.md}` - version number 4.1.5
- `evolution/knowledge-base/kb-index.md` - version number 4.1.5
- `docsV3/VERSION_HISTORY.md` - v4.1.5 entry + statistics table row

**Follow-up record** (after the 4.1.5 release): corrected the attribution of the V2 archive KB cleanup in the v4.1.4 entry — moved from "verified no change needed (already covered in v4.1.3)" to "changes in this release" and labeled "gap fix", with the "Modified Files" list and the two overview tables updated accordingly.

---

## v4.1.4 (2026-09-10)

### Review Wrap-up

Implemented leftover items from the previous round of review and verified the actual state of earlier fixes:

**Verified no change needed** (confirmed by per-file grep):
- The v4.1.1/v4.1.2 rows in the bottom statistics table already have a `PATCH` type column — added in v4.1.3

**Changes in this release**:
- Gap fix: V2 archive KB privacy cleanup — `docsV3/archive/evolution-manual-v2/knowledge-base/{facts,pitfalls,state}.md` still contained employer/local-environment identifiers (the v4.1.3 cleanup covered the current KB and active documents but not the archive directory; this round of review re-scanned and confirmed it), generalized in this round per the current KB standard (the list is in the internal review record and is not committed)
- Rule file version number unification: `rules/{write,read,dedup}.md` heading v4.1.3 → v4.1.4
- Export script version header clarification: the header of `evolution-export.py` changed from "unchanged since V4.0.0" to "most recent substantive change in the V4.1.3 sha256 refresh fix", and noted that the VERSION constant is the sync-state schema version (3.5.0), independent of the system documentation version
- `CLAUDE.md` adds "Release rules": findings confirmed in each round of review must appear in the fix list or be explicitly labeled won't-fix + reason (to prevent a "funnel of dropped items")
- Removed the line in the v2.0.0 section referencing the non-existent file `INSTALLATION_GUIDE_V2.md` (dead link)
- Created the sha256 invariant regression test `.claude/skills/evolution/tests/test_sha256_invariant.py` (3 assertion groups, all passing):
  1. Double append does not trigger a file-replaced false positive
  2. status read-only mode does not modify files on disk
  3. Corruption recovery chain writes back correctly

### Modified Files

- `.claude/skills/evolution/rules/{write,read,dedup}.md` - heading version number → 4.1.4
- `.claude/skills/evolution/evolution-export.py` - header version description clarified + system version 4.1.4
- `.claude/skills/evolution/tests/test_sha256_invariant.py` - new
- `CLAUDE.md` - version number 4.1.4 + release rules
- `.claude/skills/evolution/{SKILL.md,config.yaml,commands/init.md,commands/sync.md}` - version number 4.1.4
- `evolution/knowledge-base/kb-index.md` - version number 4.1.4
- `docsV3/archive/evolution-manual-v2/knowledge-base/{facts,pitfalls,state}.md` - privacy cleanup gap fix
- `docsV3/VERSION_HISTORY.md` - v4.1.4 entry + dead link removal

---

## v4.1.3 (2026-09-10)

### Fixed Release

Fixed CRITICAL issues found by the five-perspective review (multi-model):

**Must fix**:
- sha256 refresh: after appending on the incremental path, update fi.sha256 in sync (to prevent a file-replaced false positive)
- Root directory cleanup: deleted 18 stale files + docs/ + leftover lock/chunk backups
- Bilingual README fix: created a real English README.md
- KB privacy cleanup: generalized real employer/identity information
- Added the LICENSE file (MIT)

**Suggested fixes**:
- state-version-newer labeled as unimplemented
- "current session filtering" removed as a fictional promise
- Corrected corruption recovery guidance
- Added changelog for the removal of test_concurrent.py
- Added the v4.1.1/v4.1.2 rows to the VERSION_HISTORY statistics table

### Modified Files

- `.claude/skills/evolution/evolution-export.py` - sha256 refresh + corruption guidance fix
- `README.md` - rewritten as the English version
- `LICENSE` - new
- `evolution/knowledge-base/*.md` - privacy cleanup
- root directory - cleanup of stale files
- all version numbers upgraded to 4.1.3

---

## v4.1.2 (2026-09-10)

### Fixed Release

Fixed all 10 issues found by the three-perspective adversarial review (multi-model):

**Must fix**:
- CLEANUP_PATTERNS removes sync-state.json (to prevent accidental deletion of the state file)
- Unified lock path as export.lock (to prevent concurrent lost updates)
- --mode status writes back after recovery (to prevent a read-only command from destroying state)
- error state changed to exit 1 (aligned with the exit code protocol)
- Created README.md / README.zh-CN.md (release preparation)

**Suggested fixes**:
- Added rollback banners to the three docsV4 design documents
- export_full loads existing state (preserving batch history)
- status string unified as failed
- trust_committed promise marked as unimplemented
- Cleaned up root directory clutter

### Modified Files

- `.claude/skills/evolution/evolution-export.py` - CLEANUP_PATTERNS + lock path + recovery chain + exit code + status string
- `.claude/skills/evolution/commands/init.md` - version number + cleanup suggestion adjustment
- `.claude/skills/evolution/commands/sync.md` - version number
- `README.md` / `README.zh-CN.md` - new
- `docsV4/*.md` - rollback banners
- Deleted `tests/test_concurrent.py` (disabled; no longer applicable after the lock scheme change)
- all version numbers upgraded to 4.1.2

---

## v4.1.1 (2026-09-10)

### Fixed Release

Fixed all issues found in the review (multi-model review):

**Must fix**:
- evolution-export.py header version labeling (engine version v3.10.0 / system version 4.1.1)
- /evolution-init registration path (created .claude/commands/evolution-init.md)
- Path anchoring implementation (get_project_root() function, parents[3])
- kb-manager.py archiving (moved to archive/v4.0.0-kb-manager/)
- facts.md / pitfalls.md footer update (2026-09-10)
- CLAUDE.md dead link fix (removed references to non-existent files)

**Suggested fixes**:
- Exit code protocol documented (sync.md)
- assert changed to explicit error (commit_batch cursor-regression)
- chunk naming documented (init.md step 2)
- Empty-document guidance removed (read.md no longer routes to growth-notes etc.)

### Modified Files

- `.claude/skills/evolution/evolution-export.py` - header rewrite + path anchoring + assert changed to error
- `.claude/commands/evolution-init.md` - new
- `.claude/skills/evolution/kb-manager.py` - moved to archive/
- `.claude/skills/evolution/commands/init.md` - version number + documentation update
- `.claude/skills/evolution/commands/sync.md` - version number + exit code documentation
- `.claude/skills/evolution/rules/read.md` - removed empty-document guidance
- `evolution/knowledge-base/facts.md` - footer update
- `evolution/knowledge-base/pitfalls.md` - footer update
- `evolution/knowledge-base/kb-index.md` - version number update
- `CLAUDE.md` - version number + dead link fix

---

## v4.1.0 (2026-09-10)

**Fixed release**: based on consensus among four reviewers — kept the V4 engine-layer fixes (the 3 Critical issues that would cause permanent data loss were indeed real problems), rolled back knowledge-layer over-engineering, restored the V3 lightweight rules + added two red lines, and restored knowledge base usability (all 16 [P] entries restored to [D]/[V], pending.md deleted).

### Kept (all engine-layer fixes)

- Dual cursors (`exported_lines` / `committed_lines`) + batch state machine + `--mode commit` protocol and receipt
- Integrity check (mtime+size fast path → sha256 decision table)
- Atomic write (tmp + fsync + os.replace) + three-level recovery chain
- Full export streaming (two-pass scan + k-way merge), global timestamp sorting, token safety factor 1.5,
  800K character hard guard, ParseStats parse defense, documentation honesty

### Rolled Back (knowledge-layer over-engineering)

- `kb-manager.py`: downgraded from "sole write entry point" to an optional read-only tool (only `validate` /
  `health` / `scan` available; `add` / `promote` / `deprecate` / `restore` / `archive` /
  `migrate` / `compress` report an error and exit immediately, exit 2)
  - V4.1.0 review fix: the entire file archived to
    `evolution/knowledge-base/archive/v4.0.0-kb-manager/`, moved out of the skill directory (eliminating
    dead code and the misleading `validate` error message)
- `[P]` isolation + pending.md: deleted; "new knowledge lands in [D] and is immediately usable" restored
- Four-tier status `[P]/[D]/[V]/[X]/[C]/blocked` → restored to three tiers `[D]/[V]/[X]`
- Evidence type binding + confidence, `kb-meta` metadata line: all removed, restored to plain markdown
- Lifecycle (30/90/180/365-day thresholds), automatic archive/ archiving: removed (no archive/ directory was ever generated)
- Sensitive scan write gate: removed (config.yaml `sensitive_patterns` section deleted)
- `/kb-review` `/kb-status` `/kb-archive` `/kb-restore`: 4 command files deleted,
  SKILL.md restored to 2 commands (`/evolution` `/evolution-init`)
- `sync.md` health-check scan step (`kb-manager.py health`) removed; commit batch protocol retained

### Added (two red lines in write.md, replacing the entire pending subsystem)

1. `[D]`/unverified entries must not eliminate `[V]`; conflicts are kept side by side and labeled "contradiction exists, pending human ruling"
2. Unverified entries are not the sole basis for high-risk decisions; when conflicting with `[V]`, `[V]` prevails and the user is warned

### Main Modified Files

- `evolution/knowledge-base/{facts,pitfalls,state}.md` — removed `kb-meta` lines, `[P]`→`[D]`
- `evolution/knowledge-base/pending.md` — deleted (empty isolation zone)
- `evolution/knowledge-base/kb-index.md` — restored V3 format (removed the [P] isolation zone description)
- `.claude/skills/evolution/rules/{write,read,dedup}.md` — restored V3 + two red lines (write.md rules 3/4)
- `.claude/skills/evolution/commands/` — deleted kb-review/kb-status/kb-archive/kb-restore
- `.claude/skills/evolution/{SKILL.md,config.yaml}` — 4.1.0; config removes
  status_markers extension/lifecycle/lock/sensitive_patterns, keeps sync_engine
- `.claude/skills/evolution/kb-manager.py` → `evolution/knowledge-base/archive/v4.0.0-kb-manager/` — 4.1.0: archived after the write entry point was disabled (V4.1.0 review fix)
- `.claude/skills/evolution/tests/test_concurrent.py` — marked disabled (retained for reference)
- `CLAUDE.md`, `docsV3/VERSION_HISTORY.md` — 4.1.0

---

## v4.0.0 (2026-08-24)

**MAJOR upgrade**: implemented the V4 design (docsV4/) based on an adversarial audit (54 agents, 39 confirmed findings), fixed 3 Critical issues that would cause permanent data loss, and rebuilt the knowledge quality defense line.

### Critical Issues Fixed

1. **Critical 1 — incremental cursor committed before knowledge extraction**
   - `processed_lines` split into dual cursors `exported_lines` / `committed_lines`
   - The incremental start point changed to `committed_lines + 1`; a batch is created for each export, and after
     the sub agent analyzes it, an explicit confirmation via `--mode commit` is required (returning a receipt),
     so interruptions can be recovered and failures automatically regenerated
2. **Critical 2 — cursor had no integrity check; truncation/rotation silently lost data**
   - Added `check_integrity`: mtime+size fast path → sha256 comparison decision table;
     truncation/replacement of the whole file triggers re-export + WARN + partial status; pure appends follow the normal incremental path
3. **Critical 3 — state file was not written atomically**
   - `save_sync_state` changed to tmp + fsync + os.replace atomic write;
   - three-level recovery chain on corruption: `.bak` recovery → explicit failure when no backup exists (never silently fall back to empty state)

### New Features (engine layer)

- Batch manifest and state machine (exported/analyzing/committed/failed) + regeneration + retry limit
- `--mode commit / start / analyze-failed / status --verify` CLI and exit code protocol
  (0=success / 1=failed; partial also exits with 0, distinguished by the `status` field of the returned JSON;
  the authoritative definition is in the "exit code protocol" section of `.claude/skills/evolution/commands/sync.md`)
- Full export streaming: two-pass scan + k-way merge (O(1) memory), global timestamp sorting,
  session-aware turn grouping, unconditional flush for oversized turns (fixing timestamp disorder)
- Token estimation safety factor 1.5 + 800K character hard guard; ParseStats parse defense (bad lines do not crash)

### New Features (knowledge layer)

- Four-tier status model `[P]/[D]/[V]/[X]` + conflict overlay `[C]`; 100% of new entries first land in the pending.md isolation zone
- `kb-manager.py` sole write entry point (add/promote/deprecate/restore/archive/compress/
  health/scan/migrate/validate): `.kb.lock` transaction lock + temporary copy verification + atomic replacement
- Sensitive information gate: scan before writing (config.yaml sensitive_patterns is the sole authoritative source);
  matched entries land in pending in masked form (blocked=secret, zero raw values written to disk)
- Knowledge lifecycle: overdue archiving (archive/YYYY-MM/ + manifest), index compression (500-line limit),
  four new commands `/kb-review` `/kb-status` `/kb-archive` `/kb-restore`

### Removed

- Phantom commands `/kb-sync` `/growth-sync` `/alignment-sync` (never registered, #23 command unification)

### Main Modified Files

- `.claude/skills/evolution/evolution-export.py` — dual cursor + batch + integrity + streaming refactor
- `.claude/skills/evolution/kb-manager.py` — new (sole write entry point + transaction + lifecycle)
- `.claude/skills/evolution/config.yaml` — sync_engine/lifecycle/lock/sensitive_patterns
- `.claude/skills/evolution/rules/{write,read,dedup}.md` — V4 rule rewrite
- `.claude/skills/evolution/commands/` — added kb-review/kb-status/kb-archive/kb-restore
- `evolution/knowledge-base/pending.md` — new isolation zone
- `.gitignore`, README (privacy section)

---

## v3.9.0 (2026-08-01)

### New Features

1. **`/evolution-init` pre-check**
   - Before initialization, run `python .claude/skills/evolution/evolution-export.py --mode status` to check `last_full_sync`
   - When an existing initialization record is detected, confirm with the user whether to continue
   - Prevents accidental resets that overwrite chunk files and reset the incremental cursor

### Modified Files

- `.claude/skills/evolution/commands/init.md`
  - Added step 0 pre-check logic
  - Fixed an orphan U+FE0F variation selector character
  - Unified the command format as `python .claude/skills/evolution/evolution-export.py --mode status`

---

## v3.8.0 (2026-08-01)

### Fixes

1. **Enforce use of the export script + prohibit manual glob**
   - The `/evolution-init` command explicitly prohibits manually globbing `~/.claude/projects/`
   - If the script returns `status != success`, it must stop and report
   - Do not bypass the script, do not fall back to manual reading

2. **Fixed `find_jsonl_file` returning all files**
   - Uses `glob("*.jsonl")` to match only .jsonl files in the current directory
   - Does not enter the subagents subdirectory, no extra filtering needed
   - Returns the list of all discovered JSONL files (ascending by modification time)

3. **Added validation mechanism**
   - File consumption consistency check: assert that the `discovered_files` and `parsed_files` sets are equal
   - Cross-process file lock `file_lock`: prevents concurrent exports from corrupting state
   - Uses `msvcrt.locking` on Windows and `fcntl.flock` on Linux/macOS

### Modified Files

- `.claude/skills/evolution/evolution-export.py` - added consistency check, file lock, `parse_jsonl_full`, `count_physical_lines`
- `.claude/skills/evolution/commands/init.md` - enforced script + prohibited manual glob
- `docsV3/EXPORT_AND_ANALYSIS_DESIGN.md` - design document updated accordingly

---

## v3.7.0 (2026-08-01)

### Fixes

1. **Fixed the `/evolution-init` command**
   - Calls `evolution-export.py` to export all historical conversations
   - Prevents sampling from losing historical conversations

---

## v3.6.0 (2026-08-01)

### Fixes

1. **Distinguish initialization from incremental sync commands**
   - Changed `/evolution init` into the standalone command `/evolution-init`
   - `/evolution` is dedicated to incremental sync
   - Avoids misoperations caused by parameter confusion

---

## v3.5.0 (2026-07-31)

### Refactoring

1. **Refactored based on writing-great-skills rules**
   - SKILL.md reduced from 96 lines to 37 lines
   - Follows the progressive disclosure principle, with a concise entry file

---

## v3.4.0 (2026-07-31)

### Refactoring

1. **Modular refactoring**
   - SKILL.md split into a modular structure
   - Added `config.yaml` unified configuration (pagination parameters, token estimation, status markers)
   - Added the `commands/` directory (init.md, sync.md)
   - Added the `rules/` directory (write.md, read.md, dedup.md)
   - `evolution-export.py` reads configuration from config.yaml

---

## v3.3.0 (2026-07-30)

### Fixes

1. **JSON serialization crash**
   - Unified `state_to_dict` serialization to avoid FileInfo being non-JSON-serializable

2. **Incremental unit drift**
   - `processed_lines` changed to use the real line number of the last entry (physical line number) instead of `len(entries)`
   - Avoids mixing units between physical line numbers and logical entry counts

3. **Windows encoding**
   - Forces stdout/stderr to use UTF-8 to avoid GBK encoding crashes
   - File reads and writes explicitly specify `encoding='utf-8'` + `errors='replace'`

4. **Token estimation bias**
   - CJK coefficient lowered from 1.5 to 1.0 characters/token, correcting the systematic underestimation

5. **cleanup safety**
   - Only deletes files within the whitelist, never rmtree an entire directory

6. **File handle leaks**
   - Fixed multiple instances of file handles not being closed properly

---

## v3.2.1 (2026-07-30)

### Changes

1. **Updated pagination parameter**
   - Target chunk size: 80K → 150K (based on attention research)
   - Based on U-shaped attention curve research from the "Lost in the Middle" paper

---

## v3.2.0-draft (2026-07-29)

### Initial Design

1. **Initial design draft**
   - Initial design based on a 200K window assumption
   - Later iterated into v3.2.1 (150K) and v3.3.0 (90K)

---

## v3.1.0 (2026-07-29)

### New Features

1. **Initialization command**
   - Added the `/evolution init` command
   - Analyzes all historical conversations after the first installation
   - Generates the initial knowledge base

2. **Conversation export mechanism**
   - The initial design included Method A (AI memory) and Method B (file recording)
   - Since v3.7.0 it is unified as export via the `evolution-export.py` script (the only method)

3. **Sub Agent execution design**
   - All operations executed by sub agent
   - Reduces pollution to main session

### Design Document Changes

1. **CLAUDE.md**
   - Created project configuration file
   - Defined knowledge base location

2. **SKILL.md**
   - Updated to v3.1.0
   - Added initialization command
   - Added conversation export mechanism
   - Emphasized sub agent execution principles

3. **DESIGN_V3.1.0.md**
   - Created new design document
   - Detailed design considerations
   - Documented document responsibility division

---

## v3.0.0 (2026-07-28)

**Major changes**:
- Removed `evolution-auto/` directory (auto-trigger version)
- Knowledge base directory changed from `evolution-manual/` to `evolution/`
- Simplified system, kept only manual trigger version

**Reason for changes**:
- All content must be manually reviewed
- Humans also need to read documents for learning
- Auto-trigger version was not battle-tested
- Simplify system, reduce complexity

**Modified files**:
- Deleted `evolution-auto/` directory
- Renamed `evolution-manual/` → `evolution/`
- `.claude/skills/evolution/SKILL.md`
  - Version number: 2.1.0 → 3.0.0
  - Removed "auto trigger" section
  - Removed "manual trigger" heading (only one version left)
  - Updated knowledge base location: `evolution-manual/` → `evolution/`
  - Added core principle: manual review
- `evolution/knowledge-base/kb-index.md`
  - Version number: 2.1.0 → 3.0.0
  - Removed "manual trigger" label
  - Updated location information

**Backward compatibility**:
- ❌ Not compatible (directory structure changes)
- ⚠️ Requires migrating existing knowledge base

**Migration guide**:
```bash
# 1. Rename directory
mv evolution-manual evolution

# 2. Update path references in SKILL.md (done automatically)

# 3. Verify
/evolution
```

---

### [2.1.0] - 2026-07-28

**New features**:
- Added write review mechanism (status markers)
- New entries are marked as `[D]` (draft) by default
- User-confirmed entries are marked as `[V]` (verified)
- Deprecated entries are marked as `[X]` (deprecated)

**Modified files**:
- `.claude/skills/evolution/SKILL.md`
  - Added "Write rules (review mechanism)" section
  - Defined three-tier status model (draft/verified/deprecated)
  - Clarified write rules and conflict handling
  
- `evolution-manual/knowledge-base/kb-index.md`
  - Added "Reading guide (AI must follow)" section
  - Defined status marker descriptions
  - Clarified usage rules (priority, conflict handling)

- `evolution-manual/knowledge-base/facts.md`
  - Added status marker descriptions
  - Added `[V]` markers to existing entries

**Design documents**:
- `docs/EARLY_REVIEW.md` - AI's in-depth review
- `docs/PROJECT_BACKGROUND.md` - Project background (original user requirements)

**Reason for improvement**:
- The AI review identified "missing write review mechanism" as a fatal flaw
- Erroneous information can form a self-reinforcing loop
- A simple review mechanism is needed to break the loop

**Impact scope**:
- All knowledge base files (facts.md, pitfalls.md, etc.)
- AI's reading and writing behavior
- Users may need to review new entries

**Backward compatibility**:
- ✅ Fully compatible with V2.0
- ✅ Old entries have no markers, default to `[D]`
- ✅ Reading rules are friendly to unmarked entries

---

### [2.0.0] - 2026-07-28

**Major changes**:
- Migrated from Slash Command to Skill system
- Supports progressive disclosure
- Supports auto trigger (AI judgment)

**New features**:
- Bidirectional capability (read + write)
- Progressive reading rules
- Separated from Auto Memory

**Modified files**:
- `.claude/skills/evolution/SKILL.md` - Created new
- `CLAUDE.md` - Deleted (Skill works independently)

**Design documents**:
- `docs/V2_DESIGN.md` - V2 design document
- `docs/EVOLUTION_RULES_AND_LOGIC_V2.md` - System rules
- `docs/V2_TEST_GUIDE.md` - Test guide
- `docs/UPDATE_NOTES_V2.md` - Update notes
- `docs/PROJECT_BACKGROUND.md` - Project background
- `docs/EARLY_REVIEW.md` - AI review

**Reason for improvement**:
- V1 used Slash Command, AI was unaware of the knowledge base
- V2 uses Skill, AI knows and can auto trigger
- Saves 66% context consumption

---

### [1.0.0] - 2026-07-21

**Initial release**:
- Used Slash Command trigger
- Basic knowledge base structure
- Unidirectional capability (read only)

**Files**:
- `.claude/commands/evolution.md` - Command definition
- `evolution-manual/knowledge-base/` - Knowledge base directory

**Known issues**:
- AI is unaware of the knowledge base
- Cannot auto trigger
- High context consumption (full read)

---

## Change Statistics

| Version | Date | Type | Major changes |
|---------|------|------|---------------|
| v1.0.0 | 2026-07-21 | Initial | Slash Command |
| v2.0.0 | 2026-07-28 | MAJOR | Migrated to Skill system |
| v2.1.0 | 2026-07-28 | MINOR | Write review mechanism |
| v3.0.0 | 2026-07-28 | MAJOR | Removed auto version, simplified system |
| v3.1.0 | 2026-07-29 | MINOR | Added initialization command, conversation export mechanism |
| v3.2.0-draft | 2026-07-29 | DRAFT | Initial design based on 200K window assumption (superseded by v3.2.1) |
| v3.2.1 | 2026-07-30 | PATCH | Updated pagination parameter: 80K → 150K |
| v3.3.0 | 2026-07-30 | MINOR | Fixed multiple bugs (serialization, encoding, token estimation, etc.) |
| v3.4.0 | 2026-07-31 | MAJOR | Modular refactoring, config.yaml unified configuration |
| v3.5.0 | 2026-07-31 | MINOR | SKILL.md refactored, reduced from 96 lines to 37 lines |
| v3.6.0 | 2026-08-01 | MINOR | Distinguish initialization from incremental sync commands |
| v3.7.0 | 2026-08-01 | MINOR | Fixed /evolution-init calling the export script |
| v3.8.0 | 2026-08-01 | MINOR | Fixed three bugs + added validation mechanism |
| v3.9.0 | 2026-08-01 | MINOR | Added /evolution-init pre-check |
| v4.0.0 | 2026-08-24 | MAJOR | Dual cursors+batch+commit, integrity check, atomic write, [P] isolation, transaction lock, lifecycle, sensitive gate |
| v4.1.0 | 2026-09-10 | PATCH | Kept engine-layer fixes, rolled back knowledge-layer over-engineering ([P] isolation/kb-manager write entry point/lifecycle/sensitive gate/4 new commands), restored [D]/[V]/[X] three tiers + two red lines |
| v4.1.1 | 2026-09-10 | PATCH | Fixed release: path anchoring, version labeling, kb-manager archiving, documentation cleanup |
| v4.1.2 | 2026-09-10 | PATCH | Fixed release: 10 review issue fixes (CLEANUP/lock/status/exit/README/banner/state/string/marker/cleanup) |
| v4.1.3 | 2026-09-10 | PATCH | Five-perspective review fixes (sha256 refresh/root directory cleanup/English README/KB privacy cleanup/LICENSE) |
| v4.1.4 | 2026-09-10 | PATCH | Review wrap-up (release rules/sha256 regression test/V2 archive KB cleanup gap fix/version number unification/version header clarification/dead link removal) |
| v4.1.5 | 2026-09-10 | PATCH | Five-perspective review fixes: privacy cleanup, test rewrite, documentation fixes |
| v4.1.6 | 2026-09-11 | PATCH | Version unification (including rules drift fix), privacy generalization (docsV4 examples/export.py docstring/docsV3 paths), design document notes, outdated banner, verification checklist completion, grep self-check rule |

---

## Future Plans

### Voided (original [4.1.0] planned items; no longer applicable after V4.1.0 rolled back [P] isolation/lifecycle)
- Unified ruling on the restore target location and the [P] isolation principle
- Unification of the semantics of cleanup and sync-state.json never being deleted
- health stale statistics excluding blocked entries
- Automatic health-check cleanup of leftover .kb.tmp files

---

## Related Documents

| Document | Description |
|----------|-------------|
| `docsV3/archive/EARLY_REVIEW.md` | AI's in-depth review (archived) |
| `docsV3/archive/V2_DESIGN.md` | V2 design document (archived) |
| `docsV3/archive/EVOLUTION_RULES_AND_LOGIC_V2.md` | System rules V2 (archived) |
| `docsV3/PROJECT_BACKGROUND.md` | Project background |

---

**End of document**
