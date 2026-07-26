import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image

try:
    from pdf2docx import Converter
except ImportError:  # pragma: no cover
    Converter = None

try:
    import pypandoc
except ImportError:  # pragma: no cover
    pypandoc = None

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
except ImportError:  # pragma: no cover
    A4 = None
    canvas = None


def normalize_format_name(format_name: str) -> str:
    """Normalise le nom de format pour la recherche et le routage."""
    if not format_name:
        return ""

    name = format_name.strip().replace(".", "").upper()
    if name == "JPEG":
        return "JPEG"
    if name == "JPG":
        return "JPG"
    return name


def _ensure_directory(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _get_output_extension(dest_format: str) -> str:
    if dest_format in {"JPG", "JPEG"}:
        return "jpg"
    return dest_format.lower()


def _libreoffice_available() -> str | None:
    return shutil.which("soffice") or shutil.which("libreoffice")


def _libreoffice_convert_to_pdf(src_path: str, dest_path: str) -> str:
    soffice = _libreoffice_available()
    if not soffice:
        raise EnvironmentError(
            "LibreOffice/soffice introuvable. Installez LibreOffice pour convertir les documents Office en PDF."
        )

    dest_dir = os.path.dirname(dest_path)
    _ensure_directory(dest_dir)

    command = [
        soffice,
        "--headless",
        "--convert-to",
        "pdf",
        src_path,
        "--outdir",
        dest_dir,
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if completed.returncode != 0:
        raise RuntimeError(
            f"LibreOffice conversion échouée : {completed.stderr or completed.stdout}"
        )

    generated_pdf = os.path.join(dest_dir, Path(src_path).with_suffix(".pdf").name)
    if not os.path.exists(generated_pdf):
        raise RuntimeError("La conversion LibreOffice n'a pas généré de fichier PDF attendu.")

    if os.path.abspath(generated_pdf) != os.path.abspath(dest_path):
        os.replace(generated_pdf, dest_path)

    return dest_path


def convert_jpg_to_png(src_path: str, dest_path: str) -> str:
    with Image.open(src_path) as image:
        image = image.convert("RGBA")
        image.save(dest_path, format="PNG")
    return dest_path


def convert_jpeg_to_png(src_path: str, dest_path: str) -> str:
    return convert_jpg_to_png(src_path, dest_path)


def convert_png_to_jpg(src_path: str, dest_path: str) -> str:
    with Image.open(src_path) as image:
        rgb = image.convert("RGB")
        rgb.save(dest_path, format="JPEG", quality=95)
    return dest_path


def convert_png_to_jpeg(src_path: str, dest_path: str) -> str:
    return convert_png_to_jpg(src_path, dest_path)


def convert_pdf_to_docx(src_path: str, dest_path: str) -> str:
    if Converter is None:
        raise ImportError(
            "La bibliothèque pdf2docx est requise pour convertir PDF en DOCX. Installez-la avec 'pip install pdf2docx'."
        )

    converter = Converter(src_path)
    converter.convert(dest_path, start=0, end=None)
    converter.close()

    if not os.path.exists(dest_path):
        raise RuntimeError("La conversion PDF->DOCX a échoué sans générer de fichier de sortie.")

    return dest_path


def convert_docx_to_pdf(src_path: str, dest_path: str) -> str:
    return _libreoffice_convert_to_pdf(src_path, dest_path)


def convert_pptx_to_pdf(src_path: str, dest_path: str) -> str:
    return _libreoffice_convert_to_pdf(src_path, dest_path)


def convert_xlsx_to_pdf(src_path: str, dest_path: str) -> str:
    return _libreoffice_convert_to_pdf(src_path, dest_path)


def convert_txt_to_pdf(src_path: str, dest_path: str) -> str:
    if canvas is not None and A4 is not None:
        _convert_text_to_pdf_reportlab(src_path, dest_path)
        return dest_path

    if pypandoc is not None:
        pypandoc.convert_file(src_path, "pdf", outputfile=dest_path)
        if not os.path.exists(dest_path):
            raise RuntimeError("La conversion TXT->PDF a échoué avec pypandoc.")
        return dest_path

    raise ImportError(
        "La conversion TXT->PDF nécessite reportlab ou pypandoc. Installez 'reportlab' ou 'pypandoc'."
    )


def _convert_text_to_pdf_reportlab(src_path: str, dest_path: str) -> None:
    _ensure_directory(os.path.dirname(dest_path))
    c = canvas.Canvas(dest_path, pagesize=A4)
    width, height = A4
    margin = 40
    y = height - margin
    line_height = 14

    with open(src_path, "r", encoding="utf-8", errors="ignore") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            for chunk in _wrap_text(line, int((width - 2 * margin) / 7.2)):
                if y < margin + line_height:
                    c.showPage()
                    y = height - margin
                c.drawString(margin, y, chunk)
                y -= line_height

    c.save()


def _wrap_text(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    words = text.split(" ")
    lines = []
    current_line = []
    current_length = 0

    for word in words:
        if current_length + len(word) + len(current_line) > max_chars:
            lines.append(" ".join(current_line))
            current_line = [word]
            current_length = len(word)
        else:
            current_line.append(word)
            current_length += len(word)

    if current_line:
        lines.append(" ".join(current_line))

    return lines


CONVERSION_FUNCTIONS = {
    ("JPG", "PNG"): convert_jpg_to_png,
    ("JPEG", "PNG"): convert_jpeg_to_png,
    ("PNG", "JPG"): convert_png_to_jpg,
    ("PNG", "JPEG"): convert_png_to_jpeg,
    ("PDF", "DOCX"): convert_pdf_to_docx,
    ("DOCX", "PDF"): convert_docx_to_pdf,
    ("PPTX", "PDF"): convert_pptx_to_pdf,
    ("XLSX", "PDF"): convert_xlsx_to_pdf,
    ("TXT", "PDF"): convert_txt_to_pdf,
}


def perform_conversion(
    src_path: str,
    src_format: str,
    dest_format: str,
    output_folder: str,
) -> str:
    """Convertit un fichier et renvoie le chemin du fichier converti."""
    normalized_src = normalize_format_name(src_format)
    normalized_dest = normalize_format_name(dest_format)

    if normalized_src == normalized_dest:
        raise ValueError("Le format d'origine et le format de sortie sont identiques.")

    conversion = CONVERSION_FUNCTIONS.get((normalized_src, normalized_dest))
    if conversion is None:
        raise ValueError(
            f"Conversion non supportée : {normalized_src} → {normalized_dest}."
        )

    _ensure_directory(output_folder)
    output_extension = _get_output_extension(normalized_dest)
    output_filename = f"{Path(src_path).stem}.{output_extension}"
    output_path = os.path.join(output_folder, output_filename)

    if os.path.exists(output_path):
        base = Path(src_path).stem
        counter = 1
        while True:
            candidate = os.path.join(output_folder, f"{base}_{counter}.{output_extension}")
            if not os.path.exists(candidate):
                output_path = candidate
                break
            counter += 1

    return conversion(src_path, output_path)
