# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk

# Drag & Drop root
SUPPORTS_DND = False
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # pip install tkinterdnd2
    DND_ROOT = TkinterDnD.Tk
    SUPPORTS_DND = True
except Exception:
    DND_FILES = None
    DND_ROOT = tk.Tk  # fallback

def _rounded_rect(canvas, x1, y1, x2, y2, r=16, **kwargs):
    pts = [
        x1+r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y2-r, x2, y2,
        x2-r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y1+r, x1, y1,
    ]
    return canvas.create_polygon(pts, smooth=True, **kwargs)

class GlassCard(ttk.Frame):
    """Panel con fondo 'glass' redondeado."""
    def __init__(self, master, title: str = ""):
        
        super().__init__(master)
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=self._bg(master))
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.inner = ttk.Frame(self, padding=16)
        self.inner.pack(fill=tk.BOTH, expand=True)
        self.title = title
        self.bind("<Configure>", self._redraw)
        self.canvas.bind("<Configure>", self._redraw)

    def _bg(self, w):
        try:
            return w.winfo_toplevel().cget("bg")
        except Exception:
            return "#0b1220"

    def _redraw(self, _evt=None):
        self.after(5, self._draw)

    def _draw(self):
        self.canvas.delete("all")
        w = max(100, self.winfo_width()); h = max(60, self.winfo_height())
        pad = 6
        # Sombra
        _rounded_rect(self.canvas, pad, pad+2, w-pad, h-pad+2, r=22, fill="#000000", stipple="gray25", outline="")
        # Capa
        _rounded_rect(self.canvas, pad, pad, w-pad, h-pad, r=22, fill="#101827", outline="#334155")
        # Contenido
        self.canvas.create_window(0, 0, anchor="nw", window=self.inner, width=w, height=h)
        if self.title:
            self.canvas.create_text(22, 18, anchor="w", text=self.title, fill="#e5e7eb", font=("Segoe UI", 12, "bold"))

class DropArea(ttk.Frame):
    """Área de arrastrar y soltar con borde marcado."""
    def __init__(self, master, title: str, on_files, multiple=True):
        super().__init__(master, padding=6)
        self.on_files = on_files
        self.multiple = multiple

        # Lienzo con borde discontinuo
        self.canvas = tk.Canvas(self, height=120, highlightthickness=0, bd=0)
        self.canvas.pack(fill=tk.X, expand=True)
        self._draw(normal=True)

        # Texto y botón
        self.label = ttk.Label(self, text=title, style="Caption.TLabel")
        self.label.pack(anchor="w", pady=(8, 4))
        self.btn = ttk.Button(self, text="Elegir archivos", style="Accent.TButton", command=self._open_dialog)
        self.btn.pack(anchor="w")

        # Efecto hover
        self.canvas.bind("<Enter>", lambda e: self._draw(normal=False))
        self.canvas.bind("<Leave>", lambda e: self._draw(normal=True))

        # DnD
        top = master.winfo_toplevel()
        if SUPPORTS_DND and hasattr(top, "drop_target_register") and DND_FILES is not None:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._on_drop)
            ttk.Label(self, text="Drag & Drop activo", style="Hint.TLabel").pack(anchor="w", pady=(6,0))
        else:
            ttk.Label(self, text="Drag & Drop no disponible (instala tkinterdnd2)", style="Hint.TLabel").pack(anchor="w", pady=(6,0))

    def _fg(self):
        return "#3b82f6"

    def _draw(self, normal=True):
        self.canvas.delete("all")
        w = max(200, self.canvas.winfo_width() or 600)
        h = max(100, self.canvas.winfo_height() or 120)
        pad = 4
        fill = "#0f172a" if normal else "#111b2e"
        outline = self._fg()
        # Tarjeta
        _rounded_rect(self.canvas, pad, pad, w-pad, h-pad, r=18, fill=fill, outline=outline)
        # Borde discontínuo interior
        dash = (8, 6)
        self.canvas.create_rectangle(
            pad+6, pad+6, w-pad-6, h-pad-6,
            outline=outline, width=2, dash=dash
        )
        self.canvas.create_text(w/2, h/2, text="Suelta aquí los archivos", fill="#e5e7eb")

    def _open_dialog(self):
        if self.multiple:
            files = tk.filedialog.askopenfilenames(title="Selecciona archivo(s)")
            if files: self.on_files(list(files))
        else:
            f = tk.filedialog.askopenfilename(title="Selecciona archivo")
            if f: self.on_files([f])

    def _on_drop(self, event):
        data = event.data
        paths, curr, in_brace = [], "", False
        for ch in data:
            if ch == "{":
                in_brace, curr = True, ""
            elif ch == "}":
                in_brace = False
                if curr: paths.append(curr); curr = ""
            elif ch == " " and not in_brace:
                if curr: paths.append(curr); curr = ""
            else:
                curr += ch
        if curr: paths.append(curr)
        if not self.multiple and paths:
            paths = [paths[0]]
        self.on_files(paths)
