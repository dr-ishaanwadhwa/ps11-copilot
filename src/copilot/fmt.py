"""Indian number formatting, done in code from one value (NFR-SAFE-2, FR-QA-3).

Hindi answers (P1) will reuse exactly these strings, so English and Hindi can never disagree.
"""


def inr(x: float, paise: bool = False) -> str:
    neg = x < 0
    x = abs(x)
    whole = int(x) if paise else int(round(x))
    s = str(whole)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups + [tail])
    if paise:
        s += f".{int(round((x - int(x)) * 100)):02d}"
    return ("−₹" if neg else "₹") + s


def lakh(x: float, digits: int = 1) -> str:
    return f"₹{x / 1e5:,.{digits}f} lakh"
