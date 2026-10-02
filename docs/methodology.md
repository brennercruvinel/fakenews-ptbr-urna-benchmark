# Methodology

To be written. The fixed points so far:

- Two measurements, kept apart. Stability: `file_hash` across rebuilds, and ranking agreement of the compressed and approximate profiles with `exact`. Retrieval quality: recall@k and nDCG@k against the judgments in `qrels`, for every profile, `exact` included.
- `exact` is the reference for ranking agreement, not for relevance. Relevance comes only from `qrels`.
- Scoring happens on `doc_id`. Search returns `chunk_id`s; the evaluation maps each hit to its `doc_id` through the release's chunk map, keeps the best rank per document, and refuses a `.urna` whose chunk ids do not match the map.
- Rows with `label_conflict` stay searchable and are left out of label-based metrics.

Still open: how the queries are chosen and how relevance is judged.
