from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    GOOGLE_MAPS_API_KEY: str = ""
    MAPBOX_ACCESS_TOKEN: str = Field(default="", validation_alias="MAPBOX_API_KEY")
    OPENAI_API_KEY: str = ""
    OPENAI_VISION_MODEL: str = "gpt-4o-mini"
    OPENAI_SEGMENTED_REASONING_MODEL: str = ""
    DATABASE_URL: str = "postgresql://argus:argus@localhost:5432/argus"
    PROPERTY_CACHE_TTL_DAYS: int = 30
    SAM_SERVICE_URL: str = ""
    SAM_MODEL_ID: str = "facebook/sam3.1"
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_BASE_URL: str = "https://cloud.langfuse.com"

    @field_validator("LANGFUSE_BASE_URL", mode="before")
    @classmethod
    def strip_env_quotes(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip().strip('"').strip("'")
        return value

    model_config = {
        "env_file": "../.env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
