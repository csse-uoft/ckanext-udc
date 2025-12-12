# UDC Extension Test Suite

Comprehensive test suite for the CKAN Urban Data Centre (UDC) extension, covering multilingual functionality, user management, graph transformations, and core plugin features.

## Overview

This test suite validates the functionality of the ckanext-udc extension, including:

- Multilingual field handling and language fallback
- User management APIs (list and purge deleted users)
- Graph transformations (CKAN to JSON-LD/RDF)
- Plugin configuration and schema management
- Helper functions and Solr integration
- Package CRUD operations with custom validators

## Test Structure

```
ckanext/udc/tests/
├── README.md                   # This file
├── test_helpers.py            # Helper function tests
├── test_package_actions.py    # Package CRUD and multilingual tests
├── test_plugin.py             # Plugin configuration and schema tests
├── test_solr_config.py        # Solr language configuration tests
├── test_user_actions.py       # User management API tests
└── graph/                     # Graph transformation tests
    ├── README.md              # Graph tests documentation
    ├── test_template.py       # Template compilation tests
    ├── test_mapping_helpers.py # Mapping helper function tests
    ├── test_ckan_field.py     # CKAN field mapping tests
    ├── test_integration.py    # End-to-end integration tests
    └── test_config_validation.py # Configuration validation tests
```

## Test Files

### test_helpers.py

Tests for helper functions used throughout the extension.

**Functions Tested:**
- `process_facets_fields()` - Normalizes facet filters and logic operators
  - Removes `extras_` prefixes from field names
  - Extracts filter logic (AND/OR) from field keys
  - Handles range filters (min/max for numeric fields)
  - Processes full-text search indicators
  
- `get_maturity_percentages()` - Calculates dataset maturity scores
  - Counts completed core CKAN fields
  - Counts completed custom extra fields
  - Returns percentage completion for both categories

**Run tests:**
```bash
pytest ckanext/udc/tests/test_helpers.py -v
```

---

### test_package_actions.py

Tests for custom package actions with multilingual support and graph database integration.

**Key Test Functions:**

#### Package Update Tests
- `test_package_update_runs_preprocessor_and_updates_graph()` - Verifies package updates trigger graph database updates
- `test_package_update_wraps_graph_errors()` - Ensures graph errors are caught and wrapped with context
- `test_package_update_skips_graph_when_disabled()` - Confirms graph operations skip when GraphDB is disabled
- `test_package_update_persists_multilingual_changes()` - Validates multilingual field changes are saved correctly

#### Package Delete Tests
- `test_package_delete_invokes_graph()` - Verifies package deletion removes data from graph database
- `test_package_delete_wraps_graph_errors()` - Ensures graph deletion errors are handled gracefully
- `test_package_delete_skips_graph_when_disabled()` - Confirms deletion works without GraphDB
- `test_package_delete_succeeds_with_multilingual_extras()` - Tests deletion of packages with multilingual fields

#### Package Create Tests
- `test_package_create_handles_multilingual_fields()` - Validates multilingual fields are stored correctly on creation

**Key Features Tested:**
- Graph database synchronization
- Error handling and wrapping
- Multilingual field persistence
- Package preprocessor pipeline
- GraphDB enable/disable functionality

**Run tests:**
```bash
pytest ckanext/udc/tests/test_package_actions.py -v
```

---

### test_plugin.py

Tests for core plugin functionality including configuration loading and schema modification.

**Key Test Functions:**
- `test_reload_config_populates_field_metadata()` - Validates plugin configuration loading
  - Parses `config.example.json`
  - Populates field metadata (text_fields, date_fields, multiple_select_fields)
  - Sets up facet titles (multilingual)
  - Identifies field types and dropdown options

- `test_modify_package_schema_applies_expected_validators()` - Verifies schema validators
  - Custom validators applied to multilingual fields
  - Core field validators preserved
  - JSON load/dump validators for translated fields
  - Language object validators for multilingual data

**Key Features Tested:**
- Configuration parsing and validation
- Field type detection
- Facet title extraction
- Schema modification pipeline
- Validator chain composition

**Run tests:**
```bash
pytest ckanext/udc/tests/test_plugin.py -v
```

---

### test_solr_config.py

Tests for Solr configuration and multilingual language handling.

**Key Test Functions:**
- `test_get_udc_langs_includes_default_and_dedupes()` - Language list configuration
  - Includes default locale as first language
  - Parses configured languages from settings
  - Deduplicates language codes
  - Returns ordered list for fallback chain

- `test_get_current_lang_falls_back_to_default()` - Current language detection
  - Gets user's current language from session
  - Falls back to default locale when unavailable

- `test_pick_locale_prefers_requested_language()` - Language selection logic
  - Selects requested language when available
  - Falls back to user's current language
  - Falls back to English when current unavailable
  - Handles plain text (non-multilingual) values
  - Returns empty string for empty objects

**Key Features Tested:**
- Language configuration parsing
- Language fallback chain
- Locale selection priority
- Multilingual value extraction
- Plain text handling

**Run tests:**
```bash
pytest ckanext/udc/tests/test_solr_config.py -v
```

---

### test_user_actions.py

Tests for user management APIs (listing and purging deleted users).

**Test Classes:**

#### TestDeletedUsersList
Tests for the `deleted_users_list` action.

**Key Tests:**
- `test_list_deleted_users_as_sysadmin()` - Sysadmin can list deleted users
  - Returns list of user dictionaries
  - Includes id, name, email, state, created fields
  - Only shows users with `state='deleted'`
  
- `test_list_deleted_users_as_normal_user()` - Normal users get authorization error
- `test_list_deleted_users_anonymous()` - Anonymous users get authorization error
- `test_list_deleted_users_empty()` - Returns empty list when no deleted users
- `test_list_multiple_deleted_users()` - Lists all deleted users
- `test_list_does_not_include_active_users()` - Active users not included

#### TestPurgeDeletedUsers
Tests for the `purge_deleted_users` action.

**Key Tests:**
- `test_purge_deleted_users_as_sysadmin()` - Sysadmin can purge deleted users
  - Returns success status and count
  - Permanently removes users from database
  - Cleans up related data (memberships, collaborations)
  
- `test_purge_deleted_users_as_normal_user()` - Normal users get authorization error
- `test_purge_deleted_users_anonymous()` - Anonymous users get authorization error
- `test_purge_deleted_users_empty()` - Returns zero count when no deleted users
- `test_purge_multiple_deleted_users()` - Purges multiple users at once
- `test_purge_does_not_affect_active_users()` - Active users remain unchanged
- `test_purge_removes_user_memberships()` - Removes organization/group memberships
- `test_purge_workflow()` - Complete workflow: list → purge → verify

#### TestUserManagementIntegration
Integration tests for user management scenarios.

**Key Tests:**
- `test_deleted_user_datasets_remain()` - Datasets persist after user purge
- `test_cannot_purge_with_api_key_from_deleted_user()` - Deleted users cannot authenticate

**Key Features Tested:**
- Authorization (sysadmin-only access)
- Soft delete vs hard delete (purge)
- User listing with metadata
- Batch purging operations
- Relationship cleanup (memberships, collaborations)
- Dataset ownership preservation
- Error handling and edge cases

**Run tests:**
```bash
pytest ckanext/udc/tests/test_user_actions.py -v
```

---

### graph/ - Graph Transformation Tests

Comprehensive test suite for CKAN to JSON-LD/RDF transformations. See [graph/README.md](graph/README.md) for detailed documentation.

**Test Files:**
- `test_template.py` - Template compilation engine tests
- `test_mapping_helpers.py` - Helper function tests (UUID, type conversions, mappings)
- `test_ckan_field.py` - CKAN field accessor tests
- `test_integration.py` - End-to-end transformation tests
- `test_config_validation.py` - Configuration validation tests

**Quick Run:**
```bash
pytest ckanext/udc/tests/graph/ -v
```

See [graph/README.md](graph/README.md) for comprehensive documentation.

---

## Running Tests

### Run All Tests

```bash
cd /usr/lib/ckan/default/src/ckanext-udc
pytest ckanext/udc/tests/ -v
```

### Run Specific Test File

```bash
pytest ckanext/udc/tests/test_user_actions.py -v
pytest ckanext/udc/tests/test_helpers.py -v
pytest ckanext/udc/tests/test_solr_config.py -v
```

### Run Specific Test Class

```bash
pytest ckanext/udc/tests/test_user_actions.py::TestDeletedUsersList -v
pytest ckanext/udc/tests/test_user_actions.py::TestPurgeDeletedUsers -v
```

### Run Specific Test

```bash
pytest ckanext/udc/tests/test_user_actions.py::TestDeletedUsersList::test_list_deleted_users_as_sysadmin -v
```

### Run with Coverage

```bash
pytest ckanext/udc/tests/ --cov=ckanext.udc --cov-report=html
```

### Run with Output

```bash
pytest ckanext/udc/tests/ -v -s
```

### Run Tests Matching Pattern

```bash
pytest ckanext/udc/tests/ -k "multilingual" -v
pytest ckanext/udc/tests/ -k "user" -v
pytest ckanext/udc/tests/ -k "graph" -v
```

---

## Test Dependencies

Tests require the following packages:

```bash
pip install pytest pytest-ckan rdflib pyld
```

**Core Dependencies:**
- `pytest` - Test framework
- `pytest-ckan` - CKAN-specific test fixtures
- `ckan.tests.helpers` - CKAN test helpers
- `ckan.tests.factories` - Factory functions for test data

**Graph Test Dependencies:**
- `rdflib` - RDF graph operations
- `pyld` - JSON-LD processing
- `unittest.mock` - Mocking (standard library)

---

## Test Fixtures

### Common Fixtures (from pytest-ckan)

- `clean_db` - Resets database between tests
- `with_plugins` - Loads CKAN plugins for tests
- `app` - Flask test application
- `with_request_context` - Provides Flask request context

### Custom Fixtures (in test files)

- `udc_plugin` - Loads UDC plugin with test configuration
- `udc_plugin_instance` - Provides plugin instance for testing
- `stub_udc_plugin` - Minimal plugin stub for unit tests

---

## Test Patterns

### Testing Actions

```python
import ckan.plugins.toolkit as tk
from ckan.tests import helpers, factories

def test_action_example():
    # Create test data
    user = factories.Sysadmin()
    
    # Call action
    context = {'user': user['name']}
    result = helpers.call_action('action_name', context=context, **kwargs)
    
    # Assert results
    assert result['success'] is True
```

### Testing Authorization

```python
import pytest
import ckan.plugins.toolkit as tk

def test_authorization_failure():
    user = factories.User()  # Normal user, not sysadmin
    
    context = {'user': user['name'], 'ignore_auth': False}
    
    with pytest.raises(tk.NotAuthorized):
        helpers.call_action('restricted_action', context=context)
```

### Testing Multilingual Fields

```python
def test_multilingual_field():
    dataset = factories.Dataset(
        title_translated={"en": "English Title", "fr": "Titre français"}
    )
    
    # Verify both languages stored
    pkg = model.Package.get(dataset['id'])
    title_translated = json.loads(pkg.extras.get('title_translated', '{}'))
    
    assert title_translated['en'] == "English Title"
    assert title_translated['fr'] == "Titre français"
```

### Mocking External Dependencies

```python
from unittest.mock import patch, Mock

@patch('ckan.model.Package.get_license_register')
def test_with_mock(mock_get_register):
    mock_license = Mock()
    mock_license.url = "http://example.com/license"
    mock_get_register.return_value = {"cc-by": mock_license}
    
    # Test continues with mocked license registry
```

---


## Writing New Tests

When adding new features, follow these guidelines:

### 1. Test File Naming

- Use `test_` prefix: `test_feature_name.py`
- Group related tests in the same file
- Use descriptive names that explain what's being tested

### 2. Test Function Naming

- Use `test_` prefix: `test_function_does_something()`
- Be descriptive: `test_user_cannot_delete_without_permission()`
- Include expected behavior: `test_returns_empty_list_when_no_results()`

### 3. Test Structure

```python
def test_feature_behavior():
    # Arrange: Set up test data
    user = factories.User()
    dataset = factories.Dataset()
    
    # Act: Perform the action
    result = some_function(user, dataset)
    
    # Assert: Verify the results
    assert result['success'] is True
    assert result['data'] == expected_value
```

### 4. Use Fixtures

```python
@pytest.fixture
def sample_config():
    return {
        "fields": [...],
        "mappings": [...]
    }

def test_with_fixture(sample_config):
    result = process_config(sample_config)
    assert result is not None
```

### 5. Test Edge Cases

- Empty inputs
- None values
- Missing keys
- Invalid types
- Boundary conditions
- Error scenarios

### 6. Document Complex Tests

```python
def test_complex_multilingual_workflow():
    """
    Test complete workflow for multilingual dataset creation:
    1. Create dataset with English title
    2. Update to add French translation
    3. Verify both languages stored correctly
    4. Test language fallback on retrieval
    """
    # Test implementation...
```

---

## Troubleshooting

### Common Issues

**Issue: Tests fail with database errors**
```bash
# Solution: Reset test database
ckan -c test-core.ini db clean
ckan -c test-core.ini db init
```

**Issue: Import errors for ckanext.udc**
```bash
# Solution: Install extension in development mode
cd /usr/lib/ckan/default/src/ckanext-udc
pip install -e .
```

**Issue: Plugin not loaded in tests**
```python
# Solution: Add with_plugins fixture
@pytest.mark.usefixtures("clean_db", "with_plugins")
def test_with_plugin():
    pass
```

**Issue: Graph tests fail with RDF errors**
```bash
# Solution: Install graph dependencies
pip install rdflib pyld
```

---

## Test Data Factories

Use CKAN factories to create test data:

```python
from ckan.tests import factories

# Create users
user = factories.User()
sysadmin = factories.Sysadmin()

# Create organizations
org = factories.Organization()

# Create groups
group = factories.Group()

# Create datasets
dataset = factories.Dataset(
    title="Test Dataset",
    owner_org=org['id'],
    user=user
)

# Create resources
resource = factories.Resource(
    package_id=dataset['id'],
    url='http://example.com/data.csv'
)
```

---

## See Also

- [CKAN Testing Documentation](https://docs.ckan.org/en/latest/contributing/testing.html)
- [pytest Documentation](https://docs.pytest.org)
- [Graph Tests README](graph/README.md)
- [API Documentation](../../../docs/API_USER_MANAGEMENT.md)

---

## Contributing

When contributing tests:

1. Ensure all tests pass before submitting PR
2. Add tests for new features
3. Maintain test coverage above 80%
4. Follow existing test patterns
5. Document complex test scenarios
6. Use descriptive test names
7. Clean up test data in teardown

Run tests locally:
```bash
pytest ckanext/udc/tests/ -v --cov=ckanext.udc --cov-report=term-missing
```
