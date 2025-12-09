"""
Tests for graph/template.py - JSON-LD template compilation logic.

Tests the compile_template and compile_with_temp_value functions that parse
the mapping config into JSON-LD data.
"""
import pytest
from unittest.mock import Mock, patch
from ckanext.udc.graph.template import (
    compile_template,
    compile_with_temp_value,
    is_all_attrs_starts_with_at,
    filter_out_empty_values
)
from ckanext.udc.graph.contants import EMPTY_FIELD


@pytest.fixture(autouse=True)
def mock_udc_plugin():
    """Mock the UDC plugin for all tests."""
    with patch('ckanext.udc.graph.template.get_plugin') as mock_get_plugin:
        mock_plugin = Mock()
        mock_plugin.text_fields = []
        mock_get_plugin.return_value = mock_plugin
        yield mock_plugin


class TestIsAllAttrsStartsWithAt:
    """Test the is_all_attrs_starts_with_at helper function."""

    def test_all_attrs_start_with_at(self):
        """Test when all attributes start with @."""
        data = {"@id": "test", "@type": "Dataset", "@value": "hello"}
        assert is_all_attrs_starts_with_at(data) is True

    def test_some_attrs_dont_start_with_at(self):
        """Test when some attributes don't start with @."""
        data = {"@id": "test", "name": "Dataset", "@value": "hello"}
        assert is_all_attrs_starts_with_at(data) is False

    def test_empty_dict(self):
        """Test with empty dictionary."""
        data = {}
        assert is_all_attrs_starts_with_at(data) is True


class TestFilterOutEmptyValues:
    """Test the filter_out_empty_values function."""

    def test_filter_empty_dicts(self):
        """Test filtering out empty dictionaries."""
        data = [{"name": "test"}, {}, {"@id": "uri"}]
        result = filter_out_empty_values(data)
        assert len(result) == 2
        assert {} not in result

    def test_filter_only_id_dicts(self):
        """Test keeping dictionaries with only @id."""
        data = [{"@id": "uri1"}, {"@id": "uri2", "name": "test"}]
        result = filter_out_empty_values(data)
        assert len(result) == 2

    def test_filter_at_attrs_without_value(self):
        """Test filtering @ attributes without @value."""
        data = [
            {"@type": "xsd:string", "@language": "en"},  # No @value
            {"@type": "xsd:string", "@value": "hello"},
        ]
        result = filter_out_empty_values(data)
        assert len(result) == 1
        assert result[0]["@value"] == "hello"


class TestCompileTemplate:
    """Test the compile_template function."""

    def test_simple_string_substitution(self):
        """Test simple f-string style substitution."""
        template = ["{name}"]
        global_vars = {}
        local_vars = {"name": "TestDataset"}
        
        result = compile_template(template, global_vars, local_vars)
        assert result == "TestDataset"

    def test_empty_string_becomes_empty_field(self):
        """Test that empty strings are converted to EMPTY_FIELD."""
        template = ["{name}"]
        global_vars = {}
        local_vars = {"name": ""}
        
        result = compile_template(template, global_vars, local_vars)
        assert result == []

    def test_nested_dict_compilation(self):
        """Test compilation of nested dictionary structures."""
        template = [{
            "@id": "http://example.com/{id}",
            "@type": "Dataset",
            "name": "{title}"
        }]
        global_vars = {}
        local_vars = {"id": "123", "title": "Test Dataset"}
        
        result = compile_template(template, global_vars, local_vars)
        assert result["@id"] == "http://example.com/123"
        assert result["@type"] == "Dataset"
        assert result["name"] == "Test Dataset"

    def test_eval_expression(self):
        """Test eval() expressions in templates."""
        template = [{
            "@value": "eval(title.upper())"
        }]
        global_vars = {}
        local_vars = {"title": "hello"}
        
        result = compile_template(template, global_vars, local_vars)
        assert result == "HELLO"

    def test_eval_with_helper_function(self):
        """Test eval() with helper functions."""
        def to_uppercase(val):
            return val.upper()
        
        template = [{
            "@value": "eval(to_uppercase(name))"
        }]
        global_vars = {"to_uppercase": to_uppercase}
        local_vars = {"name": "dataset"}
        
        result = compile_template(template, global_vars, local_vars)
        assert result == "DATASET"

    def test_eval_with_text_field_localization(self, mock_udc_plugin):
        """Test eval() with localized text fields."""
        # Configure the mock plugin for this test
        mock_udc_plugin.text_fields = ["title"]
        
        def map_to_multiple_languages(val):
            if isinstance(val, dict):
                return [{"@language": lang, "@value": value} 
                       for lang, value in val.items()]
            return [{"@language": "en", "@value": val}]
        
        template = [{
            "title": "eval(title)"
        }]
        global_vars = {"map_to_multiple_languages": map_to_multiple_languages}
        local_vars = {"title": {"en": "English Title", "fr": "Titre français"}}
        
        result = compile_template(template, global_vars, local_vars)
        assert len(result["title"]) == 2
        assert any(item.get("@language") == "en" and item.get("@value") == "English Title" 
                   for item in result["title"])
        assert any(item.get("@language") == "fr" and item.get("@value") == "Titre français" 
                   for item in result["title"])

    def test_nested_list_compilation(self):
        """Test compilation of nested lists."""
        template = [{
            "@id": "http://example.com/dataset",
            "keywords": [
                {"@value": "{keyword1}"},
                {"@value": "{keyword2}"}
            ]
        }]
        global_vars = {}
        local_vars = {"keyword1": "housing", "keyword2": "transport"}
        
        result = compile_template(template, global_vars, local_vars)
        assert len(result["keywords"]) == 2
        assert result["keywords"][0]["@value"] == "housing"
        assert result["keywords"][1]["@value"] == "transport"

    def test_remove_empty_nested_attrs(self):
        """Test that empty nested attributes are removed."""
        template = [{
            "@id": "http://example.com/dataset",
            "title": "{title}",
            "description": "{description}"  # Will be empty
        }]
        global_vars = {}
        local_vars = {"title": "Test", "description": ""}
        
        result = compile_template(template, global_vars, local_vars)
        assert "title" in result
        assert "description" not in result

    def test_undefined_variable_handling(self):
        """Test that undefined variables are handled gracefully."""
        template = [{
            "@id": "http://example.com/dataset",
            "name": "{undefined_var}"
        }]
        global_vars = {}
        local_vars = {}
        
        result = compile_template(template, global_vars, local_vars)
        assert "name" not in result

    def test_complex_nested_structure(self):
        """Test complex nested structure compilation."""
        template = [{
            "@id": "http://example.com/catalogue/{id}",
            "@type": "Catalogue",
            "publisher": [{
                "@id": "http://example.com/org/{org_id}",
                "@type": "Organization",
                "name": "{org_name}",
                "email": "{org_email}"
            }]
        }]
        global_vars = {}
        local_vars = {
            "id": "cat123",
            "org_id": "org456",
            "org_name": "Test Org",
            "org_email": "test@example.com"
        }
        
        result = compile_template(template, global_vars, local_vars)
        assert result["@id"] == "http://example.com/catalogue/cat123"
        assert len(result["publisher"]) == 1
        assert result["publisher"][0]["@id"] == "http://example.com/org/org456"
        assert result["publisher"][0]["name"] == "Test Org"


class TestCompileWithTempValue:
    """Test the compile_with_temp_value function."""

    def test_simple_substitution(self):
        """Test simple substitution with available values."""
        mappings = [{"@id": "http://example.com/{id}", "name": "{name}"}]
        global_vars = {}
        local_vars = {"id": "123", "name": "Test"}
        
        result = compile_with_temp_value(mappings, global_vars, local_vars)
        assert result["@id"] == "http://example.com/123"
        assert result["name"] == "Test"

    def test_temp_value_for_undefined_vars(self):
        """Test that undefined variables are replaced with TEMP_VALUE."""
        mappings = [{"@id": "http://example.com/{id}", "name": "{undefined}"}]
        global_vars = {}
        local_vars = {"id": "123"}
        
        result = compile_with_temp_value(mappings, global_vars, local_vars)
        assert result["@id"] == "http://example.com/123"
        assert result["name"] == "TEMP_VALUE"

    def test_nested_temp_values(self):
        """Test temp values in nested structures."""
        mappings = [{
            "@id": "http://example.com/cat",
            "creator": [{
                "@id": "http://example.com/person/{person_id}",
                "name": "{person_name}"
            }]
        }]
        global_vars = {}
        local_vars = {}
        
        result = compile_with_temp_value(mappings, global_vars, local_vars)
        assert "TEMP_VALUE" in result["creator"]["@id"]
        assert result["creator"]["name"] == "TEMP_VALUE"

    def test_preserves_structure(self):
        """Test that the structure is preserved even with missing values."""
        mappings = [{
            "@id": "uri",
            "title": "{title}",
            "description": "{desc}",
            "publisher": [{
                "name": "{pub_name}"
            }]
        }]
        global_vars = {}
        local_vars = {}
        
        result = compile_with_temp_value(mappings, global_vars, local_vars)
        assert "@id" in result
        assert "title" in result
        assert "description" in result
        assert "publisher" in result
        assert len(result["publisher"]) == 1


class TestRealWorldScenarios:
    """Test with real-world-like data and mapping scenarios."""

    def test_catalogue_entry_mapping(self):
        """Test mapping a complete catalogue entry."""
        def map_to_multiple_languages(val):
            if isinstance(val, dict):
                return [{"@language": lang, "@value": value} 
                       for lang, value in val.items()]
            return [{"@language": "en", "@value": val}]
        
        template = [{
            "@id": "http://data.urbandatacentre.ca/catalogue/{id}",
            "@type": "http://data.urbandatacentre.ca/catalogue",
            "dct:title": "eval(map_to_multiple_languages(title))",
            "dct:description": "eval(map_to_multiple_languages(description))",
            "dct:issued": {
                "@type": "xsd:date",
                "@value": "{published_date}"
            }
        }]
        
        global_vars = {"map_to_multiple_languages": map_to_multiple_languages}
        local_vars = {
            "id": "dataset-001",
            "title": {"en": "Housing Data", "fr": "Données sur le logement"},
            "description": {"en": "Housing statistics", "fr": "Statistiques de logement"},
            "published_date": "2025-01-01"
        }
        
        result = compile_template(template, global_vars, local_vars)
        
        assert result["@id"] == "http://data.urbandatacentre.ca/catalogue/dataset-001"
        assert len(result["dct:title"]) == 2
        assert len(result["dct:description"]) == 2
        assert result["dct:issued"][0]["@value"] == "2025-01-01"

    def test_with_optional_fields(self):
        """Test mapping with optional fields that may be empty."""
        template = [{
            "@id": "http://example.com/{id}",
            "required_field": "{title}",
            "optional_field": "{optional}",
            "another_optional": "{also_optional}"
        }]
        
        global_vars = {}
        local_vars = {
            "id": "123",
            "title": "Required Title",
            "optional": "",  # Empty optional
            # also_optional is not provided
        }
        
        result = compile_template(template, global_vars, local_vars)
        
        assert result["@id"] == "http://example.com/123"
        assert result["required_field"] == "Required Title"
        assert "optional_field" not in result
        assert "another_optional" not in result

    def test_uri_list_generation(self):
        """Test generating a list of URIs from comma-separated values."""
        def split_to_uris(val, separator=","):
            return [{"@id": uri.strip()} for uri in val.split(separator)]
        
        template = [{
            "@id": "http://example.com/dataset",
            "formats": "eval(split_to_uris(file_format))"
        }]
        
        global_vars = {"split_to_uris": split_to_uris}
        local_vars = {"file_format": "csv,json,xml"}
        
        result = compile_template(template, global_vars, local_vars)
        
        assert len(result["formats"]) == 3
        assert {"@id": "csv"} in result["formats"]
        assert {"@id": "json"} in result["formats"]
        assert {"@id": "xml"} in result["formats"]
