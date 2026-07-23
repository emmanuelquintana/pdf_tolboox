# -*- coding: utf-8 -*-
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog

# Drag & Drop support
SUPPORTS_DND = False
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    # Para usar DnD con CustomTkinter, se suele requerir una clase base mixta o inicialización específica.
    # Aquí asumimos que la raíz (main_view) manejará la inicialización de DnD.
    SUPPORTS_DND = True
except Exception:
    DND_FILES = None

def parse_dnd_files(data, multiple=True):
    if not data:
        return []

    paths, curr, in_brace = [], "", False
    for ch in data:
        if ch == "{":
            in_brace, curr = True, ""
        elif ch == "}":
            in_brace = False
            if curr:
                paths.append(curr)
                curr = ""
        elif ch == " " and not in_brace:
            if curr:
                paths.append(curr)
                curr = ""
        else:
            curr += ch
    if curr:
        paths.append(curr)

    if not multiple and paths:
        return [paths[0]]
    return paths

class GlassCard(ctk.CTkFrame):
    """Contenedor con estilo moderno y bordes redondeados."""
    def __init__(self, master, title: str = "", **kwargs):
        super().__init__(master, corner_radius=15, border_width=1, border_color=("gray80", "#334155"), **kwargs)
        
        if title:
            self.lbl_title = ctk.CTkLabel(
                self, 
                text=title, 
                font=("Segoe UI", 16, "bold"), 
                anchor="w"
            )
            self.lbl_title.pack(fill="x", padx=20, pady=(15, 5))
            
        self.inner = ctk.CTkFrame(self, fg_color="transparent")
        self.inner.pack(fill="both", expand=True, padx=15, pady=(5, 15))

class DropArea(ctk.CTkFrame):
    """Área de arrastrar y soltar moderna."""
    def __init__(self, master, title: str, on_files, multiple=True):
        super().__init__(
            master, 
            corner_radius=10, 
            border_width=2, 
            border_color=("gray70", "gray30"),
            fg_color=("gray95", "#1e293b") # Color sutilmente diferente al fondo
        )
        self.on_files = on_files
        self.multiple = multiple

        self.lbl = ctk.CTkLabel(self, text=title, text_color=("gray50", "gray70"))
        self.lbl.pack(pady=(15, 5))

        self.btn = ctk.CTkButton(
            self, 
            text="Elegir archivos", 
            command=self._open_dialog,
            height=32
        )
        self.btn.pack(pady=(0, 15))

        # Configurar Drag & Drop
        if SUPPORTS_DND:
            # Intentamos registrar el frame para DnD
            # Nota: Esto puede fallar si 'master' no es una ventana TkinterDnD válida,
            # pero lo intentamos de forma segura.
            try:
                self.drop_target_register(DND_FILES)
                self.dnd_bind("<<Drop>>", self._on_drop)
                self.lbl.configure(text=f"{title}\n(Drag & Drop disponible)")
            except Exception:
                pass

    def _open_dialog(self):
        if self.multiple:
            files = filedialog.askopenfilenames(title="Selecciona archivo(s)")
            if files: self.on_files(list(files))
        else:
            f = filedialog.askopenfilename(title="Selecciona archivo")
            if f: self.on_files([f])

    def _on_drop(self, event):
        paths = parse_dnd_files(event.data, self.multiple)
        if paths:
            self.on_files(paths)
