from __future__ import annotations

from flask import request, Response, abort
import ckan.lib
import ckan.lib.base as base
from ckan.lib.helpers import url_for
import ckan.lib.helpers
import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
from ckan.common import CKANConfig
from ckan.config.middleware.flask_app import CKANApp, CKANFlask
import logging
import os
import json
from pathlib import Path
import requests
from .constants import UDC_REACT_PATH

from ckanext.udc_react.actions import get_maturity_levels, get_ws_token, get_organizations_and_admins
from ckanext.udc_react.socketio import initSocketIO

log = logging.getLogger(__name__)


class UdcReactPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.IMiddleware)
    # plugins.implements(plugins.IBlueprint)

    # IConfigurable
    def configure(self, config: CKANConfig):
        self.project_path = Path(os.path.dirname(os.path.abspath(__file__)))
        self.load_vars(config)
        self.load_react(self.is_production)

    def load_vars(self, config):
        # Get environment variables.
        is_ckan_debug = config["debug"]
        self.VITE_ORIGIN = os.getenv("VITE_ORIGIN", "http://localhost:5173")
        is_gunicorn = "gunicorn" in os.environ.get("SERVER_SOFTWARE", "")
        self.is_production = not is_ckan_debug or is_gunicorn

    # IMiddleware
    def make_middleware(self, app: CKANApp, config: CKANConfig) -> CKANApp:
        # In Development mode, redirect calls to vite
        if not self.is_production:

            def download_file(streamable):
                with streamable as stream:
                    stream.raise_for_status()
                    for chunk in stream.iter_content(chunk_size=8192):
                        yield chunk

            @app.route(f"/{UDC_REACT_PATH}", defaults={"path": ""})
            @app.route(f"/{UDC_REACT_PATH}/<path:path>")
            def catch_udc_react_request(path):
                # React routes
                react_paths = [
                    "",
                    "import",
                    "import-status",
                    "qa",
                    "realtime-status"
                ]
                react_path_start_with = ["maturity-levels", "chatgpt-summary", "tutorial", "dashboard", "faq", "request-organization-access"]
                if path in react_paths or any([path.startswith(p) for p in react_path_start_with]):

                    def dev_asset(file_path):
                        return f"{self.VITE_ORIGIN}/{UDC_REACT_PATH}/{file_path}"

                    return base.render(
                        "udc_react/homepage.html",
                        extra_vars={
                            "react_asset": dev_asset,
                            "VITE_ORIGIN": self.VITE_ORIGIN,
                            "manifest": self.manifest,
                            "is_production": False,
                        },
                    )
                else:
                    # Other Files in the DEV server
                    forward_url = f"{self.VITE_ORIGIN}/{UDC_REACT_PATH}/{path}"

                    log.debug(f"Getting {forward_url}")
                    resp = requests.request(
                        method=request.method,
                        url=forward_url,
                        headers={
                            key: value
                            for (key, value) in request.headers
                            if key != "Host"
                        },
                        data=request.get_data(),
                        cookies=request.cookies,
                        allow_redirects=False,
                        stream=True,
                    )

                    excluded_headers = [
                        "content-encoding",
                        "content-length",
                        "transfer-encoding",
                        "connection",
                    ]
                    headers = [
                        (name, value)
                        for (name, value) in resp.raw.headers.items()
                        if name.lower() not in excluded_headers
                    ]

                    return Response(download_file(resp), resp.status_code, headers)

        else:
            # Production build
            @app.before_request
            def before_request_func():
                if request.path.startswith(f"/{UDC_REACT_PATH}"):
                    path = request.path[len(f"/{UDC_REACT_PATH}"):]
                    print("request.path", request.path, path)
                    
                    # If the path does not exist, go to index.html
                    if request.path != "" and not os.path.exists(
                        str(self.project_path / 'public' / UDC_REACT_PATH)  + path
                    ):
                        base_url = url_for("/")

                        def prod_asset(file_path):
                            try:
                                return f"{base_url}{UDC_REACT_PATH}/{self.manifest[file_path]['file']}"
                            except Exception as e:
                                print(repr(e))
                                return "asset-not-found"

                        return base.render(
                            "udc_react/homepage.html",
                            extra_vars={
                                "react_asset": prod_asset,
                                "VITE_ORIGIN": self.VITE_ORIGIN,
                                "manifest": self.manifest,
                                "is_production": True,
                            },
                        )
                    
        # Socket.io
        initSocketIO(app)

        return app

    def make_error_log_middleware(self, app: CKANFlask, config: CKANConfig) -> CKANApp:
        return app

    # IConfigurer
    def update_config(self, config_):
        tk.add_template_directory(config_, "templates")
        self.load_vars(config_)
        if not self.is_production:
            tk.add_public_directory(config_, "ckan-udc-react/public")
        else:
            tk.add_public_directory(config_, "public")
        tk.add_resource('assets', 'udc_react')

    def load_react(self, is_production: bool):

        # Load manifest file in the production environment.
        self.manifest = {}
        if self.is_production:
            manifest_path = (
                self.project_path / f"public/{UDC_REACT_PATH}/.vite/manifest.json"
            )
            try:
                with open(manifest_path, "r") as content:
                    self.manifest = json.load(content)
            except OSError as exception:
                raise OSError(
                    f"Manifest file not found at {manifest_path}. Run `npm run build`."
                ) from exception
        log.info(
            f"udc-react started in {'production' if self.is_production else 'development'} mode."
        )
        
    def update_config_schema(self, schema):
        ignore_missing = tk.get_validator('ignore_missing')
        unicode_safe = tk.get_validator('unicode_safe')
        
        schema.update({
            'ckanext.udc_react.qa_maturity_levels': [ignore_missing, unicode_safe]
        })
        return schema

    def get_actions(self):
        return {
            'get_maturity_levels': get_maturity_levels,
            'get_ws_token': get_ws_token,
            'get_organizations_and_admins': get_organizations_and_admins,
        }
