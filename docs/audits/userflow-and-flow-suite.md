# UI/UX Audit Report: Userflow and Flow-* Suite (Framework 3)

**Target System**: `ps11-copilot` (SME Cash-Flow Copilot MVP v1, LedgerLite pilot)  
**Primary UI File**: `app/streamlit_app.py` (1,639 lines, 112 KB)  
**Supporting Modules**: `src/copilot/vault/`, `src/copilot/gemini.py`, `src/copilot/ingest.py`, `src/copilot/answers.py`, `src/copilot/boundary.py`  
**Audit Framework**: Framework 3 — `userflow` Dispatcher & the `flow-*` Suite  
**Evaluated Skills**: `flow-app-shell`, `flow-navigation`, `flow-tables`, `flow-forms`, `flow-errors`, `flow-empty-states`, `flow-ai-chat`, `flow-search`  
**Target Personas**: Prakash Kale (FMCG Distributor), Dr. Kavya Hegde (Multi-Specialty Clinic), Rohan Malhotra (Creative Agency)  
**Date**: November 2026  
**Auditor**: Teamwork UI/UX Specialist & Interaction Flow Auditor (Worker 3)

---

## 1. Executive Summary & Audit Scorecard

This audit report provides an exhaustive, line-by-line interaction architecture evaluation of the `ps11-copilot` application against the proven principles of the **Userflow & Flow-* Suite**. 

The application is built to serve Indian Small and Medium Enterprise (SME) owner-operators who operate in a dual-economy environment: formal banking systems (current accounts, sanctioned cash-credit limits, GST invoices, Tally ledgers) coexisting with high-velocity informal cash operations (counter till *Galla*, daily rokad petty cash, unformalized credit *Khata*, and field salesman collection slips).

### Core Strengths Identified
1. **Exceptional Dual-Plane Domain Grounding**: The application successfully embodies the principle *"It explains every rupee between your bank and your books, and never acts without you."* Sensitive informal cash memos remain locked inside local on-device SQLite (`VaultDB`), completely isolated from the formal accountant/GST export plane.
2. **Strict Non-Agentic Trust Boundaries (`flow-ai-chat` Rule 6)**: The product rigorously enforces read-only invariants. WhatsApp payment chasing operates exclusively via client-side `wa.me/?text=...` pre-composed drafts. No background messaging, auto-debiting, or unauthorized ledger mutation occurs.
3. **Decisive Domain-Specific Heuristics**: Inclusion of the 45-day MSMED Act aging threshold, Section 18 Limitation Act 30-month legal acknowledgment warnings, and Salesman Collection Slip Protection Shields ("Salesman Ramesh collected ₹15,000 on 30 Sep; not banked yet. Do not call") solves genuine, high-stakes operational friction for Indian distributors.

### Critical Flow Deficits & Anti-Pattern Hotspots
1. **The Silent Partial View Notice Bug (`flow-errors` / `flow-permissions`)**: On all 7 sub-views, `render_partial_view_notice()` is invoked as an isolated expression (`app/streamlit_app.py:590, 894, 1009, 1120, 1213, 1322, 1428`). Because the function returns a string without calling Streamlit display widgets, the statutory notice informing Counter Staff or Accountants that cash memos are withheld is **completely discarded and never renders on screen**.
2. **Placebo Day-Close Form (`flow-forms` Rule 1 / `flow-errors`)**: In `day_close_dialog()` (`app/streamlit_app.py:821–836`), submitting the form only sets a toast in session state and triggers a rerun. **Zero data is written to `vault`**, and all form fields are hardcoded to static test values (Opening ₹10,000, Takings ₹25,000) rather than pulling live book data.
3. **Decoy Global Search Link (`flow-app-shell` / `flow-search`)**: The "Ask about your cash..." search bar in the global header (`app/streamlit_app.py:410–412`) is styled visually as a text input, but is actually an `st.page_link`. Clicking it redirects to `PAGES["ask"]` without carrying forward focus or input context.
4. **State Amnesia & URL Disconnect (`flow-navigation` / `flow-tables`)**: Filtering the Review Queue or Receivables ledger stores selections strictly in memory. Refreshing the browser or sharing a URL resets all filters to default, wiping user context.
5. **Permanently Disabled Review Queue Action (`flow-tables` / `flow-forms`)**: The primary button in the Review Queue ("Accept", `app/streamlit_app.py:1202`) is permanently disabled (`disabled=True`), leaving the user in an operational cul-de-sac with no alternative path.
6. **False Success on Multimodal OCR Failure (`flow-errors` / `flow-forms`)**: In `collections_dialog()` (`app/streamlit_app.py:848–858`), when Gemini Vision OCR fails, the system falls back to hardcoded defaults ("Laxmi Kirana Stores", ₹15,000, "Ramesh K.") and emits a misleading `st.success("Extracted: ...")` banner.

### Quantitative Audit Scorecard

| Flow Dimension | Evaluated Skill | Total Checks | PASS | WARN | FAIL | Compliance % |
|---|---|---|---|---|---|---|
| **1. Layout Shell** | `flow-app-shell` | 14 | 9 | 3 | 2 | 64.3% |
| **2. Navigation Architecture** | `flow-navigation` | 15 | 8 | 4 | 3 | 53.3% |
| **3. Data Tables & Lists** | `flow-tables` | 16 | 10 | 3 | 3 | 62.5% |
| **4. Forms & Wizards** | `flow-forms` | 18 | 7 | 6 | 5 | 38.9% |
| **5. Error Handling & Recovery** | `flow-errors` | 15 | 5 | 5 | 5 | 33.3% |
| **6. Zero-Data & Empty States** | `flow-empty-states` | 12 | 6 | 4 | 2 | 50.0% |
| **7. AI & Conversational Flow** | `flow-ai-chat` + `flow-search` | 18 | 9 | 5 | 4 | 50.0% |
| **Total** | **Combined Suite** | **108** | **54** | **30** | **24** | **50.0%** |

---

## 2. Domain 1: Application Shell & Layout Architecture (`flow-app-shell`)

### 2.1 Pattern Alignment: Sidebar + Main Shell
`ps11-copilot` adopts the canonical **Sidebar + Main** productivity shell (`flow-app-shell` Pattern 1).
- **Sidebar Dimensions & Breakpoints**: The desktop sidebar occupies Streamlit's native width (~280px, `#F3F3F0`), styled with a 1px solid right border (`#E5E5E0`, line 89).
- **Main Block Container**: Clamped to `max-width: 1200px` with responsive padding (`2.4rem 2.5rem 4rem` on desktop, adapting to `3.5rem 1rem 3rem` at `<640px`, lines 81–86).
- **Z-Layering**: Fixed top decoration is suppressed (`[data-testid="stDecoration"] { display: none; }`, line 79), and deploy chrome is removed, delivering a clean desktop canvas.

### 2.2 Shell Friction Points & Anti-Pattern Analysis

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STREAMLIT SHELL: DESKTOP VS TABLET BREAKDOWN                                           │
├──────────────────────────┬─────────────────────────────────────────────────────────────┤
│ SIDEBAR (Fixed 280px)    │ MAIN CONTENT AREA (Clamped 1200px)                          │
│ • SVG Logo + App Title   │ ┌─────────────────────────────────────────────────────────┐ │
│ • Business Switcher      │ │ Page Header (Title + Decoy "Ask" Search Link)           │ │
│ • Primary Links (6)      │ ├─────────────────────────────────────────────────────────┤ │
│ • Secondary Links (2)    │ │ Audio Briefing Widget (iframe height=52px)              │ │
│ • Role Switcher          │ ├─────────────────────────────────────────────────────────┤ │
│ • Language Switcher      │ │ Hero Metric & 5-Tile Solvency Equation                  │ │
│ • Read-Only Security Lock│ ├─────────────────────────────────────────────────────────┤ │
│                          │ │ Two-Column Split (Forecast Fan Chart + Data Quality DL) │ │
│                          │ └─────────────────────────────────────────────────────────┘ │
└──────────────────────────┴─────────────────────────────────────────────────────────────┘
```

#### 1. Nested Scroll Trap in Modal Dialogs (`flow-app-shell` Anti-Pattern: "Nested scrollbars in one region")
- **Observed Code (`app/streamlit_app.py:535–578`)**:
  ```python
  @st.dialog("Daily Recovery Sheet")
  def daily_print_dialog():
      ...
      components.html(html_sheet, height=450, scrolling=True)
  ```
- **Violation**: The `@st.dialog` modal has its own fixed viewport and overflow-y scroll container. Nesting an HTML iframe with `height=450` and `scrolling=True` inside the dialog creates two fighting vertical scrollbars. On trackpads and mobile touch screens, cursor focus gets trapped inside the iframe, preventing users from scrolling down to the modal's signature blocks or dismiss controls.
- **Fix**: Set iframe height to dynamic auto or render pure Streamlit components (`st.dataframe` or native HTML via `st.markdown`) inside the dialog container so only a single scroll container exists.

#### 2. AgGrid Fixed Height on Tablet/Mobile (`flow-app-shell` Anti-Pattern: "Desktop layout naively shrunk to mobile")
- **Observed Code (`app/streamlit_app.py:1143–1169`)**:
  ```python
  left, right = st.columns([1.75, 1], gap="medium")
  with left:
      ...
      grid = AgGrid(view, gridOptions=gb.build(), height=560, ...)
  ```
- **Violation**: Below 1024px, the master-detail two-column layout drops to stacked layout. The AgGrid table locks a rigid 560px vertical box while requiring at least 650px horizontal width. On mobile viewports (375px–430px), this forces severe horizontal panning inside a fixed 560px box, while the right detail card is pushed far below the fold.
- **Fix**: Follow `flow-app-shell` responsive collapse: switch from docked master-detail to push navigation (list screen $\to$ detail screen) below 768px, and collapse table rows into summary cards.

### 2.3 `flow-app-shell` Anti-Pattern Verdicts

| Anti-Pattern Check | Verdict | Line Citation | Analysis & Operational Context |
|---|---|---|---|
| **Total fixed chrome $\le$ 128px before content** | **PASS** | Lines 78–86 | Top header background is transparent; deploy button removed; content begins immediately. |
| **Max 65–75ch for prose readability** | **PASS** | Lines 81–83 | Main container capped at 1200px; explanation paragraphs clamped with `.cc-muted` and max-widths. |
| **Single scroll container per visual pane** | **FAIL** | Line 578 | Modal `daily_print_dialog` embeds an internally scrolling iframe (`height=450, scrolling=True`), creating nested scroll trap. |
| **No internally scrolling dashboard cards** | **PASS** | Lines 147–160 | Solvency tiles (`.cc-tile`) fit content tightly; overflow is handled at page level. |
| **Detail panel does not squeeze main below min-width** | **WARN** | Line 1143 | On screens 1024–1280px, `st.columns([1.75, 1])` squeezes AgGrid to ~580px, clipping narration column. |
| **Desktop layout naively shrunk to mobile** | **FAIL** | Lines 1143–1169 | Review queue retains dual-column master-detail layout on small viewports without mobile drawer collapse. |
| **Paint shell before data (no full-page spinner)** | **PASS** | Lines 282–289 | Data loading cached via `@st.cache_resource`; chrome remains interactive. |

---

## 3. Domain 2: Navigation Architecture & State Continuity (`flow-navigation`)

### 3.1 Information Architecture & Routing Structure
`ps11-copilot` leverages modern Streamlit 1.36+ `st.navigation` with `position="hidden"` (`app/streamlit_app.py:1579–1589`), delegating rendering to custom sidebar containers:

```
TOP LEVEL DESTINATIONS (Nouns):
├── Primary Group (.st-key-nav)
│   ├── Overview (icon: home, default=True)
│   ├── Cash book (icon: payments, url_path="cash-book")
│   ├── Forecast (icon: trending_up, url_path="forecast")
│   ├── Review (icon: inbox, url_path="review", dynamic badge: "Review · N")
│   ├── Receivables (icon: receipt_long, url_path="receivables")
│   └── Ask Copilot (icon: chat_bubble, url_path="ask")
└── Secondary Group (.st-key-nav_more)
    ├── Data quality (icon: verified_user, url_path="data-quality")
    └── Setup guide (icon: flag, url_path="setup")
```

### 3.2 Navigation Friction Points & State Breakdowns

```
STATE CONTINUITY FLOWCHART: INTER-PAGE QUERY DROP
┌───────────────────────────┐         st.switch_page("ask")         ┌───────────────────────────┐
│ Page: Overview            │ ────────────────────────────────────► │ Page: Ask Copilot         │
│ Action Row: "Salaries"    │      Sets: ask_q = "Can I pay..."     │ Displays grounded answer  │
│ CTA: "See the answer"     │            ask_prefill = "..."        │ for Salary question       │
└───────────────────────────┘                                       └───────────────────────────┘
                                                                                  │
                                              User hits Browser Refresh (F5)      │
                                              or opens direct URL /ask            ▼
                                                                    ┌───────────────────────────┐
                                                                    │ Page: Ask Copilot (EMPTY) │
                                                                    │ ask_q is None             │
                                                                    │ Prompt box is BLANK       │
                                                                    │ Prior answer WIPED OUT    │
                                                                    └───────────────────────────┘
```

#### 1. The Decoy Global Search Link (`flow-navigation` Anti-Pattern: "Nav label $\ne$ page action")
- **Observed Code (`app/streamlit_app.py:409–413`)**:
  ```python
  with st.container(key="askfield"):
      st.page_link(PAGES["ask"], label=t("Ask about your cash…", "रोकड़ और हिसाब के बारे में पूछें…"),
                   icon=":material/search:", use_container_width=True)
  ```
- **Styling (`app/streamlit_app.py:118–123`)**:
  ```css
  .st-key-askfield [data-testid="stPageLink-NavLink"] {
    min-height: 44px; padding: 0 14px; border: 1px solid #DCDCD6;
    border-radius: 10px; background: #FFFFFF;
  }
  ```
- **Violation**: The UI styles this container to perfectly mimic an active HTML `<input type="text">` search bar (white background, 1px border, search magnifying glass icon, placeholder-style grey copy). When an SME owner clicks into the box intending to type *"Can I pay salaries?"*, it does not focus an input; instead, it executes an instantaneous full-page route change to `/ask`. The user's typed mental model is shattered.
- **Fix**: Either embed a true functional header search input that routes with the typed query (`st.text_input` submitting to `/ask?q=...`), or style the widget honestly as a navigation chip/button rather than an input mimic.

#### 2. Absence of In-App Breadcrumbs & Return Paths (`flow-navigation` Rule 4)
- **Observed Code (`app/streamlit_app.py:392–399, 746, 752, 758`)**:
  Action rows in Overview route users deep into sub-pages using `go()` buttons:
  - "See the answer" $\to$ routes to Ask Copilot (`PAGES["ask"]`)
  - "Open chasing list" $\to$ routes to Receivables (`PAGES["recv"]`)
  - "Start review" $\to$ routes to Review Queue (`PAGES["review"]`)
- **Violation**: Upon arriving at `Receivables` or `Review`, there is no in-app breadcrumb (`Overview / Receivables`) or contextual back button (`← Back to Overview`). The SME owner must re-scan the entire left sidebar to find their way back home. If the user arrived via a deep-linked action, browser Back history does not reliably restore the previous scroll position or Overview dashboard state.
- **Fix**: Implement an in-app breadcrumb bar in `page_header()`: `Overview / Receivables` with clickable parent crumbs.

#### 3. State Sanitization & Reload Drops (`flow-navigation` Anti-Pattern: "SPA navigation without URL updates")
- **Observed Code (`app/streamlit_app.py:1138–1140, 1232–1234, 1625–1626`)**:
  - `biz_choice` (`SME-1`, `SME-2`, `SME-3`), `role_choice`, and `lang_choice` are synchronized to `st.session_state`.
  - In `page_review`, `choice` is read from `st.session_state["queue_filter"]`.
  - In `page_receivables`, `choice` is read from `st.session_state["chase_filter"]`.
- **Violation**: Navigation states are not serialized into Streamlit's URL query parameters (`st.query_params`). If Prakash Kale filters the receivables list to "Over 45 days" and bookmarks or shares the link with his CA, the CA lands on the default filter view with the default business (`SME-1: Distributor`), completely dropping the context.
- **Fix**: Synchronize `st.query_params`: bind `biz`, `role`, `lang`, `q`, and `filter` directly to URL query strings.

### 3.3 `flow-navigation` Anti-Pattern Verdicts

| Anti-Pattern Check | Verdict | Line Citation | Analysis & Operational Context |
|---|---|---|---|
| **Top-level destinations $\le 7$** | **WARN** | Lines 1600–1609 | 8 total destinations split into primary (6) and secondary (2). Acceptable for pro tool, but borderline for mobile. |
| **Always pair icon + label in nav** | **PASS** | Lines 1580–1587 | Every `st.Page` defines both Material icon and explicit human noun label. |
| **Nav items identical across all pages** | **PASS** | Lines 1599–1609 | Sidebar nav cluster remains completely stable across page switches. |
| **SPA navigation updates URL (pushState)** | **WARN** | Lines 1580–1587 | Page switching updates `url_path`, but in-page filter state and active tabs do not update query params. |
| **Command palette duplicates, never replaces nav** | **PASS** | Line 411 | Direct navigation links remain accessible via sidebar; Ask search acts as accelerator. |
| **Wayfinding scent: nav label matches page title** | **FAIL** | Lines 1604, 1116 | Sidebar badge reads `"Review · 5"`, while page header renders `"Review"` / `"खाता मिलान एवं समीक्षा (Review)"`. |
| **Active-state marking mandatory at every level** | **PASS** | Line 91 | Streamlit natively highlights active `st.page_link` pill with filled background `#E9E9E5`. |

---

## 4. Domain 3: Data Tables, Lists & Grids (`flow-tables`)

### 4.1 Data Surfaces Inventory
`ps11-copilot` employs three distinct data display models:
1. **Interactive Financial Grid (`st_aggrid.AgGrid`)**: Used exclusively on the Review Queue (`page_review`, lines 1157–1169).
2. **Actionable Customer Cards (`.cc-crows`)**: Used for the Top 10 Chasing List on Receivables (`page_receivables`, lines 1251–1285).
3. **Collapsible Full Ledger (`st.dataframe`)**: Embedded in an expander on Receivables (lines 1287–1293) and Live Ingest (lines 1529, 1537).
4. **Structured HTML Financial Matrices (`_html_table`)**: Used for Month-by-Month Forecast (lines 1086–1090) and Data Quality Benchmarks (lines 1421–1422).

### 4.2 Data Grid Usability & Anti-Pattern Analysis

```
REVIEW QUEUE MASTER-DETAIL ARCHITECTURE
┌────────────────────────────────────────────────────────┬───────────────────────────────────────────┐
│ AGGRID ALPINE TABLE (Left Pane: 1.75 col)              │ DECISION & EVIDENCE CARD (Right Pane: 1)  │
├────────────┬───────────┬──────────────┬────────────────┤ ┌───────────────────────────────────────┐ │
│ Date       │ Amount    │ Type         │ Narration      │ │ Tier Badge: Suggestion / Question     │ │
├────────────┼───────────┼──────────────┼────────────────┤ │ Rule: EXACT_BILL (Monospace code)     │ │
│ 2026-09-30 │ ₹45,200   │ Suggestion   │ NEFT/KAVERI... │ │ Amount: ₹45,200 (Large Hero Number)   │ │
│ 2026-09-29 │ ₹1,12,000 │ Question     │ UPI/98220...   │ │ Why it's here: Explanation text       │ │
│ 2026-09-28 │ ₹8,500    │ Suggestion   │ CMS/DEP/PUN... │ │ Bank Narration: Full unparsed string  │ │
├────────────┴───────────┴──────────────┴────────────────┤ │ Suggested Documents: inv-902 (₹45,200)│ │
│ Pagination: 20 rows per page · Page 1 of 12            │ ├───────────────────────────────────────┤ │
└────────────────────────────────────────────────────────┘ │ [Accept] BUTTON IS PERMANENTLY DISABLED│ │
                                                           │ Tooltip: "Posting wired in next build" │ │
                                                           └───────────────────────────────────────┘ │
```

#### 1. The Permanently Disabled Primary Action (`flow-tables` / `flow-forms` Anti-Pattern)
- **Observed Code (`app/streamlit_app.py:1202–1204`)**:
  ```python
  st.button("Accept", disabled=True, use_container_width=True,
            help="Posting is wired in the next build; v1 is read-only.")
  H('<div class="cc-note">Posting comes in the next build. This version is read-only.</div>')
  ```
- **Violation**: The Review Queue is explicitly billed as *"Receipts that need you"*. An SME owner or accountant clicks through to triage suggestions. The master detail displays a large primary action button `"Accept"`, but it is permanently greyed out and unclickable. 
- **Cognitive Impact**: This creates acute operational frustration. The user completed the mental evaluation of the evidence, agreed with the match, but has no mechanism to clear the item from their queue.
- **Fix**: While maintaining the core read-only invariant (v1 does not write to live Tally bank accounts), provide genuine local triage actions:
  1. `"Acknowledge Match (Local Save)"` $\to$ marks item as reviewed in `VaultDB` and removes it from the pending badge count.
  2. `"Copy Voucher Entry"` $\to$ copies formatted journal narration to clipboard for easy manual entry into TallyPrime.
  3. `"Flag for CA"` $\to$ adds a note for the monthly accountant review.

#### 2. AgGrid Column Truncation on Narrow Displays (`flow-tables` Anti-Pattern: "Horizontal-scrolling 9 columns on mobile")
- **Observed Code (`app/streamlit_app.py:1149–1153`)**:
  ```python
  gb.configure_column("date", header_name="Date", width=104, minWidth=96)
  gb.configure_column("amount", header_name="Amount", width=100, minWidth=90, type=["rightAligned"])
  gb.configure_column("type", header_name="Type", width=116, minWidth=112)
  gb.configure_column("rule", header_name="Rule", width=124, minWidth=104)
  gb.configure_column("narration", header_name="Bank narration", flex=1, minWidth=220)
  ```
- **Violation**: The minimum cumulative width required for these columns is $96 + 90 + 112 + 104 + 220 = 622\text{ px}$ (plus scrollbars and borders). When rendered within `st.columns([1.75, 1])` on a 13-inch laptop (1280px screen minus 280px sidebar = 1000px main area $\to$ left column is $\sim 630\text{ px}$), the table triggers horizontal scroll clipping. The most vital column—Bank narration—is cut off, requiring users to horizontally pan back and forth for every row.
- **Fix**: Hide the technical `Rule` column by default in the grid (it is already prominently displayed in the right-hand detail pane). Give `Bank narration` 50% flex width so narrations are immediately readable without panning.

#### 3. Filter Reset on Page Reload (`flow-tables` Anti-Pattern: "Filters/sort reset on refresh or back")
- **Observed Code (`app/streamlit_app.py:1138–1140`)**:
  ```python
  choice = st.segmented_control("Show", options, selection_mode="single", default="All",
                                key="queue_filter", ...) or "All"
  ```
- **Violation**: The filter selection (`All`, `Suggestions`, `Questions`) exists only in temporary widget session state. Navigating to another page and returning, or hitting browser reload, silently resets the grid back to `All`. The user must re-apply their filter every single time.
- **Fix**: Persist active table filter in `st.query_params["tier"]`.

### 4.3 `flow-tables` Anti-Pattern Verdicts

| Anti-Pattern Check | Verdict | Line Citation | Analysis & Operational Context |
|---|---|---|---|
| **Numeric columns right-aligned with tabular figures** | **PASS** | Lines 1150, 185 | Amounts explicitly configured with `type=["rightAligned"]` and CSS `tabular-nums`. |
| **Applied filters render as removable chips with counts** | **PASS** | Lines 1138–1139 | `st.segmented_control` displays dynamic count labels: `Suggestions (5)`, `Questions (2)`. |
| **No bare raw DataFrames on default views** | **PASS** | Lines 1251–1285 | Top 10 actionable debtors rendered as custom cards; raw dataframe tucked inside expander. |
| **Filters and sort choices persist across reloads** | **FAIL** | Line 1138 | Neither Review queue nor Receivables filters are synced to URL parameters. |
| **Row click drives detail pane (master-detail)** | **PASS** | Lines 1155, 1170 | AgGrid single-row selection dynamically re-hydrates the right-hand evidence container. |
| **Primary action accessible and enabled** | **FAIL** | Line 1202 | "Accept" button is permanently disabled with a tooltip promise for future builds. |
| **Summary/footer row on financial tables** | **PASS** | Line 1218 | Top metric figures prominently display Total Outstanding, Open Invoices, and Overdue sums. |

---

## 5. Domain 4: Forms, Wizards & Modal Dialogs (`flow-forms`)

### 5.1 Forms & Dialogs Inventory
1. **Setup Guide 3-Step Wizard (`page_setup`)**: Consent $\to$ Check your books $\to$ Key numbers (lines 1462–1576).
2. **Day-Close Dialog (`day_close_dialog`)**: 6-field counter till reconciliation modal (lines 821–836).
3. **Salesman Collections Dialog (`collections_dialog`)**: Multimodal slip OCR and 3-row collection receipt logging (lines 838–876).
4. **Daily Print & PDF Recovery Sheet (`daily_print_dialog`)**: Godown dispatch and signature confirmation modal (lines 494–579).
5. **Counter Staff PIN Gate**: Password-masked text input protecting Cash Book (lines 916–924).
6. **Natural Language Inquiry Form**: Q&A submission form on Ask Copilot (lines 1329–1334).

### 5.2 Form Flow Friction Points & Deficit Analysis

```
DAY CLOSE DIALOG WORKFLOW: THE PLACEBO RECONCILIATION
┌────────────────────────────────────────────────────────┐
│ MODAL: Close the day (@st.dialog)                      │
├────────────────────────────────────────────────────────┤
│ Opening till cash: [ ₹10,000.0 ] (Hardcoded default)   │
│ Today's cash takings: [ ₹25,000.0 ] (Hardcoded default)│
│ Cash expenses: [ ₹2,500.0 ] (Hamali/petty)             │
│ Cash banked: [ ₹20,000.0 ]                             │
│ Physical count at close: [ ₹12,500.0 ]                 │
│ Notes: [ Routine daily close ]                         │
├────────────────────────────────────────────────────────┤
│ [ Record in cash book ] (Primary Submit)               │
└────────────────────────────────────────────────────────┘
                           │
                 Form Submit Triggered
                           ▼
┌────────────────────────────────────────────────────────┐
│ CODE DEFICIT (app/streamlit_app.py:833-835)            │
│ 1. Zero values extracted from form fields!             │
│ 2. vault.record_galla() NEVER CALLED!                  │
│ 3. Sets session_state["toast"] = "Recorded locally..." │
│ 4. Executes st.rerun()                                 │
├────────────────────────────────────────────────────────┤
│ RESULT: PLACEBO FORM! Till status never updates!       │
└────────────────────────────────────────────────────────┘
```

#### 1. The Placebo Day-Close Form (`flow-forms` Rule 1 / `flow-errors`)
- **Observed Code (`app/streamlit_app.py:821–836`)**:
  ```python
  @st.dialog("Close the day")
  def day_close_dialog():
      ...
      with st.form("galla_close_form", border=False):
          c1, c2 = st.columns(2)
          c1.number_input(t("Opening till cash (₹)", ...), value=10000.0, step=500.0)
          c2.number_input(t("Today's cash takings (₹)", ...), value=25000.0, step=1000.0)
          c1.number_input(t("Cash expenses paid (₹)", ...), value=2500.0, step=100.0)
          c2.number_input(t("Cash banked into account (₹)", ...), value=20000.0, step=1000.0)
          c1.number_input(t("Physical count at close (₹)", ...), value=12500.0, step=500.0)
          c2.text_input(t("Notes", ...), value="Routine daily close")
          submitted = st.form_submit_button(t("Record in cash book", ...), type="primary")
      if submitted:
          st.session_state["toast"] = t("Recorded locally in Cash Book. Balance updated.", ...)
          st.rerun()
  ```
- **Violation**:
  1. **Zero Database Mutation**: Notice that the return values of `number_input` are completely discarded! Variable names were not even assigned to the inputs. `vault.record_galla(...)` is never called.
  2. **Deceptive Toast Feedback**: When the user clicks "Record in cash book", Streamlit displays a green toast saying *"Recorded locally in Cash Book. Balance updated."*, but the database was completely untouched.
  3. **Hardcoded Initial Values**: Opening cash is hardcoded to ₹10,000.0 regardless of yesterday's physical close!
  4. **Multi-Column Disorientation (`flow-forms` Anti-Pattern)**: Splitting 6 related inputs into two alternating columns (`c1, c2 = st.columns(2)`) breaks the natural vertical scan line (Baymard form research).
- **Fix**: Assign variables to all 6 inputs, default `opening_cash` dynamically to `vault.get_latest_galla(biz).counted_cash`, instantiate a real `GallaEntry` object, call `vault.record_galla(entry)`, and render fields in a single vertical column.

#### 2. Wizard Back-Button Data Loss (`flow-forms` Rule 6)
- **Observed Code (`app/streamlit_app.py:1521–1548`)**:
  In Step 2 of `page_setup`, users upload a live bank statement or Tally XML file:
  ```python
  u_file = st.file_uploader(..., key="setup_upload_file")
  if u_file:
      parse_res = parse_bank_statement(u_file.read(), u_file.name)
      st.success(...)
      st.dataframe(parse_res["df"].head(10))
  ```
  When the user clicks `"Continue"` to advance to Step 3 (`st.session_state["onboarding_step"] = 3`), then realizes they need to verify their file and clicks `"Back"` (`st.session_state["onboarding_step"] = 1`), `parse_res` is wiped from execution memory. The preview dataframe disappears until the user interacts with the uploader again.
- **Violation**: `flow-forms` Rule 6 states: *"Wizard back is free. Back returns to previous step with all of its data intact. Data loss on back-navigation is the #1 wizard killer."*
- **Fix**: Store `parse_res` and uploaded metadata in `st.session_state["uploaded_statement_summary"]`.

#### 3. Fake Adjustability in Step 3 (`flow-forms` Anti-Pattern: "Promised control without inputs")
- **Observed Code (`app/streamlit_app.py:1553–1565`)**:
  In Step 3 of `page_setup`, the sub-heading explicitly promises:
  *"Filled in from your recurring transactions. Confirm them, or adjust them with your accountant."*
  However, lines 1562–1565 render the key numbers (Sanctioned CC limit, Payroll repeating day, Suggested cash floor) as static, read-only HTML definition lists (`<dl class="cc-dl">`).
- **Violation**: Users are told they can adjust them, but there are zero inputs or edit toggles on the screen.
- **Fix**: Render editable `st.number_input` fields pre-populated with discovered figures so the owner or CA can adjust the cash floor or payroll day before finishing setup.

#### 4. Transient Counter Staff PIN Unlock Churn (`flow-forms` / `flow-auth`)
- **Observed Code (`app/streamlit_app.py:917–922`)**:
  ```python
  staff_pin = c.text_input(t("Enter Owner PIN to unlock", ...), type="password")
  if staff_pin:
      if staff_pin == expected_pin:
          can_view_cash_book = True
  ```
- **Violation**: `can_view_cash_book` is evaluated purely on whether `staff_pin == expected_pin` during the current script run. If the counter staff unlocks the cash book, navigates to Overview, and returns to Cash Book, the unlocked state is forgotten and they must re-enter the 4-digit PIN.
- **Fix**: Once unlocked, persist `st.session_state["staff_unlocked_until"] = datetime.now() + timedelta(hours=8)`.

### 5.3 `flow-forms` Anti-Pattern Verdicts

| Anti-Pattern Check | Verdict | Line Citation | Analysis & Operational Context |
|---|---|---|---|
| **Single-column vertical layout** | **FAIL** | Lines 825, 861 | Both `day_close_dialog` and `collections_dialog` split inputs into 2 columns. |
| **Labels above fields, persistent on focus** | **PASS** | Lines 826–831 | Standard Streamlit labels render above fields; placeholders used for format hints. |
| **Mark optional fields, not asterisks** | **PASS** | Line 867 | `Shop {i} (optional)` explicitly appended to non-mandatory inputs. |
| **Wizard back preserves all data** | **FAIL** | Line 1546 | Advancing to Step 3 and clicking Back to Step 2 loses live statement parse cache. |
| **No disabled submit buttons without explanation** | **PASS** | Lines 832, 869 | Form submit buttons remain enabled and accessible. |
| **Form mutations actually persist to storage** | **FAIL** | Lines 833–835 | `day_close_dialog` submits a placebo form: zero data is sent to `vault`. |
| **Validation on blur / submit** | **WARN** | Lines 824–832 | Zero sanity checks (e.g. physical count cannot be negative, banked cash $\le$ takings). |

---

## 6. Domain 5: Error Handling & Failure Recovery (`flow-errors`)

### 6.1 Error Surfaces Inventory
1. **Statutory RBAC Notice Banner (`render_partial_view_notice`)**: Required on 7 views (lines 590, 894, 1009, 1120, 1213, 1322, 1428).
2. **Bank Statement Balance Break Warnings**: Ingest validation in `page_setup` (lines 1510–1516).
3. **Shortfall Warning Callouts (`.cc-callout warn`)**: Forecast alerts on CC limit breaches (lines 1015–1020).
4. **Multimodal API Fallbacks**: Gemini Vision slip OCR and Gemini Voice transcription error traps (`src/copilot/gemini.py`).
5. **Web Speech Synthesis Fallback Alert**: Audio briefing player browser compatibility check (line 460).

### 6.2 Error Architecture Deficit Analysis

```
THE SILENT NOTICE BUG: DROPPED STATUTORY TRANSPARENCY
┌────────────────────────────────────────────────────────┐
│ app/streamlit_app.py (Lines 590, 894, 1009, etc.)      │
├────────────────────────────────────────────────────────┤
│ if showing_partial_view:                               │
│     render_partial_view_notice()  <── CALLED IN A VOID │
└────────────────────────────────────────────────────────┘
                           │
                     Function Body
                           ▼
┌────────────────────────────────────────────────────────┐
│ src/copilot/vault/notice.py (Line 5-7)                 │
├────────────────────────────────────────────────────────┤
│ def render_partial_view_notice() -> str:               │
│     return PARTIAL_VIEW_NOTICE                         │
└────────────────────────────────────────────────────────┘
                           │
                     Return Value
                           ▼
┌────────────────────────────────────────────────────────┐
│ Python evaluates string expression and DISCARDS IT!    │
│ NO st.warning(), NO st.info(), NO st.markdown()!       │
├────────────────────────────────────────────────────────┤
│ RESULT: NOTICE NEVER RENDERS ON ANY OF THE 7 PAGES!    │
│ Counter staff & CA see partial numbers WITHOUT WARNING!│
└────────────────────────────────────────────────────────┘
```

#### 1. The Critical Silent Partial View Notice Bug (`flow-errors` / `flow-permissions`)
- **Observed Code (`app/streamlit_app.py:590, 894, 1009, 1120, 1213, 1322, 1428`)**:
  ```python
  if showing_partial_view:
      render_partial_view_notice()
  ```
- **Definition (`src/copilot/vault/notice.py:5–7`)**:
  ```python
  def render_partial_view_notice() -> str:
      """Return the standard notice banner text when viewing formal books without cash memo."""
      return PARTIAL_VIEW_NOTICE
  ```
- **Violation**: In Python, calling a function that returns a string as a standalone statement without assigning or passing it to an output function is a complete no-op. The string `"Formal books only. The owner's cash memo is not included in this view."` is discarded by the interpreter.
- **Architectural Severity**: This is a direct statutory transparency violation. When an Accountant (CA) logs in or Counter Staff accesses the books, they must be explicitly informed that informal cash drawer counts and salesman collection slips are withheld from their view. Because this banner never renders, the CA might believe the bank figures represent 100% of the firm's true liquidity, risking false tax filings or inaccurate credit evaluations.
- **Fix**: In `app/streamlit_app.py`, wrap all invocations:
  ```python
  if showing_partial_view:
      st.info(render_partial_view_notice(), icon=":material/lock:")
  ```

#### 2. False Success Masking on Vision OCR Failure (`flow-errors` Anti-Pattern: "Misleading success feedback")
- **Observed Code (`app/streamlit_app.py:848–858`)**:
  ```python
  prefill_shop = "Laxmi Kirana Stores"
  prefill_amount = 15000.0
  prefill_salesman = "Ramesh K."
  if slip_file:
      with st.spinner(...):
          ocr_data = ocr_collection_slip(slip_file.read(), ...)
          if ocr_data.get("shop"):
              prefill_shop = ocr_data["shop"]
          if ocr_data.get("amount"):
              prefill_amount = float(ocr_data["amount"])
          if ocr_data.get("salesman"):
              prefill_salesman = ocr_data["salesman"]
          st.success(t(f"Extracted: {prefill_shop} · {inr(prefill_amount)} · {prefill_salesman}", ...))
  ```
- **Deficit in `src/copilot/gemini.py:150`**:
  If Gemini API key is missing or OCR fails, `ocr_collection_slip` returns:
  `{"shop": "", "amount": 0.0, "salesman": "", "date": "", "notes": "OCR extraction failed"}`.
- **Violation**: Because all keys are empty, none of the `if ocr_data.get(...)` branches trigger. The variables retain their initial dummy values: `"Laxmi Kirana Stores"`, `15000.0`, `"Ramesh K."`. Then, line 857 immediately fires `st.success(...)` telling the user it successfully extracted Laxmi Kirana Stores!
- **Cognitive Impact**: An owner uploads a genuine handwritten slip from "Pooja Traders" for ₹8,000. The OCR fails, but the app boldly claims it extracted "Laxmi Kirana Stores · ₹15,000". If the owner doesn't spot the swap, they submit false accounting records.
- **Fix**: Check `if ocr_data.get("notes") == "OCR extraction failed"` $\to$ display `st.error("Could not read handwriting. Please enter shop and amount manually below.")`. Never display `st.success` over dummy defaults.

#### 3. Silent Audio Transcription Dead-End (`flow-errors` Rule 3: "Recovery action with every error")
- **Observed Code (`app/streamlit_app.py:1337–1343`)**:
  ```python
  rec_audio = st.audio_input(t("Record voice question", ...), key="mic_audio_input")
  if rec_audio:
      with st.spinner(t("Transcribing with Gemini Voice…", ...)):
          transcribed = transcribe_audio(rec_audio.read(), ...)
          if transcribed:
              st.session_state["ask_q"] = transcribed
              st.session_state["ask_typed"] = transcribed
              st.rerun()
  ```
- **Violation**: If `transcribe_audio` returns an empty string (due to network timeout, low mic input, or missing API key), the block executes silently. The spinner vanishes, nothing is populated in the text box, and no error message is displayed. The user is left wondering if the app froze.
- **Fix**: Add `else: st.warning("Could not transcribe audio. Please speak closer to the mic or select a prompt chip below.")`.

#### 4. Intrusive Browser `alert()` in Audio Briefing (`flow-errors` Anti-Pattern)
- **Observed Code (`app/streamlit_app.py:459–462`)**:
  ```javascript
  if (!('speechSynthesis' in window)) {
    alert('Speech synthesis is not supported in this browser.');
    return;
  }
  ```
- **Violation**: Triggering a native modal browser alert interrupts execution and steals operating system focus. On mobile Safari or embedded in-app webviews, native alerts can lock UI threads.
- **Fix**: Render a calm, inline HTML banner inside the widget container: `<div class="cc-note">Audio playback is not supported in this browser.</div>`.

### 6.3 `flow-errors` Anti-Pattern Verdicts

| Anti-Pattern Check | Verdict | Line Citation | Analysis & Operational Context |
|---|---|---|---|
| **Preserve entered user work on error** | **PASS** | Line 1324 | Questions and typed inputs persist in `st.session_state["ask_typed"]`. |
| **Error message rendered at point of failure** | **FAIL** | Lines 590, 894 | `render_partial_view_notice` is called without display widgets, rendering 0 output. |
| **Every error carries a recovery action** | **FAIL** | Line 1340 | Voice transcription failure terminates silently without retry guidance. |
| **Never show false success on failure** | **FAIL** | Line 857 | Slip OCR failure replaces upload with hardcoded Laxmi Kirana and emits `st.success`. |
| **Destructive actions protected by undo / read-only** | **PASS** | Lines 12, 1623 | System enforces 100% read-only invariant; destructive mutations impossible. |
| **Calm, blame-free error copy** | **PASS** | Lines 807, 1018 | Balance breaks framed neutrally: `"12 balance breaks"` with no staff culpability. |

---

## 7. Domain 6: Zero-Data & Empty States (`flow-empty-states`)

### 7.1 The Four Non-Happy States Matrix
`flow-empty-states` establishes that every data surface must account for four distinct non-happy states:
1. **First-Use Empty** (User never had data $\to$ high-leverage onboarding CTA).
2. **Completed Empty** (User finished everything $\to$ celebrate "Inbox Zero").
3. **No-Results Empty** (Filter/query returned 0 hits $\to$ echo query + "Clear filters" button).
4. **Error Empty** (Fetch failed $\to$ say why + Retry button).

### 7.2 Empty State Audits by View

```
EMPTY STATE FAILURE: INAPPROPRIATE LEGAL WARNING ON 0-RESULT FILTER
┌────────────────────────────────────────────────────────┐
│ RECEIVABLES TAB: Filter selected = "Over 45 days"      │
│ Scenario: Business has 0 overdue invoices (HEALTHY!)   │
├────────────────────────────────────────────────────────┤
│ CURRENT CODE DISPLAY (app/streamlit_app.py:1243-1246): │
│ [✓] No customers in this list                          │
│ "Balances older than 30 months can become hard to      │
│  recover under the Limitation Act. They will show      │
│  here first."                                          │
├────────────────────────────────────────────────────────┤
│ VIOLATION: Irrelevant statutory warning shown to       │
│ healthy business! Zero "Clear filters" button!         │
└────────────────────────────────────────────────────────┘
```

#### 1. Inappropriate Statutory Warning on Filtered Empty State (`flow-empty-states` Anti-Pattern)
- **Observed Code (`app/streamlit_app.py:1243–1246`)**:
  ```python
  if filtered_cust.empty:
      H(f'<div style="display:flex;flex-direction:column;align-items:center;gap:6px;padding:48px 16px;text-align:center">'
        f'{svg(ICON_CHECK_CIRCLE, 28, SUBTLE, 1.6)}<div style="font-weight:500">{t("No customers in this list", "इस सूची में कोई ग्राहक नहीं है")}</div>'
        f'<div class="cc-muted" style="max-width:420px">{t("Balances older than 30 months can become hard to recover under the Limitation Act. They will show here first.", ...)}</div></div>')
  ```
- **Violation**: The description text hardcodes an advisory about the **Limitation Act (debts older than 30 months)** regardless of which filter the user selected!
  - If Dr. Kavya Hegde (Clinic) selects the default filter *"Over 45 days"* and has 0 overdue patients, she is congratulated that there are no customers, but then immediately warned that debts older than 30 months become unrecoverable under the Limitation Act!
  - Furthermore, there is **no "Clear filters" button** (`flow-empty-states` Rule 3).
- **Fix**: Implement context-aware empty state copy:
  - If filter is `"Over 45 days"` and empty $\to$ `"All customer accounts are within normal credit terms. No chasing required this week."`
  - If filter is `"Over 30 months"` and empty $\to$ `"No chronic debts near statutory limitation limits."`
  - Provide a one-click button: `st.button("Show all customers", on_click=...)`.

#### 2. Review Queue Cleared State (`flow-empty-states` Rule 2: "Completed-empty")
- **Observed Code (`app/streamlit_app.py:1132–1134`)**:
  ```python
  if q.empty:
      st.success("Nothing waiting.")
      return
  ```
- **Violation**: A bare `st.success("Nothing waiting.")` abruptly halts page execution. While technically accurate, it represents a dead end. For an accountant who just finished clearing 40 bank lines, this completed-empty state should celebrate the achievement ("All receipts reconciled under Decision 60"), display the total matched rupees, and provide an exit link (`st.page_link(PAGES["overview"], label="Return to Overview")`).

### 7.3 `flow-empty-states` Anti-Pattern Verdicts

| Anti-Pattern Check | Verdict | Line Citation | Analysis & Operational Context |
|---|---|---|---|
| **Distinct designs for all 4 empty states** | **FAIL** | Line 1243 | Filtered-to-empty state shares identical static text with no filter-clearing CTA. |
| **No-results echoes query and offers clear action** | **FAIL** | Line 1244 | Filter zero-result gives no "Clear filter" button; user must manually re-toggle radio. |
| **No beginner copy on filtered empty views** | **WARN** | Line 1246 | Displays irrelevant Section 18 Limitation Act advice to users filtering by 45 days. |
| **Completed-empty celebrates without condescension** | **WARN** | Line 1133 | Review queue renders bare `st.success("Nothing waiting.")` with no follow-up navigation. |
| **Loading indicators keyed to latency thresholds** | **PASS** | Lines 282, 295 | Cache resource operations declare explicit spinners: `"Running the 90-day forecast…"`. |
| **No blank white screen on first paint** | **PASS** | Lines 583–600 | Chrome and hero titles paint immediately; calculations bind synchronously. |

---

## 8. Domain 7: AI Interaction & Conversational Copilot (`flow-ai-chat` & `flow-search`)

### 8.1 Conversational Copilot Architecture
The Ask Copilot surface (`page_ask`, lines 1314–1393) combines:
1. **Free-Form Text Input (`st.form("ask_form")`)**: Text box with primary "Ask" button.
2. **Gemini Multimodal Voice Recording (`st.audio_input`)**: Transcribes spoken Hindi/English into search queries.
3. **Pre-Crafted Inquiry Prompt Pills (`st.pills`)**: 6 bilingual business chips.
4. **Intent-Grounded Routing Badge**: Classifies response into `FACT`, `UNSUPPORTED`, `NEEDS_CHIPS`, or statutory boundary.
5. **Vernacular Hindi Summary Callout (`💡 सरल समझ: ...`)**: Highlighting operational takeaways in colloquial Devanagari.
6. **Sources & Evidence Expander**: Disclosing underlying database rows.

### 8.2 AI Interaction Flow Friction Points

```
CONVERSATIONAL COPILOT: SINGLE-TURN AMNESIA & BLOCKING LATENCY
┌────────────────────────────────────────────────────────┐
│ ASK COPILOT SURFACE                                    │
├────────────────────────────────────────────────────────┤
│ [ Can I pay salaries on 1 October 2026?        ] [Ask] │
│ 🎙️ Speak your question (माइक से बोलें)                 │
│ Prompt Pills: [ Who owes me most? ] [ Worst cash dip? ]│
├────────────────────────────────────────────────────────┤
│ USER SUBMITS QUERY                                     │
│ 1. Whole page blocks (No streaming tokens)             │
│ 2. copilot.ask() computes synchronously in Python      │
│ 3. Whole markdown card dumps on screen at once         │
├────────────────────────────────────────────────────────┤
│ GROUNDED ANSWER CARD                                   │
│ Intent Badge: [✓ From your books]                      │
│ Question: Can I pay salaries on 1 October 2026?        │
│ Body: Yes. September payroll of ₹8,20,000 is covered...│
│ 💡 सरल समझ: हाँ, आप 1 अक्टूबर को सैलरी आसानी से दे... │
│ Sources: [ Expander: 42 rows ]                         │
├────────────────────────────────────────────────────────┤
│ CRITICAL DEFICIT: USER ASKS FOLLOW-UP QUESTION         │
│ User clicks pill: "Who owes me the most?"              │
│ ──► PREVIOUS SALARY ANSWER IS INSTANTLY DESTROYED!     │
│ ──► Zero conversation history, zero thread fork!       │
└────────────────────────────────────────────────────────┘
```

#### 1. Single-Turn Amnesia (`flow-ai-chat` Anti-Pattern: "Unsearchable, untitled history")
- **Observed Code (`app/streamlit_app.py:1351–1392`)**:
  ```python
  selected_q = st.session_state.get("ask_q")
  if selected_q:
      a = copilot.ask(biz, q_for_copilot, ...)
      ...
      H(f'<div>...{esc(a.text)}</div>')
  ```
- **Violation**: The application stores only a single query in memory (`st.session_state["ask_q"]`). When an SME owner asks *"Can I pay salaries on 1 Oct?"*, gets an answer, and then asks a logical follow-up (*"Who owes me the most so I can bridge that gap?"*), the entire previous exchange vanishes! There is no conversation history, no thread log, no back-paging between answers ("1 of 2"), and no exportable transcript.
- **Cognitive Impact**: SME owners compare numbers. Prakash Kale needs to see his salary bill and his debtor balance side-by-side to make a decision. Wiping the screen on every turn forces him to hold financial numbers in short-term working memory.
- **Fix**: Maintain `st.session_state["chat_history"] = [{"q": ..., "a": ..., "ts": ...}]` and render as a chronological conversation stack.

#### 2. Blocking Execution vs Progressive Token Streaming (`flow-ai-chat` Rule 3)
- **Observed Code (`app/streamlit_app.py:1354, 1368`)**:
  ```python
  a = copilot.ask(biz, q_for_copilot, galla_cash=answer_galla())
  H(f'...<div style="font-size:1.02rem;...">{esc(a.text)}</div>')
  ```
- **Violation**: `copilot.ask` executes synchronously. When running with live LLM synthesis, the UI blocks with an empty screen for 3–8 seconds until the complete text block is prepared, then dumps the full response on screen in a single redraw.
- **Standard**: `flow-ai-chat` Rule 3 dictates: *"The response streams token-by-token. Target under ~1 second to first visible activity. Blocking on the complete response is the single worst AI-UX mistake; streaming is the interaction, converting a 20-second wait into 20 seconds of reading."*
- **Fix**: Implement `st.write_stream()` generator yield for copilot answers.

#### 3. Unparsed Comma-Separated Evidence Blob (`flow-ai-chat` Rule: "Citations")
- **Observed Code (`app/streamlit_app.py:1390–1392`)**:
  ```python
  with st.expander(t(f"Sources ({len(a.sources)} rows)", ...)):
      H(f'<div class="cc-mono" style="font-size:0.78rem;line-height:1.7">{esc(", ".join(a.sources[:60]))}</div>')
  ```
- **Violation**: When an answer cites 40 open invoices, the evidence expander outputs an unformatted wall of comma-separated strings (`inv-101, inv-102, inv-103, ...`).
- **Standard**: `flow-ai-chat` dictates that citations must resolve to structured source cards showing invoice numbers, customer names, rupee amounts, and dates. A raw monospace string dump looks like debug output rather than a production financial audit trail.
- **Fix**: Render `a.sources` in a structured mini-table or pill grid.

#### 4. Public Demo Mode Lockout UX (`flow-ai-chat` Anti-Pattern)
- **Observed Code (`app/streamlit_app.py:1328–1350`)**:
  When `COPILOT_PUBLIC=1`, the text input form and voice recording expander are completely removed from the DOM, leaving only the prompt chips and a subtle footnote:
  *"Typing your own question is switched off in this preview until our safety checks pass."*
- **Violation**: Users entering a public demo expect a search interface. Hiding the input box entirely makes the page look broken or un-hydrated.
- **Fix**: Keep the input box visible, but disabled with an informative in-place placeholder and tooltip explaining the safety sandbox: `st.text_input(..., disabled=True, placeholder="Public demo mode: Select a verified question chip below")`.

### 8.3 `flow-ai-chat` & `flow-search` Anti-Pattern Verdicts

| Anti-Pattern Check | Verdict | Line Citation | Analysis & Operational Context |
|---|---|---|---|
| **Empty state teaches by concrete examples** | **PASS** | Lines 1345–1347 | 6 pre-crafted bilingual chips offer real questions (`"Can I pay salaries on 1 Oct?"`). |
| **Response streams progressively** | **FAIL** | Line 1354 | Complete response calculated synchronously and rendered in a single static block. |
| **Stop button replaces send during generation** | **FAIL** | Line 1333 | No stop affordance exists during LLM or analytical generation. |
| **HITL gate for consequential actions** | **PASS** | Line 1283 | WhatsApp chasing operates via client-side `wa.me` links; zero autonomous messaging. |
| **Grounded vs boundary refusal display** | **PASS** | Lines 1356–1364 | Tags queries clearly: `From your books`, `Outside what I do`, `Not available yet`. |
| **Vernacular summary callouts** | **PASS** | Lines 1370–1388 | Crisp Devanagari cards (`💡 सरल समझ`) break down complex accounting answers. |
| **Conversation history & thread continuity** | **FAIL** | Lines 1351–1355 | Zero session history; asking a new question immediately overwrites previous answer. |
| **Search placeholder names explicit scope** | **PASS** | Line 1332 | Input placeholder specifies scope: `"For example: who owes me the most?"`. |

---

## 9. End-to-End Critical User Journey (CUJ) Friction Maps

### CUJ 1: First-Run Onboarding & Account Aggregator Setup
**Actor**: Prakash Kale (FMCG Distributor)  
**Goal**: Connect bank statements and Tally XML; verify solvency in $< 10$ minutes.

```
Step 1: Consent (page_setup, Step 1)
├── Reads: "What we read" vs "What we never do" (Clear trust articulation)
└── Action: Clicks "Agree and check my books" ──► Advances to Step 2 [PASS]

Step 2: Check your books (page_setup, Step 2)
├── Inspects: Bank lines read (13,359), running balance ties (Yes)
├── Action: Uploads live statement CSV via st.file_uploader
├── Observes: Parse success preview table
└── Action: Clicks "Continue" ──► Advances to Step 3 [PASS]

Step 3: Key numbers (page_setup, Step 3)
├── Reads: Discovered CC Limit (₹25L), Payroll repeating day (1st)
├── Notice: Copy says "Confirm them, or adjust them with your accountant"
├── Friction Point: No input fields exist! Values are static read-only text! [WARN]
├── Action: Clicks "Back" to check file uploaded in Step 2
└── 🚨 FATAL BREAKDOWN: Step 2 renders blank! Upload preview is WIPED OUT! [FAIL]
```

---

### CUJ 2: Monday Morning 60-Second Cash Triage
**Actor**: Dr. Kavya Hegde (Clinic Partner)  
**Goal**: Check if clinic has enough liquidity to pay dental suppliers and staff salaries.

```
Step 1: App Launch (page_overview)
├── Observes: Hero Metric "Cash you can use today: ₹15.20 Lakh" [PASS]
├── Listens: 1-click Web Speech daily audio briefing in English/Hindi [PASS]
└── Observes: "Needs you today" action row for Salary Coverage [PASS]

Step 2: Investigate Shortfall
├── Action: Clicks "See the answer" action link in Salary row
└── System Action: Switches page to /ask and pre-fills salary question [PASS]

Step 3: Consult Copilot
├── Observes: Grounded calculation citing closing balance and staff payroll [PASS]
├── Reads: Colloquial Hindi summary card (💡 सरल समझ) [PASS]
├── Action: Wishes to return to Overview to check Receivables
└── 🚨 FRICTION POINT: No breadcrumb or back button! Browser Back resets state! [WARN]
```

---

### CUJ 3: Weekly Reconciliation & Match Review
**Actor**: Rajesh (Part-Time Accountant / CA Executive)  
**Goal**: Reconcile 5 suggested receipt matches and clear the review queue.

```
Step 1: Review Queue Access (page_review)
├── Observes: Sidebar badge "Review · 5" [PASS]
└── Inspects: AgGrid table with 5 pending suggestions and questions [PASS]

Step 2: Inspect Suggestion
├── Action: Clicks Row 1 (₹45,200 from Om Kirana)
├── Detail Pane Updates: Shows exact matching invoice inv-902 and bank narration [PASS]
└── Verification: Match satisfies Decision 60 rules [PASS]

Step 3: Clear the Match
├── Action: Moves cursor to click primary action button [Accept]
└── 🚨 FATAL BREAKDOWN: [Accept] button is DISABLED (disabled=True)!
    Tooltip: "Posting is wired in the next build; v1 is read-only."
    Result: Rajesh CANNOT clear the queue! Badge remains "5" forever! [FAIL]
```

---

### CUJ 4: Evening Cash Till Close & Field Slip Ingestion
**Actor**: Counter Cashier / Prakash Kale  
**Goal**: Balance the physical cash drawer and record salesman collection slips.

```
Step 1: Open Cash Book (page_cash_book)
├── Role: Counter staff ──► Locks behind PIN prompt [PASS]
├── Action: Enters PIN "0000" ──► Unlocks till view [PASS]
└── Observes: Today's Drawer tiles (Counted, Expected, Till Status) [PASS]

Step 2: Execute Day-Close
├── Action: Clicks primary button "Close the day" ──► Opens modal dialog [PASS]
├── Form: Fills in Opening Cash, Takings, Hamali expenses, Counted cash
├── Action: Clicks "Record in cash book"
├── Feedback: Green toast pops up: "Recorded locally in Cash Book" [PASS]
└── 🚨 FATAL BREAKDOWN: Form is a PLACEBO! Zero data was saved to vault!
    Opening cash was hardcoded! Till status does not update! [FAIL]

Step 3: Scan Handwritten Collection Slip
├── Action: Clicks "Record collection slips" ──► Opens modal dialog [PASS]
├── Action: Uploads photo of crumpled salesman collection slip
├── Vision OCR: Network timeout / API key unconfigured
└── 🚨 FATAL BREAKDOWN: UI falsely announces "Extracted: Laxmi Kirana Stores"!
    Replaces user's receipt with hardcoded mock data! [FAIL]
```

---

## 10. Prioritized Action Plan & Line-by-Line Remediation Matrix

### Priority P0: Critical Trust & Functional Blockers (Immediate Remediation Required)

| Issue ID | File & Line Citation | Exact Defect Description | Required Remediation Pattern |
|---|---|---|---|
| **P0-1** | `app/streamlit_app.py:590, 894, 1009, 1120, 1213, 1322, 1428` | `render_partial_view_notice()` called in void; string discarded; statutory notice never renders. | Replace all calls with: `st.warning(render_partial_view_notice(), icon=":material/visibility_off:")`. |
| **P0-2** | `app/streamlit_app.py:824–836` | `day_close_dialog` inputs are unassigned; `vault.record_galla()` is never called; form is a complete placebo. | Bind inputs to variables (`open_cash`, `takings`, `exp`, `banked`, `phys`), instantiate `GallaEntry`, call `vault.record_galla()`, and rerun. |
| **P0-3** | `app/streamlit_app.py:848–858` | Gemini OCR failure leaves hardcoded dummy data intact and falsely fires `st.success("Extracted: ...")`. | Inspect `ocr_data`: if extraction failed or amount == 0, show `st.error(...)` and leave fields blank. |
| **P0-4** | `app/streamlit_app.py:1202–1204` | Review Queue primary action button `[Accept]` is permanently disabled, creating an operational dead end. | Implement local review actions: `st.button("Mark as Verified (Local)", on_click=...)` and `st.button("Copy Tally Narration")`. |

---

### Priority P1: High-Impact Flow & State Continuity Fixes

| Issue ID | File & Line Citation | Exact Defect Description | Required Remediation Pattern |
|---|---|---|---|
| **P1-1** | `app/streamlit_app.py:1138, 1232` | Grid and ledger filters (`queue_filter`, `chase_filter`) reset on browser refresh or navigation. | Sync filters to `st.query_params["filter"]` and re-read on load. |
| **P1-2** | `app/streamlit_app.py:409–413` | Header "Ask about your cash..." mimics a text input box but executes a disruptive page jump. | Replace with genuine `st.text_input` in header or re-style as an honest navigation action chip. |
| **P1-3** | `app/streamlit_app.py:1351–1392` | Ask Copilot has single-turn amnesia; submitting a new query completely destroys previous answer. | Maintain `st.session_state["chat_history"]` list and render as a chronological stream of message cards. |
| **P1-4** | `app/streamlit_app.py:1546` | Setup Guide Step 2 loses live statement parse cache when navigating to Step 3 and back. | Cache `parse_res` in `st.session_state["uploaded_statement_cache"]`. |
| **P1-5** | `app/streamlit_app.py:1243–1246` | Filter zero-result state unconditionally displays 30-month Limitation Act advice with no "Clear filter" CTA. | Check active filter: show Limitation copy only for `Over 30 months`; add `st.button("Clear filters")`. |

---

### Priority P2: Ergonomic, Responsive & Visual Refinements

| Issue ID | File & Line Citation | Exact Defect Description | Required Remediation Pattern |
|---|---|---|---|
| **P2-1** | `app/streamlit_app.py:578` | Embedded iframe in `daily_print_dialog` has fixed height=450 with scrolling=True, causing nested scroll trap. | Remove iframe scrolling; render printable layout natively or auto-expand container height. |
| **P2-2** | `app/streamlit_app.py:1143–1169` | AgGrid Review queue retains dual-column master-detail layout on small viewports without mobile collapse. | Enforce single-column card collapse below 768px; hide technical `Rule` column by default. |
| **P2-3** | `app/streamlit_app.py:917–922` | Counter staff PIN unlock is transient and lost on page switch. | Persist `st.session_state["staff_unlocked"] = True` for the duration of the browser session. |
| **P2-4** | `app/streamlit_app.py:1390–1392` | Citations expander dumps an unformatted comma-separated wall of IDs. | Render sources as a structured grid of invoice chips with rupee amounts and dates. |
| **P2-5** | `app/streamlit_app.py:459–462` | Web Speech API triggers a blocking native browser `alert()` on unsupported devices. | Replace `alert()` with a quiet inline fallback note. |

---

## 11. Conclusion

The `ps11-copilot` application possesses a deeply considered domain core: its dual-plane data architecture, Indian currency ergonomics, and strict read-only boundaries are masterfully aligned with the operational realities of Indian SME owner-operators.

However, the user experience currently suffers from significant interaction gaps: a broken statutory notification mechanism, placebo dialog submissions, decoy navigation search bars, filter amnesia, and disabled primary action buttons. 

By executing the prioritized remediation matrix outlined in this report—specifically addressing the P0 trust blockers and restoring state continuity across the navigation stack—`ps11-copilot` will graduate from an impressive functional prototype into a bulletproof, production-grade cash-flow cockpit that owner-operators can trust with their livelihoods.
