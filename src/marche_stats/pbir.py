"""Write Power BI report pages in the PBIR format from a compact layout.

A layout gives each visual a type, a position and the fields it shows. The formatting a
theme cannot set is done once in Power BI Desktop, so scaffold() never overwrites a page
folder that exists unless asked: after the first Desktop session, Desktop's files win.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

SCHEMAS = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
VISUAL_SCHEMA = f"{SCHEMAS}/visualContainer/2.13.0/schema.json"
PAGE_SCHEMA = f"{SCHEMAS}/page/2.1.0/schema.json"
HIDDEN = "HiddenInViewMode"


@dataclass(frozen=True)
class Field:
    """A model column or measure."""

    table: str
    name: str
    measure: bool = True


def M(name: str) -> Field:
    """A measure of the _Measures table."""
    return Field("_Measures", name)


def C(table: str, name: str) -> Field:
    """A column."""
    return Field(table, name, measure=False)


@dataclass(frozen=True)
class Visual:
    key: str
    type: str
    x: int
    y: int
    w: int
    h: int
    roles: dict[str, list[Field]] = field(default_factory=dict)
    title: str | None = None
    alt: str | None = None
    objects: dict | None = None
    filters: list[dict] = field(default_factory=list)
    sort: tuple[Field, str] | None = None


@dataclass(frozen=True)
class Page:
    key: str
    name: str
    visuals: list[Visual]
    hidden: bool = False
    width: int = 1280
    height: int = 720


def object_id(*parts: str) -> str:
    """Stable 20-character hex name, the form Desktop gives pages and visuals."""
    return hashlib.sha1("/".join(parts).encode("utf-8")).hexdigest()[:20]


def _literal_text(value: str | float | bool) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return f"{value}D"
    return "'" + value.replace("'", "''") + "'"


def literal(value: str | float | bool) -> dict:
    return {"expr": {"Literal": {"Value": _literal_text(value)}}}


def solid(color: str) -> dict:
    return {"solid": {"color": literal(color)}}


def field_expr(f: Field) -> dict:
    kind = "Measure" if f.measure else "Column"
    return {kind: {"Expression": {"SourceRef": {"Entity": f.table}}, "Property": f.name}}


def projection(f: Field) -> dict:
    return {"field": field_expr(f), "queryRef": f"{f.table}.{f.name}", "nativeQueryRef": f.name}


def in_filter(column: Field, values: list[str | bool]) -> dict:
    """Visual-level filter keeping the rows whose column is one of the values."""
    alias = column.table[0].lower()
    return {
        "name": object_id("filter", column.table, column.name, *map(str, values)),
        "field": field_expr(column),
        "type": "Categorical",
        "filter": {
            "Version": 2,
            "From": [{"Name": alias, "Entity": column.table, "Type": 0}],
            "Where": [
                {
                    "Condition": {
                        "In": {
                            "Expressions": [
                                {
                                    "Column": {
                                        "Expression": {"SourceRef": {"Source": alias}},
                                        "Property": column.name,
                                    }
                                }
                            ],
                            "Values": [[{"Literal": {"Value": _literal_text(v)}}] for v in values],
                        }
                    }
                }
            ],
        },
    }


def visual_json(page_key: str, v: Visual, order: int) -> dict:
    visual: dict = {"visualType": v.type}
    if v.roles:
        visual["query"] = {
            "queryState": {
                role: {"projections": [projection(f) for f in fields]}
                for role, fields in v.roles.items()
            }
        }
        if v.sort:
            sort_field, direction = v.sort
            visual["query"]["sortDefinition"] = {
                "sort": [{"field": field_expr(sort_field), "direction": direction}]
            }
    if v.objects:
        visual["objects"] = v.objects
    container = {}
    if v.title is not None:
        container["title"] = [{"properties": {"show": literal(True), "text": literal(v.title)}}]
    if v.alt is not None:
        container["general"] = [{"properties": {"altText": literal(v.alt)}}]
    if container:
        visual["visualContainerObjects"] = container
    visual["drillFilterOtherVisuals"] = True
    body = {
        "$schema": VISUAL_SCHEMA,
        "name": object_id(page_key, v.key),
        "position": {
            "x": v.x,
            "y": v.y,
            "z": order * 1000,
            "height": v.h,
            "width": v.w,
            "tabOrder": order * 1000,
        },
        "visual": visual,
    }
    if v.filters:
        body["filterConfig"] = {"filters": v.filters}
    return body


def page_json(p: Page) -> dict:
    body = {
        "$schema": PAGE_SCHEMA,
        "name": object_id(p.key),
        "displayName": p.name,
        "displayOption": "FitToPage",
        "height": p.height,
        "width": p.width,
    }
    if p.hidden:
        body["visibility"] = HIDDEN
    return body


def _write(path: Path, body: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(body, indent=2, ensure_ascii=False) + "\n")


def scaffold(pages: list[Page], definition: Path, force: bool = False) -> list[str]:
    """Write the pages that do not exist yet (all of them with force); return their names.

    The layout's pages come first in pages.json, in layout order; pages the layout does not
    know (the Phase A model check page) keep their place after them.
    """
    for page in pages:
        keys = [v.key for v in page.visuals]
        duplicates = {k for k in keys if keys.count(k) > 1}
        if duplicates:
            raise ValueError(f"{page.name}: duplicate visual keys {sorted(duplicates)}")

    written = []
    pages_dir = definition / "pages"
    for page in pages:
        folder = pages_dir / object_id(page.key)
        if folder.exists():
            if not force:
                continue
            shutil.rmtree(folder)
        _write(folder / "page.json", page_json(page))
        for order, v in enumerate(page.visuals):
            _write(
                folder / "visuals" / object_id(page.key, v.key) / "visual.json",
                visual_json(page.key, v, order),
            )
        written.append(page.name)

    meta_path = pages_dir / "pages.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    ours = [object_id(p.key) for p in pages]
    meta["pageOrder"] = ours + [name for name in meta["pageOrder"] if name not in ours]
    meta["activePageName"] = ours[0]
    _write(meta_path, meta)
    return written
