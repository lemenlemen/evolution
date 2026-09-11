#!/usr/bin/env python3
"""sha256 不变量回归测试（V4.1.4 新增，V4.1.5 重写测试 1）

覆盖三组断言（对应 V4.1.3 sha256 刷新修复的核心语义）：
1. 增量导出后 sha256 刷新防止误判 file-replaced（真实 export_full →
   commit → 追加 → export_incremental → commit → 追加 →
   export_incremental 全流程，锁定 L1867 sha256 刷新路径）
2. status 只读模式不修改磁盘文件（含损坏主文件 + 有效备份的场景）
3. 损坏恢复链正确回写（写模式：损坏改名留存 + 立即回写恢复结果）

运行：python -m unittest test_sha256_invariant -v
（在 .claude/skills/evolution/tests/ 目录下执行；仅依赖标准库）
"""

import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_ENGINE = Path(__file__).resolve().parent.parent / "evolution-export.py"


def _load_engine():
    spec = importlib.util.spec_from_file_location("evolution_export", str(_ENGINE))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


eng = _load_engine()


def _line(role, text, ts="2026-09-10T00:00:00", session="s1"):
    return json.dumps(
        {"type": role, "message": {"content": text}, "timestamp": ts, "sessionId": session},
        ensure_ascii=False,
    )


class TestSha256Invariant(unittest.TestCase):
    def test_sha256_refresh_in_incremental_export(self):
        """测试：增量导出后 sha256 刷新防止误判 file-replaced。

        真实流程：export_full → commit → 追加 → export_incremental
        （断言状态 sha256 == 文件实际 sha256，即 L1867 刷新路径）→
        commit → 再次追加 → export_incremental（断言无 file-replaced 误判）。

        若删除 L1867 的 sha256 刷新，第二次增量会因“旧 size + 陈旧 hash”
        导致 _is_byte_prefix 失败而误判 file-replaced，本测试即失败。
        """
        orig_find = eng.find_jsonl_file
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            jsonl_file = td / "test-session.jsonl"
            output_dir = td / "chunks"
            output_dir.mkdir()
            state_file = output_dir / "sync-state.json"

            def _fake_find(project_root, _td=td, _jf=jsonl_file):
                if Path(project_root) == _td and _jf.exists():
                    return [_jf]
                return orig_find(project_root)

            eng.find_jsonl_file = _fake_find
            try:
                # 创建初始 JSONL（5 条对话）
                with open(jsonl_file, "w", encoding="utf-8") as f:
                    for i in range(5):
                        role = "user" if i % 2 == 0 else "assistant"
                        f.write(_line(role, f"msg{i}", ts=f"2026-01-01T00:00:0{i}") + "\n")

                # 全量导出 + 提交（提交后 committed_lines == exported_lines，无 in-flight 批次）
                result_full = eng.export_full(str(td), str(output_dir))
                self.assertEqual(result_full["status"], "success")
                full_batch = result_full.get("batch_id")
                self.assertTrue(full_batch, "全量导出应返回 batch_id")
                rc = eng.commit_batch(full_batch, state_file)
                self.assertEqual(rc["status"], "success")

                # 第 1 次追加（2 条）
                with open(jsonl_file, "a", encoding="utf-8") as f:
                    for i in range(5, 7):
                        role = "user" if i % 2 == 0 else "assistant"
                        f.write(_line(role, f"msg{i}", ts=f"2026-01-01T00:00:0{i}") + "\n")

                # 增量导出（应刷新 sha256）
                result_inc1 = eng.export_incremental(str(td), str(output_dir))
                self.assertEqual(result_inc1["status"], "success")

                # 读取状态文件，验证 sha256 已刷新
                with open(state_file, "r", encoding="utf-8") as f:
                    state_data = json.load(f)

                actual_sha256 = eng.compute_file_sha256(jsonl_file)
                self.assertIn(str(jsonl_file), state_data["files"])
                for file_key, file_info in state_data["files"].items():
                    self.assertEqual(
                        file_info["sha256"], actual_sha256,
                        f"sha256 未刷新：状态 {file_info['sha256']} != 实际 {actual_sha256}",
                    )

                # 提交第 1 个增量批次，消除 in-flight，使第 2 次追加走新增量路径
                inc1_batch = result_inc1.get("batch_id")
                self.assertTrue(inc1_batch, "增量导出应返回 batch_id")
                rc1 = eng.commit_batch(inc1_batch, state_file)
                self.assertEqual(rc1["status"], "success")

                # 第 2 次追加（2 条）
                with open(jsonl_file, "a", encoding="utf-8") as f:
                    for i in range(7, 9):
                        role = "user" if i % 2 == 0 else "assistant"
                        f.write(_line(role, f"msg{i}", ts=f"2026-01-01T00:00:0{i}") + "\n")

                # 再次增量导出（不应误判 file-replaced）
                result_inc2 = eng.export_incremental(str(td), str(output_dir))
                self.assertEqual(result_inc2["status"], "success")
                warning_codes = [w["code"] for w in result_inc2.get("warnings", [])]
                self.assertNotIn(
                    "file-replaced", warning_codes,
                    f"第 2 次追加触发 file-replaced 误判：{warning_codes}",
                )
            finally:
                eng.find_jsonl_file = orig_find

    def test_status_readonly_does_not_touch_disk(self):
        """断言 2：readonly=True（含损坏主文件场景）不搬迁、不回写、不新增文件。"""
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            state_file = d / "sync-state.json"
            state = eng.SyncState(
                version=eng.VERSION,
                last_full_sync=None,
                last_incremental_sync=None,
                project_hash="test",
                files={},
            )
            eng.save_sync_state(state, state_file)
            before_bytes = state_file.read_bytes()
            before_listing = sorted(x.name for x in d.iterdir())

            # 健康状态只读加载：磁盘无变化
            eng.load_sync_state(state_file, readonly=True)
            self.assertEqual(state_file.read_bytes(), before_bytes)
            self.assertEqual(sorted(x.name for x in d.iterdir()), before_listing)

            # 损坏主文件 + 有效备份：只读模式仅内存恢复，磁盘原样保留
            bak = state_file.with_suffix(".json.bak")
            shutil.copy2(state_file, bak)
            state_file.write_text("{ not valid json", encoding="utf-8")
            corrupt_bytes = state_file.read_bytes()
            eng.load_sync_state(state_file, readonly=True)
            self.assertEqual(state_file.read_bytes(), corrupt_bytes, "只读模式不得回写损坏主文件")
            self.assertEqual(
                list(d.glob("sync-state.json.corrupt-*")), [], "只读模式不得搬迁损坏文件"
            )

    def test_corrupt_recovery_chain_writes_back(self):
        """断言 3：写模式损坏恢复链——损坏改名留存 + 主文件回写为有效状态。"""
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            state_file = d / "sync-state.json"
            state = eng.SyncState(
                version=eng.VERSION,
                last_full_sync=None,
                last_incremental_sync=None,
                project_hash="test",
                files={},
            )
            eng.save_sync_state(state, state_file)
            bak = state_file.with_suffix(".json.bak")
            shutil.copy2(state_file, bak)
            state_file.write_text("{ not valid json", encoding="utf-8")

            recovered = eng.load_sync_state(state_file, readonly=False)
            self.assertEqual(recovered.version, eng.VERSION)
            # 主文件已回写为可解析 JSON
            data = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertEqual(data.get("version"), eng.VERSION)
            # 损坏文件改名留存 exactly 一份
            corrupt = list(d.glob("sync-state.json.corrupt-*"))
            self.assertEqual(len(corrupt), 1, "损坏文件应改名留存一份")
            # 备份仍在
            self.assertTrue(bak.exists(), "恢复后 .bak 备份应保留")


if __name__ == "__main__":
    sys.exit(unittest.main(verbosity=2))
