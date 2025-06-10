from ckanext.udc_import_other_portals.logic import CKANBasedImport

# Map gov of alberta -> UDC
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
    "version": "version"
}

language_direct_mapping = [
    'so', 'swh', 'hi', 'ar', 'it', 'uk', 'tl', 'ur', 'ku', 'cr', 'de', 'ko',  'am', 'fa', 'th', 'ti', 'ja', 'crk', 'pa', 'pl', 'es', 'vi', 'ro'
]
language_mapping = {
    "en-CA": "http://id.loc.gov/vocabulary/iso639-1/en",
    "fr-CA": "http://id.loc.gov/vocabulary/iso639-1/fr",
    "zh-cn": "http://id.loc.gov/vocabulary/iso639-1/zh",
    "zh-hk": "http://id.loc.gov/vocabulary/iso639-1/zh",
}

# Adding direct mapping for languages
for lang in language_direct_mapping:
    language_mapping[lang] = f"http://id.loc.gov/vocabulary/iso639-1/{lang}"

# Adding [default] to the mapping
for lang in {**language_mapping}:
    language_mapping[f"{lang} [default]"] = language_mapping[lang]
    

class AlbertaImport(CKANBasedImport):

    def iterate_imports(self):
        """
        Iterate all possible imports from the source api.
        """
        for package in self.all_packages:
            
            # Check for resources
            num_resources = len(package["resources"])
            
            # If there are no resources, skip it
            if num_resources == 0:
                continue
            
            # If all resources are PDF, skip it
            if num_resources >= 1 and all(
                resource.get("format", "").strip().lower() == "pdf" for resource in package["resources"]
            ):
                continue
            
            yield package

    def map_to_cudc_package(self, src: dict, target: dict):
        """
        Map source package to cudc package.

        Args:
            src (dict): The source package that needs to be mapped.
        """
        from ckanext.udc_import_other_portals.logic.base import ensure_license
        from datetime import datetime
        import re
    

        global package_mapping
        global language_mapping

        # One-to-one Mapping
        for src_field in package_mapping:
            if package_mapping.get(src_field) and src.get(src_field):
                target[package_mapping[src_field]] = src[src_field]

        # name
        target["name"] = "ab-" + src["name"]
        if len(target["name"]) > 100:
            target["name"] = target["name"][:100]
        
        # Src type
        package_type = src.get("type", "dataset")

        # Tags
        if src.get("tags"):
            tags = [re.sub(r"[^a-zA-Z0-9 ._-]", "", tag["name"]) for tag in src["tags"]]
            # Remove tags that are longer than 100 characters
            tags = [tag for tag in tags if len(tag) <= 100]
            target["tags"] = [{"name": tag} for tag in tags]

        # theme
        if src.get("topic"):
            topic = src["topic"]
            if isinstance(topic, list):
                topic = ", ".join(topic)
                target["theme"] = topic
        
        # Location
        target["location"] = f"https://open.alberta.ca/{package_type}/{src['name']}"

        # Source
        if src.get("url"):
            target["url"] = src["url"]

        # Create License if not exists
        license_id = src.get("license_id")
        license_title = src.get("license_title")
        license_url = src.get("license_url")

        if license_id and license_title and license_url:
            ensure_license(self.build_context(), license_id, license_title, license_url)
            target["license_id"] = license_id

        # maintainer -> publisher
        if src.get("maintainer"):
            target["publisher"] = src["maintainer"]
        # email -> publisher_email
        if src.get("email"):
            target["publisher_email"] = src["email"]
        
        # contact
        if src.get("contact"):
            target["access_steward"] = src["contact"]
        if src.get("contact_email"):
            target["access_steward_email"] = src["contact_email"]
        
        # Access Category
        if src.get("sensitivity"):
            target["access_category"] = src["sensitivity"]
            
        if src.get("time_coverage_from"):
            target["time_span_start"] = src["time_coverage_from"]
        
        if src.get("time_coverage_to"):
            target["time_span_start"] = src["time_coverage_to"]
            
        # spatialcoverage -> geo_span
        if src.get("spatialcoverage"):
            target["geo_span"] = src["spatialcoverage"]
            
        # language
        if src.get("language"):
            mapped_languages = []
            languages = src["language"]
            for language in languages:
                if language_mapping.get(language):
                    mapped_languages.append(language_mapping.get(language))
            target["language"] = ",".join(mapped_languages)
        
        # Owner
        if src.get("creator"):
            target["owner"] = "\n".join(src["creator"])
        
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
            print("loading packages from api", self.base_api)
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
        all_orgs = set()
        languages = set()
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
                if key == "organization":
                    if isinstance(src[key], dict):
                        all_orgs.add(src[key]["name"] + " (" + src[key]["title"] + ")")
                    else:
                        print("organization is not a dict", src[key])
                if key == "language":
                    if isinstance(src[key], list):
                        for lang in src[key]:
                            languages.add(lang)
                    else:
                        languages.add(src[key])
        del example["resources"]
        print("example", json.dumps(example, indent=2))
        print(all_formats)
        print(all_licenses)
        print(all_orgs)
        print("languages", languages)

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
        print("cnt", cnt)


# Define which class should be used for import, CUDC will use it as an entrypoint
DefaultImportClass = AlbertaImport


# main entry
if __name__ == "__main__":
    import uuid
    from ckanext.udc_import_other_portals.model import CUDCImportConfig

    import_log_data = {
        "id": str(uuid.uuid4()),
        "owner_org": "ab",
        "run_by": "admin",
        "other_config": {
            "base_api": "https://open.alberta.ca/api/",
        },
    }
    import_log = CUDCImportConfig(**import_log_data)
    import_ = DefaultImportClass(None, import_log, None)
    import_.test()
