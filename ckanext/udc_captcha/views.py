"""Blueprint routes for captcha refresh."""
from __future__ import annotations

import ckan.lib.base as base
import ckan.model as model
import ckan.plugins.toolkit as tk
from flask import Blueprint, jsonify, redirect, request, session

from .captcha import (
    CaptchaExpiredError,
    CaptchaInvalidError,
    EmailVerificationExpiredError,
    EmailVerificationInvalidError,
    generate_captcha,
    validate_captcha,
    validate_email_verification_token,
)
from .config_utils import get_bool, get_int
from .email_verification import (
    find_user_by_login_identifier,
    get_resend_cooldown_seconds,
    resend_verification_email,
)


bp = Blueprint("udc_captcha", __name__, url_prefix="/udc-captcha")


@bp.before_app_request
def redirect_pending_registration_to_login():
    if request.method != "GET":
        return None
    if request.path.rstrip("/") != "/user/me":
        return None

    email = session.pop("udc_captcha_pending_registration_email", None)
    if not email:
        return None

    tk.h.flash_success(
        tk._("Registration successful. Please check your email (%(email)s) and verify your account before logging in.", email=email)
    )
    return redirect(tk.h.url_for("user.login"))


@bp.before_app_request
def validate_login_captcha():
    if request.method != "POST":
        return None
    if request.path.rstrip("/") != "/user/login":
        return None
    if not (get_bool("ckanext.udc_captcha.enabled", True) and get_bool("ckanext.udc_captcha.login_enabled", True)):
        return None

    token = (request.form.get("captcha_token") or "").strip()
    answer = (request.form.get("captcha_answer") or "").strip()
    ttl_seconds = get_int(
        "ckanext.udc_captcha.login_ttl_seconds",
        get_int("ckanext.udc_captcha.ttl_seconds", 300, min_value=1),
        min_value=1,
    )
    try:
        validate_captcha(token=token, answer=answer, ttl_seconds=ttl_seconds)
    except CaptchaExpiredError:
        tk.h.flash_error(tk._("Verification code expired. Please refresh and try again."))
        return redirect(tk.h.url_for("user.login"))
    except CaptchaInvalidError:
        tk.h.flash_error(tk._("Incorrect verification code."))
        return redirect(tk.h.url_for("user.login"))

    return None


@bp.before_app_request
def redirect_pending_login_to_verification():
    if request.method != "POST":
        return None
    if request.path.rstrip("/") != "/user/login":
        return None
    if not get_bool("ckanext.udc_captcha.email_verification_enabled", True):
        return None

    login_identifier = (request.form.get("login") or "").strip()
    if not login_identifier:
        return None

    user = find_user_by_login_identifier(login_identifier)
    if not user or not user.is_pending():
        return None

    session["udc_captcha_pending_login_identifier"] = login_identifier
    return redirect(tk.h.url_for("udc_captcha.pending_verification"))


@bp.get("/new")
def new_captcha():
    payload = generate_captcha()
    return jsonify(
        {
            "success": True,
            "token": payload.token,
            "image_data_uri": payload.image_data_uri,
        }
    )


@bp.get("/verify-email")
def verify_email():
    token = (request.args.get("token") or "").strip()
    ttl_seconds = get_int("ckanext.udc_captcha.email_verification_ttl_seconds", 172800, min_value=1)
    login_url = tk.h.url_for("user.login")

    try:
        payload = validate_email_verification_token(token=token, ttl_seconds=ttl_seconds)
    except EmailVerificationExpiredError:
        tk.h.flash_error(tk._("Verification link has expired. Please register again."))
        return redirect(login_url)
    except EmailVerificationInvalidError:
        tk.h.flash_error(tk._("Invalid verification link."))
        return redirect(login_url)

    user = model.User.get(payload.get("user_id"))
    if not user:
        tk.h.flash_error(tk._("User not found for this verification link."))
        return redirect(login_url)

    token_email = str(payload.get("email", "")).strip().lower()
    user_email = (user.email or "").strip().lower()
    if token_email and user_email and token_email != user_email:
        tk.h.flash_error(tk._("Verification link does not match this account email."))
        return redirect(login_url)

    if user.is_pending():
        user.activate()
        model.Session.add(user)
        model.Session.commit()
        tk.h.flash_success(tk._("Email verified. You can now log in."))
    else:
        tk.h.flash_success(tk._("Email is already verified. You can log in."))

    return redirect(login_url)


@bp.get("/pending-verification")
def pending_verification():
    login_identifier = (
        request.args.get("login")
        or session.get("udc_captcha_pending_login_identifier")
        or ""
    ).strip()

    if not login_identifier:
        return redirect(tk.h.url_for("user.login"))

    return base.render(
        "user/pending_verification.html",
        extra_vars={
            "login_identifier": login_identifier,
            "resend_cooldown_seconds": get_resend_cooldown_seconds(),
        },
    )


@bp.get("/resend-verification")
def resend_verification():
    login_identifier = (request.args.get("login") or request.args.get("email") or "").strip()
    if not login_identifier:
        return jsonify({"success": False, "message": "Login identifier is required."}), 400

    user = find_user_by_login_identifier(login_identifier)
    if not user:
        # Avoid exposing whether an email is registered.
        return jsonify(
            {
                "success": True,
                "message": "If an unverified account exists for this email, a verification email has been sent.",
            }
        )

    if not user.is_pending():
        return jsonify({"success": True, "message": "This account is already verified."})

    ok, message = resend_verification_email(user)
    status_code = 200 if ok else 429
    return jsonify({"success": ok, "message": message}), status_code


def get_blueprints():
    return [bp]
