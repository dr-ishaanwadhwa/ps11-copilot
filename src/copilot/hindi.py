"""Hindi summary lines built only from an Answer's computed numbers (T9 parity).

Every rupee figure comes from `answer.numbers` through `inr`, so the Hindi line can
never show a number the English answer doesn't. Boundary answers get a referral with
no advice. Anything we can't ground returns None, and the app shows no Hindi line.
"""

from .answers import Answer
from .fmt import inr

BOUNDARY_LINE = {
    "LOAN": "लोन, निवेश या किसी उत्पाद की सलाह हम नहीं देते। ऊपर दिए आंकड़े अपने बैंक या CA के साथ देखें।",
    "SEND": "आपकी मंज़ूरी के बिना हम कोई संदेश नहीं भेजते। ड्राफ्ट देखकर आप ही भेजें।",
}
REFERRAL = "यह सवाल हमारे दायरे से बाहर है। इस पर अपने CA या बैंक से बात करें।"


def hindi_summary(a: Answer | None) -> str | None:
    if a is None:
        return None
    if a.intent not in ("FACT", "FACT_AI"):
        if a.intent in ("UNSUPPORTED", "NEEDS_CHIPS"):
            return None
        return BOUNDARY_LINE.get(a.intent, REFERRAL)

    n = a.numbers or {}
    if {"customer", "outstanding", "invoices"} <= n.keys():
        return (f"सबसे ज़्यादा बकाया {n['customer']} पर है: {inr(n['outstanding'])} "
                f"({n['invoices']} खुले इनवॉइस)।")
    if {"salary", "closing_balance", "headroom", "yes"} <= n.keys():
        verdict = "हाँ, सैलरी दी जा सकती है।" if n["yes"] else "सिर्फ़ मौजूदा नकदी से नहीं।"
        return (f"{verdict} सैलरी: {inr(n['salary'])}। बंद बैलेंस: {inr(n['closing_balance'])}। "
                f"लिमिट सहित उपलब्ध: {inr(n['headroom'])}।")
    if {"credit_limit", "cc_drawn", "headroom"} <= n.keys():
        return (f"क्रेडिट लिमिट {inr(n['credit_limit'])}, इस्तेमाल {inr(n['cc_drawn'])}, "
                f"बची सीमा {inr(n['headroom'])}।")
    if {"runway_days", "runway_inr"} <= n.keys():
        return f"मौजूदा नकदी लगभग {n['runway_days']} दिन चलेगी ({inr(n['runway_inr'])})।"
    if "counted_cash" in n:
        return f"गल्ले में गिना हुआ नकद: {inr(n['counted_cash'])}।"
    return None
