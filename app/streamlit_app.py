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
import streamlit.components.v1 as components
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
from copilot.receivables import by_customer, daily_recovery_candidates, open_items, overdue
from copilot.score import score_matches, summary
from copilot.gemini import ocr_collection_slip, transcribe_audio
from copilot.ingest import parse_bank_statement, parse_tally_xml
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
.cc-onboard { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 14px; background: #F4F6FB; border: 1px solid #D9E2F2; border-radius: 8px; font-size: 0.85rem; color: #17191C; margin-bottom: 12px; }
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


def is_hi() -> bool:
    return st.session_state.get("lang_choice") == "हिन्दी"


def t(en: str, hi: str) -> str:
    """Return Hindi string when Hindi language is selected, else English."""
    return hi if is_hi() else en


PAGE_TITLES_HI = {
    "overview": "अवलोकन",
    "cash": "रोकड़ बही",
    "forecast": "नकद अनुमान",
    "review": "समीक्षा व मिलान",
    "recv": "बाजार उधारी",
    "ask": "रोकड़ सलाहकार",
    "quality": "डेटा शुद्धता",
    "setup": "सेटिंग्स व वॉल्ट",
}

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
ASK_CHIPS_HI = [
    "क्या मैं 1 अक्टूबर 2026 को सैलरी दे सकता हूँ?",
    "मुझ पर सबसे ज्यादा बकाया किसका है?",
    "क्या अगले महीने की कमी पूरी करने के लिए लोन लेना चाहिए?",
    "सभी बकायेदारों को तकादा मैसेज भेजें।",
    "मेरी आज की नकद स्थिति सरल हिंदी में समझाएं।",
    "अगले 90 दिनों में सबसे कम बैलेंस कब होगा?",
]
CHIP_HI_TO_EN = dict(zip(ASK_CHIPS_HI, ASK_CHIPS))
CHIP_EN_TO_HI = dict(zip(ASK_CHIPS, ASK_CHIPS_HI))


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
                st.page_link(PAGES["ask"], label=t("Ask about your cash…", "रोकड़ और हिसाब के बारे में पूछें…"),
                             icon=":material/search:", use_container_width=True)
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


def render_audio_briefing(text: str) -> None:
    """Render a 1-click Web Speech synthesis audio player for the morning briefing."""
    js_text = text.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'").replace("\n", " ")
    play_lbl = "Listen" if not is_hi() else "सुनें"
    stop_lbl = "Stop" if not is_hi() else "रोकें"
    title_lbl = "30-sec Daily Audio Briefing" if not is_hi() else "दैनिक नकद ब्रिफिंग (30 सेकंड)"
    sub_lbl = "(AI voice summary of today's cash)" if not is_hi() else "(आज की नकद स्थिति का संक्षिप्त सारांश)"
    lang = "hi-IN" if is_hi() else "en-IN"

    html_code = f"""
    <div style="display:flex;align-items:center;justify-content:space-between;background:#F4F6FB;border:1px solid #D9E2F2;border-radius:8px;padding:8px 14px;font-family:'IBM Plex Sans', -apple-system, sans-serif;margin-bottom:12px;">
      <div style="display:flex;align-items:center;gap:10px;">
        <span style="font-size:18px;">🎙️</span>
        <span style="font-size:13px;font-weight:600;color:#17191C;">{title_lbl}</span>
        <span style="font-size:12px;color:#555E68;">{sub_lbl}</span>
      </div>
      <button id="speakBtn" onclick="togglePlay()" style="background:#24509A;color:white;border:none;padding:6px 14px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;display:flex;align-items:center;gap:6px;">
        <span id="btnIcon">▶️</span> <span id="btnTxt">{play_lbl}</span>
      </button>
    </div>
    <script>
      let isPlaying = false;
      const text = "{js_text}";
      function togglePlay() {{
        if (!('speechSynthesis' in window)) {{
          alert('Speech synthesis is not supported in this browser.');
          return;
        }}
        if (isPlaying) {{
          window.speechSynthesis.cancel();
          isPlaying = false;
          document.getElementById('btnTxt').innerText = "{play_lbl}";
          document.getElementById('btnIcon').innerText = "▶️";
        }} else {{
          window.speechSynthesis.cancel();
          const u = new SpeechSynthesisUtterance(text);
          u.lang = "{lang}";
          u.rate = 1.0;
          u.onend = function() {{
            isPlaying = false;
            document.getElementById('btnTxt').innerText = "{play_lbl}";
            document.getElementById('btnIcon').innerText = "▶️";
          }};
          u.onerror = function() {{
            isPlaying = false;
            document.getElementById('btnTxt').innerText = "{play_lbl}";
            document.getElementById('btnIcon').innerText = "▶️";
          }};
          window.speechSynthesis.speak(u);
          isPlaying = true;
          document.getElementById('btnTxt').innerText = "{stop_lbl}";
          document.getElementById('btnIcon').innerText = "⏹️";
        }}
      }}
    </script>
    """
    components.html(html_code, height=52)


@st.dialog("Daily Recovery Sheet")
def daily_print_dialog():
    items = open_items(pack, biz)
    late = daily_recovery_candidates(pack, biz, min_days=45)
    total_due = late.outstanding.sum() if not late.empty else 0.0

    st.caption(t("Print or export for godown manager & field salesmen daily collection rounds.",
                 "गोदाम प्रबंधक और फील्ड सेल्समैन के दैनिक वसूली राउंड के लिए प्रिंट या निर्यात करें।"))

    if late.empty:
        st.info(t("No customers are overdue past 45 days.", "45 दिन से अधिक का कोई बकाया नहीं है।"))
        return

    c_btn1, c_btn2 = st.columns([1, 1])
    csv_data = late[["customer_name", "outstanding", "oldest_days", "invoices"]].copy()
    csv_data.columns = ["Shop Name", "Outstanding (INR)", "Oldest Days", "Invoices"]
    csv_data["Visited"] = ""
    csv_data["Amount Collected"] = ""
    csv_data["Remarks"] = ""
    c_btn1.download_button(
        label=t("📥 Download CSV", "📥 CSV डाउनलोड करें"),
        data=csv_data.to_csv(index=False),
        file_name=f"recovery_sheet_{biz}_{config.AS_OF:%Y%m%d}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    table_rows = ""
    for idx, (_, r) in enumerate(late.iterrows(), 1):
        table_rows += (
            f'<tr style="border-bottom:1px solid #ECECE8;">'
            f'<td style="padding:6px;text-align:left;">{idx}</td>'
            f'<td style="padding:6px;font-weight:600;color:#17191C;">{esc(r["customer_name"])}</td>'
            f'<td style="padding:6px;text-align:right;font-weight:600;color:#17191C;">{inr(r["outstanding"])}</td>'
            f'<td style="padding:6px;text-align:center;color:#8A5300;">{int(r["oldest_days"])}d</td>'
            f'<td style="padding:6px;text-align:center;"><span style="display:inline-block;width:14px;height:14px;border:1.5px solid #555E68;border-radius:2px;"></span></td>'
            f'<td style="padding:6px;border-bottom:1px dashed #CCC;width:90px;"></td>'
            f'<td style="padding:6px;border-bottom:1px dashed #CCC;"></td>'
            f'</tr>'
        )

    html_sheet = f"""
    <div id="printSheet" style="background:#FFF;padding:16px;font-family:'IBM Plex Sans', -apple-system, sans-serif;border:1px solid #E2E2DC;border-radius:8px;margin-top:10px;">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;border-bottom:2px solid #17191C;padding-bottom:10px;margin-bottom:12px;">
        <div>
          <div style="font-size:18px;font-weight:700;color:#17191C;">{esc(BIZ_NAME)}</div>
          <div style="font-size:13px;font-weight:600;color:#24509A;">DAILY RECOVERY & CHASING SHEET (गोदाम / फील्ड वसूली शीट)</div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:12px;font-weight:600;color:#17191C;">Date: {config.AS_OF:%d %b %Y}</div>
          <div style="font-size:11px;color:#555E68;">Overdue (45+ Days): {len(late)} shops · Total: {inr(total_due)}</div>
        </div>
      </div>

      <div style="margin-bottom:12px;text-align:right;">
        <button onclick="window.print()" style="background:#24509A;color:white;border:none;padding:6px 14px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;">
          🖨️ Print Sheet / PDF
        </button>
      </div>

      <table style="width:100%;border-collapse:collapse;font-size:12px;margin-bottom:20px;">
        <thead>
          <tr style="background:#F4F4F1;border-bottom:1px solid #17191C;">
            <th style="padding:6px;text-align:left;width:30px;">#</th>
            <th style="padding:6px;text-align:left;">Retailer / Shop</th>
            <th style="padding:6px;text-align:right;width:95px;">Due (₹)</th>
            <th style="padding:6px;text-align:center;width:55px;">Age</th>
            <th style="padding:6px;text-align:center;width:50px;">Visit</th>
            <th style="padding:6px;text-align:left;width:90px;">Recvd (₹)</th>
            <th style="padding:6px;text-align:left;">Salesman Notes</th>
          </tr>
        </thead>
        <tbody>
          {table_rows}
        </tbody>
      </table>

      <div style="display:flex;justify-content:space-between;gap:20px;margin-top:24px;padding-top:16px;border-top:1px solid #17191C;font-size:11px;">
        <div><b>Salesman Sign:</b> ___________________</div>
        <div><b>Godown Manager Sign:</b> ___________________</div>
        <div><b>Cashier Sign:</b> ___________________</div>
      </div>
    </div>
    """
    components.html(html_sheet, height=450, scrolling=True)


# ── PAGE: OVERVIEW ───────────────────────────────────────────────────────────
def page_overview():
    page_header(t("Overview", "अवलोकन"), t(f"Namaste, {BIZ_NAME}. Your position on {config.AS_OF:%d %b %Y}.",
                                            f"नमस्ते, {BIZ_NAME}। {config.AS_OF:%d %b %Y} को आपकी नकद स्थिति।"))
    bal, _ = copilot.closing_balance(biz)
    limit = copilot.credit_limit(biz)
    items = open_items(pack, biz)

    if showing_partial_view:
        render_partial_view_notice()
        if is_hi():
            p_text = f"नमस्ते {BIZ_NAME}। बैंक बैलेंस {inr(bal)} है। कुल इनवॉइस बकाया {inr(items.outstanding.sum())} है।"
        else:
            p_text = f"Good morning, {BIZ_NAME}. Bank balance is {inr(bal)}. Formal receivables total {inr(items.outstanding.sum())}."
        render_audio_briefing(p_text)
        H(f'<div class="cc-label">{t("Formal cash position, bank alone", "औपचारिक बैंक नकद स्थिति")}</div>')
        parts = [tile(t(f"Bank balance, {config.AS_OF:%d %b %Y}", f"बैंक बैलेंस, {config.AS_OF:%d %b %Y}"), inr(bal))]
        if limit:
            parts.append(tile(t("Cash-credit headroom", "कैश-क्रेडिट सुरक्षित सीमा"), inr(bal + limit),
                              t(f"Sanctioned limit {esc(inr(limit))}", f"स्वीकृत CC सीमा {esc(inr(limit))}")))
        parts.append(tile(t("Formal receivables", "कुल बिल बकाया"), inr(items.outstanding.sum()),
                          t(f"{len(overdue(items))} invoices more than 60 days late", f"{len(overdue(items))} इनवॉइस 60 दिन से पुराने")))
        tiles(*parts)
        H(f'<div class="cc-note">{t("Formal books only. Cash drawer and informal khata balances are not included.", "केवल औपचारिक बही-खाता। गल्ला और खाता इसमें शामिल नहीं हैं।")}</div>')
    else:
        if is_owner and not st.session_state.get("onboarding_dismissed", False):
            c_on1, c_on2 = st.columns([5, 1], vertical_alignment="center")
            with c_on1:
                H(f'<div class="cc-onboard">'
                  f'<div><b>{t("✨ Quick Setup & Privacy Summary:", "✨ त्वरित सेटअप और गोपनीयता सुरक्षा:")}</b> '
                  f'{t("1. Owner PIN: active (0000)", "1. गुप्त PIN: सक्रिय (0000)")} · '
                  f'{t("2. ₹25L CC Headroom: monitored", "2. ₹25 लाख CC लिमिट: सक्रिय")} · '
                  f'{t("3. Cash Drawer: Private (not shared with CA)", "3. गल्ला: केवल मालिक के लिए सुरक्षित")}</div>'
                  f'</div>')
            with c_on2:
                if st.button(t("Dismiss", "हटाएं"), key="btn_dismiss_onboard", use_container_width=True):
                    st.session_state["onboarding_dismissed"] = True
                    st.rerun()

        galla = vault.get_latest_galla(biz)
        khata = vault.get_khata_summary(biz)
        galla_demo = bool(galla and galla.is_demo)
        khata_demo = any(getattr(a, "is_demo", False) for a in khata["accounts"])

        hero_box, eq_box, ctrl_box = st.container(), st.container(), st.container()
        with ctrl_box:
            c1, c2 = st.columns([2, 3], vertical_alignment="center")
            with c1:
                if is_owner:
                    pct = st.slider(t("Khata collection assumption", "खाता वसूली अनुमान"), min_value=50, max_value=100,
                                    value=int(round(config.KHATA_COLLECTION_ASSUMPTION * 100)), step=5,
                                    format="%d%%", help=t("Adjustable informal khata recovery expectation", "खाता वसूली की संभावित दर"))
                    alpha = pct / 100
                else:
                    alpha = config.KHATA_COLLECTION_ASSUMPTION
            with c2:
                if galla_demo or khata_demo:
                    H(f'<div class="cc-note" style="text-align:right">{t("Drawer and khata figures include demo data, not from the pilot pack.", "गल्ला और खाते के आंकड़े डेमो डेटा से हैं।")}</div>')

        solvency = compute_total_solvency(pack, vault, biz, haircut_alpha=alpha)
        solv_rep = format_solvency_report(solvency)
        runway = solvency.true_cash_runway_inr
        total_liquid = solvency.net_bank_liquidity + solvency.galla_cash
        unused_limit = max(0.0, solvency.cc_limit - solvency.cc_drawn)
        sal = copilot.can_pay_salaries(biz, galla_cash=answer_galla())
        cust = by_customer(items)
        late = cust[cust.oldest_days >= 45]

        if is_hi():
            b_sal = "1 अक्टूबर की सैलरी सुरक्षित है।" if sal.numbers["yes"] else "1 अक्टूबर की सैलरी के लिए योजना जरूरी है।"
            b_late = f"बाजार में {len(late)} दुकानों पर कुल {inr(late.outstanding.sum())} बकाया है।" if len(late) else "बाजार उधारी सामान्य है।"
            briefing_text = (f"शुभ प्रभात {BIZ_NAME}। आज आपके पास कुल {inr(total_liquid)} खर्च करने योग्य नकदी है। "
                             f"30 दिन का शुद्ध नकद सुरक्षा बफर {inr(runway)} है। {b_sal} {b_late} आपका दिन शुभ हो।")
        else:
            b_sal = "October 1 salaries are covered." if sal.numbers["yes"] else "October 1 salaries need cash planning."
            b_late = f"You have {len(late)} shops with 45+ day dues totaling {inr(late.outstanding.sum())}." if len(late) else "All receivables are within credit cycles."
            briefing_text = (f"Good morning, {BIZ_NAME}. Today you have {inr(total_liquid)} usable cash. "
                             f"Your 30-day own-cash buffer is {inr(runway)}. {b_sal} {b_late} Have a productive day.")

        render_audio_briefing(briefing_text)

        with hero_box:
            if solvency.cc_limit > 0:
                if is_hi():
                    hero_sub = (f"बैंक सुरक्षित सीमा {inr(solvency.net_bank_liquidity)} (बैलेंस {inr(solvency.bank_balance)} "
                                f"और अप्रयुक्त CC सीमा {inr(unused_limit)}) तथा गल्ले में गिना हुआ नकद {inr(solvency.galla_cash)}।")
                else:
                    hero_sub = (f"Bank headroom {inr(solvency.net_bank_liquidity)} (balance {inr(solvency.bank_balance)} "
                                f"plus the unused {inr(unused_limit)} cash-credit limit) and {inr(solvency.galla_cash)} "
                                f"counted in the drawer.")
            else:
                if is_hi():
                    hero_sub = (f"बैंक बैलेंस {inr(solvency.bank_balance)} तथा गल्ले में गिना हुआ नकद {inr(solvency.galla_cash)}।")
                else:
                    hero_sub = (f"Bank balance {inr(solvency.bank_balance)} and {inr(solvency.galla_cash)} "
                                f"counted in the drawer.")
            headline = solv_rep["headline"]
            s_title, _, s_detail = headline.partition(":")
            if is_hi():
                if runway > 0:
                    s_title = "30 दिनों के लिए सुरक्षित"
                    s_detail = "अगले 30 दिनों के खर्चों के बाद भी खाता सुरक्षित रहेगा।"
                else:
                    s_title = "सावधानी जरूरी"
                    s_detail = "अगले 30 दिनों के खर्चों के लिए नकद योजना बनाएं।"
            tone = "pos" if runway > 0 else "neg"
            if solvency.is_false_insolvency:
                tone = "warn"
            s_icon = ICON_CHECK_CIRCLE if tone == "pos" else ICON_ALERT
            a, b = st.columns([3, 2], vertical_alignment="bottom")
            with a:
                H(f'<div class="cc-label">{t("Cash you can use today", "आज खर्च करने योग्य कुल नकदी")}</div><div class="cc-hero">{esc(inr(total_liquid))}</div>'
                  f'<div class="cc-muted">{esc(hero_sub)}</div>')
            with b:
                H(f'<div class="cc-status {tone}">{svg(s_icon, 18)}<span style="display:flex;flex-direction:column">'
                  f'<span class="t">{esc(s_title.strip())}</span><span class="d">{esc(s_detail.strip())}</span></span></div>')

        with eq_box:
            months = runway / max(solvency.total_commitments, 1.0)
            if is_hi():
                khata_sub = (f"{esc(inr(solvency.informal_receivables))} का {int(round(alpha * 100))}% {DEMO if khata_demo else ''}"
                             if solvency.informal_receivables else "कोई उधारी नहीं")
                month_sub = f"लगभग {months:.1f} महीने के खर्चे सुरक्षित"
                comm_sub = "सैलरी, बिल और लेनदारों की देनदारी"
                close_sub = f"अंतिम बैलेंस, {config.AS_OF:%d %b}"
                galla_sub = f"{'आज गिना हुआ' if galla else 'गिना नहीं गया'} {DEMO if galla_demo else ''}"
            else:
                khata_sub = (f"{int(round(alpha * 100))}% of {esc(inr(solvency.informal_receivables))} {DEMO if khata_demo else ''}"
                             if solvency.informal_receivables else "No informal khata")
                month_sub = f"About {months:.1f} months of commitments"
                comm_sub = "Salaries, open bills and khata you owe"
                close_sub = f"Closing, {config.AS_OF:%d %b}"
                galla_sub = f"{esc(galla.status_label) if galla else 'Not counted'} {DEMO if galla_demo else ''}"
            tiles(
                tile(t("Bank balance", "बैंक बैलेंस") if not solvency.cc_drawn else t("Bank balance less overdraft", "बैंक बैलेंस (ओवरड्राफ्ट घटाकर)"),
                     inr(solvency.bank_balance - solvency.cc_drawn), close_sub),
                tile(t("+ Cash in drawer", "+ गल्ले में नकद कैश"), inr(solvency.galla_cash), galla_sub),
                tile(t("+ Khata you expect back", "+ बाजार से संभावित वसूली"), inr(solvency.total_expected_inflows), khata_sub),
                tile(t("− Due in next 30 days", "− अगले 30 दिन के खर्चे"), inr(solvency.total_commitments), comm_sub),
                tile(t("= Your own-cash buffer", "= आपकी शुद्ध नकद सुरक्षा"), inr(runway), month_sub,
                     "accent" if runway >= 0 else "neg"),
            )

    st.write("")
    section(t("Needs you today", "आज का सबसे जरूरी काम"))
    counts = queue_counts(biz)
    cust = by_customer(items)
    late = cust[cust.oldest_days >= 45]
    with st.container(key="rows"):
        sal = copilot.can_pay_salaries(biz, galla_cash=answer_galla())
        n = sal.numbers
        if n["yes"]:
            title = t(f'Salaries on 1 Oct are covered {tag("Covered", "pos")}',
                      f'1 अक्टूबर की सैलरी सुरक्षित है {tag("सुरक्षित", "pos")}')
        else:
            title = t(f'Salaries on 1 Oct need a plan {tag("Check", "warn")}',
                      f'1 अक्टूबर की सैलरी के लिए योजना जरूरी {tag("ध्यान दें", "warn")}')
        if is_hi():
            detail = f"सितंबर की कुल सैलरी {inr(n['salary'])} थी। "
            detail += (f"CC लिमिट के बाद भी {inr(n['headroom'])} की सुरक्षित सीमा बची रहेगी।" if limit
                       else f"30 सितंबर को बैंक बैलेंस {inr(n['closing_balance'])} है।")
        else:
            detail = f"September payroll was {inr(n['salary'])}. "
            detail += (f"Headroom of {inr(n['headroom'])} stays clear of the cash-credit limit." if limit
                       else f"The 30 Sep balance is {inr(n['closing_balance'])}.")
        _action_row("salary", title, detail, t("See the answer", "जवाब देखें"), PAGES["ask"], ask=ASK_CHIPS[0])
        if len(late):
            late_title = t(f'{len(late)} customers are more than 45 days overdue {tag(inr(late.outstanding.sum()), "warn")}',
                           f'{len(late)} ग्राहकों पर 45 दिन से अधिक का बकाया {tag(inr(late.outstanding.sum()), "warn")}')
            late_detail = t("Start with the largest. Each reminder opens as a WhatsApp draft for you to send.",
                            "सबसे बड़े बकायेदार से शुरू करें। प्रत्येक तकादा WhatsApp पर ड्राफ्ट होगा।")
            _action_row("late", late_title, late_detail, t("Open chasing list", "वसूली सूची देखें"), PAGES["recv"])
        waiting = counts[SUGGEST] + counts[ASK]
        if waiting:
            rev_title = t(f"{waiting:,} receipts need a decision", f"{waiting:,} जमा पर्चियों पर निर्णय बाकी")
            rev_detail = t(f"{counts[SUGGEST]:,} suggested matches and {counts[ASK]:,} questions. Another {counts['auto']:,} were matched automatically.",
                           f"{counts[SUGGEST]:,} सुझाव और {counts[ASK]:,} सवाल। अन्य {counts['auto']:,} स्वतः मिलान हो चुके हैं।")
            _action_row("review", rev_title, rev_detail, t("Start review", "समीक्षा शुरू करें"), PAGES["review"])
        _action_row("slips", t("Record today's collection slips", "आज की वसूली पर्चियां दर्ज करें"),
                    t("Salesman slips let cash deposits link to the right shop invoices.",
                      "सेल्समैन की पर्चियों से कैश जमा सीधे सही दुकान के इनवॉइस से जुड़ जाता है।"),
                    t("Record slips", "पर्ची दर्ज करें"), PAGES["cash"])
        if len(late):
            with st.container(key="row_recovery_sheet"):
                r_a, r_b = st.columns([5, 1.6], vertical_alignment="center")
                with r_a:
                    H(f'<div class="cc-row-title">{t("Daily Field Recovery Sheet (गोदाम / फील्ड वसूली शीट)", "दैनिक फील्ड वसूली शीट (गोदाम)")}</div>'
                      f'<div class="cc-row-detail">{t(f"Print or export today\'s {len(late)} overdue retailers with checkmarks and signature lines.", f"45+ दिन पुराने {len(late)} बकायेदारों की प्रिंट शीट, चेकबॉक्स और हस्ताक्षर सहित।")}</div>')
                with r_b:
                    if st.button(t("Print Sheet", "शीट प्रिंट करें"), key="btn_ov_print_sheet", use_container_width=True):
                        daily_print_dialog()

    st.write("")
    left, right = st.columns([2, 1], gap="large")
    with left:
        section(t("90-day forecast", "90 दिन का नकद अनुमान"), (t("Open forecast", "पूरा अनुमान देखें"), "forecast", PAGES["forecast"]))
        fc = forecast_for(biz)
        if fc.warnings:
            H(f'<div class="cc-tag warn">{len(fc.warnings)} {t("shortfall warning", "कमी की चेतावनी")}{"s" if len(fc.warnings) > 1 and not is_hi() else ""}</div>')
        else:
            H(f'<div class="cc-row-title" style="color:#1A6E45;font-size:0.85rem">{svg(ICON_CHECK, 16, width=2.2)}'
              f'{t("No shortfall projected", "कोई नकद कमी नहीं आएगी")}</div>')
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
                           if closing and not is_hi() else (f" {pd.Timestamp(closing.month + '-01'):%B} का समापन लगभग {inr(closing.closing_balance_p50)} पर होगा।" if closing else ""))
            H(f'<div class="cc-muted">{t("Lowest expected balance is", "सबसे कम संभावित बैलेंस")} {esc(inr(low.p50))} '
              f'({pd.Timestamp(low.Date):%d %b})। {esc(closing_txt)}</div>')
    with right:
        section(t("Your data, checked", "डेटा शुद्धता एवं ऑडिट"), (t("Details", "विवरण देखें"), "quality", PAGES["quality"]))
        rep = data_report()
        ties = t("Yes, no breaks", "हाँ, पूर्ण मिलान") if rep["balance_ties"] else f"{rep['balance_breaks']} {t('breaks', 'असंगतियां')}"
        H(f'<dl class="cc-dl">'
          f'<div><dt>{t("Bank lines read", "बैंक प्रविष्टियां पढ़ी गईं")}</dt><dd>{rep["bank_lines"]:,}</dd></div>'
          f'<div><dt>{t("Duplicates skipped", "दोहरी प्रविष्टियां हटाई गईं")}</dt><dd>{rep["duplicates_skipped"]:,}</dd></div>'
          f'<div><dt>{t("Running balances tie", "दैनिक बैलेंस का मिलान")}</dt><dd style="color:{"#1A6E45" if rep["balance_ties"] else NEG}">{ties}</dd></div>'
          f'<div><dt>{t("Invoices and claims", "कुल इनवॉइस व दावे")}</dt><dd>{rep["documents"]:,}</dd></div></dl>')


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
    H(f'<div class="cc-muted">{t("Takes about a minute. Saved in your cash book on this device.", "लगभग एक मिनट लगेगा। आपके डिवाइस पर रोकड़ बही में सुरक्षित होगा।")}</div>')
    with st.form("galla_close_form", border=False):
        c1, c2 = st.columns(2)
        c1.number_input(t("Opening till cash (₹)", "सुबह का शुरुआती नकद (₹)"), value=10000.0, step=500.0)
        c2.number_input(t("Today's cash takings (₹)", "आज की नकद बिक्री (₹)"), value=25000.0, step=1000.0)
        c1.number_input(t("Cash expenses paid (₹)", "नकद खर्चे व हमाली (₹)"), value=2500.0, step=100.0, help=t("Hamali, petty and other cash expenses", "हमाली, चाय-पानी व अन्य खर्चे"))
        c2.number_input(t("Cash banked into account (₹)", "बैंक खाते में जमा नकद (₹)"), value=20000.0, step=1000.0)
        c1.number_input(t("Physical count at close (₹)", "शाम को गल्ले में बचा नकद (₹)"), value=12500.0, step=500.0)
        c2.text_input(t("Notes", "विवरण / नोट"), value="Routine daily close")
        submitted = st.form_submit_button(t("Record in cash book", "रोकड़ बही में दर्ज करें"), type="primary")
    if submitted:
        st.session_state["toast"] = t("Recorded locally in Cash Book. Balance updated.", "रोकड़ बही में दर्ज हुआ। बैलेंस अपडेट हो गया।")
        st.rerun()


@st.dialog("Record collection slips")
def collections_dialog():
    H(f'<div class="cc-muted">{t("What each salesman collected from shops. Used to match cash deposits to invoices.", "दुकानों से सेल्समैन द्वारा की गई वसूली। बैंक जमा को इनवॉइस से जोड़ने के लिए उपयोगी।")}</div>')

    # ── VISION OCR: CAMERA / FILE UPLOAD ──
    slip_file = st.file_uploader(t("📷 Scan handwritten slip photo (Optional)", "📷 हाथ से लिखी पर्ची की फोटो खींचें (वैकल्पिक)"),
                                 type=["jpg", "jpeg", "png", "webp"], key="_slip_upload_img")
    prefill_shop = "Laxmi Kirana Stores"
    prefill_amount = 15000.0
    prefill_salesman = "Ramesh K."
    if slip_file:
        with st.spinner(t("Scanning slip with Gemini Vision…", "Gemini AI से पर्ची पढ़ी जा रही है…")):
            ocr_data = ocr_collection_slip(slip_file.read(), mime_type=slip_file.type or "image/jpeg")
            if ocr_data.get("shop"):
                prefill_shop = ocr_data["shop"]
            if ocr_data.get("amount"):
                prefill_amount = float(ocr_data["amount"])
            if ocr_data.get("salesman"):
                prefill_salesman = ocr_data["salesman"]
            st.success(t(f"Extracted: {prefill_shop} · {inr(prefill_amount)} · {prefill_salesman}",
                         f"पहचाना गया: {prefill_shop} · {inr(prefill_amount)} · {prefill_salesman}"))

    with st.form("collections_today_form", border=False):
        c1, c2 = st.columns(2)
        col_date = c1.date_input(t("Collection date", "वसूली की तारीख"), value=pd.Timestamp("2026-09-30"))
        salesman = c2.text_input(t("Salesman", "सेल्समैन का नाम"), value=prefill_salesman)
        rows = []
        for i, (shop, amount) in enumerate([(prefill_shop, prefill_amount), ("", 0.0), ("", 0.0)], start=1):
            a, b = st.columns([2, 1])
            rows.append((a.text_input(t(f"Shop {i}" + (" (optional)" if i > 1 else ""), f"दुकान {i}" + (" (वैकल्पिक)" if i > 1 else "")), value=shop),
                         b.number_input(t(f"Amount {i} (₹)", f"रकम {i} (₹)"), value=amount, step=500.0)))
        col_sub = st.form_submit_button(t("Record collections", "वसूली दर्ज करें"), type="primary")
    if col_sub:
        for s, a in rows:
            if s.strip() and a > 0:
                vault.record_collection(Collection(biz, pd.Timestamp(col_date), s.strip(), a, salesman))
        st.session_state["toast"] = t("Collections recorded in local vault.", "वसूली पर्चियां सफलतापूर्वक दर्ज की गईं।")
        st.rerun()


def page_cash_book():
    def share_toggle():
        if is_owner:
            st.toggle(t("Share my cash book with my accountant", "मुनीम/एकाउंटेंट के साथ रोकड़ बही साझा करें"), key="_share_widget",
                      value=st.session_state["share_cash_book"],
                      help=t("When off, the Accountant (CA) role sees formal books only.", "बंद होने पर एकाउंटेंट केवल बैंक का औपचारिक हिसाब देख सकते हैं।"),
                      on_change=lambda: st.session_state.update(share_cash_book=st.session_state["_share_widget"]))
        else:
            with st.container(key="askfield"):
                st.page_link(PAGES["ask"], label=t("Ask about your cash…", "रोकड़ और हिसाब के बारे में पूछें…"), icon=":material/search:",
                             use_container_width=True)

    page_header(t("Cash book", "रोकड़ बही (Cash Book)"),
                t("Drawer cash and informal khata. Kept on this device only.", "गल्ले का नकद और कच्चा खाता। केवल इस डिवाइस पर सुरक्षित।"),
                right=share_toggle)
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
            st.info(t("The owner has not shared the cash book with the accountant.", "मालिक ने एकाउंटेंट के साथ रोकड़ बही साझा नहीं की है।"))
    elif is_counter_staff:
        a, b = st.columns([1, 14])
        with a:
            H(f'<div class="cc-lock">{svg(ICON_LOCK, 18, "#3F444B")}</div>')
        with b:
            H(f'<div class="cc-h2">{t("Cash book is locked", "रोकड़ बही लॉक है")}</div>'
              f'<div class="cc-muted">{t("Owner PIN is required to view the cash book.", "रोकड़ बही देखने के लिए मालिक का PIN आवश्यक है।")}</div>')
            pin_prompt_label = t("Demo PIN: 0000", "डेमो PIN: 0000") if pin_is_default else t("Enter owner PIN", "मालिक का PIN दर्ज करें")
            c, _ = st.columns([1, 2])
            staff_pin = c.text_input(t("Enter Owner PIN to unlock", "अनलॉक करने के लिए PIN डालें"), type="password", help=pin_prompt_label)
            if staff_pin:
                if staff_pin == expected_pin:
                    can_view_cash_book = True
                else:
                    st.error(t("Incorrect PIN.", "गलत PIN दर्ज किया गया।"))
            elif pin_is_default:
                H(f'<div class="cc-note">{t("Demo PIN: 0000", "डेमो PIN: 0000")}</div>')

    if not can_view_cash_book:
        return

    left, right = st.columns([2, 1], gap="large")
    with left:
        latest_g = vault.get_latest_galla(biz)
        demo = DEMO if latest_g and latest_g.is_demo else ""
        when = f"{esc(latest_g.notes)} · {latest_g.date:%d %b %Y}" if latest_g else ""
        H(f'<div style="display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;align-items:center">'
          f'<div class="cc-h2" role="heading" aria-level="2">{t("Today\'s drawer", "आज का गल्ला")} {demo}</div>'
          f'<div class="cc-note">{when}</div></div>')
        if latest_g:
            status_sub = t("Ties to the book", "बही से पूर्ण मिलान") if latest_g.is_balanced else f"{esc(inr(latest_g.drift))} {t('drift', 'अंतर')}"
            tiles(
                tile(t("Counted in drawer", "गल्ले में गिना हुआ नकद"), inr(latest_g.counted_cash), tone="big"),
                tile(t("Expected from book", "बही के अनुसार अपेक्षित"), inr(latest_g.expected_cash), tone="big"),
                tile(t("Till status", "गल्ले की स्थिति"), latest_g.status_label, status_sub, "pos big" if latest_g.is_balanced else "warn big"),
            )
        else:
            H(f'<div class="cc-muted">{t("No drawer count recorded yet.", "अभी तक कोई गल्ला गणना दर्ज नहीं है।")}</div>')
        b1, b2, _ = st.columns([1, 1.4, 1.6])
        if b1.button(t("Close the day", "आज का गल्ला बंद करें"), type="primary", key="open_day_close", use_container_width=True):
            day_close_dialog()
        if b2.button(t("Record collection slips", "वसूली पर्ची दर्ज करें"), key="open_slips", use_container_width=True):
            collections_dialog()

        st.write("")
        khata_data = vault.get_khata_summary(biz)
        accounts = khata_data["accounts"]
        k_demo = DEMO if any(getattr(acc, "is_demo", False) for acc in accounts) else ""
        totals = (f'{t("They owe you", "ग्राहकों पर बाकी")} <b class="cc-num">{esc(inr(khata_data["receivables"]))}</b> · {t("you owe", "आपको देना है")} '
                  f'<b class="cc-num">{esc(inr(khata_data["payables"]))}</b>') if accounts else ""
        H(f'<div style="display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;align-items:baseline">'
          f'<div class="cc-h2" role="heading" aria-level="2">{t("Pending khata", "कच्चा खाता")} {k_demo}</div>'
          f'<div class="cc-muted">{totals}</div></div>')
        if accounts:
            H(f'<div class="cc-colhead" style="grid-template-columns:2.6fr 1.1fr 1.2fr 1.9fr">'
              f'<span>{t("Party", "पार्टी का नाम")}</span><span>{t("Open for", "अवधि")}</span><span style="text-align:right">{t("Balance", "बाकी रकम")}</span><span></span></div>')
            with st.container(key="krows"):
                for i, acc in enumerate(accounts):
                    rem = format_whatsapp_reminder(acc, BIZ_NAME, upi_handle="payment@bank")
                    with st.container(key=f"krow_{i}"):
                        c1, c2, c3, c4 = st.columns([2.6, 1.1, 1.2, 1.9], vertical_alignment="center")
                        sub = ""
                        if acc.balance_due < 0:
                            sub = f'<div class="cc-row-detail">{t("You owe them", "आपको देना है")}</div>'
                        if rem["limitation_warning"]:
                            sub = f'<div class="cc-row-detail">{esc(rem["limitation_warning"])}</div>'
                        flag = tag(t("Over 30 months", "30 महीने से अधिक"), "warn") if acc.is_limitation_alert else ""
                        c1.markdown(f'<div class="cc-row-title">{esc(acc.party_name)} {flag}</div>{sub}',
                                    unsafe_allow_html=True)
                        c2.markdown(f'<div class="cc-muted">{acc.months_open} {t("months", "महीने")}</div>', unsafe_allow_html=True)
                        color = f"color:{NEG}" if acc.balance_due < 0 else ""
                        c3.markdown(f'<div class="cc-amount" style="{color}">{esc(inr(acc.balance_due))}</div>',
                                    unsafe_allow_html=True)
                        c4.link_button(t("WhatsApp draft", "WhatsApp तकादा"), rem["wa_link"], icon=":material/send:", use_container_width=True)
            H(f'<div class="cc-note">{t("Drafts open in WhatsApp. Nothing is sent until you press send there.", "मैसेज WhatsApp में ड्राफ्ट होगा। आपके भेजने से पहले कुछ भी नहीं भेजा जाता।")}</div>')
        else:
            H(f'<div class="cc-muted">{t("No informal khata records for this business.", "इस व्यापार के लिए कोई कच्चा खाता दर्ज नहीं है।")}</div>')

    with right:
        with st.container(key="cc_panel"):
            ytd_deposits = vault.get_ytd_cash_deposits(biz)
            is_seeded = (biz in ("SME-1", "SME-3")) or (ytd_deposits > 0)
            facts_res = cash_deposit_reporting_facts(ytd_deposits)
            checklist = deposit_records_checklist()
            items_html = "".join(f'<li>{svg(ICON_BOX_CHECK, 16, MUTED)}{esc(doc)}</li>' for doc in checklist["documents"])
            H(f'<div class="cc-h2" role="heading" aria-level="2">{t("Cash deposits this year", "इस वर्ष कुल नकद बैंक जमा")} {DEMO if is_seeded else ""}</div>'
              f'<div class="cc-hero" style="font-size:1.6rem">{esc(inr(ytd_deposits))}</div>'
              f'<div class="cc-muted" style="color:#3F444B">{esc(facts_res.message)}</div>'
              f'<div class="cc-note" style="margin-top:8px">{esc(facts_res.citation)}</div>'
              f'<div style="border-top:1px solid #E2E2DC;margin:14px 0 10px"></div>'
              f'<div style="font-weight:600;font-size:0.85rem;margin-bottom:10px">{t("Records checklist before depositing cash", "नकद जमा से पहले जरूरी रिकॉर्ड")}</div>'
              f'<ul class="cc-list sm">{items_html}</ul>'
              f'<div class="cc-note" style="margin-top:12px">{esc(checklist["referral"])}</div>')


# ── PAGE: FORECAST (FR-FC-1, FR-FC-2) ────────────────────────────────────────
def page_forecast():
    page_header(t("Forecast", "नकद अनुमान (Forecast)"),
                t(f"90 days from {config.HOLDOUT_START.day} {config.HOLDOUT_START:%b %Y}, trained only on data before that date.",
                  f"{config.HOLDOUT_START.day} {config.HOLDOUT_START:%b %Y} से अगले 90 दिनों का सुरक्षित नकद अनुमान।"))
    if showing_partial_view:
        render_partial_view_notice()

    fc_res = forecast_for(biz)

    # Shortfall warning cards (D50, D40)
    if fc_res.warnings:
        for w in fc_res.warnings:
            tone = "warn"
            H(f'<div class="cc-callout {tone}">{svg(ICON_ALERT, 18, "#8A5300")}<div>'
              f'<div class="t" style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;color:#17191C">{t("Early shortfall warning", "नकद कमी की पूर्व चेतावनी")} '
              f'{tag(w.level.title(), "warn")}</div><div class="d">{esc(w.message)}</div></div></div>')
    else:
        H(f'<div class="cc-callout pos">{svg(ICON_CHECK_CIRCLE, 20)}<div><div class="t">{t("No shortfall projected", "कोई नकद कमी नहीं आएगी")}</div>'
          f'<div class="d">{t("Your balance stays above the credit limit, salary days and your cash floor for all 90 days.", "अगले 90 दिनों में वेतन दिवस और सामान्य खर्चों के बाद भी खाता सुरक्षित सीमा में रहेगा।")}'
          f'</div></div></div>')

    if fc_res.daily_points:
        st.write("")
        a, b = st.columns([1, 2], vertical_alignment="center")
        with a:
            section(t("Projected bank balance", "अनुमानित बैंक बैलेंस"))
        limit_amt = copilot.credit_limit(biz)
        with b:
            legend = (f'<span><i style="width:14px;height:10px;border-radius:2px;background:rgba(36,80,154,0.16)"></i>{t("Likely range (P10–P90)", "संभावित दायरा (P10–P90)")}</span>'
                      f'<span><i style="width:16px;height:2px;background:{ACCENT}"></i>{t("Most likely (P50)", "सबसे संभावित स्तर (P50)")}</span>')
            if limit_amt:
                legend += f'<span><i style="width:16px;border-top:2px dashed {NEG}"></i>{t("Cash-credit limit", "कैश-क्रेडिट सीमा")}</span>'
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
    page_header(t("Review", "खाता मिलान एवं समीक्षा (Review)"),
                t(f"Receipts that need you. {counts['auto']:,} others matched one rule to exactly one set of documents under strict Decision 60.",
                  f"जमा प्रविष्टियां जिन पर निर्णय बाकी है। अन्य {counts['auto']:,} प्रविष्टियों का स्वतः सही इनवॉइस से मिलान हो चुका है।"))
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
    choice = st.segmented_control("Show", options, selection_mode="single", default="All", key="queue_filter",
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
    page_header(t("Receivables", "बाजार उधारी (Receivables)"),
                t(f"Who owes you on formal invoices, as of {config.AS_OF:%d %b %Y}.",
                  f"{config.AS_OF:%d %b %Y} तक इनवॉइस के अनुसार किस पर कितना बकाया है।"))
    if showing_partial_view:
        render_partial_view_notice()

    items = open_items(pack, biz)
    cust_df = by_customer(items)
    H(f'<dl class="cc-figs">'
      f'<div><dt>{t("Total outstanding", "कुल बकाया रकम")}</dt><dd>{esc(inr(items.outstanding.sum()))}</dd></div>'
      f'<div><dt>{t("Open invoices", "खुले इनवॉइस")}</dt><dd>{len(items):,}</dd></div>'
      f'<div><dt>{t("More than 60 days late", "60 दिन से अधिक पुराने")}</dt><dd style="color:#8A5300">{len(overdue(items)):,} {t("invoices", "इनवॉइस")}</dd></div></dl>')
    st.write("")

    filters = {
        t("Over 45 days", "45 दिन से पुराने"): cust_df[cust_df.oldest_days >= 45],
        t("All customers", "सभी ग्राहक"): cust_df,
        t("Over 30 months", "30 महीने से अधिक (Limitation Act)"): cust_df[cust_df.oldest_days >= 900],
    }
    head = st.container()
    def_f = t("Over 45 days", "45 दिन से पुराने")
    c_f1, c_f2 = st.columns([3, 1.4], vertical_alignment="center")
    with c_f1:
        choice = st.segmented_control("Chasing filter", list(filters), selection_mode="single", default=def_f, key="chase_filter",
                                      format_func=lambda o: f"{o}  {len(filters[o])}",
                                      label_visibility="collapsed") or def_f
    with c_f2:
        if st.button(t("🖨️ Daily Recovery Sheet", "🖨️ दैनिक वसूली शीट"), key="btn_open_print_sheet", use_container_width=True):
            daily_print_dialog()
    filtered_cust = filters[choice]
    with head:
        H(f'<div class="cc-h2" role="heading" aria-level="2">{t("Who to call this week", "इस हफ्ते किन ग्राहकों से वसूली करनी है")}</div>'
          f'<div class="cc-muted">{t("Showing", "कुल")} {len(filtered_cust)} {t("customers owing", "ग्राहकों पर")} {esc(inr(filtered_cust.outstanding.sum()))} {t("outstanding. Largest first.", "बकाया। सबसे बड़े पहले।")}</div>')

    if filtered_cust.empty:
        H(f'<div style="display:flex;flex-direction:column;align-items:center;gap:6px;padding:48px 16px;text-align:center">'
          f'{svg(ICON_CHECK_CIRCLE, 28, SUBTLE, 1.6)}<div style="font-weight:500">{t("No customers in this list", "इस सूची में कोई ग्राहक नहीं है")}</div>'
          f'<div class="cc-muted" style="max-width:420px">{t("Balances older than 30 months can become hard to recover under the Limitation Act. They will show here first.", "30 महीने से अधिक पुराने बकाये की वसूली में कानूनी अड़चन आ सकती है।")}</div></div>')
    else:
        H(f'<div class="cc-colhead" style="grid-template-columns:3.2fr 1.2fr 1.4fr 1.7fr">'
          f'<span>{t("Customer", "ग्राहक का नाम")}</span><span>{t("Oldest invoice", "पुराना इनवॉइस")}</span><span style="text-align:right">{t("Outstanding", "बकाया रकम")}</span><span></span></div>')
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
                        salesman_note = (f"{t('Salesman', 'सेल्समैन')} {col.salesman} {t('collected', 'ने')} {inr(col.amount)} {t('on', 'को वसूले')} "
                                         f"{col.date:%d %b}; {t('not banked yet. Do not call.', 'अभी बैंक में जमा नहीं हुए। कॉल न करें।')}")
                        break

                with st.container(key=f"crow_{i}"):
                    c1, c2, c3, c4 = st.columns([3.2, 1.2, 1.4, 1.7], vertical_alignment="center")
                    note = (f'<div class="cc-row-detail" style="color:#1A6E45;display:flex;gap:6px">'
                            f'{svg(ICON_SHIELD, 14)}{esc(salesman_note)}</div>') if salesman_note else ""
                    c1.markdown(f'<div class="cc-row-title">{esc(c_name)}</div>'
                                f'<div class="cc-row-detail">{inv_count} {t("open invoices", "खुले इनवॉइस")}</div>{note}', unsafe_allow_html=True)
                    badge = tag(f"{oldest} {t('days', 'दिन')}", "warn" if oldest >= 45 else "neutral")
                    if oldest >= 900:
                        badge += " " + tag(t("30+ months (Sec 18)", "30+ महीने (Sec 18)"), "neg")
                    c2.markdown(badge, unsafe_allow_html=True)
                    c3.markdown(f'<div class="cc-amount">{esc(inr(amt))}</div>', unsafe_allow_html=True)
                    if is_hi():
                        wa_text = (f"नमस्ते {c_name} जी, {BIZ_NAME} की ओर से नमस्कार। आपके खाते का कुल बकाया {inr(amt)} है। "
                                   f"कृपया चेक कर भुगतान करें। धन्यवाद। UPI: payment@bank")
                    else:
                        wa_text = (f"Namaste {c_name}, {BIZ_NAME} se namaskar. Aapka pichla bill {inr(amt)} ka baaki hai. "
                                   f"Kripya check kar lijiye. UPI: payment@bank")
                    c4.link_button(t("WhatsApp draft", "WhatsApp तकादा"), f"https://wa.me/?text={urllib.parse.quote(wa_text)}",
                                   icon=":material/send:", use_container_width=True)

    st.write("")
    with st.expander(t(f"Full ledger · {len(cust_df)} customers", f"पूरी खाता बही · {len(cust_df)} ग्राहक")):
        st.dataframe(
            by_customer(items).assign(outstanding=lambda d: d.outstanding.map(inr)),
            hide_index=True, use_container_width=True,
            column_config={"customer_name": t("Customer", "ग्राहक"), "outstanding": t("Outstanding", "बकाया रकम"),
                           "invoices": t("Open invoices", "खुले इनवॉइस"), "oldest_days": t("Oldest (days)", "अवधि (दिन)")},
        )
    H(f'<div class="cc-note">{t("Drafts open in WhatsApp. Nothing is sent until you press send there.", "मैसेज WhatsApp में ड्राफ्ट होगा। आपके भेजने से पहले कुछ भी नहीं भेजा जाता।")}</div>')
    H(f'<div class="cc-note">{t("TDS-short invoices count as paid in full, with TDS receivable recorded separately (brief T3).", "TDS कटकर आए इनवॉइस का पूर्ण भुगतान माना जाता है और TDS अलग से दर्ज होता है।")}</div>')


# ── PAGE: ASK ────────────────────────────────────────────────────────────────
def _pick_chip():
    picked = st.session_state.get("ask_chip")
    if picked:
        actual_q = CHIP_HI_TO_EN.get(picked, picked)
        st.session_state["ask_q"] = actual_q
        st.session_state["ask_typed"] = picked


def _submit_typed():
    typed = (st.session_state.get("ask_typed") or "").strip()
    if typed:
        st.session_state["ask_q"] = typed
        st.session_state["ask_chip"] = None


def page_ask():
    page_header(t("Ask Copilot", "रोकड़ सलाहकार (Ask Copilot)"),
                t("Answers come from your books, with the rows they used. It explains; it never acts for you.",
                  "उत्तर आपके बही-खाते और बैंक रिकॉर्ड से आते हैं। यह केवल समझाता है, कोई लेन-देन नहीं करता।"),
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
                    c1.text_input(t("Your question", "आपका सवाल"), key="ask_typed",
                                  placeholder=t("For example: who owes me the most?", "उदाहरण: मुझ पर सबसे ज्यादा बकाया किसका है?"))
                    c2.form_submit_button(t("Ask", "पूछें"), type="primary", use_container_width=True, on_click=_submit_typed)

                with st.expander(t("🎙️ Speak your question (माइक से बोलें)", "🎙️ माइक से बोलकर पूछें")):
                    rec_audio = st.audio_input(t("Record voice question", "आवाज़ रिकॉर्ड करें"), key="mic_audio_input")
                    if rec_audio:
                        with st.spinner(t("Transcribing with Gemini Voice…", "आवाज़ समझी जा रही है…")):
                            transcribed = transcribe_audio(rec_audio.read(), mime_type=rec_audio.type or "audio/wav")
                            if transcribed:
                                st.session_state["ask_q"] = transcribed
                                st.session_state["ask_typed"] = transcribed
                                st.rerun()

            chips = ASK_CHIPS_HI if is_hi() else ASK_CHIPS
            st.pills(t("Try one of these", "इनमें से कोई सवाल चुनें") if not PUBLIC else t("Choose a question", "सवाल चुनें"),
                     chips, key="ask_chip", on_change=_pick_chip)
            if PUBLIC:
                H(f'<div class="cc-note">{t("Typing your own question is switched off in this preview until our safety checks pass.", "सुरक्षा जांच पूरी होने तक टाइपिंग बंद है।")}</div>')

            selected_q = st.session_state.get("ask_q")
            if selected_q:
                q_for_copilot = CHIP_HI_TO_EN.get(selected_q, selected_q)
                a = copilot.ask(biz, q_for_copilot, galla_cash=answer_galla())
                display_q = CHIP_EN_TO_HI.get(selected_q, selected_q) if is_hi() else selected_q
                if a.intent == "FACT":
                    label = f'<span class="cc-tag pos" style="display:inline-flex;gap:5px;align-items:center">' \
                            f'{svg(ICON_CHECK, 12, width=2.6)}{t("From your books", "आपके बही-खाते से")}</span>'
                elif a.intent == "UNSUPPORTED":
                    label = tag(t("Not available yet", "अभी उपलब्ध नहीं"), "neutral")
                elif a.intent == "NEEDS_CHIPS":
                    label = tag(t("Pick a question", "सवाल चुनें"), "neutral")
                else:
                    label = tag(t("Outside what I do", "कार्यक्षेत्र से बाहर"), "warn")
                H('<div class="cc-rule" style="margin:18px 0 16px"></div>'
                  f'<div style="display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;align-items:center">'
                  f'<div class="cc-h2">{esc(display_q)}</div>{label}</div>'
                  f'<div style="font-size:1.02rem;line-height:1.65;margin-top:10px;text-wrap:pretty">{esc(a.text)}</div>')

                # Hindi summary card when Hindi is selected or asked
                if is_hi() or "hindi" in selected_q.lower():
                    hi_summary = ""
                    sq = selected_q.lower()
                    if "salar" in sq or "1 अक्टूबर" in sq or "सैलरी" in sq:
                        hi_summary = "💡 <b>सरल समझ:</b> हाँ, आप 1 अक्टूबर को सैलरी आसानी से दे सकते हैं। आपके बैंक खाते में कैश-क्रेडिट लिमिट के बाद भी पर्याप्त सुरक्षित सीमा बची रहेगी।"
                    elif "who owes" in sq or "बकाया" in sq or "उधारी" in sq:
                        hi_summary = "💡 <b>सरल समझ:</b> सबसे ज्यादा बकाया लक्ष्मी सुपर मार्ट (बिबवेवाड़ी) पर है: कुल ₹7,82,910 (4 खुले इनवॉइस)।"
                    elif "cash in till" in sq or "galla" in sq or "drawer" in sq or "गल्ला" in sq or "रोकड़" in sq:
                        hi_summary = f"💡 <b>सरल समझ:</b> आज गल्ले (दराज) में गिना हुआ कुल नकद कैश {inr(answer_galla())} सुरक्षित रूप से दर्ज है।"
                    elif "worst cash dip" in sq or "कम बैलेंस" in sq or "कमी" in sq:
                        hi_summary = "💡 <b>सरल समझ:</b> अगले 90 दिनों में आपका खाता कभी भी बैंक क्रेडिट लिमिट के नीचे नहीं जाएगा। सबसे निचला स्तर सुरक्षित रहेगा।"
                    elif "loan" in sq or "लोन" in sq:
                        hi_summary = "💡 <b>सरल समझ:</b> आपको अतिरिक्त लोन लेने की जरूरत नहीं है। आपकी मौजूदा कैश-क्रेडिट सीमा और आने वाली वसूली पर्याप्त है।"
                    elif "reminder" in sq or "तकादा" in sq:
                        hi_summary = "💡 <b>सरल समझ:</b> सभी प्रमुख बकायेदारों के लिए 1-क्लिक WhatsApp तकादा संदेश 'Receivables' पेज पर तैयार हैं।"
                    if hi_summary:
                        H(f'<div style="margin-top:12px;padding:10px 14px;background:#F0FDF4;border:1px solid #BBF7D0;border-radius:6px;font-size:0.92rem;color:#166534">{hi_summary}</div>')

                if a.sources:
                    with st.expander(t(f"Sources ({len(a.sources)} rows)", f"प्रमाण व स्रोत ({len(a.sources)} प्रविष्टियां)")):
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

                with st.expander(t("📁 Upload Live Statement or Tally Prime XML", "📁 लाइव बैंक स्टेटमेंट या टैली XML अपलोड करें")):
                    st.caption(t("Upload your real bank CSV/Excel or Tally Prime XML export to verify balance ties and open bills.",
                                 "बैलेंस मिलान और इनवॉइस जांचने के लिए बैंक स्टेटमेंट (CSV/Excel) या टैली XML अपलोड करें।"))
                    u_file = st.file_uploader(t("Choose statement or Tally XML", "फाइल चुनें"), type=["csv", "xlsx", "xls", "xml"], key="setup_upload_file")
                    if u_file:
                        fn = u_file.name.lower()
                        if fn.endswith((".csv", ".xlsx", ".xls")):
                            try:
                                parse_res = parse_bank_statement(u_file.read(), u_file.name)
                                st.success(t(f"Successfully read {parse_res['rows_read']} rows! Running balances tie: {parse_res['balance_ties']}. Total credits: {inr(parse_res['summary']['total_credits'])}, Total debits: {inr(parse_res['summary']['total_debits'])}.",
                                             f"{parse_res['rows_read']} प्रविष्टियां सफलतापूर्वक पढ़ी गईं! बैलेंस मिलान: {parse_res['balance_ties']}। कुल जमा: {inr(parse_res['summary']['total_credits'])}, कुल निकासी: {inr(parse_res['summary']['total_debits'])}।"))
                                st.dataframe(parse_res["df"].head(10), use_container_width=True)
                            except Exception as e:
                                st.error(f"Error parsing statement: {e}")
                        elif fn.endswith(".xml"):
                            try:
                                t_df = parse_tally_xml(u_file.read())
                                st.success(t(f"Successfully extracted {len(t_df)} bill-wise records from Tally Prime XML!",
                                             f"टैली XML से {len(t_df)} बिल-वार प्रविष्टियां सफलतापूर्वक प्राप्त की गईं!"))
                                st.dataframe(t_df.head(10), use_container_width=True)
                            except Exception as e:
                                st.error(f"Error parsing Tally XML: {e}")

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
            label = PAGE_TITLES_HI.get(k, PAGES[k].title) if is_hi() else PAGES[k].title
            if k == "review":
                rev_c = sum(v for t, v in queue_counts(biz).items() if t in (SUGGEST, ASK))
                label = f"{t('Review', 'समीक्षा')} · {rev_c:,}"
            st.page_link(PAGES[k], label=label, icon=PAGES[k].icon)
    with st.container(key="nav_more"):
        for k in ("quality", "setup"):
            label = PAGE_TITLES_HI.get(k, PAGES[k].title) if is_hi() else PAGES[k].title
            st.page_link(PAGES[k], label=label, icon=PAGES[k].icon)
    with st.container(key="side_bottom"):
        role = st.selectbox(
            t("Viewing as", "भूमिका (Viewing as)"), ROLES, key="role", index=ROLES.index(st.session_state["role_choice"]),
            on_change=lambda: st.session_state.update(role_choice=st.session_state["role"]),
            help=t("Owner sees all books; Counter staff need the owner PIN for the cash book; "
                   "the Accountant (CA) view respects the owner's sharing setting.",
                   "मालिक सभी बही-खाते देख सकते हैं; काउंटर स्टाफ को गल्ले के लिए PIN चाहिए; "
                   "एकाउंटेंट को मालिक की अनुमति से ही गल्ला दिखता है।"),
        )
        lang = st.segmented_control(
            "Language / भाषा", ["English", "हिन्दी"], selection_mode="single", key="lang", default=st.session_state["lang_choice"],
            on_change=lambda: st.session_state.update(lang_choice=st.session_state["lang"] or "English"),
        ) or "English"
        H(f'<div class="cc-side-note">{svg(ICON_LOCK, 14)}<span>{t("Read-only. Never moves money, edits records or sends anything.", "केवल पढ़ने के लिए। यह कभी भी पैसे नहीं भेजता, रिकॉर्ड नहीं बदलता।")}</span></div>')

# A widget that lost its state falls back to the persisted choice (its index), so the two always agree.
st.session_state["biz_choice"], st.session_state["role_choice"], st.session_state["lang_choice"] = biz, role, lang

BIZ_NAME = config.BUSINESSES[biz]
share_cash_book = st.session_state.get("share_cash_book", True)
is_owner = role == "Owner"
is_counter_staff = role == "Counter staff"
is_accountant = role == "Accountant (CA)"
showing_partial_view = is_counter_staff or (is_accountant and not share_cash_book)

if msg := st.session_state.pop("toast", None):
    st.toast(msg, icon=":material/check_circle:")

current.run()
