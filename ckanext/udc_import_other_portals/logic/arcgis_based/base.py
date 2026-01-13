import traceback
import logging
import time
import uuid
import re
import unicodedata
from urllib.parse import urlparse
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Set

from ckanext.udc_import_other_portals.model import CUDCImportConfig
from ckanext.udc_import_other_portals.worker.socketio_client import SocketClient
from ckanext.udc_import_other_portals.logger import ImportLogger
from ckanext.udc_import_other_portals.logic.arcgis_based.api import (
    get_all_datasets,
    check_site_alive
)
from ckanext.udc_import_other_portals.logic.base import (
    BaseImport,
    purge_package,
    get_package as get_self_package,
    get_package_ids_by_import_config_id,
    ensure_license,
)
from ckan import model


base_logger = logging.getLogger(__name__)


class ArcGISBasedImport(BaseImport):
    """
    Base class for ArcGIS Hub imports
    """
    name_prefix = ""

    def __init__(self, context, import_config: 'CUDCImportConfig', job_id: str):
        super().__init__(context, import_config, job_id)
        self.base_api = import_config.other_config.get("base_api")
        
        # Validate that base_api is provided
        if not self.base_api:
            raise ValueError("base_api is required in import configuration")

    def _ms_to_iso(self, timestamp_ms: int) -> str:
        """
        Convert milliseconds timestamp to ISO 8601 format
        """
        return datetime.utcfromtimestamp(timestamp_ms / 1000).isoformat()

    def _clean_tag(self, tag: str) -> str:
        """
        Clean tag to be CKAN-compatible: keep only allowed characters.
        """
        tag = tag.strip()
        tag = re.sub(r"[^a-zA-Z0-9 ._-]", "", tag)
        tag = re.sub(r"\s{2,}", " ", tag)
        return tag.strip()[:100]

    def _slugify_ascii(self, text: str) -> str:
        """
        Normalize text to a CKAN-safe ASCII slug.
        """
        normalized = unicodedata.normalize("NFKD", text or "")
        ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^a-z0-9_-]+", "-", ascii_text.lower())
        slug = re.sub(r"-{2,}", "-", slug).strip("-_")
        return slug

    def _strip_html(self, text: str) -> str:
        raw = re.sub(r"<[^>]*>", " ", text or "")
        return re.sub(r"\s+", " ", raw).strip()

    def _extract_license_url(self, html: str) -> Optional[str]:
        match = re.search(r'href=[\'"]([^\'"]+)[\'"]', html or "")
        return match.group(1) if match else None
    
    def _hub_base(self) -> str:
        base = (self.base_api or "").rstrip("/")
        if base.endswith("/api/v3"):
            base = base[:-7]
        return base

    def _extract_supported_formats(self, attributes: dict) -> List[str]:
        formats = set()

        def add_formats(value: Optional[str]) -> None:
            if not value or not isinstance(value, str):
                return
            for fmt in value.split(","):
                cleaned = fmt.strip().lower()
                if cleaned:
                    formats.add(cleaned)

        add_formats(attributes.get("supportedExportFormats"))
        layers = attributes.get("layers") or []
        if isinstance(layers, list):
            for layer in layers:
                if isinstance(layer, dict):
                    add_formats(layer.get("supportedExportFormats"))

        return sorted(formats)

    def _export_format_info(self, fmt: str) -> dict:
        export_formats = {
            "csv": {"label": "CSV", "format": "CSV", "download": "csv", "query": "csv"},
            "kml": {"label": "KML", "format": "KML", "download": "kml", "query": "kml"},
            "geojson": {"label": "GeoJSON", "format": "GeoJSON", "download": "geojson", "query": "geojson"},
            "shapefile": {"label": "Shapefile", "format": "SHP", "download": "shapefile"},
            "excel": {"label": "Excel", "format": "XLSX", "download": "excel", "query": "excel"},
            "sqlite": {"label": "SQLite", "format": "SQLite", "download": "sqlite"},
            "geopackage": {"label": "GeoPackage", "format": "GPKG", "download": "geopackage"},
            "filegdb": {"label": "FileGDB", "format": "FileGDB", "download": "filegdb"},
            "featurecollection": {
                "label": "Feature Collection",
                "format": "Feature Collection",
                "download": "featurecollection",
                "query": "featureCollection",
            },
            "json": {"label": "JSON", "format": "JSON", "download": "json", "query": "json"},
            "pbf": {"label": "PBF", "format": "PBF", "download": "pbf", "query": "pbf"},
        }
        key = (fmt or "").strip().lower()
        info = export_formats.get(key)
        if info:
            return info
        if not key:
            return {"label": "Download", "format": "DATA", "download": "data"}
        return {"label": key.upper(), "format": key.upper(), "download": key}

    def _layer_url(self, service_url: str, layer_id: int) -> str:
        base_url = service_url.rstrip("/")
        if re.search(r"/(FeatureServer|MapServer)/\\d+$", base_url):
            return base_url
        if re.search(r"/(FeatureServer|MapServer)/?$", base_url):
            return f"{base_url}/{layer_id}"
        return base_url

    def _layer_explore_url(self, slug: Optional[str], layer_id: int) -> Optional[str]:
        if not slug:
            return None
        base = self._hub_base()
        if not base:
            return None
        return f"{base}/datasets/{slug}/explore?layer={layer_id}"

    def _query_downloads(
        self,
        service_url: str,
        layer_id: int,
        formats: List[str],
        layer_label: Optional[str] = None,
    ) -> List[dict]:
        resources = []
        base_url = self._layer_url(service_url, layer_id)
        if not re.search(r"/(FeatureServer|MapServer)/\\d+$", base_url):
            return resources

        for fmt in formats:
            info = self._export_format_info(fmt)
            query_fmt = info.get("query")
            if not query_fmt:
                continue
            name_prefix = f"{layer_label} - " if layer_label else ""
            download_url = (
                f"{base_url}/query?where=1=1&outFields=*"
                f"&returnGeometry=true&f={query_fmt}"
            )
            resources.append({
                "name": f"{name_prefix}{info['label']} Download",
                "description": f"Download as {info['label']}",
                "url": download_url,
                "format": info["format"],
            })
        return resources

    def _format_from_url(self, url: str) -> str:
        path = urlparse(url).path
        ext = os.path.splitext(path)[1].lstrip(".")
        if ext:
            return ext.upper()
        return "URL"

    def _resource_name_from_url(self, url: str, fallback: str) -> str:
        parsed = urlparse(url)
        last_segment = (parsed.path or "").rstrip("/").split("/")[-1]
        if last_segment:
            return last_segment
        if parsed.netloc:
            return parsed.netloc
        return fallback

    def _resource_name_from_additional(self, item: dict, fallback: str) -> str:
        name = item.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
        url = item.get("url")
        if isinstance(url, str) and url.strip():
            return self._resource_name_from_url(url, fallback)
        return fallback

    def _landing_url(self, attributes: dict, src_id: str) -> Optional[str]:
        slug = attributes.get("slug")
        item_id = attributes.get("itemId") or src_id
        base_url = (self.base_api or "").rstrip("/")
        if not base_url:
            return None
        if slug:
            return f"{base_url}/datasets/{slug}"
        if item_id:
            return f"{base_url}/datasets/{item_id}"
        return None

    def _build_tags(self, attributes: dict, limit: Optional[int] = None) -> List[dict]:
        tags = []
        seen = set()
        for raw in (attributes.get("tags") or []):
            if not isinstance(raw, str) or not raw.strip():
                continue
            tag_name = self._clean_tag(raw)
            if not tag_name or tag_name in seen:
                continue
            seen.add(tag_name)
            tags.append({"name": tag_name, "display_name": tag_name})
            if limit and len(tags) >= limit:
                return tags
        for raw in (attributes.get("categories") or []):
            if not isinstance(raw, str) or not raw.strip():
                continue
            tag_name = self._clean_tag(raw)
            if not tag_name or tag_name in seen:
                continue
            seen.add(tag_name)
            tags.append({"name": tag_name, "display_name": tag_name})
            if limit and len(tags) >= limit:
                return tags
        return tags

    def _build_import_extras(self, attributes: dict, source_portal: str, source_id: str) -> List[dict]:
        extras = []
        layer_info = attributes.get("layer") or {}

        if attributes.get("recordCount") is not None:
            extras.append({"key": "record_count", "value": str(attributes.get("recordCount"))})
        if attributes.get("type"):
            extras.append({"key": "dataset_type", "value": attributes["type"]})
        geometry_type = attributes.get("geometryType") or layer_info.get("geometryType")
        if geometry_type:
            extras.append({"key": "geometry_type", "value": geometry_type})
        fields_list = (attributes.get("layer") or {}).get("fields") or layer_info.get("fields")
        if fields_list:
            field_names = [f.get("name") for f in fields_list if f.get("name")]
            if field_names:
                extras.append({"key": "fields", "value": ", ".join(field_names[:20])})
        extras.append({"key": "source_portal", "value": source_portal})
        extras.append({"key": "source_id", "value": source_id})
        return extras

    def _map_common_fields(
        self,
        src: dict,
        target: dict,
        *,
        title: str,
        notes: str,
        source_portal: str,
        tag_limit: Optional[int] = None,
    ) -> dict:
        attributes = src.get("attributes") or {}

        target["id"] = src.get("id", "")
        target["name"] = self._generate_name(src.get("id", ""), attributes.get("name", ""))
        target["title"] = title
        target["notes"] = notes

        created_ms = attributes.get("created")
        if created_ms:
            try:
                target["metadata_created"] = self._ms_to_iso(created_ms)
            except Exception:
                pass

        modified_ms = attributes.get("modified")
        if modified_ms:
            try:
                target["metadata_modified"] = self._ms_to_iso(modified_ms)
            except Exception:
                pass

        if created_ms:
            try:
                target["published_date"] = self._ms_to_iso(created_ms).split("T")[0]
            except Exception:
                pass

        modified_ms = attributes.get("itemModified") or attributes.get("modified")
        if modified_ms:
            try:
                target["accessed_date"] = self._ms_to_iso(modified_ms).split("T")[0]
            except Exception:
                pass

        target["unique_identifier"] = attributes.get("itemId") or attributes.get("id")
        metadata = attributes.get("metadata") or {}
        target["unique_metadata_identifier"] = (
            (metadata.get("metadata") or {}).get("mdFileID")
        )
        if attributes.get("size") is not None:
            try:
                size_kb = float(attributes.get("size")) / 1024
                target["file_size"] = str(round(size_kb, 2))
            except (TypeError, ValueError):
                target["file_size"] = str(attributes.get("size"))

        tags = self._build_tags(attributes, limit=tag_limit)
        if tags:
            target["tags"] = tags

        self._apply_license(attributes, target)

        access_category = attributes.get("access")
        if access_category:
            target["access_category"] = access_category

        dataset_id = src.get("id", "")
        target["resources"] = self._build_resources(attributes, dataset_id)

        landing = self._landing_url(attributes, src.get("id", ""))
        if landing:
            target["location"] = landing
            target["description_document"] = landing
        else:
            url = attributes.get("url")
            if url:
                target["location"] = url
                target["data_service"] = url

        # extent = attributes.get("extent")
        # if extent and isinstance(extent, dict):
        #     coords = extent.get("coordinates")
        #     if coords and len(coords) == 2:
        #         target["spatial"] = {
        #             "type": "Polygon",
        #             "coordinates": [[
        #                 [coords[0][0], coords[0][1]],
        #                 [coords[1][0], coords[0][1]],
        #                 [coords[1][0], coords[1][1]],
        #                 [coords[0][0], coords[1][1]],
        #                 [coords[0][0], coords[0][1]]
        #             ]]
        #         }

        if attributes.get("owner"):
            target["author"] = attributes["owner"]
            target["owner"] = attributes["owner"]

        org_name = attributes.get("orgName") or attributes.get("organization") or attributes.get("source")
        if org_name:
            target["publisher"] = org_name
            target["access_steward"] = org_name

        org_email = attributes.get("orgContactEmail")
        if isinstance(org_email, str) and org_email:
            target["access_steward_email"] = org_email.replace("mailto:", "")

        culture = attributes.get("culture")
        if culture:
            target["language"] = culture

        if attributes.get("recordCount") is not None:
            target["number_of_rows"] = str(attributes.get("recordCount"))
        fields_list = attributes.get("fieldNames") or attributes.get("fields") or []
        if isinstance(fields_list, list) and fields_list:
            target["number_of_columns"] = str(len(fields_list))
            if target.get("number_of_rows"):
                try:
                    rows_value = target["number_of_rows"]
                    cells = int(rows_value) * len(fields_list)
                    target["number_of_cells"] = str(cells)
                except Exception:
                    pass

        provenance = attributes.get("source")
        if provenance:
            target["provenance"] = provenance

        import json as _json
        extras = self._build_import_extras(attributes, source_portal, src.get("id", ""))
        target["udc_import_extras"] = _json.dumps(extras, ensure_ascii=True)

        return target

    def _service_item_ids(self) -> Set[str]:
        if hasattr(self, "_service_item_ids_cache"):
            return self._service_item_ids_cache
        item_ids = set()
        for dataset in getattr(self, "all_datasets", []) or []:
            attributes = dataset.get("attributes") or {}
            item_id = attributes.get("itemId") or dataset.get("id")
            if attributes.get("type") == "Feature Service" and item_id:
                item_ids.add(item_id)
        self._service_item_ids_cache = item_ids
        return item_ids

    def _should_skip_dataset(self, dataset: dict) -> bool:
        attributes = dataset.get("attributes") or {}
        item_id = attributes.get("itemId") or dataset.get("id")
        if attributes.get("type") == "Feature Layer" and item_id in self._service_item_ids():
            return True
        return False

    def _build_resources(self, attributes: dict, dataset_id: str) -> List[dict]:
        resources = []

        service_url = attributes.get("url")
        layers = attributes.get("layers") or []
        if service_url and isinstance(layers, list):
            slug = attributes.get("slug")
            for layer in layers:
                if not isinstance(layer, dict):
                    continue
                layer_id = layer.get("id", 0)
                layer_name = layer.get("name") or f"Layer {layer_id}"
                layer_format = layer.get("type") or "Layer"
                layer_url = self._layer_url(service_url, layer_id)
                explore_url = self._layer_explore_url(slug, layer_id)
                description = f"Layer {layer_id} via ArcGIS REST API"
                resources.append({
                    "name": layer_name,
                    "description": description,
                    "url": layer_url,
                    "format": layer_format,
                })
                if explore_url:
                    resources.append({
                        "name": f"{layer_name} (Explore)",
                        "description": f"Explore {layer_name} on ArcGIS Hub",
                        "url": explore_url,
                        "format": "HTML",
                    })
        elif service_url:
            service_format = attributes.get("content") or attributes.get("type") or "Service"
            resources.append({
                "name": service_format,
                "description": "Access via ArcGIS REST API",
                "url": service_url,
                "format": service_format,
            })

        for idx, item in enumerate(attributes.get("additionalResources") or [], start=1):
            if not isinstance(item, dict):
                continue
            extra_url = item.get("url")
            if not extra_url:
                continue
            fallback_name = f"Additional Resource {idx}"
            resource_name = self._resource_name_from_additional(item, fallback_name)
            resources.append({
                "name": resource_name,
                "description": "Additional resource from ArcGIS Hub",
                "url": extra_url,
                "format": self._format_from_url(extra_url),
            })

        # Downloads intentionally omitted: keep only layers as resources.

        return resources

    def _generate_name(self, dataset_id: str, title: str) -> str:
        """
        Generate a CKAN-safe name with an optional portal prefix.
        """
        prefix = (self.name_prefix or "").strip("-_")
        if title:
            cleaned_title = self._slugify_ascii(title)
            if cleaned_title and len(cleaned_title) > 3 and not cleaned_title.isdigit():
                if cleaned_title not in (dataset_id or "").lower():
                    base_name = cleaned_title
                else:
                    base_name = self._slugify_ascii(dataset_id)
            else:
                base_name = self._slugify_ascii(dataset_id)
        else:
            base_name = self._slugify_ascii(dataset_id)
        
        name = f"{prefix}-{base_name}" if prefix else base_name
        name = self._slugify_ascii(name)
        return name[:100].strip("-_")
    
    def _map_license(
        self,
        arcgis_license: str = "",
        license_url: Optional[str] = None,
        license_name: Optional[str] = None,
    ) -> str:
        """
        Map ArcGIS license text to CKAN license IDs.
        """
        if not arcgis_license and not license_url and not license_name:
            return "notspecified"

        license_lower = (arcgis_license or "").lower()
        license_url_lower = (license_url or "").lower()
        license_name_lower = (license_name or "").lower()

        if license_name_lower == "none":
            return "notspecified"

        if "open-government-licence-ontario" in license_url_lower:
            return "ogl-ontario"
        if "open government licence" in license_lower and "ontario" in license_lower:
            return "ogl-ontario"
        if license_name_lower == "custom" and "ontario" in license_url_lower:
            return "ogl-ontario"
        if "cc0" in license_lower or "cc-0" in license_lower or "public domain" in license_lower:
            return "cc-zero"
        if "cc by-sa" in license_lower or "cc-by-sa" in license_lower:
            return "cc-by-sa"
        if "cc by" in license_lower or "cc-by" in license_lower or "cc by 4.0" in license_lower or "cc-by-4.0" in license_lower:
            return "cc-by"
        if "ogl" in license_lower or "open government" in license_lower:
            return "ogl-canada"
        if "odbl" in license_lower:
            return "odc-odbl"
        return "notspecified"

    def _license_id_from_url(self, license_url: str) -> str:
        parsed = urlparse(license_url)
        base = (parsed.netloc + parsed.path).strip("/")
        slug = self._slugify_ascii(base) or "custom-license"
        return f"custom-{slug}"[:100].strip("-_")

    def _apply_license(self, attributes: dict, target: dict) -> None:
        license_info = attributes.get("licenseInfo", "")
        structured_license = attributes.get("structuredLicense") or {}
        structured_text = structured_license.get("text")
        license_url = (
            structured_license.get("url")
            or self._extract_license_url(structured_text)
            or self._extract_license_url(license_info)
        )
        license_title = (
            self._strip_html(structured_text)
            or self._strip_html(license_info)
            or attributes.get("license")
            or ""
        )
        license_id = self._map_license(
            license_info,
            license_url=license_url,
            license_name=attributes.get("license"),
        )
        if license_id == "notspecified" and license_url:
            license_id = self._license_id_from_url(license_url)

        if license_id and license_title and license_url:
            ensure_license(self.build_context(), license_id, license_title, license_url)
        target["license_id"] = license_id
        target["license_title"] = license_title or license_info

    def iterate_imports(self):
        """
        Iterate all possible imports from the source API.
        Subclasses can override this to filter or transform datasets.
        """
        for dataset in self.all_datasets:
            attributes = dataset.get("attributes", {})
            if attributes.get("access") != "public":
                continue
            if self._should_skip_dataset(dataset):
                continue
            yield dataset

    def run_imports(self):
        """
        Run imports for all source datasets. Users should not override this.
        """
        self.running = True
        self.socket_client = SocketClient(self.job_id)
        self.logger = ImportLogger(base_logger, 0, self.socket_client)
        
        # Fetch all datasets from ArcGIS Hub
        self.all_datasets = get_all_datasets(
            self.base_api, 
            cb=lambda x: self.logger.info(x)
        )
        
        # Preprocess the datasets, includes filtering and adding extra data
        self.all_datasets = [*self.iterate_imports()]
        
        self.dataset_ids = [d['id'] for d in self.all_datasets]
        # Set the import size for reporting in the frontend
        self.logger.total = self.import_size = len(self.dataset_ids)
        
        # Make sure the socketio server is connected
        while not self.socket_client.registered:
            time.sleep(0.2)
            base_logger.info("Waiting socketio to be connected.")
        base_logger.info("socketio connected.")
        base_logger.info(f"Import size: {self.import_size}")

        # Check if datasets are deleted from the remote since last import
        if self.import_config.other_data is None:
            self.import_config.other_data = {}
        
        try:
            # Make sure remote endpoint is alive
            base_logger.info("Make sure remote endpoint is alive")
            if check_site_alive(self.base_api):
                
                # remote ID -> cudc ID
                imported_id_map = {}
                
                def _delete_all_imports():
                    for package_id_to_delete in get_package_ids_by_import_config_id(
                        self.build_context(), self.import_config.id
                    ):
                        try:
                            package_to_delete = get_self_package(
                                self.build_context(), package_id_to_delete
                            )
                            purge_package(self.build_context(), package_id_to_delete)
                            self.logger.finished_one(
                                'deleted', 
                                package_id_to_delete, 
                                package_to_delete['name'], 
                                package_to_delete['title']
                            )
                        except Exception as e:
                            self.logger.error(
                                f"ERROR: Failed to get package {package_id_to_delete} from remote"
                            )
                            self.logger.exception(e)
                
                if self.import_config.other_data.get("imported_id_map"):
                    imported_id_map = self.import_config.other_data["imported_id_map"]
                else:
                    # Backward compatibility without imported_id_map
                    # Delete all previous imports
                    _delete_all_imports()

                # Remove datasets that are removed from the remote
                if len(imported_id_map):
                    if self.import_config.other_config.get("delete_previously_imported"):
                        # Delete all datasets that were previously imported
                        _delete_all_imports()
                        imported_id_map = {}
                    else:
                        # Get all datasets that are deleted from the remote server, Remove them in ours
                        for dataset_id_to_remove in [
                            v for k, v in imported_id_map.items() 
                            if k not in self.dataset_ids
                        ]:
                            try:
                                package_to_delete = get_self_package(
                                    self.build_context(), dataset_id_to_remove
                                )
                                purge_package(self.build_context(), dataset_id_to_remove)
                                self.logger.finished_one(
                                    'deleted', 
                                    dataset_id_to_remove, 
                                    package_to_delete['name'], 
                                    package_to_delete['title']
                                )
                                # Remove from imported_id_map
                                keys_to_remove = [
                                    k for k, v in imported_id_map.items() 
                                    if v == dataset_id_to_remove
                                ]
                                for k in keys_to_remove:
                                    imported_id_map.pop(k, None)
                            except Exception as e:
                                self.logger.error(
                                    f"ERROR: Failed to get package {dataset_id_to_remove} from remote"
                                )
                                self.logger.exception(e)

                # Iterate remote datasets
                base_logger.info("Starting iteration")
                with ThreadPoolExecutor(max_workers=4) as executor:
                    self.socket_client.executor = executor
                    futures = {
                        executor.submit(
                            self.process_package, 
                            src, 
                            imported_id_map.get(src.get("id"))
                        ): src 
                        for src in self.all_datasets
                    }
                    for future in as_completed(futures):
                        try:
                            result = future.result()
                            if not result:
                                continue
                            remote_id, mapped_id, name = result
                            if mapped_id:
                                imported_id_map[remote_id] = mapped_id
                        except Exception as e:
                            self.logger.error('ERROR: A dataset import failed.')
                            self.logger.exception(e)
                        
                        if self.socket_client.stop_requested:
                            break
                    
                    # Cleanup
                    self.socket_client.executor = None
                
                self.import_config.other_data["imported_id_map"] = imported_id_map
                if self.import_config.other_data.get("imported_ids"):
                    del self.import_config.other_data["imported_ids"]
            else:
                self.logger.error(f'ERROR: Remote endpoint is not alive!')
            
        except Exception as e:
            self.logger.error(f'ERROR: Failed:')
            self.logger.exception(e)
        finally:
            self.socket_client.disconnect()
            self.socket_client = None
        
        self.running = False
    
    def test(self, use_cache=False, limit=None, max_results=None, example_limit=50, example_out=None):
        """
        Test import by fetching and mapping datasets without saving
        """
        self.test = True
        
        cache_file = f"/tmp/arcgis_datasets_{self.import_config.id}.json"

        if use_cache:
            # Check if there is a file with all datasets
            try:
                import json
                with open(cache_file, "r") as f:
                    self.all_datasets = json.load(f)
            except:
                self.all_datasets = get_all_datasets(self.base_api, max_results=max_results)
                # save all datasets to a file
                import json
                with open(cache_file, "w") as f:
                    json.dump(self.all_datasets, f)
        else:
            self.all_datasets = get_all_datasets(self.base_api, max_results=max_results)
            # save all datasets to a file
            import json
            with open(cache_file, "w") as f:
                json.dump(self.all_datasets, f)

        if max_results and len(self.all_datasets) > max_results:
            self.all_datasets = self.all_datasets[:max_results]

        # Collect example attributes for quick mapping review
        example = {}
        for src in self.all_datasets[:example_limit]:
            attributes = src.get("attributes") or {}
            for key, value in attributes.items():
                if key in example:
                    continue
                if value is None:
                    continue
                if isinstance(value, (list, dict)) and not value:
                    continue
                if isinstance(value, str) and not value.strip():
                    continue
                example[key] = value

        if example_out:
            import json
            with open(example_out, "w") as f:
                json.dump(example, f, indent=2)

        # Iterate all datasets and make sure no error occurred
        datasets_to_map = self.all_datasets[:limit] if limit else self.all_datasets
        for src in datasets_to_map:
            mapped = self.map_to_cudc_package(src, {})
