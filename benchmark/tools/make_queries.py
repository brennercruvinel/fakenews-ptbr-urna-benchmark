#!/usr/bin/env python3
"""Derive the queries and their judgments from the structure of two sources.

  FakeTrue.Br  each row pairs a fake text with the true text that corrects it,
               plus the headline of the fake (`title_fake`), which is not part of
               either text. query = the headline; relevance 2 = the fake text it
               headed, relevance 1 = the paired true text about the same claim.
  FACTCK.BR    each fact check has a title that is not part of the indexed text
               (claim + review). query = the title without the site suffix
               (" | Aos Fatos"); relevance 2 = that check.

A query is dropped when it is shorter than 10 characters, when one of its judged
documents is not in the corpus, or when its text appears verbatim (case-folded)
inside a judged document: such a query would test string matching, not retrieval.
Identical query texts are merged, keeping the highest relevance per document.

These are silver judgments: built from the sources, not by a human judge, and
incomplete. A document about the same claim from another source is unjudged and
counts as not relevant.

Writes benchmark/queries/queries.jsonl and qrels.tsv (TREC, `query_id 0 doc_id rel`).
--check exits 1 when the tracked files differ from what the sources give.

usage (repo root): python benchmark/tools/make_queries.py [--check]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bench_env as env  # noqa: E402
import _sources  # noqa: E402
from prepare import doc_id  # noqa: E402

MIN_QUERY_LEN = 10
# the page-title suffix the agencies append ("... | Aos Fatos"), not part of the headline
SITE_SUFFIX = re.compile(r"\s+\|\s+[^|]{2,40}$")


def candidates(root: Path):
    ftb = pd.read_csv(root / "FakeTrue.Br" / "FakeTrueBr_corpus.csv")
    for i, r in enumerate(ftb.to_dict("records")):
        q = _sources.norm(r.get("title_fake"))
        judged = {doc_id(_sources.norm(r.get("fake"))): 2, doc_id(_sources.norm(r.get("true"))): 1}
        yield f"ftb-{i:05d}", q, f"FakeTrue.Br:title_fake#{i}", judged
    fck = pd.read_csv(root / "factck-br" / "FACTCKBR.tsv", sep="\t")
    for i, r in enumerate(fck.to_dict("records")):
        q = SITE_SUFFIX.sub("", _sources.norm(r.get("title")))
        body = " ".join(filter(None, (_sources.norm(r.get("claimReviewed")), _sources.norm(r.get("reviewBody")))))
        yield f"fck-{i:05d}", q, f"factck-br:title#{i}", {doc_id(body): 2}


def build(root: Path, texts: dict[str, str]) -> tuple[list[dict], list[tuple[str, str, int]], dict]:
    by_text: dict[str, dict] = {}
    dropped = {"short": 0, "judged_doc_missing": 0, "verbatim_in_doc": 0}
    for qid, q, origin, judged in candidates(root):
        if len(q) < MIN_QUERY_LEN:
            dropped["short"] += 1
            continue
        if any(d not in texts for d in judged):
            dropped["judged_doc_missing"] += 1
            continue
        if any(q.casefold() in texts[d].casefold() for d in judged):
            dropped["verbatim_in_doc"] += 1
            continue
        entry = by_text.setdefault(q, {"query_id": qid, "text": q, "origin": origin, "judged": {}})
        for d, rel in judged.items():
            entry["judged"][d] = max(rel, entry["judged"].get(d, 0))
    queries, qrels = [], []
    for e in by_text.values():
        queries.append({"query_id": e["query_id"], "text": e["text"], "origin": e["origin"]})
        for d, rel in sorted(e["judged"].items()):
            qrels.append((e["query_id"], d, rel))
    return queries, qrels, dropped


def render(queries: list[dict], qrels: list[tuple[str, str, int]]) -> tuple[str, str]:
    q = "".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in queries)
    r = "".join(f"{qid}\t0\t{d}\t{rel}\n" for qid, d, rel in qrels)
    return q, r


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    corpus = pd.read_parquet(env.prepared_dir() / "corpus.parquet", columns=["doc_id", "text"])
    texts = dict(zip(corpus["doc_id"], corpus["text"]))
    queries, qrels, dropped = build(env.data_root(), texts)
    q_text, r_text = render(queries, qrels)
    paths = {env.QUERIES / "queries.jsonl": q_text, env.QUERIES / "qrels.tsv": r_text}
    if args.check:
        stale = [p for p, t in paths.items() if not p.is_file() or p.read_text() != t]
        for p in stale:
            print(f"stale: {env.rel(p)}")
        return 1 if stale else 0
    for p, t in paths.items():
        p.write_text(t)
    n_by = {}
    for x in queries:
        n_by[x["query_id"][:3]] = n_by.get(x["query_id"][:3], 0) + 1
    print(f"{len(queries)} queries {n_by}, {len(qrels)} judgments, dropped {dropped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
