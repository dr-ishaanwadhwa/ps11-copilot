# Subsystem Specification: Sovereign Vault Unlocking & Role Ergonomics

> **Subsystem:** Sovereign Vault & Role Permissions  
> **Date:** 15 November 2026  
> **Status:** APPROVED FOR IMPLEMENTATION  
> **Origin:** Team Demo Testing (`ijt-mtka-pgm`)  

---

## 1. Problem & Friction Observed

During the live test on 15 November 2026, Harshit Sahu and Alok Ae encountered confusion attempting to unlock the vault:
- Entering PIN `0000` while viewing as Accountant did not unlock the cash drawer, because Accountant mode is restricted by ADR-001/004.
- There was ambiguity over where the PIN should be typed (the sidebar card vs the Cash Book inline card).
- When locked, a visual layout glitch was observed on certain viewports.

---

## 2. Redesigned Vault Gating Flow

1. **Unambiguous Contextual Modal:**
   - Instead of fragmented text inputs in both the sidebar and main page, clicking any locked vault element opens a focused, secure modal dialog.
   - 4-digit PIN pad with tactile keypress feedback and clear masking (`••••`).
2. **Explicit Role Explanation:**
   - If the active role is **Accountant (CA)** or **Counter Staff**, the dialog explicitly informs:
     > *"You are currently viewing as Accountant. The Sovereign Cash Drawer is private to the Owner. To view informal books, switch to Owner role or ask the Owner to enable 'Share with Accountant' in settings."*
3. **Auto-Relock Persistence:**
   - Re-confirmed invariant: Any change in operational role away from Owner immediately triggers `vault.lock()` in memory, zeroing out plaintext drawer balances from the session state.
