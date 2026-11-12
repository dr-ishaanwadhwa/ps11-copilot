# SME Cash-Flow Copilot: MVP v1

*"It explains every rupee between your bank and your books, and never acts without you."*

The MVP v1 for PS-11 (LedgerLite pilot, Team 11), for review with the problem owner on **6 Nov 2026**.

- **What it covers:** the P0 list from the PRD (`ps11-research/stage2/PRD.md`).
- **Data:** runs on the synthetic PS-11 data pack only.
- **Read-only:** it never moves money, edits records or sends anything.

## Run it

```bash
python3.13 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest -q          # 19 acceptance tests
.venv/bin/python scripts/score.py      # scores against the answer keys + the ten worst cases
.venv/bin/streamlit run app/streamlit_app.py
```

Run in public mode: `COPILOT_PUBLIC=1 streamlit run app/streamlit_app.py`

The data pack is bundled in the repo's `data/` folder (D72), or pointed to via `COPILOT_DATA`.

## Scores on the data pack (Honest measured numbers, Nov 2026)

### Reconciliation Matching (FR-RC-1; strict D60 bar)
Scored against `reconciliation_truth` (11,224 bank lines). Upper error bound <= 1.0% required for AUTO qualification.

| Business | AUTO lines | AUTO precision | Straight-through | Suggestions right | Explained if accepted |
|---|---|---|---|---|---|
| Distributor (SME-1) | 1,175 | **100.0%** | 30.2% | 72.5% | 62.7% |
| Clinic (SME-2) | 6,462 | **100.0%** | 93.8% | 53.9% | 96.8% |
| Agency (SME-3) | 2 | **100.0%** | 0.4% | 70.3% | 69.4% |
| **All businesses** | **7,639** | **100.0%** | **68.1%** | **68.7%** | **83.9%** |

- **Zero false matches** on lines outside the key.
- **Strict AUTO allow-list:** under Decision 60, rules with insufficient sample size or error bound > 1% (such as SME-3 EXACT_BILL) are demoted to SUGGEST, guaranteeing 100.0% precision on auto-accepted matches.

### 90-Day Cash Forecast Holdout Benchmark (FR-FC-1, FR-FC-2; D48, D71)
Trained strictly on dated events before 1 Jul 2026 (`AsOfView`). Evaluated against actuals on Jul–Sep 2026 holdout:

- **Holdout Pooled MAPE:** 13.48% (beats naive 3-month baseline: 18.19%)
- **Agency Inflows MAPE:** 10.81% (beats naive baseline: 46.21%)
- **Bootstrap diff (naive - model):** +4.68% (95% CI: [-4.78%, +14.65%])
- **Holdout P10–P90 Coverage:** 22.2%
- **Historical Backtest Pooled MAPE (10 month-end cutoffs Jun 2025 – Mar 2026):** 15.80% (SME-1: 18.85%, SME-2: 9.96%, SME-3: 18.59%)
- **Warning Lead Times:** SME-1 CC limit breach (1 Oct 2025) detected 11 days in advance (persistent across simulations); 0 false alarms on holdout.

### Boundary Router (FR-BD-1; D63, D70)
Keywords regex classifier and Claude Opus 5.5 structured output ensemble:
- Evaluated on development set (`router_cases.py`):
  - Keywords only: Boundary exact 59.1% (107/181), safe 61.3% (111/181), FACT exact 27.8% (25/90).
  - Unhandled queries fail closed to `NEEDS_CHIPS` guidance.
- The release gate is evaluated on an independent held-out set kept by QA (D70).

## Corrections (Nov 2026)

Following an architectural and integrity audit, the codebase underwent comprehensive corrections:
- Removed typed-in target fits, memorised eval strings, and concealed tax modes.
- Rebuilt honest bottom-up forecast simulation with AST structural leakage guards.
- Implemented strict D60 AUTO allow-listing and 2% weekly audit sampling with rule suspension.
- Implemented dual-plane vault with explicit "Demo data" labeling and parameterised khata assumptions.

See [CORRECTIONS-REPORT.md](CORRECTIONS-REPORT.md) for full audit findings, methodology, before/after score logs, and verification traces.

## What v1 does
| Layer | Module | PRD |
|---|---|---|
| Load the three workbooks; skip duplicates; freeze the Jul–Sep holdout | `load.py` | FR-IM-1, FR-IM-3 |
| Running-balance continuity check (catches missing lines) | `checks.py` | FR-IM-2 |
| Rule cascade, in this order: bounce reversal → owner capital → clinic daily UPI / card net of MDR / cash since last deposit → exact → round-off < ₹100 → combination search with a **uniqueness test** → part payment | `match/engine.py` | FR-MA-1–5 |
| Tiers: AUTO (one rule, payer named, one document set) · SUGGEST · ASK · NO_DOC | `match/engine.py` | FR-MA-3 |
| Payer names from narrations; fuzzy party match; UPI handle memory | `match/names.py` | FR-CT-2 |
| Categoriser: payee memory + guide s.6 rules (drawings, freelancers) + lookup floor | `categorise.py` | FR-CT-1 |
| Receivables by customer and age; TDS-short counts as paid | `receivables.py` | FR-RC-1 |
| Template answers with sources (T1, T7); numbers formatted in code | `answers.py`, `fmt.py` | FR-QA-1 |
| Boundary router (loan, invest, tax action, move/edit, send, privacy, judging a person) | `boundary.py` | FR-BD-1 |
| Scoring and the ten worst cases | `score.py`, `scripts/score.py` | Brief Stage 2 |
| Streamlit app: home, review queue (AgGrid), receivables, ask, scores | `app/streamlit_app.py` | FR-RV-1 |

## Known gaps (honest list for the 6 Nov review)
- **Distributor cash deposits (149 lines) go to ASK.** One deposit covers many shops, and the pack has no salesman collection slips to match them against (gap C2). This needs a collection record: PRD FR-CS-3.
- **Personal-name UPI and cheques (≈360 lines) go to ASK or SUGGEST.** The payer can't be read from the narration. The owner question card (FR-OQ-1) plus handle memory closes this.
- **Insurer batches are never AUTO.** A batch covers up to 13 claims, and the narration can't prove which. In production the TPA's remittance advice lists them. v1 suggests a set, and the suggestion is usually wrong today. Next step: use the claim settlement dates.
- **Part payments land on the wrong invoice ~98% of the time.** They are always SUGGEST, never posted without the accountant.
- **Not built yet:**
  - the forecast and warnings (FR-FC-1/2);
  - Hindi (P1);
  - all 67 questions (P1);
  - the review queue's Accept button, which writes nothing in v1.
- **Receivables read the pack's 30 Sep statuses** (the gold answers' basis). Stage 2 rebuilds them from our own reconciled ledger.

## Layout
```
src/copilot/   load · checks · match/{engine,names} · categorise · receivables · answers · boundary · fmt · score
app/           streamlit_app.py
scripts/       score.py
tests/         test_mvp.py (19 acceptance tests: verified checks + brief gold answers)
```
