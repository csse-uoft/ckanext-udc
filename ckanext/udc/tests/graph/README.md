## Graph Transformation Test Suite

Comprehensive test suite for the CKAN to JSON-LD/RDF transformation pipeline used in the UDC extension.

### Overview

This test suite validates the transformation of CKAN package dictionaries into JSON-LD and RDF graphs according to the mapping configuration defined in `config.example.json`.

**Context Information:**
- **Model**: Claude Sonnet 4.5
- **Token Usage**: ~82,000 / 1,000,000 (8.2% used)
- **Remaining**: ~918,000 tokens

### Test Structure

```
ckanext/udc/tests/graph/
├── __init__.py
├── test_template.py          # Template compilation logic tests
├── test_mapping_helpers.py   # Helper function tests
├── test_ckan_field.py         # CKAN field mapping tests
└── test_integration.py        # End-to-end integration tests
```

### Test Coverage

#### 1. **test_template.py** (Template Compilation)
Tests the core template compilation engine that processes mapping configurations.

**Key Test Classes:**
- `TestIsAllAttrsStartsWithAt` - Tests @ attribute detection
- `TestFilterOutEmptyValues` - Tests empty value filtering
- `TestCompileTemplate` - Tests template compilation with various scenarios
  - Simple string substitution
  - Nested dictionaries and lists
  - `eval()` expressions
  - Localized text fields
  - Empty value handling
- `TestCompileWithTempValue` - Tests template compilation preserving structure
- `TestRealWorldScenarios` - Tests with realistic catalogue data

**Key Features Tested:**
- F-string style variable substitution: `"{variable}"`
- Eval expressions: `"eval(function(variable))"`
- Nested structure compilation
- Empty field removal
- Multilingual field handling
- Helper function integration

#### 2. **test_mapping_helpers.py** (Helper Functions)
Tests all helper functions available in mapping configurations.

**Functions Tested:**
- `generate_uuid()` - UUID generation with caching
- `to_integer()`, `to_float()` - Type conversions
- `to_date()` - Date to XSD date conversion
- `to_bool()` - Boolean string conversion
- `mapFromCKANLicense()` - License ID/URL mapping
- `split_to_uris()` - Comma-separated string to URI list
- `quote_url()` - URL encoding preserving protocol
- `mapFromCKANTags()` - Tag string parsing
- `map_from_tags_multiple_languages()` - Multilingual tag mapping
- `map_to_multiple_languages()` - Value to language array
- `map_to_single_language()` - Language-specific value extraction
- `map_to_multiple_datasets()` - Dataset list mapping

**Key Scenarios:**
- Multilingual data handling
- CKAN license registry integration
- URL encoding edge cases
- UUID caching behavior
- Empty value handling

#### 3. **test_ckan_field.py** (CKAN Field Mapping)
Tests the `CKANField` class that provides dot notation access to package dictionaries.

**Key Features Tested:**
- Field name mapping (e.g., `title` → `title_translated`)
- Dot notation access
- `pkg_name` vs `id` precedence
- Missing field handling (returns `EMPTY_FIELD`)
- Dictionary operations (get, keys, etc.)
- Multilingual field access

**Real-World Scenarios:**
- Complete package dictionaries
- Minimal required fields
- Update vs create operations
- None value handling

#### 4. **test_integration.py** (End-to-End Integration)
Tests complete transformation pipeline from CKAN data to RDF.

**Test Classes:**
- `TestBasicTransformation` - Simple catalogue transformations
- `TestComplexTransformation` - Nested structures (publisher, creator, etc.)
- `TestDateAndTypeTransformations` - Type conversions in context
- `TestLicenseAndFormatTransformations` - License and format mappings
- `TestURLTransformations` - URL quoting in templates
- `TestTagTransformations` - Tag and keyword mappings
- `TestRDFGeneration` - JSON-LD to RDF parsing
- `TestErrorHandling` - Graceful error handling

**Key Scenarios:**
- Minimal catalogue entries
- Multilingual catalogue entries
- Nested publisher/creator information
- Optional field removal
- License mapping with registry
- Format list generation
- URL quoting with special characters
- Multilingual tags
- JSON-LD to RDF Graph conversion

### Running the Tests

#### Run all graph transformation tests:
```bash
cd /usr/lib/ckan/default/src/ckanext-udc
pytest ckanext/udc/tests/graph/ -v
```

#### Run specific test file:
```bash
pytest ckanext/udc/tests/graph/test_template.py -v
pytest ckanext/udc/tests/graph/test_mapping_helpers.py -v
pytest ckanext/udc/tests/graph/test_ckan_field.py -v
pytest ckanext/udc/tests/graph/test_integration.py -v
```

#### Run specific test class:
```bash
pytest ckanext/udc/tests/graph/test_template.py::TestCompileTemplate -v
```

#### Run specific test:
```bash
pytest ckanext/udc/tests/graph/test_integration.py::TestRDFGeneration::test_jsonld_to_rdf_conversion -v
```

#### Run with coverage:
```bash
pytest ckanext/udc/tests/graph/ --cov=ckanext.udc.graph --cov-report=html
```

### Test Data Patterns

#### Minimal Catalogue Entry
```python
data_dict = {
    "id": "dataset-001",
    "name": "my-dataset",
    "title_translated": "Test Dataset"
}
```

#### Multilingual Catalogue Entry
```python
data_dict = {
    "id": "dataset-002",
    "name": "housing-data",
    "title_translated": {
        "en": "Housing Data",
        "fr": "Données sur le logement"
    },
    "description_translated": {
        "en": "Urban housing statistics",
        "fr": "Statistiques sur le logement urbain"
    },
    "tags_translated": {
        "en": ["housing", "urban"],
        "fr": ["logement", "urbain"]
    }
}
```

#### Complete Catalogue Entry
```python
data_dict = {
    "id": "dataset-003",
    "name": "complete-dataset",
    "title_translated": {"en": "Complete Dataset"},
    "description_translated": {"en": "Full description"},
    "tags_translated": {"en": ["tag1", "tag2"]},
    "published_date": "2025-01-01",
    "publisher": "Organization Name",
    "publisher_email": "org@example.com",
    "file_format": "csv,json,xml",
    "license_id": "cc-by",
    "location": "http://example.com/dataset"
}
```

### Mapping Configuration Pattern

The tests validate transformations based on this pattern from `config.example.json`:

```json
{
  "@context": {
    "dct": "http://purl.org/dc/terms/",
    "dcat": "http://www.w3.org/ns/dcat#"
  },
  "@id": "http://data.urbandatacentre.ca/catalogue/{ckanField.id}",
  "@type": "http://data.urbandatacentre.ca/catalogue",
  "dct:title": "eval(map_to_multiple_languages(ckanField.title))",
  "dct:description": "eval(map_to_multiple_languages(ckanField.description))",
  "dcat:keyword": "eval(map_from_tags_multiple_languages(ckanField.tags))",
  "dct:issued": {
    "@type": "xsd:date",
    "@value": "{to_date(published_date)}"
  },
  "dct:publisher": [{
    "@id": "http://data.urbandatacentre.ca/org/{publisher_id}",
    "@type": "foaf:Agent",
    "foaf:name": "{publisher}"
  }]
}
```

### Key Test Assertions

#### Template Compilation
```python
result = compile_template([mapping], helpers, variables)
assert result["@id"] == "expected_uri"
assert "empty_field" not in result
assert len(result["multilingual_field"]) == 2
```

#### Helper Functions
```python
assert generate_uuid("key1") == generate_uuid("key1")
assert to_date("2025-01-01").datatype == XSD.date
assert to_bool("yes") == "true"
assert quote_url("http://example.com/path with spaces") == "http://example.com/path%20with%20spaces"
```

#### RDF Generation
```python
g = Graph()
g.parse(data=compiled_jsonld, format='json-ld')
assert (subject_uri, predicate, object) in g
```

### Mocking Strategy

Tests use mocks for external dependencies:

```python
@patch('ckan.model.Package.get_license_register')
def test_license_mapping(mock_get_register):
    mock_license = Mock()
    mock_license.url = "http://creativecommons.org/licenses/by/4.0/"
    mock_get_register.return_value = {"cc-by": mock_license}
    # Test continues...
```

```python
@patch('ckanext.udc.graph.mapping_helpers.get_default_lang')
def test_multilingual(mock_get_default_lang):
    mock_get_default_lang.return_value = "en"
    # Test continues...
```

### Edge Cases Covered

1. **Empty Values**: Empty strings, None, missing keys
2. **Unicode**: Special characters in URLs and text
3. **Nested Structures**: Multiple levels of nesting
4. **Optional Fields**: Fields that may or may not be present
5. **Type Conversions**: Invalid inputs, edge cases
6. **Multilingual**: Missing translations, single language
7. **Eval Errors**: Invalid expressions, undefined functions
8. **UUID Caching**: Same vs different keys

### Expected Test Output

All tests should pass with output similar to:
```
ckanext/udc/tests/graph/test_template.py::TestCompileTemplate::test_simple_string_substitution PASSED
ckanext/udc/tests/graph/test_template.py::TestCompileTemplate::test_nested_dict_compilation PASSED
...
ckanext/udc/tests/graph/test_integration.py::TestRDFGeneration::test_jsonld_to_rdf_conversion PASSED

====== 100+ tests passed in X.XXs ======
```

### Maintenance

When updating the mapping configuration (`config.example.json`), ensure:

1. Add corresponding tests for new fields
2. Test new helper functions thoroughly
3. Validate JSON-LD to RDF conversion still works
4. Test both optional and required field scenarios
5. Cover multilingual aspects if applicable

### Dependencies

Tests require:
- pytest
- pytest-ckan (for CKAN test fixtures)
- rdflib (for RDF graph operations)
- pyld (for JSON-LD processing)
- unittest.mock (standard library)

Install test dependencies:
```bash
pip install pytest pytest-ckan rdflib pyld
```
