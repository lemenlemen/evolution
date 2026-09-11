---
name: evolution-sync
version: 4.1.6
description: Evolution 增量同步命令。执行 evolution-export.py 导出新增对话，提取知识并更新知识库。
disable-model-invocation: true
---

# 同步命令

## 命令

| 命令 | 用途 |
|------|------|
| `/evolution` | 执行完整同步（增量） |

> 仅 `/evolution` 一个命令。旧文档中的 `/kb-sync`、`/growth-sync`、`/alignment-sync`
> 是从未注册的幻影命令（无对应定义文件），已废弃移除——局部同步需求统一由
> `/evolution` 承担。

## 执行方式

1. 主 agent 触发 **sub agent**
2. Sub agent 执行 `python .claude/skills/evolution/evolution-export.py --mode incremental` 导出当前项目的新增对话
   - **禁止手动 glob `~/.claude/projects/`**
   - 脚本返回 `status != success` 且非 `partial` 必须停止并报告
   - 脚本返回 `status=partial` 必须向主 agent 报告 warnings 后继续
   - 输出包含 `batch_id` 与 `pending_batches`；可用 `python .claude/skills/evolution/evolution-export.py --mode status` 查询 pending_batches（未提交批次高亮）
   - **注意**：导出会包含触发时刻前已落盘的所有条目（含当前会话）。如需排除当前会话，请手动过滤。
3. Sub agent 逐 chunk 提取关键事实与踩坑记录，更新知识库，新条目标记 `[D]`
4. Sub agent 执行 `python .claude/skills/evolution/evolution-export.py --mode commit --batch-id <batch_id>` 确认批次入库
   - 返回 receipt（含 `receipt_hash`）；重复 commit 同一批次幂等，返回已有 receipt
5. Sub agent 返回摘要给主 agent：新增会话数、新增事实数、新增踩坑数、状态更新数，**必须包含 receipt**（`batch_id` + `receipt_hash`）
6. 主 agent 检查摘要中是否有 receipt，无则判定同步未完成

## 路径锚定说明

> **注意**：以下命令中的相对路径（脚本路径、`--project-path`、`--output` 默认值）
> 不依赖调用方 cwd——`evolution-export.py` 基于自身位置
> （`Path(__file__).resolve().parents[3]`）解析项目根，未显式传入 `--project-path`
> 时默认使用该根目录，`--output` 默认值同样锚定为 `<项目根>/.evolution/chunks`
> （M1 E4 已实施代码修改；设计定案见 docsV4 DESIGN_V4.0.0 §14.4 F-6）。
> 如需覆盖，显式传入绝对路径即可。

## 退出码协议

- `0 = success / partial`（用返回 JSON 的 `status` 字段区分：`status=partial` 表示完成但
  有数据质量警告，sub agent 必须把 `warnings` 转述给主 agent）
- `1 = failed`（中止，sub agent 必须停止并报告）

> `commit` / `start` / `analyze-failed` 模式按返回 JSON 的 `status` 字段判定 0/1；
> `partial` 不影响退出码（历史文档中"2=partial"的说法已作废）。

## 详细规则

- 写入规则：见 [../rules/write.md](../rules/write.md)
- 读取规则：见 [../rules/read.md](../rules/read.md)
- 去重规则：见 [../rules/dedup.md](../rules/dedup.md)
