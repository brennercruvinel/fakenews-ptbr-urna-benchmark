#!/usr/bin/env python3
"""Write benchmark/experiments/04-clean-install/results.json from a check_clean.sh run.

  python benchmark/tools/record_clean.py WORK_DIR

Refuses a run with a failed check, a run of another corpus version, or a run of a
commit other than this checkout's HEAD: the result names exactly what was verified.
"""

from __future__ import annotations

import argparse
import datetime as dt
import platform
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bench_env as env  # noqa: E402

EXPERIMENT = "04-clean-install"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("work")
    args = ap.parse_args()
    work = Path(args.work)
    commit = (work / "commit").read_text().strip()
    head = subprocess.run(["git", "-C", str(env.REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if commit != head:
        env.die(f"the check ran on {commit[:12]}, this checkout is at {head[:12]}")
    rows = [dict(zip(("status", "check", "value"), line.split("\t"))) for line in (work / "checks.tsv").read_text().splitlines()]
    failed = [r["check"] for r in rows if r["status"] != "ok"]
    if failed:
        env.die(f"failed checks: {', '.join(failed)}")
    corpus = next(r["value"] for r in rows if r["check"] == "corpus_hash")
    env.require_corpus(corpus, "the clean-install check")
    doc = {
        "experiment": EXPERIMENT,
        "title": "the README from a fresh clone",
        "corpus_hash": corpus,
        "provenance": {
            "status": "measured",
            "source": "benchmark/tools/check_clean.sh, recorded by record_clean.py",
            "date": dt.date.today().isoformat(),
            "notes": f"commit {commit}; fresh clone, uv sync, empty FAKENEWS_DATA; {platform.system()} {platform.machine()}, cpu",
        },
        "tables": [
            {
                "title": "every identity the repo pins, reproduced",
                "columns": [{"key": "check", "label": "check"}, {"key": "value", "label": "result"}],
                "rows": [{"check": r["check"], "value": r["value"]} for r in rows],
            }
        ],
    }
    env.write_json(env.EXPERIMENTS / EXPERIMENT / "results.json", doc)
    print(f"written: {env.rel(env.EXPERIMENTS / EXPERIMENT / 'results.json')} (commit {commit[:12]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
