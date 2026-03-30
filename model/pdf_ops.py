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
    from PIL import Image
except Exception:
    Image = None

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

def images_to_pdf(images: List[str], output_pdf: str, progress_callback=None):
    _require(Image is not None, "Pillow no instalado")
    total = len(images)
    imgs = []
    for i, p in enumerate(images):
        if progress_callback:
            progress_callback(i / total, f"Procesando imagen {i+1}/{total}")
        imgs.append(Image.open(p).convert("RGB"))
    
    _require(len(imgs) > 0, "No hay imágenes")
    first, rest = imgs[0], imgs[1:]
    first.save(output_pdf, save_all=True, append_images=rest)
