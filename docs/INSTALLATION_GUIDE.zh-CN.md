# Evolution 安装指南

> **版本**：4.1.6（2026-09-11）  
> **适用平台**：Windows / macOS / Linux

> **版本历史**：详见 [`VERSION_HISTORY.md`](./VERSION_HISTORY.md)

---

## 1. 前置条件

### 1.1 系统要求

| 项目 | 要求 |
|------|------|
| **Claude Code** | 最新版本（支持 Skill 系统） |
| **Python** | 3.9+（用于 `evolution-export.py` 导出对话历史） |
| **操作系统** | Windows 10+ / macOS 10.15+ / Ubuntu 18.04+ |
| **Shell** | Git Bash / Zsh / Bash |

### 1.2 验证 Claude Code 版本

```bash
claude --version
```

**预期输出**：
```
claude version 2.1.x 或更高
```

### 1.3 验证 Python 环境

```bash
python --version
```

**预期输出**：
```
Python 3.9.x 或更高
```

> Evolution 使用 `evolution-export.py` 脚本导出对话历史，Python 为必装依赖。

---

## 2. 安装步骤

### 2.1 创建 Skill 目录

```bash
# 进入项目根目录
cd <your-project>

# 创建 Skill 目录
mkdir -p .claude/skills/evolution
```

### 2.2 创建 Skill 文件（模块化结构）

Evolution v3.4.0+ 已模块化，需创建以下完整结构：

```
.claude/skills/evolution/
├── SKILL.md              # 入口文件（命令与规则索引）
├── config.yaml           # 统一配置（分页、token 估算、状态标记）
├── evolution-export.py   # 对话导出脚本（Python）
├── commands/
│   ├── init.md           # /evolution-init 初始化命令
│   └── sync.md           # /evolution 增量同步命令
├── rules/
│   ├── write.md          # 写入规则
│   ├── read.md           # 读取规则
│   └── dedup.md          # 去重规则
└── tests/
    └── test_sha256_invariant.py  # sha256 不变量回归测试（可选）
```

项目根目录另需命令注册文件（供 `/evolution-init` 斜杠命令发现）：

```
.claude/
├── commands/
│   └── evolution-init.md  # /evolution-init 命令注册（引用 skills/evolution/commands/init.md）
└── skills/
    └── evolution/         # 见上方目录树
```

从 GitHub 复制全部文件：

```bash
# 创建子目录
mkdir -p .claude/skills/evolution/commands
mkdir -p .claude/skills/evolution/rules

# 下载入口文件与配置
curl -o .claude/skills/evolution/SKILL.md https://raw.githubusercontent.com/lemenlemen/evolution/main/.claude/skills/evolution/SKILL.md
curl -o .claude/skills/evolution/config.yaml https://raw.githubusercontent.com/lemenlemen/evolution/main/.claude/skills/evolution/config.yaml
curl -o .claude/skills/evolution/evolution-export.py https://raw.githubusercontent.com/lemenlemen/evolution/main/.claude/skills/evolution/evolution-export.py

# 下载命令文件
curl -o .claude/skills/evolution/commands/init.md https://raw.githubusercontent.com/lemenlemen/evolution/main/.claude/skills/evolution/commands/init.md
curl -o .claude/skills/evolution/commands/sync.md https://raw.githubusercontent.com/lemenlemen/evolution/main/.claude/skills/evolution/commands/sync.md

# 下载规则文件
curl -o .claude/skills/evolution/rules/write.md https://raw.githubusercontent.com/lemenlemen/evolution/main/.claude/skills/evolution/rules/write.md
curl -o .claude/skills/evolution/rules/read.md https://raw.githubusercontent.com/lemenlemen/evolution/main/.claude/skills/evolution/rules/read.md
curl -o .claude/skills/evolution/rules/dedup.md https://raw.githubusercontent.com/lemenlemen/evolution/main/.claude/skills/evolution/rules/dedup.md

# 下载命令注册文件（/evolution-init 斜杠命令发现用）
mkdir -p .claude/commands
curl -o .claude/commands/evolution-init.md https://raw.githubusercontent.com/lemenlemen/evolution/main/.claude/commands/evolution-init.md

# 下载测试文件（可选）
mkdir -p .claude/skills/evolution/tests
curl -o .claude/skills/evolution/tests/test_sha256_invariant.py https://raw.githubusercontent.com/lemenlemen/evolution/main/.claude/skills/evolution/tests/test_sha256_invariant.py
```

> 也可直接克隆仓库后复制 `.claude/skills/evolution/` 整个目录。

### 2.3 创建知识库目录

```bash
# 创建知识库目录
mkdir -p evolution/knowledge-base
```

### 2.4 创建知识库模板文件

复制以下 8 个文件到 `evolution/knowledge-base/`：

- `kb-index.md` - 索引文件
- `facts.md` - 关键事实
- `pitfalls.md` - 踩坑记录
- `state.md` - 当前状态
- `growth-notes.md` - 学习笔记
- `prompt-improvements.md` - Prompt 改进
- `alignment.md` - 对齐清单
- `decisions.md` - 决策记录

模板文件参考：[knowledge-base](https://github.com/lemenlemen/evolution/tree/main/evolution/knowledge-base)

---

## 3. 验证安装

### 3.1 检查目录结构

```bash
# 查看 Skill 文件（模块化结构）
ls -R .claude/skills/evolution/

# 应该显示：
# SKILL.md
# config.yaml
# evolution-export.py
# commands/init.md
# commands/sync.md
# rules/write.md
# rules/read.md
# rules/dedup.md
# tests/test_sha256_invariant.py   # 可选（回归测试）

# 查看命令注册文件
ls .claude/commands/

# 应该显示：
# evolution-init.md

# 查看知识库文件
ls -la evolution/knowledge-base/

# 应该显示 8 个文件：
# kb-index.md
# facts.md
# pitfalls.md
# state.md
# growth-notes.md
# prompt-improvements.md
# alignment.md
# decisions.md
```

### 3.2 验证 Skill 加载

```
输入：/context
```

**观察 Skills 部分**：

**预期结果**：
```
Project
── evolution: < 50 tokens    ← 应该显示
```

### 3.3 测试初始化命令

```
输入：/evolution-init
```

> `/evolution` 是增量同步命令，首次安装后应使用 `/evolution-init` 初始化知识库。

**预期行为**：
```
AI: 我先触发 sub agent 导出全部历史主会话对话...
    [执行 evolution-export.py --mode full]
AI: 导出完成，开始逐 chunk 提取关键事实...
    [分析对话历史]
AI: 初始化完成！
    分析会话数：N，提取事实数：N，踩坑数：N
```

---

## 4. 故障排查

### 问题 1：Skill 不显示

**可能原因**：
- frontmatter 格式错误
- 目录结构不对

**解决**：
```bash
# 检查目录结构
ls -R .claude/skills/evolution/

# 应该显示完整的模块化结构：
# SKILL.md, config.yaml, evolution-export.py
# commands/init.md, commands/sync.md
# rules/write.md, rules/read.md, rules/dedup.md
# tests/test_sha256_invariant.py   # 可选（回归测试）

# 检查命令注册文件
ls .claude/commands/
# 应该显示：evolution-init.md

# 检查 frontmatter 格式
head -10 .claude/skills/evolution/SKILL.md

# 应该显示：
# ---
# name: evolution
# description: ...
# ---
```

### 问题 2：AI 全量读取

**可能原因**：
- SKILL.md 中没有明确的渐进式读取指令

**解决**：
- 检查 SKILL.md 是否有"渐进式读取规则"部分
- 确认指令明确说"不要一次性读取所有文件"

---

## 5. 升级指南

### 5.1 从 V2 升级到 V3

> V3 将知识库目录从 `evolution-manual/` 改为 `evolution/`。
> 迁移采用**整体重命名**（与 [VERSION_HISTORY.md](./VERSION_HISTORY.md) v3.0.0 迁移指南一致），
> 全部原内容随目录一起保留，无需单独备份；开始前请确认目标目录不存在。

**步骤**：

1. **前置确认**
   ```bash
   # 应看到 evolution-manual/，且不存在 evolution/
   ls -d evolution-manual evolution 2>/dev/null

   # 若 evolution/ 已存在（例如曾部分迁移），先把旧树备份到项目根目录再继续：
   # cp -r evolution-manual/knowledge-base ./knowledge-base.v2.backup.$(date +%Y%m%d)
   ```

2. **整体重命名迁移**
   ```bash
   # 整体重命名：知识库文件随目录一起迁移，天然保留原内容
   mv evolution-manual evolution
   ```

   迁移后知识库位于 `evolution/knowledge-base/`，与 V3 路径一致。
   历史遗留的 `evolution/agents/` 子目录是 V2 产物，可保留作参考或手工删除。

3. **修正知识库内旧路径（可选但推荐）**

   V2 时代的 `kb-index.md` / `facts.md` 可能仍自指 `evolution-manual/` 旧路径，
   手工将其中出现的 `evolution-manual/` 替换为 `evolution/`。

4. **验证**
   ```bash
   # 知识库文件应已在新位置
   ls evolution/knowledge-base/

   # 按照第 3 节验证安装
   ```

---

## 6. 卸载指南

> **以下所有命令必须在项目根目录（即包含 `.claude/` 和 `evolution/` 的目录）执行。**
> 执行前先 `pwd` 确认当前位置，避免误删其他目录。

### 6.0 卸载前备份（强烈建议）

知识库默认不在版本控制内，删除后无法恢复。先备份：

```bash
# 确认在项目根目录
pwd

# 备份知识库到项目根目录之外的位置
cp -r evolution/knowledge-base ~/evolution-kb-backup-$(date +%Y%m%d)

# 确认备份成功后再继续
ls ~/evolution-kb-backup-*
```

### 6.1 完全卸载

```bash
# 1) 先预览将要删除的内容（不实际删除）
find .claude/skills/evolution evolution/knowledge-base -type f

# 2) 删除 Skill
rm -r .claude/skills/evolution

# 3) 删除知识库（精确路径，只删 knowledge-base，不动项目源码）
rm -r evolution/knowledge-base

# 4) 若 evolution/ 下已无内容，可移除空目录；仍有其他文件则保留
rmdir evolution 2>/dev/null || echo "evolution/ 非空，已保留"

# 5) 清理导出缓存与同步状态（可选，含全部 chunk 文件）
rm -r .evolution
```

> ⚠️ **不要执行 `rm -rf evolution`**：
> - 本仓库项目根目录本身可能就叫 `evolution`，在错误的目录层级执行会删掉整个项目；
> - 即使在项目根执行，也会连同 `evolution/` 下非知识库内容一起删除。
> 始终使用上面的精确路径 `evolution/knowledge-base`。
>
> 使用 `rm -r`（不带 `-f`）时，遇到写保护文件会提示确认，这是预期的保护行为。

### 6.2 保留知识库

如果只想卸载 Skill，保留知识库：

```bash
# 只删除 Skill
rm -r .claude/skills/evolution

# 保留知识库
# evolution/knowledge-base/ 目录保持不变
```

---

## 7. 最佳实践

### 7.1 定期清理

```bash
# 检查知识库大小
du -sh evolution/knowledge-base/

# 如果过大，考虑归档旧条目
```

### 7.2 版本控制

```bash
# 将知识库纳入版本控制
git add evolution/knowledge-base/
git commit -m "chore: update knowledge base"
```

### 7.3 团队共享

```bash
# 将 Skill 文件提交到仓库
git add .claude/skills/evolution/
git commit -m "feat: add evolution skill"

# 团队成员克隆后自动获得
```

---

## 8. 参考资料

### 8.1 官方文档

- [Extend Claude with skills](https://code.claude.com/docs/en/skills)
- [How Claude remembers your project](https://code.claude.com/docs/en/memory)
- [Commands](https://code.claude.com/docs/en/commands)

### 8.2 项目文档

- [设计文档](./DESIGN_V3.1.0.md)
- [项目背景](./PROJECT_BACKGROUND.md)
- [版本历史](./VERSION_HISTORY.md)

---

**安装完成！开始使用 Evolution v4.1.6。**
