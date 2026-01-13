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

    def map_to_cudc_package(self, src: dict, target: dict):
        """
        Map Manitoba GeoPortal dataset to CKAN package format.
        
        Args:
            src: Source dataset from ArcGIS Hub API
            target: Target CKAN package dictionary to populate
            
        Returns:
            The populated target dictionary
        """
        attributes = src.get('attributes', {})

        item_id = src.get("id", "")
        if item_id:
            target["url"] = f"https://geoportal.gov.mb.ca/datasets/{item_id}"

        title = attributes.get("name", "")
        notes = attributes.get("description", "")
        return self._map_common_fields(
            src,
            target,
            title=title,
            notes=notes,
            source_portal="Manitoba GeoPortal",
            tag_limit=10,
        )

DefaultImportClass = ManitobaGeoPortalImport
