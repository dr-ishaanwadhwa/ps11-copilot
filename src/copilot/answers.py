"""FR-QA-1: template answers. Every number is computed here and cites the rows it came from.

v1 answers the brief's live tests T1 (who owes me most) and T7 (can I pay salaries), and routes every
boundary question first (T8, T10 and the other 14). All 67 questions are P1.
"""
import re
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from . import config
from .boundary import route
from .categorise import Categoriser
from .fmt import inr
from .load import Pack
from .receivables import by_customer, open_items


@dataclass
class Answer:
    text: str
    intent: str
    sources: list[str] = field(default_factory=list)   # txn_ids / document ids behind the numbers
    numbers: dict = field(default_factory=dict)        # raw values, for tests and the Hindi renderer (P1)


class Copilot:
    def __init__(self, pack: Pack, vault: Any = None, cat_df: Any = None):
        self.pack = pack
        self.vault = vault
        if cat_df is not None:
            self.cat = cat_df
        else:
            self.cat = Categoriser(pack).apply(pack.bank)

    # ── facts ───────────────────────────────────────────────────────────────
    def closing_balance(self, biz: str, on: pd.Timestamp = config.AS_OF) -> tuple[float, str]:
        b = self.pack.bank[(self.pack.bank.business_id == biz) & (self.pack.bank.txn_date <= on)]
        last = b.sort_values(["txn_date", "seq"]).iloc[-1]
        return float(last.balance_inr), last.txn_id

    def credit_limit(self, biz: str) -> float:
        acct = str(self.pack.businesses.set_index("business_id").loc[biz, "bank_account"])
        m = re.search(r"limit ₹([\d,]+)", acct)
        return float(m.group(1).replace(",", "")) if m else 0.0

    def salary_run(self, biz: str, month: str) -> tuple[float, list[str]]:
        c = self.cat
        s = c[(c.business_id == biz) & (c.category == "Salary") & (c.txn_date.dt.strftime("%Y-%m") == month)]
        return float(s.debit_inr.sum()), list(s.txn_id)

    # ── templates ───────────────────────────────────────────────────────────
    def who_owes_most(self, biz: str) -> Answer:
        items = open_items(self.pack, biz)
        top = by_customer(items).iloc[0]
        rows = items[items.customer_name == top.customer_name]
        oldest = int(rows.days_open.max())
        text = (f"{top.customer_name} owes you the most: {inr(top.outstanding)} across {int(top.invoices)} "
                f"invoices as of {config.AS_OF:%d %b %Y}. The oldest has been open {oldest} days.")
        return Answer(text, "FACT", list(rows.invoice_no),
                      {"customer": top.customer_name, "outstanding": float(top.outstanding), "invoices": int(top.invoices)})

    def can_pay_salaries(self, biz: str, on: pd.Timestamp = pd.Timestamp("2026-10-01"), galla_cash: float = 0.0) -> Answer:
        month = (on - pd.offsets.MonthBegin(1)).strftime("%Y-%m")
        salary, sal_rows = self.salary_run(biz, month)
        bal, bal_row = self.closing_balance(biz, on - pd.Timedelta(days=1))
        limit = self.credit_limit(biz)
        available = bal + limit
        yes = available >= salary
        limit_txt = (f", leaving {inr(available)} of headroom within the {inr(limit)} cash-credit limit"
                     if limit else "")
        galla_sentence = f" You also counted {inr(galla_cash)} in the drawer today; it is not included above." if galla_cash > 0 else ""
        text = (f"{'Yes' if yes else 'Not from current liquidity alone'}. Salaries were {inr(salary)} in "
                f"{pd.Timestamp(month + '-01'):%B}. The closing balance on {on - pd.Timedelta(days=1):%d %b %Y} "
                f"is {inr(bal)}{limit_txt}.{galla_sentence} Receipts expected and other payments due in the first week: "
                f"[forecast, not in v1].")
        return Answer(text, "FACT", [bal_row] + sal_rows,
                      {"salary": salary, "closing_balance": round(bal), "headroom": round(available),
                       "galla_cash": round(galla_cash), "yes": yes})

    def ask(self, biz: str, question: str, galla_cash: float = 0.0) -> Answer:
        r = route(question)
        if r.intent != "FACT":
            facts = []
            if r.intent in ("LOAN", "JUDGE_PERSON", "SEND"):
                items = open_items(self.pack, biz)
                facts.append(f"Customers owe you {inr(items.outstanding.sum())} across {len(items)} invoices.")
            return Answer(" ".join([r.reply] + facts), r.intent)
        q = question.lower()
        if "owe" in q and "most" in q:
            return self.who_owes_most(biz)
        if "salar" in q and ("pay" in q or "afford" in q):
            effective_galla = galla_cash
            if effective_galla == 0.0 and self.vault:
                latest = self.vault.get_latest_galla(biz)
                if latest:
                    effective_galla = latest.counted_cash
            return self.can_pay_salaries(biz, galla_cash=effective_galla)
        if ("cash" in q or "galla" in q or "till" in q) and ("drawer" in q or "hand" in q or "counted" in q or "have" in q) and self.vault:
            latest = self.vault.get_latest_galla(biz)
            if latest:
                text = f"You counted {inr(latest.counted_cash)} in the drawer on {latest.date:%d %b %Y} (Status: {latest.status_label})."
                return Answer(text, "FACT", [f"GALLA-{latest.date:%Y%m%d}"], {"counted_cash": latest.counted_cash, "status": latest.status_label})
        if ("solvency" in q or "runway" in q or "buffer" in q) and self.vault:
            sol = self.vault.compute_solvency(self.pack, biz)
            text = f"Your true cash runway buffer is {inr(sol.true_cash_runway_inr)} (Net bank liquidity: {inr(sol.net_bank_liquidity)}, drawer cash: {inr(sol.galla_cash)})."
            return Answer(text, "FACT", [f"SOLVENCY-{biz}"], {"runway_inr": sol.true_cash_runway_inr, "bank_liquidity": sol.net_bank_liquidity, "galla_cash": sol.galla_cash})
        return Answer("I can't answer that yet in this version. It's on the list for the next release.", "UNSUPPORTED")
