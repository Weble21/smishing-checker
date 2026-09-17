"""Small fail-closed HTTP proxy for the isolated browser.

The browser has no default internet route. This process is the only component
attached to both the browser network and the outbound network. Every target is
resolved, checked, then connected by numeric IP (never resolved a second time).
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import os
import socket
from urllib.parse import urlsplit


MAX_HEADER_BYTES = 16_384
MAX_TRANSFER_BYTES = 10 * 1024 * 1024
CONNECT_TIMEOUT = 5
TUNNEL_TIMEOUT = 25
ALLOWED_METHODS = {"GET", "HEAD"}
logger = logging.getLogger(__name__)


class BlockedTarget(ValueError):
    pass


def public_ip(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return (
        address.is_global
        and not address.is_multicast
        and not address.is_reserved
        and not address.is_unspecified
    )


def parse_target(method: str, target: str) -> tuple[str, int, str | None]:
    if method == "CONNECT":
        if any(char in target for char in "/?#@\\"):
            raise BlockedTarget("Invalid CONNECT authority")
        try:
            parts = urlsplit("https://" + target)
            host, port = parts.hostname, parts.port
        except ValueError as exception:
            raise BlockedTarget("Invalid CONNECT authority") from exception
        if not host or port != 443 or parts.path or parts.query or parts.fragment:
            raise BlockedTarget("Only HTTPS port 443 is supported")
        return host, port, None

    if method not in ALLOWED_METHODS:
        raise BlockedTarget("Only GET and HEAD requests are supported")
    try:
        parts = urlsplit(target)
        host, port = parts.hostname, parts.port
    except ValueError as exception:
        raise BlockedTarget("Invalid HTTP URL") from exception
    if (parts.scheme.lower() != "http" or not host or parts.username
            or parts.password or port not in {None, 80}):
        raise BlockedTarget("Only absolute HTTP port 80 URLs are supported")
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    return host, 80, path


async def resolve_public(host: str, port: int) -> tuple[str, int]:
    if not host or len(host) > 253 or any(char.isspace() for char in host):
        raise BlockedTarget("Invalid host")
    loop = asyncio.get_running_loop()
    try:
        answers = await asyncio.wait_for(
            loop.getaddrinfo(host, port, type=socket.SOCK_STREAM),
            timeout=CONNECT_TIMEOUT,
        )
    except (OSError, asyncio.TimeoutError) as exception:
        raise BlockedTarget("DNS resolution failed") from exception
    if not answers or any(not public_ip(answer[4][0]) for answer in answers):
        raise BlockedTarget("Non-public DNS answer")
    return answers[0][4][0], answers[0][0]


async def _transfer(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    total = 0
    while True:
        data = await reader.read(65_536)
        if not data:
            break
        total += len(data)
        if total > MAX_TRANSFER_BYTES:
            raise BlockedTarget("Transfer limit exceeded")
        writer.write(data)
        await writer.drain()


async def _tunnel(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    remote_reader: asyncio.StreamReader,
    remote_writer: asyncio.StreamWriter,
) -> None:
    tasks = [
        asyncio.create_task(_transfer(client_reader, remote_writer)),
        asyncio.create_task(_transfer(remote_reader, client_writer)),
    ]
    try:
        done, pending = await asyncio.wait(
            tasks, timeout=TUNNEL_TIMEOUT, return_when=asyncio.FIRST_COMPLETED,
        )
        for task in done:
            task.result()
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
    finally:
        for task in tasks:
            task.cancel()


async def handle_client(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
) -> None:
    remote_writer: asyncio.StreamWriter | None = None
    try:
        header = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5)
        if len(header) > MAX_HEADER_BYTES:
            raise BlockedTarget("Headers too large")
        lines = header.decode("iso-8859-1").split("\r\n")
        method, target, version = lines[0].split(" ")
        if version != "HTTP/1.1" and version != "HTTP/1.0":
            raise BlockedTarget("Unsupported HTTP version")
        host, port, path = parse_target(method, target)
        ip, family = await resolve_public(host, port)
        remote_reader, remote_writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port, family=family),
            timeout=CONNECT_TIMEOUT,
        )
        if method == "CONNECT":
            writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            await writer.drain()
            await _tunnel(reader, writer, remote_reader, remote_writer)
        else:
            # Drop user-supplied routing and hop-by-hop headers. The proxy itself
            # decides the Host and closes the upstream connection after a response.
            kept = []
            for line in lines[1:]:
                if not line:
                    continue
                if ":" not in line:
                    raise BlockedTarget("Malformed HTTP header")
                name = line.split(":", 1)[0].lower()
                if name in {
                    "host", "proxy-authorization", "proxy-connection", "connection",
                    "keep-alive", "upgrade", "transfer-encoding", "content-length",
                }:
                    continue
                kept.append(line)
            authority = host if ":" not in host else f"[{host}]"
            request = "\r\n".join([
                f"{method} {path} HTTP/1.1", f"Host: {authority}",
                *kept, "Connection: close", "", "",
            ]).encode("iso-8859-1")
            remote_writer.write(request)
            await remote_writer.drain()
            await asyncio.wait_for(_transfer(remote_reader, writer), TUNNEL_TIMEOUT)
    except (BlockedTarget, ValueError, UnicodeError, asyncio.IncompleteReadError,
            asyncio.LimitOverrunError):
        writer.write(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
        await writer.drain()
    except (OSError, asyncio.TimeoutError):
        writer.write(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
        await writer.drain()
    finally:
        if remote_writer is not None:
            remote_writer.close()
            await remote_writer.wait_closed()
        writer.close()
        await writer.wait_closed()


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    port = int(os.getenv("EGRESS_PROXY_PORT", "3128"))
    server = await asyncio.start_server(
        handle_client, host="0.0.0.0", port=port,
        limit=MAX_HEADER_BYTES + 1,
    )
    logger.info("Egress proxy listening on port %s", port)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
