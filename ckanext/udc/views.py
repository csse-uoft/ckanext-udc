# -*- coding: utf-8 -*-
from __future__ import annotations
import logging

from datetime import datetime
from collections import OrderedDict
from functools import partial
from typing import Any, Iterable, Optional, Union, cast
from werkzeug.datastructures import MultiDict

from flask import Blueprint

import ckan.lib.base as base
from ckan.lib.helpers import helper_functions as h
from ckan.lib.helpers import Page
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.model as model
import ckan.plugins as plugins
import ckan.authz as authz
import ckan.plugins.toolkit as tk
import ckan.model as model

from ckan.lib.helpers import Page
from ckan.common import asbool, current_user, CKANConfig, request, g, config, _
from ckan.views.dataset import _sort_by, _pager_url, _setup_template_variables, _get_pkg_template
from ckan.lib.search import SearchQueryError, SearchError

from ckan.types import Context, Response

import chalk
import re
from urllib.parse import urlencode
from ckanext.udc.solr.config import get_current_lang

log = logging.getLogger(__name__)
bp = Blueprint("catalogue_search", __name__)



def remove_field(package_type: Optional[str],
                 key: str,
                 value: Optional[str] = None,
                 replace: Optional[str] = None):
    if not package_type:
        package_type = u'dataset'
    url = h.url_for(u'{0}.search'.format(package_type))
    
    if key.startswith('extras_'):
        # Remove the extras_ prefix
        key = key[7:]
    elif key.endswith('_ngram'):
        # Remove the _ngram suffix
        key = key[:-6]

    params_items = request.args.items(multi=True)
    params_nopage = [
        (k, v) for k, v in params_items
        if k != 'page'
    ]
    params = list(params_nopage)
    if value:
        # Assume `fts_` and `exact_` cannot be used together with the same value
        # print(chalk.red(f"Genererate remove link for Key: {key}, Value: {value}"))
        if (f"exact_{key}", value) in params:
            params.remove((f"exact_{key}", value))
        if (f"fts_{key}", value) in params:
            params.remove((f"fts_{key}", value))
        if (key, value) in params:
            params.remove((key, value))
            
    else:
        for (k, v) in params[:]:
            if k == key:
                if (f"exact_{key}", value) in params:
                    params.remove((f"exact_{key}", value))
                if (f"fts_{key}", value) in params:
                    params.remove((f"fts_{key}", value))
                if (k, v) in params:
                    params.remove((k, v))
                
    if replace is not None:
        params.append((key, replace))

    params = [(k, v.encode('utf-8') if isinstance(v, str) else str(v))
              for k, v in params]
    return url + u'?' + urlencode(params)


# Solr type = text_general/text
# FTS only
# TODO: If exact match is needed, we need to alter the ckan solr schema
CKAN_FTS_FIELDS = ["title", "notes", "url", "version",
                   "author", "author_email", "maintainer", "maintainer_email"]

# Core string facets: exact match; optional _ngram if you enable Option B
CORE_STRING_FACETS = ["organization", "license_id"]

def _solr_field_for(param_kind: str, ui_field: str, lang: str,
                    text_fields: set[str]) -> str | None:
    """
    Map stable UI field names to concrete Solr fields.
      param_kind: 'fts' | 'exact' | 'min' | 'max'
    """
    # Text maturity fields (multilingual)
    if ui_field in text_fields:
        if param_kind == 'fts':
            return f"{ui_field}_{lang}_txt"
        if param_kind == 'exact':
            return f"{ui_field}_{lang}_f"
        if param_kind in ('min', 'max'):
            return f"extras_{ui_field}"

    # Tags are multilingual too
    if ui_field == "tags":
        if param_kind == 'fts':
            return f"tags_{lang}_txt"
        if param_kind == 'exact':
            return f"tags_{lang}_f"

    # CKAN core text fields: fts only
    if ui_field in CKAN_FTS_FIELDS:
        if param_kind == 'fts':
            return f"{ui_field}_{lang}_txt"
        # ignore exact_ for these
        return None
    
    # Core string facets
    if ui_field in CORE_STRING_FACETS:
        if param_kind == 'exact':
            return ui_field
        # enable FTS via _ngram (Not supported in current schema)
        # if param_kind == 'fts': 
        #     return f"{ui_field}_ngram"

    # Everything else (selects / numbers / dates etc) use extras_*
    if param_kind in ('min', 'max'):
        return f"extras_{ui_field}"
    # exact match for non-text -> extras_*
    if param_kind == 'exact':
        return f"extras_{ui_field}"
    # fts on non-text: allow user-entered terms as exact values on extras_*
    if param_kind == 'fts':
        return f"extras_{ui_field}"

    return None

def _get_search_details() -> dict[str, Any]:
    fq = u''

    # fields_grouped will contain a dict of params containing
    # a list of values eg {u'tags':[u'tag1', u'tag2']}

    fields = []
    fields_grouped = {}      # key: solr_field -> { ui, values|min|max, fts:bool }
    filter_logics = {}       # key: ui_field -> 'AND' or 'OR'
    include_undefined = set()  # set of solr field names for date/number 'include empty'
    search_extras: 'MultiDict[str, Any]' = MultiDict()
    
    udc = plugins.get_plugin('udc')
    # Get the list of text fields from the udc plugin
    # Only the text fields support full text search
    text_fields = udc.text_fields

    # Get the list of date fields from the udc plugin
    date_fields = udc.date_fields
    
    lang = request.args.get('lang') or get_current_lang()

    
    # Solr type = string
    # FTS + exact
    # For FTS match, we need to add suffix `_ngram` to the field name (ckan solr schema is altered to support this)
    ckan_fields_exact = ["tags", "organization", "license_id"]

    for (param, value) in request.args.items(multi=True):
        # Ignore internal parameters
        if param not in [u'q', u'page', u'sort'] and len(value) and not param.startswith(u'_'):
            print(chalk.green(f"Param: {param}, Value: {value}"))
            
        # Toggle logic
        if param.startswith('filter-logic-'):
            ui_name = param[13:]
            if value.lower() == 'and':
                filter_logics[ui_name] = 'AND'
            elif value == 'date':
                # include undefined date
                solr_key = _solr_field_for('min', ui_name, lang, text_fields)  # same base field
                if solr_key:
                    include_undefined.add(solr_key)
            elif value == 'number':
                solr_key = _solr_field_for('min', ui_name, lang, text_fields)
                if solr_key:
                    include_undefined.add(solr_key)
            continue

        # fts_*
        if param.startswith('fts_'):
            ui_name = param[4:]
            solr_key = _solr_field_for('fts', ui_name, lang, text_fields)
            if not solr_key:
                continue
            fields_grouped.setdefault(solr_key, {'ui': ui_name, 'fts': True, 'values': []})
            fields_grouped[solr_key]['values'].append(value)
            continue

        # exact_*
        if param.startswith('exact_'):
            ui_name = param[6:]
            solr_key = _solr_field_for('exact', ui_name, lang, text_fields)
            if not solr_key:
                continue
            fields_grouped.setdefault(solr_key, {'ui': ui_name, 'fts': False, 'values': []})
            fields_grouped[solr_key]['values'].append(value)
            continue

        # min_/max_ (numbers/dates on extras_*)
        if param.startswith('min_'):
            ui_name = param[4:]
            solr_key = _solr_field_for('min', ui_name, lang, text_fields)
            if not solr_key:
                continue
            fields_grouped.setdefault(solr_key, {'ui': ui_name})
            fields_grouped[solr_key]['min'] = value
            continue

        if param.startswith('max_'):
            ui_name = param[4:]
            solr_key = _solr_field_for('max', ui_name, lang, text_fields)
            if not solr_key:
                continue
            fields_grouped.setdefault(solr_key, {'ui': ui_name})
            fields_grouped[solr_key]['max'] = value
            continue

        # legacy / unknown -> pass-through as extras
        if not param.startswith(u'ext_'):
            fields.append((param, value))
        else:
            search_extras.update({param: value})
            
    # Build fq
    from datetime import datetime
    for solr_key, opts in fields_grouped.items():
        # values group
        if 'values' in opts:
            vals = opts['values']
            ui_name = opts.get('ui', solr_key)
            logic_op = filter_logics.get(ui_name, 'OR')
            if len(vals) > 1:
                joined = f' {logic_op} '.join([f'"{v}"' for v in vals])
                fq += f' {solr_key}:({joined})'
            else:
                fq += f' {solr_key}:"{vals[0]}"'
            continue

        # range group (dates / numbers on extras_*)
        _min = opts.get('min')
        _max = opts.get('max')
        # Date normalization if the underlying UI field was a date field
        ui_name = opts.get('ui')
        if ui_name and solr_key.startswith("extras_") and ui_name in date_fields:
            try:
                # Convert date to UTC ISO format
                if _min:
                    _min = datetime.strptime(_min, '%Y-%m-%d').strftime('%Y-%m-%dT%H:%M:%SZ')
                if _max:
                    d = datetime.strptime(_max, '%Y-%m-%d')
                    # Add 23:59:59 to the max date to include the whole day
                    _max = d.replace(hour=23, minute=59, second=59).strftime('%Y-%m-%dT%H:%M:%SZ')
            except ValueError:
                # If the date is not in the correct format, skip it
                continue

        # Handle min and max values for number and date ranges
        if _min and _max:
            range_query = f' {solr_key}:[{_min} TO {_max}]'
        elif _min:
            range_query = f' {solr_key}:[{_min} TO *]'
        elif _max:
            range_query = f' {solr_key}:[* TO {_max}]'
        else:
            range_query = ""

        # Handle undefined date and number ranges
        if range_query:
            if solr_key in include_undefined:
                range_query = f'({range_query} OR (*:* -{solr_key}:[* TO *]))'
            fq += range_query

    extras = dict((k, v[0]) if len(v) == 1 else (k, v)
                  for k, v in search_extras.lists())

    return {
        u'fields': fields,
        u'fields_grouped': fields_grouped,
        u'fq': fq,
        u'search_extras': extras,
        'filter_logics': filter_logics
    }


def _facet_alias_map(facet_keys: list[str], lang: str) -> tuple[list[str], dict[str, str]]:
    """
    Given stable facet keys, return (solr_facet_fields, alias_to_solr_map).
    - text maturity fields in udc.text_fields -> <name>_<lang>_f
    - tags -> tags_<lang>_f
    - extras_* and other core facets -> as-is
    """
    udc = plugins.get_plugin('udc')
    text_fields = set(udc.text_fields or [])

    alias_to_solr = OrderedDict()
    for key in facet_keys:
        if key == "tags":
            alias_to_solr[key] = f"tags_{lang}_f"
        elif key.startswith("extras_"):
            alias_to_solr[key] = key
        elif key in text_fields:
            alias_to_solr[key] = f"{key}_{lang}_f"
        else:
            alias_to_solr[key] = key

    solr_fields = list(dict.fromkeys(alias_to_solr.values()))
    return solr_fields, alias_to_solr


@bp.route(
    "/catalogue",
    endpoint="search",
    strict_slashes=False
)
def custom_dataset_search():
    package_type = 'catalogue'
    extra_vars: dict[str, Any] = {}

    try:
        context = cast(Context, {
            u'model': model,
            u'user': current_user.name,
            u'auth_user_obj': current_user
        })
        logic.check_access(u'site_read', context)
    except logic.NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    # unicode format (decoded from utf8)
    extra_vars[u'q'] = q = request.args.get(u'q', u'')

    extra_vars['query_error'] = False
    page = h.get_page_number(request.args)

    limit = config.get(u'ckan.datasets_per_page')
    
    # print(chalk.green(f"Page: {page}, Limit: {limit}, Query: {q}, Package Type: {package_type}, Current User: {current_user.name}"))

    # most search operations should reset the page counter:
    params_nopage = [(k, v) for k, v in request.args.items(multi=True)
                     if k != u'page']

    # remove_field is a partial function that will remove a field from the search
    # results. It is used in the search results template to generate links that
    # remove a field from the search results.
    extra_vars[u'remove_field'] = partial(remove_field, package_type)
    
    # print("Remove field: ", extra_vars[u'remove_field'])

    sort_by = request.args.get(u'sort', None)
    params_nosort = [(k, v) for k, v in params_nopage if k != u'sort']

    extra_vars[u'sort_by'] = partial(_sort_by, params_nosort, package_type)
    # print("Sort by: ", sort_by)

    if not sort_by:
        sort_by_fields = []
    else:
        sort_by_fields = [field.split()[0] for field in sort_by.split(u',')]
    extra_vars[u'sort_by_fields'] = sort_by_fields

    pager_url = partial(_pager_url, params_nopage, package_type)

    details = _get_search_details()
    print(details)
    extra_vars[u'fields'] = details[u'fields']
    extra_vars[u'fields_grouped'] = details[u'fields_grouped']
    extra_vars[u'filter_logics'] = details[u'filter_logics']
    fq = details[u'fq']
    search_extras = details[u'search_extras']

    context = cast(Context, {
        u'model': model,
        u'session': model.Session,
        u'user': current_user.name,
        u'for_view': True,
        u'auth_user_obj': current_user
    })

    # Unless changed via config options, don't show other dataset
    # types any search page. Potential alternatives are do show them
    # on the default search page (dataset) or on one other search page
    search_all_type = config.get(u'ckan.search.show_all_types')
    search_all = False

    try:
        # If the "type" is set to True or False, convert to bool
        # and we know that no type was specified, so use traditional
        # behaviour of applying this only to dataset type
        search_all = asbool(search_all_type)
        search_all_type = u'dataset'
    # Otherwise we treat as a string representing a type
    except ValueError:
        search_all = True

    if not search_all or package_type != search_all_type:
        # Only show datasets of this particular type
        fq += u' +dataset_type:{type}'.format(type=package_type)

    facets: dict[str, str] = OrderedDict()

    org_label = h.humanize_entity_type(
        u'organization',
        h.default_group_type(u'organization'),
        u'facet label') or _(u'Organizations')

    group_label = h.humanize_entity_type(
        u'group',
        h.default_group_type(u'group'),
        u'facet label') or _(u'Groups')

    default_facet_titles = {
        u'organization': org_label,
        u'groups': group_label,
        u'tags': _(u'Tags'),
        u'res_format': _(u'Formats'),
        u'license_id': _(u'Licenses'),
    }

    for facet in h.facets():
        if facet in default_facet_titles:
            facets[facet] = default_facet_titles[facet]
        else:
            facets[facet] = facet

    # Facet titles
    for plugin in plugins.PluginImplementations(plugins.IFacets):
        facets = plugin.dataset_facets(facets, package_type)
    
    facet_fields = list(facets.keys())
    # # Remove date facet as it is not supported by solr
    # for date_field in h.date_fields:
    #     if date_field in facets:
    #         print("Removing date field: ", date_field)
    #         facet_fields.remove(date_field)
    #         facets.pop(date_field)
    # print("Facet Fields: ", facet_fields)

    extra_vars[u'facet_titles'] = facets
    # extra_vars[u'facet_titles'].update(plugins.get_plugin('udc').facet_titles)
    # print(chalk.yellow(f"Facet Titles: {extra_vars[u'facet_titles']}"))
    
    lang = request.args.get('lang') or get_current_lang()
    facet_fields_stable = list(facets.keys())
    solr_facet_fields, alias_to_solr = _facet_alias_map(facet_fields_stable, lang)

    data_dict: dict[str, Any] = {
        u'q': q,
        u'fq': fq.strip(),
        u'facet.field': solr_facet_fields,
        # u'facet.limit': -1,
        u'rows': limit,
        u'start': (page - 1) * limit,
        u'sort': sort_by,
        u'extras': search_extras,
        u'include_private': config.get(
            u'ckan.search.default_include_private'),
    }
    # print(chalk.green(f"Data Dict: {data_dict}"))
    try:
        query = logic.get_action(u'package_search')(context, data_dict)

        extra_vars[u'sort_by_selected'] = query[u'sort']

        extra_vars[u'page'] = Page(
            collection=query[u'results'],
            page=page,
            url=pager_url,
            item_count=query[u'count'],
            items_per_page=limit
        )
        # print(chalk.red("search_facets"), query[u'search_facets'])
        
        raw_facets = query.get('search_facets', {})
        search_facets_stable = {}
        for alias, solr_name in alias_to_solr.items():
            if solr_name in raw_facets:
                search_facets_stable[alias] = raw_facets[solr_name]

        extra_vars[u'search_facets'] = search_facets_stable
        # extra_vars[u'search_facets'] = query[u'search_facets']
        extra_vars[u'page'].items = query[u'results']
    except SearchQueryError as se:
        # User's search parameters are invalid, in such a way that is not
        # achievable with the web interface, so return a proper error to
        # discourage spiders which are the main cause of this.
        log.info(u'Dataset search query rejected: %r', se.args)
        base.abort(
            400,
            _(u'Invalid search query: {error_message}')
            .format(error_message=str(se))
        )
    except SearchError as se:
        # May be bad input from the user, but may also be more serious like
        # bad code causing a SOLR syntax error, or a problem connecting to
        # SOLR
        log.error(u'Dataset search error: %r', se.args)
        extra_vars[u'query_error'] = True
        extra_vars[u'search_facets'] = {}
        extra_vars[u'page'] = Page(collection=[])

    # FIXME: try to avoid using global variables
    g.search_facets_limits = {}
    default_limit: int = config.get(u'search.facets.default')
    for facet in cast(Iterable[str], extra_vars[u'search_facets'].keys()):
        try:
            limit = int(
                request.args.get(
                    u'_%s_limit' % facet,
                    default_limit
                )
            )
        except ValueError:
            base.abort(
                400,
                _(u'Parameter u"{parameter_name}" is not '
                  u'an integer').format(parameter_name=u'_%s_limit' % facet)
            )

        g.search_facets_limits[facet] = limit

    _setup_template_variables(context, {}, package_type=package_type)

    extra_vars[u'dataset_type'] = package_type

    # TODO: remove
    for key, value in extra_vars.items():
        setattr(g, key, value)

    # print(chalk.green(f"Extra Vars: {extra_vars}"))
    return base.render('package/custom_search.html', extra_vars)


@bp.route(
    "/dataset",
    endpoint="redirect-search",
    strict_slashes=False
)
def redirect_to_catalogue_search():
    # Redirect to the catalogue search page
    new_url = re.sub(r'(/[\w-]*)?/dataset', r'\1/catalogue', request.url)
    return tk.redirect_to(new_url)
