# Evolution v3.9.0 对抗性审核报告

> 生成：2026-08-16 | 方式：Workflow 对抗性审核（多模型交叉审计，对立模型交叉反驳验证）
> 规模：54 agents | 报告 48 条 | 反驳剔除 9 条 | **确认 39 条**
> 性质：仅意见方案，未修改任何文件

## 严重度分布
- **CRITICAL**: 3
- **HIGH**: 13
- **MEDIUM**: 22
- **LOW**: 1

## 确认发现（39 条）

### 1. [HIGH] 同步游标先于知识提取提交造成不可恢复的数据丢失

**文件**: `.claude/skills/evolution/evolution-export.py` | **来源**: design

**描述**: 增量导出在分析者消费 chunk 之前就推进了同步游标，导致“导出成功但知识提取失败”时不可恢复地跳过历史。脚本在解析新增条目后更新 processed_lines，并在写出 chunk 后立即保存 sync-state.json；而 sub agent 的分析是后续独立步骤。如果 sub agent 超时、被中止、权限失败或只处理了前几个 chunk，下一次 /evolution 从新游标开始，未分析内容不会再次出现，用户通常只看到一次成功的导出摘要而不知道知识已丢失。全量模式同样会先写入 last_full_sync，之后分析失败会使后续增量同步跳过整个历史。

**失败场景**: 运行 /evolution 产生多个 chunk，sub agent 在第二个 chunk 写库时超时；sync-state.json 已记录所有新增行。再次运行 /evolution 返回“无新内容”，剩余历史永远不再被提取。

**建议方案**: 将“已导出”和“已分析/已提交”拆成两个游标；只有所有 chunk 经成功确认、知识库事务提交并完成校验后才推进 committed cursor。为每次同步生成带 session/批次 ID 的 manifest，失败可重试；状态写入使用临时文件+原子替换，并明确向主 agent 返回 partial/failed 状态。

### 2. [MEDIUM] 知识库写入没有跨 sub agent 的事务与并发保护

**文件**: `docsV3/EXPORT_AND_ANALYSIS_DESIGN.md` | **来源**: design

**描述**: 系统只保护 export.py 的跨进程导出，不保护知识库及索引的读改写事务。多个触发入口都允许 sub agent 直接修改同一组 markdown 文件，且写入规则要求同时更新详情文件和 kb-index.md。两个同步任务并发时可以各自读取旧索引、分别追加后覆盖同一文件，造成条目丢失；或者一个任务把旧条目标为 [X]，另一个任务基于旧版本追加，最终索引与详情文件不一致。export.lock 无法覆盖这段临界区。

**失败场景**: 用户快速触发 /evolution 和 /growth-sync，两个 sub agent 同时读取 kb-index.md 并写入同一 facts.md/index；后写入者覆盖前者的追加，或索引显示已存在条目而详情文件没有它。

**建议方案**: 增加知识库级锁和事务协议：同步前获取 KB lock，写临时副本、校验索引引用与状态标记，再原子替换；或把知识条目存为 append-only/versioned records，由单一提交器合并。并发任务必须检测冲突而不是静默覆盖。

### 3. [HIGH] 草稿知识会被读取并形成错误自强化闭环

**文件**: `.claude/skills/evolution/rules/write.md` | **来源**: design

**描述**: [D] 并非隔离数据，而是允许被正常使用；同时提取器会把 assistant 的完整回答、thinking 摘要和工具摘要作为候选知识。用户不审核时，模型的错误推断会进入知识库，并在后续任务中作为“未验证但可使用”的上下文反复影响决策。没有待审核队列、TTL、置信度、来源强制绑定或自动回滚机制；“用户沉默”没有定义为拒绝，因而知识库会单调积累垃圾。

**失败场景**: 某次对话中 AI 错误地判断代理配置，用户没有回应确认；同步生成 [D]。后续任务按索引读取 facts.md，采用该配置并再次生成相同错误，冲突规则还可能把正确旧条目标为 [X]。

**建议方案**: 将 [D] 放入默认不可用于决策的 quarantine/pending 区，只有显式审核动作才能提升为 [V]；保存来源 entry/session、证据和置信度，设置过期/复核期限。冲突时禁止自动废弃 [V]，应并列保留并要求人工或独立验证器裁决。

### 4. [HIGH] 内容摘要策略会静默丢掉关键证据

**文件**: `docsV3/EXPORT_AND_ANALYSIS_DESIGN.md` | **来源**: design

**描述**: 分页和过滤以粗略字符系数及固定摘要窗口为正确性依据，但摘要会直接删除知识证据。tool_result 只保留开头和错误尾部，成功命令的关键输出若位于中间会消失；超大 entry/turn 还会按预算截断 text。因而“无 chunk 超过上限”只证明大小估算成立，不证明所有事实都可被分析，且验收只检查 token 估算而不检查语义覆盖。

**失败场景**: 一次安装命令输出在前 500 字是进度信息、关键版本/路径在中间、末尾无错误；导出后 chunk 不包含该事实，sub agent 得出错误或缺失的环境知识，而后续同步无法恢复已被摘要丢弃的原文。

**建议方案**: 不要用固定首尾截断作为唯一证据压缩；先按结构提取命令结果中的版本、错误、路径和变更，保留原始内容引用/哈希以便回溯。对被截断条目标记 incomplete 并允许按 entry 二次取原文；用事实召回/覆盖测试而非只测 token 范围。

### 5. [MEDIUM] 多 session 聚合不保证时间顺序

**文件**: `.claude/skills/evolution/evolution-export.py` | **来源**: design

**描述**: 设计宣称按时间顺序分页，但实现按文件修改时间拼接 entries 后直接分页，没有跨 session 的 timestamp 排序。多个 session 文件的 mtime 顺序不等于事件发生顺序，尤其是旧 session 被补写或并行 session 交错时，知识提取会把后发生的状态放在前面，产生错误的状态演进和冲突判定。

**失败场景**: 用户在两个并行 session 中先后修改同一配置；较早 session 因后台写入而 mtime 更新，导出顺序变为 session B、session A。sub agent 按 chunk 顺序提取并把旧状态当成最新状态，增量冲突处理可能把正确值标成 [X]。

**建议方案**: 为每个 entry 使用 timestamp 加稳定 tie-breaker 做全局排序，保留 session/file/line 作为来源；检测时间戳异常和跨 session 重叠，不能把文件 mtime 当事件时间。状态知识应要求明确事件证据和版本/时间。

### 6. [MEDIUM] [V] 的验证语义过宽且缺少范围与时效

**文件**: `.claude/skills/evolution/rules/write.md` | **来源**: design

**描述**: 状态标记的“验证”标准把历史工具输出和外部文档引用视为足以成为 [V]，但没有验证其时效、适用项目或因果关系。工具输出只能证明某次命令返回了某值，不一定证明该配置解决了问题；外部文档也可能对应另一版本。这样 [V] 的语义从“事实已被当前项目确认”退化为“曾经出现过证据”，一旦错误就会被读取规则无条件正常使用。

**失败场景**: 历史对话中的 node -v 输出来自另一个 shell/目录，或外部文档针对旧版本；同步把相关条目标为 [V]，后续 agent 按已验证事实操作当前项目，失败后却不会触发重新审核。

**建议方案**: 拆分 verified 状态为 observed/externally-sourced/project-verified，并强制记录命令 cwd、时间、版本、证据来源和适用范围；只有针对当前项目成功复现或用户明确确认才能进入可自动使用的状态。

### 7. [MEDIUM] sub agent 没有可观测且可恢复的完成协议

**文件**: `.claude/skills/evolution/commands/sync.md` | **来源**: design

**描述**: sub agent 是整个系统的实际执行者，但命令协议只要求“触发”并等待返回摘要，没有定义任务 ID、心跳、超时后的状态查询、幂等重试或提交回执。主 agent 无法区分 sub agent 尚未开始、静默失败、部分完成和已完成；而脚本状态又可能已前移，因此用户得到的摘要可能是成功/无新内容而非真实的知识库完成状态。

**失败场景**: 主 agent 成功派发 sub agent 后连接断开，sub agent 在脚本完成、知识库写入前退出；用户稍后再次运行同步，因游标已前移得到“无新内容”，且没有失败批次可检查。

**建议方案**: 建立可持久化的 job 状态（queued/running/partial/committed/failed）、批次 manifest、心跳和超时回收；主 agent 必须查询最终 commit receipt 后才报告成功。重试必须幂等，且失败批次的 chunk 与游标不可被正常增量路径跳过。

### 8. [CRITICAL] 增量游标无完整性校验：文件被截断/轮换/回滚时静默永久丢数据

**文件**: `<project-root>\.claude\skills\evolution\evolution-export.py` | **来源**: code

**描述**: sync-state.json 里存了每个文件的 sha256、mtime、processed_bytes（FileInfo 第112-121行，全量导出时在第848-856行写入），但增量导出（export_incremental 第936-974行）对已存在文件只用 `start_line = processed_lines + 1` 继续读，从不重新计算或比对 sha256/mtime。processed_lines 是物理行号游标，其正确性完全依赖『文件只增不减』这个未被验证的假设。

**失败场景**: Claude Code 对过长 session 会轮换/截断 JSONL 文件（或用户清空历史、从备份恢复、磁盘工具截断）。原文件 processed_lines=5000，新文件只有 80 行。下次增量执行 `parse_jsonl(file, 5001)` 时第213行 `if line_num < start_line: continue` 把所有行跳过，entries 为空 → 第949行 `continue`，游标不更新、无任何告警。新文件里 1-80 行的真实对话永远不被导出——静默、永久的数据丢失，且无任何机制触发全量重导。

**建议方案**: 增量导出前对每个已存在文件重新计算 sha256，与 state 中记录比对：若不同（说明文件被截断/轮换/回滚），回退为从 start_line=0 全量重导该文件（或至少告警并触发 --mode full），并重置其游标。同时可将 mtime/大小作为便宜的快速变化信号。

### 9. [HIGH] save_sync_state 非原子写入：半途崩溃/磁盘满导致状态损坏并触发全量重复导出

**文件**: `<project-root>\.claude\skills\evolution\evolution-export.py` | **来源**: code

**描述**: save_sync_state（第730-734行）直接 `open(state_file,'w')` + `json.dump`，没有临时文件+rename，也没有 fsync。load_sync_state（第682-727行）遇到 JSONDecodeError 会静默回退到 `_empty_state()`。

**失败场景**: 增量导出写完 chunk-inc-*.md 后，在写 sync-state.json 时进程被 kill / Ctrl-C / 磁盘满 / 断电，留下半截 JSON。下一次 `/evolution` 执行时 load_sync_state 捕获 JSONDecodeError → 返回空 state → 所有文件都被当作新文件（start_line=0）→ 把全部历史重新导出为 chunk-inc，知识库产生大量重复 [D] 条目，且增量游标整体重置。

**建议方案**: 改为原子写入：先写 `sync-state.json.tmp`，`f.flush()` + `os.fsync()`，再 `os.replace(tmp, final)`（同目录原子重命名）。这样任何中断只会留下完整的旧状态或完整的新状态，绝不会是半截文件。

### 10. [HIGH] 错误形状的行导致未捕获 AttributeError，整次导出崩溃（健壮性倒挂）

**文件**: `<project-root>\.claude\skills\evolution\evolution-export.py` | **来源**: code

**描述**: _try_extract_entry（第186-198行）只捕获 `json.JSONDecodeError`。若某行是合法 JSON 但非对象（如 `null`、`[]`、`123`、`"x"`），`entry.get('type')` 抛 AttributeError；若 entry 是对象但 `message` 为 null/字符串，extract_conversation_content（第257行 `msg = entry.get('message', {})`，第267行 `msg.get('content','')`）同样抛 AttributeError。二者都不在任何 try/except 内。

**失败场景**: JSONL 文件某一行是 `null`（或人工追加/尾部半写残留了一条 `123`，或某条 user/assistant 的 message 字段为 null/字符串）。`json.loads` 成功解析，随后 `entry.get` / `msg.get` 抛 AttributeError，沿 parse_jsonl 生成器 → list(parse_jsonl(...)) → export_full/export_incremental 一路冒泡到 main 的 `except Exception`，整个导出以 status=error 终止。结果：一条『格式合法但形状不符』的行比一条 JSON 损坏的行更致命——后者只是被跳过，前者炸掉全部导出。

**建议方案**: 在 _try_extract_entry 内对整体用 try/except (AttributeError, TypeError) 包裹，或在取字段前加 `isinstance(entry, dict)` 与 `isinstance(msg, dict)` 防御，遇到非法形状同样 `return None` 并打印 WARN，而不是让异常冒泡。

### 11. [MEDIUM] 超大轮次触发跨 chunk 时间乱序：更早的内容落到更晚的 chunk 文件

**文件**: `<project-root>\.claude\skills\evolution\evolution-export.py` | **来源**: code

**描述**: paginate_entries（第535-574行）中，当某个 turn 超过 max_tokens 且此时 current_chunk 尚小于 min_tokens 时，第541行的 `if current_chunk and current_tokens > min_tokens` 不成立，current_chunk（时间上更早的轮次）不被 flush；紧接着第548-550行把该超大 turn 的 sub_turns 直接 append 进 chunks，然后 continue。之后 current_chunk 继续积累，最终在循环末尾才 flush 到 chunks 尾部。

**失败场景**: 轮次 T1(10K)、T2(250K，超过200K上限)、T3(10K)。处理 T2 时 current_chunk=[T1] 因 10K<40K 不 flush，T2 被拆成 sub_turns 先 append。最终 chunks=[T2a, T2b, [T1,T3]]，写出的 chunk-00/01 是时间上居中的 T2，chunk-02 反而包含最早和最晚的 T1+T3。下游按文件名顺序读 chunk 时，历史顺序被打乱，可能把因果颠倒的内容混入知识库。

**建议方案**: 遇到超大轮次时，无论 current_chunk 是否达到 min_tokens，都应先把 current_chunk flush 进 chunks（保持时间顺序），再 append sub_turns；或统一在最终用时间戳对 chunk 排序兜底。

### 12. [MEDIUM] token 估算系统性偏低，200K『硬上限』可被实际超出 1.3~2 倍导致下游截断

**文件**: `<project-root>\.claude\skills\evolution\evolution-export.py` | **来源**: code

**描述**: estimate_tokens（第382-399行）对代码/英文用 4 字符/token，对 CJK 用 1.0 字符/token；is_wide_char（第362-379行）把 emoji（如 👍 U+1F44D 的 east_asian_width 为 W）当作 1 字符=1 token。实际 BPE 分词中 emoji 常为 2-3 甚至更多 token，代码实际常约 3 字符/token。估算误差会被 MAX_CHUNK_TOKENS 用来强制『硬上限』（split_large_turn 第474-508行）。

**失败场景**: 一个以代码/表情为主的大轮次，估算 200K tokens 但实际约 260K+。脚本认为已在上限内不再拆分，写出的 chunk-*.md 实际超出下游模型的上下文窗口，读取该 chunk 的 sub agent 在提取知识时窗口截断，chunk 尾部内容被静默丢弃。所谓『200K 硬上限』只对估算值成立，不是对真实 token 数成立。

**建议方案**: 降低估算乐观度：代码/英文系数降到 3~3.5，emoji/多字节字符按 2~3 token 计；或在 split_large_turn/truncate_entry 处对 max_tokens 施加安全系数（如按 0.7 折算），确保真实 token 数不超过窗口。

### 13. [MEDIUM] 全量导出把全部 JSONL 一次性载入内存，大历史可能 OOM

**文件**: `<project-root>\.claude\skills\evolution\evolution-export.py` | **来源**: code

**描述**: export_full（第838-844行）对每个文件 `parse_jsonl_full` 返回完整 entries 列表（第220-236行）并全部 `all_entries.extend`，最后在内存中一次性分页。无流式处理，也无条数上限。

**失败场景**: 一个长期活跃项目有几十个 session JSONL，单个文件可达几十~上百 MB。全量导出把所有 user/assistant 条目（含 tool_result 摘要、thinking 摘要）全部驻留内存，内存占用可达数 GB，在内存受限环境被 OOM killer 终止——此时 chunk 文件写了一半、sync-state 未写，叠加问题2/3，留下残缺输出与脏状态。

**建议方案**: 改为按文件流式聚合或分批处理：先按文件逐个收集并估算，达到 target_tokens 就落盘一个 chunk；或至少对大文件做分块读取，避免一次性 list() 全部 entries。

### 14. [HIGH] 游标在知识消费前提交造成不可恢复的数据丢失

**文件**: `.claude/skills/evolution/evolution-export.py` | **来源**: data

**描述**: 导出脚本在分析代理消费 chunk 之前就提交同步游标；脚本成功但 sub agent 随后崩溃、被取消或知识库写入失败时，下一次增量同步会从已提交的末尾开始，直接返回“无新内容”，导致这批对话永久不会再次进入分析。全量导出同样在返回前写入状态，而设计流程把分析放在脚本之后。应将状态拆成 pending/committed 两阶段，只有 chunk 已被可靠消费并完成知识库写入后才推进游标；同时保存 chunk manifest/checksum，失败时可重放。

**失败场景**: 运行 sync 时脚本在第 1013 行保存了 processed_lines，随后 sub agent 在读取 chunk 或写知识库前被终止；再次运行 sync 时第 939 行从旧内容之后开始，已提交的对话不再生成 chunk。

**建议方案**: 实施导出-消费事务：先写不可变批次和 pending state，知识库写入成功后原子提交游标；启动时发现 pending 批次必须重放或明确回滚。

### 15. [MEDIUM] 文件重写或截断会绕过游标校验并漏数据

**文件**: `.claude/skills/evolution/evolution-export.py` | **来源**: data

**描述**: 增量路径完全不使用已有 FileInfo 的 sha256、mtime、processed_bytes 来验证文件是否仍是原来内容；对已存在文件还只更新 mtime/字节数，不更新 sha256。若 JSONL 被编辑器重写、会话迁移、轮转后复用原文件名，旧游标会落在新内容的错误位置，既可能漏掉替换内容，也可能把新内容与旧游标拼接。文档声称会检测截断，但实现没有行数减少检查。

**失败场景**: init 后用户把某个已处理的 JSONL 在游标之前插入一条记录，或重写该文件后保留超过 processed_lines 的行数；sync 仍从 processed_lines+1 解析，插入/替换的记录被跳过。若文件缩短，解析可直接得到空新增内容而不发出截断错误。

**建议方案**: 在增量解析前校验文件身份和前缀（size、mtime 仅作提示，需前缀 hash/稳定记录 ID）；发现截断、重写或 hash 变化时 fail closed，生成该文件的重建批次，而不是继续使用旧游标。

### 16. [MEDIUM] 状态丢失会绕过 init 防护并制造全量重复

**文件**: `.claude/skills/evolution/commands/init.md` | **来源**: data

**描述**: 状态文件不存在或损坏时 load_sync_state 返回空状态；init 的前置检查只看 last_full_sync 是否为空。因此删除/损坏状态文件不会阻止重新初始化，且 init 文档明确知识库文件不会清空，结果是全量历史再次写入已有知识库。状态文件部分损坏时还会逐项丢弃非法 FileInfo，形成隐式的“部分全量重导”。

**失败场景**: 已有知识库和已同步历史，用户误删 sync-state.json 后执行 /evolution-init；status 返回空状态，前置检查走“首次初始化”，full 从头导出，sub agent 将相同事实追加到未清空的 facts/pitfalls 等文件。

**建议方案**: 把状态丢失视为高风险恢复场景而非首次运行：要求显式 `--rebuild`/用户确认，默认拒绝；用独立且冗余的初始化标记或批次日志检测已有知识库，并提供基于批次 ID 的幂等写入。

### 17. [MEDIUM] 导出锁未覆盖知识库事务导致并发覆盖与重复

**文件**: `.claude/skills/evolution/evolution-export.py` | **来源**: data

**描述**: export.lock 只保护 Python 导出和状态文件，不保护后续 sub agent 对知识库的读取-去重-写入事务。两个命令可以先后拿到导出锁、各自生成全量/增量批次，然后并行修改同一组 Markdown；两边都基于旧 kb-index 判断为“全新”，会互相覆盖或重复追加。

**失败场景**: 用户确认两次 /evolution-init，或 init 与 sync 的 sub agent 重叠：两个分析代理同时读取相同 kb-index 和 facts.md，分别追加相同条目并写回；最后写入者还可能覆盖前一个代理的更新。

**建议方案**: 把知识库更新纳入同一批次锁/事务，或使用带版本校验的原子读改写（CAS）；同一项目只允许一个 active analysis batch，其他任务排队或重试。

### 18. [MEDIUM] 大规模输入触发全量内存爆炸且不可恢复

**文件**: `.claude/skills/evolution/evolution-export.py` | **来源**: data

**描述**: 全量导出把所有文件的所有 ConversationEntry 和内容块先放入 all_entries，再统一分页；增量也把所有新增 entry 收集到 list。对 10GB JSONL 或多个大型 session，这会形成与输入规模近似甚至更高的 Python 堆内存占用，同时全量还为每个文件再次完整计算 SHA-256。脚本可能 OOM/被系统杀死，且若在状态提交/分析边界发生，用户只能得到不完整批次。

**失败场景**: 项目有 10 个各约 1GB 的 session 文件，执行 full；解析结果、截断后的字符串、列表和分页结构同时驻留内存，进程在完成 chunk 输出前被杀死，无法完成一次可消费的导出。

**建议方案**: 改为按文件/轮次流式处理并增量写批次 chunk，使用外部排序或按文件独立批次，避免 all_entries 全量驻留；提供内存/磁盘配额和可恢复 checkpoint，避免再次从头扫描。

### 19. [MEDIUM] 可变 chunk 路径允许批次交叉污染

**文件**: `.claude/skills/evolution/evolution-export.py` | **来源**: data

**描述**: chunk 文件没有批次 ID、不可变命名或消费确认；incremental 的 chunk-inc-00.md 会被下一次增量覆盖，cleanup 也能在分析代理仍使用路径时删除它。导出锁只在 Python 调用期间有效，sub agent 读取期间不持锁。因此一个慢分析与下一次 sync/cleanup 重叠时，代理可能读到另一批内容、读到缺失文件，或把结果归因到错误批次。

**失败场景**: 第一次 sync 生成 chunk-inc-00.md 后 sub agent 尚未读完；用户触发第二次 sync 或 cleanup，文件被覆盖/删除；第一次代理继续读取同一路径，得到混合内容或文件不存在，却可能仍写入知识库。

**建议方案**: 每次导出使用唯一 batch 目录和不可变 chunk 名称，返回 manifest；消费完成后再清理，并以批次 lease/ack 防止覆盖或删除未确认的文件。

### 20. [CRITICAL] 增量游标先提交、知识提取后执行，提取失败导致对话永久丢失

**文件**: `<project-root>\.claude\skills\evolution\evolution-export.py` | **来源**: ux

**描述**: export_incremental 在脚本内就先 save_sync_state 推进游标（processed_lines / last_incremental_sync），而真正产生价值的『逐 chunk 提取知识并写回知识库』是由 sub agent 在脚本返回之后才执行的。二者非原子，且游标先落盘、无回滚。

**失败场景**: 用户运行 /evolution。sub agent 执行 evolution-export.py --mode incremental 成功：脚本末尾（第 1012-1013 行）立即写回 sync-state.json，把 processed_lines 推到最新行、记录 last_incremental_sync。随后 sub agent 才开始 sync.md 步骤 3-4 的『提取事实/踩坑并更新知识库』。若这一步失败——sub agent 崩溃/被父进程超时杀死、命中 token 上限被截断、或模型中断——游标已经持久化，但知识从未写入。下一次 /evolution 从新的 processed_lines 继续，这批对话被当作『已处理』永久跳过，知识静默丢失，且无任何报错或回滚。

**建议方案**: 把游标推进与知识提取解耦并原子化：export 阶段只产出 chunk 与『待提取』标记（不写 sync-state），知识库写入成功后再 commit 游标；或让 sub agent 提取完成后再回写游标。至少要在提取失败时把 sync-state 回滚到本次同步前的快照，并在摘要中显式报告『导出成功但提取失败』。

### 21. [HIGH] init 前置检查读取错误的信号源，且会被它本应防护的状态损坏所反杀

**文件**: `<project-root>\.claude\skills\evolution\commands\init.md` | **来源**: ux

**描述**: v3.9.0 新增的 /evolution-init 前置检查只检查 .evolution/chunks/sync-state.json 的 last_full_sync（导出游标），而非知识库本身。load_sync_state 对文件缺失/JSON 损坏一律回退到空状态（last_full_sync=null），status 模式又永远返回 status:success。

**失败场景**: 场景 A：sync-state.json 被删/损坏（磁盘故障、手动清理、cleanup 误删、git 操作）→ load_sync_state 返回空状态 → init 前置检查看到 last_full_sync=null，误判为『首次安装』，跳过 Y/N 确认直接 --mode full，覆盖 chunk 并重置增量游标，产生重复条目且用户毫无察觉。安全机制被它要防护的损坏形态直接绕过。场景 B（反向）：evolution/knowledge-base/ 被手动清空但 sync-state.json 完好 → 前置检查提示『已有初始化记录』，但知识库实际为空；init.md 声称支持的『知识库被清空后』场景无法正确触发，用户无法重建。

**建议方案**: 前置检查改为检测知识库本身（evolution/knowledge-base/kb-index.md 是否存在 + 条目数/校验和），而非导出游标。对 sync-state.json 损坏/缺失要显式告警，并区分『全新安装』与『状态损坏』两种状态——状态损坏同样必须强制 Y/N 确认，绝不允许静默放行。

### 22. [HIGH] 两棵知识库树字节级重复，新树索引自指旧路径，导致读写错位与静默分叉

**文件**: `<project-root>\evolution\knowledge-base\kb-index.md` | **来源**: ux

**描述**: 磁盘上同时存在 evolution/knowledge-base/ 与 evolution-manual/knowledge-base/ 两棵完全相同的知识库树（diff 无差异）。config.yaml 与 read.md 指向前者，但前者自己的 kb-index.md 声明『位置：evolution-manual/knowledge-base/kb-index.md』，facts.md 也写『项目级存储：evolution-manual/knowledge-base/』及已删除的『双系统设计 evolution-manual + evolution-auto』。

**失败场景**: AI 按 read.md 读 evolution/knowledge-base/kb-index.md，随后若依索引内部路径去定位/回写详情文件，会落到 evolution-manual/ 那棵旧树。之后两棵树被不同的同步分别更新，静默分叉：用户在 evolution/knowledge-base/（config 指定的正确位置）里看不到本应写入的新内容，却能在旧目录里看到。同时内容停留在 2026-07-24 的 v2.1.0，描述的是 v3.0.0 已删除的架构，属于自相矛盾的历史残留。

**建议方案**: 归档或删除 evolution-manual/ 旧树（或明确主从关系），把 kb-index.md / facts.md 中的自指路径统一改为 evolution/knowledge-base/，并建立『单一事实来源』约束，禁止再整树复制知识库。

### 23. [MEDIUM] 命令名与定义错位：文档中的 /evolution 无对应注册名，/kb-sync 等三个命令是幻影

**文件**: `<project-root>\.claude\skills\evolution\commands\sync.md` | **来源**: ux

**描述**: commands/ 目录下只有 init.md（name: evolution-init）和 sync.md（name: evolution-sync）两个定义。但 SKILL.md 与 sync.md 命令表都让用户输入 /evolution、/kb-sync、/growth-sync、/alignment-sync。后三个没有任何 .md 定义，/evolution 与 frontmatter 的 name: evolution-sync 不一致。

**失败场景**: 用户输入 /kb-sync、/growth-sync、/alignment-sync，因无定义而不被识别、无任何响应（用户却被告知这些命令可用）。/evolution 的注册名很可能是 /evolution-sync 而非文档所写 /evolution。更关键的是模糊匹配场景：用户敲 /evo，候选实际是 /evolution-init 与 /evolution-sync，误选 init 即进入前置检查流程，叠加 finding 2 的绕过风险，可导致静默覆盖。

**建议方案**: 为 /kb-sync、/growth-sync、/alignment-sync 建立真实定义或从文档删除；统一 sync.md 的 name 与文档命令名（name 改为 evolution 或文档统一写 /evolution-sync），消除模糊匹配误触面。

### 24. [MEDIUM] 相对路径 --project-path=. 依赖调用方 cwd，sub agent cwd 复位时定位到错误项目

**文件**: `<project-root>\.claude\skills\evolution\commands\init.md` | **来源**: ux

**描述**: init.md / sync.md 要求执行 `python .claude/skills/evolution/evolution-export.py --mode full`，脚本路径与 --project-path 均用相对路径（默认 .），compute_project_hash 据此算项目 hash。而 sub agent 的 Bash cwd 在调用间会被复位。

**失败场景**: 若 sub agent 执行脚本时 cwd 不是项目根（<project-root>），compute_project_hash('.') 算出错误 hash，导致：要么『未找到 JSONL 文件』报错；更糟的是找到别的项目的 JSONL，把别的项目历史导出成 chunk 写进当前项目的 .evolution/chunks/，污染/覆盖本项目的 chunk 与 sync-state。init 前置检查同样会因读错路径读到不存在的 sync-state.json → last_full_sync=null → 绕过确认。

**建议方案**: 在命令文档中硬编码绝对项目根（--project-path <project-root>，脚本用绝对路径），或让脚本基于自身 __file__ 解析项目根，不再依赖调用方 cwd。

### 25. [MEDIUM] 导出包含当前会话自身（含命令自身脚本输出）污染知识库，而真正分析的 sub agent 会话反被排除

**文件**: `<project-root>\.claude\skills\evolution\evolution-export.py` | **来源**: ux

**描述**: find_jsonl_file 只 glob 顶层 *.jsonl，当前主会话（用户敲 /evolution-init 或 /evolution 的那次）就在其中，且会被全量导出；而真正执行提取的 sub agent 会话在 subagents/ 子目录被 M4 有意排除。

**失败场景**: 全量导出会把『用户运行 /evolution-init + 助手输出的一大段脚本 JSON 结果』当作历史事实/踩坑抽进知识库，制造关于 evolution 自身操作的元记录；而 sub agent 实际的分析过程永不入知识库。结果方向正好相反：『包装层的命令回显』入知识库，『干活的分析内容』系统性缺失。叠加每次同步都再次导出上一次同步的记录，产生自指的元污染。

**建议方案**: 导出时过滤当前会话文件及已知的 evolution 自举命令产物（至少对 tool_result 里的脚本输出做抑制）；重新评估排除 subagents 的策略——要么一并导出 sub agent 产物，要么在文档中明确说明为何排除，避免知识库系统性缺失分析过程。

### 26. [CRITICAL] 卸载命令 `rm -rf evolution` 会误删整个项目/知识库，且无备份、无确认

**文件**: `docsV3/INSTALLATION_GUIDE.md` | **来源**: docs

**描述**: 6.1 完全卸载章节给出 `rm -rf evolution`（第271行）用于"删除知识库"，但知识库实际位置是 `evolution/knowledge-base/`，删除的是整个 `evolution/` 目录。该命令是裸相对路径、无 `cd` 前置说明、无备份提示、无 `--dry-run`、无二次确认。而知识库默认不纳入版本控制（除非用户手动执行 7.2 的 git add），`rm -rf` 即永久丢失。

**失败场景**: 本仓库的项目根目录就叫 `evolution`（<project-root>）。用户若在父目录 E:\<parent-dir>\ 下执行卸载脚本，`rm -rf evolution` 会删除整个项目（含全部源码、docsV3、git 历史）。即使从项目根目录执行，也会删除 `evolution/` 子目录下的全部知识库内容且无法恢复。6.2 的"保留知识库"方案只有读完全文才看到，新手按 6.1 顺序执行就已造成不可逆损失。

**建议方案**: 改为删除精确路径 `rm -rf evolution/knowledge-base/`；在命令前强制要求确认并先备份（如 `cp -r evolution/knowledge-base evolution/knowledge-base.uninstall.backup`）；明确标注"必须在项目根目录执行"；增加 `--dry-run` 或交互确认提示；移除 `rm -rf` 改为先 `rm -r` 列出将删除内容。

### 27. [HIGH] V2→V3 迁移把备份放在即将被删除的目录内，且与版本历史里的迁移路径自相矛盾

**文件**: `docsV3/INSTALLATION_GUIDE.md` | **来源**: docs

**描述**: 5.1 升级指南（第236-253行）：先 `cp -r evolution-manual/knowledge-base evolution-manual/knowledge-base.v2.backup`（备份落在 evolution-manual 内部），再 `mv evolution-manual/knowledge-base/*.md evolution/knowledge-base/`，最后 `rmdir evolution-manual/`。但备份目录 `knowledge-base.v2.backup` 仍在 evolution-manual 内，`rmdir` 必然失败。同时 VERSION_HISTORY.md v3.0.0（第231-240行）给出的迁移命令是 `mv evolution-manual evolution`（整体重命名），两条迁移路径互相矛盾。

**失败场景**: 用户按 5.1 操作：`rmdir evolution-manual/` 因备份仍在内而失败；用户遂改用 `rm -rf evolution-manual/` 强行清理，把唯一的 V2 知识库备份 `knowledge-base.v2.backup` 一并删除，V2 历史知识全部丢失。若用户改按 VERSION_HISTORY 的 `mv evolution-manual evolution` 操作，则 5.1 里的 `evolution-manual/` 已不存在，两条指引无法同时成立，升级用户必然卡在自相矛盾的步骤上。

**建议方案**: 统一迁移方案为 VERSION_HISTORY 的 `mv evolution-manual evolution`（整体重命名，天然保留原内容）；若保留 5.1 的文件级迁移，备份必须写到 evolution-manual 之外（如 `cp -r evolution-manual/knowledge-base ./knowledge-base.v2.backup`），且删除旧目录改用带内容的显式 `rm -rf` 前先校验备份存在。

### 28. [HIGH] "导出全部对话、无遗漏、防止采样"是虚假承诺：脚本按设计截断内容并排除 subagents 转录

**文件**: `docsV3/EVOLUTION_RULES_AND_LOGIC_V3.md` | **来源**: docs

**描述**: EVOLUTION_RULES 5.3 声称"✅ 脚本导出全部对话，无遗漏"，VERSION_HISTORY v3.7.0 声称"防止采样导致历史对话丢失"。但 EXPORT_AND_ANALYSIS_DESIGN.md 2.2 明确定义了内容截断（thinking 保留约30%、tool_use 约40%、tool_result 约20%，并各截前N字），4.2 明确 `find_jsonl_file` 只 glob 顶层 `*.jsonl`、"不进入 subagents 子目录"。截断和目录排除本身就是采样/遗漏。

**失败场景**: Claude Code 的 subagent 转录存放在 `~/.claude/projects/<hash>/subagents/`，正是 Evolution 自身 sub agent 分析工作的发生地，这些对话被静默排除。用户深信"全部导出"，但包含关键踩坑/决策的 subagent 会话（如某次 sub agent 分析中发现的错误原因）永远不会进入知识库，用户也无从得知被漏掉。截断则导致 tool_result 的完整报错栈、thinking 的后半段推理被丢弃，违背"无遗漏"承诺。

**建议方案**: 将措辞改为"导出主会话对话（去噪 + 摘要截断，subagent 转录默认排除）"，并说明排除 subagents 的理由（避免 Evolution 自我摄取形成强化循环）。若确需完整，应提供 `--include-subagents` / `--no-truncate` 选项；在摘要中如实报告被截断/被排除的条目数。

### 29. [MEDIUM] sync-state.json 的 `version` 冻结在 3.4.0，v3.8.0 改动导出逻辑却未触发状态迁移，版本语义易被误读

**文件**: `docsV3/EXPORT_AND_ANALYSIS_DESIGN.md` | **来源**: docs

**描述**: 4.6 说明 `version` 字段记录"数据结构/导出逻辑版本号，当前 3.4.0，用于后续版本的旧状态迁移"。但 v3.8.0（4.9）已实质改变导出逻辑（文件锁、一致性校验、find_jsonl_file 行为、不再输出 filtered_entries），`version` 仍停留在 3.4.0，从未递增，导致"用于旧状态迁移"的机制形同虚设——旧状态文件不会被检测为需要迁移。同时文档版本已是 3.9.0，与数据版本 3.4.0 并存，虽有一条"语义独立"注释，但极易被忽略。

**失败场景**: 用户从 v3.4.0 升级到 v3.9.0，旧的 sync-state.json（含旧的 file_info/stats/export_history 结构）被 `load_sync_state` 容错回退到空状态，触发一次非预期的全量重导出；或用户查看 sync-state.json 看到 `version: 3.4.0`，误判自己的 Evolution 停留在 3.4.0，尝试寻找"3.4.0→3.9.0 升级步骤"而困惑。由于 version 从不随导出逻辑变更而递增，任何基于该字段的自动迁移逻辑都不会触发。

**建议方案**: 当导出逻辑/schema 变更时同步递增 `version`（例如 v3.8.0 应写到 3.8.0），并在 `load_sync_state` 中按 version 做显式迁移；或在文档显著位置用示例说明"3.9.0 是文档版本，3.4.0 是数据版本"，避免只在一处小字注释。

### 30. [MEDIUM] "静默运行 / 人类无感 / 不需要用户主动干预"与实际纯手动触发设计自相矛盾

**文件**: `docsV3/PROJECT_BACKGROUND.md` | **来源**: docs

**描述**: PROJECT_BACKGROUND.md 4.1 描述系统"基本是静默运行…由 sub agents 在后台静悄悄地运行…人类基本无感"，核心特性列表又写"人类无感：不需要用户主动干预"，同时却又列"手动触发：用户也可以主动触发"。而 VERSION_HISTORY v3.0.0 明确"删除 auto 版本，只保留手动触发版本"，EXPORT_AND_ANALYSIS_DESIGN.md 第1113行还把"自动触发"列为"未来优化方向"。实际系统完全依赖用户手动输入 `/evolution` 或 `/evolution-init`，没有任何自动后台触发。

**失败场景**: 新用户读完项目背景后，以为装好后系统会自动在后台沉淀知识，于是从不手动触发 `/evolution`，几周后发现知识库几乎为空——这段时间的对话从未被导出/分析。"不需要用户主动干预"与"手动触发"在同一段落并列，用户无法判断到底要不要动手，最终按更省事的理解（自动）行事，导致知识长期未同步。

**建议方案**: 删除"静默运行/人类无感/不需要主动干预"等暗示自动化的表述，统一为"手动触发，sub agent 后台执行，不污染主会话"；如需自动化，应明确标注为未实现的规划项而非现状。

### 31. [MEDIUM] 增量同步的文件截断/轮转检测未落地：记录 sha256/mtime/total_lines 但算法描述未使用，可能静默漏同步

**文件**: `docsV3/EXPORT_AND_ANALYSIS_DESIGN.md` | **来源**: docs

**描述**: 4.6 记录了 `sha256`/`mtime`/`total_lines`/`processed_bytes` 等校验字段，3.1 边界情况表声称"JSONL 文件被截断（行数减少）→ 警告用户，建议全量重新导出"。但 3.1 的"增量识别算法"只描述"读取 processed_lines → 从 processed_lines+1 起解析 → 有新条目则增量，否则跳过"，未说明如何用 sha256/mtime/total_lines 检测文件被整体重写或轮转。

**失败场景**: Claude Code 在会话整理/归档时可能重写或截断 JSONL。若文件被截断到行数 < processed_lines，增量从 processed_lines+1 开始已越过 EOF，返回 0 条新记录，脚本按"无新条目则跳过"静默结束，不产生任何警告。用户以为同步成功，实际该文件的新增对话被永久漏掉（下次游标仍指向越界位置），边界表承诺的"警告用户"并未实现。

**建议方案**: 在增量导出前用记录的 sha256/mtime/total_lines 与当前文件比对：发现 total_lines < processed_lines 或 mtime 突变/内容哈希改变且行数减少时，按文档所述显式警告并建议全量重导出，而非静默跳过；在算法描述中补上这一校验步骤。

### 32. [LOW] chunk 数量与 token 估算多处自相矛盾（90K 目标 vs ~136K 均值 vs 140-150K 实际；371K/90K≈4.1 却称 5-6 个）

**文件**: `docsV3/EXPORT_AND_ANALYSIS_DESIGN.md` | **来源**: docs

**描述**: 2.3 设目标 90K token 并写"约 270KB 文本，按 3 chars/token"；但 4.4 的 estimate_tokens 是英文 4 字符/token、CJK 1.0 字符/token，与"3 chars/token"不一致。5.1 成本表写"371K = 5-6 个 chunk × ~136K avg"，而关键变更一节写"90K 估算、实际 140-150K"，2.2 又写"371K/90K ≈ 4.1，实际 5-6 个"。同一文档对"单个 chunk 实际多大"给出了 90K/136K/140-150K 三个互斥数字。

**失败场景**: 用户想评估 sub agent 每页实际消耗以判断自己的模型窗口是否够用：看 2.3 认为每 chunk 约 90K，看 5.1 认为是 ~136K，看关键变更认为是 140-150K。若用户实际窗口较小（如 200K 而非 1M），以 90K 为预期却收到 ~150K 的 chunk，叠加分析指令/知识库读写/输出后可能逼近窗口上限导致截断或分析质量下降。数字矛盾让人无法可靠规划。

**建议方案**: 统一术语，区分"估算 token（90K 目标）"与"实际 token（约 140-150K，含 CJK 修正系数 1.68）"，在 5.1 成本表用一致口径；删除或修正"3 chars/token"这类与 estimate_tokens 不符的换算；对"4.1 却得到 5-6 个"补充明确解释（轮次边界 + min_tokens 合并导致 chunk 数高于数学除法）。

### 33. [MEDIUM] 日志重写会造成不可恢复的增量漏读

**文件**: `.claude/skills/evolution/evolution-export.py` | **来源**: evolution

**描述**: 增量同步只用物理行号作为游标，未检测已消费文件被截断、重写或内容替换。文件在 Claude 日志轮转、压缩或恢复后若行数仍大于旧游标，下一次同步会从旧行号之后读取，导致被替换部分永久跳过；即使 SHA-256 已保存，也没有用它做一致性判断或回退策略。

**失败场景**: 一次同步将某 JSONL 消费到第 10,000 行；随后日志轮转工具原地重写该文件并保留 12,000 行。下一次增量从第 10,001 行开始，重写后的前 10,000 行不会再次导出，知识库永久缺少其中新增或修正的事实。

**建议方案**: 每次增量前比较文件大小、inode/文件标识和旧 SHA-256；检测到截断或内容变化时从安全回退点重新扫描，或将文件版本纳入状态并重新导出受影响文件。不要只依赖行号。

### 34. [HIGH] 旧 chunk 残留导致重复摄入和无界膨胀

**文件**: `.claude/skills/evolution/evolution-export.py` | **来源**: evolution

**描述**: 导出器在写入新 chunk 前不清理旧的 chunk 文件。全量导出只覆盖当前编号范围，增量导出每次都从 chunk-inc-00.md 开始；旧文件会留在目录中，而命令流程没有规定逐次消费后清理或按本次 manifest 限定输入。长期运行会留下历史副本并制造重复分析。

**失败场景**: 第一次全量导出生成 chunk-00 至 chunk-20，第二次因历史筛选或文件变化只生成 chunk-00 至 chunk-03；chunk-04 至 chunk-20 仍存在。sub agent 按目录读取 chunk 文件时再次分析旧历史，重复条目持续写入知识库，且磁盘和候选上下文不断增长。

**建议方案**: 每次导出使用唯一 run 目录或先生成原子 manifest；消费端只读取该 manifest 列出的文件。成功消费后删除对应 chunks，或实现带版本/时间的归档与明确保留上限。

### 35. [HIGH] 未验证新知识可淘汰已验证事实

**文件**: `.claude/skills/evolution/.claude/skills/evolution/rules/write.md` | **来源**: evolution

**描述**: 冲突规则会无条件把旧条目标为[X]，即使新条目只是[D]、仅由 AI 提取且证据更弱；读取规则随后完全跳过[X]。这使一次错误或幻觉提取能够删除一个已经[V]验证的事实，违背“V优先”的设计。

**失败场景**: 知识库中已有经工具验证的[V]端口配置；新会话中的日志片段被错误解释为另一端口，生成[D]冲突条目。同步立即把旧[V]标为[X]，后续 AI 不再读取正确配置，按错误[D]配置执行任务并可能反复强化错误。

**建议方案**: 禁止[D]自动废弃[V]；冲突应并存为待审项，要求同等或更强证据和人类确认后才能替换。保留 supersedes/evidence/source 字段及可恢复历史。

### 36. [HIGH] 敏感对话在人工审核前已被持久化

**文件**: `.claude/skills/evolution/evolution-export.py` | **来源**: evolution

**描述**: 导出流程没有任何敏感信息识别、脱敏或人工阻断；它完整保留 user/assistant 文本，并且工具摘要明确保留 Bash 命令、Write 内容片段和 tool result 片段。所谓人工审核只要求条目标记为[D]，并不阻止机密先落盘到 .evolution/chunks 或知识库。

**失败场景**: 用户在对话中粘贴 API key，或 Bash 输出环境变量/个人路径；执行同步后原文进入 chunk，sub agent 将其提炼进 facts/pitfalls，随后项目目录被提交或共享，密钥和个人信息随知识库泄露。

**建议方案**: 在写 chunk 前做 secret/PII 检测并默认掩码，禁止把原始 tool result 和命令全文送入长期知识；对高置信敏感内容停止同步并要求人工确认。将“审核”设为写入前门槛，而不只是[D]标签。

### 37. [MEDIUM] 知识库写入阶段没有并发保护

**文件**: `.claude/skills/evolution/.claude/skills/evolution/commands/sync.md` | **来源**: evolution

**描述**: 导出锁只保护 exporter 的状态和 chunk 生成，不保护 sub agent 对知识库文件的读取、去重、追加和索引更新。命令流程在 exporter 返回后才分析/写 KB，因此两个后台 sub agent 可同时基于同一旧索引写入同一文件。

**失败场景**: 用户快速触发两次同步，或一个 init 与一个 sync 重叠；两个 sub agent 都读取同一 facts.md，均判断某条目不存在并追加，然后分别重写 kb-index.md。结果可能丢失后一方的索引更新、重复追加同一条目，甚至产生半写入文件。

**建议方案**: 为整个“导出后分析到 KB 提交”阶段增加项目级互斥锁；采用临时文件+原子替换、基于版本的 compare-and-swap，并在提交前重新读取索引和详情文件。

### 38. [MEDIUM] 知识库没有有效期和可审计的事实生命周期

**文件**: `.claude/skills/evolution/.claude/skills/evolution/rules/dedup.md` | **来源**: evolution

**描述**: 知识条目只有[D]/[V]/[X]三态，没有事实有效期、适用范围、来源、反例或复核时间；去重规则对相同信息只更新时间戳、对新信息追加，也没有主动发现过期内容或清理机制。长期运行后旧配置、旧决策和旧状态会与新条目并存，且旧[V]不会自动失效。

**失败场景**: 项目依赖、端口或发布流程在数月后改变；旧条目仍为[V]，新条目只是追加记录。新会话按“优先[V]”读取旧事实并执行已失效步骤；运行一年后文件继续增长，4.0.0 的清理只是规划而非当前保护。

**建议方案**: 为条目增加 source/session、scope、observed_at、reviewed_at、expires_at 和 supersedes；冲突按时间/范围/证据解析。实现可审计的 stale 标记、归档、容量阈值和恢复机制，并在过期条目未复核时阻止高风险使用。

### 39. [MEDIUM] 移除 Skill 后知识库静默失去维护能力

**文件**: `.claude/skills/evolution/.claude/skills/evolution/SKILL.md` | **来源**: evolution

**描述**: 维护能力完全封装在 skill、exporter 和 sub-agent 执行规则中；知识库本身没有自描述的同步协议、状态恢复说明或独立维护入口。移除/未加载 skill 后，剩余 Markdown 仍可被人看到，但不会自动发现新会话、更新索引、处理冲突或推进[D]审核，形成“知识库维护依赖自身维护系统”的自举断裂。

**失败场景**: 项目迁移到未安装该 skill 的新 AI 环境，或 skill 暂时被禁用；新会话能看到 evolution/knowledge-base，却没有触发路径和增量游标使用说明，于是继续使用旧[V]/[D]知识但不再同步，长期静默退化。

**建议方案**: 在知识库根目录提供独立、版本化的维护协议和最小恢复工具/manifest，记录最后同步、待审核、冲突和迁移步骤；把“无 skill 时只读/禁止假定新鲜”的安全行为写入入口文件，并提供可验证的导入导出恢复流程。

---

## 被反驳的发现（9 条）

1. **跳过坏 JSONL 行会让可恢复故障变成永久数据丢失**（design）— 反驳理由：代码机制属实：parse_jsonl 会跳过 JSON 解析失败的行（仅 WARN，返回 None），且 export_incremental 用 `new_processed_lines = entries[-1].line_no` 推进游标。但"可恢复故障变成永久丢失"这一核心主张不成立。关键点：(1) 瞬时的截断写入（半行）只可能出现在文件末尾——JSONL 是顺序追加写入，下一行必须先写完当前行的换行符才能写入，因此半行后面不可能跟完整行。而"坏行在末尾"这一真实情形，代码实际上处理正确：末尾半行解析失败后，entries[-1].line_no 指向它之前最后一条有效 entry，游标停在半行之前；下次同步 start_line=last_valid+1 会重新读到已补全的半行。若末尾半行是新内容中唯一内容（entries 为空），则 `if not entries: continue` 根本不更新游标，同样会重读。(2) 发现的失败场景（半行后跟完整行）与顺序追加语义矛盾，物理上不可发生。(3) 非瞬时的编码异常/永久格式坏行是"写入时已永久损坏"，重试/重放也无法恢复其内容，跳过它正是文档宣称的容错行为，不构成"可恢复数据丢失"。综上，"high 级、可恢复故障→永久丢数据"不成立，最多是防御性改进建议（如停止推进游标/持久化坏行），而非真实缺陷。
2. **导出不清理旧 chunk 文件：chunk 数量变少时残留过期文件被下游重复导入**（code）— 反驳理由：代码确实不会删除旧的 chunk 文件，但发现所依赖的失败链条未被仓库核实：导出结果显式返回本次生成的 chunks 清单，init/sync 指令要求“逐 chunk”分析，设计文档的模板也是传入单个 chunk 路径；仓库内没有下游按 `chunk-*.md` 或 `chunk-inc-*.md` glob 读取的实现或指令。因而旧文件是潜在的目录卫生问题，不能确认会被下游重复导入，更不足以判定为 high。
3. **subagent 对话 JSONL 被静默排除，子代理内的决策/踩坑永不进入知识库**（code）— 反驳理由：无法确认该发现为真实缺陷。代码在第154、159-161行明确将目标定义为“顶层 JSONL”，并使用 glob("*.jsonl")；仓库设计文档（docsV3/EXPORT_AND_ANALYSIS_DESIGN.md 第532-538行）及历史说明也明确记录这是有意排除 subagents，而非遗漏。更关键的是，在当前项目实际目录 <project-hash> 下未发现顶层 *.jsonl，只有 subagents/ 下的文件；因此当前场景不会“静默生成一个缺少子代理内容的成功知识库”，而会在第833-834行显式返回“未找到 JSONL 文件”错误。若同时存在顶层会话和 subagents，确实只导出顶层，但这符合已文档化的范围选择；该发现把“用户可能希望纳入子代理”当成了既定需求，未证明这是当前项目的契约。因此应判定为建议/产品范围争议，而非已确认 bug。
4. **坏行后的游标推进使可恢复错误变成永久丢失**（data）— 反驳理由：机制属实（parse_jsonl_full 的 last_entry_line_no 与 export_incremental 的 entries[-1].line_no+1 确实会让游标越过坏行），但失败场景自相矛盾且不可发生：(1) "写入中断"产生的坏行必在追加写日志的文件末尾，其后不存在"第101行正常"，游标停在99，坏行下次仍从100起重读，bug不触发；(2) "磁盘损坏"产生的中间坏行是永久性的，不存在"后来被修复"，数据在源头已丢失，任何游标策略（含推荐的重试队列）都无法恢复；(3) 唯一接近真实的场景是"崩溃撕裂写+续写同一会话文件"，但撕裂行尾部字节已物理丢失、内容不可恢复，丢失由撕裂写造成而非游标推进造成；(4) 这些 JSONL 是 append-only 会话日志、从不在原地修改，"修复第100行"前提不成立；即便人工修复，全量导出 export_full 会重新解析全部内容兜底恢复。因此"可恢复错误变永久丢失"是对不可恢复情形的误述，high 严重度被高估。
5. **状态可跨项目复用导致审计边界混淆**（data）— 反驳理由：反驳成立。(1) 失败场景描述与代码不符：/evolution-init 在前置 status 检查确认后执行的是 --mode full，而 export_full（第885-892行）会全新构造 SyncState，project_hash=compute_project_hash(当前B路径)、last_full_sync=now、files=B的jsonl文件，状态被完全重建，不会"仍携带 A 的初始化时间/游标"。(2) project_hash 在整个 skill 目录中只被写入/序列化/加载，从未被任何逻辑读取或校验（grep 确认无消费点），因此 stale 的 project_hash 不产生任何功能或审计后果。(3) 跨项目复制时 file 路径必然不同（不同 project_root → 不同 hash → 不同 ~/.claude/projects/<hash>/ 目录），增量同步对不匹配的 file_key 走 start_line=0，会正确重读 B 的全部历史并导出正确 chunk，无数据丢失/重复/错误导出，stale 旧 key 只是惰性残留。(4) last_incremental_sync 从未被读取，last_full_sync 仅被 init 前置提示使用。综上，唯一残余影响是复制后运行 init 会多弹一次"已有初始化记录"确认（轻微 UX 噪声），并非标题所称的"审计边界混淆"，且该场景本身（整树复制 .evolution 到新项目）非常规。medium 严重度不成立。
6. **SKILL 宣称的『重复错误→自动同步』是死代码：描述允许模型触发，命令却禁用模型执行**（ux）— 反驳理由：无法确认该发现为真实的“死代码”。`SKILL.md` 的自动触发只负责加载父 skill；`disable-model-invocation: true` 位于被链接的命令文档，限制的是该命令作为独立命令被模型自动调用，并不禁止父 skill 读取并执行其正文。更关键的是，`commands/sync.md:18-26` 已明确给出完整可执行路径：主 agent 触发 sub agent，sub agent 运行 `python .claude/skills/evolution/evolution-export.py --mode incremental`，并规定失败处理和摘要。因此“正文没有任何可执行同步路径”与现状不符。现存至多是父 `SKILL.md` 未明确写出“自动触发后读取 sync.md 并执行”的可发现性/文档清晰度问题；没有证据表明命令禁用属性会阻断该路径，也没有可确认的必然失败场景，不能维持 high 严重度。
7. **sub agent 静默失败，无端到端验证，用户看不到任何可操作的错误**（ux）— 反驳理由：未能确认该发现为代码库中的真实缺陷。脚本本身对异常返回 status:error 并以退出码 1 结束（evolution-export.py:1109-1118），且 sync.md 已明确要求 sub agent 遇到 status != success 停止并报告；sub agent 的执行结果由调用框架返回给主 agent，不能仅因这里没有额外的 kb-index 校验就推断必然被静默吞掉。status 在损坏/缺失状态时返回空状态是 status 查询的容错语义，增量模式无新内容返回 success 也是合法成功的 no-op，并非失败。该发现至多是对主 agent 编排层的未验证健壮性建议；仓库中没有能证明“错误未透传”或“用户看到完成”的实际调用链。
8. **重新执行 `/evolution-init` 会清空用户已人工验证的 `[V]` 条目，前置检查不覆盖此风险**（docs）— 反驳理由：无法确认该发现成立。实际执行规范 .claude/skills/evolution/commands/init.md 第19行明确写明“知识库文件不会被清空”，前置确认提示的已知后果是覆盖 chunk、重置游标和可能产生重复条目，而不是删除或降级既有条目；第31行的“所有条目标记 [D]”描述的是生成的初始条目，未证明会改写已有 [V]/[X] 条目。docsV3/EVOLUTION_RULES_AND_LOGIC_V3.md 的 4.1 是设计流程描述，不能单独证明实现会无差别覆盖现有知识库。因此给出的具体失败场景（既有 [V] 全部被重置为 [D]）在当前文件证据下不可复现；前置检查未统计 [V] 只能算潜在 UX 改进，不能判定为真实高严重度缺陷。
9. **冷启动索引没有可检索知识地图**（evolution）— 反驳理由：该发现把"轻量索引"这一文档化设计误判为路由缺陷，且其具体失败场景与现有规则自相矛盾。(1) 冷启动路由并非由索引逐条内容承担：read.md 步骤2 已硬编码 question→file 映射表（环境配置→facts.md、历史错误→pitfalls.md、更新状态→state.md、验收→alignment.md、决策→decisions.md），AI 遵循的是确定性映射而非"凭索引猜测"。发现声称"AI 只能凭类别猜测"不成立。(2) 失败场景与规则冲突：问"部署参数"按映射应读 facts.md，合规 AI 不会"误读 pitfalls.md"，该场景要求 AI 无视自身路由规则。(3) 轻量索引是刻意的设计约束：facts.md 明确写"kb-index.md（索引，200 行限制内）"、"索引+详情文件，详情文件按需读取"；SKILL.md 也写"入口 kb-index.md（<200 行）"。建议的逐条 ID/标题/关键词/manifest/二级索引会突破 200 行上限，是与既定架构的分歧而非 bug 修复。(4) 当前规模（总 16 条、单文件 <90 行）下，按需读 1-2 个文件即可覆盖，"全量读取突破渐进式上下文目标"被夸大——读取单文件本就是设计的粒度。真实存在的仅一处小瑕疵：read.md 措辞"基于索引中的分类摘要"，但索引概览表只有"类别/文件/条目数/更新时间"而无"摘要"，属文档用词不一致，不影响路由功能。综上，这是改进建议而非可复现的正确性缺陷，不足以判为 medium 真实问题。
