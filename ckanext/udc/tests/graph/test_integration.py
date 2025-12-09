"""
Integration tests for the complete graph transformation pipeline.

Tests the end-to-end transformation from CKAN package dictionaries
to JSON-LD and RDF graphs using the real mapping configuration.
"""
import pytest
import json
from unittest.mock import Mock, patch
from rdflib import Graph, URIRef, Literal, Namespace
from pyld import jsonld

from ckanext.udc.graph.template import compile_template
from ckanext.udc.graph.mapping_helpers import all_helpers
from ckanext.udc.graph.ckan_field import prepare_data_dict
from ckanext.udc.graph.contants import EMPTY_FIELD


@pytest.fixture(autouse=True)
def mock_udc_plugin():
    """Mock the UDC plugin for all tests."""
    with patch('ckanext.udc.graph.template.get_plugin') as mock_get_plugin:
        mock_plugin = Mock()
        mock_plugin.text_fields = []
        mock_get_plugin.return_value = mock_plugin
        yield mock_plugin


class TestBasicTransformation:
    """Test basic transformation scenarios."""

    def test_minimal_catalogue_entry(self):
        """Test transforming a minimal catalogue entry."""
        mapping = {
            "@context": {
                "dct": "http://purl.org/dc/terms/",
                "xsd": "http://www.w3.org/2001/XMLSchema#"
            },
            "@id": "http://data.urbandatacentre.ca/catalogue/{id}",
            "@type": "http://data.urbandatacentre.ca/catalogue",
            "dct:title": "{title}"
        }
        
        data_dict = {
            "id": "dataset-001",
            "title_translated": "Test Dataset",
            "name": "test-dataset"
        }
        
        prepared_dict = prepare_data_dict(data_dict)
        result = compile_template(
            [mapping],
            all_helpers,
            prepared_dict
        )
        
        assert result["@id"] == "http://data.urbandatacentre.ca/catalogue/dataset-001"
        assert result["@type"] == "http://data.urbandatacentre.ca/catalogue"
        assert result["dct:title"] == "Test Dataset"

    @patch('ckanext.udc.graph.mapping_helpers.get_default_lang')
    def test_multilingual_catalogue_entry(self, mock_get_default_lang):
        """Test transforming a multilingual catalogue entry."""
        mock_get_default_lang.return_value = "en"
        
        def map_to_multiple_languages(val):
            if isinstance(val, dict):
                return [{"@language": lang, "@value": value} 
                       for lang, value in val.items()]
            return [{"@language": "en", "@value": val}]
        
        mapping = {
            "@context": {"dct": "http://purl.org/dc/terms/"},
            "@id": "http://data.urbandatacentre.ca/catalogue/{id}",
            "dct:title": "eval(map_to_multiple_languages(title))",
            "dct:description": "eval(map_to_multiple_languages(description))"
        }
        
        data_dict = {
            "id": "dataset-002",
            "title_translated": {
                "en": "Housing Data",
                "fr": "Données sur le logement"
            },
            "description_translated": {
                "en": "Urban housing statistics",
                "fr": "Statistiques sur le logement urbain"
            },
            "name": "housing-data"
        }
        
        prepared_dict = prepare_data_dict(data_dict)
        helpers = {**all_helpers, "map_to_multiple_languages": map_to_multiple_languages}
        
        result = compile_template(
            [mapping],
            helpers,
            prepared_dict
        )
        
        assert len(result["dct:title"]) == 2
        assert {"@language": "en", "@value": "Housing Data"} in result["dct:title"]
        assert {"@language": "fr", "@value": "Données sur le logement"} in result["dct:title"]
        assert len(result["dct:description"]) == 2


class TestComplexTransformation:
    """Test complex transformation scenarios with nested structures."""

    @patch('ckanext.udc.graph.mapping_helpers.get_default_lang')
    def test_catalogue_with_publisher(self, mock_get_default_lang):
        """Test transformation with nested publisher information."""
        mock_get_default_lang.return_value = "en"
        
        def map_to_multiple_languages(val):
            if isinstance(val, dict):
                return [{"@language": lang, "@value": value} 
                       for lang, value in val.items()]
            return [{"@language": "en", "@value": val}]
        
        mapping = {
            "@context": {
                "dct": "http://purl.org/dc/terms/",
                "foaf": "http://xmlns.com/foaf/0.1/"
            },
            "@id": "http://data.urbandatacentre.ca/catalogue/{id}",
            "dct:title": "eval(map_to_multiple_languages(title))",
            "dct:publisher": [{
                "@id": "http://data.urbandatacentre.ca/org/{publisher_id}",
                "@type": "foaf:Agent",
                "foaf:name": "{publisher}",
                "foaf:mbox": "{publisher_email}"
            }]
        }
        
        data_dict = {
            "id": "dataset-003",
            "title_translated": {"en": "Transport Data"},
            "name": "transport-data",
            "publisher": "Urban Planning Department",
            "publisher_email": "planning@city.ca",
            "publisher_id": "upd-001"
        }
        
        prepared_dict = prepare_data_dict(data_dict)
        helpers = {**all_helpers, "map_to_multiple_languages": map_to_multiple_languages}
        
        result = compile_template(
            [mapping],
            helpers,
            prepared_dict
        )
        
        assert len(result["dct:publisher"]) == 1
        publisher = result["dct:publisher"][0]
        assert publisher["@id"] == "http://data.urbandatacentre.ca/org/upd-001"
        assert publisher["@type"] == "foaf:Agent"
        assert publisher["foaf:name"] == "Urban Planning Department"
        assert publisher["foaf:mbox"] == "planning@city.ca"

    def test_optional_fields_removed(self):
        """Test that optional empty fields are removed from output."""
        mapping = {
            "@id": "http://example.com/{id}",
            "required": "{title}",
            "optional1": "{description}",
            "optional2": "{notes}",
            "nested": [{
                "field1": "{field1}",
                "field2": "{field2}"
            }]
        }
        
        data_dict = {
            "id": "test-001",
            "title": "Required Title",
            "description": "",  # Empty
            # notes is missing
            "field1": "Value 1"
            # field2 is missing
        }
        
        prepared_dict = prepare_data_dict(data_dict)
        result = compile_template(
            [mapping],
            all_helpers,
            prepared_dict
        )
        
        assert result["required"] == "Required Title"
        assert "optional1" not in result
        assert "optional2" not in result
        assert len(result["nested"]) == 1
        assert result["nested"][0]["field1"] == "Value 1"
        assert "field2" not in result["nested"][0]


class TestDateAndTypeTransformations:
    """Test transformations involving dates and type conversions."""

    def test_date_transformation(self):
        """Test date field transformation to XSD date."""
        mapping = {
            "@id": "http://example.com/{id}",
            "dct:issued": {
                "@type": "xsd:date",
                "@value": "{to_date(published_date)}"
            }
        }
        
        data_dict = {
            "id": "test-001",
            "published_date": "2025-01-15"
        }
        
        prepared_dict = prepare_data_dict(data_dict)
        result = compile_template(
            [mapping],
            all_helpers,
            prepared_dict
        )
        
        assert result["dct:issued"][0]["@type"] == "xsd:date"
        assert "2025-01-15" in str(result["dct:issued"][0]["@value"])

    def test_boolean_transformation(self):
        """Test boolean field transformation."""
        mapping = {
            "@id": "http://example.com/{id}",
            "hasData": {
                "@type": "xsd:boolean",
                "@value": "{to_bool(contains_data)}"
            }
        }
        
        data_dict = {
            "id": "test-001",
            "contains_data": "yes"
        }
        
        prepared_dict = prepare_data_dict(data_dict)
        result = compile_template(
            [mapping],
            all_helpers,
            prepared_dict
        )
        
        assert result["hasData"][0]["@value"] == "true"

    def test_empty_date_removed(self):
        """Test that empty dates are removed from output."""
        mapping = {
            "@id": "http://example.com/{id}",
            "title": "{title}",
            "issued": {
                "@type": "xsd:date",
                "@value": "{to_date(published_date)}"
            }
        }
        
        data_dict = {
            "id": "test-001",
            "title": "Test",
            "published_date": ""
        }
        
        prepared_dict = prepare_data_dict(data_dict)
        result = compile_template(
            [mapping],
            all_helpers,
            prepared_dict
        )
        
        assert "title" in result
        assert "issued" not in result


class TestLicenseAndFormatTransformations:
    """Test license and file format transformations."""

    @patch('ckan.model.Package.get_license_register')
    def test_license_mapping(self, mock_get_register):
        """Test CKAN license mapping."""
        mock_license = Mock()
        mock_license.url = "http://creativecommons.org/licenses/by/4.0/"
        mock_get_register.return_value = {"cc-by": mock_license}
        
        mapping = {
            "@id": "http://example.com/{id}",
            "dct:license": "eval(mapFromCKANLicense(license_id))"
        }
        
        data_dict = {
            "id": "test-001",
            "license_id": "cc-by"
        }
        
        # Clear license map
        from ckanext.udc.graph.mapping_helpers import licenseMap
        licenseMap.clear()
        
        prepared_dict = prepare_data_dict(data_dict)
        result = compile_template(
            [mapping],
            all_helpers,
            prepared_dict
        )
        
        assert len(result["dct:license"]) == 1
        assert result["dct:license"][0]["@id"] == "http://creativecommons.org/licenses/by/4.0/"

    def test_format_list_transformation(self):
        """Test file format list transformation."""
        mapping = {
            "@id": "http://example.com/{id}",
            "dct:format": "eval(split_to_uris(file_format))"
        }
        
        data_dict = {
            "id": "test-001",
            "file_format": "csv,json,xml"
        }
        
        prepared_dict = prepare_data_dict(data_dict)
        result = compile_template(
            [mapping],
            all_helpers,
            prepared_dict
        )
        
        assert len(result["dct:format"]) == 3
        assert {"@id": "csv"} in result["dct:format"]
        assert {"@id": "json"} in result["dct:format"]
        assert {"@id": "xml"} in result["dct:format"]


class TestURLTransformations:
    """Test URL quoting and transformation."""

    def test_url_quoting(self):
        """Test URL quoting with spaces."""
        mapping = {
            "@id": "http://example.com/{id}",
            "dcat:accessURL": {
                "@id": "eval(quote_url(location))"
            }
        }
        
        data_dict = {
            "id": "test-001",
            "location": "http://example.com/data with spaces"
        }
        
        prepared_dict = prepare_data_dict(data_dict)
        result = compile_template(
            [mapping],
            all_helpers,
            prepared_dict
        )
        
        assert "with%20spaces" in result["dcat:accessURL"][0]["@id"]
        assert "http://example.com/" in result["dcat:accessURL"][0]["@id"]


class TestTagTransformations:
    """Test tag transformation scenarios."""

    def test_multilingual_tags(self):
        """Test multilingual tags transformation."""
        def map_from_tags_multiple_languages(tags_dict):
            tags = []
            for lang, tags_list in tags_dict.items():
                for tag in tags_list:
                    tags.append({
                        "@language": lang,
                        "@value": tag.strip()
                    })
            return tags
        
        mapping = {
            "@id": "http://example.com/{id}",
            "dcat:keyword": "eval(map_from_tags_multiple_languages(tags))"
        }
        
        data_dict = {
            "id": "test-001",
            "tags_translated": {
                "en": ["housing", "transport"],
                "fr": ["logement", "transport"]
            },
            "name": "test"
        }
        
        prepared_dict = prepare_data_dict(data_dict)
        helpers = {
            **all_helpers,
            "map_from_tags_multiple_languages": map_from_tags_multiple_languages
        }
        
        result = compile_template(
            [mapping],
            helpers,
            prepared_dict
        )
        
        assert len(result["dcat:keyword"]) == 4
        assert {"@language": "en", "@value": "housing"} in result["dcat:keyword"]
        assert {"@language": "fr", "@value": "logement"} in result["dcat:keyword"]


class TestRDFGeneration:
    """Test generation of actual RDF from compiled templates."""

    @patch('ckanext.udc.graph.mapping_helpers.get_default_lang')
    def test_jsonld_to_rdf_conversion(self, mock_get_default_lang):
        """Test that compiled JSON-LD can be parsed as RDF."""
        mock_get_default_lang.return_value = "en"
        
        mapping = {
            "@context": {
                "dct": "http://purl.org/dc/terms/",
                "xsd": "http://www.w3.org/2001/XMLSchema#"
            },
            "@id": "http://data.urbandatacentre.ca/catalogue/{id}",
            "@type": "http://www.w3.org/ns/dcat#Dataset",
            "dct:title": "{title}",
            "dct:issued": {
                "@type": "xsd:date",
                "@value": "{to_date(published_date)}"
            }
        }
        
        data_dict = {
            "id": "dataset-001",
            "title_translated": "Test Dataset",
            "name": "test-dataset",
            "published_date": "2025-01-01"
        }
        
        prepared_dict = prepare_data_dict(data_dict)
        compiled = compile_template(
            [mapping],
            all_helpers,
            prepared_dict
        )
        
        # Parse as RDF
        g = Graph()
        g.parse(data=compiled, format='json-ld')
        
        # Verify triples exist
        DCT = Namespace("http://purl.org/dc/terms/")
        DCAT = Namespace("http://www.w3.org/ns/dcat#")
        
        subject = URIRef("http://data.urbandatacentre.ca/catalogue/dataset-001")
        
        # Check that subject exists
        assert (subject, None, None) in g
        
        # Check title exists
        titles = list(g.objects(subject, DCT.title))
        assert len(titles) > 0
        
        # Check type
        types = list(g.objects(subject, URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")))
        assert DCAT.Dataset in types


class TestErrorHandling:
    """Test error handling in transformations."""

    def test_invalid_eval_expression(self):
        """Test that invalid eval expressions are handled gracefully."""
        mapping = {
            "@id": "http://example.com/{id}",
            "invalid": "eval(nonexistent_function())"
        }
        
        data_dict = {
            "id": "test-001"
        }
        
        prepared_dict = prepare_data_dict(data_dict)
        result = compile_template(
            [mapping],
            all_helpers,
            prepared_dict
        )
        
        # Invalid field should be removed
        assert "invalid" not in result

    def test_missing_required_variable(self):
        """Test handling of missing required variables."""
        mapping = {
            "@id": "http://example.com/{missing_id}",
            "title": "{title}"
        }
        
        data_dict = {
            "title": "Test"
        }
        
        prepared_dict = prepare_data_dict(data_dict)
        result = compile_template(
            [mapping],
            all_helpers,
            prepared_dict
        )
        
        # Should remove @id if variable is missing
        assert "@id" not in result or "missing_id" in result.get("@id", "")
