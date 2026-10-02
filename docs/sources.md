# Sources

The license bill of materials and the label rules, one section per upstream, at the revisions pinned in `sources/sources.toml`.

The MIT license of this repo does not apply to any text listed here. A text found in several sources keeps every origin, with its license, in `origins`.

## License status

Every source has a license, MIT or Apache-2.0. Four declare it upstream; for three, it rests on the maintainer's verification, whose evidence is still to be recorded, so redistribution of their texts is not established yet:

| Source | License | Basis |
|---|---|---|
| FakeBr-hf, FakeTrue.Br-hf, bilstm-combined | Apache-2.0 | declared on the hub card |
| factck-br | MIT | declared in the repo's `LICENSE` |
| Fake.br-Corpus, FakeRecogna, FakeTrue.Br | MIT | verified by the maintainer, Brenner Cruvinel, on 2026-10-02; evidence pending |

The last three repos carry no license file at their pinned revisions, so the GitHub page shows none, and a public repository without a license file grants no license by itself ([GitHub docs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)). `license_basis = "maintainer-verified"` in `sources/sources.toml` marks that the terms come from the maintainer's verification, not from a file in the upstream, and `license_evidence` has to say where that verification can be checked:

- a link to the author's grant (an issue, a release note, a page by the authors), or
- an archived copy of the authors' written permission, committed under `docs/license-evidence/<source>.md` with its date and sender.

The repository and the dataset were made public on 2026-10-02, by the maintainer's decision, with these three pieces of evidence still to be recorded; the dataset's `CHECKSUMS.json` lists the gap (`license_evidence_missing`). `export_parquet.py` keeps refusing a regular export until the evidence is in, so the next export without `--private` is the one that closes it.

Cite each source when you use its rows; the papers are listed below where the upstream names one.

- [x] Every source is pinned to a revision and a tree hash.
- [x] Every source has a license and the basis for it.
- [ ] Every maintainer-verified license has a `license_evidence`.

## FakeBr-hf

- Upstream: [vzani/corpus-fake-br](https://huggingface.co/datasets/vzani/corpus-fake-br), files `corpus_train_df.parquet` and `corpus_test_df.parquet`.
- License: Apache-2.0, as declared on the dataset card. The texts are Fake.br's (MIT).
- Labels: `label` is veracity, True for true news and False for fake. Checked against Fake.br-Corpus: all 7,200 texts match its `full_texts/true` and `full_texts/fake` folders the same way.
- Splits: train and test, kept.

## FakeTrue.Br-hf

- Upstream: [vzani/corpus-faketrue-br](https://huggingface.co/datasets/vzani/corpus-faketrue-br), the same two parquet files.
- License: Apache-2.0, as declared. The texts are FakeTrue.Br's (MIT).
- Labels: as FakeBr-hf. Its 3,182 unique texts all match FakeTrue.Br's `true` and `fake` columns with the same labels.
- Splits: train and test, kept.

## Fake.br-Corpus

- Upstream: [roneysco/Fake.br-Corpus](https://github.com/roneysco/Fake.br-Corpus), `full_texts/`.
- License: MIT, verified by the maintainer (no license file upstream); evidence pending. The README asks to cite the PROPOR 2018 paper (Monteiro et al.) and the Expert Systems with Applications 2020 paper (Silva et al.).
- Labels: the folder, `true` or `fake`.
- Text: the original articles in `full_texts/`. Urna's corpus_next.v1 read `preprocessed/pre-processed.csv`, which the README describes as the text with stopwords, accents and diacritics removed.

## FakeRecogna

- Upstream: [Gabriel-Lino-Garcia/FakeRecogna](https://github.com/Gabriel-Lino-Garcia/FakeRecogna), `dataset/FakeRecogna.xlsx`.
- License: MIT, verified by the maintainer (no license file upstream); evidence pending.
- Labels: `Classe` 1 is true, 0 is fake. All 2,479 titles tagged `#boato` and every boatos.org url are class 0.
- Text: title, subtitle and body joined. The body (`Noticia`) is lemmatized and stopword-stripped upstream, in both spreadsheets; title and subtitle are natural text.

## FakeTrue.Br

- Upstream: [jpchav98/FakeTrue.Br](https://github.com/jpchav98/FakeTrue.Br), `FakeTrueBr_corpus.csv`.
- License: MIT, verified by the maintainer (no license file upstream); evidence pending.
- Labels: each row is a pair, the `fake` text and the `true` text that corrects it. The text is lowercase upstream.

## factck-br

- Upstream: [jghm-f/FACTCK.BR](https://github.com/jghm-f/FACTCK.BR), `FACTCKBR.tsv`. Urna's `data/demo/Instructions.md` points at `opit-research/factck-br`, which no longer exists.
- License: MIT. Cite Moreno and Bressan, WebMedia 2019.
- Claims checked by Agência Lupa, Aos Fatos and Truco.
- Labels: the text rating (`alternativeName`). "Falso" is fake, "Verdadeiro" is true, every other rating (distorcido, exagerado, sem contexto, impreciso and the rest) is dropped. The numeric `ratingValue` is not used: its scale differs per agency, and 469 claims rated "Falso" carry a 4.
- Text: the claim and the review body joined.

## bilstm-combined

- Upstream: [vzani/portuguese-fake-news-classifier-bilstm-combined](https://huggingface.co/vzani/portuguese-fake-news-classifier-bilstm-combined), `corpus/corpus_test_df.parquet`.
- License: Apache-2.0, as declared. The texts are Fake.br's and FakeTrue.Br's (MIT).
- Labels: as FakeBr-hf.
- Splits: test only. Its test split does not match the vzani dataset splits, which is where every split conflict comes from.
