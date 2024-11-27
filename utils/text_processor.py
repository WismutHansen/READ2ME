import nltk
import re
import unicodedata
from typing import List, Optional

# Download necessary NLTK resources
nltk.download("punkt")
nltk.download("averaged_perceptron_tagger")
nltk.download("wordnet")


class AdvancedTextPreprocessor:
    def __init__(
        self, min_chars: int = 50, language: str = "english", keep_acronyms: bool = True
    ):
        """
        Advanced text preprocessor using NLTK for sophisticated text processing.

        Args:
            min_chars (int): Minimum characters for combined sentences
            language (str): Language for sentence tokenization
            keep_acronyms (bool): Preserve acronyms during processing
        """
        self.min_chars = min_chars
        self.language = language
        self.keep_acronyms = keep_acronyms

        # Comprehensive abbreviations and acronyms
        self.abbreviations = {
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

    def normalize_text(self, text: str) -> str:
        """
        Normalize text by handling Unicode and common text artifacts.

        Args:
            text (str): Input text to normalize

        Returns:
            str: Normalized text
        """
        # Unicode normalization
        text = unicodedata.normalize("NFKC", text)

        # Standardize whitespace and line breaks
        text = re.sub(r"\s+", " ", text)
        text = text.replace(" | ", ". ")

        # Replace various dash/hyphen types
        text = text.replace("—", "-").replace("–", "-")

        # Normalize quotation marks
        text = text.translate(str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'"}))

        return text.strip()

    def is_acronym(self, token: str) -> bool:
        """
        Check if a token is an acronym.

        Args:
            token (str): Token to check

        Returns:
            bool: True if token is an acronym, False otherwise
        """
        return (
            self.keep_acronyms
            and token.isupper()
            and len(token) > 1
            and all(c.isalpha() for c in token)
        )

    def preprocess_text(self, text: str) -> List[str]:
        """
        Preprocess text using NLTK's advanced tokenization.

        Args:
            text (str): Input text to preprocess

        Returns:
            List[str]: Processed sentences
        """
        # Normalize text first
        text = self.normalize_text(text)

        # Use NLTK's sentence tokenizer (supports multiple languages)
        sentence_tokenizer = nltk.data.load(f"tokenizers/punkt/{self.language}.pickle")

        # Tokenize sentences
        sentences = sentence_tokenizer.tokenize(text)

        # Advanced sentence processing
        processed_sentences = []
        buffer = ""

        for sentence in sentences:
            # Trim whitespace
            sentence = sentence.strip()

            # Skip empty sentences
            if not sentence:
                continue

            # Check for abbreviations and special tokens
            tokens = nltk.word_tokenize(sentence)

            # Preserve certain abbreviations and acronyms
            if any(abbr in sentence for abbr in self.abbreviations):
                if buffer and len(buffer) + len(sentence) + 1 < self.min_chars:
                    buffer += f" {sentence}"
                else:
                    if buffer:
                        processed_sentences.append(buffer.strip())
                    buffer = sentence
                continue

            # Combine short sentences
            if len(buffer) + len(sentence) + 1 < self.min_chars:
                buffer += f" {sentence}" if buffer else sentence
            else:
                if buffer:
                    processed_sentences.append(buffer.strip())
                buffer = sentence

        # Add any remaining buffer
        if buffer:
            processed_sentences.append(buffer.strip())

        # Final filtering
        return [
            sent
            for sent in processed_sentences
            if sent.strip() and len(sent.strip()) > 5
        ]

    def extract_entities(self, text: str) -> dict:
        """
        Extract named entities using NLTK.

        Args:
            text (str): Input text

        Returns:
            dict: Extracted entities
        """
        # Tokenize and POS tag the text
        tokens = nltk.word_tokenize(text)
        tagged = nltk.pos_tag(tokens)

        # Extract named entities
        entities = {"PERSON": [], "ORGANIZATION": [], "LOCATION": []}

        # Simple NER using POS tags (Note: This is a basic implementation)
        for word, tag in tagged:
            if tag.startswith("NNP"):  # Proper noun
                entities["PERSON"].append(word)
            # Add more sophisticated NER logic as needed

        return entities


# Example usage
def main():
    # Sample text with complex tokenization challenges
    sample_text = """
    Dr. Smith, a renowned researcher at MIT, recently published a groundbreaking study. 
    The research, conducted in collaboration with U.S. National Laboratories, 
    explores innovative solutions for climate change. e.g. renewable energy technologies.
    """

    # Initialize preprocessor
    preprocessor = AdvancedTextPreprocessor(
        min_chars=50, language="english", keep_acronyms=True
    )

    # Preprocess text
    processed_sentences = preprocessor.preprocess_text(sample_text)

    # Extract entities
    entities = preprocessor.extract_entities(sample_text)

    print("Processed Sentences:")
    for sentence in processed_sentences:
        print(f"- {sentence}")

    print("\nExtracted Entities:")
    print(entities)


if __name__ == "__main__":
    main()
