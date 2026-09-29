import os
from unittest.mock import patch

import pytest

from app.config import Settings
from app.observability import (
    runtime_observability_enabled,
    setup_mlflow_evaluation,
    setup_runtime_observability,
)


def test_runtime_observability_requires_enabled_credentials():
    assert runtime_observability_enabled(Settings()) is False
    assert runtime_observability_enabled(
        Settings(
            LANGFUSE_TRACING_ENABLED=True,
            LANGFUSE_PUBLIC_KEY="lf_pk_test",
            LANGFUSE_SECRET_KEY="lf_sk_test",
        )
    ) is True


def test_setup_runtime_observability_sets_langfuse_environment(monkeypatch):
    config = Settings(
        OBSERVABILITY_ENV="test",
        APP_VERSION="test-version",
        LANGFUSE_TRACING_ENABLED=True,
        LANGFUSE_PUBLIC_KEY="lf_pk_test",
        LANGFUSE_SECRET_KEY="lf_sk_test",
        LANGFUSE_BASE_URL="http://langfuse.test",
    )

    setup_runtime_observability(config)

    assert os.environ["LANGFUSE_TRACING_ENABLED"] == "true"
    assert os.environ["LANGFUSE_PUBLIC_KEY"] == "lf_pk_test"
    assert os.environ["LANGFUSE_SECRET_KEY"] == "lf_sk_test"
    assert os.environ["LANGFUSE_BASE_URL"] == "http://langfuse.test"
    assert os.environ["LANGFUSE_ENVIRONMENT"] == "test"
    assert os.environ["LANGFUSE_RELEASE"] == "test-version"


def test_setup_mlflow_evaluation_requires_explicit_enablement():
    with pytest.raises(RuntimeError, match="MLFLOW_EVAL_ENABLED"):
        setup_mlflow_evaluation(Settings(MLFLOW_EVAL_ENABLED=False))


def test_setup_mlflow_evaluation_configures_server(monkeypatch):
    config = Settings(
        MLFLOW_EVAL_ENABLED=True,
        MLFLOW_TRACKING_URI="http://mlflow.test:5000",
        MLFLOW_EXPERIMENT_NAME="argus-test",
        MLFLOW_S3_ENDPOINT_URL="http://minio.test:9000",
        AWS_ACCESS_KEY_ID="test-access",
        AWS_SECRET_ACCESS_KEY="test-secret",
    )

    with (
        patch("mlflow.set_tracking_uri") as set_tracking_uri,
        patch("mlflow.set_experiment") as set_experiment,
    ):
        setup_mlflow_evaluation(config)

    set_tracking_uri.assert_called_once_with("http://mlflow.test:5000")
    set_experiment.assert_called_once_with("argus-test")
    assert os.environ["MLFLOW_S3_ENDPOINT_URL"] == "http://minio.test:9000"
