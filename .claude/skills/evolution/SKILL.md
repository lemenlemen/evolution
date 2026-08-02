---
name: evolution
version: 3.8.0
description: 人机共生进化系统，管理项目知识库。当用户询问历史知识（环境配置、技术决策）、检测到重复错误、需执行知识同步、或用户输入 /evolution（含 init）时触发。所有操作由 sub agent 后台执行，减少主会话污染。
disable-model-invocation: false
---

## 命令

| 命令 | 用途 | 说明 |
|------|------|------|
| `/evolution-init` | 初始化知识库 | [init.md](commands/init.md) |
| `/evolution` | 增量同步 | [sync.md](commands/sync.md) |
| `/kb-sync` | 只同步知识库 | [sync.md](commands/sync.md) |
| `/growth-sync` | 只生成学习笔记 | [sync.md](commands/sync.md) |
| `/alignment-sync` | 只检查对齐项 | [sync.md](commands/sync.md) |

## 规则

| 规则 | 说明 |
|------|------|
| 写入 | [write.md](rules/write.md) |
| 读取 | [read.md](rules/read.md) |
| 去重 | [dedup.md](rules/dedup.md) |

## 知识库

`evolution/knowledge-base/`，入口 `kb-index.md`（<200 行）。

配置见 [config.yaml](config.yaml) · 导出机制见 [sync.md](commands/sync.md)

## 核心原则

1. **与 Auto Memory 分离** - 不污染 Claude Code 的 Auto Memory 系统
2. **项目级存储** - 存储在 `evolution/knowledge-base/`
3. **按需加载** - 通过索引引导 AI 按需读取，避免上下文污染
4. **人工审核** - 所有内容必须人工核对，人类也要读取文档学习
