"""
Manitoba GeoPortal (https://geoportal.gov.mb.ca/) import implementation.
"""

from ckanext.udc_import_other_portals.logic.arcgis_based.base import ArcGISBasedImport


class ManitobaGeoPortalImport(ArcGISBasedImport):
    """
    Import class for Manitoba's GeoPortal (https://geoportal.gov.mb.ca/).
    
    The Manitoba GeoPortal is an ArcGIS Hub portal providing access to geospatial
    data from the Province of Manitoba, Canada. It includes datasets related to
    infrastructure, natural resources, demographics, and more.
    
    Configuration example:
    {
        "base_api": "https://geoportal.gov.mb.ca",
        "organization_uuid": "your-org-uuid-here"
    }
    """
    name_prefix = "mb"
    source_portal = "Manitoba GeoPortal"

DefaultImportClass = ManitobaGeoPortalImport
