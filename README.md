# Task Manager Microservices

A Kubernetes-deployable microservices app with:
- User API (Flask) to register/list users
- Task API (Flask) to create/list/complete/delete tasks
- Frontend (Nginx static HTML/JS) for an interactive UI
- PostgreSQL with persistent storage
- Ingress for browser access and independent horizontal scaling

Both APIs provide health endpoints; services initialize their tables automatically.

## Architecture

- Components:
  - Frontend (`Services/frontend`): Nginx serves `index.html` and reverse-proxies API calls:
    - `/api/tasks` → task-service
    - `/api/user` → user-service
    - `/api/health` → task-service health
  - User API (`Services/user-service`):
    - REST: `POST /register`, `GET /users`, `GET /health`
    - Also accepts prefixed routes: `/api/user/register`, `/api/user/users`, `/api/user/health`
  - Task API (`Services/task-service`):
    - REST: `POST /tasks`, `GET /tasks`, `PATCH /tasks/{id}/complete`, `DELETE /tasks/{id}`, `GET /health`
    - Also accepts prefixed routes under `/api/tasks` and `/api/health`
  - Database (`kubernetes/postgres-*.yaml`): Postgres Deployment + Service with PV/PVC persistence
  - Ingress (`kubernetes/ingress.yaml`): Routes `/` → frontend, `/api/tasks` → task-service, `/api/user` → user-service

- Principles:
  - Microservices with independent scaling (`replicas: 2`)
  - Stateless services; state in Postgres
  - Config via env vars and Secret
  - Health probes and readiness gates
  - Clear north-south routing via Ingress

## Prerequisites

- Docker Desktop (running)
- Homebrew (macOS), `kubectl`, `minikube`
- Ingress: `minikube addons enable ingress`

## Quick Start (Local Dev)

1) Start cluster and ingress
- `minikube start --driver=docker`
- `minikube addons enable ingress`
- Ensure PV path in minikube: `minikube ssh -- 'sudo mkdir -p /mnt/data/postgres && sudo chown -R 999:999 /mnt/data/postgres'`

2) Build images directly into minikube
- `minikube image build -t user-service:local Services/user-service`
- `minikube image build -t task-service:local Services/task-service`
- `minikube image build -t frontend:local Services/frontend`

3) Deploy manifests
- `kubectl apply -f kubernetes/postgres-pv.yaml`
- `kubectl apply -f kubernetes/postgres-secret.yaml`
- `kubectl apply -f kubernetes/postgres-deployment.yaml`
- `kubectl apply -f kubernetes/user-service.yaml`
- `kubectl apply -f kubernetes/task-service.yaml`
- `kubectl apply -f kubernetes/frontend.yaml`
- `kubectl apply -f kubernetes/ingress.yaml`

4) Wait for pods
- `kubectl rollout status deployment/postgres --timeout=180s`
- `kubectl rollout status deployment/user-service --timeout=240s`
- `kubectl rollout status deployment/task-service --timeout=240s`
- `kubectl rollout status deployment/frontend --timeout=240s`

5) Access the app
- Ingress host: `echo "$(minikube ip) task-user.local" | sudo tee -a /etc/hosts`
- Open UI: `http://task-user.local/`
- APIs via Ingress: `http://task-user.local/api/tasks`, `http://task-user.local/api/user`

Alternative (port-forward)
- Frontend: `kubectl port-forward service/frontend 8080:80` → `http://localhost:8080/`
- Task API: `kubectl port-forward service/task-service 8081:80` → `http://localhost:8081/`
- User API: `kubectl port-forward service/user-service 8082:80` → `http://localhost:8082/`

## Endpoints Summary

- Frontend UI: `/`
- Task API:
  - `GET /api/health` (health)
  - `GET /api/tasks` (list)
  - `POST /api/tasks` (create: { title, description })
  - `PATCH /api/tasks/{id}/complete` (complete)
  - `DELETE /api/tasks/{id}` (delete)
- User API:
  - `GET /api/user/health` (health)
  - `GET /api/user/users` (list)
  - `POST /api/user/register` (create: { name, email })

## Publish Images to Docker Hub (Optional)

1) Login: `docker login`
2) Build and push multi-arch images:
- `DOCKERHUB_USER=<your_user> TAG=v1 scripts/build_push.sh`
3) Update `image:` in manifests to your tags:
- `kubernetes/user-service.yaml` → `<your_user>/user-service:v1`
- `kubernetes/task-service.yaml` → `<your_user>/task-service:v1`
- Optionally create a frontend repo/tag and update `kubernetes/frontend.yaml`
4) Re-apply: `kubectl apply -f kubernetes/`

## Troubleshooting

- 502 via tunnels: Prefer port-forward or run a single tunnel to the frontend (same-origin) so `/api/*` works.
- Pods Pending/CrashLoop: `kubectl describe pod <pod>`, `kubectl logs <pod>`.
- Ingress not routing: ensure addon enabled and hosts entry added; on some setups use `minikube tunnel`.
- Postgres path: PV uses `/mnt/data/postgres` inside minikube VM.

## Presentation Notes

- Show UI interactions (create/complete/delete tasks, register users)
- Show logs: `kubectl logs deployment/* -f`
- Scale services independently with `kubectl scale`
- Discuss architecture, security, and deployment decisions
