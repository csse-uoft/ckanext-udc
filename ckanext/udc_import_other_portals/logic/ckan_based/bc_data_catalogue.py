from ckanext.udc_import_other_portals.logic import CKANBasedImport

# Map BC Data Catalogue -> UDC
# one-to-one mapping without modification
package_mapping = {
    # CKAN Fields
    "id": "id",
    "title": "title",
    # "author": "author",  # Author is uuid
    # "author_email": "author_email",  # N/A
    "notes": "notes",
    "metadata_created": "metadata_created",
    "metadata_modified": "metadata_modified",
}


# https://catalogue.data.gov.bc.ca/api/
class BCDataCatalogueImport(CKANBasedImport):

    def iterate_imports(self):
        """
        Iterate all possible imports from the source api.
        """
        for package in self.all_packages:
            yield package
        

    def map_to_cudc_package(self, src: dict, target: dict):
        """
        Map source package to cudc package.

        Args:
            src (dict): The source package that needs to be mapped.
        """
        from ckanext.udc_import_other_portals.logic.base import (
            ensure_license,
        )
        import re

        # Default fields in CUDC
        global package_mapping

        # One-to-one Mapping
        for src_field in package_mapping:
            if package_mapping.get(src_field) and src.get(src_field):
                target[package_mapping[src_field]] = src[src_field]

        # Create License if not exists
        license_id = src.get("license_url") # use license_url as id
        license_title = src.get("license_title")
        license_url = src.get("license_url")

        if license_id and license_title and license_url:
            ensure_license(self.build_context(), license_id, license_title, license_url)
            target["license_id"] = license_id

        # name
        target["name"] = "bc-data-catalogue-" + src["name"]
        if len(target["name"]) > 100:
            target["name"] = target["name"][:100]

        # location
        target["location"] = f"https://catalogue.data.gov.bc.ca/dataset/{src['name']}"
        
        # source
        # "more_info": [
        #       {
        #         "description": "B.C. Drought Information Portal",
        #         "url": "https://droughtportal.gov.bc.ca/"
        #       }
        #     ],
        if src.get("more_info"):
            more_info = src["more_info"]
            if isinstance(more_info, list) and len(more_info) > 0:
                target["url"] = more_info[0].get("url")

        # Tags
        if src.get("tags"):
            # Remove special characters from tags,
            # can only contain alphanumeric characters, spaces (" "), hyphens ("-"), underscores ("_") or dots (".")'
            tags = [re.sub(r"[^a-zA-Z0-9 ._-]", "", tag["name"]) for tag in src["tags"]]
            # Remove tags that are longer than 100 characters
            tags = [tag for tag in tags if len(tag) <= 100]
            target["tags"] = [{"name": tag} for tag in tags]

        # Organization -> owner
        target["owner"] = src["organization"]["title"]

        # contact -> contact point (access_steward + access_steward_email)
        # "contacts": [
        #     {
        #       "displayed": [
        #         "displayed"
        #       ],
        #       "email": "GeoBCInfo@gov.bc.ca",
        #       "name": "GeoBC Inquiries",
        #       "org": "e51a8106-11c7-4436-a967-7cee18bfb159",
        #       "role": "pointOfContact"
        #     }
        #   ],
        
        if src.get("contacts"):
            contacts = src["contacts"]
            if isinstance(contacts, list) and len(contacts) > 0:
                contact = contacts[0]
                if contact.get("name"):
                    target["access_steward"] = contact["name"]
                if contact.get("email"):
                    target["access_steward_email"] = contact["email"]
                
        # record_publish_date -> published_date
        if src.get("record_publish_date"):
            target["published_date"] = src["record_publish_date"]
            
        # lineage_statement -> provenance
        if src.get("lineage_statement"):
            target["provenance"] = src["lineage_statement"]

        # Resources
        target["resources"] = []
        for resource in src["resources"]:
            target["resources"].append({
                    # "id": resource["id"], // error will occur if id is used by other package
                    "name": resource["name"],
                    "url": resource.get("url") if resource.get("url") else f"https://catalogue.data.gov.bc.ca/dataset/{src['name']}/resource/{resource['id']}",
                    "format": resource.get("format"),
                    "mimetype": resource.get("mimetype"),
                    "mimetype_inner": resource.get("mimetype_inner"),
                    "last_modified": resource.get("last_modified"),
                })
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
        all_subjects = set()
        all_topics = set()
        all_orgs = dict()
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
                if key == "subject":
                    all_subjects.update(src[key])
                if key == "topic_category":
                    all_topics.update(src[key])
                    print(src["id"], src["name"])
                if key == "owner_org":
                    if src[key] not in all_orgs:
                        all_orgs[src[key]] = src["organization"]

        # print("example", json.dumps(example, indent=2))
        # dump to file
        # with open("example_package.json", "w") as f:
        #     json.dump(example, f, indent=2)
        # print(all_subjects)
        # print(all_topics)
        # print(all_orgs)
        

        for src in self.all_packages:
            target = {
                "owner_org": self.import_config.owner_org,
                "type": "catalogue",
                "license_id": "notspecified",
            }
            
            mapped = self.map_to_cudc_package(src, target)
            # print("mapped", json.dumps(mapped, indent=2))
            # break


# Define which class should be used for import, CUDC will use it as an entrypoint
DefaultImportClass = BCDataCatalogueImport

# main entry
if __name__ == "__main__":
    import uuid
    from ckanext.udc_import_other_portals.model import CUDCImportConfig

    import_log_data = {
        "id": str(uuid.uuid4()),
        "owner_org": "bc-data-catalogue",
        "run_by": "admin",
        "other_config": {
            "base_api": "https://catalogue.data.gov.bc.ca/api/",
        }
    }
    import_log = CUDCImportConfig(**import_log_data)
    import_ = DefaultImportClass(None, import_log, None)
    import_.test()
