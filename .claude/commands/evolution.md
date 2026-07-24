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
- **内容**：包括所有代码片段、错误信息、技术细节、决策讨论
- **不删除**：任何内容，保持原始对话的完整性

### 2. 创建临时目录
```bash
mkdir -p .claude/.tmp/
```

### 3. 派出 Knowledge Base Sub-Agent

使用 Agent tool，参数：
- `subagent_type: "general-purpose"`
- `run_in_background: true`
- `description: "evolution knowledge-base sync"`
- `prompt: |`
  ```
  你是 Knowledge Base Agent。
  
  ## 任务
  读取对话导出文件，提取关键信息写入 memory 文件。
  
  ## 输入
  - 对话导出文件：`~/.claude/projects/<your-project-name>/.tmp/conv-export-{timestamp}.md`
  - 现有 memory 文件：`~/.claude/projects/<your-project-name>/memory/`
  
  ## 处理
  1. 读取对话导出文件（完整内容，不要压缩）
  2. 提取关键事实（环境配置、技术决策、依赖关系）→ 追加到 facts.md
  3. 提取踩坑记录（重复错误、新发现的坑、解决方案）→ 追加到 pitfalls.md
  4. 更新当前状态（任务进度、待确认项）→ 追加到 state.md
  5. 更新索引 → 更新 kb-index.md 的概览表格
  
  ## 去重
  - 检查已有记录，避免重复
  - 如果信息已存在，更新时间戳而不是新增
  
  ## 输出
  只返回 1 行摘要，格式：
  `KB: +N facts, +M pitfalls, +K state updates`
  ```

### 4. 派出 Growth Sub-Agent

使用 Agent tool，参数：
- `subagent_type: "general-purpose"`
- `run_in_background: true`
- `description: "evolution growth sync"`
- `prompt: |`
  ```
  你是 Growth Agent。
  
  ## 任务
  读取对话导出文件，生成学习笔记和 Prompt 改进建议。
  
  ## 输入
  - 对话导出文件：`~/.claude/projects/<your-project-name>/.tmp/conv-export-{timestamp}.md`
  - 现有文件：`evolution-manual/knowledge-base/`
  
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

### 5. 派出 Alignment Sub-Agent

使用 Agent tool，参数：
- `subagent_type: "general-purpose"`
- `run_in_background: true`
- `description: "evolution alignment sync"`
- `prompt: |`
  ```
  你是 Alignment Agent。
  
  ## 任务
  读取对话导出文件，识别需要对齐的项目。
  
  ## 输入
  - 对话导出文件：`~/.claude/projects/<your-project-name>/.tmp/conv-export-{timestamp}.md`
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

### 6. 清理临时文件
```bash
rm -rf .claude/.tmp/
```

### 7. 汇报结果

将三个 sub-agent 的摘要合并，输出给用户：

```
Evolution 同步完成：
- KB: +N facts, +M pitfalls, +K state updates
- Growth: +N notes, +M prompt tips
- Alignment: +N audits, +M decisions
```

## 关键约束

1. **不压缩对话**：传递给 sub-agent 的是完整对话，不是摘要
2. **Sub-agent 独立执行**：主 agent 不读取 memory 文件，不执行提取工作
3. **只报告摘要**：主 agent 只展示 sub-agent 返回的摘要，不展示执行细节
4. **失败处理**：如果某个 sub-agent 失败，报告错误，其他结果正常显示

## 文件位置

- 临时文件：`.claude/.tmp/`
- Knowledge Base 文件：`evolution-manual/knowledge-base/`
