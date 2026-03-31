"""FastAPI application entry point.

Endpoints
---------
POST /input              – Submit cargo and tank data (default session).
POST /input/{session_id} – Submit cargo and tank data for a named session.
POST /optimize           – Run allocation on the default session.
POST /optimize/{session_id} – Run allocation on a named session.
GET  /results            – Retrieve result for the default session.
GET  /results/{session_id}  – Retrieve result for a named session.
DELETE /session/{session_id} – Clear a session's data.
GET  /health             – Liveness check.
"""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from typing import Dict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.models import (
    ErrorResponse,
    HealthResponse,
    InputAcceptedResponse,
    InputPayload,
    OptimizationResult,
    ValidationErrorResponse,
)
from app.optimizer import optimize
from app.storage import store

load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "info").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate limiting (simple in-process token bucket per IP)
# ---------------------------------------------------------------------------

RATE_LIMIT_CALLS = int(os.getenv("RATE_LIMIT_CALLS", "60"))
RATE_LIMIT_PERIOD = int(os.getenv("RATE_LIMIT_PERIOD", "60"))  # seconds

_rate_store: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(ip: str) -> bool:
    """Return True if the IP is within rate limits, False if exceeded."""
    now = time.monotonic()
    window_start = now - RATE_LIMIT_PERIOD
    calls = _rate_store[ip]
    # Drop timestamps outside the current window
    _rate_store[ip] = [t for t in calls if t > window_start]
    if len(_rate_store[ip]) >= RATE_LIMIT_CALLS:
        return False
    _rate_store[ip].append(now)
    return True


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5173,https://shipiq.abhidev.xyz",
    ).split(",")
    if o.strip()
]

app = FastAPI(
    title="ShipIQ – Cargo Optimization Service",
    description=(
        "Production-ready REST API for optimizing cargo loading into vessel tanks. "
        "Supports cargo splitting, maximises loaded volume, and returns a detailed "
        "allocation breakdown."
    ),
    version="2.0.0",
    openapi_tags=[
        {
            "name": "system",
            "description": "Operational endpoints for health and service checks.",
        },
        {
            "name": "workflow",
            "description": (
                "Main cargo-allocation workflow: submit input, run optimization, "
                "and fetch the latest result."
            ),
        },
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(ip):
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please slow down."},
        )
    return await call_next(request)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get(
    "/health",
    tags=["system"],
    summary="Service health check",
    response_model=HealthResponse,
)
def health() -> Dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

_INPUT_RESPONSES = {
    422: {
        "model": ValidationErrorResponse,
        "description": "Validation error: payload shape or values are invalid.",
    }
}


@app.post(
    "/input",
    status_code=status.HTTP_201_CREATED,
    tags=["workflow"],
    summary="Submit cargo and tank data (default session)",
    response_model=InputAcceptedResponse,
    responses=_INPUT_RESPONSES,
)
def post_input(payload: InputPayload) -> InputAcceptedResponse:
    """Accept cargo and tank lists for the default session."""
    return _handle_input(payload, "default")


@app.post(
    "/input/{session_id}",
    status_code=status.HTTP_201_CREATED,
    tags=["workflow"],
    summary="Submit cargo and tank data for a named session",
    response_model=InputAcceptedResponse,
    responses=_INPUT_RESPONSES,
)
def post_input_session(
    session_id: str, payload: InputPayload
) -> InputAcceptedResponse:
    """Accept cargo and tank lists for a specific session."""
    return _handle_input(payload, session_id)


def _handle_input(payload: InputPayload, session_id: str) -> InputAcceptedResponse:
    store.save_input(payload, session_id)
    logger.info(
        "Input stored [session=%s] – %d cargos, %d tanks",
        session_id,
        len(payload.cargos),
        len(payload.tanks),
    )
    return InputAcceptedResponse(
        message="Input stored successfully.",
        cargo_count=len(payload.cargos),
        tank_count=len(payload.tanks),
    )


# ---------------------------------------------------------------------------
# Optimize
# ---------------------------------------------------------------------------

_OPTIMIZE_RESPONSES = {
    400: {
        "model": ErrorResponse,
        "description": "No input data has been submitted yet.",
    }
}


@app.post(
    "/optimize",
    status_code=status.HTTP_200_OK,
    tags=["workflow"],
    summary="Run allocation optimization (default session)",
    response_model=OptimizationResult,
    responses=_OPTIMIZE_RESPONSES,
)
def post_optimize() -> OptimizationResult:
    """Execute the greedy cargo-to-tank allocation on the default session."""
    return _handle_optimize("default")


@app.post(
    "/optimize/{session_id}",
    status_code=status.HTTP_200_OK,
    tags=["workflow"],
    summary="Run allocation optimization for a named session",
    response_model=OptimizationResult,
    responses=_OPTIMIZE_RESPONSES,
)
def post_optimize_session(session_id: str) -> OptimizationResult:
    """Execute the greedy allocation algorithm for a specific session."""
    return _handle_optimize(session_id)


def _handle_optimize(session_id: str) -> OptimizationResult:
    payload = store.get_input(session_id)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No input data found. Please POST to /input first.",
        )
    result = optimize(payload.cargos, payload.tanks)
    store.save_result(result, session_id)
    logger.info(
        "Optimization complete [session=%s] – loaded %.2f / %.2f (%.1f%%)",
        session_id,
        result.total_loaded_volume,
        result.total_tank_capacity,
        result.loading_efficiency_pct,
    )
    return result


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

_RESULTS_RESPONSES = {
    404: {
        "model": ErrorResponse,
        "description": "Optimization has not been run yet for this session.",
    }
}


@app.get(
    "/results",
    status_code=status.HTTP_200_OK,
    tags=["workflow"],
    summary="Retrieve latest result (default session)",
    response_model=OptimizationResult,
    responses=_RESULTS_RESPONSES,
)
def get_results() -> OptimizationResult:
    """Return the most-recently computed allocation for the default session."""
    return _handle_get_results("default")


@app.get(
    "/results/{session_id}",
    status_code=status.HTTP_200_OK,
    tags=["workflow"],
    summary="Retrieve latest result for a named session",
    response_model=OptimizationResult,
    responses=_RESULTS_RESPONSES,
)
def get_results_session(session_id: str) -> OptimizationResult:
    """Return the most-recently computed allocation for a specific session."""
    return _handle_get_results(session_id)


def _handle_get_results(session_id: str) -> OptimizationResult:
    result = store.get_result(session_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No optimization result available. Please POST to /optimize first.",
        )
    return result


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------


@app.delete(
    "/session/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["workflow"],
    summary="Clear a session's data",
)
def delete_session(session_id: str) -> None:
    """Remove all stored input and results for a session."""
    store.clear(session_id)
    logger.info("Session cleared [session=%s]", session_id)

