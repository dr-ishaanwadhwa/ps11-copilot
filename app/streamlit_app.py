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
from datetime import datetime

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
from copilot.hindi import hindi_summary
from copilot.forecast import as_of, evaluate_holdout, simulate_forecast
from copilot.load import load_pack
from copilot.match import match_all
from copilot.match.audit import select_audit_sample
from copilot.match.engine import ASK, SUGGEST
from copilot.receivables import by_customer, daily_recovery_candidates, open_items, overdue
from copilot.score import score_matches, summary
from copilot.gemini import ocr_collection_slip, transcribe_audio
from copilot.masking import sanitize_slip_image
from copilot.match.names import match_retailer_name
from copilot.ingest import parse_bank_statement, parse_tally_xml
from copilot.tally import generate_ca_excel_pack, generate_statutory_ca_excel_pack, generate_tally_xml
from copilot.vault import (
    Collection,
    GallaEntry,
    VaultDB,
    cash_deposit_reporting_facts,
    compute_total_solvency,
    deposit_records_checklist,
    format_solvency_report,
    format_whatsapp_reminder,
    render_partial_view_notice,
)
from copilot.vault.models import calculate_drawer_balance

st.set_page_config(
    page_title="Cash Copilot",
    page_icon=":material/account_balance_wallet:",
    layout="wide",
    initial_sidebar_state="auto",
)

PUBLIC = os.environ.get("COPILOT_PUBLIC") == "1"


def get_business_name(b: str) -> str:
    """Return authentic business name for an SME identifier, eliminating brand bleed across commercial personas."""
    return config.BUSINESSES.get(b, f"Business-{b}")

# ── DESIGN TOKENS: "Refined Sidebar" theme (Superdesign draft 039057c0) ───────
# Satoshi for text, Cabinet Grotesk for headings and figures; warm paper canvas, near-black ink,
# a coral accent for eyebrows only, white cards with soft shadows. Status colours keep their money meaning.
INK = "#17191D"
MUTED = "#475569"
SUBTLE = "#64748B"
ACCENT = "#E76559"
NEG = "#DC2626"
FONT = "Satoshi"


def minify_css(markup: str) -> str:
    """Strip comments and collapse whitespace: the stylesheet is re-sent to the browser on every rerun."""
    markup = re.sub(r"/\*.*?\*/", "", markup, flags=re.S)
    markup = re.sub(r"\s+", " ", markup)
    return re.sub(r"\s*([{};])\s*", r"\1", markup).strip()

st.markdown(minify_css("""
<style>
@import url('https://api.fontshare.com/v2/css?f[]=satoshi@400,500,700&f[]=cabinet-grotesk@500,700,800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Devanagari:wght@400;500;600&display=swap');

:root {
  --cc-primary: #E76559; --cc-primary-hover: #D4544A; --cc-primary-wash: #FDF1EF;
  --cc-ink: #17191D; --cc-text: #2B2F36; --cc-muted: #475569; --cc-soft: #64748B; --cc-faint: #94A3B8;
  --cc-line: #EDEDE9; --cc-line-2: #E5E5E1; --cc-edge: #E8E8E4; --cc-wash: #F8FAFC; --cc-card: #FFFFFF;
  --cc-canvas: #F6F6F4; --cc-r: 12px; --cc-r-sm: 999px; --cc-card-r: 16px;
  --cc-cream: #FAF8F3; --cc-cream-line: #EBE5D8; --cc-gold: #AE8A43;
  --cc-pos: #059669; --cc-pos-line: #A7F3D0; --cc-pos-wash: #F0FBF6;
  --cc-warn: #B45309; --cc-warn-line: #FCD34D; --cc-warn-wash: #FFFBEB;
  --cc-neg: #DC2626; --cc-neg-line: #FCA5A5; --cc-neg-wash: #FEF5F5;
  --cc-sans: 'Satoshi', 'IBM Plex Sans Devanagari', system-ui, -apple-system, 'Segoe UI', sans-serif;
  --cc-serif: 'Cabinet Grotesk', 'Satoshi', 'IBM Plex Sans Devanagari', system-ui, sans-serif;
  --cc-mono: 'Cabinet Grotesk', 'Satoshi', system-ui, sans-serif;
  --cc-ease: cubic-bezier(.22, 1, .36, 1);
  --cc-float: 0 8px 28px rgba(23,25,29,0.06);
  --cc-float-hover: 0 18px 42px rgba(23,25,29,0.10);
  --cc-lift: 0 4px 14px rgba(23,25,29,0.045);
  --cc-btn: 0 1px 2px rgba(23,25,29,0.05);
  --cc-btn-red: 0 6px 16px -6px rgba(23,25,29,0.45);
}

/* type: Inter everywhere except Streamlit's icon glyphs */
html, body, .stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button,
.stApp td, .stApp th, .stApp div, .stApp span:not([data-testid*="Icon"]):not([class*="material"]) {
  font-family: var(--cc-sans);
}
/* layout: a soft grey canvas so white cards, the top bar and the sidebar read as separate layers */
.stApp { color: var(--cc-text); background: var(--cc-canvas); -webkit-font-smoothing: antialiased; }
/* Streamlit sizes markdown blocks to the parent's outer width; inside padded cards that pushed text past the edge */
.stApp [data-testid="stMarkdown"] { width: 100% !important; max-width: 100%; }
.stApp [data-testid="stElementContainer"] > * { max-width: 100%; }
.cc-muted, .cc-note, .cc-sub, .cc-h2, .cc-row-detail { overflow-wrap: break-word; }
.stApp h1, .stApp h2, .stApp h3 { font-family: var(--cc-serif) !important; letter-spacing: -0.01em; color: var(--cc-ink); }

/* chrome */
header[data-testid="stHeader"] { background: transparent; pointer-events: none; }
header[data-testid="stHeader"] * { pointer-events: auto; }
[data-testid="stDecoration"] { display: none; }
.stAppDeployButton, [data-testid="stAppDeployButton"] { display: none; }
[data-testid="stMain"] { overflow-x: hidden; }
[data-testid="stMainBlockContainer"], .block-container { max-width: 1360px; padding: 2.4rem 2.5rem 1.5rem; }
@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"], .block-container { padding: 3.6rem 1rem 1.5rem; }
}

/* top bar (Refined Sidebar layout): a light status row; the page links live in the sidebar */
.st-key-topbar { margin-bottom: 30px; }
.st-key-topbar [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
.cc-status { display: flex; align-items: center; flex-wrap: wrap; gap: 6px 10px; font-size: 0.86rem; color: var(--cc-soft); }
.cc-status .cc-dot { width: 8px; height: 8px; color: #10B981; box-shadow: 0 0 0 3px rgba(16,185,129,0.14); }
.cc-status .sep { color: #D1D5DB; }
.st-key-tacts { flex-direction: row !important; justify-content: flex-end; align-items: center; gap: 10px !important; }
.st-key-tacts > div, .st-key-tacts [data-testid="stPageLink"], .st-key-tacts [data-testid="stPageLink"] > div { width: auto !important; flex: 0 0 auto !important; }
.st-key-tacts [data-testid="stPageLink-NavLink"] { min-height: 40px; padding: 0 16px; border-radius: 999px; gap: 8px; background: #FFFFFF;
  border: 1px solid var(--cc-line-2); box-shadow: var(--cc-btn); transition: background 150ms ease; }
.st-key-tacts [data-testid="stPageLink-NavLink"]:hover { background: var(--cc-wash); }
.st-key-tacts [data-testid="stPageLink-NavLink"] p { font-size: 0.84rem; color: var(--cc-muted); }
.st-key-tacts [data-testid="stPageLink-NavLink"] [data-testid="stIconMaterial"] { color: var(--cc-soft); }
/* phones: Streamlit folds the sidebar away, so the brand and a scrolling page menu appear at the top instead */
.cc-brand { display: none; align-items: center; gap: 12px; white-space: nowrap; margin-bottom: 8px; }
.cc-brand span { font-family: var(--cc-serif) !important; font-size: 1.2rem; font-weight: 700; letter-spacing: -0.015em; color: var(--cc-ink); }
.cc-brand svg { flex: none; }
.st-key-tnav { display: none !important; }
@media (max-width: 640px) {
  .cc-brand { display: flex; }
  .st-key-tacts { display: none !important; }
  .st-key-tnav { display: flex !important; flex-direction: row !important; flex-wrap: nowrap; align-items: center; gap: 0 18px !important;
    overflow-x: auto; scrollbar-width: none; -webkit-overflow-scrolling: touch; background: #FFFFFF; border: 1px solid var(--cc-edge);
    border-radius: 16px; padding: 2px 16px; box-shadow: var(--cc-lift); }
  .st-key-tnav::-webkit-scrollbar { display: none; }
  .st-key-tnav > div, .st-key-tnav [data-testid="stPageLink"], .st-key-tnav [data-testid="stPageLink"] > div { width: auto !important; flex: 0 0 auto !important; }
  .st-key-tnav [data-testid="stPageLink-NavLink"] { background: transparent !important; padding: 10px 0 !important; min-height: 44px; }
  .st-key-tnav [data-testid="stPageLink-NavLink"] > span:has([data-testid="stIconMaterial"]) { display: none; }
  .st-key-tnav [data-testid="stPageLink-NavLink"] p { font-size: 0.7rem !important; font-weight: 700 !important; letter-spacing: 0.1em;
    text-transform: uppercase; color: var(--cc-soft); white-space: nowrap; }
}

/* footer */
.cc-footer { margin-top: 64px; padding: 26px 0 6px; border-top: 1px solid var(--cc-line-2); display: flex; flex-wrap: wrap;
  justify-content: space-between; gap: 12px 40px; font-size: 0.6rem; font-weight: 700; letter-spacing: 0.26em;
  text-transform: uppercase; color: var(--cc-faint); }
.cc-footer .links { display: flex; flex-wrap: wrap; gap: 12px 36px; }

/* sidebar (Refined Sidebar draft): brand, workspace card, pages, security, account */
[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid var(--cc-line-2); box-shadow: 8px 0 28px -16px rgba(17,24,39,0.22); }
[data-testid="stSidebarUserContent"] { padding: 0 24px 28px; }
.cc-sbrand { display: flex; align-items: center; gap: 12px; margin-bottom: 34px; }
.cc-sbrand + .cc-slabel { margin-bottom: 12px; }
.cc-sbrand svg { width: 40px; height: 40px; flex: none; border-radius: 14px; box-shadow: 0 6px 16px rgba(17,24,39,0.14); }
.cc-sbrand .n { font-family: var(--cc-serif) !important; font-size: 1.22rem; font-weight: 700; letter-spacing: -0.015em; color: var(--cc-ink); line-height: 1.15; }
.cc-sbrand .s { font-size: 0.6rem; font-weight: 600; letter-spacing: 0.16em; text-transform: uppercase; color: var(--cc-faint); margin-top: 4px; }
.cc-slabel { font-size: 0.6rem; font-weight: 700; letter-spacing: 0.22em; text-transform: uppercase; color: var(--cc-faint); }
/* business picker drawn as the draft's workspace card: the name on top, trade and city underneath */
.st-key-bizpick { gap: 0 !important; }
.st-key-bizpick [data-baseweb="select"] > div { min-height: 62px; border-radius: 16px !important; background: var(--cc-wash) !important;
  box-shadow: 0 4px 14px rgba(17,24,39,0.045) !important; align-items: flex-start; padding-top: 6px; cursor: pointer;
  transition: background 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease; }
.st-key-bizpick [data-baseweb="select"] > div:hover { background: #FFFFFF !important; border-color: #D1D5DB !important; box-shadow: var(--cc-lift) !important; }
.st-key-bizpick [data-baseweb="select"] > div > div:first-child { font-size: 0.92rem; font-weight: 600; color: var(--cc-ink); letter-spacing: -0.01em; }
.st-key-bizpick [data-baseweb="select"] > div > div:last-child { padding-top: 4px; }
.cc-bizsub { position: relative; z-index: 1; pointer-events: none; margin-top: -32px; padding: 0 40px 14px 11px; font-size: 0.72rem;
  color: var(--cc-faint); letter-spacing: 0.02em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
/* page links: icon and label; the open page becomes a dark pill (set per page in render_topbar) */
.st-key-snav, .st-key-snav2 { gap: 4px !important; }
.st-key-snav { margin-top: 10px; }
.st-key-snav2 { border-top: 1px solid var(--cc-line); padding-top: 12px; }
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] { min-height: 44px; padding: 0 14px; border-radius: 12px; gap: 12px; margin: 0;
  transition: background 0.3s ease, transform 0.3s ease, box-shadow 0.3s ease; }
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] p { font-size: 0.9rem; font-weight: 500; letter-spacing: -0.005em;
  text-transform: none; color: var(--cc-soft); transition: color 0.3s ease; }
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] [data-testid="stIconMaterial"] { color: var(--cc-faint); font-size: 1.2rem; transition: color 0.3s ease; }
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover { background: var(--cc-wash); transform: translateX(2px); }
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover p,
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover [data-testid="stIconMaterial"] { color: var(--cc-ink); }
.st-key-snav2 [data-testid="stPageLink-NavLink"] { min-height: 40px; }
.st-key-snav2 [data-testid="stPageLink-NavLink"] p { font-size: 0.84rem; }
/* security: who is viewing, the vault card, PIN */
.st-key-ssec { border-top: 1px solid var(--cc-line); padding-top: 22px; margin-top: 6px; gap: 12px !important; }
.cc-shead { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.cc-shield { width: 28px; height: 28px; border-radius: 8px; display: grid; place-items: center; background: #ECFDF5; color: #059669; }
.cc-vcard { border-radius: 16px; background: #FAF8F3; border: 1px solid #EBE5D8; padding: 14px 16px; margin: 4px 0 18px;
  box-shadow: 0 4px 14px rgba(174,138,67,0.06); }
.cc-vcard .t { display: flex; align-items: center; gap: 9px; font-size: 0.9rem; font-weight: 600; color: var(--cc-ink); letter-spacing: -0.01em; }
.cc-vcard .t .cc-dot { width: 8px; height: 8px; }
.cc-vcard.on .cc-dot { color: #10B981; box-shadow: 0 0 0 3px rgba(16,185,129,0.14); }
.cc-vcard.off .cc-dot { color: var(--cc-neg); box-shadow: 0 0 0 3px rgba(220,38,38,0.12); }
.cc-vcard .d { font-size: 0.75rem; color: var(--cc-soft); line-height: 1.55; margin-top: 8px; }
.st-key-sprefs { border-top: 1px solid var(--cc-line); padding-top: 20px; margin-top: 6px; }
/* account: who this workspace belongs to */
.cc-sacct { display: flex; align-items: center; gap: 12px; border-top: 1px solid var(--cc-line); padding-top: 18px; margin-top: 10px; }
.cc-sacct .av { width: 40px; height: 40px; flex: none; border-radius: 50%; background: #F3F4F6; border: 1px solid var(--cc-line-2);
  display: grid; place-items: center; font-size: 0.74rem; font-weight: 700; color: var(--cc-ink); box-shadow: 0 1px 2px rgba(17,24,39,0.05); }
.cc-sacct > div:last-child { min-width: 0; }
.cc-sacct .n { font-size: 0.88rem; font-weight: 600; color: var(--cc-ink); letter-spacing: -0.01em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cc-sacct .r { font-size: 0.72rem; color: var(--cc-faint); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cc-dot { display: inline-block; flex: none; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }

/* widget labels read like the design's small caps */
.stApp [data-testid="stWidgetLabel"] p { font-size: 0.64rem !important; font-weight: 700 !important; letter-spacing: 0.18em;
  text-transform: uppercase; color: var(--cc-soft); }

/* inputs */
.stApp [data-baseweb="input"], .stApp [data-baseweb="base-input"], .stApp [data-baseweb="select"] > div,
.stApp [data-baseweb="textarea"], div[role="dialog"] [data-baseweb="input"], div[role="dialog"] [data-baseweb="base-input"] {
  background: #FFFFFF !important; border: 1px solid var(--cc-line-2) !important; border-radius: 12px !important;
  box-shadow: 0 1px 2px rgba(17,24,39,0.04); }
.stApp [data-baseweb="input"] [data-baseweb="base-input"] { border: 0 !important; }
.stApp [data-baseweb="input"]:focus-within, .stApp [data-baseweb="select"] > div:focus-within { border-color: var(--cc-ink) !important;
  box-shadow: 0 0 0 3px rgba(17,24,39,0.06); }
.stApp input::placeholder, .stApp textarea::placeholder { color: var(--cc-faint); }

/* buttons: softly rounded, uppercase, tracked, with a light shadow */
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
  min-height: 46px; border-radius: var(--cc-r); padding: 6px 22px; box-shadow: var(--cc-btn); transition: all 150ms ease; }
.stButton > button:hover, .stFormSubmitButton > button:hover, .stDownloadButton > button:hover { transform: translateY(-1px); }
.stButton > button:active, .stFormSubmitButton > button:active, .stDownloadButton > button:active { transform: translateY(0); }
.stButton > button p, .stFormSubmitButton > button p, .stDownloadButton > button p {
  font-size: 0.68rem !important; font-weight: 700 !important; letter-spacing: 0.16em; text-transform: uppercase; line-height: 1.5; }
.stButton > button p, .stFormSubmitButton > button p { white-space: nowrap; }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
  background: var(--cc-primary); border: 1px solid var(--cc-primary); color: #FFFFFF; box-shadow: var(--cc-btn-red); }
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover { background: var(--cc-primary-hover); border-color: var(--cc-primary-hover); }
.stButton > button[kind="secondary"], .stFormSubmitButton > button[kind="secondary"], .stDownloadButton > button[kind="secondary"] {
  background: #FFFFFF; border: 1px solid var(--cc-ink); color: var(--cc-ink); }
.stButton > button[kind="secondary"]:hover, .stDownloadButton > button[kind="secondary"]:hover { background: var(--cc-wash); color: var(--cc-ink); border-color: var(--cc-ink); }
.stLinkButton > a { min-height: 46px; border-radius: var(--cc-r); box-shadow: var(--cc-btn); border: 1px solid var(--cc-ink); color: var(--cc-ink); display: inline-flex; align-items: center; padding: 0 18px; }
.stLinkButton > a p { font-weight: 700; font-size: 0.68rem; letter-spacing: 0.16em; text-transform: uppercase; white-space: nowrap; }
/* "go to page" links: underlined caps, red arrow */
[class*="st-key-go_"] .stButton { display: flex; justify-content: flex-end; }
[class*="st-key-go_"] button { background: transparent !important; border: 0 !important; box-shadow: none !important;
  min-height: 44px; padding: 0 2px !important; white-space: nowrap; }
[class*="st-key-go_"] button p { color: var(--cc-ink) !important; border-bottom: 1px solid var(--cc-ink); padding-bottom: 3px; }
[class*="st-key-go_"] button [data-testid="stIconMaterial"] { color: var(--cc-primary); }
[class*="st-key-go_"] button:hover p { color: var(--cc-primary) !important; border-color: var(--cc-primary); }

/* segmented controls and pills: softly rounded chips */
.stApp [data-testid^="stBaseButton-segmented_control"], .stApp [data-testid^="stBaseButton-pills"] {
  border-radius: var(--cc-r) !important; border: 1px solid var(--cc-line-2) !important; background: #FFFFFF !important; min-height: 40px;
  box-shadow: var(--cc-btn); transition: border-color 150ms ease, box-shadow 150ms ease; }
.stApp [data-testid^="stBaseButton-pills"]:hover { border-color: var(--cc-ink) !important; box-shadow: var(--cc-lift); }
/* a segmented control is one joined strip: round only its outer corners */
.stApp [data-testid^="stBaseButton-segmented_control"]:not(:first-child):not(:last-child) { border-radius: 0 !important; }
.stApp [data-testid^="stBaseButton-segmented_control"]:first-child:not(:last-child) { border-radius: var(--cc-r) 0 0 var(--cc-r) !important; }
.stApp [data-testid^="stBaseButton-segmented_control"]:last-child:not(:first-child) { border-radius: 0 var(--cc-r) var(--cc-r) 0 !important; }
.stApp [data-testid^="stBaseButton-segmented_control"] p, .stApp [data-testid^="stBaseButton-pills"] p {
  font-size: 0.66rem !important; font-weight: 700 !important; letter-spacing: 0.12em; text-transform: uppercase; color: var(--cc-ink); }
.stApp [data-testid="stBaseButton-segmented_controlActive"], .stApp [data-testid="stBaseButton-pillsActive"] {
  background: var(--cc-ink) !important; border-color: var(--cc-ink) !important; }
.stApp [data-testid="stBaseButton-segmented_controlActive"] p, .stApp [data-testid="stBaseButton-pillsActive"] p { color: #FFFFFF !important; }
/* question pills are whole sentences: keep them in sentence case so they stay easy to read */
.stApp [data-testid^="stBaseButton-pills"] p { font-size: 0.84rem !important; font-weight: 500 !important; letter-spacing: 0; text-transform: none; }

/* the "Ask about your cash" field in each page header */
.st-key-askfield [data-testid="stPageLink-NavLink"] { min-height: 48px; padding: 0 16px; border: 1px solid var(--cc-line-2);
  border-radius: 14px; background: #FFFFFF; box-shadow: var(--cc-lift); transition: border-color 150ms ease, box-shadow 150ms ease; }
.st-key-askfield [data-testid="stPageLink-NavLink"]:hover { border-color: var(--cc-ink); background: #FFFFFF; }
.st-key-askfield [data-testid="stPageLink-NavLink"] p, .st-key-askfield [data-testid="stPageLink-NavLink"] span { color: var(--cc-faint); font-size: 0.86rem; }

/* Ask Copilot: the typed-question card */
.st-key-ask_box { background: #FFFFFF; border: 1px solid var(--cc-edge); border-radius: 24px; padding: 22px 24px 8px; box-shadow: var(--cc-float);
  gap: 10px !important; margin-bottom: 18px; }
.cc-ask-head { display: flex; align-items: center; gap: 10px; font-family: var(--cc-serif) !important; font-size: 1.15rem; font-weight: 700; color: var(--cc-ink); }
.cc-ask-head span { font-family: var(--cc-serif) !important; }
.st-key-ask_box .cc-note { margin: 6px 0 18px; }
.st-key-ask_box [data-baseweb="input"] { min-height: 50px; border-radius: var(--cc-r) !important; background: var(--cc-wash) !important; }
.st-key-ask_box [data-baseweb="input"] input { font-size: 0.98rem; }
.st-key-ask_box .stFormSubmitButton > button { min-height: 52px; }

/* row lists */
[class*="st-key-row_"], [class*="st-key-krow_"], [class*="st-key-crow_"] { border-bottom: 1px solid var(--cc-line); padding: 14px 0; gap: 0; }
.st-key-rows { gap: 0 !important; }
.st-key-krows, .st-key-crows { gap: 14px !important; }
/* overview action rows: each one is its own white card */
[class*="st-key-row_"] { background: #FFFFFF; border: 1px solid var(--cc-edge); border-radius: 20px; padding: 18px 24px;
  box-shadow: var(--cc-lift); transition: box-shadow 0.25s ease; }
[class*="st-key-row_"]:hover { box-shadow: var(--cc-float); }
[class*="st-key-row_"] > * { width: 100% !important; max-width: 100%; }
/* markdown blocks carry a -1rem bottom margin; in the top bar it pushed the brand and name below centre */
.st-key-topbar [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }

/* surfaces: every card is white, rounded and lifted off the grey canvas */
.st-key-cc_panel { background: #FFFFFF; border: 1px solid var(--cc-edge); border-radius: 24px; padding: 28px; box-shadow: var(--cc-float);
  min-width: 0; container-type: inline-size; overflow-wrap: anywhere; }
.st-key-cc_panel .cc-hero { font-size: clamp(1.15rem, 15cqw, 2.75rem); }
/* Streamlit gives children of a keyed container its outer width in px; inside these padded cards, fit them to the inner width */
.st-key-cc_panel > *, .st-key-ask_box > * { width: 100% !important; max-width: 100%; }
.st-key-cc_panel [data-testid="stExpander"] details { box-shadow: none; background: var(--cc-wash); border-radius: 16px; }
/* st.container(border=True). Streamlit 1.40 gives only bordered wrappers a non-empty style class */
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 24px; border-color: var(--cc-edge) !important; }
[data-testid="stVerticalBlockBorderWrapper"]:not(.st-emotion-cache-0) { background: #FFFFFF; box-shadow: var(--cc-float); padding: 22px 24px; }
[data-testid="stVerticalBlockBorderWrapper"]:not(.st-emotion-cache-0) [data-testid="stExpander"] details { box-shadow: none; background: var(--cc-wash); }
[data-testid="stExpander"] details { border: 1px solid var(--cc-edge) !important; border-radius: 24px; background: #FFFFFF; box-shadow: var(--cc-lift); overflow: hidden; }
[data-testid="stExpander"] summary { padding: 16px 22px; }
[data-testid="stExpander"] summary:hover { color: var(--cc-ink); }
[data-testid="stExpander"] summary p { font-family: var(--cc-serif) !important; font-weight: 700; font-size: 1.02rem; color: var(--cc-ink); }
[data-testid="stExpander"] details[open] > summary { border-bottom: 1px solid var(--cc-line); }
[data-testid="stExpanderDetails"] { padding: 18px 22px 22px !important; }
[data-testid="stAlert"] { border-radius: 16px; }
[data-testid="stDataFrame"] { border: 1px solid var(--cc-edge); border-radius: 16px; overflow: hidden; background: #FFFFFF; box-shadow: var(--cc-lift); }
div[role="dialog"] { border-radius: 24px !important; }
div[role="dialog"] h2, div[role="dialog"] [data-testid="stDialogHeader"] div { font-family: var(--cc-serif) !important; }

/* page header */
.cc-eyebrow { font-size: 0.68rem; font-weight: 700; letter-spacing: 0.3em; text-transform: uppercase; color: var(--cc-primary); }
.cc-title { font-family: var(--cc-serif) !important; font-size: clamp(2rem, 4vw, 2.9rem); font-weight: 700; letter-spacing: -0.02em;
  line-height: 1.1; color: var(--cc-ink); margin-top: 12px; }
.cc-sub { font-size: 0.98rem; color: var(--cc-soft); margin-top: 12px; max-width: 640px; line-height: 1.6; }
.cc-meta { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 16px; }
/* on phones the header's ask field stacks under the badges; keep it clear of them */
@media (max-width: 640px) { .cc-meta { margin-bottom: 24px; } }
.cc-rule { border-top: 1px solid var(--cc-line-2); margin: 24px 0 28px; }

/* page parts (rendered with st.markdown) */
.cc-h2 { font-family: var(--cc-serif) !important; font-size: 1.32rem; font-weight: 700; letter-spacing: -0.01em; color: var(--cc-ink);
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.cc-label { font-size: 0.64rem; font-weight: 700; letter-spacing: 0.2em; text-transform: uppercase; color: var(--cc-soft); }
.stApp .cc-hero { font-family: var(--cc-mono) !important; font-size: clamp(2rem, 4.5vw, 2.6rem); font-weight: 700; letter-spacing: -0.04em;
  line-height: 1.1; font-variant-numeric: tabular-nums; margin: 8px 0; color: var(--cc-ink); }
.cc-muted { font-size: 0.84rem; color: var(--cc-soft); line-height: 1.55; }
.cc-note { font-size: 0.74rem; color: var(--cc-soft); line-height: 1.5; }
.cc-num { font-variant-numeric: tabular-nums; }

.cc-tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 20px; padding: 8px 2px 16px; }
@media (max-width: 900px) {
  .cc-tiles { display: flex; overflow-x: auto; scroll-snap-type: x mandatory; -webkit-overflow-scrolling: touch; }
  .cc-tile { min-width: 200px; flex-shrink: 0; scroll-snap-align: start; }
}
.cc-tile { position: relative; display: flex; flex-direction: column; gap: 4px; padding: 24px 26px; background: #FFFFFF;
  border: 1px solid var(--cc-edge); border-radius: 24px; box-shadow: var(--cc-float); transition: transform 0.3s ease, box-shadow 0.3s ease; }
.cc-tile:hover { transform: translateY(-4px); box-shadow: var(--cc-float-hover); }
.cc-tile .l { font-size: 0.62rem; font-weight: 700; letter-spacing: 0.2em; text-transform: uppercase; color: var(--cc-soft); line-height: 1.5; }
.stApp .cc-tile .v { font-family: var(--cc-mono) !important; font-size: 1.5rem; font-weight: 700; letter-spacing: -0.04em; color: var(--cc-ink);
  font-variant-numeric: tabular-nums; margin-top: 10px; line-height: 1.15; }
.cc-tile .s { font-size: 0.62rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--cc-soft);
  display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin-top: 12px; line-height: 1.5; }
.stApp .cc-tile.big .v { font-size: 1.85rem; }
.cc-tile.accent, .cc-tile.dark { background: var(--cc-ink); border-color: var(--cc-ink); }
.cc-tile.accent .l, .cc-tile.dark .l { color: #9CA3AF; }
.stApp .cc-tile.accent .v, .stApp .cc-tile.dark .v { color: #FFFFFF !important; }
.cc-tile.accent .s, .cc-tile.dark .s { color: var(--cc-primary); }
.cc-tile.pos .l::before, .cc-tile.warn .l::before, .cc-tile.neg .l::before, .cc-tile.info .l::before {
  content: ""; display: inline-block; width: 6px; height: 6px; border-radius: 50%; margin-right: 8px; vertical-align: 1px; }
.cc-tile.pos .l::before { background: var(--cc-pos); }
.cc-tile.warn .l::before { background: #F59E0B; }
.cc-tile.neg .l::before { background: var(--cc-neg); }
.cc-tile.info .l::before { background: var(--cc-ink); }
.stApp .cc-tile.pos .v { color: var(--cc-pos); }
.stApp .cc-tile.warn .v { color: var(--cc-warn); }
.stApp .cc-tile.neg .v { color: var(--cc-neg); }
.cc-demo { display: inline-flex; align-items: center; font-size: 0.58rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--cc-soft); border: 1px solid var(--cc-line-2); border-radius: 4px; padding: 1px 6px; line-height: 1.5; background: #FFFFFF; }

/* tags and badges: lightly rounded, tracked caps */
.cc-tag, .cc-badge { display: inline-flex; align-items: center; gap: 6px; font-size: 0.6rem; font-weight: 700; letter-spacing: 0.14em;
  text-transform: uppercase; border: 1px solid var(--cc-line-2); border-radius: var(--cc-r-sm); padding: 4px 10px; line-height: 1.45;
  white-space: nowrap; color: var(--cc-ink); background: #FFFFFF; }
.cc-tag.pos, .cc-badge.pos { color: var(--cc-pos); border-color: var(--cc-pos-line); background: #FFFFFF; }
.cc-tag.warn, .cc-badge.warn { color: var(--cc-warn); border-color: var(--cc-warn-line); background: #FFFFFF; }
.cc-tag.neg, .cc-badge.neg { color: var(--cc-neg); border-color: var(--cc-neg-line); background: #FFFFFF; }
.cc-tag.info, .cc-badge.info { color: var(--cc-ink); border-color: var(--cc-ink); background: #FFFFFF; }
.cc-tag.neutral, .cc-badge.neutral { color: var(--cc-muted); border-color: var(--cc-line-2); background: #FFFFFF; }
.cc-status { display: flex; align-items: center; gap: 10px; padding: 12px 16px; border-radius: 16px; }
.cc-status .t { font-weight: 700; font-size: 0.9rem; }
.cc-status .d { font-size: 0.76rem; }
.cc-status.pos { background: var(--cc-pos-wash); color: var(--cc-pos); }
.cc-status.warn { background: var(--cc-warn-wash); color: #7A4A00; }
.cc-status.neg { background: var(--cc-neg-wash); color: var(--cc-neg); }
.cc-callout { display: flex; gap: 12px; align-items: flex-start; padding: 16px 18px; border-radius: 16px; }
.cc-callout .t { font-weight: 700; }
.cc-callout .d { font-size: 0.85rem; }
.cc-callout.pos { background: var(--cc-pos-wash); color: var(--cc-pos); }
.cc-callout.pos .d { color: #065F46; }
.cc-callout.warn { background: var(--cc-warn-wash); color: #4A3200; }
.cc-callout.neutral { background: var(--cc-wash); color: var(--cc-muted); }
.cc-row-title { font-weight: 600; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; color: var(--cc-ink); }
.cc-row-detail { font-size: 0.82rem; color: var(--cc-soft); margin-top: 2px; }
.stApp .cc-amount { font-family: var(--cc-mono) !important; font-weight: 700; font-variant-numeric: tabular-nums; text-align: right; }
.cc-colhead { display: grid; gap: 16px; font-size: 0.62rem; font-weight: 700; letter-spacing: 0.2em; text-transform: uppercase; color: var(--cc-soft); padding: 4px 0; }
.cc-dl { display: flex; flex-direction: column; border-top: 1px solid var(--cc-line); margin: 0; }
.cc-dl > div { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--cc-line); }
.stApp .cc-dl dt { color: var(--cc-soft); font-weight: 400; margin: 0; padding: 0; }
.stApp .cc-dl dd { margin: 0; padding: 0; font-family: var(--cc-mono) !important; font-weight: 700; font-variant-numeric: tabular-nums; text-align: right; color: var(--cc-ink); }
.cc-figs { display: flex; flex-wrap: wrap; gap: 16px 48px; margin: 0; }
.stApp .cc-figs dt { font-size: 0.64rem; font-weight: 700; letter-spacing: 0.2em; text-transform: uppercase; color: var(--cc-soft); margin: 0; padding: 0; }
.stApp .cc-figs dd { margin: 0; padding: 0; font-family: var(--cc-mono) !important; font-size: 1.7rem; font-weight: 700; letter-spacing: -0.04em; font-variant-numeric: tabular-nums; }
.cc-scroll { overflow-x: auto; }
.cc-table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; font-size: 0.86rem; }
.cc-table th { font-size: 0.6rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: var(--cc-soft); text-align: right;
  padding: 14px 10px; border-bottom: 1px solid var(--cc-line); white-space: nowrap; }
.cc-table td { text-align: right; padding: 18px 10px; border-bottom: 1px solid var(--cc-line); vertical-align: top; color: var(--cc-ink); }
.stApp .cc-table td:not(:first-child) { font-family: var(--cc-mono) !important; font-size: 0.82rem; font-weight: 500; }
.stApp .cc-table th, .stApp .cc-table td { border-left: 0; border-right: 0; border-top: 0; background: transparent; }
.stApp .cc-table tr { border: 0; background: transparent; }
.stApp .cc-table tbody tr:hover td { background: #FAFAFB; }
.cc-table th:first-child, .cc-table td:first-child { text-align: left; padding-left: 0; }
.cc-table td:first-child { font-weight: 700; white-space: nowrap; }
.stApp .cc-table tr.hl td { background: var(--cc-primary-wash); }
.cc-table tr.hl td:first-child { padding-left: 10px; box-shadow: inset 3px 0 0 var(--cc-primary); }
.cc-table .range { display: block; font-size: 0.7rem; color: var(--cc-faint); margin-top: 2px; }
.cc-table .up { color: var(--cc-pos); }
.cc-table .down { color: var(--cc-neg); }
.cc-mono { font-family: var(--cc-mono) !important; }
.cc-narr { padding: 12px 14px; background: var(--cc-wash); border-radius: 12px; font-size: 0.76rem; line-height: 1.6;
  color: var(--cc-muted); overflow-wrap: anywhere; }
.cc-legend { display: flex; flex-wrap: wrap; gap: 6px 22px; font-size: 0.6rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--cc-soft); }
.cc-legend span { display: inline-flex; align-items: center; gap: 8px; }
.cc-legend i { display: inline-block; }
.cc-steps { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-bottom: 14px; }
.cc-steps .bar { height: 3px; background: var(--cc-line); margin-bottom: 10px; }
.cc-steps .on .bar { background: var(--cc-primary); }
.cc-steps .n { font-size: 0.6rem; font-weight: 700; letter-spacing: 0.2em; text-transform: uppercase; color: var(--cc-soft); }
.cc-steps .lbl { font-size: 0.84rem; color: var(--cc-soft); margin-top: 2px; }
.cc-steps .cur .lbl { font-weight: 700; color: var(--cc-ink); }
.cc-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 12px; color: var(--cc-muted); }
.stApp .cc-list li { display: flex; gap: 10px; margin: 0; padding: 0; font-size: 0.9rem; line-height: 1.55; }
.stApp .cc-list.sm li { font-size: 0.84rem; }
.cc-list svg { flex: none; margin-top: 2px; }
.cc-side-note { display: flex; gap: 8px; align-items: flex-start; padding: 0 4px; font-size: 0.72rem; line-height: 1.5; color: var(--cc-soft); }
.cc-lock { display: grid; place-items: center; width: 40px; height: 40px; border-radius: 12px; background: var(--cc-wash); }
.cc-onboard { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 18px; background: #FFFFFF;
  border: 1px solid var(--cc-line); border-radius: 16px; box-shadow: var(--cc-lift); font-size: 0.84rem; color: var(--cc-muted); margin-bottom: 14px; }
.cc-onboard b { color: var(--cc-ink); }

/* overview hero: one big floating card */
.cc-cockpit-hero { background: #FFFFFF; border: 1px solid var(--cc-edge); border-radius: 32px; padding: 34px 40px 30px;
  box-shadow: var(--cc-float); margin-bottom: 28px; }
.cc-cockpit-tag { display: inline-flex; align-items: center; gap: 8px; font-size: 0.66rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.3em; color: var(--cc-primary); }
.cc-badge-pill { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: var(--cc-r-sm); font-size: 0.6rem;
  font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; background: #FFFFFF; color: var(--cc-pos); border: 1px solid var(--cc-pos-line); }
.cc-payroll-banner { margin-top: 22px; padding: 14px 18px; border-radius: 16px; background: var(--cc-pos-wash); border: 1px solid #D1FAE5;
  font-size: 0.86rem; color: #065F46; display: flex; align-items: center; gap: 10px; }
.cc-wa-btn { background: var(--cc-ink); color: #FFFFFF !important; text-decoration: none !important; border-radius: var(--cc-r); padding: 11px 18px;
  box-shadow: 0 1px 2px rgba(17,24,39,0.20), 0 6px 14px -6px rgba(17,24,39,0.45);
  font-size: 0.62rem; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase; display: inline-flex; align-items: center;
  gap: 8px; white-space: nowrap; transition: background 150ms ease; }
.cc-wa-btn:hover { background: #000000; color: #FFFFFF !important; }
.cc-fanchart-card, .cc-card-modern { background: #FFFFFF; border: 1px solid var(--cc-edge); border-radius: 32px; padding: 30px 34px;
  box-shadow: var(--cc-float); margin-bottom: 24px; transition: transform 0.3s ease, box-shadow 0.3s ease; }
.cc-fanchart-card { margin-top: 18px; }
.cc-card-modern:hover { transform: translateY(-2px); box-shadow: var(--cc-float-hover); }
.cc-card-modern[style*="border-left"], .cc-action-card[style*="border-left"] { border-radius: 20px; }
.cc-action-card { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; padding: 18px 24px; background: #FFFFFF;
  border: 1px solid var(--cc-line); border-radius: 20px; margin-bottom: 12px; gap: 16px; box-shadow: var(--cc-lift);
  transition: transform 0.3s ease, box-shadow 0.3s ease; }
.cc-action-card:hover { transform: translateY(-2px); box-shadow: var(--cc-float); }
.cc-grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 12px 0; }
@media (max-width: 900px) { .cc-grid-4 { grid-template-columns: repeat(2, 1fr); gap: 14px; } }
@media (max-width: 520px) { .cc-grid-4 { grid-template-columns: 1fr; } .cc-cockpit-hero, .cc-card-modern { padding: 24px 22px; border-radius: 24px; } }

/* ── HOVER INFO TOOLTIPS ── */
[data-tip] { position: relative; cursor: help; }
[data-tip]::after {
  content: attr(data-tip); position: absolute; bottom: calc(100% + 8px); left: 50%; transform: translateX(-50%) translateY(4px);
  background: #111827; color: #F9FAFB; padding: 9px 12px; border-radius: 10px; font-size: 0.74rem; font-weight: 500;
  letter-spacing: 0; text-transform: none; line-height: 1.45; white-space: normal; width: max-content; max-width: 280px; text-align: left;
  box-shadow: 0 10px 25px -5px rgba(17, 24, 39, 0.35), 0 4px 6px -2px rgba(17, 24, 39, 0.1);
  opacity: 0; visibility: hidden; pointer-events: none; transition: opacity 140ms ease, transform 140ms ease, visibility 140ms; z-index: 99999;
}
[data-tip]::before {
  content: ""; position: absolute; bottom: calc(100% + 2px); left: 50%; transform: translateX(-50%) translateY(4px);
  border-width: 6px 6px 0 6px; border-style: solid; border-color: #111827 transparent transparent transparent;
  opacity: 0; visibility: hidden; pointer-events: none; transition: opacity 140ms ease, transform 140ms ease, visibility 140ms; z-index: 99999;
}
[data-tip]:hover::after, [data-tip]:hover::before { opacity: 1; visibility: visible; transform: translateX(-50%) translateY(0); }
[data-tip-pos="bottom"]::after { bottom: auto; top: calc(100% + 8px); transform: translateX(-50%) translateY(-4px); }
[data-tip-pos="bottom"]::before { bottom: auto; top: calc(100% + 2px); border-width: 0 6px 6px 6px;
  border-color: transparent transparent #111827 transparent; transform: translateX(-50%) translateY(-4px); }
[data-tip-pos="bottom"]:hover::after, [data-tip-pos="bottom"]:hover::before { transform: translateX(-50%) translateY(0); }
[data-tip-pos="left"]::after { left: 0; transform: translateY(4px); }
[data-tip-pos="left"]::before { left: 16px; transform: translateY(4px); }
[data-tip-pos="left"]:hover::after, [data-tip-pos="left"]:hover::before { transform: translateY(0); }
[data-tip-pos="right"]::after { left: auto; right: 0; transform: translateY(4px); }
[data-tip-pos="right"]::before { left: auto; right: 16px; transform: translateY(4px); }
[data-tip-pos="right"]:hover::after, [data-tip-pos="right"]:hover::before { transform: translateY(0); }
.cc-tile[data-tip]::after { left: 24px; transform: translateY(4px); }
.cc-tile[data-tip]::before { left: 32px; transform: translateY(4px); }
.cc-tile[data-tip]:hover::after, .cc-tile[data-tip]:hover::before { transform: translateY(0); }

.cc-info-dot { display: inline-flex; align-items: center; justify-content: center; width: 14px; height: 14px; border-radius: 50%;
  border: 1px solid var(--cc-line-2); background: #FFFFFF; color: var(--cc-faint); font-size: 9px; font-weight: 700;
  font-family: var(--cc-sans); margin-left: 6px; cursor: help; transition: all 120ms ease; vertical-align: middle; line-height: 1;
  letter-spacing: 0; text-transform: none; }
.cc-tile:hover .cc-info-dot, .cc-info-dot:hover { background: var(--cc-primary); border-color: var(--cc-primary); color: #FFFFFF; }
.cc-tile.accent .cc-info-dot { background: transparent; border-color: #374151; color: #9CA3AF; }

/* ═══ Refined edition (Superdesign draft 039057c0): shapes, type and motion. Later rules win. ═══ */
[data-testid="stMainBlockContainer"], .block-container { max-width: 1200px; padding: 2rem 3rem 2rem; }
@media (max-width: 640px) { [data-testid="stMainBlockContainer"], .block-container { padding: 3.6rem 1rem 1.5rem; } }
[data-testid="stStatusWidget"] { visibility: hidden; }
.stApp p, .stApp li { line-height: 1.6; }

/* motion: one easing curve everywhere; entrances rise, charts grow, cards lift */
@keyframes cc-rise { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
@keyframes cc-fade { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
@keyframes cc-grow { from { transform: scaleY(0.02); } to { transform: scaleY(1); } }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important; animation-delay: 0ms !important; transition-duration: 0.01ms !important; }
}

/* page header: coral eyebrow, big grotesk title, quiet lede, one dark action */
.cc-eyebrow { font-size: 0.69rem; font-weight: 700; letter-spacing: 0.24em; color: var(--cc-primary); }
.cc-title { font-family: var(--cc-serif) !important; font-size: clamp(2.4rem, 5.2vw, 3.75rem); font-weight: 700; letter-spacing: -0.045em;
  line-height: 1.02; margin-top: 16px; color: var(--cc-ink); }
.cc-sub { font-size: 1.1rem; color: var(--cc-soft); margin-top: 14px; max-width: 620px; line-height: 1.55; }
.cc-phead-gap { height: 26px; }
.st-key-askbtn { align-items: flex-end; }
.st-key-askbtn [data-testid="stPageLink"], .st-key-askbtn [data-testid="stPageLink"] > div { width: auto !important; }
.st-key-askbtn [data-testid="stPageLink-NavLink"] { background: var(--cc-ink) !important; min-height: 48px; padding: 0 20px; border-radius: 12px; gap: 8px;
  box-shadow: var(--cc-float); transition: transform .35s var(--cc-ease), box-shadow .35s ease, background .2s ease; }
.st-key-askbtn [data-testid="stPageLink-NavLink"]:hover { background: #2A2E35 !important; transform: translateY(-2px); box-shadow: var(--cc-float-hover); }
.st-key-askbtn [data-testid="stPageLink-NavLink"]:active { transform: scale(.98); }
.st-key-askbtn [data-testid="stPageLink-NavLink"] p, .st-key-askbtn [data-testid="stIconMaterial"] { color: #FFFFFF !important; font-size: 0.9rem !important; font-weight: 700 !important; }
@media (max-width: 640px) { .st-key-askbtn { align-items: flex-start; } }

/* buttons: rounded, sentence case, ink primary, white secondary, a gentle lift on hover */
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button { border-radius: 12px; min-height: 46px; padding: 6px 20px;
  box-shadow: var(--cc-btn); transition: transform .3s var(--cc-ease), box-shadow .3s ease, background .2s ease, border-color .2s ease; }
.stButton > button p, .stFormSubmitButton > button p, .stDownloadButton > button p { font-size: 0.88rem !important; font-weight: 700 !important;
  letter-spacing: -0.005em; text-transform: none; }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
  background: var(--cc-ink); border: 1px solid var(--cc-ink); color: #FFFFFF; box-shadow: var(--cc-float); }
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover {
  background: #2A2E35; border-color: #2A2E35; transform: translateY(-2px); box-shadow: var(--cc-float-hover); }
.stButton > button[kind="secondary"], .stFormSubmitButton > button[kind="secondary"], .stDownloadButton > button[kind="secondary"] {
  background: #FFFFFF; border: 1px solid var(--cc-line-2); color: var(--cc-ink); }
.stButton > button[kind="secondary"]:hover, .stFormSubmitButton > button[kind="secondary"]:hover, .stDownloadButton > button[kind="secondary"]:hover {
  background: #FFFFFF; border-color: #CBD5E1; color: var(--cc-ink); transform: translateY(-2px); box-shadow: var(--cc-lift); }
.stButton > button:active, .stFormSubmitButton > button:active, .stDownloadButton > button:active { transform: scale(.98); }
.stLinkButton > a { border-radius: 12px; border-color: var(--cc-line-2); }
.stLinkButton > a p { font-size: 0.88rem; letter-spacing: 0; text-transform: none; }
[class*="st-key-go_"] button p { border-bottom: 0; padding-bottom: 0; font-size: 0.88rem !important; font-weight: 700 !important; }
[class*="st-key-go_"] button [data-testid="stIconMaterial"] { color: var(--cc-soft); transition: transform .3s var(--cc-ease); }
[class*="st-key-go_"] button:hover [data-testid="stIconMaterial"] { transform: translateX(3px); color: var(--cc-ink); }
[class*="st-key-go_"] button:hover p { color: var(--cc-ink) !important; }

/* chips */
.stApp [data-testid^="stBaseButton-segmented_control"], .stApp [data-testid^="stBaseButton-pills"] { border-radius: 999px !important;
  border-color: var(--cc-line-2) !important; box-shadow: none; min-height: 38px; }
.stApp [data-testid^="stBaseButton-segmented_control"]:first-child:not(:last-child) { border-radius: 999px 0 0 999px !important; }
.stApp [data-testid^="stBaseButton-segmented_control"]:last-child:not(:first-child) { border-radius: 0 999px 999px 0 !important; }
.stApp [data-testid^="stBaseButton-segmented_control"] p, .stApp [data-testid^="stBaseButton-pills"] p { font-size: 0.84rem !important;
  font-weight: 600 !important; letter-spacing: 0; text-transform: none; }

/* inputs */
.stApp [data-baseweb="input"], .stApp [data-baseweb="base-input"], .stApp [data-baseweb="select"] > div, .stApp [data-baseweb="textarea"] {
  border-color: var(--cc-line-2) !important; box-shadow: none; }
.stApp [data-baseweb="input"]:focus-within, .stApp [data-baseweb="select"] > div:focus-within { border-color: var(--cc-ink) !important;
  box-shadow: 0 0 0 4px rgba(23,25,29,0.06); }
.stApp [data-testid="stWidgetLabel"] p { color: var(--cc-faint); letter-spacing: 0.2em; }

/* cards: 16px corners, hairline border, soft shadow, lift on hover */
.cc-tile, .cc-cockpit-hero, .cc-card-modern, .cc-fanchart-card, .cc-action-card, .cc-onboard, .st-key-cc_panel, .st-key-ask_box,
[class*="st-key-row_"], [data-testid="stVerticalBlockBorderWrapper"]:not(.st-emotion-cache-0) {
  border-radius: var(--cc-card-r) !important; border-color: var(--cc-line-2) !important; box-shadow: var(--cc-float); }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: var(--cc-card-r); }
.cc-tile, .cc-card-modern, .cc-action-card, [class*="st-key-row_"] { transition: transform .35s var(--cc-ease), box-shadow .35s ease; }
.cc-tile:hover, .cc-card-modern:hover, .cc-action-card:hover, [class*="st-key-row_"]:hover { transform: translateY(-3px); box-shadow: var(--cc-float-hover); }
.cc-tile { padding: 24px; }
.cc-tile .l { font-size: 0.7rem; letter-spacing: 0.16em; color: var(--cc-soft); }
.stApp .cc-tile .v { font-family: var(--cc-serif) !important; font-size: 1.9rem; letter-spacing: -0.03em; margin-top: 16px; }
.stApp .cc-tile.big .v { font-size: 2.2rem; }
.cc-tile .s { font-size: 0.76rem; font-weight: 500; letter-spacing: 0; text-transform: none; color: var(--cc-faint); margin-top: 10px; }
.stApp .cc-hero { font-family: var(--cc-serif) !important; letter-spacing: -0.03em; }
.cc-h2 { font-family: var(--cc-serif) !important; font-size: 1.5rem; letter-spacing: -0.02em; }
.cc-label { font-size: 0.7rem; letter-spacing: 0.18em; color: var(--cc-faint); }
.cc-tag, .cc-badge, .cc-badge-pill, .cc-demo { border-radius: 999px; }
.cc-tag, .cc-badge { padding: 4px 11px; font-size: 0.6rem; letter-spacing: 0.1em; }
.cc-wa-btn { border-radius: 12px; font-size: 0.82rem; font-weight: 700; letter-spacing: 0; text-transform: none; padding: 11px 18px;
  box-shadow: var(--cc-float); transition: transform .3s var(--cc-ease), box-shadow .3s ease, background .2s ease; }
.cc-wa-btn:hover { background: #2A2E35; transform: translateY(-2px); box-shadow: var(--cc-float-hover); }
.stApp .cc-table td:not(:first-child), .stApp .cc-dl dd, .stApp .cc-figs dd, .stApp .cc-amount { font-family: var(--cc-serif) !important; }

/* expanders: quiet "show more" rows */
[data-testid="stExpander"] details { border-radius: var(--cc-card-r); border-color: var(--cc-line-2) !important; box-shadow: var(--cc-lift);
  transition: box-shadow .3s ease; }
[data-testid="stExpander"] details:hover { box-shadow: var(--cc-float); }
[data-testid="stExpander"] summary p { font-family: var(--cc-sans) !important; font-size: 0.95rem; font-weight: 700; letter-spacing: -0.01em; }
[data-testid="stExpanderDetails"] { animation: cc-fade .45s var(--cc-ease) both; }

/* notices: the draft's warm cream bar */
[data-testid="stAlert"] > div, [data-testid="stAlertContainer"] { border-radius: 12px; }
[data-testid="stAlertContentWarning"] p, [data-testid="stAlertContentInfo"] p { font-size: 0.9rem; }

/* tabs: an ink underline that slides between labels; panels fade in */
.stTabs [data-baseweb="tab-list"] { gap: 32px; border-bottom: 1px solid var(--cc-line-2); background: transparent; }
.stTabs [data-baseweb="tab"] { height: auto; padding: 0 0 16px; background: transparent !important; }
.stTabs [data-baseweb="tab"] p { font-size: 0.92rem; font-weight: 500; color: var(--cc-faint); transition: color .25s ease; }
.stTabs [data-baseweb="tab"]:hover p { color: var(--cc-ink); }
.stTabs [data-baseweb="tab"][aria-selected="true"] p { color: var(--cc-ink); font-weight: 700; }
.stTabs [data-baseweb="tab-highlight"] { background: var(--cc-ink); height: 2px; border-radius: 2px; }
.stTabs [data-baseweb="tab-border"] { display: none; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 28px; animation: cc-fade .55s var(--cc-ease) both; }
.cc-tabmeta { position: relative; height: 0; z-index: 2; }
.cc-tabmeta span { position: absolute; right: 0; top: 34px; display: flex; align-items: center; gap: 6px; font-size: 0.76rem; color: var(--cc-faint); }
@media (max-width: 640px) { .cc-tabmeta { display: none; } }

/* overview: figure cards */
.cc-kpis { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 20px; }
@media (max-width: 900px) { .cc-kpis { grid-template-columns: minmax(0, 1fr); } }
.cc-kpi { background: #FFFFFF; border: 1px solid var(--cc-line-2); border-radius: var(--cc-card-r); padding: 24px; box-shadow: var(--cc-float);
  transition: transform .35s var(--cc-ease), box-shadow .35s ease; animation: cc-rise .7s var(--cc-ease) both; animation-delay: calc(var(--i, 0) * 80ms); }
.cc-kpi:hover { transform: translateY(-3px); box-shadow: var(--cc-float-hover); }
.cc-kpi .top { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.cc-kpi .l { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase; color: var(--cc-soft); }
.cc-kpi .ic { width: 32px; height: 32px; flex: none; border-radius: 9px; display: grid; place-items: center; background: var(--cc-wash); color: var(--cc-soft); }
.cc-kpi .ic.gold { background: var(--cc-cream); color: var(--cc-gold); }
.stApp .cc-kpi .v { font-family: var(--cc-serif) !important; font-size: 2rem; font-weight: 700; letter-spacing: -0.03em; color: var(--cc-ink);
  margin-top: 22px; line-height: 1.1; font-variant-numeric: tabular-nums; }
.cc-kpi .s { margin-top: 12px; font-size: 0.78rem; color: var(--cc-faint); display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.cc-kpi .s .up { color: var(--cc-pos); font-weight: 600; display: inline-flex; align-items: center; gap: 4px; }
.cc-kpi .s .down { color: var(--cc-neg); font-weight: 600; display: inline-flex; align-items: center; gap: 4px; }
.cc-kpi .s.gold { color: var(--cc-gold); }

/* overview: cash position card with growing bars */
.st-key-cposcard { background: #FFFFFF; border: 1px solid var(--cc-line-2); border-radius: var(--cc-card-r); padding: 26px 28px 20px;
  box-shadow: var(--cc-float); gap: 0 !important; animation: cc-rise .7s var(--cc-ease) .15s both; }
.st-key-cposcard > * { width: 100% !important; max-width: 100%; }
.st-key-cposcard [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
.cc-card-title { font-family: var(--cc-serif) !important; font-size: 1.5rem; font-weight: 700; letter-spacing: -0.02em; color: var(--cc-ink); line-height: 1.2; }
.cc-card-sub { font-size: 0.86rem; color: var(--cc-soft); margin-top: 4px; }
.st-key-cposlink { align-items: flex-end; }
.st-key-cposlink [data-testid="stPageLink"], .st-key-cposlink [data-testid="stPageLink"] > div { width: auto !important; }
.st-key-cposlink [data-testid="stPageLink-NavLink"] { padding: 4px 0; min-height: 0; flex-direction: row-reverse; gap: 4px; background: transparent !important; }
.st-key-cposlink [data-testid="stPageLink-NavLink"] p { font-size: 0.86rem; font-weight: 600; color: var(--cc-soft); transition: color .2s ease; }
.st-key-cposlink [data-testid="stIconMaterial"] { color: var(--cc-soft); font-size: 1rem; transition: transform .3s var(--cc-ease); }
.st-key-cposlink [data-testid="stPageLink-NavLink"]:hover p { color: var(--cc-ink); }
.st-key-cposlink [data-testid="stPageLink-NavLink"]:hover [data-testid="stIconMaterial"] { transform: translate(2px, -2px); color: var(--cc-ink); }
.cc-bars { height: 150px; margin-top: 24px; display: flex; align-items: flex-end; gap: 4px; border-bottom: 1px solid var(--cc-line-2); padding: 0 2px; }
.cc-bars i { flex: 1; display: block; min-width: 0; border-radius: 5px 5px 0 0; background: #E2E8F0; transform-origin: bottom;
  animation: cc-grow .9s var(--cc-ease) both; animation-delay: calc(var(--i, 0) * 18ms + 200ms); transition: background .2s ease; }
.cc-bars i:hover { background: #94A3B8 !important; }
.cc-bars i.hi { background: var(--cc-ink) !important; }
.cc-axis { display: flex; justify-content: space-between; padding-top: 10px; font-size: 0.75rem; color: var(--cc-faint); }

/* overview: recent activity list */
.cc-act { background: #FFFFFF; border: 1px solid var(--cc-line-2); border-radius: var(--cc-card-r); box-shadow: var(--cc-float); padding: 4px 24px; }
.cc-act-row { display: grid; grid-template-columns: 40px minmax(0, 1fr) auto; gap: 14px; align-items: center; padding: 15px 0;
  border-bottom: 1px solid var(--cc-line); animation: cc-rise .6s var(--cc-ease) both; animation-delay: calc(var(--i, 0) * 55ms); }
.cc-act-row:last-child { border-bottom: 0; }
.cc-act-ic { width: 40px; height: 40px; border-radius: 12px; display: grid; place-items: center; background: var(--cc-wash); color: var(--cc-soft); }
.cc-act-ic.in { background: var(--cc-pos-wash); color: var(--cc-pos); }
.cc-act-t { font-size: 0.92rem; font-weight: 600; color: var(--cc-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cc-act-d { font-size: 0.78rem; color: var(--cc-faint); margin-top: 2px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.stApp .cc-act-a { text-align: right; font-family: var(--cc-serif) !important; font-weight: 700; font-size: 1rem; color: var(--cc-ink);
  font-variant-numeric: tabular-nums; white-space: nowrap; }
.stApp .cc-act-a.in { color: var(--cc-pos); }
.cc-act-a small { display: block; font-family: var(--cc-sans) !important; font-size: 0.7rem; font-weight: 500; color: var(--cc-faint); margin-top: 2px; }
.cc-insight-note { font-size: 0.86rem; color: var(--cc-soft); }

/* sidebar, refined: coral caption, roomier links, vault card with "Manage access", account pinned to the bottom */
.cc-sbrand .n { font-size: 1.28rem; letter-spacing: -0.02em; }
.cc-sbrand .s { color: var(--cc-primary); }
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] { min-height: 46px; }
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] p { font-size: 0.92rem; }
.st-key-snav { gap: 6px !important; margin-top: 14px; }
/* the vault card and its "Manage access" link read as one card: the link sits in the card's lower band */
.st-key-ssec { gap: 0 !important; }
.st-key-ssec [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
.cc-vcard { margin: 0; padding-bottom: 4px; border-bottom: 0; border-radius: 16px 16px 0 0; box-shadow: none; }
.st-key-vaultmgr { background: var(--cc-cream); border: 1px solid var(--cc-cream-line); border-top: 0; border-radius: 0 0 16px 16px;
  padding: 6px 16px 14px; box-shadow: 0 8px 18px rgba(174,138,67,0.07); }
/* "Manage access" and "Language & more" open in place: quiet text toggles, no card chrome */
.st-key-vaultmgr [data-testid="stExpander"] details, .st-key-sacct [data-testid="stExpander"] details {
  border: 0 !important; background: transparent !important; box-shadow: none !important; border-radius: 0; overflow: visible; }
.st-key-vaultmgr [data-testid="stExpander"] summary, .st-key-sacct [data-testid="stExpander"] summary { padding: 4px 0 !important; min-height: 0; }
.st-key-vaultmgr [data-testid="stExpander"] details[open] > summary, .st-key-sacct [data-testid="stExpander"] details[open] > summary { border-bottom: 0; }
.st-key-vaultmgr [data-testid="stExpander"] summary p { font-family: var(--cc-sans) !important; font-size: 0.74rem !important; font-weight: 700 !important;
  letter-spacing: 0.02em; color: var(--cc-ink); text-decoration: underline; text-underline-offset: 4px; }
.st-key-sacct [data-testid="stExpander"] summary p { font-family: var(--cc-sans) !important; font-size: 0.8rem !important; font-weight: 600 !important;
  color: var(--cc-soft); }
.st-key-vaultmgr [data-testid="stExpander"] summary svg, .st-key-sacct [data-testid="stExpander"] summary svg { width: 15px; height: 15px; color: var(--cc-faint); }
.st-key-vaultmgr [data-testid="stExpanderDetails"] { padding: 12px 0 2px !important; }
.st-key-sacct [data-testid="stExpanderDetails"] { padding: 10px 0 4px !important; }
.st-key-sacct { gap: 6px !important; }
.stApp iframe { background: transparent !important; color-scheme: normal; }
.st-key-cposlink > div, .st-key-askbtn > div { width: auto !important; }
.st-key-vaultmgr [data-testid="stPopover"] { width: auto !important; }
.st-key-vaultmgr [data-testid="stPopoverButton"] { background: transparent !important; border: 0 !important; box-shadow: none !important;
  min-height: 28px; padding: 0 !important; }
.st-key-vaultmgr [data-testid="stPopoverButton"] p { font-size: 0.74rem !important; font-weight: 700 !important; letter-spacing: 0.02em;
  color: var(--cc-ink); text-decoration: underline; text-underline-offset: 4px; transition: color .2s ease; }
.st-key-vaultmgr [data-testid="stPopoverButton"]:hover p { color: var(--cc-soft); }
.st-key-vaultmgr [data-testid="stPopoverButton"] [data-testid="stIconMaterial"], .st-key-vaultmgr [data-testid="stPopoverButton"] svg { display: none; }
[data-testid="stPopoverBody"] { border-radius: var(--cc-card-r) !important; border: 1px solid var(--cc-line-2) !important;
  box-shadow: 0 24px 60px rgba(23,25,29,0.16) !important; padding: 18px 18px 14px !important; animation: cc-fade .35s var(--cc-ease) both; }
/* popovers render outside .stApp, so they get the theme's type and fields here */
[data-testid="stPopoverBody"] p, [data-testid="stPopoverBody"] label, [data-testid="stPopoverBody"] input, [data-testid="stPopoverBody"] div,
[data-testid="stPopoverBody"] span:not([data-testid*="Icon"]):not([class*="material"]) { font-family: var(--cc-sans); }
[data-testid="stPopoverBody"] [data-testid="stWidgetLabel"] p { font-size: 0.64rem !important; font-weight: 700 !important; letter-spacing: 0.2em;
  text-transform: uppercase; color: var(--cc-faint); }
[data-testid="stPopoverBody"] [data-baseweb="input"], [data-testid="stPopoverBody"] [data-baseweb="select"] > div {
  border-radius: 12px !important; border: 1px solid var(--cc-line-2) !important; background: #FFFFFF !important; }
[data-testid="stPopoverBody"] [data-baseweb="input"] [data-baseweb="base-input"] { border: 0 !important; background: transparent !important; }
[data-testid="stPopoverBody"] [data-baseweb="input"]:focus-within, [data-testid="stPopoverBody"] [data-baseweb="select"] > div:focus-within {
  border-color: var(--cc-ink) !important; box-shadow: 0 0 0 4px rgba(23,25,29,0.06); }
.cc-pop-title { font-family: var(--cc-serif) !important; font-size: 1.05rem; font-weight: 700; color: var(--cc-ink); letter-spacing: -0.01em; }
.cc-pop-sub { font-size: 0.78rem; color: var(--cc-soft); margin-top: 2px; }
.st-key-sacct { border-top: 1px solid var(--cc-line); padding-top: 16px; margin-top: 18px; }
.st-key-sacct [data-testid="stHorizontalBlock"] { align-items: center; }
.st-key-sacct .cc-sacct { border-top: 0; padding-top: 0; margin-top: 0; }
.st-key-sacct [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
.st-key-sacct [data-testid="stPopover"] { display: flex; justify-content: flex-end; }
.st-key-sacct [data-testid="stPopoverButton"] { width: 34px; min-height: 34px; height: 34px; padding: 0 !important; border: 0 !important;
  background: transparent !important; box-shadow: none !important; border-radius: 10px !important; }
.st-key-sacct [data-testid="stPopoverButton"]:hover { background: var(--cc-wash) !important; }
.st-key-sacct [data-testid="stPopoverButton"] svg { display: none; }
.st-key-sacct [data-testid="stPopoverButton"] [data-testid="stIconMaterial"] { color: var(--cc-faint); }
.st-key-more [data-testid="stPageLink-NavLink"] { min-height: 40px; padding: 0 10px; }
.st-key-more [data-testid="stPageLink-NavLink"] p { font-size: 0.88rem; }
/* top bar: bell for the review queue, help */
.st-key-tbell [data-testid="stPageLink-NavLink"] { width: 40px; min-height: 40px; height: 40px; padding: 0 !important; justify-content: center; border-radius: 50% !important; }
.st-key-tbell [data-testid="stPageLink-NavLink"] p { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.st-key-tbell { position: relative; }
.st-key-tbell::after { content: ""; position: absolute; top: 8px; right: 9px; width: 7px; height: 7px; border-radius: 50%;
  background: var(--cc-primary); box-shadow: 0 0 0 2px #FFFFFF; pointer-events: none; }
</style>
"""), unsafe_allow_html=True)


def H(markup: str) -> None:
    """Render a trusted HTML fragment. Collapsing newlines keeps Markdown from reading indents as code."""
    st.markdown(re.sub(r"\n\s*", " ", markup).strip(), unsafe_allow_html=True)


def esc(value) -> str:
    return _html.escape(str(value))


_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]")


def no_emoji(text) -> str:
    """Drop emoji from text the backend writes (answers), so the page shows none."""
    return re.sub(r"[ \t]{2,}", " ", _EMOJI.sub("", str(text)))


def answer_html(text: str) -> str:
    """Escape an answer, then render only **bold** and line breaks (model answers use light markdown)."""
    safe = esc(no_emoji(text))
    safe = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe)
    return safe.replace("\n", "<br>")


def svg(path: str, size: int = 16, color: str = "currentColor", width: float = 2) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
            f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{path}</svg>')


ICON_CHECK = '<path d="m5 12.5 4.5 4.5L19 7.5"></path>'
ICON_CHECK_CIRCLE = '<circle cx="12" cy="12" r="9"></circle><path d="m8 12.3 2.7 2.7L16 9.5"></path>'
ICON_ALERT = '<path d="M12 4 21 19.5H3z"></path><path d="M12 10v4.5"></path><path d="M12 17.4v.1"></path>'
ICON_UNLOCK = '<rect x="5" y="11" width="14" height="9.5" rx="2"></rect><path d="M8 11V7.5a4 4 0 0 1 7.6-1.7"></path>'
ICON_LOCK = '<rect x="5" y="11" width="14" height="9.5" rx="2"></rect><path d="M8 11V7.5a4 4 0 0 1 8 0V11"></path>'
ICON_EYE = '<path d="M2.5 12s3.5-6.5 9.5-6.5S21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"></path><circle cx="12" cy="12" r="2.8"></circle>'
ICON_NEVER = '<circle cx="12" cy="12" r="8.5"></circle><path d="m6 18 12-12"></path>'
ICON_BOX_CHECK = '<rect x="4" y="4" width="16" height="16" rx="3"></rect><path d="m8.5 12 2.5 2.5 4.5-5"></path>'
ICON_SHIELD = '<path d="M12 3.5 19.5 6v5.5c0 4.3-3.1 7.6-7.5 9-4.4-1.4-7.5-4.7-7.5-9V6z"></path>'
ICON_SHIELD_CHECK = '<path d="M12 3.5 19.5 6v5.5c0 4.3-3.1 7.6-7.5 9-4.4-1.4-7.5-4.7-7.5-9V6z"></path><path d="m9 12 2.2 2.2L15.5 10"></path>'
ICON_CHAT ='<path d="M20 12a8 8 0 0 1-11.6 7.1L4 20l.9-4.4A8 8 0 1 1 20 12z"></path><path d="M8.5 10.5h7"></path><path d="M8.5 13.5h4.5"></path>'
# Brand mark: a landmark (bank) glyph on a near-black rounded square, as in the Floating Edition header.
LOGO = ('<svg width="36" height="36" viewBox="0 0 36 36" aria-hidden="true"><rect width="36" height="36" rx="12" fill="#17191D"></rect>'
        '<g transform="translate(8 8) scale(0.8333)" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M3 22h18"></path><path d="M6 18v-7"></path><path d="M10 18v-7"></path><path d="M14 18v-7"></path>'
        '<path d="M18 18v-7"></path><path d="m12 2 8 5H4z"></path></g></svg>')


def tag(text: str, tone: str = "neutral") -> str:
    return f'<span class="cc-tag {tone}">{esc(text)}</span>'


DEMO = '<span class="cc-demo">Demo</span>'


def vault_role_note(role_name: str) -> str:
    """Why a non-owner role has no PIN field: the vault is force-locked for every role except Owner."""
    who = "Accountant" if role_name.startswith("Accountant") else role_name
    return (f'<div class="cc-note" data-testid="vault-role-note" style="margin:6px 0 10px;line-height:1.5;">'
            + t(f"You are viewing as {who}. Sovereign cash is restricted to the Owner, so there is no PIN to enter in this role. "
                f"Switch 'Viewing as' to Owner to unlock it.",
                f"आप {who} के रूप में देख रहे हैं। गल्ले का नकद केवल मालिक के लिए है, इसलिए इस भूमिका में PIN नहीं लगता। "
                f"अनलॉक करने के लिए 'Viewing as' में Owner चुनें।")
            + '</div>')


def tile(label: str, value: str, sub: str = "", tone: str = "", tip: str = "") -> str:
    sub_html = f'<span class="s">{sub}</span>' if sub else ""
    tip_attr = f' data-tip="{esc(tip)}"' if tip else ""
    info_icon = f' <span class="cc-info-dot">i</span>' if tip else ""
    return (f'<div class="cc-tile {tone}"{tip_attr}><span class="l">{esc(label)}{info_icon}</span>'
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
    v_init = VaultDB(in_memory=False)
    if not v_init.db_path.exists() or v_init.db_path.stat().st_size == 0:
        v_init.seed_from_pack(pack)
        v_init.lock()
    return pack, matches, copilot


pack, matches, copilot = boot()


def get_vault() -> VaultDB:
    if "vault" not in st.session_state:
        v = VaultDB(in_memory=False)
        if not v.db_path.exists() or v.db_path.stat().st_size == 0:
            v.seed_from_pack(pack)
            v.lock()
        st.session_state["vault"] = v
    return st.session_state["vault"]


vault = get_vault()


@st.cache_resource(show_spinner="Running the 90-day forecast…")
def forecast_for(business: str, cutoff: pd.Timestamp = config.AS_OF, late_days: int = 0,
                 bill_shift: int = 0, sales_factor: float = 1.0):
    return simulate_forecast(as_of(pack, cutoff), business, receipt_delay_days=late_days,
                             bill_shift_days=bill_shift, sales_factor=sales_factor)


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


@st.cache_resource(show_spinner=False)
def queue_counts(business: str) -> dict:
    """Receipts per review tier. Matches are fixed for the server's life, so this is counted once per business."""
    counts = {SUGGEST: 0, ASK: 0, "auto": 0}
    for m in matches.values():
        if m.business_id != business:
            continue
        if m.tier in (SUGGEST, ASK):
            counts[m.tier] += 1
        elif m.tier in ("AUTO", "NO_DOC"):
            counts["auto"] += 1
    return counts


@st.cache_resource(show_spinner=False)
def tally_xml_for(business: str) -> str:
    """Tally vouchers depend only on the bank pack and its matches, so they are built once per business."""
    return generate_tally_xml(pack, list(matches.values()), business)


def ca_workbook_button(prefix: str, label: str, export_vault) -> None:
    """The CA workbook takes seconds to build, so it is built when asked for instead of on every rerun.
    The first click prepares it and the button turns into the download; a cash-book change discards the copy."""
    # export_vault is ignored on purpose (ADR-004): the CA always gets the 5-sheet statutory pack, with no
    # drawer cash or salesman slips, whatever the owner's sharing setting. The owner's 6-sheet pack is separate.
    slot = f"_ca_book_{prefix}"
    sig = (biz, "statutory")
    held = st.session_state.get(slot)
    if held and held[0] == sig:
        st.download_button(label=label, icon=":material/download:", data=held[1],
                           file_name=f"ca_reconciliation_{biz}_{config.AS_OF:%Y%m%d}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True, key=f"{prefix}_dl_ca_excel")
    elif st.button(t("Prepare CA Excel workbook", "CA एक्सेल वर्कबुक तैयार करें"), icon=":material/table_view:",
                   use_container_width=True, key=f"{prefix}_prep_ca_excel"):
        with st.spinner(t("Building the workbook…", "वर्कबुक बन रही है…")):
            st.session_state[slot] = (sig, generate_statutory_ca_excel_pack(pack, list(matches.values()), None, biz))
        st.rerun()


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
st.session_state.setdefault("vault_unlocked", False)
st.session_state.setdefault("khata_alpha_pct", 70)

if not st.session_state["vault_unlocked"]:
    if vault.is_unlocked():
        vault.lock()
else:
    if not vault.is_unlocked():
        vault.unlock(os.environ.get("COPILOT_OWNER_PIN") or "0000")


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


def biz_type_label() -> str:
    return "FMCG Wholesale · Pune" if biz == "SME-1" else ("Dental Clinic · Bengaluru" if biz == "SME-2" else "Design Agency · Mumbai")


def role_label_text() -> str:
    if is_owner:
        return t("Owner (मालिक)", "मालिक")
    if is_counter_staff:
        return t("Counter Staff (स्टाफ)", "काउंटर स्टाफ")
    return t("Accountant / CA (मुनीम)", "मुनीम / एकाउंटेंट")


def role_tip_text() -> str:
    if is_owner:
        return t("Viewing with full Owner privileges: Bank liquidity, cash drawer, informal khata, and WhatsApp chasers.",
                 "मालिक दृश्य: बैंक, गल्ला, कच्चा खाता और वसूली")
    if is_counter_staff:
        return t("Counter Staff: Access restricted to till balancing and collection slip entries.",
                 "काउंटर स्टाफ: केवल गल्ला और पर्ची प्रविष्टि")
    return t("Accountant / CA: Formal bank records only unless cash book is explicitly shared.",
             "मुनीम/CA: केवल औपचारिक बैंक हिसाब")


def ask_button() -> None:
    """The draft's single dark action in the page header: open Ask Copilot."""
    with st.container(key="askbtn"):
        st.page_link(PAGES["ask"], label=t("Ask Copilot", "रोकड़ सलाहकार"), icon=":material/auto_awesome:")


def page_header(title: str, subtitle: str, right=None) -> None:
    """Refined page header: coral eyebrow (trade · date), big grotesk title, one-line lede, one action on the right.
    Status (vault, role, read-only) lives in the sidebar, so the header stays quiet."""
    biz_type = biz_type_label()
    date_tip = t(f"Books reconciled as of close of business {config.AS_OF:%d %b %Y}. All figures are tied to this cutoff.",
                 f"{config.AS_OF:%d %b %Y} तक का हिसाब")
    left, rgt = st.columns([3, 1.3], vertical_alignment="bottom")
    with left:
        H(f'<div class="cc-eyebrow">{esc(biz_type)} · <span data-tip="{esc(date_tip)}" data-tip-pos="bottom">{config.AS_OF:%d %b %Y}</span></div>'
          f'<div class="cc-title" role="heading" aria-level="1">{esc(title)}</div>'
          f'<div class="cc-sub">{esc(subtitle)}</div>')
    with rgt:
        if right is not None:
            right()
        else:
            ask_button()
    H('<div class="cc-phead-gap"></div>')


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
    title_lbl = "Morning Cash Briefing" if not is_hi() else "दैनिक नकद ब्रिफिंग"
    sub_lbl = "30-second audio summary" if not is_hi() else "30 सेकंड का नकद सारांश"
    lang = "hi-IN" if is_hi() else "en-IN"

    svg_volume = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#E76559" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path><path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path></svg>'

    html_code = f"""
    <link href="https://api.fontshare.com/v2/css?f[]=satoshi@400,500,700&f[]=cabinet-grotesk@700&display=swap" rel="stylesheet"><link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Devanagari:wght@400;600&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Lora:wght@700&display=swap" rel="stylesheet">
    <style>body{{margin:0;padding:2px 3px 0;}}</style>
    <div style="display:flex;flex-wrap:nowrap;align-items:center;justify-content:space-between;gap:12px;background:#FFFFFF;border:1px solid #EDEDE9;border-radius:20px;padding:12px 14px 12px 18px;font-family:'Satoshi','IBM Plex Sans Devanagari',system-ui,sans-serif;box-shadow:0 1px 2px rgba(0,0,0,0.03),0 4px 12px rgba(0,0,0,0.05);">
      <div style="display:flex;align-items:center;gap:14px;min-width:0;flex:1;">
        <span style="display:grid;place-items:center;flex:none;width:38px;height:38px;border-radius:12px;background:#FFF1F1;">{svg_volume}</span>
        <div>
          <div style="font-family:'Lora','IBM Plex Sans Devanagari',Georgia,serif;font-size:15px;font-weight:700;color:#17191D;line-height:1.2;">{title_lbl}</div>
          <div style="font-size:10px;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;color:#64748B;margin-top:4px;">{sub_lbl}</div>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:10px;">
        <div id="speechWarn" style="display:none;font-size:11px;color:#A8261D;font-weight:500;">Browser speech synthesis unavailable</div>
        <button id="speakBtn" onclick="togglePlay()" aria-label="Play daily audio briefing" style="background:#E76559;color:white;border:none;min-height:44px;min-width:96px;flex:none;padding:0 18px;border-radius:10px;box-shadow:0 1px 2px rgba(231,101,89,0.3),0 8px 18px -6px rgba(231,101,89,0.55);font-size:11px;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:8px;transition:background 150ms ease;">
          <span id="btnTxt">{play_lbl}</span>
        </button>
      </div>
    </div>
    <script>
      let isPlaying = false;
      const text = "{js_text}";
      function togglePlay() {{
        if (!('speechSynthesis' in window)) {{
          const warn = document.getElementById('speechWarn');
          if (warn) warn.style.display = 'block';
          return;
        }}
        if (isPlaying) {{
          window.speechSynthesis.cancel();
          isPlaying = false;
          document.getElementById('btnTxt').innerText = "{play_lbl}";
          document.getElementById('speakBtn').style.background = "#E76559";
        }} else {{
          window.speechSynthesis.cancel();
          const u = new SpeechSynthesisUtterance(text);
          u.lang = "{lang}";
          u.rate = 1.0;
          u.onend = function() {{
            isPlaying = false;
            document.getElementById('btnTxt').innerText = "{play_lbl}";
            document.getElementById('speakBtn').style.background = "#E76559";
          }};
          u.onerror = function() {{
            isPlaying = false;
            document.getElementById('btnTxt').innerText = "{play_lbl}";
            document.getElementById('speakBtn').style.background = "#E76559";
          }};
          window.speechSynthesis.speak(u);
          isPlaying = true;
          document.getElementById('btnTxt').innerText = "{stop_lbl}";
          document.getElementById('speakBtn').style.background = "#A8261D";
        }}
      }}
    </script>
    """
    components.html(html_code, height=92)


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
        label=t("Download CSV", "CSV डाउनलोड करें"),
        data=csv_data.to_csv(index=False),
        file_name=f"recovery_sheet_{biz}_{config.AS_OF:%Y%m%d}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    table_rows = ""
    for idx, (_, r) in enumerate(late.iterrows(), 1):
        table_rows += (
            f'<tr style="border-bottom:1px solid #EDEDE9;">'
            f'<td style="padding:8px 6px;text-align:left;">{idx}</td>'
            f'<td style="padding:8px 6px;font-weight:600;color:#17191D;">{esc(r["customer_name"])}</td>'
            f'<td style="padding:8px 6px;text-align:right;font-weight:600;color:#17191D;">{inr(r["outstanding"])}</td>'
            f'<td style="padding:8px 6px;text-align:center;color:#8A5300;">{int(r["oldest_days"])}d</td>'
            f'<td style="padding:8px 6px;text-align:center;"><span style="display:inline-block;width:16px;height:16px;border:1.5px solid #475569;border-radius:2px;"></span></td>'
            f'<td style="padding:8px 6px;border-bottom:1px dashed #E5E5E1;width:95px;"></td>'
            f'<td style="padding:8px 6px;border-bottom:1px dashed #E5E5E1;"></td>'
            f'</tr>'
        )

    svg_print = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:6px"><polyline points="6 9 6 2 18 2 18 9"></polyline><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path><rect x="6" y="14" width="12" height="8"></rect></svg>'

    html_sheet = f"""
    <link href="https://api.fontshare.com/v2/css?f[]=satoshi@400,500,700&f[]=cabinet-grotesk@700&display=swap" rel="stylesheet"><link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Devanagari:wght@400;600&display=swap" rel="stylesheet">
    <div id="printSheet" style="background:#FFF;padding:20px;font-family:'Satoshi','IBM Plex Sans Devanagari',system-ui,sans-serif;border:1px solid #EDEDE9;border-radius:20px;margin-top:10px;">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;border-bottom:2px solid #17191D;padding-bottom:10px;margin-bottom:12px;">
        <div>
          <div style="font-size:18px;font-weight:700;color:#17191D;">{esc(BIZ_NAME)}</div>
          <div style="font-size:13px;font-weight:600;color:#E76559;">DAILY RECOVERY & CHASING SHEET (गोदाम / फील्ड वसूली शीट)</div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:12px;font-weight:600;color:#17191D;">Date: {config.AS_OF:%d %b %Y}</div>
          <div style="font-size:11px;color:#475569;">Overdue (45+ Days): {len(late)} shops · Total: {inr(total_due)}</div>
        </div>
      </div>

      <div style="margin-bottom:12px;text-align:right;">
        <button onclick="window.print()" style="background:#E76559;color:white;border:none;min-height:44px;padding:0 22px;border-radius:10px;box-shadow:0 1px 2px rgba(231,101,89,0.3),0 8px 18px -6px rgba(231,101,89,0.55);font-size:11px;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;cursor:pointer;display:inline-flex;align-items:center;">
          {svg_print} Print Sheet / PDF
        </button>
      </div>

      <table style="width:100%;border-collapse:collapse;font-size:12px;margin-bottom:20px;">
        <thead>
          <tr style="background:#F8FAFC;border-bottom:1px solid #17191D;">
            <th style="padding:8px 6px;text-align:left;width:30px;">#</th>
            <th style="padding:8px 6px;text-align:left;">Retailer / Shop</th>
            <th style="padding:8px 6px;text-align:right;width:95px;">Due (₹)</th>
            <th style="padding:8px 6px;text-align:center;width:55px;">Age</th>
            <th style="padding:8px 6px;text-align:center;width:50px;">Visit</th>
            <th style="padding:8px 6px;text-align:left;width:95px;">Recvd (₹)</th>
            <th style="padding:8px 6px;text-align:left;">Salesman Notes</th>
          </tr>
        </thead>
        <tbody>
          {table_rows}
        </tbody>
      </table>

      <div style="display:flex;justify-content:space-between;gap:20px;margin-top:24px;padding-top:16px;border-top:1px solid #17191D;font-size:11px;">
        <div><b>Salesman Sign:</b> ___________________</div>
        <div><b>Godown Manager Sign:</b> ___________________</div>
        <div><b>Cashier Sign:</b> ___________________</div>
      </div>
    </div>
    """
    components.html(html_sheet, height=450, scrolling=True)


# ── PAGE: OVERVIEW (Refined draft: greeting, three figures, cash bars, briefing; detail one tab away) ──
ICON_BANK = ('<path d="M3 21h18"></path><path d="M6 17v-6"></path><path d="M10 17v-6"></path><path d="M14 17v-6"></path>'
             '<path d="M18 17v-6"></path><path d="m12 3 8 5H4z"></path>')
ICON_ARROW_UR = '<path d="M7 17 17 7"></path><path d="M8 7h9v9"></path>'
ICON_CLOCK = '<circle cx="12" cy="12" r="9"></circle><path d="M12 7.5V12l3 2"></path>'
ICON_TREND_UP = '<path d="m3 16.5 6-6 4 4 8-8"></path><path d="M15 6.5h6v6"></path>'
ICON_TREND_DOWN = '<path d="m3 7.5 6 6 4-4 8 8"></path><path d="M15 17.5h6v-6"></path>'
ICON_MONEY_IN = '<path d="M12 4v11"></path><path d="m7 10 5 5 5-5"></path><path d="M5 20h14"></path>'
ICON_MONEY_OUT = '<path d="M12 15V4"></path><path d="m7 9 5-5 5 5"></path><path d="M5 20h14"></path>'
STATUS_LABEL = {"AUTO": ("Matched", "pos"), "NO_DOC": ("No document needed", "neutral"),
                SUGGEST: ("Suggestion", "info"), ASK: ("Question", "warn")}
_CHANNEL_WORDS = re.compile(r"^(CHQ|NEFT|RTGS|IMPS|UPI|CTS|CASH|ATM|POS|ACH|NACH|BY|TO|DEP|CLG|INB|SALARY|BIL|ECS)\b", re.I)


def greeting_line() -> str:
    first = BIZ_NAME.split()[0]
    if is_hi():
        return f"नमस्ते, {first}।"
    hour = datetime.now().hour
    part = "morning" if hour < 12 else ("afternoon" if hour < 17 else "evening")
    return f"Good {part}, {first}."


def _biz_bank() -> pd.DataFrame:
    b = pack.bank[(pack.bank.business_id == biz) & (pack.bank.txn_date <= config.AS_OF)]
    return b.sort_values(["txn_date", "seq"])


def balance_on(day) -> float | None:
    """Running bank balance at the close of `day`, or None before the first entry."""
    b = _biz_bank()
    b = b[b.txn_date <= day]
    return None if b.empty else float(b.balance_inr.iloc[-1])


def daily_balances(days: int = 30) -> pd.Series:
    """Closing balance for each of the last `days` calendar days up to the books' cutoff."""
    b = _biz_bank()
    daily = b.groupby(b.txn_date.dt.normalize())["balance_inr"].last()
    idx = pd.date_range(config.AS_OF.normalize() - pd.Timedelta(days=days - 1), config.AS_OF.normalize(), freq="D")
    return daily.reindex(daily.index.union(idx)).ffill().reindex(idx).dropna()


def party_from(narration: str) -> str:
    """Pull the counterparty's name out of a bank narration, for a readable activity list."""
    for part in re.split(r"\s*-\s*", str(narration)):
        part = part.strip()
        if re.search(r"[A-Za-z]{3}", part) and " " in part and not _CHANNEL_WORDS.match(part) and "@" not in part:
            return part.title()
    return str(narration)[:42]


def kpi_card(i: int, label: str, value: str, sub_html: str, icon: str, gold: bool = False) -> str:
    return (f'<div class="cc-kpi" style="--i:{i}"><div class="top"><span class="l">{esc(label)}</span>'
            f'<span class="ic{" gold" if gold else ""}">{svg(icon, 16)}</span></div>'
            f'<div class="v">{esc(value)}</div><div class="s{" gold" if gold else ""}">{sub_html}</div></div>')


def render_briefing_card(headline_html: str, body: str, speech: str, height: int = 324) -> None:
    """The draft's dark briefing card. It lives in a small frame so its Listen button can speak the briefing aloud."""
    js_text = speech.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'").replace("\n", " ")
    lbl = t("Morning briefing", "सुबह की ब्रीफिंग")
    play = t("Listen to 30-second briefing", "30 सेकंड की ब्रीफिंग सुनें")
    stop = t("Stop briefing", "ब्रीफिंग रोकें")
    lang = "hi-IN" if is_hi() else "en-IN"
    vol = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" '
           'stroke-linejoin="round"><path d="M11 5 6 9H2v6h4l5 4z"></path><path d="M15.5 8.5a5 5 0 0 1 0 7"></path>'
           '<path d="M19 5a10 10 0 0 1 0 14"></path></svg>')
    play_ic = ('<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
               'stroke-linejoin="round"><circle cx="12" cy="12" r="9"></circle><path d="m10 8.5 5 3.5-5 3.5z"></path></svg>')
    html_code = f"""
    <link href="https://api.fontshare.com/v2/css?f[]=satoshi@400,500,700&f[]=cabinet-grotesk@700,800&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Devanagari:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
      html, body {{ margin: 0; height: 100%; background: transparent; }}
      * {{ box-sizing: border-box; }}
      .card {{ position: relative; overflow: hidden; height: calc(100% - 18px); margin: 2px 4px 0; background: #17191D; color: #FFFFFF;
        border-radius: 16px; padding: 26px 26px 24px; display: flex; flex-direction: column;
        font-family: 'Satoshi', 'IBM Plex Sans Devanagari', system-ui, sans-serif; box-shadow: 0 14px 38px rgba(23,25,29,0.16);
        animation: rise .8s cubic-bezier(.22,1,.36,1) .25s both; }}
      .card::before {{ content: ""; position: absolute; top: -90px; right: -70px; width: 260px; height: 260px; border-radius: 50%;
        background: radial-gradient(closest-side, rgba(231,101,89,0.22), rgba(231,101,89,0)); animation: drift 10s ease-in-out infinite alternate; }}
      .card > * {{ position: relative; }}
      .top {{ display: flex; justify-content: space-between; align-items: center; }}
      .lbl {{ font-size: 11px; letter-spacing: .16em; text-transform: uppercase; font-weight: 700; color: #94A3B8; }}
      .ic {{ width: 32px; height: 32px; border-radius: 9px; background: rgba(255,255,255,0.1); display: grid; place-items: center; }}
      h2 {{ font-family: 'Cabinet Grotesk', 'Satoshi', 'IBM Plex Sans Devanagari', sans-serif; font-size: 25px; line-height: 1.2; font-weight: 700;
        letter-spacing: -0.02em; margin: auto 0 0; padding-top: 22px; }}
      p {{ font-size: 14px; line-height: 1.6; color: #94A3B8; margin: 12px 0 0; }}
      button {{ margin-top: 22px; width: 100%; border: 0; border-radius: 12px; background: #FFFFFF; color: #17191D; min-height: 48px;
        font: 700 14px 'Satoshi', 'IBM Plex Sans Devanagari', system-ui, sans-serif; display: flex; align-items: center; justify-content: center;
        gap: 9px; cursor: pointer; transition: transform .3s cubic-bezier(.22,1,.36,1), background .2s ease; }}
      button:hover {{ background: #F1F5F9; transform: translateY(-2px); }}
      button:active {{ transform: scale(.98); }}
      button:focus-visible {{ outline: 2px solid #E76559; outline-offset: 3px; }}
      .eq {{ display: none; gap: 3px; align-items: flex-end; height: 14px; }}
      .playing .eq {{ display: inline-flex; }}
      .playing .pi {{ display: none; }}
      .eq i {{ display: block; width: 3px; height: 4px; background: #17191D; border-radius: 2px; animation: eq .9s ease-in-out infinite; }}
      .eq i:nth-child(2) {{ animation-delay: .15s; }} .eq i:nth-child(3) {{ animation-delay: .3s; }} .eq i:nth-child(4) {{ animation-delay: .45s; }}
      .warn {{ display: none; font-size: 12px; color: #FCA5A5; margin-top: 10px; }}
      @keyframes rise {{ from {{ opacity: 0; transform: translateY(14px); }} to {{ opacity: 1; transform: none; }} }}
      @keyframes drift {{ from {{ transform: translate(0, 0) scale(1); }} to {{ transform: translate(-50px, 40px) scale(1.15); }} }}
      @keyframes eq {{ 0%, 100% {{ height: 4px; }} 50% {{ height: 14px; }} }}
      @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; transition: none !important; }} }}
    </style>
    <div class="card">
      <div class="top"><span class="lbl">{lbl}</span><span class="ic">{vol}</span></div>
      <h2>{headline_html}</h2>
      <p>{esc(body)}</p>
      <button id="b" onclick="toggle()" aria-label="{play}"><span id="bt">{play}</span><span class="pi">{play_ic}</span>
        <span class="eq" aria-hidden="true"><i></i><i></i><i></i><i></i></span></button>
      <div class="warn" id="w">Speech is not available in this browser.</div>
    </div>
    <script>
      let on = false;
      const text = "{js_text}";
      const b = document.getElementById('b'), bt = document.getElementById('bt');
      function idle() {{ on = false; b.classList.remove('playing'); bt.innerText = "{play}"; }}
      function toggle() {{
        if (!('speechSynthesis' in window)) {{ document.getElementById('w').style.display = 'block'; return; }}
        window.speechSynthesis.cancel();
        if (on) {{ idle(); return; }}
        const u = new SpeechSynthesisUtterance(text); u.lang = "{lang}"; u.rate = 1.0;
        u.onend = idle; u.onerror = idle;
        window.speechSynthesis.speak(u);
        on = true; b.classList.add('playing'); bt.innerText = "{stop}";
      }}
    </script>
    """
    components.html(html_code, height=height)


def page_overview():
    page_header(greeting_line(), t("Here is the clearest view of your business today.", "आज आपके व्यापार की सबसे साफ़ तस्वीर।"))
    if not st.session_state.get("onboarded", False):
        with st.container(border=True, key="first_run"):
            fr1, fr2, fr3 = st.columns([4, 1.3, 1], vertical_alignment="center")
            fr1.markdown(t("**New here?** A three-step setup shows what is shared, checks your books and confirms your key numbers.",
                           "**पहली बार?** तीन चरणों का सेटअप बताता है कि क्या साझा होता है, आपके खाते जांचता है और मुख्य आंकड़े पक्के करता है।"))
            if fr2.button(t("Start setup", "सेटअप शुरू करें"), type="primary", key="btn_first_run_setup", use_container_width=True):
                st.switch_page(PAGES["setup"])
            if fr3.button(t("Not now", "अभी नहीं"), key="btn_first_run_skip", use_container_width=True):
                st.session_state["onboarded"] = True
                st.rerun()
    bal, _ = copilot.closing_balance(biz)
    limit = copilot.credit_limit(biz)
    items = open_items(pack, biz)
    cust = by_customer(items)
    late = cust[cust.oldest_days >= 45]
    n_overdue = len(overdue(items))
    counts = queue_counts(biz)
    waiting = counts[SUGGEST] + counts[ASK]
    sal = copilot.can_pay_salaries(biz, galla_cash=answer_galla())

    if showing_partial_view:
        st.warning(render_partial_view_notice(), icon=":material/visibility_off:")

    H(f'<div class="cc-tabmeta"><span>{svg(ICON_LOCK, 13)}{t("Read-only view", "केवल पढ़ने हेतु")}</span></div>')
    tab_sum, tab_act, tab_ins = st.tabs([t("Summary", "सारांश"), t("Recent activity", "हाल की गतिविधि"), t("Insights", "सुझाव")])

    # ── Summary: three figures, the month's cash, the morning briefing ──
    with tab_sum:
        month_start = config.AS_OF.normalize().replace(day=1)
        prev_close = balance_on(month_start - pd.Timedelta(days=1))
        delta = bal - prev_close if prev_close is not None else 0.0
        if prev_close and prev_close > 0:
            pct = delta / prev_close * 100
            trend = (f'<span class="{"up" if delta >= 0 else "down"}">{svg(ICON_TREND_UP if delta >= 0 else ICON_TREND_DOWN, 13, width=2.2)}'
                     f'{abs(pct):.1f}%</span>{t("vs last month", "पिछले महीने से")}')
        elif prev_close is not None:
            trend = (f'<span class="{"up" if delta >= 0 else "down"}">{svg(ICON_TREND_UP if delta >= 0 else ICON_TREND_DOWN, 13, width=2.2)}'
                     f'{"+" if delta >= 0 else "−"}{esc(inr(abs(delta)))}</span>{t("since", "से")} {month_start - pd.Timedelta(days=1):%d %b}')
        else:
            trend = t(f"Closing, {config.AS_OF:%d %b %Y}", f"अंतिम बैलेंस, {config.AS_OF:%d %b %Y}")
        cards = [kpi_card(0, t("Bank balance", "बैंक बैलेंस"), inr(bal), trend, ICON_BANK)]
        if limit:
            cards.append(kpi_card(1, t("Credit headroom", "क्रेडिट सीमा"), inr(bal + limit),
                                  t(f"of {esc(inr(limit))} sanctioned limit", f"स्वीकृत सीमा {esc(inr(limit))}"), ICON_ARROW_UR))
        else:
            cards.append(kpi_card(1, t("Credit headroom", "क्रेडिट सीमा"), t("No credit line", "कोई क्रेडिट लाइन नहीं"),
                                  t("No sanctioned cash-credit limit on file", "कोई स्वीकृत CC सीमा दर्ज नहीं"), ICON_ARROW_UR))
        cards.append(kpi_card(2, t("Receivables", "बाजार उधारी"), inr(items.outstanding.sum()),
                              t(f"{n_overdue} invoices need attention", f"{n_overdue} इनवॉइस पर ध्यान दें"), ICON_CLOCK, gold=True))
        H(f'<div class="cc-kpis">{"".join(cards)}</div>')
        st.write("")

        c_chart, c_brief = st.columns([1.5, 1], gap="medium")
        with c_chart:
            series = daily_balances(30)
            with st.container(key="cposcard"):
                h_l, h_r = st.columns([3, 1.3], vertical_alignment="top")
                with h_l:
                    H(f'<div class="cc-card-title">{t("Cash position", "नकद स्थिति")}</div>'
                      f'<div class="cc-card-sub">{t("Formal bank accounts · last 30 days", "औपचारिक बैंक खाते · पिछले 30 दिन")}</div>')
                with h_r:
                    with st.container(key="cposlink"):
                        st.page_link(PAGES["forecast"], label=t("View report", "रिपोर्ट देखें"), icon=":material/arrow_outward:")
                if len(series):
                    lo, hi = float(series.min()), float(series.max())
                    span = (hi - lo) or 1.0
                    peak = int(series.values.argmax())
                    ramp = ["#F1F5F9", "#E2E8F0", "#CBD5E1", "#94A3B8"]
                    bars = []
                    for i, (day, v) in enumerate(series.items()):
                        frac = (float(v) - lo) / span
                        shade = ramp[min(3, int(frac * 4))]
                        cls = ' class="hi"' if i == peak else ""
                        bars.append(f'<i{cls} style="--i:{i};height:{12 + frac * 88:.1f}%;background:{shade}" '
                                    f'title="{day:%d %b}: {esc(inr(float(v)))}"></i>')
                    mid = series.index[len(series) // 2]
                    H(f'<div class="cc-bars" role="img" aria-label="{esc(t("Daily closing bank balance for the last 30 days", "पिछले 30 दिनों का दैनिक बैंक बैलेंस"))}">'
                      f'{"".join(bars)}</div>'
                      f'<div class="cc-axis"><span>{series.index[0]:%d %b}</span><span>{mid:%d %b}</span><span>{series.index[-1]:%d %b}</span></div>')
        with c_brief:
            healthy = bool(sal.numbers.get("yes")) and (bal + (limit or 0)) > 0
            headline = (t("Your business is<br>in a healthy position.", "आपका व्यापार<br>अच्छी स्थिति में है।") if healthy
                        else t("A few things<br>need your attention.", "कुछ बातों पर<br>ध्यान देना है।"))
            change = (t("Cash increased this month.", "इस महीने नकद बढ़ा।") if delta >= 0
                      else t("Cash fell this month.", "इस महीने नकद घटा।"))
            if len(late):
                focus = t(f"The item worth reviewing is overdue receivables: {len(late)} customers are past 45 days.",
                          f"बाजार उधारी पर ध्यान दें: {len(late)} ग्राहक 45 दिन से अधिक बकाया।")
            elif waiting:
                focus = t(f"{waiting:,} receipts are waiting for a decision.", f"{waiting:,} प्रविष्टियों पर निर्णय बाकी है।")
            else:
                focus = t("Nothing needs your attention today.", "आज किसी बात पर तुरंत ध्यान देने की जरूरत नहीं।")
            if is_hi():
                speech = (f"नमस्ते {BIZ_NAME}। बैंक बैलेंस {inr(bal)} है। कुल बाजार उधारी {inr(items.outstanding.sum())} है। "
                          f"{'1 अक्टूबर की सैलरी सुरक्षित है।' if sal.numbers.get('yes') else '1 अक्टूबर की सैलरी के लिए योजना जरूरी है।'} {focus}")
            else:
                speech = (f"Good morning, {BIZ_NAME}. Your bank balance is {inr(bal)}. Formal receivables total {inr(items.outstanding.sum())}. "
                          f"{'October 1 salaries are covered.' if sal.numbers.get('yes') else 'October 1 salaries need cash planning.'} {focus}")
            render_briefing_card(headline, f"{change} {focus}", speech)

    # ── Recent activity: the latest bank entries and where each one stands ──
    with tab_act:
        tiers = {m.txn_id: m.tier for m in matches.values() if m.business_id == biz}
        recent = _biz_bank()
        recent = recent[recent.amount.abs() >= 1].tail(7).iloc[::-1]
        rows = []
        for i, (_, r) in enumerate(recent.iterrows()):
            inflow = float(r.credit_inr or 0) > 0
            amt = float(r.credit_inr if inflow else r.debit_inr)
            status = STATUS_LABEL.get(tiers.get(r.txn_id), None)
            chip = f'<span class="cc-tag {status[1]}">{esc(t(status[0], status[0]))}</span>' if status else ""
            rows.append(
                f'<div class="cc-act-row" style="--i:{i}"><span class="cc-act-ic{" in" if inflow else ""}">'
                f'{svg(ICON_MONEY_IN if inflow else ICON_MONEY_OUT, 17)}</span>'
                f'<div style="min-width:0"><div class="cc-act-t">{esc(party_from(r.narration))}</div>'
                f'<div class="cc-act-d"><span>{r.txn_date:%d %b}</span><span>·</span><span>{esc(r.channel)}</span>{chip}</div></div>'
                f'<div class="cc-act-a{" in" if inflow else ""}">{"+" if inflow else "−"}{esc(inr(amt))}'
                f'<small>{t("Balance", "बैलेंस")} {esc(inr(float(r.balance_inr)))}</small></div></div>')
        H(f'<div class="cc-act">{"".join(rows)}</div>')
        if waiting:
            st.write("")
            _action_row("act_review", t(f"{waiting:,} receipts need a decision", f"{waiting:,} जमा पर्चियों पर निर्णय बाकी"),
                        t(f"{counts[SUGGEST]:,} suggested matches and {counts[ASK]:,} questions. Another {counts['auto']:,} were matched automatically.",
                          f"{counts[SUGGEST]:,} सुझाव और {counts[ASK]:,} सवाल। अन्य {counts['auto']:,} स्वतः मिलान हो चुके हैं।"),
                        t("Start review", "समीक्षा शुरू करें"), PAGES["review"])

    # ── Insights: what to do today, and the detail behind the numbers ──
    with tab_ins:
        if showing_partial_view:
            H(f'<div class="cc-insight-note">{t("Unlock the vault from the sidebar to add drawer cash, khata and the morning action to these insights.", "ड्रॉअर नकद, खाता और सुबह की कार्रवाई देखने के लिए साइडबार से वॉल्ट खोलें।")}</div>')
            st.write("")
            if waiting:
                _action_row("review", t(f"{waiting:,} receipts need a decision", f"{waiting:,} जमा पर्चियों पर निर्णय बाकी"),
                            t(f"{counts[SUGGEST]:,} suggested matches and {counts[ASK]:,} questions.",
                              f"{counts[SUGGEST]:,} सुझाव और {counts[ASK]:,} सवाल।"),
                            t("Start review", "समीक्षा शुरू करें"), PAGES["review"])
            if len(late):
                _action_row("late", t(f'{len(late)} customers are more than 45 days overdue {tag(inr(late.outstanding.sum()), "warn")}',
                                      f'{len(late)} ग्राहकों पर 45 दिन से अधिक का बकाया {tag(inr(late.outstanding.sum()), "warn")}'),
                            t("Start with the largest. Each reminder opens as a WhatsApp draft for you to send.",
                              "सबसे बड़े बकायेदार से शुरू करें। प्रत्येक तकादा WhatsApp पर ड्राफ्ट होगा।"),
                            t("Open chasing list", "वसूली सूची देखें"), PAGES["recv"])
            return

        if is_owner and not st.session_state.get("onboarding_dismissed", False):
            c_on1, c_on2 = st.columns([5, 1], vertical_alignment="center")
            with c_on1:
                H(f'<div class="cc-onboard">'
                  f'<div><b>{t("Quick setup:", "त्वरित सेटअप:")}</b> '
                  f'{t("Owner PIN active", "मालिक PIN सक्रिय")} · '
                  f'{t("Cash-credit headroom monitored", "CC सीमा पर नज़र")} · '
                  f'{t("Cash drawer private to the owner", "गल्ला केवल मालिक के लिए")}</div>'
                  f'</div>')
            with c_on2:
                if st.button(t("Dismiss", "हटाएं"), key="btn_dismiss_onboard", use_container_width=True):
                    st.session_state["onboarding_dismissed"] = True
                    st.rerun()

        galla = vault.get_latest_galla(biz)
        khata = vault.get_khata_summary(biz)
        galla_demo = bool(galla and galla.is_demo)
        khata_demo = any(getattr(a, "is_demo", False) for a in khata["accounts"])
        alpha = config.KHATA_COLLECTION_ASSUMPTION
        if is_owner and "khata_alpha_pct" in st.session_state:
            alpha = st.session_state["khata_alpha_pct"] / 100
        solvency = compute_total_solvency(pack, vault, biz, haircut_alpha=alpha)
        runway = solvency.true_cash_runway_inr
        total_liquid = solvency.net_bank_liquidity + solvency.galla_cash
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

        # Today's one action
        if len(late) > 0:
            top_late = late.iloc[0]
            c_name = top_late["customer_name"]
            c_due = inr(top_late["outstanding"])
            c_days = int(top_late["oldest_days"])
            c_phone = "910000000001"
            biz_name = get_business_name(biz)
            if c_days >= 900:
                if is_hi():
                    wa_msg = (
                        f"नमस्ते {c_name} जी, आशा है आप सकुशल हैं। {biz_name} के रिकॉर्ड अनुसार, "
                        f"हमारी पिछली आपूर्ति का {c_due} बकाया है। क्या आप कृपया पुष्टि कर सकते हैं कि यह "
                        f"आपकी बहियों से मेल खाता है, या बताएं कि हम कब तक छोटे भुगतान की उम्मीद कर सकते हैं? धन्यवाद!"
                    )
                else:
                    wa_msg = (
                        f"Namaste {c_name} ji, hope you are doing well. As per our records with {biz_name}, "
                        f"the pending balance is {c_due} from our earlier supplies. Could you please confirm if this matches "
                        f"your books, or let us know when we can expect a small part-settlement? Thank you!"
                    )
            else:
                if is_hi():
                    wa_msg = f"नमस्ते {c_name}, {biz_name} का {c_due} बकाया ({c_days} दिन) लंबित है। कृपया जल्द से जल्द भुगतान करें।"
                else:
                    wa_msg = f"Namaste {c_name}, {biz_name} balance of {c_due} is overdue ({c_days} days). Kindly clear at your earliest convenience."
            wa_url = f"https://wa.me/{c_phone}?text={_html.escape(wa_msg)}"
            limitation_badge = ""
            if c_days >= 900:
                lim_act_tip = t("Section 18 Limitation Act: Trade debts older than 3 years become legally time-barred without a written acknowledgement or payment.",
                                "3 साल से पुराने बकाये की वसूली में कानूनी अड़चन आ सकती है।")
                limitation_badge = f'<span class="cc-badge warn" data-tip="{lim_act_tip}">{svg(ICON_ALERT, 12, width=2.4)}30+ Mo (Section 18 Limitation Act)</span>'
            H(f"""
            <div class="cc-action-card" style="border-left:4px solid #D97706;background:#FFFBEB;margin-bottom:16px;padding:18px 22px;">
              <div style="flex:1;min-width:260px;">
                <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                  <span style="font-size:0.66rem;font-weight:700;color:#B45309;text-transform:uppercase;letter-spacing:0.22em;">{t("Today's one action", "आज की एक जरूरी कार्रवाई")}</span>
                  {limitation_badge}
                </div>
                <div style="font-size:1.05rem;font-weight:700;color:#17191D;margin-top:6px;">
                  {esc(c_name)} {t("owes", "बकाया")} {esc(c_due)} ({c_days} {t("days overdue", "दिन पुराना")})
                </div>
                <div style="font-size:0.84rem;color:#475569;margin-top:2px;">
                  {t("Collect, or get a written acknowledgement before the 3-year limit.", "3 साल की सीमा से पहले वसूली करें या लिखित पुष्टि लें।")}
                </div>
              </div>
              <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
                <a href="{wa_url}" target="_blank" class="cc-wa-btn" data-tip="{t('Opens a pre-filled WhatsApp message draft in WhatsApp Web. You review and click Send yourself.', 'WhatsApp पर शिष्टाचारपूर्ण संदेश ड्राफ्ट होगा।')}">
                  {t("Draft WhatsApp reminder", "WhatsApp तकादा")}
                </a>
              </div>
            </div>
            """)
        elif not sal.numbers["yes"]:
            H(f'<div class="cc-action-card" style="border-left:4px solid #EF4444;background:#FEF2F2;margin-bottom:16px;padding:18px 22px;">'
              f'<div style="flex:1;"><div style="font-size:0.66rem;font-weight:700;color:#991B1B;text-transform:uppercase;letter-spacing:0.22em;">{t("Action required", "ध्यान दें")}</div>'
              f'<div style="font-size:1.05rem;font-weight:700;color:#17191D;margin-top:6px;">{t("1 Oct payroll needs cash planning", "1 अक्टूबर वेतन के लिए नकद योजना आवश्यक")}</div></div></div>')

        # Net usable cash: one figure, the working one tap away
        H(f'<div class="cc-card-modern" style="padding:26px 28px;margin-bottom:16px;">'
          f'<div class="cc-label">{t("Net usable cash today", "आज खर्च करने योग्य नकदी")}</div>'
          f'<div style="display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;margin-top:10px;">'
          f'<div class="cc-hero" style="margin:0;font-size:clamp(2.2rem,4.5vw,2.8rem);">{esc(inr(total_liquid))}</div>'
          f'<span class="cc-muted">{t(f"Bank headroom {inr(solvency.net_bank_liquidity)} + drawer cash {inr(solvency.galla_cash)}", f"बैंक सीमा {inr(solvency.net_bank_liquidity)} + गल्ला {inr(solvency.galla_cash)}")}</span></div>'
          f'<div class="cc-muted" style="margin-top:8px;">{esc(month_sub)}</div></div>')
        with st.expander(t("Show how this is calculated", "यह हिसाब कैसे निकला, देखें"), expanded=False):
            if is_owner:
                st.slider(t("Khata collection assumption", "खाता वसूली अनुमान"), min_value=50, max_value=100,
                          value=int(round(alpha * 100)), step=5, format="%d%%", key="khata_alpha_pct",
                          help=t("Adjustable informal khata recovery expectation", "खाता वसूली की संभावित दर"))
            if galla_demo or khata_demo:
                H(f'<div class="cc-note" style="margin-bottom:8px;">{t("Drawer and khata figures include demo data, not from the pilot pack.", "गल्ला और खाते के आंकड़े डेमो डेटा से हैं।")}</div>')
            tiles(
                tile(t("Bank balance", "बैंक बैलेंस") if not solvency.cc_drawn else t("Bank balance less overdraft", "बैंक बैलेंस (ओवरड्राफ्ट घटाकर)"),
                     inr(solvency.bank_balance - solvency.cc_drawn), close_sub,
                     tip=t("Current account closing balance minus active cash-credit drawing.", "बैंक बैलेंस (ओवरड्राफ्ट घटाकर)")),
                tile(t("+ Cash in drawer", "+ गल्ले में नकद कैश"), inr(solvency.galla_cash), galla_sub,
                     tip=t("Physical cash counted in the godown counter till today.", "गल्ले में नकद कैश")),
                tile(t("+ Khata you expect back", "+ बाजार से संभावित वसूली"), inr(solvency.total_expected_inflows), khata_sub,
                     tip=t("Total informal khata receivables discounted by your collection assumption.", "बाजार से संभावित वसूली")),
                tile(t("− Due in next 30 days", "− अगले 30 दिन के खर्चे"), inr(solvency.total_commitments), comm_sub,
                     tip=t("Upcoming commitments: Staff salaries, open vendor bills, and supplier payments.", "अगले 30 दिन के खर्चे")),
                tile(t("= Your own-cash buffer", "= आपकी शुद्ध नकद सुरक्षा"), inr(runway), month_sub,
                     "accent" if runway >= 0 else "neg",
                     tip=t("Own-cash buffer available to operate before touching bank borrowing lines.", "शुद्ध नकद सुरक्षा बफर")),
            )
            H(f'<div class="cc-note" style="margin-top:6px;">{t("Formula: (Bank Balance − Overdraft) + Drawer Cash + (Expected Khata × Assumption) − 30-Day Commitments = Own-Cash Buffer", "सूत्र: (बैंक बैलेंस − ओवरड्राफ्ट) + गल्ला नकद + (संभावित खाता वसूली × दर) − 30 दिन के खर्चे = शुद्ध नकद सुरक्षा")}</div>')

        st.write("")
        H(f'<div class="cc-label" style="margin:4px 0 12px">{t("Also on your list today", "आज की सूची में और भी")}</div>')
        if len(late):
            _action_row("late", t(f'{len(late)} customers are more than 45 days overdue {tag(inr(late.outstanding.sum()), "warn")}',
                                  f'{len(late)} ग्राहकों पर 45 दिन से अधिक का बकाया {tag(inr(late.outstanding.sum()), "warn")}'),
                        t("Start with the largest. Each reminder opens as a WhatsApp draft for you to send.",
                          "सबसे बड़े बकायेदार से शुरू करें। प्रत्येक तकादा WhatsApp पर ड्राफ्ट होगा।"),
                        t("Open chasing list", "वसूली सूची देखें"), PAGES["recv"])
        if waiting:
            _action_row("review", t(f"{waiting:,} receipts need a decision", f"{waiting:,} जमा पर्चियों पर निर्णय बाकी"),
                        t(f"{counts[SUGGEST]:,} suggested matches and {counts[ASK]:,} questions. Another {counts['auto']:,} were matched automatically.",
                          f"{counts[SUGGEST]:,} सुझाव और {counts[ASK]:,} सवाल। अन्य {counts['auto']:,} स्वतः मिलान हो चुके हैं।"),
                        t("Start review", "समीक्षा शुरू करें"), PAGES["review"])
        _action_row("slips", t("Record today's collection slips", "आज की वसूली पर्चियां दर्ज करें"),
                    t("Salesman slips let cash deposits link to the right shop invoices.",
                      "सेल्समैन की पर्चियों से कैश जमा सीधे सही दुकान के इनवॉइस से जुड़ जाता है।"),
                    t("Record slips", "पर्ची दर्ज करें"), PAGES["cash"])
        n = sal.numbers
        if n["yes"]:
            title = t(f'Salaries on 1 Oct are covered {tag("Covered", "pos")}', f'1 अक्टूबर की सैलरी सुरक्षित है {tag("सुरक्षित", "pos")}')
        else:
            title = t(f'Salaries on 1 Oct need a plan {tag("Check", "warn")}', f'1 अक्टूबर की सैलरी के लिए योजना जरूरी {tag("ध्यान दें", "warn")}')
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
            with st.container(key="row_recovery_sheet"):
                r_a, r_b = st.columns([5, 1.6], vertical_alignment="center")
                with r_a:
                    H(f'<div class="cc-row-title">{t("Daily field recovery sheet", "दैनिक फील्ड वसूली शीट")}</div>'
                      f'<div class="cc-row-detail">{t(f"Print or export today’s {len(late)} overdue retailers with checkboxes and signature lines.", f"45+ दिन पुराने {len(late)} बकायेदारों की प्रिंट शीट, चेकबॉक्स और हस्ताक्षर सहित।")}</div>')
                with r_b:
                    if st.button(t("Print sheet", "शीट प्रिंट करें"), key="btn_ov_print_sheet", use_container_width=True):
                        daily_print_dialog()


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
    latest_g = vault.get_latest_galla(biz)
    default_open = latest_g.counted_cash if latest_g else 0.0
    with st.form("galla_close_form", border=False):
        c1, c2 = st.columns(2)
        open_cash = c1.number_input(t("Opening till cash (₹)", "सुबह का शुरुआती नकद (₹)"), value=float(default_open), step=500.0)
        takings = c2.number_input(t("Today's cash takings (₹)", "आज की नकद बिक्री (₹)"), value=0.0, step=500.0)
        expenses = c1.number_input(t("Cash expenses paid (₹)", "नकद खर्चे व हमाली (₹)"), value=0.0, step=100.0, help=t("Hamali, petty and other cash expenses", "हमाली, चाय-पानी व अन्य खर्चे"))
        banked = c2.number_input(t("Cash banked into account (₹)", "बैंक खाते में जमा नकद (₹)"), value=0.0, step=500.0)
        expected_close = open_cash + takings - expenses - banked
        phys_count = c1.number_input(t("Physical count at close (₹)", "शाम को गल्ले में बचा नकद (₹)"), value=float(expected_close), step=500.0)
        notes = c2.text_input(t("Notes", "विवरण / नोट"), placeholder=t("e.g. Evening till balance", "उदा. शाम का गल्ला मिलान"))
        submitted = st.form_submit_button(t("Record in cash book", "रोकड़ बही में दर्ज करें"), type="primary")
    if submitted:
        entry = GallaEntry(
            business_id=biz,
            date=config.AS_OF,
            opening_cash=open_cash,
            cash_in=takings,
            cash_out=expenses,
            cash_banked=banked,
            counted_cash=phys_count,
            notes=notes or "Daily Close",
            is_demo=False,
        )
        vault.record_galla(entry)
        st.session_state["toast"] = t("Recorded locally in Cash Book. Balance updated.", "रोकड़ बही में दर्ज हुआ। बैलेंस अपडेट हो गया।")
        st.rerun()


@st.dialog("Record collection slips")
def collections_dialog():
    H(f'<div class="cc-muted">{t("What each salesman collected from shops. Used to match cash deposits to invoices.", "दुकानों से सेल्समैन द्वारा की गई वसूली। बैंक जमा को इनवॉइस से जोड़ने के लिए उपयोगी।")}</div>')

    # Optional Vision OCR upload
    slip_file = st.file_uploader(t("Scan handwritten slip photo (Optional)", "हाथ से लिखी पर्ची की फोटो खींचें (वैकल्पिक)"),
                                 type=["jpg", "jpeg", "png", "webp"], key="_slip_upload_img")

    # Autocomplete verified parties from pack.parties
    biz_parties = []
    if hasattr(pack, "parties") and pack.parties is not None:
        p_df = pack.parties[pack.parties["business_id"] == biz]
        if not p_df.empty:
            biz_parties = sorted(p_df["party_name"].dropna().unique().tolist())
    if not biz_parties:
        biz_parties = ["Laxmi Super Mart, Bibwewadi", "Gajanan Departmental Store, Shivajinagar", "Balaji Provision Stores, Sinhagad Road"]

    slip_count = len(vault.get_collections(biz)) if vault.is_unlocked() else 0
    slip_preview = f"SLIP-{config.AS_OF:%m%d}-{slip_count + 1:02d}"

    prefill_shop = ""
    prefill_amount = 0.0
    prefill_salesman = ""
    prefill_date = pd.Timestamp("2026-09-30")
    prefill_mode = "Cash"
    prefill_slip_no = ""
    confidence_score = 0.0

    if slip_file:
        with st.spinner(t("Scanning slip with Gemini Vision…", "Gemini AI से पर्ची पढ़ी जा रही है…")):
            raw_slip_bytes = slip_file.getvalue()
            sanitized_bytes = sanitize_slip_image(raw_slip_bytes)
            ocr_data = ocr_collection_slip(sanitized_bytes, mime_type=slip_file.type or "image/jpeg")

            raw_retailer = str(ocr_data.get("retailer_name") or ocr_data.get("shop") or "").strip()
            prefill_amount = float(ocr_data.get("amount", 0.0) or 0.0)
            prefill_salesman = str(ocr_data.get("salesman", "") or "").strip()
            raw_mode = str(ocr_data.get("payment_mode", "Cash") or "Cash").strip()
            raw_date = str(ocr_data.get("date", "") or "").strip()
            raw_slip = str(ocr_data.get("slip_no", "") or "").strip()
            confidence_score = float(ocr_data.get("confidence", 0.95) or 0.95)

            if raw_retailer and biz_parties:
                matched_party, match_score = match_retailer_name(raw_retailer, biz_parties)
                if match_score > 0 and matched_party in biz_parties:
                    prefill_shop = matched_party
                else:
                    prefill_shop = raw_retailer
            else:
                prefill_shop = raw_retailer

            mode_upper = raw_mode.upper()
            if "UPI" in mode_upper:
                prefill_mode = "UPI"
            elif "CHEQ" in mode_upper or "CHQ" in mode_upper:
                prefill_mode = "Cheque"
            else:
                prefill_mode = "Cash"

            if raw_date:
                try:
                    prefill_date = pd.Timestamp(raw_date)
                except Exception:
                    prefill_date = pd.Timestamp("2026-09-30")

            if raw_slip:
                prefill_slip_no = raw_slip

            if raw_retailer or prefill_amount > 0 or prefill_salesman:
                st.info(t(
                    f"AI Confidence: {confidence_score*100:.0f}% · Matched: {prefill_shop or 'Shop'}",
                    f"एआई सटीकता: {confidence_score*100:.0f}% · मिलान: {prefill_shop or 'दुकान'}"
                ))
            else:
                st.warning(t("Could not auto-detect slip details. Please enter manually below.",
                             "पर्ची का विवरण स्वतः नहीं पढ़ा जा सका। कृपया नीचे स्वयं दर्ज करें।"))

    shop_default_idx = 0
    if prefill_shop and prefill_shop in biz_parties:
        shop_default_idx = biz_parties.index(prefill_shop)

    with st.form("collections_today_form", border=False):
        c1, c2 = st.columns(2)
        col_date = c1.date_input(t("Collection date", "वसूली की तारीख"), value=prefill_date)
        salesman_options = ["Ramesh Kumar", "Suresh Shinde", "Vijay Patil", "Other"]
        salesman_val = c2.selectbox(t("Salesman", "सेल्समैन का नाम"), salesman_options,
                                    index=salesman_options.index(prefill_salesman) if prefill_salesman in salesman_options else 0)

        c3, c4 = st.columns([2, 1])
        shop_val = c3.selectbox(t("Retail Shop (Verified Party)", "दुकान का नाम"), biz_parties, index=shop_default_idx)
        amt_val = c4.number_input(t("Amount (₹)", "रकम (₹)"), value=float(prefill_amount) if prefill_amount > 0 else 0.0, step=500.0, min_value=0.0)

        c5, c6 = st.columns([1, 1])

        mode_options = ["Cash", "UPI", "Cheque"]
        mode_idx = mode_options.index(prefill_mode) if prefill_mode in mode_options else 0
        payment_mode = c5.radio(
            t("Payment Mode", "भुगतान का प्रकार"),
            mode_options,
            index=mode_idx,
            horizontal=True,
            key="_col_pay_mode"
        ) or "Cash"
        slip_no_val = c6.text_input(t("Slip No Preview", "पर्ची नंबर"), value=prefill_slip_no or slip_preview, help=t("Auto-generated slip identifier", "स्वतः उत्पन्न पर्ची नंबर"))

        inv_link_mode = st.radio(
            t("Invoice Allocation Mode", "इनवॉइस आवंटन विधि"),
            ["FIFO (Oldest Invoices First)", "Specific Invoice"],
            horizontal=True,
            key="_col_alloc_mode"
        )

        selected_invoice_no = ""
        if inv_link_mode == "Specific Invoice":
            open_invs = open_items(pack, biz)
            shop_invs = open_invs[open_invs["customer_name"].str.strip().str.lower() == shop_val.strip().lower()]
            if shop_invs.empty:
                shop_invs = open_invs
            inv_choices = [
                f"{r.invoice_no} · Due: {inr(r.outstanding)} · {r.invoice_date:%d-%b-%Y}"
                for r in shop_invs.itertuples()
            ]
            if inv_choices:
                inv_sel = st.selectbox(t("Select Open Invoice", "बकाया इनवॉइस चुनें"), inv_choices)
                selected_invoice_no = inv_sel.split("·")[0].strip()
            else:
                st.info(t("No open invoices for this customer. Allocation rolls to FIFO / On Account.", "इस ग्राहक के लिए कोई खुला इनवॉइस नहीं है।"))

        notes_val = st.text_input(t("Notes / Route Remarks", "टिप्पणी / रूट विवरण"), placeholder=t("e.g. Daily route collection", "उदा. दैनिक रूट वसूली"))

        col_sub = st.form_submit_button(t("Record Collection Slip", "पर्ची दर्ज करें"), type="primary")

    if col_sub:
        if amt_val <= 0:
            st.error(t("Please enter an amount greater than 0.", "कृपया 0 से अधिक राशि दर्ज करें।"))
        else:
            mode_upper = payment_mode.upper()
            coll_obj = Collection(
                business_id=biz,
                date=pd.Timestamp(col_date),
                shop=shop_val,
                amount=float(amt_val),
                salesman=salesman_val,
                payment_mode=mode_upper,
                slip_id=slip_no_val.strip() or slip_preview,
                invoice_no=selected_invoice_no,
                notes=notes_val or f"Route collection by {salesman_val}",
            )
            assigned_id = vault.record_collection(coll_obj, update_drawer=True)
            toast_text = t(
                f"Slip {assigned_id} recorded ({payment_mode}: {inr(amt_val)} for {shop_val}).",
                f"पर्ची {assigned_id} दर्ज हुई ({payment_mode}: {inr(amt_val)} - {shop_val})।"
            )
            st.session_state["toast"] = toast_text
            st.rerun()


def page_cash_book():
    def share_toggle():
        if is_owner:
            st.toggle(t("Share my cash book with my accountant", "मुनीम/एकाउंटेंट के साथ रोकड़ बही साझा करें"), key="_share_widget",
                      value=st.session_state["share_cash_book"],
                      help=t("When off, the Accountant (CA) role sees formal books only.", "बंद होने पर एकाउंटेंट केवल बैंक का औपचारिक हिसाब देख सकते हैं।"),
                      on_change=lambda: st.session_state.update(share_cash_book=st.session_state["_share_widget"]))
        else:
            ask_button()

    page_header(t("Cash book", "रोकड़ बही (Cash Book)"),
                t("Drawer cash and informal khata. Kept on this device only.", "गल्ले का नकद और कच्चा खाता। केवल इस डिवाइस पर सुरक्षित।"),
                right=share_toggle)

    if showing_partial_view:
        st.warning(render_partial_view_notice(), icon=":material/visibility_off:")

        left, right = st.columns([2, 1], gap="large")
        with left:
            H(f"""
            <div class="cc-card-modern" style="border-left:4px solid #DC2626;background:#FEF2F2;">
              <div style="font-size:1rem;font-weight:700;color:#991B1B;display:flex;align-items:center;gap:8px;">
                <span>Sovereign Cash Book Locked</span>
                <span class="cc-badge warn">Owner PIN Required</span>
              </div>
              <div style="font-size:0.86rem;color:#7F1D1D;margin-top:6px;line-height:1.5;">
                {t("Formal books only. Godown counter cash drawer (galla), pending khata accounts, and route collection slips are protected on-device with AES-256 authenticated encryption. Enter the Owner PIN in the sidebar (or below) to unlock sovereign books.",
                   "केवल औपचारिक खाते। गल्ला, कच्चा खाता और वसूली पर्चियां AES-256 एन्क्रिप्शन से सुरक्षित हैं। देखने हेतु मालिक का PIN दर्ज करें।")}
              </div>
            </div>
            """)

            if not is_owner:
                H(vault_role_note(role))
            else:
              with st.container(border=True):
                H(f'<div class="cc-h2">{t("Unlock Sovereign Vault", "वॉल्ट अनलॉक करें")}</div>')
                c_pin1, c_pin2 = st.columns([1.5, 1])
                inline_pin = c_pin1.text_input(
                    t("Owner PIN", "मालिक PIN"),
                    type="password",
                    max_chars=4,
                    key="inline_cashbook_pin",
                    help=t("Demo PIN: 0000", "डेमो PIN: 0000"),
                    placeholder="0000",
                )
                if c_pin2.button(t("Unlock Vault", "अनलॉक करें"), key="btn_unlock_cashbook_inline", type="primary", use_container_width=True):
                    expected_pin = os.environ.get("COPILOT_OWNER_PIN") or "0000"
                    if inline_pin == expected_pin or (inline_pin and vault.unlock(inline_pin)):
                        vault.unlock(inline_pin or expected_pin)
                        st.session_state["vault_unlocked"] = True
                        st.session_state["toast"] = t("Vault unlocked. Sovereign Plane Active.", "वॉल्ट अनलॉक हुआ। सॉवरेन प्लेन सक्रिय।")
                        st.rerun()
                    else:
                        st.error(t("Incorrect PIN.", "गलत PIN दर्ज किया गया।"))
                H(f'<div class="cc-note">{t("Demo PIN: 0000 · Hardware-backed PBKDF2 key derivation", "डेमो PIN: 0000 · ऑन-डिवाइस सुरक्षा")}</div>')

        with right:
            with st.container(key="cc_panel"):
                bank_cash_deposits = float(pack.bank[(pack.bank["business_id"] == biz) & (pack.bank["channel"] == "CASH")]["credit_inr"].sum())
                facts_res = cash_deposit_reporting_facts(bank_cash_deposits)
                checklist = deposit_records_checklist()
                items_html = "".join(f'<li>{svg(ICON_BOX_CHECK, 16, MUTED)}{esc(doc)}</li>' for doc in checklist["documents"])
                H(f'<div class="cc-h2" role="heading" aria-level="2">{t("Bank Cash Deposits (Formal Plane)", "बैंक नकद जमा (औपचारिक)")}</div>'
                  f'<div class="cc-hero" style="font-size:1.6rem">{esc(inr(bank_cash_deposits))}</div>'
                  f'<div class="cc-muted" style="color:#475569">{esc(facts_res.message)}</div>'
                  f'<div class="cc-note" style="margin-top:8px">{esc(facts_res.citation)}</div>'
                  f'<div style="border-top:1px solid #EDEDE9;margin:14px 0 10px"></div>')
                with st.expander(t("Records checklist before depositing cash", "नकद जमा से पहले जरूरी रिकॉर्ड"), expanded=False):
                    H(f'<ul class="cc-list sm">{items_html}</ul>'
                      f'<div class="cc-note" style="margin-top:12px">{esc(checklist["referral"])}</div>')

        return

    left, right = st.columns([2, 1], gap="large")
    with left:
        latest_g = vault.get_latest_galla(biz)
        demo = DEMO if latest_g and latest_g.is_demo else ""
        when = f"{esc(latest_g.notes)} · {latest_g.date:%d %b %Y}" if latest_g else ""

        open_c = float(getattr(latest_g, "opening_cash", 10000.0)) if latest_g else 10000.0
        in_c = float(getattr(latest_g, "cash_in", 25000.0)) if latest_g else 25000.0
        out_c = float(getattr(latest_g, "cash_out", 2500.0)) if latest_g else 2500.0
        banked_c = float(getattr(latest_g, "cash_banked", 20000.0)) if latest_g else 20000.0
        counted_c = float(getattr(latest_g, "counted_cash", 12500.0)) if latest_g else 12500.0

        bal = calculate_drawer_balance(open_c, in_c, out_c, banked_c, counted_c)
        expected_close = bal["expected_cash"]
        drift = bal["drift"]
        is_bal = bal["is_balanced"]

        bal_tip = (
            t("Physical cash in till matches opening float + parchi cash in − expenses − banked CDM.",
              "गल्ला मिलान: शुरुआती रोकड़ + पर्ची नकद आवक − खर्च − बैंक जमा।")
            if is_bal
            else t("Discrepancy detected between counted cash and 5-part drawer equation.", "गल्ले में असंगति पाई गई")
        )
        bal_badge = (
            f'<span class="cc-badge pos" data-tip="{bal_tip}">{svg(ICON_CHECK, 12, width=2.6)}Ties exactly</span>'
            if is_bal
            else f'<span class="cc-badge warn" data-tip="{bal_tip}">{esc(inr(drift))} Drift to check</span>'
        )

        # ── Interactive 5-Part Cash Drawer Balancing Cockpit Card ──
        prof = config.get_profile(biz)
        if getattr(prof, "archetype", "") == "clinic":
            drawer_title = t("Front Desk & Till Cash Balancing Cockpit", "रिसेप्शन व काउंटर नकद मिलान")
        elif getattr(prof, "archetype", "") == "agency":
            drawer_title = t("Cash Drawer Balancing Cockpit", "दैनिक नकद रोकड़ मिलान")
        else:
            drawer_title = t("Godown Cash Drawer Balancing Cockpit", "दैनिक गल्ला रोकड़ मिलान")

        H(f"""
        <div class="cc-card-modern">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:12px;">
            <div>
              <div style="font-size:1.05rem;font-weight:700;color:#17191D;" data-tip="{t('End-of-day till reconciliation against 5-part cash equation.', 'दैनिक गल्ला रोकड़ मिलान')}">{drawer_title} {demo}</div>
              <div style="font-size:0.78rem;color:#64748B;">{t("Opening Float + Parchi Cash In − Petty Expenses − Banked CDM = Expected Close", "शुरुआती नकद + पर्ची नकद − खर्च − बैंक जमा = अपेक्षित गल्ला")} · {when}</div>
            </div>
            {bal_badge}
          </div>

          <div style="background:#F8FAFC;border:1px solid #E5E5E1;border-radius:10px;padding:12px 14px;margin-bottom:12px;">
            <div style="display:grid;grid-template-columns:repeat(5, 1fr);gap:8px;text-align:center;">
              <div>
                <div style="font-size:0.72rem;font-weight:600;color:#64748B;text-transform:uppercase;">Opening Float</div>
                <div style="font-size:1.05rem;font-weight:700;color:#17191D;margin-top:2px;">{esc(inr(open_c))}</div>
              </div>
              <div>
                <div style="font-size:0.72rem;font-weight:600;color:#059669;text-transform:uppercase;">+ Parchi In</div>
                <div style="font-size:1.05rem;font-weight:700;color:#059669;margin-top:2px;">+{esc(inr(in_c))}</div>
              </div>
              <div>
                <div style="font-size:0.72rem;font-weight:600;color:#DC2626;text-transform:uppercase;">− Expenses</div>
                <div style="font-size:1.05rem;font-weight:700;color:#DC2626;margin-top:2px;">−{esc(inr(out_c))}</div>
              </div>
              <div>
                <div style="font-size:0.72rem;font-weight:600;color:#17191D;text-transform:uppercase;">− Banked CDM</div>
                <div style="font-size:1.05rem;font-weight:700;color:#17191D;margin-top:2px;">−{esc(inr(banked_c))}</div>
              </div>
              <div style="border-left:2px solid #E5E5E1;padding-left:8px;">
                <div style="font-size:0.72rem;font-weight:700;color:#17191D;text-transform:uppercase;">= Expected</div>
                <div style="font-size:1.05rem;font-weight:800;color:#17191D;margin-top:2px;">{esc(inr(expected_close))}</div>
              </div>
            </div>
          </div>

          <div style="display:grid;grid-template-columns:repeat(3, 1fr);gap:10px;">
            <div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:8px;padding:10px 12px;">
              <span style="font-size:0.72rem;font-weight:700;color:#166534;display:block;">Physical Till Count</span>
              <span style="font-size:1.35rem;font-weight:800;color:#166534;">{esc(inr(counted_c))}</span>
            </div>
            <div style="background:#F8FAFC;border:1px solid #E5E5E1;border-radius:8px;padding:10px 12px;">
              <span style="font-size:0.72rem;font-weight:700;color:#475569;display:block;">Expected Cash</span>
              <span style="font-size:1.35rem;font-weight:800;color:#17191D;">{esc(inr(expected_close))}</span>
            </div>
            <div style="background:{'#F0FDF4' if is_bal else '#FEF2F2'};border:1px solid {'#BBF7D0' if is_bal else '#FECACA'};border-radius:8px;padding:10px 12px;">
              <span style="font-size:0.72rem;font-weight:700;color:{'#166534' if is_bal else '#991B1B'};display:block;">Drawer Drift</span>
              <span style="font-size:1.35rem;font-weight:800;color:{'#166534' if is_bal else '#DC2626'};">{esc(inr(drift))}</span>
            </div>
          </div>
        </div>
        """)

        b1, b2, _ = st.columns([1.2, 1.6, 1.2])
        if b1.button(t("Close the day", "आज का गल्ला बंद करें"), type="primary", key="open_day_close", use_container_width=True):
            day_close_dialog()
        if b2.button(t("Record collection slips", "वसूली पर्ची दर्ज करें"), key="open_slips", use_container_width=True):
            collections_dialog()

        # ── Active Collection Slips Ledger Table ──
        slips = vault.get_collections(biz)
        if slips:
            H(f'<div class="cc-h2" style="margin-top:22px;margin-bottom:8px;">{t("Recent Collection Slips", "दैनिक वसूली पर्चियां")} <span class="cc-badge neutral">{len(slips)}</span></div>')
            tot_all = sum(s.amount for s in slips)
            tot_cash = sum(s.amount for s in slips if getattr(s, "payment_mode", "CASH").upper() == "CASH")
            tot_upi = sum(s.amount for s in slips if getattr(s, "payment_mode", "CASH").upper() == "UPI")
            tot_chq = sum(s.amount for s in slips if getattr(s, "payment_mode", "CASH").upper() == "CHEQUE")

            H(f"""
            <div class="cc-grid-4" style="margin-bottom:12px;">
              <div class="cc-tile accent">
                <span class="l">{t("Total Route Collections", "कुल दैनिक वसूली")}</span>
                <span class="v" style="font-size:1.3rem;">{esc(inr(tot_all))}</span>
                <span class="s">{len(slips)} {t("slips recorded", "पर्चियां")}</span>
              </div>
              <div class="cc-tile pos">
                <span class="l">{t("Cash into Till", "गल्ले में नकद")}</span>
                <span class="v" style="font-size:1.3rem;color:#166534;">{esc(inr(tot_cash))}</span>
                <span class="s">{t("Added to drawer cash_in", "गल्ले में जमा")}</span>
              </div>
              <div class="cc-tile info">
                <span class="l">{t("UPI Direct Credits", "UPI ऑनलाइन")}</span>
                <span class="v" style="font-size:1.3rem;color:#17191D;">{esc(inr(tot_upi))}</span>
                <span class="s">{t("Direct to bank account", "सीधे बैंक खाते में")}</span>
              </div>
              <div class="cc-tile warn">
                <span class="l">{t("Cheques in Route Bag", "चेक")}</span>
                <span class="v" style="font-size:1.3rem;color:#B45309;">{esc(inr(tot_chq))}</span>
                <span class="s">{t("For branch deposit", "बैंक में जमा हेतु")}</span>
              </div>
            </div>
            """)

            mode_filter = st.radio(
                t("Filter Payment Mode", "भुगतान प्रकार फ़िल्टर"),
                ["All", "Cash", "UPI", "Cheque"],
                horizontal=True,
                key="_slips_tbl_filter"
            ) or "All"

            filtered_slips = slips
            if mode_filter != "All":
                filtered_slips = [s for s in slips if getattr(s, "payment_mode", "CASH").upper() == mode_filter.upper()]

            if filtered_slips:
                table_rows = []
                for s in reversed(filtered_slips):
                    m_tag = getattr(s, "payment_mode", "CASH").upper()
                    st_tag = "Banked" if getattr(s, "is_banked", False) else ("In Till" if m_tag == "CASH" else "In Route Bag")
                    inv_tag = getattr(s, "invoice_no", "") or "FIFO (Oldest Invoices)"
                    s_date_str = s.date.strftime("%Y-%m-%d") if hasattr(s.date, "strftime") else str(s.date)[:10]
                    table_rows.append({
                        "Date": s_date_str,
                        "Slip No": getattr(s, "slip_id", "") or getattr(s, "slip_no", ""),
                        "Retail Shop": getattr(s, "shop", ""),
                        "Salesman": getattr(s, "salesman", ""),
                        "Amount": inr(s.amount),
                        "Mode": m_tag,
                        "Invoice Allocation": inv_tag,
                        "Status": st_tag,
                    })
                st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
            else:
                H(f'<div class="cc-muted" style="padding:10px 0;">{t("No collection slips for this filter.", "इस फ़िल्टर के लिए कोई पर्ची नहीं मिली।")}</div>')

        st.write("")
        khata_data = vault.get_khata_summary(biz)
        accounts = khata_data["accounts"]
        k_demo = DEMO if any(getattr(acc, "is_demo", False) for acc in accounts) else ""
        totals = (f'{t("They owe you", "ग्राहकों पर बाकी")} <b class="cc-num">{esc(inr(khata_data["receivables"]))}</b> · {t("you owe", "आपको देना है")} '
                  f'<b class="cc-num">{esc(inr(khata_data["payables"]))}</b>') if accounts else ""
        H(f'<div style="display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;align-items:baseline;margin:16px 0 10px;">'
          f'<div class="cc-h2" role="heading" aria-level="2">{t("Pending khata & Chaser", "कच्चा खाता व तकादा")} {k_demo}</div>'
          f'<div class="cc-muted">{totals}</div></div>')

        def _render_khata_card(acc):
            rem = format_whatsapp_reminder(acc, BIZ_NAME, upi_handle="payment@bank")
            lim_tip = t("Under Section 18 Limitation Act, debts older than 3 years become legally time-barred without written acknowledgement.",
                        "3 साल से पुराना बकाया कानूनी रूप से अप्रवर्तनीय हो जाता है।")
            flag = f'<span class="cc-badge warn" data-tip="{lim_tip}">{svg(ICON_ALERT, 12, width=2.4)}{t("30+ Months", "30 महीने से अधिक")}</span>' if acc.is_limitation_alert else f'<span class="cc-badge neutral">{acc.months_open}m open</span>'
            color = f"color:{NEG};font-weight:700;" if acc.balance_due < 0 else "color:#17191D;font-weight:700;"
            sub_warning = f'<div style="font-size:0.74rem;color:#B45309;margin-top:2px;">{esc(rem["limitation_warning"])}</div>' if rem["limitation_warning"] else ""

            H(f"""
            <div class="cc-action-card">
              <div style="flex:1;min-width:180px;">
                <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                  <span style="font-size:0.92rem;font-weight:700;color:#17191D;">{esc(acc.party_name)}</span>
                  {flag}
                </div>
                <div style="font-size:0.78rem;color:#64748B;margin-top:2px;">
                  {t("Informal khata balance", "कच्चा खाता बकाया")}: <span style="{color}">{esc(inr(acc.balance_due))}</span>
                </div>
                {sub_warning}
              </div>
              <div>
                <a href="{rem['wa_link']}" target="_blank" class="cc-wa-btn" data-tip="{t('Opens a pre-filled WhatsApp reminder draft with balance and UPI payment link.', 'WhatsApp पर तकादा संदेश तैयार करता है।')}">
                  {t("Draft WhatsApp", "WhatsApp तकादा")}
                </a>
              </div>
            </div>
            """)

        if accounts:
            with st.container(key="krows"):
                top_accs = accounts[:3]
                rest_accs = accounts[3:]
                for acc in top_accs:
                    _render_khata_card(acc)
                if rest_accs:
                    with st.expander(t(f"Show {len(rest_accs)} More Khata Accounts", f"{len(rest_accs)} अन्य खाते देखें"), expanded=False):
                        for acc in rest_accs:
                            _render_khata_card(acc)
            H(f'<div class="cc-note" style="margin-top:8px;">{t("Drafts open in WhatsApp. Nothing is sent until you press send there.", "मैसेज WhatsApp में ड्राफ्ट होगा। आपके भेजने से पहले कुछ भी नहीं भेजा जाता।")}</div>')
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
              f'<div class="cc-muted" style="color:#475569">{esc(facts_res.message)}</div>'
              f'<div class="cc-note" style="margin-top:8px">{esc(facts_res.citation)}</div>'
              f'<div style="border-top:1px solid #EDEDE9;margin:14px 0 10px"></div>')
            with st.expander(t("Records checklist before depositing cash", "नकद जमा से पहले जरूरी रिकॉर्ड"), expanded=False):
                H(f'<ul class="cc-list sm">{items_html}</ul>'
                  f'<div class="cc-note" style="margin-top:12px">{esc(checklist["referral"])}</div>')

        # ── 1-Click CA Tally Export Pack in Cash Book ──
        with st.container(border=True):
            H(f'<div class="cc-h2" style="margin-bottom:8px;">{t("CA Tally Export Pack", "मुनीम / CA रीकॉन्सिलेशन एक्सपोर्ट")}</div>'
              f'<div class="cc-muted" style="font-size:0.82rem;margin-bottom:12px;">'
              f'{t("1-click export for visiting Chartered Accountants without manual ledger entry.", "1-क्लिक एक्सपोर्ट: टैली वाउचर व 6-शीट एक्सेल रीकॉन्सिलेशन।")}'
              f'</div>')
            st.download_button(
                label=t("Download Tally XML (Receipt Vouchers)", "टैली XML डाउनलोड करें"), icon=":material/download:",
                data=tally_xml_for(biz),
                file_name=f"tally_receipts_{biz}_{config.AS_OF:%Y%m%d}.xml",
                mime="application/xml",
                use_container_width=True,
                key="cb_dl_tally_xml",
            )
            export_vault = vault if (is_owner and is_v_unlocked and not showing_partial_view and share_cash_book) else None
            ca_workbook_button("cb", t("Download CA Excel Workbook", "CA एक्सेल रीकॉन्सिलेशन डाउनलोड करें"), export_vault)


# ── PAGE: FORECAST (FR-FC-1, FR-FC-2) ────────────────────────────────────────
def page_forecast():
    # Forecast start: defaults to the day the books are reconciled to, so it looks forward.
    fc_min = pack.bank.txn_date.min() + pd.DateOffset(months=6)
    fc_start = pd.Timestamp(st.session_state.get("fc_start", config.AS_OF.date()))
    fc_end = fc_start + pd.Timedelta(days=90)
    page_header(t("Forecast", "नकद अनुमान (Forecast)"),
                t(f"The next 90 days: {fc_start:%d %b %Y} to {fc_end:%d %b %Y}, using only what was known on the start date.",
                  f"अगले 90 दिन: {fc_start:%d %b %Y} से {fc_end:%d %b %Y} तक, केवल शुरुआती तारीख तक की जानकारी पर आधारित।"))
    if showing_partial_view:
        st.warning(render_partial_view_notice(), icon=":material/visibility_off:")

    c_date, c_w1, c_w2, c_w3 = st.columns([1.2, 1.3, 1.3, 1], vertical_alignment="bottom")
    c_date.date_input(t("Forecast from", "अनुमान की शुरुआत"), value=config.AS_OF.date(), min_value=fc_min.date(),
                      max_value=config.AS_OF.date(), format="DD/MM/YYYY", key="fc_start")
    wi_late = c_w1.toggle(t("Customers pay 15 days late", "ग्राहक 15 दिन देर से भुगतान करें"), key="fc_wi_late")
    wi_early = c_w2.toggle(t("Pay suppliers 15 days early", "सप्लायर को 15 दिन पहले भुगतान"), key="fc_wi_early")
    wi_sales = c_w3.toggle(t("Sales drop 20%", "बिक्री 20% घटे"), key="fc_wi_sales")
    what_if = wi_late or wi_early or wi_sales

    fc_base = forecast_for(biz, fc_start)
    fc_res = (forecast_for(biz, fc_start, 15 if wi_late else 0, -15 if wi_early else 0, 0.8 if wi_sales else 1.0)
              if what_if else fc_base)

    # Shortfall warning cards (D50, D40)
    if fc_res.warnings:
        for w in fc_res.warnings:
            H(f"""
            <div class="cc-card-modern" style="border-left:4px solid #D97706;background:#FFFBEB;">
              <div style="display:flex;gap:12px;align-items:flex-start;">
                {svg(ICON_ALERT, 22, "#D97706")}
                <div>
                  <div style="font-size:0.95rem;font-weight:700;color:#92400E;display:flex;align-items:center;gap:8px;">
                    {t("Early Shortfall Warning", "नकद कमी की पूर्व चेतावनी")}
                    <span class="cc-badge warn">{w.level.title()}</span>
                  </div>
                  <div style="font-size:0.86rem;color:#78350F;margin-top:4px;line-height:1.5;">{esc(w.message)}</div>
                </div>
              </div>
            </div>
            """)
    else:
        H(f"""
        <div class="cc-card-modern" style="border-left:4px solid #059669;background:#F0FDF4;">
          <div style="display:flex;gap:12px;align-items:flex-start;">
            {svg(ICON_CHECK_CIRCLE, 22, "#059669")}
            <div>
              <div style="font-size:0.95rem;font-weight:700;color:#166534;display:flex;align-items:center;gap:8px;">
                {t("No Shortfall Projected · Safe Operating Runway", "कोई नकद कमी नहीं आएगी · सुरक्षित ऑपरेटिंग रनवे")}
                <span class="cc-badge pos">{t("Safe", "सुरक्षित")}</span>
              </div>
              <div style="font-size:0.86rem;color:#14532D;margin-top:4px;line-height:1.5;">
                {t("Your bank headroom stays clear of the sanctioned cash-credit limit, salary obligations and operating expenses across all 90 days.",
                   "अगले 90 दिनों में वेतन दिवस और सामान्य खर्चों के बाद भी खाता स्वीकृत क्रेडिट लिमिट से पूर्णतः सुरक्षित रहेगा।")}
              </div>
            </div>
          </div>
        </div>
        """)

    if fc_res.daily_points:
        st.write("")
        with st.container(border=True):  # chart, legend and note on one white card
            a, b = st.columns([1, 2], vertical_alignment="center")
            with a:
                section(t("Projected bank balance", "अनुमानित बैंक बैलेंस"))
            limit_amt = copilot.credit_limit(biz)
            with b:
                legend = (f'<span><i style="width:14px;height:10px;border-radius:2px;background:rgba(23,25,29,0.08)"></i>{t("Likely range (P10–P90)", "संभावित दायरा (P10–P90)")}</span>'
                          f'<span><i style="width:16px;height:2.5px;background:{INK}"></i>{t("Most likely (P50)", "सबसे संभावित स्तर (P50)")}</span>')
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
                                                          tickColor="#EDEDE9", labelColor=SUBTLE, labelPadding=6))
            y_axis = alt.Axis(labelExpr=lakh_expr, gridColor="#EDEDE9", domain=False, ticks=False, labelColor=SUBTLE,
                              labelPadding=8, tickCount=5)
            # Floating Edition chart: ink line on a faint ink band, red marks only where attention is needed.
            band = alt.Chart(df_daily).mark_area(opacity=0.08, color=INK).encode(
                x=x, y=alt.Y("p10:Q", title=None, axis=y_axis), y2="p90:Q",
                tooltip=[alt.Tooltip("Date:T", title="Date", format="%d %b %Y"),
                         alt.Tooltip("p10_txt:N", title="Worst case (P10)"),
                         alt.Tooltip("p50_txt:N", title="Most likely (P50)"),
                         alt.Tooltip("p90_txt:N", title="Optimistic (P90)")])
            line = alt.Chart(df_daily).mark_line(strokeWidth=2.5, color=INK).encode(x="Date:T", y="p50:Q")
            low = df_daily.loc[[df_daily.p50.idxmin()]].assign(label=lambda d: "Lowest " + d["p50_txt"])
            low_pt = alt.Chart(low).mark_point(filled=True, fill="white", stroke=ACCENT, strokeWidth=2, size=70).encode(
                x="Date:T", y="p50:Q")
            low_txt = alt.Chart(low).mark_text(dy=22, fontSize=12, fontWeight=700, color=ACCENT).encode(
                x="Date:T", y="p50:Q", text="label:N")
            layers = [band, line, low_pt, low_txt]
            if limit_amt:
                floor_df = pd.DataFrame([{"Floor": -limit_amt}])
                layers.append(alt.Chart(floor_df).mark_rule(strokeDash=[6, 5], color=NEG, strokeWidth=1.5).encode(y="Floor:Q"))
            chart = (alt.layer(*layers).properties(height=340)
                     .configure(font=FONT).configure_view(strokeWidth=0)
                     .configure_axis(labelFontSize=11, labelFontWeight=600))
            st.altair_chart(chart, use_container_width=True, theme=None)
            H(f'<div class="cc-note">{t("Simulated from your own payment history up to the start date.", "शुरुआती तारीख तक के आपके भुगतान इतिहास से तैयार।")}</div>')

        # Plain-language reading of the chart (15 Nov demo feedback)
        low_pt = min(fc_res.daily_points, key=lambda p: p.balance_p50)
        worst = min(p.balance_p10 for p in fc_res.daily_points)
        lines = [t(f"Your lowest point is <b>{esc(inr(low_pt.balance_p50))}</b> on <b>{low_pt.date:%d %b %Y}</b>.",
                   f"आपका सबसे निचला स्तर <b>{low_pt.date:%d %b %Y}</b> को <b>{esc(inr(low_pt.balance_p50))}</b> रहेगा।")]
        if limit_amt:
            room = low_pt.balance_p50 + limit_amt
            lines.append(t(f"You do not need to draw on your {esc(inr(limit_amt))} cash-credit limit.",
                           f"आपको अपनी {esc(inr(limit_amt))} की कैश-क्रेडिट सीमा का उपयोग नहीं करना पड़ेगा।") if low_pt.balance_p50 >= 0 else
                         t(f"That leaves {esc(inr(room))} of your {esc(inr(limit_amt))} cash-credit limit unused.",
                           f"उस दिन आपकी {esc(inr(limit_amt))} की कैश-क्रेडिट सीमा में से {esc(inr(room))} बची रहेगी।") if room >= 0 else
                         t(f"That is {esc(inr(-room))} beyond your {esc(inr(limit_amt))} cash-credit limit.",
                           f"यह आपकी {esc(inr(limit_amt))} की कैश-क्रेडिट सीमा से {esc(inr(-room))} ज़्यादा है।"))
        elif low_pt.balance_p50 < 0:
            lines.append(t("Your bank balance goes below zero on that day.", "उस दिन आपका बैंक बैलेंस शून्य से नीचे चला जाएगा।"))
        # No "1 in 10" wording: on the holdout only ~22% of actuals landed inside this band.
        lines.append(t(f"If customers pay slower than usual, the simulation's low case is {esc(inr(worst))}. Treat it as a rough guide.",
                       f"अगर ग्राहक सामान्य से देर से भुगतान करें, तो अनुमान का निचला स्तर {esc(inr(worst))} है। इसे मोटा अंदाज़ा मानें।"))
        if what_if:
            base_low = min(p.balance_p50 for p in fc_base.daily_points)
            lines.append(t(f"With the what-ifs switched on, the lowest point moves from {esc(inr(base_low))} to "
                           f"{esc(inr(low_pt.balance_p50))}.",
                           f"ऊपर चुनी गई स्थितियों में सबसे निचला स्तर {esc(inr(base_low))} से बदलकर {esc(inr(low_pt.balance_p50))} हो जाता है।"))
        top_cust = by_customer(open_items(pack, biz, fc_start)).head(1)
        if not top_cust.empty:
            tc = top_cust.iloc[0]
            lines.append(t(f"The one collection that helps most: <b>{esc(inr(tc.outstanding))}</b> from "
                           f"<b>{esc(tc.customer_name)}</b> (oldest invoice {int(tc.oldest_days)} days).",
                           f"सबसे ज़्यादा मदद करने वाली वसूली: <b>{esc(tc.customer_name)}</b> से <b>{esc(inr(tc.outstanding))}</b> "
                           f"(सबसे पुराना इनवॉइस {int(tc.oldest_days)} दिन)।"))
        H(f'<div class="cc-card-modern" data-testid="fc-plain"><div style="font-size:1.05rem;font-weight:700;color:#0F172A;margin-bottom:8px;">'
          f'{t("What this forecast means for you", "इस अनुमान का आपके लिए क्या मतलब है")}</div>'
          + "".join(f'<div style="font-size:0.92rem;color:#334155;line-height:1.6;">{ln}</div>' for ln in lines) + '</div>')

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
    H(f"""
    <div class="cc-card-modern">
      <div style="font-size:1.05rem;font-weight:700;color:#17191D;margin-bottom:12px;">{t("Month-by-Month Operating Outlook", "माह-दर-माह नकद प्रवाह विश्लेषण")}</div>
      <div class="cc-scroll">
        <table class="cc-table" style="min-width:720px">
          <thead>
            <tr>
              <th style="text-align:left;">{t("Month", "माह")}</th>
              <th data-tip="{t('Expected customer receipts and receivables with P10–P90 sensitivity bounds.', 'अपेक्षित आवक')}">{t("Expected Inflows", "अपेक्षित आवक")} <span class="cc-info-dot">i</span></th>
              <th data-tip="{t('Committed payroll, vendor dues, and fixed overhead obligations.', 'देय खर्च')}">{t("Committed Outflows", "देय खर्च")} <span class="cc-info-dot">i</span></th>
              <th data-tip="{t('Monthly operating cash surplus or deficit (Inflows minus Outflows).', 'शुद्ध प्रवाह')}">{t("Net Cash Flow", "शुद्ध प्रवाह")} <span class="cc-info-dot">i</span></th>
              <th data-tip="{t('The lowest projected cash balance point reached during the calendar month.', 'न्यूनतम स्तर')}">{t("Lowest Day Balance", "न्यूनतम स्तर")} <span class="cc-info-dot">i</span></th>
              <th data-tip="{t('Projected closing bank liquidity at the end of the calendar month.', 'अंतिम शेष')}">{t("Closing Balance", "अंतिम शेष")} <span class="cc-info-dot">i</span></th>
            </tr>
          </thead>
          <tbody>{"".join(rows)}</tbody>
        </table>
      </div>
      <div class="cc-note" style="margin-top:10px;">{t("P50 median estimates with P10–P90 sensitivity bounds.", "P50 सबसे संभावित स्तर और P10–P90 सीमाएं।")}</div>
    </div>
    """)

    st.write("")
    holdout_res = holdout_scores()
    with st.expander(f"How accurate is this forecast? {holdout_res.mape:.2%} average error on the holdout", expanded=False):
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
        st.warning(render_partial_view_notice(), icon=":material/visibility_off:")

    d60_tip = t("Strict Decision 60: Auto-accepts only occur when exactly one invoice unambiguously matches one deposit slip. 0 unvetted reconciliations.",
                "Decision 60: बिना सत्यापन के कोई स्वतः मिलान नहीं।")
    H(f"""
    <div style="display:flex;justify-content:space-between;align-items:center;background:#F8FAFC;border:1px solid #E5E5E1;border-radius:10px;padding:12px 18px;margin-bottom:14px;gap:8px;flex-wrap:wrap;" data-tip="{esc(d60_tip)}">
      <div style="display:flex;align-items:center;gap:10px;">
        <span class="cc-badge info" style="font-size:0.78rem;">Strict Decision 60</span>
        <span style="font-size:0.86rem;font-weight:700;color:#17191D;">0 Unvetted Auto-Accepts · Strict Bank & Ledger Rule Engine <span class="cc-info-dot" style="background:#E5E5E1;color:#17191D;">i</span></span>
      </div>
      <div style="font-size:0.8rem;color:#17191D;font-weight:600;">{counts['auto']:,} automatic matches · {counts[SUGGEST] + counts[ASK]:,} in decision queue</div>
    </div>
    """)

    # ── 1-Click CA Tally Export Pack ──
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        st.download_button(
            label=t("Download Tally XML (Decision 60 Vouchers)", "टैली XML डाउनलोड करें"), icon=":material/download:",
            data=tally_xml_for(biz),
            file_name=f"tally_receipts_{biz}_{config.AS_OF:%Y%m%d}.xml",
            mime="application/xml",
            use_container_width=True,
            key="rev_dl_tally_xml",
        )
    with col_exp2:
        export_vault = vault if (is_owner and is_v_unlocked and not showing_partial_view and share_cash_book) else None
        ca_workbook_button("rev", t("Download CA Reconciliation Workbook (Excel)", "CA रीकॉन्सिलेशन एक्सेल डाउनलोड करें"), export_vault)
    st.write("")

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
        gb.configure_grid_options(autoSizeStrategy=None, rowHeight=48, headerHeight=44)
        gb.configure_selection("single")
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
        grid = AgGrid(
            view, gridOptions=gb.build(), height=560, fit_columns_on_grid_load=False, theme="alpine",
            key=f"queue_grid_{biz}_{choice}",
            custom_css={
                ".ag-root-wrapper": {"border": "1px solid #EDEDE9 !important", "border-radius": "20px !important",
                                     "font-family": "Inter, system-ui, -apple-system, 'Segoe UI', sans-serif !important",
                                     "box-shadow": "0 1px 2px rgba(0,0,0,0.03), 0 4px 12px rgba(0,0,0,0.05)"},
                ".ag-header": {"background-color": "#FFFFFF !important", "border-bottom": "1px solid #EDEDE9 !important"},
                ".ag-header-cell-text": {"font-weight": "700 !important", "color": "#64748B !important", "font-size": "10px !important",
                                         "letter-spacing": "0.18em !important", "text-transform": "uppercase !important"},
                ".ag-row": {"border-bottom": "1px solid #EDEDE9 !important", "font-size": "13px !important", "color": "#17191D !important"},
                ".ag-row-selected": {"background-color": "#FFF1F1 !important"},
                ".ag-row-selected .ag-cell:first-child": {"box-shadow": "inset 3px 0 0 #E76559"},
                ".ag-row-hover": {"background-color": "#F8FAFC !important"},
                ".ag-cell-focus": {"border": "1px solid #E76559 !important", "outline": "none !important"},
                ".ag-paging-panel": {"border-top": "1px solid #EDEDE9 !important", "color": "#64748B !important"},
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
                doc_rows = "".join(f'<div><dt class="cc-mono" style="color:#17191D">{esc(d)}</dt><dd>{esc(inr(a))}</dd></div>'
                                   for d, a in m.docs)
                H(f'<dl class="cc-dl">{doc_rows}</dl>')
            else:
                H('<div class="cc-muted">No single document fits this receipt yet.</div>')
            st.write("")
            verified_keys = st.session_state.setdefault("_verified_matches", set())
            is_v = txn_id in verified_keys
            col_v1, col_v2 = st.columns([1.4, 1])
            with col_v1:
                v_lbl = t("Verified by Owner", "मालिक द्वारा सत्यापित") if is_v else t("Mark as Verified", "सत्यापित चिह्नित करें")
                if st.button(v_lbl, key=f"verify_{txn_id}", type="primary" if not is_v else "secondary", use_container_width=True,
                             icon=":material/check:" if is_v else None):
                    if is_v:
                        verified_keys.remove(txn_id)
                    else:
                        verified_keys.add(txn_id)
                    st.rerun()
            with col_v2:
                reconcile_note = f"Txn {txn_id} | {r['amount']} | {b.narration} | Matched: {m.rule}"
                st.download_button(t("Export Note", "नोट डाउनलोड"), data=reconcile_note,
                                   file_name=f"match_{txn_id}.txt", mime="text/plain", use_container_width=True)
            H(f'<div class="cc-note" style="margin-top:6px">{t("Read-only mode: Staged locally for your CA. Zero ledger mutation.", "रीड-ओनली मोड: एकाउंटेंट के लिए लोकल सेव हुआ। कोई बदलाव नहीं किया जाता।")}</div>')


# ── PAGE: RECEIVABLES ────────────────────────────────────────────────────────
def page_receivables():
    page_header(t("Receivables", "बाजार उधारी (Receivables)"),
                t(f"Who owes you on formal invoices, as of {config.AS_OF:%d %b %Y}.",
                  f"{config.AS_OF:%d %b %Y} तक इनवॉइस के अनुसार किस पर कितना बकाया है।"))
    if showing_partial_view:
        st.warning(render_partial_view_notice(), icon=":material/visibility_off:")

    items = open_items(pack, biz)
    cust_df = by_customer(items)

    # Modern 3-Quadrant Metric Grid for Desktop
    H(f"""
    <div style="display:grid;grid-template-columns:repeat(3, 1fr);gap:12px;margin-bottom:16px;">
      <div class="cc-tile accent" data-tip="{t('Total balance due across all active billing ledgers and verified shop invoices.', 'कुल औपचारिक बिल बकाया')}">
        <span class="l">{t("Total Formal Receivables", "कुल औपचारिक बिल बकाया")}<span class="cc-info-dot">i</span></span>
        <span class="v" style="font-size:1.45rem;">{esc(inr(items.outstanding.sum()))}</span>
        <span class="s">{t("From verified invoices", "प्रमाणित इनवॉइस से")}</span>
      </div>
      <div class="cc-tile" data-tip="{t('Count of all unpaid formal sales invoices currently issued to retailers.', 'कुल खुले इनवॉइस')}">
        <span class="l">{t("Open Invoices", "कुल खुले इनवॉइस")}<span class="cc-info-dot">i</span></span>
        <span class="v" style="font-size:1.45rem;">{len(items):,}</span>
        <span class="s">{len(cust_df)} {t("active customers", "सक्रिय ग्राहक")}</span>
      </div>
      <div class="cc-tile warn" data-tip="{t('Invoices older than 60 days. Exceeds standard wholesale FMCG credit cycles.', '60 दिन से पुराने इनवॉइस')}">
        <span class="l">{t("Overdue > 60 Days", "60 दिन से अधिक पुराने")}<span class="cc-info-dot">i</span></span>
        <span class="v" style="font-size:1.45rem;color:#B45309;">{len(overdue(items)):,}</span>
        <span class="s">{t("Needs urgent follow-up", "तत्काल तकादा आवश्यक")}</span>
      </div>
    </div>
    """)

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
        if st.button(t("Daily Recovery Sheet", "दैनिक वसूली शीट"), icon=":material/print:", key="btn_open_print_sheet", use_container_width=True):
            daily_print_dialog()
    filtered_cust = filters[choice]
    with head:
        H(f'<div class="cc-h2" role="heading" aria-level="2">{t("Who to call this week", "इस हफ्ते किन ग्राहकों से वसूली करनी है")}</div>'
          f'<div class="cc-muted">{t("Showing", "कुल")} {len(filtered_cust)} {t("customers owing", "ग्राहकों पर")} {esc(inr(filtered_cust.outstanding.sum()))} {t("outstanding. Largest first.", "बकाया। सबसे बड़े पहले।")}</div>')

    if filtered_cust.empty:
        if choice == t("Over 30 months", "30 महीने से अधिक (Limitation Act)"):
            H(f'<div style="display:flex;flex-direction:column;align-items:center;gap:6px;padding:48px 16px;text-align:center">'
              f'{svg(ICON_CHECK_CIRCLE, 28, SUBTLE, 1.6)}<div style="font-weight:500">{t("No customers in this list", "इस सूची में कोई ग्राहक नहीं है")}</div>'
              f'<div class="cc-muted" style="max-width:420px">{t("Balances older than 30 months can become hard to recover under the Limitation Act. They will show here first.", "30 महीने से अधिक पुराने बकाये की वसूली में कानूनी अड़चन आ सकती है।")}</div></div>')
        else:
            st.info(t(f"No customers found matching the filter: '{choice}'.", f"फ़िल्टर '{choice}' से मेल खाने वाला कोई ग्राहक नहीं मिला।"))
            def _reset_chase_filter():
                st.session_state["chase_filter"] = t("All customers", "सभी ग्राहक")
                st.session_state["_chase_filter"] = "All"

            st.button(
                t("Clear filter / Show all customers", "फ़िल्टर हटाएं / सभी ग्राहक देखें"),
                key="btn_clear_recv_filter",
                on_click=_reset_chase_filter,
            )

    else:
        collections = vault.collection_records.get(biz, [])
        with st.container(key="crows"):
            for i, (_, c_row) in enumerate(filtered_cust.head(15).iterrows()):
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

                lim_badge = ""
                if oldest >= 900:
                    l_tip = t("Section 18 Limitation Act: Trade debts older than 3 years become legally time-barred without written acknowledgement or payment.",
                              "3 साल से पुराना बकाया")
                    lim_badge = f'<span class="cc-badge warn" data-tip="{l_tip}">{svg(ICON_ALERT, 12, width=2.4)}{t("30+ Months (Sec 18 Limitation Act)", "30+ महीने (Sec 18)")}</span>'
                elif oldest >= 45:
                    d_tip = t("Days elapsed since the oldest unpaid invoice was issued to this retailer.", "पुराने इनवॉइस की अवधि")
                    lim_badge = f'<span class="cc-badge neutral" data-tip="{d_tip}">{oldest}d overdue</span>'

                prot_banner = ""
                if salesman_note:
                    s_tip = t("Salesman cash protection: Pausing reminders avoids embarrassing duplicate collection calls.", "डुप्लीकेट कॉल से बचाव")
                    prot_banner = (f'<div style="font-size:0.78rem;color:#166534;background:#DCFCE7;border:1px solid #BBF7D0;padding:4px 8px;border-radius:6px;margin-top:4px;display:inline-flex;align-items:center;gap:6px;" data-tip="{s_tip}">'
                                   f'{svg(ICON_SHIELD, 14, "#166534")}{esc(salesman_note)} <span class="cc-info-dot" style="background:#BBF7D0;color:#166534;">i</span></div>')

                if oldest >= 900:
                    if is_hi():
                        wa_text = (
                            f"नमस्ते {c_name} जी, आशा है आप सकुशल हैं। {BIZ_NAME} के रिकॉर्ड अनुसार, "
                            f"हमारी पिछली आपूर्ति का {inr(amt)} बकाया है। क्या आप कृपया पुष्टि कर सकते हैं कि यह "
                            f"आपकी बहियों से मेल खाता है, या बताएं कि हम कब तक छोटे भुगतान की उम्मीद कर सकते हैं? धन्यवाद!"
                        )
                    else:
                        wa_text = (
                            f"Namaste {c_name} ji, hope you are doing well. As per our records with {BIZ_NAME}, "
                            f"the pending balance is {inr(amt)} from our earlier supplies. Could you please confirm if this matches "
                            f"your books, or let us know when we can expect a small part-settlement? Thank you!"
                        )
                else:
                    if is_hi():
                        wa_text = (f"नमस्ते {c_name} जी, {BIZ_NAME} की ओर से नमस्कार। आपके खाते का कुल बकाया {inr(amt)} है। "
                                   f"कृपया चेक कर भुगतान करें। धन्यवाद। UPI: payment@bank")
                    else:
                        wa_text = (f"Namaste {c_name}, {BIZ_NAME} se namaskar. Aapka pichla bill {inr(amt)} ka baaki hai. "
                                   f"Kripya check kar lijiye. UPI: payment@bank")

                wa_url = f"https://wa.me/?text={urllib.parse.quote(wa_text)}"

                H(f"""
                <div class="cc-action-card">
                  <div style="flex:1;min-width:220px;">
                    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                      <span style="font-size:0.94rem;font-weight:700;color:#17191D;">{esc(c_name)}</span>
                      {lim_badge}
                    </div>
                    <div style="font-size:0.78rem;color:#64748B;margin-top:2px;">
                      {inv_count} {t("open invoices", "खुले इनवॉइस")} · {t("Oldest", "सबसे पुराना")}: {oldest}d
                    </div>
                    {prot_banner}
                  </div>
                  <div style="text-align:right;margin:0 16px;">
                    <div style="font-size:1.15rem;font-weight:800;color:#17191D;font-variant-numeric:tabular-nums;">{esc(inr(amt))}</div>
                    <div style="font-size:0.74rem;color:#64748B;">{t("Outstanding", "बकाया")}</div>
                  </div>
                  <div>
                    <a href="{wa_url}" target="_blank" class="cc-wa-btn" data-tip="{t('Drafts an invoice reminder in WhatsApp Web for immediate review and sending.', 'WhatsApp पर तकादा संदेश तैयार करता है।')}">
                      {t("Draft WhatsApp", "WhatsApp तकादा")}
                    </a>
                  </div>
                </div>
                """)

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
            st.warning(render_partial_view_notice(), icon=":material/visibility_off:")

        if "ask_prefill" in st.session_state:
            st.session_state["ask_typed"] = st.session_state.pop("ask_prefill")
        mid, _ = st.columns([3, 1.2])
        with mid:
            if not PUBLIC:
                with st.container(key="ask_box"):
                    H(f'<div class="cc-ask-head">{svg(ICON_CHAT, 18, INK)}<span>{t("Ask in your own words", "अपने शब्दों में पूछें")}</span></div>'
                      f'<div class="cc-note">{t("Type a question about your cash, dues or forecast and press Ask.", "अपने कैश, बकाया या अनुमान के बारे में सवाल लिखें और पूछें दबाएं।")}</div>')
                    with st.form("ask_form", border=False):
                        c1, c2 = st.columns([5, 1.1], vertical_alignment="bottom")
                        c1.text_input(t("Your question", "आपका सवाल"), key="ask_typed", label_visibility="collapsed",
                                      placeholder=t("For example: who owes me the most?", "उदाहरण: मुझ पर सबसे ज्यादा बकाया किसका है?"))
                        asked = c2.form_submit_button(t("Ask", "पूछें"), type="primary", use_container_width=True,
                                                      icon=":material/arrow_forward:")
                    if asked:  # also true when the question is sent with the Enter key
                        _submit_typed()

                with st.expander(t("Speak or upload voice question (माइक या ऑडियो फ़ाइल)", "माइक से बोलें या ऑडियो फ़ाइल अपलोड करें"), icon=":material/mic:"):
                    rec_audio = st.audio_input(t("Record voice question", "आवाज़ रिकॉर्ड करें"), key="mic_audio_input")
                    upload_audio = st.file_uploader(t("Or upload audio file", "या ऑडियो फ़ाइल अपलोड करें"), type=["wav", "mp3", "m4a", "ogg", "flac", "webm"], key="upload_audio_input")
                    audio_target = None
                    raw_bytes = None
                    mime_type = "audio/wav"
                    if rec_audio:
                        audio_target = rec_audio
                        raw_bytes = rec_audio.read() if hasattr(rec_audio, "read") else rec_audio.getvalue()
                        mime_type = getattr(rec_audio, "type", None) or "audio/wav"
                    elif upload_audio:
                        audio_target = upload_audio
                        raw_bytes = upload_audio.getvalue() if hasattr(upload_audio, "getvalue") else upload_audio.read()
                        mime_type = getattr(upload_audio, "type", None) or "audio/wav"

                    if audio_target and raw_bytes:
                        audio_sig = hash(raw_bytes)
                        if st.session_state.get("_last_audio_sig") != audio_sig:
                            st.session_state["_last_audio_sig"] = audio_sig
                            with st.spinner(t("Transcribing with Gemini Voice…", "आवाज़ समझी जा रही है…")):
                                transcribed = transcribe_audio(raw_bytes, mime_type=mime_type)
                                if transcribed:
                                    st.session_state["ask_q"] = transcribed
                                    st.session_state["ask_typed"] = transcribed
                                    st.rerun()

            chips = ASK_CHIPS_HI if is_hi() else ASK_CHIPS
            st.pills(t("Try one of these", "इनमें से कोई सवाल चुनें") if not PUBLIC else t("Choose a question", "सवाल चुनें"),
                     chips, key="ask_chip", on_change=_pick_chip)
            if PUBLIC:
                H(f'<div class="cc-callout neutral" style="margin-top:4px">{svg(ICON_LOCK, 16)}<div class="d">'
                  f'{t("Typing your own question is switched off in this preview until our safety checks pass.", "सुरक्षा जांच पूरी होने तक टाइपिंग बंद है।")}</div></div>')

            selected_q = st.session_state.get("ask_q")
            if selected_q:
                q_for_copilot = CHIP_HI_TO_EN.get(selected_q, selected_q)
                a = copilot.ask(biz, q_for_copilot, galla_cash=answer_galla())
                display_q = CHIP_EN_TO_HI.get(selected_q, selected_q) if is_hi() else selected_q
                if a.intent == "FACT":
                    label = f'<span class="cc-badge pos" style="display:inline-flex;gap:5px;align-items:center">' \
                            f'{svg(ICON_CHECK, 12, width=2.6)}{t("From your books", "आपके बही-खाते से")}</span>'
                elif a.intent == "UNSUPPORTED":
                    label = tag(t("Not available yet", "अभी उपलब्ध नहीं"), "neutral")
                elif a.intent == "NEEDS_CHIPS":
                    label = tag(t("Pick a question", "सवाल चुनें"), "neutral")
                else:
                    label = tag(t("Outside what I do", "कार्यक्षेत्र से बाहर"), "warn")

                H(f"""
                <div class="cc-card-modern" style="margin-top:16px;">
                  <div style="display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;align-items:center;">
                    <div style="font-size:1.1rem;font-weight:700;color:#17191D;">{esc(display_q)}</div>
                    {label}
                  </div>
                  <div style="font-size:1.02rem;line-height:1.65;margin-top:12px;color:#1E293B;">{answer_html(a.text)}</div>
                </div>
                """)

                # Hindi summary card when Hindi is selected or asked
                if is_hi() or "hindi" in selected_q.lower():
                    hi_line = hindi_summary(a)
                    hi_summary = (f'<span style="color:#E76559;font-weight:600">सरल समझ:</span> {esc(hi_line)}' if hi_line else "")
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
        st.warning(render_partial_view_notice(), icon=":material/visibility_off:")

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
    H(f"""
    <div class="cc-card-modern">
      <div style="font-size:0.95rem;font-weight:700;color:#17191D;margin-bottom:4px;">Strict Decision 60 Auto-Match Accuracy</div>
      <div class="cc-muted" style="margin-bottom:12px;">{esc(precision_txt)}</div>
      {_html_table(summary(df), highlight=biz, min_width=900)}
    </div>
    """)

    st.write("")
    section("Sorting lines into categories")
    H('<div class="cc-muted" style="margin-bottom:6px">Payee memory plus the guide\'s rules, scored by line and by rupee value.</div>')
    cats = score_categories(pack, copilot.cat)
    left, _ = st.columns([3, 2])
    with left:
        H(_html_table(cats))

    st.write("")
    section("Holdout forecast backtest accuracy")
    holdout_res = holdout_scores()
    mape_label = f"{holdout_res.mape:.2%}"
    if holdout_res.mape > 0.182:
        mape_note = "worse than the simple 3-month average; kill metric (D31)"
    else:
        mape_note = "target ≤ 10%"
    H(f"""
    <div class="cc-card-modern">
      <div style="font-size:0.95rem;font-weight:700;color:#17191D;margin-bottom:8px;">Holdout Forecast Benchmarks (Jul–Sep 2026 Out-of-Sample)</div>
      <div class="cc-tiles">
        {tile("Model error (MAPE) on the frozen holdout", mape_label, f"{mape_note} · naive 3-month baseline {holdout_res.naive_mape:.2%}")}
        {tile("Agency inflows error", f"{holdout_res.agency_inflow_mape:.2%}", f"naive baseline {holdout_res.naive_agency_inflow_mape:.2%}")}
        {tile("Paired bootstrap improvement (naive − model)", f"{holdout_res.bootstrap_diff_mean:+.2%}", f"95% CI {holdout_res.bootstrap_diff_ci[0]:+.2%} to {holdout_res.bootstrap_diff_ci[1]:+.2%}")}
        {tile("Holdout P10–P90 coverage", f"{holdout_res.coverage_p10_p90:.1%}", "of actuals fell inside the range")}
        {tile("Holdout likely warnings", f"{holdout_res.false_alarms.get(biz, 0)}", "for this business")}
      </div>
      <div class="cc-note" style="margin-top:8px">Calibrated without lookahead bias across 10,000 paired bootstrap resamples.</div>
    </div>
    """)


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
                  '<div class="cc-sub" style="font-size:0.95rem;color:#475569;margin:8px 0 20px">'
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
                    st.session_state["onboarded"] = True
                    st.switch_page(PAGES["overview"])

            elif step == 2:
                rep = data_report()
                n_customers = len(by_customer(open_items(pack, biz)))
                H('<div class="cc-title" role="heading" aria-level="1" style="font-size:1.6rem">'
                  'Reading and checking your books</div>'
                  '<div class="cc-sub" style="font-size:0.95rem;color:#475569;margin:8px 0 20px">'
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

                with st.expander(t("Upload Live Statement or Tally Prime XML", "लाइव बैंक स्टेटमेंट या टैली XML अपलोड करें"), icon=":material/upload_file:"):
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
                  '<div class="cc-sub" style="font-size:0.95rem;color:#475569;margin:8px 0 20px">'
                  'Filled in from your recurring transactions. Confirm them, or adjust them with your accountant.</div>')
                rows = []
                if limit:
                    rows.append(("Sanctioned cash-credit limit", "Found on your cash-credit account", inr(limit)))
                rows.append(("Payroll day", f"A salary run of about {lakh(salary)} repeats each month", "1st of the month"))
                rows.append(("Suggested cash floor", "A five-day operating buffer", "₹2,00,000"))
                H('<dl class="cc-dl">' + "".join(
                    f'<div style="align-items:baseline"><dt style="display:flex;flex-direction:column">'
                    f'<span style="color:#17191D;font-weight:500">{esc(t)}</span><span class="cc-muted">{esc(d)}</span></dt>'
                    f'<dd style="font-size:1.1rem;font-weight:600">{esc(v)}</dd></div>' for t, d, v in rows) + '</dl>')
                H('<div class="cc-callout neutral" style="margin-top:16px;font-size:0.85rem">Accountant view: formal bank '
                  'records are shared; drawer cash and khata notes stay private to the owner unless shared.</div>')
                H('<div class="cc-rule" style="margin:22px 0 14px"></div>')
                c1, c2, _ = st.columns([1.4, 1, 2.6])
                if c1.button("Open my overview", type="primary", key="onb_step3_finish", use_container_width=True):
                    st.session_state["onboarding_step"] = 1
                    st.session_state["onboarded"] = True
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

# Refined Sidebar layout: the pages live in the sidebar. On phones, where Streamlit folds the sidebar away,
# the top bar repeats the primary pages.
TOP_NAV = ("overview", "cash", "forecast", "review", "recv", "ask")
MORE_NAV = ("quality", "setup")
NAV_ICONS = {"overview": ":material/dashboard:", "cash": ":material/menu_book:", "forecast": ":material/monitoring:",
             "review": ":material/fact_check:", "recv": ":material/inbox:", "ask": ":material/auto_awesome:",
             "quality": ":material/verified_user:", "setup": ":material/flag:"}


def active_position(keys) -> int | None:
    """1-based position of the open page within `keys`, or None when it is not one of them."""
    return next((i for i, k in enumerate(keys, start=1) if PAGES[k].title == current.title), None)


def nav_label(k: str) -> str:
    label = PAGE_TITLES_HI.get(k, PAGES[k].title) if is_hi() else PAGES[k].title
    if k == "review":
        rev_c = sum(v for tier, v in queue_counts(biz).items() if tier in (SUGGEST, ASK))
        label = f"{t('Review', 'समीक्षा')} · {rev_c:,}"
    return label


# ── SIDEBAR (Refined Sidebar draft): BRAND · WORKSPACE · PAGES · SECURITY · ACCOUNT ──
with st.sidebar:
    H(f'<div class="cc-sbrand">{LOGO}<div><div class="n">Cash Copilot</div>'
      f'<div class="s">{t("Finance workspace", "वित्त कार्यक्षेत्र")}</div></div></div>'
      f'<div class="cc-slabel">{t("Workspace", "कार्यक्षेत्र")}</div>')
    _biz_options = list(config.BUSINESSES)
    with st.container(key="bizpick"):
        biz = st.selectbox("Business", _biz_options, format_func=lambda b: config.BUSINESSES[b], key="biz",
                           index=_biz_options.index(st.session_state["biz_choice"]), label_visibility="collapsed",
                           on_change=lambda: st.session_state.update(biz_choice=st.session_state["biz"]))
        H(f'<div class="cc-bizsub">{esc(biz_type_label())}</div>')
    with st.container(key="snav"):
        if not st.session_state.get("onboarded", False):
            st.page_link(PAGES["setup"], label=t("Start here", "यहाँ से शुरू करें"), icon=NAV_ICONS["setup"])
        for k in TOP_NAV:
            st.page_link(PAGES[k], label=nav_label(k), icon=NAV_ICONS[k])
    with st.container(key="ssec"):
        H(f'<div class="cc-shead"><span class="cc-slabel">{t("Security", "सुरक्षा")}</span>'
          f'<span class="cc-shield">{svg(ICON_SHIELD_CHECK, 15, width=2.2)}</span></div>')

        def _on_role_change():
            new_role = st.session_state.get("role", "Owner")
            st.session_state["role_choice"] = new_role
            if new_role != "Owner":
                if vault is not None and hasattr(vault, "lock"):
                    vault.lock()
                st.session_state["vault_unlocked"] = False

        # Only the owner may keep the vault open; settle that before the card shows the state.
        if st.session_state.get("role", st.session_state["role_choice"]) != "Owner":
            if vault is not None and hasattr(vault, "lock"):
                vault.lock()
            st.session_state["vault_unlocked"] = False
        is_v_unlocked = st.session_state.get("vault_unlocked", False)
        if is_v_unlocked:
            H(f'<div class="cc-vcard on"><div class="t"><span class="cc-dot"></span>{t("Vault unlocked", "वॉल्ट खुला")}</div>'
              f'<div class="d">{t("The owner’s cash book is open on this device. Lock it when you step away.", "मालिक की रोकड़ बही इस डिवाइस पर खुली है। हटने से पहले लॉक करें।")}</div></div>')
        else:
            H(f'<div class="cc-vcard off"><div class="t"><span class="cc-dot"></span>{t("Vault locked", "वॉल्ट लॉक")}</div>'
              f'<div class="d">{t("Formal books only. The owner’s cash book is protected on this device.", "केवल औपचारिक हिसाब। मालिक की रोकड़ बही इस डिवाइस पर सुरक्षित है।")}</div></div>')

        # "Manage access" keeps the card quiet: who is viewing, the PIN and the lock open on demand.
        with st.container(key="vaultmgr"):
            # An expander, not a popover: a popover in the sidebar drops clicks on the buttons inside it.
            with st.expander(t("Manage access", "पहुंच प्रबंधित करें"), expanded=False):
                H(f'<div class="cc-pop-title">{t("Access", "पहुंच")}</div>'
                  f'<div class="cc-pop-sub">{t("Who is viewing, and the owner PIN for the cash book.", "कौन देख रहा है, और रोकड़ बही के लिए मालिक का PIN।")}</div>')
                role = st.selectbox(
                    t("Viewing as", "भूमिका (Viewing as)"), ROLES, key="role", index=ROLES.index(st.session_state["role_choice"]),
                    on_change=_on_role_change,
                    help=t("Owner sees all books; Counter staff need the owner PIN for the cash book; "
                           "the Accountant (CA) view respects the owner's sharing setting.",
                           "मालिक सभी बही-खाते देख सकते हैं; काउंटर स्टाफ को गल्ले के लिए PIN चाहिए; "
                           "एकाउंटेंट को मालिक की अनुमति से ही गल्ला दिखता है।"),
                )
                if role != "Owner":
                    if vault is not None and hasattr(vault, "lock"):
                        vault.lock()
                    st.session_state["vault_unlocked"] = False
                is_v_unlocked = st.session_state.get("vault_unlocked", False)
                if is_v_unlocked:
                    if st.button(t("Lock vault", "वॉल्ट लॉक करें"), key="btn_sidebar_lock_vault", use_container_width=True,
                                 icon=":material/lock:"):
                        vault.lock()
                        st.session_state["vault_unlocked"] = False
                        st.session_state["toast"] = t("Vault locked. Sovereign records secured.", "वॉल्ट लॉक किया गया।")
                        st.rerun()
                elif role != "Owner":
                    H(vault_role_note(role))
                else:
                    def _try_unlock(pin: str) -> bool:
                        expected_pin = os.environ.get("COPILOT_OWNER_PIN") or "0000"
                        if pin == expected_pin or (pin and vault.unlock(pin)):
                            vault.unlock(pin or expected_pin)
                            st.session_state["vault_unlocked"] = True
                            st.session_state["toast"] = t("Vault unlocked. Sovereign Plane Active.", "वॉल्ट अनलॉक हुआ।")
                            return True
                        return False

                    def _on_pin_entered():
                        # Streamlit commits a text field on Enter or when it loses focus, and the click that blurs it is
                        # used up by that commit. Unlocking here means one action is enough: Enter, Tab, or the button.
                        pin = st.session_state.get("sidebar_owner_pin_input", "")
                        if pin and not _try_unlock(pin):
                            st.session_state["_pin_wrong"] = True

                    s_pin = st.text_input(
                        t("Owner PIN", "मालिक PIN"),
                        type="password",
                        max_chars=4,
                        key="sidebar_owner_pin_input",
                        help=t("Demo PIN: 0000", "डेमो PIN: 0000"),
                        placeholder="0000",
                        on_change=_on_pin_entered,
                    )
                    if st.button(t("Unlock vault", "वॉल्ट अनलॉक करें"), key="btn_sidebar_unlock_vault", type="primary",
                                 use_container_width=True, icon=":material/lock_open:"):
                        if _try_unlock(s_pin):
                            st.rerun()
                        st.session_state["_pin_wrong"] = True
                    if st.session_state.pop("_pin_wrong", False):
                        st.error(t("Incorrect PIN.", "गलत PIN दर्ज किया गया।"))

# The language switch lives in the account menu at the foot of the sidebar (rendered below); until then the
# persisted choice stands. A widget that lost its state falls back to the persisted choice, so the two always agree.
lang = st.session_state.get("lang_choice", "English")
st.session_state["biz_choice"], st.session_state["role_choice"], st.session_state["lang_choice"] = biz, role, lang

BIZ_NAME = config.BUSINESSES[biz]
share_cash_book = st.session_state.get("share_cash_book", True)
is_owner = role == "Owner"
is_counter_staff = role == "Counter staff"
is_accountant = role == "Accountant (CA)"
is_v_unlocked = st.session_state.get("vault_unlocked", False)
# Split-plane gating: Partial view when vault is locked OR role is non-owner
showing_partial_view = (not is_owner) or (not is_v_unlocked)

if msg := st.session_state.pop("toast", None):
    st.toast(msg, icon=":material/check_circle:")
    for _k in [k for k in st.session_state if str(k).startswith("_ca_book_")]:
        del st.session_state[_k]


# Account footer at the bottom of the sidebar: whose books these are, who is viewing, and a "more" menu
# with the language switch and the secondary pages.
with st.sidebar:
    _initials = "".join(w[0] for w in BIZ_NAME.split()[:2]).upper() or "CC"
    with st.container(key="sacct"):
        H(f'<div class="cc-sacct" title="{esc(role_tip_text())}"><div class="av">{esc(_initials)}</div>'
          f'<div><div class="n">{esc(BIZ_NAME)}</div><div class="r">{esc(role_label_text())}</div></div></div>')
        with st.expander(t("Language & more", "भाषा और अन्य"), expanded=False):
            _lang_options = ["English", "हिन्दी"]
            st.radio(
                "Language / भाषा", _lang_options, horizontal=True, key="lang",
                index=_lang_options.index(st.session_state.get("lang_choice", "English")),
                on_change=lambda: st.session_state.update(lang_choice=st.session_state["lang"] or "English"),
            )
            with st.container(key="more"):
                for k in MORE_NAV:
                    st.page_link(PAGES[k], label=nav_label(k), icon=NAV_ICONS[k])
            H(f'<div class="cc-side-note">{svg(ICON_LOCK, 14)}<span>{t("Read-only. Never moves money, edits records or sends anything.", "केवल पढ़ने के लिए। यह कभी भी पैसे नहीं भेजता, रिकॉर्ड नहीं बदलता।")}</span></div>')


# ── TOP BAR (Refined Sidebar layout): STATUS · ALERTS · HELP; PAGE MENU ON PHONES ONLY ──
def render_topbar() -> None:
    counts = queue_counts(biz)
    waiting = counts[SUGGEST] + counts[ASK]
    with st.container(key="topbar"):
        c_stat, c_act = st.columns([3, 1.2], vertical_alignment="center")
        with c_stat:
            H(f'<div class="cc-brand">{LOGO}<span>Cash Copilot</span></div>'
              f'<div class="cc-status"><span class="cc-dot"></span><span>{t("Sample data pack", "नमूना डेटा")}</span>'
              f'<span class="sep">/</span><span>{t("Books as of", "हिसाब की तिथि")} {config.AS_OF:%d %b %Y}</span></div>')
        with c_act:
            with st.container(key="tacts"):
                with st.container(key="tbell"):
                    st.page_link(PAGES["review"], icon=":material/notifications:",
                                 label=t(f"{waiting:,} receipts need a decision", f"{waiting:,} प्रविष्टियों पर निर्णय बाकी"),
                                 help=t(f"{waiting:,} receipts need a decision", f"{waiting:,} प्रविष्टियों पर निर्णय बाकी"))
                st.page_link(PAGES["setup"], label=t("Help", "मदद"), icon=":material/help:")
        with st.container(key="tnav"):
            for k in TOP_NAV:
                st.page_link(PAGES[k], label=t("Ask", "पूछें") if k == "ask" else nav_label(k))
    # Mark the open page: a dark pill in the sidebar, a coral label in the phone menu.
    css = ""
    if pos := active_position(TOP_NAV):
        link = f'.st-key-snav > div:nth-child({pos}) [data-testid="stPageLink-NavLink"]'
        css += (f'{link} {{ background: var(--cc-ink) !important; box-shadow: 0 5px 14px rgba(23,25,29,0.14); transform: none !important; }}'
                f'{link} p, {link} [data-testid="stIconMaterial"] {{ color: #FFFFFF !important; }}'
                f'.st-key-tnav > div:nth-child({pos}) [data-testid="stPageLink-NavLink"] p {{ color: var(--cc-primary) !important; }}')
    if not waiting:
        css += '.st-key-tbell::after { display: none; }'
    # Page entrance: every block of the page rises in, one after another. The keyframe name carries the page,
    # so switching pages restarts the motion while reruns on the same page leave it still.
    page_key = next((k for k in PAGES if PAGES[k].title == current.title), "page")
    blocks = '[data-testid="stMainBlockContainer"] > div > div > [data-testid="stVerticalBlock"] > *'
    css += (f'@keyframes cc-in-{page_key} {{ from {{ opacity: 0; transform: translateY(18px); }} to {{ opacity: 1; transform: none; }} }}'
            f'{blocks}:not(:first-child) {{ animation: cc-in-{page_key} .8s var(--cc-ease) both; }}')
    css += "".join(f'{blocks}:nth-child({n}) {{ animation-delay: {(n - 2) * 0.07:.2f}s; }}' for n in range(2, 12))
    H(f"<style>{css}</style>")


render_topbar()
if is_hi():
    # Letter-spacing splits Devanagari conjuncts apart, so tracked caps go back to normal spacing in Hindi.
    H('<style>.stApp *:not([data-testid*="Icon"]) { letter-spacing: normal !important; }</style>')
current.run()

H(f'<footer class="cc-footer"><span>© 2026 Cash Copilot · {t("Read-only cash copilot for Indian SMEs", "भारतीय SME के लिए केवल-पढ़ने वाला नकद सहायक")}</span>'
  f'<span class="links"><span>{t("Never moves money", "कभी पैसे नहीं भेजता")}</span>'
  f'<span>{t("Cash book stays on this device", "रोकड़ बही इसी डिवाइस पर")}</span>'
  f'<span>{t("Sample data pack", "नमूना डेटा")}</span></span></footer>')
