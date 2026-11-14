# ADR 0004: Split-Plane Data Isolation and View Synthesis

## Status
accepted

## Context
Indian SME cash-flow management suffers from a structural dichotomy. Blending formal tax-cleared transactions and informal counter cash movements into a single unified general ledger violates statutory corporate accounting standards (proviso to Rule 3(1) of the Companies (Accounts) Rules, 2014 and MCA Rule 11(g) audit trail requirements), and exposes the business to massive tax penalties upon inspection. Conversely, maintaining completely isolated systems creates severe "morning cash blindness".

In high-velocity wholesale distribution (e.g. FMCG or pharmaceutical stockists), a business owner's bank account may show an alarming overdraft balance (e.g. -₹5,30,000 against a ₹25,00,000 Cash Credit limit), prompting acute panic over imminent insolvency ("false insolvency"). Under this distorted signal, the owner delays supplier orders, slows down inventory replenishment, or holds delivery vehicles. In physical reality, the business holds ₹6,40,000 in cash inside the godown counter drawer, ₹3,20,000 in delivery route collection slips in transit, and ₹10,12,000 in collectible customer khata balances, yielding an actual robust spendable liquidity buffer.

## Decision
We establish a unidirectional **Split-Plane Data Isolation and View Synthesis** architecture.

1. **Strict Data Segregation at Rest**:
   - The Public Plane (audited GST books, MCA tamper-proof edit logs, formal bank feeds) and the Sovereign Vault Plane (counter cash till, salesman parchi collection slips, informal customer khata) reside in strictly separate storage domains.
   - There is zero bidirectional synchronization between the two planes at rest.

2. **Downstream Unidirectional Integration**:
   - Formal commitments (statutory tax liabilities, supplier payment dues, employee payroll obligations, and bank EMI/interest schedules) flow downward into a volatile, memory-resident **Total Solvency Engine**.
   - Sovereign vault records never propagate upward into the formal accounting ledger.

3. **RAM-Only Solvency Synthesis ("Aaj Ka Hisaab")**:
   - The owner's operational liquidity cockpit is synthesized strictly on-demand in volatile local RAM.
   - The engine computes the comprehensive 5-part cash runway equation:
     $$\text{True Cash Runway} = (\text{Bank Cleared Balance} - \text{CC Drawn}) + \text{Galla Drawer Cash} + (\text{Inflows}_{\text{Pakka}} + \alpha \cdot \text{Inflows}_{\text{Kaccha}}) - \text{30-Day Commitments}$$
   - Here, $\alpha \in [0.5, 1.0]$ represents the owner-calibrated collection haircut applied to informal trade receivables to account for historical recovery delays and bad debt risks.

4. **Zero Cross-Plane Persistence**:
   - Synthesized cockpit metrics, physical drawer counts, and informal khata balances are never written back, cached, or persisted into the Public Plane database.
   - The presentation layer cleanly separates the unified owner cockpit from lawful, exportable formal tax books.

## Considered Options
- **Unified General Ledger with Shadow/Informal Flags**: Rejected. Maintaining informal transactions with shadow flags in the same database violates MCA Rule 11(g) audit trail requirements. Any forensic review or tax inspection of general ledger exports would immediately reveal shadow markers.
- **Completely Disconnected Offline Records**: Rejected. Perpetuates morning cash blindness, fosters false insolvency panic, and fails to provide early warning before bank Cash Credit limits or payroll obligations are breached.
- **Unidirectional RAM-Only View Synthesis**: Accepted. Delivers accurate, unified morning liquidity intelligence directly to the business owner while guaranteeing that formal tax books remain 100% audit-compliant and completely segregated.

## Consequences
- **Positive**: Eliminates false insolvency panic; provides true operational cash runway in under 10 seconds every morning; guarantees that formal accounting books remain pristine and inspection-ready.
- **Negative / Trade-off**: The business owner must maintain disciplined daily counter drawer balancing and salesman route slip handovers for the synthesized cockpit to reflect true cash; synthesized metrics are ephemeral in volatile memory and recomputed dynamically on launch.
