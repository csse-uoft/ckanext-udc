from types import SimpleNamespace

from ckanext.udc.cli import udc as udc_cli


def test_get_number_field_names_uses_config_order():
    fields = udc_cli._get_number_field_names(
        {
            "maturity_model": [
                {
                    "fields": [
                        {"name": "title", "type": "text"},
                        {"name": "number_of_rows", "type": "number"},
                    ]
                },
                {
                    "fields": [
                        {"name": "number_of_cells", "type": "number"},
                        {"name": "number_of_rows", "type": "number"},
                    ]
                },
            ]
        }
    )

    assert fields == ["number_of_rows", "number_of_cells"]


def test_inspect_number_field_value_detects_fixable_localized_json():
    inspection = udc_cli._inspect_number_field_value('{"en": "351", "fr": "351"}')

    assert inspection == {
        "status": "fixable_localized",
        "normalized": "351",
    }


def test_inspect_number_field_value_flags_conflicting_localized_json():
    inspection = udc_cli._inspect_number_field_value('{"en": "351", "fr": "352"}')

    assert inspection == {
        "status": "invalid_localized",
        "normalized": None,
    }


def test_process_number_field_migration_dry_run_reports_without_mutating():
    package = SimpleNamespace(
        id="pkg-1",
        name="housing-data",
        extras={"number_of_cells": '{"en": "351"}'},
    )
    messages = []

    stats = udc_cli._process_number_field_migration(
        [package],
        ["number_of_cells"],
        fix=False,
        echo=messages.append,
    )

    assert package.extras["number_of_cells"] == '{"en": "351"}'
    assert stats == {
        "packages_scanned": 1,
        "packages_with_issues": 1,
        "issues_found": 1,
        "fixable": 1,
        "fixed": 0,
        "invalid": 0,
    }
    assert messages == [
        'Would fix package pkg-1 (housing-data) field "number_of_cells": \'{"en": "351"}\' -> \'351\''
    ]


def test_process_number_field_migration_fix_updates_fixable_values():
    package = SimpleNamespace(
        id="pkg-1",
        name="housing-data",
        extras={
            "number_of_cells": '{"en": "351"}',
            "number_of_rows": "not-a-number",
        },
    )
    messages = []

    stats = udc_cli._process_number_field_migration(
        [package],
        ["number_of_cells", "number_of_rows"],
        fix=True,
        echo=messages.append,
    )

    assert package.extras["number_of_cells"] == "351"
    assert package.extras["number_of_rows"] == "not-a-number"
    assert stats == {
        "packages_scanned": 1,
        "packages_with_issues": 1,
        "issues_found": 2,
        "fixable": 1,
        "fixed": 1,
        "invalid": 1,
    }
    assert messages == [
        'Fix package pkg-1 (housing-data) field "number_of_cells": \'{"en": "351"}\' -> \'351\'',
        'Invalid value on package pkg-1 (housing-data) field "number_of_rows": \'not-a-number\'',
    ]