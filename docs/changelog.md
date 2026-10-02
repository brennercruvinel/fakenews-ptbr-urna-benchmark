# Changelog

## Unreleased

- Scaffold: layout, sources list and README for review.
- Separate `doc_id` (dedup and `qrels`) from the `chunk_id` Urna cites, with a chunk map per release.
- Call `exact` the reference for ranking agreement; relevance comes from `qrels`.
- Record `label_conflict` and `split_conflict` in the schema, with every occurrence kept in `origins`.
- Mark the build commands as a planned workflow and name what `urna build` without a checkout depends on.
- State that MIT covers code and results, not the corpus text.
- Write `qrels.tsv` in TREC format (`query_id 0 doc_id relevance`).
- Define the document ranking rebuilt from chunk hits: first hit per document, metrics over the first k distinct documents, re-query with more chunks when short.
