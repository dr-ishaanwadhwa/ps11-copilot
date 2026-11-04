"""FR-BD-1: a fixed router for what the copilot must not do (brief §7; guide s.7).

Runs BEFORE any answer is built. It classifies intent from the owner's words; it never lets a model
decide whether a boundary applies. The answer still gives the facts the owner needs (brief: "Refer to
the CA or bank, and still give the facts").
"""
import re
from dataclasses import dataclass

READ_ONLY = "I can't do that: I'm read-only, so I never move, change or delete money or records."


@dataclass
class Route:
    intent: str          # FACT | LOAN | INVEST | TAX_ACTION | TAX_ADVICE | MOVE_OR_EDIT | SEND | PRIVACY | JUDGE_PERSON
    reply: str | None    # fixed reply for a boundary; None for FACT (answered from the ledger)


_RULES: list[tuple[str, re.Pattern, str]] = [
    ("PRIVACY", re.compile(r"\b(bank account|account (number|details)|ifsc|aadhaar|pan (number|card))\b", re.I),
     "I can't share another person's bank or identity details. I can show what they owe you and their payment history."),
    ("LOAN", re.compile(r"\b(loan|borrow|overdraft|credit line|lender)\b", re.I),
     "I can't recommend a loan, lender or product. Here are the facts: the shortfall, when it happens, and the "
     "levers inside the business (collections due, payments that can move). Your bank or CA can advise on funding."),
    ("INVEST", re.compile(r"\b(invest|mutual funds?|stocks?|shares|fixed deposit|\bfd\b|insurance policy)\b", re.I),
     "I can't give investment advice. I can show how much cash is free after this month's commitments; "
     "a registered adviser or your bank can advise on where to put it."),
    ("TAX_ACTION", re.compile(r"\b(file|filing|gstr|skip (paying )?gst|delay (the )?gst|not pay (the )?gst)\b", re.I),
     "I can't file returns or advise skipping a tax payment. I can show this month's GST and TDS figures and "
     "their due dates for your CA."),
    ("TAX_ADVICE", re.compile(r"\b(income tax|tax liability|how much tax)\b", re.I),
     "I can't compute your final tax; your CA does that. I can give your CA a clean summary of income and expenses."),
    ("MOVE_OR_EDIT", re.compile(r"\b(transfer|pay .* now|send ₹|move money|delete|remove|edit) ?", re.I), READ_ONLY),
    ("SEND", re.compile(r"\b(send|remind|reminder|message|whatsapp|email)\b", re.I),
     "I'll draft the reminders for you to review: one per customer, with invoice numbers and amounts. "
     "Nothing is sent until you approve it."),
    ("JUDGE_PERSON", re.compile(r"\b(going to pay|will .* pay me|trust (him|her|them)|fraud|cheat)\b", re.I),
     "I can't judge a person. Here are the facts: what they owe, how long it's been open, and how they've paid before."),
]


def route(question: str) -> Route:
    q = question.strip()
    for intent, pat, reply in _RULES:
        if pat.search(q):
            return Route(intent, reply)
    return Route("FACT", None)
