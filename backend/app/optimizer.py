"""Core cargo-to-tank allocation optimizer.

Algorithm
---------
Because *cargo splitting is allowed* and *each tank holds only one cargo
type*, the problem reduces to a simple greedy fill:

1. Sort tanks by capacity (largest first) – optional but produces a tidy
   allocation that is easier to inspect.
2. Maintain a queue of remaining cargo sorted by volume (largest first).
3. For each tank, fill it with as much of the *current* cargo as possible.
   If the cargo is fully consumed before the tank is full, move to the next
   cargo item (the tank still holds only the first cargo type used there).
4. Continue until every tank is filled or every cargo is exhausted.

Optimality proof (sketch)
--------------------------
With splitting allowed, the maximum loadable volume is
    min(ΣV_cargo, ΣC_tank).
The greedy algorithm always achieves this bound because it never wastes
capacity when cargo is still available.

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


def optimize(cargos: List[Cargo], tanks: List[Tank]) -> OptimizationResult:
    """Run the greedy cargo allocation algorithm.

    Parameters
    ----------
    cargos:
        List of cargo items (id, volume).
    tanks:
        List of tanks (id, capacity).

    Returns
    -------
    OptimizationResult
        Complete allocation breakdown plus summary statistics.
    """
    total_cargo_volume = sum(c.volume for c in cargos)
    total_tank_capacity = sum(t.capacity for t in tanks)

    # Work with mutable copies – sort largest first for a clean allocation.
    cargo_queue: Deque[Tuple[str, float]] = deque(
        sorted(((c.id, c.volume) for c in cargos), key=lambda x: -x[1])
    )
    tank_list: List[Tank] = sorted(tanks, key=lambda t: -t.capacity)

    allocations: List[AllocationEntry] = []
    # Track remaining volume per cargo id (for reporting unallocated cargo).
    remaining: dict[str, float] = {c.id: c.volume for c in cargos}

    for tank in tank_list:
        space_left = tank.capacity

        while space_left > 0 and cargo_queue:
            cargo_id, cargo_remaining = cargo_queue[0]

            loaded = min(space_left, cargo_remaining)
            space_left -= loaded
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

            if remaining[cargo_id] == 0:
                cargo_queue.popleft()
            else:
                # Partial fill: update the remaining volume for this cargo.
                cargo_queue[0] = (cargo_id, remaining[cargo_id])

            # A tank can only hold one cargo type – stop after the first
            # cargo has been assigned to this tank.
            break

    total_loaded = _round2(
        sum(a.allocated_volume for a in allocations)
    )
    efficiency = _round2(
        total_loaded / total_tank_capacity * 100 if total_tank_capacity > 0 else 0.0
    )

    unallocated = [
        Cargo(id=cid, volume=_round2(vol))
        for cid, vol in remaining.items()
        if vol > 0
    ]

    # Determine which tanks received no allocation at all.
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
