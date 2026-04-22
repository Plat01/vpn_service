#!/usr/bin/env python3
"""
Проверка работоспособности VPN-ссылок (VLESS, Trojan).
Базовая проверка: TCP-соединение, валидация параметров.
Для полной проверки нужен xray-core/sing-box клиент.
"""

import asyncio
import re
import socket
import ssl
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, unquote


@dataclass
class VPNSource:
    protocol: str
    uuid: str
    host: str
    port: int
    params: dict
    remark: str
    raw: str

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"


@dataclass
class CheckResult:
    source: VPNSource
    tcp_ok: bool
    tcp_time_ms: float
    tls_ok: bool
    tls_error: str
    params_valid: bool
    params_error: str


def parse_vless_url(url: str) -> VPNSource | None:
    query_pos = url.find("?")
    if query_pos == -1:
        return None

    hash_pos = url.find("#", query_pos)
    if hash_pos == -1:
        return None

    base_url = url[:hash_pos]
    remark = unquote(url[hash_pos + 1 :])

    pattern = r"^vless://([^@]+)@([^:]+):(\d+)\?(.*)$"
    match = re.match(pattern, base_url)
    if not match:
        return None

    uuid, host, port, query = match.groups()
    params = parse_qs(query)
    params = {k: v[0] for k, v in params.items()}

    return VPNSource(
        protocol="vless",
        uuid=uuid,
        host=host,
        port=int(port),
        params=params,
        remark=remark,
        raw=url,
    )


def parse_trojan_url(url: str) -> VPNSource | None:
    query_pos = url.find("?")
    if query_pos == -1:
        return None

    hash_pos = url.find("#", query_pos)
    if hash_pos == -1:
        return None

    base_url = url[:hash_pos]
    remark = unquote(url[hash_pos + 1 :])

    pattern = r"^trojan://([^@]+)@([^:]+):(\d+)\?(.*)$"
    match = re.match(pattern, base_url)
    if not match:
        return None

    password, host, port, query = match.groups()
    params = parse_qs(query)
    params = {k: v[0] for k, v in params.items()}

    return VPNSource(
        protocol="trojan",
        uuid=password,
        host=host,
        port=int(port),
        params=params,
        remark=remark,
        raw=url,
    )


def parse_vpn_url(url: str) -> VPNSource | None:
    url = url.strip()
    if url.startswith("vless://"):
        return parse_vless_url(url)
    elif url.startswith("trojan://"):
        return parse_trojan_url(url)
    return None


def validate_params(source: VPNSource) -> tuple[bool, str]:
    if source.protocol == "vless":
        security = source.params.get("security", "")
        if security not in ("reality", "tls", "none", ""):
            return False, f"Unknown security: {security}"

        if security == "reality":
            required = ("sni", "pbk", "sid")
            missing = [p for p in required if p not in source.params]
            if missing:
                return False, f"Missing Reality params: {missing}"

        flow = source.params.get("flow", "")
        if flow and flow not in ("xtls-rprx-vision", "xtls-rprx-origin"):
            return False, f"Unknown flow: {flow}"

    elif source.protocol == "trojan":
        security = source.params.get("security", "tls")
        if security not in ("tls", "none"):
            return False, f"Unknown security: {security}"

    if source.port < 1 or source.port > 65535:
        return False, f"Invalid port: {source.port}"

    return True, ""


async def check_tcp_connection(
    host: str, port: int, timeout: float = 5.0
) -> tuple[bool, float]:
    start = time.monotonic()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        elapsed_ms = (time.monotonic() - start) * 1000
        return True, elapsed_ms
    except (asyncio.TimeoutError, socket.error, OSError) as e:
        return False, 0.0


async def check_tls_connection(
    host: str, port: int, sni: str, timeout: float = 5.0
) -> tuple[bool, str]:
    try:
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED

        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port, ssl=context, server_hostname=sni),
            timeout=timeout,
        )
        writer.close()
        await writer.wait_closed()
        return True, ""
    except Exception as e:
        return False, str(e)[:100]


async def check_source(source: VPNSource) -> CheckResult:
    tcp_ok, tcp_time = await check_tcp_connection(source.host, source.port)

    tls_ok = False
    tls_error = ""

    security = source.params.get("security", "")
    sni = source.params.get("sni", source.host)

    if security in ("tls", "reality"):
        tls_ok, tls_error = await check_tls_connection(source.host, source.port, sni)

    params_valid, params_error = validate_params(source)

    return CheckResult(
        source=source,
        tcp_ok=tcp_ok,
        tcp_time_ms=tcp_time,
        tls_ok=tls_ok,
        tls_error=tls_error,
        params_valid=params_valid,
        params_error=params_error,
    )


def print_result(result: CheckResult, index: int, total: int):
    src = result.source

    status_parts = []
    if result.tcp_ok:
        status_parts.append(f"TCP ✓ {result.tcp_time_ms:.0f}ms")
    else:
        status_parts.append("TCP ✗")

    security = src.params.get("security", "")
    if security in ("tls", "reality"):
        if result.tls_ok:
            status_parts.append("TLS ✓")
        else:
            status_parts.append(f"TLS ✗")

    if not result.params_valid:
        status_parts.append(f"PARAMS ✗")

    status = " | ".join(status_parts)

    remark = src.remark[:40] if src.remark else src.host

    print(f"[{index}/{total}] {remark}")
    print(f"  {src.host}:{src.port} ({src.protocol}/{security})")
    print(f"  {status}")

    if not result.params_valid:
        print(f"  Params error: {result.params_error}")

    if security in ("tls", "reality") and not result.tls_ok and result.tcp_ok:
        print(f"  TLS error: {result.tls_error}")

    print()


async def main():
    links_file = Path(__file__).parent.parent / ".eggs" / "vless_links.txt"

    if not links_file.exists():
        print(f"File not found: {links_file}")
        sys.exit(1)

    sources = []
    with open(links_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            source = parse_vpn_url(line)
            if source:
                sources.append(source)

    if not sources:
        print("No valid VPN URLs found")
        sys.exit(1)

    print(f"Checking {len(sources)} VPN sources...\n")
    print("=" * 60)
    print()

    tasks = [check_source(s) for s in sources]
    results = await asyncio.gather(*tasks)

    for i, result in enumerate(results, 1):
        print_result(result, i, len(results))

    print("=" * 60)
    print("\nSummary:")

    tcp_ok = sum(1 for r in results if r.tcp_ok)
    tls_ok = sum(1 for r in results if r.tls_ok)
    params_ok = sum(1 for r in results if r.params_valid)

    print(f"  TCP connection OK: {tcp_ok}/{len(results)}")
    print(f"  TLS handshake OK: {tls_ok}/{len(results)}")
    print(f"  Params valid: {params_ok}/{len(results)}")

    print("\nNote: Full VPN validation requires xray-core or sing-box client.")
    print("This script only checks basic connectivity and parameter validity.")


if __name__ == "__main__":
    asyncio.run(main())
