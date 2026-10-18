"""Contract test for the internals of the core integration ntfy.

FF Agent reads the subscription of a topic from the ntfy integration (subentry type,
keys, server URL) and relies on the semantics of its event entity. It must not import
``homeassistant.components.ntfy`` (that imports the library aiontfy). This test parses
the installed source with ``ast`` instead and fails if something the integration
relies on changes.
"""

from __future__ import annotations

import ast
from pathlib import Path

import homeassistant
from homeassistant import const as ha_const

from custom_components.ff_agent.const import (
    NTFY_CONF_TOPIC,
    NTFY_CONF_URL,
    NTFY_DEFAULT_SERVER,
    NTFY_DOMAIN,
    NTFY_SUBENTRY_TYPE,
)

HA_ROOT = Path(homeassistant.__file__).parent
NTFY = HA_ROOT / "components" / "ntfy"


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _constants(path: Path) -> dict[str, object]:
    """Return the module-level constants with a literal value."""
    constants: dict[str, object] = {}
    for node in _tree(path).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            target, value = node.target, node.value
        else:
            continue
        if isinstance(target, ast.Name) and isinstance(value, ast.Constant):
            constants[target.id] = value.value
    return constants


def _names(node: ast.AST) -> set[str]:
    """Return all names and attribute names used below a node."""
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
        elif isinstance(child, ast.Attribute):
            names.add(child.attr)
    return names


def test_ntfy_constants_match() -> None:
    """Domain, subentry type, topic key and default server are what FF Agent uses."""
    constants = _constants(NTFY / "const.py")

    assert constants["DOMAIN"] == NTFY_DOMAIN
    assert constants["SUBENTRY_TYPE_TOPIC"] == NTFY_SUBENTRY_TYPE
    assert constants["CONF_TOPIC"] == NTFY_CONF_TOPIC
    default_url = constants["DEFAULT_URL"]
    assert isinstance(default_url, str)
    assert default_url.startswith("https://ntfy.sh")
    assert default_url == NTFY_DEFAULT_SERVER


def test_ntfy_config_flow_stores_the_server_url() -> None:
    """The config entry of ntfy stores the server under CONF_URL ("url")."""
    tree = _tree(NTFY / "config_flow.py")
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "homeassistant.const"
        for alias in node.names
    }
    assert "CONF_URL" in imported
    assert ha_const.CONF_URL == NTFY_CONF_URL
    # The data of a new entry and of a topic contain the expected keys.
    dict_keys = {
        key.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Dict)
        for key in node.keys
        if isinstance(key, ast.Name)
    }
    assert {"CONF_URL", "CONF_TOPIC"} <= dict_keys


def test_ntfy_event_entity_is_an_event_entity_per_subentry() -> None:
    """One EventEntity per topic subentry; the platform passes the subentry ID."""
    tree = _tree(NTFY / "event.py")
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    assert any(
        "EventEntity" in {base.id for base in cls.bases if isinstance(base, ast.Name)}
        for cls in classes
    )
    setup = next(
        node
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "async_setup_entry"
    )
    keywords = {
        keyword.arg
        for node in ast.walk(setup)
        if isinstance(node, ast.Call)
        for keyword in node.keywords
    }
    assert "config_subentry_id" in keywords
    assert "subentries" in _names(setup)
    # The watchdog that reconnects and writes "available" (ADR 0003, 3.).
    assert "RECONNECT_INTERVAL" in _constants(NTFY / "event.py")


def test_event_entity_state_is_the_trigger_time() -> None:
    """The state of an event entity is the time of the last event, restored later."""
    tree = _tree(HA_ROOT / "components" / "event" / "__init__.py")
    event_entity = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "EventEntity"
    )
    bases = {base.id for base in event_entity.bases if isinstance(base, ast.Name)}
    assert "RestoreEntity" in bases
    methods = {
        node.name
        for node in event_entity.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    assert {"_trigger_event", "state", "async_internal_added_to_hass"} <= methods
    assert "isoformat" in _names(event_entity)


def test_registry_helpers_exist() -> None:
    """The registry helpers FF Agent uses exist with the expected parameters."""
    tree = _tree(HA_ROOT / "helpers" / "entity_registry.py")
    functions = {
        node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    resolve = functions["async_resolve_entity_id"]
    assert [arg.arg for arg in resolve.args.args] == ["registry", "entity_id_or_uuid"]
    registry_entry = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "RegistryEntry"
    )
    fields = {
        node.target.id
        for node in registry_entry.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    }
    assert {"config_entry_id", "config_subentry_id", "platform", "id"} <= fields


def test_get_url_takes_allow_cloud() -> None:
    """network.get_url still takes the keywords of the reachability probe."""
    tree = _tree(HA_ROOT / "helpers" / "network.py")
    get_url = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "get_url"
    )
    keywords = {arg.arg for arg in get_url.args.kwonlyargs}
    assert {"allow_internal", "allow_cloud", "prefer_external"} <= keywords


def test_restored_attribute() -> None:
    """The placeholder state of the registry is marked with "restored"."""
    assert ha_const.ATTR_RESTORED == "restored"


def _assigns_available_false(node: ast.AST) -> bool:
    """Return whether the code below the node sets _attr_available to False."""
    for child in ast.walk(node):
        if isinstance(child, ast.Assign | ast.AnnAssign):
            targets = child.targets if isinstance(child, ast.Assign) else [child.target]
            names = {
                target.attr if isinstance(target, ast.Attribute) else target.id
                for target in targets
                if isinstance(target, ast.Attribute | ast.Name)
            }
            value = child.value
            if (
                "_attr_available" in names
                and isinstance(value, ast.Constant)
                and value.value is False
            ):
                return True
    return False


def test_ntfy_entity_is_not_unavailable_when_added() -> None:
    """Adding the entity does not write "unavailable" by itself.

    The filter treats the first state after the registry placeholder as the restored
    value. That relies on the entity not going through an "unavailable" of its own
    while it is added: no available property, no _attr_available = False in the
    class body, in __init__ or in async_added_to_hass.
    """
    for path, name in (
        (NTFY / "entity.py", "NtfyBaseEntity"),
        (NTFY / "event.py", "NtfyEventEntity"),
    ):
        cls = next(
            node
            for node in _tree(path).body
            if isinstance(node, ast.ClassDef) and node.name == name
        )
        methods = {
            node.name: node
            for node in cls.body
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        }
        assert "available" not in methods
        class_level = [
            node for node in cls.body if isinstance(node, ast.Assign | ast.AnnAssign)
        ]
        assert not any(_assigns_available_false(node) for node in class_level)
        for method in ("__init__", "async_added_to_hass"):
            if method in methods:
                assert not _assigns_available_false(methods[method])
