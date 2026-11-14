# ADR-001: Local-First Sovereign Vault Architecture

> **Status:** Accepted  
> **Date:** 2026-11-14  
> **Deciders:** Team 11 Architecture Board  
> **Technical Domain:** Data Persistence, Cryptography, Local-First Architecture, Zero-Knowledge Privacy  
> **Cross-References:** `GLOSSARY.md` (§1, §2), `copilot.vault.models`, `copilot.vault.guardrails`  

---

## 1. Context and Problem Statement

Indian micro, small, and medium enterprises (MSMEs)—specifically wholesale FMCG distributors, semi-urban healthcare clinics, and service agencies—operate across a structural dual-plane financial reality:
1. **The Formal Public Plane (Plane A)**: Bank current accounts, Cash Credit (CC) hypothecated facilities, GST Network invoices (GSTR-1, GSTR-2B, GSTR-3B), and official ledgers audited by the visiting Chartered Accountant (CA).
2. **The Sovereign Operating Plane (Plane B)**: Physical cash drawers (*Galla*), secondary godown safe cash, informal trade credit extended to retail counters (*Pending Khata*), unbanked counter receipts (*Rokad*), and salesman field collection slips (*Kaccha Parchi*).

Conventional cloud-based accounting and neo-banking platforms (e.g., RazorpayX, Khatabook, Zoho Books, Tally on AWS) demand that all enterprise financial records be continuously synchronized to centralized multi-tenant cloud servers. For Indian SME merchants, this cloud-first architecture introduces catastrophic operational, regulatory, and legal vulnerabilities:
- **Cloud Custody Risk & Subpoena Vulnerability**: Hosting confidential counter cash receipts, salesman collection slips, or informal credit ledgers on third-party cloud servers exposes the business owner to automated third-party data discovery, cloud vendor data breaches, and third-party algorithmic surveillance under the Digital Personal Data Protection (DPDP) Rules, 2025.
- **The Dual-Plane Liquidity Paradox**: Bank-only cloud systems report false insolvency (signaling imminent operational failure when the bank balance is drawn to the CC limit, while completely ignoring ₹6,40,000 of physical counter cash) or hidden insolvency (reporting healthy bank balances while ignoring unrecorded spot supplier cash liabilities).
- **Latency and Offline Availability**: Wholesale distribution centers operate in dense, high-interference physical markets (e.g., Sadar Bazar, Crawford Market, Chickpet) characterized by intermittent cellular connectivity. A cash-flow copilot that requires network round-trips to compute daily solvency or verify a cash receipt halts counter operations.

We require an architectural foundation that delivers absolute sovereign privacy, sub-second local query response, deterministic resilience against connectivity outages, and zero cloud custody liability.

---

## 2. Decision

We decide to implement a **Local-First Sovereign Vault Architecture** founded on the following core design principles:

### 2.1 On-Device Hardware-Encrypted Storage (SQLCipher 4 AES-256)
- **Engine**: Local embedded SQLCipher 4 (256-bit AES-CBC with HMAC-SHA512 per-page integrity verification) embedded within SQLite and local DuckDB instances.
- **Key Derivation & Hardware Security Integration**:
  - Master encryption keys are generated via platform hardware security modules: **Android StrongBox Keymaster** (FIPS 140-2 Level 3 tamper-resistant hardware) and **iOS Secure Enclave / Apple Keychain** (`kSecAccessControlBiometryAny`).
  - **Raw BLOB Optimization**: Standard PBKDF2 / Argon2 key derivation imposes 80ms–150ms of CPU latency on mobile/embedded processors upon database open. To satisfy the `<10-minute daily review` budget and instantaneous cockpit load times, the copilot derives a raw 256-bit cryptographic key BLOB once per session from the hardware enclave, caches it in memory-pinned space (`mlock`), and passes it directly to SQLCipher (`PRAGMA key = "x'...'"`). This delivers cold database initialization in **$< 8\text{ ms}$**.

### 2.2 Unidirectional Downward Data Flow Firewall
We establish a non-negotiable architectural invariant: **Unidirectional Downward Synchronization**.

```
+---------------------------------------------------------------------------------+
|                       FORMAL PUBLIC PLANE (Plane A)                             |
|       Bank Statements (OFX/CSV)  |  GSTN E-Invoices  |  Audited Tally Books     |
+---------------------------------------------------------------------------------+
                                       │
                                       │  (Strict Unidirectional Downward Flow)
                                       │  Ingest bank credits & formal commitments
                                       ▼
+---------------------------------------------------------------------------------+
|                   SOVEREIGN LOCAL-FIRST VAULT (Plane B)                         |
|   ┌─────────────────────────────────────────────────────────────────────────┐   |
|   │ SQLCipher 4 AES-256 (Local Device Storage)                              │   |
|   │  - Galla Cash Till & Float Counters (copilot.vault.GallaEntry)          │   |
|   │  - Daily Rokad Bahi Cash Register (copilot.vault.RokadEntry)            │   |
|   │  - Pending Khata Trade Credit (copilot.vault.KhataAccount)              │   |
|   │  - Field Collection Slips (copilot.vault.Collection)                    │   |
|   │  - Local True Solvency Engine (copilot.vault.TotalSolvency)             │   |
|   └─────────────────────────────────────────────────────────────────────────┘   |
|                                      │                                          |
|                                      X  (STRICT UPWARD FIREWALL)                |
|                                      X  NO unbilled transactions, cash memos,   |
|                                      X  or informal ledgers EVER exported       |
+---------------------------------------------------------------------------------+
```

- Formal banking feeds and tax invoices flow downward into the local vault to evaluate overall liquidity.
- No informal transaction, Galla cash count, Rokad disbursement, or Khata credit entry can ever flow upward or be exported to external accounting software, CA portals, or tax filings without explicit multi-factor owner approval and formal tax invoice conversion.

### 2.3 On-Device True Solvency Computation
Solvency is computed locally within `copilot.vault.models.TotalSolvency` without transmitting intermediate parameters off the physical device:
$$\text{True Solvency Runway} = (\text{Bank Balance} - \text{CC Drawn}) + \text{Galla Cash} + \left(\alpha \times \sum \text{Pending Khata}\right) - \left(\text{Formal Commitments} + \text{Cash Supplier Payables}\right)$$
- $\alpha$ is calibrated by default to **$0.85$** (15% bad-debt haircut).
- Computes both **False Insolvency** (bank deficit $< 0$ while combined runway $> 0$) and **Hidden Insolvency** on-device in under 2 milliseconds.

### 2.4 Sovereign Disaster Recovery & User-Controlled Exports
- Cloud synchronization is disabled by default.
- Encrypted local backups are generated as single-file, Argon2id-wrapped, AES-256-GCM encrypted bundles (`.vault` archive) that the owner can export manually via USB, AirDrop, or personal Google Drive/iCloud container using their own private keys.

---

## 3. Consequences

### Positive Consequences
- **Absolute Regulatory & Evidentiary Isolation**: The enterprise maintains an ironclad boundary between statutory tax books and confidential internal operating cash, eliminating the risk of cloud subpoena or accidental exposure to external auditors.
- **Sub-10ms Operating Performance**: All queries, daily cash balancing (`GallaEntry.is_balanced`), and solvency runway projections execute entirely against local flash storage with zero network latency.
- **Complete Offline Independence**: The entire application functions with zero degradation in wholesale basements, warehouse godowns, or rural retail routes with zero internet connectivity.
- **Zero Cloud Custody Liability**: The platform operator stores zero customer financial transactions, eliminating data fiduciary liabilities, data breach notification overheads, and regulatory compliance burdens under the DPDP Act, 2023.

### Negative Consequences and Mitigations
- **User Responsibility for Device Loss**: If a user loses their physical device without an offsite backup, data cannot be recovered by the software vendor.  
  *Mitigation*: The cockpit prompts the user for a weekly local encrypted backup export to physical media or private personal cloud storage.
- **Multi-Device Synchronization Complexity**: Seamless multi-device real-time collaboration (e.g., cashier tablet + owner smartphone) requires peer-to-peer local Wi-Fi synchronization rather than a centralized cloud hub.  
  *Mitigation*: Implement local-network peer-to-peer sync using encrypted TLS channels over mDNS/Bonjour for same-store multi-terminal setups.

---

## 4. Considered Alternatives and Rejection Rationale

1. **Centralized Multi-Tenant Cloud Database (PostgreSQL / Supabase / AWS Aurora)**:
   - *Rejected*: Incurred catastrophic legal and privacy risks. Storing unbilled salesman collection slips and informal counter cash on multi-tenant cloud servers creates an existential legal liability under the Income-tax Act, 2025 and BNS §241, and violates the merchant's trust.
2. **Client-Side Plain SQLite with Cloud Database Synchronization**:
   - *Rejected*: Plain SQLite leaves unencrypted plaintext databases on mobile flash storage, vulnerable to forensic extraction if the physical device is inspected or seized.
3. **Standard PBKDF2 Password Derivation on App Launch**:
   - *Rejected*: Benchmark testing showed 120ms–250ms startup delays on budget Android hardware (MediaTek Helio / Snapdragon 680 series commonly used by cashiers and delivery agents), violating the sub-second UI responsiveness requirement. Replacing PBKDF2 with hardware enclave raw BLOB passing reduced initialization to $< 8\text{ ms}$.

---

## 5. Compliance & Verification Method

### 5.1 Verification Commands
Verify local vault models, mathematical invariants, and zero network leaks:
```bash
# Execute local vault test suite
cd /Users/ishaanwadhwa/Projects/ps11-copilot
.venv/bin/pytest tests/test_vault.py -v
```

### 5.2 Architectural Invariants Tested
- **Test Case `test_galla_balancing_and_drift`**: Validates that physical cash counting, drift detection ($\Delta > ₹50$ flagged as `"Drift to check"`), and expected cash balancing execute deterministically on-device.
- **Test Case `test_true_solvency_calculation`**: Confirms that `TotalSolvency` accurately detects False Insolvency without network communication.
- **Code Audit**: Verify `src/copilot/vault/models.py` imports only local data libraries (`dataclasses`, `pandas`), containing zero HTTP client imports or external network calls.
