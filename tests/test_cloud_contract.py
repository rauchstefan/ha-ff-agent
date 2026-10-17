"""Contract test for the Home Assistant APIs that tests can only stub.

The cloud integration cannot be imported in the test environment, so the tests
replace it with a stand-in. This test parses the installed source with ``ast`` (without
importing it) and fails if a name or parameter the stand-in relies on changes.
"""

from __future__ import annotations

import ast
from pathlib import Path

import homeassistant
import pytest

HA_ROOT = Path(homeassistant.__file__).parent


def _definitions(relative_path: str) -> dict[str, ast.AST]:
    """Return the top-level functions and classes of a Home Assistant module."""
    tree = ast.parse((HA_ROOT / relative_path).read_text(encoding="utf-8"))
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
    }


def _parameters(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    args = node.args
    return [arg.arg for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs)]


@pytest.mark.parametrize(
    ("name", "is_async", "parameters"),
    [
        ("async_active_subscription", False, ["hass"]),
        ("async_is_connected", False, ["hass"]),
        ("async_get_or_create_cloudhook", True, ["hass", "webhook_id"]),
        ("async_delete_cloudhook", True, ["hass", "webhook_id"]),
    ],
)
def test_cloud_functions_match_the_stand_in(
    name: str, is_async: bool, parameters: list[str]
) -> None:
    """The cloud helpers FF Agent calls exist with the expected signature."""
    node = _definitions("components/cloud/__init__.py")[name]

    assert isinstance(node, ast.AsyncFunctionDef if is_async else ast.FunctionDef)
    assert _parameters(node) == parameters


def test_cloud_exceptions_match_the_stand_in() -> None:
    """CloudNotConnected is a CloudNotAvailable, which the code catches."""
    definitions = _definitions("components/cloud/__init__.py")

    assert isinstance(definitions["CloudNotAvailable"], ast.ClassDef)
    not_connected = definitions["CloudNotConnected"]
    assert isinstance(not_connected, ast.ClassDef)
    assert [base.id for base in not_connected.bases if isinstance(base, ast.Name)] == [
        "CloudNotAvailable"
    ]


def test_webhook_url_helper_parameters() -> None:
    """webhook.async_generate_url still takes the keywords the code passes."""
    node = _definitions("components/webhook/__init__.py")["async_generate_url"]

    assert isinstance(node, ast.FunctionDef)
    assert {"allow_internal", "allow_external", "prefer_external"} <= set(
        _parameters(node)
    )
