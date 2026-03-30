from ckanext.udc_react.maintenance import (
    is_maintenance_exempt_path,
    is_maintenance_mode_enabled,
    should_render_maintenance,
)


def test_is_maintenance_mode_enabled_accepts_common_truthy_values():
    assert is_maintenance_mode_enabled(True) is True
    assert is_maintenance_mode_enabled("true") is True
    assert is_maintenance_mode_enabled("1") is True
    assert is_maintenance_mode_enabled("yes") is True


def test_is_maintenance_mode_enabled_defaults_to_false():
    assert is_maintenance_mode_enabled(None) is False
    assert is_maintenance_mode_enabled(False) is False
    assert is_maintenance_mode_enabled("false") is False


def test_is_maintenance_exempt_path_allows_dashboard_and_supporting_routes():
    assert is_maintenance_exempt_path("/udrc") is True
    assert is_maintenance_exempt_path("/udrc/system-config/manage") is True
    assert is_maintenance_exempt_path("/api/3/action/package_search") is True
    assert is_maintenance_exempt_path("/user/login") is True
    assert is_maintenance_exempt_path("/base/css/main.css") is True


def test_should_render_maintenance_only_for_non_exempt_html_pages():
    assert should_render_maintenance(
        path="/catalogue",
        enabled=True,
        method="GET",
        accept_header="text/html,application/xhtml+xml",
    ) is True

    assert should_render_maintenance(
        path="/udrc",
        enabled=True,
        method="GET",
        accept_header="text/html,application/xhtml+xml",
    ) is False

    assert should_render_maintenance(
        path="/catalogue",
        enabled=True,
        method="POST",
        accept_header="text/html,application/xhtml+xml",
    ) is False

    assert should_render_maintenance(
        path="/catalogue",
        enabled=False,
        method="GET",
        accept_header="text/html,application/xhtml+xml",
    ) is False