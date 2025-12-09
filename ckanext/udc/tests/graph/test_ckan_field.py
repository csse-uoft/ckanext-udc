"""
Tests for graph/ckan_field.py - CKAN field mapping logic.

Tests the prepare_data_dict function that applies field name mappings
to CKAN package dictionaries for use in graph transformations.
"""
import pytest

from ckanext.udc.graph.ckan_field import prepare_data_dict, ckanFieldMapping


class TestPrepareDataDict:
    """Test prepare_data_dict function."""

    def test_basic_field_mapping(self):
        """Test that basic fields are mapped correctly."""
        data = {
            "title_translated": {"en": "My Dataset", "fr": "Mon jeu de données"},
            "description_translated": {"en": "Description"},
            "url": "http://example.com/source"
        }
        
        result = prepare_data_dict(data)
        
        # Original fields should still be present
        assert result["title_translated"] == {"en": "My Dataset", "fr": "Mon jeu de données"}
        assert result["description_translated"] == {"en": "Description"}
        assert result["url"] == "http://example.com/source"
        
        # Mapped fields should be accessible by normalized names
        assert result["title"] == {"en": "My Dataset", "fr": "Mon jeu de données"}
        assert result["description"] == {"en": "Description"}
        assert result["source"] == "http://example.com/source"

    def test_id_field_with_pkg_name(self):
        """Test that pkg_name is used for id if available."""
        data = {
            "id": "original-id",
            "pkg_name": "package-name"
        }
        
        result = prepare_data_dict(data)
        
        # pkg_name should take precedence for 'id'
        assert result["id"] == "package-name"

    def test_id_field_without_pkg_name(self):
        """Test that id is used when pkg_name is not available."""
        data = {
            "id": "original-id"
        }
        
        result = prepare_data_dict(data)
        
        assert result["id"] == "original-id"

    def test_preserves_original_data(self):
        """Test that original data_dict is not modified."""
        data = {
            "name": "my-dataset",
            "title_translated": {"en": "My Dataset"}
        }
        
        original_data = data.copy()
        result = prepare_data_dict(data)
        
        # Original dict should not be modified
        assert data == original_data
        
        # Result should have new mapped fields
        assert "title" in result

    def test_all_mappings_applied(self):
        """Test that all field mappings are applied."""
        data = {
            "title_translated": {"en": "Title"},
            "description_translated": {"en": "Desc"},
            "tags_translated": {"en": ["tag1"]},
            "author": "John Doe",
            "author_email": "john@example.com",
            "url": "http://example.com",
            "version": "1.0"
        }
        
        result = prepare_data_dict(data)
        
        assert result["title"] == {"en": "Title"}
        assert result["description"] == {"en": "Desc"}
        assert result["tags"] == {"en": ["tag1"]}
        assert result["author"] == "John Doe"
        assert result["author_email"] == "john@example.com"
        assert result["source"] == "http://example.com"
        assert result["version"] == "1.0"

    def test_empty_string_values_preserved(self):
        """Test that empty string values are preserved."""
        data = {
            "name": "dataset",
            "author": ""
        }
        
        result = prepare_data_dict(data)
        
        # Empty string should be preserved, not replaced with EMPTY_FIELD
        assert result["author"] == ""


class TestCKANFieldMapping:
    """Test the ckanFieldMapping dictionary."""

    def test_mapping_values(self):
        """Test that mapping values are correct."""
        assert ckanFieldMapping["title"] == "title_translated"
        assert ckanFieldMapping["description"] == "description_translated"
        assert ckanFieldMapping["tags"] == "tags_translated"
        assert ckanFieldMapping["source"] == "url"


class TestRealWorldScenarios:
    """Test with real-world-like CKAN package dictionaries."""

    def test_complete_package_dict(self):
        """Test with a complete package dictionary."""
        data = {
            "name": "housing-data-2025",
            "title_translated": {
                "en": "Housing Statistics 2025",
                "fr": "Statistiques sur le logement 2025"
            },
            "description_translated": {
                "en": "Comprehensive housing data for urban areas",
                "fr": "Données complètes sur le logement pour les zones urbaines"
            },
            "tags_translated": {
                "en": ["housing", "statistics", "urban"],
                "fr": ["logement", "statistiques", "urbain"]
            },
            "id": "abc-123-def-456",
            "pkg_name": "housing-data-2025",
            "author": "Urban Data Centre",
            "author_email": "data@urbancentre.ca",
            "url": "http://data.urbancentre.ca/datasets/housing-2025",
            "version": "1.0"
        }
        
        result = prepare_data_dict(data)
        
        # Test all accessors
        assert result["name"] == "housing-data-2025"
        assert result["id"] == "housing-data-2025"  # pkg_name takes precedence
        assert result["title"]["en"] == "Housing Statistics 2025"
        assert result["description"]["fr"] == "Données complètes sur le logement pour les zones urbaines"
        assert "housing" in result["tags"]["en"]
        assert result["author"] == "Urban Data Centre"
        assert result["author_email"] == "data@urbancentre.ca"
        assert result["source"] == "http://data.urbancentre.ca/datasets/housing-2025"
        assert result["version"] == "1.0"

    def test_package_dict_for_update(self):
        """Test package dict used for update operation."""
        data = {
            "pkg_name": "existing-dataset",
            "id": "old-id-should-not-be-used",
            "title_translated": {"en": "Updated Title"},
            "version": "2.0"
        }
        
        result = prepare_data_dict(data)
        
        # For updates, pkg_name should be used as id
        assert result["id"] == "existing-dataset"
        assert result["title"]["en"] == "Updated Title"
        assert result["version"] == "2.0"

    def test_package_dict_with_custom_fields(self):
        """Test that custom fields (not in mapping) are preserved."""
        data = {
            "name": "dataset",
            "id": "123",
            "custom_field": "custom_value",
            "another_field": {"key": "value"}
        }
        
        result = prepare_data_dict(data)
        
        # Custom fields should be preserved
        assert result["custom_field"] == "custom_value"
        assert result["another_field"] == {"key": "value"}

    def test_multilingual_fields(self):
        """Test accessing multilingual fields."""
        data = {
            "title_translated": {
                "en": "English Title",
                "fr": "Titre français",
                "es": "Título español"
            },
            "description_translated": {
                "en": "English description",
                "fr": "Description française"
            }
        }
        
        result = prepare_data_dict(data)
        
        assert result["title"]["en"] == "English Title"
        assert result["title"]["fr"] == "Titre français"
        assert result["description"]["en"] == "English description"

    def test_tags_translated(self):
        """Test accessing translated tags."""
        data = {
            "tags_translated": {
                "en": ["housing", "transport", "health"],
                "fr": ["logement", "transport", "santé"]
            }
        }
        
        result = prepare_data_dict(data)
        
        assert len(result["tags"]["en"]) == 3
        assert "housing" in result["tags"]["en"]
        assert len(result["tags"]["fr"]) == 3
        assert "logement" in result["tags"]["fr"]

