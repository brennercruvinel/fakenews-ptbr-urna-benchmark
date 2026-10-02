#!/usr/bin/env python3
"""Write benchmark/experiments/03-stability/results.json: does a build come back the same?

Three checks, none of them about relevance:
  re-embed   the first SAMPLE documents embedded again with the same model and
             device, compared bit for bit with the vectors the build used
  rebuild    every build run again by build.py into a scratch dir; same file_hash?
             (vectors come from the embed cache, so this isolates urna.build)
  agreement  per model, how much of each preset's top-10 documents is in the
             exact preset's top-10, over every query (the exact run is the
             reference for ranking agreement, not for relevance)

Rows from an earlier run are kept for the builds not given now, so the check can
run one model at a time when disk or memory is short.

usage (repo root): python benchmark/tools/stability.py candidates/*
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bench_env as env  # noqa: E402
import _embed  # noqa: E402

EXPERIMENT = "03-stability"
SAMPLE = 1000


def top10(run: Path) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    for line in run.read_text().splitlines():
        qid, _, did, rank, _, _ = line.split(" ")
        if int(rank) <= 10:
            out[qid].append(did)
    return out


def reembed(model: str, device: str, doc_ids: list[str], texts: list[str]) -> dict:
    emb = _embed.load(model, device)
    ref = np.load(_embed.cache_path(emb.entry, device, doc_ids), mmap_mode="r")[: len(texts)]
    again = emb.embed(texts)
    return {"identical": bool(np.array_equal(ref, again)), "max_abs_diff": float(np.max(np.abs(ref - again)))}


def rebuild(build_dir: Path, lock: dict, scratch: Path) -> bool:
    out = scratch / build_dir.name
    cmd = [sys.executable, str(Path(__file__).with_name("build.py")), "--model", lock["model"]["name"],
           "--preset", lock["build"]["preset"], "--device", lock["environment"]["device"], "--out", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)
    again = json.loads((out / "build.lock.json").read_text())["output"]["file_hash"]
    shutil.rmtree(out)  # one rebuild on disk at a time
    return again == lock["output"]["file_hash"]


def merge(table: int, rows: list[dict], key: tuple[str, ...]) -> list[dict]:
    """Keep the rows of a previous run for builds not measured now, so the check can run
    one model at a time; rows measured now replace theirs. Ordered by models.toml, then preset."""
    path = env.EXPERIMENTS / EXPERIMENT / "results.json"
    prev = json.loads(path.read_text()) if path.is_file() else {}
    # rows of another corpus version never survive into this one
    old = prev["tables"][table]["rows"] if prev.get("corpus_hash") == env.corpus_hash() else []
    fresh = {tuple(r[k] for k in key) for r in rows}
    merged = [r for r in old if tuple(r[k] for k in key) not in fresh] + rows
    models = list(_embed.models())
    presets = {"exact": 0, "tiny": 1, "hybrid": 2}

    def order(r: dict):
        name = r.get("model") or r["build"].rsplit("-", 1)[0]
        preset = r.get("preset") or (r["build"].rsplit("-", 1)[1] if "build" in r else "")
        return (models.index(name) if name in models else 99, presets.get(preset, 9))

    return sorted(merged, key=order)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("builds", nargs="+")
    args = ap.parse_args()
    corpus = pd.read_parquet(env.prepared_dir() / "corpus.parquet", columns=["doc_id", "text"])
    doc_ids, texts = list(corpus["doc_id"]), list(corpus["text"][:SAMPLE])
    builds = [Path(b) for b in args.builds]
    locks = {b: json.loads((b / "build.lock.json").read_text()) for b in builds}
    for b, lock in locks.items():
        env.require_corpus(lock["corpus"]["corpus_hash"], env.rel(b))

    embed_rows, seen = [], set()
    for b, lock in locks.items():
        key = (lock["model"]["name"], lock["environment"]["device"])
        if key in seen:
            continue
        seen.add(key)
        r = reembed(*key, doc_ids, texts)
        embed_rows.append({"model": key[0], "device": key[1], **r})
        print(f"re-embed {key}: {r}")

    build_rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for b, lock in locks.items():
            same = rebuild(b, lock, Path(tmp))
            build_rows.append({"build": b.name, "file_hash": lock["output"]["file_hash"][:19], "same": same})
            print(f"rebuild {b.name}: {'same file_hash' if same else 'DIFFERENT'}")

    agree_rows = []
    for b, lock in locks.items():
        model, preset = lock["model"]["name"], lock["build"]["preset"]
        ref, run = env.RUNS / f"{model}-exact.run", env.RUNS / f"{b.name}.run"
        if preset == "exact" or not (ref.is_file() and run.is_file()):
            continue
        for r in (ref, run):
            env.require_corpus(json.loads(r.with_suffix(".json").read_text()).get("corpus_hash", ""), env.rel(r))
        a, e = top10(run), top10(ref)
        overlap = [len(set(a[q]) & set(e[q])) / 10 for q in e]
        same_first = [bool(a[q]) and a[q][0] == e[q][0] for q in e]
        agree_rows.append({"model": model, "preset": preset, "overlap": float(np.mean(overlap)), "same_top1": float(np.mean(same_first))})

    embed_rows = merge(0, embed_rows, ("model", "device"))
    build_rows = merge(1, build_rows, ("build",))
    agree_rows = merge(2, agree_rows, ("model", "preset"))
    doc = {
        "experiment": EXPERIMENT,
        "title": "re-embedding, rebuilding, and agreement with exact",
        "corpus_hash": env.corpus_hash(),
        "provenance": {
            "status": "measured",
            "source": "benchmark/tools/stability.py",
            "date": dt.date.today().isoformat(),
            "notes": f"corpus {env.corpus_hash()}; re-embed sample: the first {SAMPLE} documents",
        },
        "tables": [
            {"title": "re-embedding the same documents", "rows": embed_rows, "columns": [
                {"key": "model", "label": "model"}, {"key": "device", "label": "device"},
                {"key": "identical", "label": "bit-identical"}, {"key": "max_abs_diff", "label": "max abs diff", "fmt": "f9"}]},
            {"title": "rebuilding every file", "rows": build_rows, "columns": [
                {"key": "build", "label": "build"}, {"key": "file_hash", "label": "file_hash (prefix)"},
                {"key": "same", "label": "same file_hash"}]},
            {"title": "top-10 agreement with the exact preset of the same model", "rows": agree_rows, "columns": [
                {"key": "model", "label": "model"}, {"key": "preset", "label": "preset"},
                {"key": "overlap", "label": "top-10 overlap", "fmt": "f3"},
                {"key": "same_top1", "label": "same top-1", "fmt": "f3"}]},
        ],
    }
    env.write_json(env.EXPERIMENTS / EXPERIMENT / "results.json", doc)
    print(f"written: {env.rel(env.EXPERIMENTS / EXPERIMENT / 'results.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
