# ShipIQ - Cargo Optimization Service

Production-ready cargo allocation platform with FastAPI backend and React frontend.

Deployed website: https://shipiq.abhidev.xyz/

<div align="center">

![ShipIQ](https://img.shields.io/badge/ShipIQ-Cargo%20Optimization-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11+-green?style=for-the-badge&logo=python)
![React](https://img.shields.io/badge/React-18-blue?style=for-the-badge&logo=react)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker)

</div>

## Table of Contents

- [Problem Overview](#problem-overview)
- [Problem Solution](#problem-solution)
- [Architecture](#architecture)
- [Environment Variables Guide](#environment-variables-guide)
- [Local Development](#local-development)
- [EC2 Deployment](#ec2-deployment)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Design Decisions](#design-decisions)

## Problem Overview

ShipIQ needs an optimization engine that assigns cargo volumes into tank capacities while following domain constraints.

Core constraints:

- Maximize loaded cargo volume.
- Cargo can be split across multiple tanks.
- One tank can hold only one cargo ID.
- Return clear, auditable allocation output for operations teams.

## Problem Solution

This repository provides:

- FastAPI service for input, optimization, and result retrieval.
- Greedy allocation algorithm with predictable and testable behavior.
- React UI for data input and results visualization.
- Nginx reverse proxy in frontend container to route `/api/*` calls to backend.

Algorithm summary:

- Time complexity: O((n+m) log(n+m)) where n = tanks and m = cargos.
- With cargo splitting enabled, optimal total loaded volume is:

```text
min(sum(cargo_volumes), sum(tank_capacities))
```

## Architecture

```text
Browser
  -> Frontend (React + Nginx)
      -> /api/* reverse-proxy
          -> Backend (FastAPI)
```

Key folders:

- `backend/app`: API routes, models, optimizer, storage.
- `backend/tests`: API and optimizer tests.
- `frontend/src`: React app.
- `frontend/nginx.conf`: frontend static serving + API proxy.
- `docker-compose.yml`: production-style local/EC2 compose.
- `docker-compose.dev.yml`: development compose with hot reload.

## Environment Variables Guide

### Backend

Use in `backend/.env` (or compose environment):

```env
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=info
```

### Frontend

The value of `VITE_API_URL` depends on how frontend is served.

1. Use `VITE_API_URL=/api` when frontend is behind Nginx reverse proxy.
   Example: `docker-compose.yml` setup and EC2 deployment.
2. Use `VITE_API_URL=http://localhost:8000` when frontend runs as Vite dev server in browser and backend is exposed on localhost:8000.

Current defaults in this repo:

- `frontend/.env`: `VITE_API_URL=/api` (proxy mode)
- `frontend/.env.example`: `VITE_API_URL=/api`
- `docker-compose.dev.yml`: frontend env uses `http://localhost:8000`

## Local Development

### Option A: Docker Compose (production-style)

Use this when you want behavior close to EC2 deployment.

```bash
docker compose up -d --build
```

Access:

- App: http://localhost:3000
- API docs via proxy: http://localhost:3000/api/docs
- ReDoc via proxy: http://localhost:3000/api/redoc

Notes:

- Backend is internal-only in this mode (not published to host).
- Frontend routes API calls through `/api`.

### Option B: Docker Compose Dev (hot reload)

Use this for iterative development.

```bash
docker compose -f docker-compose.dev.yml up --build
```

Access:

- Frontend dev server: http://localhost:3000
- Backend direct: http://localhost:8000
- API docs direct: http://localhost:8000/docs

### Option C: Without Docker

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Recommended frontend env for this mode:

```env
VITE_API_URL=http://localhost:8000
```

## EC2 Deployment

Live URL:

- https://shipiq.abhidev.xyz/

Server provisioning done on EC2:

- `git`: clone and update the repository.
- `docker`: build and run backend/frontend containers.
- `nginx`: reverse proxy from 80/443 to app container port.
- `certbot`: issue and renew TLS certificates for HTTPS.

Deployment model:

1. App stack runs with Docker Compose.
2. Frontend container is published on host port 3000.
3. Host Nginx listens on 80/443 and proxies to `127.0.0.1:3000`.
4. Frontend Nginx proxies `/api` to backend container internally.
5. Certbot manages HTTPS certificates and renewal.

Suggested security posture:

- Keep backend container unexposed to public internet.
- Expose only 80/443 in EC2 Security Group.
- Store secrets outside git (SSM Parameter Store or Secrets Manager).

## API Documentation

Core endpoints:

- `GET /health`
- `POST /input`
- `POST /optimize`
- `GET /results`

Docs URLs by mode:

- Compose production-style: `http://localhost:3000/api/docs`
- Compose dev or backend direct: `http://localhost:8000/docs`
- Hosted: `https://shipiq.abhidev.xyz/api/docs`

Example request flow:

```bash
# 1) Submit input
curl -X POST http://localhost:8000/input \
  -H "Content-Type: application/json" \
  -d '{
    "cargos": [
      {"id": "C1", "volume": 1234},
      {"id": "C2", "volume": 900}
    ],
    "tanks": [
      {"id": "T1", "capacity": 1000},
      {"id": "T2", "capacity": 1500}
    ]
  }'

# 2) Optimize
curl -X POST http://localhost:8000/optimize

# 3) Fetch results
curl http://localhost:8000/results
```

## Testing

Backend tests:

```bash
cd backend
pytest tests/ -v
```

Dockerized tests:

```bash
docker compose run --rm backend pytest tests/ -v
```

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Greedy algorithm | Optimal under given constraints with simple, maintainable implementation |
| React + FastAPI split | Clear separation of concerns, independent deployment paths |
| Nginx `/api` proxy | Avoids CORS and keeps browser-facing API endpoint stable |
| Docker-first setup | Consistent behavior across local and EC2 environments |
| In-memory storage | Lightweight for assignment scope, replaceable with persistent datastore |

