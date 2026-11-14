"""FR-QA-1: template answers. Every number is computed here and cites the rows it came from.

v1 answers the brief's live tests T1 (who owes me most) and T7 (can I pay salaries), and routes every
boundary question first (T8, T10 and the other 14). All 67 questions are P1.
"""
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from . import config
from .boundary import route, keyword_route, is_known_fact_question
from .categorise import Categoriser
from .fmt import inr
from .load import Pack
from .masking import mask
from .receivables import by_customer, open_items


@dataclass
class Answer:
    text: str
    intent: str
    sources: list[str] = field(default_factory=list)
    numbers: dict = field(default_factory=dict)


class Copilot:
    def __init__(self, pack: Pack, vault: Any = None, cat_df: Any = None):
        self.pack = pack
        self.vault = vault
        if cat_df is not None:
            self.cat = cat_df
        else:
            self.cat = Categoriser(pack).apply(pack.bank)

    def closing_balance(self, biz: str, on: pd.Timestamp = config.AS_OF) -> tuple[float, str]:
        b = self.pack.bank[(self.pack.bank.business_id == biz) & (self.pack.bank.txn_date <= on)]
        last = b.sort_values(["txn_date", "seq"]).iloc[-1]
        return float(last.balance_inr), last.txn_id

    def credit_limit(self, biz: str) -> float:
        return self.pack.credit_limit(biz)

    def salary_run(self, biz: str, month: str) -> tuple[float, list[str]]:
        c = self.cat
        s = c[(c.business_id == biz) & (c.category == "Salary") & (c.txn_date.dt.strftime("%Y-%m") == month)]
        return float(s.debit_inr.sum()), list(s.txn_id)

    def party_names(self, biz: str) -> list[str]:
        if self.pack.parties is None or self.pack.parties.empty:
            return []
        p = self.pack.parties
        if "business_id" in p.columns and "party_name" in p.columns:
            return sorted(p[p.business_id == biz]["party_name"].dropna().unique().tolist())
        if "party_name" in p.columns:
            return sorted(p["party_name"].dropna().unique().tolist())
        return []

    def _get_vault(self) -> Any:
        if self.vault is not None:
            return self.vault
        try:
            import streamlit as st
            if "vault" in st.session_state and st.session_state["vault"]:
                return st.session_state["vault"]
        except Exception:
            pass
        try:
            from .vault import VaultDB
            v = VaultDB(in_memory=True)
            v.seed_from_pack(self.pack, pin="0000")
            return v
        except Exception:
            return None

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

    def cash_runway(self, biz: str) -> Answer:
        vault = self._get_vault()
        if not vault:
            return Answer("Cash runway calculation requires access to the Sovereign Vault.", "UNSUPPORTED")
        sol = vault.compute_solvency(self.pack, biz)
        runway_inr = sol.true_cash_runway_inr
        commitments = sol.total_commitments
        daily_burn = commitments / 30.0 if commitments > 0 else 1.0
        runway_days = round(runway_inr / daily_burn)

        text = (
            f"Your true cash runway buffer is {inr(runway_inr)} ({runway_days} days / {runway_days} दिन). "
            f"Daily burn rate is {inr(daily_burn)} based on 30-day commitments of {inr(commitments)} "
            f"(Net bank liquidity: {inr(sol.net_bank_liquidity)}, drawer cash: {inr(sol.galla_cash)})."
        )
        return Answer(
            text,
            "FACT",
            [f"SOLVENCY-{biz}"],
            {
                "runway_days": runway_days,
                "runway_inr": runway_inr,
                "commitments": commitments,
                "daily_burn": daily_burn,
                "bank_liquidity": sol.net_bank_liquidity,
                "galla_cash": sol.galla_cash,
            },
        )

    def credit_headroom(self, biz: str) -> Answer:
        bal, bal_row = self.closing_balance(biz)
        limit = self.credit_limit(biz)
        cc_drawn = abs(bal) if (bal < 0 and limit > 0) else 0.0
        headroom = bal + max(0.0, limit - cc_drawn)

        text = (
            f"Credit Limit & Headroom (क्रेडिट लिमिट और हेडरूम):\n"
            f"- Closing Bank Balance (बैंक बैलेंस): {inr(bal)}\n"
            f"- Sanctioned Limit (स्वीकृत लिमिट): {inr(limit)}\n"
            f"- Drawn Balance (उपयोग की गई राशि): {inr(cc_drawn)}\n"
            f"- Net Available Liquidity / Headroom (कुल उपलब्ध नकदी सीमा): {inr(headroom)}."
        )
        return Answer(
            text,
            "FACT",
            [bal_row, f"CREDIT-LIMIT-{biz}"],
            {
                "closing_balance": bal,
                "credit_limit": limit,
                "cc_drawn": cc_drawn,
                "headroom": headroom,
            },
        )

    def section_18_debts(self, biz: str) -> Answer:
        sources = []
        critical = []

        # 1. Formal open invoices
        items = open_items(self.pack, biz)
        if not items.empty:
            formal_s18 = items[items.days_open >= 913]
            for _, row in formal_s18.iterrows():
                critical.append({
                    "party": str(row["customer_name"]),
                    "amount": float(row["outstanding"]),
                    "age": f"{int(row['days_open'])} days",
                    "type": "Formal Invoice",
                })
                sources.append(str(row["invoice_no"]))

        # 2. Sovereign Khata accounts
        vault = self._get_vault()
        if vault:
            try:
                khata = vault.get_khata_summary(biz)
                for acc in khata.get("accounts", []):
                    if acc.is_limitation_alert or acc.months_open >= 30:
                        critical.append({
                            "party": acc.party_name,
                            "amount": float(acc.balance_due),
                            "age": f"{acc.months_open} months",
                            "type": "Informal Khata",
                        })
                        sources.append(f"KHATA-{biz}-{acc.party_name}")
            except Exception:
                pass

        total_critical_amt = sum(c["amount"] for c in critical)
        parties = [c["party"] for c in critical]

        if critical:
            debt_lines = "\n".join(
                f"- {c['party']}: {inr(c['amount'])} ({c['age']}, {c['type']})"
                for c in critical
            )
            text = (
                f"Section 18 Limitation Act Alert (धारा 18 समय-सीमा चेतावनी):\n"
                f"Under Section 18 of the Limitation Act, 1963, commercial debts older than 36 months risk becoming legally time-barred and unenforceable in court. "
                f"The copilot triggers an alert at 30 months (913 days) to protect your recovery rights.\n"
                f"Critical aging debt(s) nearing the 36-month cliff ({len(critical)} account(s), total {inr(total_critical_amt)}):\n"
                f"{debt_lines}\n"
                f"Action Required: Obtain written or digital WhatsApp acknowledgment of debt before the 36-month cliff to legally renew the limitation period. Use client-side 📲 Draft WhatsApp links on the Receivables page."
            )
        else:
            text = (
                f"Section 18 Limitation Act Status (धारा 18 समय-सीमा स्थिति):\n"
                f"No open receivables currently exceed the 30-month (913-day) limitation alert threshold as of {config.AS_OF:%d %b %Y}. "
                f"All customer dues remain legally enforceable under the Limitation Act, 1963. (कोई भी उधारी 30 महीने की सीमा के पास नहीं है।)"
            )

        return Answer(
            text,
            "FACT",
            sources or [f"RECEIVABLES-{biz}"],
            {
                "critical_count": len(critical),
                "critical_amount": total_critical_amt,
                "parties": parties,
            },
        )

    def aaj_ka_hisaab(self, biz: str) -> Answer:
        bal, bal_row = self.closing_balance(biz)
        limit = self.credit_limit(biz)
        cc_drawn = abs(bal) if (bal < 0 and limit > 0) else 0.0
        headroom = bal + max(0.0, limit - cc_drawn)

        vault = self._get_vault()
        galla_val = 0.0
        runway_inr = 0.0
        runway_days = 0
        if vault:
            try:
                latest = vault.get_latest_galla(biz)
                if latest:
                    galla_val = latest.counted_cash
                sol = vault.compute_solvency(self.pack, biz)
                runway_inr = sol.true_cash_runway_inr
                daily_burn = sol.total_commitments / 30.0 if sol.total_commitments > 0 else 1.0
                runway_days = round(runway_inr / daily_burn)
            except Exception:
                pass

        pay_ans = self.can_pay_salaries(biz, galla_cash=galla_val)
        can_pay = pay_ans.numbers.get("yes", True)
        salary_amt = pay_ans.numbers.get("salary", 0.0)

        s18_ans = self.section_18_debts(biz)
        s18_count = s18_ans.numbers.get("critical_count", 0)
        s18_amt = s18_ans.numbers.get("critical_amount", 0.0)
        s18_parties = s18_ans.numbers.get("parties", [])

        payroll_hi = "हाँ, सैलरी भुगतान सुरक्षित है" if can_pay else "सावधानी: वर्तमान तरलता से पूरा वेतन संभव नहीं"
        payroll_en = "Yes, payroll fully funded" if can_pay else "Warning: current liquidity insufficient for full payroll"

        if s18_count > 0:
            parties_str = ", ".join(s18_parties)
            s18_hi = f"चेतावनी: {s18_count} खाते ({parties_str}) कुल {inr(s18_amt)} 30 महीने से अधिक पुराने (धारा 18 समय-सीमा जोखिम)"
            s18_en = f"Alert: {s18_count} account(s) totaling {inr(s18_amt)} nearing 36-month Section 18 cliff"
            s18_summary = f"{s18_hi} / {s18_en}"
        else:
            s18_summary = "कोई पुरानी उधारी 30 महीने की सीमा पार नहीं है / All customer dues within legal limitation"

        text = (
            f"आज का हिसाब (Daily Financial Summary as of {config.AS_OF:%d %b %Y}):\n"
            f"1. बैंक बैलेंस (Bank Balance): {inr(bal)}\n"
            f"2. क्रेडिट लिमिट हेडरूम (Credit Headroom): {inr(headroom)} (स्वीकृत लिमिट / Sanctioned: {inr(limit)})\n"
            f"3. गल्ला रोकड़ (Galla Cash): {inr(galla_val)}\n"
            f"4. वास्तविक कैश रनवे (True Cash Runway): {runway_days} दिन ({runway_days} days, {inr(runway_inr)} buffer)\n"
            f"5. वेतन स्थिति (Payroll Status): {payroll_hi} ({payroll_en}, {inr(salary_amt)})\n"
            f"6. धारा 18 उधारी चेतावनी (Section 18 Limitation Alert): {s18_summary}."
        )

        sources = [bal_row, f"SOLVENCY-{biz}"]
        if s18_count > 0 and s18_ans.sources:
            sources.extend(s18_ans.sources)

        numbers = {
            "bank_balance": bal,
            "credit_limit": limit,
            "headroom": headroom,
            "galla_cash": galla_val,
            "runway_days": runway_days,
            "runway_inr": runway_inr,
            "can_pay_salaries": can_pay,
            "salary_amount": salary_amt,
            "section_18_count": s18_count,
            "section_18_amount": s18_amt,
            "section_18_parties": s18_parties,
        }
        return Answer(text, "FACT", sources, numbers)

    def ask(self, biz: str, question: str, galla_cash: float = 0.0) -> Answer:
        # Check boundary keywords locally first (zero bytes sent to cloud)
        kw = keyword_route(question)
        if kw.intent != "FACT":
            facts = []
            if kw.intent in ("LOAN", "JUDGE_PERSON", "SEND"):
                items = open_items(self.pack, biz)
                facts.append(f"Customers owe you {inr(items.outstanding.sum())} across {len(items)} invoices.")
            return Answer(" ".join([kw.reply] + facts), kw.intent)

        q = question.lower().strip()

        # Check local deterministic queries FIRST before calling cloud LLM router (ADR-001 & Offline resilience)
        # 1. Section 18 Limitation queries
        if any(k in q for k in ["limitation", "30 महीने", "36 महीने", "3 साल", "section 18", "धारा 18", "purani udhari", "पुरानी उधारी"]):
            return self.section_18_debts(biz)

        # 2. Aaj Ka Hisaab / Daily Cockpit status (supports both hisaab and hisab transliterations)
        if any(k in q for k in ["आज का हिसाब", "aaj ka hisaab", "aaj ka hisab", "hisaab", "hisab", "हिसाब", "दैनिक स्थिति", "daily hisaab", "cockpit"]):
            return self.aaj_ka_hisaab(biz)

        # 3. Top Debtor / Who owes most
        if ("owe" in q and "most" in q) or any(k in q for k in ["उधारी", "बकाया", "sabse zyada", "kis par hai", "who owes most"]):
            return self.who_owes_most(biz)

        # 4. Payroll feasibility
        if ("salar" in q and ("pay" in q or "afford" in q or "run" in q)) or any(k in q for k in ["सैलरी", "वेतन", "salary", "salaries"]):
            effective_galla = galla_cash
            if effective_galla == 0.0:
                vault = self._get_vault()
                if vault:
                    try:
                        latest = vault.get_latest_galla(biz)
                        if latest:
                            effective_galla = latest.counted_cash
                    except Exception:
                        pass
            return self.can_pay_salaries(biz, galla_cash=effective_galla)

        # 5. Cash Runway / Solvency
        if any(k in q for k in ["solvency", "runway", "buffer", "रनवे", "कितने दिन", "cash runway", "kitne din"]):
            return self.cash_runway(biz)

        # 6. Credit Headroom
        if any(k in q for k in ["credit limit", "headroom", "सीसी लिमिट", "od limit", "क्रेडिट लिमिट", "बैंक लिमिट"]):
            return self.credit_headroom(biz)

        # 7. Galla / Drawer cash
        if ("cash" in q or "galla" in q or "till" in q or "गल्ला" in q or "रोकड़" in q) and (
            "drawer" in q or "hand" in q or "counted" in q or "have" in q or "kitna" in q or "कितना" in q
        ):
            vault = self._get_vault()
            if vault:
                try:
                    latest = vault.get_latest_galla(biz)
                    if latest:
                        text = f"You counted {inr(latest.counted_cash)} in the drawer on {latest.date:%d %b %Y} (Status: {latest.status_label})."
                        return Answer(text, "FACT", [f"GALLA-{latest.date:%Y%m%d}"], {"counted_cash": latest.counted_cash, "status": latest.status_label})
                except Exception:
                    pass

        # For non-deterministic / open-ended questions, route with known names masked
        vault = self._get_vault()
        khata_names = [a.party_name for a in vault.get_khata_summary(biz).get("accounts", [])] if vault else []
        all_known = tuple(self.party_names(biz)) + tuple(khata_names)
        r = route(question, use_llm=True, known_names=list(all_known))
        if r.intent != "FACT":
            facts = []
            if r.intent in ("LOAN", "JUDGE_PERSON", "SEND"):
                items = open_items(self.pack, biz)
                facts.append(f"Customers owe you {inr(items.outstanding.sum())} across {len(items)} invoices.")
            return Answer(" ".join([r.reply] + facts), r.intent)

        # Grounded AI Copilot for general SME queries
        from .ai_client import get_ai_client

        ai = get_ai_client()
        if ai.is_configured:
            biz_name = config.BUSINESSES.get(biz, biz)
            bal, _ = self.closing_balance(biz)
            limit = self.credit_limit(biz)
            headroom = bal + limit
            items = open_items(self.pack, biz)
            total_recv = float(items.outstanding.sum())
            overdue_count = len(items[items.days_open > 45])

            galla_val = galla_cash
            solvency_info = ""
            if vault:
                try:
                    latest_g = vault.get_latest_galla(biz)
                    if latest_g and galla_val == 0.0:
                        galla_val = latest_g.counted_cash
                    sol = vault.compute_solvency(self.pack, biz)
                    solvency_info = (
                        f"- 30-Day Solvency Runway Buffer: {inr(sol.true_cash_runway_inr)}\n"
                        f"- Expected informal khata inflows: {inr(sol.total_expected_inflows)}\n"
                        f"- 30-Day commitments: {inr(sol.total_commitments)}\n"
                    )
                except Exception:
                    pass

            facts = (
                f"- Business: {biz_name}\n"
                f"- Closing Bank Balance (as of {config.AS_OF:%d %b %Y}): {inr(bal)}\n"
                f"- Sanctioned Credit Limit: {inr(limit)} (Net Headroom: {inr(headroom)})\n"
                f"- Physical Cash in Shop Drawer (Galla): {inr(galla_val)}\n"
                f"- Total Formal Receivables: {inr(total_recv)} across {len(items)} invoices ({overdue_count} > 45 days)\n"
                f"{solvency_info}"
            )
            masked_question = mask(question, list(all_known))
            ai_ans = ai.generate_grounded_answer(biz_name, masked_question, facts)
            if ai_ans:
                return Answer(
                    ai_ans,
                    "FACT_AI",
                    sources=[f"BANK-{biz}", f"LEDGER-{biz}"],
                    numbers={"closing_balance": bal, "headroom": headroom, "galla_cash": galla_val},
                )

        return Answer("I can't answer that yet in this version. It's on the list for the next release.", "UNSUPPORTED")
