# Changelog

## Unreleased

- Correct the query install for the minilm and mpnet files: they need Urna built from `main` (the route of hoffresearch/urna #264 is not in 0.5.1, the latest release), and the card's `hf download` fetched the whole model repo, whose `pytorch_model.bin` enters the fingerprint and changes the `model_hash`. The card now downloads only the files in `model.snapshot_files` at `model.revision`; checked: both fingerprints equal the locks' `model_hash`, and `retrieve --model-path` answers offline with urna `main` at `7ef2b725`, while the 0.5.1 binary cannot serve them.
- Scaffold: layout, sources list and README for review.
- Separate `doc_id` (dedup and `qrels`) from the `chunk_id` Urna cites, with a chunk map per release.
- Call `exact` the reference for ranking agreement; relevance comes from `qrels`.
- Record `label_conflict` and `split_conflict` in the schema, with every occurrence kept in `origins`.
- Mark the build commands as a planned workflow and name what `urna build` without a checkout depends on.
- State that MIT covers code and results, not the corpus text.
- Write `qrels.tsv` in TREC format (`query_id 0 doc_id relevance`).
- Define the document ranking rebuilt from chunk hits: first hit per document, metrics over the first k distinct documents, re-query with more chunks when short.
