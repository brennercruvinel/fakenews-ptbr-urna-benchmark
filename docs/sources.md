# Sources

The license bill of materials and the label rules, one section per upstream, at the revisions pinned in `sources/sources.toml`.

The MIT license of this repo does not apply to any text listed here. A text found in several sources keeps every origin, with its license, in `origins`.

## Redistribution status

Three sources declare a license (Apache-2.0 for the vzani copies, MIT for FACTCK.BR). Three declare none: Fake.br-Corpus, FakeRecogna and FakeTrue.Br are academic releases that ask for a citation and grant nothing in writing. Without a grant, redistributing their texts is not covered by any license, and the vzani copies inherit that gap: they are Apache-2.0 as published, but their texts come from Fake.br and FakeTrue.Br.

What this means in practice:

- [x] Every source is pinned to a revision and a tree hash.
- [x] Every license field states what the upstream declares, or `none-declared`.
- [ ] Written permission from the authors of Fake.br-Corpus, FakeRecogna and FakeTrue.Br, or a decision to publish without their texts.

The Hugging Face dataset stays private until the last item is closed.

## FakeBr-hf

- Upstream: [vzani/corpus-fake-br](https://huggingface.co/datasets/vzani/corpus-fake-br), files `corpus_train_df.parquet` and `corpus_test_df.parquet`.
- License: Apache-2.0, as declared on the dataset card. The texts are Fake.br's.
- Labels: `label` is veracity, True for true news and False for fake. Checked against Fake.br-Corpus: all 7,200 texts match its `full_texts/true` and `full_texts/fake` folders the same way.
- Splits: train and test, kept.

## FakeTrue.Br-hf

- Upstream: [vzani/corpus-faketrue-br](https://huggingface.co/datasets/vzani/corpus-faketrue-br), the same two parquet files.
- License: Apache-2.0, as declared. The texts are FakeTrue.Br's.
- Labels: as FakeBr-hf. Its 3,182 unique texts all match FakeTrue.Br's `true` and `fake` columns with the same labels.
- Splits: train and test, kept.

## Fake.br-Corpus

- Upstream: [roneysco/Fake.br-Corpus](https://github.com/roneysco/Fake.br-Corpus), `full_texts/`.
- License: none declared. The README asks to cite the PROPOR 2018 paper (Monteiro et al.) and the Expert Systems with Applications 2020 paper (Silva et al.).
- Labels: the folder, `true` or `fake`.
- Text: the original articles in `full_texts/`. Urna's corpus_next.v1 read `preprocessed/pre-processed.csv`, which the README describes as the text with stopwords, accents and diacritics removed.

## FakeRecogna

- Upstream: [Gabriel-Lino-Garcia/FakeRecogna](https://github.com/Gabriel-Lino-Garcia/FakeRecogna), `dataset/FakeRecogna.xlsx`.
- License: none declared.
- Labels: `Classe` 1 is true, 0 is fake. All 2,479 titles tagged `#boato` and every boatos.org url are class 0.
- Text: title, subtitle and body joined. The body (`Noticia`) is lemmatized and stopword-stripped upstream, in both spreadsheets; title and subtitle are natural text.

## FakeTrue.Br

- Upstream: [jpchav98/FakeTrue.Br](https://github.com/jpchav98/FakeTrue.Br), `FakeTrueBr_corpus.csv`.
- License: none declared.
- Labels: each row is a pair, the `fake` text and the `true` text that corrects it. The text is lowercase upstream.

## factck-br

- Upstream: [jghm-f/FACTCK.BR](https://github.com/jghm-f/FACTCK.BR), `FACTCKBR.tsv`. Urna's `data/demo/Instructions.md` points at `opit-research/factck-br`, which no longer exists.
- License: MIT. Cite Moreno and Bressan, WebMedia 2019.
- Claims checked by Agência Lupa, Aos Fatos and Truco.
- Labels: the text rating (`alternativeName`). "Falso" is fake, "Verdadeiro" is true, every other rating (distorcido, exagerado, sem contexto, impreciso and the rest) is dropped. The numeric `ratingValue` is not used: its scale differs per agency, and 469 claims rated "Falso" carry a 4.
- Text: the claim and the review body joined.

## bilstm-combined

- Upstream: [vzani/portuguese-fake-news-classifier-bilstm-combined](https://huggingface.co/vzani/portuguese-fake-news-classifier-bilstm-combined), `corpus/corpus_test_df.parquet`.
- License: Apache-2.0, as declared. The texts are Fake.br's and FakeTrue.Br's.
- Labels: as FakeBr-hf.
- Splits: test only. Its test split does not match the vzani dataset splits, which is where every split conflict comes from.
