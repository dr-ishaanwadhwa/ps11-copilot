"""FR-CT-2: pull the payer/payee name out of a narration and resolve it to known parties.

Narrations are data, never instructions (FR-BD-2): we only pattern-match them.
"""
import re

from rapidfuzz import fuzz, process

_PATTERNS = [
    re.compile(r"^UPI-(?P<name>[^-]+)-(?P<handle>[^-]+@[^-]+)-"),
    re.compile(r"^NEFT CR-[A-Z0-9]+-(?P<name>[^-]+)-"),
    re.compile(r"^NEFT-[A-Z0-9]+-(?P<name>[^-]+)-"),
    # NEFT/RTGS REF NAME [REF]: a bank reference always contains a digit, a name word never does
    re.compile(r"^(?:NEFT|RTGS) (?:DR |CR )?(?:[A-Z]*\d[A-Z0-9]* )?(?P<name>[A-Z][A-Z .&]+?)(?: [A-Z]{4}[A-Z0-9]{8,})?$"),
    re.compile(r"^INF/NEFT/\d+/[A-Z]+/(?P<name>[^/]+)/"),
    re.compile(r"^IMPS/(?P<name>[^/]+)/"),
    re.compile(r"^(?:NACH|BBPS)[-/ ](?P<name>[^-/]+)"),
]
_SUFFIX = re.compile(r"\b(PVT|LTD|LT|LIMITED|PRIVATE|LLP|CO|AND)\b")


def norm(s: str) -> str:
    s = str(s).upper().split(",")[0]
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = _SUFFIX.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def extract(narration: str) -> tuple[str | None, str | None]:
    """Return (name, upi_handle) from a narration, or (None, None)."""
    text = str(narration).strip()
    for p in _PATTERNS:
        m = p.match(text)
        if m:
            gd = m.groupdict()
            return norm(gd["name"]), gd.get("handle")
    return None, None


class PartyIndex:
    """Fuzzy lookup of a narration name against one business's parties (customers, TPAs, suppliers)."""

    def __init__(self, names: list[str]):
        self.names = sorted(set(names))
        self.normed = {n: norm(n) for n in self.names}

    def resolve(self, name: str | None, threshold: int = 92) -> list[str]:
        if not name or len(name) < 4:
            return []
        hits = [n for n, nn in self.normed.items()
                if nn == name or nn.startswith(name) or (len(nn) >= 6 and name.startswith(nn))]
        if hits:
            return hits
        return [n for n, nn in self.normed.items() if fuzz.ratio(nn, name) >= threshold]


_GENERIC_RETAIL_WORDS = {
    "kirana", "provision", "provisions", "store", "stores", "mart", "general",
    "supermarket", "mini", "departmental", "shop", "traders", "trading", "enterprise", "enterprises",
}


def match_retailer_name(query: str, party_list: list[str], threshold: float = 65.0) -> tuple[str, float]:
    """Match an extracted retailer name against verified business parties using RapidFuzz.

    Uses token_set_ratio to handle omitted localities and partial names.
    Guards against single generic words (e.g. 'kirana', 'provision', 'stores') to prevent false
    high-confidence matches.
    Returns (matched_party, confidence) where confidence is in [0.0, 1.0].
    If no match or score < threshold, returns (query, 0.0).
    """
    if not query or not party_list:
        return (query or "", 0.0)

    clean_query = str(query).strip()
    if not clean_query:
        return (query, 0.0)

    tokens = [t for t in re.findall(r"\w+", clean_query.lower())]
    distinctive = [t for t in tokens if t not in _GENERIC_RETAIL_WORDS and len(t) >= 2]
    if not distinctive:
        # Query consists solely of generic retail stop words.
        # Fall back to fuzz.ratio with penalty so partial smudges do not cause false high-confidence matches.
        match = process.extractOne(clean_query, party_list, scorer=fuzz.ratio)
        if match:
            best_match, score, _ = match
            penalized_score = float(score) * 0.5
            if penalized_score >= threshold:
                return (str(best_match), penalized_score / 100.0)
        return (query, 0.0)

    match = process.extractOne(clean_query, party_list, scorer=fuzz.token_set_ratio)
    if match:
        best_match, score, _ = match
        if score >= threshold:
            return (str(best_match), float(score) / 100.0)

    return (query, 0.0)

