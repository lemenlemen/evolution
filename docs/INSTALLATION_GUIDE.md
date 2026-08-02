# Evolution Installation Guide

🌐 **Language / 语言**: [English](INSTALLATION_GUIDE.md) | [中文](INSTALLATION_GUIDE.zh-CN.md)

> **Version**: 3.8.0 (2026-08-01)
> **Supported platforms**: Windows / macOS / Linux

> **Version history**: See [`VERSION_HISTORY.md`](./VERSION_HISTORY.md)

---

## 1. Prerequisites

### 1.1 System Requirements

| Item | Requirement |
|------|-------------|
| **Claude Code** | Latest version (Skill system support) |
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

Create a `SKILL.md` file under `.claude/skills/evolution/`, refer to:
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

Template file reference: [knowledge-base](https://github.com/lemenlemen/evolution/tree/main/evolution/knowledge-base)

---

## 3. Verify Installation

### 3.1 Check Directory Structure

```bash
# Check Skill files
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
Enter: /context
```

**Observe the Skills section**:

**Expected result**:
```
Project
── evolution: < 50 tokens    ← Should be displayed
```

### 3.3 Test Manual Trigger

```
Enter: /evolution
```

**Expected behavior**:
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

**Possible causes**:
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

### Problem 2: AI Reads All Files at Once

**Possible causes**:
- No explicit progressive reading instructions in SKILL.md

**Solution**:
- Check if SKILL.md has a "progressive reading rules" section
- Confirm the instructions explicitly say "do not read all files at once"

### Problem 3: Auto-Trigger Not Working

**Possible causes**:
- `disable-model-invocation: true` (should be `false`)
- `description` trigger keywords are unclear

**Solution**:
- Check that frontmatter has `disable-model-invocation: false`
- Improve the `description` field trigger keywords

---

## 5. Upgrade Guide

### 5.1 Upgrading from V2 to V3

**Steps**:

1. **Backup V2 files**
   ```bash
   # Backup the old knowledge base
   cp -r evolution-manual/knowledge-base evolution-manual/knowledge-base.v2.backup
   ```

2. **Migrate knowledge base**
   ```bash
   # Move files from old directory to new directory
   mv evolution-manual/knowledge-base/*.md evolution/knowledge-base/
   ```

3. **Delete old directory**
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

## 6. Uninstall Guide

### 6.1 Full Uninstall

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

**Installation complete! Start using Evolution v3.8.0.**
