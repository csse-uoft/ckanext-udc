from ckan.types import Schema, Context, CKANApp, Response
from ckan.common import current_user, CKANConfig
from werkzeug.exceptions import (
    default_exceptions,
    HTTPException,
    Unauthorized,
    Forbidden,
)
from typing import Any, Callable, Collection, KeysView, Optional, Union, cast
import ckan.lib.base as base
import sys
import logging
import chalk
import ckan.lib.helpers as h
import pprint
from flask import session

log = logging.getLogger(__name__)


MESSAGE_NOT_LOGGED_IN_ADD_TO_CATALOGUE = """
You are not authorized to add to the catalogue. Please login to add a catalogue entry. If you do not have an account, please <a href="/user/register">create one</a>.
"""
MESSAGE_NOT_LOGGED_IN_CREATE_ORGANIZATION = """
You are not authorized to create an organization. Please login to create an organization. If you do not have an account, please <a href="/user/register">create one</a>.
"""


def override_error_handler(app: CKANApp, config: CKANConfig):

    @app.errorhandler(Forbidden)
    def handle_forbidden(e) -> Union[tuple[str, Optional[int]], Optional[Response]]:
        log.info(chalk.red(str(e)))
        log.info(pprint.pformat(e.__dict__))

        # Custom error handler for dataset creation "Unauthorized to create a package"
        if e.description == "Unauthorized to create a package":
            if current_user.is_anonymous:
                # Remove the error flash message
                session["_flashes"].clear()
                # Add a custom error message and type to the redirect
                h.flash(MESSAGE_NOT_LOGGED_IN_ADD_TO_CATALOGUE, "alert-warning")

                return h.redirect_to(
                    controller="user", action="login", next="/catalogue/new"
                )
            else:
                # Remove the error flash message
                session["_flashes"].clear()
                return h.redirect_to("/udc-react/request-organization-access/redirected")
        
        elif e.description == "Unauthorized to create a group":
            # Remove the error flash message
            session["_flashes"].clear()
            # Add a custom error message and type to the redirect
            h.flash(MESSAGE_NOT_LOGGED_IN_CREATE_ORGANIZATION, "alert-warning")

            return h.redirect_to(
                controller="user", action="login", next="/organization/new"
            )

        # Default CKAN error handler below
        debug = config.get("debug")
        if isinstance(e, HTTPException):
            if debug:
                log.debug(e, exc_info=sys.exc_info)  # type: ignore
            else:
                log.info(e)

            show_login_redirect_link = current_user.is_anonymous and type(e) in (
                Unauthorized,
                Forbidden,
            )
            extra_vars = {
                "code": e.code,
                "content": e.description,
                "name": e.name,
                "show_login_redirect_link": show_login_redirect_link,
            }
            return base.render("error_document_template.html", extra_vars), e.code

        log.error(e, exc_info=sys.exc_info)  # type: ignore
        extra_vars = {"code": [500], "content": "Internal server error"}
        return base.render("error_document_template.html", extra_vars), 500
