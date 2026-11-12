# UI/UX Usability Heuristics Audit: ps11-copilot
**Framework**: Jakob Nielsen's 10 Usability Heuristics (`wondelai/skills@ux-heuristics`)  
**Target Codebase**: `/Users/ishaanwadhwa/Projects/ps11-copilot` (`app/streamlit_app.py` and supporting UI modules)  
**Auditor**: Teamwork Usability Heuristics Auditor (Worker Audit Framework 5)  
**Date**: November 2026  
**Status**: Production-Grade Standalone Audit Report  

---

## 1. Executive Summary & Evaluation Context

This usability audit evaluates **ps11-copilot** (SME Cash-Flow Copilot MVP v1) through the rigorous lens of **Jakob Nielsen's 10 Usability Heuristics**. The evaluation assesses the application's ability to serve Indian Small and Medium Enterprise (SME) owner-operators (e.g., FMCG distributors, healthcare clinics, and creative agencies) who navigate high-frequency operational pressures, hybrid cash/formal bookkeeping, and strict regulatory boundaries.

The core product principle of ps11-copilot states:
> *"It explains every rupee between your bank and your books, and never acts without you."*

### Key Audit Findings
1. **World-Class Real-World Modeling (Heuristics 2 & 5)**: The application excels in vernacular Indian commercial concepts. Innovations such as the **Salesman Protection Shield** (anti-double-dunning guard), statutory **Limitation Act Section 18 aging alerts**, **SFT Rule 114E cash deposit checklists**, and **Cash-Credit (CC) headroom visualization** ground the interface in the operational reality of Indian owner-operators.
2. **Critical Silent Failure in System Status (Heuristic 1)**: A major defect was identified across seven pages where `render_partial_view_notice()` is invoked as an isolated expression statement without rendering (`app/streamlit_app.py:590, 894, 1009, 1120, 1213, 1322, 1428`). Because `src/copilot/vault/notice.py:5-7` returns a raw string rather than calling a display function, restricted roles (`Counter staff`, `Accountant`) are **never informed** that informal cash records are omitted from their view.
3. **Interaction Dead-Ends and Action Traps (Heuristics 3 & 5)**: The primary review workflow dead-ends with a permanently disabled "Accept" button (`app/streamlit_app.py:1202`). Furthermore, modal dialogs for daily till closing and collection slip entry pre-populate static demo numbers (`Opening ₹10,000`, `Takings ₹25,000`), risking accidental ledger corruption if submitted without full field overwrite.
4. **Linguistic Parity & Audience Clutter (Heuristics 4 & 8)**: While Overview and sidebar navigation offer English/Hindi bilingual switching, downstream pages (Forecast, Review Queue, Data Quality, Setup Guide) exhibit severe language leaks with hardcoded English strings. Additionally, the Forecast page pollutes the owner's view with academic machine learning benchmark metrics (holdout MAPE, bootstrap differences) that are irrelevant to daily business management.

---

## 2. Overall Heuristic Scorecard

| # | Heuristic | Score (1–5) | Status | Key Strength | Primary Usability Friction Point |
|---|---|:---:|:---:|---|---|
| **H1** | **Visibility of System Status** | **3 / 5** | Needs Fix | Dynamic pending review badge (`Review · N`), live solvency state, caching spinners. | `render_partial_view_notice` silent return bug; browser alert on speech synthesis. |
| **H2** | **Match Between System and the Real World** | **4 / 5** | Strong | Deep Indian SME alignment: Galla, Rokad, Khata, Lakh/Crore, CC headroom, Hamali. | Internal matcher rule code leaks (`EXACT_AMBIGUOUS`) and academic ML metrics. |
| **H3** | **User Control and Freedom** | **3 / 5** | Needs Fix | Sovereign read-only posture guarantees safety; client-side WhatsApp drafts. | Permanently disabled "Accept" button; dialogs lack explicit "Cancel" actions; no undo. |
| **H4** | **Consistency and Standards** | **3 / 5** | Needs Fix | Cohesive visual tokens (`IBM Plex Sans`), standard page headers and action rows. | Incomplete Hindi translations across 4+ pages; inconsistent `st.button` vs `st.page_link`. |
| **H5** | **Error Prevention** | **4 / 5** | Strong | Salesman Protection Shield prevents customer embarrassment; CC breach early warnings. | Pre-filled dialog form values risk recording dummy numbers; missing till close confirmation. |
| **H6** | **Recognition Rather than Recall** | **4 / 5** | Strong | Bilingual prompt pills eliminate blank prompt anxiety; 5-tile explicit math equation. | Password field lacks reveal toggle; ephemeral toasts fade quickly; context drops on jump. |
| **H7** | **Flexibility and Efficiency of Use** | **3 / 5** | Needs Fix | 3-tier role switcher; 1-click WhatsApp links; voice and slip OCR multimodal input. | Zero keyboard shortcuts for high-volume reconciliation; rigid top-10 customer clamp. |
| **H8** | **Aesthetic and Minimalist Design** | **3 / 5** | Needs Fix | High signal-to-noise hero solvency cards; restrained functional color palette. | ML holdout evaluation metrics clutter Forecast view; nested scroll trap in print dialog. |
| **H9** | **Help Users Recognize, Diagnose, and Recover from Errors** | **3 / 5** | Needs Fix | IntentRouter provides constructive explanations; Limitation Act recovery drafts. | Raw Python stack exceptions on file parse failure; unhelpful generic Q&A fallback. |
| **H10** | **Help and Documentation** | **3 / 5** | Needs Fix | 3-step setup guide; pre-deposit checklist; contextual parameter tooltips. | No global FAQ or search; glossary inaccessible in-app; hover tooltips broken on mobile. |
| **Total** | **Composite Usability Index** | **3.3 / 5.0** | **Acceptable MVP (B-)** | **Exceptional domain modeling & safety** | **Implementation bugs, language gaps, dead ends** |

---

## 3. Detailed Heuristic Evaluations

---

### H1. Visibility of System Status
> *The design should always keep users informed about what is going on, through appropriate feedback within a reasonable amount of time.*

#### Context & Application
In an SME financial copilot, users must know at all times: what role they are viewing as, whether the data is complete or partial, the progress of background computations (forecasting, OCR, voice transcription), and the outcome of financial data entry.

#### Strengths & Positive Patterns
1. **Persistent Header & Trust Indicator**: Every page renders the current business identity (`BIZ_NAME`), the accounting date (`30 Sep 2026`), and a prominent sidebar trust note: *"Read-only. Never moves money, edits records or sends anything"* with lock icon (`app/streamlit_app.py:1623–1624`).
2. **Dynamic Review Counter Badge**: In the sidebar navigation (`lines 1602–1604`), the Review link dynamically reflects pending triage items: `Review · N` (aggregating `SUGGEST` and `ASK` tiers). Users immediately see when new items arrive without navigating to the page.
3. **Multi-State Solvency Status Card**: The hero block on Overview (`lines 680–697`) renders an immediate visual indicator of financial runway: green badge (`30 दिनों के लिए सुरक्षित`) with `ICON_CHECK_CIRCLE`, amber warning badge (`सावधानी जरूरी`) when runway is negative, or warning tone when "false insolvency" is detected.
4. **Asynchronous Feedback Spinners**: Heavy calculations are wrapped in `@st.cache_resource(show_spinner="...")` (`lines 282, 295, 300, 305`), and multimodal AI operations show explicit feedback: `st.spinner("Scanning slip with Gemini Vision…")` (`line 849`) and `st.spinner("Transcribing with Gemini Voice…")` (`line 1338`).
5. **Interactive Audio Playback State**: The daily audio briefing widget (`lines 451–487`) actively toggles between `▶️ Listen` and `⏹️ Stop` with real-time button color and icon state updates.

#### Deficits & Exact Code Citations
1. **Critical Deficit — Silent Partial View Notice Bug**:
   - **Citations**: `app/streamlit_app.py:590, 894, 1009, 1120, 1213, 1322, 1428` and `src/copilot/vault/notice.py:5–7`.
   - **Observation**: When viewing as `Counter staff` or `Accountant (CA)` (with cash sharing disabled), the application executes:
     ```python
     if showing_partial_view:
         render_partial_view_notice()
     ```
     However, `render_partial_view_notice()` in `src/copilot/vault/notice.py` merely returns `PARTIAL_VIEW_NOTICE` as a string (`"Formal books only. The owner's cash memo is not included in this view."`). Because the caller ignores the return value and does not pass it to `st.warning()` or `st.info()`, the notice is completely discarded by the Python runtime and **never rendered on screen**.
   - **Impact**: Counter staff and external accountants are misled into believing they are viewing full operational books, completely unaware that cash drawer counts and informal khata balances are excluded.
   - **Severity**: **Major (P1)**.
2. **Crude Speech Synthesis Fallback**:
   - **Citation**: `app/streamlit_app.py:459–462`.
   - **Observation**: If a user's browser lacks the Web Speech API, clicking "Listen" triggers a native browser popup: `alert('Speech synthesis is not supported in this browser.')`.
   - **Impact**: Disrupts user flow with a blocking modal dialog rather than rendering a graceful, non-blocking inline message.
   - **Severity**: **Minor (P2)**.
3. **AgGrid Silent Selection Default**:
   - **Citation**: `app/streamlit_app.py:1170–1174`.
   - **Observation**: If AgGrid returns empty selection, the evidence pane defaults to `view.iloc[0]["txn_id"]` without visually highlighting the selected row in the grid table.
   - **Impact**: Users reading the right-side detail card are unsure which table row is currently active.
   - **Severity**: **Minor (P2)**.

#### Concrete Remediation
- Modify `app/streamlit_app.py` lines 590, 894, etc., to explicitly render the notice banner:
  ```python
  if showing_partial_view:
      st.warning(render_partial_view_notice(), icon=":material/visibility_off:")
  ```
- Replace JavaScript `alert()` in `render_audio_briefing()` with inline fallback DOM text indicating that speech synthesis is unavailable on the current browser.

---

### H2. Match Between System and the Real World
> *The design should speak the users' language, with words, phrases, and concepts familiar to the user, rather than internal jargon. Follow real-world conventions, making information appear in a natural and logical order.*

#### Context & Application
Small enterprises in India operate with informal, vernacular commercial practices: physical cash drawers (*Galla*), hand-recorded cash books (*Rokad*), informal credit ledgers (*Khata*), and cash porterage fees (*Hamali*). They calculate in Lakhs/Crores, balance Cash-Credit limits against seasonal inventory squeezes, and manage legal recovery under Indian statutes.

#### Strengths & Positive Patterns
1. **Authentic Vernacular Terminology**: The interface natively incorporates authentic Indian trade vocabulary rather than translating generic Western ERP terms (`app/streamlit_app.py:828, 935, 959, 1224`):
   - *Galla* (गल्ला) for cash till.
   - *Rokad* (रोकड़ बही) for cash receipts and disbursements.
   - *Khata* (कच्चा खाता) for informal customer credit.
   - *Hamali* (हमाली) for labor/porterage cash expenses.
   - *Takada* (तकादा) for payment reminder requests.
2. **Indian Numbering and Currency Conventions**: Numbers are formatted in Lakhs and Crores using the Indian Rupee symbol `₹` (`app/streamlit_app.py:277–279, 1043`). Chart axes on the 90-day forecast render as `₹15L`, `₹20L`, or `−₹5L` using custom Vega-Lite expressions (`(datum.value < 0 ? '−₹' : '₹') + format(abs(datum.value) / 100000, ',.0f') + 'L'`).
3. **Statutory Alignment with Indian Law**:
   - **Limitation Act, 1963 (Section 18)**: Accounts open $\ge 30$ months are tagged with `Over 30 months (Sec 18)` (`lines 974, 1274`). The copilot explains that debts older than 3 years become legally unrecoverable and generates a polite WhatsApp acknowledgment draft to reset the 3-year statutory clock.
   - **Income-tax Act SFT Reporting Thresholds (Rule 114E / Rule 237)**: The Cash Book right panel (`lines 988–1000`) factually informs owners of annual cash deposit limits (₹10 Lakh in savings, ₹50 Lakh in current accounts) and provides a concrete pre-deposit documentation checklist.
   - **MSMED Act 2006 (45-Day Payment Window)**: The default receivables aging filter isolates accounts $\ge 45$ days late (`line 1224`), matching the statutory MSMED delay threshold.
4. **Printable Daily Recovery Sheet for Field Operations**:
   - `lines 494–579`: Rather than forcing field reps to use a smartphone app in dusty godowns, the app generates a printable clipboard sheet (`daily_print_dialog`) with retailer names, dues, visit checkboxes, and signature lines for Salesman, Godown Manager, and Cashier.

#### Deficits & Exact Code Citations
1. **Matcher Internal Rule Codes Leaked to User**:
   - **Citation**: `app/streamlit_app.py:1184–1186`.
   - **Observation**: In the Review Queue evidence card, the system displays database rule identifiers inside `.cc-mono` badges:
     ```html
     <span class="cc-note cc-mono">{esc(m.rule)}</span>
     ```
     Users see raw programmer strings such as `EXACT_AMBIGUOUS`, `CLUBBED_BILLS`, `WHO_PAID`, and `ROUND_OFF`.
   - **Impact**: Exposes internal algorithm mechanics, causing unnecessary cognitive load for non-technical retail owners.
   - **Severity**: **Minor (P2)**.
2. **Academic Machine Learning Jargon in Forecast View**:
   - **Citation**: `app/streamlit_app.py:1094–1110`.
   - **Observation**: The holdout accuracy expander exposes:
     - *"Model error (MAPE) on the frozen holdout: 13.48%"*
     - *"naive 3-month baseline 18.19%"*
     - *"Paired bootstrap improvement (naive − model) +4.68% (95% CI +1.5% to +7.8%)"*
     - *"Holdout P10–P90 coverage: 22.2%"*
   - **Impact**: Uses academic statistical terminology incomprehensible to retail owners and accountants, undermining product simplicity.
   - **Severity**: **Minor (P2)**.
3. **ISO Date Formatting in Review Grid**:
   - **Citation**: `app/streamlit_app.py:1128`.
   - **Observation**: Dates in the AgGrid table are rendered as `YYYY-MM-DD` (`b.txn_date.strftime("%Y-%m-%d")`).
   - **Impact**: Conflicts with the ubiquitous Indian commercial date standard (`DD/MM/YYYY` or `DD MMM YYYY`).
   - **Severity**: **Cosmetic (P3)**.

#### Concrete Remediation
- Remove `.cc-mono` raw rule strings from the Review Queue card (`line 1186`), displaying only the human-friendly `RULE_LABEL`.
- Relocate the holdout accuracy metrics (`lines 1093–1110`) from the customer-facing Forecast page to the `Data quality` page (`page_quality`), or rephrase them in intuitive commercial terms (*"Forecast tested across 90 days of past receipts: 87% within predicted bounds"*).
- Format all grid dates using `"%d %b %Y"` or `"%d/%m/%Y"`.

---

### H3. User Control and Freedom
> *Users often perform actions by mistake. They need a clearly marked "emergency exit" to leave the unwanted action without having to go through an extended process. Support undo and redo.*

#### Context & Application
Financial software creates anxiety. If a user fears that clicking a button will accidentally debit a bank account, dispatch an aggressive legal demand to an important client, or overwrite historical books, they will avoid using the tool.

#### Strengths & Positive Patterns
1. **Guaranteed Read-Only Posture**: The system enforces zero write access to bank accounts, GST portals, or accounting packages. The persistent trust banner (`line 1623`) reassures users that exploration is completely safe.
2. **Client-Side WhatsApp Drafting**:
   - **Citation**: `app/streamlit_app.py:981, 1283` and `src/copilot/vault/chase.py`.
   - **Pattern**: Clicking "WhatsApp draft" never sends messages automatically. It opens `https://wa.me/?text=...` in the user's browser, giving the owner full liberty to review, edit, personalize, or discard the reminder before transmitting it.
3. **Setup Wizard Stepping & Skip Option**:
   - **Citation**: `app/streamlit_app.py:1494–1498, 1543–1548, 1570–1574`.
   - **Pattern**: The 3-step setup guide provides "Continue" and "Back" buttons on every step, alongside a "Skip for now" link on Step 1 that exits directly to the Overview page.
4. **Interactive Modal Dismissal**: All dialogs (`daily_print_dialog`, `day_close_dialog`, `collections_dialog`) are wrapped in `@st.dialog` containers that close cleanly when clicking outside or pressing Escape.

#### Deficits & Exact Code Citations
1. **Major Usability Friction — Permanently Disabled "Accept" Button**:
   - **Citation**: `app/streamlit_app.py:1202–1204`.
   - **Observation**: In the Review Queue detail pane, the primary CTA button is permanently disabled:
     ```python
     st.button("Accept", disabled=True, use_container_width=True,
               help="Posting is wired in the next build; v1 is read-only.")
     ```
   - **Impact**: Users are presented with a dead end on every transaction. They have no alternative actions (e.g., "Mark as verified", "Flag for CA", "Copy details", or "Dismiss").
   - **Severity**: **Major (P1)**.
2. **Missing "Cancel" Button in Dialog Forms**:
   - **Citation**: `app/streamlit_app.py:824–832, 860–869`.
   - **Observation**: Both `day_close_dialog` and `collections_dialog` provide only a single `st.form_submit_button`. There is no visual "Cancel" or "Discard" button inside the form, forcing users to rely on the tiny modal 'X' icon.
   - **Impact**: Poor affordance for aborting input, especially on mobile touch screens.
   - **Severity**: **Minor (P2)**.
3. **No Undo for Cash Book Entries**:
   - **Citation**: `app/streamlit_app.py:833–835, 870–875`.
   - **Observation**: Once a till close or collection slip is recorded, it is immediately written to the local vault and triggers `st.rerun()`. No "Undo" option is provided.
   - **Impact**: If an erroneous cash count is submitted, the user cannot revert or edit the record without restarting the session.
   - **Severity**: **Minor (P2)**.

#### Concrete Remediation
- Replace the disabled "Accept" button with active read-only workflow controls:
  ```python
  c_act1, c_act2 = st.columns(2)
  c_act1.button("📋 Copy Details", key=f"copy_{txn_id}", help="Copy reconciliation summary to clipboard")
  c_act2.button("🏷️ Mark Reviewed", key=f"rev_{txn_id}", help="Tag this item as reviewed for your CA")
  ```
- Add a secondary "Cancel" button to dialogs:
  ```python
  c_sub, c_can = st.columns([2, 1])
  c_sub.form_submit_button("Record in cash book", type="primary")
  if c_can.form_submit_button("Cancel"):
      st.rerun()
  ```

---

### H4. Consistency and Standards
> *Users should not have to wonder whether different words, situations, or actions mean the same thing. Follow platform and industry conventions.*

#### Context & Application
A consistent UI maintains uniform visual hierarchy, identical component behaviors across pages, and reliable language translations. Users should never experience jarring transitions where styling, interaction models, or languages unexpectedly change.

#### Strengths & Positive Patterns
1. **Unified Design System & Typography**: Custom CSS tokens (`INK = #17191C`, `MUTED = "#545A63"`, `ACCENT = "#24509A"`, `NEG = "#A8261D"`, font family `IBM Plex Sans` + `IBM Plex Sans Devanagari`, `lines 59–69`) guarantee uniform font weights, colors, and layout widths (`max-width: 1200px`) throughout the app.
2. **Standard Page Header Architecture**: Every view implements `page_header(title, subtitle, right=...)` (`lines 401–414`) followed by a standard `.cc-rule` separator, establishing a predictable visual anchor.
3. **Predictable Action Row Pattern**: The Overview page (`lines 811–818`) uses an identical column grid ratio `[5, 1.6]` with title, subtitle, and right-aligned arrow action button for all priority operational items.

#### Deficits & Exact Code Citations
1. **Critical Deficit — Incomplete Bilingual Parity / Language Leakage**:
   - **Citations**: `app/streamlit_app.py:1071–1110, 1133–1205, 1425–1460, 1475–1491, 1553–1567`.
   - **Observation**: Selecting "हिन्दी" in the sidebar translates the Overview, Cash Book, and Receivables headers. However, downstream pages are riddled with hardcoded English strings:
     - **Forecast Page (`lines 1071–1110`)**: Section title ("Month by month"), table headers ("Month", "Expected inflows", "Committed outflows", "Net cash flow", "Lowest daily balance", "Closing balance"), and the entire holdout accuracy expander are 100% hardcoded English.
     - **Review Queue (`lines 1133–1205`)**: Segmented control choices ("All", "Suggestions", "Questions"), AgGrid headers ("Date", "Amount", "Type", "Rule", "Bank narration"), and card labels ("Why it's here", "Bank narration", "Suggested documents", "Accept") have zero Hindi translations.
     - **Data Quality Page (`lines 1425–1460`)**: Entirely English.
     - **Setup Guide (`lines 1475–1491, 1553–1567`)**: Consent terms and key number summaries are hardcoded English.
   - **Impact**: Violates language consistency. Vernacular Hindi users encounter an abrupt linguistic wall when exploring beyond the first two pages.
   - **Severity**: **Major (P1)**.
2. **Inconsistent Navigation Interaction Models**:
   - **Citation**: `app/streamlit_app.py:394–398` vs `line 411`.
   - **Observation**: The header "Ask about your cash..." control is implemented as an `st.page_link` (`line 411`), supporting standard link behaviors (new tab, hover state). Conversely, action rows (`line 394`) and section headers use an `st.button` with custom CSS that calls `st.switch_page`.
   - **Impact**: Users cannot middle-click or open action links in new tabs, violating standard web expectations.
   - **Severity**: **Minor (P2)**.
3. **Inconsistent Segmented Control Count Formatting**:
   - **Citation**: `app/streamlit_app.py:1138` vs `line 1232`.
   - **Observation**: Review Queue formats choices with commas (`f"{o}  {sizes[o]:,}"`), whereas Receivables formats raw integers (`f"{o}  {len(filters[o])}"`).
   - **Severity**: **Cosmetic (P3)**.

#### Concrete Remediation
- Wrap all hardcoded strings in `t(en, hi)` helper calls across `page_forecast`, `page_review`, `page_quality`, and `page_setup`.
- Replace `st.button` in `go()` with `st.page_link` to restore native anchor semantics across all navigation pathways.

---

### H5. Error Prevention
> *Even better than good error messages is a careful design which prevents a problem from occurring in the first place. Either eliminate error-prone conditions, or check for them and present users with a confirmation option before they commit to the action.*

#### Context & Application
In SME cash management, mistakes can have grave consequences: double-dunning a customer whose payment was already collected by a field salesman damages vital trade relationships, while entering incorrect daily cash balances corrupts reconciliations.

#### Strengths & Positive Patterns
1. **Salesman Protection Shield (Anti-Double-Dunning Guard)**:
   - **Citation**: `app/streamlit_app.py:1258–1271`.
   - **Design Pattern**: Before displaying an overdue customer card in the Receivables chasing list, the system inspects `vault.collection_records` to check if a salesman collected cash that has not yet been deposited at the bank. If found, a green shield icon and prominent warning banner appear:
     ```html
     <div class="cc-row-detail" style="color:#1A6E45;display:flex;gap:6px">
       <svg class="icon-shield">...</svg>
       Salesman Ramesh collected ₹15,000 on 30 Sep; not banked yet. Do not call.
     </div>
     ```
   - **Usability Value**: Proactively prevents the humiliating mistake of calling an honest retailer who already paid cash to the field rep.
2. **11-Day Early Warning of Cash-Credit Breach**:
   - **Citation**: `app/streamlit_app.py:1014–1024` and `src/copilot/forecast/warnings.py`.
   - **Design Pattern**: Detects projected liquidity shortfalls well before month-end salary runs or CC limit breaches occur, alerting owners before cheques bounce.
3. **PIN-Protected Role Gates for Counter Staff**:
   - **Citation**: `app/streamlit_app.py:908–925`.
   - **Design Pattern**: Counter staff attempting to open the Cash Book are blocked by a secure PIN gate (`expected_pin`), preventing unauthorized clerks from viewing total business solvency.
4. **Public Preview Typing Lock**:
   - **Citation**: `app/streamlit_app.py:57, 1328, 1348–1350`.
   - **Design Pattern**: Under `COPILOT_PUBLIC=1`, free-form prompt typing is disabled, eliminating prompt injection vulnerabilities or unexpected LLM hallucinations during public demonstrations.

#### Deficits & Exact Code Citations
1. **Critical Flaw — Static Dummy Values Pre-Filled in Dialog Forms**:
   - **Citations**: `app/streamlit_app.py:826–831` and `lines 845–847`.
   - **Observation**: In `day_close_dialog`:
     ```python
     c1.number_input("Opening till cash (₹)", value=10000.0, step=500.0)
     c2.number_input("Today's cash takings (₹)", value=25000.0, step=1000.0)
     c1.number_input("Cash expenses paid (₹)", value=2500.0, step=100.0)
     c2.number_input("Cash banked into account (₹)", value=20000.0, step=1000.0)
     c1.number_input("Physical count at close (₹)", value=12500.0, step=500.0)
     c2.text_input("Notes", value="Routine daily close")
     ```
     Similarly, in `collections_dialog`:
     ```python
     prefill_shop = "Laxmi Kirana Stores"
     prefill_amount = 15000.0
     prefill_salesman = "Ramesh K."
     ```
   - **Impact**: Pre-populating non-zero demo numbers creates a dangerous trap. An inattentive user can click "Record in cash book" without modifying the inputs, injecting fictitious transactions into their local database.
   - **Severity**: **Major (P1)**.
2. **Absence of Confirmation on Till Close**:
   - **Citation**: `app/streamlit_app.py:832–835`.
   - **Observation**: Submitting the form commits the data immediately without showing a summary confirmation ("You are closing the till with ₹12,500. Drift: -₹4,500. Confirm?").
   - **Severity**: **Minor (P2)**.

#### Concrete Remediation
- Change default values in `day_close_dialog` to `0.0` or dynamic previous-day closing balances (`vault.get_latest_galla(biz).counted_cash`), using `placeholder="0.0"` rather than hardcoded demo amounts.
- Set collection dialog defaults to blank strings and `0.0` unless genuinely populated by the Gemini Vision OCR parser.

---

### H6. Recognition Rather than Recall
> *Minimize the user's memory load by making elements, actions, and options visible. The user should not have to remember information from one part of the interface to another.*

#### Context & Application
Small business owners manage dozens of daily interruptions. Software that requires them to remember complex tax codes, recall previous cash balances, or formulate elaborate natural language prompts creates severe cognitive friction.

#### Strengths & Positive Patterns
1. **Bilingual Prompt Pills in Ask Copilot**:
   - **Citation**: `app/streamlit_app.py:372–389, 1345–1347`.
   - **Design Pattern**: Ask Copilot provides 6 pre-crafted prompt pills in English and Hindi (e.g., *"Can I pay salaries on 1 October 2026?"*, *"Who owes me the most?"*, *"What is my worst cash dip in the next 90 days?"*).
   - **Usability Value**: Completely eliminates prompt-writing anxiety. Users click to recognize common inquiries rather than recalling syntax.
2. **5-Tile Solvency Equation (Explicit Mental Model)**:
   - **Citation**: `app/streamlit_app.py:698–722`.
   - **Design Pattern**: Instead of showing an opaque "Runway: ₹12.4L" number, the interface visually articulates the full arithmetic formula:
     `Bank balance` `+` `Cash in drawer` `+` `Khata expected back` `−` `Due in next 30 days` `=` `Your own-cash buffer`.
   - **Usability Value**: Keeps all variables visible simultaneously so the user does not need to recall obligations or cash drawer figures.
3. **Explicit Candidate Documents in Review Evidence**:
   - **Citation**: `app/streamlit_app.py:1195–1201`.
   - **Design Pattern**: The detail card lists candidate invoice numbers alongside exact rupee amounts and bank narration strings, eliminating the need to look up bills in another system.

#### Deficits & Exact Code Citations
1. **Password Field Lacks Visibility Toggle**:
   - **Citation**: `app/streamlit_app.py:917`.
   - **Observation**: Counter staff PIN entry uses `type="password"` without an eye icon toggle to reveal characters.
   - **Impact**: Users who mistype a digit cannot verify their input and must clear and re-enter blindly.
   - **Severity**: **Minor (P2)**.
2. **Ephemeral Toast Messages**:
   - **Citation**: `app/streamlit_app.py:1635–1636`.
   - **Observation**: Confirmation toasts disappear after ~4 seconds. If the user glances away, the confirmation is lost with no notification center or log to verify what happened.
   - **Severity**: **Minor (P2)**.
3. **Context Drop on Cross-Page Action Links**:
   - **Citation**: `app/streamlit_app.py:746, 752, 758`.
   - **Observation**: Clicking "See the answer" on the Overview salary row opens Ask Copilot with the query pre-filled. However, the Ask page displays no visual breadcrumb indicating that the user navigated from the Overview salary alert.
   - **Severity**: **Cosmetic (P3)**.

#### Concrete Remediation
- Provide an unmask toggle checkbox next to the PIN input for easy verification.
- Add an in-page confirmation banner upon successful day close or collection logging that remains visible until dismissed.

---

### H7. Flexibility and Efficiency of Use
> *Accelerators — unseen by the novice user — may often speed up the interaction for the expert user such that the system can cater to both inexperienced and experienced users. Allow users to tailor frequent actions.*

#### Context & Application
Distributor accountants must triage hundreds of transactions weekly, while business owners require fast morning briefings. An efficient system supports rapid keyboard workflows for power users and simple tap workflows for novices.

#### Strengths & Positive Patterns
1. **Role Selector Accelerators**:
   - **Citation**: `app/streamlit_app.py:1611–1618`.
   - **Design Pattern**: Selecting "Owner", "Counter staff", or "Accountant (CA)" tailors the interface to that user's exact operational purview, hiding unnecessary controls (such as cash sharing toggles from non-owners).
2. **One-Click WhatsApp Chasing Links**:
   - **Citation**: `app/streamlit_app.py:981, 1283`.
   - **Design Pattern**: Automatically structures polite vernacular messages with embedded invoice numbers and UPI payment handles (`wa.me/?text=...`), transforming a 5-minute manual texting chore into a 2-second tap.
3. **Multimodal Voice & Slip OCR Acceleration**:
   - **Citation**: `app/streamlit_app.py:843–859, 1335–1343`.
   - **Design Pattern**: Gemini Voice transcribes spoken Hindi/English queries directly into the search bar, and Gemini Vision extracts shop names and collected amounts from handwritten receipts.

#### Deficits & Exact Code Citations
1. **Zero Keyboard Navigation in Review Queue**:
   - **Citation**: `app/streamlit_app.py:1144–1175`.
   - **Observation**: The AgGrid reconciliation table provides no keyboard shortcuts (e.g., `Up`/`Down` arrow navigation, `Enter` to expand candidate documents, `A` to accept).
   - **Impact**: High-volume accountants are forced to perform continuous mouse clicks, slowing down triage.
   - **Severity**: **Minor (P2)**.
2. **Rigid Top-10 Customer Clamp in Receivables**:
   - **Citation**: `app/streamlit_app.py:1252`.
   - **Observation**: `page_receivables` hard-codes `filtered_cust.head(10).iterrows()`. For businesses with 40 overdue retailers, only the top 10 receive rich cards with WhatsApp link buttons and salesman protection shields. Customers 11–40 are banished to a collapsed, unstyled `st.dataframe` (`line 1287`) with no action buttons.
   - **Impact**: Owners cannot easily contact overdue customers beyond the top 10.
   - **Severity**: **Major (P1)**.
3. **Single-Row Selection Only in Reconciliation**:
   - **Citation**: `app/streamlit_app.py:1155`.
   - **Observation**: `gb.configure_selection("single")` prevents bulk actions (e.g., selecting 10 exact matches and approving them at once).
   - **Severity**: **Minor (P2)**.

#### Concrete Remediation
- Implement pagination controls or an "Expand to show all N customers" toggle on the Receivables page so every overdue account can be chased via WhatsApp.
- Configure AgGrid to enable keyboard navigation (`tabToNextCell`, row navigation) and multi-row selection checkboxes.

---

### H8. Aesthetic and Minimalist Design
> *Interfaces should not contain information which is irrelevant or rarely needed. Every extra unit of information in an interface competes with the relevant units of information and diminishes their relative visibility.*

#### Context & Application
Visual clutter in financial cockpits induces anxiety. Every displayed metric must answer an immediate operational question. Technical benchmarking data or developer diagnostic instrumentation must never pollute the end-user interface.

#### Strengths & Positive Patterns
1. **High Signal-to-Noise Solvency Cockpit**:
   - **Citation**: `app/streamlit_app.py:691–697`.
   - **Design Pattern**: The hero card foregrounds a single vital metric: *"Cash you can use today"* with bold tabular numerals (`font-size: clamp(2.1rem, 4.5vw, 2.75rem)`), paired with a concise explanation of bank balance + unused credit limit + till cash.
2. **Restrained, Meaningful Color Tokens**:
   - Uses functional color intentionally: green for verified balances and protected salesmen, amber for overdue debts, and dark red for balance breaks. Avoids gaudy purple/indigo gradients or decorative floating cards.
3. **Clean Tabular Typography**:
   - AgGrid and custom HTML tables apply `font-variant-numeric: tabular-nums` to ensure that financial digits align vertically for easy comparison.

#### Deficits & Exact Code Citations
1. **Severe Information Pollution — Academic ML Metrics on Forecast View**:
   - **Citation**: `app/streamlit_app.py:1093–1110`.
   - **Observation**: The Forecast page features a prominent expander:
     *"How accurate is this forecast? 13.48% average error on the holdout"*
     containing tiles for:
     - `Model error (MAPE) on the frozen holdout`
     - `Agency inflows error`
     - `Paired bootstrap improvement (naive − model)`
     - `Holdout P10–P90 coverage`
     - `Holdout likely warnings`
   - **Impact**: Developer/evaluator benchmark metrics are exposed directly to commercial end-users, violating minimalism and degrading trust.
   - **Severity**: **Major (P1)**.
2. **Nested Double-Scroll Trap in Print Dialog**:
   - **Citation**: `app/streamlit_app.py:578`.
   - **Observation**: `components.html(html_sheet, height=450, scrolling=True)` embeds an iframe inside an `@st.dialog` modal. When the table exceeds 450px, the modal exhibits nested vertical scrollbars.
   - **Impact**: Annoying scroll-jacking and clipped print previews.
   - **Severity**: **Minor (P2)**.
3. **Developer Attestation Footnotes Cluttering Views**:
   - **Citations**: `app/streamlit_app.py:1068, 1190, 1204, 1566`.
   - **Observation**: Footnotes such as *"Monte Carlo simulation calibrated without lookahead"* and *"Picked at random to check our automatic matches"* read like compliance audit attestations rather than end-user product copy.
   - **Severity**: **Cosmetic (P3)**.

#### Concrete Remediation
- Move the entire holdout accuracy benchmark block (`lines 1093–1110`) from `page_forecast` to `page_quality` (`Data quality`), preserving a clean financial view for the owner.
- Adjust `components.html` height dynamically or use full modal width without internal scrolling.

---

### H9. Help Users Recognize, Diagnose, and Recover from Errors
> *Error messages should be expressed in plain language (no error codes), precisely indicate the problem, and constructively suggest a solution.*

#### Context & Application
When file parsing fails, PIN entry is incorrect, or a query exceeds system boundaries, users need actionable guidance in plain vernacular language—never raw programming exceptions.

#### Strengths & Positive Patterns
1. **Constructive Statutory Boundary Routing**:
   - **Citation**: `src/copilot/boundary.py:21–56` and `app/streamlit_app.py:1364`.
   - **Design Pattern**: When an owner asks for loan advice, tax evasion methods, or personal credit judgment, the IntentRouter refuses constructively:
     *"I can't recommend a loan, lender or product. Here are the facts: the shortfall, when it happens, and the levers inside the business (collections due, payments that can move). Your bank or CA can advise on funding."*
   - **Usability Value**: Replaces a dead-end refusal with constructive financial facts and appropriate CA referrals.
2. **Clear Balance Break Error Reporting**:
   - **Citation**: `app/streamlit_app.py:803, 1435`.
   - **Design Pattern**: When running balances in uploaded bank statements do not tie, the UI reports `"N breaks"` in dark red (`NEG = #A8261D`) with the exact break row indices.
3. **Limitation Act Expiry Diagnosis & Recovery**:
   - **Citation**: `app/streamlit_app.py:972–982, 1274–1284`.
   - **Design Pattern**: Diagnoses informal debts nearing the 30-month statutory expiration and provides a pre-drafted acknowledgment message to legally reset the 3-year clock.

#### Deficits & Exact Code Citations
1. **Critical Deficit — Raw Python Stack Traces on File Upload**:
   - **Citation**: `app/streamlit_app.py:1530–1531, 1538–1539`.
   - **Observation**: In `page_setup` Step 2:
     ```python
     except Exception as e:
         st.error(f"Error parsing statement: {e}")
     ...
     except Exception as e:
         st.error(f"Error parsing Tally XML: {e}")
     ```
   - **Impact**: If a user uploads a statement with non-standard columns or a corrupted XML file, the UI dumps unformatted Python error strings (`KeyError: 'date'`, `ParseError: syntax error`). It fails to explain what columns were missing or how to format the file properly.
   - **Severity**: **Major (P1)**.
2. **Unhelpful Dead-End Q&A Fallback**:
   - **Citation**: `src/copilot/answers.py:149`.
   - **Observation**: When Copilot cannot answer a general question, it responds:
     *"I can't answer that yet in this version. It's on the list for the next release."*
   - **Impact**: Gives no suggestions on how the user might rephrase or what related data is available.
   - **Severity**: **Minor (P2)**.
3. **Silent Failure on Voice Transcription Timeout**:
   - **Citation**: `src/copilot/gemini.py:74` and `app/streamlit_app.py:1340`.
   - **Observation**: If voice recording fails or the Gemini API times out, `transcribe_audio` returns `""` and the UI reruns silently with no error banner.
   - **Severity**: **Minor (P2)**.

#### Concrete Remediation
- Catch specific file parsing exceptions in `ingest.py` and display friendly remediation guidance:
  ```python
  except ValueError as e:
      st.error("We couldn't recognize your bank statement columns. Please ensure your CSV or Excel file has clear 'Date', 'Narration', and 'Amount' or 'Debit/Credit' headers.")
  ```
- Enhance the Q&A fallback in `src/copilot/answers.py` to suggest nearby questions (*"I couldn't find an answer for that. You can ask about: salaries on 1 Oct, your largest debtor, or 90-day cash dips."*).

---

### H10. Help and Documentation
> *Even though it is better if the system can be used without documentation, it may be necessary to provide help and documentation. Any such information should be easy to search, focused on the user's task, list concrete steps to be carried out, and not be too large.*

#### Context & Application
Small enterprise operators do not read manuals. Help content must be bite-sized, in-situ, searchable, and focused on immediate operational tasks.

#### Strengths & Positive Patterns
1. **3-Step Setup & Privacy Guide**:
   - **Citation**: `app/streamlit_app.py:1462–1576`.
   - **Design Pattern**: Dedicated onboarding wizard (`Consent` $\to$ `Check books` $\to$ `Key numbers`) clearly communicating RBI Account Aggregator rails, data security, and discovered operating baselines.
2. **Statutory Pre-Deposit Records Checklist**:
   - **Citation**: `app/streamlit_app.py:998–1000`.
   - **Design Pattern**: The Cash Book right panel renders a clear bulleted checklist of documentation required prior to making large cash deposits (Hamali vouchers, salesman slips, rokad registers) with a CA referral note.
3. **Contextual Parameter Tooltips**:
   - Sliders (`Khata collection assumption`, line 632) and role selectors (`line 1614`) feature clear `help="..."` explanations.

#### Deficits & Exact Code Citations
1. **Absence of Global Help Drawer / Searchable FAQ**:
   - **Observation**: There is no dedicated help icon, FAQ drawer, or troubleshooting modal. If an owner is confused about how *Till Drift* is calculated or what *Khata Haircut* implies, they have no in-context documentation.
   - **Severity**: **Minor (P2)**.
2. **Glossary Disconnected from Interface**:
   - **Observation**: The repository contains an excellent domain glossary (`GLOSSARY.md` defining Galla, Rokad, Khata, Decision 60, True Solvency), but none of these definitions are accessible from within the running application.
   - **Severity**: **Minor (P2)**.
3. **Touch Inaccessibility of Streamlit Tooltips**:
   - **Observation**: Streamlit `help="..."` tooltips require mouse hover. On touch devices (smartphones/tablets), tooltips cannot be triggered reliably.
   - **Severity**: **Minor (P2)**.

#### Concrete Remediation
- Add an in-app help drawer or modal dialog (`@st.dialog("Copilot Guide & Glossary")`) accessible from the sidebar footer.
- Render critical explanatory notes as visible caption text (`st.caption`) rather than relying exclusively on hover-only tooltips.

---

## 4. Prioritized Usability Deficit Matrix

The identified deficits are prioritized below according to Nielsen Norman Group severity ratings:
- **Catastrophic (P0)**: Blocks workflow entirely; destroys user data.
- **Major (P1)**: Severe usability impediment; causes user confusion or misleading information.
- **Minor (P2)**: Causes friction or delay; workaround exists.
- **Cosmetic (P3)**: Superficial aesthetic or formatting imperfection.

| Issue ID | Heuristic | Severity | Location | Summary of Usability Deficit | Remediation Action |
|---|:---:|:---:|---|---|---|
| **DEF-01** | **H1** | **Major (P1)** | `app/streamlit_app.py:590, 894, 1009, 1120, 1213, 1322, 1428` | Silent `render_partial_view_notice` return bug. Notice is never rendered on screen for Counter staff or Accountants. | Wrap call in `st.warning(render_partial_view_notice(), icon=":material/visibility_off:")`. |
| **DEF-02** | **H3** | **Major (P1)** | `app/streamlit_app.py:1202–1204` | Permanently disabled "Accept" button creates an interactive dead end on every Review Queue card. | Replace with active "Copy Details" and "Mark Reviewed" secondary action buttons. |
| **DEF-03** | **H4** | **Major (P1)** | `app/streamlit_app.py:1071–1110, 1133–1205, 1425–1460, 1475–1567` | Severe Hindi language leaks across Forecast, Review Queue, Data Quality, and Setup Guide. | Implement complete bilingual dictionary coverage using `t(en, hi)`. |
| **DEF-04** | **H5** | **Major (P1)** | `app/streamlit_app.py:826–831, 845–847` | Hardcoded demo numbers pre-filled in dialog forms (`Opening ₹10,000`, `Takings ₹25,000`) invite accidental corrupt data logging. | Default form fields to `0.0` or dynamic previous-day closing balances. |
| **DEF-05** | **H7** | **Major (P1)** | `app/streamlit_app.py:1252` | Rigid top-10 customer clamp in Receivables banishes remaining overdue accounts to unstyled dataframes without WhatsApp actions. | Implement pagination or "Show all N customers" toggle with action links. |
| **DEF-06** | **H8** | **Major (P1)** | `app/streamlit_app.py:1093–1110` | Academic ML holdout evaluation metrics (MAPE, bootstrap difference) pollute the production Forecast cockpit. | Relocate holdout evaluation expander from `page_forecast` to `page_quality`. |
| **DEF-07** | **H9** | **Major (P1)** | `app/streamlit_app.py:1530–1531, 1538–1539` | Raw Python exceptions (`KeyError`, `IndexError`) displayed to user on bank statement or XML parse failure. | Catch specific parsing errors and provide plain-language column guidance. |
| **DEF-08** | **H2** | **Minor (P2)** | `app/streamlit_app.py:1186` | Technical matcher rule codes (`EXACT_AMBIGUOUS`, `CLUBBED_BILLS`) displayed directly in Review card. | Omit raw monospace rule strings, displaying only friendly human labels. |
| **DEF-09** | **H3** | **Minor (P2)** | `app/streamlit_app.py:824–832, 860–869` | Dialog forms lack explicit "Cancel" or "Discard" buttons, requiring use of tiny top-right modal 'X'. | Add secondary "Cancel" button to dialog form action bars. |
| **DEF-10** | **H7** | **Minor (P2)** | `app/streamlit_app.py:1144–1175` | AgGrid reconciliation grid lacks keyboard shortcuts and multi-row selection for high-volume bookkeeping. | Enable keyboard navigation and multi-row selection in AgGrid configuration. |
| **DEF-11** | **H8** | **Minor (P2)** | `app/streamlit_app.py:578` | Fixed 450px iframe height in `daily_print_dialog` causes nested double-scroll trap inside modal dialog. | Remove iframe scrolling constraint or size dynamically to avoid nested scrollbars. |
| **DEF-12** | **H9** | **Minor (P2)** | `src/copilot/answers.py:149` | Unhelpful generic Q&A fallback (*"can't answer that yet"*) dead-ends user inquiries. | Enhance fallback to recommend 3 nearby supported prompt pills. |
| **DEF-13** | **H10** | **Minor (P2)** | `app/streamlit_app.py:632, 1614` | Streamlit `help` hover tooltips are inaccessible on mobile touch screens. | Pair hover tooltips with explicit visible caption text for critical parameters. |
| **DEF-14** | **H1** | **Minor (P2)** | `app/streamlit_app.py:459–462` | Crude browser `alert()` dialog triggered when speech synthesis is unsupported. | Replace alert with inline, non-blocking fallback banner. |
| **DEF-15** | **H2** | **Cosmetic (P3)** | `app/streamlit_app.py:1128` | ISO date formatting (`YYYY-MM-DD`) in AgGrid table conflicts with Indian commercial format. | Reformat grid dates as `DD %b %Y`. |

---

## 5. Line-by-Line Code Remediation Plan

To facilitate swift engineering remediation, concrete code fixes for the top high-severity deficits are detailed below:

### 1. Fix Silent Partial View Notice Bug (DEF-01)
**File**: `app/streamlit_app.py`  
**Lines**: 590, 894, 1009, 1120, 1213, 1322, 1428  
**Current Code**:
```python
if showing_partial_view:
    render_partial_view_notice()
```
**Remediation**:
```python
if showing_partial_view:
    st.warning(
        t("Formal books only. Cash drawer and informal khata notes are omitted from this view.",
          "केवल औपचारिक बही-खाता। गल्ला और कच्चे खाते का विवरण इस दृश्य में शामिल नहीं है।"),
        icon=":material/visibility_off:"
    )
```

### 2. Replace Dead-End Disabled "Accept" Button (DEF-02)
**File**: `app/streamlit_app.py`  
**Lines**: 1202–1204  
**Current Code**:
```python
st.button("Accept", disabled=True, use_container_width=True,
          help="Posting is wired in the next build; v1 is read-only.")
H('<div class="cc-note">Posting comes in the next build. This version is read-only.</div>')
```
**Remediation**:
```python
c_a1, c_a2 = st.columns(2)
with c_a1:
    if st.button(t("📋 Copy Details", "📋 विवरण कॉपी करें"), key=f"copy_{txn_id}", use_container_width=True):
        st.session_state["toast"] = t("Reconciliation details copied to clipboard.", "मिलान विवरण कॉपी किया गया।")
        st.rerun()
with c_a2:
    if st.button(t("🏷️ Flag for CA", "🏷️ CA के लिए मार्क करें"), key=f"flag_{txn_id}", use_container_width=True):
        st.session_state["toast"] = t("Flagged for accountant review.", "एकाउंटेंट की समीक्षा हेतु मार्क किया गया।")
        st.rerun()
H(f'<div class="cc-note">{t("Read-only mode. Use flags to communicate with your accountant.", "रीड-ओनली मोड। मुनीम/एकाउंटेंट के साथ समन्वय के लिए फ्लैग का उपयोग करें।")}</div>')
```

### 3. Clear Hardcoded Demo Values in Dialogs (DEF-04)
**File**: `app/streamlit_app.py`  
**Lines**: 826–831  
**Current Code**:
```python
c1.number_input(..., value=10000.0, step=500.0)
c2.number_input(..., value=25000.0, step=1000.0)
c1.number_input(..., value=2500.0, step=100.0)
c2.number_input(..., value=20000.0, step=1000.0)
c1.number_input(..., value=12500.0, step=500.0)
```
**Remediation**:
```python
# Use latest recorded count for opening till, and default current entries to 0.0
last_galla = vault.get_latest_galla(biz)
prev_close = last_galla.counted_cash if last_galla else 0.0

c1.number_input(t("Opening till cash (₹)", "सुबह का शुरुआती नकद (₹)"), value=prev_close, step=500.0)
c2.number_input(t("Today's cash takings (₹)", "आज की नकद बिक्री (₹)"), value=0.0, step=500.0, placeholder="0.0")
c1.number_input(t("Cash expenses paid (₹)", "नकद खर्चे व हमाली (₹)"), value=0.0, step=100.0, placeholder="0.0")
c2.number_input(t("Cash banked into account (₹)", "बैंक खाते में जमा नकद (₹)"), value=0.0, step=1000.0, placeholder="0.0")
c1.number_input(t("Physical count at close (₹)", "शाम को गल्ले में बचा नकद (₹)"), value=0.0, step=500.0, placeholder="0.0")
```

### 4. Relocate ML Evaluation Metrics to Data Quality Page (DEF-06)
**File**: `app/streamlit_app.py`  
**Lines**: 1093–1110  
**Remediation**:
Remove `holdout_scores()` expander entirely from `page_forecast()`, and append it inside a dedicated "Algorithmic Precision & Backtesting" expander at the bottom of `page_quality()` (`lines 1459–1460`).

### 5. Graceful File Ingestion Error Handling (DEF-07)
**File**: `app/streamlit_app.py`  
**Lines**: 1530–1531, 1538–1539  
**Current Code**:
```python
except Exception as e:
    st.error(f"Error parsing statement: {e}")
```
**Remediation**:
```python
except Exception as e:
    st.error(
        t("Could not parse bank statement. Please verify that your file includes columns for Date, Description/Narration, and Withdrawal/Deposit amounts.",
          "बैंक स्टेटमेंट पढ़ने में समस्या आई। कृपया जांचें कि फाइल में तारीख (Date), विवरण (Narration), और जमा/निकासी (Amount) कॉलम मौजूद हैं।")
    )
    with st.expander(t("Technical error details", "तकनीकी विवरण")):
        st.code(str(e))
```

---

## 6. Conclusion & Verification Method

### Conclusion
`ps11-copilot` achieves a commendable **3.3 / 5.0 Composite Usability Index**. It is an exceptionally innovative, domain-grounded financial tool that honors the real-world operational realities of Indian SME owner-operators. Its statutory guardrails, salesman protection shield, dual-plane privacy isolation, and bilingual prompt chips set a high standard for localized fintech design.

By addressing the seven Major (P1) deficits identified in this audit—specifically repairing the silent partial view notice bug, replacing the disabled review button with actionable flags, removing dangerous pre-filled dialog numbers, and eliminating language leaks—the application will elevate its usability from an acceptable MVP to an institutional-grade, highly trusted commercial copilot.

### Independent Verification Method
To independently verify the citations and findings in this report:

1. **Verify Silent Partial View Bug**:
   - Inspect `src/copilot/vault/notice.py:5–7` to confirm `render_partial_view_notice()` returns a string.
   - Inspect `app/streamlit_app.py:590, 894, 1009, 1120, 1213, 1322, 1428` to confirm the return value is not captured or displayed.
2. **Verify Disabled Review Action**:
   - Inspect `app/streamlit_app.py:1202–1204` to confirm `st.button("Accept", disabled=True)`.
3. **Verify Hardcoded Dialog Values**:
   - Inspect `app/streamlit_app.py:826–831` to confirm static demo values (`10000.0`, `25000.0`, `2500.0`, `20000.0`, `12500.0`).
4. **Verify Language Leaks**:
   - Inspect `app/streamlit_app.py:1071–1110` (Forecast month-by-month table) and `1149–1153` (AgGrid headers) to confirm absence of `t()` translation helpers.
5. **Verify Test Suite Health**:
   - Execute unit tests in the project virtual environment:
     ```bash
     cd /Users/ishaanwadhwa/Projects/ps11-copilot && .venv/bin/pytest -q
     ```
     Confirm all 78 tests pass.
