# Experiment Setup

Argus uses two systems with separate responsibilities:

- **Langfuse** captures normal runtime traces, latency, token usage, cost, and
  reviewer annotations.
- **MLflow** stores canonical evaluation datasets and comparable experiment runs.

## 1. Start And Verify

Create `.env` from `.env.example`, then run:

```bash
make observability-check
```

The command waits for all dependencies, writes a synthetic trace to Langfuse,
and creates an `observability-smoke` run with an artifact in MLflow.

Open:

- Langfuse: http://localhost:3000
- MLflow: http://localhost:5001
- MinIO: http://localhost:9001

The local Langfuse login defaults to `argus@example.test` and
`argus-local-password`. These credentials and every `*_local_*` secret are for
local testing only and must be replaced before deployment to a shared machine.

## 2. Collect Candidate Cases

Set `LANGFUSE_TRACING_ENABLED=true`, then start the app with `make dev-full`.
One property analysis should be one trace. Use stable names such as
`analyze-property-images`; keep model names and property-specific values in
metadata rather than trace names.

Review traces for:

- valid and representative image inputs;
- complete structured output;
- model, prompt, workflow, and application versions;
- latency, token usage, and errors;
- absence of API keys or private data in captured fields.

Google image URLs currently contain credentials. Do not enable runtime tracing
for retained data until URL credentials are masked or removed from trace input.

## 3. Build Ground Truth

Reviewers should annotate fields against a written labeling guide. A case becomes
benchmark truth only after approval or adjudication. Store the following with
each case:

- stable `case_id`, property grouping key, and image/source version;
- input references and hashes;
- expected field values and allowed nulls;
- reviewer and approval state;
- collection time and geographic slice;
- dataset split assigned at the property/group level.

Create immutable dataset versions such as `property-vision-v1`. Never split
individual feedback rows from the same property across train and evaluation.

## 4. Define An Experiment

Change one controlled factor at a time whenever possible:

- prompt version;
- model snapshot;
- temperature or other inference parameter;
- image preprocessing or workflow version.

Use an MLflow experiment name for the long-lived problem, currently
`argus-property-analysis`. Use one run per candidate and log:

- dataset name and version;
- Git commit and application version;
- prompt name/hash/version;
- exact model and parameters;
- scorer names and versions;
- aggregate metrics and per-case outputs.

## 5. Score And Compare

Start with field-specific deterministic metrics:

- categorical and boolean fields: accuracy, precision, recall, and F1;
- numeric estimates: MAE plus an acceptable tolerance rate;
- nullable fields: abstention precision and recall;
- confidence values: calibration error or Brier score.

Add LLM judges only for subjective fields such as architectural style or visible
condition, and calibrate those judges against human-reviewed examples.

Always compare candidates on the same frozen holdout set. Review aggregate
results, important slices, and individual failures before choosing a winner.

## 6. Promote And Repeat

Record the selected run ID and promotion rationale. Keep the old run as the
baseline, add confirmed failures to a future dataset version, and rerun the full
suite after every prompt, model, or workflow change.

MLflow's current workflow is: trace the application, attach human expectations,
create an evaluation dataset, run `mlflow.genai.evaluate()`, compare results, and
iterate. Langfuse's runtime traces are candidate evidence; MLflow's reviewed
dataset is the benchmark source of truth.
