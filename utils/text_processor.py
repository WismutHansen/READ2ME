import re
import unicodedata
from typing import List, Dict

import nltk

# ---------------------------------------------------------------------------
# Ensure required NLTK resources are present
# ---------------------------------------------------------------------------


def _ensure_nltk_resources() -> None:
    """Download missing NLTK corpora on‑the‑fly.

    Newer NLTK (≥3.9) splits Punkt into an extra *punkt_tab* asset.  We try to
    fetch both traditional and modern names so the code works across versions.
    """
    for res in ("punkt_tab", "punkt", "averaged_perceptron_tagger", "wordnet"):
        try:
            nltk.data.find(res)
        except LookupError:
            # *punkt_tab* is optional on older releases – ignore failures there
            try:
                nltk.download(res, quiet=True)
            except Exception:
                pass  # pragma: no cover


_ensure_nltk_resources()

# ---------------------------------------------------------------------------


class AdvancedTextPreprocessor:
    """Sentence bundling + very light‑weight NER."""

    def __init__(
        self,
        min_chars: int = 50,
        language: str = "english",
        keep_acronyms: bool = True,
    ) -> None:
        self.min_chars = min_chars
        self.language = language
        self.keep_acronyms = keep_acronyms

        # Acronyms / abbreviations worth preserving to avoid false splits
        self.abbreviations: set[str] = {
            "U.S.",
            "U.K.",
            "e.g.",
            "i.e.",
            "etc.",
            "Dr.",
            "Mr.",
            "Mrs.",
            "Ms.",
            "Prof.",
            "Sr.",
            "Jr.",
            "Inc.",
            "Ltd.",
            "Corp.",
            "Co.",
            "St.",
            "Mt.",
            "Ph.D.",
            "M.D.",
            "R.N.",
            "CEO",
            "CFO",
            "CTO",
        }

    # ---------------------------------------------------------------------

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Unicode normalisation + cosmetic whitespace/dash fixes."""
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r"\s+", " ", text)
        text = text.replace(" | ", ". ")
        text = text.replace("—", "-").replace("–", "-")
        text = text.translate(str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'"}))
        return text.strip()

    def _is_acronym(self, token: str) -> bool:
        return (
            self.keep_acronyms
            and token.isupper()
            and len(token) > 1
            and token.isalpha()
        )

    # ---------------------------------------------------------------------

    def preprocess_text(self, text: str) -> List[str]:
        """Split *text* into sentences while stitching tiny fragments together."""

        text = self._normalize_text(text)

        # High‑level helper chooses punkt or punkt_tab automatically
        try:
            sentences = nltk.tokenize.sent_tokenize(text, language=self.language)
        except LookupError:  # pragma: no cover
            _ensure_nltk_resources()
            sentences = nltk.tokenize.sent_tokenize(text, language=self.language)

        processed: list[str] = []
        buffer = ""

        for sentence in map(str.strip, sentences):
            if not sentence:
                continue

            # Preserve common abbreviation‑heavy snippets
            if any(abbr in sentence for abbr in self.abbreviations):
                if buffer and len(buffer) + len(sentence) + 1 < self.min_chars:
                    buffer += " " + sentence
                else:
                    if buffer:
                        processed.append(buffer.strip())
                    buffer = sentence
                continue

            # Merge glove‑fitting short sentences
            if len(buffer) + len(sentence) + 1 < self.min_chars:
                buffer += (" " if buffer else "") + sentence
            else:
                if buffer:
                    processed.append(buffer.strip())
                buffer = sentence

        if buffer:
            processed.append(buffer.strip())

        return [s for s in processed if len(s) > 5]

    # ---------------------------------------------------------------------

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract rudimentary named entities via POS tagging."""
        _ensure_nltk_resources()
        tokens = nltk.word_tokenize(text)
        tagged = nltk.pos_tag(tokens)

        entities: Dict[str, List[str]] = {
            "PERSON": [],
            "ORGANIZATION": [],
            "LOCATION": [],
        }
        for word, tag in tagged:
            if tag.startswith("NNP"):
                entities["PERSON"].append(word)
        return entities


# ---------------------------------------------------------------------------


def _demo() -> None:  # pragma: no cover
    sample = (
        "Dr. Smith, a renowned researcher at MIT, recently published a groundbreaking study. "
        "The research, conducted in collaboration with U.S. National Laboratories, "
        "explores innovative solutions for climate change, e.g. renewable energy technologies."
    )

    pre = AdvancedTextPreprocessor(min_chars=50)
    for s in pre.preprocess_text(sample):
        print("-", s)
    print("\nEntities:", pre.extract_entities(sample))


if __name__ == "__main__":
    _demo()
