import type { NextRequest } from 'next/server';

/**
 * Same-origin proxy to the FastAPI service (split-bridge BFF, blueprint 7.3 / 8.1).
 * GET and POST are forwarded to `${COPILOT_API_BASE}/api/v1/<path>` with the query string.
 * The upstream body is returned as a stream, so SSE (copilot/stream) and binary exports pass through unbuffered.
 */
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

// PYTHON_BRIDGE_URL is the name used in docs/specs/01-frontend-architecture.md; accept either.
const API_BASE = () =>
  (process.env.COPILOT_API_BASE ?? process.env.PYTHON_BRIDGE_URL ?? 'http://127.0.0.1:8000').replace(/\/+$/, '');

// Only these upstream response headers are passed to the browser.
const PASS_HEADERS = ['content-type', 'content-disposition'];

async function forward(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }): Promise<Response> {
  const { path } = await ctx.params;
  const target = `${API_BASE()}/api/v1/${path.map(encodeURIComponent).join('/')}${req.nextUrl.search}`;

  const headers = new Headers();
  const contentType = req.headers.get('content-type');
  if (contentType) headers.set('content-type', contentType);
  const accept = req.headers.get('accept');
  if (accept) headers.set('accept', accept);

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: req.method,
      headers,
      body: req.method === 'POST' ? await req.arrayBuffer() : undefined,
      cache: 'no-store',
      signal: req.signal,
    });
  } catch {
    return Response.json({ error: 'api_unreachable' }, { status: 502 });
  }

  const out = new Headers();
  for (const name of PASS_HEADERS) {
    const v = upstream.headers.get(name);
    if (v) out.set(name, v);
  }
  out.set('cache-control', 'no-store, no-transform');
  out.set('x-accel-buffering', 'no');
  return new Response(upstream.body, { status: upstream.status, headers: out });
}

export const GET = forward;
export const POST = forward;
