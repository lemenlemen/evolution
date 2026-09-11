# Evolution 版本历史

> **当前版本**：4.1.6
> **发布日期**：2026-09-11

---

## 版本变更概览

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v4.1.6 | 2026-09-11 | 修复版：隐私泛化、版本号统一、设计文档注记、过时横幅、安装指南补全、发布规则自检 |
| v4.1.5 | 2026-09-10 | 修复版：sha256 回归测试重写（锁定增量 sha256 刷新路径）、安装指南 Python 版本、模板三节删除、归档死链、.gitignore 归档裁决 |
| v4.1.4 | 2026-09-10 | 审查收尾：发布规则、sha256 回归测试、V2 归档 KB 隐私清洗补漏、版本号统一、导出脚本版本头澄清 |
| v4.1.3 | 2026-09-10 | 修复版：五视角审查 sha256 刷新（增量误判 file-replaced）、根目录清理、README 英文版、KB 隐私清洗、LICENSE |
| v4.1.2 | 2026-09-10 | 修复版：对抗性审查 10 项修复（cleanup 保护状态文件、锁路径统一、只读 status、退出码、README、回退横幅） |
| v4.1.1 | 2026-09-10 | 修复版：路径锚定、版本标注、kb-manager 归档、文档清理 |
| v4.1.0 | 2026-09-10 | 修复版：保留引擎层修复，回退知识层过度工程，恢复知识库可用性 |
| v4.0.0 | 2026-08-24 | MAJOR: 双游标+批次+commit、完整性校验、原子写入、[P]隔离、事务锁、生命周期、敏感闸门 |
| v3.9.0 | 2026-08-01 | 添加 `/evolution-init` 前置检查，防止误触重置 |
| v3.8.0 | 2026-08-01 | 修复三个 bug：强制脚本 + 禁止手动 glob、修复 find_jsonl_file 返回所有文件、增加验证机制 |
| v3.7.0 | 2026-08-01 | 修复 `/evolution-init` 命令，调用 `evolution-export.py` 导出全部历史，防止采样 |
| v3.6.0 | 2026-08-01 | 修复 `/evolution init` 为独立命令 `/evolution-init`，区分初始化和增量同步 |
| v3.5.0 | 2026-07-31 | 基于 writing-great-skills 规则重构，SKILL.md 从 96 行缩减至 37 行 |
| v3.4.0 | 2026-07-31 | 模块化重构，SKILL.md 拆分，config.yaml 统一配置 |
| v3.3.0 | 2026-07-30 | 修复 JSON 序列化崩溃、增量单位漂移、Windows 编码、token 估算偏低（CJK 系数 1.5→1.0）、cleanup 安全、文件句柄泄漏等多项问题 |
| v3.2.0-draft | 2026-07-29 | 初始设计，基于 200K 窗口假设（已被 v3.2.1 取代） |
| v3.2.1 | 2026-07-30 | 更新分页参数：80K → 150K（基于注意力研究） |
| v3.1.0 | 2026-07-29 | 添加初始化命令、对话导出机制、sub agent 执行设计 |
| v3.0.0 | 2026-07-28 | 简化系统，删除 auto 版本，添加写入审核机制 |
| v2.1.0 | 2026-07-28 | 写入审核机制（状态标记） |
| v2.0.0 | 2026-07-28 | Skill 系统迁移 |
| v1.0.0 | 2026-07-21 | 初始版本 |

---

## v4.1.6 (2026-09-11)

### 修复版

基于 Pi 的 8 项修复清单，完成多轮审查遗留问题：

**隐私泛化**：
- docsV4/design-v4-engine.md：示例 JSON 全部合成化（project_hash/mtime/size/lines/timestamps）
- evolution-export.py:248：docstring 示例路径泛化为中性示例 `C:\Projects\demo -> C--Projects-demo`

**版本号统一**：
- 所有文件版本号统一升级到 4.1.6（CLAUDE.md/SKILL.md/config/commands/kb-index/evolution-export.py）
- rules/*.md 从 4.1.4 升级到 4.1.6（修复版本漂移）
- INSTALLATION_GUIDE 头尾从 3.9.0 升级到 4.1.6

**设计文档注记**：
- design-v4-engine.md：CLEANUP_PATTERNS 移除 sync-state.json（V4.1.2 变更注记）
- design-v4-engine.md：退出码协议简化为 0/1（V4.1.2 变更注记）

**过时文档处理**：
- EVOLUTION_RULES_AND_LOGIC_V3.md：添加过时横幅（V3 单文件结构，V4 已改为模块化）

**安装指南补全**：
- INSTALLATION_GUIDE §3.1/§4：校验清单补 tests/ + .claude/commands/

**发布规则强化**：
- CLAUDE.md：发布规则加 grep 自检（三表最新版本行一致性核对）

### 修改文件

- `CLAUDE.md` - 版本号 4.1.6 + 发布规则 grep 自检
- `.claude/skills/evolution/SKILL.md` - 版本号 4.1.6
- `.claude/skills/evolution/config.yaml` - 版本号 4.1.6
- `.claude/skills/evolution/commands/init.md` - 版本号 4.1.6
- `.claude/skills/evolution/commands/sync.md` - 版本号 4.1.6
- `.claude/skills/evolution/evolution-export.py` - 版本号 4.1.6 + docstring 泛化
- `.claude/skills/evolution/rules/write.md` - 版本号 4.1.6
- `.claude/skills/evolution/rules/read.md` - 版本号 4.1.6
- `.claude/skills/evolution/rules/dedup.md` - 版本号 4.1.6
- `evolution/knowledge-base/kb-index.md` - 版本号 4.1.6
- `docsV3/VERSION_HISTORY.md` - v4.1.6 章节 + 统计表行
- `docsV3/INSTALLATION_GUIDE.md` - 版本号 4.1.6 + 校验清单补全
- `docsV3/EVOLUTION_RULES_AND_LOGIC_V3.md` - 过时横幅
- `docsV4/design-v4-engine.md` - 隐私泛化 + V4.1.2 变更注记
- `docsV3/ADVERSARIAL_AUDIT_v3.9.0.md` - 16 处真实本地路径泛化（后补）
- `docsV3/EXPORT_AND_ANALYSIS_DESIGN.md` - 18 处真实本地路径/项目 hash 泛化（后补）
- `docsV3/archive/STATUS.md` - 1 处真实本地路径泛化（后补）
- `docsV3/archive/V2_DESIGN.md` - 2 处真实本地路径泛化（后补）
- `docsV3/PRIVACY_SCAN_v4.1.6.txt` - 隐私扫描自检结果记录（后补，新文件）
- `docsV3/privacy_scan_paths.txt` - 路径类扫描原始输出（2 行误报，已裁决为占位符）（后补，新文件）
- `docsV3/privacy_scan_hash.txt` - 项目 hash 类扫描原始输出（0 命中）（后补，新文件）
- `docsV3/privacy_scan_uuid.txt` - UUID 类扫描原始输出（0 命中）（后补，新文件）

**后补记录**（v4.1.6 条目后）：① §3.1 校验清单实际补全（tests/ 预期行 + `.claude/commands/` 校验步骤）——原条目声称已完成，但当时文件并未实际修改，本次后补使该声明成立；② 底部统计表补 v4.1.6 行；③ docsV3 四文件 37 处真实本地路径/项目 hash 泛化（原条目仅覆盖 docsV4 示例与 export.py docstring）；④ CLAUDE.md 发布规则增加"隐私扫描自检"（六类标识符模式清单）。⑤（四视角审查后补）审查发现 8 处漏检：EXPORT_AND_ANALYSIS_DESIGN.md 7 处 WSL 小写盘符路径（`/e/…` 形态）+ ADVERSARIAL_AUDIT_v3.9.0.md 1 处裸父目录形态（`E:\…\`，不含项目名）——③ 的 sed 仅覆盖反斜杠与大写盘符正斜杠两种形态；且当时"终验 0 残留"为假阴性（内容级 `grep -v` 过滤把含 `evolution/` 字样的泄露行整行滤除）。现 8 处全部补泛化（两文件累计 16/18 处全部清理，③ 的统计数字以累计口径成立）；CLAUDE.md 隐私扫描规则改为目录级排除 + 四种路径形态清单；INSTALLATION_GUIDE §4 第二份期望清单补 tests/ 与 `.claude/commands/` 校验（原条目"§3.1/§4"声明至此全部兑现）；目录级排除的正确全扫结果：六类标识符 0 真命中（2026-09-11）。隐私扫描自检结果留存于 `docsV3/PRIVACY_SCAN_v4.1.6.txt`（三类原始输出见同目录 `privacy_scan_paths.txt` / `privacy_scan_hash.txt` / `privacy_scan_uuid.txt`）。

## v4.1.5 (2026-09-10)

### 修复版

落实上一轮审查遗留的多项修复：

**测试重写**：
- sha256 回归测试 1 重写为真实增量流程（`export_full` → `commit` →
  追加 → `export_incremental` → 断言状态 sha256 == 文件实际 sha256 →
  `commit` → 再次追加 → `export_incremental` → 断言无 `file-replaced` 误判），
  真正锁定 `export_incremental` 的 sha256 刷新路径（原测试手动构造 FileInfo，
  仅覆盖 `check_integrity` 纯追加分支，未触达刷新代码）。测试时以 monkeypatch
  方式注入 `find_jsonl_file`，隔离真实 `~/.claude/projects/` 环境。

**文档修复**：
- 安装指南：`INSTALLATION_GUIDE.md` 第 1.3 节"Python 3.8.x 或更高"改为
  "Python 3.9.x 或更高"（与 1.1 节系统要求的 3.9+ 一致）
- `CLAUDE.md` 删除模板三节（Issue tracker / Triage labels / Domain docs，
  为脚手架模板残留，本仓库未落地 `.scratch/`、`CONTEXT.md`、`docs/adr/`）
- 归档死链：`docsV3/archive/EVOLUTION_RULES_AND_LOGIC_V2.md`、
  `docsV3/archive/V2_DESIGN.md` 中 `./VERSION_HISTORY.md` 改为
  `../VERSION_HISTORY.md`（归档子目录上移后相对路径失效）

**won't-fix**（按 `CLAUDE.md` 发布规则显式裁决）：
- `.gitignore` 中 `evolution/knowledge-base/archive/` 忽略规则保留现状，
  不予删除。理由：该目录存放 V4.1.0 归档的 `v4.0.0-kb-manager` 等大文件，
  按需提交策略不变；归档内容仍可通过显式 `git add -f` 纳入版本控制，
  无功能性阻塞，故记为 won't-fix。

### 修改文件

- `.claude/skills/evolution/tests/test_sha256_invariant.py` - 测试 1 重写为真实增量流程（3/3 通过）
- `docsV3/INSTALLATION_GUIDE.md` - Python 版本 3.8.x → 3.9.x
- `CLAUDE.md` - 版本号 4.1.5 + 删除模板三节
- `docsV3/archive/{EVOLUTION_RULES_AND_LOGIC_V2,V2_DESIGN}.md` - 死链修复
- `docsV3/EXPORT_AND_ANALYSIS_DESIGN.md` - 会话 UUID 泛化 + 过时横幅
- `.claude/skills/evolution/evolution-export.py` - 系统版本 4.1.5
- `.claude/skills/evolution/{SKILL.md,config.yaml,commands/init.md,commands/sync.md}` - 版本号 4.1.5
- `evolution/knowledge-base/kb-index.md` - 版本号 4.1.5
- `docsV3/VERSION_HISTORY.md` - v4.1.5 条目 + 统计表行

**后补记录**（4.1.5 发布后）：修正 v4.1.4 条目中 V2 归档 KB 清洗的归属表述——从"已验证无需改动（v4.1.3 已覆盖）"移入"本次修改"并标注"补漏"，同步补"修改文件"清单与两处概览表。

---

## v4.1.4 (2026-09-10)

### 审查收尾

落实上一轮审查遗留项，并验证先前修复的实际状态：

**已验证无需改动**（逐文件 grep 确认）：
- 底部统计表 v4.1.1/v4.1.2 行已有 `PATCH` 类型列——v4.1.3 已补

**本次修改**：
- 补漏：V2 归档 KB 隐私清洗——`docsV3/archive/evolution-manual-v2/knowledge-base/{facts,pitfalls,state}.md` 仍残留雇主/本地环境标识（v4.1.3 清洗覆盖现行 KB 与活跃文档，未覆盖归档目录；本轮审查复扫确认），本轮按现行 KB 口径泛化（清单见内部审查记录，不入库）
- 规则文件版本号统一：`rules/{write,read,dedup}.md` 标题 v4.1.3 → v4.1.4
- 导出脚本版本头澄清：`evolution-export.py` 头部"自 V4.0.0 未变"改为"最近实质修改于 V4.1.3 sha256 刷新修复"，并注明 VERSION 常量为 sync-state schema 版本（3.5.0），与系统文档版本独立
- `CLAUDE.md` 新增"发布规则"：每轮审查确认的发现必须出现在修复清单或显式标注 won't-fix + 理由（防"漏斗漏项"）
- 删除 v2.0.0 章节中对不存在文件 `INSTALLATION_GUIDE_V2.md` 的引用行（死链）
- 新建 sha256 不变量回归测试 `.claude/skills/evolution/tests/test_sha256_invariant.py`（3 组断言，全部通过）：
  1. 双追加不触发 file-replaced 误判
  2. status 只读模式不修改磁盘文件
  3. 损坏恢复链正确回写

### 修改文件

- `.claude/skills/evolution/rules/{write,read,dedup}.md` - 标题版本号 → 4.1.4
- `.claude/skills/evolution/evolution-export.py` - 头部版本说明澄清 + 系统版本 4.1.4
- `.claude/skills/evolution/tests/test_sha256_invariant.py` - 新建
- `CLAUDE.md` - 版本号 4.1.4 + 发布规则
- `.claude/skills/evolution/{SKILL.md,config.yaml,commands/init.md,commands/sync.md}` - 版本号 4.1.4
- `evolution/knowledge-base/kb-index.md` - 版本号 4.1.4
- `docsV3/archive/evolution-manual-v2/knowledge-base/{facts,pitfalls,state}.md` - 隐私清洗补漏
- `docsV3/VERSION_HISTORY.md` - v4.1.4 条目 + 死链删除

---

## v4.1.3 (2026-09-10)

### 修复版

修复五视角审查（多模型）发现的 CRITICAL 问题：

**必须修复**：
- sha256 刷新：增量路径追加后同步更新 fi.sha256（防止误判 file-replaced）
- 根目录清理：删除 18 个陈旧文件 + docs/ + 遗留锁/chunk 备份
- README 双语修复：创建真正的英文 README.md
- KB 隐私清洗：泛化真实雇主/身份信息
- 添加 LICENSE 文件（MIT）

**建议修复**：
- state-version-newer 标注未实现
- "当前会话过滤"删除虚构承诺
- 损坏恢复指引修正
- test_concurrent.py 删除补 changelog
- VERSION_HISTORY 统计表补 v4.1.1/v4.1.2 两行

### 修改文件

- `.claude/skills/evolution/evolution-export.py` - sha256 刷新 + 损坏指引修正
- `README.md` - 重写为英文版
- `LICENSE` - 新建
- `evolution/knowledge-base/*.md` - 隐私清洗
- 根目录 - 清理陈旧文件
- 版本号全部升级到 4.1.3

---

## v4.1.2 (2026-09-10)

### 修复版

修复三视角对抗性审查（多模型）发现的全部 10 项问题：

**必须修复**：
- CLEANUP_PATTERNS 移除 sync-state.json（防止误删状态文件）
- 统一锁路径为 export.lock（防止并发丢更新）
- --mode status 恢复后回写（防止只读命令摧毁状态）
- error 状态改 exit 1（与退出码协议对齐）
- 创建 README.md / README.zh-CN.md（发布准备）

**建议修复**：
- docsV4 三份设计文档加回退横幅
- export_full 加载现有状态（保留批次历史）
- status 字符串统一为 failed
- trust_committed 承诺标记为未实现
- 清理根目录杂物

### 修改文件

- `.claude/skills/evolution/evolution-export.py` - CLEANUP_PATTERNS + 锁路径 + 恢复链 + 退出码 + status 字符串
- `.claude/skills/evolution/commands/init.md` - 版本号 + cleanup 建议调整
- `.claude/skills/evolution/commands/sync.md` - 版本号
- `README.md` / `README.zh-CN.md` - 新建
- `docsV4/*.md` - 回退横幅
- 删除 `tests/test_concurrent.py`（已停用，锁方案变更后不再适用）
- 版本号全部升级到 4.1.2

---

## v4.1.1 (2026-09-10)

### 修复版

修复审核发现的所有问题（多模型 审核）：

**必须修复**：
- evolution-export.py 头部版本标注（引擎版本 v3.10.0 / 系统版本 4.1.1）
- /evolution-init 注册路径（创建 .claude/commands/evolution-init.md）
- 路径锚定实现（get_project_root() 函数，parents[3]）
- kb-manager.py 归档（移到 archive/v4.0.0-kb-manager/）
- facts.md / pitfalls.md 页脚更新（2026-09-10）
- CLAUDE.md 死链修复（移除指向不存在的文件）

**建议修复**：
- 退出码协议文档化（sync.md）
- assert 改显式错误（commit_batch cursor-regression）
- chunk 命名文档化（init.md 步骤 2）
- 空文档引导移除（read.md 不再路由到 growth-notes 等）

### 修改文件

- `.claude/skills/evolution/evolution-export.py` - 头部重写 + 路径锚定 + assert 改错误
- `.claude/commands/evolution-init.md` - 新建
- `.claude/skills/evolution/kb-manager.py` - 移到 archive/
- `.claude/skills/evolution/commands/init.md` - 版本号 + 文档更新
- `.claude/skills/evolution/commands/sync.md` - 版本号 + 退出码文档
- `.claude/skills/evolution/rules/read.md` - 移除空文档引导
- `evolution/knowledge-base/facts.md` - 页脚更新
- `evolution/knowledge-base/pitfalls.md` - 页脚更新
- `evolution/knowledge-base/kb-index.md` - 版本号更新
- `CLAUDE.md` - 版本号 + 死链修复

---

## v4.1.0 (2026-09-10)

**修复版**：基于四位审查者共识——保留 V4 引擎层修复（3 个会导致数据永久丢失的
Critical 问题确为真问题），回退知识层过度工程，恢复 V3 轻量规则 + 新增两条红线，
恢复知识库可用性（16 条 [P] 全部恢复为 [D]/[V]，pending.md 删除）。

### 保留（引擎层全部修复）

- 双游标（`exported_lines` / `committed_lines`）+ 批次状态机 + `--mode commit` 协议与 receipt
- 完整性校验（mtime+size 快速路径 → sha256 决策表）
- 原子写入（tmp + fsync + os.replace）+ 三级恢复链
- 全量导出流式化（两遍扫描 + k-way 归并）、全局时间戳排序、token 安全因子 1.5、
  字符数硬守卫 800K、ParseStats 解析防御、文档诚实化

### 回退（知识层过度工程）

- `kb-manager.py`：从"唯一写入口"降级为可选只读工具（仅 `validate` / `health` /
  `scan` 可用；`add` / `promote` / `deprecate` / `restore` / `archive` /
  `migrate` / `compress` 调用即报错退出，exit 2）
  - V4.1.0 审核修复：整文件归档至
    `evolution/knowledge-base/archive/v4.0.0-kb-manager/`，移出技能目录（消除死代码
    与 `validate` 误导性错误文案）
- `[P]` 隔离 + pending.md：删除；"新知识落 [D] 即可用"恢复
- 四级状态 `[P]/[D]/[V]/[X]/[C]/blocked` → 恢复三级 `[D]/[V]/[X]`
- 证据类型绑定 + 置信度、`kb-meta` 元数据行：全部移除，恢复普通 markdown
- 生命周期（30/90/180/365 天阈值）、archive/ 自动归档：移除（无 archive/ 目录生成过）
- 敏感扫描写入闸门：移除（config.yaml `sensitive_patterns` 段删除）
- `/kb-review` `/kb-status` `/kb-archive` `/kb-restore`：4 个命令文件删除，
  SKILL.md 恢复 2 个命令（`/evolution` `/evolution-init`）
- `sync.md` 体检扫描步骤（`kb-manager.py health`）移除；commit 批次协议保留

### 新增（write.md 两条红线，替代整个 pending 子系统）

1. `[D]`/未验证不得淘汰 `[V]`，冲突并列保留并标注"存在矛盾，待人工裁决"
2. 未验证条目不作高风险决策的唯一依据；与 `[V]` 冲突时以 `[V]` 为准并告警用户

### 主要修改文件

- `evolution/knowledge-base/{facts,pitfalls,state}.md` — 移除 `kb-meta` 行，`[P]`→`[D]`
- `evolution/knowledge-base/pending.md` — 删除（为空隔离区）
- `evolution/knowledge-base/kb-index.md` — 恢复 V3 格式（移除 [P] 隔离区说明）
- `.claude/skills/evolution/rules/{write,read,dedup}.md` — 恢复 V3 + 两条红线（write.md 规则 3/4）
- `.claude/skills/evolution/commands/` — 删除 kb-review/kb-status/kb-archive/kb-restore
- `.claude/skills/evolution/{SKILL.md,config.yaml}` — 4.1.0；config 移除
  status_markers 扩展/lifecycle/lock/sensitive_patterns，保留 sync_engine
- `.claude/skills/evolution/kb-manager.py` → `evolution/knowledge-base/archive/v4.0.0-kb-manager/` — 4.1.0：写入口禁用闸门后归档（V4.1.0 审核修复）
- `.claude/skills/evolution/tests/test_concurrent.py` — 标注停用（保留备查）
- `CLAUDE.md`、`docsV3/VERSION_HISTORY.md` — 4.1.0

---

## v4.0.0 (2026-08-24)

**MAJOR 升级**：基于对抗性审核（54 agents，39 条确认发现）实施 V4 设计（docsV4/），修复 3 个会导致数据永久丢失的 Critical 问题，并重建知识质量防线。

### 修复的 Critical 问题

1. **Critical 1 — 增量游标先于知识提取提交**
   - `processed_lines` 拆分为双游标 `exported_lines` / `committed_lines`
   - 增量起点改为 `committed_lines + 1`；每次导出建批次，sub agent 分析后经
     `--mode commit` 显式确认（返回 receipt），中断可恢复、失败自动重生成
2. **Critical 2 — 游标无完整性校验，截断/轮换静默丢数据**
   - 新增 `check_integrity`：mtime+size 快速路径 → sha256 比对决策表，
     截断/替换整文件重导 + WARN + partial 状态；纯追加走正常增量
3. **Critical 3 — 状态文件非原子写入**
   - `save_sync_state` 改为 tmp + fsync + os.replace 原子写入；
   - 损坏时三级恢复链：`.bak` 恢复 → 无备份显式失败（绝不静默回退空状态）

### 新增功能（引擎层）

- 批次清单与状态机（exported/analyzing/committed/failed）+ 重生成 + retry 上限
- `--mode commit / start / analyze-failed / status --verify` CLI 与退出码协议
  （0=success / 1=failed；partial 亦以 0 退出，由返回 JSON 的 `status` 字段区分，
  权威定义见 `.claude/skills/evolution/commands/sync.md` 的"退出码协议"）
- 全量导出流式化：两遍扫描 + k-way 归并（O(1) 内存）、全局时间戳排序、
  session 感知轮次分组、超大轮次无条件 flush（修复时间乱序）
- token 估算安全因子 1.5 + 字符数硬守卫 800K；ParseStats 解析防御（坏行不崩）

### 新增功能（知识层）

- 四级状态模型 `[P]/[D]/[V]/[X]` + 冲突叠加 `[C]`；新条目 100% 首落 pending.md 隔离区
- `kb-manager.py` 唯一写入口（add/promote/deprecate/restore/archive/compress/
  health/scan/migrate/validate）：`.kb.lock` 事务锁 + 临时副本校验 + 原子替换
- 敏感信息闸门：写入前扫描（config.yaml sensitive_patterns 唯一权威来源），
  命中条目以打码形态落 pending（blocked=secret，原始值零落盘）
- 知识生命周期：超期归档（archive/YYYY-MM/ + manifest）、索引压缩（500 行上限）、
  `/kb-review` `/kb-status` `/kb-archive` `/kb-restore` 四个新命令

### 移除

- 幻影命令 `/kb-sync` `/growth-sync` `/alignment-sync`（从未注册，#23 命令统一）

### 主要修改文件

- `.claude/skills/evolution/evolution-export.py` — 双游标+批次+完整性+流式化重构
- `.claude/skills/evolution/kb-manager.py` — 新建（唯一写入口 + 事务 + 生命周期）
- `.claude/skills/evolution/config.yaml` — sync_engine/lifecycle/lock/sensitive_patterns
- `.claude/skills/evolution/rules/{write,read,dedup}.md` — V4 规则重写
- `.claude/skills/evolution/commands/` — 新增 kb-review/kb-status/kb-archive/kb-restore
- `evolution/knowledge-base/pending.md` — 新建隔离区
- `.gitignore`、README（隐私章节）

---

## v3.9.0 (2026-08-01)

### 新增功能

1. **`/evolution-init` 前置检查**
   - 初始化前运行 `python .claude/skills/evolution/evolution-export.py --mode status` 检查 `last_full_sync`
   - 检测到已有初始化记录时，向用户确认是否继续
   - 防止误触重置导致 chunk 文件覆盖和增量游标重置

### 修改文件

- `.claude/skills/evolution/commands/init.md`
  - 添加步骤 0 前置检查逻辑
  - 修复孤立 U+FE0F 变体选择符字符
  - 统一命令格式为 `python .claude/skills/evolution/evolution-export.py --mode status`

---

## v3.8.0 (2026-08-01)

### 修复

1. **强制使用导出脚本 + 禁止手动 glob**
   - `/evolution-init` 命令中明确禁止手动 glob `~/.claude/projects/`
   - 脚本返回 `status != success` 必须停止并报告
   - 不得绕过脚本，不得回退到手动读取

2. **修复 `find_jsonl_file` 返回所有文件**
   - 使用 `glob("*.jsonl")` 只匹配当前目录下的 .jsonl 文件
   - 不进入 subagents 子目录，无需额外过滤
   - 返回所有发现的 JSONL 文件列表（按修改时间升序）

3. **增加验证机制**
   - 文件消费一致性校验：`discovered_files` 与 `parsed_files` 集合相等校验
   - 跨进程文件锁 `file_lock`：防止并发导出导致状态损坏
   - Windows 用 `msvcrt.locking`，Linux/macOS 用 `fcntl.flock`

### 修改文件

- `.claude/skills/evolution/evolution-export.py` - 新增一致性校验、文件锁、`parse_jsonl_full`、`count_physical_lines`
- `.claude/skills/evolution/commands/init.md` - 强制脚本 + 禁止手动 glob
- `docsV3/EXPORT_AND_ANALYSIS_DESIGN.md` - 同步更新设计文档

---

## v3.7.0 (2026-08-01)

### 修复

1. **修复 `/evolution-init` 命令**
   - 调用 `evolution-export.py` 导出全部历史对话
   - 防止采样导致历史对话丢失

---

## v3.6.0 (2026-08-01)

### 修复

1. **区分初始化和增量同步命令**
   - 将 `/evolution init` 改为独立命令 `/evolution-init`
   - `/evolution` 专用于增量同步
   - 避免参数混用导致的误操作

---

## v3.5.0 (2026-07-31)

### 重构

1. **基于 writing-great-skills 规则重构**
   - SKILL.md 从 96 行缩减至 37 行
   - 遵循渐进式披露原则，入口文件精简

---

## v3.4.0 (2026-07-31)

### 重构

1. **模块化重构**
   - SKILL.md 拆分为模块化结构
   - 新增 `config.yaml` 统一配置（分页参数、token 估算、状态标记）
   - 新增 `commands/` 目录（init.md、sync.md）
   - 新增 `rules/` 目录（write.md、read.md、dedup.md）
   - `evolution-export.py` 从 config.yaml 读取配置

---

## v3.3.0 (2026-07-30)

### 修复

1. **JSON 序列化崩溃**
   - 统一 `state_to_dict` 序列化，避免 FileInfo 不可 JSON 序列化

2. **增量单位漂移**
   - `processed_lines` 改用最后一条 entry 的真实行号（物理行号），而非 `len(entries)`
   - 避免物理行号与逻辑条目数的单位混用

3. **Windows 编码**
   - 强制 stdout/stderr 使用 UTF-8，避免 GBK 编码崩溃
   - 文件读写显式指定 `encoding='utf-8'` + `errors='replace'`

4. **Token 估算偏低**
   - CJK 系数由 1.5 下调至 1.0 字符/token，修正系统性偏低

5. **cleanup 安全**
   - 仅删除白名单内的文件，绝不 rmtree 整个目录

6. **文件句柄泄漏**
   - 修复多处文件句柄未正确关闭的问题

---

## v3.2.1 (2026-07-30)

### 变更

1. **更新分页参数**
   - 目标 chunk 大小：80K → 150K（基于注意力研究）
   - 基于 "Lost in the Middle" 论文的 U 型注意力曲线研究

---

## v3.2.0-draft (2026-07-29)

### 初始设计

1. **初始设计草案**
   - 基于 200K 窗口假设的初始设计
   - 后续迭代为 v3.2.1（150K）和 v3.3.0（90K）

---

## v3.1.0 (2026-07-29)

### 新增功能

1. **初始化命令**
   - 添加 `/evolution init` 命令
   - 首次安装后分析全部历史对话
   - 生成初始知识库

2. **对话导出机制**
   - 初版设计包含方法 A（AI 记忆）和方法 B（文件记录）
   - v3.7.0 后统一为 `evolution-export.py` 脚本导出（唯一方式）

3. **Sub Agent 执行设计**
   - 所有操作由 sub agent 执行
   - 减少对主 session 的污染

### 设计文档变更

1. **CLAUDE.md**
   - 创建项目配置文件
   - 定义知识库位置

2. **SKILL.md**
   - 更新到 v3.1.0
   - 添加初始化命令
   - 添加对话导出机制
   - 强调 sub agent 执行原则

3. **DESIGN_V3.1.0.md**
   - 新建设计文档
   - 详细说明设计考虑
   - 说明文档职责分工

---

## v3.0.0 (2026-07-28)

**重大变更**：
- 删除 `evolution-auto/` 目录（自动触发版本）
- 知识库目录从 `evolution-manual/` 改为 `evolution/`
- 简化系统，只保留手动触发版本

**修改原因**：
- 所有内容都必须人工核对
- 人类也要读取文档学习
- 自动触发版本未经实战检验
- 简化系统，减少复杂度

**修改文件**：
- 删除 `evolution-auto/` 目录
- 重命名 `evolution-manual/` → `evolution/`
- `.claude/skills/evolution/SKILL.md`
  - 版本号：2.1.0 → 3.0.0
  - 去掉"自动触发"章节
  - 去掉"手动触发"标题（只有一种了）
  - 更新知识库位置：`evolution-manual/` → `evolution/`
  - 新增核心原则：人工审核
- `evolution/knowledge-base/kb-index.md`
  - 版本号：2.1.0 → 3.0.0
  - 去掉"手动触发"标记
  - 更新位置信息

**向后兼容**：
- ❌ 不兼容（目录结构变化）
- ⚠️ 需要迁移现有知识库

**迁移指南**：
```bash
# 1. 重命名目录
mv evolution-manual evolution

# 2. 更新 SKILL.md 中的路径引用（已自动完成）

# 3. 验证
/evolution
```

---

### [2.1.0] - 2026-07-28

**新增功能**：
- 添加写入审核机制（状态标记）
- 新条目默认标记为 `[D]`（draft）
- 用户确认后标记为 `[V]`（verified）
- 废弃条目标记为 `[X]`（deprecated）

**修改文件**：
- `.claude/skills/evolution/SKILL.md`
  - 新增"写入规则（审核机制）"章节
  - 定义三级状态模型（draft/verified/deprecated）
  - 明确写入规则和冲突处理
  
- `evolution-manual/knowledge-base/kb-index.md`
  - 新增"读取指南（AI 必须遵守）"章节
  - 定义状态标记说明
  - 明确使用规则（优先级、冲突处理）

- `evolution-manual/knowledge-base/facts.md`
  - 添加状态标记说明
  - 现有条目添加 `[V]` 标记

**设计文档**：
- `docs/EARLY_REVIEW.md` - AI 的深度评审
- `docs/PROJECT_BACKGROUND.md` - 项目背景（用户原始需求）

**改进原因**：
- AI 评审指出"写入审核机制缺失"是致命缺陷
- 错误信息会形成自我强化循环
- 需要简单的审核机制打破循环

**影响范围**：
- 所有知识库文件（facts.md、pitfalls.md 等）
- AI 的读取和写入行为
- 用户可能需要审核新条目

**向后兼容**：
- ✅ 完全兼容 V2.0
- ✅ 旧条目无标记，默认为 `[D]`
- ✅ 读取规则对无标记条目友好

---

### [2.0.0] - 2026-07-28

**重大变更**：
- 从 Slash Command 迁移到 Skill 系统
- 支持渐进式披露
- 支持自动触发（AI 判断）

**新增功能**：
- 双向功能（读取 + 写入）
- 渐进式读取规则
- 与 Auto Memory 分离

**修改文件**：
- `.claude/skills/evolution/SKILL.md` - 新建
- `CLAUDE.md` - 已删除（Skill 独立工作）

**设计文档**：
- `docs/V2_DESIGN.md` - V2 设计文档
- `docs/EVOLUTION_RULES_AND_LOGIC_V2.md` - 系统规则
- `docs/V2_TEST_GUIDE.md` - 测试指南
- `docs/UPDATE_NOTES_V2.md` - 更新说明
- `docs/PROJECT_BACKGROUND.md` - 项目背景
- `docs/EARLY_REVIEW.md` - AI 评审

**改进原因**：
- V1 使用 Slash Command，AI 不知道知识库存在
- V2 使用 Skill，AI 知道且可自动触发
- 节省 66% 上下文消耗

---

### [1.0.0] - 2026-07-21

**初始版本**：
- 使用 Slash Command 触发
- 基础知识库结构
- 单向功能（只读取）

**文件**：
- `.claude/commands/evolution.md` - 命令定义
- `evolution-manual/knowledge-base/` - 知识库目录

**已知问题**：
- AI 不知道知识库存在
- 无法自动触发
- 上下文消耗大（全量读取）

---

## 变更统计

| 版本 | 日期 | 类型 | 主要变更 |
|------|------|------|----------|
| v1.0.0 | 2026-07-21 | 初始 | Slash Command |
| v2.0.0 | 2026-07-28 | MAJOR | 迁移到 Skill 系统 |
| v2.1.0 | 2026-07-28 | MINOR | 写入审核机制 |
| v3.0.0 | 2026-07-28 | MAJOR | 删除 auto 版本，简化系统 |
| v3.1.0 | 2026-07-29 | MINOR | 添加初始化命令、对话导出机制 |
| v3.2.0-draft | 2026-07-29 | DRAFT | 初始设计，基于 200K 窗口假设（已被 v3.2.1 取代） |
| v3.2.1 | 2026-07-30 | PATCH | 更新分页参数：80K → 150K |
| v3.3.0 | 2026-07-30 | MINOR | 修复多项 bug（序列化、编码、token 估算等） |
| v3.4.0 | 2026-07-31 | MAJOR | 模块化重构，config.yaml 统一配置 |
| v3.5.0 | 2026-07-31 | MINOR | SKILL.md 重构，从 96 行缩减至 37 行 |
| v3.6.0 | 2026-08-01 | MINOR | 区分初始化和增量同步命令 |
| v3.7.0 | 2026-08-01 | MINOR | 修复 /evolution-init 调用导出脚本 |
| v3.8.0 | 2026-08-01 | MINOR | 修复三个 bug + 增加验证机制 |
| v3.9.0 | 2026-08-01 | MINOR | 添加 /evolution-init 前置检查 |
| v4.0.0 | 2026-08-24 | MAJOR | 双游标+批次+commit、完整性校验、原子写入、[P]隔离、事务锁、生命周期、敏感闸门 |
| v4.1.0 | 2026-09-10 | PATCH | 保留引擎层修复，回退知识层过度工程（[P]隔离/kb-manager写入口/生命周期/敏感闸门/4新命令），恢复[D]/[V]/[X]三级+两条红线 |
| v4.1.1 | 2026-09-10 | PATCH | 修复版：路径锚定、版本标注、kb-manager 归档、文档清理 |
| v4.1.2 | 2026-09-10 | PATCH | 修复版：10 项审查问题修复（CLEANUP/锁/status/exit/README/横幅/状态/字符串/标记/清理） |
| v4.1.3 | 2026-09-10 | PATCH | 五视角审查修复（sha256 刷新/根目录清理/README 英文版/KB 隐私清洗/LICENSE） |
| v4.1.4 | 2026-09-10 | PATCH | 审查收尾（发布规则/sha256 回归测试/V2 归档 KB 清洗补漏/版本号统一/版本头澄清/死链删除） |
| v4.1.5 | 2026-09-10 | PATCH | 五视角审查修复：隐私清洗、测试重写、文档修复 |
| v4.1.6 | 2026-09-11 | PATCH | 版本统一（含 rules 漂移修复）、隐私泛化（docsV4 示例/export.py docstring/docsV3 路径）、设计文档注记、过时横幅、校验清单补全、grep 自检规则 |

---

## 未来规划

### 作废（原 [4.1.0] 规划项，V4.1.0 回退 [P] 隔离/lifecycle 后不再适用）
- restore 落点与 [P] 隔离原则的统一裁决
- cleanup 与 sync-state.json 永不删除语义的统一
- health stale 统计排除 blocked 条目
- .kb.tmp 残留的体检自动清理

---

## 相关文档

| 文档 | 说明 |
|------|------|
| `docsV3/archive/EARLY_REVIEW.md` | AI 的深度评审（已归档） |
| `docsV3/archive/V2_DESIGN.md` | V2 设计文档（已归档） |
| `docsV3/archive/EVOLUTION_RULES_AND_LOGIC_V2.md` | 系统规则 V2（已归档） |
| `docsV3/PROJECT_BACKGROUND.md` | 项目背景 |

---

**文档结束**
