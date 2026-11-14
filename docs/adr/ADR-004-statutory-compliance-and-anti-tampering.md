# ADR-004: Statutory Compliance, Anti-Tampering, and Evidentiary Integrity Architecture

> **Status:** Accepted  
> **Date:** 2026-11-14  
> **Deciders:** Team 11 Architecture Board  
> **Technical Domain:** Statutory Tax Compliance, Criminal Law Safeguards, Audit Trail Integrity, Anti-Tampering Architecture  
> **Cross-References:** `GLOSSARY.md` (§6), `copilot.vault.guardrails`, `copilot.vault.models`, `tests/test_vault.py`  

---

## 1. Context and Problem Statement

SME owners in India operate in an aggressive regulatory climate governed by modern statutory frameworks:
1. **The Income-tax Act, 2025** and **Income-tax Rules, 2026** (effective 1 April 2026, overhauling the Income-tax Act, 1961).
2. **Bharatiya Nyaya Sanhita (BNS), 2023** (effective 1 July 2024, replacing the Indian Penal Code, 1860).
3. **Central Goods and Services Tax (CGST) Act, 2017**.
4. **Companies (Accounts) Rules, 2014 (Rule 11(g) Audit Trail Mandate)**.

In informal trading circles, software developers are frequently asked to build features that conceal or destroy records during tax inspections:
- **"Panic Wipe" / "Emergency Nuke" Buttons**: A hidden gesture or hotkey that instantly deletes local databases or clears memory upon a tax survey or search.
- **"Dual-Company Stealth Toggle"**: A hidden switch that conceals cash transactions without leaving any audit trace, presenting a false, sanitized screen to visiting officers.
- **"Cash Structuring / Smurfing Assistants"**: Algorithmic advice that calculates how to split a large cash receipt (e.g., ₹4,50,000) across multiple fake invoices under ₹2,00,000 to circumvent statutory cash ceilings.

Implementing such features exposes the software engineers, platform architects, and business owners to severe criminal liability:
- Under **Section 241 of the Bharatiya Nyaya Sanhita (BNS), 2023** (Destruction of document or electronic record to prevent its production as evidence), destroying or altering electronic records to conceal evidence from a public servant carries imprisonment up to two years, a fine, or both.
- Under **Section 132(1)(i) of the CGST Act, 2017**, tampering with or destroying material evidence in relation to tax evasion is a non-bailable criminal offense.
- Under **Rule 11(g) of the Companies (Accounts) Rules, 2014**, software must maintain an immutable, tamper-evident audit trail with no ability to disable or manipulate logging.

We must define unambiguous architectural boundaries that protect the platform and the merchant: strictly prohibiting evidence tampering while providing lawful, transparent presentation modes and deterministic statutory tripwires.

---

## 2. Decision

We establish the following core architectural mandates (`src/copilot/vault/guardrails.py` and `src/copilot/vault/models.py`):

```
+-----------------------------------------------------------------------------------+
|                        STATUTORY BOUNDARY ENGINE MATRIX                           |
+-----------------------------------------------------------------------------------+
| 1. Income-tax Act, 2025 §186 (Old 269ST)                                          |
|    - Threshold: Cash receipt >= Rs. 2,00,000 / day / person                       |
|    - Engine Response: BLOCKED + Penalty Notice + Lawful Remedy                    |
|    - Prohibition: Strict refusal to split into smaller invoices                   |
|                                                                                   |
| 2. Income-tax Act, 2025 §36(4)-(6) (Old 40A(3))                                  |
|    - Threshold: Cash expense > Rs. 10,000 (Rs. 35,000 transport)                  |
|    - Engine Response: WARNING + Disallowance Notice + Lawful Remedy               |
|                                                                                   |
| 3. Income-tax Act, 2025 §185 & §188 (Old 269SS & 269T)                            |
|    - Threshold: Cash loan acceptance / repayment >= Rs. 20,000                    |
|    - Engine Response: BLOCKED + S.185/188 Citation + Account-Payee Requirement    |
|                                                                                   |
| 4. Income-tax Rules, 2026 Rule 237 (SFT Reporting)                                |
|    - Bank SFT Reporting Thresholds: Rs. 10L (Savings) / Rs. 50L (Current)         |
|    - Engine Response: Neutral Facts + Records Checklist + CA Referral             |
|    - Prohibition: NO countdowns, NO remaining headroom, NO evasion advice        |
|                                                                                   |
| 5. Bharatiya Nyaya Sanhita, 2023 §241 & CGST §132                                 |
|    - Strict Architectural Ban on "Panic Wipe", "Nuke", or stealth deletion       |
|    - Lawful Presentation Mode: displays transparent Partial View Notice           |
|      "Formal books only. The owner's cash memo is not included in this view."    |
+-----------------------------------------------------------------------------------+
```

### 2.1 Absolute Prohibition of Panic Wipes, Database Deletion, or Tampering
- The copilot code will **NEVER** include:
  1. Any "panic wipe", "database nuke", or "emergency reset" button or shortcut.
  2. Any code that deletes or overwrites database files in response to hotkeys, remote signals, or location triggers.
  3. Any code that assists in splitting invoices, structuring cash deposits, or evading statutory ceilings.
- Attempting to circumvent these safeguards violates platform integrity and triggers immediate system halt.

### 2.2 Lawful Presentation Mode with Transparent Partial View Notice
- Business owners frequently need to display their screens to visiting junior bookkeepers, delivery personnel, or external auditors.
- To maintain privacy without committing evidentiary concealment under BNS §241, the copilot provides a **Role-Locked Presentation Mode**.
- In Presentation Mode, the UI displays only the Formal Plane (Plane A).
- **Mandatory Partial View Notice**: The UI displays an overt, unremovable banner:
  ```python
  PARTIAL_VIEW_NOTICE = "Formal books only. The owner's cash memo is not included in this view."
  ```
- **Legal Invariant**: This notice explicitly states that the view is scoped to formal records, eliminating any false claim that the merchant presented a fabricated all-inclusive ledger.

### 2.3 Deterministic Statutory Tripwires (`copilot.vault.guardrails`)
The copilot implements deterministic compliance checks that evaluate transactions against the Income-tax Act, 2025:
1. **Section 186 (Old Section 269ST) — Single-Day Cash Receipt Ceiling**:
   - Limit: **₹2,00,000** from a person in a day or in respect of a single transaction.
   - Status: `BLOCKED` if amount $\ge ₹2,00,000$.
   - Lawful Remedy: *"Accept payment via formal digital banking (IMPS/NEFT/RTGS/UPI) or account-payee cheque. Splitting the bill into multiple smaller cash receipts is illegal structuring."*
2. **Section 36(4)–(6) (Old Section 40A(3)) — Business Cash Expense Ceiling**:
   - Limit: **₹10,000** per day per payee (**₹35,000** for payment to goods transport operators).
   - Status: `WARNING` if exceeded (100% tax disallowance of expense).
   - Lawful Remedy: *"Settle via bank transfer (UPI, NEFT, Net Banking) to preserve full business expense deduction."*
3. **Section 185 & Section 188 (Old Sections 269SS & 269T) — Informal Cash Loans**:
   - Limit: **₹20,000** for accepting or repaying any loan or deposit in cash.
   - Status: `BLOCKED` if amount $\ge ₹20,000$.
   - Lawful Remedy: *"Route all business borrowing or repayments strictly through account-payee banking channels."*

### 2.4 Rule 237 SFT Reporting Neutrality (Decision 68)
Under Rule 237 of the Income-tax Rules, 2026, banking institutions must report aggregate cash deposits of **₹10 Lakh or more in savings accounts** (₹5 Lakh without PAN) and **₹50 Lakh or more in current accounts** via the Annual Statement of Financial Transactions (SFT).
- **Prohibited Behavior**: The copilot will **never** display a countdown timer, a *"remaining deposit capacity"*, or advice on how to spread cash across multiple bank branches to avoid SFT triggers.
- **Mandatory Neutral Fact Output**:
  > *"Cash deposited this financial year: ₹[X]. Banks report yearly cash deposits of ₹10 lakh or more in savings accounts (₹5 lakh without PAN) and ₹50 lakh or more in current accounts to the tax department. Keep records of where deposited cash came from. Your CA can advise."*
- **Deposit Records Checklist**: Provides a factual list of supporting records to preserve (bank withdrawal slips, daily cash memos, day-close counts) and explicitly refers the owner to their Chartered Accountant.

---

## 3. Consequences

### Positive Consequences
- **Total Protection Against Criminal Liability**: Software architects, developers, and business owners are protected from prosecution under BNS §241 and CGST Act §132. The system maintains an unblemished legal posture.
- **Chartered Accountant Endorsement**: Practicing CAs can confidently recommend the copilot to SME clients because the software actively prevents client infractions, promotes account-payee digital rails, and defers complex tax judgments to professional advisors.
- **Zero Risk of Regulatory De-Platforming**: Eliminates the risk of App Store or Google Play Store expulsion or government ban under intermediary liability rules.

### Negative Consequences and Mitigations
- **User Frustration Over Blocked Transactions**: A merchant attempting to record a ₹2,50,000 cash receipt is blocked with a warning rather than allowed to enter the transaction silently.  
  *Mitigation*: The engine provides clear, actionable lawful remedies (e.g., accepting ₹50,000 in cash and ₹2,00,000 via UPI) and explains the statutory penalty that would otherwise be levied by the tax department.

---

## 4. Considered Alternatives and Rejection Rationale

1. **Implementing a "Stealth Mode" or "Panic Wipe" Gesture**:
   - *Rejected*: Flagrant violation of Section 241 of the Bharatiya Nyaya Sanhita, 2023. Knowingly designing software that destroys evidence of financial transactions is an abetment of criminal evidentiary destruction.
2. **Automated Cash Splitting / Invoice Smurfing Engine**:
   - *Rejected*: Structuring transactions to circumvent statutory ceilings is illegal under the Income-tax Act, 2025 and Prevention of Money Laundering Act (PMLA), 2002.
3. **Omitting Cash Ceilings Entirely**:
   - *Rejected*: Leaves the SME owner completely unaware of statutory limits, leading to massive penalties under Section 271D, 271DA, and 271E (now codified under the 2025 Act) during tax assessments.

---

## 5. Compliance & Verification Method

### 5.1 Verification Commands
Run unit tests verifying that guardrails enforce statutory ceilings and display neutral notices:
```bash
cd /Users/ishaanwadhwa/Projects/ps11-copilot
.venv/bin/pytest tests/test_vault.py -k "guardrails or compliance or sft" -v
```

### 5.2 Architectural Invariants Tested
- **Test Case `test_check_single_receipt_cash`**: Verifies that ₹1,99,999 is `SAFE` while ₹2,00,000 is `BLOCKED` with citation to IT Act 2025 Section 186.
- **Test Case `test_check_cash_expense_transport_distinction`**: Verifies that standard expense $> ₹10,000$ triggers `WARNING`, while transport expenses up to ₹35,000 remain `SAFE`.
- **Test Case `test_sft_rule_237_neutrality`**: Asserts that `cash_deposit_reporting_facts` contains no countdowns or evasion advice, and includes the mandatory disclaimer *"Your CA can advise."*
- **Test Case `test_partial_view_notice`**: Asserts that `PARTIAL_VIEW_NOTICE` matches the verbatim text: `"Formal books only. The owner's cash memo is not included in this view."`
