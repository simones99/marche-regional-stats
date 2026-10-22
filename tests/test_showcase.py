"""The showcase as build-showcase assembles it, which is what gets published."""

import shutil
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from marche_stats import cli

PAGES = (
    "01-overview.png",
    "02-population-health.png",
    "03-economy-labour.png",
    "04-education.png",
    "05-provinces.png",
    "06-business.png",
    "07-benchmark.png",
    "08-about.png",
)


class _Tags(HTMLParser):
    """Every start tag of a page, with its attributes."""

    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def _tags(page: Path) -> list[tuple[str, dict[str, str | None]]]:
    parser = _Tags()
    parser.feed(page.read_text(encoding="utf-8"))
    return parser.tags


def _local_references(page: Path) -> list[str]:
    references = []
    for _, attrs in _tags(page):
        for name in ("src", "href", "poster"):
            value = attrs.get(name)
            if value and not urlsplit(value).scheme and not value.startswith(("#", "//")):
                references.append(urlsplit(value).path)
    return references


def _build(tmp_path: Path, *extra: str) -> Path:
    out = tmp_path / "showcase"
    assert cli.main(["build-showcase", "--out", str(out), *extra]) == 0
    return out


def test_every_local_reference_resolves_to_a_written_file(tmp_path):
    out = _build(tmp_path)
    references = _local_references(out / "index.html")
    assert references
    missing = [ref for ref in references if not (out / ref).is_file()]
    assert missing == []
    names = {Path(ref).name for ref in references}
    assert {"01-overview.png", "marche-regional-profile.pdf"} <= names


def test_the_eight_pages_and_the_pdf_are_published(tmp_path):
    out = _build(tmp_path)
    published = {path.name for path in out.rglob("*") if path.is_file()}
    assert {*PAGES, "marche-regional-profile.pdf"} <= published


def test_the_clip_recording_notes_are_not_published(tmp_path):
    out = _build(tmp_path)
    assert not (out / "README.md").exists()


def test_every_report_page_is_shown_and_opens_at_full_size(tmp_path):
    out = _build(tmp_path)
    tags = _tags(out / "index.html")
    shown = {Path(attrs["src"]).name for tag, attrs in tags if tag == "img" and attrs.get("src")}
    linked = {Path(attrs["href"]).name for tag, attrs in tags if tag == "a" and attrs.get("href")}
    assert set(PAGES) <= shown
    assert set(PAGES) <= linked


def test_every_image_has_a_text_alternative(tmp_path):
    out = _build(tmp_path)
    images = [attrs for tag, attrs in _tags(out / "index.html") if tag == "img"]
    assert images
    assert [img["src"] for img in images if not (img.get("alt") or "").strip()] == []


def _meta(page: Path) -> dict[str, str | None]:
    """Content of each meta tag, by its property or name."""
    return {
        attrs.get("property") or attrs.get("name"): attrs.get("content")
        for tag, attrs in _tags(page)
        if tag == "meta" and (attrs.get("property") or attrs.get("name"))
    }


def test_the_link_preview_tags_are_declared(tmp_path):
    meta = _meta(_build(tmp_path) / "index.html")
    for key in (
        "og:title",
        "og:description",
        "og:image",
        "og:image:alt",
        "twitter:title",
        "twitter:description",
        "twitter:image",
    ):
        assert (meta.get(key) or "").strip(), key
    assert meta.get("twitter:card") == "summary_large_image"


def test_the_preview_image_is_the_overview_on_the_pages_domain(tmp_path):
    out = _build(tmp_path)
    meta = _meta(out / "index.html")
    pages = "https://simones99.github.io/marche-regional-stats/"
    assert meta.get("og:url") == pages
    assert meta.get("og:image") == pages + "report/01-overview.png"
    assert meta.get("twitter:image") == meta.get("og:image")
    assert (out / "report" / "01-overview.png").is_file()


def test_visits_are_counted_on_the_authors_goatcounter_account(tmp_path):
    out = _build(tmp_path)
    counters = [
        (attrs["data-goatcounter"], attrs.get("src"))
        for tag, attrs in _tags(out / "index.html")
        if tag == "script" and "data-goatcounter" in attrs
    ]
    assert counters == [("https://halfhit.goatcounter.com/count", "https://gc.zgo.at/count.js")]


def test_only_the_pdf_and_repository_buttons_are_counted_as_clicks(tmp_path):
    out = _build(tmp_path)
    clicks = {
        attrs.get("href"): attrs["data-goatcounter-click"]
        for _, attrs in _tags(out / "index.html")
        if "data-goatcounter-click" in attrs
    }
    assert clicks == {
        "report/marche-regional-profile.pdf": "pdf",
        "https://github.com/simones99/marche-regional-stats": "repository",
    }


def test_a_missing_report_export_stops_the_build(tmp_path, capsys):
    exports = tmp_path / "exports"
    shutil.copytree(cli.ROOT / "powerbi" / "exports", exports)
    (exports / "png" / "06-business.png").unlink()
    argv = ["build-showcase", "--exports", str(exports), "--out", str(tmp_path / "out")]
    assert cli.main(argv) == 1
    assert "06-business.png" in capsys.readouterr().err
