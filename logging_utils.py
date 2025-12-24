import logging
import os
import socket
from urllib.parse import urlparse


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    level_name = os.getenv("A2A_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


def resolve_url(url: str) -> tuple[str | None, int | None, list[str]]:
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port
    if port is None and parsed.scheme:
        port = 443 if parsed.scheme == "https" else 80

    ips: list[str] = []
    if host and port:
        try:
            infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            ips = sorted({info[4][0] for info in infos})
        except socket.gaierror as exc:
            ips = [f"<dns_error:{exc}>"]

    return host, port, ips
