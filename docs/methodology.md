# Methodology

To be written. The fixed points so far:

- Two measurements, kept apart. Stability: `file_hash` across rebuilds, and ranking agreement of the compressed and approximate profiles with `exact`. Retrieval quality: recall@k and nDCG@k against the judgments in `qrels`, for every profile, `exact` included.
- `exact` is the reference for ranking agreement, not for relevance. Relevance comes only from `qrels`.
- Rows with `label_conflict` stay searchable and are left out of label-based metrics.

## From chunk hits to a document ranking

Search returns chunks; `qrels` judges documents. The evaluation rebuilds a document ranking from each query's hits:

1. Map every hit to its `doc_id` through the release's chunk map. A `.urna` whose chunk ids do not match the map is refused.
2. Walk the hits in rank order. The first hit of a document gives it the next document rank; later hits of the same document are dropped. Hits `A, A, B` become `A, B` at ranks 1 and 2, and a document's score is the exact-rerank score of its best chunk.
3. Metrics at k are computed over the first k distinct documents. When the chunk hits yield fewer than k distinct documents, the query is run again with a larger chunk count (doubling, up to the corpus size), and the ranking comes from that final run, not from stitching runs together.
4. The result is written as a TREC run (`query_id Q0 doc_id rank score run_tag`) and scored against `qrels.tsv`, so any TREC scorer reproduces the numbers. The chunk count each query needed is recorded next to the run.

Still open: how the queries are chosen, how relevance is judged, and the relevance scale.
