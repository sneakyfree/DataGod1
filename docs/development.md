# DataGod Development Guide

This document provides guidelines and instructions for developing the DataGod platform.

## Table of Contents

- [Quick Start](#quick-start)
- [Architecture Overview](#architecture-overview)
- [Development Environment Setup](#development-environment-setup)
- [Project Structure](#project-structure)
- [Common Development Tasks](#common-development-tasks)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Database Development](#database-development)
- [API Development](#api-development)
- [Frontend Development](#frontend-development)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

Get up and running in 5 minutes:

```bash
# Clone and setup
git clone https://github.com/your-org/DataGod.git
cd DataGod

# Option 1: Docker (recommended - no local dependencies needed)
cp .env.example .env
docker-compose up -d
# Access: http://localhost:8000/docs (API), http://localhost:3000 (Frontend)

# Option 2: Local development
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn api.src.main:app --reload --port 8000

# In another terminal for frontend
cd frontend/datagod-frontend
npm install
npm run dev
```

---

## Architecture Overview

DataGod follows a modular architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│                  (Next.js + TypeScript)                     │
│         http://localhost:3000                               │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP/REST
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                       │
│    ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│    │ Auth     │ │ Search   │ │ Records  │ │ Export   │     │
│    │ /auth/*  │ │ /search/*│ │ /records/*│ │ /export/*│     │
│    └──────────┘ └──────────┘ └──────────┘ └──────────┘     │
│         http://localhost:8000/api/v2                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  PostgreSQL   │  │    Redis      │  │    Celery     │
│   Database    │  │    Cache      │  │   Workers     │
│   :5432       │  │   :6379       │  │ (background)  │
└───────────────┘  └───────────────┘  └───────────────┘
```

**Key Components:**

| Component | Technology | Purpose |
|-----------|------------|---------|
| API | FastAPI (Python 3.11) | REST API, authentication, business logic |
| Frontend | Next.js 14 + TypeScript | User interface, dashboards |
| Database | PostgreSQL 15 | Data persistence, records |
| Cache | Redis 7 | Session cache, rate limiting |
| Workers | Celery | Background tasks, scraping |
| Scrapers | Custom Python | Data collection from public records |

---

## Development Environment Setup

### Prerequisites

**Required:**
1. Python 3.9+ (3.11 recommended)
2. Node.js 18+ (for frontend)
3. Git

**Optional but Recommended:**
4. Docker & Docker Compose (simplifies setup)
5. PostgreSQL 15+ (if not using Docker)
6. Redis 7+ (if not using Docker)
7. VS Code with Python and ESLint extensions

### Setting Up the Environment

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/datagod.git
   cd datagod
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Node.js dependencies** (for frontend):
   ```bash
   cd frontend
   npm install
   ```

5. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

6. **Initialize the database**:
   ```bash
   alembic upgrade head
   ```

7. **Run the development server**:
   ```bash
   # Backend
   python datagod/main.py
   
   # Frontend (in separate terminal)
   cd frontend
   npm run dev
   ```

## Project Structure

```
DataGod/
├── api/                          # FastAPI REST API
│   └── src/
│       ├── main.py              # Application entry point
│       ├── api_v2.py            # API v2 endpoints
│       └── api_v2_simple.py     # Simplified API
│
├── datagod/                      # Core Python package
│   ├── config/                  # Configuration management
│   │   └── settings.py          # Environment settings
│   ├── models/                  # SQLAlchemy models
│   │   ├── user.py              # User model
│   │   ├── jurisdiction.py      # Jurisdiction model
│   │   ├── record.py            # Record model
│   │   └── entity.py            # Entity model
│   ├── scrapers/                # Data collectors
│   │   ├── base_scraper.py      # Base scraper class
│   │   ├── base_api_integration.py  # API integration base
│   │   ├── texas_api.py         # Texas scraper
│   │   ├── california_api.py    # California scraper
│   │   └── ...                  # Other state scrapers
│   ├── services/                # Business logic services
│   │   └── email_service.py     # Email notifications
│   ├── ml/                      # Machine learning modules
│   │   └── mortgage/            # Mortgage prediction
│   └── utils/                   # Utility functions
│       ├── data_validation.py   # Input validation
│       └── data_processor.py    # Data processing
│
├── frontend/datagod-frontend/    # Next.js frontend
│   ├── src/
│   │   ├── components/          # React components
│   │   │   ├── auth/            # Login, Register forms
│   │   │   ├── dashboard/       # Dashboard widgets
│   │   │   └── search/          # Search interface
│   │   ├── services/            # API client services
│   │   │   └── api.ts           # Backend API calls
│   │   └── pages/               # Next.js pages
│   └── package.json
│
├── tests/                        # Test suite
│   ├── conftest.py              # Pytest fixtures
│   ├── test_api.py              # API tests
│   ├── test_models.py           # Model tests
│   └── test_scrapers.py         # Scraper tests
│
├── alembic/                      # Database migrations
│   └── versions/                # Migration files
│
├── docs/                         # Documentation
│   ├── deployment.md            # Deployment guide
│   └── development.md           # This file
│
├── scripts/                      # Utility scripts
│   └── deploy.sh                # Deployment script
│
├── nginx/                        # Nginx configuration
│   └── nginx.conf               # Reverse proxy config
│
├── docker-compose.yml           # Docker orchestration
├── Dockerfile                   # Backend Docker image
├── requirements.txt             # Python dependencies
├── pytest.ini                   # Test configuration
├── alembic.ini                  # Migration configuration
└── .env.example                 # Environment template
```

### Key Files

| File | Purpose |
|------|---------|
| `api/src/main.py` | FastAPI application factory |
| `api/src/api_v2.py` | All API endpoints |
| `db_manager.py` | Database operations |
| `datagod/models/` | SQLAlchemy ORM models |
| `datagod/scrapers/` | State-specific scrapers |
| `tests/conftest.py` | Shared test fixtures |

---

## Common Development Tasks

### Running the API Server

```bash
# Development mode with auto-reload
python -m uvicorn api.src.main:app --reload --port 8000

# Or with Docker
docker-compose up api

# Access API docs at: http://localhost:8000/docs
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=datagod --cov=api --cov-report=html

# Run specific test file
pytest tests/test_api.py -v

# Run specific test
pytest tests/test_api.py::TestAuthEndpoints::test_login_success -v

# Run tests matching pattern
pytest -k "test_user" -v
```

### Database Operations

```bash
# Create a new migration
alembic revision --autogenerate -m "Add user preferences"

# Apply all migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# View migration history
alembic history

# Reset database (Docker)
docker-compose down -v
docker-compose up -d db
docker-compose exec api alembic upgrade head
```

### Frontend Development

```bash
cd frontend/datagod-frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Run linting
npm run lint

# Type checking
npx tsc --noEmit
```

### Adding a New Scraper

1. Create new file: `datagod/scrapers/newstate_api.py`
2. Extend `BaseAPIIntegration`:

```python
from datagod.scrapers.base_api_integration import BaseAPIIntegration

class NewStateCountyAPI(BaseAPIIntegration):
    def authenticate(self):
        # Implement authentication
        pass

    def search_records(self, **kwargs):
        # Implement search
        pass

    def get_record_details(self, record_id):
        # Implement detail fetch
        pass

    def map_api_data_to_standard_format(self, data):
        # Map to standard format
        pass
```

3. Add to `datagod/scrapers/__init__.py`
4. Create tests in `tests/test_newstate_api.py`

### Adding a New API Endpoint

1. Edit `api/src/api_v2.py`:

```python
@app.get("/api/v2/new-endpoint")
async def new_endpoint(
    current_user: User = Depends(get_current_user)
):
    """
    Description of what this endpoint does.
    """
    return {"message": "success"}
```

2. Add tests in `tests/test_api.py`
3. Update API documentation if needed

---

## Coding Standards

### Python Standards

1. **PEP 8 Compliance**:
   - Use 4 spaces for indentation
   - Limit lines to 79 characters
   - Use meaningful variable and function names

2. **Type Hints**:
   - All functions should have type hints
   - Use `typing` module for complex types

3. **Documentation**:
   - Docstrings for all public functions
   - Class docstrings
   - Module docstrings

4. **Error Handling**:
   - Use specific exceptions
   - Log errors appropriately
   - Don't ignore exceptions

### JavaScript/TypeScript Standards

1. **ESLint and Prettier**:
   - Follow Airbnb style guide
   - Use Prettier for code formatting

2. **React Best Practices**:
   - Use functional components with hooks
   - Component-based architecture
   - Proper state management

3. **Code Organization**:
   - Component files in separate directories
   - Meaningful naming conventions
   - Modular code structure

## Testing

### Running Tests

1. **Unit Tests**:
   ```bash
   pytest tests/
   ```

2. **Integration Tests**:
   ```bash
   pytest tests/integration/
   ```

3. **Test Coverage**:
   ```bash
   pytest tests/ --cov=datagod --cov-report=html
   ```

### Test Structure

1. **Test Files**:
   - `tests/test_model_name.py` for model tests
   - `tests/test_endpoint_name.py` for API endpoint tests
   - `tests/test_utils.py` for utility function tests

2. **Test Coverage**:
   - Aim for 80%+ code coverage
   - Test edge cases
   - Test error conditions

## Development Workflow

### Branching Strategy

1. **Main Branch**: Stable production code
2. **Development Branch**: Active development
3. **Feature Branches**: For specific features
4. **Hotfix Branches**: For urgent bug fixes

### Commit Guidelines

1. **Commit Messages**:
   - Use present tense
   - Be descriptive
   - Follow conventional commits format

2. **Example**:
   ```
   feat: add user authentication
   fix: resolve database connection issue
   docs: update API documentation
   ```

### Pull Request Process

1. Create a feature branch from `development`
2. Make your changes
3. Write tests
4. Run all tests
5. Update documentation if needed
6. Create a pull request to `development`
7. Request code review
8. Address feedback
9. Merge after approval

## Database Development

### Schema Changes

1. **Create Migration**:
   ```bash
   alembic revision --autogenerate -m "Add user preferences table"
   ```

2. **Review Migration**:
   - Check generated code
   - Add any manual changes
   - Test migration

3. **Apply Migration**:
   ```bash
   alembic upgrade head
   ```

### Data Migrations

1. **Use Alembic** for schema changes
2. **Write data migration scripts** for data transformations
3. **Test migrations** in staging environment
4. **Document migration steps** in release notes

## API Development

### Adding New Endpoints

1. **Create endpoint in `api/` directory**
2. **Add route decorator**
3. **Implement business logic**
4. **Add input validation**
5. **Add error handling**
6. **Write tests**
7. **Update API documentation**

### API Versioning

1. **URL Versioning**: `/api/v1/endpoint`
2. **Header Versioning**: `Accept: application/vnd.datagod.v1+json`
3. **Use semantic versioning**

## Frontend Development

### Component Structure

1. **Create component directory**:
   ```
   components/MyComponent/
   ├── MyComponent.tsx
   ├── MyComponent.test.tsx
   └── index.ts
   ```

2. **Component Structure**:
   ```typescript
   import React from 'react';
   
   interface MyComponentProps {
     title: string;
     onClick?: () => void;
   }
   
   const MyComponent: React.FC<MyComponentProps> = ({ title, onClick }) => {
     return (
       <div onClick={onClick}>
         <h2>{title}</h2>
       </div>
     );
   };
   
   export default MyComponent;
   ```

### State Management

1. **Use React Context** for global state
2. **Use SWR** for data fetching and caching
3. **Use Redux Toolkit** for complex state management

## Performance Optimization

### Backend Optimization

1. **Database Queries**:
   - Use indexes appropriately
   - Avoid N+1 queries
   - Use pagination for large datasets

2. **Caching**:
   - Use Redis for frequently accessed data
   - Implement cache invalidation strategies
   - Set appropriate TTL values

3. **Asynchronous Processing**:
   - Use Celery for background tasks
   - Implement task queues
   - Handle task failures gracefully

### Frontend Optimization

1. **Code Splitting**:
   - Split bundles by route
   - Lazy load components
   - Use dynamic imports

2. **Image Optimization**:
   - Use responsive images
   - Implement lazy loading
   - Compress images

3. **Component Optimization**:
   - Memoize expensive calculations
   - Use React.memo for components
   - Implement virtual scrolling for lists

## Security Best Practices

### Backend Security

1. **Input Validation**:
   - Validate all inputs
   - Sanitize user data
   - Use parameterized queries

2. **Authentication**:
   - Use JWT tokens
   - Implement proper session management
   - Secure password storage

3. **Authorization**:
   - Implement role-based access control
   - Validate permissions for each request
   - Use middleware for access control

### Frontend Security

1. **XSS Prevention**:
   - Escape user content
   - Use React's built-in XSS protection
   - Validate and sanitize inputs

2. **CSRF Protection**:
   - Implement CSRF tokens
   - Use SameSite cookies
   - Validate request origins

## Debugging and Logging

### Backend Debugging

1. **Logging**:
   - Use Python logging module
   - Log at appropriate levels (DEBUG, INFO, WARNING, ERROR)
   - Include context in logs

2. **Debugging Tools**:
   - Use pdb for Python debugging
   - Use logging to trace execution flow
   - Implement health checks

### Frontend Debugging

1. **Browser Dev Tools**:
   - Use React DevTools
   - Monitor network requests
   - Debug component state

2. **Console Logging**:
   - Use console.log for debugging
   - Implement debug mode
   - Log important state changes

## Deployment Preparation

### Pre-Deployment Checklist

1. **Code Quality**:
   - Run all tests
   - Check code coverage
   - Run linters
   - Review code changes

2. **Database**:
   - Run migrations
   - Test database connectivity
   - Verify data integrity

3. **API**:
   - Test all endpoints
   - Verify authentication
   - Check rate limiting

4. **Frontend**:
   - Test all components
   - Verify responsive design
   - Check browser compatibility

## Contributing

### How to Contribute

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Update documentation
6. Submit a pull request

### Code Review Process

1. All pull requests require at least one review
2. Code must pass all tests
3. Code must follow style guidelines
4. Documentation must be updated
5. Performance impact must be considered

## Release Process

### Versioning

1. **Semantic Versioning**:
   - MAJOR.MINOR.PATCH
   - MAJOR: Breaking changes
   - MINOR: New features
   - PATCH: Bug fixes

2. **Release Tags**:
   - Use git tags for releases
   - Follow semantic versioning
   - Create release notes

### Release Checklist

1. Update version in `setup.py` or `package.json`
2. Update `CHANGELOG.md`
3. Run all tests
4. Build artifacts
5. Create release tag
6. Publish to package repositories
7. Update documentation

---

## Troubleshooting

### Common Issues

#### Database Connection Failed

**Error:** `sqlalchemy.exc.OperationalError: could not connect to server`

**Solutions:**
```bash
# Check if PostgreSQL is running
docker-compose ps db

# Check database logs
docker-compose logs db

# Verify DATABASE_URL in .env
echo $DATABASE_URL

# Reset database
docker-compose down -v
docker-compose up -d db
```

#### Import Errors

**Error:** `ModuleNotFoundError: No module named 'datagod'`

**Solutions:**
```bash
# Ensure you're in the project root
pwd  # Should be /path/to/DataGod

# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or install in development mode
pip install -e .
```

#### Port Already in Use

**Error:** `Error: address already in use`

**Solutions:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use different port
python -m uvicorn api.src.main:app --port 8001
```

#### Redis Connection Failed

**Error:** `redis.exceptions.ConnectionError`

**Solutions:**
```bash
# Check if Redis is running
docker-compose ps redis

# Test Redis connection
docker-compose exec redis redis-cli -a $REDIS_PASSWORD ping

# Check REDIS_PASSWORD in .env matches docker-compose.yml
```

#### Frontend Build Errors

**Error:** `npm ERR! ERESOLVE unable to resolve dependency tree`

**Solutions:**
```bash
# Clear npm cache
rm -rf node_modules package-lock.json
npm cache clean --force
npm install

# Use legacy peer deps if needed
npm install --legacy-peer-deps
```

#### Test Failures

**Error:** `pytest: error: unrecognized arguments`

**Solutions:**
```bash
# Ensure pytest is installed
pip install pytest pytest-cov

# Run from project root
cd /path/to/DataGod
pytest

# Check for conflicting pytest.ini
cat pytest.ini
```

#### Migration Errors

**Error:** `alembic.util.exc.CommandError: Can't locate revision`

**Solutions:**
```bash
# Check current migration state
alembic current

# Reset migrations (development only!)
alembic downgrade base
alembic upgrade head

# If table already exists, mark as migrated
alembic stamp head
```

### Getting Help

1. Check the logs: `docker-compose logs -f`
2. Search existing issues on GitHub
3. Check the API docs: http://localhost:8000/docs
4. Join the community Discord/Slack (if available)
5. Open a GitHub issue with:
   - Error message
   - Steps to reproduce
   - Environment details (OS, Python version, etc.)
