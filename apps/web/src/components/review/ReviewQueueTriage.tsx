'use client';

import React, { useState } from 'react';
import { formatINR } from '@/lib/types';
import type { BankTransaction, MatchTier } from '@/lib/types';
import { Check, X, ShieldCheck, Filter, Search, ArrowRight, CornerDownLeft, Ban } from 'lucide-react';
import { fetchReviewQueue, useApiResource } from '@/lib/api';
import { useCockpitStore } from '@/lib/store';
import { submitReviewDecision } from '@/lib/actions/reviewActions';
import { DataSourceBadge } from '@/components/vault/ClientVaultDisplay';

// SAMPLE DATA ONLY: shown (with a "Sample data" label) when the API cannot be reached.
const mockTransactions: BankTransaction[] = [
  {
    txnId: 'TXN-1002345',
    date: '2026-09-30',
    amount: 45000,
    type: 'CREDIT',
    narration: 'CMS/DEP/CDM-9023/KAVERI DISTRIBUTORS',
    balance: 1239000,
    tier: 'SUGGEST',
    ruleApplied: 'CASH_DEPOSIT (Linked Slips)',
    candidatePayer: 'Salesman Route Till Pool',
    matchScore: 0.98,
    isAudited: false,
    verifiedByOwner: false,
  },
  {
    txnId: 'TXN-1002346',
    date: '2026-09-30',
    amount: 82400,
    type: 'CREDIT',
    narration: 'NEFT/N0930263849/BALAJI GENERAL STORE/PUNB',
    balance: 1194000,
    tier: 'SUGGEST',
    ruleApplied: 'CLUBBED_INVOICES (INV-402, INV-403)',
    candidatePayer: 'Balaji General Store',
    matchScore: 0.95,
    isAudited: false,
    verifiedByOwner: false,
  },
  {
    txnId: 'TXN-1002347',
    date: '2026-09-29',
    amount: 114000,
    type: 'CREDIT',
    narration: 'RTGS/R092928374/MATOSHREE SUPERMARKET/HDFC',
    balance: 1111600,
    tier: 'SUGGEST',
    ruleApplied: 'MATERIALITY_CEILING_CAP (>= ₹1.00L)',
    candidatePayer: 'Matoshree Supermarket',
    matchScore: 0.99,
    isAudited: true,
    verifiedByOwner: false,
  },
  {
    txnId: 'TXN-1002348',
    date: '2026-09-29',
    amount: 25000,
    type: 'CREDIT',
    narration: 'UPI/628394019284/PAYTM/LAXMI MART',
    balance: 997600,
    tier: 'AUTO',
    ruleApplied: 'EXACT_UTR_INVOICE_TIE',
    candidatePayer: 'Laxmi Mart',
    matchScore: 1.0,
    isAudited: true,
    verifiedByOwner: true,
  },
  {
    txnId: 'TXN-1002349',
    date: '2026-09-28',
    amount: 15400,
    type: 'CREDIT',
    narration: 'IMPS/P2A/6293049182/UNKNOWN REMITTER',
    balance: 972600,
    tier: 'ASK',
    ruleApplied: 'UNRESOLVED_NARRATION_AMBIGUITY',
    candidatePayer: 'Requires Owner Allocation',
    matchScore: 0.45,
    isAudited: false,
    verifiedByOwner: false,
  },
];

const MAX_ROWS = 300;
type Decided = 'APPROVED' | 'REJECTED';

export function ReviewQueueTriage() {
  const businessId = useCockpitStore((st) => st.businessId);
  const role = useCockpitStore((st) => st.role);
  const [activeTier, setActiveTier] = useState<MatchTier | 'ALL'>('SUGGEST');
  const [selectedTxnId, setSelectedTxnId] = useState<string | null>(null);
  const [selectedBatch, setSelectedBatch] = useState<string[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterMateriality, setFilterMateriality] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [toastIsError, setToastIsError] = useState(false);
  // Optimistic decisions, keyed by txnId. Rolled back if the API call fails.
  const [decided, setDecided] = useState<Record<string, Decided>>({});

  const { data, status } = useApiResource(
    (signal) => fetchReviewQueue(businessId, activeTier, signal),
    [businessId, activeTier]
  );

  const sampleCounts = mockTransactions.reduce<Record<string, number>>((acc, t) => {
    acc[t.tier] = (acc[t.tier] ?? 0) + 1;
    return acc;
  }, {});
  const counts = data?.countsByTier ?? (status === 'sample' ? sampleCounts : null);
  const total = data?.totalCount ?? (status === 'sample' ? mockTransactions.length : null);
  const countLabel = (n: number | null | undefined) => (n === null || n === undefined ? '' : ` (${n.toLocaleString('en-IN')})`);

  const sourceItems: BankTransaction[] = data ? data.items : status === 'sample' ? mockTransactions : [];

  const filteredItems = sourceItems.filter((txn) => {
    if (activeTier !== 'ALL' && txn.tier !== activeTier) return false;
    if (filterMateriality && txn.amount < 100000) return false;
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      return (
        txn.narration.toLowerCase().includes(q) ||
        (txn.candidatePayer && txn.candidatePayer.toLowerCase().includes(q)) ||
        txn.txnId.toLowerCase().includes(q)
      );
    }
    return true;
  });
  const visibleItems = filteredItems.slice(0, MAX_ROWS);

  const activeTxn = filteredItems.find((t) => t.txnId === selectedTxnId) ?? filteredItems[0] ?? null;

  const showToast = (msg: string, isError = false) => {
    setToastMessage(msg);
    setToastIsError(isError);
    setTimeout(() => setToastMessage(null), 4000);
  };

  // Optimistic update with rollback: mark rows decided now, undo the ones the API refuses.
  const decide = async (ids: string[], decision: 'APPROVE' | 'REJECT') => {
    const todo = ids.filter((id) => !decided[id]);
    if (todo.length === 0) return;
    const mark: Decided = decision === 'APPROVE' ? 'APPROVED' : 'REJECTED';
    setDecided((prev) => ({ ...prev, ...Object.fromEntries(todo.map((id) => [id, mark])) }));
    const results = await Promise.all(
      todo.map((txnId) => submitReviewDecision({ txnId, decision, note: `Reviewed as ${role}` }))
    );
    const failed = todo.filter((_, i) => !results[i].ok);
    if (failed.length > 0) {
      setDecided((prev) => {
        const next = { ...prev };
        failed.forEach((id) => delete next[id]);
        return next;
      });
      const firstError = results.find((r) => !r.ok);
      showToast(
        `${failed.length} decision${failed.length > 1 ? 's' : ''} not saved and reverted. ${firstError && !firstError.ok ? firstError.error : ''}`,
        true
      );
      return;
    }
    const first = results[0];
    const hash = first && first.ok ? first.result.auditHash.slice(0, 10) : '';
    showToast(
      todo.length === 1
        ? `Transaction ${todo[0]} ${mark.toLowerCase()}. Audit entry ${hash}…`
        : `${todo.length} transactions ${mark.toLowerCase()}.`
    );
  };

  const handleBatchApprove = () => {
    const ids = selectedBatch;
    setSelectedBatch([]);
    void decide(ids, 'APPROVE');
  };

  const toggleSelectRow = (txnId: string) => {
    if (selectedBatch.includes(txnId)) {
      setSelectedBatch(selectedBatch.filter((id) => id !== txnId));
    } else {
      setSelectedBatch([...selectedBatch, txnId]);
    }
  };

  return (
    <div className="flex flex-col gap-5 p-6 max-w-7xl mx-auto h-full">
      {/* Toast alert */}
      {toastMessage && (
        <div role="status" className={`fixed top-6 right-6 z-50 rounded-xl ${toastIsError ? 'bg-red-600' : 'bg-emerald-600'} text-white px-4 py-3 shadow-2xl flex items-center gap-3 text-xs font-semibold`}>
          <ShieldCheck className="h-4 w-4" />
          <span>{toastMessage}</span>
          <button onClick={() => setToastMessage(null)} className="ml-2 hover:opacity-80">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Header and Circuit Breaker Status */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Decision 60 Precision Triage
            </span>
            <span className="rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 text-[10px] font-bold px-2 py-0.5 border border-emerald-300">
              Audit Circuit Breaker: ACTIVE
            </span>
            <DataSourceBadge status={status} />
          </div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
            Reconciliation Review Queue
          </h2>
        </div>

        <div className="flex items-center gap-3 text-xs text-slate-500">
          <span>Keyboard shortcuts:</span>
          <kbd className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 font-mono">
            j/k
          </kbd>
          <span>Nav</span>
          <kbd className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 font-mono">
            a
          </kbd>
          <span>Approve</span>
          <kbd className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 font-mono">
            r
          </kbd>
          <span>Reassign</span>
        </div>
      </div>

      {/* Segmented Tier Selector */}
      <div className="flex flex-wrap gap-2 p-1 rounded-xl bg-slate-100 dark:bg-slate-800/80 w-fit text-xs font-bold">
        <button
          onClick={() => setActiveTier('ALL')}
          className={`px-3 py-1.5 rounded-lg transition ${
            activeTier === 'ALL'
              ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm'
              : 'text-slate-500 hover:text-slate-900'
          }`}
        >
          All Items{countLabel(total)}
        </button>
        <button
          onClick={() => setActiveTier('SUGGEST')}
          className={`px-3 py-1.5 rounded-lg transition ${
            activeTier === 'SUGGEST'
              ? 'bg-white dark:bg-slate-900 text-amber-600 shadow-sm'
              : 'text-slate-500 hover:text-slate-900'
          }`}
        >
          Suggestions{countLabel(counts?.SUGGEST)}
        </button>
        <button
          onClick={() => setActiveTier('ASK')}
          className={`px-3 py-1.5 rounded-lg transition ${
            activeTier === 'ASK'
              ? 'bg-white dark:bg-slate-900 text-sky-600 shadow-sm'
              : 'text-slate-500 hover:text-slate-900'
          }`}
        >
          Questions{countLabel(counts?.ASK)}
        </button>
        <button
          onClick={() => setActiveTier('AUTO')}
          className={`px-3 py-1.5 rounded-lg transition ${
            activeTier === 'AUTO'
              ? 'bg-white dark:bg-slate-900 text-emerald-600 shadow-sm'
              : 'text-slate-500 hover:text-slate-900'
          }`}
        >
          Auto-Posted{countLabel(counts?.AUTO)}
        </button>
      </div>

      {/* 3-Pane Triage Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start min-h-[500px]">
        {/* Left Filter Sidebar (20% -> 3 cols) */}
        <div className="lg:col-span-3 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 flex flex-col gap-4">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-700 dark:text-slate-200">
            <Filter className="h-4 w-4" />
            <span>Triage Filters</span>
          </div>

          <div className="relative">
            <Search className="h-3.5 w-3.5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search narration, party..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:outline-none"
            />
          </div>

          <div className="flex flex-col gap-2 text-xs">
            <span className="font-semibold text-slate-500">Materiality Filter</span>
            <label className="flex items-center gap-2 cursor-pointer text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                checked={filterMateriality}
                onChange={(e) => setFilterMateriality(e.target.checked)}
                className="rounded accent-emerald-600"
              />
              <span>Material Lines (≥ ₹1.00 Lakh)</span>
            </label>
          </div>

          <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800 text-[11px] text-slate-500 space-y-1">
            <div className="font-semibold text-slate-700 dark:text-slate-300">ADR-002 Invariants:</div>
            <div>• Wilson 95% error bound ≤ 1.00%</div>
            <div>• 2.0% continuous audit sampling</div>
            <div>• Single audit rejection halts engine</div>
          </div>
        </div>

        {/* Center Transaction Table (45% -> 5 cols) */}
        <div className="lg:col-span-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden shadow-sm">
          <div className="p-3 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs text-slate-500 font-semibold">
            <span>
              {status === 'loading' ? 'Loading…' : `Showing ${visibleItems.length}${filteredItems.length > visibleItems.length ? ` of ${filteredItems.length}` : ''} transactions`}
            </span>
            <span>Date • Amount • Rule</span>
          </div>

          <div className="divide-y divide-slate-100 dark:divide-slate-800 max-h-[520px] overflow-y-auto">
            {status === 'loading' && sourceItems.length === 0 &&
              [0, 1, 2, 3, 4].map((i) => <div key={i} className="m-3 h-12 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-800" />)}
            {visibleItems.map((txn) => {
              const isSelected = txn.txnId === activeTxn?.txnId;
              const isChecked = selectedBatch.includes(txn.txnId);
              const done = decided[txn.txnId];

              return (
                <div
                  key={txn.txnId}
                  onClick={() => setSelectedTxnId(txn.txnId)}
                  className={`p-3.5 cursor-pointer flex items-center justify-between transition ${
                    isSelected
                      ? 'bg-emerald-50/60 dark:bg-emerald-950/30 border-l-4 border-emerald-500'
                      : 'hover:bg-slate-50 dark:hover:bg-slate-800/50'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={(e) => {
                        e.stopPropagation();
                        toggleSelectRow(txn.txnId);
                      }}
                      className="rounded accent-emerald-600"
                    />
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-slate-900 dark:text-white">
                          {txn.date}
                        </span>
                        <span
                          className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                            txn.tier === 'AUTO'
                              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                              : txn.tier === 'SUGGEST'
                              ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                              : 'bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300'
                          }`}
                        >
                          {txn.tier}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 truncate max-w-[200px] mt-0.5">
                        {txn.candidatePayer || txn.narration}
                      </p>
                    </div>
                  </div>

                  <div className="text-right">
                    {done && (
                      <span className={`text-[10px] font-bold ${done === 'APPROVED' ? 'text-emerald-600' : 'text-red-600'}`}>
                        {done === 'APPROVED' ? 'Approved' : 'Rejected'}
                      </span>
                    )}
                    <div className="font-mono text-xs font-bold text-slate-900 dark:text-white">
                      {txn.type === 'CREDIT' ? '+' : '−'}{formatINR(Math.abs(txn.amount))}
                    </div>
                    <span className="text-[10px] text-slate-400 block truncate max-w-[120px]">
                      {txn.ruleApplied}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Inspector Detail (35% -> 4 cols) */}
        <div className="lg:col-span-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm flex flex-col justify-between">
          {activeTxn ? (
            <>
              <div>
                <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
                  <span className="font-mono text-xs font-bold text-slate-500">{activeTxn.txnId}</span>
                  <span className="text-xs text-slate-400">Bank Formal Ledger</span>
                </div>

                <div className="mt-4">
                  <span className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">
                    {activeTxn.type === 'CREDIT' ? 'Credit Amount' : 'Debit Amount'}
                  </span>
                  <div className="text-2xl font-extrabold font-mono text-slate-900 dark:text-white mt-0.5">
                    {formatINR(Math.abs(activeTxn.amount))}
                  </div>
                </div>

                <div className="mt-4 space-y-3 text-xs">
                  <div>
                    <span className="text-slate-400 block mb-0.5">Bank Narration</span>
                    <p className="font-mono text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-800 p-2 rounded-lg text-[11px] break-all">
                      {activeTxn.narration}
                    </p>
                  </div>

                  <div>
                    <span className="text-slate-400 block mb-0.5">Decision 60 Applied Rule</span>
                    <div className="font-semibold text-slate-800 dark:text-slate-200">
                      {activeTxn.ruleApplied}
                    </div>
                    <span className="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium">
                      Confidence Score: {Math.round(activeTxn.matchScore * 100)}%
                    </span>
                  </div>

                  <div>
                    <span className="text-slate-400 block mb-0.5">Assigned Counterparty</span>
                    <div className="font-bold text-slate-900 dark:text-white">
                      {activeTxn.candidatePayer || 'Unassigned'}
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-100 dark:border-slate-800 flex flex-col gap-2">
                {decided[activeTxn.txnId] ? (
                  <p className={`text-center text-xs font-bold ${decided[activeTxn.txnId] === 'APPROVED' ? 'text-emerald-600' : 'text-red-600'}`}>
                    {decided[activeTxn.txnId] === 'APPROVED' ? 'Approved' : 'Rejected'} and recorded in the audit ledger.
                  </p>
                ) : (
                  <div className="flex gap-2">
                    <button
                      onClick={() => void decide([activeTxn.txnId], 'APPROVE')}
                      className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow transition"
                    >
                      <Check className="h-4 w-4" />
                      <span>Approve [a]</span>
                    </button>
                    <button
                      onClick={() => void decide([activeTxn.txnId], 'REJECT')}
                      className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs font-bold shadow transition"
                    >
                      <Ban className="h-4 w-4" />
                      <span>Reject</span>
                    </button>
                  </div>
                )}

                <button
                  onClick={() => alert(`Reassigning candidate payer for ${activeTxn.txnId}`)}
                  className="w-full flex items-center justify-center gap-2 py-2 border border-slate-300 dark:border-slate-700 rounded-xl text-xs font-semibold hover:bg-slate-50 dark:hover:bg-slate-800 transition"
                >
                  <CornerDownLeft className="h-3.5 w-3.5" />
                  <span>Reassign Candidate Payer [r]</span>
                </button>
              </div>
            </>
          ) : (
            <p className="text-xs text-slate-500">
              {status === 'loading' ? 'Loading transactions…' : 'No transactions in this tier.'}
            </p>
          )}
        </div>
      </div>

      {/* Floating Batch Action Bar */}
      {selectedBatch.length > 1 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 flex items-center gap-4 bg-slate-900 text-white px-5 py-3 rounded-2xl shadow-2xl border border-slate-700">
          <span className="text-xs font-semibold">
            {selectedBatch.length} items selected
          </span>
          <button
            onClick={handleBatchApprove}
            className="flex items-center gap-1.5 px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition"
          >
            <span>Batch Approve ({selectedBatch.length})</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => setSelectedBatch([])}
            className="text-xs text-slate-400 hover:text-white"
          >
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
}
