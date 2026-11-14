# ADR-003: Section 18 Limitation Act Legal Shield and Zero-Knowledge Debt Recovery Architecture

> **Status:** Accepted  
> **Date:** 2026-11-14  
> **Deciders:** Team 11 Architecture Board  
> **Technical Domain:** Statutory Compliance, Digital Evidence, Legal Engineering, Privacy Architecture, Cryptography  
> **Cross-References:** `GLOSSARY.md` (§4), `copilot.vault.chase`, `copilot.vault.models.KhataAccount`, `tests/test_vault.py`  

---

## 1. Context and Problem Statement

Trade receivables constitute the single largest and most vulnerable current asset for Indian wholesale distributors and manufacturers. In standard Indian trading practice, credit extended to retail counters is informal, revolving, and rarely backed by formal promissory notes or bank guarantees. This operational model faces severe statutory and privacy hazards:

1. **The 3-Year Statutory Guillotine (Limitation Act, 1963)**: Under Article 14 and Article 15 of the Schedule to the Limitation Act, 1963, the statutory limitation period for filing a civil suit to recover the price of goods sold or money lent is **exactly 3 years (36 months)** from the date the invoice becomes payable. Once 36 months elapse without formal legal action or written acknowledgment, the debt becomes legally time-barred and unenforceable in a court of law. Traditional accounting software tracks debtor aging only up to "90+ days", leaving owners completely blind to the approaching 36-month legal expiration cliff.
2. **Cloud WhatsApp BSP Privacy and Consent Violations (DPDP Rules, 2025)**: Competing recovery platforms (e.g., Credflow, RazorpayX, Khatabook) automate payment reminders by ingesting the merchant's entire customer directory, outstanding balances, and phone numbers onto central cloud servers and transmitting automated debt collection messages via cloud WhatsApp Business Solution Providers (BSPs like Twilio, Gupshup, or Meta Cloud API). Under the **Digital Personal Data Protection (DPDP) Act, 2023** and **DPDP Rules, 2025**:
   - Uploading a retail shopkeeper's phone number and debt status to a third-party cloud without explicit, logged consent is a direct regulatory violation.
   - Using cloud BSP APIs makes the software vendor a Data Fiduciary/Processor, exposing both the vendor and merchant to regulatory penalties up to ₹250 Crore for unauthorized data processing.
3. **Judicial Inadmissibility of Digital Debt Confirmations (Bharatiya Sakshya Adhiniyam, 2023)**: If a debtor disputes an outstanding balance in commercial court, simple mobile screenshots or unverified chat printouts are routinely rejected by judges. Under Section 63 of the **Bharatiya Sakshya Adhiniyam (BSA), 2023** (which superseded Section 65B of the Indian Evidence Act, 1872 on 1 July 2024), an electronic record is only admissible if accompanied by a contemporaneous cryptographic hash certificate, device metadata, and an attestation of system integrity.

We require an on-device, zero-knowledge architecture that alerts merchants to the limitation cliff, enables lawful debt clock resets, complies fully with DPDP Rules 2025, and produces BSA Section 63 evidentiary proof without transmitting customer data to the cloud.

---

## 2. Decision

We decide to architect the **Section 18 Limitation Act Legal Shield and Zero-Knowledge Recovery Engine** (`src/copilot/vault/chase.py`):

```
                        LOCAL KHATA ACCOUNT RECORD
                                    │
                         Months Open >= 30 Months?
                                    │
                  ┌─────────────────┴─────────────────┐
                  │ YES                               │ NO
                  ▼                                   ▼
        LIMITATION DANGER ALERT             Standard Courtesy Alert
   (Approaching 36m legal guillotine)         (Routine balance reminder)
                  │
                  ▼
   Client-Side Deep Link Generation (Zero Cloud Transmission)
   Construct local "https://wa.me/{phone}?text={encoded_message}"
   Draft neutral, relationship-preserving acknowledgment request:
   "Namaste {party} ji... pending balance is {amt}... Could you please
    confirm if this matches your books...?"
                  │
                  ▼
   Owner Taps Link -> Opens Native WhatsApp on Owner's Own Device
                  │
                  ▼
   Debtor Replies Confirming Balance via WhatsApp Message
                  │
                  ▼
   Section 18 Clock Reset & BSA 2023 Section 63 Digital Certificate
   1. Statutory limitation period resets for a FRESH 3-YEAR PERIOD.
   2. Local SHA-256 cryptographic digest calculated on message payload.
   3. Hardware device metadata, timestamp, and certificate generated on-device.
```

### 2.1 30-Month Statutory Limitation Alert Tripwire
- In `copilot.vault.models.KhataAccount`, we establish the property `is_limitation_alert`:
  ```python
  @property
  def is_limitation_alert(self) -> bool:
      """Section 18 Limitation Act alert: debts older than 30 months risk becoming unenforceable."""
      return self.months_open >= 30
  ```
- By firing the warning at **30 months**, the merchant is provided a **6-month operational buffer** before the 36-month statutory guillotine falls.

### 2.2 Section 18 & Section 19 Statutory Debt Clock Reset
- **Section 18, Limitation Act, 1963**: Where, before the expiration of the prescribed period for a suit, an acknowledgment of liability in respect of property or right has been made in writing signed by the party against whom such property or right is claimed, **a fresh period of limitation shall be computed from the time when the acknowledgment was so signed**.
- **Digital Validity under IT Act, 2000**: Under Section 4 and Section 10A of the Information Technology Act, 2000, electronic records and communications (including WhatsApp messages and email acknowledgments) satisfy the legal requirement for "in writing" and "signed" acknowledgments.
- **Section 19 (Part-Payment)**: Any token payment made towards the principal debt (e.g., ₹500 via UPI) similarly restarts the full 3-year statutory clock.

### 2.3 Client-Side Zero-Knowledge `wa.me` Deep Link Generation
- The copilot generates reminders strictly on the client device using URL schemes (`https://wa.me/<phone>?text=<encoded_text>`).
- **Zero Cloud Transmission**: Customer contact numbers, ledger balances, and draft reminders **never touch any server, cloud BSP, or external API**.
- **User Agency**: The copilot never sends automated messages in the background. The merchant reviews the draft in the "Aaj Ka Hisaab" cockpit and taps the link, which opens the native WhatsApp application on the merchant's personal smartphone. The merchant chooses whether and when to send the message.
- **DPDP Act, 2023 Compliance**: Because data processing occurs entirely within the merchant's personal device for direct bilateral commercial communication, zero third-party data processing or fiduciary transfer occurs.

### 2.4 BSA Section 63 Contemporaneous Digital Evidentiary Certificate
To ensure electronic acknowledgments withstand judicial scrutiny under Section 63 of the Bharatiya Sakshya Adhiniyam, 2023:
1. When a debtor's written confirmation is received, the copilot computes a **SHA-256 cryptographic hash** of the raw text and attached transaction metadata.
2. The copilot generates a printable, machine-readable digital certificate recording:
   - Unique Cryptographic Hash (SHA-256).
   - UTC and IST Timestamp of receipt.
   - Operating Device Hardware Identifier (Device Model, OS Build, MAC/IMEI hash).
   - Invariant declaration under BSA §63(4) certifying that the device was operating under lawful control without security compromise.

### 2.5 Non-Incriminating, Relationship-Preserving Vernacular Copy
Aggressive corporate collection notices destroy delicate wholesale trade relationships. The engine generates courteous, non-threatening phrasing:
- *Standard Reminder*:
  > *"Namaste [Party Name] ji, warm greetings from [Business Name]. Just sharing a friendly update: your current pending khata balance is ₹[Amount]. Whenever convenient, please arrange the settlement via UPI to [Handle]. Thank you for your partnership!"*
- *Section 18 Acknowledgment Request*:
  > *"Namaste [Party Name] ji, hope you are doing well. As per our records with [Business Name], the pending balance is ₹[Amount] from our earlier supplies. Could you please confirm if this matches your books, or let us know when we can expect a small part-settlement? Thank you!"*

---

## 3. Consequences

### Positive Consequences
- **Elimination of Bad-Debt Write-Offs Due to Limitation Expiry**: Merchants capture formal acknowledgments or part-payments within the 30–36 month window, legally preserving hundreds of thousands of rupees in collectible receivables.
- **Complete Immunity from DPDP Act Cloud Liabilities**: Zero customer personal data is ingested or stored on cloud servers. No expensive cloud BSP subscriptions (Twilio/Gupshup per-message fees) are required.
- **Court-Admissible Evidence**: Generated BSA Section 63 certificates provide practicing advocates and CAs with mathematically tamper-evident exhibits ready for commercial summary suits under Order XXXVII of the Code of Civil Procedure (CPC), 1908.

### Negative Consequences and Mitigations
- **Reliance on Debtor Willingness to Reply**: A debtor may choose to ignore the WhatsApp reminder.  
  *Mitigation*: If no reply is recorded within 30 days of the month-30 alert, the copilot escalates the alert to recommend a physical visit by the salesman to secure a signed physical statement of account or token ₹100 cash part-payment under Section 19.

---

## 4. Considered Alternatives and Rejection Rationale

1. **Cloud-Based Automated WhatsApp Bot via WhatsApp Business API**:
   - *Rejected*: Incurred massive compliance overhead under DPDP Rules, 2025; exposed customer debt lists to Meta/cloud vendors; high per-conversation API costs; and violated user trust.
2. **Automated Registered Post Legal Notices via Third-Party Legal API**:
   - *Rejected*: Sending formal advocate notices prematurely destroys the commercial relationship with retail counters, causing the retailer to switch distributors. A polite WhatsApp acknowledgment achieves the exact same Section 18 legal shield without alienating the customer.
3. **Standard 90-Day Aging Bucket Cutoff Only**:
   - *Rejected*: Leaving debts older than 90 days in an unmonitored aggregate bucket hides the approach of the 3-year statutory expiration threshold.

---

## 5. Compliance & Verification Method

### 5.1 Verification Commands
Run unit tests verifying the 30-month alert threshold and client-side `wa.me` link encoding:
```bash
cd /Users/ishaanwadhwa/Projects/ps11-copilot
.venv/bin/pytest tests/test_vault.py -k "limitation" -v
```

### 5.2 Architectural Invariants Tested
- **Test Case `test_khata_limitation_alert`**: Confirms that `KhataAccount(months_open=29).is_limitation_alert` is `False`, while `months_open=30` evaluates to `True`.
- **Test Case `test_format_whatsapp_reminder_link_encoding`**: Verifies that `format_whatsapp_reminder` produces a valid `wa.me` URL, includes proper international dial code formatting (`91...`), cleanly URL-encodes the message body, and includes the specific Section 18 acknowledgment prompt when `is_limitation_alert` is active.
- **Privacy Audit**: Inspect `src/copilot/vault/chase.py` to ensure it contains zero network requests, third-party SDKs, or cloud messaging dependencies.
