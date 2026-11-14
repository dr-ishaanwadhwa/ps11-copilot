# ADR 0003: Statutory Compliance and Limitation Legal Shield

## Status
accepted

## Context
Indian distributors and wholesale traders operate in a high-risk statutory environment governed by commercial credit laws, digital evidence standards, and stringent anti-evasion tax provisions.

First, under the Limitation Act, 1963, unsecured commercial trade credit expires and becomes legally unenforceable in civil court after three years (36 months) from the invoice or delivery date. Over 40% of overdue SME receivables quietly cross this 3-year threshold, resulting in complete capital forfeiture because business owners lack systematic tracking of limitation clocks. However, under Section 18 (written or electronic balance acknowledgment) and Section 19 (part-payment) of the Limitation Act, a valid acknowledgment made before expiry legally resets the 3-year limitation clock back to day zero.

Second, under Section 63 of the Bharatiya Sakshya Adhiniyam (BSA), 2023 (which replaced Section 65B of the Indian Evidence Act, 1872), electronic records such as WhatsApp messages, payment screenshots, and digital account statements are only admissible in court proceedings if accompanied by a Section 63(4) certificate confirming hardware provenance, device custody, and cryptographic hash integrity.

Third, during tax surveys, GST inspections, or search proceedings, distressed business owners frequently demand software features such as "panic wipe" buttons, clandestine dual databases, or emergency data concealment modes to destroy unbilled cash records. Under Section 241 of the Bharatiya Nyaya Sanhita (BNS), 2023, destroying, altering, or secreting electronic records with the intent to prevent their production in legal proceedings is a serious criminal offence punishable by up to three years imprisonment. Similarly, Section 132(1)(j) of the Central Goods and Services Tax (CGST) Act, 2017 criminalizes the tampering with or destruction of material evidence.

Fourth, the Income-tax Act, 2025 (effective 1 April 2026) imposes strict cash transaction thresholds: Section 36(4) caps daily business cash expenditures to a single person at ₹10,000 (with an exception up to ₹35,000 for goods carriage transport under Section 36(6)), imposing a 100% tax deduction disallowance on breaches; Section 186 imposes a 100% monetary penalty on single-day cash receipts of ₹2,00,000 or more; Section 185 and Section 188 penalize accepting or repaying loans/deposits in cash of ₹20,000 or more; and Rule 237 (mandated via Form 165) requires commercial banks to report annual cash deposits exceeding ₹50,00,000 in current accounts or ₹10,00,000 in savings accounts under the Statement of Financial Transactions (SFT).

## Decision
We establish a comprehensive, deterministic **Statutory Legal Shield** embedded natively across the copilot architecture:

1. **Section 18 Limitation Renewal Shield**:
   - The engine continuously tracks the aging of every open debtor account.
   - At 30 months elapsed (180 days prior to the statutory 36-month expiry), the engine raises an urgent limitation alert badge (`months_open >= 30`).
   - The system generates client-side, polite vernacular WhatsApp renewal drafts (`wa.me` links) requesting formal balance confirmations or nominal token UPI payments, which legally reset the 3-year limitation countdown back to zero under Sections 18 and 19.

2. **BSA Section 63 Digital Evidence Hashing**:
   - Every balance confirmation, customer acknowledgment, collection slip, and communication record is hashed on-device using SHA-256.
   - The resulting cryptographic digest is stamped alongside local device identifiers, transmission timestamps, and counterparty metadata, enabling one-click generation of export-ready Section 63(4) evidence certificates for court recovery suits.

3. **Absolute Ban on Panic Wipes & Anti-Spoliation Compliance (BNS §241)**:
   - We categorically reject and prohibit all panic wipes, hidden stealth toggles, duress destruction scripts, or evasive dual ledgers.
   - To serve legitimate external accounting needs (e.g. CA quarterly tax reviews), the application provides a lawful role-based presentation view ("Formal books only") with an immutable, prominent banner: *"Formal books only. The owner's cash memo is not included in this view."* This satisfies MCA Rule 11(g) audit integrity while fully protecting users and developers from criminal evidence tampering prosecution under BNS §241 and CGST Act §132(1)(j).

4. **Deterministic Cash Limit Interceptors**:
   - Real-time fact-checking intercepts transactions exceeding statutory limits: ₹10,000 business cash expenses under ITA 2025 Sec 36(4), ₹2,00,000 cash receipts under Sec 186, and ₹20,000 cash loan movements under Sec 185/188.
   - The copilot displays factual citations and tax consequence notices (100% tax disallowance or equal penalty exposure) along with lawful payment alternatives (account-payee cheque, NEFT/RTGS, UPI).
   - For cumulative annual bank cash deposits, the copilot tracks proximity to Rule 237 SFT reporting thresholds factually, strictly refusing to provide evasion advice or deposit structuring techniques and always providing an audit documentation checklist for Chartered Accountant referral.

## Considered Options
- **Emergency Duress / Panic Wipe Feature**: Categorically rejected. Violates BNS Section 241 and CGST Act Section 132(1)(j), exposing both the SME merchant and the software engineering team to criminal prosecution for active evidence spoliation.
- **Unmonitored Debt Aging**: Rejected. Results in massive unrecoverable bad debts as trade credit quietly passes the 36-month statutory cliff without merchant awareness.
- **Statutory Legal Shield Architecture**: Accepted. Proactively preserves merchant legal standing for debt collection, guarantees admissible electronic evidence under BSA 2023 §63, enforces anti-spoliation compliance under BNS §241, and prevents punitive tax disallowances under the Income-tax Act, 2025.

## Consequences
- **Positive**: Rescues at-risk trade receivables before statutory expiration; establishes legally admissible evidence trails; shields developers and users from criminal liability; maintains 100% adherence to Indian statutory frameworks.
- **Negative / Trade-off**: Refuses user requests for tax evasion, restructuring, or clandestine record destruction; requires business owners to manage CA audits through lawful presentation boundaries rather than concealment.
