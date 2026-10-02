# Methodology

How the benchmark measures, and what each number can and cannot say.

- Two measurements, kept apart. Stability: `file_hash` across rebuilds, and ranking agreement of the compressed and approximate profiles with `exact`. Retrieval quality: recall@k and nDCG@k against the judgments in `qrels`, for every profile, `exact` included.
- `exact` is the reference for ranking agreement, not for relevance. Relevance comes only from `qrels`.
- Rows with `label_conflict` stay searchable and are left out of label-based metrics.

## From chunk hits to a document ranking

Search returns chunks; `qrels` judges documents. The evaluation rebuilds a document ranking from each query's hits:

1. Map every hit to its `doc_id` through the release's chunk map. A `.urna` whose chunk ids do not match the map is refused.
2. Walk the hits in rank order. The first hit of a document gives it the next document rank; later hits of the same document are dropped. Hits `A, A, B` become `A, B` at ranks 1 and 2, and a document's score is the exact-rerank score of its best chunk.
3. Metrics at k are computed over the first k distinct documents. When the chunk hits yield fewer than k distinct documents, the query is run again with a larger chunk count (doubling, up to the corpus size), and the ranking comes from that final run, not from stitching runs together.
4. The result is written as a TREC run (`query_id Q0 doc_id rank score run_tag`) and scored against `qrels.tsv`, so any TREC scorer reproduces the numbers. The chunk count each query needed is recorded next to the run.

## Queries and relevance

The queries are headlines and fact-check titles that the sources keep outside the indexed text: 1,728 FakeTrue.Br headlines of fake texts and 873 FACTCK.BR titles. Relevance comes from the structure of the sources: grade 2 for the document the headline was written for, grade 1 for the true text paired with a fake one in FakeTrue.Br. `benchmark/queries/README.md` has the rules and the counts.

They are silver judgments. No person judged them, and they are incomplete: another source's article about the same claim is unjudged and counts as a miss. That makes recall a lower bound, the same for every model and preset, which is enough to compare them and not enough to state how good retrieval is in absolute terms. Human-judged qrels, pooled from the runs of every model, are the way to close that gap.

## Metrics

- Retrieval quality, per profile: nDCG@10 (graded), recall@10 and recall@100 (any grade above 0), and hit@1 for the grade-2 document.
- Stability, per profile against `exact` of the same model: top-10 overlap of the document rankings, and whether a rebuild gives the same `file_hash`.
