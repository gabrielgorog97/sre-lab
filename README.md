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

## Run with Docker

```bash
docker build -t sre-lab:0.1.0 .
docker run -d --name sre-lab -p 8000:8000 sre-lab:0.1.0
curl localhost:8000/health
docker rm -f sre-lab
```

## Run with Terraform

Terraform pulls the image from GHCR and runs it as a container on Docker Desktop.
The image tag is set in `terraform/terraform.tfvars`.

```bash
cd terraform
terraform init
terraform plan -out=sre-lab.tfplan
terraform apply sre-lab.tfplan
curl localhost:8080/health
terraform destroy
```

## Run on Kubernetes (Docker Desktop)

Always pass `--context docker-desktop` so nothing is applied to another cluster.

```bash
kubectl --context docker-desktop apply -f k8s/namespace.yaml
kubectl --context docker-desktop apply -f k8s/
kubectl --context docker-desktop -n sre-lab rollout status deployment/sre-lab
kubectl --context docker-desktop -n sre-lab port-forward svc/sre-lab 9090:80
curl localhost:9090/health
```

## Lint and test

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest
```
