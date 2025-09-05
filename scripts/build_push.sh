#!/usr/bin/env bash
set -euo pipefail

# Build and push multi-arch images for both services to Docker Hub.
# Usage:
#   DOCKERHUB_USER=<your_user> TAG=v1 scripts/build_push.sh
# Requires: Docker Desktop logged in (`docker login`).

DOCKERHUB_USER=${DOCKERHUB_USER:-}
TAG=${TAG:-v1}

if [[ -z "${DOCKERHUB_USER}" ]]; then
  echo "Error: DOCKERHUB_USER is not set. Export it or prefix the command." >&2
  echo "Example: DOCKERHUB_USER=yourname TAG=v1 scripts/build_push.sh" >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon not running. Please start Docker Desktop." >&2
  exit 1
fi

echo "Ensuring buildx builder exists..."
if ! docker buildx inspect multi >/dev/null 2>&1; then
  docker buildx create --use --name multi
else
  docker buildx use multi
fi

PLATFORMS=${PLATFORMS:-linux/amd64,linux/arm64}

echo "Building and pushing ${DOCKERHUB_USER}/user-service:${TAG} for ${PLATFORMS}..."
docker buildx build \
  --platform ${PLATFORMS} \
  -t ${DOCKERHUB_USER}/user-service:${TAG} \
  --push \
  Services/user-service

echo "Building and pushing ${DOCKERHUB_USER}/task-service:${TAG} for ${PLATFORMS}..."
docker buildx build \
  --platform ${PLATFORMS} \
  -t ${DOCKERHUB_USER}/task-service:${TAG} \
  --push \
  Services/task-service

cat <<EOF

Images pushed:
  - ${DOCKERHUB_USER}/user-service:${TAG}
  - ${DOCKERHUB_USER}/task-service:${TAG}

Next, update manifests:
  sed -i '' -E "s|^(\s*image:).*$|\1 ${DOCKERHUB_USER}/user-service:${TAG}|" kubernetes/user-service.yaml
  sed -i '' -E "s|^(\s*image:).*$|\1 ${DOCKERHUB_USER}/task-service:${TAG}|" kubernetes/task-service.yaml

Then apply:
  kubectl apply -f kubernetes/user-service.yaml
  kubectl apply -f kubernetes/task-service.yaml
EOF

