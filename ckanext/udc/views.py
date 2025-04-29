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


def _get_search_details() -> dict[str, Any]:
    fq = u''

    # fields_grouped will contain a dict of params containing
    # a list of values eg {u'tags':[u'tag1', u'tag2']}

    fields = []
    fields_grouped = {}
    filter_logics = {}
    include_undefined = []
    search_extras: 'MultiDict[str, Any]' = MultiDict()
    
    # Get the list of text fields from the udc plugin
    # Only the text fields support full text search
    text_fields = plugins.get_plugin('udc').text_fields
    
    # Get the list of date fields from the udc plugin
    date_fields = plugins.get_plugin('udc').date_fields
    
    # Solr type = text_general/text
    # FTS only
    # TODO: If exact match is needed, we need to alter the ckan solr schema
    ckan_fields_fts = ["title", "notes", "url", "version", 
                   "author", "author_email", "maintainer", "maintainer_email"]
    
    # Solr type = string
    # FTS + exact
    # For FTS match, we need to add suffix `_ngram` to the field name (ckan solr schema is altered to support this)
    ckan_fields_exact = ["tags", "organization", "license_id"]

    for (param, value) in request.args.items(multi=True):
        # Ignore internal parameters
        if param not in [u'q', u'page', u'sort'] and len(value) and not param.startswith(u'_'):
            print(chalk.green(f"Param: {param}, Value: {value}"))
            
            if param.startswith('filter-logic-'):
                if value.lower() == 'and':
                    filter_logics[param[13:]] = 'AND'
                elif value == 'date':
                    # Date filter logic, include undefined date
                    include_undefined.append('extras_' + param[13:])
                elif value == 'number':
                    # Number filter logic, include undefined number
                    include_undefined.append('extras_' + param[13:])
                    
            elif param.startswith('fts_'):
                field_name = param[4:]
                # For text fields, we need to add `extras_` prefix to make solr do full text search
                # Text fields (in the maturity model) and CKAN Fields are the only fields that support full text search
                # CKAN Fields does not need to add `extras_` prefix except for `tags`
                if field_name in text_fields:
                    field_name = "extras_" + field_name
                if field_name in ckan_fields_exact:
                    field_name = field_name + "_ngram"
                    
                if field_name not in fields_grouped:
                    fields_grouped[field_name] = {
                        'values': [value],
                        'fts': True,
                    }
                else:
                    fields_grouped[field_name]['values'].append(value)
            elif param.startswith('exact_'):
                field_name = param[6:]
                # For exact matches, we do not add `extras_` prefix for CKAN fields and text fields
                # For all other fields, we need to add `extras_` prefix to make solr do exact search
                if field_name in ckan_fields_fts:
                    # Exaxt match is not available for FTS fields
                    print(chalk.red(f"Exact match is not available for FTS fields: {field_name}"))
                    continue
                if not (field_name in text_fields or field_name in ckan_fields_fts or field_name in ckan_fields_exact):
                    field_name = "extras_" + field_name
                    
                if field_name not in fields_grouped:
                    fields_grouped[field_name] = {
                        'values': [value],
                        'fts': False
                    }
                else:
                    fields_grouped[field_name]['values'].append(value)
            elif param.startswith('min_'):
                field_name = "extras_" + param[4:]
                if field_name not in fields_grouped:
                    fields_grouped[field_name] = {
                        'min': value,
                    }
                else:
                    fields_grouped[field_name]['min'] = value
            elif param.startswith('max_'):
                field_name = "extras_" + param[4:]
                if field_name not in fields_grouped:
                    fields_grouped[field_name] = {
                        'max': value,
                    }
                else:
                    fields_grouped[field_name]['max'] = value
                
            elif not param.startswith(u'ext_'):
                # Not sure what is this for
                fields.append((param, value))
                # fq += u' %s:"%s"' % (param, value)
                if param not in fields_grouped:
                    fields_grouped[param] = {
                        'values': [value],
                        'fts': False
                    }
                else:
                    fields_grouped[param]['values'].append(value)
            else:
                search_extras.update({param: value})

    extras = dict([
        (k, v[0]) if len(v) == 1 else (k, v)
        for k, v in search_extras.lists()
    ])
    
    # Build fq from fields_grouped
    for key, options in fields_grouped.items():
        
        if 'values' in options:
            values = options['values']
            filter_logic = filter_logics.get(key, 'OR')
            if len(values) > 1:
                fq += u' %s:(%s)' % (key, f' {filter_logic} '.join([f'"{v}"' for v in values]))
            else:
                fq += u' %s:"%s"' % (key, values[0])
        else:
            min = options.get('min')
            max = options.get('max')
            if key.startswith("extras") and key[7:] in date_fields:
                try:
                    # Convert date to UTC ISO format
                    if min:
                        min = datetime.strptime(min, '%Y-%m-%d').strftime('%Y-%m-%dT%H:%M:%SZ')
                    if max:
                        maxDate = datetime.strptime(max, '%Y-%m-%d')
                        # Add 23:59:59 to the max date to include the whole day
                        max = maxDate.replace(hour=23, minute=59, second=59).strftime('%Y-%m-%dT%H:%M:%SZ')
                except ValueError:
                    # If the date is not in the correct format, skip it
                    continue
            
            # Handle min and max values for number and date ranges
            range_query = ""
            if min and max:
                range_query = u' %s:[%s TO %s]' % (key, min, max)
            elif min:
                range_query = u' %s:[%s TO *]' % (key, min)
            elif max:
                range_query = u' %s:[* TO %s]' % (key, max)
                
            # Handle undefined date and number ranges
            if (key in include_undefined) and range_query:
                range_query = f'({range_query} OR (*:* -{key}:[* TO *]))'
            fq += range_query
    
    return {
        u'fields': fields,
        u'fields_grouped': fields_grouped,
        u'fq': fq,
        u'search_extras': extras,
        'filter_logics': filter_logics
    }



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
    data_dict: dict[str, Any] = {
        u'q': q,
        u'fq': fq.strip(),
        u'facet.field': facet_fields,
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
        extra_vars[u'search_facets'] = query[u'search_facets']
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
