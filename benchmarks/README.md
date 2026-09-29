# Argus Experiments

Runtime application traces belong in Langfuse. Repeatable datasets, scorers, and
evaluation runs belong in MLflow.

## Connectivity Test

```bash
make observability-check
```

This starts both platforms, creates an MLflow experiment and artifact, and sends
a synthetic Langfuse trace. It does not call OpenAI.

## Experiment Lifecycle

1. Start the stack with `make observability`.
2. Enable runtime collection with `LANGFUSE_TRACING_ENABLED=true` and run Argus.
3. Inspect and annotate useful traces in Langfuse. Do not promote unreviewed user
   corrections directly into benchmark truth.
4. Export only approved cases into a versioned MLflow evaluation dataset.
5. Define deterministic field scorers before adding LLM judges.
6. Run each prompt/model/workflow candidate against the same frozen dataset.
7. Compare aggregate metrics and inspect per-case failures in MLflow.
8. Promote a candidate only after it beats the baseline without regressing key
   slices such as geography, property type, and image availability.

See `docs/experiments.md` for the detailed setup and naming conventions.
