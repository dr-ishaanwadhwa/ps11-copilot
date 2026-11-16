# SME Cash-Flow Copilot: Go-to-Market Playbook

Milestone 5 synthesis, 15 November 2026. Every number carries a bracketed source. "Proposal:" marks a suggestion that no source makes. "not established in existing documents" marks a figure or claim that no source supports.

**Source key.** [AUDIT] PRODUCT_STRATEGY_AUDIT.md. [PITCH] PITCH_DECK_PLAN.md. [PRECODE] STRATEGY_PRECODE_CIRCLES.md. [COMPETE] COMPETITIVE_MATRIX_WEDGES.md. [ADR-1] docs/adr/0001 (sovereign vault). [ADR-2] docs/adr/0002 (Decision 60). [ADR-3] docs/adr/0003 (Section 18 and statutory shield). [ADR-4] docs/adr/0004 (split-plane isolation). [FEEDBACK] docs/wiki/feedback-2026-11-15-demo.md. [GLOSSARY] GLOSSARY.md. Section numbers follow each source's headings.

---

## 1. Summary

We sell first to owner-run FMCG wholesale distributors in trading hubs, at the Growth tier of ₹14,999 a year [AUDIT 3.3, 4.3]. The main channel is visiting Chartered Accountants (CAs), who receive the formal reconciliation tool free [AUDIT 4.2]. Distributors switch because bank-only software shows False Insolvency. The Kaveri Distributors case had ₹1,70,467 of Bank Headroom and ₹6,40,000 of counted Galla Cash at the same time [PRECODE 2.1; PITCH slide 1]. The copilot computes True Solvency across both planes, and no competitor in the matrix does so [COMPETE 5]. The sources do not settle the order in which clinics and agencies follow (section 10).

---

## 2. Beachhead and ICP

The beachhead is FMCG wholesale distributors, about 450,000 units in the serviceable obtainable market [AUDIT 3.3]. Clinics (about 550,000) and agencies (about 350,000) are the other two segments [AUDIT 3.3].

| Archetype | Buyer and scale | Trigger moment | Pain, as stated in sources | Answering capability |
|---|---|---|---|---|
| FMCG wholesale distributor (Kaveri, Pune) | Proprietor; ₹18 Cr turnover; 110 kirana accounts; ₹25L Sanctioned Credit Limit [PRECODE 2.2] | Morning check of Bank Headroom before an RTGS or cheque clears; headroom below the ₹2.5L floor [PRECODE 2.2, 2.5] | "Will my cheques bounce today? How close am I to the ₹25L CC limit?" [PRECODE 3.2] | Net usable headroom; Daily Galla Balancing; Decision 60 AUTO matching; Section 18 alert [PRECODE 3.4; ADR-2; ADR-3] |
| Dental and diagnostic clinic (Bengaluru) | Partner or proprietor; ₹15.2L monthly inflows [PRECODE 1.2] | 96.8% of receipts arrive as daily batches that match no single patient invoice [PRECODE 1.2] | Insurer disallowances of 8.8% to 9.4% of billing [PRECODE 1.2]; "delayed TPA insurance claims" [AUDIT 3.3] | Batch unbundling under the DAILY_UPI and MDR_NET rules [ADR-2]; Starter tier [AUDIT 4.3] |
| Creative agency (Delhi) | LLP partner; ₹26.5L monthly inflows [PRECODE 1.2] | Salary-day dip on the 1st to 5th, in 13 of 18 months [PRECODE 1.2] | 82.9% of receipts arrive short because of Section 194J/194C TDS [PRECODE 1.2] | TDS reconciliation; 90-day forecast; Starter tier [AUDIT 4.3]. EXACT_BILL is SUGGEST-only (upper bound 1.95%), so most agency matches need one click [COMPETE 6.2] |

Direct quotes exist only for the distributor persona. Buyer interviews for the other two segments are not established in existing documents.

---

## 3. Positioning and wedge

Positioning line: "It explains every rupee between your bank and your books, and never acts without you" (Decision 10) [AUDIT 1].

| Competitor | Where it wins | Where the copilot differs | Source |
|---|---|---|---|
| TallyPrime 7.1 | CA standard; about 28,000 partners; 2.7M licensed businesses [COMPETE 2.1] | Single formal ledger; no cash plane; bill allocation is manual [COMPETE 2.1] | COMPETE 2.1 |
| RazorpayX | Corporate payouts; partner-bank data [COMPETE 2.2] | Autonomous payouts break the approval model; partner banks only [COMPETE 2.2, 5] | COMPETE 2.2 |
| Credflow | Tally sync and WhatsApp reminders [COMPETE 2.3] | Mirrors Tally only; uploads customer lists to cloud BSPs [COMPETE 2.3] | COMPETE 2.3 |
| Khatabook | Micro-retail simplicity; over 50M downloads [COMPETE 2.4] | No bank statement intelligence; no CC modelling [COMPETE 2.4] | COMPETE 2.4 |
| Bank apps and neo-banks | Acquiring rails; loans [COMPETE 4.1, 4.2] | Single-bank silos; promote credit lines when owners are squeezed [COMPETE 4.1] | COMPETE 4.1 |
| Visiting CA | Statutory compliance [COMPETE 3.4] | Retrospective; blind to daily CC headroom [COMPETE 3.4] | COMPETE 3.4 |

---

## 4. Channels, in priority order

**1. Visiting CA partner portal (primary).** Fit: CAs already see the formal books and hold 40 to 80 SME clients each [AUDIT 3.4; PITCH slide 8]. The tool saves 26.9 hours a month of bank reconciliation per client [PRECODE 1.2]. What must be true: (a) CAs accept the 5-sheet Excel and Tally XML exports, since CA resistance is a named churn risk [AUDIT 5.2]; (b) CA exports omit Galla and Collection Slip cash [AUDIT 4.2]; (c) CAs refer clients without payment. The referral rate is not established in existing documents. "ICAI tie-ups" [PITCH slide 8] are not backed by any signed agreement in the sources.

**2. Wholesale trade associations and mandi clusters (beachhead).** Fit: dense mandis spread adoption by word of mouth [PITCH slide 8]. Named clusters: Pune Market Yard, Delhi Sadar Bazar, Mumbai APMC Vashi [PITCH slide 8]. What must be true: a first design partner in each cluster produces results the others can check, and one association endorses the tool. Association agreements are not established in existing documents.

**3. Bank working-capital alliances (last).** Fit: banks could accept BSA-certified extracts for CC renewals [PITCH slide 8]. What must be true: banks accept those extracts. The "45 days to 48 hours" renewal claim is not established in existing documents. Do not start this channel before Phase 3.

Proposal: no WhatsApp referral channel. The wa.me links are for debtor chasing [ADR-3], and reusing them would need a DPDP review.

---

## 5. Pricing and packaging

| Tier | Monthly | Annual, paid upfront | Target | Main entitlements [AUDIT 4.1] |
|---|---|---|---|---|
| Starter | ₹750 | ₹7,999 | Retail and clinics | One entity; 1,500 bank transactions a month; 90-day cash dip view; wa.me links; Tally XML and 5-sheet export |
| Growth (flagship) | ₹1,499 | ₹14,999 | Wholesale distributors | 5,000 transactions a month; route slip OCR; multi-bank and CC; BSA evidence vault; Daily Recovery Sheet |
| Enterprise | ₹2,999 | ₹29,999 | Multi-branch | Unlimited transactions; multi-godown; 5 seats; CA onboarding specialist; custom ERP XML |
| CA partner | Free | Free | Visiting CAs | Lifetime free portal access [AUDIT 4.2] |

- The annual price is ₹1,000 below twelve monthly payments on Starter (₹9,000) [computed from AUDIT 4.1].
- **Source conflict.** [COMPETE 5, row 7] gives the copilot "Rs. 750 to 1,500 per month" and lists no Enterprise tier. [AUDIT 4.1] lists ₹2,999 for Enterprise. Both cannot be current.
- The blended ARPU of ₹14,000 a year [AUDIT 3.4] is not derived from the tier mix in the sources.
- **ROI claims.** [AUDIT 4.3] says the distributor ROI is above 40x, the clinic above 25x and the agency above 30x. The components the audit lists give 7.6x for one Section 18 recovery of ₹1,14,000 against ₹14,999 [AUDIT 5.4], and about 3.0x for ₹45,000 of avoided penal interest. The 40x, 25x and 30x multiples are not established in existing documents. Do not use them in sales material.
- Discounts, trial length and payment terms are not established in existing documents.

---

## 6. Launch sequence

**Phase 1: first 10 design partners.**
- Entry: the production app is live at sme-cashflow.medevolv.in [FEEDBACK 1]. ACT-01 is marked DONE and the ACT-02 forecast card must be closed [FEEDBACK 3]. Proposal: ACT-05 (vault unlock) is also an entry gate, because the CA channel depends on it.
- Mix: Proposal: 4 distributors, 3 clinics, 3 agencies, distributors first, per the beachhead [AUDIT 3.3].
- Exit: all 10 partners have one full month of imported statements (Proposal: duration). The daily review is timed under 10 minutes [PRECODE 4.5]. Zero unexpected CC or OD limit breaches [PRECODE 2.5]. The 2% weekly audit sample has no CA rejection, and any rejection suspends that rule class [ADR-2].

**Phase 2: first 100 paying.**
- Entry: Phase 1 exit met. Three tiers are priced [AUDIT 4.1]. The CA portal is live with free access [AUDIT 4.2].
- Exit: 100 paid subscriptions (Proposal: the number). At least one CA firm has onboarded 10 or more clients (Proposal). The sources' Year 1 target is 12,000 subscribers [PITCH slide 7]. No path from 100 to 12,000 is written down.

**Phase 3: repeatable motion.**
- Entry: Phase 2 exit met. CAC is measured on a live cohort. The ₹2,600 blended CAC is stated in [PITCH slide 7]; whether it was measured is not established in existing documents.
- Exit: 12,000, 48,000 and 150,000 paying subscribers at Months 12, 24 and 36, with 300, 1,100 and 3,000 CA partners [PITCH slide 7; AUDIT 3.4]. At these numbers, the implied clients per CA are 40 in Year 1 and 43.6 in Year 2 (computed), not the 50 average used for the Year 3 target [AUDIT 3.4].

---

## 7. Metrics per phase

| Phase | Metric | Value or target | Source |
|---|---|---|---|
| 1 | Unexpected CC/OD breaches | 0 | PRECODE 2.5 |
| 1 | Daily review time | Under 10 minutes | PRECODE 4.5 |
| 1 | AUTO false matches | 0 in the 2% audit sample | ADR-2 |
| 1 | Upload success on first try | Proposal: set after the first 10 partners' file formats are known | Proposal |
| 1 | User can say what the 90-day forecast means | Proposal: one-sentence test with each partner | Proposal |
| 2 | Paying subscribers | 100 | Proposal |
| 2 | Blended ARPU | ₹14,000 a year | AUDIT 3.4 |
| 2 | Logo retention | "over 92%" stated; measurement method not established in existing documents | AUDIT 5.1; PITCH slide 7 |
| 3 | CA partner firms | 300, 1,100, 3,000 | PITCH slide 7 |
| 3 | Blended CAC | ₹2,600 stated; measurement not established in existing documents | PITCH slide 7 |
| 3 | LTV/CAC | 8.38x stated; inputs conflict (section 10) | PITCH slide 7 |
| 3 | Net revenue retention | 122% stated; basis not established in existing documents | PITCH slide 7 |
| 3 | Gross margin | 86.4% in Year 3 stated; cost build not established in existing documents | PITCH slide 7 |

---

## 8. Regulatory and trust claims

**We may say** (design facts, stated in the ADRs and product docs):
- Vault data is encrypted at rest with SQLCipher AES-256, with the key tied to a local PIN and hardware keystore [ADR-1]. Say this only after the shipped build is verified (section 10).
- The copilot does not move money or send messages without the owner acting. wa.me links are built client-side and sent by the owner [PRECODE 2.6; AUDIT 1].
- A bank line posts as AUTO only if its rule class has zero errors in history, a 95% Wilson upper bound at or below 1%, at least 381 error-free matches, a unique document set, an amount under ₹1,00,000, and a verified counterparty. Two per cent of AUTO items are audited each week, and one failure suspends the class [ADR-2].
- The formal-books view shows only the formal plane, with the banner "Formal books only. The owner's cash memo is not included in this view." [ADR-3; PRECODE 2.4]
- Figures are computed in code, not by an LLM [PRECODE 2.6].
- The copilot refuses panic-wipe, concealment and evasion requests [ADR-3].
- Losing the device PIN means losing the vault unless an offline backup exists [ADR-1]. State this trade-off in onboarding.

**We may not say:**
- "100% precision." The source figure is zero false matches in 11,224 lines [ADR-2]. The upper bounds on the qualified classes are 0.06% to 0.81% [COMPETE 6.2]. Use "0 false matches observed; 95% upper bound X% per class."
- "100% DPDP compliant," "immune to Section 247," or "immune to cloud subpoena" [AUDIT 2.1, 2.5]. These are legal conclusions, and no counsel opinion is in the repo. Proposal: obtain legal review before any of these appear in material.
- "Court-admissible" or "restarts the limitation clock" as a guarantee. [ADR-3] says the copilot generates a Section 63(4) certificate. [PRECODE 6] relies on Delhi and Karnataka High Court views that it names but does not cite. Legal effect needs counsel. Use "Section 63(4) certificate," not "Form 63" [AUDIT 2.3; PITCH slide 8], since the ADRs and PRECODE use the section number.
- "Zero data leaves the device." This conflicts with the Claude API calls on PII-masked text [PRECODE 2.6], with the hosted production URL [FEEDBACK 1], and with the planned Google sign-in [FEEDBACK 2.4].
- "Zero hallucination" without qualification. Numbers are computed in code, but an LLM handles intent routing [PRECODE 2.6].
- "Compliant with MCA Rule 11(g)." The copilot generates Tally XML vouchers with deterministic GUIDs [AUDIT 2.4]. The edit log belongs to TallyPrime.
- Tax or legal advice. The fail-closed boundary router is meant to block it [PRECODE 3.4].

---

## 9. Product readiness gaps from the 15 November demo

- **Upload robustness (ACT-01, P0).** Tracker status is DONE, but the reported failure came from reading the README sheet, not from column names [FEEDBACK 2.1]. The fix shipped on 15 Nov as sheet selection in `src/copilot/ingest.py`; the regex header table was not needed and was not built [docs/wiki/subsystems/statement-ingestion-regex.md, section 0]. Gate: Phase 1 entry, tested on the Retail India file and on each partner's bank export.
- **Forecast clarity (ACT-02, P0).** The chart shows holdout history, not a forward forecast, and has no plain-language card [FEEDBACK 2.2]. Gate: Phase 1 entry.
- **Vault role clarity (ACT-05, P1).** The PIN has two entry points, and the role switcher adds confusion [FEEDBACK 2.3]. The sources disagree on whether an accountant mode exists. [FEEDBACK 2.3] describes one, and [PRECODE 2.4] says Accountant Presentation Mode was purged. [COMPETE 6.1] still describes it. Gate: Phase 1 entry, because the CA channel depends on it.
- **Visual polish (ACT-03, P1; ACT-04, P1).** Remove the emojis and fix the Setup Guide overlap and Cash Book overflow [FEEDBACK 2.5, 2.7]. Gate: Phase 1 exit, because design partners will judge the product on it.
- **Onboarding-first entry (ACT-07, P2).** The planned landing page adds an archetype selector and Google sign-in [FEEDBACK 2.4]. Proposal: gate for Phase 2, since self-serve sign-up needs it. Phase 1 partners can be onboarded by hand.
- **Free-text Ask Copilot (ACT-06, P2).** Users currently get preset chips only. Freeform input needs rate limits and boundary checks [FEEDBACK 2.6]. Proposal: gate for Phase 2, and send only PII-masked text to any external model [PRECODE 2.6].

---

## 10. Open questions for the team

1. Does the shipped production app keep vault data on the device or on the server? [ADR-1] says on-device; the hosted Streamlit app suggests server-side processing [FEEDBACK 1]. Every privacy claim depends on the answer.
2. Which Starter-to-Enterprise prices apply? [COMPETE 5] and [AUDIT 4.1] disagree (section 5).
3. What is the measured CAC? [PITCH slide 7] uses ₹2,600, while [AUDIT 6] and [PITCH slide 6] say "zero-CAC."
4. Do the LTV inputs reconcile? ₹21,800 LTV at ₹14,000 ARPU is about 1.6 years of revenue [PITCH slide 7], but the same slide cites a lifetime above 3.5 years.
5. How many AUTO posts were there? [AUDIT 2.2] and [PITCH slide 5] give 1,170, but the qualified classes alone sum to 7,633 sample lines [COMPETE 6.2; ADR-2], and ADR-2 cites about 68% autonomous. The 1,170 figure is the open conflict.
6. Which rate applies? Rokda APR for 2% over 30 days is 24.83% simple [AUDIT 5.3; PRECODE 2.1] but 27.86% compounded [COMPETE 1.2; PRECODE 7.3]. The 5%/15-day compounded figure is 227.18% in one table and 248.88% in the scenario text of the same section [PRECODE 7.3]. The CC cost is 11.75% [AUDIT 5.3; PRECODE 2.2], 12.00% [PRECODE 2.1], or 10.5% to 13.5% [COMPETE 1.2; PRECODE 7.3].
7. Is there counsel's view on Section 18 acknowledgments by WhatsApp, and on DPDP positioning?
8. Which ADR set governs? docs/adr contains two sets. ADR-004 is split-plane in one and statutory compliance in the other [ADR-4; AUDIT 2.4].
9. What are the sources for the $1.3 trillion economy figure [PITCH slide 1], the 45-day renewal figure [PITCH slide 8], and the SAM range of 14.5M to 18.0M [AUDIT 3.2]? None is derived in the documents.
