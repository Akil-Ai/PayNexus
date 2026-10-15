"""PayNexus application settings via Pydantic Settings."""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_env: str = "development"
    app_version: str = "1.0.0"
    app_secret: str = "app_secret_for_webhook_hmac_change_me"

    # Database
    database_url: str = "postgresql+asyncpg://paynexus:paynexus_secret@localhost:5432/paynexus"
    sync_database_url: str = "postgresql://paynexus:paynexus_secret@localhost:5432/paynexus"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret_key: str = "super_secret_jwt_key_change_in_production_min_32_chars"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    # API key header
    api_key_header: str = "X-API-Key"

    # Field encryption
    field_encryption_key: str = "KzQa7Fmd00C1afjWWBPUuXOmGQhur3Ck-TYWI42oyfw="

    # Idempotency
    idempotency_ttl_seconds: int = 86400
    idempotency_lock_timeout_seconds: int = 30

    # Rate limiting
    rate_limit_per_minute: int = 300

    # CORS
    allowed_origins: str = "http://localhost:3000,http://localhost"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    # Mock service URLs
    rail_upi_url: str = "http://localhost:8101"
    rail_neft_url: str = "http://localhost:8102"
    rail_swift_url: str = "http://localhost:8103"
    rail_card_url: str = "http://localhost:8104"
    sanctions_url: str = "http://localhost:8201"
    kyc_url: str = "http://localhost:8202"

    # Observability
    log_level: str = "INFO"

    # Seed
    seed_random_seed: int = 42
    seed_num_customers: int = 200
    seed_num_payments: int = 5000

    # Model path
    fraud_model_path: str = "/app/models/fraud_model.pkl"

    @property
    def ENVIRONMENT(self) -> str:
        return self.app_env

    @property
    def CORS_ORIGINS(self) -> List[str]:
        return self.allowed_origins_list


    @property
    def RAIL_UPI_URL(self) -> str:
        return self.rail_upi_url

    @property
    def RAIL_NEFT_URL(self) -> str:
        return self.rail_neft_url

    @property
    def RAIL_SWIFT_URL(self) -> str:
        return self.rail_swift_url

    @property
    def RAIL_CARD_URL(self) -> str:
        return self.rail_card_url

    @property
    def SANCTIONS_URL(self) -> str:
        return self.sanctions_url

    @property
    def KYC_URL(self) -> str:
        return self.kyc_url

    @property
    def KYC_SERVICE_URL(self) -> str:
        return self.kyc_url




@lru_cache()
def get_settings() -> Settings:
    return Settings()
