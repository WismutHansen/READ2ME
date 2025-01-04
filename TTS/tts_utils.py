import os
import re
from phonemizer import backend as phonemizer_backend
import mimetypes
from utils.asr.audio2text import transcribe


def format_percentage(speed: float) -> str:
    """
    Converts a floating-point number to a percentage string in the form:
    1.0 -> "+0%", 1.1 -> "+10%", 0.9 -> "-10%", etc.
    Ensures the value stays between -50% and +50%.

    :param value: The floating-point value to format.
    :return: A string representing the percentage.
    """
    # Clamp the value to be between 0.5 and 1.5 (corresponding to -50% and +50%)
    clamped_value = max(0.5, min(1.5, speed))

    # Calculate the percentage change from 1.0
    percentage_change = (clamped_value - 1.0) * 100

    # Format the percentage with a "+" or "-" sign
    return f"{percentage_change:+.0f}%"


def load_transcript(voice_file: str, file_path: str) -> str:
    base_name = os.path.splitext(voice_file)[0]  # remove extension
    transcript_file = os.path.join(file_path, base_name + ".txt")

    if not os.path.exists(transcript_file):
        transcript = transcribe(os.path.join(file_path, voice_file))
        return transcript

    else:
        with open(transcript_file, "r", encoding="utf-") as file:
            transcript = file.read()
        return transcript


def get_voices_wav(directory: str) -> list:
    """
    Scans the given directory for available voices by matching audio and .txt files.

    Args:
        directory (str): Path to the directory containing audio and .txt files.

    Returns:
        list: A list of available voice filenames (including their extensions).
    """
    available_voices = []

    # Get list of all audio and .txt files in the directory
    audio_files = {
        f
        for f in os.listdir(directory)
        if mimetypes.guess_type(f)[0] and mimetypes.guess_type(f)[0].startswith("audio")
    }
    transcript_files = {f for f in os.listdir(directory) if f.endswith(".txt")}

    # Find common base filenames (without extensions) that have both audio and .txt files
    for audio_file in audio_files:
        base_name = os.path.splitext(audio_file)[
            0
        ]  # Extract the filename without extension
        transcript_file = base_name + ".txt"
        if transcript_file in transcript_files:
            available_voices.append(audio_file)  # Append the full audio filename

    return available_voices


# -------------------------------------------------------------------
# Utility functions for preparing text input for TTS engines
# like turning numbers into spelled out words etc.
# Required for getting natural sounding speech output for
# some TTS engines where the training didn't account for
# these aspects. Currently only focused on English text!
# -------------------------------------------------------------------


def resplit_strings(arr):
    """
    Given a list of string tokens (e.g. words, phrases), tries to
    split them into two sub-lists whose total lengths are as balanced
    as possible. The goal is to chunk a large string in half without
    splitting in the middle of a word.
    """
    if not arr:
        return "", ""
    if len(arr) == 1:
        return arr[0], ""

    min_diff = float("inf")
    best_split = 0
    lengths = [len(s) for s in arr]
    spaces = len(arr) - 1
    left_len = 0
    right_len = sum(lengths) + spaces

    for i in range(1, len(arr)):
        # Add current word + space to left side
        left_len += lengths[i - 1] + (1 if i > 1 else 0)
        # Remove from right side
        right_len -= lengths[i - 1] + 1
        diff = abs(left_len - right_len)
        if diff < min_diff:
            min_diff = diff
            best_split = i

    return " ".join(arr[:best_split]), " ".join(arr[best_split:])


def recursive_split(text, lang="a"):
    """
    Splits a piece of text into smaller segments so that
    each segment's phoneme length < some ~limit (~500 tokens).
    """
    # We'll reuse your existing `phonemize_text` + `tokenize` from script 1
    # to see if it is < 512 tokens. If it is, return it as a single chunk.
    # Otherwise, split on punctuation or whitespace and recurse.

    # 1. Phonemize first, check length
    ps = phonemize_text(text, lang=lang, do_normalize=True)
    tokens = tokenize(ps)
    if len(tokens) < 512:
        return [(text, ps)]

    # If too large, we split on certain punctuation or fallback to whitespace
    # We'll look for punctuation that often indicates sentence boundaries
    # If none found, fallback to space-split
    for punctuation in [r"[.?!…]", r"[:,;—]"]:
        pattern = f"(?:(?<={punctuation})|(?<={punctuation}[\"'»])) "
        # Attempt to split on that punctuation
        splits = re.split(pattern, text)
        if len(splits) > 1:
            break
    else:
        # If we didn't break out, just do whitespace split
        splits = text.split(" ")

    # Use resplit_strings to chunk it about halfway
    left, right = resplit_strings(splits)
    # Recurse
    return recursive_split(left, lang=lang) + recursive_split(right, lang=lang)


def segment_and_tokenize(long_text, lang="a"):
    """
    Takes a large text, optionally normalizes or cleans it,
    then breaks it into a list of (segment_text, segment_phonemes).
    """
    # Additional cleaning if you want:
    # long_text = normalize_text(long_text) # your existing function
    # We chunk it up using recursive_split
    segments = recursive_split(long_text, lang=lang)
    return segments


# -------------- Normalization & Phonemization Routines -------------- #


def parens_to_angles(s):
    return s.replace("(", "«").replace(")", "»")


def split_num(num):
    num = num.group()
    if "." in num:
        return num
    elif ":" in num:
        h, m = [int(n) for n in num.split(":")]
        if m == 0:
            return f"{h} o'clock"
        elif m < 10:
            return f"{h} oh {m}"
        return f"{h} {m}"
    year = int(num[:4])
    if year < 1100 or year % 1000 < 10:
        return num
    left, right = num[:2], int(num[2:4])
    s = "s" if num.endswith("s") else ""
    if 100 <= year % 1000 <= 999:
        if right == 0:
            return f"{left} hundred{s}"
        elif right < 10:
            return f"{left} oh {right}{s}"
    return f"{left} {right}{s}"


def flip_money(m):
    m = m.group()
    bill = "dollar" if m[0] == "$" else "pound"
    if m[-1].isalpha():
        return f"{m[1:]} {bill}s"
    elif "." not in m:
        s = "" if m[1:] == "1" else "s"
        return f"{m[1:]} {bill}{s}"
    b, c = m[1:].split(".")
    s = "" if b == "1" else "s"
    c = int(c.ljust(2, "0"))
    coins = (
        f"cent{'' if c == 1 else 's'}"
        if m[0] == "$"
        else ("penny" if c == 1 else "pence")
    )
    return f"{b} {bill}{s} and {c} {coins}"


def point_num(num):
    a, b = num.group().split(".")
    return " point ".join([a, " ".join(b)])


def normalize_text(text):
    text = text.replace(chr(8216), "'").replace(chr(8217), "'")
    text = text.replace("«", chr(8220)).replace("»", chr(8221))
    text = text.replace(chr(8220), '"').replace(chr(8221), '"')
    text = parens_to_angles(text)

    # Replace some common full-width punctuation in CJK:
    for a, b in zip("、。！，：；？", ",.!,:;?"):
        text = text.replace(a, b + " ")

    text = re.sub(r"[^\S \n]", " ", text)
    text = re.sub(r"  +", " ", text)
    text = re.sub(r"(?<=\n) +(?=\n)", "", text)
    text = re.sub(r"\bD[Rr]\.(?= [A-Z])", "Doctor", text)
    text = re.sub(r"\b(?:Mr\.|MR\.(?= [A-Z]))", "Mister", text)
    text = re.sub(r"\b(?:Ms\.|MS\.(?= [A-Z]))", "Miss", text)
    text = re.sub(r"\b(?:Mrs\.|MRS\.(?= [A-Z]))", "Mrs", text)
    text = re.sub(r"\betc\.(?! [A-Z])", "etc", text)
    text = re.sub(r"(?i)\b(y)eah?\b", r"\1e'a", text)
    text = re.sub(
        r"\d*\.\d+|\b\d{4}s?\b|(?<!:)\b(?:[1-9]|1[0-2]):[0-5]\d\b(?!:)",
        split_num,
        text,
    )
    text = re.sub(r"(?<=\d),(?=\d)", "", text)
    text = re.sub(
        r"(?i)[$£]\d+(?:\.\d+)?(?: hundred| thousand| (?:[bm]|tr)illion)*\b|[$£]\d+\.\d\d?\b",
        flip_money,
        text,
    )
    text = re.sub(r"\d*\.\d+", point_num, text)
    text = re.sub(r"(?<=\d)-(?=\d)", " to ", text)  # Could be minus; adjust if needed
    text = re.sub(r"(?<=\d)S", " S", text)
    text = re.sub(r"(?<=[BCDFGHJ-NP-TV-Z])'?s\b", "'S", text)
    text = re.sub(r"(?<=X')S\b", "s", text)
    text = re.sub(
        r"(?:[A-Za-z]\.){2,} [a-z]", lambda m: m.group().replace(".", "-"), text
    )
    text = re.sub(r"(?i)(?<=[A-Z])\.(?=[A-Z])", "-", text)
    return text.strip()


# -------------------------------------------------------------------
# Vocab and Symbol Mapping used in StyleTTS2 and Kokoro
# -------------------------------------------------------------------


def get_vocab():
    _pad = "$"
    _punctuation = ';:,.!?¡¿—…"«»“” '
    _letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    _letters_ipa = "ɑɐɒæɓʙβɔɕçɗɖðʤəɘɚɛɜɝɞɟʄɡɠɢʛɦɧħɥʜɨɪʝɭɬɫɮʟɱɯɰŋɳɲɴøɵɸθœɶʘɹɺɾɻʀʁɽʂʃʈʧʉʊʋⱱʌɣɤʍχʎʏʑʐʒʔʡʕʢǀǁǂǃˈˌːˑʼʴʰʱʲʷˠˤ˞↓↑→↗↘'̩'ᵻ"
    symbols = [_pad] + list(_punctuation) + list(_letters) + list(_letters_ipa)
    dicts = {}
    for i, s in enumerate(symbols):
        dicts[s] = i
    return dicts


VOCAB = get_vocab()


def tokenize(ps: str):
    """Convert the phoneme string into integer tokens based on VOCAB."""
    return [VOCAB.get(p) for p in ps if p in VOCAB]


# -------------------------------------------------------------------
# Initialize a simple phonemizer
#   For English:
#       'a' ~ en-us
#       'b' ~ en-gb
# -------------------------------------------------------------------

phonemizers = dict(
    a=phonemizer_backend.EspeakBackend(
        language="en-us", preserve_punctuation=True, with_stress=True
    ),
    b=phonemizer_backend.EspeakBackend(
        language="en-gb", preserve_punctuation=True, with_stress=True
    ),
)


def phonemize_text(text, lang="a", do_normalize=True):
    if do_normalize:
        text = normalize_text(text)
    ps_list = phonemizers[lang].phonemize([text])
    ps = ps_list[0] if ps_list else ""

    # Some custom replacements (from your code)
    ps = ps.replace("kəkˈoːɹoʊ", "kˈoʊkəɹoʊ").replace("kəkˈɔːɹəʊ", "kˈəʊkəɹəʊ")
    ps = ps.replace("ʲ", "j").replace("r", "ɹ").replace("x", "k").replace("ɬ", "l")
    # Example: insert space before "hˈʌndɹɪd" if there's a letter, e.g. "nˈaɪn" => "nˈaɪn hˈʌndɹɪd"
    ps = re.sub(r"(?<=[a-zɹː])(?=hˈʌndɹɪd)", " ", ps)
    # "z" at the end of a word -> remove space (just your snippet)
    ps = re.sub(r' z(?=[;:,.!?¡¿—…"«»“” ]|$)', "z", ps)
    # If lang is 'a', handle "ninety" => "ninedi"? Just from your snippet:
    if lang == "a":
        ps = re.sub(r"(?<=nˈaɪn)ti(?!ː)", "di", ps)

    # Only keep valid symbols
    ps = "".join(p for p in ps if p in VOCAB)
    return ps.strip()
