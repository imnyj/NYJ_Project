"""Scientific PDF reader.

Two modes:
    (a) GROBID mode   — structured extraction (sections, references, figures).
                         Requires a running GROBID server (Docker or local).
    (b) Plain mode    — PyPDF2 fallback, just text. Works everywhere.

The ContextualChunker doesn't care which mode produced the text; it only
needs a string. But GROBID mode preserves section structure which helps
Librarian filter only the relevant parts into refs.json.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from core.logger import get_logger

log = get_logger("pdf_reader")

try:
    from grobid_client.grobid_client import GrobidClient  # noqa: F401
    _GROBID_AVAILABLE = True
except ImportError:
    _GROBID_AVAILABLE = False

try:
    import pypdf  # noqa: F401
    _PYPDF_AVAILABLE = True
except ImportError:
    _PYPDF_AVAILABLE = False


@dataclass
class ParsedPaper:
    title: str = ""
    abstract: str = ""
    full_text: str = ""
    sections: list[dict] = field(default_factory=list)   # [{name, text}]
    references: list[dict] = field(default_factory=list)
    source_path: str = ""


class PDFReader:
    def __init__(
        self,
        *,
        grobid_url: str | None = None,
    ):
        self.grobid_url = grobid_url or os.environ.get(
            "GROBID_URL", "http://localhost:8070"
        )

    def read(self, pdf_path: str | Path) -> ParsedPaper:
        pdf_path = Path(pdf_path)
        if not pdf_path.is_file():
            raise FileNotFoundError(pdf_path)

        if _GROBID_AVAILABLE and self._grobid_reachable():
            try:
                return self._read_grobid(pdf_path)
            except Exception as e:
                log.warning("grobid_failed_fallback", err=str(e))

        if _PYPDF_AVAILABLE:
            return self._read_pypdf(pdf_path)

        log.error("no_pdf_backend_available")
        return ParsedPaper(source_path=str(pdf_path))

    # ------------------------------------------------------------- grobid

    def _grobid_reachable(self) -> bool:
        if not _GROBID_AVAILABLE:
            return False
        try:
            import requests
            r = requests.get(f"{self.grobid_url}/api/isalive", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def _read_grobid(self, pdf_path: Path) -> ParsedPaper:
        import xml.etree.ElementTree as ET
        import requests

        with pdf_path.open("rb") as f:
            r = requests.post(
                f"{self.grobid_url}/api/processFulltextDocument",
                files={"input": f},
                timeout=120,
            )
        r.raise_for_status()
        # TEI XML
        ns = {"tei": "http://www.tei-c.org/ns/1.0"}
        root = ET.fromstring(r.text)

        def _text_of(elem) -> str:
            return "".join(elem.itertext()).strip() if elem is not None else ""

        title_el = root.find(".//tei:titleStmt/tei:title", ns)
        abstract_el = root.find(".//tei:profileDesc/tei:abstract", ns)
        sections: list[dict] = []
        # TEI <div> elements nest; if we walked every div we'd emit the same
        # paragraphs multiple times (once per ancestor). Collect text at the
        # DEEPEST div level by only keeping divs whose <p> children are not
        # themselves inside another div's descendants — i.e. leaf divs.
        for div in root.findall(".//tei:body//tei:div", ns):
            # Is this div a "leaf" (no <div> children)?
            if div.find("tei:div", ns) is not None:
                continue
            head = div.find("tei:head", ns)
            name = _text_of(head) or ""
            text = "\n".join(_text_of(p) for p in div.findall("tei:p", ns))
            if text:
                sections.append({"name": name, "text": text})

        full = "\n\n".join(s["text"] for s in sections)
        return ParsedPaper(
            title=_text_of(title_el),
            abstract=_text_of(abstract_el),
            full_text=full,
            sections=sections,
            source_path=str(pdf_path),
        )

    # -------------------------------------------------------------- pypdf

    def _read_pypdf(self, pdf_path: Path) -> ParsedPaper:
        import pypdf
        text_parts: list[str] = []
        with pdf_path.open("rb") as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
        full = "\n\n".join(t for t in text_parts if t.strip())
        return ParsedPaper(
            full_text=full,
            source_path=str(pdf_path),
        )
