import click
import ckan.model as model
import logging
from importlib import import_module
import os
import polib
from ckan.common import config
from ckan.lib.i18n import build_js_translations, get_ckan_i18n_dir


@click.group(short_help=u"UDC commands.")
def udc():
    pass

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
