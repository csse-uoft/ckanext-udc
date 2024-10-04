from ckanext.udc_import_other_portals.logic import CKANBasedImport
from ckanext.udc_import_other_portals.logic.ckan_based.api import (
    import_package,
    get_package_ids,
    get_package,
)

# Map city of toronto -> UDC
# one-to-one mapping without modification
package_mapping = {
    "author": "author",
    "author_email": "author_email",
    # Try keeping the id same
    "id": "id",
    "last_refreshed": "",
    "metadata_created": "metadata_created",
    "metadata_modified": "metadata_modified",
    "notes": "notes",
    "title": "title",
    "topics": "theme",
    "version": "version",
    # CKAN Fields but not used in CUDC
    "maintainer": "maintainer",
    "maintainer_email": "maintainer_email",
}

format_mapping = {
    "XSD": "application/xml",
    "XLS": "application/vnd.ms-excel",
    "DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "KML": "application/vnd.google-earth.kml+xml",
    "DOC": "application/msword",
    "JPEG": "image/jpeg",
    "SHP": "application/vnd.shp",
    "JSON": "application/json",
    "GPKG": "application/geopackage+sqlite3",
    "XLSX": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "TXT": "text/plain",
    "ZIP": "application/zip",
    "CSV": "text/csv",
    "GEOJSON": "application/json",
    "WEB": "text/html",
    "RAR": "application/x-rar-compressed",
    "XLSM": "application/vnd.ms-excel.sheet.macroEnabled.12",
    "GZ": "application/x-gzip",
    # 'SAV': 'application/x-spss-sav', // Not registered yet at IANA
    "PDF": "application/pdf",
    "XML": "application/xml",
}


class CityOfTorontoImport(CKANBasedImport):
    def __init__(self, context, import_config, job_id):
        super().__init__(
            context,
            import_config,
            job_id,
            # City of Toronto URL
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/api",
        )

    def iterate_imports(self):
        """
        Iterate all possible imports from the source api.
        """
        import requests

        global get_package_ids, get_package

        for package in self.all_packages:
            # Get the quality of the package
            quality_data = (
                requests.get(
                    f"{self.base_api}/3/action/quality_show?package_id={package['id']}"
                )
                .json()
                .get("result")
            )

            if len(quality_data) > 0:
                package["quality"] = quality_data[0]

            yield package

    def map_to_cudc_package(self, src: dict):
        """
        Map source package to cudc package.

        Args:
            src (dict): The source package that needs to be mapped.
        """
        from ckanext.udc_import_other_portals.logic.base import ensure_license
        from datetime import datetime
        import re

        # Default fields in CUDC
        target = {
            "owner_org": self.import_config.owner_org,
            "type": "catalogue",
            "license_id": "notspecified",
        }

        global package_mapping

        # One-to-one Mapping
        for src_field in package_mapping:
            if package_mapping.get(src_field) and src.get(src_field):
                target[package_mapping[src_field]] = src[src_field]

        # name
        target["name"] = "city-toronto-" + src["name"]

        # Tags
        if src.get("tags"):
            tags = [re.sub(r"[^a-zA-Z0-9 ._-]", "", tag["name"]) for tag in src["tags"]]
            # Remove tags that are longer than 100 characters
            tags = [tag for tag in tags if len(tag) <= 100]
            target["tags"] = [{"name": tag} for tag in tags]

        # Location
        target["location"] = f"https://open.toronto.ca/dataset/{src['name']}"

        # Source
        if src.get("information_url"):
            target["url"] = src["information_url"]

        # Create License if not exists
        license_id = src.get("license_id")
        if license_id == "open-government-licence-toronto":
            # Open Government Licence – Toronto
            license_id = "https://open.toronto.ca/open-data-license/"
            ensure_license(
                self.build_context(),
                license_id,
                "Open Government Licence – Toronto",
                license_id,
            )
            target["license_id"] = license_id

        # File formats
        global format_mapping
        if src.get("formats"):
            formats = src["formats"].split(",")
            formats_iana = []
            for format in formats:
                mime_type = format_mapping.get(format)
                if mime_type:
                    formats_iana.append(
                        "https://www.iana.org/assignments/media-types/" + mime_type
                    )

            target["file_formats"] = ",".join(formats_iana)

        # date_published -> published_date
        # "2019-07-23 17:53:27.345526" -> "2019-07-23"
        if src.get("date_published"):
            try:
                target["published_date"] = datetime.strptime(
                    src["date_published"], "%Y-%m-%d %H:%M:%S.%f"
                ).strftime("%Y-%m-%d")
            except:
                target["published_date"] = datetime.strptime(
                    src["date_published"], "%Y-%m-%d %H:%M:%S"
                ).strftime("%Y-%m-%d")

        # maintainer -> publisher
        if src.get("maintainer"):
            target["publisher"] = src["maintainer"]
        # maintainer_email -> publisher_email
        if src.get("maintainer_email"):
            target["publisher_email"] = src["maintainer_email"]

        # Owner
        division = src.get("owner_division")
        unit = src.get("owner_unit")
        email = src.get("owner_email")

        owner = ", ".join([x for x in [division, unit, email] if x])
        if owner:
            target["owner"] = owner

        # Quality
        if src.get("quality"):
            score = src["quality"].get("score")
            grade = src["quality"].get("grade")
            recorded_at = src["quality"].get("recorded_at")
            if src.get("is_retired"):
                target["quality_annotation"] = (
                    "This dataset is retired. Its Data Quality Score will not "
                    "be calculated. The last recorded Data Quality Score was "
                    f"{float(score) * 100}% ({grade}) on {recorded_at}."
                )
            else:
                target["quality_annotation"] = (
                    f"Data Quality Score: {float(score) * 100}% ({grade}) as of {recorded_at}"
                )
            target["quality_dimension_metric"] = (
                "Data Quality is provided by the City of Toronto"
            )

        # Resources
        target["resources"] = []
        for resource in src["resources"]:
            target["resources"].append(
                {
                    # "id": resource["id"], // error will occur if id is used by other package
                    "name": resource["name"],
                    "url": resource.get("url"),
                    "format": resource.get("format"),
                    "mimetype": resource.get("mimetype"),
                    "mimetype_inner": resource.get("mimetype_inner"),
                    "last_modified": resource.get("last_modified"),
                }
            )
        return target

    def test(self):
        from ckanext.udc_import_other_portals.logic.ckan_based.api import (
            get_all_packages,
        )

        # Check if there is a file with all packages
        try:
            import json

            with open("all_packages.json", "r") as f:
                print("loadding packages")
                self.all_packages = json.load(f)
                print("all_packages loaded from file", len(self.all_packages))
        except:
            self.all_packages = get_all_packages(self.base_api)
            # save all packages to a file
            import json

            with open("all_packages.json", "w") as f:
                json.dump(self.all_packages, f)
                print("all_packages saved", len(self.all_packages))

        # Iterrate all packages and get an example of each property if it exists
        example = {}
        all_formats = set()
        all_licenses = set()
        for src in self.all_packages:
            for key in src:
                if key not in example:
                    if isinstance(src[key], list):
                        if len(src[key]) > 0:
                            example[key] = src[key]
                    elif isinstance(src[key], str):
                        if len(src[key]) > 0:
                            example[key] = src[key]
                    elif isinstance(src[key], dict):
                        if len(src[key]) > 0:
                            example[key] = src[key]
                if key == "formats":
                    all_formats.update(src[key].split(","))
                if key == "license_id":
                    all_licenses.add(src[key])
        del example["resources"]
        # print("example", json.dumps(example, indent=2))
        print(all_formats)
        print(all_licenses)

        for src in self.all_packages:
            #
            mapped = self.map_to_cudc_package(src)
            # print("mapped", json.dumps(mapped, indent=2))
            # break


# Define which class should be used for import, CUDC will use it as an entrypoint
DefaultImportClass = CityOfTorontoImport


# main entry
if __name__ == "__main__":
    import uuid
    from ckanext.udc_import_other_portals.model import CUDCImportConfig

    import_log_data = {
        "id": str(uuid.uuid4()),
        "owner_org": "city-of-toronto",
        "run_by": "admin",
    }
    import_log = CUDCImportConfig(**import_log_data)
    import_ = DefaultImportClass(None, import_log, None)
    import_.test()
