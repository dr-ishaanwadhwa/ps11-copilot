# ADR 0001: Local-First Sovereign Vault

## Status
accepted

## Context
Indian SMEs operate across a split-plane commercial reality where formal bank accounts coexist with counter drawer cash (Galla), delivery route collections, and informal customer credit books (Khata). Conventional cloud accounting SaaS platforms (Zoho Books, QuickBooks, RazorpayX) mandate multi-tenant cloud database synchronization of all financial transactions.

Under Section 247 of the Income-tax Act, 2025 (effective 1 April 2026), tax search and survey authorities possess expansive statutory powers to inspect, access, and seize "virtual digital spaces", encompassing cloud databases, hosted servers, and remote SaaS storage. If informal cash records or working cash buffers are discovered on cloud servers, merchants face aggressive deemed-income tax assessments and penal levies (30% to 84% under Sections 102 and 195). Furthermore, cloud software providers face statutory abetment and intermediary prosecution under Section 484 of the Income-tax Act, 2025 and Section 122(3) of the Central Goods and Services Tax (CGST) Act, 2017 for actively hosting informal shadow ledgers.

Because of automated tax department data mining across GSTN, e-Way bills, and banking feeds, Indian wholesale merchants categorically refuse to record physical drawer balances or informal customer accounts in any software connected to central cloud servers.

## Decision
We reject multi-tenant cloud storage and central server synchronization for informal cash, collection slips, and trade credit management. We architect an air-gapped, on-device **Sovereign Vault** built on embedded SQLite/DuckDB encrypted with **SQLCipher 4 (AES-256 with per-page HMAC verification)**.

The cryptographic key is derived from a local user PIN combined with hardware-backed key storage (Android Keystore / iOS Keychain / Secure Enclave). The application transmits zero cloud telemetry, emits zero remote logging of transaction amounts, and holds no central database capable of subpoena or data exfiltration.

Data integration is strictly unidirectional: formal tax commitments and official bank statement feeds pull downward into the local vault in a read-only fashion. The Sovereign Vault never pushes, mirrors, or exposes informal cash entries upward to cloud servers, external APIs, or statutory accounting exports.

## Considered Options
- **Multi-Tenant Cloud SaaS with Row-Level Encryption**: Rejected. Cloud databases remain vulnerable to search and seizure under Income-tax Act Section 247, expose platform developers to criminal abetment liability under CGST Act Section 122(3) and Income-tax Act Section 484, and trigger immediate merchant rejection due to cloud visibility fears.
- **Unencrypted Local SQLite / Mobile Shared Preferences**: Rejected. Standard OS storage decrypts whenever the user unlocks the mobile device, leaving raw databases exposed to automated Android Debug Bridge (ADB) extraction, unencrypted local backups, and device malware.
- **Local-First SQLCipher 4 Sovereign Vault with Hardware Keystore**: Accepted. Provides military-grade AES-256 zero-knowledge encryption at rest, achieves sub-10ms query execution directly on consumer hardware, operates 100% offline at remote godown counters, and insulates both merchant and platform from cloud search exposure.

## Consequences
- **Positive**: Complete merchant trust through physical data sovereignty; zero developer intermediary liability; total operational functionality without internet connectivity at wholesale godown locations.
- **Negative / Trade-off**: No automatic multi-device cloud synchronization without user-managed encrypted peer-to-peer export; lost device PIN results in permanent data loss unless an encrypted offline physical backup was maintained.
