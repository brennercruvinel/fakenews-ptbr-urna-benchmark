# Queries

`queries.jsonl` holds one real claim per line (`query_id`, `text`, `origin`). A query never comes from the text of a corpus row; the self-perturbed vectors Urna's gate uses today measure stability and live in the stability experiment, not here.

`qrels.tsv` is in TREC qrels format: four tab-separated columns, no header, one judgment per line.

```
query_id	0	doc_id	relevance
```

The second column is the TREC iteration field, always `0` and ignored by the scorers. `doc_id` is the corpus `doc_id` (`sha256:<hex>`), never a `chunk_id`. `relevance` is an integer; the scale is defined in `docs/methodology.md`. The file reads as-is in `trec_eval` and `ir_measures`.
