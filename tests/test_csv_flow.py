"""The full log -> list -> retest flow on the CSV backend, through the real CLI."""
import csv
import json
import shutil
from pathlib import Path

import pytest

from qa_bug_logger.cli import main
from qa_bug_logger.model import HEADERS, Bug

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def config(tmp_path, monkeypatch):
    """A copy of the demo project inside a temp dir, so tests never touch the repo."""
    shutil.copytree(EXAMPLES, tmp_path / "examples")
    cfg = tmp_path / "examples" / "demo.json"
    data = json.loads(cfg.read_text(encoding="utf-8"))
    data["csv_folder"] = str(tmp_path / "bug-logs")
    data["evidence_folder"] = str(tmp_path / "evidence")
    cfg.write_text(json.dumps(data), encoding="utf-8")
    return cfg


def log(cfg, bug_id, *extra):
    return main(["log", "--config", str(cfg), "--bug-id", bug_id, "--module", "Cart", "--severity", "High",
                 "--priority", "P2", "--title", f"{bug_id} title", "--description", "d",
                 "--steps", r"1. open\n2. click", "--expected", "e", "--actual", "a", *extra])


def rows(cfg):
    folder = Path(json.loads(cfg.read_text(encoding="utf-8"))["csv_folder"])
    with open(folder / "Demo_Shop.csv", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_log_writes_a_complete_row_with_evidence(config, tmp_path):
    shot = tmp_path / "screen.png"
    shot.write_bytes(b"\x89PNG fake")
    assert log(config, "BUG-001", "--evidence", str(shot)) == 0
    [row] = rows(config)
    assert list(row.keys()) == HEADERS
    assert row["Status"] == "Open"
    assert row["Steps to Reproduce"] == "1. open\n2. click"
    assert row["Evidence"].endswith("Demo Shop/BUG-001/screen.png")
    assert Path(row["Evidence"]).read_bytes() == b"\x89PNG fake"


def test_duplicate_bug_id_is_rejected(config):
    assert log(config, "BUG-001") == 0
    assert log(config, "BUG-001") == 2
    assert len(rows(config)) == 1


def test_retest_resolves_fixed_bugs_and_keeps_open_ones(config, capsys):
    log(config, "BUG-001")
    log(config, "BUG-002")
    log(config, "BUG-003")  # no check configured
    assert main(["retest", "--config", str(config)]) == 0
    by_id = {r["Bug ID"]: r for r in rows(config)}
    assert (by_id["BUG-001"]["Retest Result"], by_id["BUG-001"]["Status"]) == ("Pass", "Resolved")
    assert (by_id["BUG-002"]["Retest Result"], by_id["BUG-002"]["Status"]) == ("Fail", "Open")
    assert "expected 0.16" in by_id["BUG-002"]["Retest Notes"]
    assert by_id["BUG-003"]["Retest Result"] == ""
    assert "1 pass, 1 fail, 1 skipped" in capsys.readouterr().out


def test_fail_on_open_gates_ci(config):
    log(config, "BUG-002")
    assert main(["retest", "--config", str(config), "--fail-on-open"]) == 1


def test_resolved_bugs_drop_out_of_the_open_list(config, capsys):
    log(config, "BUG-001")
    log(config, "BUG-002")
    main(["retest", "--config", str(config)])
    capsys.readouterr()
    main(["list", "--config", str(config)])
    out = capsys.readouterr().out
    assert "BUG-002" in out and "BUG-001" not in out and "1 open bug(s)" in out


@pytest.mark.parametrize("field,value", [("severity", "Urgent"), ("priority", "P9"), ("bug_id", " ")])
def test_invalid_bug_fields_are_rejected(field, value):
    args = dict(bug_id="BUG-1", project="p", module="m", severity="High", priority="P2", title="t",
                description="d", steps="s", expected="e", actual="a")
    args[field] = value
    with pytest.raises(ValueError):
        Bug(**args)
