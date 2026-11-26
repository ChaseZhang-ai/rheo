"""CLI 合同测试：validate/gen 的退出码语义。

--lenient 的合同（--help 文案）：数据问题只报告不拒绝；无法读取的文件仍以退出码 2 报告。
"""

import json

from rheotrace.cli import main
from rheotrace.core import dumps_line
from rheotrace.gen import generate_file


def _corrupt_mode(path):
    """生成一份合法 trace，再把第一个 weight_sync 的 mode 改成非法值：文件可读，恰产一个 E06。"""
    generate_file(path, preset="grpo", seed=2)
    events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    for e in events:
        if e["type"] == "weight_sync":
            e["mode"] = "bogus"
            break
    path.write_text("\n".join(dumps_line(e) for e in events) + "\n")
    return path


def test_strict_data_error_exit_1(tmp_path):
    p = _corrupt_mode(tmp_path / "bad.jsonl")
    assert main(["validate", str(p)]) == 1


def test_lenient_data_error_reports_without_rejecting(tmp_path, capsys):
    """--lenient 合同：数据问题打印完整报告（REJECTED + E 行）但退出码 0。"""
    p = _corrupt_mode(tmp_path / "bad.jsonl")
    assert main(["validate", str(p), "--lenient"]) == 0
    out = capsys.readouterr().out
    assert "REJECTED" in out and "[E06]" in out


def test_lenient_unreadable_file_still_exit_2(tmp_path):
    assert main(["validate", str(tmp_path / "nope.jsonl"), "--lenient"]) == 2


def test_strict_unreadable_file_exit_2(tmp_path):
    assert main(["validate", str(tmp_path / "nope.jsonl")]) == 2


def test_valid_file_exit_0_both_modes(tmp_path):
    p = tmp_path / "good.jsonl"
    generate_file(p, preset="grpo", seed=1)
    assert main(["validate", str(p)]) == 0
    assert main(["validate", str(p), "--lenient"]) == 0


def test_warnings_only_never_rejects(tmp_path):
    """W 级（末行残缺截断）两模式下都退出码 0：拒绝只由 error 触发。"""
    p = tmp_path / "w.jsonl"
    generate_file(p, preset="grpo", seed=3)
    body = p.read_text()
    p.write_text(body + '{"ts":1,"type":')  # 末行残缺且无换行 → W01
    assert main(["validate", str(p)]) == 0
    assert main(["validate", str(p), "--lenient"]) == 0


def test_gen_writes_file_and_reports_count(tmp_path, capsys):
    out = tmp_path / "gen.jsonl"
    assert main(["gen", "--preset", "grpo", "--seed", "5", "--out", str(out)]) == 0
    assert out.exists()
    assert " events " in capsys.readouterr().out


def test_gen_unwritable_out_exit_2(tmp_path):
    assert main(["gen", "--preset", "grpo", "--seed", "5", "--out", str(tmp_path)]) == 2
