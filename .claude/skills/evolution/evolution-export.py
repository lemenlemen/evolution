#!/usr/bin/env python3
"""
Evolution Export Script

导出和分析 Claude Code 对话历史，生成知识库输入文件。

版本：v3.8.0
日期：2026-07-31

功能：
- 发现 JSONL 文件路径
- 解析 JSONL 格式
- 过滤噪声（metadata 条目）
- 提取有意义的对话内容
- 分页输出（目标 90K tokens/chunk）
- 状态管理（增量同步）
- 跨进程文件锁保证并发安全

修复历史：
- v3.5.0: 基于 writing-great-skills 规则重构，SKILL.md 从 96 行缩减至 37 行
- v3.4.0: 模块化重构，从 config.yaml 读取配置
- v3.3.0: 修复 JSON 序列化崩溃、增量单位漂移、Windows 编码、token 估算偏低、
          cleanup 安全、文件句柄泄漏等多项问题
"""

import os
import json
import hashlib
import sys
import time
import re
import unicodedata
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

VERSION = "3.4.0"

# 尝试从 config.yaml 读取配置
CONFIG_PATH = Path(__file__).parent / "config.yaml"

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

# cleanup 模式只删除这些文件，绝不 rmtree 整个目录（S5）
CLEANUP_PATTERNS = ("chunk-*.md", "chunk-inc-*.md", "sync-state.json")

# 文件锁等待超时（秒）
LOCK_TIMEOUT = 120.0


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
    """文件同步状态"""
    path: str
    sha256: str
    mtime: float
    total_lines: int
    processed_lines: int
    processed_bytes: int
    last_event_timestamp: Optional[str] = None


@dataclass
class SyncState:
    """同步状态"""
    version: str
    last_full_sync: Optional[str]
    last_incremental_sync: Optional[str]
    project_hash: str
    files: dict[str, FileInfo]


# =============================================================================
# 路径发现
# =============================================================================

def compute_project_hash(project_root: str) -> str:
    """
    计算 Claude Code 项目 hash

    策略：
    1. 先将 :\\ 替换为 --（处理 Windows 盘符）
    2. 再将剩余的 \\ 和 / 替换为 -
    3. 示例：<project-root> -> <project-hash>
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

def _try_extract_entry(raw_line: str, line_num: int, file_name: str) -> Optional[ConversationEntry]:
    """解析单行 JSONL，返回 ConversationEntry 或 None（跳过空行/无效/非对话条目）"""
    line = raw_line.strip()
    if not line:
        return None
    try:
        entry = json.loads(line)
    except json.JSONDecodeError:
        print(f"[WARN] {file_name}:{line_num} JSON 解析失败", file=sys.stderr)
        return None
    if entry.get('type') not in ('user', 'assistant'):
        return None
    return extract_conversation_content(entry, line_num)


def parse_jsonl(file_path: Path, start_line: int = 0) -> Iterator[ConversationEntry]:
    """
    流式解析 JSONL 文件

    参数：
    - file_path: JSONL 文件路径
    - start_line: 起始行号（用于增量导出，从该行之后开始解析）

    返回：生成器，每次 yield 一个 ConversationEntry
    """
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        for line_num, line in enumerate(f, start=1):
            if line_num < start_line:
                continue
            entry = _try_extract_entry(line, line_num, file_path.name)
            if entry:
                yield entry


def parse_jsonl_full(file_path: Path) -> tuple[list[ConversationEntry], int, int]:
    """
    单次扫描解析整个 JSONL，同时统计物理行总数与最后一个 entry 的行号。

    S6: 用于全量导出，避免多次读取文件。返回 (entries, total_lines, last_entry_line_no)。
    """
    entries: list[ConversationEntry] = []
    total_lines = 0
    last_entry_line_no = 0
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        for line_num, line in enumerate(f, start=1):
            total_lines = line_num
            entry = _try_extract_entry(line, line_num, file_path.name)
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

    result = ConversationEntry(
        session=entry.get('sessionId', ''),
        line_no=line_num,
        timestamp=entry.get('timestamp', ''),
        role=entry_type,
        content=[]
    )

    content = msg.get('content', '')

    if isinstance(content, str):
        result.content.append(ContentBlock(type='text', text=content))
    elif isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            block_type = block.get('type')
            if block_type == 'text':
                result.content.append(ContentBlock(type='text', text=block.get('text', '')))
            elif block_type == 'thinking':
                thinking = block.get('thinking', '')
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


# =============================================================================
# 分页
# =============================================================================

def group_into_turns(entries: list[ConversationEntry]) -> list[list[ConversationEntry]]:
    """
    将条目按对话轮次分组

    一个轮次 = 用户消息 + 后续的所有 assistant 消息（直到下一个用户消息）
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
    """对超大 entry 的 text 块做截断兜底，使其 token 数不超过 max_tokens（M2）"""
    new_blocks = []
    budget = max_tokens
    for block in entry.content:
        block_tokens = estimate_tokens(block.text)
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
    """
    sub_turns = []
    current = []
    current_tokens = 0

    for entry in turn:
        entry_tokens = estimate_entries_tokens([entry])

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


def paginate_entries(
    entries: list[ConversationEntry],
    target_tokens: int = TARGET_CHUNK_TOKENS,
    max_tokens: int = MAX_CHUNK_TOKENS,
    min_tokens: int = MIN_CHUNK_TOKENS
) -> list[list[ConversationEntry]]:
    """
    将对话条目分页为多个 chunk

    规则：
    1. 按时间顺序处理
    2. 保持对话轮次完整性（不在轮次中间切分）
    3. 目标大小 90K tokens，硬上限 200K tokens
    4. 最小 chunk 大小 40K tokens（不足则尝试合并到上一页，合并后不超 max_tokens，M1）

    返回：chunk 列表，每个 chunk 是 entry 列表
    """
    chunks = []
    current_chunk = []
    current_tokens = 0

    # 先按轮次分组
    turns = group_into_turns(entries)

    for turn in turns:
        turn_tokens = estimate_entries_tokens(turn)

        # 如果单个轮次就超过 max_tokens，需要拆分
        if turn_tokens > max_tokens:
            # 先保存当前 chunk
            if current_chunk and current_tokens > min_tokens:
                chunks.append(current_chunk)
                current_chunk = []
                current_tokens = 0

            # 拆分大轮次
            sub_turns = split_large_turn(turn, max_tokens)
            for sub_turn in sub_turns:
                chunks.append(sub_turn)
            continue

        # 如果加入此轮次会超过 target_tokens
        if current_tokens + turn_tokens > target_tokens and current_chunk:
            chunks.append(current_chunk)
            current_chunk = list(turn)  # 拷贝，避免副作用
            current_tokens = turn_tokens
        else:
            current_chunk.extend(turn)
            current_tokens += turn_tokens

    # 处理最后一个 chunk
    if current_chunk:
        if current_tokens < min_tokens and chunks:
            # 太小，尝试合并到上一个 chunk（M1: 合并前检查不超 max_tokens）
            prev_tokens = estimate_entries_tokens(chunks[-1])
            if prev_tokens + current_tokens <= max_tokens:
                chunks[-1].extend(current_chunk)
            else:
                # 合并后超限，作为独立 chunk 保留
                chunks.append(current_chunk)
        else:
            chunks.append(current_chunk)

    return chunks


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
    """将一组对话条目转换为 Markdown 格式"""
    lines = []
    lines.append(f"# 对话历史导出 - Chunk {chunk_idx}/{total_chunks}")
    lines.append("")

    # 元信息
    if chunk:
        first_ts = chunk[0].timestamp
        last_ts = chunk[-1].timestamp
        total_tokens = sum(estimate_entries_tokens([t]) for t in chunk)
        lines.append(f"> 时间范围：{first_ts} ~ {last_ts}")
        lines.append(f"> 估算 tokens：{total_tokens:,}")
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
        'total_lines': fi.total_lines,
        'processed_lines': fi.processed_lines,
        'processed_bytes': fi.processed_bytes,
        'last_event_timestamp': fi.last_event_timestamp,
    }


def state_to_dict(state: SyncState) -> dict:
    """SyncState 转可序列化字典（S1: 统一序列化，避免 FileInfo 不可 JSON 序列化）"""
    return {
        'version': state.version,
        'last_full_sync': state.last_full_sync,
        'last_incremental_sync': state.last_incremental_sync,
        'project_hash': state.project_hash,
        'files': {k: file_info_to_dict(v) for k, v in state.files.items()},
    }


def _empty_state() -> SyncState:
    return SyncState(
        version=VERSION,
        last_full_sync=None,
        last_incremental_sync=None,
        project_hash="",
        files={},
    )


def load_sync_state(state_file: Path) -> SyncState:
    """
    加载同步状态

    M3: 显式 schema 校验，用 data.get(...) 读取字段，忽略未知键；
    文件损坏或类型不符时回退到空状态。
    """
    if not state_file.exists():
        return _empty_state()

    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"[WARN] 状态文件损坏，重新初始化：{e}", file=sys.stderr)
        return _empty_state()

    if not isinstance(data, dict):
        return _empty_state()

    files: dict[str, FileInfo] = {}
    raw_files = data.get('files', {})
    if isinstance(raw_files, dict):
        for k, v in raw_files.items():
            if not isinstance(v, dict):
                continue
            try:
                files[k] = FileInfo(
                    path=str(v.get('path', k)),
                    sha256=str(v.get('sha256', '')),
                    mtime=float(v.get('mtime', 0.0)),
                    total_lines=int(v.get('total_lines', 0)),
                    processed_lines=int(v.get('processed_lines', 0)),
                    processed_bytes=int(v.get('processed_bytes', 0)),
                    last_event_timestamp=v.get('last_event_timestamp'),
                )
            except (TypeError, ValueError):
                continue

    return SyncState(
        version=str(data.get('version', VERSION)),
        last_full_sync=data.get('last_full_sync'),
        last_incremental_sync=data.get('last_incremental_sync'),
        project_hash=str(data.get('project_hash', '')),
        files=files,
    )


def save_sync_state(state: SyncState, state_file: Path) -> None:
    """保存同步状态"""
    state_dict = state_to_dict(state)
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state_dict, f, ensure_ascii=False, indent=2)


def compute_file_sha256(file_path: Path) -> str:
    """计算文件 SHA256"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


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


def export_full(project_root: str, output_dir: str) -> dict:
    """
    全量导出

    参数：
    - project_root: 项目根目录
    - output_dir: 输出目录

    返回：导出结果
    """
    _validate_str(project_root, "project_root")
    _validate_str(output_dir, "output_dir")

    output_path = Path(output_dir)
    lock_path = output_path / "export.lock"

    with file_lock(lock_path):
        # 发现全部 JSONL 文件
        jsonl_files = find_jsonl_file(project_root)
        if not jsonl_files:
            return {"status": "error", "message": "未找到 JSONL 文件"}

        discovered_files = [str(f) for f in jsonl_files]
        parsed_files: list[str] = []
        all_entries: list[ConversationEntry] = []
        files_state: dict[str, FileInfo] = {}

        for jsonl_file in jsonl_files:
            # S6: 单次扫描完成解析 + 统计物理行数 + 末条 entry 行号，避免多次读文件
            entries, total_lines, last_entry_line_no = parse_jsonl_full(jsonl_file)
            all_entries.extend(entries)
            parsed_files.append(str(jsonl_file))

            # S2: processed_lines 用最后一条 entry 的真实行号，而非 len(entries)
            files_state[str(jsonl_file)] = FileInfo(
                path=str(jsonl_file),
                sha256=compute_file_sha256(jsonl_file),
                mtime=jsonl_file.stat().st_mtime,
                total_lines=total_lines,
                processed_lines=last_entry_line_no,
                processed_bytes=jsonl_file.stat().st_size,
                last_event_timestamp=entries[-1].timestamp if entries else None,
            )

        # 校验：每个发现的文件都被解析（discovered == parsed）
        if set(discovered_files) != set(parsed_files):
            return {
                "status": "error",
                "message": "文件消费不一致：部分发现的 JSONL 文件未被解析",
                "discovered_files": discovered_files,
                "parsed_files": parsed_files,
            }

        # 分页（跨文件聚合后统一分页）
        chunks = paginate_entries(all_entries)

        # 创建输出目录
        output_path.mkdir(parents=True, exist_ok=True)

        # 输出 chunk 文件
        chunk_files = []
        for i, chunk in enumerate(chunks):
            chunk_file = output_path / f"chunk-{i:02d}.md"
            content = turn_to_markdown(chunk, i, len(chunks))
            chunk_file.write_text(content, encoding='utf-8')
            chunk_files.append({
                "file": str(chunk_file),
                "tokens_est": sum(estimate_entries_tokens([t]) for t in chunk),
                "turns": len(chunk)
            })

        state = SyncState(
            version=VERSION,
            last_full_sync=datetime.now().isoformat(),
            last_incremental_sync=None,
            project_hash=compute_project_hash(project_root),
            files=files_state,
        )
        save_sync_state(state, output_path / "sync-state.json")

        return {
            "status": "success",
            "mode": "full",
            "total_entries": len(all_entries),
            "processed_entries": len(all_entries),
            "discovered_files": discovered_files,
            "parsed_files": parsed_files,
            "chunks": chunk_files,
            "sync_state": state_to_dict(state),  # S1
        }


def export_incremental(project_root: str, output_dir: str) -> dict:
    """
    增量导出

    参数：
    - project_root: 项目根目录
    - output_dir: 输出目录

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
            return {"status": "error", "message": "未找到 JSONL 文件"}

        discovered_files = [str(f) for f in jsonl_files]
        parsed_files: list[str] = []
        all_entries: list[ConversationEntry] = []

        for jsonl_file in jsonl_files:
            file_key = str(jsonl_file)
            if file_key in state.files:
                # S2: processed_lines 是物理行号，+1 起始下一行
                start_line = state.files[file_key].processed_lines + 1
            else:
                start_line = 0

            # 解析新增内容
            entries = list(parse_jsonl(jsonl_file, start_line))
            all_entries.extend(entries)
            parsed_files.append(str(jsonl_file))

            if not entries:
                continue

            # S2: processed_lines 用最后一条 entry 的真实行号（而非 len(entries)），避免单位混用与状态漂移
            new_processed_lines = entries[-1].line_no
            new_processed_bytes = jsonl_file.stat().st_size
            new_last_ts = entries[-1].timestamp

            if file_key in state.files:
                # 直接赋值为最后一条 entry 的行号
                state.files[file_key].processed_lines = new_processed_lines
                state.files[file_key].processed_bytes = new_processed_bytes
                state.files[file_key].last_event_timestamp = new_last_ts
                state.files[file_key].mtime = jsonl_file.stat().st_mtime
                # total_lines 为信息字段，不参与增量逻辑，保持原值（可能略陈旧）
            else:
                # S7: 统一 encoding='utf-8' + with；total_lines 用单次扫描
                state.files[file_key] = FileInfo(
                    path=str(jsonl_file),
                    sha256=compute_file_sha256(jsonl_file),
                    mtime=jsonl_file.stat().st_mtime,
                    total_lines=count_physical_lines(jsonl_file),
                    processed_lines=new_processed_lines,
                    processed_bytes=new_processed_bytes,
                    last_event_timestamp=new_last_ts,
                )

        # 校验：每个发现的文件都被解析（discovered == parsed）
        if set(discovered_files) != set(parsed_files):
            return {
                "status": "error",
                "message": "文件消费不一致：部分发现的 JSONL 文件未被解析",
                "discovered_files": discovered_files,
                "parsed_files": parsed_files,
            }

        if not all_entries:
            return {
                "status": "success",
                "message": "无新内容",
                "new_entries": 0,
                "discovered_files": discovered_files,
                "parsed_files": parsed_files,
            }

        # 分页（通常只有 1 个 chunk）
        chunks = paginate_entries(all_entries)

        # 创建输出目录
        output_path.mkdir(parents=True, exist_ok=True)

        # 输出 chunk 文件
        chunk_files = []
        for i, chunk in enumerate(chunks):
            chunk_file = output_path / f"chunk-inc-{i:02d}.md"
            content = turn_to_markdown(chunk, i, len(chunks))
            chunk_file.write_text(content, encoding='utf-8')
            chunk_files.append({
                "file": str(chunk_file),
                "tokens_est": sum(estimate_entries_tokens([t]) for t in chunk),
                "turns": len(chunk)
            })

        state.last_incremental_sync = datetime.now().isoformat()
        save_sync_state(state, state_file)

        return {
            "status": "success",
            "mode": "incremental",
            "new_entries": len(all_entries),
            "discovered_files": discovered_files,
            "parsed_files": parsed_files,
            "chunks": chunk_files,
            "sync_state": state_to_dict(state),  # S1
        }


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
        return {"status": "error", "message": f"目标路径不是目录：{output_path}"}

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
    parser.add_argument("--mode", choices=["full", "incremental", "status", "cleanup"], required=True)
    parser.add_argument("--project-path", default=".")
    parser.add_argument("--output", default=".evolution/chunks")

    try:
        args = parser.parse_args()

        # M6: 防御性类型校验
        if not isinstance(args.project_path, str) or not args.project_path:
            raise ValueError("--project-path 必须是非空字符串")
        if not isinstance(args.output, str) or not args.output:
            raise ValueError("--output 必须是非空字符串")

        if args.mode in ("full", "incremental"):
            if not os.path.isdir(args.project_path):
                result = {"status": "error", "message": f"项目路径不存在：{args.project_path}"}
                print(json.dumps(result, ensure_ascii=False, indent=2))
                sys.exit(1)

        if args.mode == "full":
            result = export_full(args.project_path, args.output)
        elif args.mode == "incremental":
            result = export_incremental(args.project_path, args.output)
        elif args.mode == "status":
            state_file = Path(args.output) / "sync-state.json"
            state = load_sync_state(state_file)
            result = {"status": "success", "state": state_to_dict(state)}  # S1
        elif args.mode == "cleanup":
            result = cleanup_output(args.output)
        else:  # 防御性兜底（M6）
            raise ValueError(f"未知模式：{args.mode}")

        print(json.dumps(result, ensure_ascii=False, indent=2))  # S3: stdout 已 reconfigure 为 UTF-8

    except SystemExit:
        raise
    except Exception as e:
        # M7: 兜底异常处理，输出结构化错误而非栈
        print(f"[ERROR] {type(e).__name__}: {e}", file=sys.stderr)
        try:
            print(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False, indent=2))
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
