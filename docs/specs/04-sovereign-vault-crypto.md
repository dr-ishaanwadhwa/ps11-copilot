# 04. Sovereign Vault Cryptography Specification

**Specification ID:** `SPEC-CRYPTO-004`  
**Classification:** Modular Engineering Specification  
**Target Repository:** `/Users/ishaanwadhwa/Projects/ps11-copilot`  
**Related Blueprint:** `docs/blueprints/nextjs-threejs-cashflow-copilot.md` §6.1, §2.4  
**Related Invariants:** ADR-001 (Local-First Sovereign Vault), Income-tax Act §247 / DPDP Act 2023

---

## 1. Architectural Mandate & Threat Model

In the Indian MSME economy, merchants operate across two financial realities:
1. **The Formal Public Plane:** Bank accounts, GST filings, and official accounting ledgers audited by Chartered Accountants.
2. **The Sovereign Operating Cash Plane:** Physical counter cash (*Galla/Rokad*), secondary godown safes, and daily salesman route collection slips (*Kaccha Parchi*).

### The Threat
Transmitting informal cash drawer counts or salesman collection slips to a remote cloud backend exposes the business owner to severe regulatory and legal risks:
- Deemed income additions and search & seizure under Section 247(1)(vi) of the Income-tax Act, 2025.
- Data breaches and unauthorized customer phone book exposure under the Digital Personal Data Protection (DPDP) Act, 2023.

### The Invariant (ADR-001)
Client-side informal drawer cash records and collection slips must **never** touch a remote cloud backend or server database unencrypted. Plaintext cash records exist **exclusively in volatile browser memory (RAM)** of the merchant's authenticated device.

---

## 2. Cryptographic Envelope Specification

Encrypted records written to client storage conform to the immutable binary envelope format:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    SOVEREIGN VAULT ENVELOPE FORMAT (v1)                      │
├───────────────┬───────────────┬───────────────┬──────────────────────────────┤
│ MAGIC (12B)   │ SALT (16B)    │ NONCE (12B)   │ CIPHERTEXT + TAG (VARIABLE)  │
├───────────────┼───────────────┼───────────────┼──────────────────────────────┤
│ ASCII string  │ Cryptographic │ Cryptographic │ AES-256-GCM encrypted        │
│ "SOV_VAULT_V1\0" random salt  │ random IV     │ payload + 16-byte auth tag   │
│ (Header ID)   │ for PBKDF2    │ for AES-GCM   │ (Guarantees integrity)       │
└───────────────┴───────────────┴───────────────┴──────────────────────────────┘
```

### 2.1 Key Derivation Function (PBKDF2-HMAC-SHA256)
- **Algorithm:** PBKDF2 with HMAC-SHA256.
- **Iterations:** 100,000 iterations (conforming to OWASP Password Storage standards).
- **Salt:** 16-byte cryptographically secure pseudorandom number generator (`window.crypto.getRandomValues(new Uint8Array(16))`).
- **Derived Key:** 256-bit symmetric key (`AES-GCM`, 256 bits, exportable: false).
- **Web Worker Offloading:** In production environments, PBKDF2 key derivation is offloaded to a background Web Worker (`vaultCrypto.worker.ts`) to prevent freezing the UI main thread on budget mobile processors.

### 2.2 Authenticated Encryption (AES-256-GCM)
- **Cipher:** `AES-GCM` (Galois/Counter Mode).
- **Initialization Vector (Nonce):** 12-byte cryptographically random IV generated uniquely per encryption operation.
- **Authentication Tag:** 16-byte (128-bit) integrity tag appended automatically by Web Crypto.
- **Plaintext Format:** UTF-8 encoded JSON string containing domain entities (drawer balancing records, salesman parchi collection slips).

---

## 3. Client Storage Architecture

```
Browser Storage:
├── IndexedDB: "ps11_sovereign_vault"
│   ├── ObjectStore: "sovereign_vault_store"
│   │   └── Key: "latest_envelope" -> ArrayBuffer (Binary Envelope)
│   └── ObjectStore: "draft_slips_encrypted"
│       └── Key: "active_parchi_drafts" -> ArrayBuffer (In-progress drafts)
```

### 3.1 Local Envelope Persistence
- When the user locks the vault or saves a day-close balancing record, the encrypted envelope is committed to browser **IndexedDB** (`ps11_sovereign_vault / sovereign_vault_store`).
- Zero unencrypted cash data is stored in LocalStorage, SessionStorage, or HTTP cookies.

### 3.2 In-Progress Parchi Draft Scratchpad
Cashiers frequently log collection slips intermittently throughout the afternoon while attending to counter customers. To prevent data loss without violating ADR-001:
- Every keystroke on an active salesman slip form is encrypted on-the-fly and auto-saved to an encrypted IndexedDB scratchpad (`draft_slips_encrypted`).
- If the browser tab crashes or is accidentally refreshed, uncommitted drafts are restored automatically upon PIN re-authentication.

---

## 4. Volatile RAM Lifecycle & Ergonomic Protections

```
┌────────────────────────────────────────────────────────────────────────┐
│                        VOLATILE RAM LIFECYCLE                          │
├─────────────────────┬─────────────────────┬────────────────────────────┤
│   PIN / BIOMETRIC   │   ACTIVE SESSION    │      AUTO-LOCK & WIPE      │
│     AUTHENTICATION  │   (VOLATILE RAM)    │     (MEMORY EVACUATION)    │
├─────────────────────┼─────────────────────┼────────────────────────────┤
│ • User enters PIN   │ • CryptoKey stored  │ • 15-min idle timer fires  │
│ • PBKDF2 derives    │   in Zustand store  │   OR 5-min tab grace ends  │
│   CryptoKey in RAM  │ • GallaEntry cached │ • CryptoKey = null         │
│ • Decrypts envelope │ • Fast sub-10ms UI  │ • GallaEntry = null        │
│ • Vault is UNLOCKED │   reads from RAM    │ • Vault status -> LOCKED   │
└─────────────────────┴─────────────────────┴────────────────────────────┘
```

### 4.1 Tab-Switch Ergonomics (5-Minute Grace Period)
- Closing or locking the vault on immediate `visibilitychange: hidden` severely disrupts cashier workflow (switching to WhatsApp Web to check UTR slips or PDF bills).
- The system enforces a **5-minute background grace period timer**. If the tab returns to active focus within 300 seconds, the session remains uninterrupted. If hidden for $> 300$ seconds, the session keys are wiped.

### 4.2 Inactivity Evacuation (15-Minute Timeout)
- Continuous user activity (mouse, touch, keydown) resets the idle timer.
- After 15 minutes of zero input, the store triggers `useVaultStore.getState().lockVault()`, which sets `sessionCryptoKey = null`, clears decrypted balances, and garbage-collects all sensitive data from memory.

---

## 5. WebAuthn PRF Biometric Passkey Upgrade

To protect against offline GPU dictionary attacks on short 4-digit PINs ($10^4$ combinations cracked in $<30$ seconds):
1. The system supports the **WebAuthn PRF (Pseudo-Random Function) extension**.
2. Platform biometrics (Touch ID, Face ID, Windows Hello) derive a 256-bit hardware-backed symmetric key directly from the device's Secure Enclave / StrongBox.
3. The derived PRF key wraps the master vault encryption key. Extraction of the encrypted envelope without physical biometric authorization is mathematically infeasible.

---

## 6. Zero Cloud Plaintext Leakage Guarantees

### 6.1 Downward-Only Data Flow
- Formal bank feeds, Cash-Credit limits, and GST obligations synchronize **unidirectionally downward** from the server into the client application.
- Physical drawer counts, till drifts, and informal route slips **never travel upward** across HTTP.

### 6.2 Zero-Knowledge Conversational Template Tokens
When the user queries the AI Copilot regarding daily solvency:
- The HTTP request to `/api/copilot/stream` contains **only formal identifiers**: `{ question, businessId, asOfDate }`.
- The server evaluates formal records and streams structured response chunks with placeholder tokens:
  `"You also have {{LOCAL_VAULT_GALLA_CASH}} physical cash in your godown drawer."`
- The client component intercepts the token in the browser and interpolates the decrypted balance from `useVaultStore` in volatile RAM.
- Result: The user sees their true cash position, while third-party LLMs, CDN proxies, and server access logs maintain zero knowledge of the cash holding.
