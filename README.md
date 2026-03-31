# ShipIQ — Cargo Optimization Service

Production-ready cargo allocation platform with FastAPI backend and React frontend.

**Deployed:** https://shipiq.abhidev.xyz/

---

## What's new in v2

| Area | Change |
|---|---|
| **Persistence** | SQLite replaces in-memory store — data survives restarts |
| **CORS** | Restricted to configured origins (no more wildcard `*`) |
| **Rate limiting** | 60 req / 60 s per IP, configurable via env vars |
| **Session isolation** | `/input/:id`, `/optimize/:id`, `/results/:id` routes for concurrent users |
| **Weight constraints** | `weight` on Cargo, `weight_limit` on Tank — optimizer respects both |
| **Explicit constraint** | Single-cargo-per-tank rule is now an explicit code path, not a `break` |
| **Frontend API** | axios removed; pure `fetch`-based `services/api.js` |
| **CSV import** | Drag-and-drop / file-picker CSV import for cargos and tanks |
| **CSV export** | Download allocation results as CSV with one click |
| **Input validation** | Real-time per-row error messages before you can run optimization |
| **Dependencies** | Updated to latest stable FastAPI, Pydantic, httpx, pytest |
| **Tests** | Full session isolation tests, weight constraint tests, persistence tests |

---

## Quick start

```bash
# Production
docker compose up --build

# Development (hot reload)
docker compose -f docker-compose.dev.yml up --build
```

- Frontend: http://localhost:3000  
- Backend API docs: http://localhost:8000/docs

---

## Backend environment variables

| Variable | Default | Description |
|---|---|---|
| `SHIPIQ_DB_PATH` | `shipiq.db` | SQLite file path |
| `ALLOWED_ORIGINS` | `http://localhost:3000,...` | Comma-separated CORS origins |
| `RATE_LIMIT_CALLS` | `60` | Max requests per IP per window |
| `RATE_LIMIT_PERIOD` | `60` | Rate limit window in seconds |
| `LOG_LEVEL` | `info` | Logging level |

Copy `backend/.env.example` → `backend/.env` and customise.

---

## API endpoints

### Workflow (default session)
| Method | Path | Description |
|---|---|---|
| `POST` | `/input` | Submit cargo & tank data |
| `POST` | `/optimize` | Run allocation |
| `GET` | `/results` | Fetch latest result |

### Multi-session
| Method | Path | Description |
|---|---|---|
| `POST` | `/input/{session_id}` | Submit for a named session |
| `POST` | `/optimize/{session_id}` | Run for a named session |
| `GET` | `/results/{session_id}` | Fetch result for a named session |
| `DELETE` | `/session/{session_id}` | Clear a session |

### System
| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness probe |

Full interactive docs at `/docs` (Swagger UI).

---

## CSV import format

**Cargo CSV** (`id,volume,weight`)
```
id,volume,weight
C1,1234,500
C2,4352,0
```

**Tank CSV** (`id,capacity,weight_limit`)
```
id,capacity,weight_limit
T1,1500,600
T2,4000,0
```
`weight` / `weight_limit` = 0 means unconstrained.

Download starter templates from the UI with the **↓ Template** button.

---

## Running tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

---

## Project structure

```
ShipIQ/
├── backend/
│   ├── app/
│   │   ├── main.py       # FastAPI app, routes, CORS, rate limiting
│   │   ├── models.py     # Pydantic models (Cargo, Tank, results)
│   │   ├── optimizer.py  # Greedy allocation algorithm
│   │   └── storage.py    # SQLite persistence layer
│   ├── tests/
│   │   ├── test_api.py       # Integration tests
│   │   └── test_optimizer.py # Unit tests (incl. weight constraints)
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.jsx              # Main component
│       ├── services/api.js      # Fetch-based API client
│       ├── utils/csv.js         # CSV import/export utilities
│       └── index.css
├── docker-compose.yml
└── docker-compose.dev.yml
```
