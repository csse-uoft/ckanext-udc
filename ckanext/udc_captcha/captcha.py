"""Backend captcha generation and validation helpers."""
from __future__ import annotations

import base64
import random
from dataclasses import dataclass
from html import escape
from typing import Any

from itsdangerous import BadSignature, BadTimeSignature, URLSafeTimedSerializer

import ckan.plugins.toolkit as tk


class CaptchaError(Exception):
    """Base captcha error."""


class CaptchaExpiredError(CaptchaError):
    """Captcha token is expired."""


class CaptchaInvalidError(CaptchaError):
    """Captcha token or answer is invalid."""


class EmailVerificationError(Exception):
    """Base email verification error."""


class EmailVerificationExpiredError(EmailVerificationError):
    """Verification token is expired."""


class EmailVerificationInvalidError(EmailVerificationError):
    """Verification token is invalid."""


@dataclass
class CaptchaPayload:
    token: str
    image_data_uri: str


def generate_captcha(code_length: int = 5) -> CaptchaPayload:
    """Generate a signed captcha token and an SVG data URI."""
    code = _generate_code(code_length)
    token = _serializer().dumps({"answer": code.lower()})
    svg = _render_svg(code)
    image_data_uri = "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return CaptchaPayload(token=token, image_data_uri=image_data_uri)


def validate_captcha(token: str, answer: str, ttl_seconds: int = 300) -> None:
    """Validate captcha token and answer."""
    if not token:
        raise CaptchaInvalidError("Missing captcha token.")
    if not answer:
        raise CaptchaInvalidError("Missing captcha answer.")

    try:
        payload: dict[str, Any] = _serializer().loads(token, max_age=ttl_seconds)
    except BadTimeSignature as exc:
        raise CaptchaExpiredError("Captcha has expired.") from exc
    except BadSignature as exc:
        raise CaptchaInvalidError("Invalid captcha token.") from exc

    expected = str(payload.get("answer", "")).strip().lower()
    actual = answer.strip().lower()
    if not expected or actual != expected:
        raise CaptchaInvalidError("Incorrect verification code.")


def generate_email_verification_token(user_id: str, email: str) -> str:
    """Generate a signed token for account email verification."""
    payload = {"user_id": user_id, "email": (email or "").strip().lower()}
    return _email_serializer().dumps(payload)


def validate_email_verification_token(token: str, ttl_seconds: int = 172800) -> dict[str, Any]:
    """Validate email verification token and return payload."""
    if not token:
        raise EmailVerificationInvalidError("Missing verification token.")
    try:
        payload: dict[str, Any] = _email_serializer().loads(token, max_age=ttl_seconds)
    except BadTimeSignature as exc:
        raise EmailVerificationExpiredError("Verification token has expired.") from exc
    except BadSignature as exc:
        raise EmailVerificationInvalidError("Invalid verification token.") from exc

    user_id = str(payload.get("user_id", "")).strip()
    if not user_id:
        raise EmailVerificationInvalidError("Verification token has no user ID.")
    return payload


def _serializer() -> URLSafeTimedSerializer:
    secret = (
        tk.config.get("ckanext.udc_captcha.secret")
        or tk.config.get("beaker.session.secret")
        or tk.config.get("app_instance_uuid")
        or "udc-captcha-fallback-secret"
    )
    return URLSafeTimedSerializer(secret_key=secret, salt="ckanext.udc_captcha")


def _email_serializer() -> URLSafeTimedSerializer:
    secret = (
        tk.config.get("ckanext.udc_captcha.secret")
        or tk.config.get("beaker.session.secret")
        or tk.config.get("app_instance_uuid")
        or "udc-captcha-fallback-secret"
    )
    return URLSafeTimedSerializer(secret_key=secret, salt="ckanext.udc_captcha.email_verification")


def _generate_code(code_length: int) -> str:
    length = max(4, min(8, int(code_length)))
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(random.choice(alphabet) for _ in range(length))


def _render_svg(code: str) -> str:
    width = 180
    height = 56
    escaped = escape(code)

    noise = []
    for _ in range(8):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        stroke = random.choice(["#d1d5db", "#cbd5e1", "#e2e8f0", "#c7d2fe"])
        noise.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="1"/>'
        )

    chars = []
    base_x = 18
    step = 28
    for idx, ch in enumerate(escaped):
        x = base_x + idx * step + random.randint(-2, 2)
        y = 36 + random.randint(-3, 3)
        rot = random.randint(-18, 18)
        fill = random.choice(["#0f172a", "#1e293b", "#111827"])
        chars.append(
            f'<text x="{x}" y="{y}" fill="{fill}" font-family="monospace" '
            f'font-size="28" font-weight="700" transform="rotate({rot} {x} {y})">{ch}</text>'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
        '<rect width="100%" height="100%" rx="6" ry="6" fill="#f8fafc" stroke="#cbd5e1"/>'
        + "".join(noise)
        + "".join(chars)
        + "</svg>"
    )
