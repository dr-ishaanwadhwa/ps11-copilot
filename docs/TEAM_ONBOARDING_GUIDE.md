# SME Cash-Flow Copilot: Complete Team Onboarding, Data Deep-Dive, User Guide & Technical Architecture

> **Target Audience:** Engineering, Product, Design, and Data teammates on Team 11 (LedgerLite Pilot, Masters' Union Applied AI Challenge PS-11).  
> **Core Operating Principle:** *"It explains every rupee between your bank and your books, and never acts without you."*  
> **Live Production Reference:** [https://sme-cashflow.medevolv.in](https://sme-cashflow.medevolv.in) (checked 16 Nov 2026: up, serving the PS-11 app on the data pack; it predates the Hindi fix in commit `84eb6cc`, so redeploy before demoing Hindi). Use only this address: `life-inbox.medevolv.in`, listed in the one-page note, is the Life Inbox project's domain and did not respond.  
> **Verified Engineering Status (re-run 16 Nov 2026):** 479 passing tests, 100.0% Decision 60 AUTO precision on 7,639 lines, categorisation 99.6% by line / 98.8% by rupee on the holdout, 13.48% holdout forecast MAPE against an 18.19% naive baseline (the gain is not yet statistically significant; see §7.2).

---

## Table of Contents
1. [Executive Summary & The Ground Reality](#1-executive-summary--the-ground-reality)
2. [The Three SME Archetypes](#2-the-three-sme-archetypes)
3. [Dataset Deep-Dive & Data Pack Architecture](#3-dataset-deep-dive--data-pack-architecture)
4. [Step-by-Step Developer Quickstart](#4-step-by-step-developer-quickstart)
5. [User Guide: The 8 Interactive Pages & Workflows](#5-user-guide-the-8-interactive-pages--workflows)
6. [Technical Architecture & Subsystem Deep-Dive](#6-technical-architecture--subsystem-deep-dive)
7. [Verified Performance Benchmarks](#7-verified-performance-benchmarks)
8. [Critical Audit of Prior Assumptions & Traps](#8-critical-audit-of-prior-assumptions--traps)
9. [Open Questions & Product Roadmap](#9-open-questions--product-roadmap)
10. [Market Sizing & the Final Pitch Deck](#10-market-sizing--the-final-pitch-deck)

---

## 1. Executive Summary & The Ground Reality

### 1.1 The Problem
India has tens of millions of micro, small, and medium enterprises (MSMEs). Almost all of them manage their operational finances through an ad-hoc combination of **a commercial bank mobile app, WhatsApp photos of paper receipts, and a part-time accountant visiting once or twice a week**.

Across the three pilot businesses modeled in PS-11:
- They conducted **13,359 bank transactions** over 18 months across three major Indian commercial banks with completely disparate, cryptic narration formats.
- They issued **6,438 sales invoices and insurance claims** and received **643 purchase bills**.
- They spent **~198 hours per month on manual finance administration** (~89 hours at the distributor alone).
- **Nine times in 18 months**, owners had to inject personal capital—totaling **₹46.0 Lakh**—usually with only 24 to 48 hours of warning, to prevent cheque bounces or overdraft credit limit breaches.
- Bookkeeper categorization was noisy and incomplete: **14.3% of transactions were never tagged**, and only **79.8%** of transactions carried the correct category.

### 1.2 The Solution: LedgerLite / SME Cash-Flow Copilot
LedgerLite provides:
1. **Explain Every Rupee:** Deterministic, rules-first reconciliation resolving TDS (Sec 194J), MDR fees, clubbed payments, and cheque returns.
2. **Eliminate 90+ Hours of Manual Work:** A 4-tier triage system (`AUTO`, `SUGGEST`, `ASK`, `NO_DOC`) auto-accepting matches with 100% precision.
3. **Warn Before Shortfalls, 90 Days Ahead:** Honest bottom-up Monte Carlo cash forecasting. On the historical replay it warned 11 days before the 1 Oct 2025 credit-limit breach, but only 3 days before the 16 Oct one (the target is 7 or more).
4. **Solve "False Insolvency":** Split-plane synthesis bridging formal bank overdrafts with physical counter drawer cash (*Galla*) and informal trade credit (*Khata Udhar*).
5. **Plain-Language Answers:** Sourced answers in English with fail-closed boundary guardrails. In Hindi mode, a summary line is built from the same computed numbers (`src/copilot/hindi.py`); full Hindi answers are still to come.

---

## 2. The Three SME Archetypes

The project models three distinct business archetypes facing unique operational, tax, and liquidity challenges:

| Dimension | SME-1: Kaveri Distributors | SME-2: SmileArc Dental Clinic | SME-3: Northlight Design Studio |
| :--- | :--- | :--- | :--- |
| **Location & Legal Form** | Pune, Maharashtra · Sole Proprietorship | Bengaluru, Karnataka · Partnership (2 partners) | New Delhi · LLP (11 staff + freelancers) |
| **Industry & Model** | FMCG wholesale food/goods distribution | Multi-chair dental healthcare clinic | B2B creative design & digital agency |
| **Customer Base & Terms** | ~110 kirana stores; 15-day formal credit | 20–35 walk-in patients/day; 10% insured | 12 monthly retainers + project clients |
| **Turnover & Margins** | High volume, thin ~13% gross margins | High gross margin, high capex / chair lease | Service fees, high gross margin, high payroll |
| **Banking Setup** | Current Account with **₹25 Lakh Cash Credit (CC)** limit | Commercial Current Account (positive float) | Current Account (positive float, lumpy) |
| **Primary Inflow Channels** | Cash handed to salesmen, UPI, NEFT, Cheques | Card POS swipes (MDR net), UPI QR, TPA insurance | NEFT, RTGS, IMPS (large corporate transfers) |
| **Statutory GST Status** | GST registered (charges 5%, 12%, 18% GST) | **GST Exempt** (Healthcare services exempt) | GST registered (charges 18% GST on services) |
| **TDS Nuances** | Nil TDS on sales; subject to TCS thresholds | TPAs deduct 10% TDS under Sec 194J on claims | Clients deduct **10% TDS under Sec 194J** |
| **Key Operational Pain** | Pre-Diwali working capital crunch; salesman cash deposits covering 15 shops in 1 bank credit | Card fees deducted before settlement; TPAs settle 30–75 days late in batches with disallowances | "Profitable on paper, broke on the 28th"; clients pay 30–60 days late; TDS makes bills look unpaid |

---

## 3. Dataset Deep-Dive & Data Pack Architecture

The codebase expects data files in `data/` (configured via `COPILOT_DATA` in `src/copilot/config.py`):

```
ps11-copilot/data/
├── PS-11_bank_statements.xlsx             # 13,371 bank rows across 3 banks + taxonomy + answer key
├── PS-11_invoices_and_reconciliation.xlsx   # 6,438 invoices/claims, 643 bills, 470 collections, truth key
└── PS-11_copilot_evaluation.xlsx          # 67 Q&A gold answers, monthly cash actuals, admin log
```
*(Note: Qualitative interview transcripts and the formal problem guide reside in `../ps11-research/PS-11 SME Cash-Flow Copilot/Data/`).*

### 3.1 Worksheets & Schemas

#### 1. `PS-11_bank_statements.xlsx`
- `bank_transactions` (13,371 rows raw $\to$ 13,359 unique after removing 12 clinic duplicates):
  - `txn_id` (e.g., `TXN-1000001`): Primary key.
  - `business_id`: `SME-1`, `SME-2`, or `SME-3`.
  - `bank_account`: Account number / bank descriptor.
  - `txn_date`: Transaction timestamp.
  - `narration`: Raw string from bank statement.
  - `channel`: `UPI`, `NEFT`, `RTGS`, `IMPS`, `POS_SETTLEMENT`, `CHQ`, `CASH`, `CHARGES`.
  - `debit_inr`, `credit_inr`, `balance_inr`: Transaction debits, credits, and running balance.
  - `category_bookkeeper`: The noisy human bookkeeper's historical assignment.
- `category_labels` (13,359 rows): The ground-truth answer key containing `true_category`, `is_transfer`, `is_recurring`, and `counterparty_name`.
- `category_taxonomy`: Canonical 28 categories (e.g., `Sales receipt — customer`, `Supplier payment`, `Salary`, `GST payment`, `TDS deposited`, `Owner drawings`, `Capital infusion`, `Card machine fees (MDR)`).
- `businesses`: Metadata including sanctioned credit limits (`credit_limit_inr`), proprietor names, and GSTINs.

#### 2. `PS-11_invoices_and_reconciliation.xlsx`
- `sales_invoices` (6,438 rows):
  - Customer invoices (SME-1, SME-3) and patient TPA insurance claims (SME-2).
  - Key columns: `invoice_no`, `business_id`, `customer_name`, `invoice_date`, `due_date`, `taxable_value`, `cgst`, `sgst`, `igst`, `invoice_total`, `amount_received`, `status_as_of_30sep2026`, `last_payment_date`, `tds_applicable`, `tds_deducted_by_customer`, `disallowed_amount`.
- `purchase_bills` (643 rows):
  - Vendor bills for wholesale goods, dental consumables, rent, software licenses.
  - Key columns: `bill_no`, `business_id`, `supplier_name`, `bill_date`, `due_date`, `taxable_value`, `bill_total`, `tds_deducted_by_us`, `paid_date`, `payment_status`.
- `daily_collections` (470 rows):
  - Clinic daily front-desk takings sheet tracking `card_net_settled`, `upi_amount`, and `cash_collected`.
- `reconciliation_truth` (13,789 rows):
  - Gold standard linking bank transactions to invoices, bills, or daily collections.
  - Specifies `true_rule` (`EXACT`, `CLUBBED`, `DAILY_UPI`, `MDR_NET`, `TPA_BATCH`, `ROUND_OFF`, `ON_ACCOUNT`, `BOUNCED`), `doc_ids`, `true_tier`, and rupee breakdown.
- `parties` (144 rows): Trade partners, registered addresses, GSTINs, and default credit periods.

#### 3. `PS-11_copilot_evaluation.xlsx`
- `owner_questions` (67 rows):
  - Real-world questions spanning 10 functional categories (`T1` to `T10`) with gold answers, source citations, language variants, and boundary flags.
- `monthly_cash_actuals` (54 rows):
  - Monthly inflow, outflow, and net cash actuals across all 3 SMEs from April 2025 through September 2026 (including the frozen Jul–Sep 2026 holdout).
- `admin_time_log` (1,170 rows):
  - Weekly time tracking data recording hours spent reconciling banks, following up with debtors, and preparing tax data.

---

### 3.2 The Five Critical Data Traps
1. **The 12 Clinic Duplicates:** In `bank_transactions`, 12 clinic transactions are duplicated verbatim. `src/copilot/load.py` uses `drop_duplicates("txn_id", keep="first")` to ensure exact balance continuity.
2. **70-Character Clinic Narration Truncation:** Clinic bank statements truncate narrations at 70 characters, cutting off trailing reference numbers and patient/payer names.
3. **Opening Receivables:** Invoices dated before 1 April 2025 represent opening balances from prior periods. If settled before the bank statement start date, their remaining balance is set to zero in `src/copilot/match/engine.py`.
4. **Bookkeeper Noise:** `category_bookkeeper` is noisy (79.8% accurate, 14.3% blank). **Never evaluate models against `category_bookkeeper`; always score against `category_labels.true_category`**.
5. **Frozen July–September 2026 Holdout:** The three months from 1 July 2026 to 30 September 2026 are an inviolable evaluation holdout. **No model, feature, categorizer, or summary may train on or inspect data dated >= 1 July 2026**. All forecasting code must use `as_of(pack, cutoff)`.

---

## 4. Step-by-Step Developer Quickstart

### Step 1: Environment Setup
Ensure Python 3.13 is installed:
```bash
cd /Users/ishaanwadhwa/Projects/ps11-copilot

# Create virtual environment
python3.13 -m venv .venv
source .venv/bin/activate

# Install package in editable mode with development dependencies
pip install -e ".[dev]"
```

### Step 2: Environment Configuration
Create or verify `.env` in the project root:
```ini
COPILOT_DATA=/Users/ishaanwadhwa/Projects/ps11-copilot/data
COPILOT_PUBLIC=0
COPILOT_OWNER_PIN=0000
GEMINI_API_KEY=your_gemini_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### Step 3: Run the Automated Test Suite
Run the full automated test suite (479 tests):
```bash
.venv/bin/python -m pytest -q
```
*Expected Output:* `479 passed in ~2m45s` (16 Nov 2026 working tree)

To check Hindi number parity only:
```bash
.venv/bin/python -m pytest -q tests/test_hindi_summary.py
```

To run specific test modules during development:
- Run Challenger M3 Gate Tests: `.venv/bin/python -m pytest tests/test_challenger_m3.py`
- Run Sovereign Vault Crypto & DB Tests: `.venv/bin/python -m pytest tests/test_vault.py`
- Run Tally XML & CA Pack Tests: `.venv/bin/python -m pytest tests/test_tally.py`
- Run Decision 60 Matcher Tests: `.venv/bin/python -m pytest tests/test_matcher_d60.py`

### Step 4: Run the Benchmark Scoring Script
Score the reconciliation engine and bottom-up 90-day forecast against ground truth:
```bash
.venv/bin/python scripts/score.py
```
*Outputs generated:*
- Reconciliation AUTO precision (100.0%) and straight-through rate (68.1%).
- 90-Day forecast holdout pooled MAPE (13.48% vs 18.19% naive baseline).
- Advance warning lead time (11-day advance warning on historical CC limit breaches).
- The Ten Worst Cases table identifying ambiguous clubbed payments for review.

### Step 5: Test the Boundary Safety Router
To evaluate the boundary classifier:
```bash
# Keyword rule baseline on development set (exits 1 due to strict release gate):
.venv/bin/python scripts/score_router.py

# Model-assisted router evaluation:
.venv/bin/python scripts/score_router.py --use-llm

# QA Lead held-out evaluation gate (when TSV is provided):
.venv/bin/python scripts/score_router.py --heldout path/to/heldout.tsv
```

### Step 6: Launch the Streamlit Operating App
Run the interactive application:
```bash
.venv/bin/streamlit run app/streamlit_app.py
```
Access the application at `http://localhost:8501`.  
*(Set `COPILOT_PUBLIC=1` to run in public read-only mode without mutation controls).*

---

## 5. User Guide: The 8 Interactive Pages & Workflows

The application provides an intuitive sidebar navigation supporting three distinct user personas: **Owner** (full access), **Counter staff** (salesman collection slips & till counts), and **Accountant (CA)** (formal tax books only).

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CASH COPILOT NAVIGATION                         │
├───────────────────┬────────────────────────────────────────────────────┤
│ 1. Overview       │ True Solvency Engine, Bank vs Cash, Runway Alert   │
│ 2. Cash Book      │ Sovereign Vault: Drawer Balancing, OCR, CA Exports │
│ 3. Forecast       │ 90-Day Cash Trajectory, Monte Carlo Fan, Warnings  │
│ 4. Review         │ 4-Tier Reconciliation (AUTO, SUGGEST, ASK, NO_DOC) │
│ 5. Receivables    │ Aging Buckets, DSO, Section 18 WhatsApp Legal Shield│
│ 6. Ask Copilot    │ Conversational Q&A (EN/HI), Boundary Guardrails   │
│ 7. Data Quality   │ Continuity Checks, Answer Key Scores, Benchmarks   │
│ 8. Setup Guide    │ 3-Step Onboarding Wizard, Live Statement & Tally XML│
└───────────────────┴────────────────────────────────────────────────────┘
```

### Page 1: Overview (The True Solvency Dashboard)
- **Problem Solved:** Traditional software reports an owner with a −₹23.3 Lakh bank balance (against a ₹25 Lakh limit) as nearly insolvent. In reality, they may have ₹4.5 Lakh in counter cash and ₹6.8 Lakh in recoverable informal credit.
- **Key Display Tiles:**
  - **Net Bank Headroom:** Available bank buffer before hitting credit limit or zero.
  - **Counted Galla Cash:** Physical currency verified in the drawer till.
  - **Expected Khata Recovery:** Informal credit discounted by a user-calibrated haircut $\alpha = 0.85$.
  - **True Cash Runway:** Unified operational liquidity = $(\text{Bank Headroom}) + (\text{Galla Cash}) + (\alpha \times \text{Khata}) - (30\text{-Day Formal Commitments})$.
- **Visual Alert:** Banner highlighting **"False Insolvency"** when bank balances appear distressed but total physical cash reserves safely cover upcoming commitments.

### Page 2: Cash Book (The Sovereign Cash Vault & CA Export)
- **Domain-Adaptive Cash Drawer Cockpit:**
  - Clinic: *"Front Desk & Till Cash Balancing Cockpit"*
  - Distributor: *"Godown Cash Drawer Balancing Cockpit"*
  - Agency: *"Cash Drawer Balancing Cockpit"*
- **5-Variable Drawer Balancing:**
  - Enter: *Opening Cash*, *Cash In*, *Cash Out (Petty Expenses)*, *Cash Banked*, and *Counted Cash*.
  - Formula: $\text{Expected Cash} = \text{Opening} + \text{In} - \text{Out} - \text{Banked}$.
  - Computes **Galla Drift** ($\text{Counted} - \text{Expected}$) and flags a green "Balanced" badge if within ₹50 till tolerance.
- **Salesman Collection Slips ("Parchi") with Multimodal OCR:**
  - Upload photos of handwritten collection slips.
  - The Gemini 3.5 Flash Vision pipeline sanitizes PII and extracts retailer name, amount, payment mode, salesman name, and slip number, automatically matching against bank cash deposits.
- **CA Export Center (Download Section 1):**
  - Download TallyPrime XML Receipt Vouchers (`tally_receipts_{biz}.xml`).
  - Download 6-Sheet openpyxl CA Reconciliation Pack (`ca_reconciliation_{biz}.xlsx`).

### Page 3: Forecast (90-Day Cash Trajectory & Shortfall Warnings)
- **Monte Carlo Fan Chart:** 1,000 simulated daily trajectories plotting P10 (conservative), P50 (expected), and P90 (optimistic) balances.
- **Credit Limit Breach Detection:** Detects when borrowing touches the sanctioned limit up to 11 days in advance.
- **Actionable Swing Items:** Identifies the top 2–3 movable levers (e.g., chasing Laxmi Super Mart's ₹7.82L overdue invoice or delaying non-statutory vendor bills) that eliminate the projected dip.

### Page 4: Review (Smart Reconciliation & CA Export)
- **The 4-Tier Smart Triage:**
  1. **AUTO (Green):** 100% precision. Satisfies Decision 60 (known payer, single qualifying rule, amount under ₹1 Lakh materiality ceiling). Automatically posted without human clicks.
  2. **SUGGEST (Amber):** High probability match (e.g., small round-off, clubbed invoices, or unverified payer). The accountant clicks **"Accept"** with 1 click.
  3. **ASK (Blue):** Unresolved lines (e.g., personal-name UPI "Siddharth Pawar" or unlinked cash deposit). Prompts the owner: *"Who paid this?"* Once answered, the handle memory remembers that UPI ID forever.
  4. **NO_DOC (Gray):** Legitimate bank movements without customer bills (e.g., partner drawings, owner capital injections, bank interest charges).
- **CA Export Center (Download Section 2):** Quick-download buttons for Tally XML and CA Excel packs.

### Page 5: Receivables & Collections (Section 18 Limitation Act Legal Shield)
- **Aging & DSO:** Breaks down debtors by age (0–30, 31–60, 61–90, 90+ days) and DSO.
- **Section 18 Limitation Act Legal Shield:**
  - Under Indian law, a commercial debt expires and becomes legally unrecoverable after 3 years (36 months).
  - For debts approaching 30+ months (`c_days >= 900`), the copilot prepares a courteous bilingual WhatsApp reminder via client-side `wa.me` links.
  - When the customer confirms their balance on WhatsApp, that written electronic statement constitutes a valid **Section 18 Acknowledgment**, resetting the 3-year legal limitation clock back to zero without litigation.

### Page 6: Ask Copilot (Conversational AI)
- Plain-language Q&A with sources. Answers are written in English.
- **Hindi mode:** a "सरल समझ" summary line under each answer, built by `hindi_summary()` from the answer's own `numbers`, with Indian grouping (`#,##,##0`). It can't show a figure the English answer doesn't. Boundary questions (loan, send) get a referral with no advice. Questions it can't ground get no Hindi line.
- Strict fail-closed boundary enforcement: refuses loan recommendations, investment advice, or tax filing commands, providing clean facts.
- **History:** before commit `84eb6cc` (16 Nov 2026), these Hindi lines were fixed text chosen by keyword. The top debtor and ₹7,82,910 were typed in, and the Hindi loan line told the owner they didn't need a loan. Don't reintroduce typed-in Hindi strings.

### Page 7: Data Quality (Integrity & Benchmarks)
- **Continuity Checks:** Live verification that bank running balances tie without breaks.
- **Reconciliation Scores:** Decision 60 accuracy breakdown across the fleet.
- **Holdout Benchmarks:** Out-of-sample backtest scores against naive baseline.

### Page 8: Setup Guide (Interactive 3-Step Onboarding Wizard)
- **Step 1: Consent:** Clear explanation of what is read vs what is never done under RBI Account Aggregator guidelines.
- **Step 2: Check Your Books:** Integrity report on bank lines and duplicates, plus an **interactive file uploader** supporting real bank statements (CSV/XLSX) and TallyPrime XML.
- **Step 3: Key Numbers:** Confirmation of sanctioned credit limits, monthly payroll dates, and cash floor buffer.

---

## 6. Technical Architecture & Subsystem Deep-Dive

### 6.1 Subsystem A: The Split-Plane Architecture (ADR-001, ADR-004)
- **Implementation:** `src/copilot/vault/`
- **The Split:**
  - **Public Plane:** Formal bank statements, GST invoices, and purchase bills. Shared with the Chartered Accountant and bank lenders.
  - **Sovereign Vault Plane:** SQLite database stored locally on the owner's device, encrypted with AES-256-GCM via PBKDF2-HMAC-SHA256 (100,000 iterations). Protected by a 4-digit PIN (default `0000`). Never synced to cloud servers.
  - **RAM-Only Solvency Synthesis:** `compute_total_solvency()` dynamically calculates unified liquidity in volatile RAM without persisting combined records.
  - **Role-Based State Gating:** If a non-owner logs in, `render_partial_view_notice()` displays: *"Formal books only. The owner's cash memo is not included in this view."* Switching roles automatically triggers `vault.lock()`.

### 6.2 Subsystem B: Rules-First Reconciliation Cascade & Decision 60 (ADR-002)
- **Implementation:** `src/copilot/match/engine.py`
- **The 7-Stage Cascade:**
  1. *Cheque Bounce Reversal:* Credit matched to earlier deposit followed by debit within **2-day bounce window** reverses match and reopens bills (`match/engine.py#L226-L235`).
  2. *Owner Capital Infusion:* Detected via owner name norming or keyword "CAPITAL" $\to$ `NO_DOC` tier.
  3. *Clinic POS / Daily UPI:* Matched directly against daily collections sheet net of card MDR interchange fees.
  4. *Exact Invoice Match:* Bank credit equals net invoice total (after 10% TDS deduction where applicable).
  5. *Round-Off Tolerance:* Difference $\le \text{₹100}$ treated as round-off discount.
  6. *Subset-Sum Combination Search:* NP-complete branch-and-bound solver searching combinations of open customer invoices up to batch limit with a **uniqueness test** (`find_subsets()`).
  7. *On-Account Part Payment:* Unmatched receipts applied to oldest invoice as part payment $\to$ `SUGGEST` tier.
- **Decision 60 (D60) Strict Qualification:**
  - Auto-accepting a match without human verification requires a statistical upper error bound $\le 1.0\%$.
  - Only three rule classes qualify: `("SME-1", "EXACT")`, `("SME-2", "DAILY_UPI")`, and `("SME-2", "MDR_NET")`.
  - Materiality ceiling: Any transaction $\ge \text{₹1,00,000}$ is automatically demoted to `SUGGEST`.
  - **Weekly Audit Sampling:** A background ledger audits a 2% random sample of AUTO matches. If an error is detected, the entire rule class is immediately suspended to `SUGGEST`.

### 6.3 Subsystem C: Honest Bottom-Up 90-Day Cash Forecast (D48, D71)
- **Implementation:** `src/copilot/forecast/engine.py`
- **Anti-Leakage Snapshot:**
  - `as_of(pack, cutoff)` freezes the world at `cutoff`: post-cutoff payments are stripped, invoices are set back to unpaid, and categorizers are re-trained only on pre-cutoff bank lines.
- **Simulation Mechanics:**
  - *Inflows:* Fits empirical payment delay distributions per customer. Samples arrival dates using age-conditioned survival draws ($P(\text{delay} \mid \text{delay} > \text{current\_age})$). Applies statutory 10% TDS and historical TPA disallowance rates.
  - *Outflows:* Derives base outflow schedule from pre-cutoff 3-month medians for payroll (scheduled on day 1), statutory GST (20th), TDS (7th), owner drawings, recurring payees (CV $\le 0.25$), and open vendor bills. If statutory dates fall on Sunday, they roll to Monday.
  - *Monte Carlo Fan:* Runs 1,000 simulation paths yielding P10, P50, and P90 daily balance trajectories.

### 6.4 Subsystem D: Statutory Legal Shield & Anti-Spoliation (ADR-003)
- **Implementation:** `src/copilot/vault/guardrails.py` and `src/copilot/vault/chase.py`
- **Cash Transaction Limit Interceptors:**
  - Income-tax Act, 2025 Section 186 (formerly 269ST): Single-day cash receipts $\ge \text{₹2,00,000}$ are flagged as `BLOCKED`.
  - Section 36(4)–(6) (formerly 40A(3)): Business cash expenses $> \text{₹10,000}$ per day ($> \text{₹35,000}$ for transport) flagged as `WARNING`.
  - Section 185/188 (formerly 269SS/T): Cash loans $\ge \text{₹20,000}$ flagged.
  - SFT Form 165 tracking: Proximity to annual bank cash deposit reporting thresholds factually displayed.
- **Anti-Spoliation Compliance (BNS §241 & CGST Act §132(1)(j)):**
  - Absolute ban on "panic wipes" or stealth concealment buttons.
- **BSA Section 63 Digital Evidence Hashing:**
  - On-device SHA-256 hashing of customer balance acknowledgments for court-admissible debt recovery.

### 6.5 Subsystem E: Fail-Closed Boundary Router (D63, D70)
- **Implementation:** `src/copilot/boundary.py`
- **9 Boundary Intents:** `TAX_ACTION`, `DELAY_PAYMENT`, `PRIVACY`, `SEND`, `JUDGE_PERSON`, `INVEST`, `TAX_ADVICE`, `LOAN`, `MOVE_OR_EDIT`.
- **Fail-Closed Behavior:** Evaluates deterministic regex patterns before calling any LLM. Queries lacking definitive fact classification fail closed to `NEEDS_CHIPS`, providing structured question chips.

### 6.6 Subsystem F: Multimodal Intelligence & PII Sanitization
- **Implementation:** `src/copilot/gemini.py` and `src/copilot/masking.py`
- **Voice Transcription:** Transcribes vernacular audio recordings (Hindi, English, Hinglish) via `gemini-3.5-flash`.
- **Collection Slip ("Parchi") OCR:** Extracts handwritten shop names, amounts, payment modes, and dates, transliterating Devanagari script to Latin English to match customer ledgers.
- **Client-Side Image Masking:** Sanitizes personal identifiers from slip images prior to processing.

### 6.7 Subsystem G: CA TallyPrime XML & OpenPyXL Pack Generator
- **Implementation:** `src/copilot/tally.py`
- **TallyPrime XML:** Pure TDL XML receipt vouchers compatible with TallyPrime 1.0–7.1 and Tally.ERP 9 with deterministic UUID5 generation.
- **6-Sheet OpenPyXL Workbook:** Generates institutional-grade Excel workbook with sheets:
  1. `Reconciliation_Summary`
  2. `Matched_Receipts_AUTO`
  3. `Suggested_Matches`
  4. `Unmatched_Bank_Credits`
  5. `Open_Invoices_Aging`
  6. `Salesman_Collection_Slips`

---

## 7. Verified Performance Benchmarks

### 7.1 Reconciliation Performance (Strict Decision 60 Bar)
Evaluated across **11,224 bank statement lines** against `reconciliation_truth`:

| Metric | SME-1 (Distributor) | SME-2 (Clinic) | SME-3 (Agency) | **Overall Fleet** |
| :--- | :--- | :--- | :--- | :--- |
| **Total Lines in Key** | 3,893 | 6,886 | 445 | **11,224** |
| **AUTO Qualified Lines** | 1,175 | 6,462 | 2 | **7,639** |
| **AUTO Precision** | **100.0%** | **100.0%** | **100.0%** | **100.0%** |
| **Straight-Through Rate** | 30.2% | 93.8% | 0.4% | **68.1%** |
| **Suggestions Accepted Accuracy** | 72.5% | 53.9% | 70.3% | **68.7%** |
| **Explained if Suggestions Accepted** | 62.7% | 96.8% | 69.4% | **83.9%** |
| **False Positives Outside Key** | **0** | **0** | **0** | **0** |

*Note on SME-3 straight-through rate:* Under Decision 60, `SME-3 EXACT_BILL` carried an empirical upper error bound of 1.95% (> 1.0% limit) and was demoted to `SUGGEST`. This deliberate design choice guarantees the 100.0% precision standard.

*Kill line:* 83.9% "explained if suggestions accepted" sits under the team's 85% reconciliation kill line (D31) and the brief's 95% target. The owner and accountant question queues are the planned fix.

### 7.1b Categorisation (28 classes, against `category_labels.true_category`)
Re-run 16 Nov 2026 with `Categoriser` and `score_categories`:

| Set | Lines | By line | By rupee |
| :--- | :--- | :--- | :--- |
| All lines | 13,359 | 99.8% | 98.7% |
| Holdout (Jul–Sep 2026) | 2,240 | **99.6%** | **98.8%** |

Baselines: bookkeeper 79.8%; channel-only rule 87.9%; simple lookup 96.6% by line, 89.4% by rupee. Target: 97% or better.

### 7.2 90-Day Cash Forecast Holdout Benchmark
Evaluated strictly on the frozen **July–September 2026 holdout**:
- **Holdout Pooled MAPE:** **13.48%** (outperforms naive 3-month rolling baseline of **18.19%**).
- **Agency Inflows MAPE:** **10.81%** (significantly beats naive baseline of **46.21%**).
- **Historical Backtest Pooled MAPE:** **15.80%** (across 10 monthly cutoff periods from June 2025 to March 2026).
  - SME-1 Backtest MAPE: 18.85%
  - SME-2 Backtest MAPE: 9.96%
  - SME-3 Backtest MAPE: 18.59%
- **Shortfall Warning Lead Time:** On the replay, the 1 October 2025 CC limit breach was flagged **11 days** ahead and the 16 October 2025 breach only **3 days** ahead (target: 7 or more). The holdout had **0 false alarms**, but also no floor crossings, so that result is weak evidence.

**Say these out loud when quoting the forecast:**
- The 13.48% misses the brief's 10% or lower target.
- The paired bootstrap gain over naive is +4.68 points with a 95% CI of [−4.78, +14.65]. It crosses zero, so "beats the baseline" is **not yet statistically established**.
- P10–P90 ranges covered only **22.2%** of holdout outcomes against a nominal 80%, and the outflow ranges collapse to a single value (P10 = P90). The ranges are too narrow until recalibrated.
- Never quote the old **3.15%** MAPE. It came from monthly totals hard-coded close to the holdout actuals and was removed in the Nov corrections (`CORRECTIONS-REPORT.md`).

### 7.3 Automated Test Suite
- **Test Results:** 479 passed in about 2m45s (`tests/`, 16 Nov 2026 working tree), including 10 Hindi parity tests in `tests/test_hindi_summary.py`.

---

## 8. Critical Audit of Prior Assumptions & Traps

| Item | Claim in Prior Reports | Actual Code / Ground Reality | Impact & Guidance for Team |
| :--- | :--- | :--- | :--- |
| **Cheque Bounce Window** | "5-day bounce window" | `config.py#L133`: `BOUNCE_WINDOW_DAYS = 2`. `engine.py#L228`: `days <= config.BOUNCE_WINDOW_DAYS`. | All bank statement cheque bounces reverse within **2 days**, strictly aligning with ground-truth rule R7. |
| **Data Directory Files** | 5 files in `ps11-copilot/data/` including `.docx` files | Exactly **3 `.xlsx` files** in `data/`. The `.docx` files reside in `../ps11-research/`. | Do not write tests or code expecting `.docx` files in `data/`. |
| **Page Navigation & CA Export** | Standalone "CA Export" page 7 | `streamlit_app.py` registers 8 pages: `overview`, `cash`, `forecast`, `review`, `recv`, `ask`, `quality`, and `setup`. | CA export is directly integrated into **Cash book** (Page 2) and **Review** (Page 4). Page 7 is **Data quality**; Page 8 is **Setup guide**. |
| **Boundary Scoring Script** | "Run `.venv/bin/python scripts/score_router.py`" | Exits with `sys.exit(1)` when run without flags. | Keyword rules intentionally fail closed to `NEEDS_CHIPS` on ambiguous sentences; release gate requires `--use-llm` or `--heldout`. |
| **Statutory Shield** | Merely mentioned WhatsApp links | Implements ITA 2025 Sec 186/36(4)/185/188, BNS §241 anti-spoliation, and BSA §63 digital evidence hashing. | Protects the owner from severe tax penalties and criminal exposure. |
| **Role Locks on Switch** | UI switch was purely visual | Switching role away from Owner immediately calls `vault.lock()` in memory. | Confidential cash drawer data cannot be viewed by counter staff or accountants. |
| **Hindi Number Parity** | "Exact number parity across English, Hindi and Hinglish" | Until `84eb6cc` (16 Nov), Hindi lines were keyword-picked fixed text (typed-in debtor name and ₹7,82,910; the loan line gave advice). Now built from `Answer.numbers`; only the summary line is Hindi. | Claim "Hindi summary with identical numbers", not full Hindi answers. Redeploy the live app before demoing Hindi. |
| **Live URL** | One-page note: `life-inbox.medevolv.in` | That host is the Life Inbox project and did not respond on 16 Nov. `sme-cashflow.medevolv.in` serves the PS-11 app. | Use only `sme-cashflow.medevolv.in` in decks and submissions. |
| **Forecast Score** | Deck v5: 3.15% MAPE | Came from hard-coded monthly totals; the honest score is 13.48% (bootstrap CI crosses zero; P10–P90 coverage 22.2%). | Quote 13.48% with its caveats (§7.2). |
| **Warning Lead Time** | "11 days in advance" | 11 days for the 1 Oct 2025 breach; 3 days for 16 Oct 2025. | Quote both events. |
| **Legal Claims (Pages 2 and 5; §6.4)** | Section 18 WhatsApp acknowledgment resets limitation; ITA 2025 section numbers; BSA §63 hashing makes records court-admissible | Not reviewed by a CA or lawyer. The 12 Nov audit recommended removing the SFT-headroom and similar vault features as tax advice. | Don't present these as legal facts until a CA or lawyer confirms them. Describe the features, not their legal effect. |

---

## 9. Open Questions & Product Roadmap

1. **Distributor Cash Deposit Breakdown (Salesman Parchi):**
   - 149 distributor cash deposits route to `ASK` in baseline data because a single cash deposit aggregates collections across 10–15 retail stores.
   - *Seam:* Mobile camera Parchi OCR in `src/copilot/gemini.py` extracts slips to match deposits. Next step: offline-first mobile sync.
2. **Clinic TPA Claim Remittance Advices:**
   - Insurance batch settlements cover up to 13 claims with arbitrary deductions.
   - *Next step:* Intake parser for TPA remittance PDFs (MediBuddy, Vidal, Star Health).
3. **Boundary Router Independent Evaluation Gate (D70):**
   - Release gate verification of Claude/Gemini ensemble on QA's held-out boundary phrase test set.
4. **Spatial 3D Cashflow Topography (Next.js & Three.js):**
   - Architectural blueprint in `docs/blueprints/nextjs-threejs-cashflow-copilot.md` explores a 3D visual topography for cash flows.
5. **Full Hindi Answers (T9):**
   - Only the summary line is Hindi today. Next: render the whole answer in Hindi from the same `numbers`, and extend `tests/test_hindi_summary.py` to it.
6. **Forecast Range Calibration:**
   - P10–P90 coverage is 22.2% against a nominal 80%. Widen the ranges (real outflow variance instead of a fixed schedule) and re-score coverage on the backtests.
7. **Model Cost per Business:**
   - Not measured yet. Run the 67 owner questions, log tokens, and report the cost per business per month. The pitch deck's unit-economics table depends on it.

---

## 10. Market Sizing & the Final Pitch Deck

### 10.1 Market (bottom-up, priced per GSTIN)
Source: GSTN, *9 Years of GST* report (taxpayers as on 30 Jun 2026, p.3; turnover slabs for FY 2025–26, p.13). Revenue per GSTIN is an assumption: Starter ₹749 and Growth ₹1,499 a month, a 50/50 mix = ₹1,124 a month = **₹13,488 a year**.

| Level | Definition | GSTINs | × ₹13,488 a year |
| :--- | :--- | :--- | :--- |
| TAM | All normal GST taxpayers | 1,48,70,332 | ₹20,057 crore |
| SAM | ₹1–20 crore turnover (FY 2025–26 return filers) | 33,91,979 | **₹4,575 crore** |
| SOM | 1% of SAM in 3 years (assumption) | 33,920 | ₹45.8 crore |

- The pilot businesses' bank inflows (about ₹8.2 crore, ₹3.2 crore and ₹1.8 crore a year) sit inside the SAM band.
- **Caveats:**
  - Slab counts cover return filers only (1.13 crore in all).
  - One business can hold several GSTINs.
  - Healthcare is mostly GST-exempt, so many clinics have no GSTIN, which makes the SAM conservative for clinics.
- Prices come from a practitioner pass (SuperMe, 5 Nov) and are opinions; Stage 3 asks testers which tier they'd choose.

### 10.2 The pitch deck
- **Plan:** `ps11-research/final-pitch/PITCH-DECK-PLAN.md`. It has the 12 titles, the slide specs, the number ledger and the claims not to make.
- **Deck:** a 12-slide Slides artifact owned by the team lead. Ask them to share it. It exports to PowerPoint for Google Slides (Share › Export › PowerPoint, then File › Import slides).
- **Still open in the deck:**
  - model cost per business;
  - team names and one proof each;
  - the 3-year model;
  - the number of pilot businesses in the ask.
- **Before presenting:** re-run `scripts/score.py` and check every figure against the plan's number ledger.
