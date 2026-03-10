"""CKAN plugin: backend-generated captcha for user registration."""
from __future__ import annotations

from typing import Any, Callable

import ckan.model as model
import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
from ckan.common import CKANConfig
from flask import has_request_context, session

from .captcha import (
    CaptchaExpiredError,
    CaptchaInvalidError,
    generate_captcha,
    validate_captcha,
)
from .config_utils import get_bool, get_int
from .email_verification import (
    get_resend_cooldown_seconds,
    mark_user_pending_and_send_verification,
)
from .views import get_blueprints


@tk.chained_action
def user_create(original_action: Callable[..., Any], context: dict[str, Any], data_dict: dict[str, Any]):
    """Validate captcha for public registration requests."""
    clean_data = dict(data_dict)
    token = (clean_data.get("captcha_token") or "").strip()
    answer = (clean_data.get("captcha_answer") or "").strip()

    # Remove captcha fields before passing to the original user schema/action.
    clean_data.pop("captcha_token", None)
    clean_data.pop("captcha_answer", None)

    if _captcha_required(context):
        ttl_seconds = get_int("ckanext.udc_captcha.ttl_seconds", 300, min_value=1)
        try:
            validate_captcha(token=token, answer=answer, ttl_seconds=ttl_seconds)
        except CaptchaExpiredError as exc:
            raise tk.ValidationError(
                {
                    "captcha_answer": ["Verification code expired. Please refresh and try again."],
                    "captcha_token": [str(exc)],
                }
            )
        except CaptchaInvalidError as exc:
            raise tk.ValidationError(
                {
                    "captcha_answer": ["Incorrect verification code."],
                    "captcha_token": [str(exc)],
                }
            )

    user_dict = original_action(context, clean_data)

    if _email_verification_required(context):
        _mark_user_pending_and_send_verification(user_dict)

    return user_dict


def udc_captcha_generate():
    """Template helper: generate captcha token + image data URI."""
    payload = generate_captcha()
    return {"token": payload.token, "image_data_uri": payload.image_data_uri}


def udc_email_verification_enabled() -> bool:
    """Template helper: whether registration email verification is enabled."""
    return get_bool("ckanext.udc_captcha.email_verification_enabled", True)


def udc_email_verification_resend_cooldown_seconds() -> int:
    """Template helper: resend cooldown in seconds."""
    return get_resend_cooldown_seconds()


def _captcha_required(context: dict[str, Any]) -> bool:
    if not get_bool("ckanext.udc_captcha.enabled", True):
        return False
    return _is_public_registration(context)


def _is_public_registration(context: dict[str, Any]) -> bool:
    if context.get("ignore_auth"):
        return False

    auth_user_obj = context.get("auth_user_obj")
    if auth_user_obj and getattr(auth_user_obj, "sysadmin", False):
        return False

    user_name = context.get("user")
    if user_name:
        user_obj = model.User.get(user_name)
        if user_obj and user_obj.sysadmin:
            return False

    return True


def _email_verification_required(context: dict[str, Any]) -> bool:
    if not get_bool("ckanext.udc_captcha.email_verification_enabled", True):
        return False
    return _is_public_registration(context)


def _mark_user_pending_and_send_verification(user_dict: dict[str, Any]) -> None:
    user_id = user_dict.get("id")
    if not user_id:
        return

    user_obj = model.User.get(user_id)
    if not user_obj or not user_obj.email:
        return

    mark_user_pending_and_send_verification(user_obj)
    _remember_pending_registration(user_obj)


def _remember_pending_registration(user_obj: model.User) -> None:
    if not has_request_context():
        return
    session["udc_captcha_pending_registration_email"] = user_obj.email


class UdcCaptchaPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IBlueprint)

    def configure(self, config_: CKANConfig) -> None:
        # Required by IConfigurable; no runtime initialization is needed yet.
        return None

    def update_config(self, config_: CKANConfig):
        tk.add_template_directory(config_, "templates")

    def update_config_schema(self, schema):
        ignore_missing = tk.get_validator("ignore_missing")
        boolean_validator = tk.get_validator("boolean_validator")
        int_validator = tk.get_validator("int_validator")

        schema.update(
            {
                "ckanext.udc_captcha.enabled": [ignore_missing, boolean_validator],
                "ckanext.udc_captcha.ttl_seconds": [ignore_missing, int_validator],
                "ckanext.udc_captcha.secret": [ignore_missing],
                "ckanext.udc_captcha.email_verification_enabled": [ignore_missing, boolean_validator],
                "ckanext.udc_captcha.email_verification_ttl_seconds": [ignore_missing, int_validator],
                "ckanext.udc_captcha.resend_cooldown_seconds": [ignore_missing, int_validator],
            }
        )
        return schema

    def get_actions(self):
        return {"user_create": user_create}

    def get_helpers(self):
        return {
            "udc_captcha_generate": udc_captcha_generate,
            "udc_email_verification_enabled": udc_email_verification_enabled,
            "udc_email_verification_resend_cooldown_seconds": udc_email_verification_resend_cooldown_seconds,
        }

    def get_blueprint(self):
        return get_blueprints()
