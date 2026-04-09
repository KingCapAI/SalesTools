from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./data/kingcap.db"

    # JWT
    jwt_secret: str = "change-this-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # Microsoft OAuth
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_tenant_id: str = ""

    # Gemini
    google_gemini_api_key: str = ""  # For AI Design Conceptor (legacy direct API)
    google_gemini_api_key_mockup: str = ""  # For Mockup Builder (legacy, falls back to main key)

    # Google Cloud / Vertex AI (preferred — more reliable than direct Gemini API)
    google_cloud_project: str = ""
    google_application_credentials_json: str = ""  # Full JSON service account key

    # EBizCharge Payment Gateway
    ebizcharge_source_key: str = ""
    ebizcharge_pin: str = ""
    ebizcharge_environment: str = "sandbox"  # "sandbox" or "production"

    # Business Central (Dynamics 365)
    bc_client_id: str = ""
    bc_client_secret: str = ""
    bc_tenant_id: str = ""
    bc_environment: str = "production"
    bc_company_id: str = ""

    # Pipedrive CRM
    pipedrive_api_token: str = ""
    pipedrive_webhook_secret: str = ""

    # Klaviyo Email Marketing
    klaviyo_private_key: str = ""
    klaviyo_public_key: str = ""

    # ShipStation Shipping
    shipstation_api_key: str = ""
    shipstation_api_secret: str = ""
    shipstation_webhook_secret: str = ""

    # Google Analytics / Ads
    ga4_measurement_id: str = ""
    ga4_api_secret: str = ""
    google_ads_customer_id: str = ""
    google_ads_conversion_action_id: str = ""

    # Anthropic (Claude AI)
    anthropic_api_key: str = ""

    # Resend (Email)
    resend_api_key: str = ""
    email_from: str = "King Cap <orders@wearkingcap.com>"

    # App URLs
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    store_frontend_url: str = "http://localhost:5174"

    # Cloudflare R2 Storage
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "kingcap-uploads"
    r2_public_url: str = ""  # e.g. "https://pub-xxxx.r2.dev"

    # Upload settings
    upload_dir: str = "uploads"  # Legacy local path, used as fallback if R2 not configured
    max_file_size_mb: int = 25

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
