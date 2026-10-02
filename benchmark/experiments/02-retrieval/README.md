# 02 retrieval

hypothesis: a multilingual sentence-transformers model finds the judged documents far more often than potion, an English static table, and the compressed presets of a model lose little against its exact preset.
method: the 2,601 queries of benchmark/queries, embedded by each build's own model, searched the way the urna cli routes them (exact, hnsw, or hybrid with the query text, beam max(100, k)); chunk hits become a document ranking (first hit per document), scored as a TREC run against the silver qrels; ir_measures reproduces the numbers.
verdict: mpnet leads (nDCG@10 0.528), minilm is close behind at half the dimension and less than half the embed time (0.503), potion trails far behind (0.326). tiny keeps every multilingual number within 0.001 of exact at about a quarter of the bytes; on potion it loses 0.013 nDCG@10 and 0.035 recall@100. hybrid lands within 0.001 of exact for the multilingual models and 0.004 above it on potion's recall@100: urna ranks a candidate pool (hnsw plus bm25) by exact cosine, so the top of the list is the brute-force top and bm25 only swaps a few documents into the tail.

The tables are in `table.md`. The qrels are silver and incomplete, so the absolute numbers are lower bounds; the comparison between rows is what they support.
