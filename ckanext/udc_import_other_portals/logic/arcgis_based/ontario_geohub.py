from ckanext.udc_import_other_portals.logic.arcgis_based.base import ArcGISBasedImport

# https://geohub.lio.gov.on.ca/

class OntarioGeoHubImport(ArcGISBasedImport):
    """
    Import implementation for Ontario GeoHub (https://geohub.lio.gov.on.ca/)
    """
    name_prefix = "on"
    source_portal = "Ontario GeoHub"
    
DefaultImportClass = OntarioGeoHubImport
