# sre-lab

A small API used to practice the full SRE toolchain: Docker, GitHub Actions, Terraform,
Kubernetes, Helm, Argo CD, Prometheus and Grafana.

## Endpoints

- `GET /` returns a hello message
- `GET /health` returns `{"status": "ok"}`, used by health checks
- `GET /metrics` exposes Prometheus metrics (request count and latency)

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
```

## Lint and test

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest
```
