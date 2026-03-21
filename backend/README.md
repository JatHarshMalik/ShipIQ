# ShipIQ Backend – Cargo Optimization Service

FastAPI-based REST API for optimizing cargo loading into vessel tanks.

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker

```bash
docker build -t shipiq-backend .
docker run -p 8000:8000 shipiq-backend
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

```bash
pytest tests/ -v
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

- `APP_HOST`: Server host (default: 0.0.0.0)
- `APP_PORT`: Server port (default: 8000)
- `LOG_LEVEL`: Logging level (default: info)
