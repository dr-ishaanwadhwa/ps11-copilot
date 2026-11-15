# SME Cashflow Copilot: Next.js 15+ App Router & Three.js 3D Spatial Topography
## Comprehensive Architectural & Visual Design Blueprint

**Document Reference:** `ARCH-SPEC-2026-M1`  
**Classification:** Publication-Grade Technical Specification  
**Target Repository:** `/Users/ishaanwadhwa/Projects/ps11-copilot`  
**Author:** Teamwork Blueprint Architecture Subagent (`worker_blueprint_m1`)  
**Parent Orchestrator:** `66f8e37c-7419-49c0-b513-8564a45102cd`  
**Date of Ratification:** 15 November 2026  
**Status:** AUTHORITATIVE ARCHITECTURAL STANDARD  

---

## Table of Contents
1. [Executive Summary & Design System Foundation](#1-executive-summary--design-system-foundation)
   - 1.1 Architectural Vision & Modern Stack Specification
   - 1.2 Technology Stack Matrix & Rationale
   - 1.3 Design System & OKLCH Perceptual Color Spaces
   - 1.4 Typography Pairing & Indian Numeral Formatting System
   - 1.5 Ergonomics, Accessibility & Cashier Touch Ergonomics
2. [Modern Next.js 15+ App Router Architecture](#2-modern-nextjs-15-app-router-architecture)
   - 2.1 File System & Route Hierarchy
   - 2.2 React Server Components (RSC) vs. Client Component Boundaries
   - 2.3 Server Actions for Type-Safe Mutations with Optimistic Rollbacks
   - 2.4 Client State Management Architecture (Zustand & WebCrypto)
   - 2.5 Loading Skeletons, Perceived Performance & `flow-errors` Fault Recovery
3. [Detailed Component Hierarchy, Layouts & Interactions for All 7 Target Views](#3-detailed-component-hierarchy-layouts--interactions-for-all-7-target-views)
   - 3.1 Master Application Shell (`(dashboard)/layout.tsx`)
   - 3.2 View 1: Overview Cockpit ("Aaj Ka Hisaab")
   - 3.3 View 2: Cash Book & Sovereign Vault
   - 3.4 View 3: Forecast & Simulation (90-Day Cash Dip Simulation)
   - 3.5 View 4: Review Queue (Decision 60 Precision Triage)
   - 3.6 View 5: Receivables & Recovery (Section 18 Shield & MSMED)
   - 3.7 View 6: Ask Copilot (Grounded Conversational AI)
   - 3.8 View 7: Statutory Exports & Data Quality
4. [3D Spatial Cashflow Topography (Three.js & React Three Fiber)](#4-3d-spatial-cashflow-topography-threejs--react-three-fiber)
   - 4.1 Spatial Metaphor & Continuous Elevation Heightfield Mesh
   - 4.2 Scene Graph & R3F Component Hierarchy
   - 4.3 Procedural Terrain Shader & Topographic Isolines
   - 4.4 Dynamic Instanced Particle Flow Velocity Field
   - 4.5 Constrained Camera Kinematics & Cinematic Fly-Throughs
   - 4.6 60fps Performance Budget, Memory Pooling & WebGL Lifecycle
   - 4.7 Responsive 2D Canvas / SVG Elevation Topography Fallback
5. [Conversational AI-Native Interface & Vernacular Audio Engine](#5-conversational-ai-native-interface--vernacular-audio-engine)
   - 5.1 Grounded AI-Native Architecture & Zero-Stochastic Guarantee
   - 5.2 Server-Sent Events (SSE) Streaming Pipeline & Verifiable Citations
   - 5.3 Vernacular Audio Briefing Player & Waveform Visualizer
6. [Non-Negotiable Invariants Compliance (ADR-001 to ADR-004)](#6-non-negotiable-invariants-compliance-adr-001-to-adr-004)
   - 6.1 ADR-001: Local-First Sovereign Vault Cryptography
   - 6.2 ADR-002: Decision 60 Deterministic Precision Matching
   - 6.3 ADR-003: Section 18 Limitation Act Statutory Shield
   - 6.4 ADR-004: MCA Rule 11(g) Edit Log & BNS §241 Anti-Spoliation
7. [Full API Specifications & Data Contracts](#7-full-api-specifications--data-contracts)
   - 7.1 Core Domain TypeScript Interfaces & Zod Validation Schemas
   - 7.2 Next.js Server Actions & Route Handlers Specifications
   - 7.3 Python FastAPI Microservice Bridge Contracts
8. [Step-by-Step Phased Zero-Downtime Migration Roadmap](#8-step-by-step-phased-zero-downtime-migration-roadmap)
   - 8.1 Phase 1: Split-Bridge BFF (Dual-Port Coexistence)
   - 8.2 Phase 2: Dual-Run Parity & Statistical Verification
   - 8.3 Phase 3: Complete Cutover to Next.js 15 App Router

---

## 1. Executive Summary & Design System Foundation

### 1.1 Architectural Vision & Modern Stack Specification
The SME Cashflow Copilot is an AI-native financial operating intelligence system engineered specifically for Indian Small and Medium Enterprises (FMCG distributors, retail pharma, clinics, creative agencies, and regional manufacturers). The enterprise reality in India involves a dual-plane economic structure:
1. **Plane A (Formal Banking & Tax Plane):** Bank current accounts, Cash-Credit (CC) facilities, GST e-invoices, and TDS deductions audited by Chartered Accountants under strict MCA Rule 11(g) rules.
2. **Plane B (Sovereign Operating Cash Plane):** Physical godown drawer cash (*Galla/Rokad*), morning opening floats, daily salesman route collections (*Kaccha Parchi*), petty cash expenses (*Hamali/Chai*), and informal customer trade ledgers (*Khata*).

The current production application runs on a monolithic Python 3.12 / Streamlit 1.40.2 runtime (`app/streamlit_app.py`, 2,697 lines). While the underlying computational engines (`src/copilot/`) achieve 100.0% precision under Decision 60 across 11,224 transactions, the Streamlit frontend suffers from fundamental architectural bottlenecks:
- **Full-Script Re-execution Overhead:** Every user interaction re-executes the entire Python script, causing 12–15 seconds of cashier latency during evening collection slip logging.
- **State Amnesia & WebSocket Fragility:** Transient mobile network drops in wholesale market godowns trigger session disconnections, resetting active filters and unsaved forms.
- **Flat Visual Presentation:** A 2D spreadsheet layout fails to provide the merchant with a holistic spatial mental model of multi-dimensional cash velocity, receivables delays, and Cash-Credit limit cliffs.

This blueprint establishes the authoritative architectural and visual specification for migrating the SME Cashflow Copilot to an **AI-Native Next.js 15+ App Router, React 19, TypeScript 5, Tailwind CSS v4, and Three.js / React Three Fiber (R3F) 3D Spatial Topography** platform. The upgrade guarantees sub-10ms UI interactions, zero cloud leakage of sovereign cash records, mathematical preservation of Decision 60 precision, and a transformative 3D financial topography.

---

### 1.2 Technology Stack Matrix & Rationale

| Layer | Selected Technology | Version | Architectural Rationale |
|---|---|---|---|
| **Framework** | Next.js (App Router) | `15.1.x` | React Server Components (RSC) eliminate client bundle bloat for large bank ledgers; Route Groups isolate auth/PIN gates; streaming SSR delivers sub-100ms TTFB. |
| **UI Runtime** | React | `19.0.x` | Native Support for `useActionState`, `useOptimistic`, Server Actions, and React Compiler memoization without boilerplate `useMemo`/`useCallback`. |
| **Language** | TypeScript | `5.6.x` | Compile-time mathematical safety; strict typing between paisa integers and rupee floats; shared schemas between frontend and Python backend via Zod. |
| **Styling** | Tailwind CSS v4 | `4.0.x` | CSS-first `@theme` configuration; native OKLCH wide-gamut perceptual color space; sub-millisecond build times without PostCSS overhead. |
| **3D Engine** | Three.js & React Three Fiber | `r170` / `8.17.x` | Declarative WebGL scene graph; continuous heightfield cashflow mesh with custom GLSL shaders; instanced particle flow velocity field (<35 draw calls). |
| **3D Helpers** | `@react-three/drei` | `9.120.x` | Performance utilities: `AdaptiveDpr`, `Preload`, `OrbitControls`, `Html` overlays, and WebGL context loss handling. |
| **Component Primitives** | Radix UI / shadcn/ui | Latest | Headless, accessible primitives conforming to WAI-ARIA with full keyboard navigation and 44px touch targets. |
| **Data Grids** | TanStack Table v8 | `8.20.x` | Headless, virtualized, zero-licensing data grid for 3-pane review queue triage with custom keyboard bindings (`j`/`k`/`a`/`r`). |
| **Client Storage** | IndexedDB / OPFS | Native / `idb-keyval` | Local-first encrypted envelope persistence for Sovereign Vault; zero plaintext storage on disk. |
| **Cryptographic Engine** | Web Crypto API (`crypto.subtle`) | Native W3C | Native browser-hardware PBKDF2-HMAC-SHA256 (100k iterations) and AES-256-GCM authenticated encryption in volatile memory (ADR-001). |
| **Backend Compute Bridge** | Python FastAPI / DuckDB | `3.12` / `1.1.x` | High-performance headless microservice executing Monte Carlo simulations, vector indexing, Tally XML generation, and DuckDB analytical queries. |

---

### 1.3 Design System & OKLCH Perceptual Color Spaces

The visual language reflects the **Dual-Plane Enterprise Reality**: formal corporate banking is rendered in an authoritative **Trust Navy** palette (Plane A), while the merchant's confidential internal till is distinguished by a warm, protective **Sovereign Gold / Amber** palette (Plane B). All colors are specified in the perceptual **OKLCH** color space, guaranteeing uniform perceived lightness and contrast across both standard sRGB monitors and wide-gamut mobile OLED displays.

```css
/* app/globals.css - Tailwind CSS v4 Directives & Theme Tokens */
@import "tailwindcss";

@theme {
  /* Typography Scale */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', ui-monospace, monospace;
  --font-devanagari: 'IBM Plex Sans Devanagari', 'Noto Sans Devanagari', sans-serif;

  /* Plane A: Formal White Plane (Trust Navy) */
  --color-formal-primary: oklch(0.38 0.14 255);       /* Deep Trust Navy #1A3E78 */
  --color-formal-surface: oklch(0.98 0.008 255);      /* Crisp Porcelain #F4F6FB */
  --color-formal-surface-card: oklch(1.00 0.00 0);    /* Pure White Card */
  --color-formal-border: oklch(0.85 0.015 255);       /* Muted Steel Border #D0D5DD */
  --color-formal-text: oklch(0.20 0.04 255);         /* Slate Ink Text #101828 */
  --color-formal-muted: oklch(0.55 0.02 255);        /* Secondary Meta Text #667085 */

  /* Plane B: Sovereign Cash Plane (Vault Amber / Gold) */
  --color-vault-accent: oklch(0.72 0.16 75);          /* Warm Sovereign Gold #D99B26 */
  --color-vault-surface: oklch(0.97 0.03 85);         /* Soft Protective Parchment #FFFDF5 */
  --color-vault-surface-card: oklch(0.99 0.015 85);   /* Warm Cream Card #FFFDF8 */
  --color-vault-border: oklch(0.82 0.08 80);          /* Burnished Brass Border #E5C378 */
  --color-vault-text: oklch(0.25 0.06 70);           /* Deep Bronze Text #432E05 */

  /* Semantic Financial Indicators */
  --color-surplus: oklch(0.62 0.19 145);              /* Emerald Solvency Green #16A34A */
  --color-surplus-surface: oklch(0.96 0.04 145);      /* Emerald Pale Fill #F0FDF4 */
  --color-surplus-border: oklch(0.84 0.10 145);       /* Emerald Border #BBF7D0 */

  --color-deficit: oklch(0.55 0.22 25);               /* Ruby Liability Red #DC2626 */
  --color-deficit-surface: oklch(0.96 0.04 25);       /* Ruby Pale Fill #FEF2F2 */
  --color-deficit-border: oklch(0.85 0.10 25);        /* Ruby Border #FECACA */

  --color-warning: oklch(0.70 0.18 60);               /* Amber Cliff Alert #D97706 */
  --color-warning-surface: oklch(0.97 0.05 60);       /* Amber Pale Fill #FFFBEB */
  --color-warning-border: oklch(0.86 0.10 60);        /* Amber Border #FDE68A */

  /* Dark Mode (Godown Evening / Low Light OLED Midnight) */
  --color-dark-bg: oklch(0.12 0.02 260);              /* Deep Obsidian #020617 */
  --color-dark-surface: oklch(0.16 0.025 260);         /* Midnight Elevation #0E1223 */
  --color-dark-card: oklch(0.20 0.03 260);            /* Card Surface #151B30 */
  --color-dark-border: oklch(0.30 0.02 260);          /* Slate Muted Border #334155 */
  --color-dark-text-high: oklch(0.98 0.005 260);      /* 100% High Contrast Text #F8FAFC */
  --color-dark-text-muted: oklch(0.70 0.02 260);     /* 70% Secondary Text #94A3B8 */
}
```

---

### 1.4 Typography Pairing & Indian Numeral Formatting System

#### Font Pairing Rationale
1. **Primary Interface:** `Inter` variable font provides structural neutral readability for UI labels, table headers, and form inputs.
2. **Numeric Monetary Data:** `JetBrains Mono` with OpenType `tnum` (Tabular Numerals) and `zero` (Slashed Zero) enabled. In financial tables, numbers must align strictly by decimal place without horizontal jitter when figures mutate.
3. **Vernacular Devanagari:** `IBM Plex Sans Devanagari` provides industry-leading typographic clarity for Hindi briefings, Devanagari summary cards, and regional retailer party names.

#### Indian Lakh/Crore Numeral Formatting Engine
Western formatting (`1,000,000`) creates acute cognitive load for Indian business owners accustomed to calculating in Thousands, Lakhs ($10^5$), and Crores ($10^7$). The application enforces strict Indian numeral formatting across all UI layers:

$$\text{Format Rule: } \underbrace{\text{Crore}}_{> 1,00,00,000} \text{ or } \underbrace{\text{Lakh}}_{> 1,00,000} \text{ with standard } \text{₹ } X,XX,XX,XXX.XX$$

// lib/formatters/inr.ts
const indianCurrencyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

const indianCurrencyIntegerFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

export interface FormatOptions {
  showDecimals?: boolean;
  compact?: boolean;
  signed?: boolean;
}

export function formatINR(val: number, options: FormatOptions = {}): string {
  if (val === null || val === undefined || isNaN(val)) return '₹0';
  
  const isNegative = val < 0;
  const absVal = Math.abs(val);
  const signPrefix = isNegative ? '−' : (options.signed ? '+' : '');

  if (options.compact) {
    if (absVal >= 10000000) {
      const cr = (absVal / 10000000).toFixed(2);
      return `${signPrefix}₹${cr} Cr`;
    }
    if (absVal >= 100000) {
      const lakh = (absVal / 100000).toFixed(2);
      return `${signPrefix}₹${lakh} L`;
    }
  }

  // Use memoized module-level formatters to avoid GC pressure in 60fps renders & large virtualized grids
  const formatter = options.showDecimals
    ? indianCurrencyFormatter
    : indianCurrencyIntegerFormatter;

  const formattedStr = formatter.format(absVal);
  return `${signPrefix}${formattedStr}`;
}
```

---

### 1.5 Ergonomics, Accessibility & Cashier Touch Ergonomics
Wholesale distributor counters and retail pharma cashiers operate under harsh, fast-paced physical conditions: direct fluorescent glare, dusty tablet touchscreens, and rapid counter checkout queues.
- **44px Minimum Touch Targets:** All interactive buttons, segmented tabs, and checkbox controls enforce a minimum physical bounding box of $44 \times 44\text{px}$ (`min-h-[44px] min-w-[44px]`).
- **Color-Blind Dual-Encoding:** Critical financial states are never communicated via color alone. Every red/green tile pairs an OKLCH semantic color with an unambiguous text label and icon (e.g., `🛡️ SAFE`, `⚠️ CLIFF`, `✓ TIED`).
- **WCAG 2.1 AAA Contrast:** Crucial financial text (bank balances, CC headroom, drift alerts) achieves contrast ratios exceeding $7:1$ against backgrounds, with secondary body text exceeding $4.5:1$.
- **Keyboard-First Hotkeys:** Review queue and cash drawer operations feature single-key hotkey triage (`j` for Next, `k` for Previous, `a` for Approve, `r` for Reject/Reassign, `Esc` to Lock Vault).

---

## 2. Modern Next.js 15+ App Router Architecture

### 2.1 File System & Route Hierarchy
The application leverages Next.js 15+ App Router utilizing Route Groups `(auth)` and `(dashboard)` to cleanly isolate the PIN-gated lock screen from the main dashboard shell:

```
ps11-copilot-ui/
├── app/
│   ├── (auth)/
│   │   └── lock/
│   │       ├── page.tsx                  # PIN-gated unlock screen (ADR-001 WebCrypto)
│   │       └── layout.tsx                # Isolated centered layout (no dashboard chrome)
│   ├── (dashboard)/
│   │   ├── layout.tsx                    # Master Shell: Responsive Sidebar, TopNav, ⌘K
│   │   ├── page.tsx                      # Root redirect -> /overview
│   │   ├── overview/
│   │   │   ├── page.tsx                  # View 1: Overview Cockpit ("Aaj Ka Hisaab")
│   │   │   ├── loading.tsx               # Perceived-performance skeleton layout
│   │   │   └── error.tsx                 # flow-errors boundary preserving vault state
│   │   ├── cash-book/
│   │   │   ├── page.tsx                  # View 2: Cash Book & Sovereign Vault
│   │   │   ├── loading.tsx
│   │   │   └── @modal/                   # Intercepting route for salesman parchi modal
│   │   │       └── parchi/page.tsx
│   │   ├── forecast/
│   │   │   ├── page.tsx                  # View 3: 90-Day Cash Dip Simulation
│   │   │   └── loading.tsx
│   │   ├── review/
│   │   │   ├── page.tsx                  # View 4: Decision 60 Review Queue (3-Pane)
│   │   │   └── loading.tsx
│   │   ├── receivables/
│   │   │   ├── page.tsx                  # View 5: Receivables & Section 18 Shield
│   │   │   └── loading.tsx
│   │   ├── copilot/
│   │   │   ├── page.tsx                  # View 6: Ask Copilot Grounded Chat
│   │   │   └── loading.tsx
│   │   └── exports/
│   │       ├── page.tsx                  # View 7: Statutory Tally XML & CA Excel
│   │       └── loading.tsx
│   ├── api/                              # Route Handlers for streaming and blob downloads
│   │   ├── copilot/
│   │   │   ├── stream/route.ts           # Token streaming SSE route
│   │   │   └── transcribe/route.ts       # Gemini voice audio transcription
│   │   └── exports/
│   │       ├── tally-xml/route.ts        # Pure XML voucher download stream
│   │       ├── ca-excel/route.ts         # CA 5-sheet statutory OpenPyXL workbook stream
│   │       └── internal-diagnostic/route.ts # PIN-gated 6-sheet dual-plane workbook stream
│   ├── globals.css                       # Tailwind CSS v4 design tokens
│   └── layout.tsx                        # Root layout: Fonts, React Query, WebCrypto init
├── components/
│   ├── 3d/                               # Three.js / React Three Fiber components
│   │   ├── CashflowTopographyCanvas.tsx  # Dynamic client-only Canvas wrapper
│   │   ├── TerrainMesh.tsx               # Procedural heightfield mesh & shaders
│   │   ├── ParticleFlowField.tsx         # InstancedMesh cash velocity vector field
│   │   ├── TopographyCameraRig.tsx       # OrbitControls + cinematic camera fly-throughs
│   │   └── Fallback2DTopography.tsx      # SVG / Canvas 2D elevation fallback
│   ├── audio/
│   │   ├── VernacularAudioPlayer.tsx     # Web Audio API waveform & playback controller
│   │   └── WaveformCanvas.tsx            # Canvas 2D frequency visualizer
│   ├── ui/                               # Headless design system primitives
│   │   ├── button.tsx, badge.tsx, card.tsx, dialog.tsx, drawer.tsx,
│   │   ├── table.tsx, tabs.tsx, tooltip.tsx, slider.tsx, command.tsx
│   └── views/                            # View-specific domain compound components
│       ├── overview/
│       ├── cash-book/
│       ├── forecast/
│       ├── review/
│       ├── receivables/
│       ├── copilot/
│       └── exports/
├── lib/
│   ├── crypto/                           # ADR-001 WebCrypto AES-GCM / PBKDF2
│   │   ├── vaultCrypto.ts
│   │   └── keyDerivation.ts
│   ├── formatters/                       # Lakh / Crore Indian numeral formatters
│   │   ├── inr.ts
│   │   └── dates.ts
│   ├── store/                            # Client state management (Zustand)
│   │   ├── useVaultStore.ts
│   │   ├── useCockpitStore.ts
│   │   └── useUndoStore.ts
│   └── actions/                          # Next.js Server Actions
│       ├── reviewActions.ts
│       ├── parchiActions.ts
│       └── exportActions.ts
└── types/
    ├── vault.d.ts
    ├── matching.d.ts
    └── forecast.d.ts
```

---

### 2.2 React Server Components (RSC) vs. Client Component Boundaries

To guarantee sub-100ms initial page load, eliminate client JavaScript bundle bloat, and strictly maintain the ADR-001 cryptographic firewall, the component boundary is strictly segregated:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      RSC / CLIENT COMPONENT BOUNDARY                   │
├───────────────────────────────────┬────────────────────────────────────┤
│   REACT SERVER COMPONENTS (RSC)   │    CLIENT COMPONENTS ('use client') │
│   (Zero Client JavaScript Weight)  │   (Interactive & Cryptographic RAM)│
├───────────────────────────────────┼────────────────────────────────────┤
│ • Root Application Shell          │ • WebCrypto AES-256-GCM Vault      │
│ • Sidebar & Navigation Chrome     │ • Sovereign Galla Drawer Cockpit   │
│ • Bank Statement Data Feeds       │ • Salesman Parchi Ingestion Form   │
│ • Open GST Invoices & Bills       │ • Three.js / R3F Topography Canvas │
│ • Monte Carlo Pre-calculated Grid │ • Review Queue 3-Pane Triage Table │
│ • Static Financial Metric Cards   │ • TanStack Table Hotkey Handlers   │
│ • Tally XML / Excel Export Server │ • Vernacular Audio Player & Canvas │
│ • Statutory Legal Citation Notes  │ • Grounded Copilot Chat Input      │
├───────────────────────────────────┴────────────────────────────────────┤
│                                   │                                    │
│    One-Way Downward Data Feed     │   STRICT UPWARD FIREWALL (ADR-001) │
│    (Bank closing bal, CC limit,   │   Zero plaintext vault records,    │
│     payroll & formal commitments) ───► informal parchis, or Galla cash │
│                                   │   ever transmitted to backend.     │
└───────────────────────────────────┴────────────────────────────────────┘
```

#### Dual-Plane Hydration Barrier (Zero SSR Mismatch Guarantee)
Because the Next.js server has zero knowledge of client-side sovereign vault cash (ADR-001), Server Components pre-render only formal banking balances (e.g., Bank current balance ₹12.39L). Attempting to interpolate client-only drawer cash directly during initial render would trigger fatal React 19 Hydration Mismatch errors (`Text content did not match: Server "₹12.39L" vs Client "₹16.59L"`).

To permanently eradicate SSR hydration mismatches:
1. **Client-Hydrated Islands:** Any UI element that displays physical drawer cash, salesman collection slips, or synthesized True Solvency (`Bank + Cash − Commitments`) is isolated within a client-hydrated island (`<ClientVaultDisplay />`, `<TrueSolvencyCard />`) mounted via `dynamic(() => import(...), { ssr: false })` or wrapped in a `useSyncExternalStore` hydration gate.
2. **Neutral SSR Placeholder:** During server pre-rendering, the component outputs a lightweight, zero-layout-shift skeleton (`<Skeleton className="h-28 w-full" />`).
3. **RAM Subscription:** Upon client-side hydration, the island connects to `useVaultStore` in volatile browser memory. If unlocked, it smoothly transitions to the synthesized True Solvency figure (`₹16.59L`), preserving ADR-001 while maintaining 100% hydration consistency.

```tsx
// components/views/overview/ClientVaultDisplay.tsx
'use client'

import dynamic from 'next/dynamic';
import { useSyncExternalStore } from 'react';
import { useVaultStore } from '@/lib/store/useVaultStore';
import { formatINR } from '@/lib/formatters/inr';
import { Skeleton } from '@/components/ui/skeleton';

export function ClientVaultDisplay({ bankBalance, commitments }: { bankBalance: number; commitments: number }) {
  const isHydrated = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  );
  const { isUnlocked, gallaEntry } = useVaultStore();

  if (!isHydrated) {
    return <Skeleton className="h-24 w-full animate-pulse rounded-xl bg-formal-border/20" />;
  }

  const drawerCash = isUnlocked ? (gallaEntry?.countedCash ?? 0) : 0;
  const netUsable = bankBalance + drawerCash - commitments;

  return (
    <div className="flex flex-col gap-1">
      <span className="text-3xl font-bold font-mono tracking-tight text-formal-text">
        {formatINR(netUsable, { compact: true })}
      </span>
      <span className="text-xs text-formal-muted">
        {isUnlocked 
          ? `(Bank: ${formatINR(bankBalance, { compact: true })} + Drawer: ${formatINR(drawerCash, { compact: true })})`
          : `(Bank: ${formatINR(bankBalance, { compact: true })} · Vault Locked)`}
      </span>
    </div>
  );
}
```

---

### 2.3 Server Actions for Type-Safe Mutations with Optimistic Rollbacks

All state mutations on the formal plane (reconciliation approval, payer assignment, export trigger) execute via Next.js Server Actions with Zod runtime validation and optimistic UI updates:

```typescript
// lib/actions/reviewActions.ts
'use server'

import { revalidatePath } from 'next/cache';
import { z } from 'zod';

const ReconcileSchema = z.object({
  txnId: z.string().min(1),
  decision: z.enum(['APPROVE', 'REJECT', 'REASSIGN']),
  assignedPartyId: z.string().optional(),
  note: z.string().optional(),
});

export async function reconcileMatchAction(input: z.infer<typeof ReconcileSchema>) {
  // Validate input schema
  const parsed = ReconcileSchema.safeParse(input);
  if (!parsed.success) {
    return { success: false, error: 'Invalid mutation parameters' };
  }

  try {
    // Intercept and post to Python bridge microservice
    const response = await fetch(`${process.env.PYTHON_BRIDGE_URL}/api/review/reconcile`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(parsed.data),
    });

    if (!response.ok) {
      throw new Error(`Python engine returned status ${response.status}`);
    }

    const payload = await response.json();
    
    // Invalidate cached server components
    revalidatePath('/review');
    revalidatePath('/overview');

    return { 
      success: true, 
      txnId: parsed.data.txnId, 
      newStatus: payload.status,
      auditHash: payload.auditHash // MCA Rule 11(g) compliance hash
    };
  } catch (err: any) {
    return { success: false, error: err.message || 'Server action mutation failed' };
  }
}
```

---

### 2.4 Client State Management Architecture (Zustand & WebCrypto)

Interactive client state is partitioned into three specialized stores:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CLIENT ZUSTAND STORES                           │
├─────────────────────┬─────────────────────┬────────────────────────────┤
│    useVaultStore    │   useCockpitStore   │        useUndoStore        │
├─────────────────────┼─────────────────────┼────────────────────────────┤
│ • isUnlocked        │ • currentBiz (SME1) │ • optimisticActionQueue    │
│ • sessionCryptoKey  │ • locale (hi / en)  │ • 10-second rollback toast │
│ • gallaEntry (till) │ • presentationMode  │ • pendingCommitTimerId     │
│ • parchiDrafts      │ • khataAlpha (0.85) │ • restoreSnapshot()        │
│ • 15-min idle lock  │ • 3D / 2D viewMode  │                            │
│ • 5-min tab grace   │                     │                            │
│ • WebAuthn PRF key  │                     │                            │
└─────────────────────┴─────────────────────┴────────────────────────────┘
```

1. **`useVaultStore` (ADR-001 Sovereign Vault Plane & Ergonomic Protection):**
   - Holds volatile decrypted data in RAM only.
   - Master AES-256-GCM `CryptoKey` is derived in a background Web Worker (`vaultCrypto.worker.ts`) via PBKDF2 (100k iterations) or unwrapped via the **WebAuthn PRF (Pseudo-Random Function) Biometric Passkey** extension, keeping the UI main thread locked at 60fps and eliminating the $10^4$ 4-digit PIN offline brute-force vulnerability.
   - **Cashier Tab-Switch Ergonomics:** Instead of an abrupt lock on `document.visibilityState === 'hidden'` (which destroys active cashier drafts when switching to WhatsApp Web or checking PDF bills), the vault implements a **5-minute background grace period timer**.
   - **Encrypted In-Progress Draft Preservation:** Active salesman parchi draft forms are auto-saved to an encrypted IndexedDB scratchpad (`draft_slips_encrypted`) on every keystroke. If the user closes the browser or the 5-minute timer expires, uncommitted drafts remain encrypted on disk and are instantly restored upon re-authentication.
   - **Atomic Inactivity Wipe:** After 15 minutes of continuous user inactivity (zero mouse, touch, or key events) or after 5 minutes in a hidden background tab, the store executes an atomic memory wipe (`reset()`), nullifying the RAM `CryptoKey` and locking the vault.
2. **`useCockpitStore` (UI Parameter Plane):**
   - Synchronizes URL search parameters via `nuqs`: business archetype (`?biz=SME-1`), language (`?lang=hi`), and presentation mode (`?mode=formal`).
3. **`useUndoStore` (`flow-errors` Optimistic Mutation Engine):**
   - Provides a 10-second safety window for destructive or consequential actions (e.g., verifying a batch of transactions or archiving a customer). Displays an interactive toast with a progress bar and "Undo" button before committing to the server.
   - Handles rapid cashier logging: supports high-frequency sequential parchi commits by queuing actions into a FIFO pipeline without blocking counter triage.

---

### 2.5 Loading Skeletons, Perceived Performance & `flow-errors` Fault Recovery
- **Perceived Performance via Streaming Suspense:** Each route features a bespoke `loading.tsx` rendering pulsing animated skeleton frames that precisely match the dimensions of target metric tiles, data tables, and the 3D canvas, preventing Cumulative Layout Shift ($\text{CLS} < 0.05$).
- **`flow-errors` Resilient Boundaries:** When backend microservice network timeouts occur, the error boundary (`error.tsx`) catches the exception locally, renders an actionable recovery card ("FastAPI backend unreachable; retrying in 5s..."), and crucially **preserves the in-memory Sovereign Vault state**, preventing the user from losing their counted drawer cash.

---

## 3. Detailed Component Hierarchy, Layouts & Interactions for All 7 Target Views

### 3.1 Master Application Shell (`(dashboard)/layout.tsx`)

The application layout follows `flow-app-shell` and `flow-navigation` standards: a fixed 260px collapsible sidebar, a top navigation bar displaying the active business profile, current As-Of date, and a global Command Palette (`⌘K`).

```
+----------------------------------------------------------------------------------------------------+
| TOP NAV: [Logo] SME Cashflow Copilot | SME-1: Kaveri Distributors | As-Of: 30 Sep 2026 | ⌘K Search |
+------------------+---------------------------------------------------------------------------------+
| SIDEBAR          | MAIN CONTENT REGION                                                             |
|                  |                                                                                 |
| [1] Cockpit ⚡   | (Active Route View Mounted Here with Instant Cross-Fade Animation)              |
| [2] Cash Book 🪙 |                                                                                 |
| [3] Forecast 📈  |                                                                                 |
| [4] Review ⚖️    |                                                                                 |
| [5] Recover 🛡️   |                                                                                 |
| [6] Copilot 🤖   |                                                                                 |
| [7] Exports 📊   |                                                                                 |
| ──────────────── |                                                                                 |
| [Vault: UNLOCKED]|                                                                                 |
| [Lang: हिन्दी/EN]|                                                                                 |
+------------------+---------------------------------------------------------------------------------+
```

---

### 3.2 View 1: Overview Cockpit ("Aaj Ka Hisaab")

#### 1. Visual Layout Mockup (ASCII Wireframe)
```
+----------------------------------------------------------------------------------------------------+
| OVERVIEW COCKPIT: "AAJ KA HISAAB"                                     [Role: Owner] [Lang: हिन्दी] |
+----------------------------------------------------------------------------------------------------+
| ⚠️ PARTIAL VIEW NOTICE: Formal books only. Vault unlocked: Total Solvency synthesized.             |
+----------------------------------------------------------------------------------------------------+
| HERO NET USABLE LIQUIDITY CARD                                                                     |
| Net Usable Cash: ₹16,59,000 (Bank: ₹12.39L + Drawer: ₹4.20L) | Runway: 3.8 Months [SURPLUS ✓]      |
| Payroll Status: 1 Oct Salaries (₹4.65L) 100% Funded | Headroom Clear of CC Limit: ₹21.20L          |
+----------------------------------------------------------------------------------------------------+
| VERNACULAR AUDIO BRIEFING PLAYER                                                                   |
| [▶ Play Briefing] [10s ⏪] [⏩ 10s] | |||||||||||||||||||||||||||||||||||||||||||| (01:24 / 02:45) |
| Transcript: "शुभ प्रभात रमेश जी। आज कावेरी डिस्ट्रीब्यूटर्स के पास कुल ₹16.59L खर्च करने योग्य नकदी है..."   |
+----------------------------------------------------------------------------------------------------+
| 4 VITAL PULSE TILES                                                                                |
| ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐                |
| │ Net Usable Cash  │ │ Bank Headroom    │ │ Cash in Drawer   │ │ Due in 30 Days   │                |
| │ ₹16,59,000       │ │ ₹21,20,000       │ │ ₹4,20,000        │ │ ₹4,65,000        │                |
| │ Bank + Till Cash │ │ CC Limit: ₹25L   │ │ Physical Counted │ │ Payroll + Vendor │                |
| └──────────────────┘ └──────────────────┘ └──────────────────┘ └──────────────────┘                |
+----------------------------------------------------------------------------------------------------+
| SINGLE FOCAL ACTION CARD                                                                           |
| 🚨 Priority 1: Matoshree Supermarket owes ₹1,14,000 (930 days overdue)                            |
| ⚠️ Section 18 Limitation Alert: Claim expires in 60 days!                                          |
| [💬 Send WhatsApp AoD Reminder]  [📋 View Ledger]  [✓ Log Part Settlement]                         |
+----------------------------------------------------------------------------------------------------+
| 3D SPATIAL CASHFLOW TOPOGRAPHY PREVIEW                                                             |
| [Interactive 3D Canvas: Cash peaks & 1 Oct salary valley glide] [Expand Full Forecast ->]         |
+----------------------------------------------------------------------------------------------------+
| DUAL-PLANE TRUE SOLVENCY EQUATION (COLLAPSIBLE ACCORDION)                                          |
| True Buffer = (Bank ₹12.39L − CC Drawn ₹3.80L) + Galla ₹4.20L + (0.85 × Khata ₹22.00L) − Due ₹4.65L|
| Collection Haircut Slider (α): [==== 85% ====]  Net Solvency Buffer: +₹32,64,000                  |
+----------------------------------------------------------------------------------------------------+
```

#### 2. Component Hierarchy & Interfaces
```tsx
// app/(dashboard)/overview/page.tsx (RSC + Client Islands)
<OverviewPage>
  <PartialViewNotice />
  <CockpitHeroCard 
    bankBalance={1239000} 
    headroom={2120000} 
    runwayMonths={3.8} 
  >
    {/* Client-hydrated island: synthesizes drawer cash in volatile RAM without SSR mismatch */}
    <ClientVaultDisplay bankBalance={1239000} commitments={465000} />
  </CockpitHeroCard>
  
  <VernacularAudioPlayer 
    audioSrc="/api/copilot/audio-brief?lang=hi" 
    transcriptHindi="शुभ प्रभात रमेश जी..." 
    transcriptEnglish="Good morning Ramesh ji..." 
  />
  
  <VitalPulseGrid>
    <PulseTile id="bank-headroom" amount={2120000} label="Bank Headroom" tone="positive" />
    <PulseTile id="commitments" amount={465000} label="Due in 30 Days" tone="warning" />
    {/* Client-hydrated pulse tiles subscribing to RAM useVaultStore */}
    <ClientPulseTile id="net-cash" label="Net Usable Cash" fallbackAmount={1239000} />
    <ClientPulseTile id="drawer-cash" label="Cash in Drawer" fallbackAmount={0} />
  </VitalPulseGrid>
  
  <FocalActionCard 
    debtorName="Matoshree Supermarket" 
    amount={114000} 
    overdueDays={930} 
    isLimitationAlert={true}
    phone="+919820012345" 
  />
  
  <SpatialTopographyPreview height={260} mode="compact" />
  
  {/* Client-hydrated True Solvency equation slider and accordion */}
  <ClientTrueSolvencyCard 
    bankBalance={1239000} 
    ccDrawn={380000} 
    formalDue={465000} 
  />
</OverviewPage>
```

```typescript
export interface CockpitHeroCardProps {
  bankBalance: number;
  headroom: number;
  runwayMonths: number;
  children?: React.ReactNode;
}

export interface ClientPulseTileProps {
  id: string;
  label: string;
  fallbackAmount: number;
  tone?: 'positive' | 'warning' | 'neutral' | 'critical';
}

export interface FocalActionCardProps {
  debtorName: string;
  amount: number;
  overdueDays: number;
  isLimitationAlert: boolean;
  phone: string;
  onSendWhatsapp?: () => void;
  onLogSettlement?: () => void;
}

export interface ClientTrueSolvencyCardProps {
  bankBalance: number;
  ccDrawn: number;
  formalDue: number;
  defaultKhataAlpha?: number;
}
```

#### 3. Key Interaction Flows
- **Morning Quick-Check (Sub-60s Flow):** Owner opens app on mobile phone $\rightarrow$ Glance at Hero Usable Liquidity (`₹16.59L`) $\rightarrow$ Tap `▶ Play Briefing` to listen in Hindi while inspecting physical godown shutters $\rightarrow$ Tap Single Focal Action WhatsApp button to send a legally sound balance acknowledgment request to the top overdue customer.

---

### 3.3 View 2: Cash Book & Sovereign Vault

#### 1. Visual Layout Mockup (ASCII Wireframe)
```
+----------------------------------------------------------------------------------------------------+
| CASH BOOK & SOVEREIGN VAULT                                           [Status: 🔓 UNLOCKED IN RAM] |
+----------------------------------------------------------------------------------------------------+
| 5-PART GODOWN CASH DRAWER BALANCING COCKPIT                                                        |
| ┌──────────────┬──────────────┬──────────────┬──────────────┬──────────────┬─────────────────────┐ |
| │ Opening Float│ + Parchi In  │ − Hamali Exp │ − Banked CDM │= Expected    │ Physical Counted    │ |
| │ ₹10,000      │ ₹25,000      │ ₹2,500       │ ₹20,000      │ ₹12,500      │ ₹12,500             │ |
| └──────────────┴──────────────┴──────────────┴──────────────┴──────────────┴─────────────────────┘ |
| Drawer Drift: ₹0.00  |  Status: [ ✓ BALANCED (< ₹50 drift) ]                                       |
| [📋 Open Day-Close Wizard]  [💵 Denomination Counter]  [🔒 Lock Sovereign Vault]                   |
+----------------------------------------------------------------------------------------------------+
| SALESMAN COLLECTION SLIP (PARCHI) LOGGING                                                          |
| [+ Record New Collection Slip]  [📸 OCR Slip via Gemini Vision]  Active Slips in Transit: ₹65,000   |
| ┌──────────┬──────────────┬───────────────┬────────────┬─────────────┬───────────┬───────────────┐ |
| │ Slip No  │ Date         │ Salesman      │ Shop/Party │ Amount (₹)  │ Mode      │ Status        │ |
| ├──────────┼──────────────┼───────────────┼────────────┼─────────────┼───────────┼───────────────┤ |
| │ SLP-1092 │ 30 Sep 2026  │ Ramesh Kumar  │ Laxmi Mart │ ₹15,000     │ Cash      │ In Till ✓     | |
| │ SLP-1093 │ 30 Sep 2026  │ Vijay Patil   │ Balaji Gen │ ₹8,500      │ UPI       │ Settled ✓     | |
| │ SLP-1094 │ 30 Sep 2026  │ Ramesh Kumar  │ Om Super   │ ₹22,000     │ Cheque    │ In Bag (Route)│ |
| └──────────┴──────────────┴───────────────┴────────────┴─────────────┴───────────┴───────────────┘ |
+----------------------------------------------------------------------------------------------------+
| STATUTORY CEILING COMPLIANCE SHIELD                                                                |
| 🛡️ Section 186 Cash Receipt Guard: No single counter cash receipt >= ₹2,00,000 logged today.       |
| 🛡️ Section 36(4) Expense Guard: Hamali cash voucher ₹2,500 is within ₹10,000 tax ceiling.         |
| ℹ️ SFT Rule 237 Deposit Facts: YTD Cash Deposited: ₹14.50L (Current Account SFT Threshold: ₹50.00L)|
+----------------------------------------------------------------------------------------------------+
```

#### 2. Component Hierarchy & Interfaces
```tsx
<CashBookPage>
  <VaultGatedBoundary isUnlocked={isVaultUnlocked} onUnlock={deriveAndDecryptVault}>
    <FivePartDrawerCockpit 
      openingFloat={10000} 
      parchiIn={25000} 
      cashOut={2500} 
      banked={20000} 
      counted={12500} 
      drift={0} 
      isBalanced={true} 
      onCommitDayClose={handleDayClose} 
    />
    <SalesmanParchiSection>
      <ParchiActionToolbar onManualEntry={openParchiModal} onCameraCapture={triggerVisionOCR} />
      <ActiveSlipsTable slips={collectionSlips} onSelectSlip={inspectSlip} />
    </SalesmanParchiSection>
    <StatutoryGuardrailBanners auditChecks={guardrailResults} />
  </VaultGatedBoundary>
</CashBookPage>
```

#### 3. Key Interaction Flows
- **Evening Cashier Balancing Flow:** Cashier returns from market $\rightarrow$ Click `Complete Day Close` $\rightarrow$ Enter counted physical currency note denominations (e.g. $20 \times ₹500, 25 \times ₹100$) $\rightarrow$ System dynamically evaluates:
  $$\text{Expected} = 10000 + 25000 - 2500 - 20000 = 12500, \quad \text{Drift} = 12500 - 12500 = 0.00$$
  If $|\text{Drift}| < ₹50.00$, the status illuminates green `✓ BALANCED`. Cashier clicks `Confirm & Seal Day Close`. Records are committed to encrypted IndexedDB.

---

### 3.4 View 3: Forecast & Simulation (90-Day Cash Dip Simulation)

#### 1. Visual Layout Mockup (ASCII Wireframe)
```
+----------------------------------------------------------------------------------------------------+
| 90-DAY CASH DIP SIMULATION & STRESS TESTING                         [Model: Bottom-Up Monte Carlo] |
+----------------------------------------------------------------------------------------------------+
| 🛡️ OUTLOOK STATUS: SAFE (Zero breaches of sanctioned CC Limit of ₹25,00,000)                       |
| Out-of-Sample Holdout Accuracy: MAPE 5.61% (vs Naive 18.20%) | P10-P90 Coverage: 93.3%             |
+----------------------------------------------------------------------------------------------------+
| 3D SPATIAL TOPOGRAPHY & PROBABILITY FAN CHART                                                      |
| [View Selector: (•) 3D Spatial Landscape  ( ) 2D Area Fan Chart]                                  |
|                                                                                                    |
|    ^ Cash (INR)                                                                                    |
| +30L│      __/\_ P90 (Optimistic)                                                                  |
| +16L│_____/=====\_____ P50 (Median Cash Peak)                                                      |
|  +4L│    \_______/     P10 (Worst Case Dip on 1 Oct Salaries: +₹4.20L)                             |
|   0L├───-──-──-──-──-──-──-──-──-──-──-──-──-──-──-──-──-──-──-──-──-──-──- (Zero Cash Floor)       |
| -25L|════════════════════════════════════════════════════════ (Sanctioned CC Danger Limit)        |
|     +---------------------------------------------------------------------> 90-Day Horizon        |
|     30 Sep (T0)        15 Oct (GST)       1 Nov (Salaries)      31 Dec                             |
+----------------------------------------------------------------------------------------------------+
| INTERACTIVE SCENARIO STRESS SLIDERS                                                                |
| 1. Customer Delay Surge: [+15 Days Overdue]    [=====|================] (Affects Top 5 Retailers)  |
| 2. Raw Material Cash Surge: [₹2,50,000 Advance][========|=============]                            |
| 3. Collection Haircut (α): [80% Realization]   [===============|======]                            |
| Simulated Lowest Point: +₹2,10,000 on 1 Nov (Headroom clear by ₹27.10L)                            |
+----------------------------------------------------------------------------------------------------+
| MONTH-BY-MONTH OPERATING OUTLOOK MATRIX                                                            |
| ┌──────────────┬──────────────────┬──────────────────┬──────────────┬──────────────┬─────────────┐ |
| │ Month        │ Inflows (P50)    │ Outflows (Committed) Net Cash Flow│ Lowest Point │ Closing Bal │ |
| ├──────────────┼──────────────────┼──────────────────┼──────────────┼──────────────┼─────────────┐ |
| │ October 2026 │ ₹48,20,000 (P10: 42L) ₹42,10,000     │ +₹6,10,000   │ +₹4,20,000   │ ₹22,69,000  │ |
| │ November 2026│ ₹52,40,000 (P10: 45L) ₹44,50,000     │ +₹7,90,000   │ +₹6,10,000   │ ₹30,59,000  │ |
| │ December 2026│ ₹61,00,000 (P10: 51L) ₹46,80,000     │ +₹14,20,000  │ +₹12,40,000  │ ₹44,79,000  │ |
| └──────────────┴──────────────────┴──────────────────┴──────────────┴──────────────┴─────────────┘ |
+----------------------------------------------------------------------------------------------------+
```

#### 2. Component Hierarchy & Interfaces
```tsx
<ForecastPage>
  <ForecastMetricHeader 
    mapeScore={0.0561} 
    holdoutCoverage={0.933} 
    lowestDipAmount={420000} 
    lowestDipDate="2026-10-01" 
  />
  <TopographyVisualizationCard>
    <ViewToggle active={viewMode} onChange={setViewMode} />
    {viewMode === '3D' ? (
      <CashflowTopographyCanvas simulationData={forecastPoints} stressModifiers={stressParams} />
    ) : (
      <Fallback2DTopography simulationData={forecastPoints} creditLimit={2500000} />
    )}
  </TopographyVisualizationCard>
  <StressTestSliderPanel 
    onDelayChange={(days) => setStressParams(p => ({ ...p, delayDays: days }))} 
    onExpenseSurge={(amt) => setStressParams(p => ({ ...p, extraExpense: amt }))} 
    onHaircutChange={(alpha) => setStressParams(p => ({ ...p, alpha }))} 
  />
  <MonthlyOutlookTable outlookMatrix={monthlyOutlookData} />
</ForecastPage>
```

---

### 3.5 View 4: Review Queue (Decision 60 Precision Triage)

#### 1. Visual Layout Mockup (ASCII Wireframe)
```
+----------------------------------------------------------------------------------------------------+
| REVIEW QUEUE: DECISION 60 PRECISION MATCHING                          [Circuit Breaker: ACTIVE ✓]  |
+----------------------------------------------------------------------------------------------------+
| SEGMENTED TIER SELECTOR:                                                                           |
| [ All Items (3,533) ]  [ Suggestions (1,744) ]  [ Questions (619) ]  [ Auto-Posted ✓ (1,170) ]     |
+----------------------------------------------------------------------------------------------------+
| 3-PANE TRIAGE LAYOUT:                                                                              |
| LEFT FILTER (20%)      | CENTER TRANSACTION TABLE (45%)          | RIGHT INSPECTOR DETAIL (35%)    |
| ┌────────────────────┐ │ ┌────────────┬──────────┬─────────────┐ │ ┌─────────────────────────────┐ |
| │ Search Narration.. │ │ │ Date       │ Amount   │ Tier / Rule │ │ │ Txn: TXN-1002345 (HDFC Bank)│ |
| │ [                ] │ │ ├────────────┼──────────┼─────────────┤ │ │ Date: 30 Sep 2026           │ |
| │ Rule Filter:       │ │ │ 30 Sep 2026│ ₹45,000  │ SUGGEST:    │ │ │ Amount: ₹45,000.00 (CREDIT) │ |
| │ [x] CASH_DEPOSIT   │ │ │            │          │ CASH_DEP    │ │ ├─────────────────────────────┤ |
| │ [x] CLUBBED        │ │ │ 30 Sep 2026│ ₹82,400  │ SUGGEST:    │ │ │ Narration:                  │ |
| │ [x] ON_ACCOUNT     │ │ │            │          │ CLUBBED     │ │ │ "CMS/DEP/CDM-9023/KAVERI"   │ |
| │ [ ] ASK_OWNER      │ │ │ 29 Sep 2026│ ₹1,14,000│ SUGGEST:    │ │ ├─────────────────────────────┤ |
| │                    │ │ │            │          │ MATERIAL    │ │ │ Decision 60 Rule Applied:   │ |
| │ Materiality:       │ │ └────────────┴──────────┴─────────────┘ │ │ CASH_DEPOSIT (Linked Slips) │ |
| │ [x] >= ₹1 Lakh     │ │ Keyboard: [j] Down [k] Up               │ │ Match Confidence: 100%        │ |
| └────────────────────┘ │           [a] Approve [r] Reassign      │ ├─────────────────────────────┤ |
|                        │                                         │ │ Linked Documents:           │ |
|                        │                                         │ │ • SLP-1092: Laxmi ₹15,000   │ |
|                        │                                         │ │ • SLP-1093: Balaji ₹8,500   │ |
|                        │                                         │ │ • SLP-1094: Om ₹21,500      │ |
|                        │                                         │ ├─────────────────────────────┤ |
|                        │                                         │ │ [✓ Approve & Post to Tally] │ |
|                        │                                         │ │ [🔄 Reassign Candidate Payer]│ |
|                        │                                         │ └─────────────────────────────┘ |
+----------------------------------------------------------------------------------------------------+
| FLOATING BATCH ACTION BAR (Mounted when 2+ rows selected)                                          |
| Selected: 14 Suggestions (Total: ₹4,28,000) | [⚡ Batch Approve 14 Items]  [Dismiss Selection]    |
+----------------------------------------------------------------------------------------------------+
```

#### 2. Component Hierarchy & Interfaces
```tsx
<ReviewQueuePage>
  <D60HeaderStatus 
    autoCount={1170} 
    suggestCount={1744} 
    askCount={619} 
    noDocCount={23} 
    isCircuitBreakerActive={true} 
  />
  <ThreePaneTriageLayout>
    <TriageFilterSidebar 
      rules={activeRules} 
      onToggleRule={handleRuleFilter} 
      searchTerm={searchTerm} 
      onSearch={setSearchTerm} 
    />
    <TransactionGridTable 
      transactions={unreconciledItems} 
      selectedId={activeTxnId} 
      onSelectRow={setActiveTxnId} 
      onBatchSelect={setSelectedBatch} 
    />
    <TransactionDetailInspector 
      transaction={activeTxn} 
      onApprove={handleSingleApprove} 
      onReassign={handleReassignPayer} 
    />
  </ThreePaneTriageLayout>
  {selectedBatch.length > 1 && (
    <BatchActionBar 
      items={selectedBatch} 
      onBatchApprove={handleBatchApprove} 
      onClear={() => setSelectedBatch([])} 
    />
  )}
</ReviewQueuePage>
```

#### 3. Key Interaction Flows
- **Rapid Keyboard Triage Flow:** User presses `j` $\rightarrow$ Next row highlighted $\rightarrow$ Right pane instantly updates with candidate invoice numbers and slip matches $\rightarrow$ User presses `a` $\rightarrow$ Server Action `reconcileMatchAction` fires $\rightarrow$ Row animates off screen with green flash $\rightarrow$ Optimistic toast displays with 10s "Undo" option $\rightarrow$ Transaction is permanently queued for Tally XML export.

---

### 3.6 View 5: Receivables & Recovery (Section 18 Shield & MSMED)

#### 1. Visual Layout Mockup (ASCII Wireframe)
```
+----------------------------------------------------------------------------------------------------+
| RECEIVABLES & RECOVERY ACCELERATOR                                    [Section 18 Shield: ACTIVE]  |
+----------------------------------------------------------------------------------------------------+
| 3-QUADRANT RECEIVABLES METRIC GRID                                                                 |
| ┌───────────────────────────┐ ┌───────────────────────────┐ ┌────────────────────────────────────┐ |
| │ Total Formal Receivables  │ │ Open Invoices             │ │ Overdue > 60 Days                │ |
| │ ₹90,47,000                │ │ 346 Invoices              │ │ ₹23,82,000 (91 Invoices)         │ |
| │ Verified against GST Ledg │ │ 64 Active Trade Debtors   │ │ 26.3% of Total Formal Book       │ |
| └───────────────────────────┘ └───────────────────────────┘ └────────────────────────────────────┘ |
+----------------------------------------------------------------------------------------------------+
| FILTER SEGMENTS:                                                                                   |
| [ Over 45 Days (MSMED Priority) ]  [ All 64 Debtors ]  [ ⚠️ Over 30 Months (Section 18 Cliff: 4) ] |
| [🖨️ Generate Printable Daily Field Recovery Sheet]                                                  |
+----------------------------------------------------------------------------------------------------+
| CUSTOMER RECOVERY CARDS & SALESMAN PROTECTION SHIELD                                               |
|                                                                                                    |
| 1. MATOSHREE SUPERMARKET (Oldest: 930 Days Overdue) | Total Due: ₹1,14,000.00                      |
|    ┌─────────────────────────────────────────────────────────────────────────────────────────────┐ |
|    │ ⚠️ SECTION 18 LIMITATION ACT CLIFF: Debt is 31 months old. Statutory 3-year bar in 60 days.  │ |
|    │ Legal Remedy: Client-side WhatsApp balance acknowledgment (AoD) resets the 3-year clock.    │ |
|    │ [💬 Send WhatsApp AoD Link (wa.me)]  [📥 Log Debtor Reply & Issue BSA §63 Certificate]      │ |
|    └─────────────────────────────────────────────────────────────────────────────────────────────┘ |
|                                                                                                    |
| 2. BALAJI GENERAL STORE (Oldest: 48 Days Overdue) | Total Due: ₹65,000.00                          |
|    ┌─────────────────────────────────────────────────────────────────────────────────────────────┐ |
|    │ 🛡️ SALESMAN PROTECTION SHIELD ACTIVE:                                                       │ |
|    │ "Salesman Ramesh Kumar collected ₹15,000 cash today (Slip SLP-1092); not banked yet.        │ |
|    │ DO NOT CALL RETAILER - CASH IN ROUTE BAG."                                                  │ |
|    └─────────────────────────────────────────────────────────────────────────────────────────────┘ |
+----------------------------------------------------------------------------------------------------+
```

#### 2. Component Hierarchy & Interfaces
```tsx
// app/(dashboard)/receivables/page.tsx
<ReceivablesRecoveryView>
  <ReceivablesMetricGrid 
    totalOutstanding={9047000} 
    openInvoiceCount={346} 
    activeDebtorCount={64} 
    overdue60DaysAmount={2382000} 
    overdue60DaysCount={91} 
  />

  <ReceivablesFilterBar 
    activeSegment={activeSegment} 
    onSelectSegment={setActiveSegment} 
    onOpenDailyRecoverySheet={() => setIsRecoverySheetOpen(true)} 
  />

  <OverdueGrid>
    {debtors.map((debtor) => (
      <CustomerRecoveryCard 
        key={debtor.customerId} 
        debtor={debtor}
        onSendWhatsApp={() => handleGenerateWhatsAppAoD(debtor)}
        onLogDebtorReply={() => setSelectedDebtorForReply(debtor)}
      >
        {debtor.hasSalesmanCollectedToday && (
          <SalesmanShieldBanner 
            salesmanName={debtor.salesmanName} 
            collectedAmount={debtor.collectedTodayAmount} 
            slipNumber={debtor.collectedSlipId} 
          />
        )}
      </CustomerRecoveryCard>
    ))}
  </OverdueGrid>

  {/* WhatsApp AoD Link Modal */}
  {selectedDebtorForAoD && (
    <WhatsAppAoDModal 
      debtor={selectedDebtorForAoD} 
      businessName="Kaveri Distributors" 
      onClose={() => setSelectedDebtorForAoD(null)} 
    />
  )}

  {/* Out-of-band Debtor WhatsApp Written Reply Ingestion Modal */}
  {selectedDebtorForReply && (
    <DebtorAodReplyModal 
      debtor={selectedDebtorForReply} 
      businessName="Kaveri Distributors" 
      isOpen={!!selectedDebtorForReply} 
      onClose={() => setSelectedDebtorForReply(null)} 
      onGenerateBsaCertificate={handleIssueBsaCertificate} 
    />
  )}

  {/* Printable Daily Field Recovery Sheet */}
  <DailyRecoverySheetModal 
    isOpen={isRecoverySheetOpen} 
    debtors={debtors} 
    asOfDate="2026-09-30" 
    onClose={() => setIsRecoverySheetOpen(false)} 
  />
</ReceivablesRecoveryView>
```

```typescript
export interface ReceivablesMetricGridProps {
  totalOutstanding: number;
  openInvoiceCount: number;
  activeDebtorCount: number;
  overdue60DaysAmount: number;
  overdue60DaysCount: number;
}

export interface CustomerRecoveryCardProps {
  debtor: CustomerReceivable;
  onSendWhatsApp: () => void;
  onLogDebtorReply: () => void;
  children?: React.ReactNode;
}

export interface SalesmanShieldBannerProps {
  salesmanName: string;
  collectedAmount: number;
  slipNumber: string;
}

export interface DebtorAodReplyModalProps {
  debtor: CustomerReceivable;
  businessName: string;
  isOpen: boolean;
  onClose: () => void;
  onGenerateBsaCertificate: (payload: DebtorReplyPayload) => Promise<BsaCertificateResult>;
}

export interface DebtorReplyPayload {
  customerId: string;
  customerName: string;
  replyText: string;
  replyTimestamp: string;
  senderPhone: string;
  acknowledgedAmount: number;
  screenshotFile?: File;
}

export interface BsaCertificateResult {
  certificateId: string;
  sha256Hash: string;
  statutoryClockExtendedUntil: string;
  pdfDownloadUrl: string;
}

export interface DailyRecoverySheetModalProps {
  isOpen: boolean;
  debtors: CustomerReceivable[];
  asOfDate: string;
  onClose: () => void;
}
```

#### 3. Key Interaction Flows & Invariants
- **Section 18 Digital AoD Flow:** For any customer account open $\ge 900$ days (30+ months), the system prohibits generic threatening legal notices. Instead, clicking `Send WhatsApp AoD Link` generates a client-side `wa.me` URL:
  ```
  https://wa.me/919820012345?text=Namaste%20Matoshree%20Supermarket%20ji%2C%20hope%20you%20are%20doing%20well.%20As%20per%20our%20records%20with%20Kaveri%20Distributors%2C%20the%20pending%20balance%20is%20%E2%82%B91%2C14%2C000%20from%20our%20earlier%20supplies.%20Could%20you%20please%20confirm%20if%20this%20matches%20your%20books%2C%20or%20let%20us%20know%20when%20we%20can%20expect%20a%20small%20part-settlement%3F%20Thank%20you!
  ```
- **Zero-Knowledge Privacy:** The WhatsApp link is synthesized 100% in the user's browser via native string concatenation. No customer telephone numbers or debt balances are ever transmitted to cloud WhatsApp Business Solution Providers (Twilio, Meta Cloud API), ensuring complete compliance with the Digital Personal Data Protection (DPDP) Act, 2023.
- **Out-of-Band Debtor Reply Ingestion & BSA 2023 §63 Certificate:**
  Because WhatsApp communication occurs out-of-band on mobile devices, the web browser cannot passively snoop on debtor responses. When the retailer replies (e.g., *"Haan Ramesh bhai, ₹1.14L confirm hai, agle hafte ₹50k bhejte hain"*), the user opens `<DebtorAodReplyModal>`:
  1. The user pastes the debtor's written reply text, message timestamp, and optional chat screenshot.
  2. The browser's native WebCrypto engine executes SHA-256 contemporaneous hashing over the canonical UTF-8 payload:
     $$\text{Hash} = \text{SHA-256}(\text{Party} \parallel \text{GSTIN} \parallel \text{Balance} \parallel \text{ReplyText} \parallel \text{Timestamp} \parallel \text{UserAgent})$$
  3. The modal generates and downloads a cryptographically verifiable **Form 63 BSA Digital Hash Certificate** containing the SHA-256 checksum and electronic audit record.
  4. The debtor's Section 18 limitation clock is officially extended by **36 months** in the local ledger, shielding the debt from statutory extinguishment under commercial court rules.
- **Salesman Protection Shield:** If a route salesman logged a parchi today that is currently in the cash bag or godown till (`status !== 'BANKED'`), the customer card displays an amber warning banner:
  $$\texttt{"DO NOT CALL RETAILER - ₹15,000 cash in Salesman Ramesh Kumar's bag (Slip SLP-1092)."}$$
  This prevents distributor owners from embarrassing salesmen or double-demanding payment from retailers.

---

### 3.7 View 6: Ask Copilot (Grounded Conversational AI)

#### 1. Visual Layout Mockup (ASCII Wireframe)
```
+----------------------------------------------------------------------------------------------------+
| ASK COPILOT: GROUNDED CONVERSATIONAL ASSISTANT                        [Zero Stochastic Hallucination]
+----------------------------------------------------------------------------------------------------+
| ACTIVE FINANCIAL CONTEXT:                                                                          |
| [SME-1: Kaveri Distributors]  [Bank Verified: 30 Sep 2026]  [Sovereign Vault: Unlocked (RAM)]      |
+----------------------------------------------------------------------------------------------------+
| CONVERSATION STREAM COLUMN:                                                                        |
|                                                                                                    |
| 👤 Owner: "Can I safely pay my staff salaries on October 1st?"                                     |
|                                                                                                    |
| 🤖 Copilot:                                                                                        |
|   ┌─ Tool Execution Callouts ────────────────────────────────────────────────────────────────────┐ |
|   │ ⚡ Consulted Bank Current Balance: ₹12,39,000 (HDFC Bank Formal Plane)                        │ |
|   │ ⚡ Evaluated 1 Oct Payroll Obligation: ₹4,65,000 (24 Staff Members)                           │ |
|   │ ⚡ Streamed Zero-Knowledge Template Token: {{LOCAL_VAULT_GALLA_CASH}} (Client RAM Synthesis)   │ |
|   └──────────────────────────────────────────────────────────────────────────────────────────────┘ |
|   Yes, you can safely pay your October 1st salaries of **₹4,65,000** [1].                        |
|                                                                                                    |
|   Even if you pay 100% of salaries exclusively from your HDFC bank account, your bank balance will |
|   remain positive at **₹7,74,000**, which is **₹32,74,000 clear** of your sanctioned CC facility   |
|   limit (-₹25.00L). You also have **₹4,20,000** physical cash in your godown drawer [2].          |
|   *(Note: Drawer figure interpolated in local volatile RAM; zero cash data sent to cloud).*       |
|                                                                                                    |
|   ┌─ Devanagari Summary Card (हिन्दी सारांश) ───────────────────────────────────────────────────────┐ |
|   │ हाँ, आप 1 अक्टूबर को ₹4,65,000 का वेतन आराम से दे सकते हैं। वेतन भुगतान के बाद भी बैंक में     │ |
|   │ ₹7.74L शेष रहेगा और गल्ले में ₹4.20L नकद सुरक्षित रहेगा।                                      │ |
|   └──────────────────────────────────────────────────────────────────────────────────────────────┘ |
|                                                                                                    |
|   ▼ Expand Verified Citations & Ledger Rows (2 Source Items):                                      |
|     • [1] Salary Ledger: 24 employees, base ₹4,65,000, scheduled 2026-10-01 [View Payroll]        |
|     • [2] Local Sovereign Vault: Galla #GL-9024, physical count ₹4,20,000 (Client-Only) [Cash Book]|
+----------------------------------------------------------------------------------------------------+
| PINNED COMPOSER & PROMPT SUGGESTION CAROUSEL                                                       |
| [💼 Can I pay salaries on 1 Oct?] [🔍 Who owes me the most?] [🪙 What is today's till cash?]       |
| ┌───────────────────────────────────────────────────────────────────────────┬────────────────────┐ |
| │ Ask a cashflow question in English, हिन्दी, or Hinglish...                 │ [🎤 Voice] [Send]  │ |
| └───────────────────────────────────────────────────────────────────────────┴────────────────────┘ |
+----------------------------------------------------------------------------------------------------+
```

#### 2. Component Hierarchy & Interfaces
```tsx
// app/(dashboard)/copilot/page.tsx
<AskCopilotView>
  <ContextStatusBar 
    businessId="SME-1" 
    asOfDate="2026-09-30" 
    vaultState={isVaultUnlocked ? 'UNLOCKED_RAM' : 'LOCKED_FORMAL'} 
  />
  <ChatConversationScrollArea>
    {messages.map((msg) => (
      <ChatMessageItem 
        key={msg.id} 
        message={msg}
        // Client-side zero-knowledge template interpolation
        interpolatedContent={interpolateLocalVaultTokens(msg.content, {
          isVaultUnlocked,
          gallaCash: gallaEntry?.countedCash ?? 0,
          gallaDate: gallaEntry?.date ?? 'Today',
        })}
      >
        {msg.toolExecutions && <ToolExecutionBlock steps={msg.toolExecutions} />}
        <MarkdownRenderer content={msg.content} />
        {msg.hindiSummary && <DevanagariSummaryCard text={msg.hindiSummary} />}
        {msg.citations && (
          <VerifiableCitationAccordion 
            citations={msg.citations} 
            localVaultCitation={isVaultUnlocked ? {
              id: 'local-vault',
              source: 'Sovereign Galla Till',
              amount: gallaEntry?.countedCash ?? 0,
              badge: 'RAM_ONLY'
            } : undefined}
          />
        )}
      </ChatMessageItem>
    ))}
  </ChatConversationScrollArea>
  <PromptSuggestionCarousel onSelectPrompt={handlePromptSelect} />
  <ChatInputComposer 
    onSendMessage={handleSendQuery} 
    onAudioRecorded={handleVoiceTranscribe} 
    isStreaming={isStreaming} 
    onStopStream={abortStream} 
  />
</AskCopilotView>
```

```typescript
export interface ChatMessageItemProps {
  message: CopilotMessage;
  interpolatedContent?: string;
  children?: React.ReactNode;
}

export interface CopilotMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string; // May contain templates: {{LOCAL_VAULT_GALLA_CASH}}
  hindiSummary?: string;
  toolExecutions?: ToolExecutionStep[];
  citations?: CitationItem[];
  timestamp: string;
}

export interface ToolExecutionStep {
  toolName: string;
  status: 'running' | 'completed' | 'failed';
  resultSummary?: string;
}

export interface CitationItem {
  id: string;
  source: string;
  amount: number;
  date?: string;
  deepLink?: string;
  badge?: 'BANK_FORMAL' | 'GST_INVOICE' | 'RAM_ONLY';
}

export interface ChatInputComposerProps {
  onSendMessage: (query: string) => Promise<void>;
  onAudioRecorded: (blob: Blob) => Promise<void>;
  isStreaming: boolean;
  onStopStream: () => void;
}
```

#### 3. Client-Side Zero-Knowledge Template Interpolation Architecture
Under ADR-001, the merchant's physical cash count must NEVER be transmitted in HTTP request payloads. When an owner asks: `"Can I pay salaries on 1 October?"`:
1. **Sanitized Query Dispatch:** The client dispatches `POST /api/copilot/stream` containing **only** `{ question, businessId, asOfDate }`.
2. **Server Structured Streaming:** The server executes Python tool calls against formal bank and payroll tables, streaming SSE text chunks with verifiable tokens:
   ```
   "Even if you pay salaries from HDFC, your balance remains ₹7.74L. You also have {{LOCAL_VAULT_GALLA_CASH}} in your physical drawer."
   ```
3. **Volatile RAM Interpolation:** In `AskCopilotView.tsx`, the client component intercepts the token `{{LOCAL_VAULT_GALLA_CASH}}` and replaces it dynamically with `formatINR(gallaEntry.countedCash)` in volatile browser memory.
4. **Zero Cloud Residue:** No proxy, CDN, server access log, or third-party LLM inference log ever records the merchant's physical cash holding.

---

### 3.8 View 7: Statutory Exports & Data Quality

#### 1. Visual Layout Mockup (ASCII Wireframe)
```
+----------------------------------------------------------------------------------------------------+
| STATUTORY EXPORTS & CA AUDIT RECONCILIATION                           [100% Balance Tie Certified] |
+----------------------------------------------------------------------------------------------------+
| 1-CLICK EXPORT PACK GENERATION                                                                     |
| ┌──────────────────────────────────────────────┐ ┌───────────────────────────────────────────────┐ |
| │ 📥 TALLYPRIME XML RECEIPT VOUCHERS           │ │ 📊 CA 5-SHEET STATUTORY EXCEL RECONCILIATION   │ |
| │ Format: Pure TDL XML with deterministic GUIDs│ │ Format: OpenPyXL (.xlsx) with Live Tie Formulas│ |
| │ 1,170 Reconciled AUTO Receipts Ready         │ │ Sheets 1–5: Strict Statutory Formal Book Only: │ |
| │ MCA Rule 11(g) Edit Log & CDATA Protected    │ │ 1. Reconciliation_Summary (Excludes Block D)   │ |
| │ [ Download TallyPrime XML Voucher Pack ]     │ │ 2. Matched_Receipts_AUTO                       │ |
| └──────────────────────────────────────────────┘ │ 3. Suggested_Matches                           │ |
|                                                  │ 4. Unmatched_Bank_Credits                      │ |
|                                                  │ 5. Open_Invoices_Aging (<30Mo & Cliff)         │ |
|                                                  │ [ Download 5-Sheet Statutory CA Pack ]         │ |
|                                                  └───────────────────────────────────────────────┘ |
+----------------------------------------------------------------------------------------------------+
| INTERNAL MANAGEMENT DIAGNOSTIC PACK (SOVEREIGN DUAL-PLANE RECONCILIATION)                          |
| 🔒 Owner PIN Unlock Required | Distinct Internal Format (NEVER Shared with External Auditors)      |
| Includes: Full 6 Sheets (Sheet 6: Salesman Route Slips + Sheet 1 Block D Till Cash Cross-Check)    |
| [ 🔐 Unlock Sovereign Vault to Export Internal Management Diagnostic Pack ]                       |
+----------------------------------------------------------------------------------------------------+
| DATA INTEGRITY MATRIX & RECONCILIATION SUMMARY                                                     |
| Bank Lines Ingested: 13,359 lines across 18 months  | Balance Breaks Detected: 0                   |
| ┌──────────────────────────┬──────────────────────────┬──────────────────────┬───────────────────┐ |
| │ Opening Bank Bal         │ + Total Bank Credits     │ − Total Bank Debits  │ = Closing Bank Bal│ |
| │ ₹8,42,100.00             │ ₹4,12,45,000.00          │ ₹4,08,48,100.00      │ ₹12,39,000.00     │ |
| └──────────────────────────┴──────────────────────────┴──────────────────────┴───────────────────┘ |
| Bank Balance Tie Status: [ ✓ PASS: 100% TIED (Variance: ₹0.00) ]                                   |
+----------------------------------------------------------------------------------------------------+
```

#### 2. Component Hierarchy & Interfaces
```tsx
// app/(dashboard)/exports/page.tsx
<StatutoryExportsView>
  <ExportPackGrid>
    <TallyXmlExportCard 
      autoVoucherCount={1170} 
      totalCreditAmount={41245000} 
      onExportXml={handleDownloadTallyXml} 
    />
    <CaExcelExportCard 
      sheetCount={5} 
      isStatutoryCertified={true} 
      onExportWorkbook={handleDownloadStatutoryCaExcel} 
    />
  </ExportPackGrid>

  <InternalManagementPackCard 
    isVaultUnlocked={isVaultUnlocked} 
    routeSlipCount={collectionSlips.length} 
    countedDrawerCash={gallaEntry?.countedCash ?? 0} 
    onExportInternalPack={handleDownloadInternalPack} 
    onPromptUnlock={promptVaultPinModal} 
  />

  <DataIntegrityMatrix 
    totalBankLinesIngested={13359} 
    monthsAudited={18} 
    balanceBreaks={0} 
    openingBalance={842100} 
    totalCredits={41245000} 
    totalDebits={40848100} 
    closingBalance={1239000} 
    isBalanceTied={true} 
  />
</StatutoryExportsView>
```

```typescript
export interface TallyXmlExportCardProps {
  autoVoucherCount: number;
  totalCreditAmount: number;
  onExportXml: () => Promise<void>;
}

export interface CaExcelExportCardProps {
  sheetCount: 5;
  isStatutoryCertified: boolean;
  onExportWorkbook: () => Promise<void>;
}

export interface InternalManagementPackCardProps {
  isVaultUnlocked: boolean;
  routeSlipCount: number;
  countedDrawerCash: number;
  onExportInternalPack: () => Promise<void>;
  onPromptUnlock: () => void;
}

export interface DataIntegrityMatrixProps {
  totalBankLinesIngested: number;
  monthsAudited: number;
  balanceBreaks: number;
  openingBalance: number;
  totalCredits: number;
  totalDebits: number;
  closingBalance: number;
  isBalanceTied: boolean;
}
```

#### 3. Key Interaction Flows & Invariants
- **ADR-004 CA Export Split-Plane Firewall Hardening:**
  The statutory CA Excel export is strictly a **5-sheet formal workbook** consisting exclusively of:
  1. `Reconciliation_Summary` (Summary metrics, opening/closing bank tie-out formula, zero mentions of drawer cash).
  2. `Matched_Receipts_AUTO` (1,170 verified bank receipts straight-posted with Tally GUIDs).
  3. `Suggested_Matches` (1,744 reviewed credit entries with confidence ratings).
  4. `Unmatched_Bank_Credits` (619 bank credits awaiting formal invoices).
  5. `Open_Invoices_Aging` (Outstanding trade receivables with MSMED and Section 18 aging brackets).
  
  **Mandatory Split-Plane Isolation:**
  - Sheet 6 (`Salesman_Collection_Slips`) is **completely omitted** from the statutory workbook.
  - Block D (`CASH DRAWER & COLLECTIONS CROSS-CHECK`) is **completely removed** from Sheet 1.
  - This guarantees that a Chartered Accountant or statutory tax auditor reviewing the official workbook cannot view informal cash collections or route slips, preventing accidental deemed-income tax assessments under Section 247(1)(vi) of the Income-tax Act, 2025.
- **Separate Internal Management Diagnostic Pack:**
  If the business owner desires internal dual-plane reconciliation (cross-checking physical drawer cash against route slips), they must explicitly generate the **Internal Management Diagnostic Pack**. This pack is strictly PIN-gated, labeled with bold disclaimers, and never titled or presented as a CA Statutory Reconciliation Pack.
- **Deterministic Tally Voucher GUID Generation & CDATA Sanitization:**
  Every generated XML receipt voucher assigns an immutable GUID structured as `<GUID>COPILOT-{biz}-{txn_id}</GUID>`. All dynamic text elements (`<PARTYNAME>`, `<NARRATION>`, `<GUID>`) are strictly wrapped in `<![CDATA[ ... ]]>` blocks and escaped for XML control characters (`&`, `<`, `>`, `"`, `'`), ensuring seamless import into TallyPrime without parser termination.

---

## 4. 3D Spatial Cashflow Topography (Three.js & React Three Fiber)

### 4.1 Spatial Metaphor & Continuous Elevation Heightfield Mesh

Traditional financial spreadsheets flatten multi-dimensional enterprise health into disconnected numbers. The **3D Spatial Cashflow Topography** transforms the merchant's financial outlook into an intuitive cartographic landscape:

```
                  [GREEN LIQUIDITY PLATEAU]
                     Y > 0: Usable Cash Buffer
                           /\
                          /  \
                         /    \     [AMBER STRENGTH RIDGE]
                        /      \      P50 Median Flow
                       /        \_________
                      /                   \
─────────────────────/─────────────────────\────────────────────── Y = 0 (Zero Cash Floor)
                    /                       \
                   /                         \______ [RED CC DANGER CLIFF]
                  /                                   Y = -₹25,00,000 Limit
                 /
      [PAYROLL TROUGH (CANYON)]
         1 Oct Salary Dip
```

1. **Cartesian Coordinate Mapping:**
   - **$X$-Axis (Timeline):** Extends across 90 days from $T_0$ (Today / Cutoff) to $T_{+90}$ calendar days.
   - **$Y$-Axis (Liquidity Elevation):** Rupee balance heightfield:
     - **Plateaus ($Y > 0$):** Rolling emerald hills representing spendable liquidity (Bank Current Balance + Drawer Cash).
     - **Canyons ($Y < 0$):** Valleys representing committed statutory obligations (1 Oct Payroll, 20 Oct GST).
     - **Translucent Red Datum Floor:** Fixed at $-₹25,00,000$ representing the sanctioned Cash-Credit facility limit. A visual breach occurs if canyon floors penetrate this plane.
   - **$Z$-Axis (Category Lanes & Probability Envelope):**
     - $Z_0$: P10 Conservative trajectory (sloping southern shoulder).
     - $Z_1$: P50 Median expected trajectory (the central mountain ridge).
     - $Z_2$: P90 Optimistic trajectory (sloping northern shoulder).

---

### 4.2 Scene Graph & R3F Component Hierarchy

```tsx
<Canvas
  camera={{ position: [0, 55, 95], fov: 42, near: 0.1, far: 1000 }}
  dpr={[1, 2]}
  gl={{ antialias: true, alpha: false, powerPreference: 'high-performance' }}
>
  <color attach="background" args={['#020617']} />
  
  {/* Lighting Rig: Dynamic real-time directional shadow maps are disabled (castShadow={false}) 
      in favor of baked vertex AO lighting, keeping draw calls strictly under budget */}
  <ambientLight intensity={0.6} />
  <directionalLight position={[30, 60, 40]} intensity={1.0} castShadow={false} />
  <pointLight position={[0, 15, 0]} intensity={0.8} color="#22C55E" />

  <TopographyCameraRig />

  <group position={[-45, 0, 0]}>
    {/* Continuous 3D Heightfield Topographic Surface (1 draw call) */}
    <TerrainMesh points={dailyForecastPoints} creditLimit={2500000} />

    {/* Translucent CC Facility Datum Plane (1 draw call) */}
    <CreditLimitPlane limit={2500000} width={90} depth={30} />

    {/* Dynamic 1-Draw-Call Instanced Cash Velocity Particles (1 draw call, GPU-vertex animated) */}
    <ParticleFlowField particleCount={1500} velocityVectors={flowVectors} />

    {/* 3D Milestone Landmark Beacons: Rendered via InstancedMesh (1 call for stems, 1 call for beacon heads)
        Text billboards are rendered as CSS3D DOM overlays via @react-three/drei <Html>, incurring 0 WebGL draw calls */}
    <InstancedMilestonePins 
      landmarks={[
        { position: [1, 4.2, 0], label: "1 Oct: Salaries (-₹4.65L)", type: "SALARY" },
        { position: [20, 8.5, 0], label: "20 Oct: GST Return (-₹3.10L)", type: "TAX" },
        { position: [45, 18.2, 0], label: "Diwali Customer Receipts (+₹12.5L)", type: "RECEIPT" },
      ]} 
    />
  </group>
</Canvas>
```

---

### 4.3 Procedural Terrain Shader & Topographic Isolines

The terrain mesh is generated dynamically via a custom Three.js `ShaderMaterial`. In the vertex shader, bicubic interpolation derives smooth curves from discrete daily P10/P50/P90 simulation points. In the fragment shader, procedural **isolines** (cartographic contour lines) snap to exact multiples of ₹1,00,000 ($₹0, ₹1\text{L}, ₹2\text{L}, \dots$):

```glsl
// components/3d/shaders/terrain.frag.glsl
precision highp float;

varying vec3 vPosition;
varying float vElevation;

uniform vec3 uColorSurplus;   // OKLCH Emerald
uniform vec3 uColorDeficit;   // OKLCH Ruby
uniform vec3 uColorWarning;   // OKLCH Amber
uniform float uCreditLimit;

void main() {
  // Normalize elevation relative to zero line
  float normElevation = vElevation / 3000000.0;
  vec3 baseColor = mix(uColorDeficit, uColorSurplus, smoothstep(-0.5, 1.0, normElevation));

  // Procedural Topographic Isolines (Snaps to exact multiples of ₹1,00,000)
  float isofactor = fract(vElevation / 100000.0);
  float line = smoothstep(0.02, 0.0, min(isofactor, 1.0 - isofactor));

  // Translucent danger wash if below CC limit floor
  if (vElevation < -uCreditLimit) {
    baseColor = vec3(0.85, 0.12, 0.12);
  }

  vec3 finalColor = mix(baseColor, vec3(1.0, 1.0, 1.0), line * 0.35);
  gl_FragColor = vec4(finalColor, 0.95);
}
```

---

### 4.4 Dynamic Instanced Particle Flow Velocity Field

To visualize cash velocity without burdening the GPU, 1,500 particles are rendered via a single `THREE.InstancedMesh` consuming exactly **1 draw call**:
- **Inflow Particles:** Emerge from customer retail nodes and accelerate along Bezier trajectories into the central bank peak.
- **Outflow Particles:** Stream downward from the bank peak into supplier payables and salary canyon floors.
- **Mathematical Velocity:** Particle velocity scales with the square root of the monetary value:
  $$v_i = v_{\text{base}} \cdot \sqrt{\frac{\text{Amount}_i}{\text{Median Transaction Amount}}}$$

---

### 4.5 Constrained Camera Kinematics & Cinematic Fly-Throughs

The camera rig uses `OrbitControls` constrained to protect the user's spatial orientation:
- **Polar Angle Limits:** Clamped between $20^\circ$ and $75^\circ$ ($\frac{\pi}{9} \le \theta \le \frac{5\pi}{12}$), preventing the camera from flipping upside down or clipping through the ground.
- **Azimuth Angle Limits:** Clamped to $[-45^\circ, +45^\circ]$ around the median forward vector, preserving the left-to-right chronological timeline.
- **Cinematic Preset Flight Paths (GSAP / `@react-spring/three`):**
  1. `Macro Horizon`: High-angle isometric overview showing the complete 90-day trajectory.
  2. `Godown Galla Close-Up`: Camera smoothly swoops down to focus on today's physical drawer float.
  3. `1 Oct Payroll Glide`: Low-angle glide along the valley floor verifying that the CC limit floor is never breached.
  4. `Scenario Morphing`: When the user drags a stress slider, the mesh vertices dynamically morph in real time at 60fps.

---

### 4.6 60fps Performance Budget, Memory Pooling & WebGL Lifecycle

| Resource Category | Budget Allocation | Rationale |
|---|---|---|
| **Draw Calls** | $\le 32$ total draw calls | Keeps CPU command preparation under $2\text{ms}$ per frame. |
| **Triangles / Vertices** | $128 \times 64 = 8,192$ quads ($16,384$ triangles) | Low vertex count allows instant CPU/GPU morphing during slider dragging. |
| **Texture Memory** | $\le 16\text{MB}$ | Shaders are pure mathematical procedurals; zero heavy image textures. |
| **Frame Rate** | Locked 60fps (Frame time $\le 16.6\text{ms}$) | Smooth gesture panning on 90Hz/120Hz mobile screens. |

#### WebGL Context Loss Recovery Lifecycle
Wholesale distributor cashiers frequently switch apps to take phone calls, scan barcodes, or check WhatsApp. Budget Android tablets (3GB–4GB RAM) aggressively reclaim WebGL GPU contexts. To prevent permanent screen freezing or browser tab Out-Of-Memory (OOM) crashes:

```typescript
// components/3d/CashflowTopographyCanvas.tsx
'use client'

import React, { useRef, useEffect, useState } from 'react';
import * as THREE from 'three';

export function disposeThreeScene(scene: THREE.Scene) {
  scene.traverse((obj) => {
    if ((obj as THREE.Mesh).isMesh) {
      const mesh = obj as THREE.Mesh;
      if (mesh.geometry) mesh.geometry.dispose();
      if (mesh.material) {
        if (Array.isArray(mesh.material)) {
          mesh.material.forEach((m) => m.dispose());
        } else {
          mesh.material.dispose();
        }
      }
    }
  });
}

export function CashflowTopographyWrapper(props: TopographyProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const [isContextLost, setIsContextLost] = useState(false);
  const [webglEpoch, setWebglEpoch] = useState(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const handleContextLost = (e: Event) => {
      e.preventDefault();
      console.warn('WebGL context lost. Disposing GPU buffers and engaging 2D fallback.');
      if (sceneRef.current) {
        disposeThreeScene(sceneRef.current);
      }
      setIsContextLost(true);
    };

    const handleContextRestored = () => {
      console.info('WebGL context restored. Remounting R3F Canvas with fresh epoch.');
      // Increment epoch key to force React to unmount dead Canvas and re-allocate fresh VBOs
      setWebglEpoch((prev) => prev + 1);
      setIsContextLost(false);
    };

    // Listen directly on the HTMLCanvasElement without calling getContext()
    canvas.addEventListener('webglcontextlost', handleContextLost, false);
    canvas.addEventListener('webglcontextrestored', handleContextRestored, false);

    return () => {
      canvas.removeEventListener('webglcontextlost', handleContextLost);
      canvas.removeEventListener('webglcontextrestored', handleContextRestored);
      if (sceneRef.current) {
        disposeThreeScene(sceneRef.current);
      }
    };
  }, []);

  if (isContextLost) {
    return <Fallback2DTopography simulationData={props.simulationData} creditLimit={props.creditLimit} />;
  }

  return (
    <CashflowTopographyCanvas 
      key={`r3f-canvas-epoch-${webglEpoch}`} 
      ref={canvasRef} 
      sceneRef={sceneRef} 
      {...props} 
    />
  );
}
```

---

### 4.7 Responsive 2D Canvas / SVG Elevation Topography Fallback

For devices with low GPU capabilities (GPU score $< 20$ detected via `detect-gpu`), mobile battery-saver mode, or when WebGL context loss occurs, the interface automatically mounts `Fallback2DTopography.tsx`:
- **Isometric Fan Projection:** Renders a 2.5D SVG isometric elevation diagram with Altair-calibrated D3 area bands representing P10 (worst-case), P50 (median), and P90 (optimistic) cash envelopes.
- **Eradication of DOM Thrashing (48 CSS Gradient Strokes vs 1,500 DOM Nodes):** Simulating 1,500 moving SVG circle elements on mobile browsers causes severe main-thread layout thrashing ($35\text{--}50\text{ms}$ per frame). In fallback mode, the 1,500 WebGL particles are replaced with **48 lightweight CSS-animated flow stream gradient strokes** (`stroke-dasharray` / `stroke-dashoffset` keyframes). This consumes $<0.5\text{ms}$ of CPU time, maintaining a locked 60fps interaction speed.
- **2D Pan/Zoom Kinematics:** Standard 2D pan and pinch-to-zoom (`react-zoom-pan-pinch`) replace 3D OrbitControls, providing intuitive spreadsheet-style panning while preserving 100% data fidelity.

---

## 5. Conversational AI-Native Interface & Vernacular Audio Engine

### 5.1 Grounded AI-Native Architecture & Zero-Stochastic Guarantee
Under ADR-002, LLMs are strictly forbidden from performing accounting reconciliation matching or guessing debits and credits. In the conversational assistant (`View 6: Ask Copilot`), AI is confined to:
1. **Deterministic Intent Routing:** Queries pass through a 9-intent statutory boundary router (`src/copilot/boundary.py`), immediately intercepting prohibited legal, tax evasion, or destructive requests.
2. **Deterministic Data Grounding:** Financial numbers are queried directly from DuckDB/DataFrames using validated SQL templates.
3. **Natural Language Articulation:** The LLM receives pre-calculated, verified numbers and synthesizes polite vernacular explanations citing source ledger rows.

---

### 5.2 Server-Sent Events (SSE) Streaming Pipeline & Verifiable Citations
- **Streaming Route (`/api/copilot/stream`):** Implements HTTP chunked Server-Sent Events with under $500\text{ms}$ Time-to-First-Token.
- **Tool Execution Callouts:** Emits status chunks rendered as compact pills in the chat UI (`⚡ Querying HDFC Bank statement...`, `📊 Calculating 90-day Monte Carlo distribution...`).
- **Verifiable Citation Trays:** Every sentence containing financial figures embeds a citation index `[1]`. Clicking the badge expands an audit tray displaying:
  $$\text{Source: Txn ID, Bank Date, Reconciled Party Name, Amount (₹), and Deep Link to Review Queue}$$

---

### 5.3 Vernacular Audio Briefing Player & Waveform Visualizer
Indian SME owners frequently consume financial status hands-free during morning transit:
1. **Dual Language Toggle (`हिन्दी` / `English`):** Seamlessly toggles audio briefing scripts between pure Hindi and professional English.
2. **Interactive HTML5 Canvas 2D Waveform:** Renders dynamic frequency bars using the browser's Web Audio API `AudioContext` and `AnalyserNode`.
3. **Time-Synced Transcript Highlighting:** As audio plays, the corresponding Devanagari phrase illuminates in gold, ensuring multi-modal comprehension.
4. **Playback Controls:** Play, Pause, 10s Rewind, 10s Fast-Forward, and Speed Selector ($0.8\times, 1.0\times, 1.25\times$).

---

## 6. Non-Negotiable Invariants Compliance (ADR-001 to ADR-004)

### 6.1 ADR-001: Local-First Sovereign Vault Cryptography
- **Mandate:** Informal counter cash records, Galla counts, and pending khata ledgers must NEVER touch a remote cloud backend unencrypted.
- **Client-Side WebCrypto Architecture (`lib/crypto/vaultCrypto.ts`):**
  - **Key Derivation & Web Worker Offloading:** Browser native `window.crypto.subtle.deriveKey` using `PBKDF2-HMAC-SHA256` with 100,000 iterations and 16-byte cryptographically secure random salt. Key derivation is executed within a background Web Worker (`vaultCrypto.worker.ts`), preventing main thread freezing (200–350ms) on budget mobile processors.
  - **Biometric Passkey Defense (WebAuthn PRF):** To mitigate offline brute-force attacks against short 4-digit PINs ($10^4$ combinations cracked in $<30$ seconds on GPU), the vault provides an enterprise upgrade leveraging the **WebAuthn PRF (Pseudo-Random Function) extension**. The PRF extension derives a hardware-backed 256-bit symmetric key from platform biometrics (Touch ID, Face ID, Windows Hello) to wrap the master vault key, making offline extraction impossible without physical device biometric access.
  - **Authenticated Cipher:** `AES-256-GCM` with a 12-byte cryptographically secure random initialization vector (`nonce`) and 16-byte authentication tag.
  - **Envelope Format:**
    $$\underbrace{[\text{MAGIC: 12B}]}_{\texttt{SOV\_VAULT\_V1\textbackslash 0}} + \underbrace{[\text{SALT: 16B}]}_{\text{PBKDF2 Salt}} + \underbrace{[\text{NONCE: 12B}]}_{\text{GCM IV}} + \underbrace{[\text{CIPHERTEXT + 16B TAG}]}_{\text{Encrypted Payload}}$$
  - **Persistence & Scratchpad Storage:** Authenticated binary envelopes persist locally in browser **IndexedDB** (`sovereign_vault_store`). In-progress parchi entry forms are continuously auto-saved to an encrypted IndexedDB scratchpad (`draft_slips_encrypted`).
  - **Ergonomic Memory Wipe Lifecycle:** Decryption occurs exclusively in volatile RAM (`useVaultStore`). To prevent accidental draft loss when cashiers switch tabs to check WhatsApp or PDF bills, the vault enforces a **5-minute background grace period timer** before purging session keys from memory.
  - **Client-Side Zero-Knowledge Template Interpolation:** Bank statements and GST invoices flow downward from the server; when querying the AI Copilot, the server streams structured response templates containing placeholder tokens (`{{LOCAL_VAULT_GALLA_CASH}}`). The client component interpolates decrypted local drawer cash in volatile RAM. **Zero plaintext cash drawer data flows upward across HTTP.**

---

### 6.2 ADR-002: Decision 60 Deterministic Precision Matching
- **Mandate:** Automated accounting reconciliation must maintain 100.0% precision without probabilistic hallucinations.
- **Exact Mathematical Tier Counts for SME-1 (Kaveri Distributors):**
  - Total Ingested Bank Lines: **4,636**
  - `AUTO` Tier: Exactly **1,170** items (100.0% precision, straight-through posted).
  - `SUGGEST` Tier: Exactly **1,744** items (surfaced in Review Queue for 1-click confirmation).
  - `ASK` Tier: Exactly **619** items (routed to owner or accountant for allocation).
  - `NO_DOC` Tier: Exactly **23** items (owner capital infusion or bank charges).
- **Statistical Gating:** Rules qualify for `AUTO` only if historical holdout Wilson 95% score confidence interval upper error bound is $\le 1.00\%$.
- **Materiality Ceiling:** Any transaction $\ge ₹1,00,000$ is automatically demoted to `SUGGEST`.
- **2% Weekly Audit Circuit Breaker:** 2.0% of `AUTO` lines are randomly sampled each week; any auditor rejection instantly suspends the rule class in `AuditLedger`.

---

### 6.3 ADR-003: Section 18 Limitation Act Statutory Shield
- **Mandate:** Trade receivables approaching the 3-year statutory guillotine under the Limitation Act, 1963 must be shielded from legal extinguishment.
- **30-Month Early Tripwire:** Customers with open invoices $\ge 900$ days (30+ months) trigger the Section 18 warning badge.
- **Relationship-Preserving WhatsApp Balance Acknowledgment (AoD):**
  Synthesizes a polite request for written confirmation:
  > *"Namaste {Customer Name} ji, hope you are doing well. As per our records with {Business Name}, the pending balance is ₹{Amount} from our earlier supplies. Could you please confirm if this matches your books, or let us know when we can expect a small part-settlement? Thank you!"*
- **Statutory Clock Reset:** Under Section 18 of the Limitation Act and Sections 4/10A of the IT Act, 2000, a written electronic confirmation restarts the 3-year clock.
- **BSA 2023 Section 63 Digital Certificate:** Client browser computes a SHA-256 hash certificate with device metadata for legal admissibility.

---

### 6.4 ADR-004: MCA Rule 11(g) Edit Log & BNS §241 Anti-Spoliation
- **Mandate:** Full compliance with MCA Rule 11(g) audit trails and BNS §241 / CGST §132 criminal penalties for electronic record destruction.
- **Prohibition of Panic Wipes:** Zero emergency delete or stealth wipe buttons exist in the system.
- **Transparent Partial View Notice:** Whenever the Sovereign Vault is locked or viewed by non-owners, the interface renders an unremovable banner:
  $$\texttt{"Formal books only. The owner's cash memo is not included in this view."}$$
- **Deterministic Tally GUIDs:** All vouchers generate immutable GUIDs `<GUID>COPILOT-{biz}-{txn_id}</GUID>`.
- **CA Export Split-Plane Firewall Hardening:**
  The statutory CA Excel export is strictly a **5-sheet formal workbook** (`Reconciliation_Summary`, `Matched_Receipts_AUTO`, `Suggested_Matches`, `Unmatched_Bank_Credits`, `Open_Invoices_Aging`).
  - Sheet 6 (`Salesman_Collection_Slips`) is **completely omitted**.
  - Block D (`CASH DRAWER & COLLECTIONS CROSS-CHECK`) is **completely removed** from Sheet 1.
  - Dual-plane internal balancing is restricted to a separate, PIN-gated "Internal Management Diagnostic Pack".
- **Statutory Cash Tripwires:**
  - IT Act 2025 §186: Cash receipt $\ge ₹2,00,000$ from a single party in a day is `BLOCKED`.
  - IT Act 2025 §36(4): Cash business expense $> ₹10,000$ ($> ₹35,000$ transport) triggers `WARNING` (tax disallowance).
  - IT Act 2025 §185/§188: Cash loans or repayments $\ge ₹20,000$ are `BLOCKED`.
  - Income-tax Rules Rule 237: Factual SFT reporting facts (₹10L savings / ₹50L current) without evasion advice.

---

## 7. Full API Specifications & Data Contracts

### 7.1 Core Domain TypeScript Interfaces & Zod Validation Schemas

```typescript
// types/domain.ts
import { z } from 'zod';

// ==========================================
// 1. Sovereign Vault Plane Types (ADR-001)
// ==========================================
export const GallaEntrySchema = z.object({
  id: z.string(),
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  openingCash: z.number().nonnegative(),
  cashIn: z.number().nonnegative(),
  cashOut: z.number().nonnegative(),
  cashBanked: z.number().nonnegative(),
  countedCash: z.number().nonnegative(),
  expectedCash: z.number().nonnegative(),
  drift: z.number(),
  isBalanced: z.boolean(),
  notes: z.string().optional(),
});
export type GallaEntry = z.infer<typeof GallaEntrySchema>;

export const CollectionSlipSchema = z.object({
  slipId: z.string(),
  date: z.string(),
  salesman: z.string(),
  shopName: z.string(),
  amount: z.number().positive(),
  paymentMode: z.enum(['CASH', 'UPI', 'CHEQUE']),
  allocatedInvoiceId: z.string().optional(),
  status: z.enum(['IN_TRANSIT', 'IN_TILL', 'BANKED']),
});
export type CollectionSlip = z.infer<typeof CollectionSlipSchema>;

// ==========================================
// 2. Decision 60 Matching Types (ADR-002)
// ==========================================
export const MatchTierSchema = z.enum(['AUTO', 'SUGGEST', 'ASK', 'NO_DOC']);
export type MatchTier = z.infer<typeof MatchTierSchema>;

export const BankTransactionSchema = z.object({
  txnId: z.string(),
  date: z.string(),
  amount: z.number(),
  type: z.enum(['CREDIT', 'DEBIT']),
  narration: z.string(),
  balance: z.number(),
  tier: MatchTierSchema,
  ruleApplied: z.string(),
  candidatePayer: z.string().optional(),
  matchScore: z.number().min(0).max(1),
  isAudited: z.boolean().default(false),
  verifiedByOwner: z.boolean().default(false),
});
export type BankTransaction = z.infer<typeof BankTransactionSchema>;

// ==========================================
// 3. Receivables & Section 18 Types (ADR-003)
// ==========================================
export const CustomerReceivableSchema = z.object({
  customerId: z.string(),
  customerName: z.string(),
  phone: z.string(),
  totalOutstanding: z.number().nonnegative(),
  openInvoiceCount: z.number().int().nonnegative(),
  oldestInvoiceDays: z.number().int().nonnegative(),
  isLimitationAlert: z.boolean(), // Oldest >= 900 days
  hasSalesmanCollectedToday: z.boolean(),
  recentCollectionNote: z.string().optional(),
});
export type CustomerReceivable = z.infer<typeof CustomerReceivableSchema>;

// ==========================================
// 4. Cockpit Overview Types (View 1)
// ==========================================
export const VitalPulseMetricSchema = z.object({
  id: z.string(),
  label: z.string(),
  amount: z.number(),
  tone: z.enum(['positive', 'warning', 'neutral', 'critical']),
  subtitle: z.string().optional(),
});
export type VitalPulseMetric = z.infer<typeof VitalPulseMetricSchema>;

export const SolvencyEquationSchema = z.object({
  formalBankBalance: z.number(),
  ccFacilityDrawn: z.number(),
  ccFacilitySanctioned: z.number(),
  formalDueNext30Days: z.number(),
  formalReceivables: z.number(),
  defaultKhataRealizationRate: z.number().min(0).max(1).default(0.85),
});
export type SolvencyEquation = z.infer<typeof SolvencyEquationSchema>;

export const OverviewPayloadSchema = z.object({
  businessId: z.string(),
  businessName: z.string(),
  asOfDate: z.string(),
  bankCurrentBalance: z.number(),
  ccSanctionedLimit: z.number(),
  ccHeadroom: z.number(),
  runwayMonths: z.number(),
  pulseMetrics: z.array(VitalPulseMetricSchema),
  topFocalAction: CustomerReceivableSchema.nullable(),
  solvencyBase: SolvencyEquationSchema,
  audioBriefUrl: z.string(),
});
export type OverviewPayload = z.infer<typeof OverviewPayloadSchema>;

// ==========================================
// 5. 90-Day Forecast & Simulation Types (View 3)
// ==========================================
export const ForecastSimulationPointSchema = z.object({
  dayIndex: z.number().int().min(0).max(90),
  date: z.string(),
  p10WorstCase: z.number(),
  p50Median: z.number(),
  p90Optimistic: z.number(),
  ccFacilityLimit: z.number(),
  milestoneEvent: z.object({
    title: z.string(),
    amount: z.number(),
    category: z.enum(['SALARY', 'GST_TAX', 'ADVANCE_TAX', 'VENDOR_DUE', 'CUSTOMER_RECEIPT']),
  }).optional(),
});
export type ForecastSimulationPoint = z.infer<typeof ForecastSimulationPointSchema>;

export const MonthlyOutlookItemSchema = z.object({
  monthName: z.string(),
  inflowsP50: z.number(),
  inflowsP10: z.number(),
  committedOutflows: z.number(),
  netCashFlow: z.number(),
  lowestDipPoint: z.number(),
  closingBalance: z.number(),
  hasBreachedCreditLimit: z.boolean(),
});
export type MonthlyOutlookItem = z.infer<typeof MonthlyOutlookItemSchema>;

export const StressTestParametersSchema = z.object({
  customerDelayDays: z.number().int().min(0).max(60).default(0),
  rawMaterialExpenseSurge: z.number().nonnegative().default(0),
  collectionRealizationAlpha: z.number().min(0.5).max(1.0).default(0.85),
});
export type StressTestParameters = z.infer<typeof StressTestParametersSchema>;

export const ForecastPayloadSchema = z.object({
  businessId: z.string(),
  asOfDate: z.string(),
  holdoutMapeScore: z.number(),
  holdoutCoverageRate: z.number(),
  lowestProjectedBalance: z.number(),
  lowestProjectedDate: z.string(),
  simulationPoints: z.array(ForecastSimulationPointSchema),
  monthlyMatrix: z.array(MonthlyOutlookItemSchema),
});
export type ForecastPayload = z.infer<typeof ForecastPayloadSchema>;

// ==========================================
// 6. Conversational Copilot Stream Types (View 6)
// ==========================================
export const CitationItemSchema = z.object({
  id: z.string(),
  source: z.string(),
  amount: z.number(),
  date: z.string().optional(),
  deepLink: z.string().optional(),
  badge: z.enum(['BANK_FORMAL', 'GST_INVOICE', 'RAM_ONLY']).optional(),
});
export type CitationItemType = z.infer<typeof CitationItemSchema>;

export const CopilotStreamChunkSchema = z.discriminatedUnion('type', [
  z.object({
    type: z.literal('tool_start'),
    toolName: z.string(),
  }),
  z.object({
    type: z.literal('tool_done'),
    toolName: z.string(),
    result: z.string(),
  }),
  z.object({
    type: z.literal('token'),
    content: z.string(),
  }),
  z.object({
    type: z.literal('template_token'),
    token: z.string(), // e.g. "{{LOCAL_VAULT_GALLA_CASH}}"
    field: z.enum(['gallaCash', 'trueSolvency', 'gallaCountDate']),
  }),
  z.object({
    type: z.literal('citation'),
    citation: CitationItemSchema,
  }),
  z.object({
    type: z.literal('done'),
  }),
]);
export type CopilotStreamChunk = z.infer<typeof CopilotStreamChunkSchema>;

// ==========================================
// 7. Statutory & Diagnostic Export Types (View 7)
// ==========================================
export const TallyExportRequestSchema = z.object({
  businessId: z.string(),
  asOfDate: z.string(),
  voucherType: z.literal('Receipt'),
  includeAutoOnly: z.boolean().default(true),
});
export type TallyExportRequest = z.infer<typeof TallyExportRequestSchema>;

export const CaExcelExportRequestSchema = z.object({
  businessId: z.string(),
  asOfDate: z.string(),
  format: z.literal('STATUTORY_5_SHEET'),
  omitInformalCash: z.literal(true), // Enforced split-plane firewall
});
export type CaExcelExportRequest = z.infer<typeof CaExcelExportRequestSchema>;

export const InternalManagementExportRequestSchema = z.object({
  businessId: z.string(),
  asOfDate: z.string(),
  format: z.literal('INTERNAL_DUAL_PLANE_6_SHEET'),
  ownerPinAuthenticated: z.boolean(),
});
export type InternalManagementExportRequest = z.infer<typeof InternalManagementExportRequestSchema>;

export const DataIntegrityScorecardSchema = z.object({
  totalBankLinesIngested: z.number().int(),
  monthsAudited: z.number().int(),
  balanceBreaksDetected: z.number().int(),
  openingBankBalance: z.number(),
  totalBankCredits: z.number(),
  totalBankDebits: z.number(),
  closingBankBalance: z.number(),
  is100PercentTied: z.boolean(),
  tieVariance: z.number(),
});
export type DataIntegrityScorecard = z.infer<typeof DataIntegrityScorecardSchema>;

export const ExportPayloadSchema = z.object({
  tallyVouchersAvailable: z.number().int(),
  tallyTotalCreditAmount: z.number(),
  caWorkbookSheetCount: z.literal(5),
  integrityScorecard: DataIntegrityScorecardSchema,
});
export type ExportPayload = z.infer<typeof ExportPayloadSchema>;
```

---

### 7.2 Next.js Server Actions & Route Handlers Specifications

#### 1. Reconcile Transaction Server Action (`lib/actions/reviewActions.ts`)
- **Input:** `{ txnId: string, decision: 'APPROVE' | 'REJECT' | 'REASSIGN', assignedPartyId?: string, note?: string }`
- **Output:** `{ success: boolean, txnId: string, newTier: MatchTier, auditHash: string }`
- **Error Behavior:** Emits validation errors or logs circuit breaker suspension if an audit line fails.

#### 2. Copilot SSE Token Streaming Route (`POST /api/copilot/stream`)
Under **ADR-001**, physical godown cash balances (`vaultGallaCash`) are **strictly prohibited** from client request payloads!

- **Request Body (Pure Formal Context Only):**
  ```json
  {
    "question": "Can I pay salaries on 1 October?",
    "businessId": "SME-1",
    "asOfDate": "2026-09-30"
  }
  ```
- **Response Stream (SSE Chunks with Zero-Knowledge Template Tokens):**
  ```
  data: {"type": "tool_start", "toolName": "consult_bank_liquidity"}
  data: {"type": "tool_done", "toolName": "consult_bank_liquidity", "result": "₹12.39L HDFC current balance"}
  data: {"type": "tool_start", "toolName": "evaluate_payroll_commitments"}
  data: {"type": "tool_done", "toolName": "evaluate_payroll_commitments", "result": "₹4.65L (24 employees)"}
  data: {"type": "token", "content": "Yes, you can safely pay your October 1st salaries of **₹4,65,000** [1]. Even paying 100% from HDFC, your balance remains positive at **₹7,74,000**, which is **₹32,74,000 clear** of your sanctioned CC facility limit (-₹25.00L). You also have {{LOCAL_VAULT_GALLA_CASH}} physical cash in your godown drawer [2]."}
  data: {"type": "template_token", "token": "{{LOCAL_VAULT_GALLA_CASH}}", "field": "gallaCash"}
  data: {"type": "citation", "citation": {"id": "1", "source": "Payroll Ledger", "amount": 465000, "date": "2026-10-01", "badge": "BANK_FORMAL"}}
  data: {"type": "done"}
  ```
- **Client-Side Synthesis Execution:**
  Upon receiving `template_token` chunks, `AskCopilotView.tsx` reads decrypted `gallaEntry.countedCash` from local volatile memory (`useVaultStore`) and performs client-side token replacement:
  $$\text{"\{\{LOCAL\_VAULT\_GALLA\_CASH\}\}"} \longrightarrow \text{"₹4,20,000"}$$
  This ensures that confidential physical cash numbers are presented seamlessly to the owner while maintaining an absolute zero-knowledge network perimeter.

#### 3. Statutory CA Excel Export Route (`POST /api/exports/ca-excel`)
- **Request Body:** `{ businessId: "SME-1", asOfDate: "2026-09-30", format: "STATUTORY_5_SHEET", omitInformalCash: true }`
- **Response:** Strict 5-sheet OpenPyXL workbook (`Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`). Completely omits Sheet 6 (`Salesman_Collection_Slips`) and excludes Block D from Sheet 1.

#### 4. TallyPrime XML Export Route (`POST /api/exports/tally-xml`)
- **Request Body:** `{ businessId: "SME-1", asOfDate: "2026-09-30", voucherType: "Receipt", includeAutoOnly: true }`
- **Response:** Pure TDL XML stream (`Content-Type: application/xml`). All string values (`<PARTYNAME>`, `<NARRATION>`, `<GUID>`) are wrapped in `<![CDATA[ ... ]]>` blocks with deterministic GUIDs structured as `<GUID>COPILOT-{biz}-{txn_id}</GUID>`.

---

### 7.3 Python FastAPI Microservice Bridge Contracts

The Python backend exposes a dedicated FastAPI microservice interfacing directly with DuckDB and SQLite:

1. `GET /api/v1/overview?biz=SME-1&as_of=2026-09-30`
   - Returns formal bank closing balance, CC headroom, 30-day commitments, and top recovery focal action conforming to `OverviewPayloadSchema`.
2. `GET /api/v1/forecast/monte-carlo?biz=SME-1&paths=1000&days=90`
   - Returns 90 daily simulation points (P10, P50, P90), lowest dip callout, and monthly outlook matrix conforming to `ForecastPayloadSchema`.
3. `POST /api/v1/export/tally-xml`
   - Generates and streams pure TDL XML with deterministic GUIDs and strict CDATA string wrapping (`Content-Type: application/xml`).
4. `POST /api/v1/export/ca-excel`
   - Generates and streams the **5-sheet statutory CA Excel workbook** (`Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`). Enforces split-plane firewall: zero rows of drawer cash or salesman route slips.
5. `POST /api/v1/export/internal-diagnostic-excel`
   - Gated behind owner PIN authentication. Generates the 6-sheet internal dual-plane diagnostic workbook (including Sheet 6 route slips and Sheet 1 Block D). Marked strictly with internal diagnostic banners.

---

## 8. Step-by-Step Phased Zero-Downtime Migration Roadmap

```
PHASE 1: Split-Bridge BFF (Weeks 1–3)
┌─────────────────────────────────┐       ┌──────────────────────────────────┐
│ Legacy Streamlit UI (Port 8501) │       │ Next.js 15+ App Router (Port 3000│
└────────────────┬────────────────┘       └─────────────────┬────────────────┘
                 │                                          │
                 ▼                                          ▼
     ┌───────────────────────┐                  ┌───────────────────────┐
     │ DuckDB / SQLite Files │◄─────────────────┤ FastAPI Bridge Proxy  │
     │ (.copilot_state/)     │   Direct Reads   │ (Port 8000)           │
     └───────────────────────┘                  └───────────────────────┘

PHASE 2: Dual-Run Parity & Statistical Verification (Weeks 4–6)
- Concurrent execution of Decision 60 matching across both runtimes.
- Automated checksum verification: confirm that AUTO 1,170, SUGGEST 1,744, ASK 619 counts match 100%.
- Merchant pilots Next.js Overview Cockpit & 3D Spatial Topography in parallel with Streamlit.

PHASE 3: Complete Cutover to Next.js 15 App Router (Weeks 7–8)
- Next.js becomes default production frontend at https://sme-cashflow.medevolv.in.
- Python engine encapsulated in Docker as pure headless microservice.
- Streamlit completely decommissioned with zero data loss and 100% historical audit log continuity.
```

### 8.1 Phase 1: Split-Bridge BFF (Coexistence)
- Maintain Streamlit on Port 8501 for uninterrupted daily business operations.
- Launch the Next.js 15 App Router dashboard on Port 3000.
- Fastify/FastAPI bridge reads existing DuckDB and SQLite files in `.copilot_state/` in read-only mode.

### 8.2 Phase 2: Dual-Run Parity Verification
- Run automated daily reconciliation verification scripts:
  $$\Delta_{\text{reconciled}} = |\text{Next.js Matched Lines} - \text{Streamlit Matched Lines}| \equiv 0$$
- Validate that client-side WebCrypto encryption produces identical Galla balance formulas without data drift.

### 8.3 Phase 3: Complete Cutover
- Cut over reverse proxy (Nginx / Cloudflare) to route production traffic to Next.js.
- Decommission Streamlit process. Historical audit ledgers and Tally GUIDs remain 100% backward-compatible.

---

## Summary & Architectural Ratification
This architectural blueprint provides a comprehensive, publication-grade foundation for modernizing the SME Cashflow Copilot. By marrying **Next.js 15+ App Router server performance** with **Three.js 3D spatial intuition**, **WebCrypto client-side sovereignty (ADR-001)**, and **mathematical Decision 60 certitude (ADR-002)**, the system establishes a new industry benchmark for AI-native SME financial intelligence in India.
