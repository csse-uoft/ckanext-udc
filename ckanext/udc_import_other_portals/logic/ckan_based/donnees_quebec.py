from ckanext.udc_import_other_portals.logic import CKANBasedImport

# Map Données Québec -> UDC
# one-to-one mapping without modification
package_mapping = {
    # CKAN Fields
    "id": "id",
    "title": "title",
    "author": "author",
    "author_email": "author_email",
    # "notes": "notes",  # handled separately for translation
    "metadata_created": "metadata_created",
    "metadata_modified": "metadata_modified",
    "version": "version",
    # CKAN Fields but not used in CUDC
    "maintainer": "maintainer",
    "maintainer_email": "maintainer_email",
}


# https://www.donneesquebec.ca/recherche/api/
class DonneesQuebecImport(CKANBasedImport):
    def before_create_organization(self, organization: dict, related_package: dict):
        """
        A hook to modify the organization before creating it.
        """
        # Use the organization title from the package
        if related_package.get("organization") and related_package["organization"].get("title"):
            organization["title"] = related_package["organization"]["title"]
        return organization

    def map_to_cudc_package(self, src: dict, target: dict):
        """
        Map source package to cudc package.

        Args:
            src (dict): The source package that needs to be mapped.
            target (dict): The target package to be populated.
        """
        from ckanext.udc_import_other_portals.logic.base import ensure_license
        import re

        global package_mapping

        # One-to-one Mapping
        for src_field in package_mapping:
            if package_mapping.get(src_field) and src.get(src_field):
                target[package_mapping[src_field]] = src[src_field]

        # name
        target["name"] = "donnees-quebec-" + src["name"]
        if len(target["name"]) > 100:
            target["name"] = target["name"][:100]
            
        # title translated
        if src.get("title"):
            target["title_translated"] = {
                "fr": src["title"],
            }
            
        # notes translated (description)
        if src.get("notes"):
            target["notes_translated"] = {
                "fr": src["notes"],
            }

        # location
        target["location"] = f"https://www.donneesquebec.ca/recherche/dataset/{src['name']}"

        # source (url field)
        if src.get("url"):
            target["url"] = src["url"]

        # Create License if not exists
        license_id = src.get("license_id")
        license_title = src.get("license_title")
        license_url = src.get("license_url")

        if license_id and license_title and license_url:
            ensure_license(self.build_context(), license_id, license_title, license_url)
            target["license_id"] = license_id

        # Tags
        if src.get("tags"):
            # Remove special characters from tags,
            # can only contain alphanumeric characters, spaces (" "), hyphens ("-"), underscores ("_") or dots (".")'
            tags = [re.sub(r"[^a-zA-Z0-9 ._-]", "", tag["name"]) for tag in src["tags"]]
            # Remove tags that are longer than 100 characters
            tags = [tag for tag in tags if len(tag) <= 100]
            # tags_translated expects a dict with language keys and list of strings as values
            target["tags_translated"] = {
                "fr": tags
            }

        # Groups -> theme
        if src.get("groups") and len(src["groups"]) > 0:
            themes = [group["title"] for group in src["groups"] if group.get("title")]
            if themes:
                target["theme"] = {
                    "fr": ", ".join(themes)
                }

        # Organization -> owner
        if src.get("organization") and src["organization"].get("title"):
            target["owner"] = {
                "fr": src["organization"]["title"]
            }

        # maintainer -> publisher
        if src.get("maintainer"):
            target["publisher"] = {
                "fr": src["maintainer"]
            }
        # maintainer_email -> publisher_email
        if src.get("maintainer_email"):
            target["publisher_email"] = src["maintainer_email"]

        # language
        if src.get("language"):
            lang = src["language"].upper()
            if lang == "FR":
                target["language"] = "http://id.loc.gov/vocabulary/iso639-1/fr"
            elif lang == "EN" or lang == "FR_EN":
                target["language"] = "http://id.loc.gov/vocabulary/iso639-1/en"

        # temporal -> time_span
        if src.get("temporal"):
            temporal = src["temporal"]
            # Parse temporal string like "2008-11-01- (Aujourd'hui -2 jours)"
            # or specific date ranges
            # target["time_span"] = temporal

        # ext_spatial -> geo_span
        if src.get("ext_spatial"):
            target["geo_span"] = {
                "fr": src["ext_spatial"]
            }

        # methodologie -> provenance
        if src.get("methodologie"):
            target["provenance"] = {
                "fr": src["methodologie"]
            }

        # Resources
        target["resources"] = []
        for resource in src.get("resources", []):
            target["resources"].append(
                {
                    # "id": resource["id"], // error will occur if id is used by other package
                    "name": resource.get("name"),
                    "url": resource.get("url"),
                    "format": resource.get("format"),
                    "mimetype": resource.get("mimetype"),
                    "mimetype_inner": resource.get("mimetype_inner"),
                    "last_modified": resource.get("last_modified"),
                    "description": resource.get("description"),
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
                print("loading packages")
                self.all_packages = json.load(f)
                print("all_packages loaded from file", len(self.all_packages))
        except:
            print("loading packages from api", self.base_api)
            self.all_packages = get_all_packages(self.base_api)
            # save all packages to a file
            import json

            with open("all_packages.json", "w") as f:
                json.dump(self.all_packages, f)
                print("all_packages saved", len(self.all_packages))

        # Iterate all packages and get an example of each property if it exists
        example = {}
        all_formats = {}
        all_licenses = {}
        all_languages = {}
        all_groups = {}
        all_update_frequencies = {}
        
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
                if key == "resources" and isinstance(src[key], list):
                    for resource in src[key]:
                        if resource.get("format"):
                            fmt = resource["format"]
                            all_formats[fmt] = all_formats.get(fmt, 0) + 1
                if key == "license_id":
                    lic = src[key]
                    all_licenses[lic] = all_licenses.get(lic, 0) + 1
                if key == "language":
                    lang = src[key]
                    if lang not in all_languages:
                        print("found new language:", lang, src.get("id"))
                    all_languages[lang] = all_languages.get(lang, 0) + 1
                if key == "groups" and isinstance(src[key], list):
                    for group in src[key]:
                        if group.get("title"):
                            grp = group["title"]
                            all_groups[grp] = all_groups.get(grp, 0) + 1
                if key == "update_frequency":
                    freq = src[key]
                    all_update_frequencies[freq] = all_update_frequencies.get(freq, 0) + 1

        # Remove resources from example for cleaner output
        if "resources" in example:
            del example["resources"]
            
        print("example", json.dumps(example, indent=2))
        print("all_formats (count):", sorted(all_formats.items(), key=lambda x: x[1], reverse=True))
        print("all_licenses (count):", sorted(all_licenses.items(), key=lambda x: x[1], reverse=True))
        print("all_languages (count):", sorted(all_languages.items(), key=lambda x: x[1], reverse=True))
        print("all_groups (count):", sorted(all_groups.items(), key=lambda x: x[1], reverse=True))
        print("all_update_frequencies (count):", sorted(all_update_frequencies.items(), key=lambda x: x[1], reverse=True))

        cnt = 0
        for src in self.iterate_imports():
            target = {
                "owner_org": self.import_config.owner_org,
                "type": "catalogue",
                "license_id": "notspecified",
            }
            mapped = self.map_to_cudc_package(src, target)
            cnt += 1
            # print("mapped", json.dumps(mapped, indent=2))
            # break
        print("Total packages to import:", cnt)


# Define which class should be used for import, CUDC will use it as an entrypoint
DefaultImportClass = DonneesQuebecImport


# main entry
if __name__ == "__main__":
    import uuid
    from ckanext.udc_import_other_portals.model import CUDCImportConfig

    import_log_data = {
        "id": str(uuid.uuid4()),
        "owner_org": "donnees-quebec",
        "run_by": "admin",
        "other_config": {
            "base_api": "https://www.donneesquebec.ca/recherche/api/",
        },
    }
    import_log = CUDCImportConfig(**import_log_data)
    import_ = DefaultImportClass(None, import_log, None)
    import_.test()
