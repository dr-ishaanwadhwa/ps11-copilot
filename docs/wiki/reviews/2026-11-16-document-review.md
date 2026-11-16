# Review: documents from the 15 Nov multi-agent run

> **Date:** 16 November 2026
> **Scope:** documents written by the interrupted 15 Nov run, checked against the code and the data pack in this repo
> **Method:** every product or performance claim that can be checked was measured (`.venv/bin/python`) or traced to a file. Market sizes, prices and legal statements were not validated; they are listed as unsourced where no source is given.

## Verdict

| Document | Usable as it stands? | Main problem |
|---|---|---|
| `docs/strategy/PITCH_DECK_PLAN.md` | **No.** Do not show outside the team. | Headline accuracy and security claims are false. One case study does not exist in the data. |
| `docs/strategy/PRODUCT_STRATEGY_AUDIT.md` | **No**, for the same reasons | Same claims as the pitch plan; wrong owner and staff facts |
| `docs/audits/STATUTORY_INVARIANTS_ATTESTATION.md` | **No.** It must not be shown to a CA or partner. | It "certifies" mechanisms that do not exist (hash chain, client-side vault, 60fps 3D) |
| `docs/strategy/GTM_PLAYBOOK.md` (written 15 Nov, sourced) | Yes, as an internal draft | Every number is cited to the two documents above, so it inherits their errors; see its section 5 contradictions list |
| `docs/blueprints/...` and `docs/specs/*` | Yes, as a design target | Read as plans, not as a description of what is built |
| `docs/TEAM_ONBOARDING_GUIDE.md` | Mostly | Stale test count; no mention of the API or the web app; `.env` is not auto-loaded |

## 1. Measured numbers that contradict the documents

| Claim | Where | Measured | How |
|---|---|---|---|
| Forecast error 5.61% MAPE vs 18.20% naive | PITCH slide 5, l.241, 254, 271 | **13.5%** vs 18.2% naive (holdout); 15.8% pooled over 10 rolling backtests | `evaluate_holdout(load_pack())`, `evaluate_backtests` |
| 93.3% of actuals inside the P10–P90 band | PITCH l.241, 255 | **22.2%**. The bands are much too narrow (a calibrated band holds about 80%). | same |
| "0 false matches in production, 100% precision" | PITCH l.240, 250, 411 | 100% AUTO precision is real, but it is measured on the **synthetic** truth sheet, not production. It holds because AUTO is an allow-list of 3 rule classes. | `score_matches` |
| AUTO 1,170 / SUGGEST 1,744 / ASK 619 "across 11,224 transactions" | AUDIT l.127, PITCH l.269 | Those tier counts are **SME-1 only** (3,556 lines). All three businesses together: AUTO 7,630, SUGGEST 2,565, ASK 664, UNMATCHED 356. | `match_all` |
| "1,744 confirmed via 1-click triage" | PITCH l.269 | SUGGEST suggestions are right **72.5%** of the time for SME-1 and 69% overall | `score_matches` |
| "619 unannotated payments resolved" | PITCH l.269 | ASK lines are **not** resolved; the engine asks the owner | engine tiers |
| Wilson 95% gate, "n ≥ 381" | AUDIT l.124, PITCH l.225 | No Wilson computation exists; the gate is a fixed list in `match/engine.py:34-41` | grep |
| Matoshree Supermarket, INV-2023-882, 930 days old | AUDIT l.387-400, PITCH slides 1-2 | **Does not exist.** Invoices start Feb 2025; the oldest open invoice is 302 days old. | data pack |
| Owner "Prakash Gupta", 11 staff | AUDIT l.274 | Prakash **Kale**, **16** staff | `businesses` sheet |
| "13,359 real-world commercial transactions", "pilot testing", "traction" | PITCH l.262, AUDIT l.127 | The data pack is **synthetic** (its own README says so). No pilots or customers exist. | data README |
| 276 / 291 / 337 tests passing | PITCH l.256, ATTESTATION §4, onboarding §3 | 460+ tests at this review; 337 was a point-in-time count | `pytest` |

Counting note: the Data quality page and `score.summary` report "auto" as AUTO plus NO_DOC lines, i.e. 7,639 (SME-1 1,175; SME-2 6,462; SME-3 2). Pure AUTO matches number 7,630; the 9 NO_DOC lines are posted automatically with no document to match. Both figures are correct. Label whichever one you quote.

Confirmed and safe to use: 13,359 bank lines (12 duplicates removed), 6,438 sales invoices, 18 months (1 Apr 2025 to 30 Sep 2026), 3 businesses, SME-1 low of −₹23,29,533 on 1 Oct 2025 against a ₹25L limit, receivables ₹90,47,390 on 346 invoices, 89 admin hours a month for SME-1, ₹1L AUTO cap, 2% weekly audit sample, Tally XML GUIDs, 5-sheet CA pack.

## 2. Security and privacy claims vs what is built

| Claim | Reality |
|---|---|
| "On-device", "air-gapped", "never leaves the device", "zero-knowledge" | The deployed product is a **hosted Streamlit server**. The vault file is on the server (`.copilot_state/sovereign_vault.db`) and the server holds the key while it is unlocked. |
| "SQLCipher 4", "hardware-backed", "StrongBox", "WebAuthn PRF" | None of these exist. The vault is sqlite serialised and encrypted with AES-256-GCM, with the key derived by PBKDF2-SHA256 (100k iterations) in Python `cryptography`. "WebAuthn" is only a label on the web lock page. |
| 4-digit PIN as the only secret | The default is `0000` (`COPILOT_OWNER_PIN`). PBKDF2 does not protect a 10,000-value PIN space. |
| "Zero cloud" | OCR and voice transcription go to Gemini; the router can call Mistral or OpenRouter (`gemini.py`, `ai_client.py`) |
| Web lock page "biometric passkey" | It unlocks with a hard-coded `1234` (`apps/web/src/app/(auth)/lock/page.tsx:46`). Note that the web demo PIN (1234) differs from the server owner PIN (0000). |
| Internal 6-sheet export is PIN-gated (ATTESTATION §2.4) | **Was not.** The request flag defaulted to `true` and was only the client's own claim. **Fixed 16 Nov:** the server now checks the owner PIN (`ownerPin`, constant-time compare); the flag alone gets 403. Tests updated in `test_api.py`, `test_adversarial_m4_statutory_invariants.py` and `test_challenger_m4_empirical.py`. |

## 3. Attestation-specific findings

- **"SHA-256 audit hash chain with prev_hash" (§2.4):** there is no chain. `POST /review/reconcile` hashes one decision, **returns the hash to the browser and stores it nowhere** (`api/routers/review.py:97-117`).
- **"Unalterable, tamper-evident audit log" (MCA Rule 11(g)):** the ledger is a JSON file rewritten in place (`match/audit.py`). Anyone with disk access can edit it without a trace.
- **Review decisions are filed under the wrong business:** `reconcile` always records `("SME-1", "MANUAL_RECONCILE")` (`review.py:104`).
- **Code path cited for the vault, `apps/web/lib/crypto/vault.ts`:** it does not exist. The real file is `apps/web/src/lib/crypto.ts`.
- **"60fps, < 32 draw calls" 3D topography (§5.3):** until 16 Nov the 3D view **crashed on load in every browser**, because `@react-three/fiber` 8 does not run on React 19. The 15 Nov "build passes" check never opened a page. It was fixed by upgrading to fiber 9 and drei 10. No frame-rate measurement exists.
- **Section 18 tripwire (§2.3):** the 900-day rule is implemented, but with this data it **never fires**: the oldest open invoice is about 300 days old. The tests prove it only by moving the as-of date to 2030.
- **Legal-effect sentences:** "constitutes an Acknowledgment of Debt … resetting the clock", "court-admissible", "Solemn Declaration", "CERTIFIED". An AI-written engineering document cannot certify legal compliance. These need a CA or lawyer, or should be rewritten as "the code does X; test Y checks it".
- **Two ADR sets disagree on what ADR-004 is:** `docs/adr/0004-*` is split-plane isolation; `docs/adr/ADR-004-*` is statutory compliance and anti-tampering. Pick one numbering.

## 4. Specs and blueprint

The specs describe a target, and much of it is now built: route groups, the 7 views wired to the API with a sample-data fallback, the topography stack, the camera rig, the audio player, loading and error boundaries, and the formatters. Gaps and mismatches:

- **No server actions.** Except for `reviewActions`, data flows through a same-origin proxy (`apps/web/src/app/api/v1/[...path]/route.ts`), not React Server Components.
- **`/api/copilot/transcribe` does not exist** (blueprint 2.1); voice exists only in Streamlit.
- **The `@modal/parchi` intercepting route, `components/ui/*` primitives and the multi-file stores** of blueprint 2.1 do not exist; one `store.ts` is used.
- **The API address variable** is `PYTHON_BRIDGE_URL` in spec 01 and `COPILOT_API_BASE` in code. The proxy now accepts both.
- **Spec 05 uses `/api/v1/export/...` (singular).** The API serves both singular and plural paths.
- **Emoji in mockups.** 45 lines in the blueprint and 25 in spec 02 still contain emoji, against the 15 Nov decision.
- **Migration roadmap (blueprint section 8)** says Streamlit is decommissioned in weeks 7-8. Today the web app is not in the Dockerfile or compose file, and **`apps/web` is untracked in git**.

## 5. Onboarding guide

- **Stale test count.** "276 passed" is out of date (460+).
- **`.env` is not loaded by anything.** No `load_dotenv` exists, so the variables must be exported in the shell.
- **No instructions for the API or the web app.** To run them:
  `.venv/bin/python -m uvicorn copilot.api.app:app --port 8000`, then in `apps/web`: `npx next dev`. Set `COPILOT_API_BASE` if the API is not on `127.0.0.1:8000`.
- **It quotes the honest forecast numbers** (13.48% vs 18.19%), which contradict the pitch plan. Keep the onboarding numbers.

## 6. Recommended next steps

1. Correct the pitch plan and strategy audit using section 1. Before any external use, remove the Matoshree case and the "on-device / SQLCipher / hardware / zero-knowledge / court-admissible" language.
2. Withdraw the attestation, or rewrite it as an engineering test report without certification language.
3. Engineering:
   - persist and chain the audit hashes, and make the ledger append-only;
   - fix the `SME-1` hard-code in `reconcile`;
   - calibrate the forecast bands (22% coverage);
   - decide whether the vault should really run in the browser (the claim) or on the server (the build), and make the documents match.
4. Commit `apps/web` and add it to the deployment, or label it a prototype in every document.
