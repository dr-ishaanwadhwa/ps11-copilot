# SME Cash-Flow Copilot

The shared domain language for Team 11's SME Cash-Flow Copilot across wholesale distribution, retail healthcare, and creative agency operations.

## Language

### Official White / Tax Ledger Plane

**Tax Invoice**:
A statutory billing document issued to a customer at or before the removal of taxable goods, registered on the GST portal.
_Avoid_: Bill, sales receipt, estimate, quotation

**Current Account**:
A formal commercial bank account used for business collections, payments, and statutory tax remittances.
_Avoid_: Bank balance, business account, checking account

**Bank Transaction**:
A single debit or credit entry cleared and recorded on an official bank statement.
_Avoid_: Bank line, ledger line, payment entry

**MCA Audit Trail**:
An unalterable, always-on edit log recording every voucher creation, modification, and deletion mandated for corporate entities.
_Avoid_: Change history, edit log, activity log

**e-Way Bill**:
A mandatory electronic document generated on the GST portal evidencing the physical transport of goods consignments exceeding statutory thresholds.
_Avoid_: Delivery challan, transport receipt, road permit

---

### Godown Drawer / Galla Cash Plane

**Galla Cash**:
The physical currency counted and held in the store counter or godown till drawer at any given moment.
_Avoid_: Black money, shadow cash, unaccounted cash, cash in hand

**Counter Cash Receipt**:
A direct, immediate payment in physical currency received at the store counter for non-tax cash retail supplies.
_Avoid_: Off-book sale, kacha bill, direct settlement

**Petty Cash Payout**:
A small physical currency disbursement from the drawer till for immediate transport freight, loading wages, or routine shop expenses.
_Avoid_: Cash leak, informal expense, unbilled payout

**Galla Drift**:
The mathematical discrepancy between physical currency counted in the drawer at day-close and the calculated expected cash.
_Avoid_: Missing cash, cash shortfall, drawer theft

**Daily Galla Balancing**:
The end-of-day reconciliation routine comparing opening drawer float, day's takings, petty payouts, and banked cash against the physical count.
_Avoid_: Cash closing, rokad tally, till count

---

### Salesman Collection Slips Plane

**Collection Slip**:
A serialized paper receipt or digital slip issued by a delivery salesman to a retail shopkeeper acknowledging cash or cheque collection on a delivery route.
_Avoid_: Parchi, receipt slip, memo

**Route Bag**:
The daily collection pouch containing all cash, post-dated cheques, and collection slips gathered by a field salesman across a delivery route.
_Avoid_: Cash bag, collection bundle, route tally

**In-Transit Cash**:
Physical currency collected from retail shops by a delivery salesman that has not yet been physically handed over to the godown cashier.
_Avoid_: Floating cash, salesman cash, pending cash

**Cheque Bounce**:
A deposited customer cheque returned unpaid by the clearing bank, reversing the ledger credit and reopening the original unpaid debt.
_Avoid_: Cheque return, dishonoured cheque, failed clearing

**Slip Handover**:
The physical verification and signing process where a field salesman surrenders route collections and signed slips to the store cashier.
_Avoid_: Evening settlement, route close, slip balancing

---

### Cash Credit (CC) / Overdraft Bank Plane

**Sanctioned Credit Limit**:
The maximum credit borrowing ceiling approved by a commercial bank under a formal credit agreement.
_Avoid_: Loan limit, overdraft line, bank ceiling

**Drawing Power**:
The dynamic borrowing limit permitted by the bank, calculated as eligible paid inventory and debtors aged strictly under 90 days minus bank margins.
_Avoid_: DP, available borrowing, credit capacity

**Bank Headroom**:
The net usable buffer remaining before an active Cash Credit balance touches the applicable drawing limit.
_Avoid_: Headroom, available limit, credit cushion

**Penal Interest**:
The punitive interest surcharge assessed by a bank on any borrowing that exceeds the sanctioned limit or drawing power.
_Avoid_: Penalty charges, overdraft fee, late interest

**Credit Limit Breach**:
An operational event where bank overdraft borrowing exceeds the applicable drawing power, triggering bank notices and punitive charges.
_Avoid_: Account default, loan blowout, limit crossing

---

### Trade Debt & Credit Terms Plane

**Trade Debtor**:
A recurring retail buyer or corporate customer who purchases goods or services on deferred commercial payment terms.
_Avoid_: Client, buyer, account, party

**Pending Khata**:
The cumulative informal trade credit extended to regular neighborhood customers tracked outside formal GST invoicing.
_Avoid_: Udhar, kacha khata, informal debt

**Days Outstanding**:
The total number of calendar days elapsed since an invoice was raised that it has stayed unpaid.
_Avoid_: Overdue days, age, invoice age

**Days Overdue**:
The number of calendar days past an invoice's formal contractual due date that it remains unpaid; zero until due date passes.
_Avoid_: Late days, days outstanding

**Rokda Discount**:
An immediate cash discount conceded by a supplier in exchange for upfront payment rather than trade credit.
_Avoid_: Cash discount, CD, prompt discount

**Implied APR**:
The annualized percentage cost of working capital forfeited by accepting supplier trade credit instead of taking an immediate cash discount.
_Avoid_: Discount rate, APR, borrowing spread

**Limitation Clock**:
The statutory three-year countdown under the Limitation Act during which a trade debt remains legally enforceable in Indian civil courts.
_Avoid_: Expiry time, debt deadline, recovery clock

**Section 18 Acknowledgment**:
A signed written or electronic statement from a debtor confirming their outstanding balance, which legally resets the three-year limitation clock back to zero.
_Avoid_: Debt confirmation, balance acceptance, WhatsApp proof

---

### True Solvency & View Synthesis

**True Solvency**:
The actual operational liquidity of an enterprise, combining formal bank liquidity with physical drawer cash and expected khata collections, minus 30-day obligations.
_Avoid_: Total cash, net worth, cash position

**False Insolvency**:
A misleading operational state where formal bank accounts indicate severe overdraft distress while the business possesses ample drawer cash and collectible debts.
_Avoid_: Paper broke, fake loss, bank crisis

**Collection Haircut**:
A user-calibrated discount percentage applied to informal receivables to reflect historical default and recovery timing risk.
_Avoid_: Risk factor, alpha, deduction rate

**30-Day Commitment**:
An unavoidable cash obligation maturing within 30 calendar days, comprising employee payroll, statutory tax liabilities, bank EMIs, and supplier dues.
_Avoid_: Expenses, outgoings, fixed costs
