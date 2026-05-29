"""
DataGod Configuration Settings
Centralized configuration management for all components
"""

import os
from pathlib import Path
from typing import Optional

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "db"
LOGS_DIR = PROJECT_ROOT / "logs"
CACHE_DIR = PROJECT_ROOT / "cache"

# Create directories
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# Database Configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://datagod:datagod@localhost:5433/datagod"
)

# Database connection pool settings
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))

# API Configuration
API_HOST = os.getenv(
    "API_HOST", "0.0.0.0"
)  # nosec B104 - intentional server bind, host configurable via env
API_PORT = int(os.getenv("API_PORT", "8000"))
API_WORKERS = int(os.getenv("API_WORKERS", "4"))
API_DEBUG = os.getenv("API_DEBUG", "false").lower() == "true"

# Security Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
)

# CORS Configuration
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
).split(",")

# Redis Configuration (for caching)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_CACHE_TTL = int(os.getenv("REDIS_CACHE_TTL", "3600"))

# External API Keys (for integrations)
FLORIDA_PROPERTY_APPRAISER_API_KEY = os.getenv("FLORIDA_PROPERTY_APPRAISER_API_KEY")
CALIFORNIA_SOS_API_KEY = os.getenv("CALIFORNIA_SOS_API_KEY")

# Scraping Configuration
SCRAPER_RATE_LIMIT = float(
    os.getenv("SCRAPER_RATE_LIMIT", "1.0")
)  # requests per second
SCRAPER_TIMEOUT = int(os.getenv("SCRAPER_TIMEOUT", "30"))
SCRAPER_MAX_RETRIES = int(os.getenv("SCRAPER_MAX_RETRIES", "3"))
SCRAPER_CONCURRENT_REQUESTS = int(os.getenv("SCRAPER_CONCURRENT_REQUESTS", "5"))
SCRAPER_USE_PROXIES = os.getenv("SCRAPER_USE_PROXIES", "false").lower() == "true"

# Proxy Configuration
PROXY_LIST_FILE = os.getenv(
    "PROXY_LIST_FILE", str(PROJECT_ROOT / "config" / "proxies.txt")
)

# Data Deduplication Configuration
DEDUPLICATION_SIMILARITY_THRESHOLD = float(
    os.getenv("DEDUPLICATION_SIMILARITY_THRESHOLD", "0.8")
)
DEDUPLICATION_ALGORITHM = os.getenv("DEDUPLICATION_ALGORITHM", "fuzzy_match")
DEDUPLICATION_BATCH_SIZE = int(os.getenv("DEDUPLICATION_BATCH_SIZE", "1000"))

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv(
    "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
LOG_FILE = os.getenv("LOG_FILE", str(LOGS_DIR / "datagod.log"))
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", "10485760"))  # 10MB
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))

# Email Configuration (for notifications)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@datagod.com")

# File Upload Configuration
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))  # 10MB
ALLOWED_EXTENSIONS = os.getenv("ALLOWED_EXTENSIONS", ".csv,.json,.xlsx,.txt").split(",")
UPLOAD_DIR = PROJECT_ROOT / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Export Configuration
EXPORT_DIR = PROJECT_ROOT / "exports"
EXPORT_DIR.mkdir(exist_ok=True)
EXPORT_MAX_ROWS = int(os.getenv("EXPORT_MAX_ROWS", "100000"))

# Monitoring Configuration
ENABLE_METRICS = os.getenv("ENABLE_METRICS", "true").lower() == "true"
METRICS_PORT = int(os.getenv("METRICS_PORT", "9090"))
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "60"))

# Feature Flags
ENABLE_ADVANCED_SEARCH = os.getenv("ENABLE_ADVANCED_SEARCH", "true").lower() == "true"
ENABLE_DATA_EXPORT = os.getenv("ENABLE_DATA_EXPORT", "true").lower() == "true"
ENABLE_REAL_TIME_UPDATES = (
    os.getenv("ENABLE_REAL_TIME_UPDATES", "false").lower() == "true"
)
ENABLE_USER_MANAGEMENT = os.getenv("ENABLE_USER_MANAGEMENT", "false").lower() == "true"
ENABLE_SUBSCRIPTION_SYSTEM = (
    os.getenv("ENABLE_SUBSCRIPTION_SYSTEM", "false").lower() == "true"
)

# Development/Production Settings
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = ENVIRONMENT == "development"

# External Service URLs
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.getenv("BACKEND_URL", f"http://localhost:{API_PORT}")

# Rate Limiting
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds

# Cache Settings
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
CACHE_BACKEND = os.getenv("CACHE_BACKEND", "redis")  # redis or memory
CACHE_DEFAULT_TTL = int(os.getenv("CACHE_DEFAULT_TTL", "300"))

# Pagination
DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", "50"))
MAX_PAGE_SIZE = int(os.getenv("MAX_PAGE_SIZE", "1000"))

# Data Validation
ENABLE_DATA_VALIDATION = os.getenv("ENABLE_DATA_VALIDATION", "true").lower() == "true"
VALIDATION_STRICT_MODE = os.getenv("VALIDATION_STRICT_MODE", "false").lower() == "true"

# Backup Configuration
BACKUP_ENABLED = os.getenv("BACKUP_ENABLED", "true").lower() == "true"
BACKUP_INTERVAL_HOURS = int(os.getenv("BACKUP_INTERVAL_HOURS", "24"))
BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
BACKUP_DIR = PROJECT_ROOT / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

# Notification Settings
NOTIFICATION_EMAIL_ENABLED = (
    os.getenv("NOTIFICATION_EMAIL_ENABLED", "true").lower() == "true"
)
NOTIFICATION_SLACK_ENABLED = (
    os.getenv("NOTIFICATION_SLACK_ENABLED", "false").lower() == "true"
)
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

# Performance Monitoring
PERFORMANCE_MONITORING_ENABLED = (
    os.getenv("PERFORMANCE_MONITORING_ENABLED", "true").lower() == "true"
)
SLOW_QUERY_THRESHOLD = float(os.getenv("SLOW_QUERY_THRESHOLD", "1.0"))  # seconds
