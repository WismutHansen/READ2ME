"""
paywall_detector.py – heuristic paywall / anti-bot page detection
"""

from __future__ import annotations

import re
from typing import Any, Iterable

from rapidfuzz import fuzz, process
import extruct

# --------------------------------------------------------------------------- #
# 1.  Keyword / regex inventory                                               #
# --------------------------------------------------------------------------- #

_REGEXES: tuple[re.Pattern, ...] = (
    re.compile(r"browser (?:requires|supports) javascript", re.I),
    re.compile(r"enable cookies", re.I),
    re.compile(r"verify (?:you'?re|that you are) (?:not )?a robot", re.I),
    re.compile(r"press and hold to (?:confirm|proceed)", re.I),
    re.compile(r"\bpaywall\b", re.I),
    re.compile(r"\bsubscription (?:required|only)\b", re.I),
    re.compile(r'\bisAccessibleForFree"?\s*:\s*false\b', re.I),
)

_KEYWORDS: tuple[str, ...] = (
    "robot.txt",
    "access denied",
    "please enable javascript",
    "please enable cookies",
    "subscribe to read",
    "support independent journalism",
)

_FUZZY_PHRASES: tuple[str, ...] = (
    "please make sure your browser supports javascript and cookies",
    "to continue, please click the box below",
    "for inquiries related to this message",
)

# --------------------------------------------------------------------------- #
# 2.  Helpers                                                                 #
# --------------------------------------------------------------------------- #


def _normalise(text: str) -> str:
    """Lower-case and collapse whitespace."""
    return " ".join(text.split()).lower()


def _keyword_hit(text: str) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in _KEYWORDS)


def _regex_hit(text: str) -> bool:
    return any(rx.search(text) for rx in _REGEXES)


def _fuzzy_hit(text: str, threshold: int = 92) -> bool:
    """Return True if *text* fuzzy-matches any of _FUZZY_PHRASES above *threshold*."""
    candidate = process.extractOne(
        _normalise(text),
        _FUZZY_PHRASES,
        scorer=fuzz.ratio,
    )
    return bool(candidate and candidate[1] >= threshold)


def _jsonld_paywall(html_str: str) -> bool:
    """
    Extract JSON-LD with extruct and return True if any object
    advertises `isAccessibleForFree = false`.
    """
    try:
        jsonld: Iterable[Any] = extruct.extract(
            html_str,
            base_url="",
            syntaxes=["json-ld"],
            uniform=True,
        ).get("json-ld", [])
    except Exception:
        # Bad markup, extruct couldn't parse
        return False

    for item in jsonld:
        # item can be dict or list[dict]
        objs: Iterable[dict] = item if isinstance(item, list) else [item]  # type: ignore[arg-type]
        for obj in objs:
            if isinstance(obj, dict) and obj.get("isAccessibleForFree") is False:
                return True
    return False


# --------------------------------------------------------------------------- #
# 3.  Public API                                                              #
# --------------------------------------------------------------------------- #


def is_paywall_or_robot_text(
    raw: str | bytes,
    http_status: int | None = None,
) -> bool:
    """
    Heuristically decide whether *raw* (HTML or plain text) represents a
    paywall / anti-bot barrier.

    Parameters
    ----------
    raw :
        The HTML/text body you received.
    http_status :
        Upstream HTTP status if you have it (e.g. 403, 451).

    Returns
    -------
    bool
        True  → very likely a paywall / anti-bot screen
        False → normal page content
    """
    if not raw:
        return False

    text = raw.decode(errors="ignore") if isinstance(raw, bytes) else raw

    # 0) Obvious HTTP clues
    if http_status in {401, 403, 429, 451}:
        return True

    # 1) Fast path – keywords / regex
    if _keyword_hit(text) or _regex_hit(text):
        return True

    # 2) Structured JSON-LD metadata
    if _jsonld_paywall(text):
        return True

    # 3) Fuzzy fallback
    return _fuzzy_hit(text)


# --------------------------------------------------------------------------- #
# 4.  CLI debug (optional)                                                    #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    import argparse
    from pathlib import Path

    import requests  # lightweight, only needed for CLI mode

    parser = argparse.ArgumentParser(description="Detect paywall/robot pages")
    parser.add_argument("target", help="file path or URL to test")
    args = parser.parse_args()

    target = args.target
    if Path(target).is_file():
        sample = Path(target).read_text(encoding="utf-8", errors="ignore")
        print(is_paywall_or_robot_text(sample))
    else:
        resp = requests.get(target, timeout=15)
        print(is_paywall_or_robot_text(resp.text, http_status=resp.status_code))
