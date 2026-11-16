# Subsystem Specification: First-Run Onboarding Landing Experience

> **Subsystem:** Application Shell & Onboarding  
> **Date:** 15 November 2026  
> **Status:** APPROVED FOR ARCHITECTURE  
> **Origin:** Team Demo Discussion (`ijt-mtka-pgm`)  

---

## 1. Problem & Strategic Context

In the live demo on 15 November 2026, the team discovered two UX issues with the existing onboarding structure:
1. **Visual Glitch in Setup Wizard:** Step 2 exhibited an overlapping CSS issue where the "Upload file" action conflicted with the upload zone bounds.
2. **Inverted Hierarchy:** Alok Ae and Dr. Ishaan noted that burying the setup flow on Page 8 (*"Setup Guide"*) felt disjointed for a new user entering the application.

> *Alok Ae:* "This is not the first thing that users should be able to see even... proper landing page and then once they log in from there they should be able to see all of this..."  
> *Dr. Ishaan Wadhwa:* "Instead of login login we'll just say select which business you are... I'll add Google authentication... That is free anyway. So that'll be easier."

---

## 2. The Onboarding Landing Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                   FIRST-RUN LANDING PAGE ARCHITECTURE                  │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Hero Landing Value Proposition                                      │
│    "Explain Every Rupee Between Your Bank and Your Books"              │
├────────────────────────────────────────────────────────────────────────┤
│ 2. One-Click Google Authentication                                     │
│    Fast, trusted OAuth session initiation                              │
├────────────────────────────────────────────────────────────────────────┤
│ 3. Commercial Archetype Selector                                       │
│    [ FMCG Wholesale Distributor ] [ Healthcare Clinic ] [ Agency ]     │
├────────────────────────────────────────────────────────────────────────┤
│ 4. Seamless Data Connection (3 Options)                                │
│    (a) Instant Demo Mode (Kaveri, SmileArc, or Northlight data pack)   │
│    (b) Upload Bank Statement & Tally XML (with fuzzy regex parser)     │
│    (c) Connect via Account Aggregator (Setu / Anumati sandbox)         │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Implementation Strategy in Next.js 15+ App Router
- Route: `/` renders the high-craft marketing and onboarding entry when unauthenticated.
- Once authenticated via NextAuth / Google OAuth, redirects to `/dashboard/overview` ("Aaj Ka Hisaab").
- Removes the buried Page 8 in Streamlit, converting it into a clean, modern first-run modal or drawer.
