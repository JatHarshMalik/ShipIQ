"""Integration tests for the REST API."""

from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient

# Use an in-memory (temp) DB for tests
os.environ["SHIPIQ_DB_PATH"] = ":memory:"

from app.main import app
from app.storage import store

SAMPLE_PAYLOAD = {
    "cargos": [
        {"id": "C1", "volume": 1234},
        {"id": "C2", "volume": 4352},
        {"id": "C3", "volume": 3321},
        {"id": "C4", "volume": 2456},
        {"id": "C5", "volume": 5123},
        {"id": "C6", "volume": 1879},
        {"id": "C7", "volume": 4987},
        {"id": "C8", "volume": 2050},
        {"id": "C9", "volume": 3678},
        {"id": "C10", "volume": 5432},
    ],
    "tanks": [
        {"id": "T1", "capacity": 1234},
        {"id": "T2", "capacity": 4352},
        {"id": "T3", "capacity": 3321},
        {"id": "T4", "capacity": 2456},
        {"id": "T5", "capacity": 5123},
        {"id": "T6", "capacity": 1879},
        {"id": "T7", "capacity": 4987},
        {"id": "T8", "capacity": 2050},
        {"id": "T9", "capacity": 3678},
        {"id": "T10", "capacity": 5432},
    ],
}


@pytest.fixture(autouse=True)
def reset_store():
    store.clear("default")
    yield
    store.clear("default")


@pytest.fixture()
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /input
# ---------------------------------------------------------------------------


class TestPostInput:
    def test_valid_input_returns_201(self, client):
        resp = client.post("/input", json=SAMPLE_PAYLOAD)
        assert resp.status_code == 201
        body = resp.json()
        assert body["cargo_count"] == 10
        assert body["tank_count"] == 10

    def test_session_input_returns_201(self, client):
        resp = client.post("/input/user-abc", json=SAMPLE_PAYLOAD)
        assert resp.status_code == 201

    def test_empty_cargos_returns_422(self, client):
        payload = {**SAMPLE_PAYLOAD, "cargos": []}
        assert client.post("/input", json=payload).status_code == 422

    def test_empty_tanks_returns_422(self, client):
        payload = {**SAMPLE_PAYLOAD, "tanks": []}
        assert client.post("/input", json=payload).status_code == 422

    def test_duplicate_cargo_ids_returns_422(self, client):
        payload = {
            "cargos": [{"id": "C1", "volume": 100}, {"id": "C1", "volume": 200}],
            "tanks": [{"id": "T1", "capacity": 300}],
        }
        assert client.post("/input", json=payload).status_code == 422

    def test_duplicate_tank_ids_returns_422(self, client):
        payload = {
            "cargos": [{"id": "C1", "volume": 100}],
            "tanks": [{"id": "T1", "capacity": 300}, {"id": "T1", "capacity": 400}],
        }
        assert client.post("/input", json=payload).status_code == 422

    def test_negative_volume_returns_422(self, client):
        payload = {
            "cargos": [{"id": "C1", "volume": -100}],
            "tanks": [{"id": "T1", "capacity": 300}],
        }
        assert client.post("/input", json=payload).status_code == 422

    def test_zero_capacity_returns_422(self, client):
        payload = {
            "cargos": [{"id": "C1", "volume": 100}],
            "tanks": [{"id": "T1", "capacity": 0}],
        }
        assert client.post("/input", json=payload).status_code == 422

    def test_new_input_clears_previous_result(self, client):
        client.post("/input", json=SAMPLE_PAYLOAD)
        client.post("/optimize")
        assert client.get("/results").status_code == 200
        client.post("/input", json=SAMPLE_PAYLOAD)
        assert client.get("/results").status_code == 404

    def test_weight_fields_accepted(self, client):
        payload = {
            "cargos": [{"id": "C1", "volume": 500, "weight": 250}],
            "tanks": [{"id": "T1", "capacity": 500, "weight_limit": 300}],
        }
        assert client.post("/input", json=payload).status_code == 201


# ---------------------------------------------------------------------------
# POST /optimize
# ---------------------------------------------------------------------------


class TestPostOptimize:
    def test_optimize_without_input_returns_400(self, client):
        assert client.post("/optimize").status_code == 400

    def test_optimize_returns_result(self, client):
        client.post("/input", json=SAMPLE_PAYLOAD)
        resp = client.post("/optimize")
        assert resp.status_code == 200
        body = resp.json()
        assert "allocations" in body
        assert body["loading_efficiency_pct"] == 100.0

    def test_optimize_full_load_sample_data(self, client):
        client.post("/input", json=SAMPLE_PAYLOAD)
        body = client.post("/optimize").json()
        expected = sum(c["volume"] for c in SAMPLE_PAYLOAD["cargos"])
        assert body["total_loaded_volume"] == expected
        assert body["unallocated_cargo"] == []

    def test_optimize_each_tank_single_cargo(self, client):
        client.post("/input", json=SAMPLE_PAYLOAD)
        body = client.post("/optimize").json()
        tank_cargo_map: dict[str, set[str]] = {}
        for entry in body["allocations"]:
            tank_cargo_map.setdefault(entry["tank_id"], set()).add(entry["cargo_id"])
        for tank_id, cargo_set in tank_cargo_map.items():
            assert len(cargo_set) == 1, f"Tank {tank_id} has multiple cargos"

    def test_optimize_partial_capacity(self, client):
        payload = {
            "cargos": [{"id": "C1", "volume": 500}],
            "tanks": [{"id": "T1", "capacity": 1000}],
        }
        client.post("/input", json=payload)
        body = client.post("/optimize").json()
        assert body["total_loaded_volume"] == 500
        assert body["loading_efficiency_pct"] == 50.0

    def test_optimize_session_isolated(self, client):
        """Two sessions should not share results."""
        client.post("/input/s1", json=SAMPLE_PAYLOAD)
        client.post("/optimize/s1")
        # s2 has no input – should 400
        assert client.post("/optimize/s2").status_code == 400


# ---------------------------------------------------------------------------
# GET /results
# ---------------------------------------------------------------------------


class TestGetResults:
    def test_results_before_optimize_returns_404(self, client):
        assert client.get("/results").status_code == 404

    def test_results_after_optimize_returns_200(self, client):
        client.post("/input", json=SAMPLE_PAYLOAD)
        client.post("/optimize")
        resp = client.get("/results")
        assert resp.status_code == 200
        assert "allocations" in resp.json()

    def test_results_consistent_with_optimize_response(self, client):
        client.post("/input", json=SAMPLE_PAYLOAD)
        opt_body = client.post("/optimize").json()
        res_body = client.get("/results").json()
        assert opt_body == res_body

    def test_results_persist_across_calls(self, client):
        """Results must survive a second GET /results call (persistence check)."""
        client.post("/input", json=SAMPLE_PAYLOAD)
        client.post("/optimize")
        first = client.get("/results").json()
        second = client.get("/results").json()
        assert first == second


# ---------------------------------------------------------------------------
# DELETE /session
# ---------------------------------------------------------------------------


class TestDeleteSession:
    def test_delete_session_clears_data(self, client):
        client.post("/input/to-delete", json=SAMPLE_PAYLOAD)
        client.post("/optimize/to-delete")
        assert client.get("/results/to-delete").status_code == 200
        client.delete("/session/to-delete")
        assert client.get("/results/to-delete").status_code == 404
