#!/usr/bin/env bash
# Invoked by scripts/deploy_ssm.py; credentials come from the EC2 instance role.
set -Eeuo pipefail
umask 077

stage=initialization
candidate=
env_candidate=
active_compose=
step() {
  stage=$1
  echo "[deploy] $stage"
}
diagnostics() {
  result=$?
  trap - EXIT
  if [ "$result" -ne 0 ]; then
    echo "[deploy] FAILED: stage=$stage exit=$result" >&2
    if [ -n "$active_compose" ] && [ -s "$active_compose" ]; then
      docker compose --env-file .env -f "$active_compose" ps -a || true
      docker compose --env-file .env -f "$active_compose" logs --no-color --tail 100 || true
    fi
  fi
  if [ -n "$candidate" ]; then rm -f -- "$candidate"; fi
  if [ -n "$env_candidate" ]; then rm -f -- "$env_candidate"; fi
  exit "$result"
}
trap diagnostics EXIT
trap 'echo "[deploy] Command failed at line $LINENO (exit=$?)" >&2' ERR

step "Validate deployment inputs"
: "${TAG:?Missing image tag}"
: "${REGISTRY:?Missing ECR registry}"
: "${AWS_REGION:?Missing AWS region}"
: "${COMPOSE_B64:?Missing Compose configuration}"
step "Open deployment directory"
cd "${DEPLOY_DIR:-/opt/smishing}"

step "Check required tools"
for tool in docker aws curl flock base64 mktemp awk cp mv rm grep sleep; do
  if ! command -v "$tool" >/dev/null; then
    echo "Missing required tool: $tool" >&2
    exit 1
  fi
done

# Also protects against SSM commands surviving a runner disconnect.
step "Acquire deployment lock"
exec 9>.deploy.lock
if ! flock -w 30 9; then
  echo "Could not acquire .deploy.lock within 30 seconds; check for an active deployment." >&2
  exit 1
fi
step "Check environment and model files"
for required in .env models/text/config.json models/url/model/config.json models/url/internal_test_metrics.json; do
  if [ ! -f "$required" ] || { [ "$required" != .env ] && [ ! -s "$required" ]; }; then
    echo "Missing required deployment file: $required" >&2
    exit 1
  fi
done
step "Check Docker Compose capabilities"
docker compose version
if ! docker compose up --help | grep -- '--wait-timeout' >/dev/null; then
  echo "Docker Compose must support up --wait-timeout. Check the installed Compose plugin." >&2
  exit 1
fi

step "Prepare deployment files"
candidate=$(mktemp ./compose.deploy.XXXXXX.yml)
env_candidate=$(mktemp ./.env.deploy.XXXXXX)
active_compose=$candidate

printf '%s' "$COMPOSE_B64" | base64 --decode > "$candidate"
export IMAGE_TAG="$TAG" ECR_REGISTRY="$REGISTRY"
step "Validate Compose configuration"
docker compose --env-file .env -f "$candidate" config --quiet
step "Log in to ECR from EC2"
aws ecr get-login-password --region "$AWS_REGION" |
  docker login --username AWS --password-stdin "$REGISTRY"

# Pull before changing the active server configuration.
step "Pull application images"
docker compose --env-file .env -f "$candidate" pull
step "Save previous configuration and install release"
if [ -f compose.prod.yml ]; then
  cp compose.prod.yml compose.prod.yml.previous
  cp .env .env.previous
fi
awk '!/^[[:space:]]*(export[[:space:]]+)?(IMAGE_TAG|ECR_REGISTRY)[[:space:]]*=/' .env > "$env_candidate"
printf '\nIMAGE_TAG=%s\nECR_REGISTRY=%s\n' "$TAG" "$REGISTRY" >> "$env_candidate"
mv "$env_candidate" .env
mv "$candidate" compose.prod.yml
active_compose=compose.prod.yml

step "Start services and wait for readiness"
docker compose --env-file .env -f compose.prod.yml up -d --wait --wait-timeout 900
# The web service has no container healthcheck; verify its HTTP endpoint too.
step "Check web HTTP response"
# Docker running does not mean Spring is listening yet. Retry even when the
# published port accepts TCP but resets it before the HTTP server is ready.
for attempt in {1..30}; do
  if curl --fail --silent --show-error --connect-timeout 3 --max-time 5 \
    http://127.0.0.1:8080/ > /dev/null; then
    echo "[deploy] Web HTTP check passed (attempt $attempt/30)"
    break
  else
    http_result=$?
  fi
  if [ "$attempt" -eq 30 ]; then
    echo "[deploy] Web did not become ready after 30 attempts (curl exit=$http_result)." >&2
    exit "$http_result"
  fi
  echo "[deploy] Waiting for web startup (attempt $attempt/30, curl exit=$http_result)"
  sleep 5
done
docker compose --env-file .env -f compose.prod.yml ps
echo "Deployment verified: $TAG"
