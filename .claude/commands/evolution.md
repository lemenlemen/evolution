# Evolution 系统 - 完整同步

执行 Evolution 系统的所有后台代理，同步当前对话的关键信息。

## 执行架构

使用 Agent tool 派出真正的 sub-agent，主 agent 只负责调度和汇报。

## 执行步骤

### 1. 导出全量对话
将当前 Session 的**所有对话**完整导出到临时文件：
- 路径：`.claude/.tmp/conv-export-{timestamp}.md`
- **范围**：从第 1 轮到当前轮，全量导出（不是最近 5 轮）
- **格式**：保留完整的用户消息和 AI 回复，不做任何压缩或摘要

### 2. 创建临时目录
```bash
mkdir -p .claude/.tmp/
```

### 3. 派出 Knowledge Base Sub-Agent
使用 Agent tool 启动 sub-agent，读取对话导出文件，提取关键信息写入：
- facts.md - 关键事实
- pitfalls.md - 踩坑记录
- state.md - 当前状态
- kb-index.md - 更新索引

### 4. 派出 Growth Sub-Agent
生成学习笔记和 Prompt 改进建议：
- growth-notes.md - 学习笔记
- prompt-improvements.md - Prompt 改进

### 5. 派出 Alignment Sub-Agent
识别需要对齐的项目：
- alignment.md - 对齐清单
- decisions.md - 决策记录

### 6. 清理临时文件
```bash
rm -rf .claude/.tmp/
```

### 7. 汇报结果
```
Evolution 同步完成：
- KB: +N facts, +M pitfalls, +K state updates
- Growth: +N notes, +M prompt tips
- Alignment: +N audits, +M decisions
```

## 文件位置

- 临时文件：`.claude/.tmp/`
- Knowledge Base 文件：`evolution-manual/knowledge-base/`
