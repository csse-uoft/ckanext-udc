from ckanext.udc import helpers as udc_helpers


def test_process_facets_fields_normalizes_keys_and_logic():
    facets_fields = {
        "extras_theme": {"values": ["Health"]},
        "tags_ngram": {"values": ["data"], "fts": True},
        "filter-logic-extras_theme": ["and"],
        "file_size": {"min": "5", "max": "10"},
    }

    expected = {
        "theme": {
            "logic": "and",
            "values": [
                {"ori_field": "extras_theme", "ori_value": "Health", "value": "Health"}
            ],
        },
        "tags": {
            "logic": "or",
            "values": [
                {
                    "ori_field": "tags_ngram",
                    "ori_value": "data",
                    "value": 'Search for "data"',
                }
            ],
        },
        "file_size": {
            "logic": "or",
            "values": [
                {"ori_field": "min_file_size", "ori_value": "5", "value": "From: 5"},
                {"ori_field": "max_file_size", "ori_value": "10", "value": "To: 10"},
            ],
        },
    }

    assert udc_helpers.process_facets_fields(facets_fields) == expected


def test_get_maturity_percentages_counts_core_and_custom_fields():
    config = [
        {
            "fields": [
                {"ckanField": "title"},
                {"ckanField": "description"},
                {"ckanField": "organization_and_visibility"},
                {"name": "custom_extra", "label": "Custom"},
            ]
        }
    ]
    pkg_dict = {
        "title": "Dataset",
        "notes": "Description lives in notes",
        "custom_extra": "value",
    }

    assert udc_helpers.get_maturity_percentages(config, pkg_dict) == ["100%"]
