from ckanext.udc_import_other_portals.logic.arcgis_based.base import ArcGISBasedImport

# https://geohub.lio.gov.on.ca/

class OntarioGeoHubImport(ArcGISBasedImport):
    """
    Import implementation for Ontario GeoHub (https://geohub.lio.gov.on.ca/)
    """
    name_prefix = "on"

    def map_to_cudc_package(self, src: dict, target: dict):
        """
        Map ArcGIS Hub dataset to CUDC package format.
        
        Args:
            src (dict): The source ArcGIS dataset
            target (dict): The target package template with default values
        """
        attributes = src.get('attributes') or {}
        title = attributes.get("name", "") or attributes.get("snippet", "")
        notes = attributes.get("description", "") or attributes.get("searchDescription", "")
        return self._map_common_fields(
            src,
            target,
            title=title,
            notes=notes,
            source_portal="Ontario GeoHub",
        )
    
DefaultImportClass = OntarioGeoHubImport
