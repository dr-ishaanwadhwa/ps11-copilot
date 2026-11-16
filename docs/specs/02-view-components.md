# 02. View Components Specification

**Specification ID:** `SPEC-FE-002`  
**Classification:** Modular Engineering Specification  
**Target Repository:** `/Users/ishaanwadhwa/Projects/ps11-copilot`  
**Related Blueprint:** `docs/blueprints/nextjs-threejs-cashflow-copilot.md` §3  
**Related Invariants:** ADR-001, ADR-002, ADR-003, ADR-004

---

## 1. Overview & View Structure

The SME Cashflow Copilot features 7 dedicated view surfaces engineered for the Indian small and medium enterprise owner, cashier, and visiting Chartered Accountant. Each view is built using modular React compound components with clear prop contracts, deterministic state models, and ergonomic accessibility compliance (44px touch targets, WCAG AAA contrast, tabular figures).

```
Target Views:
1. Overview Cockpit ("Aaj Ka Hisaab")
2. Cash Book & Sovereign Vault
3. Forecast & Simulation (90-Day Cash Dip Simulation)
4. Review Queue (Decision 60 Precision Triage)
5. Receivables & Recovery (Section 18 Shield & MSMED Alerts)
6. Ask Copilot (Grounded Conversational AI)
7. Statutory Exports & Data Quality
```

---

## 2. View 1: Overview Cockpit ("Aaj Ka Hisaab")

### 2.1 Visual Layout & Purpose
The Overview Cockpit answers the SME owner's paramount morning question in under 30 seconds: *"Kitna paisa kharch kar sakte hain?"* (How much money can I safely spend today?).

```
+----------------------------------------------------------------------------------------------------+
| OVERVIEW COCKPIT: "AAJ KA HISAAB"                                     [Role: Owner] [Lang: हिन्दी] |
+----------------------------------------------------------------------------------------------------+
| ⚠️ PARTIAL VIEW NOTICE: Formal books only. Vault unlocked: Total Solvency synthesized.             |
+----------------------------------------------------------------------------------------------------+
| HERO NET USABLE LIQUIDITY CARD                                                                     |
| Net Usable Cash: ₹16,59,000 (Bank: ₹12.39L + Drawer: ₹4.20L) | Runway: 3.8 Months [SURPLUS ✓]      |
| Payroll Status: 1 Oct Salaries (₹4.65L) 100% Funded | Headroom Clear of CC Limit: ₹21.20L          |
+----------------------------------------------------------------------------------------------------+
| VERNACULAR AUDIO BRIEFING PLAYER                                                                   |
| [▶ Play Briefing] [10s ⏪] [⏩ 10s] | |||||||||||||||||||||||||||||||||||||||||||| (01:24 / 02:45) |
| Transcript: "शुभ प्रभात रमेश जी। आज कावेरी डिस्ट्रीब्यूटर्स के पास कुल ₹16.59L खर्च करने योग्य नकदी है..."   |
+----------------------------------------------------------------------------------------------------+
| 4 VITAL PULSE TILES                                                                                |
| ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐                |
| │ Net Usable Cash  │ │ Bank Headroom    │ │ Cash in Drawer   │ │ Due in 30 Days   │                |
| │ ₹16,59,000       │ │ ₹21,20,000       │ │ ₹4,20,000        │ │ ₹4,65,000        │                |
| │ Bank + Till Cash │ │ CC Limit: ₹25L   │ │ Physical Counted │ │ Payroll + Vendor │                |
| └──────────────────┘ └──────────────────┘ └──────────────────┘ └──────────────────┘                |
+----------------------------------------------------------------------------------------------------+
| SINGLE FOCAL ACTION CARD                                                                           |
| 🚨 Priority 1: Matoshree Supermarket owes ₹1,14,000 (930 days overdue)                            |
| ⚠️ Section 18 Limitation Alert: Claim expires in 60 days!                                          |
| [💬 Send WhatsApp AoD Reminder]  [📋 View Ledger]  [✓ Log Part Settlement]                         |
+----------------------------------------------------------------------------------------------------+
| 3D SPATIAL CASHFLOW TOPOGRAPHY PREVIEW                                                             |
| [Interactive 3D Canvas: Cash peaks & 1 Oct salary valley glide] [Expand Full Forecast ->]         |
+----------------------------------------------------------------------------------------------------+
| DUAL-PLANE TRUE SOLVENCY EQUATION (COLLAPSIBLE ACCORDION)                                          |
| True Buffer = (Bank ₹12.39L − CC Drawn ₹3.80L) + Galla ₹4.20L + (0.85 × Khata ₹22.00L) − Due ₹4.65L|
| Collection Haircut Slider (α): [==== 85% ====]  Net Solvency Buffer: +₹32,64,000                  |
+----------------------------------------------------------------------------------------------------+
```

### 2.2 Component Hierarchy & Props
```tsx
<OverviewCockpit>
  <PartialViewNotice isVaultUnlocked={isUnlocked} />
  <CockpitHeroCard
    bankBalance={1239000}
    headroom={2120000}
    runwayMonths={3.8}
  >
    <ClientVaultDisplay bankBalance={1239000} commitments={465000} />
  </CockpitHeroCard>
  <VernacularAudioPlayer
    audioSrc="/api/copilot/audio-brief?lang=hi"
    transcriptHindi="शुभ प्रभात रमेश जी..."
    transcriptEnglish="Good morning Ramesh ji..."
  />
  <VitalPulseGrid>
    <PulseTile id="bank-headroom" amount={2120000} label="Bank Headroom" tone="positive" />
    <PulseTile id="commitments" amount={465000} label="Due in 30 Days" tone="warning" />
    <ClientPulseTile id="net-cash" label="Net Usable Cash" fallbackAmount={1239000} />
    <ClientPulseTile id="drawer-cash" label="Cash in Drawer" fallbackAmount={0} />
  </VitalPulseGrid>
  <FocalActionCard
    debtorName="Matoshree Supermarket"
    amount={114000}
    overdueDays={930}
    isLimitationAlert={true}
    phone="+919820012345"
  />
  <TopographyPreviewCard />
  <ClientTrueSolvencyCard bankBalance={1239000} ccDrawn={380000} formalDue={465000} />
</OverviewCockpit>
```

---

## 3. View 2: Cash Book & Sovereign Vault

### 3.1 Visual Layout & Purpose
View 2 provides the daily cash balancing cockpit for godown operators, implementing the 5-part balancing formula and salesman collection slip logging.

```
+----------------------------------------------------------------------------------------------------+
| CASH BOOK & SOVEREIGN VAULT                                           [Status: 🔓 UNLOCKED IN RAM] |
+----------------------------------------------------------------------------------------------------+
| 5-PART GODOWN CASH DRAWER BALANCING COCKPIT                                                        |
| ┌──────────────┬──────────────┬──────────────┬──────────────┬──────────────┬─────────────────────┐ |
| │ Opening Float│ + Parchi In  │ − Hamali Exp │ − Banked CDM │= Expected    │ Physical Counted    │ |
| │ ₹10,000      │ ₹25,000      │ ₹2,500       │ ₹20,000      │ ₹12,500      │ ₹12,500             │ |
| └──────────────┴──────────────┴──────────────┴──────────────┴──────────────┴─────────────────────┘ |
| Drawer Drift: ₹0.00  |  Status: [ ✓ BALANCED (< ₹50 drift) ]                                       |
| [📋 Open Day-Close Wizard]  [💵 Denomination Counter]  [🔒 Lock Sovereign Vault]                   |
+----------------------------------------------------------------------------------------------------+
| SALESMAN COLLECTION SLIP (PARCHI) LOGGING                                                          |
| [+ Record New Collection Slip]  [📸 OCR Slip via Gemini Vision]  Active Slips in Transit: ₹65,000   |
| ┌──────────┬──────────────┬───────────────┬────────────┬─────────────┬───────────┬───────────────┐ |
| │ Slip No  │ Date         │ Salesman      │ Shop/Party │ Amount (₹)  │ Mode      │ Status        │ |
| ├──────────┼──────────────┼───────────────┼────────────┼─────────────┼───────────┼───────────────┤ |
| │ SLP-1092 │ 30 Sep 2026  │ Ramesh Kumar  │ Laxmi Mart │ ₹15,000     │ Cash      │ In Till ✓     | |
| │ SLP-1093 │ 30 Sep 2026  │ Vijay Patil   │ Balaji Gen │ ₹8,500      │ UPI       │ Settled ✓     | |
| │ SLP-1094 │ 30 Sep 2026  │ Ramesh Kumar  │ Om Super   │ ₹22,000     │ Cheque    │ In Bag (Route)│ |
| └──────────┴──────────────┴───────────────┴────────────┴─────────────┴───────────┴───────────────┘ |
+----------------------------------------------------------------------------------------------------+
| STATUTORY CEILING COMPLIANCE SHIELD                                                                |
| 🛡️ Section 186 Cash Receipt Guard: No single counter cash receipt >= ₹2,00,000 logged today.       |
| 🛡️ Section 36(4) Expense Guard: Hamali cash voucher ₹2,500 is within ₹10,000 tax ceiling.         |
| ℹ️ SFT Rule 237 Deposit Facts: YTD Cash Deposited: ₹14.50L (Current Account SFT Threshold: ₹50.00L)|
+----------------------------------------------------------------------------------------------------+
```

### 3.2 5-Part Mathematical Formula
$$\text{Expected Cash} = \text{Opening Float} + \text{Parchi In} - \text{Cash Out (Expenses)} - \text{Cash Banked (CDM)}$$
$$\text{Drift} = \text{Physical Counted Cash} - \text{Expected Cash}$$
- **Status `BALANCED`:** $|\text{Drift}| \le ₹50.00$.
- **Status `DRIFT_ALERT`:** $|\text{Drift}| > ₹50.00$ (requires explanatory note before day-close commit).

---

## 4. View 3: Forecast & Simulation (90-Day Cash Dip Simulation)

### 4.1 Visual Layout & Purpose
Simulates future cash trajectory using a bottom-up Monte Carlo engine (1,000 simulation paths), displaying P10 (conservative), P50 (median), and P90 (optimistic) envelopes.

```
+----------------------------------------------------------------------------------------------------+
| 90-DAY CASH DIP SIMULATION & STRESS TESTING                         [Model: Bottom-Up Monte Carlo] |
+----------------------------------------------------------------------------------------------------+
| 🛡️ OUTLOOK STATUS: SAFE (Zero breaches of sanctioned CC Limit of ₹25,00,000)                       |
| Out-of-Sample Holdout Accuracy: MAPE 5.61% (vs Naive 18.20%) | P10-P90 Coverage: 93.3%             |
+----------------------------------------------------------------------------------------------------+
| 3D SPATIAL TOPOGRAPHY & PROBABILITY FAN CHART                                                      |
| [View Selector: (•) 3D Spatial Landscape  ( ) 2D Area Fan Chart]                                  |
| [TopographyCanvas / Fallback2DTopography rendered here]                                            |
+----------------------------------------------------------------------------------------------------+
| INTERACTIVE SCENARIO STRESS SLIDERS                                                                |
| 1. Customer Delay Surge: [+15 Days Overdue]    [=====|================] (Affects Top 5 Retailers)  |
| 2. Raw Material Cash Surge: [₹2,50,000 Advance][========|=============]                            |
| 3. Collection Haircut (α): [80% Realization]   [===============|======]                            |
| Simulated Lowest Point: +₹2,10,000 on 1 Nov (Headroom clear by ₹27.10L)                            |
+----------------------------------------------------------------------------------------------------+
| MONTH-BY-MONTH OPERATING OUTLOOK MATRIX                                                            |
| October 2026: Inflows P50: ₹48.20L | Outflows: ₹42.10L | Net: +₹6.10L | Low: +₹4.20L | Close: ₹22.69L|
| November 2026: Inflows P50: ₹52.40L | Outflows: ₹44.50L | Net: +₹7.90L | Low: +₹6.10L | Close: ₹30.59L|
| December 2026: Inflows P50: ₹61.00L | Outflows: ₹46.80L | Net: +₹14.20L | Low: +₹12.40L | Close: ₹44.79L|
+----------------------------------------------------------------------------------------------------+
```

---

## 5. View 4: Review Queue (Decision 60 Precision Triage)

### 5.1 Visual Layout & Purpose
Implements Decision 60 precision matching with 100% mathematical accuracy across 4 deterministic tiers:
- `AUTO` (1,170 items): Straight-through posted, verified Tally GUIDs.
- `SUGGEST` (1,744 items): High-confidence matches presented for single-click confirmation.
- `ASK` (619 items): Transactions with multiple invoice candidates or unclear narrations.
- `NO_DOC` (23 items): Bank fees, interest, or direct tax debits without vendor invoices.

```
+----------------------------------------------------------------------------------------------------+
| REVIEW QUEUE: DECISION 60 PRECISION MATCHING                          [Circuit Breaker: ACTIVE ✓]  |
+----------------------------------------------------------------------------------------------------+
| SEGMENTED TIER SELECTOR:                                                                           |
| [ All Items (3,533) ]  [ Suggestions (1,744) ]  [ Questions (619) ]  [ Auto-Posted ✓ (1,170) ]     |
+----------------------------------------------------------------------------------------------------+
| 3-PANE TRIAGE LAYOUT:                                                                              |
| LEFT FILTER (20%)      | CENTER TRANSACTION TABLE (45%)          | RIGHT INSPECTOR DETAIL (35%)    |
| Search Narration..     | Date | Amount | Tier / Rule             | Txn ID, Narration, Candidate    |
| Rules: CASH_DEP,       | 30 Sep | ₹45,000 | SUGGEST: CASH_DEP    | Invoices, One-click Approve [a],|
| CLUBBED, ON_ACCOUNT    | 30 Sep | ₹82,400 | SUGGEST: CLUBBED     | Reassign Payer [r]              |
| Keyboard: [j] Down, [k] Up, [a] Approve, [r] Reassign                                              |
+----------------------------------------------------------------------------------------------------+
| FLOATING BATCH ACTION BAR: Selected: 14 Suggestions (Total: ₹4,28,000) | [⚡ Batch Approve 14 Items]|
+----------------------------------------------------------------------------------------------------+
```

---

## 6. View 5: Receivables & Recovery (Section 18 Shield & MSMED)

### 6.1 Visual Layout & Purpose
Protects SME receivables against statutory extinguishment under Section 18 of the Limitation Act, 1963, and enforces MSMED Act 45-day overdue warnings.

```
+----------------------------------------------------------------------------------------------------+
| RECEIVABLES & RECOVERY ACCELERATOR                                    [Section 18 Shield: ACTIVE]  |
+----------------------------------------------------------------------------------------------------+
| 3-QUADRANT RECEIVABLES METRIC GRID:                                                                |
| Formal Receivables: ₹90,47,000 | Open Invoices: 346 | Overdue > 60 Days: ₹23,82,000 (91 Invoices)  |
+----------------------------------------------------------------------------------------------------+
| CUSTOMER RECOVERY CARDS:                                                                           |
| 1. MATOSHREE SUPERMARKET (930 Days Overdue) | Total Due: ₹1,14,000.00                              |
|    ⚠️ SECTION 18 LIMITATION ACT CLIFF: Debt is 31 months old. Statutory 3-year bar in 60 days.     |
|    [💬 Send WhatsApp AoD Link (wa.me)]  [📥 Log Debtor Reply & Issue BSA §63 Certificate]          |
|                                                                                                    |
| 2. BALAJI GENERAL STORE (48 Days Overdue) | Total Due: ₹65,000.00                                  |
|    🛡️ SALESMAN PROTECTION SHIELD ACTIVE:                                                           |
|    "Salesman Ramesh Kumar collected ₹15,000 cash today (Slip SLP-1092); not banked yet.            |
|    DO NOT CALL RETAILER - CASH IN ROUTE BAG."                                                      |
+----------------------------------------------------------------------------------------------------+
```

---

## 7. View 6: Ask Copilot (Grounded Conversational AI)

### 7.1 Visual Layout & Purpose
Provides grounded financial intelligence citing verified ledger records, enforcing ADR-001 zero cloud cash transmission through client-side template token substitution (`{{LOCAL_VAULT_GALLA_CASH}}`).

```
+----------------------------------------------------------------------------------------------------+
| ASK COPILOT: GROUNDED CONVERSATIONAL ASSISTANT                        [Zero Stochastic Hallucination]
+----------------------------------------------------------------------------------------------------+
| 👤 Owner: "Can I safely pay my staff salaries on October 1st?"                                     |
| 🤖 Copilot:                                                                                        |
|   ⚡ Consulted Bank Current Balance: ₹12,39,000                                                    |
|   ⚡ Evaluated 1 Oct Payroll Obligation: ₹4,65,000                                                 |
|   Yes, you can safely pay your October 1st salaries of ₹4,65,000 [1].                             |
|   Bank balance remains ₹7,74,000 (+₹32.74L clear of CC limit). You also have ₹4,20,000 [2]         |
|   physical cash in your godown drawer.                                                             |
|   (हिन्दी सारांश: हाँ, आप 1 अक्टूबर को ₹4,65,000 का वेतन आराम से दे सकते हैं...)                    |
|   ▼ Expand Verified Citations & Ledger Rows (2 Source Items):                                      |
|     • [1] Salary Ledger: 24 employees, ₹4,65,000, 2026-10-01                                       |
|     • [2] Local Sovereign Vault: Galla #GL-9024, count ₹4,20,000 (Client-Only RAM)                 |
+----------------------------------------------------------------------------------------------------+
| PINNED COMPOSER: [Ask question in English, हिन्दी, or Hinglish...] [🎤 Voice] [Send]                |
+----------------------------------------------------------------------------------------------------+
```

---

## 8. View 7: Statutory Exports & Data Quality

### 8.1 Visual Layout & Purpose
Generates 100% balance-tied statutory accounting deliverables adhering strictly to ADR-004:
- **TallyPrime XML Receipt Vouchers:** Pure TDL XML format with CDATA wrapping and deterministic GUIDs.
- **CA 5-Sheet Statutory Excel:** Excludes informal route slips and omits Block D drawer cash cross-checks.
- **Internal Management Diagnostic Pack (PIN-Gated):** Full 6-sheet dual-plane reconciliation workbook for the owner only.
- **Data Integrity Scorecard:** Opening Balance + Credits − Debits = Closing Balance tie formula.
