from __future__ import annotations

import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
import logging

log = logging.getLogger(__name__)


class UdcThemePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)

    def update_config(self, config_):
        tk.add_template_directory(config_, 'templates')
        tk.add_public_directory(config_, 'public')
        tk.add_resource('assets', 'udc_theme')
