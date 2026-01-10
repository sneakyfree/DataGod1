import os
from pydantic_settings import BaseSettings
from pathlib import Path
import sys

# Add project root to path to access datagod config
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from datagod.config.settings import DATABASE_URL

class Settings(BaseSettings):
    # Database settings - integrate with existing DataGod config
    database_url: str = DATABASE_URL

    # API settings
    api_title: str = "DataGod API"
    api_version: str = "1.0.0"
    api_description: str = "API for DataGod - Public Records Data Aggregation Platform"
    api_docs_url: str = "/docs"
    api_openapi_url: str = "/openapi.json"

    # Security settings
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    # Caching
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", 6379))
    redis_db: int = int(os.getenv("REDIS_DB", 0))
    cache_expiration: int = 3600

    # Authentication
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "your-jwt-secret-key-here")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Export settings
    max_export_records: int = 10000
    export_cache_time: int = 300

    # Monitoring
    enable_monitoring: bool = True
    monitoring_interval: int = 60

    # Integration
    enable_neural_network_integration: bool = True
    enable_scraper_integration: bool = True

    class Config:
        env_file = ".env"

settings = Settings()
