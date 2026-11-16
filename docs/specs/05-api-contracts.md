# 05. API Contracts & TypeScript / Zod Schemas Specification

**Specification ID:** `SPEC-API-005`  
**Classification:** Modular Engineering Specification  
**Target Repository:** `/Users/ishaanwadhwa/Projects/ps11-copilot`  
**Related Blueprint:** `docs/blueprints/nextjs-threejs-cashflow-copilot.md` §7  
**Related Invariants:** ADR-001 (Zero Plaintext Cash), ADR-002 (Decision 60 Precision), ADR-004 (Statutory Split-Plane Firewall)

---

## 1. Domain Schemas (TypeScript & Zod)

The system enforces strict type safety and schema validation across all boundaries using Zod.

```typescript
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
  isLimitationAlert: z.boolean(), // Oldest >= 900 days (30+ months)
  hasSalesmanCollectedToday: z.boolean(),
  recentCollectionNote: z.string().optional(),
  salesmanName: z.string().optional(),
  collectedTodayAmount: z.number().optional(),
  collectedSlipId: z.string().optional(),
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
export type CitationItem = z.infer<typeof CitationItemSchema>;

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

## 2. Next.js Server Actions Specification

### 2.1 `reconcileMatchAction(input)`
- **Module:** `lib/actions/reviewActions.ts`
- **Method:** Next.js Server Action (`'use server'`)
- **Input Parameters:**
  - `txnId: string`
  - `decision: 'APPROVE' | 'REJECT' | 'REASSIGN'`
  - `assignedPartyId?: string`
  - `note?: string`
- **Output:**
  - `{ success: true, txnId: string, newStatus: string, auditHash: string }`
  - `{ success: false, error: string }`
- **Side Effects:** Calls Python bridge service, posts immutable audit trail record under MCA Rule 11(g), revalidates paths `/review` and `/overview`.

---

## 3. Next.js Route Handlers Specification

### 3.1 Conversational Token Stream (`POST /api/copilot/stream`)
- **Request Headers:** `Content-Type: application/json`
- **Request Body (Pure Formal Context):**
  ```json
  {
    "question": "Can I pay salaries on 1 October?",
    "businessId": "SME-1",
    "asOfDate": "2026-09-30"
  }
  ```
  *(Note: Zero plaintext drawer cash numbers are permitted in request payloads under ADR-001).*
- **Response Headers:** `Content-Type: text/event-stream; charset=utf-8`
- **Response Body:** Chunked SSE stream formatted as JSON payloads conforming to `CopilotStreamChunkSchema`.

### 3.2 Pure TDL XML Voucher Export (`POST /api/exports/tally-xml`)
- **Request Body:** Conforms to `TallyExportRequestSchema`.
- **Response Headers:** `Content-Type: application/xml`, `Content-Disposition: attachment; filename="tally_receipts.xml"`
- **Response Body:** XML string with CDATA wrapping and deterministic GUIDs `<GUID>COPILOT-{biz}-{txn_id}</GUID>`.

### 3.3 Statutory CA 5-Sheet Excel Export (`POST /api/exports/ca-excel`)
- **Request Body:** Conforms to `CaExcelExportRequestSchema`.
- **Response Headers:** `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `Content-Disposition: attachment; filename="CA_Reconciliation_Statutory.xlsx"`
- **Invariants:** Strictly 5 sheets. Omits Sheet 6 (`Salesman_Collection_Slips`) and deletes Block D from Sheet 1.

---

## 4. Python FastAPI Microservice Bridge Contracts

The Next.js BFF connects to a headless Python FastAPI microservice on Port 8000:

| HTTP Verb | Path | Request Payload | Response Schema | Description |
|---|---|---|---|---|
| `GET` | `/api/v1/overview` | Query: `biz, as_of` | `OverviewPayloadSchema` | Pre-rendered formal bank balances, CC headroom, 30-day commitments. |
| `GET` | `/api/v1/forecast/monte-carlo` | Query: `biz, paths, days` | `ForecastPayloadSchema` | 90 daily simulation points (P10, P50, P90) and monthly outlook matrix. |
| `POST` | `/api/v1/review/reconcile` | `ReconcileSchema` | `{ status, auditHash }` | Deterministic Decision 60 reconciliation engine mutation. |
| `POST` | `/api/v1/export/tally-xml` | `TallyExportRequestSchema` | XML binary stream | TallyPrime XML receipt voucher generator. |
| `POST` | `/api/v1/export/ca-excel` | `CaExcelExportRequestSchema` | XLSX binary stream | Strict 5-sheet statutory reconciliation pack. |
| `POST` | `/api/v1/export/internal-diagnostic-excel` | `InternalManagementExportRequestSchema` | XLSX binary stream | PIN-gated 6-sheet dual-plane diagnostic pack. |
