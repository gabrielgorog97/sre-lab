# sre-lab

A small demo store, **uptime.supply**, used to practice the full SRE toolchain: Docker,
GitHub Actions, Terraform, Kubernetes, Helm, Argo CD, Prometheus, Grafana and Loki.
Nothing is for sale and no payment is taken.

The store has a chaos panel that slows down or fails the checkout. That is what makes the
alerts, dashboards and logs in this repo show something real.

## Endpoints

- `GET /` the store UI
- `GET /api/products` the product list
- `POST /api/checkout` places a fake order; returns 503 when chaos says the payment fails
- `GET /api/chaos`, `POST /api/chaos` read or set extra latency and failure rate for checkout.
  Chaos is kept in memory per pod and resets itself after 5 minutes.
- `GET /health` returns `{"status": "ok"}`, used by health checks
- `GET /error` always returns 500
- `GET /metrics` exposes Prometheus metrics (requests, latency, `shop_orders_total`)

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

## Monitoring (Prometheus, Grafana, Alertmanager)

`argocd/monitoring.yaml` installs kube-prometheus-stack. Grafana and Prometheus are exposed
as LoadBalancer services, which Docker Desktop publishes on localhost.

The Grafana admin password is read from a Secret that is created by hand, so it never
lands in Git:

```bash
kubectl --context docker-desktop create namespace monitoring
kubectl --context docker-desktop -n monitoring create secret generic grafana-admin \
  --from-literal=admin-user=admin --from-literal=admin-password='<choose-one>'
kubectl --context docker-desktop apply -f argocd/monitoring.yaml
kubectl --context docker-desktop apply -f argocd/monitoring-dashboards.yaml
```

- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090

## Public URLs (Cloudflare Tunnel)

| URL | What | Access |
|---|---|---|
| https://sre.gabrielgorog.ro | the store (dev) | public |
| https://grafana.gabrielgorog.ro | dashboards, logs, alerts | public read-only, admin login for changes |
| https://argocd.gabrielgorog.ro | GitOps apps | public read-only, admin login for changes |

A `cloudflared` pod opens an outbound connection to Cloudflare, so the cluster needs no public
IP and no open ports. Everything is online only while the cluster runs.

Prometheus and Alertmanager have no login of their own, so they stay private. Their data is
visible through Grafana, which uses both as data sources.

Argo CD is installed from the upstream manifest, not managed by itself, so read-only access
is set by hand:

```bash
kubectl -n argocd patch cm argocd-cm --type merge \
  -p '{"data":{"users.anonymous.enabled":"true","url":"https://argocd.gabrielgorog.ro"}}'
kubectl -n argocd patch cm argocd-rbac-cm --type merge -p '{"data":{"policy.default":"role:readonly"}}'
```

One-time setup, done from the CLI without the Zero Trust dashboard:

```bash
cloudflared tunnel login
cloudflared tunnel create sre-lab
cloudflared tunnel route dns sre-lab sre.gabrielgorog.ro
kubectl -n cloudflared create secret generic tunnel-credentials \
  --from-file=credentials.json=$HOME/.cloudflared/<tunnel-id>.json
kubectl apply -f argocd/cloudflared.yaml
```

## Lint and test

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest
```
