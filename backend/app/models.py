"""Pydantic models for cargo optimization service."""

from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field, field_validator


class Cargo(BaseModel):
    """Represents a cargo item with a unique ID, volume, and optional weight."""

    id: str = Field(..., description="Unique cargo identifier (e.g. C1)")
    volume: float = Field(..., gt=0, description="Cubic volume of the cargo (m³)")
    weight: float = Field(
        default=0.0,
        ge=0,
        description="Mass of the cargo in metric tonnes (0 = unconstrained)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "C1",
                "volume": 1234,
                "weight": 500,
            }
        }
    }


class Tank(BaseModel):
    """Represents a storage tank with a unique ID, capacity, and optional weight limit."""

    id: str = Field(..., description="Unique tank identifier (e.g. T1)")
    capacity: float = Field(..., gt=0, description="Maximum volume capacity (m³)")
    weight_limit: float = Field(
        default=0.0,
        ge=0,
        description="Maximum load in metric tonnes (0 = unconstrained)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "T1",
                "capacity": 1500,
                "weight_limit": 600,
            }
        }
    }


class InputPayload(BaseModel):
    """Request body for POST /input."""

    cargos: List[Cargo] = Field(..., min_length=1)
    tanks: List[Tank] = Field(..., min_length=1)

    model_config = {
        "json_schema_extra": {
            "example": {
                "cargos": [
                    {"id": "C1", "volume": 1234},
                    {"id": "C2", "volume": 900},
                ],
                "tanks": [
                    {"id": "T1", "capacity": 1000},
                    {"id": "T2", "capacity": 1500},
                ],
            }
        }
    }

    @field_validator("cargos")
    @classmethod
    def cargo_ids_unique(cls, cargos: List[Cargo]) -> List[Cargo]:
        ids = [c.id for c in cargos]
        if len(ids) != len(set(ids)):
            raise ValueError("Cargo IDs must be unique")
        return cargos

    @field_validator("tanks")
    @classmethod
    def tank_ids_unique(cls, tanks: List[Tank]) -> List[Tank]:
        ids = [t.id for t in tanks]
        if len(ids) != len(set(ids)):
            raise ValueError("Tank IDs must be unique")
        return tanks


class AllocationEntry(BaseModel):
    """A single cargo-to-tank allocation record."""

    tank_id: str
    cargo_id: str
    allocated_volume: float
    tank_capacity: float
    utilization_pct: float

    model_config = {
        "json_schema_extra": {
            "example": {
                "tank_id": "T1",
                "cargo_id": "C1",
                "allocated_volume": 1000,
                "tank_capacity": 1000,
                "utilization_pct": 100.0,
            }
        }
    }


class OptimizationResult(BaseModel):
    """Full result returned by the optimizer."""

    allocations: List[AllocationEntry]
    total_cargo_volume: float
    total_tank_capacity: float
    total_loaded_volume: float
    loading_efficiency_pct: float
    unallocated_cargo: List[Cargo]
    unused_tank_capacity: List[Tank]

    model_config = {
        "json_schema_extra": {
            "example": {
                "allocations": [
                    {
                        "tank_id": "T1",
                        "cargo_id": "C1",
                        "allocated_volume": 1000,
                        "tank_capacity": 1000,
                        "utilization_pct": 100.0,
                    },
                    {
                        "tank_id": "T2",
                        "cargo_id": "C1",
                        "allocated_volume": 234,
                        "tank_capacity": 1500,
                        "utilization_pct": 15.6,
                    },
                ],
                "total_cargo_volume": 1234,
                "total_tank_capacity": 2500,
                "total_loaded_volume": 1234,
                "loading_efficiency_pct": 49.36,
                "unallocated_cargo": [],
                "unused_tank_capacity": [{"id": "T2", "capacity": 1266}],
            }
        }
    }


class HealthResponse(BaseModel):
    """Response payload for GET /health."""

    status: str = Field(..., description="Service status value")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "ok",
            }
        }
    }


class InputAcceptedResponse(BaseModel):
    """Success response for POST /input."""

    message: str
    cargo_count: int
    tank_count: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Input stored successfully.",
                "cargo_count": 2,
                "tank_count": 2,
            }
        }
    }


class ErrorResponse(BaseModel):
    """Standard error response for predictable API errors."""

    detail: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "detail": "No input data found. Please POST to /input first.",
            }
        }
    }


class ValidationErrorItem(BaseModel):
    """Single validation error entry returned by FastAPI/Pydantic."""

    loc: List[str | int]
    msg: str
    type: str


class ValidationErrorResponse(BaseModel):
    """Validation response schema for 422 responses."""

    detail: List[ValidationErrorItem]

    model_config = {
        "json_schema_extra": {
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
    }
