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

usage (repo root): python benchmark/tools/stability.py candidates/*
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
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


def reembed(model: str, device: str, corpus_hash: str, texts: list[str]) -> dict:
    emb = _embed.load(model, device)
    m = emb.entry
    cache = env.data_root() / "embed" / f"{m['name']}-{m['revision'][:12]}-{device}-{corpus_hash[7:19]}.npy"
    ref = np.load(cache, mmap_mode="r")[: len(texts)]
    again = emb.embed(texts)
    return {"identical": bool(np.array_equal(ref, again)), "max_abs_diff": float(np.max(np.abs(ref - again)))}


def rebuild(build_dir: Path, lock: dict, scratch: Path) -> bool:
    out = scratch / build_dir.name
    cmd = [sys.executable, str(Path(__file__).with_name("build.py")), "--model", lock["model"]["name"],
           "--preset", lock["build"]["preset"], "--device", lock["environment"]["device"], "--out", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)
    again = json.loads((out / "build.lock.json").read_text())["output"]["file_hash"]
    return again == lock["output"]["file_hash"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("builds", nargs="+")
    args = ap.parse_args()
    prep = json.loads((env.prepared_dir() / "prepare.json").read_text())
    texts = list(pd.read_parquet(env.prepared_dir() / "corpus.parquet", columns=["text"])["text"][:SAMPLE])
    builds = [Path(b) for b in args.builds]
    locks = {b: json.loads((b / "build.lock.json").read_text()) for b in builds}

    embed_rows, seen = [], set()
    for b, lock in locks.items():
        key = (lock["model"]["name"], lock["environment"]["device"])
        if key in seen:
            continue
        seen.add(key)
        r = reembed(*key, prep["corpus_hash"], texts)
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
        a, e = top10(run), top10(ref)
        overlap = [len(set(a[q]) & set(e[q])) / 10 for q in e]
        same_first = [bool(a[q]) and a[q][0] == e[q][0] for q in e]
        agree_rows.append({"model": model, "preset": preset, "overlap": float(np.mean(overlap)), "same_top1": float(np.mean(same_first))})

    doc = {
        "experiment": EXPERIMENT,
        "title": "re-embedding, rebuilding, and agreement with exact",
        "provenance": {
            "status": "measured",
            "source": "benchmark/tools/stability.py",
            "date": dt.date.today().isoformat(),
            "notes": f"re-embed sample: the first {SAMPLE} documents of the corpus",
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
