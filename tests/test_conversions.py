import os
from pathlib import Path

import pytest
from PIL import Image

import conversions
from conversions import (
    _get_output_extension,
    _libreoffice_convert_to_pdf,
    _wrap_text,
    convert_jpg_to_png,
    convert_png_to_jpg,
    normalize_format_name,
    perform_conversion,
)


def test_normalize_format_name_variants():
    """Teste la normalisation des formats d'extension."""
    assert normalize_format_name(None) == ""
    assert normalize_format_name(" jpg ") == "JPG"
    assert normalize_format_name("jpeg") == "JPEG"
    assert normalize_format_name("Pdf") == "PDF"


def test_get_output_extension():
    """Teste l'extension de sortie normalisée pour différents formats."""
    assert _get_output_extension("JPG") == "jpg"
    assert _get_output_extension("PNG") == "png"
    assert _get_output_extension("PDF") == "pdf"


def test_wrap_text_short_and_long():
    """Teste le retour de texte enveloppé pour de courtes et de longues chaînes."""
    assert _wrap_text("Hello", 10) == ["Hello"]

    long_text = "This is a very long line that should be wrapped."
    lines = _wrap_text(long_text, 15)
    assert len(lines) > 1
    assert all(len(line) <= 15 for line in lines)


def test_libreoffice_convert_to_pdf_no_soffice(monkeypatch):
    """Teste le comportement lorsque LibreOffice n'est pas installé."""
    monkeypatch.setattr(conversions, "_libreoffice_available", lambda: None)

    with pytest.raises(EnvironmentError, match="LibreOffice/soffice introuvable"):
        _libreoffice_convert_to_pdf("/tmp/source.docx", "/tmp/dest.pdf")


def test_libreoffice_convert_to_pdf_success(tmp_path, monkeypatch):
    """Teste la conversion LibreOffice vers PDF lorsque la commande fonctionne."""
    src_path = tmp_path / "source.docx"
    dest_path = tmp_path / "sortie.pdf"
    generated_pdf = tmp_path / "source.pdf"

    src_path.write_text("dummy")
    generated_pdf.write_text("pdf content")

    monkeypatch.setattr(conversions, "_libreoffice_available", lambda: "/usr/bin/soffice")

    class DummyCompleted:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(
        conversions.subprocess,
        "run",
        lambda *args, **kwargs: DummyCompleted(),
    )

    result = _libreoffice_convert_to_pdf(str(src_path), str(dest_path))

    assert result == str(dest_path)
    assert os.path.exists(dest_path)


def test_convert_jpg_to_png_and_png_to_jpg(tmp_path):
    """Teste les conversions image JPEG->PNG et PNG->JPG."""
    src_jpg = tmp_path / "source.jpg"
    png_dest = tmp_path / "output.png"
    jpg_dest = tmp_path / "output.jpg"

    image = Image.new("RGB", (10, 10), color="red")
    image.save(src_jpg, format="JPEG")

    result_png = convert_jpg_to_png(str(src_jpg), str(png_dest))
    assert result_png == str(png_dest)
    assert png_dest.exists()
    with Image.open(png_dest) as img:
        assert img.format == "PNG"

    result_jpg = convert_png_to_jpg(str(png_dest), str(jpg_dest))
    assert result_jpg == str(jpg_dest)
    assert jpg_dest.exists()
    with Image.open(jpg_dest) as img:
        assert img.format == "JPEG"


def test_convert_pdf_to_docx_import_error(monkeypatch):
    """Teste l'erreur levée si pdf2docx n'est pas installé."""
    monkeypatch.setattr(conversions, "Converter", None)

    with pytest.raises(ImportError, match="pdf2docx"):
        conversions.convert_pdf_to_docx("source.pdf", "dest.docx")


def test_convert_pdf_to_docx_success(monkeypatch, tmp_path):
    """Teste la conversion PDF->DOCX en simulant le comportement du convertisseur."""
    src_path = str(tmp_path / "source.pdf")
    dest_path = str(tmp_path / "sortie.docx")
    Path(src_path).write_text("pdf data")

    class FakeConverter:
        def __init__(self, path):
            assert path == src_path

        def convert(self, dest, start, end):
            Path(dest).write_text("docx data")

        def close(self):
            pass

    monkeypatch.setattr(conversions, "Converter", FakeConverter)

    result = conversions.convert_pdf_to_docx(src_path, dest_path)

    assert result == dest_path
    assert os.path.exists(dest_path)


def test_convert_txt_to_pdf_with_reportlab(monkeypatch, tmp_path):
    """Teste la conversion TXT->PDF via la fonction interne reportlab quand elle existe."""
    src_path = tmp_path / "texte.txt"
    dest_path = tmp_path / "sortie.pdf"
    src_path.write_text("ligne 1\nligne 2")

    monkeypatch.setattr(conversions, "canvas", object())
    monkeypatch.setattr(conversions, "A4", (100, 100))
    monkeypatch.setattr(conversions, "_convert_text_to_pdf_reportlab", lambda src, dest: Path(dest).write_text("pdf"))

    result = conversions.convert_txt_to_pdf(str(src_path), str(dest_path))

    assert result == str(dest_path)
    assert os.path.exists(dest_path)


def test_convert_txt_to_pdf_import_error_when_no_backend(monkeypatch):
    """Teste l'erreur si aucun backend TXT->PDF n'est disponible."""
    monkeypatch.setattr(conversions, "canvas", None)
    monkeypatch.setattr(conversions, "A4", None)
    monkeypatch.setattr(conversions, "pypandoc", None)

    with pytest.raises(ImportError, match="La conversion TXT->PDF nécessite"):
        conversions.convert_txt_to_pdf("input.txt", "output.pdf")


def test_perform_conversion_same_format_raises(tmp_path):
    """Teste la détection lorsqu'un utilisateur demande une conversion vers le même format."""
    src_path = tmp_path / "source.png"
    src_path.write_text("data")

    with pytest.raises(ValueError, match="identiques"):
        perform_conversion(str(src_path), "PNG", "PNG", str(tmp_path))


def test_perform_conversion_unsupported_conversion(tmp_path):
    """Teste le rejet d'une conversion qui n'est pas prise en charge."""
    src_path = tmp_path / "source.png"
    src_path.write_text("data")

    with pytest.raises(ValueError, match="Conversion non supportée"):
        perform_conversion(str(src_path), "PNG", "TIFF", str(tmp_path))


def test_perform_conversion_handles_existing_output(tmp_path, monkeypatch):
    """Teste la résolution de nom de fichier lorsqu'un fichier de sortie existe déjà."""
    src_path = tmp_path / "source.png"
    src_path.write_text("data")
    output_folder = tmp_path / "converted"
    output_folder.mkdir()

    (output_folder / "source.jpg").write_text("exists")
    (output_folder / "source_1.jpg").write_text("exists")

    def fake_convert(src, dest):
        Path(dest).write_text("ok")
        return dest

    monkeypatch.setitem(conversions.CONVERSION_FUNCTIONS, ("PNG", "JPG"), fake_convert)

    result = perform_conversion(str(src_path), "PNG", "JPG", str(output_folder))

    assert result.endswith("source_2.jpg")
    assert os.path.exists(result)
