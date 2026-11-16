import type { ForecastPlainSummary, ForecastSimulationPoint } from './types';
import { formatINR } from './types';

/**
 * SAMPLE DATA ONLY. A small deterministic event model used when no live API is
 * configured or the request fails. The scenario toggles shift/scale the sample
 * events, so the numbers are an approximation, never a real forecast.
 */

export const DEFAULT_AS_OF = '2026-09-30';
export const CC_LIMIT = 2500000;
const OPENING_BALANCE = 1239000;
const DAILY_NET_SALES = 21000;

export interface Scenario {
  receiptDelayDays: number; // 0 or 15
  billShiftDays: number; // 0 or -15
  salesFactor: number; // 1 or 0.8
}

export const NO_SCENARIO: Scenario = { receiptDelayDays: 0, billShiftDays: 0, salesFactor: 1 };

export function isScenarioActive(s: Scenario): boolean {
  return s.receiptDelayDays !== 0 || s.billShiftDays !== 0 || s.salesFactor !== 1;
}

const SAMPLE_TOP_ACTION = { customerName: 'Laxmi Provision Stores', outstanding: 182400, oldestInvoiceDays: 52 };

interface SampleEvent {
  day: number;
  amount: number;
  kind: 'receipt' | 'bill' | 'fixed';
  title: string;
  category: 'SALARY' | 'GST_TAX' | 'VENDOR_DUE' | 'CUSTOMER_RECEIPT';
}

function parseDate(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(Date.UTC(y, (m || 1) - 1, d || 1));
}
function addDays(d: Date, n: number): Date {
  return new Date(d.getTime() + n * 86400000);
}
function toIso(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function formatLongDate(iso: string): string {
  return parseDate(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
}

function buildEvents(asOf: Date): SampleEvent[] {
  const events: SampleEvent[] = [];
  for (let m = 0; m < 5; m++) {
    const y = asOf.getUTCFullYear();
    const mo = asOf.getUTCMonth() + m;
    const at = (dom: number) => Math.round((Date.UTC(y, mo, dom) - asOf.getTime()) / 86400000);
    events.push({ day: at(1), amount: -465000, kind: 'fixed', title: 'Salaries', category: 'SALARY' });
    events.push({ day: at(20), amount: -380000, kind: 'fixed', title: 'GST payment', category: 'GST_TAX' });
    events.push({ day: at(10), amount: -540000, kind: 'bill', title: 'Supplier bills', category: 'VENDOR_DUE' });
    events.push({ day: at(28), amount: -310000, kind: 'bill', title: 'Supplier bills', category: 'VENDOR_DUE' });
    for (const dom of [5, 15, 25]) {
      events.push({ day: at(dom), amount: 320000, kind: 'receipt', title: 'Customer collections', category: 'CUSTOMER_RECEIPT' });
    }
  }
  return events;
}

export function buildSampleSeries(asOfIso: string, sc: Scenario = NO_SCENARIO): ForecastSimulationPoint[] {
  const asOf = parseDate(asOfIso);
  const events = buildEvents(asOf).map((e) => {
    if (e.kind === 'receipt') return { ...e, day: e.day + sc.receiptDelayDays };
    if (e.kind === 'bill') return { ...e, day: e.day + sc.billShiftDays };
    return e;
  });
  const points: ForecastSimulationPoint[] = [];
  let bal = OPENING_BALANCE;
  for (let d = 0; d <= 90; d++) {
    const todays = events.filter((e) => e.day === d);
    if (d > 0) bal += DAILY_NET_SALES * sc.salesFactor;
    for (const e of todays) bal += e.amount;
    const spread = 60000 + 22000 * Math.sqrt(d);
    const big = todays.find((e) => Math.abs(e.amount) >= 300000);
    points.push({
      dayIndex: d,
      date: toIso(addDays(asOf, d)),
      p10WorstCase: bal - spread,
      p50Median: bal,
      p90Optimistic: bal + spread * 1.2,
      ccFacilityLimit: CC_LIMIT,
      ...(big ? { milestoneEvent: { title: big.title, amount: Math.abs(big.amount), category: big.category } } : {}),
    });
  }
  return points;
}

/** Plain-language summary computed from any simulation series (sample or live). */
export function summarise(
  points: ForecastSimulationPoint[],
  scenarioActive: boolean,
  baselineLowest: number | null,
  creditLimit = CC_LIMIT
): ForecastPlainSummary {
  let low = points[0];
  let worst = points[0];
  for (const p of points) {
    if (p.p50Median < low.p50Median) low = p;
    if (p.p10WorstCase < worst.p10WorstCase) worst = p;
  }
  const breaches = worst.p10WorstCase < -creditLimit;
  const action = SAMPLE_TOP_ACTION;
  const headline = `Your lowest balance will be ${formatINR(low.p50Median)} on ${formatLongDate(low.date)}.`;
  const detail = breaches
    ? `In a bad run it could drop to ${formatINR(worst.p10WorstCase)}, past your ${formatINR(creditLimit)} cash-credit limit.`
    : `You stay inside your ${formatINR(creditLimit)} cash-credit limit, even in a bad run (${formatINR(worst.p10WorstCase)}).`;
  return {
    lowestBalance: low.p50Median,
    lowestDate: low.date,
    worstCaseLowestBalance: worst.p10WorstCase,
    creditLimit,
    breachesCreditLimit: breaches,
    scenarioActive,
    baselineLowestBalance: scenarioActive ? baselineLowest : null,
    topCollectionAction: action,
    headline,
    detail,
  };
}

export function sampleForecast(asOfIso: string, sc: Scenario) {
  const points = buildSampleSeries(asOfIso, sc);
  const active = isScenarioActive(sc);
  const baseline = active ? Math.min(...buildSampleSeries(asOfIso, NO_SCENARIO).map((p) => p.p50Median)) : null;
  return { points, summary: summarise(points, active, baseline) };
}
