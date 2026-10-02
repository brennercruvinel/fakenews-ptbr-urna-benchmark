"""One loader per upstream dataset, each yielding occurrences in a fixed order.

An occurrence is one text as one source has it:
  text          whitespace-normalized, NFC, BOM removed
  title, url    where the source has them, else ""
  label_raw     the source's own label, as a string
  label         "true", "fake", or None when the source label is not a verdict
  source_split  "train", "test" or "none"
  source_row    where the text sits in the source (file, split and row)

Label rules, checked against the data (docs/sources.md has the evidence):
  vzani parquet   label is veracity: True = true news, False = fake
  Fake.br         full_texts/true and full_texts/fake
  FakeRecogna     Classe 1 = true, 0 = fake
  FakeTrue.Br     column `true` and column `fake` of each pair
  FACTCK.BR       the text label (alternativeName): falso -> fake, verdadeiro -> true,
                  every other rating (distorcido, exagerado, sem contexto, ...) -> None.
                  ratingValue is not used: its scale differs per agency, and rating 4
                  is "Falso" on 469 rows.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterator
from pathlib import Path

import pandas as pd

MIN_TEXT_LEN = 20


def norm(s) -> str:
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFC", s.replace("﻿", ""))
    return re.sub(r"\s+", " ", s).strip()


def occ(text, label_raw, label, split, row, title="", url="") -> dict:
    return {
        "text": norm(text),
        "title": norm(title),
        "url": norm(url),
        "label_raw": str(label_raw),
        "label": label,
        "source_split": split,
        "source_row": row,
    }


def _vzani(root: Path, files: list[tuple[str, str]]) -> Iterator[dict]:
    for split, rel in files:
        df = pd.read_parquet(root / rel)
        for i, r in enumerate(df.itertuples(index=False)):
            lab = bool(r.label)
            yield occ(r.text, lab, "true" if lab else "fake", split, f"{rel}#{i}")


def load_fakebr_hf(root: Path) -> Iterator[dict]:
    yield from _vzani(root, [("train", "corpus_train_df.parquet"), ("test", "corpus_test_df.parquet")])


def load_faketrue_br_hf(root: Path) -> Iterator[dict]:
    yield from _vzani(root, [("train", "corpus_train_df.parquet"), ("test", "corpus_test_df.parquet")])


def load_bilstm(root: Path) -> Iterator[dict]:
    yield from _vzani(root, [("test", "corpus/corpus_test_df.parquet")])


def load_fake_br_corpus(root: Path) -> Iterator[dict]:
    base = root / "full_texts"
    for label in ("fake", "true"):
        files = sorted((base / label).glob("*.txt"), key=lambda p: int(p.stem))
        for p in files:
            meta = base / f"{label}-meta-information" / f"{p.stem}-meta.txt"
            lines = meta.read_text(encoding="utf-8").splitlines() if meta.is_file() else []
            url = lines[1] if len(lines) > 1 else ""
            yield occ(p.read_text(encoding="utf-8"), label, label, "none", f"full_texts/{label}/{p.name}", url=url)


def load_fake_recogna(root: Path) -> Iterator[dict]:
    rel = "dataset/FakeRecogna.xlsx"
    df = pd.read_excel(root / rel)
    for i, r in enumerate(df.to_dict("records")):
        body = " ".join(filter(None, (norm(r.get("Titulo")), norm(r.get("Subtitulo")), norm(r.get("Noticia")))))
        cls = r.get("Classe")
        label = {0: "fake", 1: "true"}.get(int(cls)) if pd.notna(cls) else None
        yield occ(body, cls, label, "none", f"{rel}#{i}", title=r.get("Titulo"), url=r.get("URL"))


def load_faketrue_br(root: Path) -> Iterator[dict]:
    rel = "FakeTrueBr_corpus.csv"
    df = pd.read_csv(root / rel)
    for i, r in enumerate(df.to_dict("records")):
        yield occ(r.get("fake"), "fake", "fake", "none", f"{rel}#{i}:fake", title=r.get("title_fake"), url=r.get("link_f"))
        yield occ(r.get("true"), "true", "true", "none", f"{rel}#{i}:true", url=r.get("link_t"))


FACTCK_LABELS = {"falso": "fake", "verdadeiro": "true"}


def load_factck_br(root: Path) -> Iterator[dict]:
    rel = "FACTCKBR.tsv"
    df = pd.read_csv(root / rel, sep="\t")
    for i, r in enumerate(df.to_dict("records")):
        raw = norm(r.get("alternativeName"))
        body = " ".join(filter(None, (norm(r.get("claimReviewed")), norm(r.get("reviewBody")))))
        yield occ(body, raw, FACTCK_LABELS.get(raw.lower()), "none", f"{rel}#{i}", title=r.get("title"), url=r.get("URL"))


LOADERS = {
    "FakeBr-hf": load_fakebr_hf,
    "FakeTrue.Br-hf": load_faketrue_br_hf,
    "Fake.br-Corpus": load_fake_br_corpus,
    "FakeRecogna": load_fake_recogna,
    "FakeTrue.Br": load_faketrue_br,
    "factck-br": load_factck_br,
    "bilstm-combined": load_bilstm,
}
