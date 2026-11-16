'use client';

import React, { useEffect, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import { Fallback2DTopography } from '@/components/topography/Fallback2DTopography';
import { formatINR } from '@/lib/types';
import type { ForecastPlainSummary, ForecastSimulationPoint, MonthlyOutlookItem } from '@/lib/types';
import { fetchForecast } from '@/lib/api';
import { useCockpitStore } from '@/lib/store';
import {
  CC_LIMIT,
  DEFAULT_AS_OF,
  NO_SCENARIO,
  formatLongDate,
  isScenarioActive,
  sampleForecast,
  summarise,
} from '@/lib/forecast-mock';
import { ShieldCheck, Sliders, Calendar, Sparkles, Info } from 'lucide-react';

const TopographyCanvas = dynamic(
  () => import('@/components/topography/TopographyCanvas').then((mod) => mod.TopographyCanvas),
  {
    ssr: false,
    loading: () => <div className="h-[380px] w-full animate-pulse rounded-xl bg-slate-900 border border-slate-800" />,
  }
);

interface ForecastView {
  points: ForecastSimulationPoint[];
  summary: ForecastPlainSummary;
  months: MonthlyOutlookItem[];
  /** Measured holdout accuracy from the API; null when the API did not report it (never a constant). */
  holdout: { mape: number | null; coverage: number | null };
  source: 'live' | 'sample';
  loading: boolean;
}

// SAMPLE DATA ONLY: used with the "Sample data" label when the API cannot be reached.
const SAMPLE_MONTHS: MonthlyOutlookItem[] = [
  { monthName: 'Oct 2026', inflowsP50: 4820000, inflowsP10: 4300000, committedOutflows: 4210000, netCashFlow: 610000, lowestDipPoint: 420000, closingBalance: 1850000, hasBreachedCreditLimit: false },
  { monthName: 'Nov 2026', inflowsP50: 5240000, inflowsP10: 4700000, committedOutflows: 4450000, netCashFlow: 790000, lowestDipPoint: 610000, closingBalance: 2640000, hasBreachedCreditLimit: false },
  { monthName: 'Dec 2026', inflowsP50: 6100000, inflowsP10: 5500000, committedOutflows: 4680000, netCashFlow: 1420000, lowestDipPoint: 1240000, closingBalance: 4060000, hasBreachedCreditLimit: false },
];
const NOT_MEASURED = { mape: null, coverage: null };
const pct = (v: number | null) => (v === null ? 'not measured' : `${(v * 100).toFixed(1)}%`);

const WHAT_IFS = [
  { key: 'late', label: 'Customers pay 15 days late' },
  { key: 'early', label: 'Pay suppliers 15 days early' },
  { key: 'drop', label: 'Sales drop 20%' },
] as const;
type WhatIfKey = (typeof WHAT_IFS)[number]['key'];

export default function ForecastPage() {
  const businessId = useCockpitStore((st) => st.businessId);
  const [asOf, setAsOf] = useState(DEFAULT_AS_OF);
  const [whatIf, setWhatIf] = useState<Record<WhatIfKey, boolean>>({ late: false, early: false, drop: false });
  const scenario = useMemo(
    () => ({
      receiptDelayDays: whatIf.late ? 15 : 0,
      billShiftDays: whatIf.early ? -15 : 0,
      salesFactor: whatIf.drop ? 0.8 : 1,
    }),
    [whatIf]
  );
  const [view, setView] = useState<ForecastView>(() => {
    const sample = sampleForecast(DEFAULT_AS_OF, NO_SCENARIO);
    return { ...sample, months: SAMPLE_MONTHS, holdout: NOT_MEASURED, source: 'sample', loading: true };
  });

  useEffect(() => {
    const sample = sampleForecast(asOf, scenario);
    const sampleView: ForecastView = { ...sample, months: SAMPLE_MONTHS, holdout: NOT_MEASURED, source: 'sample', loading: false };
    setView((v) => ({ ...v, loading: true }));
    const ctl = new AbortController();
    fetchForecast(
      {
        biz: businessId,
        asOf,
        receiptDelayDays: scenario.receiptDelayDays,
        billShiftDays: scenario.billShiftDays,
        salesFactor: scenario.salesFactor,
      },
      ctl.signal
    )
      .then((res) => {
        const pts = res.simulationPoints && res.simulationPoints.length > 0 ? res.simulationPoints : null;
        const summary =
          res.plainSummary ??
          (pts ? summarise(pts, isScenarioActive(scenario), null, CC_LIMIT) : null);
        if (!summary || !pts) throw new Error('Forecast response had no usable data');
        setView({
          points: pts,
          summary,
          months: res.monthlyMatrix ?? [],
          holdout: { mape: res.holdoutMapeMeasured ?? null, coverage: res.holdoutCoverageMeasured ?? null },
          source: 'live',
          loading: false,
        });
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setView(sampleView);
      });
    return () => ctl.abort();
  }, [asOf, scenario, businessId]);

  const { summary, points: seriesPoints, source, months, holdout, loading } = view;
  const scenarioActive = summary.scenarioActive;
  const delta =
    scenarioActive && summary.baselineLowestBalance !== null
      ? summary.lowestBalance - summary.baselineLowestBalance
      : null;

  const [viewMode, setViewMode] = useState<'3D' | '2D'>('3D');
  const [delayDays, setDelayDays] = useState(15);
  const [extraExpense, setExtraExpense] = useState(250000);
  const [haircutAlpha, setHaircutAlpha] = useState(0.85);

  const ccLimit = summary.creditLimit;

  return (
    <div className="flex flex-col gap-6 p-6 max-w-7xl mx-auto">
      {/* Header and Model Badge */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Bottom-Up Monte Carlo Engine
            </span>
            <span
              title="Measured on the frozen holdout set. Shows 'not measured' when the API does not report it."
              className="rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 text-[10px] font-bold px-2 py-0.5 border border-emerald-300"
            >
              Holdout MAPE: {pct(holdout.mape)} · Coverage: {pct(holdout.coverage)}
            </span>
          </div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
            Next 90 days from {formatLongDate(asOf)}
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Covers {formatLongDate(asOf)} to {formatLongDate(seriesPoints[seriesPoints.length - 1]?.date ?? asOf)}. Books are reconciled to {formatLongDate(DEFAULT_AS_OF)}.
          </p>
        </div>

        {/* 3D vs 2D Toggle */}
        <div className="flex items-center gap-1 rounded-xl bg-slate-100 dark:bg-slate-800 p-1 text-xs font-bold">
          <button
            onClick={() => setViewMode('3D')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition ${
              viewMode === '3D'
                ? 'bg-white dark:bg-slate-900 text-emerald-600 shadow-sm'
                : 'text-slate-500 hover:text-slate-900'
            }`}
          >
            <Sparkles className="h-3.5 w-3.5" />
            <span>3D Spatial Landscape</span>
          </button>
          <button
            onClick={() => setViewMode('2D')}
            className={`px-3 py-1.5 rounded-lg transition ${
              viewMode === '2D'
                ? 'bg-white dark:bg-slate-900 text-emerald-600 shadow-sm'
                : 'text-slate-500 hover:text-slate-900'
            }`}
          >
            2D Area Fan Chart
          </button>
        </div>
      </div>

      {/* Outlook Status Banner */}
      <div className="rounded-xl border border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/50 dark:bg-emerald-950/20 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2.5">
          <ShieldCheck className="h-5 w-5 text-emerald-600 flex-shrink-0" />
          <div>
            <span className="font-bold text-emerald-900 dark:text-emerald-200 block">
              {summary.breachesCreditLimit ? 'OUTLOOK STATUS: WATCH — Cash-Credit Limit at Risk' : 'OUTLOOK STATUS: SAFE — Zero Cash-Credit Breaches'}
            </span>
            <span className="text-slate-600 dark:text-slate-300">
              {summary.breachesCreditLimit
                ? `The worst simulated paths cross the ${formatINR(summary.creditLimit)} sanctioned CC limit.`
                : `All simulation paths stay inside the ${formatINR(summary.creditLimit)} sanctioned CC limit.`}
            </span>
          </div>
        </div>
        <div className="text-right flex-shrink-0">
          <span className="text-slate-500 block">Lowest Projected Dip:</span>
          <span className="font-mono font-bold text-slate-900 dark:text-white text-sm">
            {formatINR(summary.lowestBalance)} ({formatLongDate(summary.lowestDate)})
          </span>
        </div>
      </div>

      {/* Topography / Probability Chart Container */}
      <div className="rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm">
        {viewMode === '3D' ? (
          <TopographyCanvas height={380} creditLimit={ccLimit} simulationPoints={seriesPoints} />
        ) : (
          <Fallback2DTopography height={380} creditLimit={ccLimit} simulationPoints={seriesPoints} />
        )}
      </div>

      {/* Plain-language summary card */}
      <section
        aria-labelledby="forecast-meaning-title"
        className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-sm"
      >
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
          <h3 id="forecast-meaning-title" className="text-base font-bold text-slate-900 dark:text-white">
            What this forecast means for you
          </h3>
          {loading && (
            <span role="status" className="text-[10px] font-bold text-slate-500 animate-pulse">Loading live forecast…</span>
          )}
          {source === 'sample' && !loading && (
            <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 px-2 py-0.5 text-[10px] font-bold text-slate-600 dark:text-slate-300">
              <Info className="h-3 w-3" aria-hidden="true" />
              Sample data
            </span>
          )}
        </div>

        <ul className="space-y-2.5 text-sm text-slate-700 dark:text-slate-200">
          <li>
            <span className="font-semibold">Lowest balance: </span>
            <span className="font-mono font-bold">{formatINR(summary.lowestBalance)}</span> on{' '}
            <span className="font-semibold">{formatLongDate(summary.lowestDate)}</span>.
          </li>
          <li>
            <span className="font-semibold">Cash-credit limit: </span>
            {summary.breachesCreditLimit ? (
              <span className="font-bold text-red-600 dark:text-red-400">
                At risk. In a bad run your balance could drop to {formatINR(summary.worstCaseLowestBalance)}, past your {formatINR(summary.creditLimit)} limit.
              </span>
            ) : (
              <span className="font-bold text-emerald-700 dark:text-emerald-400">
                You stay inside your {formatINR(summary.creditLimit)} limit, even in a bad run ({formatINR(summary.worstCaseLowestBalance)}).
              </span>
            )}
          </li>
          <li>
            <span className="font-semibold">Best action: </span>
            {summary.topCollectionAction ? (
              <>
                Collect {formatINR(summary.topCollectionAction.outstanding)} from{' '}
                <span className="font-semibold">{summary.topCollectionAction.customerName}</span>
                {' '}(oldest invoice {summary.topCollectionAction.oldestInvoiceDays} days old). It helps your cash more than any other single follow-up.
              </>
            ) : (
              <>No single collection stands out. Keep your usual follow-ups going.</>
            )}
          </li>
        </ul>

        {delta !== null && summary.baselineLowestBalance !== null && (
          <div className="mt-4 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 p-3 text-xs text-amber-950 dark:text-amber-200">
            <span className="font-bold">With your what-ifs: </span>
            the lowest point moves from {formatINR(summary.baselineLowestBalance)} to {formatINR(summary.lowestBalance)}
            {' '}
            {delta === 0 ? '(no change).' : <>({delta < 0 ? 'lower' : 'higher'} by <span className="font-mono font-bold">{formatINR(Math.abs(delta))}</span>).</>}
            {source === 'sample' && ' This is an approximate adjustment to the sample data.'}
          </div>
        )}

        {/* Controls */}
        <div className="mt-5 pt-4 border-t border-slate-100 dark:border-slate-800 flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-3">
            <label htmlFor="forecast-from" className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              Forecast from
            </label>
            <input
              id="forecast-from"
              type="date"
              value={asOf}
              onChange={(e) => e.target.value && setAsOf(e.target.value)}
              className="rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-2 py-1 text-xs font-mono"
            />
            {asOf !== DEFAULT_AS_OF && (
              <button
                type="button"
                onClick={() => setAsOf(DEFAULT_AS_OF)}
                className="text-[11px] font-semibold text-emerald-700 dark:text-emerald-400 hover:underline"
              >
                Reset to reconciled date ({formatLongDate(DEFAULT_AS_OF)})
              </button>
            )}
          </div>

          <fieldset>
            <legend className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">What if...</legend>
            <div className="flex flex-wrap gap-2">
              {WHAT_IFS.map((w) => (
                <button
                  key={w.key}
                  type="button"
                  role="switch"
                  aria-checked={whatIf[w.key]}
                  onClick={() => setWhatIf((prev) => ({ ...prev, [w.key]: !prev[w.key] }))}
                  className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                    whatIf[w.key]
                      ? 'border-emerald-600 bg-emerald-600 text-white'
                      : 'border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:border-emerald-500'
                  }`}
                >
                  {w.label}
                </button>
              ))}
            </div>
          </fieldset>
        </div>
      </section>

      {/* Interactive Scenario Stress Sliders */}
      <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <Sliders className="h-4 w-4 text-emerald-600" />
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">
            Real-Time Scenario Stress Testing
          </h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <div className="flex items-center justify-between text-xs font-semibold mb-1">
              <span className="text-slate-700 dark:text-slate-300">Customer Delay Surge</span>
              <span className="font-mono text-emerald-600">+{delayDays} Days Overdue</span>
            </div>
            <input
              type="range"
              min="0"
              max="60"
              step="5"
              value={delayDays}
              onChange={(e) => setDelayDays(parseInt(e.target.value))}
              className="w-full accent-emerald-600"
            />
            <span className="text-[11px] text-slate-400 mt-1 block">
              Simulates top 5 wholesale customers delaying trade payments.
            </span>
          </div>

          <div>
            <div className="flex items-center justify-between text-xs font-semibold mb-1">
              <span className="text-slate-700 dark:text-slate-300">Raw Material Cash Surge</span>
              <span className="font-mono text-amber-600">{formatINR(extraExpense, { compact: true })}</span>
            </div>
            <input
              type="range"
              min="0"
              max="1000000"
              step="50000"
              value={extraExpense}
              onChange={(e) => setExtraExpense(parseInt(e.target.value))}
              className="w-full accent-amber-500"
            />
            <span className="text-[11px] text-slate-400 mt-1 block">
              Simulates advance cash required for Diwali inventory procurement.
            </span>
          </div>

          <div>
            <div className="flex items-center justify-between text-xs font-semibold mb-1">
              <span className="text-slate-700 dark:text-slate-300">Khata Realization Rate (α)</span>
              <span className="font-mono text-indigo-600">{Math.round(haircutAlpha * 100)}%</span>
            </div>
            <input
              type="range"
              min="0.5"
              max="1.0"
              step="0.05"
              value={haircutAlpha}
              onChange={(e) => setHaircutAlpha(parseFloat(e.target.value))}
              className="w-full accent-indigo-600"
            />
            <span className="text-[11px] text-slate-400 mt-1 block">
              Haircut applied to informal customer credit balances.
            </span>
          </div>
        </div>
      </div>

      {/* Month-by-Month Operating Outlook Matrix */}
      <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <Calendar className="h-4 w-4 text-slate-500" />
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">
            Monthly Liquidity Outlook
          </h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 font-semibold">
                <th className="py-2.5 px-3">Operating Month</th>
                <th className="py-2.5 px-3">Projected Inflows (P50)</th>
                <th className="py-2.5 px-3">Committed Outflows</th>
                <th className="py-2.5 px-3">Net Monthly Cash</th>
                <th className="py-2.5 px-3">Lowest Dip Point</th>
                <th className="py-2.5 px-3">Credit-Limit Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-slate-700 dark:text-slate-200">
              {months.map((m) => (
                <tr key={m.monthName} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                  <td className="py-3 px-3 font-bold">{m.monthName}</td>
                  <td className="py-3 px-3 font-mono text-emerald-600">{formatINR(m.inflowsP50)}</td>
                  <td className="py-3 px-3 font-mono text-red-500">{formatINR(m.committedOutflows)}</td>
                  <td className={`py-3 px-3 font-mono font-bold ${m.netCashFlow >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                    {formatINR(m.netCashFlow, { signed: true })}
                  </td>
                  <td className="py-3 px-3 font-mono">{formatINR(m.lowestDipPoint)}</td>
                  <td className={`py-3 px-3 font-bold ${m.hasBreachedCreditLimit ? 'text-red-600' : 'text-emerald-600'}`}>
                    {m.hasBreachedCreditLimit ? 'LIMIT BREACH' : 'SAFE'}
                  </td>
                </tr>
              ))}
              {months.length === 0 && (
                <tr><td colSpan={6} className="py-3 px-3 text-slate-500">No monthly outlook returned.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
