from types import SimpleNamespace

import pytest

from ckanext.udc.solr import config as solr_config


class DummyConfig:
    def __init__(self, values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


def test_get_udc_langs_includes_default_and_dedupes(monkeypatch):
    dummy = DummyConfig(
        {
            "ckan.locale_default": "fr",
            "udc.multilingual.languages": "en es en fr",
        }
    )
    monkeypatch.setattr(solr_config, "config", dummy)

    assert solr_config.get_udc_langs() == ["fr", "en", "es"]


def test_get_current_lang_falls_back_to_default(monkeypatch):
    dummy = DummyConfig({"ckan.locale_default": "es"})
    monkeypatch.setattr(solr_config, "config", dummy)
    monkeypatch.setattr(solr_config, "h", SimpleNamespace(lang=lambda: None))

    assert solr_config.get_current_lang() == "es"


def test_pick_locale_prefers_requested_language(monkeypatch):
    monkeypatch.setattr(solr_config, "h", SimpleNamespace(lang=lambda: "fr"))

    texts = {"en": "Hello", "fr": "Bonjour", "es": "Hola"}

    assert solr_config.pick_locale(texts, lang="es") == "Hola"
    assert solr_config.pick_locale(texts) == "Bonjour"
    assert solr_config.pick_locale("plain text") == "plain text"
    assert solr_config.pick_locale({}) == ""

    fallback_texts = {"en": "Hello", "de": "Hallo"}
    # When current language missing, it should fall back to English
    monkeypatch.setattr(solr_config, "h", SimpleNamespace(lang=lambda: "it"))
    assert solr_config.pick_locale(fallback_texts) == "Hello"
