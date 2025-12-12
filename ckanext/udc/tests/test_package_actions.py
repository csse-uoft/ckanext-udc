import json
import types
import uuid
from pathlib import Path

import pytest
import ckan.logic as logic
import ckan.model as model
import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
from configparser import ConfigParser
from sqlalchemy import create_engine
from ckan.tests import helpers as ckan_helpers

from ckanext.udc import helpers
from ckanext.udc import plugin as udc_plugin_module
from ckanext.udc.solr import solr as udc_solr


CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.example.json"


def _read_ini(path):
    parser = ConfigParser(defaults={"here": str(path.parent)})
    parser.read(path)
    data = dict(parser.defaults())
    if parser.has_section("app:main"):
        data.update(dict(parser.items("app:main")))
    return data


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_test_ckan():
    if tk.config.get("sqlalchemy.url"):
        return

    repo_root = Path(__file__).resolve().parents[4]
    core_conf = _read_ini(repo_root / "ckan/test-core.ini")
    ext_conf = _read_ini(Path(__file__).resolve().parents[3] / "test.ini")
    conf = {**core_conf, **ext_conf}
    conf.pop("use", None)
    conf.setdefault("ckan.site_url", "http://test.ckan.local")
    conf.setdefault("ckan.locale_default", "en")
    conf.setdefault("udc.multilingual.languages", "en fr")
    conf.setdefault("ckan.base_public_folder", "public")
    conf.setdefault("ckan.base_templates_folder", "templates")
    conf.setdefault("ckan.auth.create_unowned_dataset", "true")
    conf.setdefault("ckan.storage_path", "/tmp")

    cfg = tk.config
    for key, value in conf.items():
        cfg[key] = value

    engine = create_engine(conf["sqlalchemy.url"])
    model.init_model(engine)
    model.repo.init_db()


@pytest.fixture
def stub_udc_plugin(monkeypatch):
    plugin = types.SimpleNamespace(disable_graphdb=False)
    monkeypatch.setattr(helpers.plugins, "get_plugin", lambda name: plugin)
    return plugin


@pytest.fixture
def udc_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    for level in data.get("maturity_model", []):
        for field in level.get("fields", []):
            if field.get("type") in {"multiple_select", "single_select"}:
                field.setdefault("options", [])

    return data


@pytest.fixture
def udc_plugin_instance(monkeypatch, udc_config):
    udc_solr.update_solr_maturity_model_fields(udc_config["maturity_model"])
    monkeypatch.setattr(udc_plugin_module, "update_solr_maturity_model_fields", lambda *_: None)
    plugin = plugins.get_plugin("udc")
    if plugin is None:
        plugins.load("udc")
        plugin = plugins.get_plugin("udc")
    plugin.disable_graphdb = True
    plugin.reload_config(udc_config)
    return plugin


@pytest.fixture
def clean_db():
    ckan_helpers.reset_db()
    try:
        yield
    finally:
        model.Session.remove()


def test_package_update_runs_preprocessor_and_updates_graph(monkeypatch, stub_udc_plugin):
    calls = []

    def fake_before(context, data_dict):
        calls.append(("before", data_dict.get("file_format")))
        data_dict["file_format"] = "normalized"

    def fake_action(context, data_dict):
        calls.append(("action", data_dict.get("file_format")))
        return {"id": "pkg", "file_format": "normalized"}

    def fake_graph(context, result_dict):
        calls.append(("graph", result_dict.get("file_format")))

    monkeypatch.setattr(helpers, "before_package_update_for_file_format", fake_before)
    monkeypatch.setattr(helpers, "onUpdateCatalogue", fake_graph)

    result = helpers.package_update(fake_action, {"user": "tester"}, {"file_format": "csv"})

    assert result == {"id": "pkg", "file_format": "normalized"}
    assert calls == [
        ("before", "csv"),
        ("action", "normalized"),
        ("graph", "normalized"),
    ]


def test_package_update_wraps_graph_errors(monkeypatch, stub_udc_plugin):
    monkeypatch.setattr(helpers, "before_package_update_for_file_format", lambda *_: None)

    def fake_action(context, data_dict):
        return {"ok": True}

    def boom(context, data_dict):
        raise RuntimeError("boom")

    monkeypatch.setattr(helpers, "onUpdateCatalogue", boom)

    with pytest.raises(logic.ValidationError) as excinfo:
        helpers.package_update(fake_action, {}, {})

    messages = excinfo.value.error_dict.get("message")
    assert messages
    assert "Error occurred in updating the knowledge graph" in messages[0]


def test_package_update_skips_graph_when_disabled(monkeypatch, stub_udc_plugin):
    stub_udc_plugin.disable_graphdb = True
    monkeypatch.setattr(helpers, "before_package_update_for_file_format", lambda *_: None)

    def fake_action(context, data_dict):
        data_dict["visited"] = True
        return {"ok": True}

    def fail(*_):
        raise AssertionError("graph should be skipped")

    monkeypatch.setattr(helpers, "onUpdateCatalogue", fail)

    payload = {}
    result = helpers.package_update(fake_action, {}, payload)

    assert result == {"ok": True}
    assert payload["visited"] is True


def test_package_delete_invokes_graph(monkeypatch, stub_udc_plugin):
    calls = []

    def fake_action(context, data_dict):
        calls.append("action")
        return {"id": data_dict.get("id")}

    def fake_graph(context, data_dict):
        calls.append("graph")

    monkeypatch.setattr(helpers, "onDeleteCatalogue", fake_graph)

    result = helpers.package_delete(fake_action, {}, {"id": "pkg"})

    assert result == {"id": "pkg"}
    assert calls == ["action", "graph"]


def test_package_delete_wraps_graph_errors(monkeypatch, stub_udc_plugin):
    def fake_action(context, data_dict):
        return {"id": data_dict.get("id")}

    def boom(context, data_dict):
        raise RuntimeError("boom")

    monkeypatch.setattr(helpers, "onDeleteCatalogue", boom)

    with pytest.raises(logic.ValidationError) as excinfo:
        helpers.package_delete(fake_action, {}, {"id": "pkg"})

    messages = excinfo.value.error_dict.get("message")
    assert messages
    assert "Error occurred in updating the knowledge graph" in messages[0]


def test_package_delete_skips_graph_when_disabled(monkeypatch, stub_udc_plugin):
    stub_udc_plugin.disable_graphdb = True

    def fake_action(context, data_dict):
        return {"id": data_dict.get("id")}

    def fail(*_):
        raise AssertionError("graph should be skipped")

    monkeypatch.setattr(helpers, "onDeleteCatalogue", fail)

    result = helpers.package_delete(fake_action, {}, {"id": "pkg"})

    assert result == {"id": "pkg"}


pytestmark = pytest.mark.ckan_config("udc.multilingual.languages", "en fr")


def _create_multilingual_dataset(plugin):
    context = {"model": model, "session": model.Session, "schema": plugin.create_package_schema()}
    data = {
        "name": f"udc-{uuid.uuid4().hex[:8]}",
        "title": "Multilingual Dataset",
        "title_translated": {"en": "Multilingual Dataset", "fr": "Jeu de données multilingue"},
        "notes_translated": {"en": "English description", "fr": "Description française"},
        "tags_translated": {"en": ["roads", "traffic"], "fr": ["routes"]},
        "theme": {"en": "transport", "fr": "transport-fr"},
        "type": "dataset",
    }
    return ckan_helpers.call_action("package_create", context=context, **data)


@pytest.mark.usefixtures("clean_db")
def test_package_create_handles_multilingual_fields(udc_plugin_instance):
    created = _create_multilingual_dataset(udc_plugin_instance)

    show_context = {"model": model, "session": model.Session, "schema": udc_plugin_instance.show_package_schema()}
    shown = ckan_helpers.call_action("package_show", context=show_context, id=created["id"])

    # Verify multilingual fields are stored
    assert shown["title_translated"]["en"] == "Multilingual Dataset"
    assert shown["title_translated"]["fr"] == "Jeu de données multilingue"
    assert shown["notes_translated"]["en"] == "English description"
    assert shown["notes_translated"]["fr"] == "Description française"
    assert shown["tags_translated"]["en"] == ["roads", "traffic"]
    assert shown["tags_translated"]["fr"] == ["routes"]
    assert shown["theme"] == {"en": "transport", "fr": "transport-fr"}


@pytest.mark.usefixtures("clean_db")
def test_package_update_persists_multilingual_changes(udc_plugin_instance):
    created = _create_multilingual_dataset(udc_plugin_instance)

    show_context = {"model": model, "session": model.Session, "schema": udc_plugin_instance.show_package_schema()}
    pkg = ckan_helpers.call_action("package_show", context=show_context, id=created["id"])

    pkg["title_translated"] = {"en": "Updated Title", "fr": "Titre mis à jour"}
    pkg["notes_translated"] = {"en": "Updated English", "fr": "Description mise à jour"}
    pkg["theme"] = {"en": "economy", "fr": "économie"}
    pkg["tags_translated"] = {"en": ["economy"], "fr": ["économie"]}
    pkg.pop("tags", None)

    update_context = {"model": model, "session": model.Session, "schema": udc_plugin_instance.update_package_schema()}
    ckan_helpers.call_action("package_update", context=update_context, **pkg)

    refreshed = ckan_helpers.call_action("package_show", context=show_context, id=created["id"])

    # Verify multilingual fields are updated
    assert refreshed["title_translated"]["en"] == "Updated Title"
    assert refreshed["title_translated"]["fr"] == "Titre mis à jour"
    assert refreshed["notes_translated"]["en"] == "Updated English"
    assert refreshed["notes_translated"]["fr"] == "Description mise à jour"
    assert refreshed["theme"] == {"en": "economy", "fr": "économie"}
    assert refreshed["tags_translated"]["en"] == ["economy"]
    assert refreshed["tags_translated"]["fr"] == ["économie"]


@pytest.mark.usefixtures("clean_db")
def test_package_delete_succeeds_with_multilingual_extras(udc_plugin_instance):
    created = _create_multilingual_dataset(udc_plugin_instance)

    delete_context = {"model": model, "session": model.Session, "ignore_auth": True}
    ckan_helpers.call_action("package_delete", context=delete_context, id=created["id"])

    # Verify package is marked as deleted
    show_context = {
        "model": model,
        "session": model.Session,
        "schema": udc_plugin_instance.show_package_schema(),
        "ignore_auth": True,
    }
    deleted = ckan_helpers.call_action(
        "package_show",
        context=show_context,
        id=created["id"],
    )

    assert deleted["state"] == "deleted"
    assert deleted["theme"] == {"en": "transport", "fr": "transport-fr"}
