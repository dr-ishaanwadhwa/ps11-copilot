'use client';

import React, { useState } from 'react';
import dynamic from 'next/dynamic';
import { ClientVaultDisplay, DataSourceBadge } from '@/components/vault/ClientVaultDisplay';
import { formatINR } from '@/lib/types';
import type { OverviewPayload } from '@/lib/types';
import { fetchOverview, useApiResource } from '@/lib/api';
import { useCockpitStore, useVaultStore } from '@/lib/store';
import { Play, Pause, Volume2, AlertTriangle, ShieldCheck, MessageSquare, ArrowRight, Sparkles } from 'lucide-react';
import Link from 'next/link';

const TopographyCanvas = dynamic(
  () => import('@/components/topography/TopographyCanvas').then((mod) => mod.TopographyCanvas),
  {
    ssr: false,
    loading: () => <div className="h-[320px] w-full animate-pulse rounded-xl bg-slate-900 border border-slate-800" />,
  }
);

// SAMPLE DATA ONLY: shown (with a "Sample data" label) when the API cannot be reached.
const SAMPLE_OVERVIEW: OverviewPayload = {
  businessId: 'SME-1',
  businessName: 'Kaveri Distributors',
  asOfDate: '2026-09-30',
  bankCurrentBalance: 1239000,
  ccSanctionedLimit: 2500000,
  ccHeadroom: 2120000,
  runwayMonths: 3.8,
  pulseMetrics: [],
  topFocalAction: {
    customerId: 'CUST-001',
    customerName: 'Matoshree Supermarket',
    phone: '+919820012345',
    totalOutstanding: 114000,
    openInvoiceCount: 3,
    oldestInvoiceDays: 930,
    isLimitationAlert: true,
    hasSalesmanCollectedToday: false,
  },
  solvencyBase: {
    formalBankBalance: 1239000,
    ccFacilityDrawn: 380000,
    ccFacilitySanctioned: 2500000,
    formalDueNext30Days: 465000,
    formalReceivables: 2200000,
    defaultKhataRealizationRate: 0.85,
  },
  audioBriefUrl: '',
};

// The API fills every customer phone with this placeholder; never open a chat to it.
const PLACEHOLDER_PHONE = '910000000001';
const usablePhone = (phone: string) => {
  const digits = phone.replace(/\D/g, '');
  return digits.length >= 10 && digits !== PLACEHOLDER_PHONE ? digits : null;
};

const formatAsOf = (iso: string) => {
  const d = new Date(`${iso}T00:00:00`);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
};

export function OverviewCockpit() {
  const { isUnlocked, gallaEntry } = useVaultStore();
  const { locale, setLocale, khataAlpha, setKhataAlpha, businessId, asOfDate, businessName: storeName } = useCockpitStore();
  const { data, status } = useApiResource((signal) => fetchOverview(businessId, asOfDate, signal), [businessId, asOfDate]);
  const ov = data ?? SAMPLE_OVERVIEW;
  const businessName = data ? data.businessName : storeName;

  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [isEquationOpen, setIsEquationOpen] = useState(false);

  // Formal plane metrics (bank, CC, dues, receivables) come from the API or the labelled sample.
  const formalBank = ov.bankCurrentBalance;
  const ccLimit = ov.ccSanctionedLimit;
  const ccHeadroom = ov.ccHeadroom;
  const formalDue = ov.solvencyBase.formalDueNext30Days;
  const khataBook = ov.solvencyBase.formalReceivables;
  const ccDrawn = ov.solvencyBase.ccFacilityDrawn;

  const drawerCash = isUnlocked ? (gallaEntry?.countedCash ?? 0) : 0;
  const trueBuffer = formalBank - ccDrawn + drawerCash + (khataAlpha * khataBook) - formalDue;
  const fundedBy = formalBank + ccHeadroom;
  const duesCovered = fundedBy >= formalDue;
  const focal = ov.topFocalAction;
  const focalPhone = focal ? usablePhone(focal.phone) : null;

  if (status === 'loading' && !data) {
    return (
      <div className="flex flex-col gap-6 p-6 max-w-7xl mx-auto" aria-busy="true">
        <div className="h-48 animate-pulse rounded-2xl bg-slate-200 dark:bg-slate-800" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-24 animate-pulse rounded-xl bg-slate-200 dark:bg-slate-800" />
          ))}
        </div>
        <div className="h-32 animate-pulse rounded-xl bg-slate-200 dark:bg-slate-800" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6 max-w-7xl mx-auto">
      {/* 1. Partial View Notice (ADR-004 Transparent Auditing) */}
      {!isUnlocked && (
        <div className="flex items-center justify-between rounded-lg bg-amber-50 dark:bg-amber-950/60 p-4 border border-amber-300 dark:border-amber-700/60 text-amber-900 dark:text-amber-200 text-sm">
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0" />
            <span>
              <strong>Formal books only.</strong> Sovereign drawer cash is locked in browser memory. Physical counts are excluded from this view.
            </span>
          </div>
          <Link
            href="/lock"
            className="px-3 py-1 bg-amber-600 hover:bg-amber-700 text-white font-medium rounded text-xs transition"
          >
            Unlock Vault
          </Link>
        </div>
      )}

      {/* 2. Hero Net Usable Liquidity Card */}
      <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4 pb-4 border-b border-slate-100 dark:border-slate-800">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Daily Solvency Cockpit
              </span>
              <span className={`rounded-full text-[10px] font-bold px-2 py-0.5 ${
                trueBuffer >= 0
                  ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300'
                  : 'bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-300'
              }`}>
                {trueBuffer >= 0 ? 'Surplus Mode' : 'Shortfall Mode'}
              </span>
              <DataSourceBadge status={status} />
            </div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white mt-1">
              &quot;Aaj Ka Hisaab&quot; — True Spendable Runway
            </h2>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setLocale(locale === 'hi' ? 'en' : 'hi')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-xs font-medium hover:bg-slate-50 dark:hover:bg-slate-800"
            >
              <span>{locale === 'hi' ? 'हिन्दी' : 'English'}</span>
            </button>
            <span className="text-xs text-slate-400 font-mono">As of {formatAsOf(ov.asOfDate)}</span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-center">
          <div className="lg:col-span-2">
            <span className="text-xs text-slate-500 uppercase tracking-wider font-medium">Net Usable Liquidity</span>
            <ClientVaultDisplay bankBalance={formalBank} commitments={formalDue} className="mt-1" />
            <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-600 dark:text-slate-300">
              <span className="flex items-center gap-1">
                <ShieldCheck className="h-4 w-4 text-emerald-500" />
                Next-30-day dues ({formatINR(formalDue, { compact: true })}){' '}
                <strong>{duesCovered ? 'Fully funded' : 'Not fully funded'}</strong>
              </span>
              <span className="flex items-center gap-1">
                <ShieldCheck className="h-4 w-4 text-emerald-500" />
                CC Headroom Clear by <strong>{formatINR(ccHeadroom, { compact: true })}</strong>
              </span>
            </div>
          </div>

          <div className="rounded-xl bg-slate-50 dark:bg-slate-800/60 p-4 border border-slate-100 dark:border-slate-800">
            <div className="text-xs font-medium text-slate-500">Runway Confidence</div>
            <div className="text-2xl font-bold text-slate-900 dark:text-white font-mono mt-0.5">
              {ov.runwayMonths.toFixed(1)} Months
            </div>
            <p className="text-[11px] text-slate-500 mt-1">
              Bank balance plus cash-credit headroom, divided by the next 30 days of committed dues.
            </p>
          </div>
        </div>
      </div>

      {/* 3. Vernacular Audio Briefing Player */}
      <div className="rounded-xl border border-indigo-100 dark:border-indigo-900/50 bg-gradient-to-r from-indigo-50/50 to-purple-50/30 dark:from-indigo-950/20 dark:to-purple-950/10 p-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsPlayingAudio(!isPlayingAudio)}
              className="h-10 w-10 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white flex items-center justify-center shadow-md transition"
            >
              {isPlayingAudio ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4 ml-0.5" />}
            </button>
            <div>
              <div className="flex items-center gap-2">
                <Volume2 className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                <span className="text-xs font-bold text-indigo-950 dark:text-indigo-200">
                  {locale === 'hi' ? '30-सेकंड की ऑडियो समीक्षा' : '30-Second Morning Audio Brief'}
                </span>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-300 italic mt-0.5">
                {locale === 'hi'
                  ? `“शुभ प्रभात। आज ${businessName} के पास कुल ${formatINR(formalBank + drawerCash - formalDue, { compact: true })} खर्च करने योग्य नकदी है...”`
                  : `“Good morning. ${businessName} has ${formatINR(formalBank + drawerCash - formalDue, { compact: true })} spendable liquidity today...”`}
              </p>
            </div>
          </div>
          <span className="text-xs text-indigo-700 dark:text-indigo-300 font-mono self-end sm:self-center">
            {isPlayingAudio ? '00:14 / 00:32' : '00:32'}
          </span>
        </div>
      </div>

      {/* 4. Four Vital Pulse Tiles */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
          <span className="text-xs font-medium text-slate-500">Net Usable Cash</span>
          <div className="text-xl font-bold font-mono text-slate-900 dark:text-white mt-1">
            {formatINR(formalBank + drawerCash - formalDue, { compact: true })}
          </div>
          <span className="text-[10px] text-slate-400">Bank + Counted Till</span>
        </div>

        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
          <span className="text-xs font-medium text-slate-500">Bank Headroom</span>
          <div className="text-xl font-bold font-mono text-emerald-600 dark:text-emerald-400 mt-1">
            {formatINR(ccHeadroom, { compact: true })}
          </div>
          <span className="text-[10px] text-slate-400">Limit: {formatINR(ccLimit, { compact: true })}</span>
        </div>

        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
          <span className="text-xs font-medium text-slate-500">Cash in Drawer</span>
          <div className="text-xl font-bold font-mono text-amber-600 dark:text-amber-400 mt-1">
            {isUnlocked ? formatINR(drawerCash, { compact: true }) : 'Locked'}
          </div>
          <span className="text-[10px] text-slate-400">Physical Counted</span>
        </div>

        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
          <span className="text-xs font-medium text-slate-500">Due in 30 Days</span>
          <div className="text-xl font-bold font-mono text-red-600 dark:text-red-400 mt-1">
            {formatINR(formalDue, { compact: true })}
          </div>
          <span className="text-[10px] text-slate-400">Payroll &amp; trade dues</span>
        </div>
      </div>

      {/* 5. Single Focal Action Card */}
      {focal ? (
        <div className="rounded-xl border-2 border-red-200 dark:border-red-900/60 bg-red-50/50 dark:bg-red-950/20 p-5">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold bg-red-600 text-white">
                  <AlertTriangle className="h-3 w-3" aria-hidden="true" />Priority 1 Recovery Action
                </span>
                <span className="text-xs font-medium text-red-700 dark:text-red-300">
                  {focal.isLimitationAlert
                    ? `Section 18 Limitation Alert (${Math.floor(focal.oldestInvoiceDays / 30)} Months Old)`
                    : 'Most overdue customer balance'}
                </span>
              </div>
              <h3 className="text-base font-bold text-slate-900 dark:text-white mt-1.5">
                {focal.customerName} owes {formatINR(focal.totalOutstanding)} ({focal.oldestInvoiceDays} Days Overdue)
              </h3>
              <p className="text-xs text-slate-600 dark:text-slate-300 mt-0.5">
                {focal.isLimitationAlert
                  ? 'The 3-year commercial limitation period is close. A written WhatsApp balance acknowledgment restarts the legal clock.'
                  : `${focal.openInvoiceCount} open invoices. Following up on the oldest one first improves cash soonest.`}
              </p>
            </div>

            <div className="flex items-center gap-2 flex-shrink-0">
              {focalPhone ? (
                <a
                  href={`https://wa.me/${focalPhone}?text=${encodeURIComponent(
                    `Namaste ${focal.customerName} ji, as per our records with ${businessName} pending balance is Rs ${Math.round(focal.totalOutstanding)}. Could you please confirm or send part settlement?`
                  )}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold shadow-sm transition"
                >
                  <MessageSquare className="h-4 w-4" />
                  Send WhatsApp AoD Link
                </a>
              ) : (
                <span
                  title="No phone number on file for this customer"
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-slate-200 dark:bg-slate-800 text-slate-500 rounded-lg text-xs font-bold cursor-not-allowed"
                >
                  <MessageSquare className="h-4 w-4" />
                  No phone on file
                </span>
              )}
              <Link
                href="/receivables"
                className="px-3 py-2 border border-slate-300 dark:border-slate-700 rounded-lg text-xs font-semibold hover:bg-white dark:hover:bg-slate-800 transition"
              >
                View Ledger
              </Link>
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 text-xs text-slate-600 dark:text-slate-300">
          No open customer invoices to chase.
        </div>
      )}

      {/* 6. 3D Spatial Topography Preview */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-emerald-500" />
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">
              3D Spatial Cashflow Topography
            </h3>
          </div>
          <Link
            href="/forecast"
            className="flex items-center gap-1 text-xs font-medium text-emerald-600 hover:text-emerald-700 dark:text-emerald-400"
          >
            <span>Full 90-Day Simulation</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
        <TopographyCanvas height={320} creditLimit={ccLimit} />
      </div>

      {/* 7. Collapsible Dual-Plane True Solvency Equation */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden shadow-sm">
        <button
          onClick={() => setIsEquationOpen(!isEquationOpen)}
          className="w-full flex items-center justify-between p-4 text-left hover:bg-slate-50 dark:hover:bg-slate-800/50 transition"
        >
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm text-slate-800 dark:text-slate-200">
              Dual-Plane True Solvency Equation
            </span>
            <span className="text-xs text-slate-500">
              (Buffer = Bank − CC Drawn + Till + (α × Khata) − Dues)
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm font-bold text-emerald-600 dark:text-emerald-400">
              {formatINR(trueBuffer, { compact: true })}
            </span>
            <span className="text-xs text-slate-400">{isEquationOpen ? '▲' : '▼'}</span>
          </div>
        </button>

        {isEquationOpen && (
          <div className="p-4 pt-0 border-t border-slate-100 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-300">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
              <div>
                <label className="block text-slate-500 font-medium mb-1">
                  Receivables Collection Haircut (α): {Math.round(khataAlpha * 100)}%
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="1.0"
                  step="0.05"
                  value={khataAlpha}
                  onChange={(e) => setKhataAlpha(parseFloat(e.target.value))}
                  className="w-full accent-emerald-600"
                />
                <span className="text-[11px] text-slate-400 mt-1 block">
                  Conservative realization: {Math.round(khataAlpha * 100)}% of {formatINR(khataBook, { compact: true })} receivables is treated as spendable.
                </span>
              </div>

              <div className="rounded-lg bg-slate-50 dark:bg-slate-800 p-3 font-mono text-[11px] space-y-1">
                <div>Bank Balance: +{formatINR(formalBank)}</div>
                <div>Overdraft CC Drawn: −{formatINR(ccDrawn)}</div>
                <div>Godown Till Cash: +{formatINR(drawerCash)}</div>
                <div>Receivables Realization ({Math.round(khataAlpha * 100)}% of {formatINR(khataBook, { compact: true })}): +{formatINR(khataAlpha * khataBook)}</div>
                <div>Committed 30-Day Dues: −{formatINR(formalDue)}</div>
                <div className="border-t border-slate-300 dark:border-slate-700 pt-1 font-bold text-emerald-600 dark:text-emerald-400">
                  Net True Solvency Buffer: {formatINR(trueBuffer)}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
