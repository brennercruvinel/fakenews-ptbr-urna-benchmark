#!/usr/bin/env python3
"""Run the queries against one or more builds and score them against the qrels.

  python benchmark/tools/evaluate.py candidates/minilm-exact [candidates/minilm-tiny ...]

Each argument is a build directory (fakenews.urna, chunk_map.parquet, build.lock.json).
For each one:
  1. the chunk ids read from the file must equal the chunk map, in order
  2. every query is embedded with the build's model and searched the way urna
     0.5.3 and later route it: exact, hnsw (`search_ann`) or hybrid (`search_hybrid`
     with the query text), with ef max(100, k), which the file's floor of 400 (its
     ef_construction) widens to 400
  3. chunk hits become a document ranking: the first hit of a document takes the
     next rank, later hits of it are dropped; a query with fewer than DEPTH
     distinct documents is run again with twice the chunks, up to the corpus size
  4. the ranking is written as a TREC run, benchmark/runs/<build>.run, and scored:
     nDCG@10 (graded), recall@10 and recall@100 (grade > 0), hit@1 (grade 2)

Writes benchmark/runs/<build>.json with the scores, per query family too.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bench_env as env  # noqa: E402
import _embed  # noqa: E402

DEPTH = 100
BEAM = 100


def load_queries() -> tuple[list[dict], dict[str, dict[str, int]]]:
    queries = [json.loads(line) for line in (env.QUERIES / "queries.jsonl").read_text().splitlines()]
    qrels: dict[str, dict[str, int]] = defaultdict(dict)
    for line in (env.QUERIES / "qrels.tsv").read_text().splitlines():
        qid, _, did, rel = line.split("\t")
        qrels[qid][did] = int(rel)
    return queries, qrels


def searcher(f, mode: str):
    if mode == "exact":
        return lambda vec, text, k: f.search(vec, k)
    if mode == "ann":
        return lambda vec, text, k: f.search_ann(vec, k, max(BEAM, k))
    if mode == "hybrid":
        return lambda vec, text, k: f.search_hybrid(vec, text, k, max(BEAM, k))
    env.die(f"unknown search mode {mode!r}")


def doc_ranking(search, vec, text, chunk_to_doc, n_chunks) -> tuple[list[tuple[str, float]], int]:
    k = DEPTH
    while True:
        seen, ranking = set(), []
        for h in search(vec, text, k):
            d = chunk_to_doc[h.chunk_id]
            if d not in seen:
                seen.add(d)
                ranking.append((d, float(h.score)))
        if len(ranking) >= DEPTH or k >= n_chunks:
            return ranking[:DEPTH], k
        k = min(2 * k, n_chunks)


def ndcg(ranked: list[str], judged: dict[str, int], k: int) -> float:
    dcg = sum(judged.get(d, 0) / math.log2(i + 2) for i, d in enumerate(ranked[:k]))
    ideal = sorted(judged.values(), reverse=True)[:k]
    idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal))
    return dcg / idcg if idcg else 0.0


def recall(ranked: list[str], judged: dict[str, int], k: int) -> float:
    rel = {d for d, g in judged.items() if g > 0}
    return len(rel & set(ranked[:k])) / len(rel) if rel else 0.0


def score_query(ranked: list[str], judged: dict[str, int]) -> dict[str, float]:
    return {
        "ndcg@10": ndcg(ranked, judged, 10),
        "recall@10": recall(ranked, judged, 10),
        "recall@100": recall(ranked, judged, 100),
        "hit@1": float(bool(ranked) and judged.get(ranked[0], 0) == 2),
    }


def mean(rows: list[dict[str, float]]) -> dict[str, float]:
    return {k: round(sum(r[k] for r in rows) / len(rows), 4) for k in rows[0]} if rows else {}


def evaluate(build_dir: Path, queries: list[dict], qrels: dict, embedders: dict) -> dict:
    import urna

    lock = json.loads((build_dir / "build.lock.json").read_text())
    env.require_corpus(lock["corpus"]["corpus_hash"], env.rel(build_dir))
    preset = {p["name"]: p for p in env.load_toml(env.PRESETS_TOML)["preset"]}[lock["build"]["preset"]]
    cmap = pd.read_parquet(build_dir / "chunk_map.parquet")
    f = urna.open(str(build_dir / "fakenews.urna"))
    if list(f.chunk_ids()) != list(cmap["chunk_id"]):
        env.die(f"{env.rel(build_dir)}: chunk ids do not match chunk_map.parquet")
    chunk_to_doc = dict(zip(cmap["chunk_id"], cmap["doc_id"]))
    name = lock["model"]["name"]
    if name not in embedders:
        embedders[name] = _embed.load(name, lock["environment"]["device"])
    emb = embedders[name]
    if emb.model_hash != lock["model"]["model_hash"]:
        env.die(f"{env.rel(build_dir)}: the local {name} snapshot does not match the build's model_hash")
    vecs = emb.embed([q["text"] for q in queries])
    search = searcher(f, preset["search"])
    run_name = build_dir.name
    lines, per_query, depth_used = [], {}, {}
    t0 = time.perf_counter()
    for q, v in zip(queries, vecs):
        ranking, k_used = doc_ranking(search, v.tolist(), q["text"], chunk_to_doc, len(cmap))
        depth_used[q["query_id"]] = k_used
        lines += [f"{q['query_id']} Q0 {d} {i + 1} {s:.6f} {run_name}" for i, (d, s) in enumerate(ranking)]
        per_query[q["query_id"]] = score_query([d for d, _ in ranking], qrels.get(q["query_id"], {}))
    secs = time.perf_counter() - t0
    env.RUNS.mkdir(parents=True, exist_ok=True)
    (env.RUNS / f"{run_name}.run").write_text("\n".join(lines) + "\n")
    families = defaultdict(list)
    for qid, s in per_query.items():
        families[qid.split("-")[0]].append(s)
    result = {
        "build": run_name,
        "model": name,
        "preset": lock["build"]["preset"],
        "search": preset["search"],
        "file_hash": lock["output"]["file_hash"],
        "corpus_hash": lock["corpus"]["corpus_hash"],
        "bytes": lock["output"]["bytes"],
        "n_queries": len(per_query),
        "all": mean(list(per_query.values())),
        "by_family": {fam: {"n": len(rows), **mean(rows)} for fam, rows in sorted(families.items())},
        "chunks_requested_max": max(depth_used.values()),
        "search_ms_per_query": round(1000 * secs / len(queries), 2),
    }
    env.write_json(env.RUNS / f"{run_name}.json", result)
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("builds", nargs="+", help="build directories (candidates/<model>-<preset> or a release dir)")
    args = ap.parse_args()
    queries, qrels = load_queries()
    embedders: dict = {}
    for b in args.builds:
        r = evaluate(Path(b), queries, qrels, embedders)
        print(f"{r['build']}: {json.dumps(r['all'])} ({r['search_ms_per_query']} ms/query)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
