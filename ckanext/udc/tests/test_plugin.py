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
import pytest

import ckan.plugins.toolkit as tk

import ckanext.udc.plugin as plugin
from ckanext.udc.i18n import (
    udc_json_load,
    udc_lang_object,
    udc_json_dump,
)


@pytest.fixture()
def udc_plugin():
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
