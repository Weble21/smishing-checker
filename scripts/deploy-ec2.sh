#!/usr/bin/env bash
# Invoked by scripts/deploy_ssm.py; credentials come from the EC2 instance role.
set -Eeuo pipefail
umask 077

: "${TAG:?Missing image tag}"
: "${REGISTRY:?Missing ECR registry}"
: "${AWS_REGION:?Missing AWS region}"
: "${COMPOSE_B64:?Missing Compose configuration}"
cd "${DEPLOY_DIR:-/opt/smishing}"

# Also protects against SSM commands surviving a runner disconnect.
exec 9>.deploy.lock
flock -w 30 9
for required in .env models/text/config.json models/url/model/config.json models/url/internal_test_metrics.json; do
  if [ ! -f "$required" ] || { [ "$required" != .env ] && [ ! -s "$required" ]; }; then
    echo "Missing required deployment file: $required" >&2
    exit 1
  fi
done
docker compose up --help | grep -- '--wait-timeout' >/dev/null
command -v curl >/dev/null

candidate=$(mktemp ./compose.deploy.XXXXXX.yml)
env_candidate=$(mktemp ./.env.deploy.XXXXXX)
active_compose=$candidate
diagnostics() {
  result=$?
  trap - EXIT
  if [ "$result" -ne 0 ]; then
    echo "Deployment failed; inspect the logs below before retrying." >&2
    docker compose --env-file .env -f "$active_compose" ps -a || true
    docker compose --env-file .env -f "$active_compose" logs --no-color --tail 100 || true
  fi
  rm -f -- "$candidate" "$env_candidate"
  exit "$result"
}
trap diagnostics EXIT

printf '%s' "$COMPOSE_B64" | base64 --decode > "$candidate"
export IMAGE_TAG="$TAG" ECR_REGISTRY="$REGISTRY"
docker compose --env-file .env -f "$candidate" config --quiet
aws ecr get-login-password --region "$AWS_REGION" |
  docker login --username AWS --password-stdin "$REGISTRY"

# Pull before changing the active server configuration.
docker compose --env-file .env -f "$candidate" pull
if [ -f compose.prod.yml ]; then
  cp compose.prod.yml compose.prod.yml.previous
  cp .env .env.previous
fi
awk '!/^[[:space:]]*(export[[:space:]]+)?(IMAGE_TAG|ECR_REGISTRY)[[:space:]]*=/' .env > "$env_candidate"
printf '\nIMAGE_TAG=%s\nECR_REGISTRY=%s\n' "$TAG" "$REGISTRY" >> "$env_candidate"
mv "$env_candidate" .env
mv "$candidate" compose.prod.yml
active_compose=compose.prod.yml

docker compose --env-file .env -f compose.prod.yml up -d --wait --wait-timeout 900
# The web service has no container healthcheck; verify its HTTP endpoint too.
curl --fail --silent --show-error --retry 24 --retry-delay 5 \
  --retry-connrefused --retry-max-time 150 --max-time 5 \
  http://127.0.0.1:8080/ > /dev/null
docker compose --env-file .env -f compose.prod.yml ps
echo "Deployment verified: $TAG"
