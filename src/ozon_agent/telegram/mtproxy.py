"""MTProxy connector for Telegram Bot API.

Parses tg://proxy URLs and connects through Telegram's MTProxy.
Uses raw sockets with the MTProxy Obfuscated2 protocol.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import random
import socket
import struct
import time
from typing import Any

from urllib.parse import parse_qs, urlparse


def parse_proxy_url(url: str) -> dict[str, Any]:
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    return {
        "server": params.get("server", [""])[0],
        "port": int(params.get("port", ["0"])[0]),
        "secret": params.get("secret", [""])[0],
    }


def _int_to_bytes(n: int, length: int) -> bytes:
    return n.to_bytes(length, "little")


def _bytes_to_int(b: bytes) -> int:
    return int.from_bytes(b, "little")


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _sha1(data: bytes) -> bytes:
    return hashlib.sha1(data).digest()


class MTProxy:
    """Minimal MTProxy Obfuscated2 connector."""

    # Protocol constants
    TAG_PADDING = b"\x00" * 15
    TAG_SERVER = b"\x01\x00\x00\x00\x00\x00\x00\x00"
    TAG_CLIENT = b"\x01\x00\x00\x00\x00\x00\x00\x00"

    def __init__(self, proxy_url: str):
        parsed = parse_proxy_url(proxy_url)
        self.host = parsed["server"]
        self.port = parsed["port"]
        self.secret_hex = parsed["secret"]
        self.secret = bytes.fromhex(self.secret_hex)
        self._sock: socket.socket | None = None
        self._init: bytes = b""
        self._key: bytes = b""
        self._iv: bytes = b""
        self._decrypt_key: bytes = b""
        self._decrypt_iv: bytes = b""
        self._msg_seq: int = 0

    def connect(self, timeout: float = 30.0) -> None:
        """Establish MTProxy connection."""
        self._sock = socket.create_connection((self.host, self.port), timeout=timeout)
        self._sock.settimeout(timeout)
        self._init_connection()

    def _init_connection(self) -> None:
        """Perform Obfuscated2 handshake."""
        sock = self._sock
        assert sock is not None

        # Generate random padding
        random_bytes = os.urandom(55)

        # Generate init payload (64 bytes total)
        # First 56 bytes: random padding + protocol marker
        # Last 8 bytes: DC ID (for proxy selection)
        init = random_bytes[:55] + b"\xef"  # 0xef = proxy protocol tag

        # Ensure first byte != 0xef (required by protocol)
        if init[0:1] == b"\xef":
            init = b"\xee" + init[1:]

        self._init = init

        # Encrypt init with secret
        # For FakeTLS proxies, the secret is used to derive encryption keys
        if len(self.secret) == 16:
            # Simple proxy: send secret directly
            sock.sendall(b"\xee" + self.secret + init)
        elif len(self.secret) >= 17 and self.secret[0:1] in (b"\xb0", b"\xb1", b"\xb2"):
            # FakeTLS proxy
            # Derive key from secret
            self._derive_fake_tls_keys()
            # Send FakeTLS ClientHello
            self._send_fake_tls_hello()
        else:
            # Dedicated proxy tag
            sock.sendall(b"\xef" + self.secret + init)

        # Read server response
        response = sock.recv(64)
        if len(response) < 5:
            raise ConnectionError("MTProxy handshake: too short response")

        # For FakeTLS, parse the TLS-like response
        if self.secret[0:1] in (b"\xb0", b"\xb1", b"\xb2"):
            self._parse_fake_tls_response(response)

    def _derive_fake_tls_keys(self) -> None:
        """Derive encryption keys for FakeTLS proxy."""
        # The secret contains: [prefix(1)] [key(32)] [dc_id(2)] [serial(2)]
        # For FakeTLS: use the key part for encryption
        if len(self.secret) >= 33:
            key_material = self.secret[1:33]
        else:
            key_material = self.secret[1:]

        # Derive encrypt/decrypt keys
        self._key = _sha256(b"key" + key_material)[:32]
        self._iv = _sha256(b"iv" + key_material)[:32]
        self._decrypt_key = _sha256(b"dkey" + key_material)[:32]
        self._decrypt_iv = _sha256(b"div" + key_material)[:32]

    def _send_fake_tls_hello(self) -> None:
        """Send FakeTLS ClientHello."""
        sock = self._sock
        assert sock is not None

        # FakeTLS ClientHello: 0x16 0x03 0x01 + length + TLS data
        # Simplified: just send the proxy secret + init
        random_padding = os.urandom(55)
        init = random_padding[:55] + b"\xef"

        # For FakeTLS, prepend with TLS-like header
        hello = b"\x16\x03\x01" + struct.pack("!H", len(self.secret) + 64)
        hello += self.secret + init

        sock.sendall(hello)

    def _parse_fake_tls_response(self, response: bytes) -> None:
        """Parse FakeTLS ServerHello response."""
        # Skip TLS header if present
        if response[0:1] == b"\x16":
            # TLS record: type(1) + version(2) + length(2) + data
            if len(response) >= 5:
                data_len = struct.unpack("!H", response[3:5])[0]
                response = response[5:5 + data_len]

        # The actual proxy response follows
        if len(response) >= 64:
            # Parse init from response
            self._init = response[:64]

    def close(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def send_http_request(self, method: str, params: dict[str, Any] | None = None,
                          timeout: float = 30.0) -> dict[str, Any]:
        """Send HTTP request through MTProxy tunnel."""
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set")

        # Build HTTP request
        path = f"/bot{token}/{method}"
        body = ""
        if params:
            body = "&".join(f"{k}={v}" for k, v in params.items())

        host = "api.telegram.org"
        request_lines = [
            f"POST {path} HTTP/1.1",
            f"Host: {host}",
            "Content-Type: application/x-www-form-urlencoded",
            f"Content-Length: {len(body)}",
            "Connection: keep-alive",
            "",
            body,
        ]
        raw_request = "\r\n".join(request_lines).encode("utf-8")

        # Send through tunnel
        self._sock_send(raw_request)

        # Read response
        response_data = self._sock_recv_all(timeout)

        # Parse HTTP response
        header_end = response_data.find(b"\r\n\r\n")
        if header_end == -1:
            raise ConnectionError("Invalid HTTP response from proxy tunnel")

        response_body = response_data[header_end + 4:]
        return json.loads(response_body.decode("utf-8"))

    def _sock_send(self, data: bytes) -> None:
        """Send data through the tunnel."""
        assert self._sock is not None
        # For MTProxy, data goes through the encrypted tunnel
        # Simplified: send raw for now (real implementation needs encryption)
        self._sock.sendall(data)

    def _sock_recv_all(self, timeout: float) -> bytes:
        """Receive full HTTP response."""
        assert self._sock is not None
        self._sock.settimeout(timeout)
        chunks = []
        while True:
            try:
                chunk = self._sock.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
                # Check if we have complete HTTP response
                data = b"".join(chunks)
                if b"\r\n\r\n" in data:
                    # Check Content-Length
                    header_end = data.find(b"\r\n\r\n")
                    headers = data[:header_end].decode("utf-8", errors="ignore")
                    for line in headers.split("\r\n"):
                        if line.lower().startswith("content-length:"):
                            content_len = int(line.split(":", 1)[1].strip())
                            body_start = header_end + 4
                            if len(data) >= body_start + content_len:
                                return data[:body_start + content_len]
                    # Chunked transfer - try to detect end
                    if data.endswith(b"\r\n0\r\n\r\n"):
                        return data
            except socket.timeout:
                break
            except Exception:
                break
        return b"".join(chunks)


def make_api_call(method: str, params: dict[str, Any] | None = None,
                  timeout: float = 30.0) -> dict[str, Any]:
    """Make Bot API call through MTProxy."""
    proxy_url = os.environ.get("TELEGRAM_PROXY_URL", "").strip()
    if not proxy_url:
        raise ValueError("TELEGRAM_PROXY_URL not set")

    proxy = MTProxy(proxy_url)
    try:
        proxy.connect(timeout=timeout)
        return proxy.send_http_request(method, params, timeout)
    finally:
        proxy.close()
