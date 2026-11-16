"""FastAPI Application Entrypoint for SME Cash-Flow Copilot Microservice.

Provides clean, typed deep-module interfaces between the Python data/matching
layer (`src/copilot/`) and the web BFF / UI endpoints.
"""
from __future__ import annotations

import logging
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routers.copilot import router as copilot_router
from .routers.exports import router as exports_router
from .routers.forecast import router as forecast_router
from .routers.overview import router as overview_router
from .routers.receivables import router as receivables_router
from .routers.review import router as review_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("copilot.api")

app = FastAPI(
    title="SME Cash-Flow Copilot Headless Microservice",
    description="Local-first cashflow operating intelligence and statutory reconciliation microservice for Indian MSMEs.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 1. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 2. Request Timing & Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = (time.perf_counter() - start_time) * 1000.0
    logger.info(
        "%s %s -> status=%d duration=%.2fms",
        request.method,
        request.url.path,
        response.status_code,
        process_time,
    )
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
    return response


# 3. Router Registration under /api/v1
API_V1_PREFIX = "/api/v1"
app.include_router(overview_router, prefix=API_V1_PREFIX)
app.include_router(forecast_router, prefix=API_V1_PREFIX)
app.include_router(review_router, prefix=API_V1_PREFIX)
app.include_router(receivables_router, prefix=API_V1_PREFIX)
app.include_router(copilot_router, prefix=API_V1_PREFIX)
app.include_router(exports_router, prefix=f"{API_V1_PREFIX}/exports", tags=["exports"])

# Also register export alias (/api/v1/export) for Next.js BFF compatibility
app.include_router(exports_router, prefix=f"{API_V1_PREFIX}/export", tags=["exports_alias"])



@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok", "service": "copilot-api", "version": "0.1.0"}


@app.get("/", tags=["system"])
def root():
    return {
        "service": "SME Cash-Flow Copilot API",
        "version": "0.1.0",
        "docs": "/docs",
        "status": "active",
    }
