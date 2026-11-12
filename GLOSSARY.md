# Domain Glossary: SME Cash-Flow Copilot (ps11-copilot)

Shared domain vocabulary across modules, tests, and documentation.

---

### Core Domain Entities & Modules

- **Vault (`copilot.vault`)**: The local-first dual-plane cash operating ledger. Bridges formal bank accounts with physical cash drawers (Galla) and informal ledger balances (Rokad, Khata). Never transmits unvetted offline transactions to formal tax or accounting books.
- **True Solvency**: The SME's actual liquidity position considering formal bank liquidity (balance + Cash Credit headroom) plus physical counted cash, plus expected informal receivables discounted by a user-calibrated haircut ($\alpha$), minus 30-day fixed obligations (salaries, rent, debt servicing).
- **Galla**: The physical till or cash drawer at the store counter. Counted daily and balanced against recorded day-close receipts.
- **Khata**: Informal credit extended to recurring customers or retailers, tracked outside formal GST invoicing.
- **Rokad**: The informal daily cash book recording unbanked receipts and counter disbursements.
- **Day-Close Collections**: Field salesman collection slips documenting cash gathered from retailers, linked to bank deposits as `SUGGEST` matches under Decision 55.
- **IntentRouter (`copilot.boundary`)**: The safety gatekeeper module classifying SME owner inquiries into factual queries vs legal/statutory boundary areas (Rule 237, limitation notices, CA referrals) before answer generation.
- **CashForecastSimulator (`copilot.forecast`)**: Monte Carlo cash-flow simulation engine evaluating 90-day daily bank balance paths using empirical customer delay profiles, historical disallowance rates, and statutory tax deductions.
- **Copilot (`copilot.answers`)**: Unified SME owner Q&A intake interface synthesizing cited factual answers from enterprise ledger sources.
- **Matcher (`copilot.match`)**: Automated transaction reconciliation engine matching bank credits and debits to invoices, bills, and collection slips using Decision 60 qualified audit rules.

---

### Architectural Design Vocabulary

- **Module**: Anything with an interface and an implementation (scale-agnostic: function, class, package).
- **Interface**: Everything a caller must know to use the module correctly (types, invariants, ordering, errors).
- **Implementation**: Internal body of code hidden behind a module's seam.
- **Seam**: The location where a module's interface lives and where behavior can be substituted without editing callers.
- **Adapter**: A concrete implementation satisfying an interface at a seam (e.g. SQLite vs In-Memory).
- **Depth**: Leverage at the interface: a large amount of behavior hidden behind a concise, stable interface.
- **Locality**: Concentration of change, bugs, and invariants in one place rather than spreading across callers.
