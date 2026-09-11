# Knowledge Base 索引

> 知识库入口索引，按需引导读取详情文件。行数上限 200。

---

## 条目一览

### facts（关键事实）

- [V] 用户身份：游戏数据分析/运营负责人
- [V] 核心工作：多语言手游运营数据分析与后台操作
- [V] 核心诉求：自动化"登录后台 → 导出数据 → Excel 分析 → 写报告"流程
- [D] 存储位置（项目级 `evolution/knowledge-base/`，与 Auto Memory 独立）
- [D] 文件结构（索引 + 详情文件）
- [D] 触发机制（`/evolution`、`/evolution-init` 手动触发）
- [D] 命名规范（Knowledge Base；作者名 `lemen`；MIT 许可）
- [D] 架构设计（索引 + 详情文件；增量写入 + 去重；单一知识库树）
- [D] GitHub 发布（https://github.com/lemenlemen/evolution，v1.0.0，双语文档）

### pitfalls（踩坑记录）

- [D] 1. GitHub MCP 限制（无批量上传，逐个文件上传；大项目用 git 命令行）
- [D] 2. git push 超时（配置本地代理后推送）
- [D] 3. 敏感信息泄漏风险（只保留核心系统文件，用模板代替实际数据）
- [D] 4. Release 创建混淆（Commits ≠ Releases，需手动创建 Release）
- [D] 5. 作者名混淆（README 作者名保留 `lemen`）
- [D] 文件上传最佳实践（小项目 MCP / 大项目 git+代理 / 自动化 Actions）
- [D] 敏感信息检查（上传前 grep 敏感关键词）

### state（当前状态）

- [D] 主任务：Evolution 系统 GitHub 发布（✅ 已完成）
- [D] 用户原始需求（记录任务事实、踩坑、经验冲突，让 AI 更好地完成任务）
- [D] 待补充信息（自动触发机制 / 遗忘机制 / 多 session 并发，均待实现）

---

## 元信息

- 总条目数：19（[V] 3 · [D] 16）
- 最后更新：2026-09-11（v4.1.6；知识条目仍为 v4.1.1 三级状态口径）
