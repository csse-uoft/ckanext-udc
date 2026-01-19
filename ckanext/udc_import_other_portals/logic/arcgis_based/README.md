# ArcGIS-based Imports

This directory contains import implementations for ArcGIS Hub-based open data portals.

## Architecture

### Base Classes

- **`api.py`**: Core API client utilities for interacting with ArcGIS Hub REST APIs
  - `get_all_datasets()`: Fetch all datasets with pagination support
  - `get_dataset()`: Fetch a single dataset by ID
  - `check_site_alive()`: Verify endpoint accessibility

- **`base.py`**: `ArcGISBasedImport` base class
  - Handles common import workflow (fetch, map, import, cleanup)
  - Manages deleted dataset detection and removal
  - Provides threading support for concurrent imports
  - Tracks import progress via SocketIO

### Implementations

- **`ontario_geohub.py`**: Ontario GeoHub (https://geohub.lio.gov.on.ca/)
  - Filters for public datasets
  - Uses shared ArcGIS mapping from `ArcGISBasedImport`
  - Sets `name_prefix` and `source_portal`

- **`manitoba_geoportal.py`**: Manitoba GeoPortal (https://geoportal.gov.mb.ca/)
  - Filters for public datasets
  - Uses shared ArcGIS mapping from `ArcGISBasedImport`
  - Sets `name_prefix` and `source_portal`

### Common Class Attributes

- `name_prefix`: prepended to generated dataset names so IDs remain unique across portals.
- `source_portal`: stored in `udc_import_extras` to identify the origin portal for debugging and provenance.

## ArcGIS Hub API Structure

ArcGIS Hub uses a V3 REST API with the following structure:

```
GET /api/v3/datasets?page[size]=100&page[number]=1
```

### Response Format

```json
{
  "data": [
    {
      "id": "dataset_id",
      "type": "dataset",
      "attributes": {
        "name": "Dataset Name",
        "description": "Dataset description",
        "snippet": "Short description",
        "tags": ["tag1", "tag2"],
        "categories": ["category1"],
        "license": "CC0-1.0",
        "owner": "Organization Name",
        "created": 1234567890000,
        "modified": 1234567890000,
        "recordCount": 1000,
        "url": "https://services.arcgis.com/.../FeatureServer/0",
        "extent": {
          "coordinates": [[-180, -90], [180, 90]]
        },
        "layer": {
          "geometryType": "esriGeometryPoint",
          "fields": [...]
        }
      }
    }
  ],
  "meta": {
    "total": 10000
  },
  "links": {
    "next": "...next page URL..."
  }
}
```

## Mapping Logic (ArcGISBasedImport)

The shared mapping lives in `ArcGISBasedImport._map_common_fields()` and covers:

- **Identifiers**
  - `id`: dataset id from ArcGIS (`src.id`)
  - `name`: CKAN-safe slug from id + title
  - `unique_identifier`: `attributes.itemId` or `attributes.id`
  - `unique_metadata_identifier`: `attributes.metadata.metadata.mdFileID` when present

- **Title & Description**
  - Provided by subclasses (`title`, `notes`)

- **Timestamps**
  - `metadata_created`, `metadata_modified` (epoch ms → ISO)
  - `published_date`, `accessed_date` (date part of created/modified)

- **Tags**
  - Merges `attributes.tags` and `attributes.categories`
  - Cleaned to CKAN-allowed characters only (no forced lowercasing)
  - `display_name` is identical to `name`

- **License**
  - Handles `structuredLicense`, `licenseInfo`, `license` with URL extraction and title parsing
  - Maps common licenses (OGL Ontario, CC, ODbL), otherwise generates a `custom-...` id

- **Resources**
  - Each `attributes.layers[]` produces one resource (REST layer URL)
  - Each layer also gets an **Explore** resource (`.../datasets/<slug>/explore?layer=<id>`)
  - No download resources are generated (Hub `/downloads` endpoints are 403 on public sites)

- **Landing / Location**
  - Uses `/datasets/<slug>` when available, otherwise `/datasets/<itemId>`
  - Falls back to service URL when needed

- **Spatial**
  - Converts ArcGIS extent to GeoJSON Polygon

- **Org / Steward / Language**
  - `author`, `owner` from `attributes.owner`
  - `publisher`, `access_steward` from `orgName`/`organization`/`source`
  - `access_steward_email` from `orgContactEmail`
  - `language` from `culture`
  - `access_category` from `access`

- **Row/Column Stats**
  - `number_of_rows` from `recordCount`
  - `number_of_columns` from `fieldNames`/`fields` length
  - `number_of_cells` = rows × columns (best effort)

- **Provenance**
  - `provenance` from `source`

- **Debug Extras**
  - Import extras are stored as JSON in `udc_import_extras` (not regular `extras`)
  - Admin-only display in dataset view

### Layer Filtering

`ArcGISBasedImport` skips datasets of type **Feature Layer** when a **Feature Service**
with the same `itemId` exists, to avoid duplicate packages.

## Adding New ArcGIS-based Imports

To add a new ArcGIS Hub portal:

1. Create a new file in this directory (e.g., `my_portal.py`)
2. Extend `ArcGISBasedImport`
3. Set `name_prefix` and `source_portal`
4. Override `iterate_imports()` to filter datasets (optional)
5. Override `map_to_cudc_package()` only if you need portal-specific fields
6. Add to `__init__.py` exports

### Example

```python
from ckanext.udc_import_other_portals.logic.arcgis_based.base import ArcGISBasedImport

class MyPortalImport(ArcGISBasedImport):
    name_prefix = "my"
    source_portal = "My Portal"

    # Override map_to_cudc_package() only if you need custom fields.
    # The base class already maps title/notes, tags, resources, license,
    # and other common metadata.
    # def map_to_cudc_package(self, src):
```

### Example: Override map_to_cudc_package

```python
from ckanext.udc_import_other_portals.logic.arcgis_based.base import ArcGISBasedImport

class MyPortalImport(ArcGISBasedImport):
    name_prefix = "my"
    source_portal = "My Portal"

    def map_to_cudc_package(self, src: dict, target: dict):
        target = super().map_to_cudc_package(src, target)

        attributes = src.get("attributes") or {}
        if attributes.get("recordCount") is not None:
            target["record_count"] = str(attributes.get("recordCount"))

        return target
```

### Example: Override iterate_imports

```python
from ckanext.udc_import_other_portals.logic.arcgis_based.base import ArcGISBasedImport

class MyPortalImport(ArcGISBasedImport):
    name_prefix = "my"
    source_portal = "My Portal"

    def iterate_imports(self):
        """Skip private datasets and those with a restricted tag."""
        for dataset in self.all_datasets:
            attributes = dataset.get("attributes") or {}
            if attributes.get("access") != "public":
                continue
            tags = attributes.get("tags") or []
            if "restricted" in tags:
                continue
            yield dataset
```

## Configuration

In the import configuration `other_config`:

```json
{
  "base_api": "https://geohub.lio.gov.on.ca",
  "org_import_mode": "importToSingleOrg",
  "delete_previously_imported": false
}
```

## Key Differences from CKAN-based Imports

1. **API Structure**: Uses `/api/v3/datasets` instead of `/api/3/action/package_search`
2. **Pagination**: Uses `page[number]` and `page[size]` query parameters
3. **Data Format**: Datasets are in `data` array with `attributes` object
4. **Resources**: Layer-only resources with separate Explore links
5. **Spatial Data**: Native support for spatial extents and geometry types
6. **Timestamps**: Uses milliseconds since epoch instead of ISO format

## Testing

Test an import configuration:

```python
from ckanext.udc_import_other_portals.model import CUDCImportConfig
from ckanext.udc_import_other_portals.logic.arcgis_based.ontario_geohub import OntarioGeoHubImport

# Create or load config
config = CUDCImportConfig.get("config-uuid")

# Initialize importer
importer = OntarioGeoHubImport(None, config, "test-job-id")

# Test mapping without importing
importer.test(use_cache=True)
```
