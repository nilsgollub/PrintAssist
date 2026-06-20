"""
PDF manipulation tools using pypdf and pikepdf.

Routing hints (natural language triggers for Claude Code):
  merge / zusammenführen / kombinieren → merge_pdfs()
  split / aufteilen / trennen          → split_pdf()
  rotate / drehen                      → rotate_pages()
  watermark / Wasserzeichen            → add_watermark()
  encrypt / verschlüsseln / Passwort   → encrypt_pdf()
  decrypt / entschlüsseln              → decrypt_pdf()
  extract / extrahieren / Seiten raus  → extract_pages()

NOTE: Pure text editing inside PDFs is NOT possible with these tools.
      Direct the user to Adobe Acrobat or another PDF editor for that.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import pypdf
import pikepdf


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------

def merge_pdfs(input_paths: Sequence[str | Path], output_path: str | Path) -> Path:
    """
    Merge multiple PDF files into one.

    Natural language triggers:
      "Merge diese PDFs", "PDFs zusammenführen", "alle Seiten in eine Datei",
      "combine PDFs", "join PDFs", "zu einem Dokument zusammenfassen"

    Args:
        input_paths: List of paths to source PDFs (order is preserved).
        output_path: Where to write the merged PDF.

    Returns:
        Path to the output file.
    """
    writer = pypdf.PdfWriter()
    for p in input_paths:
        reader = pypdf.PdfReader(str(p))
        for page in reader.pages:
            writer.add_page(page)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        writer.write(f)
    return out


# ---------------------------------------------------------------------------
# Split
# ---------------------------------------------------------------------------

def split_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    pages_per_file: int = 1,
) -> list[Path]:
    """
    Split a PDF into chunks of N pages each.

    Natural language triggers:
      "PDF aufteilen", "jede Seite einzeln speichern", "in Abschnitte aufteilen",
      "split PDF", "separate pages", "Seiten einzeln exportieren"

    Args:
        input_path:     Source PDF.
        output_dir:     Directory where split files are written.
        pages_per_file: How many pages per output file (default: 1).

    Returns:
        List of paths to the created files.
    """
    reader = pypdf.PdfReader(str(input_path))
    total = len(reader.pages)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(input_path).stem
    outputs: list[Path] = []

    for start in range(0, total, pages_per_file):
        writer = pypdf.PdfWriter()
        chunk = reader.pages[start : start + pages_per_file]
        for page in chunk:
            writer.add_page(page)
        end = min(start + pages_per_file - 1, total - 1)
        out_file = out_dir / f"{stem}_{start + 1}-{end + 1}.pdf"
        with open(out_file, "wb") as f:
            writer.write(f)
        outputs.append(out_file)

    return outputs


# ---------------------------------------------------------------------------
# Rotate
# ---------------------------------------------------------------------------

def rotate_pages(
    input_path: str | Path,
    output_path: str | Path,
    degrees: int,
    page_numbers: Sequence[int] | None = None,
) -> Path:
    """
    Rotate pages in a PDF by a given number of degrees (90, 180, 270).

    Natural language triggers:
      "Seite drehen", "um 90 Grad drehen", "Seiten rotieren", "rotate pages",
      "falsch herum", "Querformat erzwingen", "Hochformat erzwingen"

    Args:
        input_path:   Source PDF.
        output_path:  Where to write the result.
        degrees:      Rotation in degrees clockwise (90, 180, 270).
        page_numbers: 1-based list of pages to rotate. None = rotate all.

    Returns:
        Path to the output file.
    """
    if degrees not in (90, 180, 270):
        raise ValueError("Rotation muss 90, 180 oder 270 Grad sein.")

    reader = pypdf.PdfReader(str(input_path))
    writer = pypdf.PdfWriter()
    total = len(reader.pages)
    targets = set(page_numbers) if page_numbers else set(range(1, total + 1))

    for i, page in enumerate(reader.pages, start=1):
        if i in targets:
            page.rotate(degrees)
        writer.add_page(page)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        writer.write(f)
    return out


# ---------------------------------------------------------------------------
# Watermark
# ---------------------------------------------------------------------------

def add_watermark(
    input_path: str | Path,
    watermark_path: str | Path,
    output_path: str | Path,
    page_numbers: Sequence[int] | None = None,
) -> Path:
    """
    Overlay a watermark PDF onto pages of another PDF.

    Natural language triggers:
      "Wasserzeichen hinzufügen", "Stempel draufsetzen", "watermark",
      "add stamp", "überlagern mit Logo", "ENTWURF-Stempel"

    Args:
        input_path:     Source PDF.
        watermark_path: Single-page PDF used as the watermark.
        output_path:    Where to write the result.
        page_numbers:   1-based pages to watermark. None = all pages.

    Returns:
        Path to the output file.
    """
    reader = pypdf.PdfReader(str(input_path))
    wm_reader = pypdf.PdfReader(str(watermark_path))
    wm_page = wm_reader.pages[0]

    writer = pypdf.PdfWriter()
    total = len(reader.pages)
    targets = set(page_numbers) if page_numbers else set(range(1, total + 1))

    for i, page in enumerate(reader.pages, start=1):
        if i in targets:
            page.merge_page(wm_page)
        writer.add_page(page)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        writer.write(f)
    return out


# ---------------------------------------------------------------------------
# Encrypt
# ---------------------------------------------------------------------------

def encrypt_pdf(
    input_path: str | Path,
    output_path: str | Path,
    user_password: str,
    owner_password: str | None = None,
) -> Path:
    """
    Encrypt a PDF with a user password (and optional owner password).

    Natural language triggers:
      "PDF verschlüsseln", "Passwort setzen", "mit Passwort schützen",
      "encrypt PDF", "password protect", "PDF sperren"

    Args:
        input_path:     Source PDF.
        output_path:    Where to write the encrypted file.
        user_password:  Password required to open the PDF.
        owner_password: Password for full control (defaults to user_password).

    Returns:
        Path to the encrypted output file.
    """
    reader = pypdf.PdfReader(str(input_path))
    writer = pypdf.PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    writer.encrypt(
        user_password=user_password,
        owner_password=owner_password or user_password,
    )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        writer.write(f)
    return out


# ---------------------------------------------------------------------------
# Decrypt
# ---------------------------------------------------------------------------

def decrypt_pdf(
    input_path: str | Path,
    output_path: str | Path,
    password: str,
) -> Path:
    """
    Remove password protection from a PDF (requires the correct password).

    Natural language triggers:
      "PDF entschlüsseln", "Passwort entfernen", "decrypt PDF",
      "unlock PDF", "Schutz aufheben", "entsperren"

    Args:
        input_path:  Encrypted source PDF.
        output_path: Where to write the unencrypted file.
        password:    Password to unlock the PDF.

    Returns:
        Path to the decrypted output file.
    """
    # pikepdf handles more encryption schemes than pypdf
    with pikepdf.open(str(input_path), password=password) as pdf:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        pdf.save(str(out))
    return out


# ---------------------------------------------------------------------------
# Extract pages
# ---------------------------------------------------------------------------

def extract_pages(
    input_path: str | Path,
    output_path: str | Path,
    page_numbers: Sequence[int],
) -> Path:
    """
    Extract specific pages from a PDF into a new file.

    Natural language triggers:
      "Seiten extrahieren", "nur Seite X", "bestimmte Seiten rausnehmen",
      "extract pages", "save pages X to Y", "Seiten 3 bis 7 exportieren"

    Args:
        input_path:   Source PDF.
        output_path:  Where to write the extracted pages.
        page_numbers: 1-based list of page numbers to keep.

    Returns:
        Path to the output file.
    """
    reader = pypdf.PdfReader(str(input_path))
    writer = pypdf.PdfWriter()
    total = len(reader.pages)

    for n in page_numbers:
        if not (1 <= n <= total):
            raise ValueError(f"Seite {n} existiert nicht (Dokument hat {total} Seiten).")
        writer.add_page(reader.pages[n - 1])

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        writer.write(f)
    return out


# ---------------------------------------------------------------------------
# Compress (pikepdf)
# ---------------------------------------------------------------------------

def compress_pdf(
    input_path: str | Path,
    output_path: str | Path,
) -> Path:
    """
    Losslessly compress a PDF by removing redundant objects.

    Natural language triggers:
      "PDF verkleinern", "Dateigröße reduzieren", "compress PDF",
      "kleiner machen", "optimize PDF", "PDF optimieren"

    Args:
        input_path:  Source PDF.
        output_path: Where to write the compressed file.

    Returns:
        Path to the output file.
    """
    with pikepdf.open(str(input_path)) as pdf:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        pdf.save(str(out), compress_streams=True, recompress_flate=True)
    return out
