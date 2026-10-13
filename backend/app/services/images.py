import base64
import hashlib
import logging
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Only Google Maps imagery is downloaded. Anything else could make the backend
# fetch arbitrary URLs on a caller's behalf.
ALLOWED_IMAGE_HOSTS = {"maps.googleapis.com"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024
DOWNLOAD_TIMEOUT_SECONDS = 15.0


class ImageDownloadError(Exception):
    """Download failure with a message that is safe to return and trace.

    Messages never include the URL, because Google image URLs carry the API key.
    """


class DownloadedImage(BaseModel):
    data_url: str
    sha256: str
    content_type: str
    size_bytes: int


def _check_allowed(url: str, label: str) -> None:
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in ALLOWED_IMAGE_HOSTS:
        raise ImageDownloadError(
            f"{label} image host is not allowed (only Google Maps imagery is accepted)"
        )


async def download_image(url: str, label: str) -> DownloadedImage:
    """Download an allowed image and return it as a base64 data URL with its hash."""
    _check_allowed(url, label)

    try:
        async with httpx.AsyncClient(
            timeout=DOWNLOAD_TIMEOUT_SECONDS, follow_redirects=False
        ) as client:
            async with client.stream("GET", url) as response:
                if response.status_code != 200:
                    raise ImageDownloadError(
                        f"{label} image download failed: HTTP {response.status_code}"
                    )

                content_type = (
                    response.headers.get("content-type", "").split(";")[0].strip()
                )
                if content_type not in ALLOWED_CONTENT_TYPES:
                    raise ImageDownloadError(
                        f"{label} image has unsupported content type: {content_type or 'none'}"
                    )

                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_IMAGE_BYTES:
                        raise ImageDownloadError(
                            f"{label} image exceeds {MAX_IMAGE_BYTES} bytes"
                        )
    except httpx.HTTPError as exc:
        # httpx error messages include the request URL, so only report the type.
        logger.warning("%s image download failed: %s", label, type(exc).__name__)
        raise ImageDownloadError(
            f"{label} image download failed: {type(exc).__name__}"
        ) from None

    data = bytes(body)
    encoded = base64.b64encode(data).decode("ascii")
    return DownloadedImage(
        data_url=f"data:{content_type};base64,{encoded}",
        sha256=hashlib.sha256(data).hexdigest(),
        content_type=content_type,
        size_bytes=len(data),
    )
