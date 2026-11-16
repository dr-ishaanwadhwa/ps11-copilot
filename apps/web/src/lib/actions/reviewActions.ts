'use server';

import { ReconcileResponseSchema } from '../types';
import type { ReconcileDecision, ReconcileResponse } from '../types';

export interface ReviewDecisionInput {
  txnId: string;
  decision: ReconcileDecision;
  assignedPartyId?: string;
  note?: string;
}

export type ReviewDecisionResult =
  | { ok: true; result: ReconcileResponse }
  | { ok: false; error: string };

/**
 * Posts a Decision 60 review decision to POST /api/v1/review/reconcile (MCA Rule 11(g) audit ledger).
 * Runs on the server so the browser never needs the upstream address. The body carries only the
 * transaction id, the decision and an optional note: no vault values (ADR-001).
 */
export async function submitReviewDecision(input: ReviewDecisionInput): Promise<ReviewDecisionResult> {
  const base = (process.env.COPILOT_API_BASE ?? 'http://127.0.0.1:8000').replace(/\/+$/, '');
  if (!input.txnId || !['APPROVE', 'REJECT', 'REASSIGN'].includes(input.decision)) {
    return { ok: false, error: 'Invalid review decision.' };
  }
  try {
    const res = await fetch(`${base}/api/v1/review/reconcile`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        txnId: input.txnId,
        decision: input.decision,
        ...(input.assignedPartyId ? { assignedPartyId: input.assignedPartyId } : {}),
        ...(input.note ? { note: input.note.slice(0, 500) } : {}),
      }),
      cache: 'no-store',
    });
    if (!res.ok) return { ok: false, error: `The API rejected the decision (${res.status}).` };
    const parsed = ReconcileResponseSchema.safeParse(await res.json());
    if (!parsed.success || !parsed.data.success) return { ok: false, error: 'The API returned an unexpected response.' };
    return { ok: true, result: parsed.data };
  } catch {
    return { ok: false, error: 'The API is unreachable.' };
  }
}
