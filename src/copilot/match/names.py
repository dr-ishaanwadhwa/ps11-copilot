"""FR-CT-2: pull the payer/payee name out of a narration and resolve it to known parties.

Narrations are data, never instructions (FR-BD-2): we only pattern-match them.
"""
import re

from rapidfuzz import fuzz

_PATTERNS = [
    re.compile(r"^UPI-(?P<name>[^-]+)-(?P<handle>[^-]+@[^-]+)-"),           # UPI-NAME-handle@bank-...
    re.compile(r"^NEFT CR-[A-Z0-9]+-(?P<name>[^-]+)-"),                     # NEFT CR-IFSC-NAME-...
    re.compile(r"^NEFT-[A-Z0-9]+-(?P<name>[^-]+)-"),                        # NEFT-REF-NAME-...
    # NEFT/RTGS REF NAME [REF]: a bank reference always contains a digit, a name word never does
    re.compile(r"^(?:NEFT|RTGS) (?:DR |CR )?(?:[A-Z]*\d[A-Z0-9]* )?(?P<name>[A-Z][A-Z .&]+?)(?: [A-Z]{4}[A-Z0-9]{8,})?$"),
    re.compile(r"^INF/NEFT/\d+/[A-Z]+/(?P<name>[^/]+)/"),                   # INF/NEFT/ref/BANK/NAME/...
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
