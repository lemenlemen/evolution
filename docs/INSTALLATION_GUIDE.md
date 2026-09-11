# Evolution Installation Guide

🌐 **Language / 语言**: [English](INSTALLATION_GUIDE.md) | [中文](INSTALLATION_GUIDE.zh-CN.md)

> **Version**: 4.1.6 (2026-09-11)  
> **Supported platforms**: Windows / macOS / Linux

> **Version history**: See [`VERSION_HISTORY.md`](./VERSION_HISTORY.md)

---

## 1. Prerequisites

### 1.1 System Requirements

| Item | Requirement |
|------|------|
| **Claude Code** | Latest version (Skill system support) |
| **Python** | 3.9+ (used by `evolution-export.py` to export conversation history) |
| **Operating system** | Windows 10+ / macOS 10.15+ / Ubuntu 18.04+ |
| **Shell** | Git Bash / Zsh / Bash |

### 1.2 Verify Claude Code Version

```bash
claude --version
```

**Expected output**:
```
claude version 2.1.x or higher
```

### 1.3 Verify Python Environment

```bash
python --version
```

**Expected output**:
```
Python 3.9.x or higher
```

> Evolution uses the `evolution-export.py` script to export conversation history, so Python is a required dependency.

---

## 2. Installation Steps

### 2.1 Create Skill Directory

```bash
# Enter project root directory
cd <your-project>

# Create Skill directory
mkdir -p .claude/skills/evolution
```

### 2.2 Create Skill Files (Modular Structure)

Evolution v3.4.0+ is modular and requires the following complete structure:

```
.claude/skills/evolution/
├── SKILL.md              # Entry file (command and rule index)
├── config.yaml           # Unified configuration (pagination, token estimation, status markers)
├── evolution-export.py   # Conversation export script (Python)
├── commands/
│   ├── init.md           # /evolution-init initialization command
│   └── sync.md           # /evolution incremental sync command
├── rules/
│   ├── write.md          # Write rules
│   ├── read.md           # Read rules
│   └── dedup.md          # Deduplication rules
└── tests/
    └── test_sha256_invariant.py  # sha256 invariant regression test (optional)
```

The project root also needs a command registration file (for `/evolution-init` slash command discovery):

```
.claude/
├── commands/
│   └── evolution-init.md  # /evolution-init command registration (references skills/evolution/commands/init.md)
└── skills/
    └── evolution/         # See the directory tree above
```

Copy all files from GitHub:

```bash
# Create subdirectories
mkdir -p .claude/skills/evolution/commands
mkdir -p .claude/skills/evolution/rules

# Download the entry file and configuration
curl -o .claude/skills/evolution/SKILL.md https://raw.githubusercontent.com/lemenlemen/evolution/main/.claude/skills/evolution/SKILL.md
curl -o .claude/skills/evolution/config.yaml https://raw.githubusercontent.com/lemenlemen/evolution/main/.claude/skills/evolution/config.yaml
curl -o .claude/skills/evolution/evolution-export.py https://raw.githubusercontent.com/lemenlemen/evolution/main/.claude/skills/evolution/evolution-export.py

# Download command files
curl -o .claude/skills/evolution/commands/init.md https://raw.githubusercontent.com/lemenlemen/evolution/main/.claude/skills/evolution/commands/init.md
curl -o .claude/skills/evolution/commands/sync.md https://raw.githubusercontent.com/lemenlemen/evolution/main/.claude/skills/evolution/commands/sync.md

# Download rule files
curl -o .claude/skills/evolution/rules/write.md https://raw.githubusercontent.com/lemenlemen/evolution/main/.claude/skills/evolution/rules/write.md
curl -o .claude/skills/evolution/rules/read.md https://raw.githubusercontent.com/lemenlemen/evolution/main/.claude/skills/evolution/rules/read.md
curl -o .claude/skills/evolution/rules/dedup.md https://raw.githubusercontent.com/lemenlemen/evolution/main/.claude/skills/evolution/rules/dedup.md

# Download the command registration file (for /evolution-init slash command discovery)
mkdir -p .claude/commands
curl -o .claude/commands/evolution-init.md https://raw.githubusercontent.com/lemenlemen/evolution/main/.claude/commands/evolution-init.md

# Download the test file (optional)
mkdir -p .claude/skills/evolution/tests
curl -o .claude/skills/evolution/tests/test_sha256_invariant.py https://raw.githubusercontent.com/lemenlemen/evolution/main/.claude/skills/evolution/tests/test_sha256_invariant.py
```

> Alternatively, clone the repository and copy the entire `.claude/skills/evolution/` directory.

### 2.3 Create Knowledge Base Directory

```bash
# Create knowledge base directory
mkdir -p evolution/knowledge-base
```

### 2.4 Create Knowledge Base Template Files

Copy the following 8 files to `evolution/knowledge-base/`:

- `kb-index.md` - Index file
- `facts.md` - Key facts
- `pitfalls.md` - Pitfalls
- `state.md` - Current state
- `growth-notes.md` - Learning notes
- `prompt-improvements.md` - Prompt improvements
- `alignment.md` - Alignment checklist
- `decisions.md` - Decision log

Template file reference: [knowledge-base](https://github.com/lemenlemen/evolution/tree/main/evolution/knowledge-base)

---

## 3. Verify Installation

### 3.1 Check Directory Structure

```bash
# View Skill files (modular structure)
ls -R .claude/skills/evolution/

# Should show:
# SKILL.md
# config.yaml
# evolution-export.py
# commands/init.md
# commands/sync.md
# rules/write.md
# rules/read.md
# rules/dedup.md
# tests/test_sha256_invariant.py   # Optional (regression test)

# View the command registration file
ls .claude/commands/

# Should show:
# evolution-init.md

# View knowledge base files
ls -la evolution/knowledge-base/

# Should show 8 files:
# kb-index.md
# facts.md
# pitfalls.md
# state.md
# growth-notes.md
# prompt-improvements.md
# alignment.md
# decisions.md
```

### 3.2 Verify Skill Loading

```
Enter: /context
```

**Observe the Skills section**:

**Expected result**:
```
Project
── evolution: < 50 tokens    ← Should be displayed
```

### 3.3 Test the Initialization Command

```
Enter: /evolution-init
```

> `/evolution` is the incremental sync command; after the first installation you should use `/evolution-init` to initialize the knowledge base.

**Expected behavior**:
```
AI: Let me first trigger a sub agent to export all historical main session conversations...
    [Running evolution-export.py --mode full]
AI: Export complete, starting chunk-by-chunk extraction of key facts...
    [Analyzing conversation history]
AI: Initialization complete!
    Sessions analyzed: N, facts extracted: N, pitfalls: N
```

---

## 4. Troubleshooting

### Problem 1: Skill Not Showing

**Possible causes**:
- Frontmatter format error
- Incorrect directory structure

**Solution**:
```bash
# Check directory structure
ls -R .claude/skills/evolution/

# Should show the complete modular structure:
# SKILL.md, config.yaml, evolution-export.py
# commands/init.md, commands/sync.md
# rules/write.md, rules/read.md, rules/dedup.md
# tests/test_sha256_invariant.py   # Optional (regression test)

# Check the command registration file
ls .claude/commands/
# Should show: evolution-init.md

# Check frontmatter format
head -10 .claude/skills/evolution/SKILL.md

# Should show:
# ---
# name: evolution
# description: ...
# ---
```

### Problem 2: AI Reads All Files at Once

**Possible causes**:
- No explicit progressive disclosure instructions in SKILL.md

**Solution**:
- Check whether SKILL.md has a "progressive reading rules" section
- Confirm the instructions explicitly say "do not read all files at once"

---

## 5. Upgrade Guide

### 5.1 Upgrading from V2 to V3

> V3 changes the knowledge base directory from `evolution-manual/` to `evolution/`.
> Migration uses a **whole-directory rename** (consistent with the migration guide for v3.0.0 in [VERSION_HISTORY.md](./VERSION_HISTORY.md)),
> so all original content is preserved along with the directory and no separate backup is needed; before starting, confirm that the target directory does not exist.

**Steps**:

1. **Pre-check**
   ```bash
   # You should see evolution-manual/ and evolution/ should not exist
   ls -d evolution-manual evolution 2>/dev/null

   # If evolution/ already exists (e.g. a partial migration happened before), back up the old tree to the project root first, then continue:
   # cp -r evolution-manual/knowledge-base ./knowledge-base.v2.backup.$(date +%Y%m%d)
   ```

2. **Whole-directory rename migration**
   ```bash
   # Whole-directory rename: knowledge base files move with the directory, preserving the original content naturally
   mv evolution-manual evolution
   ```

   After migration the knowledge base is located at `evolution/knowledge-base/`, matching the V3 path.
   The legacy `evolution/agents/` subdirectory is a V2 artifact; you may keep it for reference or delete it manually.

3. **Fix old paths inside the knowledge base (optional but recommended)**

   The V2-era `kb-index.md` / `facts.md` may still self-reference the old `evolution-manual/` path;
   manually replace any occurrences of `evolution-manual/` with `evolution/`.

4. **Verify**
   ```bash
   # Knowledge base files should now be in the new location
   ls evolution/knowledge-base/

   # Verify the installation according to Section 3
   ```

---

## 6. Uninstall Guide

> **All commands below must be run from the project root directory (the directory containing `.claude/` and `evolution/`).**
> Run `pwd` first to confirm your location, to avoid accidentally deleting other directories.

### 6.0 Back Up Before Uninstalling (Strongly Recommended)

The knowledge base is not under version control by default, and cannot be recovered once deleted. Back it up first:

```bash
# Confirm you are in the project root directory
pwd

# Back up the knowledge base to a location outside the project root
cp -r evolution/knowledge-base ~/evolution-kb-backup-$(date +%Y%m%d)

# Confirm the backup succeeded before continuing
ls ~/evolution-kb-backup-*
```

### 6.1 Full Uninstall

```bash
# 1) Preview what will be deleted first (without actually deleting)
find .claude/skills/evolution evolution/knowledge-base -type f

# 2) Remove the Skill
rm -r .claude/skills/evolution

# 3) Remove the knowledge base (precise path, only knowledge-base, leaving project source untouched)
rm -r evolution/knowledge-base

# 4) If evolution/ is now empty, remove the empty directory; otherwise keep it
rmdir evolution 2>/dev/null || echo "evolution/ is not empty, kept"

# 5) Clean up the export cache and sync state (optional, includes all chunk files)
rm -r .evolution
```

> ⚠️ **Do not run `rm -rf evolution`**:
> - The project root directory of this repository itself may be named `evolution`, so running it at the wrong directory level would delete the entire project;
> - Even when run at the project root, it would delete non-knowledge-base content under `evolution/` as well.
> Always use the precise path `evolution/knowledge-base` shown above.
>
> When using `rm -r` (without `-f`), you will be prompted to confirm for write-protected files; this is expected protective behavior.

### 6.2 Keep the Knowledge Base

If you only want to uninstall the Skill while keeping the knowledge base:

```bash
# Only remove the Skill
rm -r .claude/skills/evolution

# Keep the knowledge base
# The evolution/knowledge-base/ directory remains unchanged
```

---

## 7. Best Practices

### 7.1 Regular Cleanup

```bash
# Check knowledge base size
du -sh evolution/knowledge-base/

# If too large, consider archiving old entries
```

### 7.2 Version Control

```bash
# Include the knowledge base in version control
git add evolution/knowledge-base/
git commit -m "chore: update knowledge base"
```

### 7.3 Team Sharing

```bash
# Commit Skill files to the repository
git add .claude/skills/evolution/
git commit -m "feat: add evolution skill"

# Team members will automatically get it after cloning
```

---

## 8. References

### 8.1 Official Documentation

- [Extend Claude with skills](https://code.claude.com/docs/en/skills)
- [How Claude remembers your project](https://code.claude.com/docs/en/memory)
- [Commands](https://code.claude.com/docs/en/commands)

### 8.2 Project Documentation

- [Design document](./DESIGN_V3.1.0.md)
- [Project background](./PROJECT_BACKGROUND.md)
- [Version history](./VERSION_HISTORY.md)

---

**Installation complete! Start using Evolution v4.1.6.**
