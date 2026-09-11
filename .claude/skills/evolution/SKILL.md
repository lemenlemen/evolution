---
name: evolution
version: 4.1.6
description: 人机共生进化系统，管理项目知识库。当用户询问历史知识（环境配置、技术决策）、检测到重复错误、需执行知识同步、或用户输入 /evolution（含 init）时触发。所有操作由 sub agent 后台执行，减少主会话污染。
disable-model-invocation: false
---

## 命令

| 命令 | 用途 | 说明 |
|------|------|------|
| `/evolution-init` | 初始化知识库 | [init.md](commands/init.md) |
| `/evolution` | 增量同步 | [sync.md](commands/sync.md) |

> 仅以上命令。旧文档中的 `/kb-sync`、`/growth-sync`、`/alignment-sync` 是从未注册的幻影命令（无对应定义文件），已废弃移除——局部同步需求统一由 `/evolution` 承担。

## 规则

| 规则 | 说明 |
|------|------|
| 写入 | [write.md](rules/write.md) |
| 读取 | [read.md](rules/read.md) |
| 去重 | [dedup.md](rules/dedup.md) |
| 批次 commit | 导出产生的批次必须 `--mode commit` 确认（返回 receipt）才算完成；sub agent 摘要缺 receipt，主 agent 判定同步/初始化未完成 |

## 知识库

`evolution/knowledge-base/`，入口 `kb-index.md`（<200 行）。

配置见 [config.yaml](config.yaml) · 导出机制见 [sync.md](commands/sync.md)

## 核心原则

1. **与 Auto Memory 分离** - 不污染 Claude Code 的 Auto Memory 系统
2. **项目级存储** - 存储在 `evolution/knowledge-base/`
3. **按需加载** - 通过索引引导 AI 按需读取，避免上下文污染
4. **人工审核** - 所有内容必须人工核对，人类也要读取文档学习
