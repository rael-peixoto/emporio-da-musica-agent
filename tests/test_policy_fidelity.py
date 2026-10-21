"""The Markdown transcription used in the prompt must match the original policy PDF.

Both directions are checked, so a typo, an invented rule or a dropped passage fails the build.
"""

import re

import pytest
from pypdf import PdfReader

from emporio.config import DATA_DIR, KNOWLEDGE_DIR


@pytest.fixture(scope="module")
def pdf_text() -> str:
    reader = PdfReader(DATA_DIR / "políticas_da_loja.pdf")
    text = " ".join(page.extract_text() for page in reader.pages)
    text = re.sub(r"\s+", " ", text)
    return re.sub(r"Página \d+", " ", text)  # page footers are layout, not content


@pytest.fixture(scope="module")
def md_text() -> str:
    return (KNOWLEDGE_DIR / "politicas.md").read_text(encoding="utf-8")


def numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:[.,/]\d+)*", text))


def words(text: str) -> set[str]:
    return set(re.findall(r"[^\W\d_]+", text.lower()))


def test_same_numbers(pdf_text, md_text):
    assert numbers(md_text) == numbers(pdf_text)


def test_same_vocabulary(pdf_text, md_text):
    assert words(md_text) == words(pdf_text)


@pytest.mark.parametrize(
    "fact",
    [
        "contato@emporiodamusica.com.br",  # cover
        "contato@empóriodamusica.com.br",  # §1.2 (accented spelling, kept verbatim)
        "(67) 3321-4500",  # §7 WhatsApp
    ],
)
def test_conflicting_contact_details_are_kept_verbatim(pdf_text, md_text, fact):
    assert fact in md_text
    assert fact.replace(" ", "") in pdf_text.replace(" ", "")
