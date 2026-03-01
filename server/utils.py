import base64
import binascii
import uuid
from urllib.parse import urlparse

from fastapi import HTTPException

from server.config import SCREENSHOT_DIR


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme:
        url = f"https://{url}"
        parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Invalid URL. Provide a valid http/https URL.")
    return url


def save_screenshot_base64(image_b64: str) -> str:
    try:
        image_bytes = base64.b64decode(image_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Invalid screenshot base64 payload.") from exc

    filename = f"{uuid.uuid4().hex}.png"
    file_path = SCREENSHOT_DIR / filename
    file_path.write_bytes(image_bytes)
    return f"/screenshots/{filename}"
