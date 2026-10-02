# 03 stability

hypothesis: on one machine, the same sources, model snapshot and preset give a byte-identical file, and the int8 hnsw preset keeps the exact preset's top-10.
method: re-embed the first 1,000 documents with each model and compare the vectors bit for bit; rebuild every file with build.py into a scratch dir and compare file_hash; per model, the share of each preset's top-10 documents that is in the exact preset's top-10, over all queries.
verdict: everything comes back the same on one machine: re-embedding gives bit-identical vectors for all three models on cpu, and all nine rebuilds give the same file_hash. tiny keeps over 99% of exact's top-10 for minilm and mpnet and 93% for potion, whose int8 rows lose more of a weaker signal. hybrid keeps over 99.9% of the top-10 for the multilingual models and 97.6% for potion. Agreement with exact measures how much compression moves the ranking; it says nothing about relevance, which is experiment 02. Builds on another machine or device are not covered: the lock records platform and device for that comparison.

The tables are in `table.md`.
