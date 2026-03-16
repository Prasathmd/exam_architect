"""Export agent: generates PDF or DOCX question banks."""
from __future__ import annotations

import logging
from urllib.request import urlretrieve
from pathlib import Path
from datetime import datetime

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class ExportAgent:
    """Exports MCQ text to PDF or DOCX."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._settings.export_dir.mkdir(parents=True, exist_ok=True)
        self._fonts_dir = self._settings.export_dir / "fonts"
        self._fonts_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_tamil_font(self) -> Path | None:
        """Find or download a Tamil-capable Unicode font for PDF export."""
        candidates = [
            Path("/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf"),
            Path("/usr/share/fonts/truetype/lohit-tamil/Lohit-Tamil.ttf"),
            Path("/usr/share/fonts/truetype/noto/NotoSerifTamil-Regular.ttf"),
            self._fonts_dir / "NotoSansTamil-Regular.ttf",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate

        download_targets = [
            (
                "https://github.com/notofonts/tamil/raw/main/fonts/ttf/NotoSansTamil/NotoSansTamil-Regular.ttf",
                self._fonts_dir / "NotoSansTamil-Regular.ttf",
            ),
            (
                "https://github.com/notofonts/tamil/raw/main/fonts/ttf/NotoSerifTamil/NotoSerifTamil-Regular.ttf",
                self._fonts_dir / "NotoSerifTamil-Regular.ttf",
            ),
        ]
        for url, target in download_targets:
            try:
                logger.info("Downloading Tamil font for PDF export: %s", url)
                urlretrieve(url, target)
                if target.exists() and target.stat().st_size > 0:
                    return target
            except Exception:
                continue
        return None

    def _path_for_job(self, job_id: str, ext: str) -> Path:
        return self._settings.export_dir / f"{job_id}_questions_{datetime.now():%Y%m%d_%H%M%S}{ext}"

    def to_docx(self, content: str, job_id: str) -> Path:
        """Write content to a DOCX file; return path."""
        try:
            from docx import Document
            from docx.shared import Pt
        except ImportError:
            raise RuntimeError("python-docx required: pip install python-docx")
        doc = Document()
        doc.add_paragraph(content.replace("\n\n", "\n"), style="Normal")
        path = self._path_for_job(job_id, ".docx")
        doc.save(path)
        return path

    def to_pdf(self, content: str, job_id: str) -> Path:
        """Write content to formatted PDF; return path."""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.enums import TA_JUSTIFY
        except ImportError:
            raise RuntimeError("reportlab required for PDF export: pip install reportlab")

        font_path = self._resolve_tamil_font()
        if not font_path:
            raise RuntimeError(
                "Tamil Unicode font not found. Install Noto Sans Tamil or allow internet for auto-download."
            )
        font_name = "ExamUnicodeTamil"
        try:
            pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
        except Exception as e:
            raise RuntimeError(f"Unable to register Tamil font for PDF: {e}") from e

        pdf_path = self._path_for_job(job_id, ".pdf")
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            leftMargin=1.8 * cm,
            rightMargin=1.8 * cm,
            topMargin=1.8 * cm,
            bottomMargin=1.8 * cm,
            title=f"Question Bank - {job_id}",
        )

        styles = getSampleStyleSheet()
        normal = ParagraphStyle(
            "ExamNormal",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        )
        heading = ParagraphStyle(
            "ExamHeading",
            parent=styles["Heading2"],
            fontName=font_name,
            fontSize=13,
            leading=18,
            spaceAfter=10,
        )

        story = [Paragraph("Exam-Architect AI - Question Bank", heading), Spacer(1, 8)]
        for line in content.splitlines():
            safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if not safe.strip():
                story.append(Spacer(1, 6))
                continue
            story.append(Paragraph(safe, normal))
        doc.build(story)
        return pdf_path

    def export(self, content: str, job_id: str, format: str = "docx") -> Path:
        """Export content to format ('docx' or 'pdf'). Returns file path."""
        if format == "pdf":
            return self.to_pdf(content, job_id)
        return self.to_docx(content, job_id)
