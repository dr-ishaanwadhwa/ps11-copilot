"""Privacy masking for router LLM inputs (Task 3.2; D63, D70).

Replaces PII and specific financial identifiers with generic tokens:
- Known party names -> Party 1, Party 2... (longest first, stable within a call)
- GSTIN -> [GSTIN]
- PAN -> [PAN]
- Emails and UPI IDs -> [ID]
- Digit runs >= 9 -> [NUMBER]
- Rupee amounts -> ₹[AMOUNT]
"""
from collections.abc import Iterable
import re

_GSTIN_RE = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b")
_PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
_ID_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\b")
_NUMBER_RE = re.compile(r"\b\d{9,}\b")
_AMOUNT_RE = re.compile(r"(?:₹|Rs\.?|INR)\s*[\d,]+(?:\.\d+)?", re.I)


def mask(text: str, known_names: Iterable[str] = ()) -> str:
    """Mask PII, party names, and financial identifiers before passing to the LLM."""
    if not text:
        return ""

    res = text

    # 1. Known party names (longest first, case-insensitive, stable mapping within call)
    names = sorted({n.strip() for n in known_names if n and len(n.strip()) > 1}, key=len, reverse=True)
    party_map: dict[str, str] = {}
    for name in names:
        pattern = re.compile(r"\b" + re.escape(name) + r"\b", re.I)
        if pattern.search(res):
            k = name.lower()
            if k not in party_map:
                party_map[k] = f"Party {len(party_map) + 1}"
            res = pattern.sub(party_map[k], res)

    # 2. GSTIN
    res = _GSTIN_RE.sub("[GSTIN]", res)

    # 3. PAN
    res = _PAN_RE.sub("[PAN]", res)

    # 4. Email / UPI ID
    res = _ID_RE.sub("[ID]", res)

    # 5. Digit runs of 9 or more (phone, bank acct, txn ref)
    res = _NUMBER_RE.sub("[NUMBER]", res)

    # 6. Rupee amounts
    res = _AMOUNT_RE.sub("₹[AMOUNT]", res)

    return res
