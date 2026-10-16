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

## Run on Kubernetes with Helm (Docker Desktop)

The chart lives in `charts/sre-lab`. Each environment has its own values file
(`values-dev.yaml`, `values-prod.yaml`) layered on top of `values.yaml`.

Always pass `--kube-context docker-desktop` / `--context docker-desktop` so nothing is
applied to another cluster.

```bash
helm upgrade --install sre-lab-dev charts/sre-lab \
  --kube-context docker-desktop -n sre-lab-dev --create-namespace \
  -f charts/sre-lab/values-dev.yaml --wait

helm list -A --kube-context docker-desktop
kubectl --context docker-desktop -n sre-lab-dev port-forward svc/sre-lab-dev 9090:80
curl localhost:9090/health

helm history sre-lab-dev --kube-context docker-desktop -n sre-lab-dev
helm rollback sre-lab-dev 1 --kube-context docker-desktop -n sre-lab-dev
```

## GitOps with Argo CD

Argo CD watches `charts/sre-lab` on `main` and keeps `sre-lab-dev` and `sre-lab-prod`
in sync with Git. Changes are made through pull requests, not with `helm upgrade`.

```bash
kubectl --context docker-desktop create namespace argocd
kubectl --context docker-desktop apply -n argocd --server-side --force-conflicts \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.5/manifests/install.yaml
kubectl --context docker-desktop apply -f argocd/
kubectl --context docker-desktop -n argocd get applications
```

Open the UI at https://localhost:8443 (user `admin`):

```bash
kubectl --context docker-desktop -n argocd port-forward svc/argocd-server 8443:443
kubectl --context docker-desktop -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d; echo
```

## Lint and test

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest
```
