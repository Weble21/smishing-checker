# Dynamic URL analysis worker

This service opens a URL in a disposable Chromium browser context and records only
observable evidence: redirects, visible text, forms, network requests, download
attempts, and a viewport screenshot. It does not click, type, submit forms, or keep
browser profiles between requests.

The candidate selection rules and evidence limits are documented in
`../docs/dynamic-analysis-scope.md`.

## Controlled outbound access

The browser is attached only to the `sandbox-internal` network. The separate
`egress-proxy` is attached to that network and to `sandbox-egress`. Every browser
HTTP request or HTTPS CONNECT reaches the proxy, which permits ports 80/443 only,
checks every A/AAAA DNS answer, and connects to the checked numeric IP. A redirect
or subresource request causes a new proxy decision. Browser routing also rejects
localhost, non-public literal IPs, and non-GET/HEAD requests.

`DYNAMIC_ANALYSIS_ENABLED=false` remains the default. Set it to `true` only after
the deployed Docker environment passes the network isolation checks below.
`DYNAMIC_ANALYSIS_EGRESS_READY=true` is set by Compose when the controlled proxy
service is present. The worker requires both flags.

## Job API and result contract

`POST /jobs` accepts `{"url":"https://example.com"}` and returns HTTP 202 with a
job ID. `GET /jobs/{jobId}` returns `QUEUED`, `RUNNING`, `COMPLETED`, `TIMED_OUT`,
or `FAILED`. Active duplicate URLs share one job. One worker consumes the bounded
queue; completed jobs are retained in memory for 30 minutes with a 200-job limit.
Container restart clears the queue and retained results.
Call `GET /jobs/{jobId}?includeArtifacts=false` when only status and assessment are
needed; this omits captured page text and screenshots from the response.

A completed result includes:

- requested and final URL plus navigation responses
- title and up to 10,000 visible text characters
- forms, input types, and possible sensitive fields
- up to 100 network requests with query values redacted
- attempted download filenames
- a base64 encoded viewport PNG

Only one browser analysis can run at a time, and each request gets a new browser
process and context. The worker never clicks, types, or submits a form.

`TIMED_OUT` and `FAILED` are explicit inconclusive outcomes. They must never be
interpreted as safe.

## Start the isolated shell

```powershell
docker compose --profile dynamic-analysis up -d --build dynamic-analysis
docker compose --profile dynamic-analysis exec dynamic-analysis python -c \
  "import json,urllib.request; print(json.load(urllib.request.urlopen('http://127.0.0.1:8081/health')))"
```

The worker API is intentionally not published to the host. The main FastAPI and
worker communicate through the separate internal `analysis-control` network. The
browser worker remains detached from every network that has a default internet
route.

Before enabling analysis, verify from inside the browser container that direct
internet access fails, the proxy denies `http://127.0.0.1/` and
`http://169.254.169.254/`, and a public HTTPS target connects through the proxy.
Then set `DYNAMIC_ANALYSIS_ENABLED=true` and recreate both `fastapi` and
`dynamic-analysis`. Keep the proxy private; it publishes no host port.
