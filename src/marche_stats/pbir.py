"""Write Power BI report pages in the PBIR format from a compact layout.

A layout gives each visual a type, a position and the fields it shows. The formatting a
theme cannot set is done once in Power BI Desktop, so scaffold() never overwrites a page
folder that exists unless asked: after the first Desktop session, Desktop's files win.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Collection
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
    return hashlib.sha1("\x1f".join(parts).encode("utf-8")).hexdigest()[:20]


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


def _dump(body: dict) -> str:
    return json.dumps(body, indent=2, ensure_ascii=False) + "\n"


def _page_files(page: Page) -> dict[Path, str]:
    """Every file of a page, serialised, keyed by its path relative to the page folder."""
    files = {Path("page.json"): _dump(page_json(page))}
    for order, v in enumerate(page.visuals):
        path = Path("visuals") / object_id(page.key, v.key) / "visual.json"
        files[path] = _dump(visual_json(page.key, v, order))
    return files


def _write_page(folder: Path, files: dict[Path, str]) -> None:
    """Stage the page, swap it in, and keep the old folder until the swap succeeds."""
    staging = folder.with_name(folder.name + ".tmp")
    backup = folder.with_name(folder.name + ".old")
    if backup.exists() and not folder.exists():  # an earlier run stopped mid-swap
        backup.rename(folder)
    shutil.rmtree(staging, ignore_errors=True)
    shutil.rmtree(backup, ignore_errors=True)
    try:
        for relative, text in files.items():
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
        if folder.exists():
            folder.rename(backup)  # PermissionError if a file is locked: nothing is lost
        try:
            staging.rename(folder)
        except BaseException:
            if backup.exists():
                backup.rename(folder)
            raise
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    shutil.rmtree(backup, ignore_errors=True)


def _merged_order(order: list[str], ours: list[str]) -> list[str]:
    """Keep the existing order; add each missing layout page after its nearest predecessor."""
    merged = list(order)
    for index, name in enumerate(ours):
        if name in merged:
            continue
        position = 0
        for earlier in reversed(ours[:index]):
            if earlier in merged:
                position = merged.index(earlier) + 1
                break
        merged.insert(position, name)
    return merged


def _validate(pages: list[Page]) -> None:
    if not pages:
        raise ValueError("no pages in the layout")
    keys = [p.key for p in pages]
    duplicates = {k for k in keys if keys.count(k) > 1}
    if duplicates:
        raise ValueError(f"duplicate page keys {sorted(duplicates)}")
    for page in pages:
        keys = [v.key for v in page.visuals]
        duplicates = {k for k in keys if keys.count(k) > 1}
        if duplicates:
            raise ValueError(f"{page.name}: duplicate visual keys {sorted(duplicates)}")


def scaffold(pages: list[Page], definition: Path, force: Collection[str] = ()) -> list[str]:
    """Write the pages whose folder does not exist yet; return their names.

    Pages whose key is in force are deleted and rewritten; other existing pages are left
    alone. A page deleted in Desktop is therefore created again on the next run, and
    renaming a page's layout key writes a new page and leaves the old folder behind.

    pages.json keeps Desktop's page order and active page: layout pages it does not list
    are inserted after their nearest earlier layout page, and it is rewritten only if that
    changes something. Pages the layout does not know (the Phase A model check page) stay.
    """
    _validate(pages)
    unknown = set(force) - {p.key for p in pages}
    if unknown:
        raise ValueError(f"unknown page keys {sorted(unknown)}")
    written = []
    pages_dir = definition / "pages"
    for page in pages:
        folder = pages_dir / object_id(page.key)
        if folder.exists() and page.key not in force:
            continue
        _write_page(folder, _page_files(page))
        written.append(page.name)

    meta_path = pages_dir / "pages.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    ours = [object_id(p.key) for p in pages]
    order = _merged_order(meta["pageOrder"], ours)
    active = meta.get("activePageName")
    if active not in order:
        active = ours[0]
    if order != meta["pageOrder"] or active != meta.get("activePageName"):
        meta["pageOrder"], meta["activePageName"] = order, active
        meta_path.write_text(_dump(meta), encoding="utf-8", newline="\n")
    return written
