# -*- coding: utf-8 -*-
import os, shutil, difflib, subprocess
from typing import List

# Core libs
try:
    from pypdf import PdfReader, PdfWriter
except Exception:
    PdfReader = None
    PdfWriter = None
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None
try:
    from PIL import Image, ImageOps
except Exception:
    Image = None
    ImageOps = None

PAGE_SIZES_MM = {
    "A4": (210, 297),
    "Carta": (216, 279),
    "Letter": (216, 279),
    "Legal": (216, 356),
    "A3": (297, 420),
    "A5": (148, 210),
}

MARGINS_MM = {
    "none": 0,
    "small": 10,
    "large": 20,
}

# ---------- Utils ----------
def _require(cond, msg):
    if not cond:
        raise RuntimeError(msg)

def ensure_ext(path: str, ext: str) -> str:
    return path if path.lower().endswith(ext) else path + ext

def split_ranges(ranges_str: str, max_pages: int) -> List[int]:
    result = set()
    for part in ranges_str.replace(" ", "").split(","):
        if not part: continue
        if "-" in part:
            a, b = part.split("-", 1)
            start = int(a) if a else 1
            end = int(b) if b else max_pages
            for p in range(start, end + 1):
                if 1 <= p <= max_pages: result.add(p - 1)
        else:
            p = int(part)
            if 1 <= p <= max_pages: result.add(p - 1)
    return sorted(result)

# ---------- Ops principales ----------
def merge_pdfs(inputs: List[str], output: str, progress_callback=None) -> None:
    _require(PdfWriter is not None, "pypdf no instalado")
    _require(len(inputs) >= 2, "Se requieren al menos 2 PDFs")
    writer = PdfWriter()
    total = len(inputs)
    for i, f in enumerate(inputs):
        if progress_callback:
            progress_callback(i / total, f"Fusionando {os.path.basename(f)}...")
        reader = PdfReader(f)
        for page in reader.pages:
            writer.add_page(page)
    with open(output, "wb") as fp:
        writer.write(fp)

def split_pdf(input_pdf: str, ranges: str, out_dir: str, merge_output: bool = False, output_filename: str = "split_merged.pdf") -> List[str]:
    _require(PdfReader is not None and PdfWriter is not None, "pypdf no instalado")
    os.makedirs(out_dir, exist_ok=True)
    reader = PdfReader(input_pdf)
    pages = split_ranges(ranges, len(reader.pages))
    _require(bool(pages), "Los rangos no seleccionaron ninguna página")
    outputs = []
    
    if merge_output:
        writer = PdfWriter()
        for p in pages:
            writer.add_page(reader.pages[p])
        out = os.path.join(out_dir, output_filename)
        with open(out, "wb") as fp:
            writer.write(fp)
        outputs.append(out)
    else:
        for p in pages:
            writer = PdfWriter()
            writer.add_page(reader.pages[p])
            out = os.path.join(out_dir, f"page_{p+1:04d}.pdf")
            with open(out, "wb") as fp:
                writer.write(fp)
            outputs.append(out)
    return outputs

def rotate_pdf(input_pdf: str, output_pdf: str, angle: int) -> None:
    _require(PdfReader is not None and PdfWriter is not None, "pypdf no instalado")
    reader = PdfReader(input_pdf)
    writer = PdfWriter()
    for page in reader.pages:
        page.rotate(angle)
        writer.add_page(page)
    with open(output_pdf, "wb") as fp:
        writer.write(fp)

def encrypt_pdf(input_pdf: str, output_pdf: str, password: str) -> None:
    _require(PdfReader is not None and PdfWriter is not None, "pypdf no instalado")
    reader = PdfReader(input_pdf)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(password)
    with open(output_pdf, "wb") as fp:
        writer.write(fp)

def remove_password(input_pdf: str, output_pdf: str, password: str) -> bool:
    _require(PdfReader is not None and PdfWriter is not None, "pypdf no instalado")
    reader = PdfReader(input_pdf)
    if reader.is_encrypted:
        success = reader.decrypt(password)
        if not success:
            return False
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    with open(output_pdf, "wb") as fp:
        writer.write(fp)
    return True

def compress_pdf_lossless(input_pdf: str, output_pdf: str):
    _require(fitz is not None, "PyMuPDF no instalado")
    doc = fitz.open(input_pdf)
    doc.save(output_pdf, deflate=True, clean=True, garbage=4, use_objstm=True, linear=True)
    doc.close()

def compress_pdf_rasterize(input_pdf: str, output_pdf: str, dpi: int = 150, progress_callback=None):
    _require(fitz is not None, "PyMuPDF no instalado")
    src = fitz.open(input_pdf)
    dst = fitz.open()
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    total = len(src)
    for i, page in enumerate(src):
        if progress_callback:
            progress_callback(i / total, f"Rasterizando página {i+1}/{total}")
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_pdf = fitz.open("pdf", fitz.Image(pix.samples, pix.width, pix.height, pix.stride, pix.n).pdf_bytes())
        dst.insert_pdf(img_pdf)
    dst.save(output_pdf, deflate=True, clean=True, garbage=4, linear=True)
    src.close(); dst.close()

def pdf_to_images(input_pdf: str, out_dir: str, dpi: int = 150, fmt: str = "png", progress_callback=None) -> List[str]:
    _require(fitz is not None, "PyMuPDF no instalado")
    os.makedirs(out_dir, exist_ok=True)
    doc = fitz.open(input_pdf)
    paths = []
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    total = len(doc)
    for i, page in enumerate(doc, start=1):
        if progress_callback:
            progress_callback(i / total, f"Exportando página {i}/{total}")
        pix = page.get_pixmap(matrix=mat, alpha=False)
        out = os.path.join(out_dir, f"page_{i:04d}.{fmt}")
        pix.save(out); paths.append(out)
    doc.close()
    return paths

def get_pdf_metadata(input_pdf: str) -> dict:
    _require(PdfReader is not None, "pypdf no instalado")
    reader = PdfReader(input_pdf)
    meta = reader.metadata
    return {
        "title": meta.get("/Title", ""),
        "author": meta.get("/Author", ""),
        "subject": meta.get("/Subject", ""),
        "keywords": meta.get("/Keywords", ""),
        "creator": meta.get("/Creator", ""),
        "producer": meta.get("/Producer", "")
    }

def set_pdf_metadata(input_pdf: str, output_pdf: str, metadata: dict) -> None:
    _require(PdfReader is not None and PdfWriter is not None, "pypdf no instalado")
    reader = PdfReader(input_pdf)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    
    # Mapping to PDF standard keys
    pdf_meta = {
        "/Title": metadata.get("title", ""),
        "/Author": metadata.get("author", ""),
        "/Subject": metadata.get("subject", ""),
        "/Keywords": metadata.get("keywords", ""),
        "/Creator": metadata.get("creator", ""),
    }
    writer.add_metadata(pdf_meta)
    
    with open(output_pdf, "wb") as fp:
        writer.write(fp)

def get_pdf_page_count(input_pdf: str) -> int:
    _require(PdfReader is not None, "pypdf no instalado")
    reader = PdfReader(input_pdf)
    if reader.is_encrypted:
        raise RuntimeError("El PDF está protegido. Desbloquéalo antes de organizar sus páginas.")
    return len(reader.pages)

def render_pdf_page_thumbnail(input_pdf: str, page_index: int, max_width: int = 128, max_height: int = 166):
    _require(fitz is not None, "PyMuPDF no instalado")
    _require(Image is not None, "Pillow no instalado")

    doc = fitz.open(input_pdf)
    try:
        _require(0 <= page_index < len(doc), "Página fuera de rango")
        page = doc.load_page(page_index)
        rect = page.rect
        zoom = min(max_width / rect.width, max_height / rect.height)
        zoom = max(0.25, min(zoom, 2.0))
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False, annots=True)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    finally:
        doc.close()

def _safe_metadata(metadata) -> dict:
    if not metadata:
        return {}

    clean = {}
    for key, value in metadata.items():
        if value is not None:
            clean[str(key)] = str(value)
    return clean

def organize_pdf_pages(page_refs: List[dict], output_pdf: str, progress_callback=None) -> str:
    _require(PdfReader is not None and PdfWriter is not None, "pypdf no instalado")
    _require(bool(page_refs), "No hay páginas para guardar")

    output_abs = os.path.abspath(output_pdf).lower()
    input_paths = {os.path.abspath(ref.get("path", "")).lower() for ref in page_refs}
    _require(output_abs not in input_paths, "Guarda el resultado con otro nombre para no sobrescribir el PDF original.")

    readers = {}
    first_metadata = None
    writer = PdfWriter()
    total = len(page_refs)

    def get_reader(path):
        if path not in readers:
            reader = PdfReader(path)
            if reader.is_encrypted:
                raise RuntimeError(f"El PDF está protegido: {os.path.basename(path)}")
            readers[path] = reader
        return readers[path]

    for index, ref in enumerate(page_refs, start=1):
        path = ref.get("path")
        page_index = int(ref.get("page_index", -1))
        _require(path and os.path.isfile(path), "Una página apunta a un PDF que ya no existe")

        reader = get_reader(path)
        _require(0 <= page_index < len(reader.pages), "Una página está fuera de rango")

        if first_metadata is None:
            first_metadata = _safe_metadata(reader.metadata)

        writer.add_page(reader.pages[page_index])
        if progress_callback:
            progress_callback(index / total, f"Copiando página {index}/{total}")

    if first_metadata:
        writer.add_metadata(first_metadata)

    with open(output_pdf, "wb") as fp:
        writer.write(fp)

    return output_pdf

def _safe_output_name(path: str, index: int, out_dir: str) -> str:
    base = os.path.splitext(os.path.basename(path))[0].strip() or f"imagen_{index:03d}"
    candidate = os.path.join(out_dir, f"{base}.pdf")
    if not os.path.exists(candidate):
        return candidate

    return os.path.join(out_dir, f"{base}_{index:03d}.pdf")

def _prepare_image_pdf_page(image_path: str, page_size: str, orientation: str, margin: str, dpi: int = 150):
    _require(Image is not None and ImageOps is not None, "Pillow no instalado")

    with Image.open(image_path) as src:
        img = ImageOps.exif_transpose(src)
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            bg = Image.new("RGB", img.size, "white")
            bg.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[-1])
            img = bg
        else:
            img = img.convert("RGB")

        if page_size == "original":
            return img.copy()

        page_w_mm, page_h_mm = PAGE_SIZES_MM.get(page_size, PAGE_SIZES_MM["A4"])
        if orientation == "landscape":
            page_w_mm, page_h_mm = page_h_mm, page_w_mm

        page_w = max(1, int(round(page_w_mm / 25.4 * dpi)))
        page_h = max(1, int(round(page_h_mm / 25.4 * dpi)))
        margin_px = int(round(MARGINS_MM.get(margin, 0) / 25.4 * dpi))
        max_w = max(1, page_w - (margin_px * 2))
        max_h = max(1, page_h - (margin_px * 2))
        scale = min(max_w / img.width, max_h / img.height)
        target_w = max(1, int(round(img.width * scale)))
        target_h = max(1, int(round(img.height * scale)))
        resized = img.resize((target_w, target_h), Image.Resampling.LANCZOS)

        page = Image.new("RGB", (page_w, page_h), "white")
        page.paste(resized, ((page_w - target_w) // 2, (page_h - target_h) // 2))
        return page

def images_to_pdf(
    images: List[str],
    output_path: str,
    page_size: str = "A4",
    orientation: str = "portrait",
    margin: str = "none",
    merge_output: bool = True,
    progress_callback=None,
):
    _require(Image is not None, "Pillow no instalado")
    _require(len(images) > 0, "No hay imágenes")

    dpi = 72 if page_size == "original" else 150
    total = len(images)

    if merge_output:
        pages = []
        try:
            for i, path in enumerate(images, start=1):
                if progress_callback:
                    progress_callback((i - 1) / total, f"Procesando imagen {i}/{total}")
                pages.append(_prepare_image_pdf_page(path, page_size, orientation, margin, dpi))

            first, rest = pages[0], pages[1:]
            first.save(output_path, "PDF", save_all=True, append_images=rest, resolution=dpi)
            if progress_callback:
                progress_callback(1.0, "PDF creado")
            return output_path
        finally:
            for page in pages:
                page.close()

    os.makedirs(output_path, exist_ok=True)
    outputs = []
    for i, path in enumerate(images, start=1):
        if progress_callback:
            progress_callback((i - 1) / total, f"Creando PDF {i}/{total}")
        page = _prepare_image_pdf_page(path, page_size, orientation, margin, dpi)
        out = _safe_output_name(path, i, output_path)
        try:
            page.save(out, "PDF", resolution=dpi)
            outputs.append(out)
        finally:
            page.close()

    if progress_callback:
        progress_callback(1.0, "PDFs creados")
    return outputs
