#!/usr/bin/env python3
"""Normalize the fetched sources into one deduplicated corpus.

Reads $FAKENEWS_DATA/<source>/ (fetch_sources.py), writes $FAKENEWS_DATA/prepared/:
  corpus.parquet   one row per unique text (the schema below), in first-occurrence order
  prepare.json     counts per source and the corpus_hash

Rules:
  - an occurrence shorter than 21 characters after normalization is dropped
  - an occurrence whose source label is not a verdict (label None) is dropped
  - doc_id = "sha256:" + sha256 of the normalized text; occurrences with the same
    doc_id become one row, and every occurrence is kept in `origins`
  - label: the shared label when every origin agrees; None with label_conflict
    when they do not
  - split: "test" when any origin comes from an upstream test split, else "train";
    split_conflict when origins come from both an upstream train and test split
  - source: the first origin's source, in the order of sources/sources.toml

corpus_hash is sha256 over the canonical JSON lines of the rows (sorted keys),
so it names the data whatever the parquet writer does with the bytes.

usage (repo root): python benchmark/tools/prepare.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bench_env as env  # noqa: E402
import _sources  # noqa: E402

ORIGIN_KEYS = ("source", "source_split", "source_row", "label_raw", "label", "url", "license")
COLUMNS = (
    "doc_id",
    "text",
    "title",
    "url",
    "label",
    "label_conflict",
    "split",
    "split_conflict",
    "source",
    "license",
    "origins",
)


def doc_id(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def collect(root: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    docs: dict[str, dict] = {}
    stats: dict[str, dict] = {}
    for src in env.sources():
        name = src["name"]
        loader = _sources.LOADERS[name]
        c = Counter()
        for o in loader(root / name):
            c["read"] += 1
            if len(o["text"]) <= _sources.MIN_TEXT_LEN:
                c["dropped_short"] += 1
                continue
            if o["label"] is None:
                c["dropped_no_verdict"] += 1
                continue
            c["kept"] += 1
            did = doc_id(o["text"])
            origin = {**{k: o[k] for k in ("source_split", "source_row", "label_raw", "label", "url")}}
            origin.update(source=name, license=src["license"])
            d = docs.get(did)
            if d is None:
                c["new_docs"] += 1
                docs[did] = {"doc_id": did, "text": o["text"], "title": o["title"], "origins": [origin]}
            else:
                if any(x["source"] == name for x in d["origins"]):
                    c["dup_within_source"] += 1
                else:
                    c["dup_of_earlier_source"] += 1
                d["origins"].append(origin)
                if not d["title"] and o["title"]:
                    d["title"] = o["title"]
        stats[name] = dict(c)
    return docs, stats


def finalize(d: dict) -> dict:
    origins = [{k: o[k] for k in ORIGIN_KEYS} for o in d["origins"]]
    labels = {o["label"] for o in origins}
    splits = {o["source_split"] for o in origins}
    first = origins[0]
    return {
        "doc_id": d["doc_id"],
        "text": d["text"],
        "title": d["title"],
        "url": next((o["url"] for o in origins if o["url"]), ""),
        "label": next(iter(labels)) if len(labels) == 1 else None,
        "label_conflict": len(labels) > 1,
        "split": "test" if "test" in splits else "train",
        "split_conflict": {"train", "test"} <= splits,
        "source": first["source"],
        "license": first["license"],
        "origins": origins,
    }


def corpus_hash(rows: list[dict]) -> str:
    h = hashlib.sha256()
    for r in rows:
        h.update(json.dumps(r, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode())
        h.update(b"\n")
    return "sha256:" + h.hexdigest()


def main() -> int:
    root = env.data_root()
    docs, stats = collect(root)
    rows = [finalize(d) for d in docs.values()]
    for r in rows:
        if r["label"] is None and not r["label_conflict"]:
            env.die(f"{r['doc_id']}: no label and no conflict")
    out = env.prepared_dir()
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=list(COLUMNS)).to_parquet(out / "corpus.parquet", index=False)
    summary = {
        "corpus_hash": corpus_hash(rows),
        "n_docs": len(rows),
        "splits": dict(Counter(r["split"] for r in rows)),
        "labels": dict(Counter(str(r["label"]) for r in rows)),
        "label_conflicts": sum(r["label_conflict"] for r in rows),
        "split_conflicts": sum(r["split_conflict"] for r in rows),
        "sources": stats,
        "source_tree_hashes": {s["name"]: s["tree_hash"] for s in env.sources()},
    }
    env.write_json(out / "prepare.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "source_tree_hashes"}, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
