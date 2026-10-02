#!/usr/bin/env python3
"""Write benchmark/experiments/01-corpus/results.json from the prepared corpus.

Tables: what each source contributed, which sources share texts, the conflicts,
and the FACTCK.BR labels the rating scale would have gotten wrong.

usage (repo root): python benchmark/tools/overlap_report.py
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bench_env as env  # noqa: E402
import _sources  # noqa: E402

EXPERIMENT = "01-corpus"


def source_table(prep: dict) -> dict:
    rows = []
    for src in env.sources():
        s = prep["sources"][src["name"]]
        rows.append(
            {
                "source": src["name"],
                "read": s.get("read", 0),
                "dropped_short": s.get("dropped_short", 0),
                "dropped_no_verdict": s.get("dropped_no_verdict", 0),
                "new_docs": s.get("new_docs", 0),
                "dup_earlier": s.get("dup_of_earlier_source", 0),
                "dup_within": s.get("dup_within_source", 0),
                "license": src["license"],
            }
        )
    cols = [
        {"key": "source", "label": "source"},
        {"key": "read", "label": "read", "fmt": "int"},
        {"key": "dropped_short", "label": "too short", "fmt": "int"},
        {"key": "dropped_no_verdict", "label": "no verdict", "fmt": "int"},
        {"key": "new_docs", "label": "new docs", "fmt": "int"},
        {"key": "dup_earlier", "label": "already in an earlier source", "fmt": "int"},
        {"key": "dup_within", "label": "repeated in the source", "fmt": "int"},
        {"key": "license", "label": "license"},
    ]
    return {"title": "what each source contributed, in source order", "columns": cols, "rows": rows}


def overlap_table(df: pd.DataFrame) -> dict:
    pairs = Counter()
    for origins in df["origins"]:
        names = sorted({o["source"] for o in origins})
        for a, b in combinations(names, 2):
            pairs[(a, b)] += 1
    rows = [{"a": a, "b": b, "shared": n} for (a, b), n in sorted(pairs.items(), key=lambda t: (-t[1], t[0]))]
    cols = [
        {"key": "a", "label": "source"},
        {"key": "b", "label": "source"},
        {"key": "shared", "label": "texts in both", "fmt": "int"},
    ]
    return {"title": "texts shared between sources", "columns": cols, "rows": rows}


def corpus_table(prep: dict, df: pd.DataFrame) -> dict:
    rows = []
    for split in ("train", "test"):
        part = df[df["split"] == split]
        rows.append(
            {
                "split": split,
                "docs": len(part),
                "fake": int((part["label"] == "fake").sum()),
                "true": int((part["label"] == "true").sum()),
                "label_conflict": int(part["label_conflict"].sum()),
                "split_conflict": int(part["split_conflict"].sum()),
            }
        )
    cols = [
        {"key": "split", "label": "split"},
        {"key": "docs", "label": "docs", "fmt": "int"},
        {"key": "fake", "label": "fake", "fmt": "int"},
        {"key": "true", "label": "true", "fmt": "int"},
        {"key": "label_conflict", "label": "label conflicts", "fmt": "int"},
        {"key": "split_conflict", "label": "split conflicts", "fmt": "int"},
    ]
    notes = [f"corpus_hash {prep['corpus_hash']}, {prep['n_docs']} docs"]
    return {"title": "the corpus", "columns": cols, "rows": rows, "notes": notes}


def factck_table(root: Path) -> dict:
    df = pd.read_csv(root / "factck-br" / "FACTCKBR.tsv", sep="\t")
    df["text_label"] = df["alternativeName"].map(lambda s: _sources.norm(s).lower())
    df["kept_as"] = df["text_label"].map(_sources.FACTCK_LABELS).fillna("dropped")
    df["scale_rule"] = df["ratingValue"].map(
        lambda v: "dropped" if pd.isna(v) or v == 3 else ("fake" if v <= 2 else "true")
    )
    g = df.groupby(["ratingValue", "kept_as", "scale_rule"], dropna=False).size().reset_index(name="n")
    rows = [
        {"rating": "-" if pd.isna(r.ratingValue) else int(r.ratingValue), "text": r.kept_as, "scale": r.scale_rule, "n": int(r.n)}
        for r in g.itertuples()
    ]
    wrong = int(((df["kept_as"] != "dropped") & (df["scale_rule"] != "dropped") & (df["kept_as"] != df["scale_rule"])).sum())
    cols = [
        {"key": "rating", "label": "ratingValue"},
        {"key": "text", "label": "label from the text rating"},
        {"key": "scale", "label": "label from the numeric scale"},
        {"key": "n", "label": "claims", "fmt": "int"},
    ]
    notes = [
        f"{wrong} claims get opposite labels from the two rules, before the length filter. "
        "The numeric rule (<=2 fake, 3 dropped, >=4 true) is the one Urna's corpus_next.v1 loader used; "
        "this corpus uses the text rating."
    ]
    return {"title": "FACTCK.BR: text rating against the numeric scale", "columns": cols, "rows": rows, "notes": notes}


def main() -> int:
    prepared = env.prepared_dir()
    prep = json.loads((prepared / "prepare.json").read_text())
    df = pd.read_parquet(prepared / "corpus.parquet")
    doc = {
        "experiment": EXPERIMENT,
        "title": "seven sources, one deduplicated corpus",
        "provenance": {
            "status": "measured",
            "source": "benchmark/tools/overlap_report.py over prepare.py output",
            "date": dt.date.today().isoformat(),
            "notes": "sources at the revisions and tree hashes pinned in sources/sources.toml",
        },
        "tables": [source_table(prep), corpus_table(prep, df), overlap_table(df), factck_table(env.data_root())],
    }
    env.write_json(env.EXPERIMENTS / EXPERIMENT / "results.json", doc)
    print(f"written: {env.rel(env.EXPERIMENTS / EXPERIMENT / 'results.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
