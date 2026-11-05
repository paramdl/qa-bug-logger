"""
Re-runs the check attached to each open bug and records the outcome.

A check is any script that exits 0 when the bug is fixed and non-zero while it still reproduces.
The project config maps bug IDs to scripts: {"retest_scripts": {"BUG-001": "checks/bug_001.py"}}.
"""
import os
import subprocess
import sys
from pathlib import Path

TIMEOUT_S = 120
NOTES_LIMIT = 500


def run_check(script: Path, env_extra: dict) -> tuple:
    """Returns (passed or None if the script is missing, notes)."""
    if not script.is_file():
        return None, f"check not found: {script}"
    try:
        proc = subprocess.run([sys.executable, str(script)], capture_output=True, text=True,
                              timeout=TIMEOUT_S, env={**os.environ, **env_extra})
    except subprocess.TimeoutExpired:
        return False, f"timed out after {TIMEOUT_S}s"
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()[-NOTES_LIMIT:]


def retest(backend, config: dict, config_dir: Path, only_bug: str = None) -> dict:
    """Retest open bugs (or one bug). Returns {bug_id: 'Pass' | 'Fail' | 'Skipped'}."""
    project = config["project"]
    scripts = config.get("retest_scripts", {})
    env = {k.upper(): str(v) for k, v in config.get("env", {}).items()}
    ids = [only_bug] if only_bug else [b["Bug ID"] for b in backend.get_open_bugs(project)]
    outcome = {}
    for bug_id in ids:
        script = scripts.get(bug_id)
        if not script:
            print(f"  [{bug_id}] no check configured, skipped")
            outcome[bug_id] = "Skipped"
            continue
        passed, notes = run_check(config_dir / script, env)
        if passed is None:
            print(f"  [{bug_id}] {notes}, skipped")
            outcome[bug_id] = "Skipped"
            continue
        result = "Pass" if passed else "Fail"
        backend.update_retest(bug_id, project, result, notes)
        print(f"  [{bug_id}] {result}")
        outcome[bug_id] = result
    return outcome
