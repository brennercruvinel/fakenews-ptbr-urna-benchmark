# 01 corpus

hypothesis: the seven sources overlap heavily, and a corpus that dedups by the hash of the normalized text holds far fewer documents than the 30,725 chunks of Urna's corpus_next.v1.
method: fetch every source at its pinned revision, normalize (NFC, whitespace, BOM), drop texts of 20 characters or less and labels that are not a verdict, dedup by sha256 of the text, keep every occurrence in `origins`; count per source, per pair of sources and per conflict.
verdict: 23,335 documents. Fake.br enters once instead of twice (corpus_next.v1 read its stopword-stripped `pre-processed.csv` beside the vzani copy, so the same 7,200 articles were in it twice under two texts). No label conflicts across the 10,381 texts found in more than one source, which confirms the label conventions. 1,746 split conflicts, all from the bilstm test split overlapping the vzani train splits; they go to test. The FACTCK.BR numeric scale would have labeled 469 "Falso" claims as true.

The tables are in `table.md`; the numbers come from `benchmark/tools/prepare.py` and `overlap_report.py`.
