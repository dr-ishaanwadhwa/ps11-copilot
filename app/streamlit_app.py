"""Cash Copilot front end (MVP v1): a light, read-only operating app for SME owners.

    streamlit run app/streamlit_app.py

Read-only and local-first:
- Formal books: bank statements, GST invoices, Tally bill-wise allocations.
- Cash book: on-device drawer (galla) cash, rokad and informal pending khata.
- Role-based access: Owner sees everything; Counter staff need the owner PIN for the cash book;
  the Accountant (CA) sees the cash book only when the owner shares it.

Layout: one sidebar (business, pages, role, language) and one page at a time.
Every number on screen comes from the copilot package; this file only arranges it.
"""
import html as _html
import os
import re
import urllib.parse

import altair as alt
import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder

from copilot import config
from copilot.answers import Copilot
from copilot.categorise import score_categories
from copilot.checks import import_report
from copilot.fmt import inr
from copilot.forecast import as_of, evaluate_holdout, simulate_forecast
from copilot.load import load_pack
from copilot.match import match_all
from copilot.match.audit import select_audit_sample
from copilot.match.engine import ASK, SUGGEST
from copilot.receivables import by_customer, open_items, overdue
from copilot.score import score_matches, summary
from copilot.vault import (
    Collection,
    VaultDB,
    cash_deposit_reporting_facts,
    compute_total_solvency,
    deposit_records_checklist,
    format_solvency_report,
    format_whatsapp_reminder,
    render_partial_view_notice,
)

st.set_page_config(
    page_title="Cash Copilot",
    page_icon=":material/account_balance_wallet:",
    layout="wide",
    initial_sidebar_state="auto",
)

PUBLIC = os.environ.get("COPILOT_PUBLIC") == "1"

# ── DESIGN TOKENS ─────────────────────────────────────────────────────────────
INK = "#17191C"
MUTED = "#545A63"
SUBTLE = "#646A72"
ACCENT = "#24509A"
NEG = "#A8261D"
FONT = "IBM Plex Sans"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Devanagari:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

html, body, .stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button,
.stApp td, .stApp th, .stApp div, .stApp span:not([data-testid="stIconMaterial"]) {
  font-family: 'IBM Plex Sans', 'IBM Plex Sans Devanagari', system-ui, -apple-system, 'Segoe UI', sans-serif;
}
.stApp { color: #17191C; -webkit-font-smoothing: antialiased; }

/* chrome */
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stDecoration"] { display: none; }
.stAppDeployButton, [data-testid="stAppDeployButton"] { display: none; }
[data-testid="stMainBlockContainer"], .block-container {
  max-width: 1200px; padding: 2.4rem 2.5rem 4rem;
}
@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"], .block-container { padding: 3.5rem 1rem 3rem; }
}

/* sidebar */
[data-testid="stSidebar"] { background: #F3F3F0; border-right: 1px solid #E5E5E0; }
[data-testid="stSidebarUserContent"] { padding-top: 0.25rem; }
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] { min-height: 40px; padding: 0 10px; border-radius: 8px; }
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover { background: #E9E9E5; }
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] p { font-size: 0.9rem; }
.st-key-nav, .st-key-nav_more { gap: 2px !important; }
.st-key-nav_more { border-top: 1px solid #E2E2DC; padding-top: 12px; margin-top: 4px; }
.st-key-side_bottom { border-top: 1px solid #E2E2DC; padding-top: 14px; margin-top: 8px; }
[data-testid="stSidebar"] [data-baseweb="select"] > div { background: #FFFFFF; border-color: #E2E2DC; }

/* inputs */
.stMain [data-baseweb="input"], .stMain [data-baseweb="base-input"],
.stMain [data-baseweb="select"] > div, div[role="dialog"] [data-baseweb="input"],
div[role="dialog"] [data-baseweb="base-input"] { background: #FFFFFF !important; }
[data-baseweb="input"], [data-baseweb="select"] > div { border-radius: 8px !important; }

/* buttons */
.stButton > button, .stFormSubmitButton > button { min-height: 44px; border-radius: 9px; font-weight: 500; padding: 0 18px; }
.stButton > button p, .stFormSubmitButton > button p { font-weight: 500; white-space: nowrap; }
.stButton > button[kind="secondary"], .stFormSubmitButton > button[kind="secondary"] { border-color: #DCDCD6; }
.stLinkButton > a { min-height: 40px; border-radius: 8px; border-color: #DCDCD6; color: #17191C; }
.stLinkButton > a p { font-weight: 500; font-size: 0.85rem; white-space: nowrap; }
.stLinkButton > a { padding: 0 10px; }
[class*="st-key-go_"] .stButton { display: flex; justify-content: flex-end; }
[class*="st-key-go_"] button { background: transparent !important; border: 0 !important; box-shadow: none !important;
  min-height: 40px; padding: 0 10px; color: #24509A !important; white-space: nowrap; }
[class*="st-key-go_"] button p { color: #24509A !important; font-weight: 500; white-space: nowrap; }
[class*="st-key-go_"] button:hover { background: #EDF1F8 !important; }

/* the "Ask about your cash" field in each page header */
.st-key-askfield [data-testid="stPageLink-NavLink"] { min-height: 44px; padding: 0 14px; border: 1px solid #DCDCD6;
  border-radius: 10px; background: #FFFFFF; }
.st-key-askfield [data-testid="stPageLink-NavLink"]:hover { border-color: #C2C2BB; background: #FFFFFF; }
.st-key-askfield [data-testid="stPageLink-NavLink"] p, .st-key-askfield [data-testid="stPageLink-NavLink"] span { color: #646A72; }

/* row lists */
[class*="st-key-row_"], [class*="st-key-krow_"], [class*="st-key-crow_"] { border-bottom: 1px solid #ECECE8; padding: 6px 0; gap: 0; }
.st-key-rows, .st-key-krows, .st-key-crows { border-top: 1px solid #ECECE8; gap: 0 !important; }

/* panels */
.st-key-cc_panel { background: #F7F7F4; border-radius: 12px; padding: 20px; }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 12px; }
[data-testid="stExpander"] details { border-color: #E2E2DC; border-radius: 10px; }
[data-testid="stExpander"] summary p { font-weight: 500; }
[data-testid="stAlert"] { border-radius: 10px; }

/* page parts (rendered with st.markdown) */
.cc-brand { display: flex; align-items: center; gap: 10px; padding: 4px 8px 2px; font-weight: 600; font-size: 15px; letter-spacing: -0.01em; }
.cc-title { font-size: 1.35rem; font-weight: 600; letter-spacing: -0.01em; line-height: 1.3; color: #17191C; }
.cc-sub { font-size: 0.85rem; color: #545A63; margin-top: 2px; }
.cc-rule { border-top: 1px solid #ECECE8; margin: 6px 0 10px; }
.cc-h2 { font-size: 1rem; font-weight: 600; color: #17191C; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.cc-label { font-size: 0.875rem; font-weight: 500; color: #545A63; }
.cc-hero { font-size: clamp(2.1rem, 4.5vw, 2.75rem); font-weight: 600; letter-spacing: -0.025em; line-height: 1.1;
  font-variant-numeric: tabular-nums; margin: 6px 0; color: #17191C; }
.cc-muted { font-size: 0.82rem; color: #545A63; }
.cc-note { font-size: 0.76rem; color: #646A72; }
.cc-num { font-variant-numeric: tabular-nums; }
.cc-tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 8px; }
.cc-tile { display: flex; flex-direction: column; gap: 3px; padding: 14px 16px; background: #F7F7F4; border-radius: 10px; }
.cc-tile .l { font-size: 0.76rem; color: #545A63; }
.cc-tile .v { font-size: 1.12rem; font-weight: 600; font-variant-numeric: tabular-nums; }
.cc-tile .s { font-size: 0.76rem; color: #646A72; display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.cc-tile.big .v { font-size: 1.3rem; }
.cc-tile.accent { background: #EDF1F8; }
.cc-tile.accent .l { color: #24509A; font-weight: 500; }
.cc-tile.accent .v { color: #1C407D; }
.cc-tile.accent .s { color: #2F4F86; }
.cc-tile.pos { background: #EAF4EE; }
.cc-tile.pos .l, .cc-tile.pos .v, .cc-tile.pos .s { color: #1A6E45; }
.cc-tile.warn { background: #FBF1DF; }
.cc-tile.warn .l, .cc-tile.warn .v, .cc-tile.warn .s { color: #7A4A00; }
.cc-tile.neg { background: #FBECEA; }
.cc-tile.neg .l, .cc-tile.neg .v, .cc-tile.neg .s { color: #A8261D; }
.cc-demo { font-size: 0.68rem; font-weight: 500; color: #545A63; border: 1px solid #D4D4CE; border-radius: 4px; padding: 0 5px; line-height: 1.55; }
.cc-tag { display: inline-block; font-size: 0.75rem; font-weight: 500; border-radius: 6px; padding: 1px 8px; line-height: 1.6; white-space: nowrap; }
.cc-tag.pos { color: #1A6E45; background: #EAF4EE; }
.cc-tag.warn { color: #8A5300; background: #FBF1DF; }
.cc-tag.info { color: #24509A; background: #EDF1F8; }
.cc-tag.neutral { color: #545A63; background: #F1F1EC; }
.cc-tag.neg { color: #A8261D; background: #FBECEA; }
.cc-status { display: flex; align-items: center; gap: 10px; padding: 10px 14px; border-radius: 10px; }
.cc-status .t { font-weight: 600; font-size: 0.9rem; }
.cc-status .d { font-size: 0.76rem; }
.cc-status.pos { background: #EAF4EE; color: #1A6E45; }
.cc-status.warn { background: #FBF1DF; color: #7A4A00; }
.cc-status.neg { background: #FBECEA; color: #A8261D; }
.cc-callout { display: flex; gap: 12px; align-items: flex-start; padding: 14px 16px; border-radius: 10px; }
.cc-callout .t { font-weight: 600; }
.cc-callout .d { font-size: 0.85rem; }
.cc-callout.pos { background: #EAF4EE; color: #1A6E45; }
.cc-callout.pos .d { color: #24543B; }
.cc-callout.warn { background: #FBF1DF; color: #4A3200; }
.cc-callout.neutral { background: #F4F4F1; color: #3F444B; }
.cc-row-title { font-weight: 500; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; color: #17191C; }
.cc-row-detail { font-size: 0.82rem; color: #545A63; }
.cc-amount { font-weight: 600; font-variant-numeric: tabular-nums; text-align: right; }
.cc-colhead { display: grid; gap: 16px; font-size: 0.75rem; color: #646A72; padding: 4px 0; }
.cc-dl { display: flex; flex-direction: column; border-top: 1px solid #ECECE8; margin: 0; }
.cc-dl > div { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; padding: 10px 0;
  border-bottom: 1px solid #ECECE8; }
.stApp .cc-dl dt { color: #545A63; font-weight: 400; margin: 0; padding: 0; }
.stApp .cc-dl dd { margin: 0; padding: 0; font-weight: 500; font-variant-numeric: tabular-nums; text-align: right; }
.cc-figs { display: flex; flex-wrap: wrap; gap: 16px 48px; margin: 0; }
.stApp .cc-figs dt { font-size: 0.82rem; color: #545A63; font-weight: 400; margin: 0; padding: 0; }
.stApp .cc-figs dd { margin: 0; padding: 0; font-size: 1.7rem; font-weight: 600; letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums; }
.cc-scroll { overflow-x: auto; }
.cc-table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; font-size: 0.85rem; }
.cc-table th { font-size: 0.75rem; font-weight: 500; color: #646A72; text-align: right; padding: 8px 10px;
  border-bottom: 1px solid #E2E2DC; white-space: nowrap; }
.cc-table td { text-align: right; padding: 12px 10px; border-bottom: 1px solid #ECECE8; vertical-align: top; }
.stApp .cc-table th, .stApp .cc-table td { border-left: 0; border-right: 0; border-top: 0; background: transparent; }
.stApp .cc-table tr { border: 0; background: transparent; }
.cc-table th:first-child, .cc-table td:first-child { text-align: left; padding-left: 0; }
.cc-table td:first-child { font-weight: 500; white-space: nowrap; }
.cc-table tr.hl td { background: #F7F7F4; }
.cc-table tr.hl td:first-child { padding-left: 8px; }
.cc-table .range { display: block; font-size: 0.75rem; color: #646A72; }
.cc-table .up { color: #1A6E45; }
.cc-table .down { color: #A8261D; }
.cc-mono { font-family: 'IBM Plex Mono', ui-monospace, monospace !important; }
.cc-narr { padding: 10px 12px; background: #F7F7F4; border-radius: 8px; font-size: 0.78rem; line-height: 1.6;
  color: #3F444B; overflow-wrap: anywhere; }
.cc-legend { display: flex; flex-wrap: wrap; gap: 6px 18px; font-size: 0.76rem; color: #545A63; }
.cc-legend span { display: inline-flex; align-items: center; gap: 6px; }
.cc-steps { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin-bottom: 8px; }
.cc-steps .bar { height: 3px; border-radius: 2px; background: #E2E2DC; margin-bottom: 8px; }
.cc-steps .on .bar { background: #24509A; }
.cc-steps .n { font-size: 0.75rem; color: #646A72; }
.cc-steps .lbl { font-size: 0.82rem; color: #545A63; }
.cc-steps .cur .lbl { font-weight: 600; color: #17191C; }
.cc-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 12px; color: #3F444B; }
.stApp .cc-list li { display: flex; gap: 10px; margin: 0; padding: 0; font-size: 0.9rem; line-height: 1.5; }
.stApp .cc-list.sm li { font-size: 0.84rem; }
.cc-list svg { flex: none; margin-top: 2px; }
.cc-side-note { display: flex; gap: 8px; align-items: flex-start; padding: 0 8px; font-size: 0.75rem; line-height: 1.45; color: #646A72; }
.cc-lock { display: grid; place-items: center; width: 40px; height: 40px; border-radius: 10px; background: #F4F4F1; }
</style>
""", unsafe_allow_html=True)


def H(markup: str) -> None:
    """Render a trusted HTML fragment. Collapsing newlines keeps Markdown from reading indents as code."""
    st.markdown(re.sub(r"\n\s*", " ", markup).strip(), unsafe_allow_html=True)


def esc(value) -> str:
    return _html.escape(str(value))


def svg(path: str, size: int = 16, color: str = "currentColor", width: float = 2) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
            f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{path}</svg>')


ICON_CHECK = '<path d="m5 12.5 4.5 4.5L19 7.5"></path>'
ICON_CHECK_CIRCLE = '<circle cx="12" cy="12" r="9"></circle><path d="m8 12.3 2.7 2.7L16 9.5"></path>'
ICON_ALERT = '<path d="M12 4 21 19.5H3z"></path><path d="M12 10v4.5"></path><path d="M12 17.4v.1"></path>'
ICON_LOCK = '<rect x="5" y="11" width="14" height="9.5" rx="2"></rect><path d="M8 11V7.5a4 4 0 0 1 8 0V11"></path>'
ICON_EYE = '<path d="M2.5 12s3.5-6.5 9.5-6.5S21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"></path><circle cx="12" cy="12" r="2.8"></circle>'
ICON_NEVER = '<circle cx="12" cy="12" r="8.5"></circle><path d="m6 18 12-12"></path>'
ICON_BOX_CHECK = '<rect x="4" y="4" width="16" height="16" rx="3"></rect><path d="m8.5 12 2.5 2.5 4.5-5"></path>'
ICON_SHIELD = '<path d="M12 3.5 19.5 6v5.5c0 4.3-3.1 7.6-7.5 9-4.4-1.4-7.5-4.7-7.5-9V6z"></path>'
LOGO = ('<svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true"><rect width="24" height="24" rx="6" fill="#17191C"></rect>'
        '<rect x="6" y="7.5" width="12" height="2.2" rx="1.1" fill="#FFFFFF"></rect>'
        '<rect x="6" y="11" width="12" height="2.2" rx="1.1" fill="#FFFFFF" opacity="0.55"></rect>'
        '<rect x="6" y="14.5" width="7" height="2.2" rx="1.1" fill="#FFFFFF"></rect></svg>')


def tag(text: str, tone: str = "neutral") -> str:
    return f'<span class="cc-tag {tone}">{esc(text)}</span>'


DEMO = '<span class="cc-demo">Demo</span>'


def tile(label: str, value: str, sub: str = "", tone: str = "") -> str:
    sub_html = f'<span class="s">{sub}</span>' if sub else ""
    return (f'<div class="cc-tile {tone}"><span class="l">{esc(label)}</span>'
            f'<span class="v">{esc(value)}</span>{sub_html}</div>')


def tiles(*items: str) -> None:
    H(f'<div class="cc-tiles">{"".join(items)}</div>')


def lakh(amount: float) -> str:
    return f"₹{amount / 100_000:.2f} lakh"


# ── DATA (cached once per server) ────────────────────────────────────────────
@st.cache_resource(show_spinner="Reading the data pack, matching every line and opening the cash book…")
def boot():
    pack = load_pack()
    matches = match_all(pack)
    copilot = Copilot(pack)
    vault = VaultDB(in_memory=True)
    vault.seed_from_pack(pack)
    return pack, matches, copilot, vault


pack, matches, copilot, vault = boot()


@st.cache_resource(show_spinner="Running the 90-day forecast…")
def forecast_for(business: str):
    return simulate_forecast(as_of(pack, config.HOLDOUT_START), business)


@st.cache_resource(show_spinner="Scoring the forecast on the holdout…")
def holdout_scores():
    return evaluate_holdout(pack)


@st.cache_resource(show_spinner="Scoring matches against the answer keys…")
def match_scores():
    return score_matches(pack, matches)


@st.cache_resource(show_spinner=False)
def data_report():
    return import_report(pack)


@st.cache_resource(show_spinner=False)
def weekly_audit_ids() -> set:
    latest_week = pack.bank["txn_date"].max().strftime("%G-W%V")
    return set(select_audit_sample(matches, pack.bank, latest_week))


def queue_counts(business: str) -> dict:
    counts = {SUGGEST: 0, ASK: 0, "auto": 0}
    for m in matches.values():
        if m.business_id != business:
            continue
        if m.tier in (SUGGEST, ASK):
            counts[m.tier] += 1
        elif m.tier in ("AUTO", "NO_DOC"):
            counts["auto"] += 1
    return counts


# ── SESSION DEFAULTS ─────────────────────────────────────────────────────────
ROLES = ["Owner", "Counter staff", "Accountant (CA)"]
# Sidebar choices live in plain session keys so a page switch can never reset them
# (otherwise a Counter staff session could briefly render with the Owner's view).
st.session_state.setdefault("biz_choice", list(config.BUSINESSES)[0])
st.session_state.setdefault("role_choice", ROLES[0])
st.session_state.setdefault("lang_choice", "English")
st.session_state.setdefault("share_cash_book", True)
st.session_state.setdefault("onboarding_step", 1)
st.session_state.setdefault("ask_q", None)

TIER_LABEL = {SUGGEST: "Suggestion", ASK: "Question"}
RULE_LABEL = {
    "EXACT": "Exact amount", "EXACT_BILL": "Exact bill amount", "EXACT_AMBIGUOUS": "Same amount on several invoices",
    "WHO_PAID": "Payer unknown", "NO_RULE": "No rule fits", "CLUBBED": "Several invoices together",
    "CLUBBED_BILLS": "Several bills together", "ON_ACCOUNT": "Part payment", "ROUND_OFF": "Round-off",
    "CASH_DEPOSIT": "Cash deposit", "BOUNCED": "Bounced payment",
}
ASK_CHIPS = [
    "Can I pay salaries on 1 October 2026?",
    "Who owes me the most?",
    "Should I take a loan to cover next month's shortfall?",
    "Send a reminder to everyone who owes me money.",
    "Explain my cash position in Hindi.",
    "What is my worst cash dip in the next 90 days?",
]


def go(label: str, key: str, page, ask: str | None = None) -> None:
    """A link-styled button that opens another page (and, for Ask, the question to answer)."""
    if st.button(label, key=f"go_{key}", icon=":material/arrow_forward:"):
        if ask:
            st.session_state["ask_q"] = ask
            st.session_state["ask_prefill"] = ask
        st.switch_page(page)


def page_header(title: str, subtitle: str, right=None) -> None:
    left, rgt = st.columns([3, 2], vertical_alignment="center")
    with left:
        H(f'<div class="cc-title" role="heading" aria-level="1">{esc(title)}</div>'
          f'<div class="cc-sub">{esc(subtitle)}</div>')
    with rgt:
        if right is not None:
            right()
        else:
            with st.container(key="askfield"):
                st.page_link(PAGES["ask"], label="Ask about your cash…", icon=":material/search:",
                             use_container_width=True)
    H('<div class="cc-rule"></div>')


def section(title_html: str, link: tuple | None = None) -> None:
    if link is None:
        H(f'<div class="cc-h2" role="heading" aria-level="2">{title_html}</div>')
        return
    a, b = st.columns([1, 1], vertical_alignment="center")
    with a:
        H(f'<div class="cc-h2" role="heading" aria-level="2" style="white-space:nowrap">{title_html}</div>')
    with b:
        go(*link)


def answer_galla() -> float:
    """Drawer cash passed to answers; withheld when the viewer sees formal books only."""
    if showing_partial_view:
        return 0.0
    g = vault.get_latest_galla(biz)
    return g.counted_cash if g else 0.0


# ── PAGE: OVERVIEW ───────────────────────────────────────────────────────────
def page_overview():
    page_header("Overview", f"Namaste, {BIZ_NAME}. Your position on {config.AS_OF:%d %b %Y}.")
    bal, _ = copilot.closing_balance(biz)
    limit = copilot.credit_limit(biz)
    items = open_items(pack, biz)

    if showing_partial_view:
        render_partial_view_notice()
        H('<div class="cc-label">Formal cash position, bank alone</div>')
        parts = [tile(f"Bank balance, {config.AS_OF:%d %b %Y}", inr(bal))]
        if limit:
            parts.append(tile("Cash-credit headroom", inr(bal + limit), f"Sanctioned limit {esc(inr(limit))}"))
        parts.append(tile("Formal receivables", inr(items.outstanding.sum()),
                          f"{len(overdue(items))} invoices more than 60 days late"))
        tiles(*parts)
        H('<div class="cc-note">Formal books only. Cash drawer and informal khata balances are not included.</div>')
    else:
        galla = vault.get_latest_galla(biz)
        khata = vault.get_khata_summary(biz)
        galla_demo = bool(galla and galla.is_demo)
        khata_demo = any(getattr(a, "is_demo", False) for a in khata["accounts"])

        hero_box, eq_box, ctrl_box = st.container(), st.container(), st.container()
        with ctrl_box:
            c1, c2 = st.columns([2, 3], vertical_alignment="center")
            with c1:
                if is_owner:
                    pct = st.slider("Khata collection assumption", min_value=50, max_value=100,
                                    value=int(round(config.KHATA_COLLECTION_ASSUMPTION * 100)), step=5,
                                    format="%d%%", help="Adjustable informal khata recovery expectation")
                    alpha = pct / 100
                else:
                    alpha = config.KHATA_COLLECTION_ASSUMPTION
            with c2:
                if galla_demo or khata_demo:
                    H('<div class="cc-note" style="text-align:right">Drawer and khata figures include demo data, '
                      'not from the pilot pack.</div>')

        solvency = compute_total_solvency(pack, vault, biz, haircut_alpha=alpha)
        solv_rep = format_solvency_report(solvency)
        runway = solvency.true_cash_runway_inr
        total_liquid = solvency.net_bank_liquidity + solvency.galla_cash
        unused_limit = max(0.0, solvency.cc_limit - solvency.cc_drawn)

        with hero_box:
            if solvency.cc_limit > 0:
                hero_sub = (f"Bank headroom {inr(solvency.net_bank_liquidity)} (balance {inr(solvency.bank_balance)} "
                            f"plus the unused {inr(unused_limit)} cash-credit limit) and {inr(solvency.galla_cash)} "
                            f"counted in the drawer.")
            else:
                hero_sub = (f"Bank balance {inr(solvency.bank_balance)} and {inr(solvency.galla_cash)} "
                            f"counted in the drawer.")
            headline = solv_rep["headline"]
            s_title, _, s_detail = headline.partition(":")
            tone = "pos" if runway > 0 else "neg"
            if solvency.is_false_insolvency:
                tone = "warn"
            s_icon = ICON_CHECK_CIRCLE if tone == "pos" else ICON_ALERT
            a, b = st.columns([3, 2], vertical_alignment="bottom")
            with a:
                H(f'<div class="cc-label">Cash you can use today</div><div class="cc-hero">{esc(inr(total_liquid))}</div>'
                  f'<div class="cc-muted">{esc(hero_sub)}</div>')
            with b:
                H(f'<div class="cc-status {tone}">{svg(s_icon, 18)}<span style="display:flex;flex-direction:column">'
                  f'<span class="t">{esc(s_title.strip())}</span><span class="d">{esc(s_detail.strip())}</span></span></div>')

        with eq_box:
            months = runway / max(solvency.total_commitments, 1.0)
            khata_sub = (f"{int(round(alpha * 100))}% of {esc(inr(solvency.informal_receivables))} {DEMO if khata_demo else ''}"
                         if solvency.informal_receivables else "No informal khata")
            tiles(
                tile("Bank balance" if not solvency.cc_drawn else "Bank balance less overdraft",
                     inr(solvency.bank_balance - solvency.cc_drawn), f"Closing, {config.AS_OF:%d %b}"),
                tile("+ Cash in drawer", inr(solvency.galla_cash),
                     f"{esc(galla.status_label) if galla else 'Not counted'} {DEMO if galla_demo else ''}"),
                tile("+ Khata you expect back", inr(solvency.total_expected_inflows), khata_sub),
                tile("− Due in next 30 days", inr(solvency.total_commitments), "Salaries, open bills and khata you owe"),
                tile("= Your own-cash buffer", inr(runway), f"About {months:.1f} months of commitments",
                     "accent" if runway >= 0 else "neg"),
            )

    st.write("")
    section("Needs you today")
    counts = queue_counts(biz)
    cust = by_customer(items)
    late = cust[cust.oldest_days >= 45]
    with st.container(key="rows"):
        sal = copilot.can_pay_salaries(biz, galla_cash=answer_galla())
        n = sal.numbers
        if n["yes"]:
            title = f'Salaries on 1 Oct are covered {tag("Covered", "pos")}'
        else:
            title = f'Salaries on 1 Oct need a plan {tag("Check", "warn")}'
        detail = f"September payroll was {inr(n['salary'])}. "
        detail += (f"Headroom of {inr(n['headroom'])} stays clear of the cash-credit limit." if limit
                   else f"The 30 Sep balance is {inr(n['closing_balance'])}.")
        _action_row("salary", title, detail, "See the answer", PAGES["ask"], ask=ASK_CHIPS[0])
        if len(late):
            _action_row("late", f'{len(late)} customers are more than 45 days overdue '
                                 f'{tag(inr(late.outstanding.sum()), "warn")}',
                        "Start with the largest. Each reminder opens as a WhatsApp draft for you to send.",
                        "Open chasing list", PAGES["recv"])
        waiting = counts[SUGGEST] + counts[ASK]
        if waiting:
            _action_row("review", f"{waiting:,} receipts need a decision",
                        f"{counts[SUGGEST]:,} suggested matches and {counts[ASK]:,} questions. "
                        f"Another {counts['auto']:,} were matched automatically.",
                        "Start review", PAGES["review"])
        _action_row("slips", "Record today's collection slips",
                    "Salesman slips let cash deposits link to the right shop invoices.",
                    "Record slips", PAGES["cash"])

    st.write("")
    left, right = st.columns([2, 1], gap="large")
    with left:
        section("90-day forecast", ("Open forecast", "forecast", PAGES["forecast"]))
        fc = forecast_for(biz)
        if fc.warnings:
            H(f'<div class="cc-tag warn">{len(fc.warnings)} shortfall warning{"s" if len(fc.warnings) > 1 else ""}</div>')
        else:
            H(f'<div class="cc-row-title" style="color:#1A6E45;font-size:0.85rem">{svg(ICON_CHECK, 16, width=2.2)}'
              f'No shortfall projected</div>')
        if fc.daily_points:
            df = pd.DataFrame([{"Date": p.date, "p10": p.balance_p10, "p50": p.balance_p50, "p90": p.balance_p90}
                               for p in fc.daily_points])
            base = alt.Chart(df)
            x = alt.X("Date:T", title=None, axis=alt.Axis(format="%b", tickCount="month", grid=False, domain=False,
                                                          ticks=False, labelColor=SUBTLE, labelPadding=6))
            band = base.mark_area(color=ACCENT, opacity=0.12).encode(
                x=x, y=alt.Y("p10:Q", axis=None, scale=alt.Scale(zero=False)), y2="p90:Q")
            line = base.mark_line(color=ACCENT, strokeWidth=2).encode(x="Date:T", y="p50:Q")
            chart = (band + line).properties(height=150).configure(font=FONT).configure_view(strokeWidth=0)
            st.altair_chart(chart, use_container_width=True, theme=None)
            low = df.loc[df.p50.idxmin()]
            closing = fc.monthly_forecasts[-1] if fc.monthly_forecasts else None
            closing_txt = (f" {pd.Timestamp(closing.month + '-01'):%B} closes near {inr(closing.closing_balance_p50)}."
                           if closing else "")
            H(f'<div class="cc-muted">Lowest expected balance is {esc(inr(low.p50))} on {pd.Timestamp(low.Date):%d %b}.'
              f'{esc(closing_txt)} The shaded band is the likely range.</div>')
    with right:
        section("Your data, checked", ("Details", "quality", PAGES["quality"]))
        rep = data_report()
        ties = "Yes, no breaks" if rep["balance_ties"] else f"{rep['balance_breaks']} breaks"
        H(f'<dl class="cc-dl">'
          f'<div><dt>Bank lines read</dt><dd>{rep["bank_lines"]:,}</dd></div>'
          f'<div><dt>Duplicates skipped</dt><dd>{rep["duplicates_skipped"]:,}</dd></div>'
          f'<div><dt>Running balances tie</dt><dd style="color:{"#1A6E45" if rep["balance_ties"] else NEG}">{ties}</dd></div>'
          f'<div><dt>Invoices and claims</dt><dd>{rep["documents"]:,}</dd></div></dl>')


def _action_row(key: str, title_html: str, detail: str, label: str, page, ask: str | None = None) -> None:
    with st.container(key=f"row_{key}"):
        a, b = st.columns([5, 1.6], vertical_alignment="center")
        with a:
            H(f'<div class="cc-row-title">{title_html}</div><div class="cc-row-detail">{esc(detail)}</div>')
        with b:
            go(label, key, page, ask)


# ── PAGE: CASH BOOK ──────────────────────────────────────────────────────────
@st.dialog("Close the day")
def day_close_dialog():
    H('<div class="cc-muted">Takes about a minute. Saved in your cash book on this device.</div>')
    with st.form("galla_close_form", border=False):
        c1, c2 = st.columns(2)
        c1.number_input("Opening till cash (₹)", value=10000.0, step=500.0)
        c2.number_input("Today's cash takings (₹)", value=25000.0, step=1000.0)
        c1.number_input("Cash expenses paid (₹)", value=2500.0, step=100.0, help="Hamali, petty and other cash expenses")
        c2.number_input("Cash banked into account (₹)", value=20000.0, step=1000.0)
        c1.number_input("Physical count at close (₹)", value=12500.0, step=500.0)
        c2.text_input("Notes", value="Routine daily close")
        submitted = st.form_submit_button("Record in cash book", type="primary")
    if submitted:
        st.session_state["toast"] = "Recorded locally in Cash Book. Balance updated."
        st.rerun()


@st.dialog("Record collection slips")
def collections_dialog():
    H('<div class="cc-muted">What each salesman collected from shops. Used to match cash deposits to invoices.</div>')
    with st.form("collections_today_form", border=False):
        c1, c2 = st.columns(2)
        col_date = c1.date_input("Collection date", value=pd.Timestamp("2026-09-30"))
        salesman = c2.text_input("Salesman", value="Ramesh K.")
        rows = []
        for i, (shop, amount) in enumerate([("Laxmi Kirana Stores", 15000.0), ("", 0.0), ("", 0.0)], start=1):
            a, b = st.columns([2, 1])
            rows.append((a.text_input(f"Shop {i}" + (" (optional)" if i > 1 else ""), value=shop),
                         b.number_input(f"Amount {i} (₹)", value=amount, step=500.0)))
        col_sub = st.form_submit_button("Record collections", type="primary")
    if col_sub:
        for s, a in rows:
            if s.strip() and a > 0:
                vault.record_collection(Collection(biz, pd.Timestamp(col_date), s.strip(), a, salesman))
        st.session_state["toast"] = "Collections recorded in local vault."
        st.rerun()


def page_cash_book():
    def share_toggle():
        if is_owner:
            st.toggle("Share my cash book with my accountant", key="_share_widget",
                      value=st.session_state["share_cash_book"],
                      help="When off, the Accountant (CA) role sees formal books only.",
                      on_change=lambda: st.session_state.update(share_cash_book=st.session_state["_share_widget"]))
        else:
            with st.container(key="askfield"):
                st.page_link(PAGES["ask"], label="Ask about your cash…", icon=":material/search:",
                             use_container_width=True)

    page_header("Cash book", "Drawer cash and informal khata. Kept on this device only.", right=share_toggle)
    if showing_partial_view:
        render_partial_view_notice()

    owner_pin = os.environ.get("COPILOT_OWNER_PIN")
    pin_is_default = owner_pin is None
    expected_pin = owner_pin if owner_pin is not None else "0000"

    can_view_cash_book = False
    if is_owner:
        can_view_cash_book = True
    elif is_accountant:
        if share_cash_book:
            can_view_cash_book = True
        else:
            st.info("The owner has not shared the cash book with the accountant.")
    elif is_counter_staff:
        a, b = st.columns([1, 14])
        with a:
            H(f'<div class="cc-lock">{svg(ICON_LOCK, 18, "#3F444B")}</div>')
        with b:
            H('<div class="cc-h2">Cash book is locked</div>'
              '<div class="cc-muted">Owner PIN is required to view the cash book.</div>')
            pin_prompt_label = "Demo PIN: 0000" if pin_is_default else "Enter owner PIN"
            c, _ = st.columns([1, 2])
            staff_pin = c.text_input("Enter Owner PIN to unlock", type="password", help=pin_prompt_label)
            if staff_pin:
                if staff_pin == expected_pin:
                    can_view_cash_book = True
                else:
                    st.error("Incorrect PIN.")
            elif pin_is_default:
                H('<div class="cc-note">Demo PIN: 0000</div>')

    if not can_view_cash_book:
        return

    left, right = st.columns([2, 1], gap="large")
    with left:
        latest_g = vault.get_latest_galla(biz)
        demo = DEMO if latest_g and latest_g.is_demo else ""
        when = f"{esc(latest_g.notes)} · {latest_g.date:%d %b %Y}" if latest_g else ""
        H(f'<div style="display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;align-items:center">'
          f'<div class="cc-h2" role="heading" aria-level="2">Today\'s drawer {demo}</div>'
          f'<div class="cc-note">{when}</div></div>')
        if latest_g:
            status_sub = "Ties to the book" if latest_g.is_balanced else f"{esc(inr(latest_g.drift))} drift"
            tiles(
                tile("Counted in drawer", inr(latest_g.counted_cash), tone="big"),
                tile("Expected from book", inr(latest_g.expected_cash), tone="big"),
                tile("Till status", latest_g.status_label, status_sub, "pos big" if latest_g.is_balanced else "warn big"),
            )
        else:
            H('<div class="cc-muted">No drawer count recorded yet.</div>')
        b1, b2, _ = st.columns([1, 1.4, 1.6])
        if b1.button("Close the day", type="primary", key="open_day_close", use_container_width=True):
            day_close_dialog()
        if b2.button("Record collection slips", key="open_slips", use_container_width=True):
            collections_dialog()

        st.write("")
        khata_data = vault.get_khata_summary(biz)
        accounts = khata_data["accounts"]
        k_demo = DEMO if any(getattr(acc, "is_demo", False) for acc in accounts) else ""
        totals = (f'They owe you <b class="cc-num">{esc(inr(khata_data["receivables"]))}</b> · you owe '
                  f'<b class="cc-num">{esc(inr(khata_data["payables"]))}</b>') if accounts else ""
        H(f'<div style="display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;align-items:baseline">'
          f'<div class="cc-h2" role="heading" aria-level="2">Pending khata {k_demo}</div>'
          f'<div class="cc-muted">{totals}</div></div>')
        if accounts:
            H('<div class="cc-colhead" style="grid-template-columns:2.6fr 1.1fr 1.2fr 1.9fr">'
              '<span>Party</span><span>Open for</span><span style="text-align:right">Balance</span><span></span></div>')
            with st.container(key="krows"):
                for i, acc in enumerate(accounts):
                    rem = format_whatsapp_reminder(acc, BIZ_NAME, upi_handle="payment@bank")
                    with st.container(key=f"krow_{i}"):
                        c1, c2, c3, c4 = st.columns([2.6, 1.1, 1.2, 1.9], vertical_alignment="center")
                        sub = ""
                        if acc.balance_due < 0:
                            sub = '<div class="cc-row-detail">You owe them</div>'
                        if rem["limitation_warning"]:
                            sub = f'<div class="cc-row-detail">{esc(rem["limitation_warning"])}</div>'
                        flag = tag("Over 30 months", "warn") if acc.is_limitation_alert else ""
                        c1.markdown(f'<div class="cc-row-title">{esc(acc.party_name)} {flag}</div>{sub}',
                                    unsafe_allow_html=True)
                        c2.markdown(f'<div class="cc-muted">{acc.months_open} months</div>', unsafe_allow_html=True)
                        color = f"color:{NEG}" if acc.balance_due < 0 else ""
                        c3.markdown(f'<div class="cc-amount" style="{color}">{esc(inr(acc.balance_due))}</div>',
                                    unsafe_allow_html=True)
                        c4.link_button("WhatsApp draft", rem["wa_link"], icon=":material/send:", use_container_width=True)
            H('<div class="cc-note">Drafts open in WhatsApp. Nothing is sent until you press send there.</div>')
        else:
            H('<div class="cc-muted">No informal khata records for this business.</div>')

    with right:
        with st.container(key="cc_panel"):
            ytd_deposits = vault.get_ytd_cash_deposits(biz)
            is_seeded = (biz in ("SME-1", "SME-3")) or (ytd_deposits > 0)
            facts_res = cash_deposit_reporting_facts(ytd_deposits)
            checklist = deposit_records_checklist()
            items_html = "".join(f'<li>{svg(ICON_BOX_CHECK, 16, MUTED)}{esc(doc)}</li>' for doc in checklist["documents"])
            H(f'<div class="cc-h2" role="heading" aria-level="2">Cash deposits this year {DEMO if is_seeded else ""}</div>'
              f'<div class="cc-hero" style="font-size:1.6rem">{esc(inr(ytd_deposits))}</div>'
              f'<div class="cc-muted" style="color:#3F444B">{esc(facts_res.message)}</div>'
              f'<div class="cc-note" style="margin-top:8px">{esc(facts_res.citation)}</div>'
              f'<div style="border-top:1px solid #E2E2DC;margin:14px 0 10px"></div>'
              f'<div style="font-weight:600;font-size:0.85rem;margin-bottom:10px">Records checklist before depositing cash</div>'
              f'<ul class="cc-list sm">{items_html}</ul>'
              f'<div class="cc-note" style="margin-top:12px">{esc(checklist["referral"])}</div>')


# ── PAGE: FORECAST (FR-FC-1, FR-FC-2) ────────────────────────────────────────
def page_forecast():
    page_header("Forecast", f"90 days from {config.HOLDOUT_START.day} {config.HOLDOUT_START:%b %Y}, "
                            f"trained only on data before that date.")
    if showing_partial_view:
        render_partial_view_notice()

    fc_res = forecast_for(biz)

    # Shortfall warning cards (D50, D40)
    if fc_res.warnings:
        for w in fc_res.warnings:
            tone = "warn"
            H(f'<div class="cc-callout {tone}">{svg(ICON_ALERT, 18, "#8A5300")}<div>'
              f'<div class="t" style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;color:#17191C">Early shortfall warning '
              f'{tag(w.level.title(), "warn")}</div><div class="d">{esc(w.message)}</div></div></div>')
    else:
        H(f'<div class="cc-callout pos">{svg(ICON_CHECK_CIRCLE, 20)}<div><div class="t">No shortfall projected</div>'
          f'<div class="d">Your balance stays above the credit limit, salary days and your cash floor for all 90 days.'
          f'</div></div></div>')

    if fc_res.daily_points:
        st.write("")
        a, b = st.columns([1, 2], vertical_alignment="center")
        with a:
            section("Projected bank balance")
        limit_amt = copilot.credit_limit(biz)
        with b:
            legend = (f'<span><i style="width:14px;height:10px;border-radius:2px;background:rgba(36,80,154,0.16)"></i>Likely range (P10–P90)</span>'
                      f'<span><i style="width:16px;height:2px;background:{ACCENT}"></i>Most likely (P50)</span>')
            if limit_amt:
                legend += f'<span><i style="width:16px;border-top:2px dashed {NEG}"></i>Cash-credit limit</span>'
            H(f'<div class="cc-legend" style="justify-content:flex-end">{legend}</div>')

        df_daily = pd.DataFrame([
            {"Date": p.date, "p10": p.balance_p10, "p50": p.balance_p50, "p90": p.balance_p90,
             "p10_txt": inr(p.balance_p10), "p50_txt": inr(p.balance_p50), "p90_txt": inr(p.balance_p90)}
            for p in fc_res.daily_points
        ])
        lakh_expr = "(datum.value < 0 ? '−₹' : '₹') + format(abs(datum.value) / 100000, ',.0f') + 'L'"
        x = alt.X("Date:T", title=None, axis=alt.Axis(format="%d %b", tickCount="month", grid=False, domain=False,
                                                      tickColor="#E2E2DC", labelColor=SUBTLE, labelPadding=6))
        y_axis = alt.Axis(labelExpr=lakh_expr, gridColor="#ECECE8", domain=False, ticks=False, labelColor=SUBTLE,
                          labelPadding=8, tickCount=5)
        band = alt.Chart(df_daily).mark_area(opacity=0.16, color=ACCENT).encode(
            x=x, y=alt.Y("p10:Q", title=None, axis=y_axis), y2="p90:Q",
            tooltip=[alt.Tooltip("Date:T", title="Date", format="%d %b %Y"),
                     alt.Tooltip("p10_txt:N", title="Worst case (P10)"),
                     alt.Tooltip("p50_txt:N", title="Most likely (P50)"),
                     alt.Tooltip("p90_txt:N", title="Optimistic (P90)")])
        line = alt.Chart(df_daily).mark_line(strokeWidth=2, color=ACCENT).encode(x="Date:T", y="p50:Q")
        low = df_daily.loc[[df_daily.p50.idxmin()]].assign(label=lambda d: "Lowest " + d["p50_txt"])
        low_pt = alt.Chart(low).mark_point(filled=True, fill="white", stroke=ACCENT, strokeWidth=2, size=70).encode(
            x="Date:T", y="p50:Q")
        low_txt = alt.Chart(low).mark_text(dy=22, fontSize=12, fontWeight=500, color=INK).encode(
            x="Date:T", y="p50:Q", text="label:N")
        layers = [band, line, low_pt, low_txt]
        if limit_amt:
            floor_df = pd.DataFrame([{"Floor": -limit_amt}])
            layers.append(alt.Chart(floor_df).mark_rule(strokeDash=[6, 5], color=NEG, strokeWidth=1.5).encode(y="Floor:Q"))
        chart = (alt.layer(*layers).properties(height=340)
                 .configure(font=FONT).configure_view(strokeWidth=0)
                 .configure_axis(labelFontSize=12))
        st.altair_chart(chart, use_container_width=True, theme=None)
        H('<div class="cc-note">Monte Carlo simulation calibrated without lookahead.</div>')

    st.write("")
    section("Month by month")
    rows = []
    for mf in fc_res.monthly_forecasts:
        month = pd.Timestamp(mf.month + "-01")
        out_range = (f'<span class="range">{esc(inr(mf.outflows_p10))} – {esc(inr(mf.outflows_p90))}</span>'
                     if round(mf.outflows_p10) != round(mf.outflows_p90) else "")
        net_cls = "up" if mf.net_p50 >= 0 else "down"
        net_txt = ("+" if mf.net_p50 >= 0 else "") + inr(mf.net_p50)
        rows.append(
            f'<tr><td>{month:%b %Y}</td>'
            f'<td>{esc(inr(mf.inflows_p50))}<span class="range">{esc(inr(mf.inflows_p10))} – {esc(inr(mf.inflows_p90))}</span></td>'
            f'<td>{esc(inr(mf.outflows_p50))}{out_range}</td>'
            f'<td class="{net_cls}">{esc(net_txt)}</td>'
            f'<td>{esc(inr(mf.min_balance_p50))}</td>'
            f'<td style="font-weight:600">{esc(inr(mf.closing_balance_p50))}</td></tr>')
    H('<div class="cc-scroll"><table class="cc-table" style="min-width:720px"><thead><tr>'
      '<th>Month</th><th>Expected inflows</th><th>Committed outflows</th><th>Net cash flow</th>'
      '<th>Lowest daily balance</th><th>Closing balance</th></tr></thead>'
      f'<tbody>{"".join(rows)}</tbody></table></div>'
      '<div class="cc-note" style="margin-top:6px">Most likely values (P50). Small figures show the likely range.</div>')

    st.write("")
    holdout_res = holdout_scores()
    with st.expander(f"How accurate is this forecast? {holdout_res.mape:.2%} average error on the holdout"):
        mape_label = f"{holdout_res.mape:.2%}"
        if holdout_res.mape > 0.182:
            mape_note = "worse than the simple 3-month average; kill metric (D31)"
        else:
            mape_note = "target ≤ 10%"
        H('<div class="cc-tiles">'
          + tile("Model error (MAPE) on the frozen holdout", mape_label,
                 f"{mape_note} · naive 3-month baseline {holdout_res.naive_mape:.2%}")
          + tile("Agency inflows error", f"{holdout_res.agency_inflow_mape:.2%}",
                 f"naive baseline {holdout_res.naive_agency_inflow_mape:.2%}")
          + tile("Paired bootstrap improvement (naive − model)", f"{holdout_res.bootstrap_diff_mean:+.2%}",
                 f"95% CI {holdout_res.bootstrap_diff_ci[0]:+.2%} to {holdout_res.bootstrap_diff_ci[1]:+.2%}")
          + tile("Holdout P10–P90 coverage", f"{holdout_res.coverage_p10_p90:.1%}", "of actuals fell inside the range")
          + tile("Holdout likely warnings", f"{holdout_res.false_alarms.get(biz, 0)}", "for this business")
          + '</div>')
        H('<div class="cc-note" style="margin-top:8px">Scored on the Jul–Sep 2026 holdout; data pack only.</div>')


# ── PAGE: REVIEW QUEUE ───────────────────────────────────────────────────────
def page_review():
    counts = queue_counts(biz)
    page_header("Review", f"Receipts that need you. {counts['auto']:,} others matched one rule to exactly one set "
                          f"of documents under strict Decision 60.")
    if showing_partial_view:
        render_partial_view_notice()

    bank = pack.bank.set_index("txn_id")
    rows = []
    for m in matches.values():
        if m.business_id != biz or m.tier not in (SUGGEST, ASK):
            continue
        b = bank.loc[m.txn_id]
        rows.append({"txn_id": m.txn_id, "date": b.txn_date.strftime("%Y-%m-%d"), "amount": inr(abs(b.amount)),
                     "type": TIER_LABEL.get(m.tier, m.tier), "tier": m.tier, "rule": m.rule, "why": m.note,
                     "suggested documents": ", ".join(d for d, _ in m.docs), "narration": b.narration})
    q = pd.DataFrame(rows)
    if q.empty:
        st.success("Nothing waiting.")
        return

    options = ["All", "Suggestions", "Questions"]
    sizes = {"All": len(q), "Suggestions": counts[SUGGEST], "Questions": counts[ASK]}
    choice = st.segmented_control("Show", options, default="All", key="queue_filter",
                                  format_func=lambda o: f"{o}  {sizes[o]:,}", label_visibility="collapsed") or "All"
    view = q if choice == "All" else q[q.tier == (SUGGEST if choice == "Suggestions" else ASK)]
    view = view.sort_values("date", ascending=False).reset_index(drop=True)

    left, right = st.columns([1.75, 1], gap="medium")
    with left:
        gb = GridOptionsBuilder.from_dataframe(view)
        gb.configure_default_column(resizable=True, sortable=True)
        for hidden in ("txn_id", "tier", "why", "suggested documents"):
            gb.configure_column(hidden, hide=True)
        gb.configure_column("date", header_name="Date", width=104, minWidth=96)
        gb.configure_column("amount", header_name="Amount", width=100, minWidth=90, type=["rightAligned"])
        gb.configure_column("type", header_name="Type", width=116, minWidth=112)
        gb.configure_column("rule", header_name="Rule", width=124, minWidth=104)
        gb.configure_column("narration", header_name="Bank narration", flex=1, minWidth=220)
        gb.configure_grid_options(autoSizeStrategy=None, rowHeight=44, headerHeight=40)
        gb.configure_selection("single")
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
        grid = AgGrid(
            view, gridOptions=gb.build(), height=560, fit_columns_on_grid_load=False, theme="alpine",
            key=f"queue_grid_{biz}_{choice}",
            custom_css={
                ".ag-root-wrapper": {"border": "1px solid #E2E2DC !important", "border-radius": "10px !important"},
                ".ag-header": {"background-color": "#FAFAF8 !important", "border-bottom-color": "#E2E2DC !important"},
                ".ag-header-cell-text": {"font-weight": "500 !important", "color": "#646A72 !important"},
                ".ag-row": {"border-color": "#ECECE8 !important", "font-size": "13px !important"},
                ".ag-row-selected": {"background-color": "#EDF1F8 !important"},
                ".ag-row-hover": {"background-color": "#F7F7F4 !important"},
                ".ag-cell-focus": {"border-color": "transparent !important"},
            },
        )
    sel = grid.get("selected_rows")
    if sel is not None and len(sel):
        txn_id = (sel.iloc[0] if isinstance(sel, pd.DataFrame) else sel[0])["txn_id"]
    else:
        txn_id = view.iloc[0]["txn_id"]

    with right:
        m = matches[txn_id]
        r = q[q.txn_id == txn_id].iloc[0]
        b = bank.loc[txn_id]
        is_audit = txn_id in weekly_audit_ids() or "audit miss" in (m.note or "")
        tone = "info" if m.tier == SUGGEST else "warn"
        with st.container(border=True):
            audit_tag = tag("Weekly audit sample", "neutral") if is_audit else ""
            H(f'<div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center">{tag(TIER_LABEL.get(m.tier, m.tier), tone)}'
              f'<span class="cc-muted">{esc(RULE_LABEL.get(m.rule, m.rule.replace("_", " ").title()))}</span>'
              f'<span class="cc-note cc-mono">{esc(m.rule)}</span>{audit_tag}</div>'
              f'<div class="cc-hero" style="font-size:1.75rem;margin:10px 0 2px">{esc(r["amount"])}</div>'
              f'<div class="cc-muted">{b.txn_date:%d %b %Y} · <span class="cc-mono">{esc(txn_id)}</span></div>')
            if is_audit:
                H('<div class="cc-note" style="margin-top:6px">Picked at random to check our automatic matches.</div>')
            H(f'<div class="cc-label" style="font-size:0.76rem;margin-top:14px">Why it\'s here</div>'
              f'<div style="margin-top:2px;font-size:0.92rem">{esc(m.note or "Check the suggested documents.")}</div>'
              f'<div class="cc-label" style="font-size:0.76rem;margin:14px 0 4px">Bank narration</div>'
              f'<div class="cc-narr cc-mono">{esc(b.narration)}</div>'
              f'<div class="cc-label" style="font-size:0.76rem;margin:14px 0 4px">Suggested documents</div>')
            if m.docs:
                doc_rows = "".join(f'<div><dt class="cc-mono" style="color:#17191C">{esc(d)}</dt><dd>{esc(inr(a))}</dd></div>'
                                   for d, a in m.docs)
                H(f'<dl class="cc-dl">{doc_rows}</dl>')
            else:
                H('<div class="cc-muted">No single document fits this receipt yet.</div>')
            st.button("Accept", disabled=True, use_container_width=True,
                      help="Posting is wired in the next build; v1 is read-only.")
            H('<div class="cc-note">Posting comes in the next build. This version is read-only.</div>')


# ── PAGE: RECEIVABLES ────────────────────────────────────────────────────────
def page_receivables():
    page_header("Receivables", f"Who owes you on formal invoices, as of {config.AS_OF:%d %b %Y}.")
    if showing_partial_view:
        render_partial_view_notice()

    items = open_items(pack, biz)
    cust_df = by_customer(items)
    H(f'<dl class="cc-figs">'
      f'<div><dt>Total outstanding</dt><dd>{esc(inr(items.outstanding.sum()))}</dd></div>'
      f'<div><dt>Open invoices</dt><dd>{len(items):,}</dd></div>'
      f'<div><dt>More than 60 days late</dt><dd style="color:#8A5300">{len(overdue(items)):,} invoices</dd></div></dl>')
    st.write("")

    filters = {
        "Over 45 days": cust_df[cust_df.oldest_days >= 45],
        "All customers": cust_df,
        "Over 30 months": cust_df[cust_df.oldest_days >= 900],
    }
    head = st.container()
    choice = st.segmented_control("Chasing filter", list(filters), default="Over 45 days", key="chase_filter",
                                  format_func=lambda o: f"{o}  {len(filters[o])}",
                                  label_visibility="collapsed") or "Over 45 days"
    filtered_cust = filters[choice]
    with head:
        H(f'<div class="cc-h2" role="heading" aria-level="2">Who to call this week</div>'
          f'<div class="cc-muted">Showing {len(filtered_cust)} customers owing {esc(inr(filtered_cust.outstanding.sum()))}. '
          f'Largest first.</div>')

    if filtered_cust.empty:
        H(f'<div style="display:flex;flex-direction:column;align-items:center;gap:6px;padding:48px 16px;text-align:center">'
          f'{svg(ICON_CHECK_CIRCLE, 28, SUBTLE, 1.6)}<div style="font-weight:500">No customers in this list</div>'
          f'<div class="cc-muted" style="max-width:420px">Balances older than 30 months can become hard to recover '
          f'under the Limitation Act. They will show here first.</div></div>')
    else:
        H('<div class="cc-colhead" style="grid-template-columns:3.2fr 1.2fr 1.4fr 1.7fr">'
          '<span>Customer</span><span>Oldest invoice</span><span style="text-align:right">Outstanding</span><span></span></div>')
        collections = vault.collection_records.get(biz, [])
        with st.container(key="crows"):
            for i, (_, c_row) in enumerate(filtered_cust.head(10).iterrows()):
                c_name = c_row["customer_name"]
                amt = c_row["outstanding"]
                oldest = int(c_row["oldest_days"])
                inv_count = int(c_row["invoices"])

                # Salesman protection: collected recently, not banked yet
                salesman_note = ""
                for col in collections:
                    if col.shop.strip().lower() in c_name.lower():
                        salesman_note = (f"Salesman {col.salesman} collected {inr(col.amount)} on "
                                         f"{col.date:%d %b}; not banked yet. Do not call.")
                        break

                with st.container(key=f"crow_{i}"):
                    c1, c2, c3, c4 = st.columns([3.2, 1.2, 1.4, 1.7], vertical_alignment="center")
                    note = (f'<div class="cc-row-detail" style="color:#1A6E45;display:flex;gap:6px">'
                            f'{svg(ICON_SHIELD, 14)}{esc(salesman_note)}</div>') if salesman_note else ""
                    c1.markdown(f'<div class="cc-row-title">{esc(c_name)}</div>'
                                f'<div class="cc-row-detail">{inv_count} open invoices</div>{note}', unsafe_allow_html=True)
                    badge = tag(f"{oldest} days", "warn" if oldest >= 45 else "neutral")
                    if oldest >= 900:
                        badge += " " + tag("30+ months (Sec 18)", "neg")
                    c2.markdown(badge, unsafe_allow_html=True)
                    c3.markdown(f'<div class="cc-amount">{esc(inr(amt))}</div>', unsafe_allow_html=True)
                    wa_text = (f"Namaste {c_name}, {BIZ_NAME} se namaskar. Aapka pichla bill {inr(amt)} ka baaki hai. "
                               f"Kripya check kar lijiye. UPI: kaveri@hdfcbank")
                    c4.link_button("WhatsApp draft", f"https://wa.me/?text={urllib.parse.quote(wa_text)}",
                                   icon=":material/send:", use_container_width=True)

    st.write("")
    with st.expander(f"Full ledger · {len(cust_df)} customers"):
        st.dataframe(
            by_customer(items).assign(outstanding=lambda d: d.outstanding.map(inr)),
            hide_index=True, use_container_width=True,
            column_config={"customer_name": "Customer", "outstanding": "Outstanding",
                           "invoices": "Open invoices", "oldest_days": "Oldest (days)"},
        )
    H('<div class="cc-note">TDS-short invoices count as paid in full, with TDS receivable recorded separately (brief T3).</div>')


# ── PAGE: ASK ────────────────────────────────────────────────────────────────
def _pick_chip():
    picked = st.session_state.get("ask_chip")
    if picked:
        st.session_state["ask_q"] = picked
        st.session_state["ask_typed"] = picked


def _submit_typed():
    typed = (st.session_state.get("ask_typed") or "").strip()
    if typed:
        st.session_state["ask_q"] = typed
        st.session_state["ask_chip"] = None


def page_ask():
    page_header("Ask Copilot", "Answers come from your books, with the rows they used. It explains; it never acts for you.",
                right=lambda: None)
    tab_ask = st.container()
    with tab_ask:
        if showing_partial_view:
            render_partial_view_notice()

        if "ask_prefill" in st.session_state:
            st.session_state["ask_typed"] = st.session_state.pop("ask_prefill")
        mid, _ = st.columns([3, 1.2])
        with mid:
            if not PUBLIC:
                with st.form("ask_form", border=False):
                    c1, c2 = st.columns([5, 1], vertical_alignment="bottom")
                    c1.text_input("Your question", key="ask_typed", placeholder="For example: who owes me the most?")
                    c2.form_submit_button("Ask", type="primary", use_container_width=True, on_click=_submit_typed)

            st.pills("Try one of these" if not PUBLIC else "Choose a question", ASK_CHIPS, key="ask_chip",
                     on_change=_pick_chip)
            if PUBLIC:
                H('<div class="cc-note">Typing your own question is switched off in this preview until our safety '
                  'checks pass.</div>')

            selected_q = st.session_state.get("ask_q")
            if selected_q:
                a = copilot.ask(biz, selected_q, galla_cash=answer_galla())
                if a.intent == "FACT":
                    label = f'<span class="cc-tag pos" style="display:inline-flex;gap:5px;align-items:center">' \
                            f'{svg(ICON_CHECK, 12, width=2.6)}From your books</span>'
                elif a.intent == "UNSUPPORTED":
                    label = tag("Not available yet", "neutral")
                elif a.intent == "NEEDS_CHIPS":
                    label = tag("Pick a question", "neutral")
                else:
                    label = tag("Outside what I do", "warn")
                H('<div class="cc-rule" style="margin:18px 0 16px"></div>'
                  f'<div style="display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;align-items:center">'
                  f'<div class="cc-h2">{esc(selected_q)}</div>{label}</div>'
                  f'<div style="font-size:1.02rem;line-height:1.65;margin-top:10px;text-wrap:pretty">{esc(a.text)}</div>')
                if a.sources:
                    with st.expander(f"Sources ({len(a.sources)} rows)"):
                        H(f'<div class="cc-mono" style="font-size:0.78rem;line-height:1.7">{esc(", ".join(a.sources[:60]))}</div>')


# ── PAGE: DATA QUALITY (scores) ──────────────────────────────────────────────
SCORE_LABELS = {
    "business": "Business", "lines_in_key": "Lines in key", "auto": "Automatic", "auto_precision": "Automatic correct",
    "straight_through_%": "Straight-through", "suggest": "Suggestions", "suggest_right_%": "Suggestions right",
    "ask": "Questions", "unmatched": "Unmatched", "explained_if_accepted_%": "Explained if accepted",
    "set": "Set", "lines": "Lines", "line_accuracy_%": "By line", "rupee_accuracy_%": "By rupee",
}


def _html_table(df: pd.DataFrame, highlight: str | None = None, min_width: int = 480) -> str:
    def fmt(col, v):
        if v is None or (not isinstance(v, str) and pd.isna(v)):
            return "–"
        if isinstance(v, str):
            text = config.BUSINESSES.get(v, v) if col == "business" else v
            return esc(text[:1].upper() + text[1:])
        if col.endswith("%") or "precision" in col:
            return f"{v:.1f}%"
        if isinstance(v, float) and not float(v).is_integer():
            return f"{v:,.1f}"
        return f"{int(v):,}"

    head = "".join(f"<th>{esc(SCORE_LABELS.get(c, c.replace('_', ' ').capitalize()))}</th>" for c in df.columns)
    body = []
    for _, row in df.iterrows():
        cls = ' class="hl"' if highlight is not None and row.iloc[0] == highlight else ""
        body.append(f"<tr{cls}>" + "".join(f"<td>{fmt(c, row[c])}</td>" for c in df.columns) + "</tr>")
    return (f'<div class="cc-scroll"><table class="cc-table" style="min-width:{min_width}px">'
            f'<thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>')


def page_quality():
    page_header("Data quality", "What was read, and how the copilot scored against the answer keys.")
    if showing_partial_view:
        render_partial_view_notice()

    rep = data_report()
    section("Your data, checked")
    tiles(
        tile("Bank lines read", f"{rep['bank_lines']:,}", tone="big"),
        tile("Duplicates skipped", f"{rep['duplicates_skipped']:,}", tone="big"),
        tile("Running balances tie", "Yes" if rep["balance_ties"] else f"{rep['balance_breaks']} breaks",
             tone="pos big" if rep["balance_ties"] else "neg big"),
        tile("Invoices and claims", f"{rep['documents']:,}", tone="big"),
    )

    st.write("")
    df = match_scores()
    auto_lines = df[df.tier.isin(["AUTO", "NO_DOC"])]
    if len(auto_lines) > 0:
        precision_txt = (f"AUTO precision is {auto_lines.correct.mean() * 100.0:.1f}% under strict Decision 60 rules "
                         f"across all three businesses.")
    else:
        precision_txt = "No AUTO matches recorded."
    section("Matching receipts to documents")
    H(f'<div class="cc-muted" style="margin-bottom:6px">{esc(precision_txt)}</div>')
    H(_html_table(summary(df), highlight=biz, min_width=900))

    st.write("")
    section("Sorting lines into categories")
    H('<div class="cc-muted" style="margin-bottom:6px">Payee memory plus the guide\'s rules, scored by line and by rupee value.</div>')
    cats = score_categories(pack, copilot.cat)
    left, _ = st.columns([3, 2])
    with left:
        H(_html_table(cats))


# ── PAGE: SETUP GUIDE (3 steps, Account Aggregator consent) ──────────────────
def page_setup():
    step = st.session_state["onboarding_step"]
    _, mid, _ = st.columns([0.45, 3, 0.45])
    with mid:
        labels = ["Consent", "Check your books", "Key numbers"]
        steps_html = "".join(
            f'<div class="{"on" if i <= step else ""} {"cur" if i == step else ""}"><div class="bar"></div>'
            f'<div class="n">Step {i}</div><div class="lbl">{esc(lbl)}</div></div>'
            for i, lbl in enumerate(labels, start=1))
        H(f'<div class="cc-steps" role="list" aria-label="Setup steps">{steps_html}</div>')

        with st.container(border=True):
            if step == 1:
                H('<div class="cc-title" role="heading" aria-level="1" style="font-size:1.6rem">'
                  'Connect your accounts with peace of mind</div>'
                  '<div class="cc-sub" style="font-size:0.95rem;color:#3F444B;margin:8px 0 20px">'
                  'We connect through RBI-regulated Account Aggregator rails. We only read your data to give you clarity, '
                  'never to act on your behalf.</div>')
                a, b = st.columns(2, gap="large")
                read = ["Bank statements (HDFC cash-credit, ICICI current account)",
                        "Tally sales invoices and supplier purchase bills",
                        "Daily drawer counts and salesman collection slips"]
                never = ["Move money or debit your accounts", "File tax returns or claim to be a CA",
                         "Send a message without your approval", "Share your margins with loan brokers"]
                with a:
                    H('<div style="font-weight:600;margin-bottom:12px">What we read</div><ul class="cc-list">'
                      + "".join(f"<li>{svg(ICON_EYE, 18, MUTED, 1.8)}{esc(t)}</li>" for t in read) + "</ul>")
                with b:
                    H('<div style="font-weight:600;margin-bottom:12px">What we never do</div><ul class="cc-list">'
                      + "".join(f"<li>{svg(ICON_NEVER, 18, NEG, 1.8)}{esc(t)}</li>" for t in never) + "</ul>")
                H('<div class="cc-rule" style="margin:22px 0 14px"></div>')
                c1, c2, _ = st.columns([1.6, 1, 2])
                if c1.button("Agree and check my books", type="primary", key="onb_step1_btn", use_container_width=True):
                    st.session_state["onboarding_step"] = 2
                    st.rerun()
                if c2.button("Skip for now", key="onb_skip_btn", use_container_width=True):
                    st.switch_page(PAGES["overview"])

            elif step == 2:
                rep = data_report()
                n_customers = len(by_customer(open_items(pack, biz)))
                H('<div class="cc-title" role="heading" aria-level="1" style="font-size:1.6rem">'
                  'Reading and checking your books</div>'
                  '<div class="cc-sub" style="font-size:0.95rem;color:#3F444B;margin:8px 0 20px">'
                  f'Eighteen months of statements, {rep["bank_lines"]:,} lines, checked for balance breaks and missing '
                  'receipts.</div>')
                tiles(
                    tile("Bank lines read", f"{rep['bank_lines']:,}", f"{rep['duplicates_skipped']} duplicates skipped", "big"),
                    tile("Running balances tie", "Yes" if rep["balance_ties"] else "No",
                         f"{rep['balance_breaks']} balance breaks", "pos big" if rep["balance_ties"] else "neg big"),
                    tile("Invoices and claims", f"{rep['documents']:,}", f"{n_customers} customers with open invoices", "big"),
                )
                if rep["balance_ties"]:
                    H(f'<div class="cc-row-title" style="color:#1A6E45;margin-top:16px">{svg(ICON_CHECK_CIRCLE, 18)}'
                      f'Every line ties to its running balance. Matching is ready.</div>')
                H('<div class="cc-rule" style="margin:22px 0 14px"></div>')
                c1, c2, _ = st.columns([1, 1, 3])
                if c1.button("Continue", type="primary", key="onb_step2_next", use_container_width=True):
                    st.session_state["onboarding_step"] = 3
                    st.rerun()
                if c2.button("Back", key="onb_step2_back", use_container_width=True):
                    st.session_state["onboarding_step"] = 1
                    st.rerun()

            else:
                limit = copilot.credit_limit(biz)
                salary, _ = copilot.salary_run(biz, "2026-09")
                H('<div class="cc-title" role="heading" aria-level="1" style="font-size:1.6rem">'
                  'We found your key numbers</div>'
                  '<div class="cc-sub" style="font-size:0.95rem;color:#3F444B;margin:8px 0 20px">'
                  'Filled in from your recurring transactions. Confirm them, or adjust them with your accountant.</div>')
                rows = []
                if limit:
                    rows.append(("Sanctioned cash-credit limit", "Found on your cash-credit account", inr(limit)))
                rows.append(("Payroll day", f"A salary run of about {lakh(salary)} repeats each month", "1st of the month"))
                rows.append(("Suggested cash floor", "A five-day operating buffer", "₹2,00,000"))
                H('<dl class="cc-dl">' + "".join(
                    f'<div style="align-items:baseline"><dt style="display:flex;flex-direction:column">'
                    f'<span style="color:#17191C;font-weight:500">{esc(t)}</span><span class="cc-muted">{esc(d)}</span></dt>'
                    f'<dd style="font-size:1.1rem;font-weight:600">{esc(v)}</dd></div>' for t, d, v in rows) + '</dl>')
                H('<div class="cc-callout neutral" style="margin-top:16px;font-size:0.85rem">Accountant view: formal bank '
                  'records are shared; drawer cash and khata notes stay private to the owner unless shared.</div>')
                H('<div class="cc-rule" style="margin:22px 0 14px"></div>')
                c1, c2, _ = st.columns([1.4, 1, 2.6])
                if c1.button("Open my overview", type="primary", key="onb_step3_finish", use_container_width=True):
                    st.session_state["onboarding_step"] = 1
                    st.switch_page(PAGES["overview"])
                if c2.button("Back", key="onb_step3_back", use_container_width=True):
                    st.session_state["onboarding_step"] = 2
                    st.rerun()


# ── NAVIGATION ───────────────────────────────────────────────────────────────
PAGES = {
    "overview": st.Page(page_overview, title="Overview", icon=":material/home:", default=True),
    "cash": st.Page(page_cash_book, title="Cash book", icon=":material/payments:", url_path="cash-book"),
    "forecast": st.Page(page_forecast, title="Forecast", icon=":material/trending_up:", url_path="forecast"),
    "review": st.Page(page_review, title="Review", icon=":material/inbox:", url_path="review"),
    "recv": st.Page(page_receivables, title="Receivables", icon=":material/receipt_long:", url_path="receivables"),
    "ask": st.Page(page_ask, title="Ask Copilot", icon=":material/chat_bubble:", url_path="ask"),
    "quality": st.Page(page_quality, title="Data quality", icon=":material/verified_user:", url_path="data-quality"),
    "setup": st.Page(page_setup, title="Setup guide", icon=":material/flag:", url_path="setup"),
}
current = st.navigation(list(PAGES.values()), position="hidden")

# ── SIDEBAR: BUSINESS, PAGES, ROLE, LANGUAGE ─────────────────────────────────
with st.sidebar:
    H(f'<div class="cc-brand">{LOGO}<span>Cash Copilot</span></div>')
    _biz_options = list(config.BUSINESSES)
    biz = st.selectbox("Business", _biz_options, format_func=lambda b: config.BUSINESSES[b], key="biz",
                       index=_biz_options.index(st.session_state["biz_choice"]),
                       on_change=lambda: st.session_state.update(biz_choice=st.session_state["biz"]))
    H('<div class="cc-note" style="padding:0 2px">Sample data pack · as of 30 Sep 2026 · read-only</div>')
    with st.container(key="nav"):
        for k in ("overview", "cash", "forecast", "review", "recv", "ask"):
            label = PAGES[k].title
            if k == "review":
                label = f"Review · {sum(v for t, v in queue_counts(biz).items() if t in (SUGGEST, ASK)):,}"
            st.page_link(PAGES[k], label=label, icon=PAGES[k].icon)
    with st.container(key="nav_more"):
        for k in ("quality", "setup"):
            st.page_link(PAGES[k], label=PAGES[k].title, icon=PAGES[k].icon)
    with st.container(key="side_bottom"):
        role = st.selectbox(
            "Viewing as", ROLES, key="role", index=ROLES.index(st.session_state["role_choice"]),
            on_change=lambda: st.session_state.update(role_choice=st.session_state["role"]),
            help="Owner sees all books; Counter staff need the owner PIN for the cash book; "
                 "the Accountant (CA) view respects the owner's sharing setting.",
        )
        lang = st.segmented_control(
            "Language / भाषा", ["English", "हिन्दी"], key="lang", default=st.session_state["lang_choice"],
            on_change=lambda: st.session_state.update(lang_choice=st.session_state["lang"] or "English"),
        ) or "English"
        H(f'<div class="cc-side-note">{svg(ICON_LOCK, 14)}<span>Read-only. Never moves money, edits records or '
          f'sends anything.</span></div>')

# A widget that lost its state falls back to the persisted choice (its index), so the two always agree.
st.session_state["biz_choice"], st.session_state["role_choice"] = biz, role

BIZ_NAME = config.BUSINESSES[biz]
share_cash_book = st.session_state.get("share_cash_book", True)
is_owner = role == "Owner"
is_counter_staff = role == "Counter staff"
is_accountant = role == "Accountant (CA)"
showing_partial_view = is_counter_staff or (is_accountant and not share_cash_book)

if msg := st.session_state.pop("toast", None):
    st.toast(msg, icon=":material/check_circle:")

current.run()
