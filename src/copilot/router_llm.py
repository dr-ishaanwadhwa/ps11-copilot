"""Claude-based structured output intent classifier (Task 3.3; D63, D66, D70).

Uses claude-opus-5-5 with low effort structured output on masked queries.
Fails closed: returns None on any connection error, rate limit, refusal, or missing key.
"""
from typing import Literal
import anthropic
from pydantic import BaseModel

from .masking import mask

Intent = Literal[
    "FACT",
    "LOAN",
    "INVEST",
    "TAX_ACTION",
    "TAX_ADVICE",
    "MOVE_OR_EDIT",
    "SEND",
    "PRIVACY",
    "JUDGE_PERSON",
    "DELAY_PAYMENT",
]


class RouterDecision(BaseModel):
    intent: Intent
    language: Literal["en", "hi", "hinglish", "other"]
    confident: bool


SYSTEM = """You are an intent classifier for an SME cash-flow assistant.
Classify the user inquiry into exactly one of the following ten intents:
1. FACT: Inquiries answered strictly from the enterprise ledger, historical figures, or bank balance.
2. LOAN: Financing options, borrowing products, or lender selection; facts on internal cash levers only.
3. INVEST: Where to park or invest surplus funds.
4. TAX_ACTION: Submitting returns, or delaying, skipping, or withholding statutory tax obligations.
5. TAX_ADVICE: Computing fiscal liabilities, tax planning, deductions, or strategies to reduce taxes.
6. MOVE_OR_EDIT: Demands to execute payments, alter accounting entries, or delete transactions.
7. SEND: Requests to dispatch notifications, reminders, or messages to counterparties.
8. PRIVACY: Requests for personal identity documents, confidential accounts, or third-party private records.
9. JUDGE_PERSON: Assessing personal honesty, moral character, or creditworthiness of an individual.
10. DELAY_PAYMENT: Guidance on postponing vendor disbursements, stalling utility dues, or stretching creditors.

Guidelines:
- Questions may appear in English, Hindi, or Hinglish. Names, entities, and financial values are pre-masked (e.g. Party 1, ₹[AMOUNT], [ID], [GSTIN]).
- If an inquiry asks what action to take regarding loans, investments, taxation, delaying obligations, dispatching messages, or transferring capital, classify it under that boundary intent even if factual context is mentioned.
- Inquiries examining the business entity own verified balances, ledger entries, or historical records are FACT.

Illustrative examples:
- FACT: "Show aggregate receipts recorded yesterday." | "कल का बैंक बैलेंस बताएं"
- LOAN: "Would an overdraft facility suit my boutique?" | "व्यापार हेतु कौन सा ऋण उचित रहेगा"
- INVEST: "Where should surplus corporate treasury reserves be deployed?" | "अधिशेष राशि को कहां लगाना चाहिए"
- TAX_ACTION: "Submit my monthly sales tax declaration immediately." | "क्या इस बार रिटर्न जमा न करें"
- TAX_ADVICE: "How can our enterprise minimize statutory fiscal liability?" | "कर देयता घटाने का कोई उपाय बताएं"
- MOVE_OR_EDIT: "Erase transaction row number seven." | "यह प्रविष्टि बहीखाते से मिटा दें"
- SEND: "Dispatch payment alert to overdue clients." | "सभी बकाएदारों को तुरंत सूचना पहुंचाओ"
- PRIVACY: "Fetch home domicile for contractor." | "ठेकेदार का निजी पैन विवरण दिखाएं"
- JUDGE_PERSON: "Is the storekeeper trustworthy with store assets?" | "क्या उस व्यापारी पर विश्वास किया जा सकता है"
- DELAY_PAYMENT: "Should we hold off paying the landlord this week?" | "मकान मालिक का किराया कुछ दिन टाल दें क्या"
"""


def classify(
    question: str, known_names: list[str], client: anthropic.Anthropic | None = None
) -> RouterDecision | None:
    """Classify user question using Claude structured outputs on masked text (Task 3.3).
    
    Returns None when the model is unavailable or declines; callers must fail closed.
    """
    try:
        client = client or anthropic.Anthropic()
        response = client.with_options(timeout=8.0).messages.parse(
            model="claude-opus-5-5",
            max_tokens=2048,
            system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": mask(question, known_names)}],
            output_format=RouterDecision,
            output_config={"effort": "low"},
        )
    except (
        anthropic.APIConnectionError,
        anthropic.RateLimitError,
        anthropic.APIStatusError,
        anthropic.AuthenticationError,
    ):
        return None
    except Exception:
        return None

    if getattr(response, "stop_reason", None) == "refusal":
        return None

    return getattr(response, "parsed_output", None)
