from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
from typing import Any, Iterable, Optional

import ckan.plugins as plugins
from ckan.common import request

from ckanext.udc.solr.config import get_current_lang


UDC_PARAM_PREFIX = "ext_udc_"
CKAN_FTS_FIELDS = [
    "title",
    "notes",
    "url",
    "version",
    "author",
    "author_email",
    "maintainer",
    "maintainer_email",
]
CORE_STRING_FACETS = ["organization", "groups", "license_id", "res_format"]


def _solr_field_for(
    param_kind: str,
    ui_field: str,
    lang: str,
    text_fields: set[str],
) -> Optional[str]:
    if ui_field in text_fields:
        if param_kind == "fts":
            return f"{ui_field}_{lang}_txt"
        if param_kind == "exact":
            return f"{ui_field}_{lang}_f"
        if param_kind in ("min", "max"):
            return f"extras_{ui_field}"

    if ui_field == "tags":
        if param_kind == "fts":
            return f"tags_{lang}_txt"
        if param_kind == "exact":
            return f"tags_{lang}_f"

    if ui_field in CKAN_FTS_FIELDS:
        if param_kind == "fts":
            return f"{ui_field}_{lang}_txt"
        return None

    if ui_field in CORE_STRING_FACETS:
        if param_kind == "exact":
            return ui_field
        return None

    if ui_field == "portal_type" and param_kind == "exact":
        return "extras_portal_type"

    if param_kind in ("min", "max", "exact", "fts"):
        return f"extras_{ui_field}"

    return None


def _decode_udc_param(param: str) -> tuple[Optional[str], Optional[str]]:
    if not param.startswith(UDC_PARAM_PREFIX):
        return None, None

    suffix = param[len(UDC_PARAM_PREFIX):]
    for kind in ("filter_logic", "exact", "fts", "min", "max"):
        prefix = f"{kind}_"
        if suffix.startswith(prefix):
            return kind, suffix[len(prefix):]

    return None, None


def _request_items() -> Iterable[tuple[str, str]]:
    try:
        return request.args.items(multi=True)
    except RuntimeError:
        return []


def get_search_details(
    params: Optional[Iterable[tuple[str, str]]] = None,
) -> dict[str, Any]:
    fq = ""
    fields: list[tuple[str, str]] = []
    fields_grouped: dict[str, Any] = {}
    filter_logics: dict[str, str] = {}
    include_undefined: set[str] = set()

    udc = plugins.get_plugin("udc")
    text_fields = set(udc.text_fields or [])
    date_fields = set(udc.date_fields or [])
    lang = get_current_lang()

    for param, value in params if params is not None else _request_items():
        if not value:
            continue

        kind, ui_name = _decode_udc_param(param)
        if not kind or not ui_name:
            continue

        if kind == "filter_logic":
            if value.lower() == "and":
                filter_logics[ui_name] = "AND"
            elif value in ("date", "number"):
                solr_key = _solr_field_for("min", ui_name, lang, text_fields)
                if solr_key:
                    include_undefined.add(solr_key)
            continue

        solr_kind = "exact" if kind == "exact" else kind
        solr_key = _solr_field_for(solr_kind, ui_name, lang, text_fields)
        if not solr_key:
            continue

        if kind in ("fts", "exact"):
            fields.append((param, value))
            group = fields_grouped.setdefault(
                solr_key,
                {"ui": ui_name, "fts": kind == "fts", "values": [], "params": []},
            )
            group["values"].append(value)
            group["params"].append(param)
            continue

        group = fields_grouped.setdefault(solr_key, {"ui": ui_name})
        group[kind] = value
        group[f"{kind}_param"] = param

    for solr_key, opts in fields_grouped.items():
        if "values" in opts:
            vals = opts["values"]
            ui_name = opts.get("ui", solr_key)
            logic_op = filter_logics.get(ui_name, "OR")
            if len(vals) > 1:
                joined = f" {logic_op} ".join([f'"{v}"' for v in vals])
                fq += f" {solr_key}:({joined})"
            else:
                fq += f' {solr_key}:"{vals[0]}"'
            continue

        min_value = opts.get("min")
        max_value = opts.get("max")
        ui_name = opts.get("ui")
        if ui_name and solr_key.startswith("extras_") and ui_name in date_fields:
            try:
                if min_value:
                    min_value = datetime.strptime(
                        min_value, "%Y-%m-%d"
                    ).strftime("%Y-%m-%dT%H:%M:%SZ")
                if max_value:
                    max_date = datetime.strptime(max_value, "%Y-%m-%d")
                    max_value = max_date.replace(
                        hour=23, minute=59, second=59
                    ).strftime("%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                continue

        if min_value and max_value:
            range_query = f" {solr_key}:[{min_value} TO {max_value}]"
        elif min_value:
            range_query = f" {solr_key}:[{min_value} TO *]"
        elif max_value:
            range_query = f" {solr_key}:[* TO {max_value}]"
        else:
            range_query = ""

        if range_query:
            if solr_key in include_undefined:
                range_query = f"({range_query} OR (*:* -{solr_key}:[* TO *]))"
            fq += range_query

    return {
        "fields": fields,
        "fields_grouped": fields_grouped,
        "filter_logics": filter_logics,
        "fq": fq,
    }


def facet_alias_map(facet_keys: Iterable[str], lang: Optional[str] = None):
    udc = plugins.get_plugin("udc")
    text_fields = set(udc.text_fields or [])
    lang = lang or get_current_lang()

    alias_to_solr: OrderedDict[str, str] = OrderedDict()
    for key in facet_keys:
        if key == "tags":
            alias_to_solr[key] = f"tags_{lang}_f"
        elif key == "portal_type":
            alias_to_solr[key] = "extras_portal_type"
        elif key == "version_dataset":
            alias_to_solr[key] = "version_dataset_url"
        elif key == "dataset_versions":
            alias_to_solr[key] = "dataset_versions_url"
        elif key.startswith("extras_"):
            alias_to_solr[key] = key
        elif key in text_fields:
            alias_to_solr[key] = f"{key}_{lang}_f"
        else:
            alias_to_solr[key] = key

    solr_fields = list(dict.fromkeys(alias_to_solr.values()))
    return solr_fields, alias_to_solr
