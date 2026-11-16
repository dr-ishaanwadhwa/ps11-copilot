# Subsystem Specification: Dynamic Forecast Simulation & Plain-Language Guidance

> **Subsystem:** Cashflow Forecasting Engine & UI  
> **Date:** 15 November 2026  
> **Status:** APPROVED FOR IMPLEMENTATION  
> **Origin:** Team Demo Feedback (`ijt-mtka-pgm`)  

---

## 1. Context & Feedback

In the team review on 15 November 2026, Alok Ae highlighted two major friction points in the Forecast page:
1. **Lack of User Comprehensibility:** 
   > *"If I don't know shit and I open the forecast graph, I'm not able to understand graph."*
2. **Static Retrospective Data vs. Dynamic Forward Forecast:** 
   > *"Also forecast it's not exactly giving you the forecast, you know. It's just giving you the data set from July to August September 30th 90 days. It's not giving you forecast of the upcoming 90 days... Forecast from date user set it should show."*

Dr. Ishaan Wadhwa outlined the strategic response:
> *"What I'll do is I'll add a small description underneath that that is easy to understand for whichever user it is... we have to create a dynamic one first of all, timeline begin set, and toggles for simulation."*

---

## 2. Technical Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                   DYNAMIC FORECAST ARCHITECTURE                        │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Simulation Anchor Selector                                          │
│    User selects "Forecast As Of Date" (Defaults to latest statement)   │
├────────────────────────────────────────────────────────────────────────┤
│ 2. Monte Carlo / TimesFM Engine                                        │
│    Simulates 1,000 daily paths forward: P10 (stress), P50, P90         │
├────────────────────────────────────────────────────────────────────────┤
│ 3. Plain-Language Solvency Card ("What this means for your money")     │
│    "Your lowest cash dip will be ₹2.1L on 14 October due to GST + Rent.│
│     You do not need to inject personal capital if 3 key debtors pay."  │
├────────────────────────────────────────────────────────────────────────┤
│ 4. Interactive Simulation Levers                                       │
│    [Toggle] What if top debtor pays 15 days late?                      │
│    [Toggle] What if GST payment is deferred to the 25th?               │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.1 The Plain-Language Executive Summary Card
Directly below the interactive Monte Carlo fan chart, render a dedicated card:
- **Header:** "What This Forecast Means For You" / "आपके पैसे की स्थिति का सारांश"
- **Key Metrics Highlighted:**
  - **Lowest Point (Trough):** Projected lowest bank balance in the next 90 days.
  - **Date of Maximum Pressure:** Exact calendar date when liquidity is tightest.
  - **Overdraft Breach Risk:** Probability of exceeding sanctioned Cash Credit limit.
  - **Primary Action Lever:** The single customer follow-up or payment rescheduling that resolves the trough.

### 2.2 Dynamic Timeline Anchor
- Allow the user to select an anchor date $T_0$.
- Pre-cutoff transactions condition the customer payment delay distributions ($P(\text{delay} \mid \text{delay} > \text{age})$).
- The forward simulation projects $T_0 \to T_0 + 90\text{ days}$.

### 2.3 Interactive Scenario Toggles
Provide 3 click-to-simulate toggles:
1. **Debtor Delay Shock:** Adds +15 days delay to the 3 largest outstanding invoices.
2. **Vendor Acceleration:** Vendor bills due within 30 days must be paid within 7 days.
3. **Cash Sales Surge:** Models a 15% increase in counter cash receipts (e.g. festive season).
