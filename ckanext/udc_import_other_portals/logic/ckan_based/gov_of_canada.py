from ckanext.udc_import_other_portals.logic import CKANBasedImport

from datetime import datetime


# Map gov of canada -> UDC
# one-to-one mapping without modification
package_mapping = {
    # CKAN Fields
    "id": "id",
    "title": "title",
    "author": "author",
    "author_email": "author_email",
    "notes": "notes",
    "metadata_created": "metadata_created",
    "metadata_modified": "metadata_modified",
    "version": "version",
    # CKAN Fields but not used in CUDC
    "maintainer": "maintainer",
    "maintainer_email": "maintainer_email",
}


# Subject to Full Name
subject_mapping = {
    "law": "Law",
    "society_and_culture": "Society and Culture",
    "education_and_training": "Education and Training",
    "government_and_politics": "Government and Politics",
    "health_and_safety": "Health and Safety",
    "arts_music_literature": "Arts, Music, Literature",
    "science_and_technology": "Science and Technology",
    "military": "Military",
    "nature_and_environment": "Nature and Environment",
    "economics_and_industry": "Economics and Industry",
    "persons": "Persons",
    "history_and_archaeology": "History and Archaeology",
    "labour": "Labour",
    "transport": "Transport",
    "information_and_communications": "Information and Communications",
    "language_and_linguistics": "Language and Linguistics",
    "form_descriptors": "Form Descriptors",
    "processes": "Processes",
    "agriculture": "Agriculture",
}

# Topic to Full Name
topic_mapping = {
    "inland_waters": "Inland Waters",
    "structure": "Structure",
    "biota": "Biota",
    "farming": "Farming",
    "utilities_communication": "Utilities and Communication",
    "elevation": "Elevation",
    "planning_cadastre": "Planning Cadastre",
    "geoscientific_information": "Geoscientific Information",
    "economy": "Economy",
    "location": "Location",
    "oceans": "Oceans",
    "society": "Society",
    "health": "Health",
    "environment": "Environment",
    "transport": "Transport",
    "boundaries": "Boundaries",
    "imagery_base_maps_earth_cover": "Imagery Base Maps Earth Cover",
    "intelligence_military": "Intelligence Military",
    "climatology_meterology_atmosphere": "Climatology Meteorology Atmosphere",
}


class GovOfCanadaImport(CKANBasedImport):
    def __init__(self, context, import_config, job_id):
        super().__init__(
            context,
            import_config,
            job_id,
            # City of Toronto URL
            "https://open.canada.ca/data/api",
        )

    def iterate_imports(self):
        """
        Iterate all possible imports from the source api.
        """
        for package in self.all_packages:
            yield package

    def map_to_cudc_package(self, src: dict):
        """
        Map source package to cudc package.

        Args:
            src (dict): The source package that needs to be mapped.
        """
        from ckanext.udc_import_other_portals.logic.base import ensure_license
        import re

        # Default fields in CUDC
        target = {"owner_org": self.import_config.owner_org, "type": "catalogue"}

        global package_mapping, subject_mapping, topic_mapping

        # One-to-one Mapping
        for src_field in package_mapping:
            if package_mapping.get(src_field) and src.get(src_field):
                target[package_mapping[src_field]] = src[src_field]

        # Create License if not exists
        license_id = src.get("license_id")
        license_title = src.get("license_title")
        license_url = src.get("license_url")

        if license_id and license_title and license_url:
            ensure_license(
                self.build_context(), license_id, license_title, license_url
            )
            target["license_id"] = license_id

        # name
        target["name"] = "gov-canada-" + src["name"]
        
        # source
        target["url"] = f"https://open.canada.ca/data/en/dataset/{src['name']}"

        # Tags
        tags = []
        kw = src.get("keywords") or {}
        # not sure what `en-t-fr` means but it is english, could be english translated from french
        keywords_en = kw.get("en") or kw.get("en-t-fr")
        if isinstance(keywords_en, list) and len(keywords_en) > 0:
            tags = keywords_en
        
        # Add subject to tags
        if src.get("subject"):
            for subject in src["subject"]:
                if subject in subject_mapping:
                    tags.append(subject_mapping[subject])
        
        # Remove special characters from tags, 
        # can only contain alphanumeric characters, spaces (" "), hyphens ("-"), underscores ("_") or dots (".")'
        tags = [re.sub(r"[^a-zA-Z0-9 ._-]", "", tag) for tag in tags]
        # Remove tags that are longer than 100 characters
        tags = [tag for tag in tags if len(tag) <= 100]
        target["tags"] = [{"name": tag} for tag in tags]
        
        # topic -> theme
        theme = []
        if src.get("topic_category"):
            for topic in src["topic_category"]:
                if topic in topic_mapping:
                    theme.append(topic_mapping[topic])
        if len(theme) > 0:
            target["theme"] = ", ".join(theme)

        # maintainer -> publisher
        target["publisher"] = src["maintainer"]
        # maintainer_email -> publisher_email
        if src.get("maintainer_email"):
            target["publisher_email"] = src["maintainer_email"]

        # Organizaton -> onwer
        target["owner"] = src["organization"]["title"]

        # metadata_contact -> contact point (access_steward)
        metadata_contact = src.get("metadata_contact") or {}
        metadata_contact_en = metadata_contact.get("en") or metadata_contact.get("en-t-fr")
        if metadata_contact_en:
            # split and remove empty strings
            metadata_contact_en = [x.strip() for x in metadata_contact_en.split(",") if x.strip()]
            target["access_steward"] = ', '.join(metadata_contact_en)
        
        # DOI -> unique_identifier
        if src.get("digital_object_identifier"):
            target["unique_identifier"] = src.get("digital_object_identifier")
            target["global_unique_identifier"] = "Yes"
        
        # date_published -> published_date
        # "2019-07-23 17:53:27.345526" -> "2019-07-23"
        if src.get("date_published"):
            global datetime
            try:
                target["published_date"] = datetime.strptime(
                    src["date_published"], "%Y-%m-%d %H:%M:%S.%f"
                ).strftime("%Y-%m-%d")
            except:
                target["published_date"] = datetime.strptime(
                    src["date_published"], "%Y-%m-%d %H:%M:%S"
                ).strftime("%Y-%m-%d")

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

        # print("example", json.dumps(example, indent=2))
        print(all_subjects)
        print(all_topics)

        for src in self.all_packages:
            #
            mapped = self.map_to_cudc_package(src)
            # print("mapped", json.dumps(mapped, indent=2))
            # break


# Define which class should be used for import, CUDC will use it as an entrypoint
DefaultImportClass = GovOfCanadaImport

# main entry
if __name__ == "__main__":
    import uuid
    from ckanext.udc_import_other_portals.model import CUDCImportConfig

    import_log_data = {
        "id": str(uuid.uuid4()),
        "owner_org": "government-of-canada",
        "run_by": "admin",
    }
    import_log = CUDCImportConfig(**import_log_data)
    import_ = DefaultImportClass(None, import_log, None)
    import_.test()
