# Evolution V3 文档

> **版本**：3.8.0
> **最后更新**：2026-07-31

---

## 文档结构

```
docs/
├── README.md                      # 本文档（索引）
├── PROJECT_BACKGROUND.md          # 项目背景
├── DESIGN_V3.1.0.md               # V3.1.0 设计文档（历史）
├── INSTALLATION_GUIDE.md          # 安装指南
├── VERSION_HISTORY.md             # 版本历史
├── EXPORT_AND_ANALYSIS_DESIGN.md  # 导出和分析设计（v3.3.0）
├── EVOLUTION_RULES_AND_LOGIC_V3.md  # 系统规则（v3）
└── archive/                       # 历史文档归档
    ├── V1_REVIEW.md               # V1 评审
    ├── V2_DESIGN.md               # V2 设计
    ├── V2_TEST_GUIDE.md           # V2 测试
    ├── UPDATE_NOTES_V2.md         # V2 更新说明
    ├── EVOLUTION_RULES_AND_LOGIC_V2.md  # V2 规则
    ├── FABLE_REVIEW.md            # AI review
    ├── SKILL_LOADING_MECHANISM.md # Skill 加载机制
    ├── IMPLEMENTATION_PLAN.md     # V2 实施计划
    └── STATUS.md                  # V2 状态
```

---

## 阅读顺序

### 新用户
1. [PROJECT_BACKGROUND.md](./PROJECT_BACKGROUND.md) - 了解项目背景和痛点
2. [INSTALLATION_GUIDE.md](./INSTALLATION_GUIDE.md) - 安装和验证
3. [DESIGN_V3.1.0.md](./DESIGN_V3.1.0.md) - 了解设计细节（可选）

### 升级用户
1. [VERSION_HISTORY.md](./VERSION_HISTORY.md) - 查看版本变更
2. [INSTALLATION_GUIDE.md](./INSTALLATION_GUIDE.md) - 升级指南

### 开发者
1. [DESIGN_V3.1.0.md](./DESIGN_V3.1.0.md) - 完整设计文档
2. [VERSION_HISTORY.md](./VERSION_HISTORY.md) - 版本历史
3. [archive/](./archive/) - 历史文档

---

## 核心文档

| 文档 | 说明 | 读者 |
|------|------|------|
| [CLAUDE.md](../CLAUDE.md) | 项目配置 | AI |
| [.claude/skills/evolution/SKILL.md](../.claude/skills/evolution/SKILL.md) | 执行指令 | AI |
| [PROJECT_BACKGROUND.md](./PROJECT_BACKGROUND.md) | 项目背景 | 人类 |
| [INSTALLATION_GUIDE.md](./INSTALLATION_GUIDE.md) | 安装指南 | 人类 |
| [DESIGN_V3.1.0.md](./DESIGN_V3.1.0.md) | 设计文档 | 人类 |
| [VERSION_HISTORY.md](./VERSION_HISTORY.md) | 版本历史 | 人类 |

---

## 版本信息

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v3.8.0 | 2026-08-01 | 修复三个 bug：强制脚本 + 禁止手动 glob、修复 find_jsonl_file 返回所有文件、增加验证机制 |
| v3.7.0 | 2026-08-01 | 修复 `/evolution-init` 命令，调用 `evolution-export.py` 导出全部历史，防止采样 |
| v3.6.0 | 2026-08-01 | 将 `/evolution init` 拆分为独立命令 `/evolution-init`，区分初始化和增量同步 |
| v3.5.0 | 2026-07-31 | 基于 writing-great-skills 规则重构，SKILL.md 从 96 行缩减至 37 行 |
| v3.4.0 | 2026-07-31 | 模块化重构，SKILL.md 拆分，config.yaml 统一配置 |
| v3.3.0 | 2026-07-30 | 修复 JSON 序列化崩溃、增量单位漂移、Windows 编码、token 估算偏低、cleanup 安全、文件句柄泄漏等 |
| v3.2.1 | 2026-07-30 | 更新分页参数：80K → 150K（基于注意力研究） |
| v3.2.0-draft | 2026-07-29 | 初始设计，基于 200K 窗口假设 |
| v3.1.0 | 2026-07-29 | 添加初始化命令、对话导出机制 |
| v3.0.0 | 2026-07-28 | 简化系统，删除 auto 版本 |
| v2.1.0 | 2026-07-28 | 写入审核机制 |
| v2.0.0 | 2026-07-28 | Skill 系统迁移 |
| v1.0.0 | 2026-07-21 | 初始版本 |

---

**欢迎使用 Evolution v3.8.0！**
