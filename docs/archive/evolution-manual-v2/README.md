# evolution-manual-v2 归档说明

> **归档日期**：2026-08-21
> **来源**：项目根目录的 `evolution-manual/`（V2 遗留目录）

## 背景

Evolution v3.0.0（2026-07-28）已将知识库目录从 `evolution-manual/` 改为 `evolution/`，
并删除了 auto 版本。但 V2 旧目录 `evolution-manual/` 一直残留在项目根目录，与新树
`evolution/knowledge-base/` 字节级重复（diff 无差异），导致：

- 双知识库树并存，读写可能错位、静默分叉
- 新树的 `kb-index.md` / `facts.md` 自指旧路径 `evolution-manual/`

本目录是 `docsV3/archive/ADVERSARIAL_AUDIT_v3.9.0.md` 问题 #22 的修复产物：
旧树整体移入此处归档，`evolution/knowledge-base/` 为唯一事实来源。

## 内容

- `agents/` — V2 的三个 agent 规格文件（knowledge-base-agent 等，V3 已由
  `.claude/skills/evolution/` 的 sub agent 机制取代）
- `knowledge-base/` — V2 知识库快照（内容与迁移后的新树完全一致，仅作历史存档）

## 注意

**请勿将本目录当作活跃知识库使用。** 唯一活跃的知识库位于项目根的
`evolution/knowledge-base/`。
