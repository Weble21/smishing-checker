from __future__ import annotations

import asyncio
import socket

import pytest

import egress_proxy as proxy
from analyzer import blocked_browser_target


@pytest.mark.parametrize("address", [
    "127.0.0.1", "10.0.0.1", "172.16.0.1", "192.168.1.1",
    "169.254.169.254", "100.64.0.1", "0.0.0.0", "224.0.0.1",
    "::1", "fe80::1", "fc00::1", "::ffff:127.0.0.1",
])
def test_non_public_addresses_are_blocked(address):
    assert not proxy.public_ip(address)


@pytest.mark.parametrize("address", ["8.8.8.8", "1.1.1.1", "2606:4700:4700::1111"])
def test_public_addresses_are_allowed(address):
    assert proxy.public_ip(address)


@pytest.mark.parametrize("method,target", [
    ("CONNECT", "example.com:80"),
    ("CONNECT", "example.com:8080"), ("CONNECT", "example.com:443/path"),
    ("CONNECT", "user@example.com:443"),
    ("POST", "http://example.com/"), ("GET", "http://example.com:8080/"),
    ("GET", "http://user:pass@example.com/"),
    ("GET", "file:///etc/passwd"),
])
def test_proxy_target_parser_rejects_unsupported_methods_and_ports(method, target):
    with pytest.raises(proxy.BlockedTarget):
        proxy.parse_target(method, target)


@pytest.mark.parametrize("url", [
    "http://127.0.0.1", "http://localhost", "http://foo.localhost",
    "http://169.254.169.254", "http://[::1]/", "http://fastapi/",
    "http://service.internal/", "file:///etc/passwd",
])
def test_browser_blocks_local_targets_before_proxy(url):
    assert blocked_browser_target(url)


def test_browser_allows_public_domain_to_reach_proxy():
    assert not blocked_browser_target("https://example.com/")


def test_dns_rejects_mixed_public_and_private_results(monkeypatch):
    async def resolve():
        async def fake_getaddrinfo(host, port, *, type):
            return [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port)),
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port)),
            ]
        loop = asyncio.get_running_loop()
        monkeypatch.setattr(loop, "getaddrinfo", fake_getaddrinfo)
        with pytest.raises(proxy.BlockedTarget):
            await proxy.resolve_public("example.com", 443)
    asyncio.run(resolve())


def test_dns_rejects_private_only_result(monkeypatch):
    async def resolve():
        async def fake_getaddrinfo(host, port, *, type):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port))]
        loop = asyncio.get_running_loop()
        monkeypatch.setattr(loop, "getaddrinfo", fake_getaddrinfo)
        with pytest.raises(proxy.BlockedTarget):
            await proxy.resolve_public("localhost", 443)
    asyncio.run(resolve())


def test_proxy_blocks_redirect_target_and_pins_checked_ip(monkeypatch):
    async def exercise():
        upstream_requests = []

        async def upstream_handler(reader, writer):
            upstream_requests.append(await reader.readuntil(b"\r\n\r\n"))
            writer.write(
                b"HTTP/1.1 302 Found\r\nLocation: http://127.0.0.1/private\r\n"
                b"Content-Length: 0\r\nConnection: close\r\n\r\n"
            )
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        upstream = await asyncio.start_server(upstream_handler, "127.0.0.1", 0)
        upstream_port = upstream.sockets[0].getsockname()[1]
        original_open_connection = asyncio.open_connection
        connected_to = []

        async def fake_resolve(host, port):
            if host == "example.com":
                return "8.8.8.8", socket.AF_INET
            raise proxy.BlockedTarget("Non-public DNS answer")

        async def fake_open_connection(host, port, *, family):
            connected_to.append((host, port))
            assert host == "8.8.8.8" and port == 80
            return await original_open_connection("127.0.0.1", upstream_port)

        monkeypatch.setattr(proxy, "resolve_public", fake_resolve)
        monkeypatch.setattr(proxy.asyncio, "open_connection", fake_open_connection)
        server = await asyncio.start_server(proxy.handle_client, "127.0.0.1", 0)
        proxy_port = server.sockets[0].getsockname()[1]

        async def request(target):
            reader, writer = await original_open_connection("127.0.0.1", proxy_port)
            writer.write(f"GET {target} HTTP/1.1\r\nHost: attacker.example\r\n\r\n".encode())
            await writer.drain()
            response = await reader.read()
            writer.close()
            await writer.wait_closed()
            return response

        async with upstream, server:
            first = await request("http://example.com/start")
            second = await request("http://127.0.0.1/private")
        assert first.startswith(b"HTTP/1.1 302 Found")
        assert second.startswith(b"HTTP/1.1 403 Forbidden")
        assert connected_to == [("8.8.8.8", 80)]
        assert b"GET /start HTTP/1.1" in upstream_requests[0]
        assert b"Host: example.com" in upstream_requests[0]
        assert b"attacker.example" not in upstream_requests[0]

    asyncio.run(exercise())
