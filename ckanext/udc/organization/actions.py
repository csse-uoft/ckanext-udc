"""Organization management actions for UDC."""
from __future__ import annotations

from typing import Any

from sqlalchemy import or_

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.logic import NotFound
from ckan.types import Context
from ckanext.activity.model.activity import Activity


@tk.side_effect_free
def udc_organization_list(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    """List organizations with pagination and filters (sysadmin only)."""
    tk.check_access("udc_organization_list", context, data_dict)

    page = int(data_dict.get("page", 1) or 1)
    page_size = int(data_dict.get("page_size", 25) or 25)
    filters = data_dict.get("filters") or {}

    query = model.Session.query(model.Group).filter(model.Group.is_organization.is_(True))
    query = _apply_org_filters(query, filters)
    total = query.count()

    orgs = (
        query.order_by(model.Group.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "results": [_org_to_dict(org) for org in orgs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@tk.side_effect_free
def udc_deleted_organization_list(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    """List deleted organizations with pagination and filters (sysadmin only)."""
    tk.check_access("udc_deleted_organization_list", context, data_dict)

    page = int(data_dict.get("page", 1) or 1)
    page_size = int(data_dict.get("page_size", 25) or 25)
    filters = data_dict.get("filters") or {}
    filters = {**filters, "state": "deleted"}

    query = model.Session.query(model.Group).filter(model.Group.is_organization.is_(True))
    query = _apply_org_filters(query, filters)
    total = query.count()

    orgs = (
        query.order_by(model.Group.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "results": [_org_to_dict(org) for org in orgs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@tk.side_effect_free
def udc_organization_packages_list(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    """List packages for an organization with pagination and filters (sysadmin only)."""
    tk.check_access("udc_organization_packages_list", context, data_dict)

    org = _get_org(data_dict)
    page = int(data_dict.get("page", 1) or 1)
    page_size = int(data_dict.get("page_size", 25) or 25)
    filters = data_dict.get("filters") or {}

    query = model.Session.query(model.Package).filter(model.Package.owner_org == org.id)
    query = _apply_package_filters(query, filters)
    total = query.count()

    packages = (
        query.order_by(model.Package.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "organization": _org_to_dict(org),
        "results": [_package_to_dict(pkg) for pkg in packages],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@tk.side_effect_free
def udc_organization_packages_ids(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    """Return package ids for an organization (sysadmin only)."""
    tk.check_access("udc_organization_packages_ids", context, data_dict)

    org = _get_org(data_dict)
    filters = data_dict.get("filters") or {}

    query = model.Session.query(model.Package.id).filter(model.Package.owner_org == org.id)
    query = _apply_package_filters(query, filters)

    ids = [row[0] for row in query.all()]
    return {"organization": _org_to_dict(org), "ids": ids, "total": len(ids)}


def udc_organization_packages_delete(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    """Delete (soft-delete) packages for an organization (sysadmin only)."""
    tk.check_access("udc_organization_packages_delete", context, data_dict)

    org = _get_org(data_dict)
    package_ids = data_dict.get("ids") or []

    if not isinstance(package_ids, list):
        raise tk.ValidationError({"ids": ["Provide a list of package ids."]})
    if not package_ids:
        raise tk.ValidationError({"ids": ["No packages selected."]})

    errors: list[dict[str, str]] = []
    deleted = 0
    delete_action = tk.get_action("package_delete")

    for pkg_id in package_ids:
        try:
            delete_action(context, {"id": pkg_id})
            deleted += 1
        except Exception as exc:  # pragma: no cover - forward exact error to UI
            errors.append({"id": str(pkg_id), "error": str(exc)})

    return {"success": not errors, "deleted": deleted, "errors": errors}


def udc_organization_delete(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    """Soft-delete organizations (sysadmin only)."""
    tk.check_access("udc_organization_delete", context, data_dict)

    org_ids = data_dict.get("ids") or []
    if not isinstance(org_ids, list):
        raise tk.ValidationError({"ids": ["Provide a list of organization ids."]})
    if not org_ids:
        raise tk.ValidationError({"ids": ["No organizations selected."]})

    errors: list[dict[str, str]] = []
    deleted = 0
    delete_action = tk.get_action("organization_delete")

    for org_id in org_ids:
        try:
            delete_action(context, {"id": org_id})
            deleted += 1
        except Exception as exc:  # pragma: no cover - pass exact backend error
            errors.append({"id": str(org_id), "error": str(exc)})

    return {"success": not errors, "deleted": deleted, "errors": errors}


def udc_purge_deleted_organizations(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    """Purge deleted organizations permanently (sysadmin only)."""
    tk.check_access("udc_purge_deleted_organizations", context, data_dict)

    selected_ids = data_dict.get("ids") or []
    if not isinstance(selected_ids, list):
        raise tk.ValidationError({"ids": ["Provide a list of organization ids."]})

    query = model.Session.query(model.Group).filter(
        model.Group.is_organization.is_(True),
        model.Group.state == "deleted",
    )
    if selected_ids:
        query = query.filter(model.Group.id.in_(selected_ids))

    orgs = query.all()
    errors: list[dict[str, str]] = []
    purged = 0
    purge_action = tk.get_action("organization_purge")

    for org in orgs:
        try:
            purge_action(context, {"id": org.id})
            purged += 1
        except Exception as exc:  # pragma: no cover - pass exact backend error
            errors.append({"id": str(org.id), "error": str(exc)})

    return {"success": not errors, "purged": purged, "errors": errors}


def _get_org(data_dict: dict[str, Any]) -> model.Group:
    org_id = data_dict.get("org_id") or data_dict.get("id") or data_dict.get("name")
    if not org_id:
        raise tk.ValidationError({"org_id": ["Organization id or name is required."]})
    org = model.Group.get(org_id)
    if not org or not org.is_organization:
        raise NotFound("Organization not found")
    return org


def _org_to_dict(org: model.Group) -> dict[str, Any]:
    title = getattr(org, "title", None) or getattr(org, "display_name", None) or org.name
    return {
        "id": org.id,
        "name": org.name,
        "title": title,
        "description": org.description,
        "state": org.state,
        "created": org.created.isoformat() if org.created else None,
    }


def _package_to_dict(package: model.Package) -> dict[str, Any]:
    return {
        "id": package.id,
        "name": package.name,
        "title": package.title,
        "state": package.state,
        "private": bool(package.private),
        "metadata_modified": package.metadata_modified.isoformat() if package.metadata_modified else None,
    }


def _apply_org_filters(query, filters: dict[str, Any]):
    search = (filters.get("q") or "").strip()
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                model.Group.name.ilike(pattern),
                model.Group.title.ilike(pattern),
                model.Group.description.ilike(pattern),
            )
        )

    name = (filters.get("name") or "").strip()
    if name:
        query = query.filter(model.Group.name.ilike(f"%{name}%"))

    title = (filters.get("title") or "").strip()
    if title:
        query = query.filter(model.Group.title.ilike(f"%{title}%"))

    state = filters.get("state")
    if state:
        query = query.filter(model.Group.state == state)
    else:
        query = query.filter(model.Group.state != "deleted")

    if _as_bool(filters.get("creator_deleted_or_purged")):
        query = _filter_orgs_by_creator_deleted_or_purged(query)

    return query


def _apply_package_filters(query, filters: dict[str, Any]):
    search = (filters.get("q") or "").strip()
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                model.Package.name.ilike(pattern),
                model.Package.title.ilike(pattern),
                model.Package.notes.ilike(pattern),
            )
        )

    name = (filters.get("name") or "").strip()
    if name:
        query = query.filter(model.Package.name.ilike(f"%{name}%"))

    title = (filters.get("title") or "").strip()
    if title:
        query = query.filter(model.Package.title.ilike(f"%{title}%"))

    state = filters.get("state")
    if state:
        query = query.filter(model.Package.state == state)
    else:
        query = query.filter(model.Package.state != "deleted")

    return query


def _filter_orgs_by_creator_deleted_or_purged(query):
    org_ids = [row[0] for row in query.with_entities(model.Group.id).all()]
    if not org_ids:
        return query.filter(model.Group.id == "__none__")

    creator_map = _org_creator_user_map(org_ids)
    creator_ids = {creator_id for creator_id in creator_map.values() if creator_id}
    if not creator_ids:
        return query.filter(model.Group.id == "__none__")

    user_rows = (
        model.Session.query(model.User.id, model.User.state)
        .filter(model.User.id.in_(creator_ids))
        .all()
    )
    user_state_map = {row[0]: row[1] for row in user_rows}

    matching_org_ids = []
    for org_id, creator_id in creator_map.items():
        if not creator_id:
            continue
        creator_state = user_state_map.get(creator_id)
        if creator_state == "deleted" or creator_state is None:
            matching_org_ids.append(org_id)

    if not matching_org_ids:
        return query.filter(model.Group.id == "__none__")

    return query.filter(model.Group.id.in_(matching_org_ids))


def _org_creator_user_map(org_ids: list[str]) -> dict[str, str | None]:
    rows = (
        model.Session.query(Activity.object_id, Activity.user_id, Activity.timestamp)
        .filter(
            Activity.activity_type == "new organization",
            Activity.object_id.in_(org_ids),
        )
        .order_by(Activity.object_id.asc(), Activity.timestamp.asc())
        .all()
    )

    creator_map: dict[str, str | None] = {}
    for object_id, user_id, _timestamp in rows:
        if object_id not in creator_map:
            creator_map[object_id] = user_id
    return creator_map


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(value, int):
        return value == 1
    return False
