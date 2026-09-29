import os

from app.config import Settings, settings


def runtime_observability_enabled(config: Settings = settings) -> bool:
    """Return whether runtime tracing has all required configuration."""
    return bool(
        config.LANGFUSE_TRACING_ENABLED
        and config.LANGFUSE_PUBLIC_KEY
        and config.LANGFUSE_SECRET_KEY
    )


def setup_runtime_observability(config: Settings = settings) -> None:
    """Configure Langfuse before its OpenAI wrapper is imported."""
    enabled = runtime_observability_enabled(config)
    os.environ["LANGFUSE_TRACING_ENABLED"] = str(enabled).lower()
    os.environ["LANGFUSE_BASE_URL"] = config.LANGFUSE_BASE_URL
    os.environ["LANGFUSE_ENVIRONMENT"] = config.OBSERVABILITY_ENV
    os.environ["LANGFUSE_RELEASE"] = config.APP_VERSION

    if enabled:
        os.environ["LANGFUSE_PUBLIC_KEY"] = config.LANGFUSE_PUBLIC_KEY
        os.environ["LANGFUSE_SECRET_KEY"] = config.LANGFUSE_SECRET_KEY


def setup_mlflow_evaluation(config: Settings = settings) -> None:
    """Configure MLflow only for explicit benchmark and evaluation commands."""
    if not config.MLFLOW_EVAL_ENABLED:
        raise RuntimeError("MLFLOW_EVAL_ENABLED must be true for evaluation runs")

    import mlflow

    os.environ["MLFLOW_S3_ENDPOINT_URL"] = config.MLFLOW_S3_ENDPOINT_URL
    if config.AWS_ACCESS_KEY_ID:
        os.environ["AWS_ACCESS_KEY_ID"] = config.AWS_ACCESS_KEY_ID
    if config.AWS_SECRET_ACCESS_KEY:
        os.environ["AWS_SECRET_ACCESS_KEY"] = config.AWS_SECRET_ACCESS_KEY

    mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
    mlflow.set_experiment(config.MLFLOW_EXPERIMENT_NAME)
