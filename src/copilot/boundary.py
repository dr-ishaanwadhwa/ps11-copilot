"""FR-BD-1: a fixed router for what the copilot must not do (brief §7; guide s.7; D63, D66, D70).

Runs BEFORE any answer is built. It classifies intent from the owner's words; it never lets a model
decide whether a boundary applies. The answer still gives the facts the owner needs (brief: "Refer to
the CA or bank, and still give the facts").
"""
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .masking import mask
from .router_llm import classify

logger = logging.getLogger(__name__)

READ_ONLY = "I can't do that: I'm read-only, so I never move, change or delete money or records."

REPLIES: dict[str, str] = {
    "PRIVACY": (
        "I can't share another person's bank or identity details. "
        "I can show what they owe you and their payment history."
    ),
    "LOAN": (
        "I can't recommend a loan, lender or product. Here are the facts: the shortfall, when it happens, "
        "and the levers inside the business (collections due, payments that can move). "
        "Your bank or CA can advise on funding."
    ),
    "INVEST": (
        "I can't give investment advice. I can display surplus liquidity after scheduled obligations; "
        "a registered adviser or bank can advise on placement."
    ),
    "TAX_ACTION": (
        "I can't file returns or advise skipping tax deposits. "
        "I can provide current GST and TDS ledger figures and due dates for your CA."
    ),
    "TAX_ADVICE": (
        "I can't compute your final tax; your CA does that. "
        "I can give your CA a clean summary of income and expenses."
    ),
    "MOVE_OR_EDIT": READ_ONLY,
    "SEND": (
        "I'll draft the reminders for you to review: one per customer, with invoice numbers and amounts. "
        "Nothing is sent until you approve it."
    ),
    "JUDGE_PERSON": (
        "I can't judge a person. Here are the facts: what they owe, how long it's been open, "
        "and how they've paid before."
    ),
    "DELAY_PAYMENT": (
        "I can't advise which payment to delay or pay late. Here are the due dates and amounts from your records; "
        "your suppliers or CA can advise on payment terms. (Note: statutory tax payments like GST or TDS cannot be delayed)."
    ),
}


@dataclass
class Route:
    intent: str
    reply: str | None
    source: str = "keywords"


NEEDS_CHIPS = Route(
    "NEEDS_CHIPS",
    "I'm not sure I understood. Please pick one of these questions.",
    source="system",
)


# Compact intent word and short stem patterns (Task 3.1)
PATTERNS: dict[str, tuple[str, str]] = {
    # 1. TAX_ACTION (checked before DELAY_PAYMENT)
    "TAX_ACTION": (
        r"\b(gstr|itr)\b|\b(file|filing|submit)\b.*\b(return|returns)\b|\b(skip|delay|avoid)\b.*\b(gst|tds|tax)\b",
        r"रिटर्न भर|टैक्स टाल|gst टाल|tds टाल|tax skip|return file",
    ),
    # 2. DELAY_PAYMENT
    "DELAY_PAYMENT": (
        r"\b(delay|stretch|postpone|hold back)\b.*\b(payment|bill|vendor|supplier|salary|rent|payee)\b|\b(pay|paying)\b.*\b(late|later)\b",
        r"देर से|बाद में देना|भुगतान टाल|रोक|late pay|delay pay",
    ),
    # 3. PRIVACY (excludes own account / balance)
    "PRIVACY": (
        r"\b(ifsc|aadhaar|pan)\b|\b(bank account|phone number|home address)\b|\b(customer|supplier|vendor|party|other)\b.*\b(bank|account|phone|address|ifsc|pan)\b",
        r"खाता नंबर|pan नंबर|फ़ोन नंबर|आधार",
    ),
    # 4. SEND (checked before MOVE_OR_EDIT)
    "SEND": (
        r"\b(send|remind|reminder|whatsapp|email|sms|message|notify)\b",
        r"भेज|रिमाइंडर|याद दिला|मैसेज|bhej|sandesh",
    ),
    # 5. JUDGE_PERSON
    "JUDGE_PERSON": (
        r"\b(honest|dishonest|fraud|cheat|cheating|trust|reliable|unreliable)\b|\b(will|going to)\b.*\b(pay|clear)\b",
        r"भरोसा|धोखा|ईमानदार|चोरी|vishwas|bharosa|dhokha",
    ),
    # 6. INVEST
    "INVEST": (
        r"\b(invest|investment|mutual fund|fixed deposit|\bfd\b|shares?|stocks?|crypto|park cash|park money)\b",
        r"निवेश|म्यूचुअल फंड|\bfd\b|शेयर|invest|nivesh",
    ),
    # 7. TAX_ADVICE
    "TAX_ADVICE": (
        r"\b(income tax|save tax|cut tax|reduce tax|tax saving|tax advice|tax liability)\b",
        r"टैक्स बचा|टैक्स कम|इनकम टैक्स|tax bachana|tax bachaun",
    ),
    # 8. LOAN (excludes credit limit / headroom / loan account queries)
    "LOAN": (
        r"\b(loan|borrow|lender|overdraft|credit line|nbfc|financing)\b",
        r"उधार|लोन|कर्ज़|udhaar",
    ),
    # 9. MOVE_OR_EDIT (commands to alter or delete records or money)
    "MOVE_OR_EDIT": (
        r"\b(transfer|delete|remove|erase|write off|modify|edit)\b",
        r"हटा दो|मिटा दो|डिलीट|बदल दो|माफ़ कर दो",
    ),
}

_READONLY_HINTS = re.compile(r"^(can (i|we)|how much|when|which|show me)\b", re.I)
_OWN_ACCOUNT = re.compile(r"\b(my|our)\s+(bank\s+)?(balance|account)\b|मेरे खाते|मेरा (बैलेंस|खाता)", re.I)
_SEND_EXCLUSIONS = re.compile(r"\b(send me|sent me|sent to me)\b", re.I)
_LOAN_EXCLUSIONS = re.compile(r"\b(credit limit|headroom|loan account)\b", re.I)


def is_known_fact_question(question: str) -> bool:
    """Matches shapes of fact questions the template answers can actually handle."""
    low = question.strip().lower()
    if re.search(r"\b(who owes|sabse zyada|owes me)\b", low):
        return True
    if re.search(r"\b(pay salaries|salaries|salary run)\b", low):
        return True
    if re.search(r"\b(balance|cash position|closing balance|headroom|galla|drawer|till|runway|solvency)\b", low):
        return True
    if re.search(r"\b(explain|hindi)\b", low):
        return True
    return False


def keyword_route(question: str) -> Route:
    """Intent classification using strict intent words and short stems only (Task 3.1)."""
    q = question.strip()
    low = q.lower()

    # Precedence 1: TAX_ACTION before DELAY_PAYMENT
    en_tax, hi_tax = PATTERNS["TAX_ACTION"]
    if re.search(en_tax, low) or re.search(hi_tax, q, re.I):
        return Route("TAX_ACTION", REPLIES["TAX_ACTION"], source="keywords")

    # Precedence 2: DELAY_PAYMENT
    en_del, hi_del = PATTERNS["DELAY_PAYMENT"]
    if re.search(en_del, low) or re.search(hi_del, q, re.I):
        return Route("DELAY_PAYMENT", REPLIES["DELAY_PAYMENT"], source="keywords")

    # Precedence 3: PRIVACY (with own-account exception)
    if not _OWN_ACCOUNT.search(low):
        en_priv, hi_priv = PATTERNS["PRIVACY"]
        if re.search(en_priv, low) or re.search(hi_priv, q, re.I):
            return Route("PRIVACY", REPLIES["PRIVACY"], source="keywords")

    # Precedence 4: SEND (before MOVE_OR_EDIT)
    if not _SEND_EXCLUSIONS.search(low):
        en_send, hi_send = PATTERNS["SEND"]
        if re.search(en_send, low) or re.search(hi_send, q, re.I):
            return Route("SEND", REPLIES["SEND"], source="keywords")

    # Precedence 5: JUDGE_PERSON
    en_jdg, hi_jdg = PATTERNS["JUDGE_PERSON"]
    if re.search(en_jdg, low) or re.search(hi_jdg, q, re.I):
        return Route("JUDGE_PERSON", REPLIES["JUDGE_PERSON"], source="keywords")

    # Precedence 6: INVEST
    en_inv, hi_inv = PATTERNS["INVEST"]
    if re.search(en_inv, low) or re.search(hi_inv, q, re.I):
        return Route("INVEST", REPLIES["INVEST"], source="keywords")

    # Precedence 7: TAX_ADVICE
    en_tadv, hi_tadv = PATTERNS["TAX_ADVICE"]
    if re.search(en_tadv, low) or re.search(hi_tadv, q, re.I):
        return Route("TAX_ADVICE", REPLIES["TAX_ADVICE"], source="keywords")

    # Precedence 8: LOAN (excluding headroom / credit limit facts)
    if not _LOAN_EXCLUSIONS.search(low):
        en_loan, hi_loan = PATTERNS["LOAN"]
        if re.search(en_loan, low) or re.search(hi_loan, q, re.I):
            return Route("LOAN", REPLIES["LOAN"], source="keywords")

    # Precedence 9: MOVE_OR_EDIT (read-only fact questions must not trip MOVE_OR_EDIT)
    en_mov, hi_mov = PATTERNS["MOVE_OR_EDIT"]
    has_move = re.search(en_mov, low) or re.search(hi_mov, q, re.I)
    if has_move and not _READONLY_HINTS.search(low):
        return Route("MOVE_OR_EDIT", REPLIES["MOVE_OR_EDIT"], source="keywords")

    return Route("FACT", None, source="keywords")


class IntentRouter:
    """Deep module encapsulating fail-closed boundary detection, LLM classification, and audit logging."""

    def __init__(self, audit_sink: Path | None = None):
        self.audit_sink = audit_sink or (
            Path(__file__).resolve().parents[2] / "scripts" / "out" / "router_disagreements.jsonl"
        )

    def _log_disagreement(
        self,
        question: str,
        known_names: list[str],
        kw_intent: str,
        llm_intent: str,
        confident: bool,
    ) -> None:
        try:
            self.audit_sink.parent.mkdir(parents=True, exist_ok=True)
            masked = mask(question, known_names)
            record = {
                "masked_question": masked,
                "keyword_intent": kw_intent,
                "llm_intent": llm_intent,
                "confident": confident,
            }
            with open(self.audit_sink, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.debug("Failed writing disagreement audit record: %s", exc)

    def route(
        self,
        question: str,
        *,
        use_llm: bool = False,
        known_names: list[str] = (),
        client: Any = None,
    ) -> Route:
        """Fail-closed ensemble router combining keyword rules and Claude classifier (Task 3.4)."""
        kw = keyword_route(question)
        if kw.intent != "FACT":
            return kw  # Keywords say boundary -> fail-safe boundary

        if not use_llm:
            return Route("FACT", None, source="keywords") if is_known_fact_question(question) else NEEDS_CHIPS

        d = classify(question, list(known_names), client=client)
        if d is None:  # Model unavailable, timeout, or refused
            return NEEDS_CHIPS

        if d.intent != "FACT":
            self._log_disagreement(question, list(known_names), kw.intent, d.intent, d.confident)
            reply = REPLIES.get(d.intent, READ_ONLY)
            return Route(d.intent, reply, source="llm")

        if not d.confident:
            return NEEDS_CHIPS

        return Route("FACT", None, source="llm")


_default_router = IntentRouter()


def route(
    question: str,
    *,
    use_llm: bool = False,
    known_names: list[str] = (),
    client: Any = None,
) -> Route:
    """Fail-closed ensemble router combining keyword rules and Claude classifier (Task 3.4)."""
    return _default_router.route(
        question,
        use_llm=use_llm,
        known_names=known_names,
        client=client,
    )
