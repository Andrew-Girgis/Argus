import base64
import hashlib

import httpx
import pytest

from app.services import images
from app.services.images import ImageDownloadError, download_image

KEYED_URL = "https://maps.googleapis.com/maps/api/staticmap?center=43,-79&key=SECRET_TEST_KEY"
JPEG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


@pytest.fixture
def respond(monkeypatch):
    """Route the downloader's HTTP client through a mock handler."""
    real_client = httpx.AsyncClient

    def install(handler):
        monkeypatch.setattr(
            images.httpx,
            "AsyncClient",
            lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
        )

    return install


async def test_downloads_image_as_data_url_with_hash(respond):
    respond(lambda request: httpx.Response(200, content=JPEG, headers={"content-type": "image/jpeg"}))

    image = await download_image(KEYED_URL, "satellite")

    assert image.data_url == "data:image/jpeg;base64," + base64.b64encode(JPEG).decode()
    assert image.sha256 == hashlib.sha256(JPEG).hexdigest()
    assert image.size_bytes == len(JPEG)
    assert image.content_type == "image/jpeg"


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/house.jpg",
        "http://maps.googleapis.com/maps/api/staticmap",
        "https://maps.googleapis.com.evil.test/maps/api/staticmap",
        "https://169.254.169.254/latest/meta-data",
        "file:///etc/passwd",
    ],
)
async def test_rejects_hosts_outside_allowlist(url, respond):
    def handler(request):
        raise AssertionError("no request should be made")

    respond(handler)

    with pytest.raises(ImageDownloadError, match="host is not allowed"):
        await download_image(url, "street_view")


async def test_does_not_follow_redirects(respond):
    respond(lambda request: httpx.Response(302, headers={"location": "http://169.254.169.254/"}))

    with pytest.raises(ImageDownloadError, match="HTTP 302"):
        await download_image(KEYED_URL, "street_view")


async def test_rejects_non_image_content(respond):
    respond(lambda request: httpx.Response(200, content=b"{}", headers={"content-type": "application/json"}))

    with pytest.raises(ImageDownloadError, match="unsupported content type"):
        await download_image(KEYED_URL, "street_view")


async def test_rejects_oversized_image(respond, monkeypatch):
    monkeypatch.setattr(images, "MAX_IMAGE_BYTES", 8)
    respond(lambda request: httpx.Response(200, content=JPEG, headers={"content-type": "image/jpeg"}))

    with pytest.raises(ImageDownloadError, match="exceeds"):
        await download_image(KEYED_URL, "street_view")


async def test_errors_never_include_the_url_or_key(respond):
    def handler(request):
        raise httpx.ConnectError(f"connection failed for {request.url}", request=request)

    respond(handler)

    with pytest.raises(ImageDownloadError) as caught:
        await download_image(KEYED_URL, "street_view")

    assert "SECRET_TEST_KEY" not in str(caught.value)
    assert "googleapis" not in str(caught.value)
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__


async def test_http_error_status_message_has_no_key(respond):
    respond(lambda request: httpx.Response(403, content=b"denied"))

    with pytest.raises(ImageDownloadError) as caught:
        await download_image(KEYED_URL, "street_view")

    assert str(caught.value) == "street_view image download failed: HTTP 403"
