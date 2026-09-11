# 关键事实 (Facts)

> 记录环境配置、技术决策、依赖关系等关键事实。
> 由 Knowledge Base Agent 自动维护

---

## 状态标记说明

- `[D]` draft — AI 提取，未经用户验证
- `[V]` verified — 用户确认或工具验证
- `[X]` deprecated — 已废弃

**格式**：`### [状态] 标题`

---

## 项目身份

- [V] **用户身份**：游戏数据分析/运营负责人
- [V] **核心工作**：管理多语言手游的运营数据分析和后台操作
- [V] **核心诉求**：将"手动登录后台 → 导出数据 → Excel 分析 → 写报告"流程自动化

---

## Evolution 系统架构

### 存储位置
- **项目级存储**：`evolution-manual/knowledge-base/`
- **与 Auto Memory 独立**：不使用 `~/.claude/projects/<project>/memory/`

### 文件结构
```
evolution-manual/
├── agents/
│   ├── knowledge-base-agent.md
│   ├── growth-agent.md
│   └── alignment-agent.md
└── knowledge-base/
    ├── kb-index.md（索引，200 行限制内）
    ├── facts.md
    ├── pitfalls.md
    ├── state.md
    ├── growth-notes.md
    ├── prompt-improvements.md
    ├── alignment.md
    └── decisions.md
```

### 触发机制
- **手动触发**：`/evolution`、`/kb-sync`、`/growth-sync`、`/alignment-sync`
- **自动触发**：每 5 轮（KB/Alignment）、每 10 轮（Growth）- 待实现

---

## 技术决策

### 命名规范
- **Knowledge Base**（不是 Memory）：避免与 Claude Code Auto Memory 冲突
- **作者名**：`lemen`（保留）
- **许可证**：MIT

### 架构设计
- **索引 + 详情文件**：kb-index.md 作为索引（<200 行），详情文件按需读取
- **增量写入 + 去重**：相同信息更新时间戳，新信息追加
- **双系统设计**：evolution-manual（手动）+ evolution-auto（自动）

### GitHub 发布
- **仓库地址**：https://github.com/lemenlemen/evolution
- **版本**：v1.0.0
- **文件数**：12 个
- **语言**：双语文档（英文为主）

---

## 依赖关系

- **Claude Code**：需要支持 Slash Commands 和 Agent tool
- **GitHub MCP**：用于文件上传（无批量上传功能）
- **Git**：用于版本控制

---

## 元信息

- **最后更新**：2026-07-24
- **Knowledge Base Agent 触发次数**：1
- **总条目数**：8
