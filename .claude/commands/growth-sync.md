# Growth Agent - 生成学习笔记

执行 Growth Agent，生成学习笔记和 Prompt 改进建议。

## 执行架构

使用 Agent tool 派出 sub-agent，主 agent 只负责调度和汇报。

## 执行步骤

### 1. 导出对话
**手动触发**：将当前 Session 的**所有对话**完整导出
**自动触发**：将最近 10 轮对话完整导出（增量同步）

- 路径：`.claude/.tmp/conv-export-{timestamp}.md`
- **格式**：保留完整的用户消息和 AI 回复，不做任何压缩或摘要

### 2. 创建临时目录
```bash
mkdir -p .claude/.tmp/
```

### 3. 派出 Growth Sub-Agent

使用 Agent tool，参数：
- `subagent_type: "general-purpose"`
- `run_in_background: true`
- `description: "growth sync"`
- `prompt: |`
  ```
  你是 Growth Agent。
  
  ## 任务
  读取对话导出文件，生成学习笔记和 Prompt 改进建议。
  
  ## 输入
  - 对话导出文件：.claude/.tmp/conv-export-{timestamp}.md
  - 现有文件：evolution-manual/knowledge-base/
  
  ## 处理
  1. 读取对话导出文件（完整内容）
  2. 识别教学机会（用户明确询问的技术概念、反复出现的概念）
  3. 为每个教学点生成学习笔记 → 追加到 growth-notes.md
     - 一句话解释
     - 为什么重要
     - 生活化类比
     - 控制在 300 字以内
  4. 分析用户的提问方式 → 追加到 prompt-improvements.md
  
  ## 输出
  只返回 1 行摘要，格式：
  `Growth: +N notes, +M prompt tips`
  ```

### 4. 清理临时文件
```bash
rm -rf .claude/.tmp/
```

### 5. 汇报结果

输出 sub-agent 返回的摘要：
```
Growth 同步完成：
- +N notes, +M prompt tips
```

## 关键约束

1. **不压缩对话**：传递给 sub-agent 的是完整对话
2. **Sub-agent 独立执行**：主 agent 不执行提取工作
3. **只报告摘要**：不展示执行细节

## 文件位置

- 临时文件：`.claude/.tmp/`
- Memory 文件：`evolution-manual/knowledge-base/`
