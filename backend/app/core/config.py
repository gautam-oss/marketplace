from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=[".env", "../.env"], extra="ignore")

    # Database
    DATABASE_URL: str
    REDIS_URL: str
    ELASTICSEARCH_URL: str

    # Auth
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Razorpay
    RAZORPAY_KEY_ID: str
    RAZORPAY_KEY_SECRET: str

    # Resend email
    RESEND_API_KEY: str
    EMAIL_FROM: str = "onboarding@resend.dev"
    # In Resend test mode, only the account owner's address can receive mail.
    # Set this to redirect all outgoing emails to one address during development.
    TEST_EMAIL_OVERRIDE: str = ""

    # AWS S3
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "ap-south-1"
    S3_BUCKET_NAME: str
    USE_LOCAL_STORAGE: bool = False

    # Sentry
    SENTRY_DSN: str = ""

    # App
    ALLOWED_ORIGINS: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
