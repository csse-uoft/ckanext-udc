"""
Tests for graph/mapping_helpers.py - Helper functions for JSON-LD mapping.

Tests all helper functions that are available in the mapping configuration,
including UUID generation, type conversions, URL quoting, and CKAN-specific mappings.
"""
import pytest
from datetime import datetime
from rdflib import Literal, XSD
from unittest.mock import Mock, patch

from ckanext.udc.graph.mapping_helpers import (
    generate_uuid,
    to_integer,
    to_float,
    to_date,
    to_bool,
    mapFromCKANLicense,
    split_to_uris,
    quote_url,
    mapFromCKANTags,
    map_from_tags_multiple_languages,
    map_to_multiple_languages,
    map_to_single_language,
    map_to_multiple_datasets,
    uuidMap,
    licenseMap
)
from ckanext.udc.graph.contants import EMPTY_FIELD


class TestGenerateUuid:
    """Test UUID generation with and without keys."""

    def test_generate_uuid_without_key(self):
        """Test that UUID is generated without a key."""
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()
        
        assert uuid1 != uuid2
        assert len(uuid1) == 36  # Standard UUID format

    def test_generate_uuid_with_key(self):
        """Test that same key returns same UUID."""
        uuid1 = generate_uuid("test_key")
        uuid2 = generate_uuid("test_key")
        
        assert uuid1 == uuid2

    def test_generate_uuid_different_keys(self):
        """Test that different keys return different UUIDs."""
        uuid1 = generate_uuid("key1")
        uuid2 = generate_uuid("key2")
        
        assert uuid1 != uuid2

    def test_uuid_persistence_in_map(self):
        """Test that UUID is stored in uuidMap."""
        key = "persistent_key"
        uuid = generate_uuid(key)
        
        assert key in uuidMap
        assert uuidMap[key] == uuid


class TestTypeConversions:
    """Test type conversion functions."""

    def test_to_integer_valid(self):
        """Test converting valid string to integer."""
        assert to_integer("42") == 42
        assert to_integer("0") == 0
        assert to_integer("-10") == -10

    def test_to_integer_invalid(self):
        """Test that invalid strings raise ValueError."""
        with pytest.raises(ValueError):
            to_integer("not a number")

    def test_to_float_valid(self):
        """Test converting valid string to float."""
        assert to_float("3.14") == 3.14
        assert to_float("0.0") == 0.0
        assert to_float("-2.5") == -2.5

    def test_to_float_invalid(self):
        """Test that invalid strings raise ValueError."""
        with pytest.raises(ValueError):
            to_float("not a float")

    def test_to_date_valid(self):
        """Test converting valid date string to XSD date."""
        result = to_date("2025-01-15")
        assert isinstance(result, Literal)
        assert result.datatype == XSD.date

    def test_to_date_empty_string(self):
        """Test that empty string returns EMPTY_FIELD."""
        assert to_date("") == EMPTY_FIELD

    def test_to_date_empty_field(self):
        """Test that EMPTY_FIELD returns EMPTY_FIELD."""
        assert to_date(EMPTY_FIELD) == EMPTY_FIELD

    def test_to_bool_yes(self):
        """Test converting 'yes' to boolean."""
        assert to_bool("yes") == "true"
        assert to_bool("Yes") == "true"
        assert to_bool("YES") == "true"

    def test_to_bool_no(self):
        """Test converting 'no' to boolean."""
        assert to_bool("no") == "false"
        assert to_bool("No") == "false"
        assert to_bool("NO") == "false"

    def test_to_bool_other(self):
        """Test that other values don't return true/false."""
        assert to_bool("maybe") is None
        assert to_bool("") is None


class TestMapFromCKANLicense:
    """Test CKAN license mapping."""

    def setUp(self):
        """Clear license map before each test."""
        licenseMap.clear()

    @patch('ckan.model.Package.get_license_register')
    def test_map_license_by_id(self, mock_get_register):
        """Test mapping license by ID."""
        mock_license = Mock()
        mock_license.url = "http://creativecommons.org/licenses/by/4.0/"
        mock_get_register.return_value = {"cc-by": mock_license}
        
        licenseMap.clear()
        result = mapFromCKANLicense("cc-by")
        
        assert len(result) == 1
        assert result[0]["@id"] == "http://creativecommons.org/licenses/by/4.0/"

    @patch('ckan.model.Package.get_license_register')
    def test_map_license_by_url(self, mock_get_register):
        """Test mapping license by URL."""
        mock_get_register.return_value = {}
        
        licenseMap.clear()
        url = "http://example.com/custom-license"
        result = mapFromCKANLicense(url)
        
        assert len(result) == 1
        assert result[0]["@id"] == url

    @patch('ckan.model.Package.get_license_register')
    def test_map_license_without_url(self, mock_get_register):
        """Test mapping license ID without URL in registry."""
        mock_license = Mock()
        mock_license.url = None
        mock_get_register.return_value = {"custom": mock_license}
        
        licenseMap.clear()
        result = mapFromCKANLicense("custom")
        
        assert len(result) == 1
        assert result[0]["@id"] == "http://data.urbandatacentre.ca/licenses/custom"


class TestSplitToUris:
    """Test URI splitting function."""

    def test_split_comma_separated(self):
        """Test splitting comma-separated URIs."""
        result = split_to_uris("csv,json,xml")
        
        assert len(result) == 3
        assert {"@id": "csv"} in result
        assert {"@id": "json"} in result
        assert {"@id": "xml"} in result

    def test_split_custom_separator(self):
        """Test splitting with custom separator."""
        result = split_to_uris("csv|json|xml", separator="|")
        
        assert len(result) == 3

    def test_split_single_value(self):
        """Test splitting single value."""
        result = split_to_uris("csv")
        
        assert len(result) == 1
        assert result[0]["@id"] == "csv"

    def test_split_empty_string(self):
        """Test splitting empty string."""
        result = split_to_uris("")
        
        assert len(result) == 1
        assert result[0]["@id"] == ""


class TestQuoteUrl:
    """Test URL quoting function."""

    def test_quote_http_url(self):
        """Test quoting HTTP URL."""
        url = "http://example.com/path with spaces"
        result = quote_url(url)
        
        assert result == "http://example.com/path%20with%20spaces"

    def test_quote_https_url(self):
        """Test quoting HTTPS URL."""
        url = "https://example.com/path with spaces"
        result = quote_url(url)
        
        assert result == "https://example.com/path%20with%20spaces"

    def test_quote_preserves_slashes(self):
        """Test that slashes are preserved in path."""
        url = "http://example.com/path/to/resource"
        result = quote_url(url)
        
        assert result == "http://example.com/path/to/resource"

    def test_quote_special_characters(self):
        """Test quoting special characters."""
        url = "http://example.com/data?key=value&foo=bar"
        result = quote_url(url)
        
        assert "?" in result
        assert "&" in result

    def test_quote_unicode_characters(self):
        """Test quoting unicode characters."""
        url = "http://example.com/données"
        result = quote_url(url)
        
        assert "donn%C3%A9es" in result


class TestMapFromCKANTags:
    """Test CKAN tags mapping."""

    def test_map_single_tag(self):
        """Test mapping single tag."""
        result = mapFromCKANTags("housing")
        
        assert len(result) == 1
        assert result[0]["@value"] == "housing"

    def test_map_multiple_tags(self):
        """Test mapping multiple comma-separated tags."""
        result = mapFromCKANTags("housing,transport,health")
        
        assert len(result) == 3
        assert {"@value": "housing"} in result
        assert {"@value": "transport"} in result
        assert {"@value": "health"} in result

    def test_map_tags_with_whitespace(self):
        """Test that whitespace is stripped from tags."""
        result = mapFromCKANTags("housing , transport , health")
        
        assert result[0]["@value"] == "housing"
        assert result[1]["@value"] == "transport"
        assert result[2]["@value"] == "health"


class TestMapFromTagsMultipleLanguages:
    """Test multilingual tags mapping."""

    def test_map_multilingual_tags(self):
        """Test mapping tags with multiple languages."""
        tags_dict = {
            "en": ["housing", "transport"],
            "fr": ["logement", "transport"]
        }
        
        result = map_from_tags_multiple_languages(tags_dict)
        
        assert len(result) == 4
        assert {"@language": "en", "@value": "housing"} in result
        assert {"@language": "en", "@value": "transport"} in result
        assert {"@language": "fr", "@value": "logement"} in result
        assert {"@language": "fr", "@value": "transport"} in result

    def test_map_single_language_tags(self):
        """Test mapping tags with single language."""
        tags_dict = {"en": ["housing", "transport"]}
        
        result = map_from_tags_multiple_languages(tags_dict)
        
        assert len(result) == 2
        assert all(tag["@language"] == "en" for tag in result)

    def test_map_empty_tags(self):
        """Test mapping empty tags dictionary."""
        result = map_from_tags_multiple_languages({})
        
        assert len(result) == 0


class TestMapToMultipleLanguages:
    """Test mapping values to multiple languages."""

    @patch('ckanext.udc.graph.mapping_helpers.get_default_lang')
    def test_map_dict_to_languages(self, mock_get_default_lang):
        """Test mapping dictionary to language array."""
        val = {"en": "English", "fr": "Français"}
        result = map_to_multiple_languages(val)
        
        assert len(result) == 2
        assert {"@language": "en", "@value": "English"} in result
        assert {"@language": "fr", "@value": "Français"} in result

    @patch('ckanext.udc.graph.mapping_helpers.get_default_lang')
    def test_map_string_to_default_language(self, mock_get_default_lang):
        """Test mapping string to default language."""
        mock_get_default_lang.return_value = "en"
        
        val = "English text"
        result = map_to_multiple_languages(val)
        
        assert len(result) == 1
        assert result[0]["@language"] == "en"
        assert result[0]["@value"] == "English text"

    def test_map_non_dict_non_string(self):
        """Test mapping non-dict, non-string value."""
        result = map_to_multiple_languages(123)
        
        assert len(result) == 0


class TestMapToSingleLanguage:
    """Test mapping values to single language."""

    @patch('ckanext.udc.graph.mapping_helpers.get_default_lang')
    def test_map_dict_to_specific_language(self, mock_get_default_lang):
        """Test mapping dictionary to specific language."""
        val = {"en": "English", "fr": "Français"}
        result = map_to_single_language(val, lang="fr")
        
        assert result == "Français"

    @patch('ckanext.udc.graph.mapping_helpers.get_default_lang')
    def test_map_dict_to_default_language(self, mock_get_default_lang):
        """Test mapping dictionary to default language when requested lang not available."""
        mock_get_default_lang.return_value = "en"
        
        val = {"en": "English", "fr": "Français"}
        result = map_to_single_language(val, lang="es")
        
        assert result == "English"

    def test_map_string_to_language(self):
        """Test mapping string returns as-is."""
        val = "Some text"
        result = map_to_single_language(val, lang="en")
        
        assert result == "Some text"

    def test_map_non_dict_non_string(self):
        """Test mapping non-dict, non-string value."""
        result = map_to_single_language(123, lang="en")
        
        assert result == ""


class TestMapToMultipleDatasets:
    """Test mapping to multiple datasets."""

    def test_map_datasets_with_ids(self):
        """Test mapping datasets with IDs."""
        datasets = [
            {"id": "http://example.com/dataset1"},
            {"id": "http://example.com/dataset2"}
        ]
        
        result = map_to_multiple_datasets(datasets)
        
        assert len(result) == 2
        assert result[0]["@id"] == "http://example.com/dataset1"
        assert result[0]["@type"] == "dcat:Dataset"
        assert result[1]["@id"] == "http://example.com/dataset2"

    def test_map_datasets_without_ids(self):
        """Test mapping datasets without IDs are skipped."""
        datasets = [
            {"title": "Dataset 1"},
            {"id": "http://example.com/dataset2"}
        ]
        
        result = map_to_multiple_datasets(datasets)
        
        assert len(result) == 1
        assert result[0]["@id"] == "http://example.com/dataset2"

    def test_map_empty_datasets(self):
        """Test mapping empty dataset list."""
        result = map_to_multiple_datasets([])
        
        assert len(result) == 0


class TestIntegrationScenarios:
    """Integration tests combining multiple helper functions."""

    @patch('ckan.model.Package.get_license_register')
    @patch('ckanext.udc.graph.mapping_helpers.get_default_lang')
    def test_complete_catalogue_mapping(self, mock_get_default_lang, mock_get_register):
        """Test a complete catalogue entry mapping scenario."""
        mock_get_default_lang.return_value = "en"
        mock_license = Mock()
        mock_license.url = "http://creativecommons.org/licenses/by/4.0/"
        mock_get_register.return_value = {"cc-by": mock_license}
        
        # Simulate mapping a catalogue entry
        licenseMap.clear()
        
        title = map_to_multiple_languages({"en": "Housing Data", "fr": "Données sur le logement"})
        tags = map_from_tags_multiple_languages({"en": ["housing", "urban"], "fr": ["logement", "urbain"]})
        license_info = mapFromCKANLicense("cc-by")
        formats = split_to_uris("csv,json")
        published = to_date("2025-01-01")
        url = quote_url("http://example.com/data with spaces")
        
        assert len(title) == 2
        assert len(tags) == 4
        assert license_info[0]["@id"] == "http://creativecommons.org/licenses/by/4.0/"
        assert len(formats) == 2
        assert isinstance(published, Literal)
        assert "with%20spaces" in url
