import pypdfium2 as pdfium
import pytest
from PIL import Image

from marche_stats import cli, pngs


def _pdf(path, pages: int) -> None:
    document = pdfium.PdfDocument.new()
    for _ in range(pages):
        document.new_page(960, 540)
    document.save(str(path))
    document.close()


def test_export_writes_one_png_per_page(tmp_path):
    pdf = tmp_path / "report.pdf"
    _pdf(pdf, len(pngs.PAGE_SLUGS))
    paths = pngs.export(pdf, tmp_path / "png", width=640)
    assert [p.name for p in paths] == [f"{slug}.png" for slug in pngs.PAGE_SLUGS]
    with Image.open(paths[0]) as image:
        assert image.size == (640, 360)


def test_export_refuses_a_pdf_with_other_pages(tmp_path):
    pdf = tmp_path / "report.pdf"
    _pdf(pdf, 3)
    with pytest.raises(ValueError, match="3 pages"):
        pngs.export(pdf, tmp_path / "png")


def test_cli_export_pngs_writes_next_to_the_pdf(tmp_path):
    pdf = tmp_path / "report.pdf"
    _pdf(pdf, len(pngs.PAGE_SLUGS))
    assert cli.main(["export-pngs", "--pdf", str(pdf)]) == 0
    assert len(list((tmp_path / "png").glob("*.png"))) == len(pngs.PAGE_SLUGS)
