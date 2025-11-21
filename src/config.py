"""
Configuration management for PoE2 Build Optimizer
"""
import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import yaml


# Define paths first - use absolute paths based on script location
BASE_DIR = Path(__file__).parent.parent.resolve()
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = BASE_DIR / "cache"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True, parents=True)
CACHE_DIR.mkdir(exist_ok=True, parents=True)
LOGS_DIR.mkdir(exist_ok=True, parents=True)


class Settings(BaseSettings):
    """Application settings loaded from environment and config file"""

    # Server
    HOST: str = Field(default="127.0.0.1", env="HOST")
    PORT: int = Field(default=8080, env="PORT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    ENV: str = Field(default="development", env="ENV")

    # Database
    DATABASE_URL: str = Field(
        default=f"sqlite:///{DATA_DIR}/poe2_optimizer.db",
        env="DATABASE_URL"
    )
    DB_POOL_SIZE: int = Field(default=10, env="DB_POOL_SIZE")
    DB_ECHO: bool = Field(default=False, env="DB_ECHO")

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_ENABLED: bool = Field(default=False, env="REDIS_ENABLED")

    # API Configuration
    POE_CLIENT_ID: Optional[str] = Field(default=None, env="POE_CLIENT_ID")
    POE_CLIENT_SECRET: Optional[str] = Field(default=None, env="POE_CLIENT_SECRET")
    POESESSID: Optional[str] = Field(default=None, env="POESESSID")  # Session cookie for trade API

    # Third-party APIs
    POE_NINJA_API: str = Field(default="https://poe.ninja/api", env="POE_NINJA_API")
    POE_NINJA_PROFILE_URL: str = Field(default="https://poe.ninja", env="POE_NINJA_PROFILE_URL")
    POE_OFFICIAL_API: str = Field(default="https://www.pathofexile.com", env="POE_OFFICIAL_API")
    TRADE_API_URL: str = Field(default="https://www.pathofexile.com/trade2/search/poe2", env="TRADE_API_URL")
    REQUEST_TIMEOUT: int = Field(default=30, env="REQUEST_TIMEOUT")

    # AI Configuration
    AI_PROVIDER: str = Field(default="anthropic", env="AI_PROVIDER")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    AI_MODEL: str = Field(
        default="claude-sonnet-4-20250514",
        env="AI_MODEL"
    )
    AI_MAX_TOKENS: int = Field(default=4096, env="AI_MAX_TOKENS")
    AI_TEMPERATURE: float = Field(default=0.7, env="AI_TEMPERATURE")

    # Rate Limiting
    POE_API_RATE_LIMIT: int = Field(default=10, env="POE_API_RATE_LIMIT")
    POE2DB_RATE_LIMIT: int = Field(default=30, env="POE2DB_RATE_LIMIT")
    ENABLE_CACHING: bool = Field(default=True, env="ENABLE_CACHING")
    CACHE_TTL: int = Field(default=3600, env="CACHE_TTL")

    # Feature Flags
    ENABLE_TRADE_INTEGRATION: bool = Field(default=True, env="ENABLE_TRADE_INTEGRATION")
    ENABLE_POB_EXPORT: bool = Field(default=True, env="ENABLE_POB_EXPORT")
    ENABLE_AI_INSIGHTS: bool = Field(default=True, env="ENABLE_AI_INSIGHTS")
    ENABLE_BUILD_SHARING: bool = Field(default=True, env="ENABLE_BUILD_SHARING")

    # Web Interface
    WEB_PORT: int = Field(default=3000, env="WEB_PORT")
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        env="CORS_ORIGINS"
    )
    MAX_SAVED_BUILDS_PER_USER: int = Field(default=50, env="MAX_SAVED_BUILDS_PER_USER")

    def get_cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS string into list"""
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        return self.CORS_ORIGINS

    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: str = Field(default="logs/poe2_optimizer.log", env="LOG_FILE")
    LOG_ROTATION: str = Field(default="100 MB", env="LOG_ROTATION")
    LOG_RETENTION: str = Field(default="7 days", env="LOG_RETENTION")

    # Security
    SECRET_KEY: str = Field(
        default="change-in-production",
        env="SECRET_KEY"
    )
    ENCRYPTION_KEY: str = Field(
        default="change-in-production",
        env="ENCRYPTION_KEY"
    )
    SESSION_TIMEOUT: int = Field(default=86400, env="SESSION_TIMEOUT")

    # Performance
    MAX_WORKERS: int = Field(default=4, env="MAX_WORKERS")
    REQUEST_TIMEOUT: int = Field(default=30, env="REQUEST_TIMEOUT")
    CALCULATION_TIMEOUT: int = Field(default=10, env="CALCULATION_TIMEOUT")

    # Data Sources
    POE2DB_BASE_URL: str = Field(
        default="https://poe2db.tw",
        env="POE2DB_BASE_URL"
    )
    POE_NINJA_BASE_URL: str = Field(
        default="https://poe.ninja",
        env="POE_NINJA_BASE_URL"
    )
    POE_OFFICIAL_API: str = Field(
        default="https://www.pathofexile.com/api",
        env="POE_OFFICIAL_API"
    )

    # Monitoring
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")
    PROMETHEUS_ENABLED: bool = Field(default=False, env="PROMETHEUS_ENABLED")
    PROMETHEUS_PORT: int = Field(default=9090, env="PROMETHEUS_PORT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


def load_yaml_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file"""
    config_file = Path(config_path)
    if config_file.exists():
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    return {}


# Global settings instance
settings = Settings()

# Load additional YAML config if exists
yaml_config = load_yaml_config()


def get_setting(key: str, default=None):
    """
    Get setting from environment, YAML config, or default
    Priority: Environment > YAML > Default
    """
    # Try environment variable first
    if hasattr(settings, key):
        return getattr(settings, key)

    # Try YAML config
    if key in yaml_config:
        return yaml_config[key]

    return default


# Paths already defined at top of file
