"""
Tests for plugin.py.

Tests are written using the pytest library (https://docs.pytest.org), and you
should read the testing guidelines in the CKAN docs:
https://docs.ckan.org/en/2.9/contributing/testing.html

To write tests for your extension you should install the pytest-ckan package:

    pip install pytest-ckan

This will allow you to use CKAN specific fixtures on your tests.

For instance, if your test involves database access you can use `clean_db` to
reset the database:

    import pytest

    from ckan.tests import factories

    @pytest.mark.usefixtures("clean_db")
    def test_some_action():

        dataset = factories.Dataset()

        # ...

For functional tests that involve requests to the application, you can use the
`app` fixture:

    from ckan.plugins import toolkit

    def test_some_endpoint(app):

        url = toolkit.url_for('myblueprint.some_endpoint')

        response = app.get(url)

        assert response.status_code == 200


To temporary patch the CKAN configuration for the duration of a test you can use:

    import pytest

    @pytest.mark.ckan_config("ckanext.myext.some_key", "some_value")
    def test_some_action():
        pass
"""
from pathlib import Path
from types import SimpleNamespace

import pytest

import ckan.plugins.toolkit as tk

import ckanext.udc.plugin as plugin
from ckanext.udc.solr import index as udc_index
from ckanext.udc.solr import solr as udc_solr
from ckanext.udc.i18n import (
    udc_json_load,
    udc_lang_object,
    udc_json_dump,
)


@pytest.fixture()
def udc_plugin(monkeypatch):
    monkeypatch.setattr(plugin, "update_solr_maturity_model_fields", lambda *_args, **_kwargs: None)

    instance = plugin.UdcPlugin()
    # Force a clean slate for each test since the plugin stores state on the instance
    instance.disable_graphdb = True
    instance.sparql_client = None
    instance.all_fields = []
    instance.facet_titles = {}
    instance.facet_titles_raw = {}
    instance.text_fields = []
    instance.date_fields = []
    instance.multiple_select_fields = []
    instance.dropdown_options = {}
    instance.maturity_model = []
    instance.mappings = {}
    instance.preload_ontologies = {}
    return instance


def _sample_config():
    return {
        "maturity_model": [
            {
                "title": "Level 1",
                "name": "lvl1",
                "fields": [
                    {"name": "text_field", "label": "Text Field", "type": "text"},
                    {"name": "date_field", "label": "Date Field", "type": "date"},
                    {
                        "name": "multi_field",
                        "label": "Multi Field",
                        "type": "multiple_select",
                        "options": [
                            {"value": "opt-a", "text": "Option A"},
                            {"value": "opt-b", "text": "Option B"},
                        ],
                    },
                    {
                        "name": "single_field",
                        "label": "Single Field",
                        "type": "single_select",
                        "options": [
                            {"value": "one", "text": "One"},
                        ],
                    },
                ],
            }
        ],
        "mappings": {"foo": "bar"},
        "preload_ontologies": {"example": "value"},
    }


def test_reload_config_populates_field_metadata(udc_plugin):
    udc_plugin.reload_config(_sample_config())

    assert udc_plugin.all_fields == [
        "text_field",
        "date_field",
        "multi_field",
        "single_field",
    ]
    assert udc_plugin.text_fields == ["text_field"]
    assert udc_plugin.date_fields == ["date_field"]
    assert udc_plugin.multiple_select_fields == ["multi_field"]
    assert udc_plugin.dropdown_options["multi_field"] == {
        "opt-a": "Option A",
        "opt-b": "Option B",
    }
    assert udc_plugin.facet_titles["single_field"] == "Single Field"
    assert udc_plugin.mappings == {"foo": "bar"}
    assert udc_plugin.preload_ontologies == {"example": "value"}


def test_modify_package_schema_applies_expected_validators(udc_plugin):
    udc_plugin.reload_config(_sample_config())

    base_schema = {}
    schema = udc_plugin._modify_package_schema(base_schema)

    ignore_missing = tk.get_validator("ignore_missing")
    convert_to_extras = tk.get_converter("convert_to_extras")

    text_pipeline = schema["text_field"]
    assert text_pipeline[0] == ignore_missing
    # text fields should round-trip JSON with multilingual helpers
    assert udc_json_load in text_pipeline
    assert udc_lang_object in text_pipeline
    assert udc_json_dump in text_pipeline
    assert text_pipeline[-1] == convert_to_extras

    number_pipeline = schema["date_field"]
    assert number_pipeline == [ignore_missing, convert_to_extras]


def test_reload_config_supports_portal_type_ckan_field(udc_plugin):
    config = {
        "maturity_model": [
            {
                "title": "Level 1",
                "name": "lvl1",
                "fields": [
                    {
                        "ckanField": "portal_type",
                        "label": {"en": "Portal type", "fr": "Type de portail"},
                        "type": "single_select",
                        "options": [
                            {"value": "CKAN", "text": "CKAN"},
                            {"value": "ArcGIS", "text": "ArcGIS"},
                        ],
                    }
                ],
            }
        ],
        "mappings": {},
        "preload_ontologies": {},
    }

    udc_plugin.reload_config(config)

    assert udc_plugin.facet_titles["portal_type"] == "Portal type"
    assert udc_plugin.dropdown_options["portal_type"] == {
        "CKAN": "CKAN",
        "ArcGIS": "ArcGIS",
    }


def test_ckan_fields_template_supports_portal_type_macro():
    template_path = Path(__file__).resolve().parents[1] / "templates" / "package" / "macros" / "ckan_fields.html"
    content = template_path.read_text()

    assert "{% macro portal_type(data, errors, short_description=\"\", long_description=\"\") %}" in content
    assert "'portal_type'" in content


def test_update_solr_fields_includes_portal_type(monkeypatch):
    added_fields = []

    monkeypatch.setattr(udc_solr, "get_udc_langs", lambda: ["en", "fr"])
    monkeypatch.setattr(udc_solr, "ensure_language_dynamic_fields", lambda langs: None)
    monkeypatch.setattr(udc_solr, "get_extras_fields", lambda: {})
    monkeypatch.setattr(udc_solr, "get_fields", lambda: {"tags_ngram": {}})
    monkeypatch.setattr(udc_solr, "add_copy_field", lambda *args, **kwargs: None)
    monkeypatch.setattr(udc_solr, "delete_copy_field", lambda *args, **kwargs: None)
    monkeypatch.setattr(udc_solr, "delete_field", lambda *args, **kwargs: None)
    monkeypatch.setattr(udc_solr, "add_field", lambda *args, **kwargs: added_fields.append((args, kwargs)))

    udc_solr.update_solr_maturity_model_fields([
        {
            "title": "Level 1",
            "name": "lvl1",
            "fields": [
                {
                    "ckanField": "portal_type",
                    "label": {"en": "Portal type"},
                    "type": "single_select",
                    "options": [
                        {"value": "ArcGIS", "text": "ArcGIS"},
                        {"value": "CKAN", "text": "CKAN"},
                    ],
                }
            ],
        }
    ])

    field_names = [call[0][0] for call in added_fields]
    assert "extras_portal_type" in field_names

    portal_type_call = next(call for call in added_fields if call[0][0] == "extras_portal_type")
    assert portal_type_call[0][1] == "string"
    assert portal_type_call[0][4] is True


def test_before_dataset_index_handles_plain_text_values_for_text_fields(monkeypatch):
    mock_plugin = SimpleNamespace(
        multiple_select_fields=[],
        text_fields=["unique_identifier"],
    )

    monkeypatch.setattr(udc_index.plugins, "get_plugin", lambda _name: mock_plugin)
    monkeypatch.setattr(udc_index, "get_udc_langs", lambda: ["en", "fr"])

    indexed = udc_index.before_dataset_index(
        {
            "id": "pkg-1",
            "name": "example-dataset",
            "title": "Example Dataset",
            "notes": "Example notes",
            "unique_identifier": "10",
        }
    )

    assert indexed["unique_identifier_en_txt"] == "10"
    assert indexed["unique_identifier_en_f"] == ["10"]
    assert "unique_identifier_fr_txt" not in indexed
