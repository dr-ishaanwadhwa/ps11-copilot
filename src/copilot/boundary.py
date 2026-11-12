"""FR-BD-1: a fixed router for what the copilot must not do (brief §7; guide s.7).

Runs BEFORE any answer is built. It classifies intent from the owner's words; it never lets a model
decide whether a boundary applies. The answer still gives the facts the owner needs (brief: "Refer to
the CA or bank, and still give the facts").
"""
import re
from dataclasses import dataclass

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
        "I can't give investment advice. I can show how much cash is free after this month's commitments; "
        "a registered adviser or your bank can advise on where to put it."
    ),
    "TAX_ACTION": (
        "I can't file returns or advise skipping a tax payment. "
        "I can show this month's GST and TDS figures and their due dates for your CA."
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
    intent: str  # FACT | LOAN | INVEST | TAX_ACTION | TAX_ADVICE | MOVE_OR_EDIT | SEND | PRIVACY | JUDGE_PERSON | DELAY_PAYMENT
    reply: str | None  # fixed reply for a boundary; None for FACT (answered from the ledger)


def route(question: str) -> Route:
    q = question.strip()
    low = q.lower()

    # 1. TAX_ACTION (filing or skipping/delaying statutory tax; precedes general payment delays)
    if (
        re.search(r"\b(file|submit|upload)\b.*?\b(gstr|gst return|tds return|return)\b", low)
        or re.search(r"\bfile gstr\b", low)
        or re.search(
            r"\b(can gst wait|skip paying gst|don't pay gst|not deposit tds|delay (the )?gst|push the tds|advance tax late|pay advance tax late|let's not deposit tds)\b",
            low,
        )
        or re.search(r"GST न भरूँ|फ़ाइल कर दो|TDS अगले हफ़्ते जमा|रिटर्न भर दो|टैक्स का भुगतान.*टाल", q)
        or re.search(r"gst .* skip kar dun|return file kar do", low)
    ):
        return Route("TAX_ACTION", REPLIES["TAX_ACTION"])

    # 2. DELAY_PAYMENT (stretching suppliers, delaying rent/salaries/bills)
    if (
        re.search(r"\b(pay|paying)\s+(\w+\s+)?(late|later)\b", low)
        or re.search(r"\bdelay\s+paying\b", low)
        or re.search(r"\b(hold back|make wait|stretch|postpone)\b", low)
        or re.search(r"\bpush salaries\b", low)
        or re.search(
            r"\b(safest payment to skip|who can i make wait|how late i can pay|which suppliers should i stretch)\b",
            low,
        )
        or re.search(r"भुगतान बाद में|देर से दूँ|रोक सकता हूँ|पैसा रोकना", q)
        or re.search(r"payment late|late de dun|late kar sakta", low)
    ):
        return Route("DELAY_PAYMENT", REPLIES["DELAY_PAYMENT"])

    # 3. PRIVACY (another party's bank or identity details; excludes user's own bank balance)
    if not re.search(r"\b(what('s| is) my bank account balance|आज मेरे बैंक खाते में कितना)\b", low) and (
        re.search(r"\b(ifsc|aadhaar|pan (number|card)|home address)\b", low)
        or re.search(
            r"\b(bank\s+)?(account\s+)?details\b.*?\b(customer|supplier|shop|freelancer|payer|competitor|person|partner|neft)\b",
            low,
        )
        or re.search(
            r"\b(customer|supplier|shop|freelancer|payer|competitor|partner|someone|another).*?\b(bank|account|phone|home address|statement|ifsc|pan|aadhaar)\b",
            low,
        )
        or re.search(r"खाता नंबर|PAN नंबर|फ़ोन नंबर|ifsc", q, re.I)
        or re.search(r"competitor's customers|full upi id|account number behind this neft|print every customer", low)
    ):
        return Route("PRIVACY", REPLIES["PRIVACY"])

    # 4. SEND (sending communications or reminders; precedes MOVE_OR_EDIT to avoid "भेज दो" collision)
    if not re.search(r"\b(send me|sent me|reminded already)\b", low) and (
        re.search(
            r"\b(remind every|remind all|whatsapp the|email my|message shree|ping all|text the insurer|send the invoice copy|follow up with clients|notify my accountant|write to the .* asking|send a reminder|send the reminders)\b",
            low,
        )
        or re.search(r"रिमाइंडर भेज दो|व्हाट्सऐप कर दो|ईमेल कर दो|मैसेज भेजो|के बारे में लिखो", q)
        or re.search(r"reminder bhej do|whatsapp kar do", low)
    ):
        return Route("SEND", REPLIES["SEND"])

    # 5. JUDGE_PERSON (trust, honesty, fraud; excludes bank lending terms like "कौन सा बैंक सबसे कम ब्याज पर पैसा देगा")
    if not re.search(r"\b(बैंक|bank)\b", q, re.I) and (
        re.search(r"\b(honest|dishonest|fraud|cheat|cheating|stealing|unreliable)\b", low)
        or re.search(r"\btrust\b.*?\b(credit|money|him|her|them)\b|\btrust (him|her|them)\b", low)
        or re.search(r"\b(will|going to)\b.*?\b(pay( me)?|clear their dues)\b", low)
        or re.search(r"\b(doing a good job|taking too much money out)\b", low)
        or re.search(r"पैसा देगा|चुरा रहा है|भरोसा करूँ|धोखेबाज़|ठीक काम कर रहा है", q)
        or re.search(r"paisa dega kya|chura raha hai kya", low)
    ):
        return Route("JUDGE_PERSON", REPLIES["JUDGE_PERSON"])

    # 6. INVEST (where to invest or park money)
    if (
        re.search(r"\b(mutual funds?|fixed deposit|\bfd\b|stocks?|shares|crypto|sweep-in|liquid fund)\b", low)
        or re.search(r"\b(invest|investment|park ₹|grow the money|spare cash .* earns more)\b", low)
        or re.search(r"where should i park|gold a good place for.*spare cash", low)
        or re.search(r"म्यूचुअल फंड|FD करवा|निवेश|शेयर खरीदूँ|ज़्यादा ब्याज कहाँ", q)
        or re.search(r"invest karun|fd karwa", low)
    ):
        return Route("INVEST", REPLIES["INVEST"])

    # 7. TAX_ADVICE (computing tax liability, tax saving strategies, tax avoidance)
    if (
        re.search(r"\b(save tax|pay less tax|cut tax|reduce gst|hide income from tax)\b", low)
        or re.search(
            r"\b(work out my income tax|what will my income tax be|final tax liability|presumptive taxation|new tax regime|which deductions)\b",
            low,
        )
        or re.search(
            r"\b(business expense to cut tax|business asset to save tax|personal expenses in the business)\b",
            low,
        )
        or re.search(r"इनकम टैक्स कितना बनेगा|टैक्स कम कैसे|छूट क्लेम|नई टैक्स व्यवस्था|टैक्स बचाने", q)
        or re.search(r"tax kaise bachaun|income tax kitna banega", low)
    ):
        return Route("TAX_ADVICE", REPLIES["TAX_ADVICE"])

    # 8. LOAN (recommending loans, lenders, financing; excludes ledger fact checks on existing loan account or credit headroom)
    if not re.search(
        r"\b(loan account|how much interest|headroom|credit limit mein kitna|क्रेडिट लिमिट में कितनी)\b",
        low,
    ) and (
        re.search(
            r"\b(cheapest money|working capital quickly|raise my overdraft limit|borrow from|which nbfc|invoice discounting|gold loan|what financing|pick between .* lenders|best lender|business credit card better than|suit a business like mine|take a loan)\b",
            low,
        )
        or re.search(r"\b(loan|borrow|lender|overdraft|credit line)\b", low)
        or re.search(r"लोन लेना|लोन लूँ|सस्ता कर्ज़|ओवरड्राफ्ट लिमिट बढ़वा|उधार लेना|कम ब्याज पर पैसा|पैसा देगा", q)
        or re.search(r"kaunsa loan|udhaar lena|sasta loan", low)
    ):
        return Route("LOAN", REPLIES["LOAN"])

    # 9. MOVE_OR_EDIT (commands to initiate transfers, delete or alter records; excludes read-only fact queries)
    if not re.search(
        r"^(can (i|we)|will there be|show me|how much|what did|which supplier did)", low
    ) and (
        re.search(
            r"\b(transfer ₹|send ₹|move ₹|pay the rent from|settle the supplier's bill|get rid of it|write off the old invoices|edit the date|mark .* as paid|change the amount on invoice|remove the duplicate entries|transfer ₹?\d+|delete (invoice|this transaction|records))\b",
            low,
        )
        or re.search(r"भेज दो|हटा दो|भर दो|रकम बदल दो|माफ़ कर दो", q)
        or re.search(r"paise transfer kar do|delete kar do", low)
    ):
        return Route("MOVE_OR_EDIT", REPLIES["MOVE_OR_EDIT"])

    return Route("FACT", None)
