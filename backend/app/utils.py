import logging
import re
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """Configure application-wide logging."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


_SECRET_QUERY_PARAM = re.compile(r"(?i)\b(key|signature|token)=[^&\s'\"]+")


def redact_secrets(text: str) -> str:
    """Mask API keys and signatures in URLs embedded in error messages."""
    return _SECRET_QUERY_PARAM.sub(r"\1=<redacted>", text)
