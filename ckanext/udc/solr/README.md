# CKAN-UDC Solr Integration

This document explains how the UDC extension configures and uses Solr. It covers language handling, schema helpers, and index-time processing so you can safely adapt the search layer.

## Overview

UDC extends Solr in three areas:

- **Configuration helpers** (`solr/config.py`) expose the language list that drives multilingual fields and resolve the active user interface language.
- **Schema helpers** (`solr/helpers.py` and `solr/solr.py`) manage dynamic and static Solr fields for the maturity model, translated core fields, and tags.
- **Index pipeline hooks** (`solr/index.py`) rewrite CKAN package dictionaries before they reach Solr to populate language-aware text and facet fields.

At runtime the CKAN plugin uses these components to keep schema state aligned with the maturity model configuration and to emit multilingual documents.

## Language Configuration (`solr/config.py`)

### `get_udc_langs()`

- Reads `ckan.locale_default` as the primary language.
- Looks at `udc.multilingual.languages`, which should be a whitespace-separated list of locale codes (eg. `"en fr"`).
- Ensures the default language appears first and deduplicates the list.
- Result drives every place that needs the ordered language list (schema generation, indexing, helpers exposed to templates).

### `get_current_lang()`

- Returns the active UI language by calling `h.lang()`; falls back to the default locale.
- Useful when actions need to honor the visitor’s current locale, including facet caching and per-language Solr field selection.

### `pick_locale(texts, lang=None)`

- Lightweight helper for grabbing the best translation from a `{lang: text}` mapping.
- Preferences: explicitly passed `lang`, then active `h.lang()`, then English, finally the first available value.
- Used in misc contexts where Solr-related metadata needs a localized label.

## Solr Schema Utilities (`solr/helpers.py`)

### Connection Helpers

- `get_solr_config()` reads connection details from CKAN’s config (`SolrSettings.get()` plus request timeout) and normalizes the base URL.
  - All subsequent helpers call this to avoid duplicating configuration logic.

### Schema Inspection

- `get_fields()` calls `GET /schema/fields` and returns a dict keyed by field name.
- `get_extras_fields()` filters that map to keys starting with `extras_`.
- `get_field_types()` and `get_dynamic_fields()` pull definitions from `/schema/fieldtypes` and `/schema/dynamicfields` respectively.

### Schema Mutation

These helpers all call the Solr Schema API (`POST /schema`) and log results:

- `add_field(...)` and `delete_field(name)` maintain static fields (used for non-text maturity model extras and helper fields like `tags_ngram`).
- `add_dynamic_field(pattern, ...)` defines dynamic-field patterns (`*_en_txt`, `*_fr_f`, etc.).
- `add_copy_field(source, dest)` and `delete_copy_field(...)` manage copyField rules.
- `delete_extras_fields()` removes all `extras_*` fields – useful when resetting the schema during development.
- `ensure_language_dynamic_fields(langs)` is the key routine that guarantees each language has:
  - `*_<lang>_txt` dynamic fields for full-text search, picking `text_<lang>` analyzer when available, otherwise `text_general`.
  - `*_<lang>_f` dynamic fields for facet values (string + docValues, multivalued).

## Schema Alignment (`solr/solr.py`)

`update_solr_maturity_model_fields(maturity_model)` is the orchestration entry point. It should be called whenever the maturity model (metadata configuration) changes.

1. **Ensure language dynamic fields** via `ensure_language_dynamic_fields(get_udc_langs())`.
2. **Compute desired `extras_*` fields** for non-text maturity model fields:
   - `date`/`datetime` → Solr `date`
   - `number` → `pfloat`
   - `multiple_select` → multivalued `string`
   - `single_select` → single-valued `string`
   - Text fields are skipped because multilingual values are now stored per-language.
3. **Sync with Solr** using `get_extras_fields()`:
   - Remove obsolete fields (`delete_field`).
   - Recreate fields whose definition changed.
   - Add new fields with `add_field`.
4. **Guarantee `tags_ngram` field** exists for partial tag search, pairing it with a `copyField` from `tags` if missing.

⚠️ After modifying the schema you must reindex CKAN (and often restart Solr) to apply changes.

## Index-Time Transformations (`solr/index.py`)

UDC registers `before_dataset_index(pkg_dict)` as a CKAN search hook. It logs the incoming document for debugging, rewrites fields, and returns the modified dict.

Key steps:

1. Copy the original `pkg_dict` to avoid mutating CKAN internals; drop `related_packages` to keep the index lean.
2. Load language list with `get_udc_langs()` and track the default language (first entry).
3. Normalize maturity model multiple-select fields into `extras_<name>` arrays (split on commas) because CKAN stores them as comma-separated strings.
4. Normalize core translated fields:
   - Parse `title_translated` / `notes_translated` JSON (`_jsonish`).
   - Ensure the default language has a value by seeding from the core `title` / `notes` if necessary.
   - Write each language into dynamic fields: `title_<lang>_txt`, `notes_<lang>_txt`.
5. Handle tags:
   - Parse `tags_translated` and seed default language from core tags when not provided.
   - For each language emit `tags_<lang>_f` (for facets) and `tags_<lang>_txt` (search support).
6. Process maturity model text fields listed in the plugin’s `text_fields`:
   - Load JSON payload, drop any lingering `extras_<name>` text copies.
   - For each language populate `<name>_<lang>_txt` (search) and `<name>_<lang>_f` (facet).
7. Return the modified dict, which CKAN then hands off to Solr.

All helper functions (`_jsonish`, `_tag_names`) and log messages are designed to aid debugging complex multilingual payloads.

## Operational Notes

- **Reindexing**: Any schema change (dynamic field adjustments, new extras fields) requires rerunning `ckan search-index rebuild` after Solr restart.
- **Language additions**: Update `udc.multilingual.languages` and rerun `update_solr_maturity_model_fields`; reindex to backfill the new per-language fields.
- **Facet caching**: The actions layer caches facets per language using `get_current_lang()` so the frontend receives the correct translated facets.
- **Solr credentials**: All schema API helpers respect `SolrSettings.get()`, so CKAN’s existing Solr credentials apply.

## Related Components

- `ckanext/udc/plugin.py` wires `before_dataset_index` into CKAN’s search hooks and exposes helper lists (`text_fields`, `multiple_select_fields`).
- `ckanext/udc/search/logic/actions.py` uses `get_current_lang()` to request language-specific facets from Solr.

With this reference you can adapt schema behaviour, extend the index-time logic, or troubleshoot Solr integration issues within CKAN-UDC.
