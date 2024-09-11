from ckanext.udc_import_other_portals.logic import CKANBasedImport
from ckanext.udc_import_other_portals.logic.ckan_based.api import import_package, get_package_ids, get_package

from datetime import datetime


# Map city of toronto -> UDC
# one-to-one mapping without modification
package_mapping = {
    "author": "author",
    "author_email": "author_email",
    # "Table", "Map"
    "formats": "file_format",
    # Try keeping the id same
    "id": "id",
    "information_url": "data_service",
    "last_refreshed": "",
    "license_id": "license_id",
    "maintainer": "maintainer",
    "maintainer_email": "maintainer_email",
    "metadata_created": "metadata_created",
    "metadata_modified": "metadata_modified",
    "name": "name",
    "notes": "notes",
    "owner_email": "owner",
    "title": "title",
    "topics": "theme",
    "version": "version",
}


class CityOfTorontoImport(CKANBasedImport):
    def __init__(self, context, import_config, job_id):
        super().__init__(
            context, import_config, job_id,
            # City of Toronto URL
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/api",
        )

    def iterate_imports(self):
        """
        Iterate all possible imports from the source api.
        """
        global get_package_ids, get_package
        packages_ids = get_package_ids(self.base_api)

        # Set the import size for reporting in the frontend
        # self.import_size = len(packages_ids)
        # yield get_package("c21f3bd1-e016-4469-abf5-c58bb8e8b5ce", self.base_api)
        for package_id in packages_ids:
            package = get_package(package_id, self.base_api)
            yield package

    def map_to_cudc_package(self, src: dict):
        """
        Map source package to cudc package.

        Args:
            src (dict): The source package that needs to be mapped.
        """
        # Default fields in CUDC
        target = {"owner_org": self.import_config.owner_org, "type": "catalogue"}

        global package_mapping

        # One-to-one Mapping
        for src_field in package_mapping:
            if package_mapping.get(src_field) and src.get(src_field):
                target[package_mapping[src_field]] = src[src_field]

        # name
        target["name"] = "toronto-" + src["name"]

        # Tags
        target["tags"] = src["tags"]

        # date_published -> published_date
        # "2019-07-23 17:53:27.345526" -> "2019-07-23"
        global datetime
        try:
            target["published_date"] = datetime.strptime(
                src["date_published"], "%Y-%m-%d %H:%M:%S.%f"
            ).strftime("%Y-%m-%d")
        except:
            target["published_date"] = datetime.strptime(
                src["date_published"], "%Y-%m-%d %H:%M:%S"
            ).strftime("%Y-%m-%d")
        
        # maintainer -> publisher
        target["publisher"] = src["maintainer"]
        # maintainer_email -> publisher_email
        target["publisher_email"] = src["maintainer_email"]

        # Resources
        target["resources"] = []
        for resource in src["resources"]:
            target["resources"].append(
                {
                    "id": resource["id"],
                    "name": resource["name"],
                    "url": resource.get("url"),
                    "format": resource.get("format"),
                    "mimetype": resource.get("mimetype"),
                    "mimetype_inner": resource.get("mimetype_inner"),
                    "last_modified": resource.get("last_modified"),
                }
            )
        return target


# Define which class should be used for import, CUDC will use it as an entrypoint
DefaultImportClass = CityOfTorontoImport
