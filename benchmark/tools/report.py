#!/usr/bin/env python3
"""Write benchmark/experiments/02-retrieval/results.json from benchmark/runs/*.json.

One row per build (model x preset): size, the four quality metrics over every
query, the same per query family, and search time. evaluate.py writes the runs.

usage (repo root): python benchmark/tools/report.py
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bench_env as env  # noqa: E402

EXPERIMENT = "02-retrieval"
METRICS = ("ndcg@10", "recall@10", "recall@100", "hit@1")
ORDER = {"exact": 0, "tiny": 1, "hybrid": 2}


def metric_cols() -> list[dict]:
    return [{"key": m, "label": m, "fmt": "f3"} for m in METRICS]


def main() -> int:
    runs = [json.loads(p.read_text()) for p in sorted(env.RUNS.glob("*.json"))]
    if not runs:
        env.die("no runs under benchmark/runs; run evaluate.py first")
    want = env.corpus_hash()
    stale = [r["build"] for r in runs if r.get("corpus_hash") != want]
    if stale:
        env.die(f"runs from another corpus version: {', '.join(stale)}; rebuild and re-evaluate them")
    models = [m["name"] for m in env.load_toml(env.MODELS_TOML)["model"]]
    runs.sort(key=lambda r: (models.index(r["model"]) if r["model"] in models else 99, ORDER.get(r["preset"], 9)))
    n = runs[0]["n_queries"]
    main_rows = [
        {"model": r["model"], "preset": r["preset"], "bytes": r["bytes"], **r["all"], "ms": r["search_ms_per_query"]}
        for r in runs
    ]
    main_table = {
        "title": f"all {n} queries",
        "columns": [
            {"key": "model", "label": "model"},
            {"key": "preset", "label": "preset"},
            {"key": "bytes", "label": "file MB", "fmt": "mb"},
            *metric_cols(),
            {"key": "ms", "label": "search ms/query", "fmt": "f2"},
        ],
        "rows": main_rows,
        "notes": [
            "nDCG@10 is graded (2 for the document the headline was written for, 1 for its FakeTrue.Br pair); "
            "recall counts any judged document; hit@1 asks for the grade-2 document at rank 1.",
            "Search time is the python call after the query vector exists, on the build machine; it leaves out "
            "embedding the query.",
        ],
    }
    fam_tables = []
    for fam, label in (("ftb", "FakeTrue.Br headlines"), ("fck", "FACTCK.BR titles")):
        rows = [{"model": r["model"], "preset": r["preset"], **r["by_family"][fam]} for r in runs if fam in r["by_family"]]
        if rows:
            fam_tables.append(
                {
                    "title": f"{label} ({rows[0]['n']} queries)",
                    "columns": [{"key": "model", "label": "model"}, {"key": "preset", "label": "preset"}, *metric_cols()],
                    "rows": [{k: v for k, v in r.items() if k != "n"} for r in rows],
                }
            )
    doc = {
        "experiment": EXPERIMENT,
        "title": "retrieval quality per model and preset",
        "corpus_hash": want,
        "provenance": {
            "status": "measured",
            "source": "benchmark/tools/evaluate.py runs, scored against benchmark/queries/qrels.tsv",
            "date": dt.date.today().isoformat(),
            "notes": f"corpus {want}; silver qrels, every number is a lower bound shared by all rows (docs/methodology.md)",
        },
        "tables": [main_table, *fam_tables],
    }
    env.write_json(env.EXPERIMENTS / EXPERIMENT / "results.json", doc)
    print(f"written: {env.rel(env.EXPERIMENTS / EXPERIMENT / 'results.json')} ({len(runs)} runs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
