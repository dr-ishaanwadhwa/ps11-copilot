# ADR 0002: Deterministic Decision 60 Precision Matching Engine

## Status
accepted

## Context
Automated bank statement reconciliation for Indian distribution, retail healthcare, and agency SMEs is complicated by non-standard commercial settlement flows. These include statutory Tax Deducted at Source (TDS) under Section 393 of the Income-tax Act, 2025 (10% pre-GST on professional services, 0.1% on high-volume goods supplies), payment gateway Merchant Discount Rate (MDR) deductions (0.4% UPI MDR, 1.0%–2.0% card processing fees), multi-invoice clubbed payments from single retailers, partial settlements, and round-off currency slack.

Deploying probabilistic Large Language Model (LLM) agents or opaque machine learning classifiers directly into the reconciliation loop introduces non-deterministic hallucinations, fluctuating allocations across identical runs, and unverifiable arithmetic. Field testing and direct accountant interrogation established the core trust hierarchy of Indian SME operators: "wrong match > category > forecast" (Grill Log Decision 49). A single false-positive automated reconciliation misallocates customer receivables, invalidates tax ledgers, and instantly destroys user confidence in the entire copilot.

## Decision
We enforce a rules-first, deterministic reconciliation engine operating within a strict 60-second execution window. The engine classifies each bank transaction into four explicit confidence tiers:
1. **AUTO**: Automated straight-through settlement requiring zero human intervention.
2. **SUGGEST**: One-click confirmation review for accountants (e.g. multi-invoice clubbed settlements, route deposit breakdowns).
3. **ASK**: Merchant clarification for ambiguous narrations or unrecognized counterparties.
4. **NO_DOC**: Owner capital infusions or proprietor cash withdrawals requiring no invoice association.

In accordance with **Decision 60**, a candidate match qualifies for the **AUTO** tier if and only if all four conditions are simultaneously satisfied:
1. **Empirical Rule Qualification**: The specific business domain $\times$ rule class achieved 0 errors in training history and maintains an upper bound on error rate $\le 1.0\%$ at a 95% binomial confidence level. Under this rule, distributor exact invoice matching (`EXACT`, n=1,173), clinic daily aggregate UPI (`DAILY_UPI`, n=5,991), and clinic net card MDR settlement (`MDR_NET`, n=469) qualify for AUTO; rules with higher statistical uncertainty (such as agency exact bill matching with 1.95% upper bound) are excluded.
2. **Document Set Uniqueness**: The subset-sum combinatorial solver returns exactly one unique invoice combination matching the net transaction amount within tolerance. If multiple valid invoice permutations exist, the match is relegated to SUGGEST.
3. **Verified Counterparty**: The payer identity is established via explicit statement narration regex or owner-confirmed historical memory (never inferred from prior automated guesses).
4. **Materiality Ceiling**: The total transaction amount is strictly below ₹1,00,000 (`_AUTO_MAX_AMOUNT = 100_000.0`). Transactions of ₹1 Lakh or greater are routed to SUGGEST regardless of rule match.

For continuous operational governance, a deterministic 2% weekly audit sample is extracted from AUTO reconciliations. Any single audit failure immediately and automatically suspends the offending rule class from the AUTO allow-list. Zero LLMs are utilized for numerical calculation, payment allocation, or match assignment.

## Considered Options
- **Probabilistic LLM Agent Matching**: Rejected. Incurs high latency and token cost, produces non-deterministic matching results, risks arithmetic hallucination on TDS and MDR splits, and cannot satisfy the immutable audit trail standards required by MCA Rule 11(g).
- **Supervised ML Classification (Random Forests / Gradient Boosted Trees)**: Rejected for autonomous matching. Cannot mathematically guarantee 100% precision on edge cases; retained strictly for heuristic ranking of matches within the SUGGEST review tier.
- **Decision 60 Deterministic Rule Engine with 4-Tier Gating**: Accepted. Achieves 100% precision on automated lines across 11,224 benchmark bank lines with complete mathematical explainability, zero hallucination, and instant rule revocation upon audit discrepancy.

## Consequences
- **Positive**: 100% precision on automated reconciliations; zero false-positive invoice closures; complete rupee-for-rupee auditability compliant with statutory accounting requirements.
- **Negative / Trade-off**: Straight-through automation rate is intentionally capped at empirical qualification limits (~68% autonomous vs ~85% under aggressive matching); clubbed or ambiguous payments require explicit one-click accountant verification.
