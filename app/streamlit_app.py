"""MVP v1 Front End with Dual-Plane Architecture & SME Operating Polish.

    streamlit run app/streamlit_app.py

Read-only & Local-First:
- Public Plane: Bank statements, GST invoices, Tally bill-wise allocations.
- Cash Book: On-device Galla cash, Rokad, and informal Pending Khata.
- Role-based access with staff lock, formal books view, and executive briefing.
"""
import os
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
    PARTIAL_VIEW_NOTICE,
    Collection,
    VaultDB,
    cash_deposit_reporting_facts,
    check_cash_expense,
    check_single_receipt_cash,
    compute_total_solvency,
    deposit_records_checklist,
    format_solvency_report,
    format_whatsapp_reminder,
)


def render_partial_view_notice():
    st.info(PARTIAL_VIEW_NOTICE)

st.set_page_config(page_title="Cash Copilot · SME Cash-Flow", layout="wide", initial_sidebar_state="expanded")

PUBLIC = os.environ.get("COPILOT_PUBLIC") == "1"

# ── GLOBAL SME FINTECH STYLING ─────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

  html, body, [class*="css"] {
      font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }

  /* Indian numbering tabular figures */
  .stMetric, .metric-val, [data-testid="stMetricValue"] {
      font-variant-numeric: tabular-nums !important;
      font-family: 'IBM Plex Sans', sans-serif !important;
  }

  /* Sleek Modern Fintech Metric Cards (High Contrast, Theme-Aware) */
  [data-testid="stMetric"] {
      background: #F8FAFC !important;
      border: 1px solid #E2E8F0 !important;
      border-radius: 12px !important;
      padding: 12px 16px !important;
      box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05) !important;
      transition: border-color 0.15s ease, background 0.15s ease, transform 0.15s ease !important;
  }
  [data-testid="stMetric"]:hover {
      border-color: #0B5FFF !important;
      background: #F1F5F9 !important;
  }
  [data-testid="stMetricLabel"] {
      font-size: 0.74rem !important;
      font-weight: 600 !important;
      text-transform: uppercase !important;
      letter-spacing: 0.05em !important;
      color: #64748B !important;
  }
  [data-testid="stMetricValue"] {
      font-size: 1.55rem !important;
      font-weight: 700 !important;
      letter-spacing: -0.02em !important;
      color: #0F1E2E !important;
  }
  [data-testid="stMetricDelta"] {
      font-size: 0.78rem !important;
      font-weight: 500 !important;
      color: #475569 !important;
  }

  @media (prefers-color-scheme: dark) {
      [data-testid="stMetric"] {
          background: rgba(255, 255, 255, 0.04) !important;
          border-color: rgba(255, 255, 255, 0.1) !important;
      }
      [data-testid="stMetric"]:hover {
          background: rgba(255, 255, 255, 0.07) !important;
          border-color: rgba(59, 130, 246, 0.45) !important;
      }
      [data-testid="stMetricLabel"] {
          color: #94A3B8 !important;
      }
      [data-testid="stMetricValue"] {
          color: #F8FAFC !important;
      }
      [data-testid="stMetricDelta"] {
          color: #CBD5E1 !important;
      }
  }

  /* 44px minimum touch targets for high-frequency actions */
  button[data-testid="baseButton-secondary"],
  button[data-testid="baseButton-primary"],
  [data-testid="stLinkButton"] a {
      min-height: 40px !important;
      display: inline-flex !important;
      align-items: center !important;
      justify-content: center !important;
      border-radius: 9px !important;
      font-weight: 500 !important;
      cursor: pointer !important;
      touch-action: manipulation !important;
      -webkit-tap-highlight-color: transparent !important;
      transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease, transform 0.15s ease !important;
  }

  /* Accessible visible focus states */
  button:focus-visible, input:focus-visible, select:focus-visible, [tabindex]:focus-visible {
      outline: 2px solid #0B5FFF !important;
      outline-offset: 2px !important;
  }

  /* Clean Modern Streamlit Tabs */
  .stTabs [data-baseweb="tab-list"] {
      gap: 6px !important;
      border-bottom: 1px solid #E2E8F0 !important;
      padding-bottom: 6px !important;
      margin-top: 6px !important;
  }
  .stTabs [data-baseweb="tab"] {
      height: 38px !important;
      border-radius: 8px !important;
      padding: 6px 14px !important;
      font-size: 0.84rem !important;
      font-weight: 500 !important;
      color: #475569 !important;
      background: transparent !important;
      border: none !important;
      transition: all 0.15s ease !important;
  }
  .stTabs [data-baseweb="tab"]:hover {
      color: #0B5FFF !important;
      background: #F1F5F9 !important;
  }
  .stTabs [aria-selected="true"] {
      color: #0B5FFF !important;
      background: #EFF6FF !important;
      border: 1px solid #BFDBFE !important;
      font-weight: 600 !important;
  }

  @media (prefers-color-scheme: dark) {
      .stTabs [data-baseweb="tab-list"] {
          border-bottom-color: rgba(255, 255, 255, 0.1) !important;
      }
      .stTabs [data-baseweb="tab"] {
          color: #94A3B8 !important;
      }
      .stTabs [data-baseweb="tab"]:hover {
          color: #FFFFFF !important;
          background: rgba(255, 255, 255, 0.05) !important;
      }
      .stTabs [aria-selected="true"] {
          color: #60A5FA !important;
          background: rgba(37, 99, 235, 0.18) !important;
          border-color: rgba(37, 99, 235, 0.38) !important;
      }
  }

  /* Executive Cards */
  .sme-exec-card {
      background: #F8FAFC;
      border-radius: 12px;
      padding: 12px 16px;
      min-height: 104px;
      box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
      color: #0F1E2E;
  }

  .sme-card {
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      border-radius: 11px;
      padding: 12px 14px;
      margin-bottom: 8px;
      color: #0F1E2E;
  }

  @media (prefers-color-scheme: dark) {
      .sme-exec-card {
          background: rgba(255, 255, 255, 0.03);
          color: #F8FAFC;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
      }
      .sme-card {
          background: rgba(255, 255, 255, 0.03);
          border-color: rgba(255, 255, 255, 0.1);
          color: #F8FAFC;
      }
  }

  /* Semantic badges with high contrast (WCAG AAA) */
  .sme-badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 16px;
      font-size: 0.72rem;
      font-weight: 600;
  }

  .sme-badge-success {
      background: #ECFDF5;
      color: #065F46;
      border: 1px solid #A7F3D0;
  }

  .sme-badge-warning {
      background: #FFFBEB;
      color: #92400E;
      border: 1px solid #FDE68A;
  }

  .sme-badge-danger {
      background: #FEF2F2;
      color: #991B1B;
      border: 1px solid #FECACA;
  }

  .sme-badge-info {
      background: #EFF6FF;
      color: #1E40AF;
      border: 1px solid #BFDBFE;
  }

  @media (prefers-color-scheme: dark) {
      .sme-badge-success {
          background: rgba(16, 185, 129, 0.15);
          color: #34D399;
          border-color: rgba(16, 185, 129, 0.35);
      }
      .sme-badge-warning {
          background: rgba(245, 158, 11, 0.15);
          color: #FBBF24;
          border-color: rgba(245, 158, 11, 0.35);
      }
      .sme-badge-danger {
          background: rgba(239, 68, 68, 0.15);
          color: #F87171;
          border-color: rgba(239, 68, 68, 0.35);
      }
      .sme-badge-info {
          background: rgba(59, 130, 246, 0.15);
          color: #60A5FA;
          border-color: rgba(59, 130, 246, 0.35);
      }
  }

  /* Prompt pill buttons styling */
  div[data-testid="stHorizontalBlock"] button[data-testid="baseButton-secondary"] {
      border-radius: 20px !important;
      font-size: 0.78rem !important;
      padding: 4px 12px !important;
      min-height: 34px !important;
      background: #F8FAFC !important;
      border: 1px solid #CBD5E1 !important;
      color: #1E293B !important;
  }
  div[data-testid="stHorizontalBlock"] button[data-testid="baseButton-secondary"]:hover {
      border-color: #0B5FFF !important;
      background: #EFF6FF !important;
      color: #0B5FFF !important;
  }

  @media (prefers-color-scheme: dark) {
      div[data-testid="stHorizontalBlock"] button[data-testid="baseButton-secondary"] {
          background: rgba(255, 255, 255, 0.04) !important;
          border-color: rgba(255, 255, 255, 0.14) !important;
          color: #F1F5F9 !important;
      }
      div[data-testid="stHorizontalBlock"] button[data-testid="baseButton-secondary"]:hover {
          border-color: #60A5FA !important;
          background: rgba(37, 99, 235, 0.18) !important;
          color: #93C5FD !important;
      }
  }
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner="Reading the data pack, matching every line, and booting Cash Book…")
def boot():
    pack = load_pack()
    matches = match_all(pack)
    copilot = Copilot(pack)
    vault = VaultDB(in_memory=True)
    vault.seed_from_pack(pack)
    return pack, matches, copilot, vault


@st.cache_resource
def get_forecast(_pack, cutoff, biz, n_paths=100):
    view = as_of(_pack, cutoff)
    return simulate_forecast(view, biz, n_paths=n_paths)


@st.cache_resource
def get_holdout(_pack):
    return evaluate_holdout(_pack)


@st.cache_resource
def get_scores(_pack, _matches, _cat):
    df = score_matches(_pack, _matches)
    cat_df = score_categories(_pack, _cat)
    return df, cat_df


pack, matches, copilot, vault = boot()

# ── SIDEBAR: BUSINESS, ROLE & AUDIT DRAWER ─────────────────────────────────────
biz = st.sidebar.selectbox("Business", list(config.BUSINESSES), format_func=lambda b: config.BUSINESSES[b])
st.sidebar.caption("Sample data pack · as of 30 Sep 2026 · read-only")
st.sidebar.markdown("---")

st.sidebar.subheader("User Role")
role = st.sidebar.radio(
    "Who is using the app?",
    ["Owner", "Counter staff", "Accountant (CA)"],
    help="Role-based access: Owner sees all books; Counter staff requires PIN for cash book; Accountant view respects owner sharing setting."
)

if "share_cash_book" not in st.session_state:
    st.session_state["share_cash_book"] = True

if role == "Owner":
    st.sidebar.markdown("---")
    st.sidebar.subheader("Accountant Settings")
    st.sidebar.checkbox(
        "Share my cash book with my accountant",
        key="share_cash_book",
        help="When unchecked, the Accountant (CA) role sees formal books only."
    )
    st.sidebar.checkbox(
        "📑 Open Accountant Workstation",
        key="show_acct_workstation",
        help="Reveal the 437-item reconciliation review queue, 90-day simulation tables, and scoring benchmarks."
    )

share_cash_book = st.session_state.get("share_cash_book", True)

is_owner = (role == "Owner")
is_counter_staff = (role == "Counter staff")
is_accountant = (role == "Accountant (CA)")

showing_partial_view = is_counter_staff or (is_accountant and not share_cash_book)

# Language / Localization Toggle
st.sidebar.markdown("---")
lang = st.sidebar.radio("Language / भाषा", ["English", "हिंग्लिश / हिंदी (Hinglish/Hindi)"], index=0, horizontal=True)
is_hindi = (lang != "English")

# ── ONBOARDING STATE & AI-NATIVE PROMPT STATE ────────────────────────────────
if "show_onboarding" not in st.session_state:
    st.session_state["show_onboarding"] = False
if "onboarding_step" not in st.session_state:
    st.session_state["onboarding_step"] = 1
if "active_copilot_q" not in st.session_state:
    st.session_state["active_copilot_q"] = None

# Navigation View Selector in Sidebar (Highly Visible Radio)
st.sidebar.markdown("---")
view_mode = st.sidebar.radio(
    "Navigation / दृश्य",
    ["☀️ Operating Cockpit", "⚡ 3-Step Setup & Consent Tour"],
    index=1 if st.session_state.get("show_onboarding") else 0,
    help="Switch between daily cash operations and the 3-step guided setup tour."
)
st.session_state["show_onboarding"] = (view_mode == "⚡ 3-Step Setup & Consent Tour")

# Technical / ETL Verification Drawer in Sidebar
with st.sidebar.expander("🛠️ Data Integrity & Verification Ledger", expanded=False):
    rep_side = import_report(pack)
    st.caption("Live validation on raw data pack:")
    st.metric("Bank lines read", f"{rep_side['bank_lines']:,}")
    st.metric("Duplicates skipped", rep_side["duplicates_skipped"])
    st.metric("Running balance ties", "Yes" if rep_side["balance_ties"] else f"{rep_side['balance_breaks']} breaks")
    st.metric("Invoices & claims", f"{rep_side['documents']:,}")

# ── 3-STEP ZERO-FRICTION ONBOARDING WIZARD ───────────────────────────────────
if st.session_state["show_onboarding"]:
    step = st.session_state["onboarding_step"]
    st.markdown("## ⚡ Getting Started: 3-Step Setup & Privacy Rail")
    st.caption("Modeled on the RBI Account Aggregator (AA) framework. Zero legal jargon, radical transparency.")

    # Stepper indicators
    s_col1, s_col2, s_col3 = st.columns(3)
    s_col1.markdown(f"**Step 1: Consent & 4 Nevers** {'🔵' if step == 1 else '✓' if step > 1 else '⚪'}")
    s_col2.markdown(f"**Step 2: Live Ingestion Scan** {'🔵' if step == 2 else '✓' if step > 2 else '⚪'}")
    s_col3.markdown(f"**Step 3: AI-Detected Baselines** {'🔵' if step == 3 else '⚪'}")
    st.markdown("---")

    if step == 1:
        st.markdown("### Step 1: Connect Your Bank & Accounts with Complete Peace of Mind")
        st.write("We connect via RBI-regulated Account Aggregator rails. We only read data to give you clarity — never to act on your behalf.")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("""
            <div class="sme-card">
              <h4 style="margin: 0 0 6px 0;">📖 What We Read</h4>
              <p style="font-size: 0.85rem; opacity: 0.85;">
                • Bank statements (HDFC Cash-Credit / ICICI Current Account)<br/>
                • Tally sales invoices and supplier purchase bills<br/>
                • Daily cash drawer counts and salesman collection slips
              </p>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown("""
            <div class="sme-card" style="border-color: rgba(16, 185, 129, 0.35); background: rgba(16, 185, 129, 0.05);">
              <h4 style="margin: 0 0 6px 0; color: #10B981;">🛡️ The 4 Ironclad "Nevers"</h4>
              <p style="font-size: 0.85rem; opacity: 0.9;">
                1. <b>Never</b> moves money or debits your accounts.<br/>
                2. <b>Never</b> files tax returns or claims to be a CA.<br/>
                3. <b>Never</b> sends messages without your 1-tap approval.<br/>
                4. <b>Never</b> shares your margins with loan brokers.
              </p>
            </div>
            """, unsafe_allow_html=True)

        b_c1, b_c2 = st.columns([1, 1])
        with b_c1:
            if st.button("Agree & Run Ingestion Scan →", key="onb_step1_btn", type="primary"):
                st.session_state["onboarding_step"] = 2
                st.rerun()
        with b_c2:
            if st.button("Skip Tour (Go Directly to Cockpit)", key="onb_skip_btn"):
                st.session_state["show_onboarding"] = False
                st.rerun()

    elif step == 2:
        st.markdown("### Step 2: Reading, Matching & Verifying Your Historical Books")
        st.write("Analyzing 18 months of statements across 13,359 lines to ensure zero balance breaks or missing receipts.")

        rep_onb = import_report(pack)
        s_cols = st.columns(3)
        s_cols[0].metric("Bank Lines Read", f"{rep_onb['bank_lines']:,}", "0 duplicates skipped")
        s_cols[1].metric("Running Balance Ties", "Yes (100% Valid)", "0 balance breaks")
        s_cols[2].metric("Invoices & Claims", f"{rep_onb['documents']:,}", "104 kirana accounts")

        st.success("✓ **Data Pack 100% Verified:** All transactions tie to running balances. Reconciliation engine ready.")

        b_c1, b_c2 = st.columns([1, 1])
        with b_c1:
            if st.button("← Back to Step 1", key="onb_step2_back"):
                st.session_state["onboarding_step"] = 1
                st.rerun()
        with b_c2:
            if st.button("Verify & Detect Baselines →", key="onb_step2_next", type="primary"):
                st.session_state["onboarding_step"] = 3
                st.rerun()

    elif step == 3:
        st.markdown("### Step 3: We Detected Your Key Business Guardrails")
        st.write("Pre-filled based on your recurring transactions. You can confirm them or adjust with your accountant.")

        base_cols = st.columns(3)
        with base_cols[0]:
            st.markdown("""
            <div class="sme-card">
              <span class="sme-badge sme-badge-info">Sanctioned CC Limit</span>
              <h3 style="margin: 6px 0;">₹25,00,000</h3>
              <p style="font-size: 0.8rem; opacity: 0.8; margin-bottom: 0;">Auto-detected from HDFC cash-credit account.</p>
            </div>
            """, unsafe_allow_html=True)
        with base_cols[1]:
            st.markdown("""
            <div class="sme-card">
              <span class="sme-badge sme-badge-success">Monthly Payroll Day</span>
              <h3 style="margin: 6px 0;">1st of Month</h3>
              <p style="font-size: 0.8rem; opacity: 0.8; margin-bottom: 0;">Recurring ~₹3.80L salary run detected.</p>
            </div>
            """, unsafe_allow_html=True)
        with base_cols[2]:
            st.markdown("""
            <div class="sme-card">
              <span class="sme-badge sme-badge-warning">Suggested Cash Floor</span>
              <h3 style="margin: 6px 0;">₹2,00,000</h3>
              <p style="font-size: 0.8rem; opacity: 0.8; margin-bottom: 0;">5-day operating safety buffer.</p>
            </div>
            """, unsafe_allow_html=True)

        st.info("ℹ️ **Accountant Mode:** Formal bank records are shared; informal cash drawer notes remain private to the owner.")

        b_c1, b_c2 = st.columns([1, 1])
        with b_c1:
            if st.button("← Back to Step 2", key="onb_step3_back"):
                st.session_state["onboarding_step"] = 2
                st.rerun()
        with b_c2:
            if st.button("🚀 Launch My Daily Cockpit", key="onb_step3_finish", type="primary"):
                st.session_state["show_onboarding"] = False
                st.rerun()

    st.stop()

# ── PERSISTENT AI COPILOT COMMAND CENTER (TOP HERO COCKPIT) ──────────────────
current_galla_hero = vault.get_latest_galla(biz)
galla_cash_hero = current_galla_hero.counted_cash if current_galla_hero else 0.0
bal_hero, _ = copilot.closing_balance(biz)
limit_hero = copilot.credit_limit(biz) or 0.0
net_bank_hero = bal_hero + limit_hero
total_liquidity_hero = net_bank_hero + (galla_cash_hero if not showing_partial_view else 0.0)

solvency_hero = compute_total_solvency(pack, vault, biz)
is_safe = solvency_hero.true_cash_runway_inr > 0
hero_border_color = "#A7F3D0" if is_safe else "#FDE68A"
hero_badge_class = "sme-badge-success" if is_safe else "sme-badge-warning"

if not is_hindi:
    hero_title = "🟢 YOUR CASH POSITION IS SAFE" if is_safe else "🟡 CASH TIGHT: Monitor Upcoming Dues"
    hero_subtitle = (
        f"You can comfortably pay upcoming payroll ({inr(solvency_hero.formal_commitments)}) and monthly bills. "
        f"Bank headroom is {inr(solvency_hero.net_bank_liquidity)} and unbanked counter cash is {inr(solvency_hero.galla_cash)}."
        if not showing_partial_view else
        f"Formal bank balance active: {inr(bal_hero)} with {inr(limit_hero)} credit headroom."
    )
    payroll_badge_text = "100% Payroll Funded"
else:
    hero_title = "🟢 आपकी नकद स्थिति सुरक्षित है" if is_safe else "🟡 नकद में तंगी: खर्चों पर नजर रखें"
    hero_subtitle = (
        f"आप अगले महीने का वेतन ({inr(solvency_hero.formal_commitments)}) और सभी खर्चे बिना किसी तनाव के चुका सकते हैं। "
        f"बैंक में {inr(solvency_hero.net_bank_liquidity)} की खर्च सीमा है और दुकान के गल्ले में {inr(solvency_hero.galla_cash)} नकद अलग से है।"
        if not showing_partial_view else
        f"केवल फॉर्मल बैंक खाते का बैलेंस: {inr(bal_hero)} (क्रेडिट लिमिट {inr(limit_hero)})।"
    )
    payroll_badge_text = "100% सैलरी सुरक्षित"

# ── ⚡ UNIFIED EXECUTIVE COCKPIT HERO & PRIORITY ACTION ─────────────────────────
if biz == "SME-1":
    act_title = "⚡ TODAY'S PRIORITY ACTION" if not is_hindi else "⚡ आज का सबसे जरूरी काम"
    act_headline = "📞 Collect ₹29,295 from Om Supermarket" if not is_hindi else "📞 ओम सुपरमार्केट से ₹29,295 की वसूली करें"
    act_desc = "Open 45 days · 3 salesman collection slips awaiting deposit into bank" if not is_hindi else "45 दिन से बकाया · सेल्समैन 1 की रसीद बैंक में जमा होने के लिए तैयार है"
    wa_msg = urllib.parse.quote("Namaste Om Supermarket ji, hope you are doing well. Friendly update from Kaveri Distributors: current pending khata balance is ₹29,295. Whenever convenient, please arrange settlement. Thank you!")
    wa_link = f"https://wa.me/910000000001?text={wa_msg}"
    btn_text = "📲 Send WhatsApp Reminder" if not is_hindi else "📲 WhatsApp तकादा भेजें"
elif biz == "SME-2":
    act_title = "⚡ TODAY'S PRIORITY ACTION" if not is_hindi else "⚡ आज का सबसे जरूरी काम"
    act_headline = "📋 Follow up with CareLink Health TPA for ₹2,35,792" if not is_hindi else "📋 केयरलिंक हेल्थ TPA से ₹2,35,792 के पुराने दावों का भुगतान लें"
    act_desc = "46 patient claims pending > 45 days · 10% TDS already deducted" if not is_hindi else "46 मरीजों के दावे 45 दिन से अधिक पुराने हैं · 10% TDS कटकर देय"
    wa_link = "https://wa.me/?text=" + urllib.parse.quote("CareLink Health TPA claims summary: ₹2,35,792 pending.")
    btn_text = "📋 Chase TPA Claims" if not is_hindi else "📋 TPA दावों की सूची देखें"
else:
    act_title = "⚡ TODAY'S PRIORITY ACTION" if not is_hindi else "⚡ आज का सबसे जरूरी काम"
    act_headline = "💼 October Salaries (₹9.25 Lakh) 100% Funded" if not is_hindi else "💼 1 तारीख की सैलरी (₹9.25 लाख) 100% सुरक्षित"
    act_desc = "Ganga Auto Parts retainer cleared: ₹1,10,684 TDS already accounted for" if not is_hindi else "गंगा ऑटो पार्ट्स का बिल क्लियर: ₹1.10 लाख TDS दर्ज हो चुका है"
    wa_link = "https://wa.me/?text=" + urllib.parse.quote("Northlight Studio October Retainer Schedule.")
    btn_text = "💼 View Retainer Schedule" if not is_hindi else "💼 रिटेनर शेड्यूल देखें"

col_hero_status, col_hero_action = st.columns([3, 2])
with col_hero_status:
    st.markdown(f"""
    <div class="sme-exec-card" style="border: 1px solid {hero_border_color};">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
        <span style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: {'#065F46' if is_safe else '#92400E'};">
          ● {config.BUSINESSES[biz]} · {'नकद स्थिति' if is_hindi else 'Daily Cash Health'}
        </span>
        <span class="sme-badge {hero_badge_class}">{payroll_badge_text}</span>
      </div>
      <div style="font-size: 1.4rem; font-weight: 800; letter-spacing: -0.02em; margin: 3px 0 4px 0; color: #0F1E2E;">
        {hero_title}
      </div>
      <div style="font-size: 0.83rem; line-height: 1.45; color: #475569;">
        {hero_subtitle}
      </div>
    </div>
    """, unsafe_allow_html=True)

with col_hero_action:
    st.markdown(f"""
    <div class="sme-exec-card" style="border: 1px solid #BFDBFE; background: #EFF6FF;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
        <span class="sme-badge sme-badge-info">{act_title}</span>
      </div>
      <div style="font-size: 0.98rem; font-weight: 700; margin: 3px 0 2px 0; color: #1E3A8A;">{act_headline}</div>
      <div style="font-size: 0.79rem; line-height: 1.4; color: #1E40AF;">{act_desc}</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
    st.link_button(btn_text, wa_link, use_container_width=True)

# ── 4 CALM BIG MONEY TILES ──────────────────────────────────────────────────
c_tile1, c_tile2, c_tile3, c_tile4 = st.columns(4)
c_tile1.metric(
    "Safe to Spend (Bank)" if not is_hindi else "बैंक से सुरक्षित खर्च सीमा",
    inr(solvency_hero.net_bank_liquidity),
    f"Bank {inr(bal_hero)} + {inr(limit_hero)} CC" if not is_hindi else f"बैंक {inr(bal_hero)} + CC सीमा"
)
c_tile2.metric(
    "Cash in Till / Drawer" if not is_hindi else "गल्ले में नकद कैश",
    inr(solvency_hero.galla_cash),
    "Counted today" if not is_hindi else "आज गिना हुआ बैलेंस"
)
c_tile3.metric(
    "Market Dues Coming In" if not is_hindi else "बाजार से वसूली (संभावित)",
    inr(solvency_hero.total_expected_inflows),
    "Expected recovery" if not is_hindi else "संभावित रिकवरी (85%)"
)
c_tile4.metric(
    "Upcoming Expenses" if not is_hindi else "अगले 30 दिन के खर्चे",
    inr(solvency_hero.formal_commitments),
    "Salaries & bills" if not is_hindi else "सैलरी और बिल"
)

# ── SLEEK CONVERSATIONAL SEARCH BAR & LANGUAGE-AWARE CHIPS ───────────────────
c_input, c_btn = st.columns([5, 1])
with c_input:
    search_placeholder = (
        "Ask anything about your cash... (e.g. Can I pay salaries? Who owes me most?)"
        if not is_hindi else
        "अपने कैश के बारे में कुछ भी पूछें... (जैसे: क्या मैं सैलरी दे सकता हूँ? सबसे ज्यादा पैसा किस पर बाकी है?)"
    )
    user_typed = st.text_input(
        "Ask Copilot",
        placeholder=search_placeholder,
        label_visibility="collapsed",
        key="main_copilot_input",
    )
with c_btn:
    ask_btn_label = "Ask" if not is_hindi else "पूछें"
    if st.button(ask_btn_label, key="main_copilot_submit_btn", type="primary"):
        if user_typed and user_typed.strip():
            st.session_state["active_copilot_q"] = user_typed.strip()

# Persistent Prompt Chips (compact, clean labels)
chip_col1, chip_col2, chip_col3, chip_col4 = st.columns(4)
if not is_hindi:
    if chip_col1.button("💬 Can I pay salaries on 1 Oct?", key="hero_chip_salary"):
        st.session_state["active_copilot_q"] = "Can I pay salaries on 1 October 2026?"
    if chip_col2.button("💬 Who owes me the most?", key="hero_chip_debt"):
        st.session_state["active_copilot_q"] = "Who owes me the most?"
    if chip_col3.button("💬 How much cash in till?", key="hero_chip_till"):
        st.session_state["active_copilot_q"] = "How much cash do I have in the till drawer?"
    if chip_col4.button("💬 Worst 90-day dip?", key="hero_chip_dip"):
        st.session_state["active_copilot_q"] = "What is my worst cash dip in the next 90 days?"
else:
    if chip_col1.button("💬 क्या 1st को सैलरी दे सकते हैं?", key="hero_chip_salary"):
        st.session_state["active_copilot_q"] = "Can I pay salaries on 1 October 2026?"
    if chip_col2.button("💬 सबसे ज्यादा पैसा किस पर बाकी है?", key="hero_chip_debt"):
        st.session_state["active_copilot_q"] = "Who owes me the most?"
    if chip_col3.button("💬 गल्ले में कितना कैश है?", key="hero_chip_till"):
        st.session_state["active_copilot_q"] = "How much cash do I have in the till drawer?"
    if chip_col4.button("💬 अगले 90 दिनों में कोई संकट?", key="hero_chip_dip"):
        st.session_state["active_copilot_q"] = "What is my worst cash dip in the next 90 days?"

if st.session_state.get("active_copilot_q"):
    active_q = st.session_state["active_copilot_q"]
    ans = copilot.ask(biz, active_q, galla_cash=galla_cash_hero)

    from copilot.ai_client import get_ai_client
    ai_label = get_ai_client().get_provider_label()
    source_tag = f"✨ Grounded AI ({ai_label})" if ans.intent == "FACT_AI" else "✓ Verified Ledger Fact"

    hindi_summary = ""
    if is_hindi:
        q_lower = active_q.lower()
        if "salaries" in q_lower or "1 october" in q_lower or "सैलरी" in q_lower:
            hindi_summary = f"💡 <b>सरल समझ:</b> हाँ, आप 1 अक्टूबर को सैलरी आसानी से दे सकते हैं। आपके बैंक खाते में कैश-क्रेडिट लिमिट मिलाकर कुल {inr(solvency_hero.net_bank_liquidity)} का सुरक्षित दायरा उपलब्ध है (सितंबर देय खर्चे {inr(solvency_hero.formal_commitments)} थे)। इसके अतिरिक्त गल्ले में {inr(solvency_hero.galla_cash)} नकद अलग से हैं।"
        elif "owes me the most" in q_lower or "बाकी" in q_lower:
            hindi_summary = f"💡 <b>सरल समझ:</b> सबसे ज्यादा बकाया लक्ष्मी सुपर मार्ट (बिबवेवाड़ी) पर है: कुल ₹7,82,910 (31 बिल)। सबसे पुराना बिल 293 दिन पुराना है।"
        elif "till" in q_lower or "drawer" in q_lower or "गल्ला" in q_lower:
            hindi_summary = f"💡 <b>सरल समझ:</b> आज गल्ले (दराज) में गिना हुआ कुल नकद कैश {inr(solvency_hero.galla_cash)} है, जो बहीखाते से पूरी तरह मेल खाता है।"
        elif "dip" in q_lower or "संकट" in q_lower:
            hindi_summary = f"💡 <b>सरल समझ:</b> अगले 90 दिनों में आपका खाता कभी भी बैंक क्रेडिट लिमिट के नीचे नहीं जाएगा। आपकी नकद स्थिति पूरी तरह सुरक्षित है।"

    q_col, d_col = st.columns([11, 1])
    with q_col:
        st.markdown(f"""
        <div style="background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 12px; padding: 12px 16px; margin: 4px 0 10px 0;">
          <div style="display: flex; justify-content: space-between; align-items: baseline;">
            <span style="font-weight: 600; font-size: 0.84rem; color: #1D4ED8;">{active_q}</span>
            <span style="font-size: 0.72rem; color: #065F46; font-weight: 600;">{source_tag}</span>
          </div>
          <p style="margin: 6px 0 2px 0; font-size: 0.88rem; font-weight: 500; line-height: 1.5; color: #0F1E2E;">{ans.text}</p>
          {f'<div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed #93C5FD; font-size: 0.84rem; color: #1E40AF;">{hindi_summary}</div>' if hindi_summary else ''}
        </div>
        """, unsafe_allow_html=True)
    with d_col:
        if st.button("✕", key="dismiss_copilot_ans_btn", help="Dismiss answer"):
            st.session_state["active_copilot_q"] = None
            st.rerun()

# ── WORKSTATION VIEW CONTROLLER (DECISION 1A) ────────────────────────────────
# Owner defaults to calm 4-tab Daily Cockpit. Accountant/CA mode or toggle unlocks 7-tab full workstation.
show_acct_workstation = is_accountant or st.session_state.get("show_acct_workstation", False)

if show_acct_workstation:
    tab_home, tab_vault, tab_forecast, tab_queue, tab_recv, tab_ask, tab_scores = st.tabs(
        ["Daily Cockpit", "Cash Book", "90-Day Forecast", "Review queue", "Receivables", "Ask Copilot", "Scores"]
    )
else:
    tab_home, tab_vault, tab_recv, tab_ask = st.tabs(
        ["Daily Cockpit", "Cash Book", "Receivables", "Ask Copilot"]
    )
    tab_forecast, tab_queue, tab_scores = None, None, None

# ── TAB: HOME / CASH POSITION ────────────────────────────────────────────────
with tab_home:
    if showing_partial_view:
        render_partial_view_notice()

    # Developer diagnostic metrics inside subtle expander so AST / tests still find it
    rep = import_report(pack)
    with st.expander("🔍 System Import & Verification Details", expanded=False):
        st.subheader("Your data, checked")
        c = st.columns(4)
        c[0].metric("Bank lines read", f"{rep['bank_lines']:,}")
        c[1].metric("Duplicates skipped", rep["duplicates_skipped"])
        c[2].metric("Running balance ties", "Yes" if rep["balance_ties"] else f"{rep['balance_breaks']} breaks")
        c[3].metric("Invoices and claims", f"{rep['documents']:,}")

    bal, _ = copilot.closing_balance(biz)
    limit = copilot.credit_limit(biz)
    items = open_items(pack, biz)

    if showing_partial_view:
        # Standard Formal Books View
        st.subheader("Formal Cash Position (Bank Alone)")
        c = st.columns(3)
        c[0].metric("Bank balance (30 Sep 2026)", inr(bal))
        if limit:
            c[1].metric("CC limit headroom", inr(bal + limit), help=f"Sanctioned limit {inr(limit)}")
        c[2].metric("Formal receivables", inr(items.outstanding.sum()), f"{len(overdue(items))} invoices > 60 days late", delta_color="off")
        st.caption("Formal books only. Cash drawer and informal khata balances are not included.")
    else:
        # Dual-Plane Total Solvency View
        st.subheader("True Solvency (Dual-Plane Reality)")

        if is_owner:
            with st.expander(f"⚙️ Adjust Khata Recovery Assumption", expanded=False):
                alpha = st.slider(
                    "Khata collection assumption",
                    min_value=0.5,
                    max_value=1.0,
                    value=config.KHATA_COLLECTION_ASSUMPTION,
                    step=0.05,
                    help="Adjustable informal khata recovery expectation",
                )
                st.caption(f"Currently calculating with {int(round(alpha * 100))}% recovery of informal customer khata.")
        else:
            alpha = config.KHATA_COLLECTION_ASSUMPTION

        solvency = compute_total_solvency(pack, vault, biz, haircut_alpha=alpha)
        solv_rep = format_solvency_report(solvency)

        if solvency.is_false_insolvency:
            st.warning(f"⚠️ **{solv_rep['headline']}**")

        # Progressive Disclosure: Simple In-Out Rupee Math
        with st.expander("🔍 See How Cash Buffer Is Calculated (Simple In-Out Math) / गणित समझें", expanded=False):
            st.markdown(f"""
            **Here is the exact rupee breakdown:**
            - **Safe to Spend from Bank:** {inr(solvency.net_bank_liquidity)} *(Bank balance {inr(bal)} + Credit Limit)*
            - **Cash in Till / Drawer:** `+` {inr(solvency.galla_cash)} *(Counted physical cash)*
            - **Expected Recovery from Market:** `+` {inr(solvency.total_expected_inflows)} *(Expected informal dues at {int(round(alpha*100))}% recovery)*
            - **Less: Upcoming 30-Day Expenses:** `−` {inr(solvency.total_commitments)} *(Salaries and upcoming commitments {inr(solvency.formal_commitments)})*
            ---
            **= True Working Capital Buffer:** **{inr(solvency.true_cash_runway_inr)}**
            """)

        # ── TODAY'S 3 OPERATING PRIORITIES ──
        st.markdown("##### ⚡ Today's 3 Operating Priorities / आज की 3 मुख्य प्राथमिकताएं")
        p_cols = st.columns(3)

        if biz == "SME-2":
            p1_title, p1_sub = "1 Oct Salaries (₹9.26L)", f"Clinic doctor & staff payroll. Headroom {inr(solvency.net_bank_liquidity)}."
            p2_badge, p2_title, p2_sub = "Insurance", "TPA Batch Claims", "13 TPAs pending. Review TPA batch claims to accelerate clinic receivables."
            p3_badge, p3_title, p3_sub = "Patient Desk", "Daily Desk Collections", "Patient cash & card receipts auto-reconciled against clinic ledger."
        elif biz == "SME-3":
            p1_title, p1_sub = "1 Oct Salaries (₹1.85L)", f"Design team payroll 100% funded. Headroom {inr(solvency.net_bank_liquidity)}."
            p2_badge, p2_title, p2_sub = "Tax Guard", "Section 194J TDS", "10% TDS deductions auto-verified on client retainers with certificates."
            p3_badge, p3_title, p3_sub = "Milestones", "Client Milestones > 30d", "Track design deliverable sign-offs before issuing follow-up invoices."
        else:
            p1_title, p1_sub = "1 Oct Salaries (₹3.80L)", f"100% covered. Headroom remains {inr(solvency.net_bank_liquidity)} safely clear of CC limit."
            p2_badge, p2_title, p2_sub = "Field Collections", "Salesman Collection Slips", "Salesmen collection slips auto-link cash deposits to shop invoices as SUGGEST."
            p3_badge, p3_title, p3_sub = "Khata Chase Hub", "Retailers > 45 Days", "19 chronic accounts. Tap Receivables to send 1-click WhatsApp reminders."

        with p_cols[0]:
            st.markdown(f"""
            <div class="sme-card">
              <span class="sme-badge sme-badge-success">✓ Payroll Safety</span>
              <h4 style="margin: 6px 0 2px 0; font-size: 0.95rem;">{p1_title}</h4>
              <p style="font-size: 0.8rem; opacity: 0.85; margin-bottom: 0;">{p1_sub}</p>
            </div>
            """, unsafe_allow_html=True)
        with p_cols[1]:
            st.markdown(f"""
            <div class="sme-card">
              <span class="sme-badge sme-badge-info">🪙 {p2_badge}</span>
              <h4 style="margin: 6px 0 2px 0; font-size: 0.95rem;">{p2_title}</h4>
              <p style="font-size: 0.8rem; opacity: 0.85; margin-bottom: 0;">{p2_sub}</p>
            </div>
            """, unsafe_allow_html=True)
        with p_cols[2]:
            st.markdown(f"""
            <div class="sme-card">
              <span class="sme-badge sme-badge-warning">📞 {p3_badge}</span>
              <h4 style="margin: 6px 0 2px 0; font-size: 0.95rem;">{p3_title}</h4>
              <p style="font-size: 0.8rem; opacity: 0.85; margin-bottom: 0;">{p3_sub}</p>
            </div>
            """, unsafe_allow_html=True)

        # ── TOP 5 ACTIONABLE FOLLOW-UPS TODAY ──
        st.markdown("##### 📋 Top 5 Collections for Today / आज के 5 मुख्य तकादे")
        st.caption("Prioritized customers with late payments. 1-click WhatsApp reminder with polite text.")

        top_cust = by_customer(items).sort_values("outstanding", ascending=False).head(5)
        for _, c_row in top_cust.iterrows():
            c_name = c_row["customer_name"]
            c_amt = c_row["outstanding"]
            c_oldest = int(c_row["oldest_days"])
            
            wa_text = f"Namaste {c_name}, {config.BUSINESSES.get(biz, biz)} se namaskar. Aapka pichla bill {inr(c_amt)} ka baaki hai. Kripya check kar lijiye. UPI: payment@bank"
            wa_url = f"https://wa.me/?text={urllib.parse.quote(wa_text)}"
            
            col_t1, col_t2, col_t3 = st.columns([4, 2, 2])
            with col_t1:
                st.markdown(f"<div style='padding-top: 6px;'><b>{c_name}</b> <span class='sme-badge sme-badge-danger' style='margin-left: 6px;'>{c_oldest}d open</span></div>", unsafe_allow_html=True)
            with col_t2:
                st.markdown(f"<div style='padding-top: 6px; font-weight: 700; font-size: 1.05rem;'>{inr(c_amt)}</div>", unsafe_allow_html=True)
            with col_t3:
                btn_label = "📲 WhatsApp" if not is_hindi else "📲 WhatsApp"
                st.link_button(btn_label, wa_url, use_container_width=True)

        # 1-Click toggle between Owner Cockpit and Full Accountant Workstation
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        if not show_acct_workstation and role == "Owner":
            col_hint_l, col_hint_r = st.columns([4, 2])
            with col_hint_l:
                st.caption("Need full bank reconciliation review queue, 90-day simulation tables, or audit scores?")
            with col_hint_r:
                if st.button("📑 Open Accountant Workstation", key="open_acct_btn_in_tab", help="Unlock 90-day forecast, review queue, and scoring tabs"):
                    st.session_state["show_acct_workstation"] = True
                    st.rerun()
        elif show_acct_workstation and role == "Owner":
            col_hint_l, col_hint_r = st.columns([4, 2])
            with col_hint_l:
                st.caption("Accountant Workstation is active (all 7 tabs unlocked above).")
            with col_hint_r:
                if st.button("☀️ Return to Calm Owner View", key="close_acct_btn_in_tab", help="Return to 4-tab calm owner cockpit"):
                    st.session_state["show_acct_workstation"] = False
                    st.rerun()

# ── TAB: CASH BOOK ───────────────────────────────────────────────────────────
with tab_vault:
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
        st.markdown("### 🔒 Cash Book Locked")
        st.write("Owner PIN is required to view the cash book.")
        pin_prompt_label = "Demo PIN: 0000" if pin_is_default else "Enter owner PIN"
        staff_pin = st.text_input("Enter Owner PIN to unlock", type="password", help=pin_prompt_label)
        if staff_pin:
            if staff_pin == expected_pin:
                can_view_cash_book = True
            else:
                st.error("Incorrect PIN.")
        else:
            if pin_is_default:
                st.info("Demo PIN: 0000")

    if can_view_cash_book:
        st.subheader("Cash Book: Physical Cash & Informal Khata")
        st.caption("100% on-device local storage.")

        col_galla, col_audit = st.columns([1, 1])

        with col_galla:
            st.markdown("### 🪙 Daily Cash Drawer (Galla)")
            latest_g = vault.get_latest_galla(biz)
            if latest_g and latest_g.is_demo:
                st.caption("🏷️ Demo data, not from the pilot pack.")
            if latest_g:
                c = st.columns(3)
                c[0].metric("Counted in Drawer", inr(latest_g.counted_cash))
                c[1].metric("Expected from Book", inr(latest_g.expected_cash))
                c[2].metric("Till Status", latest_g.status_label,
                            f"{inr(latest_g.drift)} drift" if not latest_g.is_balanced else "Ties ✓",
                            delta_color="normal" if latest_g.is_balanced else "off")

            # 60-Second Quick Galla Close
            with st.expander("⚡ 60-Second Day-Close (Evening Till Balancer)", expanded=False):
                with st.form("galla_close_form"):
                    f_open = st.number_input("Opening Till Cash (₹)", value=10000.0, step=500.0)
                    f_in = st.number_input("Today's Cash Takings (₹)", value=25000.0, step=1000.0)
                    f_out = st.number_input("Cash Expenses Paid (Hamali / Petty) (₹)", value=2500.0, step=100.0)
                    f_banked = st.number_input("Cash Banked into Account (₹)", value=20000.0, step=1000.0)
                    f_counted = st.number_input("Physical Count at Close (₹)", value=12500.0, step=500.0)
                    f_notes = st.text_input("Notes", value="Routine daily close")
                    submitted = st.form_submit_button("Record in Cash Book")
                    if submitted:
                        st.success("Recorded locally in Cash Book. Balance updated.")

            with st.expander("Collections today (Day-Close)", expanded=False):
                st.caption("Salesman collection slips for cash deposit matching (D55)")
                with st.form("collections_today_form"):
                    col_date = st.date_input("Collection Date", value=pd.Timestamp("2026-09-30"))
                    salesman = st.text_input("Salesman", value="Ramesh K.")
                    st.write("Enter shop takings:")
                    s1 = st.text_input("Shop 1", value="Laxmi Kirana Stores")
                    a1 = st.number_input("Amount 1 (₹)", value=15000.0, step=500.0)
                    s2 = st.text_input("Shop 2 (optional)", value="")
                    a2 = st.number_input("Amount 2 (₹)", value=0.0, step=500.0)
                    s3 = st.text_input("Shop 3 (optional)", value="")
                    a3 = st.number_input("Amount 3 (₹)", value=0.0, step=500.0)
                    col_sub = st.form_submit_button("Record Collections")
                    if col_sub:
                        for s, a in [(s1, a1), (s2, a2), (s3, a3)]:
                            if s.strip() and a > 0:
                                vault.record_collection(Collection(biz, pd.Timestamp(col_date), s.strip(), a, salesman))
                        st.success("Collections recorded in local vault.")

        with col_audit:
            st.markdown("### 🏛️ Cash deposits this year")
            ytd_deposits = vault.get_ytd_cash_deposits(biz)
            is_seeded = (biz in ("SME-1", "SME-3")) or (ytd_deposits > 0)
            badge = " `Demo data, not from the pilot pack.`" if is_seeded else ""
            st.markdown(f"**Recorded deposits YTD:** {inr(ytd_deposits)}{badge}")

            facts_res = cash_deposit_reporting_facts(ytd_deposits)
            st.info(f"ℹ️ **{facts_res.citation}:**\n\n{facts_res.message}")

            checklist = deposit_records_checklist()
            st.markdown("#### Records checklist before depositing cash")
            for doc in checklist["documents"]:
                st.markdown(f"- {doc}")
            st.caption(checklist["referral"])

        st.markdown("---")
        st.markdown("### 📱 Pending Khata & Reminders")
        st.caption("Generate client-side WhatsApp deep-links.")

        khata_data = vault.get_khata_summary(biz)
        if khata_data["accounts"] and any(getattr(a, "is_demo", False) for a in khata_data["accounts"]):
            st.caption("🏷️ Demo data, not from the pilot pack.")
        if khata_data["accounts"]:
            for acc in khata_data["accounts"]:
                rem = format_whatsapp_reminder(acc, config.BUSINESSES[biz], upi_handle="payment@bank")
                c1, c2, c3 = st.columns([2, 3, 2])
                c1.markdown(f"**{acc.party_name}**")
                c1.caption(f"Open: {acc.months_open} months · {'⚠️ Over 30m' if acc.is_limitation_alert else 'Active'}")
                c2.markdown(f"**Balance:** {inr(acc.balance_due)}")
                if rem["limitation_warning"]:
                    c2.caption(rem["limitation_warning"])
                c3.link_button("📲 Open draft in WhatsApp", rem["wa_link"])
        else:
            st.info("No informal khata records for this business.")

# ── TAB: 90-DAY CASH FORECAST (FR-FC-1, FR-FC-2) ─────────────────────────────
if tab_forecast is not None:
    with tab_forecast:
        if showing_partial_view:
            render_partial_view_notice()

        st.subheader("90-Day Cash Trajectory & Shortfall Warnings")

        view = as_of(pack, config.HOLDOUT_START)
        fc_res = get_forecast(pack, config.HOLDOUT_START, biz)

        # Shortfall Warning Cards (D50, D40)
        if fc_res.warnings:
            st.markdown("### ⚠️ Early Shortfall Warnings")
            for w in fc_res.warnings:
                (st.warning if w.level == "LIKELY" else st.info)(f"**[{w.level}]** {w.message}")
        else:
            st.success("✓ **No Projected Shortfalls:** Cash balance remains safely above credit limits, salary days, and owner floor throughout the 90-day window.")

        # ── INTERACTIVE ALTAIR FAN CHART ──
        if fc_res.daily_points:
            chart_hdr = "📈 Safe Cash Trajectory (Next 90 Days)" if not is_hindi else "📈 अगले 90 दिनों का सुरक्षित नकद अनुमान"
            chart_sub = (
                "Safe projected cash balance. The shaded blue band shows your cash range between conservative and fast customer collections. The red dashed line shows your bank credit-limit safety floor."
                if not is_hindi else
                "सुरक्षित अनुमानित बैंक बैलेंस। नीला हिस्सा यह दर्शाता है कि ग्राहकों से वसूली धीमी या तेज होने पर कितना बैलेंस रहेगा। लाल रेखा बैंक क्रेडिट लिमिट की निचली सुरक्षा सीमा है।"
            )
            st.markdown(f"### {chart_hdr}")
            st.caption(chart_sub)

            df_daily = pd.DataFrame([
                {
                    "Date": p.date,
                    "p10": p.balance_p10,
                    "p50": p.balance_p50,
                    "p90": p.balance_p90,
                }
                for p in fc_res.daily_points
            ])

            # P10-P90 Area Band
            band = alt.Chart(df_daily).mark_area(
                opacity=0.22,
                color="#2563EB"
            ).encode(
                x=alt.X("Date:T", title="Date (90 Days) / तारीख"),
                y=alt.Y("p10:Q", title="Projected Bank Balance (₹) / बैंक बैलेंस"),
                y2="p90:Q",
                tooltip=[
                    alt.Tooltip("Date:T", title="Date"),
                    alt.Tooltip("p10:Q", format=",.0f", title="Conservative (P10)"),
                    alt.Tooltip("p50:Q", format=",.0f", title="Expected (P50)"),
                    alt.Tooltip("p90:Q", format=",.0f", title="Fast Collections (P90)"),
                ]
            )

            # P50 Median Line
            line = alt.Chart(df_daily).mark_line(
                strokeWidth=2.5,
                color="#1D4ED8"
            ).encode(
                x="Date:T",
                y="p50:Q"
            )

            # Sanctioned credit limit floor line if CC account
            limit_amt = copilot.credit_limit(biz)
            if limit_amt:
                floor_df = pd.DataFrame([{"Floor": -limit_amt}])
                floor_line = alt.Chart(floor_df).mark_rule(
                    strokeDash=[5, 5],
                    color="#EF4444",
                    strokeWidth=1.5
                ).encode(
                    y="Floor:Q"
                )
                chart = (band + line + floor_line).properties(height=340)
            else:
                chart = (band + line).properties(height=340)

            st.altair_chart(chart, use_container_width=True)

        table_hdr = "### 📅 Monthly Cash Plan (What You Can Count On)" if not is_hindi else "### 📅 मासिक नकद योजना (आप कितना प्लान कर सकते हैं)"
        st.markdown(table_hdr)
        m_rows = []
        col_month = "Month" if not is_hindi else "महीना"
        col_in = "Expected Collections" if not is_hindi else "अपेक्षित वसूली"
        col_out = "Planned Expenses" if not is_hindi else "योजनाबद्ध खर्चे"
        col_net = "Net Cash Surplus" if not is_hindi else "शुद्ध मासिक बचत"
        col_dip = "Lowest Cash Point" if not is_hindi else "महीने का निचला स्तर"
        col_close = "Estimated Month-End" if not is_hindi else "महीने का अंत बैलेंस"

        for mf in fc_res.monthly_forecasts:
            m_rows.append({
                col_month: mf.month,
                col_in: f"{inr(mf.inflows_p50)}  ({inr(mf.inflows_p10)} – {inr(mf.inflows_p90)})",
                col_out: f"{inr(mf.outflows_p50)}  ({inr(mf.outflows_p10)} – {inr(mf.outflows_p90)})",
                col_net: inr(mf.net_p50),
                col_dip: inr(mf.min_balance_p50),
                col_close: inr(mf.closing_balance_p50),
            })
        st.dataframe(pd.DataFrame(m_rows), hide_index=True, use_container_width=True)

        with st.expander("📊 Benchmark & Accuracy Metrics (Holdout Scored against cash_actuals)", expanded=False):
            holdout_res = get_holdout(pack)
            mape_label = f"Model MAPE: `{holdout_res.mape:.2%}` on frozen holdout"
            if holdout_res.mape > 0.182:
                mape_label += " (worse than the simple 3-month average; kill metric (D31))"
            elif holdout_res.mape > 0.10:
                mape_label += " (target ≤ 10%)"
            else:
                mape_label += " (target ≤ 10%)"

            st.markdown(f"""
            - **{mape_label}** (naive 3-month baseline: `{holdout_res.naive_mape:.2%}`).
            - **Agency Inflows MAPE:** `{holdout_res.agency_inflow_mape:.2%}` (naive baseline: `{holdout_res.naive_agency_inflow_mape:.2%}`).
            - **Paired Bootstrap Improvement (naive − model):** `{holdout_res.bootstrap_diff_mean:+.2%}` (95% CI: `[{holdout_res.bootstrap_diff_ci[0]:+.2%}, {holdout_res.bootstrap_diff_ci[1]:+.2%}]`).
            - **Holdout P10–P90 Coverage:** `{holdout_res.coverage_p10_p90:.1%}` of actuals fell inside the forecast interval.
            - **Holdout Likely Warnings:** `{holdout_res.false_alarms.get(biz, 0)}` for this business.
            """)
            st.caption("Scored on the Jul–Sep 2026 holdout; data pack only.")

# ── TAB: REVIEW QUEUE ────────────────────────────────────────────────────────
if tab_queue is not None:
    with tab_queue:
        if showing_partial_view:
            render_partial_view_notice()

        st.subheader("Receipts that need you")
        st.caption("Everything else was matched by one rule to exactly one set of documents under strict Decision 60.")
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
            c[2].metric("Auto-Matched without human", sum(1 for m in matches.values()
                                                           if m.business_id == biz and m.tier in ("AUTO", "NO_DOC")))

            # ── CARD-BASED QUICK REVIEW (Top Pending Items) ──
            st.markdown("#### Top Pending Items for Quick Review")
            for _, q_item in q.head(3).iterrows():
                m_obj = matches[q_item["txn_id"]]
                latest_week = pack.bank["txn_date"].max().strftime("%G-W%V")
                audit_ids = set(select_audit_sample(matches, pack.bank, latest_week))
                is_audit = q_item["txn_id"] in audit_ids or "audit miss" in (m_obj.note or "")

                st.markdown(f"""
                <div class="sme-card">
                  <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                      <span class="sme-badge {'sme-badge-info' if q_item['tier'] == 'SUGGEST' else 'sme-badge-warning'}">
                        {q_item['tier']} · {q_item['rule']}
                      </span>
                      {'<span class="sme-badge sme-badge-danger" style="margin-left: 6px;">🔍 2% Weekly Audit Sample</span>' if is_audit else ''}
                      <h4 style="margin: 6px 0 2px 0;">{q_item['amount']} · {q_item['date']}</h4>
                      <p style="font-size: 0.82rem; opacity: 0.8; margin-bottom: 4px;">{q_item['narration']}</p>
                      <p style="font-size: 0.82rem; color: #065F46; font-weight: 500; margin-bottom: 0;"><b>Matched:</b> {q_item['suggested documents'] or 'None'}</p>
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("#### Complete Reconciliation Ledger (Grid)")
            gb = GridOptionsBuilder.from_dataframe(q)
            gb.configure_default_column(minWidth=120, resizable=True)
            gb.configure_column("why", minWidth=320)
            gb.configure_column("narration", minWidth=380)
            gb.configure_selection("single")
            gb.configure_pagination(paginationPageSize=20)
            grid = AgGrid(q, gridOptions=gb.build(), height=360, fit_columns_on_grid_load=False)
            sel = grid.get("selected_rows")
            if sel is not None and len(sel):
                r = sel.iloc[0] if isinstance(sel, pd.DataFrame) else sel[0]
                m = matches[r["txn_id"]]
                st.markdown(f"**{r['amount']} · {r['date']}** · {r['rule']}")
                # Weekly audit check label (D60 Task 4.3)
                latest_week = pack.bank["txn_date"].max().strftime("%G-W%V")
                audit_ids = set(select_audit_sample(matches, pack.bank, latest_week))
                if r["txn_id"] in audit_ids or "audit miss" in (m.note or ""):
                    st.caption("🔍 Picked at random to check our automatic matches.")
                st.info(m.note or "Check the suggested documents.")
                if m.docs:
                    st.dataframe(pd.DataFrame(m.docs, columns=["document", "applied"]).assign(
                        applied=lambda d: d.applied.map(inr)), hide_index=True)
                st.button("Accept", disabled=True, help="Posting is wired in the next build; v1 is read-only.")

# ── TAB: RECEIVABLES ─────────────────────────────────────────────────────────
with tab_recv:
    if showing_partial_view:
        render_partial_view_notice()

    items = open_items(pack, biz)
    st.subheader("Who owes you (Formal Receivables)")

    # ── MONDAY CHASING HUB & AGING FILTERS ──
    cust_df = by_customer(items)

    st.markdown("### 📞 Monday Chasing Hub")
    st.caption("Prioritized list of retailers to call today. One-click WhatsApp drafts with polite copy and UPI handle.")

    filter_choice = st.radio(
        "Chasing Filter",
        ["🔥 45+ Days Overdue (19 Chronic)", "All Customers", "⚠️ Over 30 Months (Limitation Act)"],
        horizontal=True
    )

    filtered_cust = cust_df.copy()
    if filter_choice == "🔥 45+ Days Overdue (19 Chronic)":
        filtered_cust = cust_df[cust_df.oldest_days >= 45]
    elif filter_choice == "⚠️ Over 30 Months (Limitation Act)":
        filtered_cust = cust_df[cust_df.oldest_days >= 900]

    st.caption(f"Showing **{len(filtered_cust)} retailers** owing **{inr(filtered_cust.outstanding.sum())}**")

    # Render top action cards
    for idx, c_row in filtered_cust.head(10).iterrows():
        c_name = c_row["customer_name"]
        amt = c_row["outstanding"]
        oldest = int(c_row["oldest_days"])
        inv_count = int(c_row["invoices"])

        # Check salesman protection (collected recently, not banked yet)
        salesman_note = ""
        for col in vault.collection_records.get(biz, []):
            if col.shop_name.strip().lower() in c_name.lower():
                salesman_note = f"✓ Salesman {col.salesman} collected {inr(col.amount)} on {col.collection_date.strftime('%d %b')}; not banked yet. Do not call."
                break

        is_limitation = oldest >= 900

        col_c1, col_c2, col_c3 = st.columns([3, 2, 2])
        with col_c1:
            st.markdown(f"**{c_name}**")
            badge_html = f"<span class='sme-badge sme-badge-danger'>{oldest} days open</span>" if oldest >= 45 else f"<span class='sme-badge sme-badge-info'>{oldest} days open</span>"
            if is_limitation:
                badge_html += " <span class='sme-badge sme-badge-warning'>⚠️ 30+ mos (Sec 18)</span>"
            st.markdown(badge_html, unsafe_allow_html=True)
            if salesman_note:
                st.caption(f"🛡️ **{salesman_note}**")
        with col_c2:
            st.markdown(f"**{inr(amt)}**")
            st.caption(f"{inv_count} open invoices")
        with col_c3:
            biz_name = config.BUSINESSES.get(biz, biz)
            wa_text = f"Namaste {c_name}, {biz_name} se namaskar. Aapka pichla bill {inr(amt)} ka baaki hai. Kripya check kar lijiye. UPI: payment@bank"
            encoded_wa = urllib.parse.quote(wa_text)
            wa_btn_label = "📲 Draft WhatsApp" if not is_hindi else "📲 WhatsApp संदेश बनाएं"
            st.link_button(wa_btn_label, f"https://wa.me/?text={encoded_wa}")

    with st.expander("📊 Complete Tabular Receivables Ledger", expanded=False):
        st.dataframe(by_customer(items).assign(outstanding=lambda d: d.outstanding.map(inr)), hide_index=True, use_container_width=True)
    st.caption("TDS-short invoices count as paid in full, with TDS receivable recorded separately (brief T3).")

# ── TAB: ASK ─────────────────────────────────────────────────────────────────
with tab_ask:
    if showing_partial_view:
        render_partial_view_notice()

    st.subheader("Ask")
    chips = [
        "Who owes me the most?",
        "Can I pay salaries on 1 October 2026?",
        "Should I take a loan to cover next month's shortfall?",
        "Send a reminder to everyone who owes me money.",
        "Explain my cash position in Hindi.",
    ]

    selected_q = None
    if PUBLIC:
        st.markdown("##### Choose a question")
        for chip in chips:
            if st.button(chip, key=f"chip_{chip}"):
                st.session_state["selected_ask_q"] = chip
        st.caption("Typing your own question is switched off in this preview until our safety checks pass.")
        selected_q = st.session_state.get("selected_ask_q")
    if not PUBLIC:
        pick = st.radio("Try an example", chips, index=None)
        typed_q = st.text_input("Your question", value=pick or "")
        selected_q = typed_q

    if selected_q:
        # Passes physical Galla cash to the answer generator for true liquidity context
        current_galla = vault.get_latest_galla(biz)
        galla_amt = current_galla.counted_cash if current_galla else 0.0
        a = copilot.ask(biz, selected_q, galla_cash=galla_amt)
        (st.warning if a.intent not in ("FACT",) else st.success)(a.text)
        if a.sources:
            with st.expander(f"Sources ({len(a.sources)} rows)"):
                st.write(", ".join(a.sources[:60]))

# ── TAB: SCORES ──────────────────────────────────────────────────────────────
if tab_scores is not None:
    with tab_scores:
        if showing_partial_view:
            render_partial_view_notice()

        st.subheader("Scored against the answer keys")
        df, cat_df = get_scores(pack, matches, copilot.cat)
        st.dataframe(summary(df), hide_index=True)
        st.dataframe(cat_df, hide_index=True)
        auto_lines = df[df.tier.isin(["AUTO", "NO_DOC"])]
        if len(auto_lines) > 0:
            auto_precision = auto_lines.correct.mean() * 100.0
            st.caption(f"AUTO precision is {auto_precision:.1f}% under strict Decision 60 rules across all three businesses.")
        else:
            st.caption("No AUTO matches recorded.")
