# -*- coding: utf-8 -*-
import os
from tkinter import filedialog, messagebox
from model import pdf_ops as ops

APP_NAME = "PDF Toolbox"

class PDFController:
    """Orquesta llamadas del UI hacia el modelo y maneja diálogos."""
    def __init__(self, logger=None):
        self.log = logger or (lambda msg: None)

    # ---------- Fusionar ----------
    def merge_pdfs(self, paths):
        if not paths or len(paths) < 2:
            messagebox.showerror(APP_NAME, "Agrega al menos dos PDFs")
            return
        out = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            title="Guardar PDF fusionado"
        )
        if not out:
            return
        try:
            ops.merge_pdfs(paths, out)
            self.log(f"Fusionado correctamente → {out}")
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Error al fusionar: {e}")

    # ---------- Dividir ----------
    def split_pdf(self, src_path, ranges):
        if not src_path or not os.path.isfile(src_path):
            messagebox.showerror(APP_NAME, "Selecciona un PDF válido")
            return
        out_dir = filedialog.askdirectory(title="Elige carpeta de salida")
        if not out_dir:
            return
        try:
            outs = ops.split_pdf(src_path, ranges, out_dir)
            self.log(f"Dividido en {len(outs)} archivo(s) → {out_dir}")
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Error al dividir: {e}")

    # ---------- Comprimir ----------
    def compress_pdf(self, src_path, method="lossless", dpi=150):
        if not src_path or not os.path.isfile(src_path):
            messagebox.showerror(APP_NAME, "Selecciona un PDF válido")
            return
        out = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            title="Guardar PDF comprimido"
        )
        if not out:
            return
        try:
            if method == "lossless":
                ops.compress_pdf_lossless(src_path, out)
            else:
                dpi = max(72, int(dpi))
                ops.compress_pdf_rasterize(src_path, out, dpi=dpi)
            self.log(f"Comprimido → {out}")
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Error al comprimir: {e}")

    # ---------- PDF → Imágenes ----------
    def pdf_to_images(self, src_path, dpi=150):
        if not src_path or not os.path.isfile(src_path):
            messagebox.showerror(APP_NAME, "Selecciona un PDF válido")
            return
        out_dir = filedialog.askdirectory(title="Elige carpeta de salida")
        if not out_dir:
            return
        try:
            dpi = max(72, int(dpi))
            outs = ops.pdf_to_images(src_path, out_dir, dpi=dpi, fmt="png")
            self.log(f"Exportadas {len(outs)} imagen(es) → {out_dir}")
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Error al exportar imágenes: {e}")

    # ---------- Imágenes → PDF ----------
    def images_to_pdf(self, paths):
        if not paths:
            messagebox.showerror(APP_NAME, "Agrega imágenes primero")
            return
        out = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            title="Guardar PDF"
        )
        if not out:
            return
        try:
            ops.images_to_pdf(paths, out)
            self.log(f"Creado PDF a partir de imágenes → {out}")
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Error imágenes→PDF: {e}")
