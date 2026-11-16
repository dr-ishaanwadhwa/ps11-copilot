# Chief of Staff Knowledge Base & Decision Wiki

> **Directly Responsible Individual:** Chief of Staff (`ps11-copilot`)  
> **Repository:** `/Users/ishaanwadhwa/Projects/ps11-copilot`  
> **Origin Date:** 15 November 2026  
> **Status:** Active Historical Record  

This wiki captures durable tribal knowledge, architectural decisions, user feedback syntheses, and operational invariants for the SME Cash-Flow Copilot. It operates under historical citation rules: claims cite transcripts, commits, and dates.

---

## 1. Team Reviews & Transcripts
- [2026-11-15 Live Demo Review (Transcript `ijt-mtka-pgm`)](feedback-2026-11-15-demo.md): Synthesis of core feedback from Dr. Ishaan Wadhwa, Alok Ae, Harshit Sahu, and Shourya Gupta on custom statement ingestion, vault UX, forecast dynamic simulation, and UI styling.

## 2. Strategic & Product Decisions
- [Decision 2026-11-15: UI De-AI-ification (Removing Emojis)](decisions/2026-11-15-ui-de-ai-ification.md): Mandate to eliminate amateurish emoji styling across the cockpit in favor of institutional fintech SVG iconography.
- [Decision 2026-11-15: First-Run Onboarding Landing vs Hidden Setup Guide](subsystems/onboarding-landing-experience.md): Transitioning the buried Setup Guide into a high-converting first-run landing page with Google Authentication.

## 3. Subsystem Specifications & Hardening Notes
- [Subsystem: Dynamic Forecast Simulation](subsystems/forecast-dynamic-simulation.md): Upgrading static historical 90-day charts to user-driven forward simulations with plain-language solvency cards.
- [Subsystem: Fuzzy Regex Bank Statement Ingestion](subsystems/statement-ingestion-regex.md): Multi-header normalization resolving casing and column mismatch crashes on custom retail CSV uploads.
- [Subsystem: Sovereign Vault Unlocking & Role Ergonomics](subsystems/sovereign-vault-ux.md): Resolving PIN entry disconnects, locked-state visual glitches, and role-switcher permissions.

## 4. Reviews
- [2026-11-16 Review of the 15 Nov run's documents](reviews/2026-11-16-document-review.md): measured checks of the pitch plan, strategy audit, statutory attestation, specs and onboarding guide against the code and data pack. Read before quoting any number externally.
