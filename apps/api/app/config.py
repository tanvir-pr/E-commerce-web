"""Runtime configuration. Loaded from the environment."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "local"
    database_url: str
    redis_url: str
    cors_origin: str = "http://localhost:3000"
    public_web_url: str = "http://localhost:3000"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from: str = "noreply@example.com"
    jwt_secret: str = "local-dev-only-change-me"
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_days: int = 30
    email_verification_ttl_hours: int = 24
    breach_check: str = "stub"
    login_rate_limit_per_ip: int = 20
    login_rate_limit_per_email: int = 10
    login_rate_limit_window_seconds: int = 600
    seed_superadmin_email: str = "owner@example.com"
    seed_superadmin_password: str = "ChangeMeNow1"
    # Fernet key: cryptography.fernet.Fernet.generate_key().decode()
    totp_encryption_key: str = "_-Ya7B3qukwFBFcl2y52RF4qvs52ThkeoxVKWZ9Jnq8="
    pending_auth_ttl_seconds: int = 600
    totp_issuer: str = "Store"
    password_reset_ttl_hours: int = 1
    phone_registration_enabled: bool = False
    skin_types: str = "dry,oily,combination,sensitive,acne-prone"
    skin_concerns: str = "acne,pigmentation,aging,barrier,hydration"
    media_root: str = "/data/media"
    media_url_path: str = "/api/v1/media"
    media_max_upload_bytes: int = 8_388_608
    media_thumb_max: int = 320
    media_card_max: int = 800
    media_full_max: int = 1600


@lru_cache
def get_settings() -> Settings:
    # Fields are filled from the environment. The constructor call is valid at runtime.
    return Settings()  # type: ignore[call-arg]
