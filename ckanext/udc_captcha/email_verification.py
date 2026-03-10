"""Email verification helpers."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

import ckan.model as model
import ckan.plugins.toolkit as tk
from ckan.lib.mailer import mail_user

from .captcha import generate_email_verification_token
from .config_utils import get_int

log = logging.getLogger(__name__)

_PLUGIN_EXTRAS_NAMESPACE = "udc_captcha"
_LAST_SENT_TS_KEY = "verification_last_sent_ts"


def get_resend_cooldown_seconds() -> int:
    return get_int("ckanext.udc_captcha.resend_cooldown_seconds", 60, min_value=0)


def find_user_by_login_identifier(identifier: str) -> Optional[model.User]:
    """Find a user by username or email (case-insensitive for email)."""
    value = (identifier or "").strip()
    if not value:
        return None

    user = model.User.by_name(value)
    if user:
        return user

    return model.Session.query(model.User).filter(model.User.email.ilike(value)).first()


def build_verify_url(token: str) -> str:
    verify_path = "/udc-captcha/verify-email?" + urlencode({"token": token})
    site_url = (tk.config.get("ckan.site_url") or "").rstrip("/")
    if site_url:
        return f"{site_url}{verify_path}"
    return verify_path


def mark_user_pending_and_send_verification(user: model.User) -> bool:
    """Set user to pending and send verification email."""
    changed = False
    if not user.is_pending():
        user.set_pending()
        changed = True

    sent = _send_verification_email(user)
    if sent:
        _set_last_sent_ts(user, _now_ts())
        changed = True

    if changed:
        model.Session.add(user)
        model.Session.commit()
    return sent


def resend_verification_email(user: model.User) -> tuple[bool, str]:
    """
    Resend verification email with cooldown.

    Returns:
      (success, message)
    """
    if not user.is_pending():
        return False, "Account is already verified."

    remaining = get_resend_cooldown_remaining_seconds(user)
    if remaining > 0:
        return False, f"Please wait {remaining} seconds before resending."

    sent = _send_verification_email(user)
    if not sent:
        return False, "Failed to send verification email. Please try again later."

    _set_last_sent_ts(user, _now_ts())
    model.Session.add(user)
    model.Session.commit()
    return True, "Verification email sent."


def get_resend_cooldown_remaining_seconds(user: model.User, now_ts: Optional[int] = None) -> int:
    if now_ts is None:
        now_ts = _now_ts()

    last_sent = _get_last_sent_ts(user)
    if last_sent is None:
        return 0

    cooldown = get_resend_cooldown_seconds()
    remaining = cooldown - (now_ts - last_sent)
    return max(0, remaining)


def _send_verification_email(user: model.User) -> bool:
    if not user.email:
        return False

    token = generate_email_verification_token(user.id, user.email)
    verify_url = build_verify_url(token)
    subject = tk._("Verify your email address")
    body = (
        "Hi {name},\n\n"
        "Please verify your email address by opening this link:\n"
        "{url}\n\n"
        "If you did not register, you can ignore this email.\n"
    ).format(name=user.display_name or user.name, url=verify_url)
    body_html = (
        "<p>Hi {name},</p>"
        "<p>Please verify your email address by opening this link:</p>"
        '<p><a href="{url}">{url}</a></p>'
        "<p>If you did not register, you can ignore this email.</p>"
    ).format(name=user.display_name or user.name, url=verify_url)

    try:
        mail_user(user, subject, body, body_html)
        return True
    except Exception:
        log.exception("Failed to send verification email to user id=%s", user.id)
        return False


def _get_last_sent_ts(user: model.User) -> Optional[int]:
    extras = user.plugin_extras or {}
    namespace = extras.get(_PLUGIN_EXTRAS_NAMESPACE, {})
    if not isinstance(namespace, dict):
        return None
    value = namespace.get(_LAST_SENT_TS_KEY)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _set_last_sent_ts(user: model.User, ts: int) -> None:
    extras = dict(user.plugin_extras or {})
    namespace = dict(extras.get(_PLUGIN_EXTRAS_NAMESPACE) or {})
    namespace[_LAST_SENT_TS_KEY] = int(ts)
    extras[_PLUGIN_EXTRAS_NAMESPACE] = namespace
    user.plugin_extras = extras


def _now_ts() -> int:
    return int(datetime.now(tz=timezone.utc).timestamp())
