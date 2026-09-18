from __future__ import annotations

import asyncio
import base64
import os
import ipaddress
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from playwright.async_api import Error as PlaywrightError, async_playwright

from schemas import (
    DownloadObservation,
    DynamicAnalysisResponse,
    FormObservation,
    NetworkObservation,
    RedirectHop,
)

MAX_NETWORK_REQUESTS = 100
MAX_VISIBLE_TEXT = 10_000
OBSERVATION_SECONDS = 2


def blocked_browser_target(url: str) -> bool:
    """Stop Chromium's implicit localhost proxy bypass before navigation."""
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return True
    host = parsed.hostname.rstrip(".").lower()
    if (host == "localhost" or host.endswith(".localhost")
            or "." not in host or host.endswith((".local", ".internal"))):
        return True
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    from egress_proxy import public_ip
    return not public_ip(host)


def blocked_navigation(final_url: str, responses: list[RedirectHop]) -> bool:
    return blocked_browser_target(final_url) or any(
        blocked_browser_target(response.url) for response in responses
    )


def redact_url(url: str) -> str:
    """Keep routing evidence while removing query values and fragments."""
    parsed = urlsplit(url)
    redacted_query = urlencode([
        (key, "REDACTED")
        for key, _ in parse_qsl(parsed.query, keep_blank_values=True)
    ])
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, redacted_query, ""))


async def analyze_url(url: str, timeout_seconds: float) -> DynamicAnalysisResponse:
    proxy_url = os.getenv("DYNAMIC_ANALYSIS_PROXY_URL")
    if not proxy_url or blocked_browser_target(url):
        raise ValueError("Controlled proxy is required")
    network_requests: list[NetworkObservation] = []
    downloads: list[DownloadObservation] = []
    download_urls: list[str] = []
    navigation_responses: list[RedirectHop] = []
    truncated = False

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
            chromium_sandbox=True,
        )
        context = await browser.new_context(
            accept_downloads=False,
            service_workers="block",
            viewport={"width": 1280, "height": 720},
            proxy={"server": proxy_url},
        )
        page = await context.new_page()

        async def enforce_browser_route(route) -> None:
            if blocked_browser_target(route.request.url) or route.request.method not in {"GET", "HEAD"}:
                await route.abort()
            else:
                await route.continue_()

        await context.route("**/*", enforce_browser_route)

        def observe_request(request) -> None:
            nonlocal truncated
            if len(network_requests) >= MAX_NETWORK_REQUESTS:
                truncated = True
                return
            network_requests.append(NetworkObservation(
                url=redact_url(request.url),
                method=request.method,
                resourceType=request.resource_type,
            ))

        def observe_response(response) -> None:
            if response.request.is_navigation_request() and response.frame == page.main_frame:
                navigation_responses.append(RedirectHop(
                    url=redact_url(response.url), status=response.status,
                ))

        def observe_download(download) -> None:
            download_urls.append(redact_url(download.url))
            downloads.append(DownloadObservation(
                suggestedFilename=download.suggested_filename[:255],
            ))

        page.on("request", observe_request)
        page.on("response", observe_response)
        page.on("download", observe_download)

        try:
            async with asyncio.timeout(timeout_seconds):
                try:
                    await page.goto(url, wait_until="domcontentloaded")
                except PlaywrightError as exception:
                    if "Download is starting" not in str(exception):
                        raise
                    await page.wait_for_timeout(200)
                    if not downloads:
                        raise
                await page.wait_for_timeout(OBSERVATION_SECONDS * 1000)
                title = (await page.title())[:500]
                body_text = await page.locator("body").inner_text(timeout=2_000)
                if len(body_text) > MAX_VISIBLE_TEXT:
                    body_text = body_text[:MAX_VISIBLE_TEXT]
                    truncated = True
                forms_raw = await page.locator("form").evaluate_all("""
                    forms => forms.slice(0, 30).map(form => {
                      const inputs = [...form.querySelectorAll('input, textarea, select')];
                      const types = inputs.map(input =>
                        (input.getAttribute('type') || input.tagName).toLowerCase());
                      const sensitive = inputs.filter(input => {
                        const value = `${input.name || ''} ${input.id || ''} ${input.autocomplete || ''}`;
                        const words = value.replace(/([a-z])([A-Z])/g, '$1 $2')
                          .toLowerCase().split(/[^a-z0-9]+/);
                        return input.type === 'password' || words.some(word =>
                          ['password', 'passwd', 'passcode', 'pwd', 'otp', 'pin',
                           'card', 'cardnumber', 'creditcard', 'cvv', 'cvc',
                           'account', 'resident', 'ssn'].includes(word));
                      }).map(input => input.type || input.tagName.toLowerCase());
                      return {
                        action: form.action || location.href,
                        method: (form.method || 'get').toUpperCase(),
                        inputTypes: [...new Set(types)],
                        sensitiveFields: [...new Set(sensitive)],
                      };
                    })
                """)
                forms = [FormObservation(
                    action=redact_url(item["action"]),
                    method=item["method"],
                    inputTypes=item["inputTypes"],
                    sensitiveFields=item["sensitiveFields"],
                ) for item in forms_raw]
                final_url = download_urls[-1] if download_urls else page.url
                if blocked_navigation(final_url, navigation_responses):
                    return DynamicAnalysisResponse(
                        status="FAILED", requestedUrl=redact_url(url),
                        finalUrl=redact_url(final_url),
                        redirectChain=navigation_responses,
                        networkRequests=network_requests,
                        errorCode="BLOCKED_DESTINATION",
                    )
                screenshot = base64.b64encode(await page.screenshot(
                    type="png", full_page=False,
                )).decode("ascii")
                return DynamicAnalysisResponse(
                    status="COMPLETED",
                    requestedUrl=redact_url(url),
                    finalUrl=redact_url(final_url),
                    title=title,
                    visibleText=body_text,
                    redirectChain=navigation_responses,
                    forms=forms,
                    networkRequests=network_requests,
                    downloads=downloads,
                    screenshotPngBase64=screenshot,
                    truncated=truncated,
                )
        finally:
            await context.close()
            await browser.close()
