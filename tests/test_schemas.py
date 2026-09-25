"""Schema-Tests für M0: siehe docs/bericht.md, Abschnitt 6 (Formate)."""

import json
from pathlib import Path

import jsonschema
import pytest

SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"

SCHEMA_FILES = ["pfm.schema.json", "project.schema.json", "pdiag.schema.json"]

PFM_BEISPIEL = {
    "format": "pfm/1",
    "class": "Form1",
    "type": "Form",
    "properties": {"caption": "Ampel", "width": 480, "height": 360, "theme": "system"},
    "events": {"on_create": "form_create"},
    "children": [
        {
            "name": "b_ein",
            "type": "Button",
            "properties": {
                "caption": "Einschalten",
                "left": 24,
                "top": 24,
                "width": 120,
                "height": 32,
                "variant": "primary",
            },
            "events": {"on_click": "b_ein_click"},
        },
        {
            "name": "s_rot",
            "type": "Shape",
            "properties": {
                "shape": "circle",
                "left": 200,
                "top": 24,
                "width": 64,
                "height": 64,
                "brush_color": "#000000",
            },
        },
    ],
}

PROJECT_BEISPIEL = {
    "format": "natter-project/1",
    "name": "Ampel",
    "type": "gui",
    "main": "main.py",
    "main_form": "u_main",
}

PDIAG_BEISPIEL = {
    "format": "pdiag/1",
    "type": "class",
    "page": {"size": "A4", "orientation": "landscape"},
    "style": "modern-light",
    "shapes": [
        {
            "id": "s1",
            "kind": "class",
            "x": 96,
            "y": 64,
            "w": 184,
            "h": 136,
            "text": {
                "name": "TAmpel",
                "attributes": ["-an: bool", "-zustand: str"],
                "methods": ["+einschalten()", "+get_zustand(): str"],
            },
            "abstract": False,
        }
    ],
    "connectors": [
        {
            "id": "c1",
            "kind": "composition",
            "from": "s1",
            "to": "s2",
            "waypoints": [[320, 132]],
            "labels": {"from": "1", "to": "3"},
        }
    ],
}


def load_schema(filename: str) -> dict:
    return json.loads((SCHEMAS_DIR / filename).read_text(encoding="utf-8"))


@pytest.mark.parametrize("filename", SCHEMA_FILES)
def test_schema_is_valid_json_schema(filename: str) -> None:
    schema = load_schema(filename)
    jsonschema.Draft202012Validator.check_schema(schema)


def test_pfm_beispiel_ist_gueltig() -> None:
    jsonschema.validate(PFM_BEISPIEL, load_schema("pfm.schema.json"))


def test_project_beispiel_ist_gueltig() -> None:
    jsonschema.validate(PROJECT_BEISPIEL, load_schema("project.schema.json"))


def test_pdiag_beispiel_ist_gueltig() -> None:
    jsonschema.validate(PDIAG_BEISPIEL, load_schema("pdiag.schema.json"))
