# Evolution 系统（手动触发）

> **Evolution** 是一个人机共生进化系统，让 AI 和人类在协作中共同成长。

本系统使用 **Knowledge Base（知识库）** 存储关键信息，与 Claude Code 的 Auto Memory 系统完全独立。

## 知识库架构

```
evolution-manual/knowledge-base/
├── kb-index.md            # 索引文件（AI 对话开始时读取）
├── facts.md               # 关键事实详情
├── pitfalls.md            # 踩坑记录详情
├── state.md               # 当前状态详情
├── growth-notes.md        # 学习笔记
├── prompt-improvements.md # Prompt 改进建议
├── alignment.md           # 对齐清单
└── decisions.md           # 决策记录
```

## 触发方式

### 使用 Slash Commands

```bash
/evolution          # 执行所有三个 Agent
/kb-sync            # 只执行 Knowledge Base Agent
/growth-sync        # 只执行 Growth Agent
/alignment-sync     # 只执行 Alignment Agent
```

### 使用自然语言

```
请执行 Evolution 系统，同步当前对话的关键信息
```

## 后台系统（Sub-agent 模式）

本项目配置了三个后台代理，通过 Agent tool 的 sub-agent 模式运行：
- **人类基本无感**：sub-agent 在后台运行，不阻塞主对话
- **上下文不污染**：文件操作在 sub-agent 中完成
- **错误隔离**：单个 agent 失败不影响其他 agent

## 文件位置

- **Knowledge Base**：`evolution-manual/knowledge-base/`
- **临时文件**：`.claude/.tmp/`

## 触发来源

- **触发来源**：manual
