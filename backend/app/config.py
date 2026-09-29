from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    GOOGLE_MAPS_API_KEY: str = ""
    MAPBOX_ACCESS_TOKEN: str = Field(default="", validation_alias="MAPBOX_API_KEY")
    OPENAI_API_KEY: str = ""
    DATABASE_URL: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_SECRET_KEY: str = ""

    OBSERVABILITY_ENV: str = "local"
    APP_VERSION: str = "local"

    LANGFUSE_TRACING_ENABLED: bool = False
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_BASE_URL: str = "http://localhost:3000"

    MLFLOW_EVAL_ENABLED: bool = False
    MLFLOW_TRACKING_URI: str = "http://localhost:5001"
    MLFLOW_EXPERIMENT_NAME: str = "argus-property-analysis"
    MLFLOW_S3_ENDPOINT_URL: str = "http://localhost:9000"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    model_config = {
        "env_file": "../.env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
