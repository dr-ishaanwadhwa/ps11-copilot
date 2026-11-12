# UI/UX Pro Max Audit Report: PS-11 SME Cash-Flow Copilot

**Framework**: UI/UX Pro Max (Design Intelligence, 120 UX Guidelines, Typographic Modular Scales, Semantic Color Tokens, Information Density, Cognitive Load & Indian SME Usability)  
**Target Repository**: `/Users/ishaanwadhwa/Projects/ps11-copilot`  
**Target UI Implementation**: `app/streamlit_app.py` and supporting modules (`.streamlit/config.toml`, `src/copilot/vault/notice.py`, `src/copilot/vault/models.py`)  
**Audit Execution Date**: 2026-11-12  
**Auditor**: Teamwork Worker (Framework 2 Specialist)  
**Status**: Complete Standalone Audit  

---

## 1. Executive Summary & UI/UX Maturity Score

The **ps11-copilot** application (SME Cash-Flow Copilot MVP v1, Team 11 / LedgerLite pilot) is a local-first, read-only financial copilot designed to solve cash-flow anxiety for Indian Small and Medium Enterprise (SME) owner-operators. Guided by the core product principle—*"It explains every rupee between your bank and your books, and never acts without you"*—the software bridges formal banking records (bank statements, Cash Credit limits, GST invoices) and informal on-device commerce (physical drawer *Galla*, informal daily cash *Rokad*, and pending credit *Khata*).

Applying the **UI/UX Pro Max** framework—evaluating the interface across the 120 canonical UX guidelines, modular typographic hierarchy, semantic color token systems, cognitive ergonomics for non-finance operators, and Indian vernacular usability—yields an overall **UI/UX Maturity Score of 71 / 100**.

### 1.1 UI/UX Maturity Scorecard

```
┌─────────────────────────────────────────────────────────────┬───────────┬────────┐
│ Dimension                                                   │ Weight    │ Score  │
├─────────────────────────────────────────────────────────────┼───────────┼────────┤
│ 1. Indian SME Cognitive Fit & Persona Usability             │ 20%       │  76%   │
│ 2. Typographic Scale & Modular Hierarchy                    │ 15%       │  62%   │
│ 3. Semantic Color Tokens & Boundary Contrast (WCAG 1.4.11)  │ 15%       │  64%   │
│ 4. Information Density & Visual Scannability                │ 15%       │  78%   │
│ 5. Interaction Ergonomics & Touch Targets (WCAG 2.5.8)      │ 15%       │  60%   │
│ 6. Human-in-the-Loop Trust & Boundary Safety                │ 20%       │  82%   │
├─────────────────────────────────────────────────────────────┼───────────┼────────┤
│ OVERALL UI/UX MATURITY SCORE                                │ 100%      │ 71/100 │
└─────────────────────────────────────────────────────────────┴───────────┴────────┘
```

### 1.2 Core Strengths
1. **Uncompromising Human-in-the-Loop Trust Architecture**: The app strictly enforces read-only invariants. WhatsApp payment chasing operates strictly through client-side `wa.me` draft links; zero messages are transmitted automatically, protecting SME owners from client relationship damage (`app/streamlit_app.py:981, 1283`).
2. **Salesman Protection Shield & Statutory Limitation Safety**: The receivables interface prevents double-calling customers who already paid field salesmen in cash (`app/streamlit_app.py:1260–1269`), and automatically flags accounts older than 30 months under Section 18 of the Limitation Act, 1963 to prevent legal time-barring (`app/streamlit_app.py:1274`).
3. **High-Contrast Text Hierarchy**: Body text (`#17191C` on `#FFFFFF`) achieves an exceptional 17.61:1 contrast ratio, easily surpassing WCAG AAA requirements (`app/streamlit_app.py:60, 75`).
4. **Bilingual Foundation & Audio Briefing**: The inclusion of a client-side Web Speech audio briefing (`app/streamlit_app.py:435–492`) and voice Q&A transcription (`app/streamlit_app.py:1335–1344`) addresses vernacular operators who prefer listening over reading complex financial screens.

### 1.3 Critical Defects & Vulnerabilities
1. **Critical Silent Security/Transparency Defect**: `render_partial_view_notice()` returns a string that is completely discarded in 7 separate locations (`app/streamlit_app.py:590, 894, 1009, 1120, 1213, 1322, 1428`). Restricted users (Counter Staff or CA without cash book sharing) never see the required warning banner that informal cash is excluded.
2. **Widespread WCAG 1.4.11 Component Boundary Contrast Failures**: Input borders (`#DCDCD6`, 1.38:1), sidebar selects (`#E2E2DC`, 1.17:1), expander borders (1.30:1), and divider lines (1.18:1) fall dramatically below the required 3.0:1 non-text contrast threshold. In brightly lit Indian retail counters or godowns, boundaries disappear.
3. **Severe Touch Target Violations**: Audio briefing buttons (26px height, line 451), print sheet triggers (26px height, line 549), sidebar navigation items (40px height with 2px gap, lines 91–94), and secondary link buttons (40px, line 109) violate the Apple HIG 44×44pt and Material Design 48×48dp touch target standards.
4. **Active Focus Suppression in Data Grids**: Line 1167 explicitly disables AgGrid keyboard cell focus (`.ag-cell-focus: { border-color: transparent !important; }`), violating WCAG 2.4.7 (Focus Visible) and leaving keyboard-only operators blind in the review queue.
5. **Typographic Scale Fragmentation & Sub-12px Text**: Over 18 arbitrary font sizes exist without a modular scale, including sub-11px demo badges (`.cc-demo` at 0.68rem / 10.88px, line 163), violating core readability guidelines.
6. **Iframe Font Dropping**: The Web Speech audio briefing (line 445) and Daily Recovery Print dialog (line 536) execute inside isolated iframes without importing `IBM Plex Sans Devanagari`, causing broken glyph fallbacks for Hindi text on Windows, Linux, and Android devices.
7. **Disjointed Horizontal Arithmetic Wrapping**: The 5-tile horizontal math equation (`[Bank] + [+ Galla] + [+ Khata] + [− Dues] = [= Buffer]`) uses `repeat(auto-fit, minmax(170px, 1fr))` (line 147), which breaks into random rows of 3+2 or 2+2+1 on tablets (500px–900px), severing the mathematical mental model.

---

## 2. Indian SME Owner-Operator Cognitive Fit & Persona Deep-Dive

Indian SME owner-operators operate under distinct environmental, commercial, and linguistic pressures. Unlike corporate enterprise users, they manage businesses while fielding vendor calls, supervising godown labor, and handling counter retail customers.

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                SME OPERATIONAL SPECTRUM                                 │
├────────────────────────────┬─────────────────────────────┬──────────────────────────────┤
│ Prakash Kale               │ Dr. Kavya Hegde             │ Rohan Malhotra               │
│ FMCG Distributor (Pune)    │ Clinic Partner (Bengaluru)  │ Creative Agency (Delhi)      │
│ • High volume, low margin  │ • Appointment & walk-ins    │ • High ticket, B2B retainers │
│ • Clubbed cash deposits    │ • Bundled daily POS/UPI     │ • 194J TDS deductions        │
│ • ₹25L CC overdraft limit  │ • TPA insurance delays      │ • Salary week liquidity dips │
│ • Vernacular (Marathi/Hindi)│ • "One trusted number"      │ • Agency loss anxiety        │
└────────────────────────────┴─────────────────────────────┴──────────────────────────────┘
```

### 2.1 Persona Fit Evaluation

#### 1. Prakash Kale — High-Volume FMCG Distributor (Kaveri Distributors, Pune)
- **Operational Reality**: 16 staff, ~110 kirana stores on 15-day credit, 5 supplier advance payments, ₹25 Lakh Cash Credit (CC) limit. Over 42% of customer UPI payments come from personal PhonePe/Google Pay names rather than shop names. Salesmen collect physical cash in godown rounds.
- **Cognitive Strengths in UI**:
  - The **Daily Recovery Sheet** (`daily_print_dialog()`, lines 494–579) provides a printable physical route sheet with shop names, outstanding amounts, oldest invoice days, and collection sign-off lines.
  - The **Salesman Protection Shield** (`app/streamlit_app.py:1260–1269`) is an exceptional cognitive fit: if salesman Ramesh collected ₹15,000 from Laxmi Kirana today, the receivables list explicitly notes *"Salesman Ramesh K. collected ₹15,000 on 30 Sep; not banked yet. Do not call."* This prevents Prakash from harassing a loyal retailer who already paid.
  - The **Income Tax SFT Cash Deposit Tracker** (`app/streamlit_app.py:987–1001`) factually displays YTD cash deposits against Rule 237 thresholds with a preparation checklist, without alarmist or evasion countdowns.
- **Cognitive Friction Points**:
  - **Iframe Printing Drop**: When Prakash clicks "Print Sheet / PDF" on a godown Windows desktop or Android tablet, the print dialog iframe drops Devanagari font rendering, printing illegible or fallback fonts for shop notes.
  - **Touch Ergonomics on the Move**: Prakash checks the dashboard on his phone while walking the warehouse floor. The Audio Briefing "Listen" button is only 26px high (line 451), leading to frustrating missed taps.
  - **Loan Fatigue**: Every financial app tries to sell loans. While the copilot's IntentRouter safely refuses to sell loans (`src/copilot/boundary.py:34`), the overview banner could explicitly reassure: *"100% Advisory-Free: No loan promotions, ever."*

#### 2. Dr. Kavya Hegde — Healthcare Provider (SmileArc Dental Clinic, Bengaluru)
- **Operational Reality**: 2 partners, 9 staff, 20–35 patients daily. Bank credits never match patient bills directly; receipts arrive as bundled evening UPI batches or swipe machine credits net of 1.5%–2% MDR fees. TPAs (CareLink, Claimwise) delay claims for 30–75 days and deduct unexplained disallowances.
- **Cognitive Strengths in UI**:
  - The **Galla Day-Close Modal** (`day_close_dialog()`, lines 821–836) captures opening cash, takings, expenses/hamali, and banked cash in under 60 seconds, calculating till drift with a tolerant $\pm$ ₹50 threshold.
  - The **Decision 60 Auto-Reconciliation** (`src/copilot/match/engine.py:34`) correctly auto-matches MDR net credits and daily bundled UPI takings without asking Kavya to manually verify predictable card fee deductions.
- **Cognitive Friction Points**:
  - **Mental Arithmetic Fatigue**: Kavya wants to know one thing before signing staff payroll cheques on the 28th: *"Do I have enough real cash after dental lab bills and equipment EMIs?"*
  - The horizontal equation displays 5 separate cards, forcing Kavya to visually scan across 5 numbers and perform mental addition/subtraction.
  - **The Discarded Partial View Notice**: When Kavya’s clinic accountant logs in under the "Accountant (CA)" role without cash book sharing enabled, `render_partial_view_notice()` is silently discarded (line 590). The accountant sees a bank balance of ₹2,10,000 and assumes the clinic is struggling, unaware that ₹1,85,000 in patient cash is safely sitting in the chairside locker.

#### 3. Rohan Malhotra — Creative Agency Partner (Northlight Design Studio, New Delhi)
- **Operational Reality**: 11 staff, 22 corporate clients. Billed invoices carry 18% GST, but enterprise clients withhold 10% TDS under Section 194J on the pre-GST base. Accounting software falsely flags the 10% TDS deduction as "overdue", prompting embarrassing automated reminder emails.
- **Cognitive Strengths in UI**:
  - **TDS-Aware Receivables**: Line 1295 notes *"TDS-short invoices count as paid in full, with TDS receivable recorded separately (brief T3)."* Rohan is never embarrassed by automated emails demanding TDS deductions from enterprise CFOs.
  - **Strict WhatsApp Draft-Only Paradigm**: Lines 981 and 1283 enforce `wa.me/?text=...`. Nothing is transmitted automatically. Rohan retains absolute agency over client communications.
- **Cognitive Friction Points**:
  - **Review Queue Dead-End**: In the Review Queue (`app/streamlit_app.py:1202`), the "Accept" button is permanently disabled with tooltip *"Posting comes in the next build; v1 is read-only."* While read-only safety is paramount, disabling the primary button without an alternative staging action (e.g., *"Mark as Verified"*, *"Export Reconciled Batch to Excel"*, or *"Add Note for CA"*) leaves Rohan feeling that the review queue is an incomplete toy.

---

### 2.2 The "One Morning Number" vs Mental Arithmetic Fatigue

A central premise of financial cockpit design is reducing cognitive fatigue. An owner-operator logging in at 8:30 AM should grasp their solvency status within **3 seconds**.

```
CURRENT STATE: 5-Tile Equation Grid (Cognitive Load: HIGH)
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Bank balance │ + │ Cash drawer  │ + │ Khata inflow │ − │ 30-day dues  │ = │ Net Buffer   │
│  −₹12.40L    │   │   ₹1.85L     │   │   ₹8.40L     │   │   ₹6.50L     │   │  −₹8.65L     │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
  (Breaks into 3+2 or 2+2+1 rows on mobile/tablet viewports; signs + and − float aimlessly)

RECOMMENDED STATE: Hierarchical Solvency Anchor (Cognitive Load: MINIMAL)
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ ☀️ TODAY'S USABLE CASH: ₹14,45,000                                 [Safe for 45 Days]  │
│ Bank Liquidity ₹12.60L (incl. ₹10L CC Headroom) + Drawer Cash ₹1.85L                    │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│ ▼ Breakdown: [Bank ₹2.60L] + [CC Headroom ₹10.00L] + [Drawer ₹1.85L] − [Dues ₹6.50L]    │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Detailed Breakdown of Current Cockpit Implementation:
1. **Hero Box (`app/streamlit_app.py:662–697`)**:
   - Accurately renders *"Cash you can use today"* (`.cc-hero`, line 692).
   - Accurately computes `total_liquid = solvency.net_bank_liquidity + solvency.galla_cash`.
   - Displays a clear status pill (`.cc-status`, lines 695–696) indicating 30-day safety.
2. **Horizontal Equation Grid (`app/streamlit_app.py:714–722`)**:
   - Renders 5 sequential tiles: Bank balance $\to$ Cash in drawer $\to$ Khata expected $\to$ Due in 30 days $\to$ Own-cash buffer.
   - **Cognitive Flaw**: The labels include arithmetic operators (`+ Cash in drawer`, `− Due in next 30 days`, `= Your own-cash buffer`). When rendered on desktop (1200px), this sits on one line. However, the CSS grid rule (`app/streamlit_app.py:147`):
     ```css
     .cc-tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 8px; }
     ```
     forces elements to wrap dynamically. On viewports between 640px and 920px (iPad Mini, tablet in portrait, folded Android foldables), 5 cards cannot fit in one row of min 170px. The grid breaks into **Row 1 (3 cards)** and **Row 2 (2 cards)**.
   - The card `= Your own-cash buffer` drops to the second line beneath `Cash in drawer`. The mathematical continuity is broken, forcing the user to mentally reconstruct which numbers add and which subtract.
3. **The $\alpha$ Khata Haircut Slider (`app/streamlit_app.py:629–635`)**:
   - The slider allows the owner to vary informal khata recovery expectations from 50% to 100% (default 85%).
   - While mathematically elegant, asking a busy distributor to tune a statistical haircut parameter ($\alpha$) creates cognitive friction.
   - **UX Guideline Fix**: Anchor the slider with human business terminology: *"Conservative (60%)"*, *"Expected (85%)"*, *"Optimistic (95%)"* rather than a raw percentage slider.

---

### 2.3 Vernacular Usability & Devanagari Typography Audit

The application features an English / Hindi toggle (`app/streamlit_app.py:1619–1622`). Evaluating the vernacular implementation against localization standards reveals notable strengths alongside severe rendering defects.

#### 1. Devanagari Font Dropping in Iframes (Critical Visual Bug)
- In `app/streamlit_app.py:69–74`, the main app stylesheet imports Google Fonts:
  ```css
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Devanagari:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
  ```
- However, two critical components are rendered using Streamlit's `components.html()` which creates an isolated sandboxed `<iframe>`:
  1. `render_audio_briefing()` (`app/streamlit_app.py:445`):
     ```html
     <div style="...font-family:'IBM Plex Sans', -apple-system, sans-serif;...">
     ```
  2. `daily_print_dialog()` (`app/streamlit_app.py:536`):
     ```html
     <div id="printSheet" style="...font-family:'IBM Plex Sans', -apple-system, sans-serif;...">
     ```
- **Consequence**: The iframe does **not** inherit parent document CSS `@import`. Because `IBM Plex Sans Devanagari` is omitted from the iframe's `font-family` declaration and no `<link>` tag is included, Devanagari characters inside these two components rely entirely on operating system fallback fonts (e.g., *Mangal* on older Windows or *Nirmala UI* on Windows 10/11, *Noto Sans Devanagari* on Android).
- On systems without high-quality Devanagari fallbacks, Hindi conjuncts (*युक्तियां*, *ऋण*, *बकाया*) render with disjointed matras and broken kerning.

#### 2. Translation Coverage Disparity
The application exhibits an uneven localization implementation:
- **Fully Localized Pages**:
  - `page_overview()` (~85% localized via `t()`).
  - `page_cash_book()` (~80% localized).
  - `page_receivables()` (~75% localized).
  - `page_ask()` (~80% localized, includes dedicated Hindi summary cards lines 1370–1388).
- **Zero / Poor Localization Pages**:
  - `page_forecast()`: Monthly breakdown table headers (`Month`, `Expected inflows`, `Committed outflows`, `Net cash flow`, `Lowest daily balance`, `Closing balance`, lines 1087–1088) are 100% hardcoded in English. The holdout accuracy metrics (lines 1094–1110) are 100% English.
  - `page_review()`: AgGrid column headers (`Date`, `Amount`, `Type`, `Rule`, `Bank narration`, lines 1149–1153) are 100% English. The right-hand detail card (`Why it's here`, `Suggested documents`, line 1191) is 100% English.
  - `page_quality()`: 100% hardcoded in English (lines 1426, 1431, 1448, 1453).
  - `page_setup()`: 90% hardcoded in English (lines 1466, 1475, 1481, 1485, 1503, 1553, 1570).

---

## 3. Typographic Hierarchy & Modular Scale System

### 3.1 Typographic Scale Fragmentation Audit

Professional design systems mandate a strict mathematical type scale (typically 6 to 8 standardized steps). Inspection of `app/streamlit_app.py` reveals an uncontrolled proliferation of **over 18 arbitrary font sizes**:

```
CURRENT TYPE FRAGMENTATION (18+ Distinct Sizes Detected):
├── 0.68rem  (10.88px) -> .cc-demo (Line 163) [VIOLATION: Sub-12px minimum]
├── 11px     (11.00px) -> Print Sheet footer/meta (Lines 544, 571) [VIOLATION: Sub-12px]
├── 0.75rem  (12.00px) -> .cc-tag, .cc-colhead, .cc-table th, .cc-steps .n (Lines 164, 186, 198, 218)
├── 12px     (12.00px) -> Audio player meta, Print sheet table (Lines 449, 554)
├── 0.76rem  (12.16px) -> .cc-note, .cc-tile .l, .cc-status .d, .cc-legend (Lines 145, 149, 172, 213)
├── 0.78rem  (12.48px) -> .cc-narr, Ask source list (Lines 211, 1391)
├── 13px     (13.00px) -> Audio title, AgGrid row text (Lines 448, 1164)
├── 0.82rem  (13.12px) -> .cc-muted, .cc-row-detail, .cc-figs dt, .cc-steps .lbl (Lines 144, 184, 193, 219)
├── 0.84rem  (13.44px) -> .cc-list.sm li (Line 223)
├── 0.85rem  (13.60px) -> .stLinkButton a p, .cc-sub, .cc-callout .d, .cc-table td, .cc-onboard (Lines 110, 138, 178, 197, 227)
├── 0.875rem (14.00px) -> .cc-label (Line 141)
├── 0.90rem  (14.40px) -> Sidebar link text, .cc-status .t, .cc-list li (Lines 93, 171, 222)
├── 0.92rem  (14.72px) -> Review queue note text (Line 1192)
├── 0.95rem  (15.20px) -> Setup guide subtitles (Lines 1477, 1505, 1555)
├── 15px     (15.00px) -> .cc-brand (Line 136)
├── 1.00rem  (16.00px) -> .cc-h2 (Line 140)
├── 1.02rem  (16.32px) -> Ask Copilot answer body (Line 1368)
├── 1.10rem  (17.60px) -> Setup key numbers dd (Line 1565)
├── 1.12rem  (17.92px) -> .cc-tile .v (Line 150)
├── 1.30rem  (20.80px) -> .cc-tile.big .v (Line 152)
├── 1.35rem  (21.60px) -> .cc-title (Line 137)
├── 1.60rem  (25.60px) -> Setup headings, YTD cash deposit hero (Lines 994, 1475)
├── 1.70rem  (27.20px) -> .cc-figs dd (Line 194)
├── 1.75rem  (28.00px) -> Review queue selected amount (Line 1187)
└── clamp(2.1rem, 4.5vw, 2.75rem) (33.6px–44px) -> .cc-hero (Line 142)
```

#### Key Typographic Flaws:
1. **Sub-12px Font Size Violations**:
   - `ui-ux-pro-max` §6 explicitly states: **"Text < 12px body is prohibited"**.
   - `.cc-demo` (`app/streamlit_app.py:163`) sets `font-size: 0.68rem` (10.88px).
   - `daily_print_dialog()` (`app/streamlit_app.py:544, 571`) hardcodes `font-size: 11px`.
   - On low-DPI laptops or budget mobile devices, sub-12px text exhibits illegible pixel clumping.
2. **Micro-Step Redundancy**:
   - There is no discernible perceptual difference between `0.75rem` (12px), `0.76rem` (12.16px), and `0.78rem` (12.48px).
   - Similarly, `0.82rem` (13.12px), `0.84rem` (13.44px), `0.85rem` (13.60px), and `0.875rem` (14px) represent 4 distinct sizes within a 0.88px band. This creates visual noise and renders CSS maintenance chaotic.

---

### 3.2 Recommended Modular Typographic Scale

To establish harmonic visual cadence, ps11-copilot should adopt the **Minor Third (1.200)** modular scale, based on a canonical 16px root:

| Step Token | Size (rem / px) | Line Height | Weight | Intended Purpose & Mapping | Current Code Line Replacements |
|---|---|---|---|---|---|
| `--text-xs` | `0.75rem` (12px) | 1.40 | 500 | Metadata, tags, captions, table headers | Replaces 0.68rem, 0.75rem, 0.76rem, 0.78rem, 11px |
| `--text-sm` | `0.875rem` (14px) | 1.45 | 400 / 500 | Secondary copy, row details, table cells, form labels | Replaces 0.82rem, 0.84rem, 0.85rem, 0.875rem, 0.90rem, 13px |
| `--text-base` | `1.000rem` (16px) | 1.50 | 400 / 500 | Body text, input controls, primary navigation links | Replaces 0.92rem, 0.95rem, 1.00rem, 1.02rem |
| `--text-md` | `1.200rem` (19.2px) | 1.35 | 600 | Card titles, metric tile values, subheadings | Replaces 1.10rem, 1.12rem, 1.30rem |
| `--text-lg` | `1.440rem` (23px) | 1.30 | 600 | Page subheaders, modal headers, section titles | Replaces 1.35rem |
| `--text-xl` | `1.728rem` (27.6px) | 1.25 | 600 | Secondary hero metrics, review amount hero | Replaces 1.60rem, 1.70rem, 1.75rem |
| `--text-2xl` | `2.074rem` (33.2px) | 1.15 | 700 | Primary overview hero metric (`.cc-hero`) | Replaces clamp(2.1rem, 4.5vw, 2.75rem) |

---

### 3.3 Vertical Rhythm, Line-Height & Letter-Spacing
- **Line-Height Compression**:
  - Line 142 sets `.cc-hero { line-height: 1.1; }`. While acceptable for large display numerals, `.cc-title` sets `line-height: 1.3` (line 137), causing titles with Hindi ascenders/descenders (*इ* matras and *ऊ* matras) to collide when wrapped.
  - Hindi text requires a minimum `line-height: 1.5` to accommodate upper and lower vowel markers without vertical clipping.
- **Letter-Spacing (Tracking)**:
  - Lines 136, 137, 142, and 194 set negative letter spacing: `letter-spacing: -0.01em` to `-0.025em`.
  - While negative tracking sharpens English headline typography in fonts like *Inter* or *IBM Plex Sans*, **negative tracking on Devanagari is an acute anti-pattern**. It compresses shirorekha (the top continuous line) and creates conjunct collisions.
  - **Remedy**: Apply negative tracking strictly via `:lang(en)` or when rendering numbers (`.cc-num`), and keep `letter-spacing: normal` for Devanagari glyphs.

---

### 3.4 Monospace Tabular Numerals for Financial Data
- **High-Scoring Implementation**: The codebase makes extensive use of `font-variant-numeric: tabular-nums` (lines 143, 146, 150, 185, 191, 195, 197) and imports `IBM Plex Mono` (line 69).
- Currency amounts in `.cc-amount`, `.cc-hero`, and tables align predictably on decimal positions without visual jitter when values update.
- **Omission**: AgGrid data rows (`app/streamlit_app.py:1164`) do not inherit `font-variant-numeric: tabular-nums` in `custom_css`, leading to proportional digit rendering inside the transaction grid. Adding `"font-variant-numeric": "tabular-nums"` to `.ag-row` resolves this.

---

## 4. Semantic Color Tokens & Palette Architecture

### 4.1 Current State: Token Scarcity vs Raw Hex Sprawl

Lines 60–65 of `app/streamlit_app.py` define only five top-level color constants:
```python
INK = "#17191C"
MUTED = "#545A63"
SUBTLE = "#646A72"
ACCENT = "#24509A"
NEG = "#A8261D"
```

Because these 5 tokens do not define background tints, border levels, hover interactions, or warning states, the rest of the stylesheet resorts to an uncontrolled sprawl of **over 25 hardcoded hex values**:

```
UNTOKENIZED RAW HEX SPRAWL IN CSS:
├── Accent Tints:    #EDF1F8, #D9E2F2, #1C407D, #2F4F86, #DCE4F0
├── Warning Tints:   #FBF1DF, #7A4A00, #8A5300, #4A3200
├── Success Tints:   #EAF4EE, #1A6E45, #24543B, #F0FDF4, #BBF7D0, #166534
├── Danger Tints:    #FBECEA, #A8261D
├── Surface Grays:   #FFFFFF, #F3F3F0, #F7F7F4, #F4F4F1, #F1F1EC, #FAFAF8, #E9E9E5
└── Border Grays:    #E5E5E0, #E2E2DC, #DCDCD6, #ECECE8, #C2C2BB, #D4D4CE, #CCCCCC
```

---

### 4.2 Component & Boundary Contrast Deficiencies (WCAG 1.4.11 Analysis)

WCAG 2.1 Success Criterion 1.4.11 (Non-Text Contrast) requires a minimum contrast ratio of **3.0:1** against adjacent backgrounds for:
1. User interface component boundaries (inputs, selects, buttons).
2. Visual indicators of component state (focus, hover, selection).
3. Graphical objects carrying information (charts, dividers indicating layout structure).

#### Contrast Measurement Audit:
Using the WCAG relative luminance formula ($L = 0.2126 R + 0.7152 G + 0.0722 B$):

```
┌───────────────────────────────────────┬───────────┬────────────┬──────────┬──────────────┐
│ UI Element                            │ Hex Color │ Background │ Measured │ WCAG 1.4.11  │
├───────────────────────────────────────┼───────────┼────────────┼──────────┼──────────────┤
│ Text Input Border                     │ #DCDCD6   │ #FFFFFF    │  1.38:1  │ FAIL (<3.0)  │
│ Sidebar Selectbox Border              │ #E2E2DC   │ #F3F3F0    │  1.17:1  │ FAIL (<3.0)  │
│ Ask Search Proxy Border               │ #DCDCD6   │ #FFFFFF    │  1.38:1  │ FAIL (<3.0)  │
│ Ask Search Proxy Hover Border         │ #C2C2BB   │ #FFFFFF    │  1.79:1  │ FAIL (<3.0)  │
│ Expander Container Border             │ #E2E2DC   │ #FFFFFF    │  1.30:1  │ FAIL (<3.0)  │
│ Row List Horizontal Divider           │ #ECECE8   │ #FFFFFF    │  1.18:1  │ FAIL (<3.0)  │
│ Stepper Inactive Bar                  │ #E2E2DC   │ #FFFFFF    │  1.30:1  │ FAIL (<3.0)  │
│ AgGrid Outer Container Border         │ #E2E2DC   │ #FFFFFF    │  1.30:1  │ FAIL (<3.0)  │
│ Setup Onboarding Callout Border       │ #D9E2F2   │ #F4F6FB    │  1.21:1  │ FAIL (<3.0)  │
│ Demo Badge Border                     │ #D4D4CE   │ #FFFFFF    │  1.49:1  │ FAIL (<3.0)  │
│ Print Sheet Receipt Dashed Line       │ #CCCCCC   │ #FFFFFF    │  1.61:1  │ FAIL (<3.0)  │
│ Forecast Uncertainty Band (Area Fill) │ #DCE4F0   │ #FFFFFF    │  1.28:1  │ FAIL (<3.0)  │
├───────────────────────────────────────┼───────────┼────────────┼──────────┼──────────────┤
│ Primary Button Text (ACCENT)          │ #24509A   │ #FFFFFF    │  7.81:1  │ PASS (>=4.5) │
│ Stepper Active Progress Bar           │ #24509A   │ #FFFFFF    │  7.81:1  │ PASS (>=3.0) │
│ Forecast CC Limit Rule (NEG)          │ #A8261D   │ #FFFFFF    │  7.09:1  │ PASS (>=3.0) │
└───────────────────────────────────────┴───────────┴────────────┴──────────┴──────────────┘
```

**Real-World Impact**: Under bright warehouse fluorescent lighting or direct daylight on an SME shop counter, users cannot see where an input field starts and ends. Input fields blend into the white canvas.

---

### 4.3 Proposed Production-Grade Semantic Design Token Architecture

Following `ui-ux-pro-max` §6, the ad-hoc hex values should be replaced with a formalized semantic CSS custom property system:

```css
:root {
  /* Surfaces */
  --color-surface-canvas:      #FFFFFF;
  --color-surface-subtle:      #F7F7F4;
  --color-surface-sidebar:     #F3F3F0;
  --color-surface-panel:       #F4F4F1;
  --color-surface-hover:       #E9E9E5;

  /* Typography / Content */
  --color-text-primary:        #17191C; /* Contrast 17.6:1 */
  --color-text-secondary:      #4A5059; /* Contrast 7.5:1 (replaces #545A63) */
  --color-text-subtle:         #60666E; /* Contrast 5.8:1 (replaces #646A72) */
  --color-text-inverse:        #FFFFFF;

  /* Borders & Dividers (WCAG 1.4.11 Compliant >= 3.0:1) */
  --color-border-subtle:       #D0D0CA; /* 1.55:1 (decorative dividers only) */
  --color-border-default:      #92928A; /* 3.12:1 (form inputs, buttons, cards) */
  --color-border-strong:       #666660; /* 5.51:1 (hover and active boundaries) */
  --color-border-focus:        #24509A; /* 7.81:1 (keyboard focus ring) */

  /* Semantic Feedback Tones */
  --color-accent:              #24509A;
  --color-accent-subtle:       #EDF1F8;
  --color-accent-text:         #1C407D;

  --color-success:             #166534;
  --color-success-subtle:      #DCFCE7;
  --color-success-text:        #14532D;

  --color-warning:             #854D0E;
  --color-warning-subtle:      #FEF9C3;
  --color-warning-text:        #713F12;

  --color-danger:              #991B1B;
  --color-danger-subtle:       #FEE2E2;
  --color-danger-text:         #7F1D1D;
}
```

---

## 5. Information Density & Visual Scannability

### 5.1 Overview Page Layout & Density Balance

The Overview page (`app/streamlit_app.py:582–809`) is the primary landing cockpit. It consolidates six distinct modules:
1. Header & Business Switcher.
2. 30-sec Daily Audio Briefing.
3. Solvency Cockpit (Hero Metric + Status Pill + 5-Tile Equation + Khata Slider).
4. "Needs You Today" Operational Action Rows.
5. 90-Day Forecast Mini-Chart.
6. Data Quality & Balance Tie DL Panel.

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ OVERVIEW PAGE SCANNING FLOW                                                             │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│ [Header] BIZ_NAME · As-of Date · Role Pill · Language Toggle                            │
│ ┌─────────────────────────────────────────────────────────────────────────────────────┐ │
│ │ [Audio Briefing] 🎙️ 30-sec Audio Briefing (Play Button: 26px!)                      │ │
│ └─────────────────────────────────────────────────────────────────────────────────────┘ │
│ ┌──────────────────────────────────────────────────────────┬──────────────────────────┐ │
│ │ [Solvency Hero] ₹14.45L Cash you can use today           │ [Status] 30 Days Safe    │ │
│ └──────────────────────────────────────────────────────────┴──────────────────────────┘ │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
│ │ Bank balance │+│ Cash drawer  │+│ Khata inflow │−│ 30-day dues  │=│ Net Buffer   │   │
│ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘   │
│ ┌─────────────────────────────────────────────────────────────────────────────────────┐ │
│ │ [Needs You Today] 4 Operational Action Rows (Salaries, Late Debtor, Review, Slips) │ │
│ └─────────────────────────────────────────────────────────────────────────────────────┘ │
│ ┌───────────────────────────────────────────────┬─────────────────────────────────────┐ │
│ │ [90-Day Forecast Chart]                       │ [Data Quality Panel]                │ │
│ │ Altair Area + P50 Line (150px height)         │ Lines read, breaks, documents       │ │
│ └───────────────────────────────────────────────┴─────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Scannability Findings:
- **Visual Weight Imbalance**: The 30-second audio briefing banner (`render_audio_briefing`, line 445) is visually styled like an informational callout (`background: #F4F6FB; border: 1px solid #D9E2F2;`). It sits directly above the Solvency Hero, competing for the primary optical entry point.
- **Action Row Hierarchy**: The "Needs You Today" section (lines 725–772) is exceptionally well-structured. Each row features a bold title, contextual status badge, concise explanation, and a right-aligned action trigger button.
- **Dual-Pane Bottom Balance**: The 2:1 column split between the 90-Day Forecast (left) and Data Quality panel (right) provides effective balance, pairing forward projection with historical verification.

---

### 5.2 Review Queue Master-Detail Grid & The Focus Suppression Anti-Pattern

The Review Queue (`app/streamlit_app.py:1114–1205`) pairs an interactive AgGrid table (left, 63% width) with a contextual evidence card (right, 37% width).

#### Critical Accessibility Flaw: Focus Outline Elimination
In lines 1160–1168, `custom_css` for AgGrid is defined:
```python
custom_css={
    ".ag-root-wrapper": {"border": "1px solid #E2E2DC !important", "border-radius": "10px !important"},
    ".ag-header": {"background-color": "#FAFAF8 !important", "border-bottom-color": "#E2E2DC !important"},
    ".ag-header-cell-text": {"font-weight": "500 !important", "color": "#646A72 !important"},
    ".ag-row": {"border-color": "#ECECE8 !important", "font-size": "13px !important"},
    ".ag-row-selected": {"background-color": "#EDF1F8 !important"},
    ".ag-row-hover": {"background-color": "#F7F7F4 !important"},
    ".ag-cell-focus": {"border-color": "transparent !important"},  # <-- CRITICAL DEFECT
}
```

- **WCAG Violation**: Line 1167 sets `.ag-cell-focus { border-color: transparent !important; }`.
- Under **WCAG 2.4.7 (Focus Visible)** and **WCAG 2.4.11 (Focus Appearance)**, any keyboard-focusable component must render a visible indicator with at least 3.0:1 contrast against adjacent colors.
- When an accountant uses Tab or Arrow keys to navigate transactions, **there is zero indication of which cell or row is currently focused**.
- **Remedy**: Replace `transparent !important` with a high-contrast focus token:
  ```python
  ".ag-cell-focus": {"border": "2px solid #24509A !important", "outline": "none !important"},
  ```

---

### 5.3 Receivables Aging, Salesman Protection Shield & Limitation Act Alerts

The Receivables view (`app/streamlit_app.py:1208–1296`) contains high-value domain-specific workflow innovations:

1. **Salesman Protection Shield (`app/streamlit_app.py:1258–1269`)**:
   - Matches recent unbanked salesman collection slips against open accounts.
   - If a salesman collected ₹15,000 from a retailer today, the UI suppresses the chase action and renders:
     ```html
     <div class="cc-row-detail" style="color:#1A6E45;display:flex;gap:6px">
       <svg>...</svg>Salesman Ramesh K. collected ₹15,000 on 30 Sep; not banked yet. Do not call.
     </div>
     ```
   - **Cognitive Assessment**: Superb UX. Eliminates double-chasing and protects distributor-retailer trust.
2. **Section 18 Limitation Act Warning (`app/streamlit_app.py:1273–1275`)**:
   - When an informal debt or customer account remains open $\ge 900$ days (30 months), the UI appends a red warning badge: `30+ months (Sec 18)`.
   - Accompanied by a pre-composed WhatsApp draft requesting written/electronic acknowledgment, which legally resets the 3-year limitation clock under Indian law.
3. **Touch Target Violation on WhatsApp Action**:
   - The WhatsApp draft button (`c4.link_button(...)`, line 1283) uses standard `.stLinkButton > a` which is styled in line 109 with `min-height: 40px`.
   - On mobile screens, 40px falls below the 44px touch target threshold, risking mis-taps when trying to trigger WhatsApp drafts.

---

### 5.4 AI Design Slop & Iconography Discipline

Evaluating the interface against `ui-ux-pro-max` §4 (Style Selection: **"No Emoji as Structural Icons — use vector SVGs (Lucide/Heroicons)"**):

The codebase violates this rule in multiple primary controls:
- **Audio Briefing Header (`line 447`)**: Uses raw emoji `🎙️`.
- **Audio Briefing Transport Controls (`lines 452, 486`)**: Uses raw emojis `▶️` and `⏹️`.
- **CSV Download Button (`line 514`)**: Uses raw emoji `📥 Download CSV`.
- **Print Sheet Triggers (`lines 550, 1236`)**: Uses raw emoji `🖨️ Print Sheet / PDF`.
- **Setup Onboarding Banner (`line 610`)**: Uses raw emoji `✨ Quick Setup`.
- **Vision OCR Upload Button (`line 843`)**: Uses raw emoji `📷 Scan handwritten slip photo`.
- **Voice Q&A Expander (`line 1335`)**: Uses raw emoji `🎙️ Speak your question`.
- **Ask Copilot Summary Cards (`lines 1375–1385`)**: Uses raw emoji `💡 <b>सरल समझ:</b>`.
- **Tally XML Ingest Expander (`line 1518`)**: Uses raw emoji `📁 Upload Live Statement`.

**Why Emoji Icons Degrade Perceived Quality**:
- Emojis render inconsistently across operating systems: a colorful cartoon microphone on iOS looks entirely different from a flat symbol on Android or a monochrome glyph on Windows.
- Emojis cannot inherit CSS currentColor or design tokens.
- Emojis convey an informal, hobbyist prototype feel rather than an institutional financial tool.
- **Remedy**: Replace all 9 emojis with the existing `svg()` helper (`app/streamlit_app.py:241–253`) using curated vector paths.

---

## 6. Human-in-the-Loop & Trust Design Architecture

### 6.1 The "Never Acts Without You" Principle & Zero-Unilateral-Action Enclosure

The defining invariant of ps11-copilot is its read-only safety boundary:
```
           ┌───────────────────────────────────────────────┐
           │        SOVEREIGN READ-ONLY ENCLOSURE          │
           ├───────────────────────┬───────────────────────┤
           │      WHAT IT DOES     │   WHAT IT NEVER DOES  │
           │  • Reads statements   │  ❌ Move money        │
           │  • Explains numbers   │  ❌ Debit accounts    │
           │  • Flags shortfalls   │  ❌ Auto-send emails  │
           │  • Composes drafts    │  ❌ Auto-send WA      │
           │  • Cites source rows  │  ❌ Sell debt/loans   │
           └───────────────────────┴───────────────────────┘
```

The UI communicates this guarantee across multiple layers:
1. **Sidebar Security Badge (`line 1623`)**: Displays a persistent lock icon with text: *"Read-only. Never moves money, edits records or sends anything."*
2. **Onboarding Privacy Contract (`lines 1481–1491`)**: Explicitly pairs a *"What we read"* checklist (eye icon) with a *"What we never do"* checklist (slashed circle icon).
3. **WhatsApp Deep-Linking (`lines 981, 1283`)**: Uses `wa.me/?text=...` URI schemes. The app never integrates a headless WhatsApp Business API that sends messages behind the user's back.

---

### 6.2 Critical Silent UI Bug: Discarded `render_partial_view_notice()`

A forensic investigation of the codebase uncovered a severe UI rendering defect:

#### 1. Code Definition in `src/copilot/vault/notice.py`:
```python
# src/copilot/vault/notice.py (lines 5-7)
def render_partial_view_notice() -> str:
    """Return the standard notice banner text when viewing formal books without cash memo."""
    return PARTIAL_VIEW_NOTICE
```

#### 2. Invocation in `app/streamlit_app.py`:
In **7 separate locations**, whenever `showing_partial_view` evaluates to `True`:
- **Line 590** (`page_overview`):
  ```python
  if showing_partial_view:
      render_partial_view_notice()
  ```
- **Line 894** (`page_cash_book`):
  ```python
  if showing_partial_view:
      render_partial_view_notice()
  ```
- **Line 1009** (`page_forecast`):
  ```python
  if showing_partial_view:
      render_partial_view_notice()
  ```
- **Line 1120** (`page_review`):
  ```python
  if showing_partial_view:
      render_partial_view_notice()
  ```
- **Line 1213** (`page_receivables`):
  ```python
  if showing_partial_view:
      render_partial_view_notice()
  ```
- **Line 1322** (`page_ask`):
  ```python
  if showing_partial_view:
      render_partial_view_notice()
  ```
- **Line 1428** (`page_quality`):
  ```python
  if showing_partial_view:
      render_partial_view_notice()
  ```

#### 3. Root Cause & Impact:
- `render_partial_view_notice()` is a pure function that returns a Python string: `"Formal books only. The owner's cash memo is not included in this view."`
- In `app/streamlit_app.py`, the function is called as an expression statement **without capturing its return value or passing it to `st.info()`, `st.warning()`, or `H()`**.
- **Consequence**: The function executes, produces the string, and Python immediately discards it.
- **Across the entire application, the partial view notice banner is NEVER rendered to the screen.**
- When Counter Staff or an Accountant views the system, there is zero indication that informal cash is excluded. This completely undermines PRD Decision 68 and role-based privacy trust.

#### 4. Remediation:
In all 7 locations, replace `render_partial_view_notice()` with:
```python
if showing_partial_view:
    st.info(render_partial_view_notice(), icon=":material/visibility_off:")
```

---

### 6.3 Disabled State Ergonomics in Review Queue

In `app/streamlit_app.py:1202–1204`:
```python
st.button("Accept", disabled=True, use_container_width=True,
          help="Posting is wired in the next build; v1 is read-only.")
H('<div class="cc-note">Posting comes in the next build. This version is read-only.</div>')
```

- **UX Evaluation**: While protecting the read-only invariant, rendering a primary action button that is permanently disabled across every single item generates user frustration.
- Target personas (accountants and business owners) click on transactions expecting to complete a task. A disabled button signals broken functionality.
- **Recommended Ergonomic Improvement**:
  Transform the action into an active staging action that preserves the read-only contract:
  ```python
  c_act1, c_act2 = st.columns(2)
  if c_act1.button("Mark Verified", key=f"verify_{txn_id}", use_container_width=True):
      st.toast("Marked as verified in local session.", icon=":material/check:")
  if c_act2.button("Flag for CA", key=f"flag_{txn_id}", use_container_width=True):
      st.toast("Added note for Chartered Accountant.", icon=":material/edit_note:")
  ```

---

### 6.4 Grounded Q&A Explainability & Source Row Transparency

In `app/streamlit_app.py:1356–1392`:
- When an owner asks a question, the copilot routes it through `IntentRouter`.
- Factual queries display a green tag: `From your books` with checkmark icon (`app/streamlit_app.py:1358`).
- Out-of-bounds queries display: `Outside what I do` (`line 1364`).
- **Source Row Auditability**: Lines 1389–1392 render an expandable drawer:
  ```python
  if a.sources:
      with st.expander(t(f"Sources ({len(a.sources)} rows)", f"प्रमाण व स्रोत ({len(a.sources)} प्रविष्टियां)")):
          H(f'<div class="cc-mono" style="font-size:0.78rem;line-height:1.7">{esc(", ".join(a.sources[:60]))}</div>')
  ```
- **Trust Assessment**: Highly effective. The owner or accountant can immediately verify the exact bank and ledger lines that generated the answer.

---

## 7. Concrete Line-Level Remediation Guide

Below are the exact, line-level code transformations required to elevate `app/streamlit_app.py` from a 71 to a 95+ UI/UX maturity score.

### 7.1 Fix the Discarded Partial View Notice Bug (Lines 590, 894, 1009, 1120, 1213, 1322, 1428)

```python
# CURRENT CODE (Lines 590, 894, 1009, 1120, 1213, 1322, 1428):
if showing_partial_view:
    render_partial_view_notice()

# RECOMMENDED FIX:
if showing_partial_view:
    st.info(t(render_partial_view_notice(), "केवल औपचारिक बही-खाता। मालिक का रोकड़ मेमो इस दृश्य में शामिल नहीं है।"),
            icon=":material/visibility_off:")
```

---

### 7.2 Implement Semantic Design Tokens & Modular Type Scale (Lines 60–229)

```css
/* REPLACE LINES 68-75 IN app/streamlit_app.py WITH: */
:root {
  --color-canvas: #FFFFFF;
  --color-sidebar: #F3F3F0;
  --color-card: #F7F7F4;
  --color-border-default: #92928A; /* WCAG 1.4.11 compliant (3.12:1) */
  --color-border-subtle: #DCDCD6;
  --color-text-primary: #17191C;
  --color-text-secondary: #4A5059;
  --color-accent: #24509A;
  --color-focus: #24509A;

  /* Minor Third (1.200) Modular Typographic Scale */
  --font-size-xs: 0.75rem;    /* 12px */
  --font-size-sm: 0.875rem;   /* 14px */
  --font-size-base: 1.000rem; /* 16px */
  --font-size-md: 1.200rem;   /* 19.2px */
  --font-size-lg: 1.440rem;   /* 23px */
  --font-size-xl: 1.728rem;   /* 27.6px */
  --font-size-2xl: 2.074rem;  /* 33.2px */
}

/* Ensure accessible non-text boundaries */
[data-baseweb="input"], [data-baseweb="select"] > div,
.st-key-askfield [data-testid="stPageLink-NavLink"] {
  border: 1px solid var(--color-border-default) !important;
  border-radius: 8px !important;
}

/* Accessible focus ring */
button:focus-visible, [data-baseweb="input"]:focus-within {
  outline: 2px solid var(--color-focus) !important;
  outline-offset: 2px !important;
}
```

---

### 7.3 Restore AgGrid Focus Visibility (Lines 1160–1168)

```python
# CURRENT CODE (app/streamlit_app.py:1167):
".ag-cell-focus": {"border-color": "transparent !important"},

# RECOMMENDED FIX:
".ag-cell-focus": {
    "border": "2px solid #24509A !important",
    "outline": "none !important"
},
```

---

### 7.4 Fix Iframe Devanagari Font Dropping & Touch Targets (Lines 444–454, 535–552)

#### 1. Audio Briefing Component (`app/streamlit_app.py:444–454`):
```html
<!-- CURRENT (Line 445): -->
<div style="...font-family:'IBM Plex Sans', -apple-system, sans-serif;...">
<button style="...padding:6px 14px;font-size:12px;...">▶️ Listen</button>

<!-- RECOMMENDED FIX: -->
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Devanagari:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
</style>
<div style="display:flex;align-items:center;justify-content:space-between;background:#F4F6FB;border:1px solid #92928A;border-radius:8px;padding:12px 16px;font-family:'IBM Plex Sans','IBM Plex Sans Devanagari',system-ui,sans-serif;margin-bottom:12px;">
  <div style="display:flex;align-items:center;gap:12px;">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#24509A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="22"></line></svg>
    <span style="font-size:14px;font-weight:600;color:#17191C;">{title_lbl}</span>
    <span style="font-size:13px;color:#4A5059;">{sub_lbl}</span>
  </div>
  <!-- Touch Target minimum height 44px -->
  <button id="speakBtn" onclick="togglePlay()" style="min-height:44px;min-width:96px;background:#24509A;color:white;border:none;padding:0 18px;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;">
    <span id="btnTxt">{play_lbl}</span>
  </button>
</div>
```
*(Also update `components.html(html_code, height=68)` on line 491 to prevent mobile clipping).*

---

### 7.5 Responsive Solvency Cockpit Bento Reflow (Lines 147, 714–722)

```css
/* CURRENT (Line 147): */
.cc-tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 8px; }

/* RECOMMENDED FIX: */
.cc-tiles {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}
@media (max-width: 960px) {
  .cc-tiles {
    grid-template-columns: repeat(2, 1fr);
  }
  .cc-tile:last-child {
    grid-column: span 2;
  }
}
@media (max-width: 520px) {
  .cc-tiles {
    grid-template-columns: 1fr;
  }
  .cc-tile:last-child {
    grid-column: span 1;
  }
}
```

---

## 8. Prioritized Remediation Roadmap

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          PRIORITIZED REMEDIATION ROADMAP                                │
├───────────────┬───────────────────────────────────────────┬──────────────┬──────────────┤
│ Priority Tier │ Issue & Remediation Action                │ Target Files │ Effort       │
├───────────────┼───────────────────────────────────────────┼──────────────┼──────────────┤
│ P0: Blocker   │ 1. Fix discarded partial view notice      │ streamlit.py │ 15 mins      │
│               │ 2. Restore AgGrid keyboard focus border   │ streamlit.py │ 10 mins      │
│               │ 3. Add Devanagari imports to iframes      │ streamlit.py │ 20 mins      │
├───────────────┼───────────────────────────────────────────┼──────────────┼──────────────┤
│ P1: Critical  │ 4. Upgrade input borders to 3.0:1 contrast│ streamlit.py │ 30 mins      │
│               │ 5. Expand touch targets to >= 44px        │ streamlit.py │ 45 mins      │
│               │ 6. Replace emojis with vector SVGs        │ streamlit.py │ 30 mins      │
├───────────────┼───────────────────────────────────────────┼──────────────┼──────────────┤
│ P2: High      │ 7. Consolidate to 7-step Minor Third scale│ streamlit.py │ 2 hours      │
│               │ 8. Make Solvency equation bento responsive│ streamlit.py │ 1 hour       │
│               │ 9. Complete Hindi strings in Forecast/Rev │ streamlit.py │ 1.5 hours    │
├───────────────┼───────────────────────────────────────────┼──────────────┼──────────────┤
│ P3: Polish    │ 10. Replace disabled Accept with Staging  │ streamlit.py │ 45 mins      │
│               │ 11. Add accessible table header scopes    │ streamlit.py │ 30 mins      │
└───────────────┴───────────────────────────────────────────┴──────────────┴──────────────┘
```

---

## 9. Conclusion

The **ps11-copilot** front-end demonstrates exceptional domain intuition, rigorous regulatory safety, and exemplary human-in-the-loop integrity. Its dual-plane cash architecture, salesman protection shield, and read-only WhatsApp draft integration represent best-in-class product thinking for Indian SME owner-operators.

By rectifying the critical discarded notice defect, enforcing WCAG 1.4.11 boundary contrast standards, restoring keyboard focus visibility in the review grid, expanding touch targets to 44px, and harmonizing typography through a modular scale, `ps11-copilot` will establish an institutional-grade benchmark for vernacular enterprise financial software in India.
