# Evolution

> **人机共生进化系统** —— 让 AI 和人类在协作中共同成长

**版本**：v4.1.6（2026-09-11）

🌐 **语言 / Language**: [中文](README.zh-CN.md) | [English](README.md)

![Evolution Banner](https://img.shields.io/badge/Evolution-Human--AI_Symbiosis-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Claude Code](https://img.shields.io/badge/Claude_Code-Skill-purple)
![Version](https://img.shields.io/badge/version-4.1.6-blue)

---

## 为什么做这个

**痛点一：AI 的"失忆症"。** 长程任务中，AI 会忘记你告诉过它的关键信息，反复犯同一个错误，甚至把它自己早先的错误当成事实重新喂回上下文。

**痛点二：人类没有成长。** 经过 N 轮来回沟通，用户最后只剩下"提需求"和"验收"两个角色。什么都没学到，下次任务还是从原地开始。

Evolution 是一个在后台运行的项目级知识库：让 AI 记住该记住的，也让人在协作过程中真正学到东西。

---

## 功能

- 自动从对话历史中提取关键知识
- 知识库渐进式增长 —— AI 越用越聪明
- 三级状态标记（`[D]` / `[V]` / `[X]`），人工审核把关
- 双游标 + 批次 commit 协议 —— 防止数据丢失
- 完整性校验（sha256）、原子写入、三级恢复链
- 流式导出 + 全局时间排序（支持多 session 历史）

---

## 快速开始

```bash
# 首次初始化（分析全部历史对话）
/evolution-init

# 日常增量同步
/evolution
```

安装方式：把 `.claude/skills/evolution/` 和 `evolution/` 复制到你的项目根目录。
详见[安装指南](docs/INSTALLATION_GUIDE.zh-CN.md)。

---

## 运行机制

```
用户执行 /evolution
        │
        ▼
主 agent 触发 sub agent（后台执行）
        │
        ▼
Sub agent：
  1. 调用 evolution-export.py → 解析 JSONL 历史为分页 chunk
  2. 逐 chunk 分析，提取知识
  3. 与已有知识库去重
  4. 以 [D]（草稿）写入条目，然后 commit 批次
        │
        ▼
主 agent 显示一行摘要
```

| 命令 | 用途 |
|------|------|
| `/evolution-init` | 从全部历史初始化知识库 |
| `/evolution` | 增量同步新对话 |

---

## 文档

完整双语文档位于 [`docs/`](docs/)。

### 入门
1. [项目背景](docs/PROJECT_BACKGROUND.zh-CN.md) —— 系统背后的痛点
2. [安装指南](docs/INSTALLATION_GUIDE.zh-CN.md) —— 安装与验证
3. [版本历史](docs/VERSION_HISTORY.zh-CN.md) —— 逐版本变更

### 设计
- [V4 设计文档](docs/v4/DESIGN_V4.0.0.zh-CN.md) —— 当前架构（总纲）
- [V4 同步引擎层设计](docs/v4/design-v4-engine.zh-CN.md) —— 数据完整性与健壮性
- [V4 知识管理层设计](docs/v4/design-v4-knowledge.zh-CN.md) —— 知识质量（历史稿，已回退）
- [V3 系统规则](docs/EVOLUTION_RULES_AND_LOGIC_V3.zh-CN.md) —— V3 时代规则与逻辑
- [导出和分析设计](docs/EXPORT_AND_ANALYSIS_DESIGN.zh-CN.md) —— 对话导出流水线
- [对抗性审核](docs/ADVERSARIAL_AUDIT_v3.9.0.md) —— 驱动 V4 的那次审核（仅中文）

### 归档
V1/V2 时代文档保存在 [`docs/archive/`](docs/archive/)。

---

## 隐私

知识库文件会随仓库公开，写入前请自查敏感信息。

原始对话历史（`.evolution/chunks/`、`sync-state.json`）已被 `.gitignore` 排除，不会上传。

每次发布前，对全仓库执行隐私扫描，检查六类标识符：雇主/个人姓名、本地完整路径（四种形态：反斜杠、大写盘符正斜杠、WSL 小写盘符、裸父目录）、项目 hash、会话 UUID、已知 sha256 前缀、真实状态快照值。

---

## 知识库结构

```
evolution/knowledge-base/
├── kb-index.md              # 索引（入口，<200 行）
├── facts.md                 # 关键事实
├── pitfalls.md              # 踩坑记录
├── state.md                 # 当前状态
├── growth-notes.md          # 学习笔记
├── prompt-improvements.md   # Prompt 改进建议
├── alignment.md             # 对齐清单
└── decisions.md             # 决策记录
```

---

## 许可

MIT —— 详见 [LICENSE](LICENSE)。
