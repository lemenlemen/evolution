#!/usr/bin/env python3
"""
Evolution Export Script

导出和分析 Claude Code 对话历史，生成知识库输入文件。

版本：v3.10.0（引擎版本，最近实质修改于 V4.1.3 sha256 刷新修复）
系统版本：4.1.6（文档版本）
日期：2026-09-11

功能：
- 导出和分析 Claude Code 对话历史
- 双游标 + 批次状态机（防止数据丢失）
- sha256 完整性校验（防止截断/轮换）
- 原子写入 + 三级恢复链（防止状态损坏）
- 解析防御 + ParseStats（防止坏行崩溃）
- 流式化 + k-way 归并（防止 OOM）
- 全局时间排序 + session 感知（防止乱序）
- token 安全因子 1.5 + 字符守卫（防止低估）

VERSION 常量说明：
VERSION = "3.5.0" 是 sync-state.json 数据结构版本，与系统文档版本（4.1.6）独立。
引擎代码最近实质修改于 V4.1.3（sha256 刷新修复）；VERSION 常量为 sync-state schema 版本（3.5.0），与系统文档版本独立
"""

import os
import json
import hashlib
import shutil
import sys
import time
import re
import unicodedata
import heapq
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional, Literal, Any
from dataclasses import dataclass
from datetime import datetime

# 可选的 yaml 导入（用于从 config.yaml 读取配置）
try:
    import yaml
except ImportError:
    yaml = None


# =============================================================================
# 常量定义（从 config.yaml 读取， fallback 到默认值）
# =============================================================================

VERSION = "3.5.0"  # sync-state.json 数据结构版本（与文档版本号独立；M1 E4 升级为双游标 schema）

# 尝试从 config.yaml 读取配置
CONFIG_PATH = Path(__file__).parent / "config.yaml"


def get_project_root() -> Path:
    """
    获取项目根目录（从脚本位置推导，不依赖调用方 cwd）。

    evolution-export.py 位于 <root>/.claude/skills/evolution/，
    因此项目根 = 脚本位置向上 3 级（M1 E4 / F-6 路径锚定）。
    """
    script_path = Path(__file__).resolve()
    return script_path.parents[3]

def load_config():
    """从 config.yaml 加载配置"""
    if CONFIG_PATH.exists() and yaml is not None:
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except (yaml.YAMLError, OSError) as e:
            print(f"[WARN] config.yaml 解析失败，使用默认值：{e}", file=sys.stderr)
            return None
    return None

config = load_config() or {}

# 分页参数（v3.4.0 从 config.yaml 读取）
pagination = config.get('pagination', {})
TARGET_CHUNK_TOKENS = pagination.get('target_chunk_tokens', 90000)   # 90K tokens 目标
MAX_CHUNK_TOKENS = pagination.get('max_chunk_tokens', 200000)         # 200K tokens 硬上限
MIN_CHUNK_TOKENS = pagination.get('min_chunk_tokens', 40000)          # 40K tokens 最小值

# Token 估算系数（v3.4.0 从 config.yaml 读取）
token_estimation = config.get('token_estimation', {})
CJK_CHARS_PER_TOKEN = token_estimation.get('cjk_chars_per_token', 1.0)      # 中文/CJK 约 1.0 字符/token
NON_CJK_CHARS_PER_TOKEN = token_estimation.get('non_cjk_chars_per_token', 4.0)  # 英文/代码约 4 字符/token

# 同步引擎参数（M1 E6 从 config.yaml 读取）
sync_engine = config.get('sync_engine', {})
ESTIMATE_SAFETY_FACTOR = sync_engine.get('estimate_safety_factor', 1.5)   # token 估算安全因子
MAX_CHUNK_CHARS = sync_engine.get('max_chunk_chars', 800000)              # 字符数硬守卫 = max_chunk_tokens × 4

# cleanup 模式只删除这些文件，绝不 rmtree 整个目录（S5）
# 设计红线：sync-state.json 永不删除（状态文件误删将导致游标丢失）
CLEANUP_PATTERNS = ("chunk-*.md", "chunk-inc-*.md", "*.tmp")
# 保留：sync-state.json、sync-state.json.bak、sync-state.json.corrupt-* 不进清理

# 文件锁等待超时（秒）
LOCK_TIMEOUT = 120.0

# 批次配置（M1 E4：双游标 + 批次清单，修复 Critical 1；M1 E7：改从 config.yaml sync_engine 读取）
MAX_BATCH_RETRIES = sync_engine.get('max_batch_retries', 3)          # 批次重生成上限，超限 failed(retry-exhausted)
MAX_ANALYSIS_FAILURES = sync_engine.get('max_analysis_failures', 3)  # 批次分析失败上限，超限 failed(analysis-exhausted)（F-3/N-4）
KEEP_COMMITTED_BATCHES = sync_engine.get('keep_committed_batches', 20)  # committed 批次审计保留数，更早的修剪（游标在 files 中不受影响）


# =============================================================================
# 数据结构
# =============================================================================

@dataclass
class ContentBlock:
    """对话内容块"""
    type: Literal['text', 'thinking', 'tool_use', 'tool_result']
    text: str
    truncated: bool = False
    is_error: bool = False


@dataclass
class ConversationEntry:
    """对话条目（对应 JSONL 中的一行 user/assistant 记录）。

    M5: 由 ConversationTurn 重命名而来--此类代表单条记录而非一个完整轮次。
    """
    session: str
    line_no: int
    timestamp: str
    role: Literal['user', 'assistant']
    content: list[ContentBlock]


@dataclass
class FileInfo:
    """文件同步状态（M1 E4：双游标——exported 与 committed 解耦，修复 Critical 1）"""
    path: str
    sha256: str
    mtime: float
    size: int  # 物理文件大小（用于完整性校验，与 exported_bytes 语义分离）
    total_lines: int
    exported_lines: int  # 脚本已写入 chunk 的最后 entry 行号（1-based）
    exported_bytes: int  # 导出时的文件字节数
    committed_lines: int  # sub agent 确认入库的最后 entry 行号（commit 协议推进）
    committed_bytes: int  # commit 时文件字节数
    first_event_timestamp: Optional[str] = None
    last_event_timestamp: Optional[str] = None
    integrity_warnings: int = 0


@dataclass
class BatchRecord:
    """批次记录（M1 E4：每次导出产生一个批次，sub agent 分析后通过 --mode commit 显式确认）"""
    batch_id: str
    mode: str  # "full" / "incremental" / "migration"
    status: str  # "exported" / "analyzing" / "committed" / "failed"
    created_at: str
    updated_at: str
    reason: Optional[str] = None  # 失败原因：chunks-missing / retry-exhausted / superseded / deleted / migration-unverified / analysis-exhausted 等
    retry_count: int = 0  # 重生成次数，达 MAX_BATCH_RETRIES → failed(retry-exhausted)
    analysis_failures: int = 0  # 分析失败计数（F-3/N-4）
    time_range: Optional[dict] = None  # {"start": ..., "end": ...}
    line_ranges: Optional[dict] = None  # file → [start_line, end_line]；migration 批次为 null
    chunks: Optional[list] = None  # chunk 文件清单
    commit_receipt: Optional[dict] = None


@dataclass
class SyncState:
    """同步状态"""
    version: str
    last_full_sync: Optional[str]
    last_incremental_sync: Optional[str]
    project_hash: str
    files: dict[str, FileInfo]
    batch_seq: int = 0  # 批次号单调源
    batches: dict = None  # batch_id → BatchRecord

    def __post_init__(self):
        if self.batches is None:
            self.batches = {}

    def pending_batches(self) -> list[BatchRecord]:
        """未提交批次（exported/analyzing），按创建时间升序"""
        return sorted(
            (b for b in self.batches.values() if b.status in ("exported", "analyzing")),
            key=lambda b: b.created_at,
        )


@dataclass
class ParseStats:
    """JSONL 解析统计"""
    total_lines_read: int = 0
    blank: int = 0
    json_decode_errors: int = 0
    not_dict: int = 0
    wrong_type: int = 0
    extract_errors: int = 0
    extracted_entries: int = 0

    def to_dict(self) -> dict:
        return {
            "total_lines_read": self.total_lines_read,
            "blank": self.blank,
            "json_decode_errors": self.json_decode_errors,
            "not_dict": self.not_dict,
            "wrong_type": self.wrong_type,
            "extract_errors": self.extract_errors,
            "extracted_entries": self.extracted_entries,
        }


@dataclass
class IntegrityReport:
    """完整性校验报告（M1 E5，修复 Critical 2）"""
    truncated: list = None  # 文件变短（截断/轮换）
    replaced: list = None  # hash 不同但更长（替换/重写）
    deleted: list = None  # state 有、磁盘无
    new_files: list = None  # 磁盘有、state 无
    unchanged: list = None  # 快速路径未变

    def __post_init__(self):
        for f in ("truncated", "replaced", "deleted", "new_files", "unchanged"):
            if getattr(self, f) is None:
                setattr(self, f, [])

    @property
    def need_full_reexport(self) -> list:
        """需要全量重导的文件（截断或替换）"""
        return self.truncated + self.replaced


# =============================================================================
# 路径发现
# =============================================================================

def compute_project_hash(project_root: str) -> str:
    """
    计算 Claude Code 项目 hash

    策略：
    1. 先将 :\\ 替换为 --（处理 Windows 盘符）
    2. 再将剩余的 \\ 和 / 替换为 -
    3. 示例：C:\\Projects\\demo -> C--Projects-demo
    """
    abs_path = os.path.abspath(project_root)
    path = abs_path.replace(':\\', '--').replace(':/', '--')
    path = path.replace('\\', '-').replace('/', '-')
    return path


def find_jsonl_file(project_root: str) -> list[Path]:
    """
    发现项目对应的全部顶层 JSONL 文件

    策略：
    1. 计算项目 hash
    2. 在 ~/.claude/projects/<hash>/ 下查找 .jsonl 文件
    3. glob("*.jsonl") 只匹配当前目录下的 .jsonl，不会进入 subagents 子目录，
       因此无需额外过滤（M4: 删除原先无效的 subagents 过滤）
    4. 返回所有发现的 JSONL 文件列表（按修改时间升序），空列表表示未找到
    """
    project_hash = compute_project_hash(project_root)
    claude_dir = Path.home() / ".claude" / "projects" / project_hash

    if not claude_dir.is_dir():
        print(f"[WARN] 未找到项目目录：{claude_dir}", file=sys.stderr)
        return []

    jsonl_files = list(claude_dir.glob("*.jsonl"))

    if not jsonl_files:
        print(f"[WARN] 未找到 JSONL 文件：{claude_dir}", file=sys.stderr)
        return []

    # 按修改时间升序（旧 -> 新），保持时间顺序便于跨文件聚合
    jsonl_files.sort(key=lambda f: f.stat().st_mtime)
    return jsonl_files


# =============================================================================
# JSONL 解析
# =============================================================================

def _try_extract_entry(raw_line: str, line_num: int, file_name: str, stats: Optional[ParseStats] = None) -> Optional[ConversationEntry]:
    """解析单行 JSONL，返回 ConversationEntry 或 None（跳过空行/无效/非对话条目）"""
    line = raw_line.strip()
    if not line:
        if stats:
            stats.blank += 1
        return None
    try:
        entry = json.loads(line)
    except json.JSONDecodeError:
        if stats:
            stats.json_decode_errors += 1
        print(f"[WARN] {file_name}:{line_num} JSON 解析失败", file=sys.stderr)
        return None
    # 防御：非 dict 类型的 JSON（null/[]/123/"x"/true）
    if not isinstance(entry, dict):
        if stats:
            stats.not_dict += 1
        print(f"[WARN] {file_name}:{line_num} 条目形状异常（{type(entry).__name__}），已跳过", file=sys.stderr)
        return None
    if entry.get('type') not in ('user', 'assistant'):
        if stats:
            stats.wrong_type += 1
        return None
    try:
        result = extract_conversation_content(entry, line_num)
        if result is not None and stats:
            stats.extracted_entries += 1
        return result
    except (AttributeError, TypeError, KeyError, ValueError) as e:
        if stats:
            stats.extract_errors += 1
        print(f"[WARN] {file_name}:{line_num} 内容提取失败：{e}", file=sys.stderr)
        return None


def parse_jsonl(file_path: Path, start_line: int = 0, stats: Optional[ParseStats] = None) -> Iterator[ConversationEntry]:
    """
    流式解析 JSONL 文件

    参数：
    - file_path: JSONL 文件路径
    - start_line: 起始行号（用于增量导出，从该行之后开始解析）
    - stats: 解析统计（可选）

    返回：生成器，每次 yield 一个 ConversationEntry
    """
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        for line_num, line in enumerate(f, start=1):
            if line_num < start_line:
                continue
            if stats:
                stats.total_lines_read += 1
            entry = _try_extract_entry(line, line_num, file_path.name, stats)
            if entry:
                yield entry


def parse_jsonl_full(file_path: Path, stats: Optional[ParseStats] = None) -> tuple[list[ConversationEntry], int, int]:
    """
    单次扫描解析整个 JSONL，同时统计物理行总数与最后一个 entry 的行号。

    S6: 用于全量导出，避免多次读取文件。返回 (entries, total_lines, last_entry_line_no)。
    M1 E6: 全量导出主路径已改为流式（scan_file_meta + parse_jsonl + kway_merge），
    此函数仅保留给增量路径的完整性重导（E5 reexport，条目量 = 单文件，可接受）。
    """
    entries: list[ConversationEntry] = []
    total_lines = 0
    last_entry_line_no = 0
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        for line_num, line in enumerate(f, start=1):
            total_lines = line_num
            if stats:
                stats.total_lines_read += 1
            entry = _try_extract_entry(line, line_num, file_path.name, stats)
            if entry:
                entries.append(entry)
                last_entry_line_no = line_num
    return entries, total_lines, last_entry_line_no


def count_physical_lines(file_path: Path) -> int:
    """统计 JSONL 文件物理行总数（单次读取，带正确编码，S7 用于增量首次发现新文件）"""
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        return sum(1 for _ in f)


def extract_conversation_content(entry: dict, line_num: int) -> Optional[ConversationEntry]:
    """
    从 JSONL 条目中提取有意义的对话内容

    过滤策略：
    - user text: 完整保留
    - assistant text: 完整保留
    - thinking: 摘要（前 200 字 + 最后 100 字）
    - tool_use: 摘要（工具名 + 关键参数）
    - tool_result: 摘要（前 500 字 + 错误信息）
    """
    entry_type = entry.get('type')
    msg = entry.get('message', {})
    if not isinstance(msg, dict):
        msg = {}

    result = ConversationEntry(
        session=entry.get('sessionId', ''),
        line_no=line_num,
        timestamp=entry.get('timestamp', ''),
        role=entry_type,
        content=[]
    )

    content = msg.get('content', '')
    if not isinstance(content, (str, list)):
        content = ''

    if isinstance(content, str):
        result.content.append(ContentBlock(type='text', text=content))
    elif isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            block_type = block.get('type')
            if block_type == 'text':
                text = block.get('text', '')
                if not isinstance(text, str):
                    text = str(text) if text is not None else ''
                result.content.append(ContentBlock(type='text', text=text))
            elif block_type == 'thinking':
                thinking = block.get('thinking', '')
                if not isinstance(thinking, str):
                    thinking = str(thinking) if thinking is not None else ''
                if len(thinking) > 400:
                    summary = thinking[:200] + '\n[...省略...]\n' + thinking[-100:]
                else:
                    summary = thinking
                result.content.append(ContentBlock(type='thinking', text=summary, truncated=len(thinking) > 400))
            elif block_type == 'tool_use':
                tool_name = block.get('name', 'unknown')
                tool_input = block.get('input', {})
                input_summary = summarize_tool_input(tool_name, tool_input)
                result.content.append(ContentBlock(type='tool_use', text=f'[Tool: {tool_name}]\n{input_summary}', truncated=True))
            elif block_type == 'tool_result':
                result_content = block.get('content', '')
                if isinstance(result_content, list):
                    text = '\n'.join(r.get('text', '') for r in result_content if isinstance(r, dict) and r.get('type') == 'text')
                else:
                    text = str(result_content)
                is_error = block.get('is_error', False)
                if len(text) > 600:
                    summary = text[:500]
                    if is_error:
                        summary += '\n[...错误信息...]\n' + text[-200:]
                    else:
                        summary += '\n[...省略...]'
                else:
                    summary = text
                result.content.append(ContentBlock(type='tool_result', text=summary, truncated=len(text) > 600, is_error=is_error))
    return result


def summarize_tool_input(tool_name: str, tool_input: dict) -> str:
    """
    根据工具类型生成输入摘要

    不同工具保留不同关键参数。仅在确实发生截断时才追加 '...'（M8）。
    """
    if not isinstance(tool_input, dict):
        return f'Input: {tool_input}'

    if tool_name == 'Bash':
        cmd = tool_input.get('command', '')
        if len(cmd) > 500:
            return f'Command: {cmd[:500]}...'
        return f'Command: {cmd}'

    elif tool_name == 'Edit':
        fp = tool_input.get('file_path', '')
        old = tool_input.get('old_string', '')
        new = tool_input.get('new_string', '')
        parts = [f'File: {fp}']
        if old:
            parts.append(f'Old: {old[:100]}{"..." if len(old) > 100 else ""}')
        if new:
            parts.append(f'New: {new[:100]}{"..." if len(new) > 100 else ""}')
        return '\n'.join(parts)

    elif tool_name == 'Write':
        fp = tool_input.get('file_path', '')
        content = tool_input.get('content', '')
        if len(content) > 200:
            return f'File: {fp}\nContent: {content[:200]}...'
        return f'File: {fp}\nContent: {content}'

    elif tool_name == 'Read':
        return f'File: {tool_input.get("file_path", "")}'

    elif tool_name == 'Agent':
        prompt = tool_input.get('prompt', '')
        if len(prompt) > 300:
            return f'Prompt: {prompt[:300]}...'
        return f'Prompt: {prompt}'

    else:
        summary = json.dumps(tool_input, ensure_ascii=False)
        if len(summary) > 300:
            return f'Input: {summary[:300]}...'
        return f'Input: {summary}'


# =============================================================================
# Token 估算
# =============================================================================

def is_wide_char(c: str) -> bool:
    """判断字符是否为 CJK/全角字符（占用更多 token）。M9: 扩展 CJK 范围判断。"""
    if c < '\u0080':
        return False
    if '\u4e00' <= c <= '\u9fff':   # CJK 统一汉字
        return True
    if '\u3400' <= c <= '\u4dbf':   # CJK 扩展 A
        return True
    if '\uf900' <= c <= '\ufaff':   # CJK 兼容汉字
        return True
    if '\u3040' <= c <= '\u30ff':   # 日文假名
        return True
    if '\uac00' <= c <= '\ud7af':   # 韩文音节
        return True
    if '\uff00' <= c <= '\uffef':   # 全角字符
        return True
    # 兜底：用 east_asian_width 判断 Wide/Fullwidth
    return unicodedata.east_asian_width(c) in ('W', 'F')


def estimate_tokens(text: str) -> int:
    """
    粗略估算文本的 token 数

    规则：
    - 英文/代码：约 4 字符/token
    - 中文/CJK：约 1.0 字符/token（v3.3.0 由 1.5 下调，修正系统性偏低）
    - 通过统计 CJK 字符比例加权计算
    """
    if not text:
        return 0
    total_chars = len(text)
    if total_chars == 0:
        return 0
    wide_chars = sum(1 for c in text if is_wide_char(c))
    wide_tokens = wide_chars / CJK_CHARS_PER_TOKEN
    narrow_tokens = (total_chars - wide_chars) / NON_CJK_CHARS_PER_TOKEN
    return int(wide_tokens + narrow_tokens)


def estimate_entries_tokens(entries: list[ConversationEntry]) -> int:
    """估算一组对话条目的 token 数（M5: 函数与参数统一为 entries 语义）"""
    total = 0
    for entry in entries:
        for block in entry.content:
            total += estimate_tokens(block.text)
    return total


def estimate_entry_tokens(entry: ConversationEntry) -> int:
    """估算单条对话条目的 token 数（M1 E6）"""
    return estimate_entries_tokens([entry])


def effective_tokens(tokens_est: int) -> int:
    """原始估算 × 安全因子（M1 E6，D.4：对抗 1.3~2 倍系统性低估）"""
    return int(tokens_est * ESTIMATE_SAFETY_FACTOR)


def chunk_chars(chunk: list[ConversationEntry]) -> int:
    """chunk 实际字符总数（M1 E6 硬守卫用）"""
    return sum(len(block.text) for entry in chunk for block in entry.content)


def check_chunk_limits(chunk: list[ConversationEntry], max_tokens_effective: int) -> tuple[bool, Optional[str]]:
    """
    检查 chunk 是否超过限制（M1 E6 字符数硬守卫）

    返回 (ok, reason)。reason 为 "chars_exceeded" / "tokens_exceeded" 或 None。
    """
    if chunk_chars(chunk) > MAX_CHUNK_CHARS:
        return False, "chars_exceeded"
    if effective_tokens(estimate_entries_tokens(chunk)) > max_tokens_effective:
        return False, "tokens_exceeded"
    return True, None


# =============================================================================
# 时间戳规范化与 k-way 归并（M1 E6，修复 D5）
# =============================================================================

def normalize_timestamp(ts: Any) -> tuple:
    """
    规范化时间戳为可排序元组（M1 E6）

    - 优先 datetime.fromisoformat（兼容 Z 后缀与 +08:00 偏移），统一为微秒整数
    - 解析失败/缺失/非字符串 → 归入"未知时间"桶 (1, ...)，排序时置于已知时间之后；
      同为未知时：缺失（'' / None）排最前、可解析字符串按字典序，保证确定性
    """
    if ts is None:
        return (1, 0, "")
    if not isinstance(ts, str):
        return (1, 0, str(ts))
    if not ts:
        return (1, 0, "")
    try:
        ts_norm = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts_norm)
        return (0, int(dt.timestamp() * 1_000_000), "")
    except (ValueError, TypeError, OSError):
        return (1, 0, ts)


def kway_merge(generators: list[tuple[int, Iterator[ConversationEntry]]]) -> Iterator[ConversationEntry]:
    """
    k-way 归并多个生成器，按 (normalized_timestamp, file_index, line_no) 全局排序（M1 E6）

    注意：单一生成器内部不做重排（假定文件内条目已按行号/时间序——parse_jsonl 按
    行号顺序产出，Claude Code JSONL 会话时间戳单调递增）；"未知时间"桶的跨文件
    排序由 normalize_timestamp 的元组序保证。tie-breaker (file_index, line_no)
    确定有序，与设计 D.5 一致。

    参数：
    - generators: [(file_index, 生成器), ...]，file_index 用于同时间戳 tie-break

    返回：生成器，按全局时间序 yield ConversationEntry；任一生成器耗尽自动退出堆。

    内存：堆中至多 k 条在途条目（k = 生成器数）→ O(k) 内存。
    """
    counter = 0  # 堆内单调递增序号：sort_key 完全相等时避免比较 ConversationEntry
    heap: list[tuple] = []  # (sort_key, counter, file_index, entry, gen)

    # 每个生成器预取 1 条
    for file_index, gen in generators:
        try:
            entry = next(gen)
        except StopIteration:
            continue
        sort_key = (normalize_timestamp(entry.timestamp), file_index, entry.line_no)
        heapq.heappush(heap, (sort_key, counter, file_index, entry, gen))
        counter += 1

    while heap:
        sort_key, _, file_index, entry, gen = heapq.heappop(heap)
        yield entry
        try:
            next_entry = next(gen)
        except StopIteration:
            continue
        sort_key_next = (normalize_timestamp(next_entry.timestamp), file_index, next_entry.line_no)
        heapq.heappush(heap, (sort_key_next, counter, file_index, next_entry, gen))
        counter += 1


def scan_file_meta(file_path: Path, stats: Optional[ParseStats] = None) -> tuple[Optional[str], Optional[str], int]:
    """
    流式扫描单个 JSONL 文件元数据（M1 E6 全量导出 Pass 1，O(1) 内存，不载入条目）

    只做轻量类型判断（与 _try_extract_entry 相同的过滤条件：type ∈ {user, assistant}），
    不提取内容、不输出解析告警——告警由 Pass 2 正式解析时统一输出，避免重复刷屏。
    物理行总数计入 stats.total_lines_read（调用方用独立 ParseStats 承接）。

    返回 (first_ts, last_ts, entry_count)。
    """
    first_ts: Optional[str] = None
    last_ts: Optional[str] = None
    entry_count = 0
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        for line_num, line in enumerate(f, start=1):
            if stats is not None:
                stats.total_lines_read += 1
            stripped = line.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and obj.get('type') in ('user', 'assistant'):
                ts = obj.get('timestamp')
                if first_ts is None:
                    first_ts = ts
                last_ts = ts
                entry_count += 1
    return first_ts, last_ts, entry_count


def _scan_last_entry_line(file_path: Path) -> tuple[int, int]:
    """
    流式扫描单个 JSONL，返回 (末条 user/assistant 条目的行号, 物理行总数)（M1 E6）

    O(1) 内存；用于全量导出 Pass 2 后回填每文件游标（S2：exported_lines 用
    最后一条 entry 的真实行号）与 total_lines。
    """
    last_entry_line = 0
    total_lines = 0
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        for line_num, line in enumerate(f, start=1):
            total_lines = line_num
            stripped = line.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and obj.get('type') in ('user', 'assistant'):
                last_entry_line = line_num
    return last_entry_line, total_lines


# =============================================================================
# 分页
# =============================================================================

def group_into_turns(entries: list[ConversationEntry]) -> list[list[ConversationEntry]]:
    """
    将条目按对话轮次分组

    一个轮次 = 用户消息 + 后续的所有 assistant 消息（直到下一个用户消息）

    M1 E6: 仅保留作兼容工具（分页主路径已改用 paginate_stream 的 session 感知
    流式分组——全局排序后不同 session 条目交错，此函数会跨 session 拼轮次，勿用于分页）。
    """
    turns = []
    current_turn = []

    for entry in entries:
        if entry.role == 'user' and current_turn:
            # 新轮次开始
            turns.append(current_turn)
            current_turn = [entry]
        else:
            current_turn.append(entry)

    if current_turn:
        turns.append(current_turn)

    return turns


def truncate_entry(entry: ConversationEntry, max_tokens: int) -> ConversationEntry:
    """对超大 entry 的 text 块做截断兜底，使其 token 数不超过 max_tokens（M2）

    M1 E6: 调用方传入的预算应为 effective tokens（est × 安全因子）。
    """
    new_blocks = []
    budget = max_tokens
    for block in entry.content:
        block_tokens = effective_tokens(estimate_tokens(block.text))
        if block_tokens <= budget:
            new_blocks.append(block)
            budget -= block_tokens
        elif budget > 0:
            # 按预算比例估算保留字符数
            keep_ratio = budget / block_tokens
            keep_chars = max(1, int(len(block.text) * keep_ratio) - 20)
            new_blocks.append(ContentBlock(
                type=block.type,
                text=block.text[:keep_chars] + '\n[...截断...]',
                truncated=True,
                is_error=block.is_error,
            ))
            budget = 0
        else:
            new_blocks.append(ContentBlock(
                type=block.type,
                text='[...已省略...]',
                truncated=True,
                is_error=block.is_error,
            ))
    return ConversationEntry(
        session=entry.session,
        line_no=entry.line_no,
        timestamp=entry.timestamp,
        role=entry.role,
        content=new_blocks,
    )


def split_large_turn(turn: list[ConversationEntry], max_tokens: int) -> list[list[ConversationEntry]]:
    """
    拆分大轮次

    当单个轮次（user + 后续 assistant）整体超过 max_tokens 时，按 entry 逐条切分。
    若单个 entry 本身仍超过 max_tokens，则对其 text 块做截断兜底（M2）。

    M1 E6: max_tokens 为 effective 预算（est × 安全因子），entry_tokens 同样用 effective 比较。
    """
    sub_turns = []
    current = []
    current_tokens = 0

    for entry in turn:
        entry_tokens = effective_tokens(estimate_entry_tokens(entry))

        # M2: 单个 entry 本身超过上限，截断后独立成块
        if entry_tokens > max_tokens:
            if current:
                sub_turns.append(current)
                current = []
                current_tokens = 0
            sub_turns.append([truncate_entry(entry, max_tokens)])
            continue

        if current_tokens + entry_tokens > max_tokens and current:
            sub_turns.append(current)
            current = [entry]
            current_tokens = entry_tokens
        else:
            current.append(entry)
            current_tokens += entry_tokens

    if current:
        sub_turns.append(current)

    return sub_turns


def paginate_stream(
    entry_iter: Iterator[ConversationEntry],
    target_tokens: int = TARGET_CHUNK_TOKENS,
    max_tokens: int = MAX_CHUNK_TOKENS,
    min_tokens: int = MIN_CHUNK_TOKENS
) -> Iterator[list[ConversationEntry]]:
    """
    流式分页器（M1 E6，改造 paginate_entries）

    输入为已按全局时间排序的条目流（kway_merge 输出），逐 chunk yield。

    规则：
    1. 全局时间序处理（不再依赖文件 mtime 拼接顺序）
    2. session 感知轮次分组：轮次切换 = session 变化 或 同 session 新 user 条目
       （修复 D5：全局排序后不同 session 条目交错，旧 group_into_turns 会把
       A session 的 user 与 B session 的 assistant 拼成一轮）
    3. 目标大小 target tokens（effective），硬上限 max_tokens（effective）
    4. 超大轮次（> max_tokens）：无条件先 flush 当前 chunk（修复 D4 时间乱序），
       然后拆分为独立 sub_turn chunks
    5. 尾部小 chunk 合并到上一块（M1 语义保留）：仅当上一 chunk 尚未 yield 且合并不超限时

    token 预算一律使用 effective tokens（est × ESTIMATE_SAFETY_FACTOR，M1 E6 / D.4）。
    """
    cur_chunk: list[ConversationEntry] = []
    cur_chunk_tokens_est = 0
    cur_turn: list[ConversationEntry] = []
    cur_session: Optional[str] = None
    # lookbehind=1 缓冲（N-11）：上一个已产出但尚未交付的 chunk，
    # 只有确认不再被小尾巴合并时才真正交付给调用方
    pending_chunk: Optional[list[ConversationEntry]] = None
    pending_tokens_est = 0

    def turn_tokens_est(turn: list[ConversationEntry]) -> int:
        return estimate_entries_tokens(turn)

    # 已确认不可变、待交付的 chunk 队列（lookbehind=1 之外的全部）
    yielded: list[list[ConversationEntry]] = []

    def emit_chunk(c: list[ConversationEntry], c_tokens_est: int) -> None:
        nonlocal pending_chunk, pending_tokens_est
        if not c:
            return
        if (
            pending_chunk is not None
            and effective_tokens(pending_tokens_est) < min_tokens
            and effective_tokens(pending_tokens_est + c_tokens_est) <= max_tokens
        ):
            # M1 尾部合并：上一块过小且合并不超限 → 并入缓冲（不超限才合并）
            pending_chunk.extend(c)
            pending_tokens_est += c_tokens_est
        else:
            if pending_chunk is not None:
                yielded.append(pending_chunk)
            pending_chunk = c
            pending_tokens_est = c_tokens_est

    # 轮次/chunk 处理（每当有 chunk 确认不可变，立即交付，保持流式语义）
    def flush_turn() -> None:
        nonlocal cur_chunk, cur_chunk_tokens_est, cur_turn
        if not cur_turn:
            return

        turn_tk = turn_tokens_est(cur_turn)

        if effective_tokens(turn_tk) > max_tokens:
            # 超大轮次：无条件先 flush 当前 chunk（修复 D4 时间乱序）
            if cur_chunk:
                emit_chunk(cur_chunk, cur_chunk_tokens_est)
                cur_chunk = []
                cur_chunk_tokens_est = 0
            # 然后拆分大轮次，每个 sub_turn 独立成 chunk
            for st in split_large_turn(cur_turn, max_tokens):
                emit_chunk(st, estimate_entries_tokens(st))
        else:
            if cur_chunk and effective_tokens(cur_chunk_tokens_est + turn_tk) > target_tokens:
                emit_chunk(cur_chunk, cur_chunk_tokens_est)
                cur_chunk = []
                cur_chunk_tokens_est = 0
            cur_chunk.extend(cur_turn)
            cur_chunk_tokens_est += turn_tk

        cur_turn = []

    for e in entry_iter:  # 已全局时间序
        if e.session != cur_session:
            flush_turn()  # session 变化 → 关闭当前轮次
        elif e.role == 'user' and cur_turn:
            flush_turn()  # 同 session 新 user → 关闭当前轮次
        cur_turn.append(e)
        cur_session = e.session

        # 交付已确认不可变的 chunk（lookbehind=1 之外的全部），保持流式语义
        while len(yielded) > 1:
            yield yielded.pop(0)

    flush_turn()

    # 冲刷当前 chunk
    if cur_chunk:
        emit_chunk(cur_chunk, cur_chunk_tokens_est)

    # 冲最后的 lookbehind 缓冲（此后不再有合并发生）
    if pending_chunk is not None:
        yielded.append(pending_chunk)

    yield from yielded


def paginate_entries(
    entries: list[ConversationEntry],
    target_tokens: int = TARGET_CHUNK_TOKENS,
    max_tokens: int = MAX_CHUNK_TOKENS,
    min_tokens: int = MIN_CHUNK_TOKENS
) -> list[list[ConversationEntry]]:
    """
    将对话条目分页为多个 chunk（M1 E6：paginate_stream 的列表便捷封装）

    规则：
    1. 按时间顺序处理
    2. session 感知保持对话轮次完整性（不在轮次中间切分，不跨 session 拼轮次）
    3. 目标大小 90K tokens，硬上限 200K tokens（均作用于 effective tokens）
    4. 超大轮次无条件先 flush 当前 chunk 后拆分（修复时间乱序）
    5. 最小 chunk 大小 40K tokens（不足则尝试合并到上一页，合并后不超 max_tokens）

    返回：chunk 列表，每个 chunk 是 entry 列表
    """
    return list(paginate_stream(iter(entries), target_tokens, max_tokens, min_tokens))


# =============================================================================
# 输出
# =============================================================================

def _fence(text: str) -> str:
    """生成不会与文本内容冲突的 code fence（至少 3 个反引号，M11）"""
    max_run = 0
    for m in re.finditer(r'`+', text):
        if len(m.group()) > max_run:
            max_run = len(m.group())
    return '`' * (max_run + 3)


def _wrap_code_block(text: str, lang: str = "text") -> list[str]:
    """将原始文本用 fenced code 包裹，防止 markdown 注入（M11）"""
    fence = _fence(text)
    return [f"{fence}{lang}", text, fence]


def turn_to_markdown(chunk: list[ConversationEntry], chunk_idx: int, total_chunks: int) -> str:
    """将一组对话条目转换为 Markdown 格式

    M1 E6：total_chunks < 0 表示流式导出（写盘时尚不知总数），标题只显示序号。
    """
    lines = []
    if total_chunks >= 0:
        lines.append(f"# 对话历史导出 - Chunk {chunk_idx}/{total_chunks}")
    else:
        lines.append(f"# 对话历史导出 - Chunk {chunk_idx}")
    lines.append("")

    # 元信息
    if chunk:
        first_ts = chunk[0].timestamp
        last_ts = chunk[-1].timestamp
        tokens_est = estimate_entries_tokens(chunk)
        lines.append(f"> 时间范围：{first_ts} ~ {last_ts}")
        lines.append(f"> 估算 tokens：{tokens_est:,}（effective：{effective_tokens(tokens_est):,}）")
        lines.append(f"> 对话条目：{len(chunk)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 对话内容（M11: 原始文本用 fenced code 包裹，避免 markdown 注入）
    for i, entry in enumerate(chunk, 1):
        lines.append(f"## [Entry {i}] {entry.timestamp}")
        lines.append("")

        role = "User" if entry.role == "user" else "Assistant"
        lines.append(f"### {role}:")
        lines.append("")

        for block in entry.content:
            if block.type == 'text':
                lines.append("[text]")
                lines.extend(_wrap_code_block(block.text, "text"))
            elif block.type == 'thinking':
                lines.append("[thinking]")
                lines.extend(_wrap_code_block(block.text, "text"))
            elif block.type == 'tool_use':
                lines.extend(_wrap_code_block(block.text, "text"))
            elif block.type == 'tool_result':
                label = "[tool_result]" + (" (error)" if block.is_error else "")
                lines.append(label)
                lines.extend(_wrap_code_block(block.text, "text"))
            lines.append("")

        lines.append("---")
        lines.append("")

    return '\n'.join(lines)


# =============================================================================
# 状态管理
# =============================================================================

def file_info_to_dict(fi: FileInfo) -> dict:
    """FileInfo 转可序列化字典"""
    return {
        'path': fi.path,
        'sha256': fi.sha256,
        'mtime': fi.mtime,
        'size': fi.size,
        'total_lines': fi.total_lines,
        'exported_lines': fi.exported_lines,
        'exported_bytes': fi.exported_bytes,
        'committed_lines': fi.committed_lines,
        'committed_bytes': fi.committed_bytes,
        'first_event_timestamp': fi.first_event_timestamp,
        'last_event_timestamp': fi.last_event_timestamp,
        'integrity_warnings': fi.integrity_warnings,
    }


def batch_to_dict(b: BatchRecord) -> dict:
    """BatchRecord 转可序列化字典"""
    return {
        'batch_id': b.batch_id,
        'mode': b.mode,
        'status': b.status,
        'created_at': b.created_at,
        'updated_at': b.updated_at,
        'reason': b.reason,
        'retry_count': b.retry_count,
        'analysis_failures': b.analysis_failures,
        'time_range': b.time_range,
        'line_ranges': b.line_ranges,
        'chunks': b.chunks,
        'commit_receipt': b.commit_receipt,
    }


def _parse_batch_dict(d: Any) -> Optional[BatchRecord]:
    """解析批次字典为 BatchRecord（逐字段容错，坏字段按缺失处理）"""
    if not isinstance(d, dict):
        return None
    try:
        line_ranges = d.get('line_ranges')
        if line_ranges is not None and not isinstance(line_ranges, dict):
            line_ranges = None
        chunks = d.get('chunks')
        if chunks is not None and not isinstance(chunks, list):
            chunks = None
        time_range = d.get('time_range')
        if time_range is not None and not isinstance(time_range, dict):
            time_range = None
        receipt = d.get('commit_receipt')
        if receipt is not None and not isinstance(receipt, dict):
            receipt = None
        return BatchRecord(
            batch_id=str(d.get('batch_id', '')),
            mode=str(d.get('mode', 'incremental')),
            status=str(d.get('status', 'exported')),
            created_at=str(d.get('created_at', '')),
            updated_at=str(d.get('updated_at', '')),
            reason=d.get('reason'),
            retry_count=int(d.get('retry_count', 0)),
            analysis_failures=int(d.get('analysis_failures', 0)),
            time_range=time_range,
            line_ranges=line_ranges,
            chunks=chunks,
            commit_receipt=receipt,
        )
    except (TypeError, ValueError):
        return None


def state_to_dict(state: SyncState) -> dict:
    """SyncState 转可序列化字典（S1: 统一序列化，避免 FileInfo 不可 JSON 序列化）"""
    return {
        'version': state.version,
        'last_full_sync': state.last_full_sync,
        'last_incremental_sync': state.last_incremental_sync,
        'project_hash': state.project_hash,
        'batch_seq': state.batch_seq,
        'files': {k: file_info_to_dict(v) for k, v in state.files.items()},
        'batches': {k: batch_to_dict(v) for k, v in state.batches.items()},
    }


def _empty_state() -> SyncState:
    return SyncState(
        version=VERSION,
        last_full_sync=None,
        last_incremental_sync=None,
        project_hash="",
        files={},
    )


def _parse_state_dict(data: Any) -> SyncState:
    """解析状态字典为 SyncState。

    M3: 显式 schema 校验，用 data.get(...) 读取字段，忽略未知键。
    M1 E4: 向后兼容迁移——旧版本（"3.2.1"/"3.4.0"，结构相同）字段名
    processed_lines/processed_bytes → exported_lines/exported_bytes；
    committed 游标保守置 0（旧游标在分析前已推进，不可信），
    batches 为空（迁移批次由下次增量导出时创建，触发全量重分析，KB 去重兜底）。
    """
    if not isinstance(data, dict):
        raise ValueError("状态数据不是 dict")

    old_version = str(data.get('version', ''))

    files: dict[str, FileInfo] = {}
    raw_files = data.get('files', {})
    if isinstance(raw_files, dict):
        for k, v in raw_files.items():
            if not isinstance(v, dict):
                continue
            try:
                # 向后兼容：旧字段名 processed_lines → exported_lines
                exported_lines = int(v.get('exported_lines', v.get('processed_lines', 0)))
                exported_bytes = int(v.get('exported_bytes', v.get('processed_bytes', 0)))
                # committed 游标：新状态读取；仅当旧版本（无该字段）时保守置 0
                committed_lines = int(v.get('committed_lines', 0)) if 'committed_lines' in v else 0
                files[k] = FileInfo(
                    path=str(v.get('path', k)),
                    sha256=str(v.get('sha256', '')),
                    mtime=float(v.get('mtime', 0.0)),
                    size=int(v.get('size', exported_bytes)),
                    total_lines=int(v.get('total_lines', 0)),
                    exported_lines=exported_lines,
                    exported_bytes=exported_bytes,
                    committed_lines=committed_lines,
                    committed_bytes=int(v.get('committed_bytes', 0)),
                    first_event_timestamp=v.get('first_event_timestamp'),
                    last_event_timestamp=v.get('last_event_timestamp'),
                    integrity_warnings=int(v.get('integrity_warnings', 0)),
                )
            except (TypeError, ValueError):
                continue

    # 批次清单：新状态读取；旧状态无 batches，保守置空（下次增量会重建/重分析）
    batches: dict[str, BatchRecord] = {}
    raw_batches = data.get('batches', {})
    if isinstance(raw_batches, dict):
        for bid, bv in raw_batches.items():
            parsed = _parse_batch_dict(bv)
            if parsed is not None:
                batches[str(bid)] = parsed

    # 迁移标记：旧版本升级 → 输出 WARN（迁移本身不立即写盘，导出流程必然随后保存）
    if old_version and old_version != VERSION:
        print(f"[INFO] 状态文件版本 {old_version} → {VERSION}（双游标迁移：committed_lines 置 0，下次同步将重新确认已导出行）", file=sys.stderr)

    return SyncState(
        version=VERSION,  # 升级到当前 schema 版本
        last_full_sync=data.get('last_full_sync'),
        last_incremental_sync=data.get('last_incremental_sync'),
        project_hash=str(data.get('project_hash', '')),
        files=files,
        batch_seq=int(data.get('batch_seq', 0)),
        batches=batches,
    )


def load_sync_state(state_file: Path, readonly: bool = False) -> SyncState:
    """加载 sync-state.json，三级恢复链

    readonly=True（只读路径，如 --mode status）：仅内存恢复，不搬迁损坏文件、
    不回写状态文件——只读命令不得修改磁盘状态，修复留给下一次写模式命令。
    readonly=False（写路径）：损坏文件改名留存为 .corrupt-<ts> 并立即回写恢复结果。
    """
    if not state_file.exists():
        print("[INFO] 首次运行，无状态文件", file=sys.stderr)
        return _empty_state()
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        # 尝试从 .bak 恢复
        bak = state_file.with_suffix(".json.bak")
        if bak.exists():
            try:
                with open(bak, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if readonly:
                    print(
                        f"[WARN] 状态文件损坏（{e}），已从 {bak} 内存恢复；"
                        f"只读模式不修改磁盘文件（下次写模式命令会修复）",
                        file=sys.stderr,
                    )
                    return _parse_state_dict(data)
                print(f"[WARN] 状态文件损坏（{e}），已从 {bak} 恢复", file=sys.stderr)
                # 损坏文件改名留存
                ts = datetime.now().strftime("%Y%m%d-%H%M%S")
                corrupt = state_file.with_name(f"sync-state.json.corrupt-{ts}")
                os.replace(state_file, corrupt)
                # 继续解析 data...
                # 恢复后立即回写（否则下次调用仍会读到损坏主文件）
                state = _parse_state_dict(data)
                save_sync_state(state, state_file)
                return state
            except (json.JSONDecodeError, OSError):
                pass  # .bak 也损坏，进入下一步

        # 无可用备份，显式失败
        raise RuntimeError(
            f"状态文件损坏且无可用备份：{state_file}\n"
            f"请手动删除 sync-state.json 后执行 --mode full 重新初始化"
        )

    return _parse_state_dict(data)


def save_sync_state(state: SyncState, state_file: Path) -> None:
    """原子写入 sync-state.json（tmp + flush + fsync + os.replace）"""
    state_file.parent.mkdir(parents=True, exist_ok=True)

    # 1. 保留上一份好状态（供恢复）
    if state_file.exists():
        try:
            shutil.copy2(state_file, state_file.with_suffix(".json.bak"))
        except OSError:
            pass  # 尽力而为，失败不阻断

    # 2. 写 tmp（与目标同目录 → 同文件系统 → 原子 rename 前提）
    tmp = state_file.with_name(state_file.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state_to_dict(state), f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())

    # 3. 原子替换
    os.replace(tmp, state_file)

    # 4. POSIX 下尽力 fsync 目录
    try:
        dfd = os.open(str(state_file.parent), os.O_RDONLY)
        os.fsync(dfd)
        os.close(dfd)
    except OSError:
        pass


def compute_file_sha256(file_path: Path) -> str:
    """计算文件 SHA256"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def _is_byte_prefix(old_size: int, old_sha256: str, file_path: Path) -> bool:
    """检查文件前 old_size 字节是否与上次同步内容一致（用于区分"纯追加"与"替换/重写"）。

    E5：size 增大且整体 hash 不同时，若当前文件前 old_size 字节的 sha256
    仍等于 state 记录的旧文件 hash，则为正常追加（旧行号有效，走增量）；
    否则旧内容被改写（旧行号失效，整文件重导）。
    """
    try:
        h = hashlib.sha256()
        read = 0
        with open(file_path, 'rb') as f:
            while read < old_size:
                chunk = f.read(min(8192, old_size - read))
                if not chunk:
                    return False
                h.update(chunk)
                read += len(chunk)
        return read == old_size and h.hexdigest() == old_sha256
    except OSError:
        return False


def check_integrity(state: SyncState, jsonl_files: list[Path]) -> IntegrityReport:
    """
    校验 state 中已存在文件的完整性（M1 E5，修复 Critical 2）

    决策表：
    - mtime+size 未变 → 快速路径，跳过 hash
    - 变化 + hash 相同 → 仅 mtime 抖动，刷新元数据
    - 变化 + hash 不同 + size 变小 → 截断/轮换，整文件重导
    - 变化 + hash 不同 + size 增 + 旧内容是前缀 → 纯追加（B.5.4），走正常增量
    - 变化 + hash 不同 + size 增/同长 + 旧内容非前缀 → 替换/重写，保守整文件重导
    - state 有、磁盘无 → 删除
    - 磁盘有、state 无 → 新文件

    副作用：对"hash 相同、仅 mtime 抖动"的文件原地刷新 fi.mtime/fi.size；
    对 hash 不同的文件递增 fi.integrity_warnings。其余处置由调用方完成。
    """
    report = IntegrityReport()
    discovered = {str(f) for f in jsonl_files}

    for key, fi in list(state.files.items()):
        if key not in discovered:
            report.deleted.append(key)
            continue

        path = Path(key)
        try:
            st = path.stat()
        except OSError:
            report.deleted.append(key)
            continue

        # 快速路径：mtime + size 都没变
        if st.st_mtime == fi.mtime and st.st_size == fi.size:
            report.unchanged.append(key)
            continue

        # mtime/size 变了，计算 hash
        current_hash = compute_file_sha256(path)
        if current_hash == fi.sha256:
            # hash 相同，仅 mtime 抖动，刷新元数据
            fi.mtime = st.st_mtime
            fi.size = st.st_size
            report.unchanged.append(key)
            continue

        # hash 不同
        fi.integrity_warnings += 1
        if st.st_size < fi.size:
            # 截断/轮换
            report.truncated.append(key)
        elif _is_byte_prefix(fi.size, fi.sha256, path):
            # size 增大且前 fi.size 字节与上次同步一致 → 正常追加，不重导（B.5 验收 4）
            report.unchanged.append(key)
        else:
            # 同长改写或内容被替换 → 保守整文件重导
            report.replaced.append(key)

    # 新文件
    for p in discovered:
        if p not in state.files:
            report.new_files.append(p)

    return report


# =============================================================================
# 文件锁（M12）
# =============================================================================

@contextmanager
def file_lock(lock_path: Path, timeout: float = LOCK_TIMEOUT):
    """
    跨进程文件锁，防止并发导出导致状态损坏。

    Windows 用 msvcrt.locking，Linux/macOS 用 fcntl.flock。
    进程退出时锁自动释放。
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = open(lock_path, 'w', encoding='utf-8')
    deadline = time.monotonic() + timeout
    acquired = False
    try:
        if sys.platform == 'win32':
            import msvcrt
            while True:
                try:
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                    acquired = True
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"获取文件锁超时：{lock_path}")
                    time.sleep(0.1)
        else:
            import fcntl
            while True:
                try:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                    break
                except (BlockingIOError, OSError):
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"获取文件锁超时：{lock_path}")
                    time.sleep(0.1)
        yield
    finally:
        if acquired:
            try:
                if sys.platform == 'win32':
                    import msvcrt
                    try:
                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                    except OSError:
                        pass
                else:
                    import fcntl
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        lock_file.close()


# =============================================================================
# 主流程
# =============================================================================

def _validate_str(value: Any, name: str) -> str:
    """防御性类型校验（M6）"""
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} 必须是非空字符串")
    return value


def _write_chunk_file(chunk_path: Path, content: str) -> None:
    """原子写单个 chunk 文件（tmp + os.replace）"""
    tmp = chunk_path.with_name(chunk_path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, chunk_path)


def _chunk_records(chunk: list[ConversationEntry], chunk_file: Path,
                   line_ranges: Optional[dict] = None) -> tuple[dict, dict]:
    """
    生成单个 chunk 的输出记录（M1 E6：tokens_est / tokens_effective / chars 三字段）

    返回 (chunk_files 记录, chunk_manifest 记录)。
    """
    tokens_est = estimate_entries_tokens(chunk)
    tokens_eff = effective_tokens(tokens_est)
    chars = chunk_chars(chunk)

    # 字符数硬守卫（M1 E6 D.4）：超限只告警不阻断——分页器已按 effective 预算控制，
    # 此处兜底可观测（估算器彻底失效时的最后防线）
    if chars > MAX_CHUNK_CHARS:
        print(f"[WARN] {chunk_file.name} 字符数 {chars:,} 超过硬守卫 {MAX_CHUNK_CHARS:,}（chars_exceeded）", file=sys.stderr)

    chunk_files_rec = {
        "file": str(chunk_file),
        "tokens_est": tokens_est,
        "tokens_effective": tokens_eff,
        "chars": chars,
        "turns": len(chunk),
    }
    manifest_rec = {
        "file": str(chunk_file),
        "tokens_est": tokens_est,
        "tokens_effective": tokens_eff,
        "chars": chars,
        "entries": len(chunk),
        "time_range": {"start": chunk[0].timestamp, "end": chunk[-1].timestamp} if chunk else None,
    }
    if line_ranges is not None:
        manifest_rec["line_ranges"] = line_ranges
    return chunk_files_rec, manifest_rec


def export_full(project_root: str, output_dir: str, stats: Optional[ParseStats] = None) -> dict:
    """
    全量导出（流式，O(1) 内存；M1 E6 两遍扫描 + k-way 归并）

    M1 E4：全量导出也建批次（mode="full"，一个批次含全部 chunk）。
    committed_lines 置 0（旧行号随新批次重新确认，设计 A.3"全量导出也建批次"），
    exported_lines = 末条 entry 行号；
    sub agent 分析完成后通过 --mode commit 显式确认，推进 committed 游标。

    M1 E6：
    - Pass 1 流式收集每文件元数据（total_lines/entry 数/first_ts/last_ts），不载入条目
    - Pass 2 各文件开生成器，kway_merge 按 (normalized_ts, file_index, line_no)
      全局时间序归并，paginate_stream 流式分页，chunk 满即原子落盘
    - 不再有跨文件 all_entries 累积（修复 D3 OOM 与 D5 多 session 时间乱序）

    参数：
    - project_root: 项目根目录
    - output_dir: 输出目录
    - stats: 解析统计（可选，承接 Pass 2 正式解析统计）

    返回：导出结果
    """
    _validate_str(project_root, "project_root")
    _validate_str(output_dir, "output_dir")

    output_path = Path(output_dir)
    lock_path = output_path / "export.lock"

    with file_lock(lock_path):
        # V4.1.2：加载现有状态（保留 batch_seq/batches 审计历史）；
        # full 重建基线，旧未提交批次 supersede（其行范围已失效）
        state_file = output_path / "sync-state.json"
        if state_file.exists():
            state = load_sync_state(state_file)
        else:
            state = _empty_state()
        _supersede_ts = datetime.now().isoformat()
        for _bid, _b in list(state.batches.items()):
            if _b.status in ("exported", "analyzing"):
                _b.status = "failed"
                _b.reason = "superseded"
                _b.updated_at = _supersede_ts

        # 发现全部 JSONL 文件
        jsonl_files = find_jsonl_file(project_root)
        if not jsonl_files:
            return {"status": "failed", "message": "未找到 JSONL 文件"}

        discovered_files = [str(f) for f in jsonl_files]
        parsed_files: list[str] = []
        files_state: dict[str, FileInfo] = {}
        line_ranges: dict[str, list[int]] = {}

        # ── Pass 1：元数据（流式，不载入条目）──
        file_meta: list[dict] = []
        for jsonl_file in jsonl_files:
            stats_pass1 = ParseStats()
            first_ts, last_ts, entry_count = scan_file_meta(jsonl_file, stats_pass1)
            file_meta.append({
                "path": jsonl_file,
                "first_ts": first_ts,
                "last_ts": last_ts,
                "entry_count": entry_count,
            })
            parsed_files.append(str(jsonl_file))

            files_state[str(jsonl_file)] = FileInfo(
                path=str(jsonl_file),
                sha256=compute_file_sha256(jsonl_file),
                mtime=jsonl_file.stat().st_mtime,
                size=jsonl_file.stat().st_size,
                total_lines=0,  # 占位，Pass 2 回填物理行总数
                exported_lines=0,  # 占位，Pass 2 回填末条 entry 行号
                exported_bytes=jsonl_file.stat().st_size,
                committed_lines=0,  # full 导出重置 committed（旧行号随新批次重新确认）
                committed_bytes=0,
                first_event_timestamp=first_ts,
                last_event_timestamp=last_ts,
            )
            if entry_count > 0:
                line_ranges[str(jsonl_file)] = [1, 0]  # end 占位，Pass 2 回填

        # 校验：每个发现的文件都被解析（discovered == parsed）
        if set(discovered_files) != set(parsed_files):
            return {
                "status": "failed",
                "message": "文件消费不一致：部分发现的 JSONL 文件未被解析",
                "discovered_files": discovered_files,
                "parsed_files": parsed_files,
            }

        # V4.1.2：重建文件基线，但保留 batch_seq/batches 审计历史
        # （旧未提交批次已在上文 supersede；committed 历史保留可查）
        state.version = VERSION
        state.last_full_sync = None  # 成功保存后再置时间戳
        state.last_incremental_sync = None
        state.project_hash = compute_project_hash(project_root)
        state.files = files_state

        # 创建输出目录
        output_path.mkdir(parents=True, exist_ok=True)

        now = datetime.now()
        batch_id = f"full-{now.strftime('%Y%m%d-%H%M%S')}-{state.batch_seq:04d}"
        state.batch_seq += 1

        # ── Pass 2：k-way 归并流式导出 ──
        # 注：paginate_stream 消费的是 kway_merge 输出（全局时间序），chunk 内条目
        # 已按 (normalized_ts, file_index, line_no) 排序，满足 D.7 验收 3/4。
        generators: list[tuple[int, Iterator[ConversationEntry]]] = []
        for idx, fm in enumerate(file_meta):
            gen = parse_jsonl(fm["path"], 0, stats)  # 生成器，流式
            generators.append((idx, gen))

        merged = kway_merge(generators)

        # 流式分页：chunk 满（effective 预算）即原子落盘；
        # 消费每个 entry 的同时累计全局统计（O(1) 内存）
        chunk_files: list[dict] = []
        chunk_manifest: list[dict] = []
        total_entries = 0
        min_ts: Optional[str] = None
        max_ts: Optional[str] = None

        def handle_chunk(chunk: list[ConversationEntry]) -> None:
            i = len(chunk_manifest)
            chunk_file = output_path / f"chunk-{i:02d}.md"
            content = turn_to_markdown(chunk, i, -1)
            _write_chunk_file(Path(chunk_file), content)
            rec_f, rec_m = _chunk_records(chunk, Path(chunk_file))
            chunk_files.append(rec_f)
            chunk_manifest.append(rec_m)

        for chunk in paginate_stream(merged):
            handle_chunk(chunk)
            for e in chunk:
                total_entries += 1
                ts = e.timestamp
                if ts:
                    if min_ts is None or normalize_timestamp(ts) < normalize_timestamp(min_ts):
                        min_ts = ts
                    if max_ts is None or normalize_timestamp(ts) > normalize_timestamp(max_ts):
                        max_ts = ts

        # 每文件游标回填：exported_lines = 该文件末条 entry 的真实行号（S2 语义），
        # 物理行总数一并回填。ConversationEntry 不携带源文件路径，用轻量行号扫描
        # _scan_last_entry_line（O(1) 内存）补齐。
        for fm in file_meta:
            fp_key = str(fm["path"])
            last_line, phys_lines = _scan_last_entry_line(fm["path"])
            fi = files_state[fp_key]
            fi.exported_lines = last_line
            fi.total_lines = phys_lines
            if last_line > 0:
                line_ranges[fp_key] = [1, last_line]
            elif fp_key in line_ranges:
                del line_ranges[fp_key]

        time_range = {"start": min_ts, "end": max_ts} if (min_ts and max_ts) else None

        batch = BatchRecord(
            batch_id=batch_id,
            mode="full",
            status="exported",
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            time_range=time_range,
            line_ranges=line_ranges or None,
            chunks=chunk_manifest,
        )
        state.batches[batch_id] = batch
        state.last_full_sync = now.isoformat()
        save_sync_state(state, output_path / "sync-state.json")

        return {
            "status": "success",
            "mode": "full",
            "batch_id": batch_id,
            "pending_batches": [b.batch_id for b in state.pending_batches()],
            "action_hint": "analyze_and_commit",
            "total_entries": total_entries,
            "processed_entries": total_entries,
            "discovered_files": discovered_files,
            "parsed_files": parsed_files,
            "chunks": chunk_files,
            "committed_lines": {fp: fi.committed_lines for fp, fi in state.files.items()},  # E4: 双游标可观测性
            "exported_lines": {fp: fi.exported_lines for fp, fi in state.files.items()},
            "parse_stats": stats.to_dict() if stats else None,  # E3
            "sync_state": state_to_dict(state),  # S1
        }


def export_incremental(project_root: str, output_dir: str, stats: Optional[ParseStats] = None) -> dict:
    """
    增量导出

    M1 E4（修复 Critical 1）：增量起点为 committed_lines + 1（不是 exported_lines + 1）。
    导出只推进 exported_lines；committed_lines 由 sub agent 分析完成后
    通过 --mode commit 显式确认推进。存在未提交批次时优先恢复分析而非重新导出。

    参数：
    - project_root: 项目根目录
    - output_dir: 输出目录
    - stats: 解析统计（可选）

    返回：导出结果
    """
    _validate_str(project_root, "project_root")
    _validate_str(output_dir, "output_dir")

    output_path = Path(output_dir)
    state_file = output_path / "sync-state.json"
    lock_path = output_path / "export.lock"

    with file_lock(lock_path):
        # 加载同步状态
        state = load_sync_state(state_file)

        # 发现全部 JSONL 文件
        jsonl_files = find_jsonl_file(project_root)
        if not jsonl_files:
            # E5：state 中已有文件而磁盘全部消失 → 不能提前报错，
            # 必须走 check_integrity 完成 deleted 清理（批次标 failed(deleted) + 移除 files）。
            if not state.files:
                return {"status": "failed", "message": "未找到 JSONL 文件"}
            print("[WARN] 未找到任何 JSONL 文件，state 中已跟踪文件将按 deleted 处理", file=sys.stderr)
            jsonl_files = []

        discovered_files = [str(f) for f in jsonl_files]
        parsed_files: list[str] = []
        all_entries: list[ConversationEntry] = []
        warnings_list: list[dict] = []

        # ── E5：完整性校验（修复 Critical 2：JSONL 截断/轮换导致行号错位与内容静默丢失）──
        integrity = check_integrity(state, jsonl_files)
        reexport_files: set[str] = set(integrity.need_full_reexport)
        integrity_warning_codes: set[str] = set()

        # 截断/替换文件：整文件从行 1 重导出为新批次
        reexport_entries: list[ConversationEntry] = []
        reexport_line_ranges: dict[str, list[int]] = {}
        for f in integrity.need_full_reexport:
            fi = state.files[f]
            kind = "truncated" if f in integrity.truncated else "replaced"
            old_size = fi.size
            try:
                entries_r, total_lines_r, last_entry_line_no = parse_jsonl_full(Path(f), stats)
                st_now = Path(f).stat()
                new_hash = compute_file_sha256(Path(f))
            except OSError as e:
                print(f"[WARN] 完整性重导读取失败 {f}：{e}", file=sys.stderr)
                reexport_files.discard(f)
                continue
            reexport_entries.extend(entries_r)
            fi.committed_lines = 0  # 行号对旧内容已无意义
            fi.exported_lines = last_entry_line_no
            fi.total_lines = total_lines_r
            fi.exported_bytes = st_now.st_size
            fi.sha256 = new_hash
            fi.mtime = st_now.st_mtime
            fi.size = st_now.st_size
            fi.first_event_timestamp = entries_r[0].timestamp if entries_r else None
            fi.last_event_timestamp = entries_r[-1].timestamp if entries_r else None
            if last_entry_line_no > 0:
                reexport_line_ranges[f] = [1, last_entry_line_no]

            # 旧 in-flight 批次标记 superseded
            for bid, b in list(state.batches.items()):
                if b.status in ("exported", "analyzing") and f in (b.line_ranges or {}):
                    b.status = "failed"
                    b.reason = "superseded"
                    b.updated_at = datetime.now().isoformat()

            code = f"file-{kind}"
            integrity_warning_codes.add(code)
            warnings_list.append({
                "code": code,
                "file": f,
                "detail": f"文件{kind}（原 {old_size} 字节），已整文件从行 1 重导出",
                "action": "建议人工确认该 session 是否被轮换",
            })

        # 已删除文件：相关未提交批次标 failed(deleted)，并从状态移除（已提交知识在 KB 中，无需恢复）
        for f in integrity.deleted:
            for bid, b in list(state.batches.items()):
                if b.status in ("exported", "analyzing") and f in (b.line_ranges or {}):
                    b.status = "failed"
                    b.reason = "deleted"
                    b.updated_at = datetime.now().isoformat()
            state.files.pop(f, None)
            integrity_warning_codes.add("file-deleted")
            warnings_list.append({
                "code": "file-deleted",
                "file": f,
                "detail": "文件已从磁盘删除",
                "action": "已提交知识在 KB 中，无需恢复",
            })

        # 磁盘有、state 无的新文件：由下方正常增量路径从行 1 全量导出（start_line=0），
        # 此处不做额外处理，避免重复导出。

        # ── 未提交批次优先恢复分析（不重新导出，N-2 resume 协议）──
        for b in state.pending_batches():
            chunks_intact = bool(b.chunks) and all(
                isinstance(c, dict) and c.get("file") and Path(c["file"]).exists()
                for c in b.chunks
            )
            if chunks_intact:
                # chunk 完好：resume——交给 orchestrator 继续分析（N-2：analyzing 不被过滤）
                if b.status == "exported":
                    b.status = "analyzing"
                    b.updated_at = datetime.now().isoformat()
                continue
            # chunk 缺失：标记 failed(chunks-missing)，由下方 failed 重生成循环处理
            b.status = "failed"
            b.reason = "chunks-missing"
            b.updated_at = datetime.now().isoformat()
            warnings_list.append({
                "code": "batch-chunks-missing",
                "file": b.batch_id,
                "detail": f"批次 {b.batch_id} 的 chunk 文件缺失，将重生成",
                "action": "下轮增量自动重生成该批次（按 line_ranges 精确重解析），无需人工干预",
            })

        # ── failed（非 retry-exhausted/deleted/superseded）批次重生成循环（N-3）──
        # E5：superseded 批次已被新批次（重导/重生）取代，不得再重生，否则每轮重复生成重复批次
        for b in list(state.batches.values()):
            if b.status != "failed":
                continue
            if b.reason in ("retry-exhausted", "deleted", "superseded"):
                continue
            if b.retry_count >= MAX_BATCH_RETRIES:
                b.reason = "retry-exhausted"
                b.updated_at = datetime.now().isoformat()
                warnings_list.append({
                    "code": "batch-retry-exhausted",
                    "file": b.batch_id,
                    "detail": f"批次 {b.batch_id} 重生成已达上限（{MAX_BATCH_RETRIES} 次）",
                    "action": "需要人工介入：执行 --mode full 全量重导，或显式 --mode commit 强制确认",
                })
                continue
            nb = _regenerate_batch(b, state, output_path, stats)
            b.status = "failed"
            b.reason = "superseded"
            b.updated_at = datetime.now().isoformat()
            state.batches[nb.batch_id] = nb
            warnings_list.append({
                "code": "batch-regenerated",
                "file": nb.batch_id,
                "detail": f"失败批次 {b.batch_id} 已重生成为新批次 {nb.batch_id}",
                "action": "请分析新批次的 chunk 并 commit",
            })

        # ── 新增量：仅对无 in-flight 批次且无需完整性重导的文件，从 committed_lines + 1 开始 ──
        inflight_files: set[str] = set()
        for b in state.batches.values():
            if b.status in ("exported", "analyzing") and b.line_ranges:
                inflight_files.update(b.line_ranges.keys())

        new_line_ranges: dict[str, list[int]] = {}

        for jsonl_file in jsonl_files:
            file_key = str(jsonl_file)
            parsed_files.append(file_key)

            if file_key in reexport_files:
                # E5：该文件本轮已整文件重导出（reexport 批次），跳过常规增量，避免行号错位
                continue

            if file_key in state.files:
                fi = state.files[file_key]
                # S2: 行号是物理行号，+1 起始下一行；起点为 committed_lines + 1（E4 关键变化）
                start_line = fi.committed_lines + 1
            else:
                start_line = 0

            if file_key in inflight_files:
                # 该文件有未提交批次：跳过本轮新增量导出（不变式 1：每文件最多一个 in-flight 批次）
                continue

            # 解析新增内容
            entries = list(parse_jsonl(jsonl_file, start_line, stats))
            all_entries.extend(entries)

            if not entries:
                continue

            # S2: exported_lines 用最后一条 entry 的真实行号（而非 len(entries)），避免单位混用与状态漂移
            new_exported_lines = entries[-1].line_no
            new_last_ts = entries[-1].timestamp
            new_first_ts = entries[0].timestamp
            st_size = jsonl_file.stat().st_size

            if file_key in state.files:
                fi = state.files[file_key]
                fi.exported_lines = new_exported_lines
                fi.exported_bytes = st_size
                fi.last_event_timestamp = new_last_ts
                if fi.first_event_timestamp is None:
                    fi.first_event_timestamp = new_first_ts
                fi.mtime = jsonl_file.stat().st_mtime
                fi.size = st_size
                fi.sha256 = compute_file_sha256(jsonl_file)
                # total_lines 为信息字段，不参与增量逻辑，保持原值（可能略陈旧）
                start_for_range = fi.committed_lines + 1
            else:
                # S7: 统一 encoding='utf-8' + with；total_lines 用单次扫描
                state.files[file_key] = FileInfo(
                    path=file_key,
                    sha256=compute_file_sha256(jsonl_file),
                    mtime=jsonl_file.stat().st_mtime,
                    size=st_size,
                    total_lines=count_physical_lines(jsonl_file),
                    exported_lines=new_exported_lines,
                    exported_bytes=st_size,
                    committed_lines=0,
                    committed_bytes=0,
                    first_event_timestamp=new_first_ts,
                    last_event_timestamp=new_last_ts,
                )
                start_for_range = 1
            new_line_ranges[file_key] = [start_for_range, new_exported_lines]

        # 校验：每个发现的文件都被解析（discovered == parsed）
        if set(discovered_files) != set(parsed_files):
            return {
                "status": "failed",
                "message": "文件消费不一致：部分发现的 JSONL 文件未被解析",
                "discovered_files": discovered_files,
                "parsed_files": parsed_files,
            }

        # E5：重导文件的 entries 并入本轮聚合（与常规增量一起分页建批次）
        all_entries[0:0] = reexport_entries
        new_line_ranges = dict(reexport_line_ranges, **new_line_ranges)

        # D5（M1 E6）：增量 delta 同样全局排序（多 session 各推少量行时保证 chunk 内时间序）
        all_entries.sort(key=lambda e: (normalize_timestamp(e.timestamp), e.line_no))

        batch_id = None

        if all_entries:
            # 分页（通常只有 1 个 chunk）
            chunks = paginate_entries(all_entries)

            # 创建输出目录
            output_path.mkdir(parents=True, exist_ok=True)

            now = datetime.now()
            batch_id = f"inc-{now.strftime('%Y%m%d-%H%M%S')}-{state.batch_seq:04d}"
            state.batch_seq += 1

            # 输出 chunk 文件
            chunk_files = []
            chunk_manifest = []
            for i, chunk in enumerate(chunks):
                chunk_file = output_path / f"chunk-{batch_id}-{i:02d}.md"
                content = turn_to_markdown(chunk, i, len(chunks))
                _write_chunk_file(Path(chunk_file), content)
                rec_f, rec_m = _chunk_records(
                    chunk, Path(chunk_file),
                    line_ranges=dict(new_line_ranges) if len(chunks) == 1 else None,
                )
                chunk_files.append(rec_f)
                chunk_manifest.append(rec_m)

            time_range = None
            ts_list = [e.timestamp for e in all_entries if e.timestamp]
            if ts_list:
                time_range = {"start": min(ts_list), "end": max(ts_list)}

            batch = BatchRecord(
                batch_id=batch_id,
                mode="incremental",
                status="exported",
                created_at=now.isoformat(),
                updated_at=now.isoformat(),
                time_range=time_range,
                line_ranges=dict(new_line_ranges) or None,
                chunks=chunk_manifest,
            )
            state.batches[batch_id] = batch
        else:
            chunk_files = []

        state.last_incremental_sync = datetime.now().isoformat()
        save_sync_state(state, state_file)

        # 汇总待分析批次（本轮恢复的 + 本轮新建的），并回读落盘后的真实游标
        pending_batches = [b.batch_id for b in state.pending_batches()]
        saved_state = load_sync_state(state_file)
        committed_view = {fp: fi.committed_lines for fp, fi in saved_state.files.items()}
        exported_view = {fp: fi.exported_lines for fp, fi in saved_state.files.items()}

        # E5：有完整性警告时 status 降为 partial（数据质量告警，非失败）
        output_status = "success"
        if integrity_warning_codes:
            output_status = "partial"

        if batch_id is None and not pending_batches:
            result = {
                "status": output_status,
                "message": "无新内容",
                "new_entries": 0,
                "pending_batches": [],
                "action_hint": None,
                "discovered_files": discovered_files,
                "parsed_files": parsed_files,
                "committed_lines": committed_view,  # E4: 双游标可观测性
                "exported_lines": exported_view,
                "parse_stats": stats.to_dict() if stats else None,  # E3
            }
            if warnings_list:
                result["warnings"] = warnings_list
            return result

        result = {
            "status": output_status,
            "mode": "incremental",
            "batch_id": batch_id,
            "new_entries": len(all_entries),
            "discovered_files": discovered_files,
            "parsed_files": parsed_files,
            "chunks": chunk_files,
            "pending_batches": pending_batches,
            "action_hint": "analyze_and_commit" if batch_id else ("analyze_pending" if pending_batches else None),
            "committed_lines": committed_view,  # E4: 双游标可观测性
            "exported_lines": exported_view,
            "parse_stats": stats.to_dict() if stats else None,  # E3
            "sync_state": state_to_dict(saved_state),  # S1（以落盘状态为准）
        }
        if warnings_list:
            result["warnings"] = warnings_list
        return result


def _regenerate_batch(b: BatchRecord, state: SyncState, output_path: Path, stats: Optional[ParseStats]) -> BatchRecord:
    """
    重生成失败批次（M1 E4 / N-3）

    - 普通批次：按 line_ranges 精确重解析（源文件未变则 chunk 内容字节级一致）
    - migration 批次（line_ranges 为 null）：特判为整文件从行 1 重导出
    """
    now = datetime.now()
    mode_prefix = "full" if b.mode == "migration" else "inc"
    new_batch_id = f"{mode_prefix}-{now.strftime('%Y%m%d-%H%M%S')}-{state.batch_seq:04d}"
    state.batch_seq += 1

    line_ranges: dict[str, list[int]] = {}

    if b.mode == "migration" or not b.line_ranges:
        # migration 特判：整文件从行 1 重导出（line_ranges: {f: [1, exported_lines]}）
        target_files = []
        for fp, fi in state.files.items():
            if Path(fp).exists():
                target_files.append((fp, 1, max(fi.exported_lines, fi.total_lines)))
    else:
        target_files = [
            (fp, int(rng[0]), int(rng[1]))
            for fp, rng in b.line_ranges.items()
            if Path(fp).exists()
        ]

    all_entries: list[ConversationEntry] = []
    for fp, start_line, end_line in target_files:
        entries = [
            e for e in parse_jsonl(Path(fp), start_line, stats)
            if e.line_no <= end_line
        ]
        all_entries.extend(entries)
        line_ranges[fp] = [start_line, end_line]

    chunks = paginate_entries(all_entries)
    output_path.mkdir(parents=True, exist_ok=True)

    chunk_manifest = []
    for i, chunk in enumerate(chunks):
        chunk_file = output_path / f"chunk-{new_batch_id}-{i:02d}.md"
        content = turn_to_markdown(chunk, i, len(chunks))
        _write_chunk_file(Path(chunk_file), content)
        _, rec_m = _chunk_records(chunk, Path(chunk_file))
        chunk_manifest.append(rec_m)

    ts_list = [e.timestamp for e in all_entries if e.timestamp]
    time_range = {"start": min(ts_list), "end": max(ts_list)} if ts_list else None

    return BatchRecord(
        batch_id=new_batch_id,
        mode=b.mode,
        status="exported",
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
        reason=None,
        retry_count=b.retry_count + 1,
        analysis_failures=b.analysis_failures,
        time_range=time_range,
        line_ranges=line_ranges or None,
        chunks=chunk_manifest,
    )


def _compute_receipt_hash(batch_id: str, committed_lines: dict, committed_at: str) -> str:
    """计算 receipt_hash = sha256(规范化 JSON of {batch_id, committed_lines, committed_at})（M1 E4）"""
    payload = json.dumps(
        {"batch_id": batch_id, "committed_lines": committed_lines, "committed_at": committed_at},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def commit_batch(batch_id: str, state_file: Path, force: bool = False) -> dict:
    """
    确认批次已分析完成，推进 committed_lines（M1 E4：commit 协议）

    - 幂等：重复 commit 同一批次返回已有 receipt
    - failed 批次拒绝 commit（提示先重生成）；--force 可强制确认 analysis-exhausted 批次
    - migration 批次（line_ranges 为 null）特殊语义（F-1）：committed_lines = exported_lines
    """
    with file_lock(Path(state_file).parent / "export.lock"):
        state = load_sync_state(state_file)
        batch = state.batches.get(batch_id)

        if batch is None:
            return {"status": "failed", "code": "batch-not-found", "message": f"批次 {batch_id} 不存在"}

        if batch.status == "committed":
            return {
                "status": "success",
                "mode": "commit",
                "message": "批次已提交（幂等）",
                "batch_id": batch_id,
                "receipt": batch.commit_receipt,
            }

        if batch.status == "failed":
            if force and batch.reason == "analysis-exhausted":
                # --force 显式确认（F-3/N-4）：输出显著警告，receipt 记录 forced: true
                print("[WARN] 强制确认将永久跳过该批次未分析内容", file=sys.stderr)
            else:
                return {
                    "status": "failed",
                    "code": "batch-failed",
                    "message": f"批次已失败：{batch.reason}。请先重生成（重跑 --mode incremental）或对 analysis-exhausted 批次使用 --force 显式确认",
                }

        now = datetime.now().isoformat()

        # 推进 committed_lines
        committed_lines_map: dict[str, int] = {}
        migration_commit = False

        if batch.mode == "migration" and not batch.line_ranges:
            # F-1 迁移批次特殊 commit 语义：按现状确认全部已导出行
            migration_commit = True
            for fp, fi in state.files.items():
                fi.committed_lines = max(fi.committed_lines, fi.exported_lines)
                fi.committed_bytes = fi.exported_bytes
        elif batch.line_ranges:
            for file_path, rng in batch.line_ranges.items():
                if file_path in state.files and isinstance(rng, (list, tuple)) and len(rng) == 2:
                    start, end = int(rng[0]), int(rng[1])
                    fi = state.files[file_path]
                    if end < fi.committed_lines:
                        # M7: 显式错误替代 assert（assert 在 python -O 下会被剥离）
                        return {
                            "status": "failed",
                            "code": "cursor-regression",
                            "message": f"committed_lines 只能前进：{fi.committed_lines} → {end}（{file_path}）",
                        }
                    fi.committed_lines = end  # 只前进
                    fi.committed_bytes = fi.exported_bytes

        for fp, fi in state.files.items():
            committed_lines_map[fp] = fi.committed_lines

        batch.status = "committed"
        batch.updated_at = now
        receipt = {
            "batch_id": batch_id,
            "committed_at": now,
            "committed_lines": committed_lines_map,
            "receipt_hash": _compute_receipt_hash(batch_id, committed_lines_map, now),
        }
        if migration_commit:
            receipt["migration_commit"] = True
        if force:
            receipt["forced"] = True
        batch.commit_receipt = receipt

        # 提交批次修剪：committed 批次保留最近 KEEP_COMMITTED_BATCHES 个（游标在 files 中，不受影响）
        committed_sorted = sorted(
            [b for b in state.batches.values() if b.status == "committed"],
            key=lambda b: b.updated_at or b.created_at,
        )
        if len(committed_sorted) > KEEP_COMMITTED_BATCHES:
            for old in committed_sorted[:-KEEP_COMMITTED_BATCHES]:
                del state.batches[old.batch_id]

        save_sync_state(state, state_file)
        return {"status": "success", "mode": "commit", "batch_id": batch_id, "receipt": receipt}


def mark_batch_analyzing(batch_id: str, state_file: Path) -> dict:
    """标记批次为 analyzing（仅信息性；sub agent 开始分析时调用）"""
    with file_lock(Path(state_file).parent / "export.lock"):
        state = load_sync_state(state_file)
        batch = state.batches.get(batch_id)

        if batch is None:
            return {"status": "failed", "code": "batch-not-found", "message": f"批次 {batch_id} 不存在"}
        if batch.status in ("committed", "failed"):
            return {"status": "failed", "code": "invalid-state", "message": f"批次状态为 {batch.status}，不能标记为 analyzing"}

        batch.status = "analyzing"
        batch.updated_at = datetime.now().isoformat()
        save_sync_state(state, state_file)
        return {"status": "success", "mode": "start", "batch_id": batch_id, "batch_status": batch.status}


def analyze_failed_batch(batch_id: str, state_file: Path) -> dict:
    """
    报告一次分析失败，递增 analysis_failures（F-3/N-4）

    达 MAX_ANALYSIS_FAILURES 上限 → failed(analysis-exhausted)，退出阻塞循环。
    """
    with file_lock(Path(state_file).parent / "export.lock"):
        state = load_sync_state(state_file)
        batch = state.batches.get(batch_id)

        if batch is None:
            return {"status": "failed", "code": "batch-not-found", "message": f"批次 {batch_id} 不存在"}
        if batch.status in ("committed", "failed"):
            return {"status": "failed", "code": "invalid-state", "message": f"批次状态为 {batch.status}，无需记录分析失败"}

        batch.analysis_failures += 1
        result = {
            "status": "success",
            "mode": "analyze-failed",
            "batch_id": batch_id,
            "analysis_failures": batch.analysis_failures,
        }

        if batch.analysis_failures >= MAX_ANALYSIS_FAILURES:
            batch.status = "failed"
            batch.reason = "analysis-exhausted"
            batch.updated_at = datetime.now().isoformat()
            result["batch_status"] = "failed"
            result["reason"] = "analysis-exhausted"
            result["action"] = (
                "分析失败已达上限。人工介入选项：① 检查 sub agent 失败原因后重跑增量同步（自动重生成批次）；"
                "② --mode commit --force 显式确认（将永久跳过该批次未分析内容）"
            )
            print(f"[WARN] 批次 {batch_id} 分析失败达上限（{MAX_ANALYSIS_FAILURES} 次），已标记 failed(analysis-exhausted)", file=sys.stderr)
        else:
            result["batch_status"] = batch.status
            result["action"] = "下轮 /evolution 将重新尝试分析该批次"

        batch.updated_at = datetime.now().isoformat()
        save_sync_state(state, state_file)
        return result


def cleanup_output(output_dir: str) -> dict:
    """
    清理输出目录中的临时文件

    S5: 仅删除白名单内的文件，绝不 rmtree 整个目录，避免误删。
    """
    _validate_str(output_dir, "output_dir")
    output_path = Path(output_dir)

    if not output_path.exists():
        return {"status": "success", "message": "目录不存在，无需清理", "removed": 0}
    if not output_path.is_dir():
        return {"status": "failed", "message": f"目标路径不是目录：{output_path}"}

    lock_path = output_path / "export.lock"
    with file_lock(lock_path):
        removed = 0
        for pattern in CLEANUP_PATTERNS:
            for f in output_path.glob(pattern):
                if f.is_file():
                    try:
                        f.unlink()
                        removed += 1
                    except OSError as e:
                        print(f"[WARN] 删除失败 {f}: {e}", file=sys.stderr)

        return {"status": "success", "message": f"已清理 {removed} 个临时文件", "removed": removed}


# =============================================================================
# 命令行接口
# =============================================================================

def _reconfigure_stdio() -> None:
    """Windows 下强制 stdout/stderr 使用 UTF-8，避免 GBK 编码崩溃（S3）"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass


def main():
    """主函数"""
    _reconfigure_stdio()  # S3: 必须在任何输出前完成

    import argparse

    parser = argparse.ArgumentParser(description="Evolution Export Script")
    parser.add_argument(
        "--mode",
        choices=["full", "incremental", "status", "cleanup", "commit", "start", "analyze-failed"],
        required=True,
    )
    parser.add_argument("--project-path", default=".")
    parser.add_argument("--output", default=".evolution/chunks")
    parser.add_argument("--batch-id", default=None, help="批次 ID（commit/start/analyze-failed 模式必填）")
    parser.add_argument("--force", action="store_true", help="commit --force：强制确认 analysis-exhausted 批次（F-3/N-4）")
    parser.add_argument("--verify", action="store_true", help="status --verify：只读完整性校验，不修改状态（M1 E5）")

    try:
        args = parser.parse_args()

        # M1 E4 / F-6: 路径锚定——默认值由脚本位置推导，不依赖调用方 cwd
        # （sub agent 的 Bash cwd 在调用间会被复位，相对路径会定位到错误项目）
        if args.project_path == ".":
            args.project_path = str(get_project_root())
        if args.output == ".evolution/chunks":
            args.output = str(get_project_root() / ".evolution" / "chunks")

        # M6: 防御性类型校验
        if not isinstance(args.project_path, str) or not args.project_path:
            raise ValueError("--project-path 必须是非空字符串")
        if not isinstance(args.output, str) or not args.output:
            raise ValueError("--output 必须是非空字符串")

        if args.mode in ("full", "incremental"):
            if not os.path.isdir(args.project_path):
                result = {"status": "failed", "message": f"项目路径不存在：{args.project_path}"}
                print(json.dumps(result, ensure_ascii=False, indent=2))
                sys.exit(1)

        if args.mode in ("commit", "start", "analyze-failed"):
            if not isinstance(args.batch_id, str) or not args.batch_id:
                result = {
                    "status": "failed",
                    "code": "batch-id-required",
                    "message": f"--mode {args.mode} 需要 --batch-id <id> 参数",
                }
                print(json.dumps(result, ensure_ascii=False, indent=2))
                sys.exit(1)

        if args.mode == "full":
            stats = ParseStats()
            result = export_full(args.project_path, args.output, stats)
        elif args.mode == "incremental":
            stats = ParseStats()
            result = export_incremental(args.project_path, args.output, stats)
        elif args.mode == "status":
            state_file = Path(args.output) / "sync-state.json"
            state = load_sync_state(state_file, readonly=True)  # V4.1.2：只读路径不搬迁/不回写状态文件
            pending_batches = [
                {"batch_id": b.batch_id, "mode": b.mode, "status": b.status, "analysis_failures": b.analysis_failures,
                 "chunks": [c.get("file") for c in (b.chunks or []) if isinstance(c, dict)]}
                for b in state.pending_batches()
            ]
            result = {
                "status": "success",
                "state": state_to_dict(state),  # S1
                "pending_batches": pending_batches,  # E4: 未提交批次高亮
            }
            if args.verify:
                # E5：只读完整性校验（不修改状态；check_integrity 的元数据刷新不落盘）
                jsonl_files = find_jsonl_file(args.project_path)
                integrity = check_integrity(state, jsonl_files)
                result["integrity"] = {
                    "truncated": integrity.truncated,
                    "replaced": integrity.replaced,
                    "deleted": integrity.deleted,
                    "new_files": integrity.new_files,
                    "unchanged_count": len(integrity.unchanged),
                }
                if integrity.truncated or integrity.replaced:
                    result["action_hint"] = "run_incremental_to_reexport"
            if pending_batches:
                result["action_hint"] = result.get("action_hint") or "analyze_pending"
        elif args.mode == "commit":
            batch_id = args.batch_id
            receipt = commit_batch(batch_id, Path(args.output) / "sync-state.json", force=args.force)
            print(json.dumps(receipt, ensure_ascii=False, indent=2))
            sys.exit(0 if receipt.get("status") == "success" else 1)
        elif args.mode == "start":
            batch_id = args.batch_id
            start_result = mark_batch_analyzing(batch_id, Path(args.output) / "sync-state.json")
            print(json.dumps(start_result, ensure_ascii=False, indent=2))
            sys.exit(0 if start_result.get("status") == "success" else 1)
        elif args.mode == "analyze-failed":
            batch_id = args.batch_id
            fail_result = analyze_failed_batch(batch_id, Path(args.output) / "sync-state.json")
            print(json.dumps(fail_result, ensure_ascii=False, indent=2))
            sys.exit(0 if fail_result.get("status") == "success" else 1)
        elif args.mode == "cleanup":
            result = cleanup_output(args.output)
        else:  # 防御性兜底（M6）
            raise ValueError(f"未知模式：{args.mode}")

        # E3: 高错误率警告（wrong_type 占比超 50% 提示文件可能不是会话格式）
        # E5: 完整性警告已在 export_incremental 内并入 result["warnings"]，此处仅处理 full 模式与解析统计
        if args.mode in ("full", "incremental") and isinstance(result, dict) and stats is not None:
            warnings_list = []
            if stats.total_lines_read > 0 and stats.wrong_type / stats.total_lines_read > 0.5:
                warnings_list.append({
                    "code": "high-wrong-type-ratio",
                    "detail": f"{stats.wrong_type}/{stats.total_lines_read} 行非 user/assistant 类型，文件可能不是 Claude Code 会话格式",
                    "action": "请确认 JSONL 文件来源"
                })
            if warnings_list:
                result.setdefault("warnings", []).extend(warnings_list)

        print(json.dumps(result, ensure_ascii=False, indent=2))  # S3: stdout 已 reconfigure 为 UTF-8

        # V4.1.2：退出码协议——0 = success / partial，1 = failed（与 sync.md 对齐）
        _status = result.get("status") if isinstance(result, dict) else None
        sys.exit(0 if _status in ("success", "partial") else 1)

    except SystemExit:
        raise
    except Exception as e:
        # M7: 兜底异常处理，输出结构化错误而非栈
        print(f"[ERROR] {type(e).__name__}: {e}", file=sys.stderr)
        try:
            print(json.dumps({"status": "failed", "message": str(e)}, ensure_ascii=False, indent=2))
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
