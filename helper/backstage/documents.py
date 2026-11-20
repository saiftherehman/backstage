"""Reads a presentation or document into plain text for the teleprompter.

Supported: .txt, .md, .docx, .pdf, .pptx. For slides, the speaker notes are
used when a slide has them, since that is what gets said; otherwise the
slide's own text.
"""

from pathlib import Path

SUPPORTED = (".txt", ".md", ".docx", ".pdf", ".pptx")


def read_text(path):
    path = Path(path)
    kind = path.suffix.lower()
    if kind in (".txt", ".md"):
        return path.read_text(errors="replace")
    if kind == ".docx":
        import docx
        return "\n".join(p.text for p in docx.Document(path).paragraphs)
    if kind == ".pdf":
        from pypdf import PdfReader
        return "\n\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    if kind == ".pptx":
        return _slides(path)
    raise ValueError(f"Cannot read {path.suffix} files. Use one of: {', '.join(SUPPORTED)}")


def _slides(path):
    from pptx import Presentation
    parts = []
    for number, slide in enumerate(Presentation(path).slides, start=1):
        notes = ""
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text.strip()
        text = notes or "\n".join(shape.text_frame.text for shape in slide.shapes
                                  if shape.has_text_frame and shape.text_frame.text.strip())
        parts.append(f"[Slide {number}]\n{text.strip()}")
    return "\n\n".join(parts)
