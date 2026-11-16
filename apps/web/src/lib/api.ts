import { useEffect, useState, useSyncExternalStore } from 'react';
import type { z } from 'zod';
import {
  CopilotStreamChunkSchema,
  ExportPayloadSchema,
  ForecastPayloadSchema,
  OverviewPayloadSchema,
  ReceivablesPayloadSchema,
  ReviewQueuePayloadSchema,
} from './types';
import type {
  CopilotStreamChunk,
  ExportPayload,
  ForecastPayload,
  MatchTier,
  OverviewPayload,
  ReceivablesPayload,
  ReviewQueuePayload,
} from './types';

/**
 * Split-bridge BFF client. Browser code talks to the same-origin Next proxy
 * (src/app/api/v1/[...path]/route.ts), which forwards to the FastAPI service.
 * NEXT_PUBLIC_API_BASE may point at another origin; the default is same-origin.
 */
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? '';
const url = (path: string) => `${API_BASE}/api/v1/${path}`;

// ---------------------------------------------------------------------------
// Reachability status (drives the "FastAPI Bridge" badge)
// ---------------------------------------------------------------------------
export type ApiStatus = 'unknown' | 'online' | 'offline';
let apiStatus: ApiStatus = 'unknown';
const statusListeners = new Set<() => void>();
function setApiStatus(next: ApiStatus) {
  if (next === apiStatus) return;
  apiStatus = next;
  statusListeners.forEach((l) => l());
}
export function useApiStatus(): ApiStatus {
  return useSyncExternalStore(
    (cb) => {
      statusListeners.add(cb);
      return () => statusListeners.delete(cb);
    },
    () => apiStatus,
    () => 'unknown' as ApiStatus
  );
}

const isAbort = (e: unknown) => e instanceof DOMException && e.name === 'AbortError';

/** fetch wrapper that records reachability. A 502/503/504 from the proxy means the API is down. */
async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(url(path), init);
  } catch (e) {
    if (!isAbort(e)) setApiStatus('offline');
    throw e;
  }
  setApiStatus(res.status === 502 || res.status === 503 || res.status === 504 ? 'offline' : 'online');
  return res;
}

async function getJson<S extends z.ZodTypeAny>(path: string, schema: S, signal?: AbortSignal): Promise<z.infer<S>> {
  const res = await apiFetch(path, { signal });
  if (!res.ok) throw new Error(`Request failed (${res.status}) for ${path.split('?')[0]}`);
  return schema.parse(await res.json());
}

const qs = (params: Record<string, string | number | undefined>) => {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== '') sp.set(k, String(v));
  return sp.toString();
};

// ---------------------------------------------------------------------------
// Overview
// ---------------------------------------------------------------------------
const overviewCache = new Map<string, { at: number; p: Promise<OverviewPayload> }>();
const OVERVIEW_TTL_MS = 30_000;

/** Overview is read by the page and the dashboard shell; share one in-flight request per business + date. */
export function fetchOverview(biz: string, asOf?: string, _signal?: AbortSignal): Promise<OverviewPayload> {
  const key = `${biz}|${asOf ?? ''}`;
  const hit = overviewCache.get(key);
  if (hit && Date.now() - hit.at < OVERVIEW_TTL_MS) return hit.p;
  const p = getJson(`overview?${qs({ biz, as_of: asOf })}`, OverviewPayloadSchema);
  overviewCache.set(key, { at: Date.now(), p });
  p.catch(() => overviewCache.delete(key));
  return p;
}

// ---------------------------------------------------------------------------
// Forecast
// ---------------------------------------------------------------------------
export interface ForecastQuery {
  biz: string;
  asOf: string; // YYYY-MM-DD
  receiptDelayDays: number; // 0..60
  billShiftDays: number; // -30..30, negative = pay suppliers earlier
  salesFactor: number; // 0.5..1.5
  paths?: number;
}

// The backend may omit fields the UI does not need, so every field is optional on the wire.
const ForecastResponseSchema = ForecastPayloadSchema.partial();
export type ForecastResponse = ReturnType<typeof ForecastResponseSchema.parse>;

export async function fetchForecast(q: ForecastQuery, signal?: AbortSignal): Promise<ForecastResponse> {
  const query = qs({
    biz: q.biz,
    as_of: q.asOf,
    receipt_delay_days: q.receiptDelayDays,
    bill_shift_days: q.billShiftDays,
    sales_factor: q.salesFactor,
    paths: q.paths,
  });
  return getJson(`forecast?${query}`, ForecastResponseSchema, signal);
}

// ---------------------------------------------------------------------------
// Review queue, receivables, export summary
// ---------------------------------------------------------------------------
export function fetchReviewQueue(biz: string, tier: MatchTier | 'ALL', signal?: AbortSignal): Promise<ReviewQueuePayload> {
  return getJson(`review?${qs({ biz, tier: tier === 'ALL' ? undefined : tier })}`, ReviewQueuePayloadSchema, signal);
}

export function fetchReceivables(biz: string, asOf?: string, signal?: AbortSignal): Promise<ReceivablesPayload> {
  return getJson(`receivables?${qs({ biz, as_of: asOf })}`, ReceivablesPayloadSchema, signal);
}

export function fetchExportSummary(biz: string, asOf?: string, signal?: AbortSignal): Promise<ExportPayload> {
  return getJson(`exports/summary?${qs({ biz, as_of: asOf })}`, ExportPayloadSchema, signal);
}

// ---------------------------------------------------------------------------
// Copilot SSE stream
// ---------------------------------------------------------------------------
export interface CopilotStreamRequest {
  question: string;
  businessId: string;
  asOfDate?: string;
}

/**
 * POST /copilot/stream and invoke onChunk for every `data: {...}` event.
 * ADR-001: the body is formal-plane context only (question, business, date). Never add vault values.
 * Resolves when the stream ends; rejects on HTTP/network failure. Unknown event types are ignored.
 */
export async function streamCopilot(
  req: CopilotStreamRequest,
  onChunk: (chunk: CopilotStreamChunk) => void,
  signal?: AbortSignal
): Promise<void> {
  const body = JSON.stringify({
    question: req.question,
    businessId: req.businessId,
    ...(req.asOfDate ? { asOfDate: req.asOfDate } : {}),
  });
  const res = await apiFetch('copilot/stream', {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'text/event-stream' },
    body,
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`Copilot stream failed (${res.status})`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  const flushEvent = (raw: string) => {
    const data = raw
      .split('\n')
      .filter((l) => l.startsWith('data:'))
      .map((l) => l.slice(5).replace(/^ /, ''))
      .join('\n');
    if (!data) return;
    let json: unknown;
    try {
      json = JSON.parse(data);
    } catch {
      return;
    }
    const parsed = CopilotStreamChunkSchema.safeParse(json);
    if (parsed.success) onChunk(parsed.data);
  };

  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n');
    let idx: number;
    while ((idx = buf.indexOf('\n\n')) !== -1) {
      flushEvent(buf.slice(0, idx));
      buf = buf.slice(idx + 2);
    }
  }
  buf += decoder.decode();
  if (buf.trim()) flushEvent(buf);
}

// ---------------------------------------------------------------------------
// Export downloads (through the proxy; bytes pass through untouched)
// ---------------------------------------------------------------------------
export type ExportKind = 'tally-xml' | 'ca-excel' | 'internal-diagnostic-excel';

function exportBody(kind: ExportKind, biz: string, asOf: string, ownerPin?: string) {
  if (kind === 'tally-xml') return { businessId: biz, asOfDate: asOf, voucherType: 'Receipt', includeAutoOnly: true };
  if (kind === 'ca-excel') {
    return { businessId: biz, asOfDate: asOf, format: 'STATUTORY_5_SHEET', omitInformalCash: true };
  }
  // The owner PIN is sent for this one export so the server can check it (a client-side "unlocked"
  // flag proves nothing). Drawer values are never sent.
  return { businessId: biz, asOfDate: asOf, format: 'INTERNAL_DUAL_PLANE_6_SHEET', ownerPin };
}

/** Downloads an export and triggers a browser save. Returns the saved filename. */
export async function downloadExport(
  kind: ExportKind,
  biz: string,
  asOf: string,
  opts: { ownerPin?: string } = {}
): Promise<string> {
  const res = await apiFetch(`exports/${kind}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(exportBody(kind, biz, asOf, opts.ownerPin)),
  });
  if (!res.ok) {
    if (res.status === 502) throw new Error('The API is unreachable.');
    if (res.status === 403) throw new Error('Incorrect owner PIN.');
    throw new Error(`Export failed (${res.status}).`);
  }
  const blob = await res.blob();
  const cd = res.headers.get('content-disposition') ?? '';
  const filename = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(cd)?.[1] ?? `${kind}-${biz}-${asOf}`;
  const href = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = href;
  a.download = decodeURIComponent(filename);
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(href);
  return a.download;
}

// ---------------------------------------------------------------------------
// React helper: try the API, report loading / live / sample
// ---------------------------------------------------------------------------
export type DataStatus = 'loading' | 'live' | 'sample';

/**
 * Runs `load` whenever `deps` change. `status` is 'loading' while a request is in flight,
 * 'live' on success, and 'sample' when the request failed (caller falls back to its sample data).
 * The previous `data` is kept while reloading so the view does not flash.
 */
export function useApiResource<T>(
  load: (signal: AbortSignal) => Promise<T>,
  deps: ReadonlyArray<unknown>
): { data: T | null; status: DataStatus } {
  const [state, setState] = useState<{ data: T | null; status: DataStatus }>({ data: null, status: 'loading' });
  useEffect(() => {
    const ctl = new AbortController();
    setState((s) => (s.status === 'loading' ? s : { data: s.data, status: 'loading' }));
    load(ctl.signal)
      .then((data) => {
        if (!ctl.signal.aborted) setState({ data, status: 'live' });
      })
      .catch((err: unknown) => {
        if (ctl.signal.aborted || isAbort(err)) return;
        setState({ data: null, status: 'sample' });
      });
    return () => ctl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return state;
}

export type { ForecastPayload };
