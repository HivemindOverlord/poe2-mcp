"""
Configuration management for PoE2 Build Optimizer
"""
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
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
    HOST: str = Field(default="127.0.0.1")
    PORT: int = Field(default=8080)
    DEBUG: bool = Field(default=True)
    ENV: str = Field(default="development")

    # Database
    DATABASE_URL: str = Field(
        default=f"sqlite:///{DATA_DIR}/poe2_optimizer.db"
    )
    DB_POOL_SIZE: int = Field(default=10)
    DB_ECHO: bool = Field(default=False)

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_ENABLED: bool = Field(default=False)

    # API Configuration
    # REQUIRED: Trade API authentication (run: python scripts/setup_trade_auth.py)
    POESESSID: Optional[str] = Field(default=None)

    # OPTIONAL: OAuth credentials (not yet implemented - for future use)
    # Apply at: https://www.pathofexile.com/developer/docs
    POE_CLIENT_ID: Optional[str] = Field(default=None)
    POE_CLIENT_SECRET: Optional[str] = Field(default=None)

    # Third-party APIs
    POE_NINJA_API: str = Field(default="https://poe.ninja/api")
    POE_NINJA_PROFILE_URL: str = Field(default="https://poe.ninja")
    POE_OFFICIAL_API: str = Field(default="https://www.pathofexile.com")
    TRADE_API_URL: str = Field(default="https://www.pathofexile.com/trade2/search/poe2")
    REQUEST_TIMEOUT: int = Field(default=30)

    # Rate Limiting
    POE_API_RATE_LIMIT: int = Field(default=10)
    ENABLE_CACHING: bool = Field(default=False)
    CACHE_TTL: int = Field(default=3600)

    # Feature Flags
    ENABLE_TRADE_INTEGRATION: bool = Field(default=True)
    ENABLE_POB_EXPORT: bool = Field(default=True)
    ENABLE_BUILD_SHARING: bool = Field(default=True)
    ENABLE_AI_INSIGHTS: bool = Field(default=False)  # AI-powered insights (requires additional setup)

    # Web Interface
    WEB_PORT: int = Field(default=3000)
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000"
    )
    MAX_SAVED_BUILDS_PER_USER: int = Field(default=50)

    def get_cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS string into list"""
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        return self.CORS_ORIGINS

    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FILE: str = Field(default="logs/poe2_optimizer.log")
    LOG_ROTATION: str = Field(default="100 MB")
    LOG_RETENTION: str = Field(default="7 days")

    # Security
    # CRITICAL: These must be set via environment variables (.env file)
    # Generate with: python -c "import secrets; print(secrets.token_hex(32))"
    # Never commit actual secrets to version control
    SECRET_KEY: str = Field(
        ...,  # Required, no default
        description="Cryptographically secure random key for session management"
    )
    ENCRYPTION_KEY: str = Field(
        ...,  # Required, no default
        description="Cryptographically secure random key for data encryption"
    )
    SESSION_TIMEOUT: int = Field(default=86400)

    # Performance
    MAX_WORKERS: int = Field(default=4)
    REQUEST_TIMEOUT: int = Field(default=30)
    CALCULATION_TIMEOUT: int = Field(default=10)

    # Monitoring
    SENTRY_DSN: Optional[str] = Field(default=None)
    PROMETHEUS_ENABLED: bool = Field(default=False)
    PROMETHEUS_PORT: int = Field(default=9090)

    model_config = ConfigDict(
        env_file=str(BASE_DIR / ".env"),  # Use absolute path
        env_file_encoding="utf-8",
        case_sensitive=True
    )


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
