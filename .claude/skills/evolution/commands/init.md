---
name: evolution-init
version: 4.1.6
description: Evolution 系统初始化命令。首次使用或知识库被清空后运行，调用 evolution-export.py 导出全部历史主会话对话，生成初始知识库。
disable-model-invocation: true
---

## 命令

```bash
/evolution-init
```

## 执行方式

> **路径锚定说明**：本命令及下述脚本调用中的相对路径（脚本路径、`--project-path`、
> `--output` 默认值）不依赖调用方 cwd——`evolution-export.py` 基于自身位置解析项目根
> （`project_root = Path(__file__).resolve().parents[3]`），未显式传入 `--project-path`
> 时默认使用该根目录，`--output` 默认值同样锚定为 `<项目根>/.evolution/chunks`
> （M1 E4 已实施代码修改；设计定案见 docsV4 DESIGN_V4.0.0 §14.4 F-6）。
> 如需覆盖，显式传入绝对路径即可。

0. **前置检查**（双信号检测：导出游标 + 知识库本体）
   - 信号一：运行 `python .claude/skills/evolution/evolution-export.py --mode status`
   - 信号二：检查知识库目录是否已有实际内容：
     ```bash
     ls evolution/knowledge-base/*.md 2>/dev/null
     ```
     判断标准（满足任一即视为"已有内容"）：
     - `kb-index.md` 存在，或
     - 任一 `*.md` 文件包含至少一条 `### [D]` / `### [V]` 条目
   - **信号一非 null 或信号二有内容 → 触发确认**：
     - 向用户报告："⚠️ 检测到已有初始化记录（导出游标非空 / 知识库已有条目）。重新导出会覆盖现有 chunk 文件并重置增量游标，知识库文件不会被清空但可能产生重复条目。是否继续？(Y/N)"
     - 等待用户明确确认
     - 用户选择 N → 停止执行
     - 用户选择 Y → 继续执行
   - **两个信号均为空/null 且 sync-state.json 不存在 → 全新安装**：直接继续
   - **异常情况**：sync-state.json 存在但 status 输出异常（解析失败、字段缺失），
     或状态文件存在而知识库为空/反之——按"状态可疑"处理，同样必须走 Y/N 确认，
     不得静默放行

1. 主 agent 触发 **sub agent**
2. Sub agent 执行 `python .claude/skills/evolution/evolution-export.py --mode full` 导出当前项目的全部历史**主会话**对话（subagent 转录默认排除，内容按脚本策略摘要截断）
   - **禁止手动 glob `~/.claude/projects/`**
   - 脚本返回 `status != success` 必须停止并报告
   - **注意**：导出会包含触发时刻前已落盘的所有条目（含当前会话）。如需排除当前会话，请手动过滤。
   - 不得绕过脚本，不得回退到手动读取
3. Sub agent 逐 chunk 提取关键事实与踩坑记录，生成初始知识库，所有条目标记 `[D]`
4. Sub agent 执行 `python .claude/skills/evolution/evolution-export.py --mode commit --batch-id <batch_id>` 确认批次入库
   - 返回 receipt（含 `receipt_hash`）；重复 commit 同一批次幂等，返回已有 receipt
   - **（可选）旧分片清理**：必须在 commit 成功**之后**执行——全量导出的 chunk 命名为
     `chunk-{i:02d}.md`（不带 batch_id），不会自动删除上一轮同名旧分片；确认批次已入库后可运行
     `python .claude/skills/evolution/evolution-export.py --mode cleanup`
     清理旧分片与临时文件（不会删除 sync-state.json 状态文件；cleanup 亦为增量同步的兜底清理手段）。
     commit 前清理会删除本轮待分析的 chunk，禁止提前执行
5. 返回摘要：分析会话数、提取事实数、踩坑数、状态更新数，**必须包含 receipt**（`batch_id` + `receipt_hash`）
6. 主 agent 检查摘要中是否有 receipt，无则判定初始化未完成

## 使用场景

- **首次安装 Evolution 后**
- **知识库被清空后**
- **需要重新建立知识库时**

## 完成标准

- ✅ `evolution/knowledge-base/` 目录已创建
- ✅ `kb-index.md` 已生成（<200 行）
- ✅ 所有新条目标记为 `[D]`
- ✅ 批次已 `--mode commit` 确认（返回 receipt）
- ✅ 返回摘要包含：分析会话数、提取事实数、踩坑数、状态更新数、receipt

## 详细规则

- 写入规则：见 [../rules/write.md](../rules/write.md)
- 读取规则：见 [../rules/read.md](../rules/read.md)
- 去重规则：见 [../rules/dedup.md](../rules/dedup.md)

