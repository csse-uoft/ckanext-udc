# CUDC Import Other Portals

This extension allows you to import datasets from various open data portals into your CKAN instance.

## Supported Platforms

### 1. CKAN-based Portals

Import from other CKAN instances (e.g., Open Canada, Données Québec, City of Toronto, etc.)

**Configuration:**
- **Platform**: Select "CKAN"
- **API URL**: CKAN API endpoint (e.g., `https://open.canada.ca/data/api/`)
- **Organization Mode**: Choose how to handle organizations
  - Import to specified org: All datasets go to one organization
  - Import to own org: Preserve source organization structure

**Example Code:**
```python
from ckanext.udc_import_other_portals.logic.ckan_based.base import CKANBasedImport

class MyImport(CKANBasedImport):
    def map_to_cudc_package(self, src: dict, target: dict):
        # Basic one-to-one mapping
        target["id"] = src.get("id", "")
        target["name"] = src.get("name", "")
        target["title"] = src.get("title", "")
        target["notes"] = src.get("notes", "")
        target["tags"] = src.get("tags", [])
        
        return target
```

### 2. ArcGIS Hub Portals

Import geospatial datasets from ArcGIS Hub instances (e.g., Ontario GeoHub, ArcGIS Open Data portals)

**Configuration:**
- **Platform**: Select "ArcGIS Hub"
- **API URL**: Hub base URL (e.g., `https://geohub.lio.gov.on.ca`)
- **Organization**: Select target organization for all imported datasets

**Example Code:**
```python
from ckanext.udc_import_other_portals.logic.arcgis_based.ontario_geohub import OntarioGeoHubImport

class MyArcGISImport(OntarioGeoHubImport):
    def iterate_imports(self):
        """Filter datasets before import"""
        for dataset in self.all_datasets:
            attributes = dataset.get('attributes', {})
            # Only import public datasets
            if attributes.get('access') == 'public':
                yield dataset
    
    def map_to_cudc_package(self, src: dict, target: dict):
        """Customize the mapping"""
        # Call parent implementation first
        target = super().map_to_cudc_package(src, target)
        
        # Add custom fields
        attributes = src.get('attributes', {})
        if attributes.get('recordCount'):
            target['record_count'] = str(attributes['recordCount'])
        
        return target
```

### 3. Socrata Portals (Coming Soon)

Import from Socrata-powered open data portals

## Quick Start Guide

1. **Navigate to Import Dashboard**: Access via admin panel or `/udc/import` route

2. **Create New Import Configuration**:
   - Click "New Import" tab
   - Enter import name
   - Select platform (CKAN or ArcGIS Hub)
   - Configure API URL
   - Choose organization settings

3. **Write Python Code**:
   - Extend the appropriate base class
   - Override `map_to_cudc_package()` to customize field mapping
   - Optionally override `iterate_imports()` to filter datasets

4. **Save and Run**:
   - Click "Save" to store configuration
   - Click "Save and Run Import" to execute immediately
   - Monitor progress in real-time

## Advanced Features

### Filtering Datasets

Override `iterate_imports()` to filter which datasets get imported:

```python
def iterate_imports(self):
    for dataset in self.all_datasets:
        # Only import datasets with specific tags
        tags = dataset.get('tags', [])
        if 'environment' in [t.get('name') for t in tags]:
            yield dataset
```

### Custom Field Mapping

Map source metadata to CKAN fields:

```python
def map_to_cudc_package(self, src: dict, target: dict):
    # Handle multilingual fields
    target["title_translated"] = {
        "en": src.get("title_en", ""),
        "fr": src.get("title_fr", "")
    }
    
    # Map custom fields
    target["custom_field"] = src.get("source_field", "")
    
    return target
```

### Resource Handling

Add downloadable resources:

```python
resources = []
for resource in src.get('resources', []):
    resources.append({
        "name": resource.get("name", ""),
        "url": resource.get("url", ""),
        "format": resource.get("format", ""),
        "description": resource.get("description", "")
    })
target["resources"] = resources
```

Note: ArcGIS-based imports build resources from layers (see ArcGIS Resource Mapping below), so this example is mainly for CKAN-based imports.

### Organization Management (CKAN only)

Override `before_create_organization()` to customize organization creation:

```python
def before_create_organization(self, organization: dict, related_package: dict):
    # Extract organization info from package metadata
    org_title = related_package.get("organization", {}).get("title", "")
    if org_title:
        organization["title"] = org_title
    
    return organization
```

## Scheduled Imports

Use cron schedule to automate imports. The UI provides presets plus a custom builder (no manual cron typing required):

- Daily at 2 AM: `0 2 * * *`
- Weekly on Monday at 2 AM: `0 2 * * 1`
- Monthly on the 1st: `0 2 1 * *`

Schedules are stored on the import config and registered via `rq-scheduler`. When you save/update a config, the schedule is re-synced automatically.

**Required**: run an `rq-scheduler` process alongside the CKAN workers so scheduled imports actually execute.

## Monitoring and Logs

- **Real-time Progress**: View live import status in the dashboard
- **Import Logs**: Access historical logs for each import run
- **Error Tracking**: Failed imports are logged with detailed error messages

## Troubleshooting

### Import Fails to Start

- Verify API URL is correct and accessible
- Check Python code for syntax errors
- Ensure organization is selected

### Datasets Not Importing

- Check `iterate_imports()` filter logic
- Verify source API is returning data
- Review error logs for specific failures

### Duplicate Datasets

- Enable "Delete previously imported packages" to clean up old imports
- Ensure dataset IDs are unique

## Architecture

### Import Flow

1. **Fetch**: Retrieve all datasets from source API
2. **Filter**: Apply `iterate_imports()` to filter datasets
3. **Map**: Transform each dataset using `map_to_cudc_package()`
4. **Import**: Create/update packages in CKAN
5. **Cleanup**: Remove datasets deleted from source
6. **Deduplicate**: Link duplicate datasets across imports

### ArcGIS Resource Mapping (Overview)

For ArcGIS Hub imports, resources are built from layers:

- Each Feature Service layer becomes a CKAN resource.
- Each layer also gets a companion "Explore" HTML resource (layer-specific explore page).
- Additional resources are mapped when present (preserve provided names when available).
- Feature Layer items are skipped when a matching Feature Service exists.

### Base Classes

- `BaseImport`: Core import logic and workflow
- `CKANBasedImport`: CKAN-specific implementation
- `ArcGISBasedImport`: ArcGIS Hub-specific implementation

## API Reference

See individual README files for detailed API documentation:

- [CKAN-based imports](./logic/ckan_based/README.md)
- [ArcGIS-based imports](./logic/arcgis_based/README.md)
