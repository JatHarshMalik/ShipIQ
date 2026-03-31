"""Unit tests for the cargo optimization algorithm."""

from __future__ import annotations

import pytest

from app.models import Cargo, Tank
from app.optimizer import optimize


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_CARGOS = [
    Cargo(id="C1", volume=1234),
    Cargo(id="C2", volume=4352),
    Cargo(id="C3", volume=3321),
    Cargo(id="C4", volume=2456),
    Cargo(id="C5", volume=5123),
    Cargo(id="C6", volume=1879),
    Cargo(id="C7", volume=4987),
    Cargo(id="C8", volume=2050),
    Cargo(id="C9", volume=3678),
    Cargo(id="C10", volume=5432),
]

SAMPLE_TANKS = [
    Tank(id="T1", capacity=1234),
    Tank(id="T2", capacity=4352),
    Tank(id="T3", capacity=3321),
    Tank(id="T4", capacity=2456),
    Tank(id="T5", capacity=5123),
    Tank(id="T6", capacity=1879),
    Tank(id="T7", capacity=4987),
    Tank(id="T8", capacity=2050),
    Tank(id="T9", capacity=3678),
    Tank(id="T10", capacity=5432),
]


# ---------------------------------------------------------------------------
# Basic correctness
# ---------------------------------------------------------------------------


class TestOptimizeBasic:
    def test_total_volumes_equal_full_load(self):
        result = optimize(SAMPLE_CARGOS, SAMPLE_TANKS)
        assert result.total_cargo_volume == result.total_tank_capacity
        assert result.total_loaded_volume == result.total_tank_capacity
        assert result.loading_efficiency_pct == 100.0

    def test_no_unallocated_cargo_when_capacity_sufficient(self):
        result = optimize(SAMPLE_CARGOS, SAMPLE_TANKS)
        assert result.unallocated_cargo == []

    def test_all_tanks_used(self):
        result = optimize(SAMPLE_CARGOS, SAMPLE_TANKS)
        assert result.unused_tank_capacity == []

    def test_each_tank_holds_single_cargo_type(self):
        """Each tank must reference exactly one cargo ID – explicit constraint."""
        result = optimize(SAMPLE_CARGOS, SAMPLE_TANKS)
        tank_cargo_ids: dict[str, set[str]] = {}
        for entry in result.allocations:
            tank_cargo_ids.setdefault(entry.tank_id, set()).add(entry.cargo_id)
        for tank_id, cargo_ids in tank_cargo_ids.items():
            assert len(cargo_ids) == 1, (
                f"Tank {tank_id} was assigned multiple cargo IDs: {cargo_ids}. "
                "Single-cargo-per-tank constraint violated."
            )

    def test_allocation_volumes_sum_to_total_loaded(self):
        result = optimize(SAMPLE_CARGOS, SAMPLE_TANKS)
        alloc_sum = round(sum(a.allocated_volume for a in result.allocations), 2)
        assert alloc_sum == result.total_loaded_volume

    def test_utilization_pct_within_bounds(self):
        result = optimize(SAMPLE_CARGOS, SAMPLE_TANKS)
        for entry in result.allocations:
            assert 0.0 < entry.utilization_pct <= 100.0

    def test_allocated_volume_does_not_exceed_tank_capacity(self):
        result = optimize(SAMPLE_CARGOS, SAMPLE_TANKS)
        for entry in result.allocations:
            assert entry.allocated_volume <= entry.tank_capacity + 1e-9


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestOptimizeEdgeCases:
    def test_single_cargo_single_tank_exact_fit(self):
        cargos = [Cargo(id="C1", volume=500)]
        tanks = [Tank(id="T1", capacity=500)]
        result = optimize(cargos, tanks)
        assert result.total_loaded_volume == 500
        assert result.loading_efficiency_pct == 100.0
        assert len(result.allocations) == 1
        assert result.allocations[0].cargo_id == "C1"

    def test_cargo_larger_than_single_tank_is_split(self):
        cargos = [Cargo(id="C1", volume=1000)]
        tanks = [Tank(id="T1", capacity=600), Tank(id="T2", capacity=400)]
        result = optimize(cargos, tanks)
        assert result.total_loaded_volume == 1000
        assert len(result.allocations) == 2
        for entry in result.allocations:
            assert entry.cargo_id == "C1"

    def test_capacity_larger_than_cargo_leaves_unallocated_space(self):
        cargos = [Cargo(id="C1", volume=300)]
        tanks = [Tank(id="T1", capacity=1000)]
        result = optimize(cargos, tanks)
        assert result.total_loaded_volume == 300
        assert result.loading_efficiency_pct == 30.0
        assert result.unallocated_cargo == []

    def test_cargo_volume_exceeds_capacity(self):
        cargos = [Cargo(id="C1", volume=5000)]
        tanks = [Tank(id="T1", capacity=3000)]
        result = optimize(cargos, tanks)
        assert result.total_loaded_volume == 3000
        assert len(result.unallocated_cargo) == 1
        assert result.unallocated_cargo[0].id == "C1"
        assert result.unallocated_cargo[0].volume == 2000

    def test_empty_cargo_list_results_in_no_allocations(self):
        result = optimize([], [Tank(id="T1", capacity=500)])
        assert result.total_loaded_volume == 0
        assert result.allocations == []
        assert result.unused_tank_capacity == [Tank(id="T1", capacity=500)]

    def test_empty_tank_list_results_in_no_allocations(self):
        result = optimize([Cargo(id="C1", volume=500)], [])
        assert result.total_loaded_volume == 0
        assert result.allocations == []
        assert result.unallocated_cargo == [Cargo(id="C1", volume=500)]

    def test_many_small_cargos_single_large_tank_one_cargo_per_tank(self):
        """Tank holds only one cargo type: only the first cargo loads into T1."""
        cargos = [Cargo(id=f"C{i}", volume=100) for i in range(1, 6)]
        tanks = [Tank(id="T1", capacity=500)]
        result = optimize(cargos, tanks)
        assert result.total_loaded_volume == 100
        assert len(result.allocations) == 1

    def test_loading_efficiency_partial_fill(self):
        cargos = [Cargo(id="C1", volume=200)]
        tanks = [Tank(id="T1", capacity=1000)]
        result = optimize(cargos, tanks)
        assert result.loading_efficiency_pct == 20.0

    def test_fractional_volumes(self):
        cargos = [Cargo(id="C1", volume=333.33)]
        tanks = [Tank(id="T1", capacity=333.33)]
        result = optimize(cargos, tanks)
        assert result.total_loaded_volume == 333.33


# ---------------------------------------------------------------------------
# Weight constraint tests (new)
# ---------------------------------------------------------------------------


class TestWeightConstraints:
    def test_weight_limit_prevents_overloading(self):
        """Tank weight limit of 100t with cargo density 1t/m³ — only 100m³ loads."""
        cargos = [Cargo(id="C1", volume=500, weight=500)]  # 1 t/m³
        tanks = [Tank(id="T1", capacity=500, weight_limit=100)]
        result = optimize(cargos, tanks)
        assert result.total_loaded_volume == 100.0
        assert result.unallocated_cargo[0].volume == 400.0

    def test_unconstrained_weight_ignores_weight_limit(self):
        """weight=0 means unconstrained; full volume should load regardless of weight_limit."""
        cargos = [Cargo(id="C1", volume=500, weight=0)]  # no weight
        tanks = [Tank(id="T1", capacity=500, weight_limit=100)]
        result = optimize(cargos, tanks)
        assert result.total_loaded_volume == 500.0

    def test_weight_and_volume_both_respected(self):
        """Cargo is limited by volume (200m³ max) not weight (400t headroom)."""
        cargos = [Cargo(id="C1", volume=200, weight=200)]  # 1 t/m³
        tanks = [Tank(id="T1", capacity=300, weight_limit=400)]
        result = optimize(cargos, tanks)
        # volume is the binding constraint here
        assert result.total_loaded_volume == 200.0

    def test_single_cargo_per_tank_is_explicit_not_via_break(self):
        """
        Verify the single-cargo constraint: a tank with plenty of space
        still only receives ONE cargo type.
        """
        cargos = [Cargo(id="C1", volume=50), Cargo(id="C2", volume=50)]
        tanks = [Tank(id="T1", capacity=200)]
        result = optimize(cargos, tanks)
        tank_cargo_ids = {a.cargo_id for a in result.allocations if a.tank_id == "T1"}
        assert len(tank_cargo_ids) == 1, (
            f"T1 received multiple cargo types: {tank_cargo_ids}"
        )
