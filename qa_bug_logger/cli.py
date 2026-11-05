"""
qa-bug-logger command line.

  python -m qa_bug_logger log    --config configs/demo.json --bug-id BUG-001 --module Login ...
  python -m qa_bug_logger list   --config configs/demo.json
  python -m qa_bug_logger retest --config configs/demo.json [--bug-id BUG-001]
"""
import argparse
import json
import sys
from pathlib import Path

from .backends import make_backend
from .evidence import make_evidence_store
from .model import PRIORITIES, SEVERITIES, Bug
from .retest import retest


def load_config(path: str) -> tuple:
    p = Path(path)
    with open(p, encoding="utf-8") as fh:
        return json.load(fh), p.parent


def cmd_log(args) -> int:
    config, _ = load_config(args.config)
    bug = Bug(bug_id=args.bug_id, project=config["project"], module=args.module, severity=args.severity,
              priority=args.priority, title=args.title, description=args.description,
              steps=args.steps.replace("\\n", "\n"), expected=args.expected, actual=args.actual,
              reporter=args.reporter)
    if args.evidence:
        print(f"Storing {len(args.evidence)} evidence file(s)...")
        bug.evidence = make_evidence_store(config).store(args.evidence, bug.project, bug.bug_id)
    row = make_backend(config).log_bug(bug)
    print(f"Logged {bug.bug_id} ({bug.severity}/{bug.priority}) at row {row}")
    return 0


def cmd_list(args) -> int:
    config, _ = load_config(args.config)
    bugs = make_backend(config).get_open_bugs(config["project"])
    for b in bugs:
        print(f"{b['Bug ID']:<10} {b['Severity']:<9} {b['Priority']:<3} {b['Title']}")
    print(f"{len(bugs)} open bug(s)")
    return 0


def cmd_retest(args) -> int:
    config, config_dir = load_config(args.config)
    outcome = retest(make_backend(config), config, config_dir, args.bug_id)
    failed = [b for b, r in outcome.items() if r == "Fail"]
    print(f"Retest complete: {sum(r == 'Pass' for r in outcome.values())} pass, {len(failed)} fail, "
          f"{sum(r == 'Skipped' for r in outcome.values())} skipped")
    return 1 if (failed and args.fail_on_open) else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="qa_bug_logger", description="Log bugs with evidence and retest them")
    sub = p.add_subparsers(dest="command", required=True)

    log = sub.add_parser("log", help="log a new bug")
    log.add_argument("--config", required=True)
    log.add_argument("--bug-id", required=True)
    log.add_argument("--module", required=True)
    log.add_argument("--severity", choices=SEVERITIES, required=True)
    log.add_argument("--priority", choices=PRIORITIES, required=True)
    log.add_argument("--title", required=True)
    log.add_argument("--description", required=True)
    log.add_argument("--steps", required=True, help=r"use \n between steps")
    log.add_argument("--expected", required=True)
    log.add_argument("--actual", required=True)
    log.add_argument("--reporter", default="QA Team")
    log.add_argument("--evidence", nargs="*", default=[], help="screenshots / videos")
    log.set_defaults(func=cmd_log)

    lst = sub.add_parser("list", help="list open bugs")
    lst.add_argument("--config", required=True)
    lst.set_defaults(func=cmd_list)

    rt = sub.add_parser("retest", help="re-run checks for open bugs and record the result")
    rt.add_argument("--config", required=True)
    rt.add_argument("--bug-id")
    rt.add_argument("--fail-on-open", action="store_true", help="exit 1 if any retested bug still fails")
    rt.set_defaults(func=cmd_retest)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
