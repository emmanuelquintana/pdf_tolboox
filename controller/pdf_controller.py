# -*- coding: utf-8 -*-
import os
import threading
from tkinter import filedialog, messagebox
from model import pdf_ops as ops

APP_NAME = "PDF Toolbox"

class PDFController:
    """Orquesta llamadas del UI hacia el modelo y maneja diálogos."""
    def __init__(self, logger=None, error_handler=None, on_success_action=None):
        self.log = logger or (lambda msg: None)
        self.error_handler = error_handler or (lambda title, msg: print(f"{title}: {msg}"))
        self.on_success_action = on_success_action or (lambda path: None)

    def _run_async(self, target, *args, success_msg=None, callback=None):
        def wrapper():
            try:
                result = target(*args)
                if success_msg:
                    # Si el mensaje depende del resultado (ej. ruta de salida)
                    msg = success_msg
                    if "{}" in msg or "{out}" in msg:
                        msg = msg.format(out=result)
                    self.log(msg)
                
                if callback:
                    callback()
            except Exception as e:
                self.error_handler("Error", str(e))
        
        t = threading.Thread(target=wrapper, daemon=True)
        t.start()

    # ---------- Fusionar ----------
    def merge_pdfs(self, paths):
        if not paths or len(paths) < 2:
            self.error_handler(APP_NAME, "Agrega al menos dos PDFs")
            return
        out = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            title="Guardar PDF fusionado"
        )
        if not out:
            return
        
        self.log("Iniciando fusión...")
        self._run_async(
            ops.merge_pdfs, paths, out, 
            success_msg=f"Fusionado correctamente → {out}",
            callback=lambda: self.on_success_action(out)
        )

    # ---------- Dividir ----------
    def split_pdf(self, src_path, ranges, merge=False):
        if not src_path or not os.path.isfile(src_path):
            self.error_handler(APP_NAME, "Selecciona un PDF válido")
            return
        out_dir = filedialog.askdirectory(title="Elige carpeta de salida")
        if not out_dir:
            return
        
        self.log("Iniciando división...")
        self._run_async(
            ops.split_pdf, src_path, ranges, out_dir, merge, 
            success_msg=f"Dividido correctamente en {out_dir}",
            callback=lambda: self.on_success_action(out_dir)
        )
        

    # ---------- Comprimir ----------
    def compress_pdf(self, src_path, method="lossless", dpi=150):
        if not src_path or not os.path.isfile(src_path):
            self.error_handler(APP_NAME, "Selecciona un PDF válido")
            return
        out = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            title="Guardar PDF comprimido"
        )
        if not out:
            return
        
        self.log("Iniciando compresión (esto puede tardar)...")
        if method == "lossless":
            self._run_async(
                ops.compress_pdf_lossless, src_path, out, 
                success_msg=f"Comprimido → {out}",
                callback=lambda: self.on_success_action(out)
            )
        else:
            dpi = max(72, int(dpi))
            self._run_async(
                ops.compress_pdf_rasterize, src_path, out, dpi, 
                success_msg=f"Comprimido (Raster) → {out}",
                callback=lambda: self.on_success_action(out)
            )

    # ---------- PDF → Imágenes ----------
    def pdf_to_images(self, src_path, dpi=150):
        if not src_path or not os.path.isfile(src_path):
            self.error_handler(APP_NAME, "Selecciona un PDF válido")
            return
        out_dir = filedialog.askdirectory(title="Elige carpeta de salida")
        if not out_dir:
            return
        
        self.log("Exportando páginas a imágenes...")
        dpi = max(72, int(dpi))
        self._run_async(
            ops.pdf_to_images, src_path, out_dir, dpi, "png", 
            success_msg=f"Imágenes guardadas en {out_dir}",
            callback=lambda: self.on_success_action(out_dir)
        )

    # ---------- Imágenes → PDF ----------
    def images_to_pdf(self, paths):
        if not paths:
            self.error_handler(APP_NAME, "Agrega imágenes primero")
            return
        out = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            title="Guardar PDF"
        )
        if not out:
            return
        
        self.log("Creando PDF de imágenes...")
        self._run_async(
            ops.images_to_pdf, paths, out, 
            success_msg=f"PDF Creado → {out}",
            callback=lambda: self.on_success_action(out)
        )

    # ---------- Rotar ----------
    def rotate_pdf(self, src_path, angle):
        if not src_path or not os.path.isfile(src_path):
            self.error_handler(APP_NAME, "Selecciona un PDF válido")
            return
        out = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            title="Guardar PDF Rotado"
        )
        if not out:
            return

        self.log(f"Rotando {angle} grados...")
        self._run_async(
            ops.rotate_pdf, src_path, out, int(angle), 
            success_msg=f"Rotado correctamente → {out}",
            callback=lambda: self.on_success_action(out)
        )

    # ---------- Quitar Contraseña ----------
    def remove_password(self, src_path, password):
        if not src_path or not os.path.isfile(src_path):
            self.error_handler(APP_NAME, "Selecciona un PDF válido")
            return
        out = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            title="Guardar PDF Desbloqueado"
        )
        if not out:
            return

        def task():
            success = ops.remove_password(src_path, out, password)
            if success:
                self.log(f"Contraseña removida → {out}")
                self.on_success_action(out)
            else:
                self.error_handler(APP_NAME, "Contraseña incorrecta o error al desencriptar")

        threading.Thread(target=task, daemon=True).start()
