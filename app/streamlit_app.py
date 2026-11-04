"""MVP v1 front end (local demo for 6 Nov; public URL by 12 Nov).

    streamlit run app/streamlit_app.py

Read-only: nothing here writes to a bank or ledger, or sends anything.
"""
import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder

from copilot import config
from copilot.answers import Copilot
from copilot.categorise import score_categories
from copilot.checks import import_report
from copilot.fmt import inr
from copilot.load import load_pack
from copilot.match import match_all
from copilot.match.engine import ASK, SUGGEST
from copilot.receivables import by_customer, open_items, overdue
from copilot.score import score_matches, summary

st.set_page_config(page_title="Cash Copilot · MVP v1", layout="wide")


@st.cache_resource(show_spinner="Reading the data pack and matching every line…")
def boot():
    pack = load_pack()
    matches = match_all(pack)
    return pack, matches, Copilot(pack)


pack, matches, copilot = boot()
biz = st.sidebar.selectbox("Business", list(config.BUSINESSES), format_func=lambda b: config.BUSINESSES[b])
st.sidebar.caption("Sample data pack · as of 30 Sep 2026 · read-only")

tab_home, tab_queue, tab_recv, tab_ask, tab_scores = st.tabs(
    ["Home", "Review queue", "Receivables", "Ask", "Scores"])

with tab_home:
    rep = import_report(pack)
    st.subheader("Your data, checked")
    c = st.columns(4)
    c[0].metric("Bank lines read", f"{rep['bank_lines']:,}")
    c[1].metric("Duplicate lines skipped", rep["duplicates_skipped"])
    c[2].metric("Running balance ties", "Yes" if rep["balance_ties"] else f"{rep['balance_breaks']} breaks")
    c[3].metric("Invoices and claims", f"{rep['documents']:,}")
    bal, _ = copilot.closing_balance(biz)
    limit = copilot.credit_limit(biz)
    st.subheader("Cash you can plan on")
    c = st.columns(3)
    c[0].metric("Bank balance, 30 Sep 2026", inr(bal))
    if limit:
        c[1].metric("Headroom in cash-credit limit", inr(bal + limit), help=f"Limit {inr(limit)}")
    items = open_items(pack, biz)
    c[2].metric("Customers owe you", inr(items.outstanding.sum()), f"{len(overdue(items))} invoices > 60 days late",
                delta_color="off")
    st.caption("90-day range and warnings: forecast module (in progress for 6 Nov).")

with tab_queue:
    st.subheader("Receipts that need you")
    st.caption("Everything else was matched by one rule to exactly one set of documents.")
    bank = pack.bank.set_index("txn_id")
    rows = []
    for m in matches.values():
        if m.business_id != biz or m.tier not in (SUGGEST, ASK):
            continue
        b = bank.loc[m.txn_id]
        rows.append({"txn_id": m.txn_id, "date": b.txn_date.date(), "amount": inr(abs(b.amount)),
                     "tier": m.tier, "rule": m.rule, "why": m.note,
                     "suggested documents": ", ".join(d for d, _ in m.docs), "narration": b.narration})
    q = pd.DataFrame(rows)
    if q.empty:
        st.success("Nothing waiting.")
    else:
        c = st.columns(3)
        c[0].metric("Suggestions", int((q.tier == SUGGEST).sum()))
        c[1].metric("Questions", int((q.tier == ASK).sum()))
        c[2].metric("Matched without a human", sum(1 for m in matches.values()
                                                    if m.business_id == biz and m.tier in ("AUTO", "NO_DOC")))
        gb = GridOptionsBuilder.from_dataframe(q)
        gb.configure_default_column(minWidth=120, resizable=True)
        gb.configure_column("why", minWidth=320)
        gb.configure_column("narration", minWidth=380)
        gb.configure_selection("single")
        gb.configure_pagination(paginationPageSize=20)
        grid = AgGrid(q, gridOptions=gb.build(), height=460, fit_columns_on_grid_load=False)
        sel = grid.get("selected_rows")
        if sel is not None and len(sel):
            r = sel.iloc[0] if isinstance(sel, pd.DataFrame) else sel[0]
            m = matches[r["txn_id"]]
            st.markdown(f"**{r['amount']} · {r['date']}** · {r['rule']}")
            st.info(m.note or "Check the suggested documents.")
            if m.docs:
                st.dataframe(pd.DataFrame(m.docs, columns=["document", "applied"]).assign(
                    applied=lambda d: d.applied.map(inr)), hide_index=True)
            st.button("Accept", disabled=True, help="Posting is wired in the next build; v1 is read-only.")

with tab_recv:
    items = open_items(pack, biz)
    st.subheader("Who owes you")
    st.dataframe(by_customer(items).assign(outstanding=lambda d: d.outstanding.map(inr)), hide_index=True)
    st.caption("TDS-short invoices count as paid in full, with TDS receivable (brief T3).")

with tab_ask:
    st.subheader("Ask")
    examples = ["Who owes me the most right now?", "Can I pay salaries on 1 October 2026?",
                "Should I take a loan to cover next month's shortfall?", "Send a reminder to everyone who owes me money."]
    pick = st.radio("Try", examples, index=None)
    q = st.text_input("Your question", value=pick or "")
    if q:
        a = copilot.ask(biz, q)
        (st.warning if a.intent not in ("FACT",) else st.success)(a.text)
        if a.sources:
            with st.expander(f"Sources ({len(a.sources)} rows)"):
                st.write(", ".join(a.sources[:60]))

with tab_scores:
    st.subheader("Scored against the answer keys")
    df = score_matches(pack, matches)
    st.dataframe(summary(df), hide_index=True)
    st.dataframe(score_categories(pack, copilot.cat), hide_index=True)
    st.caption("AUTO precision is the trust number: a wrong match hurts most (problem owner, 4 Nov).")
