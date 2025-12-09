"""
Please note that applying this solr schema changes will require a reindex of the dataset.
Probably also rebooting the solr server after the changes then reindex.

Available Field Types: (Also see <solr_url>/schema/fieldtypes)
----------------------
- string:
    - Exact match only, no tokenization or analysis.
    - Use for IDs, keywords, or non-searchable fields.
    - Used by license (id), tags, organization, title_string, url, version
    - Used for retrieving facets. 

- text
    - Natural language search (e.g., descriptions, long-form text)

- text_general:
    - Tokenized text with lowercase filter and word splitting.
    - Good for full-text search.
    - General text search without stemming (e.g., titles, keywords)

- text_ngram:
    - Tokenized text with lowercase filter, n-gram tokenization.
    - Good for Autocomplete, Fuzzy Matching, Partial-Word Search
    - Used by name_ngram, title_ngram.

- boolean:
    - Stores `true` or `false` values.

- pint:
    - 32-bit signed integer (numeric).

- plong:
    - 64-bit signed integer (for large numbers).

- pfloat:
    - Single-precision floating point number.

- pdouble:
    - Double-precision floating point number.

- date:
    - ISO 8601 format (`YYYY-MM-DDThh:mm:ssZ`).
    - Supports range queries.

"""

from __future__ import annotations
import logging

from .helpers import get_fields, get_extras_fields, delete_extras_fields, add_copy_field, delete_copy_field, add_field, delete_field, ensure_language_dynamic_fields
from .config import get_udc_langs

log = logging.getLogger(__name__)


def update_solr_maturity_model_fields(maturity_model: list):
    """
    Update Solr schema to include fields needed by the maturity model AND
    multilingual search/facets.

    Text fields in the maturity model are now multilingual JSON, so we DO NOT
    create 'extras_<name>' text fields anymore. Instead, the indexer writes to:
      <name>_<lang>_txt (search)
      <name>_<lang>_f   (facets)

    Non-text types (date/number/select) still use 'extras_<name>'.
    """
    # 1) Ensure dynamic language fields
    langs = get_udc_langs()
    ensure_language_dynamic_fields(langs)

    # 2) Build the static 'extras_*' fields for NON-text types only
    new_fields = {}
    for level in maturity_model:
        for field in level.get("fields", []):
            if "ckanField" in field:
                continue

            ftype = field.get("type")
            name = field["name"]
            key = f"extras_{name}"

            # TEXT -> multilingual JSON now; do not add 'extras_<name>'
            if ftype is None or ftype == "text":
                continue

            elif ftype in ("date", "datetime", "time"):
                new_fields[key] = {
                    "name": key,
                    "type": "date",
                    "multiValued": False,
                    "indexed": True,
                    "stored": True,
                    "docValues": True,
                }

            elif ftype == "number":
                new_fields[key] = {
                    "name": key,
                    "type": "pfloat",
                    "multiValued": False,
                    "indexed": True,
                    "stored": True,
                    "docValues": True,
                }

            elif ftype in ("multiple_select", "multiple_datasets"):
                new_fields[key] = {
                    "name": key,
                    "type": "string",
                    "multiValued": True,
                    "stored": True,
                    "indexed": True,
                }

            elif ftype in ("single_select", "single_dataset"):
                new_fields[key] = {
                    "name": key,
                    "type": "string",
                    "multiValued": False,
                    "indexed": True,
                    "stored": True,
                }

            else:
                raise ValueError(f"Unknown field type: {ftype}")

    # 3) Reconcile against existing 'extras_*' fields in Solr
    current_fields = get_extras_fields()

    # delete/replace changed or obsolete fields
    for current_field_name, current_field in current_fields.items():
        if current_field_name not in new_fields:
            # If we used to index a text field here, drop it now (we're multilingual)
            delete_field(current_field_name)
        else:
            desired = new_fields[current_field_name]
            if (
                desired["type"] != current_field["type"]
                or desired["indexed"] != current_field["indexed"]
                or desired["stored"] != current_field["stored"]
                or desired["multiValued"] != current_field.get("multiValued", False)
                or desired.get("docValues", False) != current_field.get("docValues", False)
            ):
                delete_field(current_field_name)
                add_field(
                    desired["name"],
                    desired["type"],
                    desired["indexed"],
                    desired["stored"],
                    desired["multiValued"],
                    desired.get("docValues", False),
                )
            # remove from "to add"
            new_fields.pop(current_field_name)

    # add remaining new fields
    for _, f in new_fields.items():
        add_field(
            f["name"],
            f["type"],
            f["indexed"],
            f["stored"],
            f["multiValued"],
            f.get("docValues", False),
        )

    if not new_fields:
        log.info("No new 'extras_*' fields to add.")
    else:
        log.info(f"Added {len(new_fields)} new 'extras_*' fields.")

    # 4) Keep tags partial-search helper
    all_fields = get_fields()
    if "tags_ngram" not in all_fields:
        add_field("tags_ngram", "text_ngram", indexed=True, stored=True, multi_valued=True)
        add_copy_field("tags", "tags_ngram")
        log.info("Added tags_ngram field.")
    else:
        log.info("tags_ngram field already exists.")

    all_fields = get_fields()

    # 5) Ensure version relationship helper fields exist and are multiValued strings
    #    These are populated by the before_dataset_index hook from JSON version metadata.
    version_fields = [
        "version_dataset_url",
        "version_dataset_title_url",
        "dataset_versions_url",
        "dataset_versions_title_url",
    ]

    for fname in version_fields:
        fdef = all_fields.get(fname)
        if not fdef:
            add_field(fname, "string", indexed=True, stored=True, multi_valued=True)
            log.info("Added version field %s as multiValued string", fname)
        else:
            needs_update = (
                fdef.get("type") != "string"
                or not fdef.get("indexed", False)
                or not fdef.get("stored", False)
                or not fdef.get("multiValued", False)
            )
            if needs_update:
                delete_field(fname)
                add_field(fname, "string", indexed=True, stored=True, multi_valued=True)
                log.info("Replaced version field %s as multiValued string", fname)
