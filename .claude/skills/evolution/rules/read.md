# 读取规则

## 渐进式读取

**重要**：不要一次性读取所有文件！遵循渐进式披露原则。

### 步骤 1：读取索引

读取 `evolution/knowledge-base/kb-index.md`

### 步骤 2：判断需求

基于索引中的分类摘要，判断当前任务需要哪些信息：

- 如果用户问环境配置 → 读取 `facts.md`
- 如果用户问历史错误 → 读取 `pitfalls.md`
- 如果需要更新状态 → 读取 `state.md`
- 如果用户问学习知识 → 读取 `growth-notes.md`
- 如果需要验收检查 → 读取 `alignment.md`
- 如果需要决策记录 → 读取 `decisions.md`

### 步骤 3：按需读取

**只读取相关的 1-2 个文件**，不要全量加载所有文件

## 配置文件

- 参数配置：见 [../config.yaml](../config.yaml)
