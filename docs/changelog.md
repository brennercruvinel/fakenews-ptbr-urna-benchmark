# Changelog

## Unreleased

- Link the header image of the README and of the dataset card to the Urna documentation, https://docs.urna.dev/, as in Urna's own README and in mtg-urna-benchmark.
- Give the README and the dataset card the structure of mtg-urna-benchmark, the sister benchmark, with the same opening link block: the dataset on Hugging Face (or the code on GitHub, on the card), Urna, the source and the sister benchmark. The README sections are Pick a build, Results, Build one, Check a release from the hub (new: `hf download`, `shasum -c`, `promote.py --check`), Query one, Check everything from scratch (`check_clean.sh`, out of Build one), Documents and chunks, then Layout, Reading (new) and License. The checklist's open item, the license evidence of three sources, moves into License. On the card, the query steps get their own Query it section, and Build and Citation are new; Citation follows `CITATION.cff`, which cites Urna as the one reference.
- Correct the query install for the minilm and mpnet files: they need Urna built from `main` (the route of hoffresearch/urna #264 is not in 0.5.1, the latest release), and the card's `hf download` fetched the whole model repo, whose `pytorch_model.bin` enters the fingerprint and changes the `model_hash`. The card now downloads only the files in `model.snapshot_files` at `model.revision`; checked: both fingerprints equal the locks' `model_hash`, and `retrieve --model-path` answers offline with urna `main` at `7ef2b725`, while the 0.5.1 binary cannot serve them.
- Scaffold: layout, sources list and README for review.
- Separate `doc_id` (dedup and `qrels`) from the `chunk_id` Urna cites, with a chunk map per release.
- Call `exact` the reference for ranking agreement; relevance comes from `qrels`.
- Record `label_conflict` and `split_conflict` in the schema, with every occurrence kept in `origins`.
- Mark the build commands as a planned workflow and name what `urna build` without a checkout depends on.
- State that MIT covers code and results, not the corpus text.
- Write `qrels.tsv` in TREC format (`query_id 0 doc_id relevance`).
- Define the document ranking rebuilt from chunk hits: first hit per document, metrics over the first k distinct documents, re-query with more chunks when short.
