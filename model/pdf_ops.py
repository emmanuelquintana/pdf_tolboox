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
def merge_pdfs(inputs: List[str], output: str) -> None:
    _require(PdfWriter is not None, "pypdf no instalado")
    _require(len(inputs) >= 2, "Se requieren al menos 2 PDFs")
    writer = PdfWriter()
    for f in inputs:
        reader = PdfReader(f)
        for page in reader.pages:
            writer.add_page(page)
    with open(output, "wb") as fp:
        writer.write(fp)

def split_pdf(input_pdf: str, ranges: str, out_dir: str) -> List[str]:
    _require(PdfReader is not None and PdfWriter is not None, "pypdf no instalado")
    os.makedirs(out_dir, exist_ok=True)
    reader = PdfReader(input_pdf)
    pages = split_ranges(ranges, len(reader.pages))
    _require(bool(pages), "Los rangos no seleccionaron ninguna página")
    outputs = []
    for p in pages:
        writer = PdfWriter()
        writer.add_page(reader.pages[p])
        out = os.path.join(out_dir, f"page_{p+1:04d}.pdf")
        with open(out, "wb") as fp:
            writer.write(fp)
        outputs.append(out)
    return outputs

def compress_pdf_lossless(input_pdf: str, output_pdf: str):
    _require(fitz is not None, "PyMuPDF no instalado")
    doc = fitz.open(input_pdf)
    doc.save(output_pdf, deflate=True, clean=True, garbage=4, use_objstm=True, linear=True)
    doc.close()

def compress_pdf_rasterize(input_pdf: str, output_pdf: str, dpi: int = 150):
    _require(fitz is not None, "PyMuPDF no instalado")
    src = fitz.open(input_pdf)
    dst = fitz.open()
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    for page in src:
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_pdf = fitz.open("pdf", fitz.Image(pix.samples, pix.width, pix.height, pix.stride, pix.n).pdf_bytes())
        dst.insert_pdf(img_pdf)
    dst.save(output_pdf, deflate=True, clean=True, garbage=4, linear=True)
    src.close(); dst.close()

def pdf_to_images(input_pdf: str, out_dir: str, dpi: int = 150, fmt: str = "png") -> List[str]:
    _require(fitz is not None, "PyMuPDF no instalado")
    os.makedirs(out_dir, exist_ok=True)
    doc = fitz.open(input_pdf)
    paths = []
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=mat, alpha=False)
        out = os.path.join(out_dir, f"page_{i:04d}.{fmt}")
        pix.save(out); paths.append(out)
    doc.close()
    return paths

def images_to_pdf(images: List[str], output_pdf: str):
    _require(Image is not None, "Pillow no instalado")
    imgs = [Image.open(p).convert("RGB") for p in images]
    _require(len(imgs) > 0, "No hay imágenes")
    first, rest = imgs[0], imgs[1:]
    first.save(output_pdf, save_all=True, append_images=rest)
