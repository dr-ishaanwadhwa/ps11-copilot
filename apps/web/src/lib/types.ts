import { z } from 'zod';

// ==========================================
// 1. Sovereign Vault Plane Types (ADR-001)
// ==========================================
export const GallaEntrySchema = z.object({
  id: z.string(),
  date: z.string(),
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
  candidatePayer: z.string().nullish(),
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
  // The API serialises absent optionals as null, so these must accept null as well as undefined.
  recentCollectionNote: z.string().nullish(),
  salesmanName: z.string().nullish(),
  collectedTodayAmount: z.number().nullish(),
  collectedSlipId: z.string().nullish(),
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
  }).nullish(), // API sends null on days with no milestone
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

export const ForecastPlainSummarySchema = z.object({
  lowestBalance: z.number(),
  lowestDate: z.string(),
  worstCaseLowestBalance: z.number(),
  creditLimit: z.number(),
  breachesCreditLimit: z.boolean(),
  scenarioActive: z.boolean(),
  baselineLowestBalance: z.number().nullable(),
  topCollectionAction: z
    .object({
      customerName: z.string(),
      outstanding: z.number(),
      oldestInvoiceDays: z.number(),
    })
    .nullable(),
  headline: z.string(),
  detail: z.string(),
});
export type ForecastPlainSummary = z.infer<typeof ForecastPlainSummarySchema>;

export const ForecastPayloadSchema = z.object({
  businessId: z.string(),
  asOfDate: z.string(),
  holdoutMapeScore: z.number(),
  holdoutCoverageRate: z.number(),
  // Honest measured holdout values. The two legacy fields above are hard-coded constants on the API.
  holdoutMapeMeasured: z.number().nullish(),
  holdoutCoverageMeasured: z.number().nullish(),
  lowestProjectedBalance: z.number(),
  lowestProjectedDate: z.string(),
  simulationPoints: z.array(ForecastSimulationPointSchema),
  monthlyMatrix: z.array(MonthlyOutlookItemSchema),
  plainSummary: ForecastPlainSummarySchema.nullish(),
});
export type ForecastPayload = z.infer<typeof ForecastPayloadSchema>;

// ==========================================
// 6. Conversational Copilot Stream Types (View 6)
// ==========================================
export const CitationItemSchema = z.object({
  id: z.string(),
  source: z.string(),
  amount: z.number(),
  date: z.string().nullish(),
  deepLink: z.string().nullish(),
  badge: z.enum(['BANK_FORMAL', 'GST_INVOICE', 'RAM_ONLY']).nullish(),
});
export type CitationItem = z.infer<typeof CitationItemSchema>;

export const ToolExecutionStepSchema = z.object({
  toolName: z.string(),
  status: z.enum(['running', 'completed', 'failed']),
  resultSummary: z.string().optional(),
});
export type ToolExecutionStep = z.infer<typeof ToolExecutionStepSchema>;

export const CopilotMessageSchema = z.object({
  id: z.string(),
  role: z.enum(['user', 'assistant']),
  content: z.string(),
  hindiSummary: z.string().optional(),
  toolExecutions: z.array(ToolExecutionStepSchema).optional(),
  citations: z.array(CitationItemSchema).optional(),
  timestamp: z.string(),
});
export type CopilotMessage = z.infer<typeof CopilotMessageSchema>;

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
    token: z.string(),
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
  omitInformalCash: z.literal(true),
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

// ==========================================
// 8. Review queue / receivables / reconcile envelopes (API v1)
// ==========================================
export const ReviewQueuePayloadSchema = z.object({
  businessId: z.string(),
  totalCount: z.number().int(),
  countsByTier: z.record(z.string(), z.number().int()),
  items: z.array(BankTransactionSchema),
});
export type ReviewQueuePayload = z.infer<typeof ReviewQueuePayloadSchema>;

export const ReceivablesPayloadSchema = z.object({
  businessId: z.string(),
  totalOutstanding: z.number(),
  overdueCount: z.number().int(),
  limitationAlertCount: z.number().int(),
  customers: z.array(CustomerReceivableSchema),
});
export type ReceivablesPayload = z.infer<typeof ReceivablesPayloadSchema>;

export const ReconcileDecisionSchema = z.enum(['APPROVE', 'REJECT', 'REASSIGN']);
export type ReconcileDecision = z.infer<typeof ReconcileDecisionSchema>;

export const ReconcileResponseSchema = z.object({
  success: z.boolean(),
  txnId: z.string(),
  newStatus: z.string(),
  auditHash: z.string(),
});
export type ReconcileResponse = z.infer<typeof ReconcileResponseSchema>;

// ==========================================
// Indian Lakh / Crore Numeral Formatter
// ==========================================
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

  const formatter = new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: options.showDecimals ? 2 : 0,
    maximumFractionDigits: options.showDecimals ? 2 : 0,
  });

  const formattedStr = formatter.format(absVal);
  return `${signPrefix}${formattedStr}`;
}
