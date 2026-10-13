"""One PNG per report page, rendered from the PDF that Power BI Desktop exports.

Desktop exports the visible pages in navigation order; the file names follow that order.
"""

from __future__ import annotations

from pathlib import Path

import pypdfium2 as pdfium

PAGE_SLUGS = (
    "01-overview",
    "02-population-health",
    "03-economy-labour",
    "04-education",
    "05-provinces",
    "06-business",
    "07-benchmark",
    "08-about",
)


def export(pdf: Path, out_dir: Path, width: int = 1600) -> list[Path]:
    """Render every page of the PDF to out_dir/<slug>.png, width pixels wide."""
    document = pdfium.PdfDocument(str(pdf))
    try:
        if len(document) != len(PAGE_SLUGS):
            raise ValueError(
                f"{pdf.name} has {len(document)} pages; expected {len(PAGE_SLUGS)}, "
                "the visible report pages"
            )
        out_dir.mkdir(parents=True, exist_ok=True)
        paths = []
        for index, slug in enumerate(PAGE_SLUGS):
            page = document[index]
            image = page.render(scale=width / page.get_width()).to_pil()
            path = out_dir / f"{slug}.png"
            image.save(path, optimize=True)
            paths.append(path)
        return paths
    finally:
        document.close()
