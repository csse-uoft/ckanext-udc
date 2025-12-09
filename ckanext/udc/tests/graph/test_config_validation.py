"""
Tests validating the actual config.example.json mapping configuration.

These tests validate that the real mapping configuration from config.example.json
works correctly with realistic CKAN data.
"""
import pytest
import json
from unittest.mock import Mock, patch
from pathlib import Path
from rdflib import Graph, URIRef, Namespace

from ckanext.udc.graph.template import compile_template
from ckanext.udc.graph.mapping_helpers import all_helpers, licenseMap
from ckanext.udc.graph.ckan_field import prepare_data_dict


# Load actual config
CONFIG_PATH = Path(__file__).parent.parent.parent / "config.example.json"


@pytest.fixture(autouse=True)
def mock_udc_plugin():
    """Mock the UDC plugin for all tests."""
    with patch('ckanext.udc.graph.template.get_plugin') as mock_get_plugin:
        mock_plugin = Mock()
        mock_plugin.text_fields = ['title', 'description']
        mock_get_plugin.return_value = mock_plugin
        yield mock_plugin


@pytest.fixture
def config():
    """Load the actual config.example.json file."""
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)


@pytest.fixture
def extended_helpers():
    """Extended helpers including those needed for config.example.json."""
    def map_to_multiple_languages(val):
        if isinstance(val, dict):
            return [{"@language": lang, "@value": value} 
                   for lang, value in val.items()]
        return [{"@language": "en", "@value": val}]
    
    def map_from_tags_multiple_languages(tags_dict):
        tags = []
        for lang, tags_list in tags_dict.items():
            for tag in tags_list:
                tags.append({"@language": lang, "@value": tag.strip()})
        return tags
    
    def map_to_multiple_datasets(datasets):
        result = []
        for ds in datasets:
            ds_id = ds.get("id")
            if ds_id:
                result.append({
                    "@id": ds_id,
                    "dcat:landingPage": ds_id,
                    "dcat:accessURL": ds_id,
                    "@type": "dcat:Dataset"
                })
        return result
    
    return {
        **all_helpers,
        "map_to_multiple_languages": map_to_multiple_languages,
        "map_from_tags_multiple_languages": map_from_tags_multiple_languages,
        "map_to_multiple_datasets": map_to_multiple_datasets
    }


class TestConfigStructure:
    """Test the structure of config.example.json."""

    def test_config_loads(self, config):
        """Test that config.example.json loads successfully."""
        assert config is not None
        assert isinstance(config, dict)

    def test_has_maturity_model(self, config):
        """Test that config has maturity_model section."""
        assert "maturity_model" in config
        assert isinstance(config["maturity_model"], list)
        assert len(config["maturity_model"]) == 6  # 6 maturity levels

    def test_has_mappings(self, config):
        """Test that config has mappings section."""
        assert "mappings" in config
        assert isinstance(config["mappings"], dict)

    def test_mappings_has_context(self, config):
        """Test that mappings have @context."""
        assert "@context" in config["mappings"]
        assert isinstance(config["mappings"]["@context"], dict)

    def test_mappings_has_id(self, config):
        """Test that mappings have @id."""
        assert "@id" in config["mappings"]

    def test_maturity_levels_structure(self, config):
        """Test maturity level structure."""
        for level in config["maturity_model"]:
            assert "title" in level
            assert "name" in level
            assert "fields" in level
            assert isinstance(level["fields"], list)


class TestMaturityLevel1Fields:
    """Test Maturity Level 1 (Basic Information) fields mapping."""

    @patch('ckanext.udc.graph.mapping_helpers.get_default_lang')
    def test_basic_fields_transformation(self, mock_get_default_lang, config, extended_helpers):
        """Test transformation of basic maturity level 1 fields."""
        mock_get_default_lang.return_value = "en"
        
        data_dict = {
            "id": "housing-2025",
            "name": "housing-data-2025",
            "title_translated": {
                "en": "Housing Statistics 2025",
                "fr": "Statistiques sur le logement 2025"
            },
            "description_translated": {
                "en": "Comprehensive housing data",
                "fr": "Données complètes sur le logement"
            },
            "tags_translated": {
                "en": ["housing", "statistics"],
                "fr": ["logement", "statistiques"]
            },
            "theme": "Housing",
            "file_format": "csv,json",
            "file_size": "125.5",
            "unique_metadata_identifier": "meta-001",
            "published_date": "2025-01-01",
            "time_span_start": "2024-01-01",
            "time_span_end": "2024-12-31",
            "geo_span": "Toronto"
        }
        
        prepared_dict = prepare_data_dict(data_dict)
        mapping = config["mappings"]
        
        result = compile_template(
            [mapping],
            extended_helpers,
            prepared_dict
        )
        
        # Validate basic structure
        assert result["@id"] == "http://data.urbandatacentre.ca/catalogue/housing-2025"
        assert result["@type"] == "http://data.urbandatacentre.ca/catalogue"
        
        # Validate multilingual title
        assert "dct:title" in result
        assert len(result["dct:title"][0]) == 2
        
        # Validate theme
        assert "dcat:theme" in result
        
        # Validate file size
        assert "cudr:file_size" in result


class TestMaturityLevel2Fields:
    """Test Maturity Level 2 (Access) fields mapping."""

    @patch('ckan.model.Package.get_license_register')
    @patch('ckanext.udc.graph.mapping_helpers.get_default_lang')
    def test_access_fields_transformation(self, mock_get_default_lang, mock_get_register, 
                                         config, extended_helpers):
        """Test transformation of access-related fields."""
        mock_get_default_lang.return_value = "en"
        mock_license = Mock()
        mock_license.url = "http://creativecommons.org/licenses/by/4.0/"
        mock_get_register.return_value = {"cc-by": mock_license}
        
        licenseMap.clear()
        
        data_dict = {
            "id": "dataset-002",
            "name": "test-dataset",
            "title_translated": {"en": "Test"},
            "access_category": "Open",
            "license_id": "cc-by",
            "limits_on_use": "Academic use only",
            "location": "http://example.com/data",
            "data_service": "http://ckan.example.com",
            "owner": "Data Owner Org",
            "access_steward": "John Doe",
            "access_steward_email": "john@example.com",
            "publisher": "Publishing Org",
            "publisher_email": "pub@example.com"
        }
        
        prepared_dict = prepare_data_dict(data_dict)
        mapping = config["mappings"]
        
        result = compile_template(
            [mapping],
            extended_helpers,
            prepared_dict
        )
        
        # Validate license mapping
        assert "dct:license" in result
        assert len(result["dct:license"]) == 1
        
        # Validate access URL
        assert "dcat:accessURL" in result
        
        # Validate publisher
        assert "dct:publisher" in result
        
        # Validate contact point
        assert "dcat:contactPoint" in result


class TestMaturityLevel3Fields:
    """Test Maturity Level 3 (Content) fields mapping."""

    @patch('ckanext.udc.graph.mapping_helpers.get_default_lang')
    def test_content_fields_transformation(self, mock_get_default_lang, config, extended_helpers):
        """Test transformation of content-related fields."""
        mock_get_default_lang.return_value = "en"
        
        data_dict = {
            "id": "dataset-003",
            "name": "test-dataset",
            "title_translated": {"en": "Test"},
            "accessed_date": "2025-01-15",
            "description_document": "http://example.com/docs",
            "language": "en,fr",
            "persistent_identifier": "yes",
            "global_unique_identifier": "yes",
            "file_format": "csv,json",
            "source": "http://example.com/source",
            "version": "1.0",
            "version_dataset": {"url": "http://example.com/v1", "title": "Version 1"},
            "dataset_versions": [
                {"url": "http://example.com/v2", "title": "Version 2"}
            ],
            "provenance": "Original data collected in 2024",
            "provenance_url": "http://example.com/provenance"
        }
        
        prepared_dict = prepare_data_dict(data_dict)
        mapping = config["mappings"]
        
        result = compile_template(
            [mapping],
            extended_helpers,
            prepared_dict
        )
        
        # Validate language mapping
        assert "dct:language" in result
        
        # Validate FAIR indicators
        assert "fair:rda-f1-01d" in result
        assert "fair:rda-f1-02d" in result


class TestCompleteMaturityLevels:
    """Test transformation with data from all maturity levels."""

    @patch('ckan.model.Package.get_license_register')
    @patch('ckanext.udc.graph.mapping_helpers.get_default_lang')
    def test_complete_catalogue_entry(self, mock_get_default_lang, mock_get_register,
                                     config, extended_helpers):
        """Test transformation with comprehensive data across all maturity levels."""
        mock_get_default_lang.return_value = "en"
        mock_license = Mock()
        mock_license.url = "http://opendatacommons.org/licenses/odbl/"
        mock_get_register.return_value = {"odc-odbl": mock_license}
        
        licenseMap.clear()
        
        # Comprehensive catalogue entry with fields from all maturity levels
        data_dict = {
            # Basic Information (Level 1)
            "id": "comprehensive-dataset-001",
            "name": "comprehensive-housing-data",
            "title_translated": {
                "en": "Comprehensive Housing Data 2025",
                "fr": "Données complètes sur le logement 2025"
            },
            "description_translated": {
                "en": "Complete housing statistics for urban areas",
                "fr": "Statistiques complètes sur le logement urbain"
            },
            "tags_translated": {
                "en": ["housing", "statistics", "urban"],
                "fr": ["logement", "statistiques", "urbain"]
            },
            "theme": "Housing",
            "file_format": "csv,json,xml",
            "file_size": "250.75",
            "unique_metadata_identifier": "meta-comprehensive-001",
            "published_date": "2025-01-01",
            "time_span_start": "2020-01-01",
            "time_span_end": "2024-12-31",
            "geo_span": "Greater Toronto Area",
            
            # Access (Level 2)
            "access_category": "Open",
            "license_id": "odc-odbl",
            "location": "http://data.city.ca/housing-2025",
            "publisher": "City Planning Department",
            "publisher_email": "planning@city.ca",
            
            # Content (Level 3)
            "language": "en,fr",
            "persistent_identifier": "yes",
            "global_unique_identifier": "yes",
            
            # Privacy (Level 4)
            "contains_individual_data": "no",
            "contains_identifiable_individual_data": "no",
            
            # Indigenous Data (Level 5)
            "contains_indigenous_data": "no",
            
            # Quality (Level 6)
            "number_of_rows": "10000",
            "number_of_columns": "25"
        }
        
        prepared_dict = prepare_data_dict(data_dict)
        mapping = config["mappings"]
        
        result = compile_template(
            [mapping],
            extended_helpers,
            prepared_dict
        )
        
        # Validate core structure
        assert result["@id"] == "http://data.urbandatacentre.ca/catalogue/comprehensive-dataset-001"
        assert result["@type"] == "http://data.urbandatacentre.ca/catalogue"
        
        # Validate multilingual fields
        assert len(result["dct:title"]) == 2
        assert len(result["dct:description"]) == 2
        assert len(result["dcat:keyword"]) == 6  # 3 tags × 2 languages
        
        # Validate temporal fields
        assert "cudr:hasTemporalStart" in result
        assert "cudr:hasTemporalEnd" in result
        
        # Validate license
        assert "dct:license" in result
        
        # Validate quality metrics
        assert "cudr:rows" in result
        assert "cudr:columns" in result


class TestRDFGraphGeneration:
    """Test that compiled mappings generate valid RDF graphs."""

    @patch('ckanext.udc.graph.mapping_helpers.get_default_lang')
    def test_jsonld_to_rdf_graph(self, mock_get_default_lang, config, extended_helpers):
        """Test that compiled JSON-LD can be parsed into an RDF graph."""
        mock_get_default_lang.return_value = "en"
        
        data_dict = {
            "id": "test-rdf-001",
            "name": "test-dataset",
            "title_translated": {"en": "Test Dataset"},
            "description_translated": {"en": "Test Description"},
            "tags_translated": {"en": ["test", "rdf"]},
            "published_date": "2025-01-01"
        }
        
        prepared_dict = prepare_data_dict(data_dict)
        mapping = config["mappings"]
        
        compiled = compile_template(
            [mapping],
            extended_helpers,
            prepared_dict
        )
        
        # Parse as RDF
        g = Graph()
        g.parse(data=compiled, format='json-ld')
        
        # Define namespaces
        DCT = Namespace("http://purl.org/dc/terms/")
        DCAT = Namespace("http://www.w3.org/ns/dcat#")
        
        # Validate subject exists
        subject = URIRef("http://data.urbandatacentre.ca/catalogue/test-rdf-001")
        assert (subject, None, None) in g
        
        # Validate title exists
        titles = list(g.objects(subject, DCT.title))
        assert len(titles) > 0
        
        # Validate keywords exist
        keywords = list(g.objects(subject, DCAT.keyword))
        assert len(keywords) >= 2  # At least "test" and "rdf"


class TestOptionalFieldHandling:
    """Test that optional fields are handled correctly."""

    @patch('ckanext.udc.graph.mapping_helpers.get_default_lang')
    def test_minimal_required_fields(self, mock_get_default_lang, config, extended_helpers):
        """Test transformation with only minimal required fields."""
        mock_get_default_lang.return_value = "en"
        
        # Only provide absolutely required fields
        data_dict = {
            "id": "minimal-001",
            "name": "minimal-dataset",
            "title_translated": {"en": "Minimal Dataset"}
        }
        
        prepared_dict = prepare_data_dict(data_dict)
        mapping = config["mappings"]
        
        result = compile_template(
            [mapping],
            extended_helpers,
            prepared_dict
        )
        
        # Should have ID and title
        assert result["@id"] == "http://data.urbandatacentre.ca/catalogue/minimal-001"
        assert "dct:title" in result
        
        # Optional fields should not be present
        optional_fields = [
            "dct:description", "cudr:accessCategory", "dct:license",
            "dcat:keyword", "cudr:file_size"
        ]
        
        # At least some optional fields should be missing
        missing_count = sum(1 for field in optional_fields if field not in result)
        assert missing_count > 0

    @patch('ckanext.udc.graph.mapping_helpers.get_default_lang')
    def test_empty_optional_fields_removed(self, mock_get_default_lang, config, extended_helpers):
        """Test that empty optional fields are removed from output."""
        mock_get_default_lang.return_value = "en"
        
        data_dict = {
            "id": "test-empty-001",
            "name": "test-dataset",
            "title_translated": {"en": "Test"},
            "description_translated": "",  # Empty
            "file_size": "",  # Empty
            "published_date": ""  # Empty
        }
        
        prepared_dict = prepare_data_dict(data_dict)
        mapping = config["mappings"]
        
        result = compile_template(
            [mapping],
            extended_helpers,
            prepared_dict
        )
        
        # Empty fields should not appear
        assert "dct:issued" not in result
        assert "cudr:file_size" not in result
