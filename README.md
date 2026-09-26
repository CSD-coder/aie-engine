# ai.Encrypt Engine

A separately deployable FastAPI control plane and Celery worker system for real, safe-tensor weight transformation. The current **1.0 milestone** is intentionally narrow: it quantises supported Safetensors weight files to actual 4/5/6/8-bit affine representations, bit-packs them into `.aie`, validates each payload hash, decodes every output tensor, and reports measured reconstruction metrics. It does not claim transformer inference or unsupported formats are validated.

## Run locally

```bash
cp .env.example .env
# Set ENGINE_API_SECRET to a strong secret before use.
docker compose up --build
```

API docs are at `/v1/docs`; health is at `/health`. Send `Authorization: Bearer $ENGINE_API_SECRET` for every `/v1` endpoint. Keep this secret solely in a server-side integration.

## Deployment

Deploy `api` as the lightweight Render web service and `worker` separately (CPU or GPU provider) using the same PostgreSQL, Redis and S3-compatible configuration. Workers are stateless and use temporary directories. Configure bucket lifecycle policies for temporary files and results; generated URLs expire after one hour. Production workers should run with least privilege, resource limits, and egress limited to Hugging Face, object storage, Redis, and PostgreSQL.

## Security and operations

* Only Safetensors are accepted in the worker path; no pickle/state-dict loading occurs.
* CORS defaults to `https://app.aiencrypt.com`, never a wildcard.
* API keys support a rotation JSON record in `ENGINE_API_KEYS_JSON`: `{"key-id":{"secret":"...","status":"active","expires_at":"2027-01-01T00:00:00+00:00","permissions":["*"]}}`.
* Job transitions are persisted; Celery uses late acknowledgements and bounded retries for transient `OSError`s. Cancellation is cooperative between pipeline phases.

## Limitations and roadmap

Remote inspection/analyse must not invent file metadata; it is deferred to the worker pipeline. Hugging Face currently expects a safe `model.safetensors` file. Mixed precision, pruning, GPU inference quality benchmarks, GGUF, and transformer inference validation are deliberately advertised as unavailable until they are implemented and measured.
