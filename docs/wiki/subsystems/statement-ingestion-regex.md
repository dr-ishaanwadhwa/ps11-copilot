# Subsystem Specification: Fuzzy Regex Bank Statement Ingestion

> **Subsystem:** Statement Ingestion & Parser  
> **Date:** 15 November 2026  
> **Status:** FIXED 15 Nov 2026 — root cause corrected, see section 0; sections 1–2 are superseded  
> **Origin:** Team Demo Custom Upload Crash (`ijt-mtka-pgm`)  

---

## 0. Correction (15 Nov 2026, after reproduction)

The diagnosis in section 1 was written from the transcript and is wrong. Reproducing the upload with
`data/PS-11_bank_statements.xlsx` showed:

- **Actual cause:** `pd.read_excel` was called without `sheet_name`, so it read only the first sheet.
  That sheet is a one-column `README`; the transactions are on the `bank_transactions` sheet. This is
  what Dr. Ishaan guessed on the call ("Maybe it's referring to the first sheet").
- **Not the cause:** column naming. The parser already matched by substring, so `txn_date`,
  `Tax date` and `channel date` all matched. It also explains why the same data worked once Alok
  re-saved it as CSV.
- **"Running balances tie: False"** had two causes: the three businesses were checked as one running
  balance, and the dataset contains 12 deliberately duplicated SME-2 rows (31 Jan 2026, per its README).

What was changed in `src/copilot/ingest.py` (tests in `tests/test_ingest.py`):

1. Excel: every sheet is read; the first one with a date and a narration column is used. If none
   qualifies, the error lists the sheets checked.
2. The running-balance check is per `business_id` / account, on a stable date sort.
3. Short keys `dr` / `cr` must be a whole word. Before, `cr` matched inside `description`, so a file
   with a Description column ahead of Credit read the narration as the credit amount.

Result on the provided workbook: 13,371 rows read; exactly the 12 duplicated rows are flagged.

Not done: de-duplication on `txn_id`, header rows that are not the first row, and the interactive
column-mapper from section 2.1. The regex table in section 2 was not implemented and is not needed
for this file.

---

## 1. Problem Statement (superseded)

During the live test session, Alok Ae uploaded a real-world format file (`Retail India` CSV) and encountered an unhandled exception:
> *"Could not find Date column. Bank statement column."*

Inspection of the file revealed that the columns were present but named with slight variations:
- File contained: `Tax date`, `Narration ID`, `business ID`, `narration`, `channel date`.
- The parser strictly checked for exact lowercase strings (`date`, `txn_date`, `transaction_date`). Because `Tax date` and `channel date` did not match the rigid lookup dictionary, parsing aborted with a user-facing error.

---

## 2. Solution: Multi-Tier Fuzzy Regex Normalizer

In `src/copilot/ingest.py`, replace exact string lookups with a priority-ranked regex dictionary:

```python
HEADER_PATTERNS = {
    "date": [
        r"^txn_?date$",
        r"^trans(?:action)?_?date$",
        r"^value_?date$",
        r"^posting_?date$",
        r"^date$",
        r"^channel_?date$",
        r".*date.*",  # Fallback fuzzy
    ],
    "narration": [
        r"^narration$",
        r"^description$",
        r"^particulars$",
        r"^remarks$",
        r"^transaction_?details$",
        r".*narrat.*",
    ],
    "credit": [
        r"^credit(?:_?inr)?$",
        r"^deposit(?:_?amount)?$",
        r"^cr(?:_?amt)?$",
        r"^inflow$",
    ],
    "debit": [
        r"^debit(?:_?inr)?$",
        r"^withdrawal(?:_?amount)?$",
        r"^dr(?:_?amt)?$",
        r"^outflow$",
    ],
    "balance": [
        r"^balance(?:_?inr)?$",
        r"^running_?balance$",
        r"^closing_?balance$",
        r"^bal$",
    ]
}
```

### 2.1 Multi-Header Resolution Rules
1. Strip leading/trailing whitespace, punctuation, and normalize to lowercase.
2. If multiple columns match a pattern (e.g. `Tax date` and `channel date`), prioritize:
   - Specific keywords (`trans`, `value`, `posting`) over generic keywords (`tax`, `channel`).
3. If no match is found, present an interactive column-mapping selectbox allowing the user to map their file's columns in 1 click.
