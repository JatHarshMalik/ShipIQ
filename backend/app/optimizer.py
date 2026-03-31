"""Core cargo-to-tank allocation optimizer.

Algorithm
---------
Because *cargo splitting is allowed* and *each tank holds only one cargo
type*, the problem reduces to a greedy fill:

1. Sort tanks by capacity (largest first).
2. Maintain a deque of remaining cargo sorted by volume (largest first).
3. For each tank, fill it with as much of the *current* cargo as possible,
   subject to:
     a. The tank's remaining volume capacity.
     b. The tank's weight limit (if > 0): loaded weight ≤ weight_limit.
   Each tank is assigned **exactly one cargo type** (hard constraint).
4. Continue until every tank is filled or every cargo is exhausted.

Optimality proof (sketch)
--------------------------
With splitting allowed and no weight constraints, the maximum loadable
volume is min(ΣV_cargo, ΣC_tank).  The greedy algorithm always achieves
this bound because it never wastes capacity when cargo is still available.
Weight limits may reduce the achievable volume below this theoretical max.

Time complexity: O(n log n + m log m + n + m) ≈ O((n+m) log(n+m))
where n = number of tanks, m = number of cargos.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, List, Tuple

from app.models import AllocationEntry, Cargo, OptimizationResult, Tank


def _round2(value: float) -> float:
    """Round to 2 decimal places for clean output."""
    return round(value, 2)


def _weight_per_volume(cargo_volume: float, cargo_weight: float) -> float:
    """Return cargo weight density (t/m³), or 0 if weight is unconstrained."""
    if cargo_weight <= 0 or cargo_volume <= 0:
        return 0.0
    return cargo_weight / cargo_volume


def _max_volume_by_weight(
    space_left: float,
    weight_loaded: float,
    weight_limit: float,
    density: float,
) -> float:
    """
    Given remaining volume space and weight headroom, return the maximum
    volume that can be loaded without breaching the weight limit.

    If density is 0 (unconstrained), only volume limits apply.
    """
    if weight_limit <= 0 or density <= 0:
        # No weight constraint active
        return space_left
    weight_headroom = weight_limit - weight_loaded
    if weight_headroom <= 0:
        return 0.0
    max_by_weight = weight_headroom / density
    return min(space_left, max_by_weight)


def optimize(cargos: List[Cargo], tanks: List[Tank]) -> OptimizationResult:
    """Run the greedy cargo allocation algorithm.

    Parameters
    ----------
    cargos:
        List of cargo items (id, volume, weight).
    tanks:
        List of tanks (id, capacity, weight_limit).

    Returns
    -------
    OptimizationResult
        Complete allocation breakdown plus summary statistics.
    """
    total_cargo_volume = sum(c.volume for c in cargos)
    total_tank_capacity = sum(t.capacity for t in tanks)

    # Work with mutable copies – sort largest first for a clean allocation.
    cargo_queue: Deque[Tuple[str, float, float]] = deque(
        sorted(
            ((c.id, c.volume, c.weight) for c in cargos),
            key=lambda x: -x[1],
        )
    )
    tank_list: List[Tank] = sorted(tanks, key=lambda t: -t.capacity)

    allocations: List[AllocationEntry] = []
    # Track remaining volume per cargo id (for reporting unallocated cargo).
    remaining: dict[str, float] = {c.id: c.volume for c in cargos}

    for tank in tank_list:
        space_left = tank.capacity
        weight_loaded = 0.0  # tonnes loaded into this tank so far

        if not cargo_queue:
            break

        # --- EXPLICIT single-cargo-per-tank constraint ---
        # Each tank receives exactly one cargo type.  We peek at the front
        # of the queue and allocate as much of that cargo as the tank allows,
        # then move to the next tank regardless of remaining space.
        cargo_id, cargo_remaining, cargo_weight = cargo_queue[0]
        density = _weight_per_volume(
            # Use original volume to compute density
            next(c.volume for c in cargos if c.id == cargo_id),
            cargo_weight,
        )

        loaded = _max_volume_by_weight(
            space_left, weight_loaded, tank.weight_limit, density
        )
        loaded = min(loaded, cargo_remaining)

        if loaded <= 0:
            # Tank weight limit prevents any loading – leave tank empty.
            continue

        weight_loaded += loaded * density if density > 0 else 0.0
        remaining[cargo_id] -= loaded

        utilization = _round2(loaded / tank.capacity * 100)
        allocations.append(
            AllocationEntry(
                tank_id=tank.id,
                cargo_id=cargo_id,
                allocated_volume=_round2(loaded),
                tank_capacity=tank.capacity,
                utilization_pct=utilization,
            )
        )

        if remaining[cargo_id] <= 1e-9:
            cargo_queue.popleft()
        else:
            # Update remaining volume for this cargo.
            cargo_queue[0] = (cargo_id, remaining[cargo_id], cargo_weight)

    total_loaded = _round2(sum(a.allocated_volume for a in allocations))
    efficiency = _round2(
        total_loaded / total_tank_capacity * 100 if total_tank_capacity > 0 else 0.0
    )

    unallocated = [
        Cargo(id=cid, volume=_round2(vol))
        for cid, vol in remaining.items()
        if vol > 1e-9
    ]

    allocated_tank_ids = {a.tank_id for a in allocations}
    unused_tanks = [t for t in tanks if t.id not in allocated_tank_ids]

    return OptimizationResult(
        allocations=allocations,
        total_cargo_volume=_round2(total_cargo_volume),
        total_tank_capacity=_round2(total_tank_capacity),
        total_loaded_volume=total_loaded,
        loading_efficiency_pct=efficiency,
        unallocated_cargo=unallocated,
        unused_tank_capacity=unused_tanks,
    )
