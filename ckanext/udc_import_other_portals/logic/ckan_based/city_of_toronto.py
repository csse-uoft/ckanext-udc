from ckanext.udc_import_other_portals.logic import CKANBasedImport

from datetime import datetime


# Map city of toronto -> UDC
# one-to-one mapping without modification
package_mapping = {
    "author": "author",
    "author_email": "author_email",
    # "Table", "Map"
    "dataset_category": "",
    # In "2019-07-23 17:53:27.345526"
    "date_published": "",
    # Short description
    "excerpt": "",
    # Comma separated, free text
    "formats": "file_format",
    # Try keeping the id same
    "id": "id",
    "information_url": "data_service",
    # String "true", "false"
    "is_retired": "",
    # Boolean true, false
    "isopen": "",
    # ?
    "last_refreshed": "",
    "license_id": "license_id",
    # Same as the `license_id`
    "license_title": "",
    # CKAN Field, we don't use it
    "maintainer": "maintainer",  # keep it?
    "maintainer_email": "maintainer_email",  # keep it?
    # CKAN Internal field that track the create/update time
    "metadata_created": "metadata_created",
    "metadata_modified": "metadata_modified",
    # string id, "polls-conducted-by-the-city"
    "name": "name",
    "notes": "notes",
    # "City Clerk's Office"
    "owner_division": "",
    # We don't have it
    "owner_email": "owner",
    # Daily
    "refresh_rate": "",
    # active
    "state": "",
    "title": "title",
    "topics": "theme",
    "version": "version",
    # Removed
    "excerpt": "",
    "groups": "",
    "num_resources": "",
    "num_tags": "",
    "organization": "",
    "owner_org": "",
    "private": "",
    "relationships_as_object": "",
    "relationships_as_subject": "",
}

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
    def __init__(self):
        super().__init__(
            # City of Toronto URL
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/api",
        )

    def map_to_cudc_package(self, src: dict):
        """
        Map source package to cudc package.

        Args:
            src (dict): The source package that needs to be mapped.
        """
        # Default fields in CUDC
        target = {"owner_org": "city-of-toronto-open-data", "type": "catalogue"}
        
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
        target["published_date"] = datetime.fromisoformat(
            src["date_published"]
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
