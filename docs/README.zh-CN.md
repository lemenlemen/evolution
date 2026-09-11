# Evolution 文档

🌐 **语言 / Language**: [中文](README.zh-CN.md) | [English](README.md)

> **版本**：4.1.6
> **最后更新**：2026-09-11

---

## 文档结构

```
docs/
├── README.md                        # 本文档（索引）
├── PROJECT_BACKGROUND.md            # 项目背景与痛点
├── INSTALLATION_GUIDE.md            # 安装指南
├── VERSION_HISTORY.md               # 版本历史
├── DESIGN_V3.1.0.md                 # V3.1.0 设计文档（历史）
├── EVOLUTION_RULES_AND_LOGIC_V3.md  # V3 系统规则与运行逻辑（已过时）
├── EXPORT_AND_ANALYSIS_DESIGN.md    # 导出和分析设计
├── ADVERSARIAL_AUDIT_v3.9.0.md      # 驱动 V4 的对抗性审核（仅中文）
├── v4/                              # V4 设计文档（当前）
│   ├── DESIGN_V4.0.0.md             # V4 设计总纲
│   ├── design-v4-engine.md          # V4 同步引擎层
│   └── design-v4-knowledge.md       # V4 知识管理层（已回退）
└── archive/                         # 历史文档归档
    ├── V1_REVIEW.md                 # V1 评审
    ├── V2_DESIGN.md                 # V2 设计
    ├── V2_TEST_GUIDE.md             # V2 测试指南
    ├── UPDATE_NOTES_V2.md           # V2 更新说明
    ├── EVOLUTION_RULES_AND_LOGIC_V2.md # V2 规则
    ├── FABLE_REVIEW.md              # 早期深度评审
    ├── SKILL_LOADING_MECHANISM.md   # Skill 加载机制研究
    ├── IMPLEMENTATION_PLAN.md       # V2 实施计划
    ├── STATUS.md                    # V2 状态
    └── evolution-manual-v2/         # V2 知识库原始快照
```

除标注"仅中文"的两篇外，以上每篇文档都有对应的 `.zh-CN.md` 中文版本。

---

## 阅读顺序

### 新用户
1. [项目背景](./PROJECT_BACKGROUND.zh-CN.md) —— 了解痛点
2. [安装指南](./INSTALLATION_GUIDE.zh-CN.md) —— 安装与验证
3. [版本历史](./VERSION_HISTORY.zh-CN.md) —— 查看变更

### 升级用户
1. [版本历史](./VERSION_HISTORY.zh-CN.md) —— 版本变更
2. [安装指南](./INSTALLATION_GUIDE.zh-CN.md) —— 升级步骤

### 开发者
1. [v4/DESIGN_V4.0.0.zh-CN.md](./v4/DESIGN_V4.0.0.zh-CN.md) —— 当前架构
2. [v4/design-v4-engine.zh-CN.md](./v4/design-v4-engine.zh-CN.md) —— 数据完整性层
3. [导出和分析设计](./EXPORT_AND_ANALYSIS_DESIGN.zh-CN.md) —— 导出流水线
4. [对抗性审核](./ADVERSARIAL_AUDIT_v3.9.0.md) —— V4 背后的那次审核

---

## 核心文档

| 文档 | 说明 | 读者 |
|------|------|------|
| [.claude/skills/evolution/SKILL.md](../.claude/skills/evolution/SKILL.md) | 执行指令（真正的 skill） | AI |
| [项目背景](./PROJECT_BACKGROUND.zh-CN.md) | 项目背景 | 人类 |
| [安装指南](./INSTALLATION_GUIDE.zh-CN.md) | 安装指南 | 人类 |
| [版本历史](./VERSION_HISTORY.zh-CN.md) | 版本历史 | 人类 |
| [v4/设计总纲](./v4/DESIGN_V4.0.0.zh-CN.md) | 当前设计 | 人类 |
| [导出和分析设计](./EXPORT_AND_ANALYSIS_DESIGN.zh-CN.md) | 导出与分析设计 | 人类 |

> 历史文档（`DESIGN_V3.1.0.md`、`EVOLUTION_RULES_AND_LOGIC_V3.md`）描述的是 V3 时代的行为，仅为参考保留；当前实现以上方 V4 文档为准。

---

## 版本信息

完整变更日志见[版本历史](./VERSION_HISTORY.zh-CN.md)。

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v4.1.6 | 2026-09-11 | 隐私泛化、版本号统一、设计文档注记、安装指南补全 |
| v4.1.5 | 2026-09-10 | sha256 回归测试重写、Python 版本修正、归档死链修复 |
| v4.1.4 | 2026-09-10 | 发布规则、sha256 回归测试、版本号统一 |
| v4.1.3 | 2026-09-10 | sha256 刷新修复（增量误判 `file-replaced`）、README、知识库隐私清洗、LICENSE |
| v4.1.2 | 2026-09-10 | 对抗性审查修复（cleanup 保护状态、锁路径、只读 status、退出码） |
| v4.1.1 | 2026-09-10 | 路径锚定、版本标注、kb-manager 归档 |
| v4.1.0 | 2026-09-10 | 保留引擎层修复，回退知识层过度工程 |
| v4.0.0 | 2026-08-24 | MAJOR：双游标 + 批次 commit、完整性校验、原子写入 |
| v3.9.0 | 2026-08-01 | 添加 `/evolution-init` 前置检查 |

---

**欢迎使用 Evolution v4.1.6！**
