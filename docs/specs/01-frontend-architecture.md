# 01. Frontend Architecture Specification

**Specification ID:** `SPEC-FE-001`  
**Classification:** Modular Engineering Specification  
**Target Repository:** `/Users/ishaanwadhwa/Projects/ps11-copilot`  
**Related Blueprint:** `docs/blueprints/nextjs-threejs-cashflow-copilot.md` §2  
**Related Invariants:** ADR-001 (Sovereign Vault), ADR-004 (MCA Rule 11(g) / Anti-Spoliation)

---

## 1. Architectural Overview & Rationale

The Next.js 15+ App Router architecture for the SME Cashflow Copilot is designed to solve the critical operational bottlenecks of legacy monolithic accounting UIs (specifically full-script re-execution, WebSocket disconnect amnesia, and cognitive overload from flat 2D ledgers).

The system implements a **Dual-Plane Architecture**:
1. **The Formal Public Plane (Plane A):** Bank statements, Cash-Credit (CC) hypothecation facilities, and GST invoices that are pre-rendered server-side via React Server Components (RSC) with zero client JavaScript weight.
2. **The Sovereign Operating Cash Plane (Plane B):** Physical counter till cash (*Galla*), godown safe holdings, and salesman route collection slips (*Kaccha Parchi*) managed strictly in-browser via the Web Crypto API and client-hydrated Zustand memory stores.

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

---

## 2. File System & Route Hierarchy

The application leverages Next.js 15+ App Router Route Groups `(auth)` and `(dashboard)` to cleanly isolate authentication and PIN security gates from the interactive dashboard environment:

```
apps/web/src/
├── app/
│   ├── layout.tsx                        # Global root layout: Fonts, providers, theme
│   ├── globals.css                       # Tailwind CSS v4 design tokens and utilities
│   ├── page.tsx                          # Root index: Redirects -> /overview
│   │
│   ├── (auth)/                           # Isolated security shell (no dashboard chrome)
│   │   └── lock/
│   │       ├── page.tsx                  # PIN-gated unlock screen (WebCrypto PBKDF2)
│   │       └── layout.tsx                # Centered, distraction-free cryptographic viewport
│   │
│   ├── (dashboard)/                      # Authenticated master shell
│   │   ├── layout.tsx                    # Shell layout: Collapsible Sidebar, TopNav, ⌘K
│   │   ├── overview/                     # View 1: Overview Cockpit ("Aaj Ka Hisaab")
│   │   │   ├── page.tsx                  # RSC layout + client-hydrated islands
│   │   │   ├── loading.tsx               # Perceived-performance skeleton layout
│   │   │   └── error.tsx                 # flow-errors boundary preserving vault RAM
│   │   ├── cash-book/                    # View 2: Cash Book & Sovereign Vault
│   │   │   ├── page.tsx                  # Interactive 5-part drawer balancing cockpit
│   │   │   └── loading.tsx
│   │   ├── forecast/                     # View 3: 90-Day Cash Dip Simulation
│   │   │   ├── page.tsx                  # 3D spatial canvas + 2D fallback toggle
│   │   │   └── loading.tsx
│   │   ├── review/                       # View 4: Decision 60 Review Queue
│   │   │   ├── page.tsx                  # Virtualized 3-pane keyboard triage grid
│   │   │   └── loading.tsx
│   │   ├── receivables/                  # View 5: Receivables & Recovery
│   │   │   ├── page.tsx                  # Section 18 Limitation Act Shield & MSMED alerts
│   │   │   └── loading.tsx
│   │   ├── copilot/                      # View 6: Ask Copilot Grounded Chat
│   │   │   ├── page.tsx                  # Conversational AI drawer with citation trays
│   │   │   └── loading.tsx
│   │   └── exports/                      # View 7: Statutory Exports & Data Quality
│   │       ├── page.tsx                  # Tally XML vouchers + CA 5-sheet Excel
│   │       └── loading.tsx
│   │
│   └── api/                              # Route Handlers for streaming and exports
│       ├── copilot/
│       │   ├── stream/route.ts           # Token streaming SSE route (zero-knowledge)
│       │   └── transcribe/route.ts       # Audio transcription endpoint
│       └── exports/
│           ├── tally-xml/route.ts        # Pure XML voucher download stream
│           ├── ca-excel/route.ts         # CA 5-sheet statutory Excel workbook stream
│           └── internal-diagnostic/route.ts # PIN-gated 6-sheet dual-plane workbook stream
```

---

## 3. Dual-Plane Hydration Barrier (Zero SSR Mismatch Guarantee)

### 3.1 The Problem
In standard SSR architectures, rendering client-held state (e.g., volatile drawer cash ₹4.20L) on top of server data (Bank balance ₹12.39L) results in hydration mismatch errors:
`Text content did not match: Server "₹12.39L" vs Client "₹16.59L"`.
Furthermore, passing drawer cash to the server to pre-render True Solvency violates **ADR-001** (zero cloud plaintext leakage).

### 3.2 The Hydration Barrier Solution
To permanently eliminate SSR hydration mismatches while strictly safeguarding confidential cash data:
1. **Client-Hydrated Islands:** All UI elements that synthesize physical drawer cash, salesman collection slips, or True Solvency (`Bank + Cash − Commitments`) are packaged inside client-hydrated islands (`ClientVaultDisplay`, `ClientPulseTile`, `ClientTrueSolvencyCard`).
2. **Neutral SSR Placeholder:** During server rendering, the component outputs a lightweight, neutral skeleton with identical spatial dimensions, guaranteeing Cumulative Layout Shift ($\text{CLS} < 0.05$).
3. **RAM Subscription Gate:** The island mounts via `useSyncExternalStore` or dynamic client-only execution (`dynamic(..., { ssr: false })`). Upon browser hydration, it subscribes to `useVaultStore` in volatile memory:
   - If vault is **Locked**: Renders formal bank figures with a transparent lock indicator.
   - If vault is **Unlocked**: Smoothly animates to synthesized True Solvency (`₹16.59L`), reading raw BLOB handles in volatile memory without network round-trips.

```tsx
// apps/web/src/components/vault/ClientVaultDisplay.tsx
'use client'

import React, { useSyncExternalStore } from 'react';
import { useVaultStore } from '@/lib/store';
import { formatINR } from '@/lib/types';

interface ClientVaultDisplayProps {
  bankBalance: number;
  commitments: number;
  className?: string;
}

export function ClientVaultDisplay({
  bankBalance,
  commitments,
  className = '',
}: ClientVaultDisplayProps) {
  const isHydrated = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  );
  
  const { isUnlocked, gallaEntry } = useVaultStore();

  if (!isHydrated) {
    return (
      <div className={`h-16 w-full animate-pulse rounded-lg bg-formal-border/30 ${className}`} />
    );
  }

  const drawerCash = isUnlocked ? (gallaEntry?.countedCash ?? 0) : 0;
  const netUsable = bankBalance + drawerCash - commitments;

  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <div className="flex items-baseline gap-2">
        <span className="text-3xl font-bold font-mono tracking-tight text-formal-text">
          {formatINR(netUsable, { compact: true })}
        </span>
        {isUnlocked ? (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-100 text-emerald-800">
            True Solvency ✓
          </span>
        ) : (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600">
            Formal Only 🔒
          </span>
        )}
      </div>
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

## 4. Server Actions for Mutations with Optimistic Rollbacks

All mutations on the formal ledger (reconciliation approval, candidate payer re-assignment, export generation) execute via Next.js Server Actions with strict Zod runtime validation:

```typescript
// apps/web/src/lib/actions/reviewActions.ts
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
  const parsed = ReconcileSchema.safeParse(input);
  if (!parsed.success) {
    return { success: false, error: 'Invalid mutation parameters' };
  }

  try {
    const bridgeUrl = process.env.PYTHON_BRIDGE_URL || 'http://localhost:8000';
    const response = await fetch(`${bridgeUrl}/api/review/reconcile`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(parsed.data),
    });

    if (!response.ok) {
      throw new Error(`Python bridge engine returned ${response.status}`);
    }

    const payload = await response.json();
    revalidatePath('/review');
    revalidatePath('/overview');

    return {
      success: true,
      txnId: parsed.data.txnId,
      newStatus: payload.status,
      auditHash: payload.auditHash,
    };
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : 'Server action failed';
    return { success: false, error: errorMsg };
  }
}
```

---

## 5. Client State Management Architecture (Zustand & WebCrypto)

Interactive client state is partitioned into three dedicated stores to maintain clear boundaries between cryptographic vault data, URL-driven cockpit settings, and optimistic mutation undo queues:

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

1. **`useVaultStore` (ADR-001 Sovereign Vault Memory):**
   - Holds decrypted drawer cash balances and active collection slips in volatile RAM.
   - Derives session keys via PBKDF2 (100k iterations) and AES-256-GCM.
   - Enforces a 5-minute background tab grace timer (preventing cashier lockout during WhatsApp checks).
   - Enforces a 15-minute continuous inactivity auto-lock and memory wipe.
2. **`useCockpitStore` (UI Parameter Plane):**
   - Stores user-selected presentation modes (`formal` vs `sovereign`), language preference (`hi` vs `en`), and recovery collection haircut rate ($\alpha \in [0.5, 1.0]$).
3. **`useUndoStore` (`flow-errors` Optimistic Mutation Engine):**
   - Implements a 10-second countdown safety window with an interactive "Undo" toast before committing high-volume reconciliations to the server.

---

## 6. Fault Tolerance & Perceived Performance

### 6.1 Skeleton Screens (`flow-empty-states`)
Every route features a matching `loading.tsx` component that mirrors the exact grid, header, and card shapes of the completed view. Shimmering animated CSS pulses maintain visual rhythm and prevent jarring layout jumps.

### 6.2 Error Boundaries (`flow-errors`)
When network timeouts or microservice bridge errors occur, the Next.js `error.tsx` boundary intercepts the failure without discarding volatile RAM vault keys. The user receives a clear, non-technical explanation, a manual retry action button, and reassurance that their entered drawer counts remain safely preserved in local memory.
