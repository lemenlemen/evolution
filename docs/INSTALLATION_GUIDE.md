# Evolution Installation Guide

> **Version**: 3.3.0 (2026-07-31)  
> **Supported Platforms**: Windows / macOS / Linux

> **Version History**: See [`VERSION_HISTORY.md`](./VERSION_HISTORY.md)

---

## 1. Prerequisites

### 1.1 System Requirements

| Item | Requirement |
|------|-------------|
| **Claude Code** | Latest version (with Skill system support) |
| **Operating System** | Windows 10+ / macOS 10.15+ / Ubuntu 18.04+ |
| **Shell** | Git Bash / Zsh / Bash |

### 1.2 Verify Claude Code Version

```bash
claude --version
```

**Expected Output**:
```
claude version 2.1.x or higher
```

---

## 2. Installation Steps

### 2.1 Create Skill Directory

```bash
# Enter project root directory
cd <your-project>

# Create Skill directory
mkdir -p .claude/skills/evolution
```

### 2.2 Create SKILL.md

Create a `SKILL.md` file in the `.claude/skills/evolution/` directory, content reference:
[SKILL.md](https://github.com/lemenlemen/evolution/blob/main/.claude/skills/evolution/SKILL.md)

Or copy from GitHub:
```bash
curl -o .claude/skills/evolution/SKILL.md https://raw.githubusercontent.com/lemenlemen/evolution/main/.claude/skills/evolution/SKILL.md
```

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

Template files reference: [knowledge-base](https://github.com/lemenlemen/evolution/tree/main/evolution/knowledge-base)

---

## 3. Verify Installation

### 3.1 Check Directory Structure

```bash
# Check Skill file
ls -la .claude/skills/evolution/

# Should show:
# SKILL.md

# Check knowledge base files
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
Input: /context
```

**Observe the Skills section**:

**Expected Result**:
```
Project
── evolution: < 50 tokens    ← Should be displayed
```

### 3.3 Test Manual Trigger

```
Input: /evolution
```

**Expected Behavior**:
```
AI: Let me read kb-index.md to understand the knowledge base overview...
    [Reading kb-index.md]
AI: Based on the index, I need to read...
    [Only reading relevant files]
AI: Done!
```

---

## 4. Troubleshooting

### Problem 1: Skill Not Showing

**Possible Causes**:
- Frontmatter format error
- Incorrect directory structure

**Solution**:
```bash
# Check directory structure
ls -la .claude/skills/evolution/

# Should show:
# SKILL.md

# Check frontmatter format
head -10 .claude/skills/evolution/SKILL.md

# Should show:
# ---
# name: evolution
# description: ...
# ---
```

### Problem 2: AI Reads Everything at Once

**Possible Causes**:
- No explicit progressive read instructions in SKILL.md

**Solution**:
- Check if SKILL.md has a "Progressive Read Rules" section
- Confirm the instructions explicitly say "do not read all files at once"

### Problem 3: Auto-Trigger Not Working

**Possible Causes**:
- `disable-model-invocation: true` (should be `false`)
- `when_to_use` description is unclear

**Solution**:
- Check that frontmatter has `disable-model-invocation: false`
- Improve the `when_to_use` description

---

## 5. Upgrade Guide

### 5.1 Upgrading from V2 to V3

**Steps**:

1. **Backup V2 Files**
   ```bash
   # Backup the old knowledge base
   cp -r evolution-manual/knowledge-base evolution-manual/knowledge-base.v2.backup
   ```

2. **Migrate Knowledge Base**
   ```bash
   # Move files from old directory to new directory
   mv evolution-manual/knowledge-base/*.md evolution/knowledge-base/
   ```

3. **Delete Old Directory**
   ```bash
   # Remove the empty old directory
   rmdir evolution-manual/knowledge-base/
   rmdir evolution-manual/
   ```

4. **Verify**
   ```bash
   # Verify according to Section 3
   ```

---

## 6. Uninstallation Guide

### 6.1 Complete Uninstallation

```bash
# Remove Skill
rm -rf .claude/skills/evolution

# Remove knowledge base
rm -rf evolution
```

### 6.2 Keep Knowledge Base

If you only want to uninstall the Skill but keep the knowledge base:

```bash
# Only remove Skill
rm -rf .claude/skills/evolution

# Keep knowledge base
# evolution/ directory remains unchanged
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
# Include knowledge base in version control
git add evolution/knowledge-base/
git commit -m "chore: update knowledge base"
```

### 7.3 Team Sharing

```bash
# Commit Skill files to the repository
git add .claude/skills/evolution/
git commit -m "feat: add evolution skill"

# Team members automatically get it after cloning
```

---

## 8. References

### 8.1 Official Documentation

- [Extend Claude with skills](https://code.claude.com/docs/en/skills)
- [How Claude remembers your project](https://code.claude.com/docs/en/memory)
- [Commands](https://code.claude.com/docs/en/commands)

### 8.2 Project Documentation

- [Design Document](./DESIGN_V3.1.0.md)
- [Project Background](./PROJECT_BACKGROUND.md)
- [Version History](./VERSION_HISTORY.md)

---

**Installation complete! Start using Evolution v3.1.0.**
