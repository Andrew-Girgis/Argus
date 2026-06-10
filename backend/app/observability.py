import re
from typing import Any

from langfuse import Langfuse, get_client


SENSITIVE_KEY_PATTERN = re.compile(
    r"(api[_-]?key|access[_-]?token|secret|password|authorization|key)",
    re.IGNORECASE,
)
URL_SECRET_PATTERN = re.compile(
    r"([?&](?:key|token|access_token)=)[^&\s]+", re.IGNORECASE
)


def mask_langfuse_data(data: Any, **_: Any) -> Any:
    """Redact credentials before observations are exported to Langfuse."""
    if isinstance(data, str):
        return URL_SECRET_PATTERN.sub(r"\1[REDACTED]", data)
    if isinstance(data, dict):
        return {
            key: (
                "[REDACTED]"
                if SENSITIVE_KEY_PATTERN.search(str(key))
                else mask_langfuse_data(value)
            )
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [mask_langfuse_data(item) for item in data]
    return data


Langfuse(mask=mask_langfuse_data)
langfuse = get_client()
