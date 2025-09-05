# Task Manager Microservices

A small, Kubernetes-deployable microservices application with two independent Flask-based services and a PostgreSQL database with persistent storage. The app demonstrates designing, containerizing, and deploying horizontally scalable microservices with REST APIs, Ingress access, and a stateful database.

## What It Does

- `user-service`: Registers users and lists users (backed by PostgreSQL).
- `task-service`: Creates tasks and lists tasks (backed by PostgreSQL).
- `postgres`: Stores user and task data, persisted across pod restarts via a PersistentVolume.
- `Ingress`: Routes external traffic to services (`/` to task-service, `/user` to user-service).

Both services expose a friendly HTML homepage and a JSON REST API. Health endpoints enable Kubernetes liveness/readiness probes.

## Architecture

- Components:
  - User API (`Services/user-service`):
    - REST: `POST /register`, `GET /users`, `GET /health`.
    - Uses env vars `POSTGRES_*` for DB config.
    - Auto-creates `users` table if not present.
  - Task API (`Services/task-service`):
    - REST: `POST /tasks`, `GET /tasks`, `GET /health`.
    - Uses env vars `POSTGRES_*` for DB config.
    - Auto-creates `tasks` table if not present.
  - Database (`kubernetes/postgres-*.yaml`):
    - Single Postgres deployment + service, with `PersistentVolume` and `PersistentVolumeClaim`.
  - Ingress (`kubernetes/ingress.yaml`):
    - Host: `task-user.local`
    - `/` -> task-service, `/user` -> user-service

- Principles and patterns:
  - Microservices: Independent deployability and scaling (`replicas: 2` per service).
  - Stateless services: State kept only in PostgreSQL.
  - Externalization of config via environment variables and Secrets.
  - Health probes for robust orchestration (readiness/liveness).
  - Ingress-based north-south access for external clients.

- Mapping:
  - User component -> `user-service` Deployment/Service
  - Task component -> `task-service` Deployment/Service
  - Data persistence -> `postgres` Deployment/Service + PV/PVC

## Benefits and Challenges

- Benefits:
  - Independent scaling: Adjust replicas per service based on load.
  - Clear separation of concerns: User vs Task responsibilities.
  - Portability: Container images deploy on any K8s cluster.
  - Observability hooks: Health endpoints for probes.

- Challenges and mitigations:
  - Service startup vs DB readiness: Health probes + lazy table init prevent crash loops; retries handled by K8s.
  - Schema migrations: For simplicity, use `CREATE TABLE IF NOT EXISTS`; production would adopt a migrations tool.
  - Stateful data on local clusters: `hostPath` PV is node-bound. Use a StorageClass/Provisioner or a managed Postgres in cloud.
  - Security: Secrets used for DB creds; prefer per-service Secrets mounted as env vars, separate credentials per service, and NetworkPolicies to restrict east-west traffic. Add TLS to Ingress in real deployments, plus pod security contexts and resource quotas. Add authN/Z for APIs (omitted for brevity); use mTLS/service mesh for stronger S2S security.

## Prerequisites

- Kubernetes cluster (e.g., minikube, Docker Desktop, kind).
- NGINX Ingress Controller installed (for `ingressClassName: nginx`).
- `kubectl` configured to target your cluster.
- Optional: `minikube addons enable ingress` if using minikube.

## Build and Images

Manifests reference prebuilt images:
- For local dev on Mac/ARM, we use local images built into minikube.
- For submission (Docker Hub), push multi-arch images and update manifests.

If you change code and want to publish your own images:
1) Login to Docker Hub: `docker login`
2) Build and push multi-arch images:
   `DOCKERHUB_USER=<your_user> TAG=v1 scripts/build_push.sh`
3) Update manifests to your images (script prints suggested `sed` commands), then:
   `kubectl apply -f kubernetes/user-service.yaml && kubectl apply -f kubernetes/task-service.yaml`

## Deployment

1) Create persistent volume and claim (for local clusters):
- Ensure the path exists on your node: `/mnt/data/postgres` (create it if needed). On minikube: `minikube ssh -- sudo mkdir -p /mnt/data/postgres && sudo chown 1000:1000 /mnt/data/postgres`.

2) Apply Kubernetes manifests (namespace default):
- `kubectl apply -f kubernetes/postgres-pv.yaml`
- `kubectl apply -f kubernetes/postgres-secret.yaml`
- `kubectl apply -f kubernetes/postgres-deployment.yaml`
- `kubectl apply -f kubernetes/user-service.yaml`
- `kubectl apply -f kubernetes/task-service.yaml`
- `kubectl apply -f kubernetes/ingress.yaml`

3) Wait for pods to be Ready:
- `kubectl get pods -w`

4) Add host entry for Ingress (if using a local cluster):
- Resolve `task-user.local` to your ingress controller IP.
  - minikube: `echo "$(minikube ip) task-user.local" | sudo tee -a /etc/hosts`
  - Docker Desktop: use `127.0.0.1` if port forwarding is set by the controller.

## Access and Test

- Task Service (via Ingress):
  - Home: `http://task-user.local/`
  - Health: `http://task-user.local/health`
  - API:
    - Create task: `POST http://task-user.local/tasks` JSON `{ "title": "T1", "description": "D1" }`
    - List tasks: `GET http://task-user.local/tasks`

- User Service (via Ingress):
  - Home: `http://task-user.local/user/`
  - Health: `http://task-user.local/user/health`
  - API:
    - Register: `POST http://task-user.local/user/register` JSON `{ "name": "Alice", "email": "alice@example.com" }`
    - List users: `GET http://task-user.local/user/users`

- Example using curl:
```
curl -X POST -H "Content-Type: application/json" \
  -d '{"name":"Alice","email":"alice@example.com"}' \
  http://task-user.local/user/register

curl http://task-user.local/user/users

curl -X POST -H "Content-Type: application/json" \
  -d '{"title":"Buy milk","description":"2L whole"}' \
  http://task-user.local/tasks

curl http://task-user.local/tasks
```

## Horizontal Scaling

- Each service Deployment uses `replicas: 2`. Scale independently:
```
kubectl scale deployment user-service --replicas=3
kubectl scale deployment task-service --replicas=4
```

## Repository Structure

- `Services/user-service/`: Flask user service + Dockerfile
- `Services/task-service/`: Flask task service + Dockerfile
- `kubernetes/`: All manifests (DB PV/PVC, DB deployment, services, ingress, secret)

## Runbook Notes

- If Postgres isn’t ready initially, services report Unhealthy via `/health` until DB connections succeed. Probes gate traffic until ready.
- `hostPath` PV is only suitable for single-node dev clusters. Use a proper StorageClass (e.g., standard/minikube-hostpath) or managed storage in cloud.
- For production, add:
  - TLS to Ingress, mTLS between services, NetworkPolicies.
  - AuthN/Z on APIs (JWT/OAuth2), rate limiting, request validation.
  - Centralized logging/metrics (e.g., ELK/EFK, Prometheus/Grafana).

## Presenting the Project

Be ready to:
- Explain the microservices idea (Users and Tasks) and how each service’s API works.
- Discuss independent scaling and statelessness with a shared DB.
- Show Kubernetes manifests, how Ingress exposes the app, and how PV/PVC persist data.
- Discuss security tradeoffs and mitigations (Secrets, probes, Ingress, future TLS/NetworkPolicies/Auth).
- Run a demo using the steps above, show pod logs (`kubectl logs`), and scale a service live.
