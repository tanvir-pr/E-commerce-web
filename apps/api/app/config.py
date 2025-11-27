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
    meilisearch_url: str = "http://meilisearch:7700"
    meilisearch_api_key: str = "store-meili-master-key"
    meilisearch_index: str = "products"
    search_enabled: bool = True
    cart_abandon_after_hours: int = 72
    cart_guest_cookie_max_age_days: int = 30
    cart_max_line_qty: int = 20
    # Part 18: hold stock after place until pay/confirm or expiry.
    stock_reservation_ttl_minutes: int = 15
    # Part 19: COD places move straight to confirmed (cancel still allowed until ship).
    cod_auto_confirm: bool = True
    # Part 20: confirmed orders older than this (hours) count as overdue for packing/ship.
    fulfilment_sla_hours: int = 48
    inventory_low_stock_threshold: int = 10
    inventory_near_expiry_days: int = 60
    # Shipping (Part 15). Poisha = BDT * 100. Used when a zone has no override.
    free_shipping_threshold_poisha: int = 300000
    # When a variant has no weight_grams, assume this for quote weight.
    shipping_default_variant_weight_grams: int = 100
    # Part 23: sandbox payment gateways (no live HTTP in sandbox mode).
    payment_gateway_mode: str = "sandbox"
    bkash_app_key: str = "sandbox-bkash-app-key"
    bkash_app_secret: str = "sandbox-bkash-app-secret"
    bkash_username: str = "sandbox"
    bkash_password: str = "sandbox"
    sslcommerz_store_id: str = "sandbox-ssl-store"
    sslcommerz_store_password: str = "sandbox-ssl-password"


@lru_cache
def get_settings() -> Settings:
    # Fields are filled from the environment. The constructor call is valid at runtime.
    return Settings()  # type: ignore[call-arg]
