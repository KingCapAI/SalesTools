"""Convert vector logo formats (PDF, SVG, AI, EPS) to PNG so they can be sent to Gemini.

Gemini's image API only accepts raster formats. Users frequently have logos in
vector formats — this service rasterizes them at upload time. The original
filename gets a .png extension; downstream code sees only PNG bytes.

Backends:
- PDF / SVG / modern .ai (Illustrator CS2+, PDF-wrapped) → PyMuPDF (pure
  Python wheel, no system deps)
- EPS / older .ai (PostScript) → Pillow + Ghostscript binary
"""

import io
from pathlib import Path
from typing import Tuple

from PIL import Image

VECTOR_EXTENSIONS = {".pdf", ".svg", ".ai", ".eps"}

# MIME types that map to vector formats. Browsers report these inconsistently
# (especially for .ai files), so we also fall back to the extension.
VECTOR_MIMES = {
    "application/pdf",
    "image/svg+xml",
    "application/postscript",   # EPS, old .ai
    "application/illustrator",  # some browsers for .ai
    "application/eps",
    "image/x-eps",
}

DEFAULT_RENDER_DPI = 300       # high-quality rasterization
MAX_OUTPUT_DIMENSION = 2048    # cap to keep payloads reasonable for Gemini


def is_vector_upload(filename: str, mime: str | None = None) -> bool:
    """Return True if the upload looks like a vector format we should convert."""
    ext = Path(filename or "").suffix.lower()
    if ext in VECTOR_EXTENSIONS:
        return True
    if mime and mime.lower() in VECTOR_MIMES:
        return True
    return False


def convert_to_png(data: bytes, source_filename: str) -> Tuple[bytes, str, str]:
    """Convert vector bytes to PNG.

    Returns (png_bytes, new_filename_with_png_ext, new_mime_type).
    Raises ValueError on unsupported format or RuntimeError on conversion failure.
    """
    ext = Path(source_filename or "").suffix.lower()
    base = Path(source_filename or "logo").stem or "logo"
    new_filename = f"{base}.png"

    if ext == ".svg":
        png_bytes = _convert_with_pymupdf(data, filetype="svg")
    elif ext == ".pdf":
        png_bytes = _convert_with_pymupdf(data, filetype="pdf")
    elif ext == ".ai":
        # .ai from Illustrator CS2+ is a PDF wrapper — PyMuPDF reads it.
        # If that fails (older PostScript-based .ai), fall back to Ghostscript.
        try:
            png_bytes = _convert_with_pymupdf(data, filetype="pdf")
        except Exception as pdf_err:
            try:
                png_bytes = _convert_postscript(data)
            except Exception as ps_err:
                raise RuntimeError(
                    f"Could not convert .ai file. Tried PDF parser ({pdf_err}) "
                    f"and PostScript parser ({ps_err}). Re-save the file as PDF "
                    "from Illustrator and try again."
                ) from ps_err
    elif ext == ".eps":
        png_bytes = _convert_postscript(data)
    else:
        raise ValueError(f"Unsupported vector format: {ext or '(unknown)'}")

    return _cap_dimensions(png_bytes), new_filename, "image/png"


# --- Format-specific converters ---


def _convert_with_pymupdf(data: bytes, filetype: str) -> bytes:
    """Render first page/frame of a PDF or SVG at high DPI via PyMuPDF."""
    import fitz  # PyMuPDF

    doc = fitz.open(stream=data, filetype=filetype)
    try:
        if doc.page_count == 0:
            raise ValueError(f"{filetype.upper()} file has no pages")
        page = doc[0]
        zoom = DEFAULT_RENDER_DPI / 72  # PyMuPDF assumes 72 dpi base
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=True)
        return pix.tobytes("png")
    finally:
        doc.close()


def _convert_postscript(data: bytes) -> bytes:
    """Render PostScript (.eps, old .ai) via Pillow's EPS plugin (needs Ghostscript)."""
    img = Image.open(io.BytesIO(data))
    # Pillow's EPS loader supports .load(scale=N) for higher resolution
    try:
        img.load(scale=4)
    except TypeError:
        img.load()

    if img.mode != "RGBA":
        img = img.convert("RGBA")

    out = io.BytesIO()
    img.save(out, "PNG")
    return out.getvalue()


def _cap_dimensions(png_bytes: bytes) -> bytes:
    """Downscale if either dimension exceeds MAX_OUTPUT_DIMENSION."""
    img = Image.open(io.BytesIO(png_bytes))
    if max(img.size) <= MAX_OUTPUT_DIMENSION:
        return png_bytes
    img.thumbnail((MAX_OUTPUT_DIMENSION, MAX_OUTPUT_DIMENSION), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, "PNG", optimize=True)
    return out.getvalue()
