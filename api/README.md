# DataGod API

This is the FastAPI-based REST API for the DataGod platform, which aggregates public records data.

## Project Structure

```
api/
├── src/
│   ├── main.py          # Main application entry point
│   ├── api.py           # API routes and endpoints
│   ├── db.py            # Database connection and session management
│   ├── models.py        # Database models
│   ├── config.py        # Configuration settings
│   └── test_api.py      # API tests
├── requirements.txt     # Python dependencies
├── Dockerfile           # Docker configuration
└── README.md            # This file
```

## Features Implemented

- [x] FastAPI application structure
- [x] Database connection with SQLAlchemy
- [x] Authentication system with JWT tokens
- [x] API endpoints for user authentication
- [x] Database models for records, jurisdictions, and data sources
- [x] Configuration management

## Running the API

### Prerequisites
- Python 3.8+
- PostgreSQL database
- Docker (optional, for containerized deployment)

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up the database:
```bash
# Make sure PostgreSQL is running
# Run migrations
alembic upgrade head
```

3. Run the API:
```bash
uvicorn api.src.main:main_app --host 0.0.0.0 --port 8000 --reload
```

### API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `POST /api/v1/token` - Get authentication token
- `GET /api/v1/users/me` - Get current user (protected)

## Testing

Run tests with:
```bash
python -m unittest api/src/test_api.py
```

## Docker Deployment

Build and run with Docker:
```bash
docker build -t datagod-api .
docker run -p 8000:8000 datagod-api
