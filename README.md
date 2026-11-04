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

The data pack is read from `~/Projects/ps11-research/PS-11 SME Cash-Flow Copilot/Data`; set `COPILOT_DATA` to point elsewhere. The pack is **not** in this repo and must never be committed (`.gitignore` blocks spreadsheets).

## Scores on the data pack (4 Nov 2026)

**Reconciliation** against `reconciliation_truth`: 11,224 bank lines, receipts and payments. A line is right only when our document set equals the key's.

| Business | AUTO precision | Straight-through (no human) | If the accountant accepts our suggestions |
|---|---|---|---|
| Distributor | 98.7% | 35.8% | 62.8% |
| Clinic | 100.0% | 94.7% | 96.8% |
| Agency | 98.8% | 55.7% | 74.6% |
| **All** | **99.74%** | **72.7%** | **84.2%** |

- **Zero false matches** on lines outside the key.
- **AUTO precision is the trust number:** the problem owner ranked a wrong match as the worst mistake (D49). The matcher is tuned for precision first.

**Categorisation** against `true_category`, trained on lines before 1 Jul 2026 only:

| Set | By line | By rupee |
|---|---|---|
| Holdout Jul–Sep 2026 | 99.6% | 98.8% |
| All lines | 99.8% | 98.7% |

The baseline was 96.6% by line and 89.4% by rupee; the target is 97% on both.

**Gold answers:**
- T1, "Who owes me the most?": exact for all three businesses.
- T7, "Can I pay salaries on 1 Oct 2026?": exact for all three (salaries, closing balance, headroom).
- All 14 boundary questions are routed to a refusal-with-facts.

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
