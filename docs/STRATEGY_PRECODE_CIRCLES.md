# SME Cash-Flow Copilot: Product Strategy, Pre-Code Questions & Persona CIRCLES Analysis

> **Document Type:** Publication-Grade Strategy, Architecture & Product Requirements Document  
> **Target System:** SME Cash-Flow Copilot (`ps11-copilot`)  
> **Author:** Team 11 (Applied AI & Product Architecture)  
> **Status:** Final / Milestone 1 Deliverable  
> **Date:** 14 November 2026  
> **Target Audience:** Engineering Leads, Product Designers, Forensic Auditors, Practicing Chartered Accountants  

---

## Table of Contents

1. [Executive Summary & Strategic Framing](#1-executive-summary--strategic-framing)
   - 1.1 The Structural Reality of Indian SME Cash Flow
   - 1.2 The Three Pilot Business Archetypes
   - 1.3 The Core Positioning Differentiator
   - 1.4 Dual-Plane Architecture: Public Formal Plane vs Sovereign Vault
2. [The Six Load-Bearing Pre-Code Questions](#2-the-six-load-bearing-pre-code-questions)
   - 2.1 Question 1: Problem Validation — Morning Cash Blindness Across Split Financial Planes
   - 2.2 Question 2: Ideal Customer Profile (ICP) Specification — Prakash Gupta / Kaveri Distributors
   - 2.3 Question 3: Solution & Alternatives Differentiation — Why Incumbents Fail
   - 2.4 Question 4: Stated Non-Goals & Statutory Firewalls
   - 2.5 Question 5: Primary Success Metric & The True Solvency Equation
   - 2.6 Question 6: Open Operational Tensions & Regulatory Reconciliations
3. [Persona CIRCLES Analysis: Prakash Gupta (Kaveri Distributors)](#3-persona-circles-analysis-prakash-gupta-kaveri-distributors)
   - 3.1 Comprehend: The Macro and Micro Operating Context
   - 3.2 Identify: Detailed Persona Architecture
   - 3.3 Report: Segmented 24-Hour Operational Needs
   - 3.4 Cut & Prioritize: P0 Survival, P1 Efficiency, P2 Non-Goals
   - 3.5 List & Evaluate: Solution Trade-Offs & Architectural Feasibility
   - 3.6 Summarize: The Zero-Knowledge Dual-Plane Operating System
4. [UX/UI Design Choices Analysis: "Aaj Ka Hisaab" Cockpit](#4-uxui-design-choices-analysis-aaj-ka-hisaab-cockpit)
   - 4.1 The "Aaj Ka Hisaab" Viewport Workflow (Zero Desktop Scroll)
   - 4.2 Three-Tier Visual Hierarchy & Screen Ergonomics
   - 4.3 High-Glare Ambient Lighting & Contrast Engineering (WCAG 2.1 AA/AAA)
   - 4.4 Non-Color Status Encoding
   - 4.5 The <10-Minute Daily Review Time Budget
   - 4.6 Ergonomic Touch Targets & Hardware Constraints
   - 4.7 Vernacular Commercial Lexicon & Non-Incriminating UI Typography
   - 4.8 Bilingual Parity & Deterministic CLDR Number Formatting

---

## 1. Executive Summary & Strategic Framing

### 1.1 The Structural Reality of Indian SME Cash Flow

Conventional financial software operates under a profound category error: it assumes that every economic transaction in a small enterprise begins and ends on a formal Goods and Services Tax (GST) tax invoice, clears through an automated corporate bank rail, and reconciles cleanly inside a centralized double-entry cloud ledger. 

For the overwhelming majority of India's 63 million Micro, Small, and Medium Enterprises (MSMEs)—which contribute over 30% of the nation's GDP and employ over 110 million citizens—this textbook model bears zero resemblance to operational reality. In traditional wholesale distribution, physical retail, outpatient healthcare, and boutique creative services, business survival depends on navigating two parallel financial universes:
1. **The Public Formal Plane:** Bank current accounts, Cash Credit (CC) overdraft lines, GST tax invoices (GSTR-1, GSTR-3B), e-Way bills, Tax Deducted at Source (TDS) certificates, and statutory audit books managed by visiting Chartered Accountants (CAs) under the strictures of MCA Rule 11(g) audit trails.
2. **The Sovereign Vault Plane:** The physical till drawer (*galla*), daily cash books (*rokad*), loose dispatch collection slips (*parchis*), informal credit ledgers (*udhar khata*), unbilled supplier spot settlements, and personal proprietor reserves.

Indian small business owners do not maintain this dual structure out of willful accounting ignorance or simple tax evasion. Rather, they operate in an economic environment where supply chains systematically reward immediate physical cash settlements with **2% to 5% prompt cash discounts (*rokda*)**. Over typical 15- to 30-day trade credit cycles, these discounts generate annualized returns of **24.8% to 128.1% APR**—dwarfing the 11% to 13% annual interest cost of bank credit lines. Holding ₹5 lakh to ₹15 lakh in physical drawer cash is an indispensable working-capital optimization strategy.

However, the coexistence of these split financial planes produces a chronic operational pathology: **Morning Cash Blindness**. Because no single system bridges formal bank overdrafts with physical till balances and field collections, business owners start every working day in a state of acute financial disorientation. Bank SMS alerts signal impending overdraft default, while substantial liquidity sits uncounted in the warehouse drawer, held by route salesmen, or locked in aging trade credit.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        THE SPLIT FINANCIAL UNIVERSE OF INDIAN SMES                     │
├───────────────────────────────────────────┬────────────────────────────────────────────┤
│           PUBLIC FORMAL PLANE             │           SOVEREIGN VAULT PLANE            │
├───────────────────────────────────────────┼────────────────────────────────────────────┤
│ • Bank Current / Cash-Credit Accounts     │ • Godown Drawer Cash (Galla)               │
│ • GST Tax Invoices (GSTR-1 / GSTR-3B)     │ • Daily Cash Book (Rokad Bahi)             │
│ • MCA Rule 11(g) Audit-Log Tally Ledger   │ • Loose Salesman Collection Slips (Parchi) │
│ • TDS Challans & Form 26AS Tax Credits    │ • Informal Retailer Credit (Udhar Khata)   │
│ • Formal Cheques & RTGS Commitments       │ • Spot Cash Supplier Settlements (Rokda)   │
│ • Shared with Visiting CA & Tax Dept      │ • Air-gapped, Private, Owner-Only Memo     │
└───────────────────────────────────────────┴────────────────────────────────────────────┘
                                     │
                          CONVERGES AT 08:00 AM IN
                                     ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                MORNING CASH BLINDNESS                                  │
│   "My bank balance is -₹23.3L against a ₹25L CC limit. Can I clear today's ₹4.2L      │
│    supplier RTGS without bouncing? Who paid by UPI yesterday? Which shops owe cash?"   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 The Three Pilot Business Archetypes

The product strategy and technical specifications of SME Cash-Flow Copilot are grounded in the empirical analysis of **13,359 bank transactions** across 18 continuous months (April 2025 to September 2026), capturing 6,438 invoices and claims across three foundational Indian commercial archetypes (verified under check `[V1, V2]`):

1. **SME-1: Fast-Moving Consumer Goods (FMCG) Wholesale Distributor (Prakash Gupta / Kaveri Distributors, Pune)**
   - **Scale & Inflows:** Annual turnover ~₹18.0 Crore; monthly inflows average ₹68.7 Lakh (`[I1]`). Supplies 110 kirana retail stores across urban and semi-urban routes.
   - **Banking & Overdraft:** Operates a ₹25,00,000 Cash Credit (CC) hypothecation facility. Squeezed to a razor-thin headroom of **₹1,70,467** on 1 October 2025 (balance plunged to **-₹23,29,533**; `[B2]`), requiring Prakash to inject **₹28,00,000** in personal funds across 5 transfers in October 2025 (`[B3]`) and **₹46,00,000** across 9 transfers over 18 months (`[B1]`).
   - **Receivables & Aging:** Outstanding receivables stand at **₹90,47,390** across 346 open invoices (`[A1]`), with **₹23,81,682** severely stalled (>60 days overdue) on 91 invoices (`[A2]`). Days Sales Outstanding (DSO) sits at **41 days** (`[A6]`), and average settlement delay is **28.1 days** (`[A5]`).
   - **Narration Chaos:** **42.0% of customer bank receipts** arrive from personal UPI/NEFT accounts without citing the shop name (`[C5]`). Only 64.3% of receipts match a single invoice exactly (`[R11]`), while 20.7% (731 of 3,525) pay multiple invoices simultaneously (`[R4]`).
   - **Admin Burden:** Finance admin consumes **89 hours/month** (`[T1]`), with **26.9 hours/month** spent on bank reconciliation (`[T3]`).

2. **SME-2: Dental & Diagnostic Healthcare Clinic (Dr. Kavya, Bengaluru)**
   - **Scale & Inflows:** Monthly inflows average ₹15.2 Lakh (`[I1]`). Combines multi-chair dental practice, outpatient consultation, and an attached pharmacy.
   - **Batch Clearing Reality:** **96.8% of bank receipts** arrive in daily consolidated batches (5,991 UPI batches, 469 card POS settlements net of Merchant Discount Rate [MDR], 155 clubbed cash deposits; `[R5]`). **0.0% of receipts** match an individual patient invoice directly (`[R12]`).
   - **Cash Drift:** Handled ₹32,50,744 in counter cash, banked ₹29,11,700, and spent ₹3,32,400 in petty hamali/clinic cash, leaving an unexplained drift of **₹6,644** (`[A9]`).
   - **TPA Disallowances:** 114 claims pending, 64 rejected, with ₹2,16,481 disallowed and ₹4,53,098 withheld in TDS (`[A4]`). Money lost to insurers represents 8.8% to 9.4% of total billing (`[A8]`). Admin consumes **45 hours/month** (`[T1]`).

3. **SME-3: Boutique Creative & Digital Design Agency (Rohan Malhotra, Delhi)**
   - **Scale & Inflows:** LLP structure; monthly inflows average ₹26.5 Lakh (`[I1]`).
   - **TDS Squeeze:** Only 9.1% of receipts match an invoice exactly (`[R13]`). **82.9% of receipts** arrive short due to Section 194J/194C TDS withholding, with 70.6% short exclusively due to statutory TDS (`[R2]`). TDS is deducted at exactly 10.0% of pre-GST taxable value across all 233 invoices (`[R3]`).
   - **Working Capital Lag:** Receivables stand at ₹57,40,700 (`[A3]`), with an average collection delay of **60.6 days** (`[A5]`) and a DSO of **81 days** (`[A6]`). Severe salary-day liquidity dips occur on the 1st–5th of every month in 13 of 18 months (`[D6]`). Admin consumes **64 hours/month** (`[T1]`).

Across all three businesses, finance administration totals **198 hours/month**, of which **55.7%** (110.3 hours) is squandered purely on manual bank reconciliation (28.7%) and chasing overdue receivables (27.0%) (`[T1, T2]`).

### 1.3 The Core Positioning Differentiator

SME Cash-Flow Copilot is positioned around a single, load-bearing principle formulated in Decision 10 of the system design log:

> **"It explains every rupee between your bank and your books, and never acts without you."** (`GRILL-LOG.md` D10)

This definition sharply separates the product from two competing industry failure modes:
1. **The Inflexible Historical Ledger (TallyPrime / BUSY):** Incumbent desktop accounting software records history for tax compliance. It tells the owner what happened three weeks ago when the CA closed the books, but provides zero forward-looking liquidity intelligence, cannot resolve messy UPI narrations, and ignores unbanked cash drawer balances.
2. **The Autonomous Fintech Black-Box (RazorpayX / Cloud Neobanks):** Venture-backed fintech platforms attempt to automate bill payments, direct debits, and collections via cloud APIs. In the Indian SME context, automated financial execution destroys trust: an autonomous system that misallocates a customer's payment, initiates an unauthorized collection reminder to a sensitive trade debtor, or drains an overdraft account without human consent is instantly uninstalled.

The copilot operates on an **approval-first, read-only** paradigm. It synthesizes intelligence, highlights statutory tripwires, models probabilistic cash trajectories, and drafts one-click client-side actions, but **never posts a voucher, dispatches a text, or executes a payment without explicit human authorization**.

### 1.4 Dual-Plane Architecture: Public Formal Plane vs Sovereign Vault

To achieve unified financial visibility without violating Indian tax and corporate laws, SME Cash-Flow Copilot introduces a partitioned **Dual-Plane Architecture**:

```
                                    ┌─────────────────────────────────────────┐
                                    │           PUBLIC FORMAL PLANE           │
                                    │                                         │
                                    │ • Bank Feeds (MT940 / CSV Statements)   │
                                    │ • TallyPrime / ERP GST Sales & Bills    │
                                    │ • GSTR-1, GSTR-2B, GSTR-3B Tax Data     │
                                    │ • Read-Only Ingestion Engine            │
                                    └────────────────────┬────────────────────┘
                                                         │
                                    One-Way Downward Sync│ (Formal commitments,
                                    (Zero Outward Leak)  │  bank balances, GST dues)
                                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                             SOVEREIGN VAULT PLANE (100% ON-DEVICE)                          │
│                                                                                             │
│  ┌─────────────────────────┐   ┌──────────────────────────┐   ┌──────────────────────────┐  │
│  │    Galla Drawer Log     │   │     Daily Rokad Bahi     │   │   Pending Khata Ledger   │  │
│  │ (Physical Cash Balance) │   │ (Counter Cash Receipts & │   │ (Informal Customer Debts │  │
│  │                         │   │  Hamali/Freight Payouts) │   │  & 30-Month Alert Clock) │  │
│  └────────────┬────────────┘   └────────────┬─────────────┘   └────────────┬─────────────┘  │
│               │                             │                              │                │
│               └───────────────────────┬─────┴──────────────────────────────┘                │
│                                       ▼                                                     │
│                        ┌──────────────────────────────┐                                     │
│                        │     TOTAL SOLVENCY ENGINE    │                                     │
│                        │                              │                                     │
│                        │ • Net Usable CC Headroom     │                                     │
│                        │ • Counted Till Cash (Galla)  │                                     │
│                        │ • Risk-Discounted Khata (α)  │                                     │
│                        │ • 30-Day Total Commitments   │                                     │
│                        └──────────────┬───────────────┘                                     │
│                                       ▼                                                     │
│                        ┌──────────────────────────────┐                                     │
│                        │  "AAJ KA HISAAB" COCKPIT UI  │                                     │
│                        │ (<10 Min Daily Review Budget)│                                     │
│                        └──────────────────────────────┘                                     │
│                                                                                             │
│  • Storage: SQLCipher 4 AES-256 (Local SQLite) with Hardware KeyStore (Android StrongBox)   │
│  • Network: 100% Air-Gapped. Zero Cloud Database Sync, Zero Telemetry.                      │
│  • Privacy Boundary: Strictly sealed. Never writes unbilled cash entries into Tally/GST.    │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

The Public Formal Plane contains compliance data that can be inspected by visiting accountants, statutory auditors, or tax officers. The Sovereign Vault Plane is an air-gapped, encrypted on-device database storing the owner's operational cash reality. By pulling formal commitments downward into the vault, the copilot computes **True Solvency** locally—without ever leaking informal data upward into formal audit books.

---

## 2. The Six Load-Bearing Pre-Code Questions

### 2.1 Question 1: Problem Validation — Morning Cash Blindness Across Split Financial Planes

#### The Empirical Anatomy of Morning Blindness
Every morning at 08:00 AM, the Indian SME distributor experiences acute financial blindness caused by the structural fragmentation of their financial records. Information is scattered across four unlinked, mutually incompatible planes:
1. **The White Tax Ledger:** Maintained in desktop TallyPrime or BUSY, typically locked on the accountant's PC and updated only 2–3 times a week. It reflects billed GST invoices and formal ledger allocations, but runs 7 to 15 days behind operational reality.
2. **The Godown Drawer Cash (*Galla*):** Physical currency notes sitting in the godown safe, accumulated from retail cash sales, driver collections, and informal trade recoveries. This cash is operationally vital for supplier *rokda* discounts and daily freight, but invisible to the bank.
3. **Salesman Route Parchis:** Loose paper dispatch slips carried by field salesmen visiting 25–40 retail kirana stores daily. Salesmen collect cash and bearer cheques, hand over handwritten receipts, and retain the proceeds until returning to the godown at 07:30 PM.
4. **Bank Cash-Credit (CC) Overdraft Limits:** The distributor's primary working capital engine. Secured against hypothecated stock and debtors, the CC account operates as an overdraft facility with a strict sanctioned ceiling (e.g., ₹25,00,000 for Kaveri Distributors). 

#### Empirical Validation from the Distributor Pilot (`[A1, A2, B1, B2, C5]`)
The data pack demonstrates the extreme operational fragility generated by this blindness:
- **The Acute Overdraft Squeeze (`[B2]`):** On 1 October 2025, Kaveri Distributors' bank overdraft balance reached **-₹23,29,533**, leaving an available credit headroom of just **₹1,70,467** against its ₹25L limit. A single unrecorded supplier cheque or freight debit would have triggered an over-limit breach, bouncing cheques and attracting criminal liability under Section 138 of the Negotiable Instruments Act.
- **Massive Capital Infusions (`[B1, B3]`):** Squeezed by morning blindness, Prakash was forced to inject **₹28,00,000** of personal funds across 5 emergency transfers between 30 September and 14 October 2025 (`[B3]`) to prevent dishonor. Across the 18-month audit period, Prakash made **9 personal emergency capital infusions totaling ₹46,00,000** (`[B1]`).
- **Narration Chaos & Identifier Loss (`[C5]`):** **42.0% of customer bank receipts** omit the shop name entirely in bank narrations. Transactions arrive as `"UPI/528192/Siddharth Pawar/PayTM"` or `"NEFT/INDB0012/Pooja Trading"`. Prakash cannot determine which of his 110 kirana stores settled their account without spending hours on phone calls.
- **Receivables Lockup (`[A1, A2, A6]`):** Total outstanding receivables sit at **₹90,47,390** across 346 open invoices (`[A1]`). Of this, **₹23,81,682 (26.3%)** is severely overdue (>60 days) across 91 invoices (`[A2]`), stretching DSO to **41 days** (`[A6]`).

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                   KAVERI DISTRIBUTORS: WORKING CAPITAL LOCKUP [A1, A2, B2]             │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Total Outstanding Receivables (346 invoices)       :  ₹90,47,390                       │
│ Receivables Stalled >60 Days Overdue (91 invoices) :  ₹23,81,682  (26.3% of total AR)  │
│ Peak Bank CC Overdraft Utilized (1 Oct 2025)       : -₹23,29,533                       │
│ Minimum Bank CC Headroom Available [B2]           :   ₹1,70,467  (Danger Zone <₹2.5L) │
│ Total Emergency Owner Injections [B1] (9 txns)     :  ₹46,00,000                       │
│ Unknown UPI Counterparties Omitting Shop Name [C5] :  42.0%                            │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

#### The Rokda Discount APR Spread vs CC Cost
Why does Prakash risk overdraft squeezes rather than banking all cash immediately? The answer lies in the microeconomics of supply-chain cash discounts (*rokda*).

In FMCG distribution, gross margins are compressed to 3.0%–8.0%, netting just **1.5% to 4.0%** after godown rent, delivery tempo expenses, hamali labor, and working capital interest (~12% p.a.). To accelerate liquidity, FMCG super-stockists and manufacturers offer immediate **2.0% to 5.0% spot cash discounts (*rokda*)** if an order is paid in cash upon delivery rather than on standard 15- to 30-day credit terms.

The implied Annual Percentage Rate (APR) captured by taking the cash discount is computed as:
$$\text{Implied APR} = \left( \frac{d}{1 - d} \right) \times \left( \frac{365}{\text{Credit Days}} \right) \times 100$$
where $d$ is the spot discount percentage.

| Cash Discount ($d$) | Credit Period | Implied Annualized Return (APR) | Cost of Bank CC Overdraft | Net Economic Arbitrage Spread |
|---|---|---|---|---|
| **2.0%** | 15 Days | **49.66% APR** | 12.00% p.a. | **+37.66%** |
| **2.0%** | 21 Days | **35.47% APR** | 12.00% p.a. | **+23.47%** |
| **2.0%** | 30 Days | **24.83% APR** | 12.00% p.a. | **+12.83%** |
| **3.0%** | 15 Days | **75.26% APR** | 12.00% p.a. | **+63.26%** |
| **3.0%** | 21 Days | **53.76% APR** | 12.00% p.a. | **+41.76%** |
| **3.0%** | 30 Days | **37.63% APR** | 12.00% p.a. | **+25.63%** |
| **5.0%** | 15 Days | **128.07% APR** | 12.00% p.a. | **+116.07%** |
| **5.0%** | 21 Days | **91.48% APR** | 12.00% p.a. | **+79.48%** |
| **5.0%** | 30 Days | **64.04% APR** | 12.00% p.a. | **+52.04%** |

*Economic Conclusion:* Capturing a **24.8% to 128.1% APR** return by settling supplier invoices in cash generates higher margin than Prakash's entire trading operation. Keeping ₹5 lakh to ₹10 lakh in physical godown cash is a rational profit-maximizing necessity.

#### The "False Insolvency" Dilemma
Single-ledger accounting systems like Tally or Zoho create dangerous "False Insolvency" alarms. On any given morning, formal bank balances look catastrophic:
$$\text{Bank Balance} = -₹23,29,533 \implies \text{Headroom} = ₹1,70,467 \implies \text{\textbf{ALARM: CRITICAL INSOLVENCY}}$$

However, in reality, Prakash holds ₹6,40,000 in counted godown cash and ₹7,20,000 in collectible retailer credit. His true operational liquidity buffer is positive. Conversely, when a distributor appears solvent on paper with ₹5,00,000 in the bank, but faces ₹8,00,000 in unrecorded route payouts and ₹6,00,000 in GST challans due tomorrow, single-ledger software signals safety right before default.

---

### 2.2 Question 2: Ideal Customer Profile (ICP) Specification — Prakash Gupta / Kaveri Distributors

#### Demographics & Business Anatomy
- **Persona Name:** Prakash Gupta (Age: 47 years).
- **Enterprise:** Kaveri Distributors, Market Yard, Gultekdi, Pune, Maharashtra.
- **Constitution:** Sole Proprietorship (operating under GSTIN: `27AABPG1234F1Z5`).
- **Commercial Domain:** Wholesale distributor of FMCG packaged goods, soaps, edible oils, and packaged staples, holding distribution mandates for 3 major consumer goods brands across 110 retail kirana accounts.
- **Annual Turnover:** ₹18.0 Crore (~₹1.50 Crore gross monthly billing; average bank receipts ₹68.7 Lakh/month `[I1]`).
- **Net Operating Margin:** 1.5% to 4.0% net margin.
- **Staff Size (11 Employees):**
  - 4 Route Salesmen (field order-taking and cash collections via two-wheelers).
  - 2 Delivery Tempo Drivers (goods dispatch and return management).
  - 3 Godown Loaders / Hamali Laborers (inventory handling and packing).
  - 1 Billing & Tally Entry Clerk (on-site computer operator).
  - 1 Part-Time Visiting Chartered Accountant (attends 2 half-days per week).
- **Banking Infrastructure:** Single Current/Cash-Credit Account with Bank of Baroda, Market Yard Branch; sanctioned limit ₹25,00,000 at 11.75% interest against hypothecation of stock and book debts.

#### Authentic 5-Stage Day-in-the-Life Workflow

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                      PRAKASH GUPTA: 5-STAGE OPERATIONAL DAY-IN-THE-LIFE                │
└────────────────────────────────────────────────────────────────────────────────────────┘

  STAGE 1: 07:30 AM – 08:30 AM │ GODOWN ARRIVAL & MORNING CASH BLINDNESS
  ────────────────────────────────────────────────────────────────────────────────────────
  • Arrives at Market Yard warehouse. Sits at metal desk; unlocks physical godown safe.
  • Receives Bank of Baroda SMS: "CC Balance is -₹21,85,420. Available Limit: ₹3,14,580."
  • Opens physical cash drawer (Galla): counts ₹4,85,000 in mixed 500-rupee bundles.
  • Operational Dread: "Marico tempo arrives at 11:30 AM with ₹6.5L stock. If I pay cash,
    I get a 3% rokda discount (saves ₹19,500). But tomorrow is the 20th—GST challan of
    ₹2.8L must clear. If I deposit the drawer cash, will my CC headroom stay above the
    ₹2.5L safety floor? Who paid by UPI last night?"

  STAGE 2: 09:00 AM – 10:30 AM │ ROUTE SALESMAN DISPATCH & PARCHI ALLOCATION
  ────────────────────────────────────────────────────────────────────────────────────────
  • Four salesmen arrive on scooters to collect daily route sheets and dispatch orders.
  • Prakash hand-writes rough customer balances on paper slips (parchis).
  • Critical Blindness: Because Tally is 5 days stale, salesman Ramesh does not know that
    Shree Durga Stores owes ₹42,000 overdue for 68 days [A2]. Ramesh books another ₹15,000
    credit order, deepening bad debt exposure.
  • Salesmen depart for Hadapsar, Kothrud, Sinhagad Road, and Camp retail routes.

  STAGE 3: 11:30 AM – 02:30 PM │ COUNTER TRADING, UPI MINING & RTGS ROULETTE
  ────────────────────────────────────────────────────────────────────────────────────────
  • Wholesale walk-in retailers arrive at godown counter to buy high-velocity staples.
  • Phone pings continuously with UPI payment notifications on personal GooglePay QR.
  • 42% of incoming transfers omit the shop name [C5]: "Received ₹18,450 from
    Sunil_K_98". Prakash interrupts staff to check: "Whose boy is Sunil? Is he from
    Om Traders or Ganpati Bahi?"
  • Bank manager calls: "Gupta ji, your CC drawing power renewal stock statement is
    overdue, and balance touched -₹23.5L. Please deposit cash by 03:00 PM."

  STAGE 4: 07:30 PM – 08:45 PM │ SALESMAN RETURN & GALLA DAY-CLOSE RECONCILIATION
  ────────────────────────────────────────────────────────────────────────────────────────
  • Salesmen return from routes with crumpled collections, torn parchis, and wet currency.
  • Prakash sits for manual reconciliation: compares dispatched bills against collected cash,
    cheques, and WhatsApp screenshot proofs.
  • Cash balancing friction: Salesman Sachin collected ₹64,200 from 9 shops, but handed
    over ₹61,800 in cash, claiming ₹2,400 was paid for tempo diesel and municipal toll.
  • Galla drawer count: Expected ₹8,42,000; counted ₹8,38,200. Unaccounted drift of ₹3,800
    logged as "to check". Prakash is exhausted; cannot determine if drift was hamali or theft.

  STAGE 5: 09:15 PM – 10:30 PM │ NIGHT KHATA REVIEW & CAPITAL INFUSION DECISION
  ────────────────────────────────────────────────────────────────────────────────────────
  • Closes godown shutters. Reviews aging notebook under fluorescent bulb.
  • Discovers ₹23.8L in receivables has crossed 60 days [A2]. Hesitates to send legal
    notices to preserve business relationships.
  • Solvency Decision: Transfers ₹3,00,000 from his personal savings account into the
    business CC account to prevent tomorrow's cheques from bouncing [B1, B3].
```

---

### 2.3 Question 3: Solution & Alternatives Differentiation — Why Incumbents Fail

The Indian SME market is flooded with accounting tools, cloud ERPs, and micro-merchant apps. Yet, none solves Prakash Gupta's morning cash blindness. Each incumbent fails due to distinct architectural and business model limitations:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        COMPETITIVE ARCHITECTURAL DIFFERENTIATION                      │
├─────────────────────┬──────────────┬──────────────┬──────────────┬─────────────────────┤
│ Dimension           │ TallyPrime   │ Khatabook /  │ Excel /      │ SME Cash-Flow       │
│                     │ 7.1 / BUSY   │ OkCredit     │ GoogleSheets │ Copilot (Team 11)   │
├─────────────────────┼──────────────┼──────────────┼──────────────┼─────────────────────┤
│ Target User         │ Accountant / │ Micro Kirana │ Business     │ Business Owner /    │
│                     │ CA           │ Retailer     │ Owner / Self │ MD & Visiting CA    │
├─────────────────────┼──────────────┼──────────────┼──────────────┼─────────────────────┤
│ Core Architectural  │ Backward-    │ Simple Udhar │ Unstructured │ Forward-Looking     │
│ Orientation         │ Looking Tax  │ Bahi Khata   │ Manual Table │ Cash Operating OS   │
├─────────────────────┼──────────────┼──────────────┼──────────────┼─────────────────────┤
│ Split-Plane Bridge  │ ✗ Fails      │ ✗ Fails      │ ✗ Fragile    │ ✓ Native Dual-Plane │
│ (Bank + Cash Vault) │ Ghost Stock  │ No Bank Feed │ Data Silo    │ Sovereign Vault     │
├─────────────────────┼──────────────┼──────────────┼──────────────┼─────────────────────┤
│ Bank Reconciliation │ ½ Rigid CSV  │ ✗ None       │ ✗ Manual     │ ✓ Decision 60 Auto  │
│ Intelligence        │ No UPI Rules │ (QR Pay only)│ Eyeballing   │ 100% Precision Gate │
├─────────────────────┼──────────────┼──────────────┼──────────────┼─────────────────────┤
│ 90-Day Cash Flow    │ ½ Naive Due- │ ✗ None       │ ½ Static     │ ✓ Probabilistic MC  │
│ Forecasting         │ Date Points  │              │ Formulas     │ Kaplan-Meier Delays │
├─────────────────────┼──────────────┼──────────────┼──────────────┼─────────────────────┤
│ CC Overdraft Limit  │ ✗ Blind to   │ ✗ No CC/OD   │ ½ Manual     │ ✓ Integrated Net    │
│ Headroom Modeling   │ Drawing Power│ Concepts     │ Calculation  │ Usable Headroom     │
├─────────────────────┼──────────────┼──────────────┼──────────────┼─────────────────────┤
│ Statutory Safe-     │ MCA 11(g)    │ Cloud Data   │ Cloud Search │ On-Device SQLCipher │
│ guards & Privacy    │ Audit Log    │ Risk (DPDP)  │ Risk (ITA247)│ BNS 241 & BSA 63    │
└─────────────────────┴──────────────┴──────────────┴──────────────┴─────────────────────┘
```

#### Detailed Breakdown of Alternatives

1. **TallyPrime 7.1 / BUSY Accounting:**
   - *Why It Fails Prakash:* Tally is the gold standard for statutory tax filings and compliance reporting for Chartered Accountants. However, it is an accounting tool, not a cash operating system. 
   - *The Lag Barrier:* Data entry happens days or weeks after physical events. Prakash cannot make 08:00 AM decisions on an un-reconciled ledger.
   - *The Narration Blindspot:* Tally requires exact party matching. When a ₹18,450 payment arrives from unknown personal account `"Siddharth Pawar"`, Tally cannot resolve it against `"Durga Kirana"`, dumping it into an un-reconciled suspense ledger.
   - *MCA Rule 11(g) Rigidity:* TallyPrime Edit Log enforces immutable audit trails. Entering rough counter cash or estimated parchi collections directly into Tally corrupts corporate books, creates phantom "ghost stock" during inventory audits, and invites tax penalties under Section 247(1)(vi) of the Income-tax Act, 2025.

2. **Khatabook / OkCredit:**
   - *Why It Fails Prakash:* Mobile ledger apps serve micro-retailers (pan shops, small grocery stores) managing simple customer credit. 
   - *Scale & Complexity Gap:* They lack multi-invoice bill-wise settlement, cannot ingest MT940/CSV bank feeds, do not track bank CC overdraft limits, and cannot model multi-tier route salesman collection workflows.
   - *Regulatory Anxiety:* Storing informal customer credit books on third-party cloud servers exposes merchants to privacy violations under the **Digital Personal Data Protection (DPDP) Rules, 2025** and automated tax surveillance.

3. **Manual Excel / Google Sheets:**
   - *Why It Fails Prakash:* Spreadsheets are flexible but break down under commercial pressure. They require tedious manual entry, formulas break, and they lack automated bank feed ingestion. 
   - *Legal & Search Hazard:* Storing unbilled cash records in cloud spreadsheets (Google Drive) creates extreme legal exposure: Section 247 of the Income-tax Act, 2025 explicitly includes cloud drives and remote databases within **"virtual digital spaces"** subject to search, seizure, and password override by tax inspection officers. Furthermore, spreadsheet exports lack cryptographic hashes and are legally inadmissible in court under **Section 63 of the Bharatiya Sakshya Adhiniyam (BSA), 2023**.

4. **The Visiting Chartered Accountant / Tax Practitioner:**
   - *Why It Fails Prakash:* Prakash’s CA visits twice a week for 2 hours. The CA’s sole objective is statutory compliance: filing GSTR-1 by the 11th, GSTR-3B by the 20th, advance tax quarterly, and income tax audit by October. 
   - The CA does not care whether Prakash has enough cash at 08:30 AM to buy biscuits from Britannia or whether salesman Ramesh is collecting from Durga Kirana. The CA manages tax liabilities; Prakash must manage operational liquidity survival.

---

### 2.4 Question 4: Stated Non-Goals & Statutory Boundaries

To ensure absolute legal defensibility and prevent criminal or civil liability for both the business owner and software developers, SME Cash-Flow Copilot enforces four inviolable boundaries:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        INVIOLABLE STATUTORY FIREWALLS & NON-GOALS                      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. NOT FULL TAX ACCOUNTING OR GSTR-1 FILING ENGINE                                     │
│    • Never computes final tax liability, generates GSTR JSON files, or files returns.  │
│    • Never replaces the Chartered Accountant or primary accounting ERP (TallyPrime).   │
│    • Role: Pre-reconciliation intelligence layer feeding clean data to the accountant. │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. NOT AUTOMATED MONEY MOVEMENT OR PAYMENT EXECUTION                                   │
│    • Zero direct API integrations for automated bank debit, NEFT, or RTGS dispatch.    │
│    • Follows read-only approval paradigm: Generates drafts, reminders, and "Copy" links.│
│    • Every rupee movement requires explicit physical authorization by the owner.       │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. NOT TAX EVASION, AUDIT CONCEALMENT, OR PANIC WIPE ENGINE                            │
│    • Section 241 of Bharatiya Nyaya Sanhita (BNS), 2023: 3 years' imprisonment for     │
│      destroying, concealing, or secreting electronic records to avoid legal evidence.  │
│    • Section 132(1)(j) of CGST Act, 2017: Non-bailable criminal offense for evidence   │
│      tampering and record falsification.                                               │
│    • Strictly refuses all "panic wipe", "duress delete", or off-book evasion queries.  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. FORMAL EXCISION OF DECEPTIVE FEATURES (DECISION 68 & AUDIT REVIEW)                  │
│    • PURGED: "Accountant Presentation Mode" (deceptive concealment without audit trail)│
│      Replaced by Staff PIN Lock labeled: "Formal books only. Cash memo not included."  │
│    • PURGED: "SFT Headroom Countdown" (coaching users to stay below bank reporting).   │
│      Replaced by factual statutory notice of Rule 237 / Form 165 requirements.         │
│    • PURGED: "Capital-Infusion Readiness Score" (scoring tax scrutiny resistance).     │
│      Replaced by 3 Golden Pillars checklist: Identity, Creditworthiness, Genuineness.  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Detailed Legal Grounding of Boundaries

- **BNS Section 241 & CGST Section 132(1)(j) Compliance:**
  Section 241 of the Bharatiya Nyaya Sanhita (BNS), 2023 provides:
  > *"Whoever destroys, conceals, or secretes any document or electronic record with intent to prevent the same from being produced as legal evidence before any Court or public servant... shall be punished with imprisonment of either description for a term which may extend to three years, or with fine, or with both."*
  
  In the 12 November 2026 technical audit (`AUDIT-REVIEW.md`), early concepts proposing a "Panic Wipe" or a stealthy "Accountant Presentation Mode" (which secretly toggled off cash drawer records when an inspector was present) were identified as criminal evidence secretion. Under **Decision 68**, these features were completely excised. 
  
  The copilot implements only a transparent **Staff PIN Lock**, designed solely to prevent godown counter clerks from snooping on the owner's personal reserves. Whenever the Staff Lock is active, the screen explicitly displays a persistent warning banner:
  > *"Formal books only. The owner's cash memo is not included."*

- **Excision of Tax Evasion Coaching (Decision 68):**
  - *SFT Headroom Countdown:* Early prototypes displayed an active meter: *"₹4,20,000 cash deposits remaining before bank reports you under SFT Form 165"*. This was condemned as coaching tax evasion. It is replaced by a static, factual statutory notice explaining Rule 237 and Rule 159 limits.
  - *Capital-Infusion Readiness Score:* Scoring whether an unbacked cash deposit could "withstand Section 102/195 scrutiny" constituted unauthorized and unethical tax advice. It is replaced by a neutral **Deposit Records Checklist** verifying whether matching bank withdrawal slips, continuous cash books, or B2C sales chits exist before funds are deposited.

---

### 2.5 Question 5: Primary Success Metric & The True Solvency Equation

#### The North Star Metric
The primary operational success metric for SME Cash-Flow Copilot is:

$$\textbf{Zero Unexpected CC/OD Limit Breaches and } <\textbf{10 Minutes Daily Review Time}$$

A distributor cannot afford a single unexpected overdraft breach. A single breach triggers:
1. Dishonor of outward supplier cheques and RTGS transfers.
2. Criminal notice under Section 138 of the Negotiable Instruments Act.
3. Penal interest of 24% to 36% p.a. levied by the lending bank.
4. Immediate suspension of supplier credit and manufacturer distribution rights.

#### The 5-Part True Solvency Equation
To eliminate unexpected breaches while maintaining a review budget under 10 minutes (<5 minutes morning ritual, <1 minute evening cash close), the copilot computes **True Solvency Buffer** locally across five integrated financial components:

$$\begin{aligned}
\text{True Solvency Buffer} &= \underbrace{\left( \text{Bank Balance} + \text{CC Sanctioned Limit} \right)}_{\text{Component 1: Net Usable Bank Headroom}} \\
&\quad + \underbrace{\text{Counted Galla Cash}}_{\text{Component 2: Physical Till Cash}} \\
&\quad + \underbrace{\sum_{i} \left( \alpha_i \times \text{Khata Receivables}_i \right)}_{\text{Component 3: Risk-Discounted Informal AR}} \\
&\quad - \underbrace{\left( \text{Salaries} + \text{GST}_{\text{due}} + \text{TDS}_{\text{due}} + \text{EMIs}_{\text{due}} + \text{Cheques}_{\text{clearing}} \right)}_{\text{Component 4: 30-Day Formal Commitments}} \\
&\quad - \underbrace{\left( \text{Hamali} + \text{Tempo Freight} + \text{Supplier Rokda Payables} \right)}_{\text{Component 5: 30-Day Informal Cash Outflows}}
\end{aligned}$$

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                         THE 5-PART TRUE SOLVENCY EQUATION                              │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   [1] NET USABLE BANK HEADROOM                                                         │
│       = Bank Current Account Balance + Sanctioned CC Limit (₹25,00,000)                │
│       (Negative balance reduces headroom; positive balance increases headroom)         │
│                                                                                        │
│   [2] COUNTED GALLA CASH                                                               │
│       = Actual physical cash verified in godown till drawer at last close              │
│                                                                                        │
│   [3] RISK-DISCOUNTED KHATA RECEIVABLES                                                │
│       = Σ (α_i × Receivable_i), where default α = 0.85 (haircut for collection delay)  │
│                                                                                        │
│   [4] 30-DAY FORMAL COMMITMENTS                                                        │
│       = Staff Salaries (1st-5th) + GST Challans (20th) + TDS Challans (7th)            │
│         + Loan EMIs + Outward Cheques in clearing pipeline                             │
│                                                                                        │
│   [5] 30-DAY INFORMAL CASH OUTFLOWS                                                    │
│       = Committed cash freight (tempo) + Hamali loading labor + Supplier Rokda orders  │
│                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Empirical Demonstration: Resolving the False Insolvency Dilemma
Consider Kaveri Distributors' liquidity position on a typical mid-month morning:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ SINGLE-LEDGER FORMAL VIEW (TallyPrime / Bank Net Banking):                             │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Current Bank Balance (Overdrawn)                   : -₹22,80,000                       │
│ Immediate Formal Cheques / RTGS Due Today          :  ₹4,50,000                        │
│ Formal Net Bank Liquidity Position                 : -₹27,30,000 (₹2.3L ABOVE CC LIMIT)│
│ SIGNAL: CRITICAL DEFAULT! STOP ALL OPERATIONS! CANNOT PAY BILLS!                       │
└────────────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────────────┐
│ DUAL-PLANE SOVEREIGN VAULT VIEW (SME Cash-Flow Copilot):                               │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ [1] Net Usable Bank Headroom (₹25L Limit - ₹22.8L Drawn)      : +₹2,20,000             │
│ [2] Counted Godown Galla Cash (Ready to Bank or Pay)          : +₹5,40,000             │
│ [3] Risk-Discounted Khata Receivables (85% of ₹8.5L due <7d)  : +₹7,22,500             │
│     TOTAL LIQUIDITY CAPACITY AVAILABLE                        : +₹14,82,500            │
│                                                                                        │
│ [4] 30-Day Formal Commitments (RTGS ₹4.5L + GST ₹2.8L + Sal)  : -₹9,80,000             │
│ [5] 30-Day Informal Cash Outflows (Freight + Hamali)          : -₹1,60,000             │
│     TOTAL COMMITTED OUTFLOWS                                  : -₹11,40,000            │
│                                                                                        │
│ NET 30-DAY TRUE SOLVENCY BUFFER                               : +₹3,42,500             │
│ OPERATIONAL RUNWAY                                            : 11.4 DAYS SAFE BUFFER  │
│ ACTION RECOMMENDATION: Deposit ₹2,50,000 from Galla cash into Bank by 01:00 PM;        │
│                        RTGS of ₹4,50,000 clears safely with ₹4,70,000 headroom left.   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

By computing True Solvency across both planes, the copilot prevents panic owner borrowings while ensuring zero overdraft breaches.

---

### 2.6 Question 6: Open Operational Tensions & Regulatory Reconciliations

Deploying a financial copilot into India's complex commercial ecosystem exposes four critical structural tensions:

#### Tension 1: Automated WhatsApp Reminders vs DPDP Rules 2025
- *The Problem:* Debt collection requires chasing overdue kirana retailers via WhatsApp. However, the **Digital Personal Data Protection (DPDP) Rules, 2025** (gazetted on 13 November 2025) impose penalties up to **₹250 Crore** on Data Fiduciaries that upload customer contact books to third-party cloud Business Solution Providers (BSPs) without verifiable, unbundled consent.
- *The Copilot Resolution:* The copilot completely rejects cloud-based WhatsApp broadcasting. Instead, it generates **client-side `wa.me` deep links** locally on the owner's smartphone. Tapping a reminder button opens the merchant's native WhatsApp client with pre-drafted Hindi/English text and an embedded NPCI-compliant UPI QR link:
  ```
  https://wa.me/919822012345?text=Namaskar%20Gupta%20ji,%20Kaveri%20Distributors%20ka%20
  purana%20hisab%20Rs.18,450%20baaki%20hai.%20UPI%20karen:%20upi://pay?pa=kaveri@icici...
  ```
  Customer phone numbers and debts never leave the device, achieving 100% DPDP compliance.

#### Tension 2: Salesman Route Slip Timing & The Salesman Protection Shield
- *The Problem:* Field salesmen collect cash and cheques throughout the day. Bank deposits occur only every 3 to 4 days. If the copilot immediately compares bank deposits against outstanding invoices, it creates an evidentiary gap: retailers who paid the salesman still appear overdue, and salesmen are vulnerable to accusations of theft.
- *The Copilot Resolution:* Implementing the **Salesman Protection Shield** (`FR-CS-3`, Decision 55). At the evening cash close, the system logs salesman collections per shop (Shop, Amount, Date, Salesman). In the receivables dashboard, these shops are immediately tagged **"Collected by [Salesman], not yet banked"** and removed from the active chase list (`C3`). When a bulk cash deposit lands in the bank account days later, the combination matcher links it back to the specific collection slips, closing the loop without human friction.

#### Tension 3: Legal Debt Admissibility Under BSA §63 & Limitation Act §18
- *The Problem:* Under Article 14 and 15 of the **Limitation Act, 1963**, suits for the recovery of trade debt must be filed within **three years** of the invoice date; after 36 months, the debt is legally time-barred and uncollectible. Furthermore, under **Section 63 of the Bharatiya Sakshya Adhiniyam (BSA), 2023** (effective 1 July 2024), informal digital exports, spreadsheets, or phone screenshots are legally inadmissible in court without a valid Section 63(4) cryptographic hash certificate.
- *The Copilot Resolution (The Legal Shield):*
  1. *Month 30 Limitation Alert:* The Sovereign Vault tracks debt aging and fires an urgent alert at **Month 30** (6 months before expiry).
  2. *Section 18 Acknowledgment Reset:* Under Section 18 of the Limitation Act, a signed written or electronic acknowledgment of debt resets the 3-year clock back to Day Zero. The copilot drafts a polite balance confirmation WhatsApp message. When the retailer replies ("Haan, balance sahi hai" or makes a token ₹500 UPI payment under Section 19), the 3-year limitation clock is legally renewed.
  3. *BSA Section 63(4) Hash Certificate:* The copilot writes every transaction and balance confirmation into an immutable local SQLite database, generating a local SHA-256 hash log capable of producing a court-admissible Section 63(4) certificate upon export.

#### Tension 4: English & Hindi Localization with 100% Numerical Parity
- *The Problem:* Many financial tools use generative LLMs to translate financial summaries into Hindi. In commercial finance, LLM hallucination of numbers (e.g., converting ₹18,450 to ₹18,540 or misplacing a zero) destroys merchant trust and violates Kill Metric 4 (`GRILL-LOG.md` D31).
- *The Copilot Resolution:*
  1. *Zero LLM Arithmetic:* External LLMs (Claude API) handle language intent classification and prompt routing strictly on **PII-masked text** (Decision 32, 63). All calculations, balances, and numbers are executed strictly in deterministic Python code.
  2. *Single-Render CLDR Engine:* Numbers are rendered once in code using standard Common Locale Data Repository (CLDR) Indian grouping (`en_IN` and `hi_IN`, e.g., `₹12,34,567.50`) and injected into static bilingual template strings.
  3. *Gender-Neutral Copy:* Hindi verbs carry grammatical gender. To accommodate female entrepreneurs like Dr. Kavya, all Hindi prompts use impersonal passive constructions (*"किया जा सकता है"*) and respectful plural forms (*"आप पुष्टि करें"*), completely avoiding gendered verbal assumptions.

---

## 3. Persona CIRCLES Analysis: Prakash Gupta (Kaveri Distributors)

The CIRCLES framework is the industry gold standard for product requirements and user experience design. Below is the comprehensive 6-stage analysis for ICP Prakash Gupta.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        THE CIRCLES FRAMEWORK SPECIFICATION                             │
├────────────┬───────────────────────────────────────────────────────────────────────────┤
│ C          │ COMPREHEND CONTEXT: Indian FMCG wholesale, dual planes, rokda economics.  │
│ I          │ IDENTIFY PERSONA: Prakash Gupta, 47, proprietor, high cognitive load.     │
│ R          │ REPORT NEEDS: Morning liquidity, midday counter, evening galla balancing. │
│ C          │ CUT & PRIORITIZE: P0 Survival vs P1 Efficiency vs P2 Non-Goals.           │
│ L          │ LIST & EVALUATE: Architectural trade-offs, local-first vs cloud.          │
│ S          │ SUMMARIZE: The Zero-Knowledge Dual-Plane Cash Operating System.           │
└────────────┴───────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Comprehend: The Macro and Micro Operating Context
- **Commercial Macro-Structure:** Indian wholesale FMCG distribution is a high-volume, low-margin business operating under intense working capital constraints. Capital velocity determines survival.
- **Regulatory Pressure (2025–2026):** 
  - *Income-tax Act, 2025 (effective 1 April 2026):* Section 36(4) cash expense disallowance (>₹10,000/day); Section 185/188 cash loan/repayment ban (≥₹20,000); Section 186 single-receipt cash ceiling (≥₹2,00,000); Rule 237 / Form 165 SFT bank reporting (₹10L savings / ₹50L current).
  - *BNS, 2023 Section 241:* Criminalization of record destruction/secretion.
  - *BSA, 2023 Section 63:* Electronic evidentiary standards.
  - *DPDP Rules, 2025:* Strict customer privacy obligations.
- **The Core Economic Paradox:** Prakash is legally mandated to operate formally, but commercially compelled to hold physical cash to capture 25%–128% APR *rokda* discounts. He must balance on this razor's edge daily.

### 3.2 Identify: Detailed Persona Architecture
- **Name:** Prakash Gupta.
- **Role:** Sole Proprietor, Kaveri Distributors, Pune.
- **Psychological Drivers:** Pride in family business; deep protective instinct for his enterprise and family; terrified of public dishonor (cheque bounce) or government scrutiny (income tax/GST raids).
- **Core Anxieties:**
  1. *The 08:30 AM Overdraft Panic:* "Will my cheques bounce today? How close am I to the ₹25L CC limit?"
  2. *The Unidentified Inflow Fog:* "Who sent ₹22,500 by UPI? Which retailer should I stop delivery to?"
  3. *The Salesman Leakage Dread:* "Are my salesmen pocketing cash or losing collection slips?"
  4. *The Bad Debt Black Hole:* "Will my ₹23.8L overdue receivables expire under the Limitation Act?"

### 3.3 Report: Segmented 24-Hour Operational Needs

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        SEGMENTED OPERATIONAL NEEDS MATRIX                              │
├─────────────────────┬─────────────────────────────────┬────────────────────────────────┤
│ Operational Window  │ User Action & Mental State      │ Specific Copilot Need          │
├─────────────────────┼─────────────────────────────────┼────────────────────────────────┤
│ 1. MORNING RITUAL   │ Godown desk arrival; high       │ • 30-second audio summary      │
│ (07:30 – 08:30 AM)  │ anxiety; preparing route slips  │ • Single Net Usable Liquidity  │
│                     │ and assessing bank RTGS danger. │ • Top 2-3 cash swing items     │
│                     │                                 │ • Route collection sheet print │
├─────────────────────┼─────────────────────────────────┼────────────────────────────────┤
│ 2. MID-DAY COUNTER  │ Fast-paced wholesale trade;     │ • Rapid UPI counterparty lookup│
│ (11:30 – 03:00 PM)  │ noise, tempo loading; handling  │ • One-question PII-masked card │
│                     │ unreferenced UPI payments.      │ • Instant statutory check on   │
│                     │                                 │   cash payouts (>₹10k)         │
├─────────────────────┼─────────────────────────────────┼────────────────────────────────┤
│ 3. EVENING CLOSE    │ Salesman check-in; physical     │ • <1 minute Galla day-close    │
│ (07:30 – 08:45 PM)  │ fatigue; counting cash bundles; │ • Per-salesman slip match      │
│                     │ reconciling route slips.        │ • Neutral "to check" drift log │
│                     │                                 │ • 30-month Section 18 alerts   │
└─────────────────────┴─────────────────────────────────┴────────────────────────────────┘
```

### 3.4 Cut & Prioritize: P0 Survival, P1 Efficiency, P2 Non-Goals

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        REQUIREMENTS PRIORITIZATION MATRIX                              │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ P0: FINANCIAL SURVIVAL & STATUTORY INTEGRITY (MUST SHIP IN V1)                         │
│ • Net Usable Bank CC Headroom calculation integrated into True Solvency Engine.        │
│ • Decision 60 Qualified Auto-Reconciliation Engine (100% precision gate).              │
│ • Fail-Closed Multilingual Boundary Router (blocking tax, loan, and evasion advice).   │
│ • <1 Minute Galla Cash Day-Close with neutral "to check" drift logging.                │
│ • Client-Side wa.me Section 18 Limitation Alert link generation at Month 30.           │
│ • 100% On-Device SQLCipher AES-256 Sovereign Vault (Zero cloud sync).                 │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ P1: OPERATIONAL EFFICIENCY & WORKFLOW BRIDGES (CORE V1 VALUE)                          │
│ • Prakash's Monday Collection Planner (D17, D23: ≥85% receipts, ≥60% paying).          │
│ • Salesman Route Slip Export with "Collected, not yet banked" status shield.           │
│ • Explain-Anything Question Cards (D59: max 10/day, largest rupees first).             │
│ • Probabilistic 90-Day Cash Forecast using Kaplan-Meier empirical delay curves.        │
│ • Monthly Structured CA GST & TDS Summary Export (XLSX/PDF; D28).                      │
│ • Deterministic CLDR Bilingual Number Formatting (Kill Metric 4 parity).               │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ P2: ADVANCED SIMULATION & EXTENSIONS (POST-V1 ROADMAP)                                 │
│ • What-If Hypothetical Commitment Simulator (Scanner/Equipment EMI impact; D26, D43).  │
│ • Forecast Track Record Evaluator ("Last month we said X, it was Y"; D41).             │
│ • Account Aggregator (AA) Consent Simulation Engine (D47).                             │
│ • Marathi Language Localization (deferred per Apurav direction; D13).                  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ NON-GOALS / PROHIBITED SCOPE (EXPLICITLY REJECTED & PURGED)                            │
│ ✗ Automated tax filing / GSTR JSON generation (replaces CA).                           │
│ ✗ Automated money movement / direct bank debit execution.                              │
│ ✗ Panic wipe / Duress delete features (BNS §241 criminal liability).                   │
│ ✗ Deceptive Accountant Presentation Mode (purged per Decision 68).                     │
│ ✗ SFT headroom countdown meters & Tax scrutiny evasion scoring (Decision 68).          │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.5 List & Evaluate: Solution Trade-Offs & Architectural Feasibility

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        ARCHITECTURAL TRADE-OFF EVALUATION                              │
├─────────────────────┬──────────────────────────┬──────────────────────────┬────────────┤
│ Dimension           │ Architecture Choice A    │ Architecture Choice B    │ Selected & │
│                     │ (Standard / Competitor)  │ (Copilot Architecture)   │ Rationale  │
├─────────────────────┼──────────────────────────┼──────────────────────────┼────────────┤
│ Data Storage &      │ Cloud Multi-Tenant DB    │ Local-First On-Device    │ B: Immune  │
│ Sovereignty         │ (Postgres / Supabase)    │ SQLCipher AES-256 Vault  │ to ITA 247 │
├─────────────────────┼──────────────────────────┼──────────────────────────┼────────────┤
│ Bank Reconciliation │ Fuzzy Heuristics / ML    │ Strict Decision 60 Gate  │ B: Zero    │
│ Engine              │ (Guesses close amounts)  │ (0 errors, 95% UB ≤1%)   │ errors     │
├─────────────────────┼──────────────────────────┼──────────────────────────┼────────────┤
│ WhatsApp Debtor     │ Cloud WhatsApp BSP API   │ Client-Side wa.me        │ B: Zero    │
│ Chasing             │ (Automated broadcast)    │ Deep Links (Native App)  │ DPDP risk  │
├─────────────────────┼──────────────────────────┼──────────────────────────┼────────────┤
│ Cash Record         │ Deceptive "Panic Wipe"   │ Transparent Staff PIN    │ B: Lawful  │
│ Protection          │ or Stealth Hide Button   │ Lock with Partial Banner │ BNS §241   │
├─────────────────────┼──────────────────────────┼──────────────────────────┼────────────┤
│ Language Model      │ Raw Audio / Text Sent    │ PII-Masked Hybrid Gate   │ B: Zero    │
│ Integration         │ to External Cloud LLM    │ (Local Rules + Masked)   │ data leak  │
└─────────────────────┴──────────────────────────┴──────────────────────────┴────────────┘
```

### 3.6 Summarize: The Zero-Knowledge Dual-Plane Cash Operating System

The synthesis of the CIRCLES analysis establishes that Prakash Gupta does not need another complex accounting package. He requires a **Zero-Knowledge Dual-Plane Cash Operating System**:
- It pulls read-only formal bank and GST data downward into his device.
- It secures his private godown drawer cash and salesman collection slips inside an encrypted local vault that never leaks upward.
- It computes his true solvency in under 5 minutes every morning, guides his salesman collections, recovers his overdue trade debts before they expire under Indian law, and gives him complete peace of mind without ever compromising his legal integrity.

---

## 4. UX/UI Design Choices Analysis: "Aaj Ka Hisaab" Cockpit

### 4.1 The "Aaj Ka Hisaab" Viewport Workflow (Zero Desktop Scroll)

In the physical environment of an Indian godown—surrounded by tempo horns, moving hand-carts, dust, and shouting laborers—a user cannot navigate complex nested menus or scroll through multi-page tables.

The **"Aaj Ka Hisaab" (Today's Account)** cockpit is engineered as a **Zero Desktop Scroll** interface:
- **Viewport Lock:** On standard desktop displays (1366×768 to 1920×1080) and tablet screens, the entire operational dashboard fits 100% inside the vertical viewport.
- **Internal Box Scrolling:** Tables (receivables aging, daily transactions) scroll strictly inside their own fixed containers; the overall browser page never scrolls vertically.
- **Single Thumb Mobile Architecture:** On mobile devices (390×844 viewport), the workflow condenses into a clean single-column feed with persistent bottom navigation.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                      "AAJ KA HISAAB" ZERO-SCROLL COCKPIT LAYOUT                        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ [Header] Kaveri Distributors (Pune) │ Role: Owner 🔒 │ Sync: Today 08:00 AM │ [EN / हिं]│
├────────────────────────────────────────────────────────────────────────────────────────┤
│ TIER 1: HERO NET USABLE LIQUIDITY CARD                                                 │
│ ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│ │  CASH YOU CAN PLAN ON (AS OF 14 NOV)                                               │ │
│ │  ₹8,82,500  [P10: ₹6,40,000  ───  P90: ₹11,20,000]                                 │ │
│ │  Status: 11.4 Days Runway Buffer │ Safe Floor: ₹2,50,000                           │ │
│ └────────────────────────────────────────────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ TIER 2: FOUR OPERATIONAL PULSE TILES                                                   │
│ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐    │
│ │ BANK CC HEADROOM │ │ COUNTED GALLA    │ │ OVERDUE >60 DAYS │ │ TODAY'S INFLOWS  │    │
│ │ ₹3,14,580        │ │ ₹4,85,000        │ │ ₹23,81,682       │ │ ₹1,85,400        │    │
│ │ (Limit: ₹25.0L)  │ │ (Ties with Safe) │ │ (91 Invoices)    │ │ (42% Unresolved) │    │
│ └──────────────────┘ └──────────────────┘ └──────────────────┘ └──────────────────┘    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ TIER 3: SINGLE FOCAL ACTION CARD                                                       │
│ ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│ │  ⚠️ WARNING · CC LIMIT HEADROOM (PROJECTED 18 NOV)                                  │ │
│ │  On 18 Nov, Bank Headroom is projected at ₹1,42,000, falling below ₹2.5L floor.    │ │
│ │  Top Swing Items: Marico RTGS (-₹4.5L, 16 Nov) · Britannia (-₹2.2L, 17 Nov)        │ │
│ │  [ View 90-Day Forecast ] [ Generate Monday Chase List ] [ Dismiss ]               │ │
│ └────────────────────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Three-Tier Visual Hierarchy & Screen Ergonomics

The screen architecture enforces strict cognitive gating:
1. **Tier 1: Hero Liquidity Metric:** Displays "Cash You Can Plan On" as an empirical range ($P_{10}$ to $P_{90}$) and days of runway buffer. Prakash absorbs his immediate solvency status within 3 seconds of opening the screen.
2. **Tier 2: Four Operational Pulse Tiles:** Surfaces the four pillars of distributor liquidity:
   - *Bank CC Headroom:* Real-time distance from the credit ceiling.
   - *Counted Galla Cash:* Verified cash in the warehouse safe.
   - *Overdue Receivables >60 Days:* Trapped capital requiring active recovery.
   - *Today's Inflows:* Incoming collections with unresolved narration indicators.
3. **Tier 3: Single Focal Action Card:** Displays exactly **one** primary operational priority at a time (e.g., an early warning card with the top 2–3 swing items, or an explain-anything question card `FR-OQ-1`). The user is never confronted with competing modal dialogs.

### 4.3 High-Glare Ambient Lighting & Contrast Engineering (WCAG 2.1 AA/AAA)

Wholesale godowns feature harsh ambient lighting conditions: glaring direct sunlight cutting across open roll-up metal shutters contrasted against deep shadows in windowless storage bays. Standard low-contrast SaaS themes (soft grey text `#9E9E9E` on white `#FFFFFF`) become completely unreadable.

The copilot implements a hardened high-contrast theme compliant with WCAG 2.1 AA and AAA standards:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        WCAG 2.1 CONTRAST & ACCESSIBILITY AUDIT                         │
├─────────────────────────┬───────────────────┬──────────────┬─────────────┬─────────────┤
│ UI Element              │ Color Hex Pair    │ Measured     │ WCAG Target │ Pass/Fail   │
│                         │ (FG on BG)        │ Contrast     │ Criterion   │ Status      │
├─────────────────────────┼───────────────────┼──────────────┼─────────────┼─────────────┤
│ Primary Text            │ #0F1E2E on White  │ 16.86:1      │ 4.5:1 (AA)  │ PASS (AAA)  │
│ Secondary Text          │ #44546A on White  │ 7.71:1       │ 4.5:1 (AA)  │ PASS (AAA)  │
│ Section Eyebrows        │ #0848C4 on #E8EFFF│ 6.66:1       │ 4.5:1 (AA)  │ PASS (AA)   │
│ Primary Button Surface  │ White on #0B5FFF  │ 5.13:1       │ 4.5:1 (AA)  │ PASS (AA)   │
│ Secondary Button Border │ #7D8A9C on White  │ 3.51:1       │ 3.0:1 (UI)  │ PASS (UI)   │
│ Card Boundary Borders   │ #B8B8B0 on White  │ 3.22:1       │ 3.0:1 (UI)  │ PASS (UI)   │
│ Danger / Warning Text   │ #9A4A00 on #FFF0DE│ 5.60:1       │ 4.5:1 (AA)  │ PASS (AA)   │
│ Success Confirmation    │ #0B7A3B on #EAF6EF│ 4.90:1       │ 4.5:1 (AA)  │ PASS (AA)   │
└─────────────────────────┴───────────────────┴──────────────┴─────────────┴─────────────┘
```

*Crucial Boundary Fix:* In standard web frameworks, card boundaries use `#E3E9F0` (contrast ratio 1.22:1), which washes out completely in godown glare. The copilot enforces `#B8B8B0` at **3.22:1** and button borders `#7D8A9C` at **3.51:1**, exceeding the WCAG 1.4.11 non-text contrast mandate (≥3.0:1) and ensuring razor-sharp card definition under bright fluorescent or outdoor lighting.

### 4.4 Non-Color Status Encoding

Under WCAG 2.1 Guideline 1.4.1 ("Use of Color"), color must never serve as the sole vehicle for transmitting critical status or urgent system warnings. In high-stress distributor environments, red-green color-blindness (affecting ~8% of Indian males) and display wash-out make color-only tags catastrophic.

The copilot strictly enforces **dual-channel encoding** across every status element:
1. **Warning Cards:** Display an amber accent, but feature the literal bold text `"WARNING · CREDIT LIMIT"` in the card eyebrow, accompanied by an explicit warning icon.
2. **Review Queue Tags:** Every status badge combines color with an immutable textual label:
   - `[ ? SUGGEST ]` — Deep Blue with question mark.
   - `[ ! ASK ]` — Dark Amber with exclamation point.
   - `[ 👤 WITH OWNER ]` — Purple with user silhouette.
   - `[ ✓ DONE ]` — Forest Green with checkmark.
3. **Cash Day-Close Drift:** If the physical count differs from expected cash, the system never flags it in red as "THEFT" or "DEFICIT". It displays a neutral slate badge reading:
   $$\text{\textbf{[ TO CHECK: ₹3,800 ]}}$$
   ensuring neutral dignity while remaining instantly discernible in grayscale screenshots.

### 4.5 The <10-Minute Daily Review Time Budget

Prakash Gupta cannot spend 45 minutes analyzing software. The copilot's daily workflow is rigorously timed to execute in under **10 minutes total per day**:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        THE <10-MINUTE DAILY REVIEW TIME BUDGET                         │
├─────────────────────┬──────────┬───────────────────────────────────────────────────────┤
│ Operational Step    │ Duration │ Specific User Action & System Execution               │
├─────────────────────┼──────────┼───────────────────────────────────────────────────────┤
│ 1. Audio Briefing   │ 0.5 Min  │ Listens to 30-sec vernacular Web Speech audio         │
│                     │ (30 sec) │ summary: "Net cash ₹8.8L. Bank headroom ₹3.1L.        │
│                     │          │ ₹4.5L RTGS clears safely. 2 warnings today."          │
├─────────────────────┼──────────┼───────────────────────────────────────────────────────┤
│ 2. Visual Scan      │ 2.0 Min  │ Reviews Hero Liquidity Range and 4 Pulse Tiles.       │
│                     │          │ Checks 90-day trajectory chart and swing items.       │
├─────────────────────┼──────────┼───────────────────────────────────────────────────────┤
│ 3. Chaser Dispatch  │ 2.0 Min  │ Taps "Send Reminders" on Monday Collection List.      │
│                     │          │ Dispatches 3–5 pre-filled client-side wa.me links.    │
├─────────────────────┼──────────┼───────────────────────────────────────────────────────┤
│ 4. Route Sheet      │ 1.0 Min  │ One-tap export/print of 4 salesman route collection   │
│    Generation       │          │ sheets with "Collected, not banked" shield badges.    │
├─────────────────────┼──────────┼───────────────────────────────────────────────────────┤
│ 5. Midday Inbox Qs  │ 3.5 Min  │ Answers 2–3 Explain-Anything cards (FR-OQ-1) via      │
│                     │          │ 1-tap buttons ("Who is Siddharth Pawar?").            │
├─────────────────────┼──────────┼───────────────────────────────────────────────────────┤
│ 6. Evening Day-Close│ 1.0 Min  │ Enters 4 figures: Cash Taken, Petty Hamali, Banked,   │
│                     │          │ Counted Cash. Day ties or logs "to check" drift.      │
├─────────────────────┼──────────┼───────────────────────────────────────────────────────┤
│ TOTAL TIME INVESTED │ 10.0 Min │ COMPLETE OPERATIONAL CONTROL RESTORED                 │
└─────────────────────┴──────────┴───────────────────────────────────────────────────────┘
```

### 4.6 Ergonomic Touch Targets & Hardware Constraints

Wholesale distributors and warehouse managers operate smartphones while handling goods. Hands are frequently dusty, calloused, or covered in packing grease. 

To ensure error-free physical interaction:
- **WCAG 2.5.5 (AAA) Touch Sizing:** All tappable controls, segmented language toggles, question card buttons, and quick-filter chips enforce a minimum target size of **44 × 44 pixels** (with a minimum 8 px spacing buffer).
- **No Drag-and-Drop or Multi-Finger Gestures:** All operations execute on single-tap buttons. Sliders and precision pinch-to-zoom gestures are prohibited.
- **Hardware Resiliency:** Streamlit and mobile layouts are optimized for low-cost Android handsets (e.g., Redmi 12, Samsung Galaxy M-series) with 3GB–4GB RAM, ensuring smooth local SQLite execution without thermal throttling or app restarts.

### 4.7 Vernacular Commercial Lexicon & Non-Incriminating UI Typography

The vocabulary of financial software carries intense psychological and legal weight. If an enterprise device is ever examined by tax authorities under Section 247(7) statutory presumptions, incriminating or loaded labels in software interfaces can be weaponized against the taxpayer as evidence of willful evasion.

The copilot strictly prohibits loaded accounting terminology and enforces an authentic, approved vernacular lexicon validated across traditional Indian commerce:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        COMMERCIAL UI LEXICON COMPLIANCE TABLE                          │
├─────────────────────────────────────┬──────────────────────────────────────────────────┤
│ Prohibited Incriminating / Anxiety  │ Approved Neutral Commercial UI Terminology       │
│ Terminology (Banned in UI & Exports)│ (Enforced across English & Hindi Screens)        │
├─────────────────────────────────────┼──────────────────────────────────────────────────┤
│ ✗ "Black Money" / "Shadow Cash"     │ ✓ "Galla Balance" / "Counted Till Cash"          │
│ ✗ "Unrecorded Sales" / "Off-Book"   │ ✓ "Direct Settlements" / "Counter Receipts"      │
│ ✗ "Secret Stash" / "Evasion Buffer" │ ✓ "Private Reserve" / "Working Liquidity Pool"   │
│ ✗ "Kaccha Udhar" (in texts)         │ ✓ "Pending Khata Balance" / "Account Summary"    │
│ ✗ "Duress Mode" / "Audit Hide"      │ ✓ "Staff PIN Lock" / "Formal Books View"         │
│ ✗ "Theft" / "Cash Deficit"          │ ✓ "To Check" / "Unreconciled Cash Difference"    │
│ ✗ "Defaulting / Delinquent Party"   │ ✓ "Delayed Account" / "Needs Follow-up"          │
│ ✗ "Legal Notice Warning"            │ ✓ "Section 18 Balance Confirmation Link"         │
└─────────────────────────────────────┴──────────────────────────────────────────────────┘
```

### 4.8 Bilingual Parity & Deterministic CLDR Number Formatting

To serve both English-speaking accountants and Hindi-preferring proprietors, the copilot provides an instant, zero-latency language toggle (`EN` / `हिं`). 

Under Kill Metric 4 (`GRILL-LOG.md` D31), **any numerical mismatch between the English and Hindi interfaces constitutes an immediate build failure**. 

#### Deterministic Formatting Rules
1. **Zero LLM Digit Generation:** Language models are strictly prohibited from generating numerical figures. Figures are calculated once as 64-bit IEEE floating-point numbers or exact Python `Decimal` instances in backend services.
2. **CLDR Grouping Parity:** Both English and Hindi screens render numbers using Common Locale Data Repository (CLDR) Indian digit grouping (lakhs and crores: `2,2,3` grouping):
   $$\text{English: } \textbf{₹12,34,567.50} \quad\iff\quad \text{Hindi: } \textbf{₹12,34,567.50}$$
3. **Impersonal, Gender-Neutral Hindi Copy:** Hindi verbs carry gender inflections. The copilot uses neutral passive constructions and respectful plural forms, ensuring seamless usability for both male and female business owners:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                     BILINGUAL PARITY VERIFICATION SAMPLE                               │
├───────────────────────────────────┬────────────────────────────────────────────────────┤
│ English Interface Screen Copy     │ Hindi Interface Screen Copy (Draft Verified)       │
├───────────────────────────────────┼────────────────────────────────────────────────────┤
│ ONE QUESTION FOR YOU              │ आपके लिए एक सवाल                                   │
│ Who is {payer_name}?              │ {payer_name} कौन हैं?                              │
│ {amount} came by UPI on {date}    │ {date} को एक निजी खाते से UPI द्वारा {amount} आए।   │
│ from a personal account. Which    │ किस दुकान ने भुगतान किया?                          │
│ shop paid?                        │                                                    │
├───────────────────────────────────┼────────────────────────────────────────────────────┤
│ [ Button 1: Durga Kirana ]        │ [ बटन १: दुर्गा किराना ]                            │
│ Open invoice {inv} is {amount}    │ खुला बिल {inv} ठीक {amount} का है                  │
├───────────────────────────────────┼────────────────────────────────────────────────────┤
│ [ Button 2: Another Shop ]        │ [ बटन २: कोई और दुकान ]                           │
├───────────────────────────────────┼────────────────────────────────────────────────────┤
│ [ Button 3: Not a Customer ]      │ [ बटन ३: यह ग्राहक का भुगतान नहीं है ]             │
├───────────────────────────────────┼────────────────────────────────────────────────────┤
│ CLOSE TODAY'S CASH · UNDER 1 MIN  │ आज का कैश बंद करें · एक मिनट से कम                 │
│ Cash taken today                  │ आज मिला कैश                                        │
│ Spent from cash (petty)           │ कैश से खर्च (छोटे खर्च)                            │
│ Deposited at the bank             │ बैंक में जमा                                       │
│ Counted in hand now               │ अभी गिना गया कैश                                   │
│ {drift} is listed **to check**    │ उम्मीद से {drift} — इसे **जाँच के लिए** रखा गया है │
└───────────────────────────────────┴────────────────────────────────────────────────────┘
```

---

## 5. Summary & Implementation Verification

This specification establishes an exhaustive, legally verified, and mathematically grounded foundation for Milestone 1 of SME Cash-Flow Copilot.

### Document Index & Verification References
- **Domain Modeling & ADRs:** Aligned with `ps11-copilot/GLOSSARY.md` and Architecture Decision Records (ADRs 0001–0003).
- **Empirical Grounding:** Derived from 13,359 bank lines, 6,438 invoices, and the 49 verified checks in `checkin1/CHECK-INDEX.md` (`[A1, A2, A5, A6, B1, B2, B3, C5, R4, R11, T1, T2, T3]`).
- **Post-Audit Corrections:** Fully incorporates the corrections mandated in `GRILL-LOG.md` (Round 11, Decisions 68–72) and `AUDIT-REVIEW.md`, including the formal excision of Accountant Presentation Mode, SFT headroom coaching, and capital-infusion readiness scores.
- **Statutory Framework:** Verified against the **Income-tax Act, 2025** and **Income-tax Rules, 2026** (effective 1 April 2026), **Bharatiya Nyaya Sanhita, 2023** (§241), **Bharatiya Sakshya Adhiniyam, 2023** (§63), **CGST Act, 2017** (§31, §122, §132), **Limitation Act, 1963** (§18, §19), and **DPDP Rules, 2025**.

*The SME Cash-Flow Copilot bridges the gap between formal banking and informal godown reality, giving Indian distributors complete operational control and financial peace of mind—without ever breaking the law.*
