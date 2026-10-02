# 03 stability

hypothesis: on one machine, the same sources, model snapshot and preset give a byte-identical file, and the int8 hnsw preset keeps the exact preset's top-10.
method: re-embed the first 1,000 documents with each model and compare the vectors bit for bit; rebuild every file with build.py into a scratch dir and compare file_hash; per model, the share of each preset's top-10 documents that is in the exact preset's top-10, over all queries.
verdict: see the tables. Agreement with exact measures how much compression moves the ranking; it says nothing about relevance, which is experiment 02.

The tables are in `table.md`.
