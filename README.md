# QA Bug Logger

[![tests](https://github.com/paramdl/qa-bug-logger/actions/workflows/tests.yml/badge.svg)](https://github.com/paramdl/qa-bug-logger/actions/workflows/tests.yml)

Log bugs in a consistent format with screenshots and videos attached, then **retest them automatically**:
each bug can carry a small check script, and one command re-runs every open bug's check, marks fixed bugs
*Resolved* and records the output of the ones that still fail.

Works out of the box with a local CSV log. Google Sheets (one tab per project) and Google Drive evidence
are optional backends for teams that share a tracker.

## Try it (no account needed)
```bash
python -m qa_bug_logger log --config examples/demo.json --bug-id BUG-001 --module Pricing \
  --severity High --priority P2 --title "Discount over 100% gives a negative price" \
  --description "Coupon above 100% is accepted" --steps "1. Add item\n2. Apply 150% coupon" \
  --expected "Price floors at 0" --actual "Price is -25.00" --evidence screenshot.png

python -m qa_bug_logger list   --config examples/demo.json
python -m qa_bug_logger retest --config examples/demo.json
```
The demo app ([`examples/shop.py`](examples/shop.py)) has one fixed bug and one open one, so a retest shows
`1 pass, 1 fail`: BUG-001 moves to *Resolved*, BUG-002 stays *Open* with the failing check's output in *Retest Notes*.

## How retesting works
A check is any script that **exits 0 when the bug is fixed** and non-zero while it still reproduces: a pytest
file, a Playwright script, a `curl` wrapper. Map bug IDs to checks in the project config:
```json
"retest_scripts": { "BUG-001": "checks/bug_001_negative_price.py" }
```
`retest --fail-on-open` exits 1 if any retested bug still fails, so the same command can gate a CI job.
Values under `"env"` in the config are passed to every check as upper-case environment variables (e.g. `BASE_URL`).

## Backends
| Config | Stores | Needs |
|---|---|---|
| `"backend": "csv"` | one CSV per project, 17 standard columns | nothing |
| `"backend": "sheets"` | one Google Sheets tab per project, header bold + frozen | `pip install -r requirements-google.txt`, an OAuth client file |
| `"evidence": "local"` | files copied to `evidence/<project>/<bug-id>/` | nothing |
| `"evidence": "drive"` | files uploaded to Drive under `<folder>/<project>/` | as above |

See [`examples/google.example.json`](examples/google.example.json). Keep `client_secrets.json` and the token file out of git (both are in `.gitignore`).

## Security choices
- **Evidence stays private by default.** Screenshots often show user data, so Drive files are only shared by link when `"share_public": true`.
- **Drive queries are escaped**, so a project name containing a quote can't break or change the folder lookup.
- **OAuth tokens are stored as JSON**, not pickled; nothing is executed when the token is loaded.
- **Bug fields are validated** (severity, priority, non-empty ID) and duplicate IDs are rejected.

## Tests
```bash
pip install -r requirements-dev.txt && pytest -q
```
Covers the full log → list → retest flow through the CLI, evidence copying, duplicate and invalid input,
the CI gate, and Drive query escaping. Runs on every push in GitHub Actions.
