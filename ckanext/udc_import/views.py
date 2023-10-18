from flask import Blueprint
from flask.views import MethodView
from typing import Any, cast, Optional, Union, Dict

import ckan.plugins.toolkit as toolkit
import ckan.logic as logic
import ckan.model as model
import ckan.lib.helpers as core_helpers
import ckan.lib.base as base
import ckan.lib.navl.dictization_functions as dict_fns

from ckan.common import _, request, current_user
from ckan.types import Context, Response

tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params

udc_import = Blueprint(u'udc_import', __name__)


def get_blueprints():
    return [udc_import]


class ImportView(MethodView):

    def post(self):
        data = clean_dict(
            dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
        )
        data.update(clean_dict(
            dict_fns.unflatten(tuplize_dict(parse_params(request.files)))
        ))

        context = cast(Context, {
            'model': model,
            'session': model.Session,
            'user': current_user.name,
            'auth_user_obj': current_user
        })
        result = []
        try:
            result = toolkit.get_action(u'udc_import_submit')(context, data)
        except logic.NotAuthorized:
            base.abort(403, _(u'Not authorized to see this page'))
        except logic.ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(errors, error_summary)
        
        side_panel_text = model.system_info.get_system_info(
            "ckanext.udc_import.side_panel_text")
        
        return base.render(
            u'udc_import/import_status.html',
            extra_vars={"result": '\n'.join(result), "side_panel_text": side_panel_text}
        )

    def get(self, 
            errors: Optional[Dict[str, Any]] = None,
            error_summary: Optional[Dict[str, Any]] = None):
        try:
            # Check permission
            toolkit.get_action(u'udc_import_check_permission')()
        except logic.NotAuthorized:
            base.abort(403, _(u'Not authorized to see this page'))

        side_panel_text = model.system_info.get_system_info(
            "ckanext.udc_import.side_panel_text")

        return base.render(
            u'udc_import/import_view.html',
            extra_vars={'errors': errors, 'error_summary': error_summary, "side_panel_text": side_panel_text}
        )


udc_import.add_url_rule(
    '/udc/import',
    view_func=ImportView.as_view('submit')
)
