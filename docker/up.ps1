param([switch]$LegacyBuilder)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$stage = Join-Path $projectRoot ('.cache/docker-build-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $stage, "$stage/ocr-service", "$stage/config", "$stage/dataset/whiteList" | Out-Null
Copy-Item -LiteralPath gradlew, build.gradle, settings.gradle, .dockerignore -Destination $stage
Copy-Item -LiteralPath gradle, src, docker -Destination $stage -Recurse
Copy-Item -LiteralPath ocr-service/app.py, ocr-service/requirements.txt -Destination "$stage/ocr-service"
Copy-Item -LiteralPath ocr-service/smishing_api -Destination "$stage/ocr-service" -Recurse
Copy-Item -LiteralPath config/official_domain_seeds.json -Destination "$stage/config"
Copy-Item -LiteralPath dataset/whiteList/official_domains.csv -Destination "$stage/dataset/whiteList"
$previousBuilder = $env:DOCKER_BUILDKIT
try {
    if ($LegacyBuilder) { $env:DOCKER_BUILDKIT = '0' }
    docker build -f "$stage/docker/web.Dockerfile" -t smishing-checker-web $stage
    if ($LASTEXITCODE -ne 0) { throw 'Web image build failed.' }
    docker build -f "$stage/docker/fastapi.Dockerfile" -t smishing-checker-fastapi $stage
    if ($LASTEXITCODE -ne 0) { throw 'FastAPI image build failed.' }
    docker compose up -d --no-build
    if ($LASTEXITCODE -ne 0) { throw 'Compose startup failed. Check docker compose logs.' }
} finally {
    $env:DOCKER_BUILDKIT = $previousBuilder
}
