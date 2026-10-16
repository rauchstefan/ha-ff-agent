"""Static checks for the HACS and Home Assistant metadata files."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest

from custom_components.ff_agent.const import DOMAIN

ROOT = Path(__file__).parent.parent
INTEGRATION = ROOT / "custom_components" / DOMAIN
HACS_REQUIRED_MANIFEST_KEYS = {
    "domain",
    "documentation",
    "issue_tracker",
    "codeowners",
    "name",
    "version",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _flatten(data: dict, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for key, value in data.items():
        full = f"{prefix}{key}"
        if isinstance(value, dict):
            keys |= _flatten(value, f"{full}.")
        else:
            keys.add(full)
    return keys


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", data[16:24])


def test_hacs_json_has_only_name_and_homeassistant() -> None:
    """hacs.json holds exactly the agreed keys."""
    assert _load(ROOT / "hacs.json") == {
        "name": "FF Agent",
        "homeassistant": "2026.3.0",
    }


def test_manifest_has_hacs_required_keys() -> None:
    """The manifest contains all keys HACS requires and the domain matches."""
    manifest = _load(INTEGRATION / "manifest.json")
    assert HACS_REQUIRED_MANIFEST_KEYS <= manifest.keys()
    assert manifest["domain"] == DOMAIN
    assert {"iot_class", "config_flow", "integration_type"} <= manifest.keys()


def test_manifest_key_order() -> None:
    """Hassfest order: domain, name, then the remaining keys alphabetically."""
    keys = list(_load(INTEGRATION / "manifest.json"))
    assert keys[:2] == ["domain", "name"]
    assert keys[2:] == sorted(keys[2:])


def test_translations_en_de_have_same_keys() -> None:
    """German and English translations cover the same keys."""
    en = _flatten(_load(INTEGRATION / "translations" / "en.json"))
    de = _flatten(_load(INTEGRATION / "translations" / "de.json"))
    assert en == de


@pytest.mark.parametrize(
    ("name", "size"),
    [("icon.png", (256, 256)), ("icon@2x.png", (512, 512))],
)
def test_brand_icon_dimensions(name: str, size: tuple[int, int]) -> None:
    """Brand icons have the sizes required for local brand images."""
    assert _png_size(INTEGRATION / "brand" / name) == size
