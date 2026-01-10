# DataGod Deployment Guide

This document provides instructions for deploying the DataGod platform to production environments.

## Table of Contents

- [Quick Start (Development)](#quick-start-development)
- [Quick Start (Production)](#quick-start-production)
- [Prerequisites](#prerequisites)
- [Docker Deployment](#docker-deployment)
- [Environment Configuration](#environment-configuration)
- [Production Checklist](#production-checklist)
- [Cloud Deployments](#cloud-deployments)
- [Monitoring & Logging](#monitoring-and-logging)
- [Backup & Recovery](#backup-and-recovery)
- [Troubleshooting](#troubleshooting)

---

## Quick Start (Development)

Get DataGod running locally in under 5 minutes:

```bash
# 1. Clone the repository
git clone https://github.com/your-org/DataGod.git
cd DataGod

# 2. Create environment file
cp .env.example .env

# 3. Start all services with Docker Compose
docker-compose up -d

# 4. Run database migrations
docker-compose exec api alembic upgrade head

# 5. Verify services are running
docker-compose ps
curl http://localhost:8000/health

# Access points:
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - Frontend: http://localhost:3000
```

## Quick Start (Production)

```bash
# 1. Clone and configure
git clone https://github.com/your-org/DataGod.git
cd DataGod
cp .env.example .env.production

# 2. Edit production environment variables (see Environment Configuration)
nano .env.production

# 3. Start with production profile (includes nginx)
docker-compose --env-file .env.production --profile production up -d

# 4. Run migrations
docker-compose exec api alembic upgrade head

# 5. Verify
curl https://yourdomain.com/health
```

---

## Overview

DataGod can be deployed to various cloud platforms including AWS, GCP, and Azure. The deployment process involves containerizing the application with Docker, setting up infrastructure with Kubernetes (optional), and configuring environment-specific settings.

## Prerequisites

Before deploying DataGod, ensure you have:

**Required:**
1. Docker (v20.10+) and Docker Compose (v2.0+) installed
2. Git for version control
3. At least 4GB RAM and 20GB disk space

**For Production:**
4. A cloud provider account (AWS, GCP, or Azure)
5. A domain name for your API
6. SSL certificates for HTTPS
7. PostgreSQL database access (or use included container)
8. Redis instance for caching (or use included container)
9. GitHub/GitLab account for CI/CD

## Docker Deployment

### Architecture Overview

DataGod consists of these Docker services:

| Service | Port | Description |
|---------|------|-------------|
| `db` | 5432 | PostgreSQL 15 database |
| `redis` | 6379 | Redis 7 cache/broker |
| `api` | 8000 | FastAPI backend |
| `frontend` | 3000 | Next.js frontend |
| `worker` | - | Celery background worker |
| `scheduler` | - | Celery beat scheduler |
| `nginx` | 80/443 | Reverse proxy (production) |

### Option 1: Development Deployment

For local development and testing:

```bash
# Start core services only
docker-compose up -d db redis api frontend

# View logs
docker-compose logs -f api

# Stop services
docker-compose down

# Stop and remove volumes (reset data)
docker-compose down -v
```

### Option 2: Full Production Deployment

For production with all services:

```bash
# Build images
docker-compose build --no-cache

# Start all services including nginx
docker-compose --profile production up -d

# Verify all containers are healthy
docker-compose ps

# Check service health
curl http://localhost/health
curl http://localhost/api/v2/health
```

### Option 3: Kubernetes Deployment

For high-availability production environments:

```bash
# Create namespace
kubectl create namespace datagod

# Apply secrets (create secrets.yaml first)
kubectl apply -f k8s/secrets.yaml -n datagod

# Apply configurations
kubectl apply -f k8s/configmap.yaml -n datagod

# Deploy database and cache
kubectl apply -f k8s/postgres.yaml -n datagod
kubectl apply -f k8s/redis.yaml -n datagod

# Wait for database to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n datagod --timeout=120s

# Deploy application
kubectl apply -f k8s/api.yaml -n datagod
kubectl apply -f k8s/frontend.yaml -n datagod
kubectl apply -f k8s/worker.yaml -n datagod

# Deploy ingress
kubectl apply -f k8s/ingress.yaml -n datagod

# Check status
kubectl get pods -n datagod
```

### Using the Deploy Script

A convenience script is provided for common operations:

```bash
# Deploy to production
./scripts/deploy.sh deploy

# Backup database
./scripts/deploy.sh backup

# View logs
./scripts/deploy.sh logs api

# Restart a service
./scripts/deploy.sh restart api

# Scale workers
docker-compose up -d --scale worker=4
```

## Environment Configuration

### Required Environment Variables

Create a `.env` file with the following variables:

```bash
# ===========================================
# DATABASE CONFIGURATION
# ===========================================
POSTGRES_USER=datagod
POSTGRES_PASSWORD=your-strong-password-here
POSTGRES_DB=datagod
DATABASE_URL=postgresql://datagod:your-strong-password-here@db:5432/datagod

# ===========================================
# REDIS CONFIGURATION
# ===========================================
REDIS_PASSWORD=your-redis-password-here
REDIS_HOST=redis
REDIS_PORT=6379

# ===========================================
# SECURITY CONFIGURATION
# ===========================================
# Generate with: openssl rand -hex 32
SECRET_KEY=your-64-character-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# ===========================================
# APPLICATION CONFIGURATION
# ===========================================
ENVIRONMENT=production
DEBUG=False
LOG_LEVEL=INFO
API_PORT=8000
FRONTEND_PORT=3000
CORS_ORIGINS=https://yourdomain.com

# ===========================================
# EMAIL CONFIGURATION (Optional)
# ===========================================
EMAIL_HOST=smtp.yourdomain.com
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@yourdomain.com
EMAIL_HOST_PASSWORD=your-email-password
EMAIL_USE_TLS=True
EMAIL_FROM=DataGod <noreply@yourdomain.com>

# ===========================================
# PAYMENT CONFIGURATION (Optional)
# ===========================================
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# ===========================================
# CLOUD STORAGE (Optional)
# ===========================================
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_DEFAULT_REGION=us-east-1
STORAGE_BUCKET_NAME=datagod-storage
```

### Environment Variable Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POSTGRES_PASSWORD` | Yes | - | PostgreSQL password |
| `SECRET_KEY` | Yes | - | Application secret key |
| `JWT_SECRET_KEY` | Yes | - | JWT signing key |
| `ENVIRONMENT` | No | development | Environment mode |
| `DEBUG` | No | False | Debug mode |
| `LOG_LEVEL` | No | INFO | Logging level |
| `CORS_ORIGINS` | No | localhost | Allowed CORS origins |

### Development vs Production

| Setting | Development | Production |
|---------|-------------|------------|
| Database | SQLite or Docker PostgreSQL | Managed PostgreSQL (RDS/Cloud SQL) |
| Debug | True | **False** |
| HTTPS | Not required | **Required** |
| Secrets | Can use defaults | **Must be unique & strong** |
| CORS | localhost allowed | Specific domains only |
| Logging | DEBUG level | INFO or WARNING |

---

## Production Checklist

Before going live, verify each item:

### Security
- [ ] Generate unique `SECRET_KEY` (64+ characters)
- [ ] Generate unique `JWT_SECRET_KEY` (32+ characters)
- [ ] Set strong database passwords (20+ characters)
- [ ] Set strong Redis password
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Configure CORS to allow only your domain
- [ ] Disable DEBUG mode (`DEBUG=False`)
- [ ] Set `ENVIRONMENT=production`
- [ ] Remove default/demo users from database
- [ ] Review and restrict API rate limits

### Database
- [ ] Run all migrations (`alembic upgrade head`)
- [ ] Verify database backups are configured
- [ ] Test backup restoration procedure
- [ ] Set up database connection pooling

### Infrastructure
- [ ] Configure log rotation
- [ ] Set up health check monitoring
- [ ] Configure alerting for downtime
- [ ] Test auto-restart on failure
- [ ] Document disaster recovery procedure

### Performance
- [ ] Enable Redis caching
- [ ] Configure Celery workers appropriately
- [ ] Set appropriate API timeout values
- [ ] Test under expected load

### Verification Commands
```bash
# Check all services are running
docker-compose ps

# Verify database connectivity
docker-compose exec api python -c "from db_manager import DatabaseManager; db = DatabaseManager(); print('DB OK')"

# Check Redis connectivity
docker-compose exec redis redis-cli -a $REDIS_PASSWORD ping

# Test API health
curl -f http://localhost:8000/health

# Test authentication
curl -X POST http://localhost:8000/api/v2/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"test"}'
```

---

## CI/CD Pipeline

DataGod uses GitHub Actions for continuous integration and deployment:

### CI Workflow

The CI workflow runs on every push to `main` and `development` branches:

1. Run tests
2. Lint code
3. Build Docker images
4. Run security scans
5. Upload artifacts

### CD Workflow

The CD workflow deploys to staging and production environments:

1. Deploy to staging environment on push to `development`
2. Deploy to production on push to `main` (with manual approval)
3. Run smoke tests after deployment
4. Send notifications on deployment success/failure

## Infrastructure Setup

### AWS Deployment

1. Create VPC with public and private subnets
2. Set up RDS PostgreSQL instance
3. Create ElastiCache Redis cluster
4. Set up S3 buckets for static assets
5. Configure Application Load Balancer
6. Set up Route 53 for DNS
7. Create SSL certificates with ACM

### GCP Deployment

1. Create VPC network
2. Set up Cloud SQL PostgreSQL instance
3. Create Memorystore Redis instance
4. Create Cloud Storage buckets
5. Configure Cloud Load Balancing
6. Set up Cloud DNS
7. Create SSL certificates with Cloud Certificate Manager

### Azure Deployment

1. Create Virtual Network
2. Set up Azure Database for PostgreSQL
3. Create Azure Cache for Redis
4. Create Azure Storage accounts
5. Configure Azure Application Gateway
6. Set up Azure DNS
7. Create SSL certificates with Azure Key Vault

## Monitoring and Logging

### Application Monitoring

DataGod integrates with monitoring tools:

1. **Prometheus** for metrics collection
2. **Grafana** for dashboard visualization
3. **ELK Stack** for log aggregation
4. **DataDog** or **New Relic** for application performance monitoring

### Health Checks

The application exposes health check endpoints:

- `/health` - Basic health check
- `/health/database` - Database connectivity check
- `/health/redis` - Redis connectivity check
- `/health/api` - API service health

## Backup and Recovery

### Database Backups

1. Daily automated backups using pg_dump
2. Weekly full backups
3. Backup retention policy (30 days)
4. Automated restore testing

### Data Recovery

1. Point-in-time recovery for PostgreSQL
2. Backup verification procedures
3. Disaster recovery plan
4. Manual backup procedures

## Scaling Considerations

### Horizontal Scaling

1. API services can be scaled independently
2. Database read replicas for read-heavy operations
3. Load balancing across instances
4. Auto-scaling based on metrics

### Performance Optimization

1. Caching with Redis for frequently accessed data
2. Database indexing for common queries
3. Asynchronous processing for heavy operations
4. CDN for static assets

## Security Best Practices

1. **Network Security**:
   - Use private subnets for application services
   - Implement security groups/ACLs
   - Enable VPC flow logs

2. **Data Security**:
   - Encrypt data at rest
   - Use encrypted connections (TLS)
   - Regular security audits
   - Principle of least privilege

3. **Application Security**:
   - Input validation and sanitization
   - Rate limiting
   - JWT token management
   - Regular security updates

## Troubleshooting

### Common Issues

1. **Database Connection Failures**:
   - Check database credentials
   - Verify network connectivity
   - Confirm database is running

2. **Docker Build Failures**:
   - Check Dockerfile syntax
   - Verify dependencies
   - Ensure correct base image

3. **API Authentication Issues**:
   - Verify JWT secret key
   - Check token expiration
   - Confirm user exists in database

### Logs and Diagnostics

1. Check application logs in `/var/log/datagod/`
2. Review Docker container logs
3. Monitor system resources (CPU, memory, disk)
4. Check database connection logs

## Maintenance Tasks

1. **Weekly**:
   - Review system logs
   - Check backup status
   - Update dependencies

2. **Monthly**:
   - Perform security audit
   - Review performance metrics
   - Update documentation

3. **Quarterly**:
   - Database optimization
   - Security patching
   - Capacity planning
