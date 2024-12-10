import click
import ckan.model as model
import logging
from importlib import import_module


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
