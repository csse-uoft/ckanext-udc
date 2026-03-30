import click
import ckan.model as model
import json
import logging
import re
from importlib import import_module
import os
import polib
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Set

from ckan.lib.i18n import build_js_translations, get_ckan_i18n_dir


@click.group(short_help=u"UDC commands.")
def udc():
    pass


def _load_udc_config() -> Dict[str, Any]:
    existing_config = model.system_info.get_system_info("ckanext.udc.config")
    if existing_config:
        return json.loads(existing_config)

    config_path = Path(__file__).resolve().parents[1] / "config.example.json"
    with config_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _get_number_field_names(udc_config: Dict[str, Any]) -> List[str]:
    fields: List[str] = []
    seen: Set[str] = set()

    for level in udc_config.get("maturity_model", []):
        for field in level.get("fields", []):
            if field.get("type") != "number":
                continue
            name = field.get("name")
            if not name or name in seen:
                continue
            fields.append(name)
            seen.add(name)

    return fields


def _normalize_scalar_number(value: Any) -> Optional[str]:
    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        text = str(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None

        # Accept common thousands separators such as 10,740 or 1,234.56.
        if re.match(r"^[+-]?\d{1,3}(,\d{3})+(\.\d+)?$", text):
            text = text.replace(",", "")
    else:
        return None

    try:
        float(text)
    except (TypeError, ValueError):
        return None

    return text


def _parse_jsonish(value: Any) -> Any:
    if isinstance(value, (dict, list, int, float)):
        return value
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return None


def _normalize_localized_number(value: Any) -> Optional[str]:
    parsed = _parse_jsonish(value)
    if not isinstance(parsed, dict):
        return None

    candidates: List[str] = []
    for localized_value in parsed.values():
        if localized_value in (None, ""):
            continue
        normalized = _normalize_scalar_number(localized_value)
        if normalized is None:
            return None
        candidates.append(normalized)

    if not candidates:
        return None

    if len(set(candidates)) == 1:
        return candidates[0]

    return None


def _inspect_number_field_value(value: Any) -> Dict[str, Any]:
    scalar_value = _normalize_scalar_number(value)
    if scalar_value is not None:
        return {"status": "ok", "normalized": scalar_value}

    if value in (None, ""):
        return {"status": "empty", "normalized": None}

    normalized_localized = _normalize_localized_number(value)
    if normalized_localized is not None:
        return {
            "status": "fixable_localized",
            "normalized": normalized_localized,
        }

    parsed = _parse_jsonish(value)
    if isinstance(parsed, dict):
        return {"status": "invalid_localized", "normalized": None}

    return {"status": "invalid", "normalized": None}


def _process_number_field_migration(
    packages: Iterable[Any],
    number_fields: List[str],
    fix: bool = False,
    echo: Optional[Callable[[str], None]] = None,
) -> Dict[str, int]:
    emit = echo or (lambda _message: None)
    stats = {
        "packages_scanned": 0,
        "packages_with_issues": 0,
        "issues_found": 0,
        "fixable": 0,
        "fixed": 0,
        "invalid": 0,
    }

    for package in packages:
        stats["packages_scanned"] += 1
        package_has_issue = False

        for field in number_fields:
            raw_value = package.extras.get(field)
            inspection = _inspect_number_field_value(raw_value)
            status = inspection["status"]

            if status in {"ok", "empty"}:
                continue

            package_has_issue = True
            stats["issues_found"] += 1
            package_id = getattr(package, "id", "<unknown>")
            package_name = getattr(package, "name", package_id)

            if status == "fixable_localized":
                normalized = inspection["normalized"]
                stats["fixable"] += 1
                if fix:
                    package.extras[field] = normalized
                    stats["fixed"] += 1
                    emit(
                        f'Fix package {package_id} ({package_name}) field "{field}": {raw_value!r} -> {normalized!r}'
                    )
                else:
                    emit(
                        f'Would fix package {package_id} ({package_name}) field "{field}": {raw_value!r} -> {normalized!r}'
                    )
                continue

            stats["invalid"] += 1
            emit(
                f'Invalid value on package {package_id} ({package_name}) field "{field}": {raw_value!r}'
            )

        if package_has_issue:
            stats["packages_with_issues"] += 1

    return stats

@udc.command()
def move_to_catalogues():
    """
    Make all packages have type=catalogue.
    This is used when we want to rename 'dataset' to 'catalogue'.
    """
    datasets = model.Session.query(model.Package).filter(model.Package.type == "dataset")
    nothing_to_do = True
    
    for dataset in datasets:
        if dataset.type == 'dataset':
            click.echo(f'Update Dataset {dataset.id}: dataset.type: "{dataset.type}" -> "catalogue"')
            dataset.type = 'catalogue'
            nothing_to_do = False
    
    if nothing_to_do:
        click.echo("Nothing to do!")
    else:
        model.repo.commit_and_remove()
        click.echo("Done. Please restart the CKAN instance!")


@udc.command()
@click.option(
    "--fix",
    is_flag=True,
    default=False,
    help="Normalize fixable localized number-field values in place.",
)
def migrate_number_fields(fix):
    """
    Check all datasets/catalogues for malformed number extras.
    """
    udc_config = _load_udc_config()
    number_fields = _get_number_field_names(udc_config)

    if not number_fields:
        click.echo("No number fields found in UDC config.")
        return

    packages = (
        model.Session.query(model.Package)
        .filter(model.Package.state == "active")
        .filter(model.Package.type.in_(["catalogue", "dataset"]))
        .yield_per(100)
    )

    click.echo(
        "Checking number fields: " + ", ".join(number_fields)
    )

    stats = _process_number_field_migration(packages, number_fields, fix=fix, echo=click.echo)

    if fix and stats["fixed"]:
        model.repo.commit_and_remove()
        click.echo(
            "Applied fixes in the database. Rebuild the search index before retrying indexing."
        )

    click.echo(
        "Summary: "
        f'packages_scanned={stats["packages_scanned"]} '
        f'packages_with_issues={stats["packages_with_issues"]} '
        f'issues_found={stats["issues_found"]} '
        f'fixable={stats["fixable"]} '
        f'fixed={stats["fixed"]} '
        f'invalid={stats["invalid"]}'
    )

    if stats["issues_found"] and not fix:
        click.echo("Dry run only. Rerun with --fix to normalize the fixable localized values.")

@udc.command()
def initdb():
    """
    Initialises the database with the required tables.
    """
    log = logging.getLogger(__name__)
    
    model.Session.remove()
    model.Session.configure(bind=model.meta.engine)

    log.info("Initializing tables")
    
    from ..licenses.model import init_tables
    init_tables()
    
    libs = [
        "ckanext.udc_import_other_portals.model",
        "ckanext.udc_react.model.organization_access_request",
    ]
    for lib_str in libs:
        try:
            lib = import_module(lib_str)
            lib.init_tables()
        except Exception as e:
            print(e)
            log.warning(f"Cannot init DB in {lib_str} plugin")
        
    log.info("DB tables initialized")


@udc.command()
@click.option("--locale", default="fr", show_default=True, help="Locale to override.")
@click.option(
    "--source",
    default=None,
    help="Path to override ckan.po (defaults to ckanext-udc i18n).",
)
@click.option(
    "--build-js",
    is_flag=True,
    default=False,
    help="Also rebuild JS translations after copying.",
)
def override_ckan_translations(locale, source, build_js):
    """
    Override CKAN core translations using a plugin-managed ckan.po file.
    """
    if not source:
        base_dir = os.path.dirname(os.path.dirname(__file__))
        source = os.path.join(base_dir, "i18n", locale, "LC_MESSAGES", "ckan.po")

    if not os.path.isfile(source):
        raise click.ClickException(f"Source translation not found: {source}")

    target_dir = get_ckan_i18n_dir()
    dest_dir = os.path.join(target_dir, locale, "LC_MESSAGES")
    os.makedirs(dest_dir, exist_ok=True)

    dest_po = os.path.join(dest_dir, "ckan.po")
    dest_mo = os.path.join(dest_dir, "ckan.mo")

    po = polib.pofile(source)
    po.save(dest_po)
    po.save_as_mofile(dest_mo)

    if build_js:
        build_js_translations()

    click.secho(
        f"CKAN translations overridden for locale '{locale}' in {dest_dir}",
        fg="green",
        bold=True,
    )
