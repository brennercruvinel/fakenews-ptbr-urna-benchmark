# Queries

2,601 queries and 4,582 judgments, written by `benchmark/tools/make_queries.py` from two sources; `make_queries.py --check` proves the tracked files match what the pinned sources give.

`queries.jsonl` holds one query per line: `query_id`, `text`, `origin` (the source field and row it came from).

- `ftb-*` (1,728): the headline of a fake text in FakeTrue.Br (`title_fake`). The headline is not part of the indexed text.
- `fck-*` (873): the title of a FACTCK.BR fact check without the site suffix (" | Aos Fatos"). The indexed text is the claim and the review, not the title.

A query is dropped when it appears verbatim inside a document judged for it (14 were), or when a judged document left the corpus (261 FACTCK.BR checks without a true or false verdict). Identical texts are merged.

`qrels.tsv` is in TREC qrels format: four tab-separated columns, no header, one judgment per line.

```
query_id	0	doc_id	relevance
```

The second column is the TREC iteration field, always `0` and ignored by the scorers. `doc_id` is the corpus `doc_id` (`sha256:<hex>`), never a `chunk_id`. The file reads as-is in `trec_eval` and `ir_measures`.

Relevance:

| Grade | Meaning |
|---:|---|
| 2 | The document the headline or title was written for |
| 1 | The other half of a FakeTrue.Br pair: the true text about the same claim |
| unjudged | Not relevant, by the TREC convention |

These are silver judgments, derived from the structure of the sources and not judged by a person. They are incomplete: a document about the same claim from another source is unjudged and counts against recall. The numbers compare models and presets on the same ruler; they are not an absolute measure of retrieval quality.
