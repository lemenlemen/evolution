---
name: evolution-sync
version: 3.8.0
---

# 同步命令

## 命令

| 命令 | 用途 |
|------|------|
| `/evolution` | 执行完整同步 |
| `/kb-sync` | 只同步知识库 |
| `/growth-sync` | 只生成学习笔记 |
| `/alignment-sync` | 只检查对齐项 |

## 执行方式

1. 主 agent 触发 **sub agent**
2. Sub agent 执行 `python .claude/skills/evolution/evolution-export.py --mode incremental` 导出当前项目的新增对话
   - **禁止手动 glob `~/.claude/projects/`**
   - 脚本返回 `status != success` 必须停止并报告
3. 逐 chunk 提取关键事实与踩坑记录
4. 更新知识库，新条目标记 `[D]`
5. 返回摘要：新增会话数、新增事实数、新增踩坑数、状态更新数

## 详细规则

- 写入规则：见 [../rules/write.md](../rules/write.md)
- 读取规则：见 [../rules/read.md](../rules/read.md)
- 去重规则：见 [../rules/dedup.md](../rules/dedup.md)
