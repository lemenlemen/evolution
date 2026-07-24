# Alignment Agent - 检查对齐

执行 Alignment Agent，检查需要对齐的项目。

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

### 3. 派出 Alignment Sub-Agent

使用 Agent tool，参数：
- `subagent_type: "general-purpose"`
- `run_in_background: true`
- `description: "alignment sync"`
- `prompt: |`
  ```
  你是 Alignment Agent。
  
  ## 任务
  读取对话导出文件，识别需要对齐的项目。
  
  ## 输入
  - 对话导出文件：`.claude/.tmp/conv-export-{timestamp}.md`
  - 现有文件：`evolution-manual/knowledge-base/`
  
  ## 处理
  1. 读取对话导出文件（完整内容）
  2. 识别需要人类验收的项目 → 追加到 alignment.md
  3. 识别不确定或边界情况 → 追加到 alignment.md
  4. 识别需要决策的点 → 追加到 decisions.md
  
  ## 输出
  只返回 1 行摘要，格式：
  `Alignment: +N audits, +M decisions`
  ```

### 4. 清理临时文件
```bash
rm -rf .claude/.tmp/
```

### 5. 汇报结果

输出 sub-agent 返回的摘要：
```
Alignment 同步完成：
- +N audits, +M decisions
```

## 关键约束

1. **不压缩对话**：传递给 sub-agent 的是完整对话
2. **Sub-agent 独立执行**：主 agent 不执行检查
3. **只报告摘要**：不展示执行细节

## 文件位置

- 临时文件：`.claude/.tmp/`
- Knowledge Base 文件：`evolution-manual/knowledge-base/`
