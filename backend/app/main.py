"""FastAPI application entry point.

Endpoints
---------
POST /input     – Submit cargo and tank data.
POST /optimize  – Run the allocation algorithm on the stored input.
GET  /results   – Retrieve the latest allocation result.
GET  /health    – Liveness check.
"""

from __future__ import annotations

import logging
import os
from typing import Dict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

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

app = FastAPI(
    title="ShipIQ – Cargo Optimization Service",
    description=(
        "Production-ready REST API for optimizing cargo loading into vessel tanks. "
        "Supports cargo splitting, maximises loaded volume, and returns a detailed "
        "allocation breakdown."
    ),
    version="1.0.0",
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
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.post(
    "/input",
    status_code=status.HTTP_201_CREATED,
    tags=["workflow"],
    summary="Submit cargo and tank data",
    response_model=InputAcceptedResponse,
    responses={
        422: {
            "model": ValidationErrorResponse,
            "description": "Validation error: payload shape or values are invalid.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "cargos", 0, "volume"],
                                "msg": "Input should be greater than 0",
                                "type": "greater_than",
                            }
                        ]
                    }
                }
            },
        }
    },
)
def post_input(payload: InputPayload) -> InputAcceptedResponse:
    """Accept cargo and tank lists for the current session.

    Storing new input **invalidates** any previously computed result.
    """
    store.save_input(payload)
    logger.info(
        "Input stored – %d cargos, %d tanks",
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


@app.post(
    "/optimize",
    status_code=status.HTTP_200_OK,
    tags=["workflow"],
    summary="Run allocation optimization",
    response_model=OptimizationResult,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "No input data has been submitted yet.",
        }
    },
)
def post_optimize() -> OptimizationResult:
    """Execute the greedy cargo-to-tank allocation algorithm.

    Requires input to have been submitted via **POST /input** first.
    Input is stored in-memory, so restarting the backend clears it.
    The result is persisted and retrievable via **GET /results**.
    """
    payload = store.get_input()
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No input data found. Please POST to /input first.",
        )

    result = optimize(payload.cargos, payload.tanks)
    store.save_result(result)
    logger.info(
        "Optimization complete – loaded %.2f / %.2f (%.1f%%)",
        result.total_loaded_volume,
        result.total_tank_capacity,
        result.loading_efficiency_pct,
    )
    return result


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@app.get(
    "/results",
    status_code=status.HTTP_200_OK,
    tags=["workflow"],
    summary="Retrieve latest allocation result",
    response_model=OptimizationResult,
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Optimization has not been executed yet for current input.",
        }
    },
)
def get_results() -> OptimizationResult:
    """Return the most-recently computed allocation.

    Returns 404 if **POST /optimize** has not been called yet (or if input
    was re-submitted after the last optimization run).
    """
    result = store.get_result()
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No optimization result available. Please POST to /optimize first.",
        )
    return result
