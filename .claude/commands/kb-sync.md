# Knowledge Base Agent - 同步知识

执行 Knowledge Base Agent，提取当前对话的关键信息。

## 执行架构

使用 Agent tool 派出 sub-agent，主 agent 只负责调度和汇报。

## 执行步骤

### 1. 导出对话
**手动触发**：将当前 Session 的**所有对话**完整导出
**自动触发**：将最近 5 轮对话完整导出（增量同步）

- 路径：`.claude/.tmp/conv-export-{timestamp}.md`
- **格式**：保留完整的用户消息和 AI 回复，不做任何压缩或摘要

### 2. 创建临时目录
```bash
mkdir -p .claude/.tmp/
```

### 3. 派出 Knowledge Base Sub-Agent

使用 Agent tool，参数：
- `subagent_type: "general-purpose"`
- `run_in_background: true`
- `description: "knowledge-base sync"`
- `prompt: |`
  ```
  你是 Knowledge Base Agent。
  
  ## 任务
  读取对话导出文件，提取关键信息写入 memory 文件。
  
  ## 输入
  - 对话导出文件：.claude/.tmp/conv-export-{timestamp}.md
  - 现有 memory 文件：evolution-manual/knowledge-base/
  
  ## 处理
  1. 读取对话导出文件（完整内容，不要压缩）
  2. 提取关键事实（环境配置、技术决策、依赖关系）→ 追加到 facts.md
  3. 提取踩坑记录（重复错误、新发现的坑、解决方案）→ 追加到 pitfalls.md
  4. 更新当前状态（任务进度、待确认项）→ 追加到 state.md
  5. 更新索引 → 更新 MEMORY.md 的概览表格
  
  ## 去重
  - 检查已有记录，避免重复
  - 如果信息已存在，更新时间戳而不是新增
  
  ## 输出
  只返回 1 行摘要，格式：
  `KB: +N facts, +M pitfalls, +K state updates`
  ```

### 4. 清理临时文件
```bash
rm -rf .claude/.tmp/
```

### 5. 汇报结果

输出 sub-agent 返回的摘要：
```
Knowledge Base 同步完成：
- +N facts, +M pitfalls, +K state updates
```

## 关键约束

1. **不压缩对话**：传递给 sub-agent 的是完整对话
2. **Sub-agent 独立执行**：主 agent 不执行提取工作
3. **只报告摘要**：不展示执行细节

## 文件位置

- 临时文件：`.claude/.tmp/`
- Memory 文件：`evolution-manual/knowledge-base/`
