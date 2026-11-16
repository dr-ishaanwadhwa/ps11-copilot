"""T9: the Hindi line carries exactly the English answer's numbers, and no advice."""
import re

import pytest

from copilot.answers import Answer
from copilot.fmt import inr
from copilot.hindi import hindi_summary

BIZ = ["SME-1", "SME-2", "SME-3"]
RUPEES = re.compile(r"₹\d(?:[\d,]*\d)?")


def rupees(s: str) -> set[str]:
    return set(RUPEES.findall(s))


@pytest.mark.parametrize("biz", BIZ)
def test_who_owes_most_parity(copilot, biz):
    a = copilot.who_owes_most(biz)
    hi = hindi_summary(a)
    assert hi and a.numbers["customer"] in hi
    assert rupees(hi) == {inr(a.numbers["outstanding"])}
    assert inr(a.numbers["outstanding"]) in a.text


@pytest.mark.parametrize("biz", BIZ)
def test_salary_parity(copilot, biz):
    a = copilot.can_pay_salaries(biz)
    hi = hindi_summary(a)
    n = a.numbers
    expected = {inr(n["salary"]), inr(n["closing_balance"]), inr(n["headroom"])}
    assert rupees(hi) == expected
    assert rupees(hi) <= rupees(a.text) | {inr(n["headroom"])}
    assert hi.startswith("हाँ") == bool(n["yes"])


def test_distributor_salary_gold(copilot):
    hi = hindi_summary(copilot.can_pay_salaries("SME-1"))
    assert {"₹3,80,160", "₹12,38,950", "₹37,38,950"} == rupees(hi)


@pytest.mark.parametrize("q", ["Should I take a loan to cover next month's shortfall?",
                               "Send a reminder to everyone who owes me money"])
def test_boundary_lines_give_no_advice(copilot, q):
    hi = hindi_summary(copilot.ask("SME-1", q))
    assert hi and not rupees(hi)
    assert "ज़रूरत नहीं" not in hi and "जरूरत नहीं" not in hi


def test_ungrounded_answers_get_no_hindi_line():
    assert hindi_summary(Answer("x", "FACT", numbers={})) is None
    assert hindi_summary(Answer("x", "UNSUPPORTED")) is None
    assert hindi_summary(None) is None
