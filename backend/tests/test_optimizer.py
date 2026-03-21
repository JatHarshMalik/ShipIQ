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
        """When total cargo == total capacity everything should be loaded."""
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

    def test_each_tank_holds_single_cargo(self):
        """A tank must reference at most one cargo ID."""
        result = optimize(SAMPLE_CARGOS, SAMPLE_TANKS)
        tank_cargo_ids: dict[str, set[str]] = {}
        for entry in result.allocations:
            tank_cargo_ids.setdefault(entry.tank_id, set()).add(entry.cargo_id)
        for tank_id, cargo_ids in tank_cargo_ids.items():
            assert len(cargo_ids) == 1, (
                f"Tank {tank_id} was assigned multiple cargo IDs: {cargo_ids}"
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
        """A cargo of 1000 split across two tanks of 600 and 400."""
        cargos = [Cargo(id="C1", volume=1000)]
        tanks = [Tank(id="T1", capacity=600), Tank(id="T2", capacity=400)]
        result = optimize(cargos, tanks)
        assert result.total_loaded_volume == 1000
        assert len(result.allocations) == 2
        # Both tanks should carry C1
        for entry in result.allocations:
            assert entry.cargo_id == "C1"

    def test_capacity_larger_than_cargo_leaves_unallocated_space(self):
        """Tank capacity exceeds total cargo – some capacity is unused."""
        cargos = [Cargo(id="C1", volume=300)]
        tanks = [Tank(id="T1", capacity=1000)]
        result = optimize(cargos, tanks)
        assert result.total_loaded_volume == 300
        assert result.loading_efficiency_pct == 30.0
        assert result.unallocated_cargo == []

    def test_cargo_volume_exceeds_capacity(self):
        """When total cargo > total capacity, partial loading occurs."""
        cargos = [Cargo(id="C1", volume=5000)]
        tanks = [Tank(id="T1", capacity=3000)]
        result = optimize(cargos, tanks)
        assert result.total_loaded_volume == 3000
        assert len(result.unallocated_cargo) == 1
        assert result.unallocated_cargo[0].id == "C1"
        assert result.unallocated_cargo[0].volume == 2000

    def test_multiple_cargos_fit_in_one_tank_each(self):
        cargos = [Cargo(id=f"C{i}", volume=100 * i) for i in range(1, 4)]
        tanks = [Tank(id=f"T{i}", capacity=100 * i) for i in range(1, 4)]
        result = optimize(cargos, tanks)
        assert result.total_loaded_volume == sum(100 * i for i in range(1, 4))
        assert result.unallocated_cargo == []

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

    def test_many_small_cargos_fill_large_tank(self):
        """Tank holds only one cargo type: only the first cargo (100 vol) loads into T1.

        Even though the tank has capacity for all 5 cargos, the constraint
        'one cargo ID per tank' means only 100 units are loaded and the
        remaining capacity is unused.
        """
        cargos = [Cargo(id=f"C{i}", volume=100) for i in range(1, 6)]
        tanks = [Tank(id="T1", capacity=500)]
        result = optimize(cargos, tanks)
        # Tank can only hold ONE cargo type, so at most 100 can be loaded into T1
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
