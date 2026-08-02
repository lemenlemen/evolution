---
name: evolution-init
version: 3.7.0
description: Evolution 系统初始化命令。首次使用或知识库被清空后运行，调用 evolution-export.py 导出全部历史对话，生成初始知识库。
disable-model-invocation: true
---

## 命令

```bash
/evolution-init
```

## 执行方式

1. 主 agent 触发 **sub agent**
2. Sub agent 执行 `python .claude/skills/evolution/evolution-export.py --mode full` 导出当前项目的全部历史对话
   - **禁止手动 glob `~/.claude/projects/`**
   - 脚本返回 `status != success` 必须停止并报告
   - 不得绕过脚本，不得回退到手动读取
3. 逐 chunk 提取关键事实与踩坑记录
4. 生成初始知识库，所有条目标记 `[D]`
5. 返回摘要：分析会话数、提取事实数、踩坑数、状态更新数

## 使用场景

- **首次安装 Evolution 后**
- **知识库被清空后**
- **需要重新建立知识库时**

## 完成标准

- ✅ `evolution/knowledge-base/` 目录已创建
- ✅ `kb-index.md` 已生成（<200 行）
- ✅ 所有新条目标记为 `[D]`
- ✅ 返回摘要包含：分析会话数、提取事实数、踩坑数、状态更新数

## 详细规则

- 写入规则：见 [../rules/write.md](../rules/write.md)
- 读取规则：见 [../rules/read.md](../rules/read.md)
- 去重规则：见 [../rules/dedup.md](../rules/dedup.md)
