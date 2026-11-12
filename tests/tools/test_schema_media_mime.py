"""local_image() MIME mapping must not depend on Python version mimetypes tables."""

import base64
from pathlib import Path

from tools.schema_media import local_image


def _write(tmp_path: Path, name: str, payload: bytes = b"media") -> Path:
    path = tmp_path / name
    path.write_bytes(payload)
    return path


def _prefix(path: Path) -> str:
    data_url = local_image(path)
    assert data_url.startswith("data:")
    assert ";base64," in data_url
    encoded = data_url.split(";base64,", 1)[1]
    assert base64.b64decode(encoded) == path.read_bytes()
    return data_url.split(";base64,", 1)[0]


def test_local_image_webp_mime(tmp_path):
    path = _write(tmp_path, "frame.webp")
    assert _prefix(path) == "data:image/webp"


def test_local_image_avif_mime(tmp_path):
    path = _write(tmp_path, "frame.avif")
    assert _prefix(path) == "data:image/avif"


def test_local_image_png_mime(tmp_path):
    path = _write(tmp_path, "frame.png")
    assert _prefix(path) == "data:image/png"


def test_local_image_jpeg_mime(tmp_path):
    path = _write(tmp_path, "frame.jpeg")
    assert _prefix(path) == "data:image/jpeg"


def test_local_image_jpg_mime(tmp_path):
    path = _write(tmp_path, "frame.jpg")
    assert _prefix(path) == "data:image/jpeg"


def test_local_image_unknown_extension_falls_back_to_png(tmp_path):
    path = _write(tmp_path, "frame.unknown")
    assert _prefix(path) == "data:image/png"


def test_local_image_uppercase_webp_mime(tmp_path):
    path = _write(tmp_path, "frame.WEBP")
    assert _prefix(path) == "data:image/webp"
