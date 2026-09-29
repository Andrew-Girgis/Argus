import json
import os
import tempfile
import time
from pathlib import Path

import mlflow
from langfuse import Langfuse

from app.config import settings
from app.observability import setup_mlflow_evaluation


def smoke_mlflow() -> dict[str, str]:
    setup_mlflow_evaluation()
    experiment = mlflow.get_experiment_by_name(settings.MLFLOW_EXPERIMENT_NAME)
    if experiment is None:
        raise RuntimeError("MLflow experiment was not created")

    with tempfile.TemporaryDirectory() as temp_dir:
        artifact = Path(temp_dir) / "smoke.json"
        artifact.write_text('{"status":"ok"}\n', encoding="utf-8")

        with mlflow.start_run(run_name="observability-smoke") as run:
            mlflow.log_param("purpose", "connectivity-test")
            mlflow.log_metric("smoke_success", 1)
            mlflow.log_artifact(artifact)
            run_id = run.info.run_id

    return {"experiment_id": experiment.experiment_id, "run_id": run_id}


def smoke_langfuse() -> dict[str, str]:
    client = Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY", "lf_pk_argus_local_testing_only"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY", "lf_sk_argus_local_testing_only"),
        base_url=os.getenv("LANGFUSE_BASE_URL", "http://localhost:3000"),
        environment="smoke-test",
    )
    if not client.auth_check():
        raise RuntimeError("Langfuse authentication failed")

    with client.start_as_current_observation(
        name="verify-observability-stack",
        as_type="span",
        input={"synthetic": True},
        output={"status": "ok"},
        metadata={"purpose": "connectivity-test"},
    ):
        pass
    client.flush()

    for _ in range(10):
        observations = client.api.observations.get_many(
            name="verify-observability-stack",
            environment="smoke-test",
            limit=1,
        )
        if observations.data:
            return {
                "base_url": os.getenv("LANGFUSE_BASE_URL", "http://localhost:3000"),
                "observation_id": observations.data[0].id,
            }
        time.sleep(1)

    raise RuntimeError("Synthetic Langfuse observation was not queryable after flush")


def main() -> None:
    result = {"mlflow": smoke_mlflow(), "langfuse": smoke_langfuse()}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
