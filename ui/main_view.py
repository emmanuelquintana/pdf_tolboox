# ui/main_view.py
# -*- coding: utf-8 -*-
import os
import tkinter as tk
from tkinter import ttk, messagebox
from ui.widgets import GlassCard, DropArea, DND_ROOT
from utils.theme import apply_theme

APP_NAME = "PDF Toolbox"
VERSION = "v1.4.2"

class PDFToolboxApp(DND_ROOT):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.title(f"{APP_NAME} {VERSION}")
        self.geometry("1240x980")
        self.minsize(980, 660)

        # Tema
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self.theme = "dark"
        self.palette = apply_theme(self, self.style, self.theme)

        # Estado por-vista (evita pisar widgets entre MERGE y ALL)
        self._view_state = {}

        # UI base
        self._build_shell()
        self._build_views()
        self._show_view("ALL")

        # Logger
        self.controller.log = self._log

    # ---------- Shell ----------
    def _build_shell(self):
        header = ttk.Frame(self, padding=(14, 10))
        header.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(header, text=APP_NAME, style="Header.TLabel").pack(side=tk.LEFT)
        self.theme_btn = ttk.Button(header, text="Modo: Oscuro ◑", command=self._toggle_theme)
        self.theme_btn.pack(side=tk.RIGHT)

        body = ttk.Frame(self)
        body.pack(expand=True, fill=tk.BOTH)

        # Sidebar
        side = ttk.Frame(body, style="Sidebar.TFrame", padding=10)
        side.pack(side=tk.LEFT, fill=tk.Y)

        def add_btn(text, key):
            ttk.Button(
                side,
                text=text,
                style="Sidebar.TButton",
                command=lambda: self._show_view(key),
            ).pack(fill=tk.X, pady=4)

        add_btn("Unir PDF", "MERGE")
        add_btn("Dividir PDF", "SPLIT")
        add_btn("Comprimir PDF", "COMPRESS")
        add_btn("Convertir PDF", "CONVERT")
        ttk.Separator(side, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        add_btn("Todas las herramientas PDF", "ALL")

        # Contenido
        self.content = ttk.Frame(body)
        self.content.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=10, pady=10)

        # Log
        self.log = tk.Text(
            self,
            height=7,
            relief="flat",
            bg=self.palette["card"],
            fg=self.palette["fg"],
            insertbackground=self.palette["fg"],
        )
        self.log.pack(fill=tk.BOTH, padx=10, pady=(0, 10))
        self._log("Listo. Drag & Drop disponible si instalas tkinterdnd2.")

    def _toggle_theme(self):
        self.theme = "light" if self.theme == "dark" else "dark"
        self.palette = apply_theme(self, self.style, self.theme)
        self.theme_btn.config(text="Modo: Claro ◐" if self.theme == "light" else "Modo: Oscuro ◑")
        self.log.configure(
            bg=self.palette["card"], fg=self.palette["fg"], insertbackground=self.palette["fg"]
        )

    def _log(self, msg: str):
        from datetime import datetime

        self.log.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.log.see(tk.END)

    # ---------- Vistas ----------
    def _build_views(self):
        self.views = {}

        v_merge = ttk.Frame(self.content)
        self.views["MERGE"] = v_merge
        self._build_merge_view(v_merge, key="MERGE")
        v_merge.place(relx=0, rely=0, relwidth=1, relheight=1)

        v_split = ttk.Frame(self.content)
        self.views["SPLIT"] = v_split
        self._build_split_view(v_split)
        v_split.place(relx=0, rely=0, relwidth=1, relheight=1)

        v_comp = ttk.Frame(self.content)
        self.views["COMPRESS"] = v_comp
        self._build_compress_view(v_comp)
        v_comp.place(relx=0, rely=0, relwidth=1, relheight=1)

        v_conv = ttk.Frame(self.content)
        self.views["CONVERT"] = v_conv
        self._build_convert_view(v_conv)
        v_conv.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Pestaña “Todas”
        v_all = ttk.Frame(self.content)
        self.views["ALL"] = v_all
        self._build_all_tabs(v_all)
        v_all.place(relx=0, rely=0, relwidth=1, relheight=1)

    def _show_view(self, key: str):
        for _, frame in self.views.items():
            frame.lower()
        self.views[key].lift()

    # ---------- MERGE ----------
    def _build_merge_view(self, parent, key: str):
        """
        Construye una instancia de la vista MERGE con estado propio.
        Usa clausuras para que cada instancia manipule su propio Listbox/array.
        """
        card = GlassCard(parent, "Unir PDFs")
        card.pack(fill=tk.BOTH, expand=True)
        inner = card.inner

        state = {"files": []}  # estado local de esta instancia

        # Lista de archivos
        list_card = GlassCard(inner, "Archivos seleccionados (arrastra para reordenar)")
        list_card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        ttk.Label(
            list_card.inner, text="Lista de PDFs seleccionados:", foreground="#e5e7eb", background="#101827"
        ).pack(anchor="w", pady=(0, 4))

        listbox = tk.Listbox(
            list_card.inner,
            height=10,
            selectmode=tk.EXTENDED,
            relief="groove",
            bg="#181f2a",
            fg="#e5e7eb",
            selectbackground="#334155",
            selectforeground="#ffffff",
            highlightthickness=1,
            highlightbackground="#3b82f6",
        )
        listbox.pack(fill=tk.BOTH, expand=True)

        def on_drop(files):
            added = [f for f in files if f.lower().endswith(".pdf")]
            if not added:
                return
            state["files"].extend(added)
            for f in added:
                listbox.insert(tk.END, f)
            self._log(f"Agregados {len(added)} PDF(s) para unir")

        # Drop + Botón
        DropArea(inner, "Arrastra aquí PDFs o haz clic para elegir", on_drop, multiple=True).pack(
            fill=tk.X, pady=(8, 10)
        )

        # Reordenado simple dentro del Listbox
        drag_data = {"start": None}

        def on_list_start(e):
            drag_data["start"] = listbox.nearest(e.y)

        def on_list_motion(e):
            start = drag_data.get("start")
            if start is None:
                return
            i = listbox.nearest(e.y)
            if i != start and 0 <= start < listbox.size():
                item = listbox.get(start)
                listbox.delete(start)
                listbox.insert(i, item)
                moved = state["files"].pop(start)
                state["files"].insert(i, moved)
                drag_data["start"] = i

        listbox.bind("<ButtonPress-1>", on_list_start)
        listbox.bind("<B1-Motion>", on_list_motion)

        # Botones
        btns = ttk.Frame(inner)
        btns.pack(fill=tk.X, pady=10)

        def merge_and_clear():
            if not state["files"]:
                messagebox.showinfo("Unir PDFs", "No has agregado archivos.")
                return
            self.controller.merge_pdfs(state["files"])
            listbox.delete(0, tk.END)
            state["files"].clear()

        def remove_selected():
            sel = list(listbox.curselection())
            for idx in reversed(sel):
                listbox.delete(idx)
                del state["files"][idx]

        def clear_all():
            listbox.delete(0, tk.END)
            state["files"].clear()

        ttk.Button(btns, text="Fusionar seleccionados", style="Accent.TButton", command=merge_and_clear).pack(
            side=tk.LEFT
        )
        ttk.Button(btns, text="Quitar seleccionado", command=remove_selected).pack(side=tk.LEFT, padx=8)
        ttk.Button(btns, text="Limpiar lista", command=clear_all).pack(side=tk.LEFT, padx=8)

        # Guarda el estado por si lo necesitas (opcional)
        self._view_state[key] = state

    # ---------- SPLIT ----------
    def _build_split_view(self, parent):
        card = GlassCard(parent, "Dividir PDF")
        card.pack(fill=tk.BOTH, expand=True)
        inner = card.inner

        self.split_file = tk.StringVar()
        self.split_ranges = tk.StringVar(value="1-")

        def on_drop(files):
            pdfs = [f for f in files if f.lower().endswith(".pdf")]
            if pdfs:
                self.split_file.set(pdfs[0])
                self._log(f"Archivo para dividir: {pdfs[0]}")

        DropArea(inner, "Arrastra un PDF o haz clic", on_drop, multiple=False).pack(fill=tk.X, pady=(8, 12))
        row1 = ttk.Frame(inner)
        row1.pack(fill=tk.X, pady=6)
        ttk.Entry(row1, textvariable=self.split_file).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row1, text="Elegir PDF", command=lambda: self._ask_one(self.split_file)).pack(side=tk.LEFT, padx=8)

        row2 = ttk.Frame(inner)
        row2.pack(fill=tk.X, pady=6)
        ttk.Label(row2, text="Rangos (ej. 1-3,5,8-)").pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.split_ranges, width=30).pack(side=tk.LEFT, padx=8)

        ttk.Button(
            inner,
            text="Dividir → Elegir carpeta",
            style="Accent.TButton",
            command=lambda: self.controller.split_pdf(self.split_file.get().strip(), self.split_ranges.get().strip()),
        ).pack(anchor="w", pady=6)

    # ---------- COMPRESS ----------
    def _build_compress_view(self, parent):
        card = GlassCard(parent, "Comprimir PDF")
        card.pack(fill=tk.BOTH, expand=True)
        inner = card.inner

        self.comp_file = tk.StringVar()
        self.comp_method = tk.StringVar(value="lossless")
        self.comp_dpi = tk.IntVar(value=150)

        def on_drop(files):
            pdfs = [f for f in files if f.lower().endswith(".pdf")]
            if pdfs:
                self.comp_file.set(pdfs[0])
                self._log(f"Archivo para comprimir: {pdfs[0]}")

        DropArea(inner, "Arrastra un PDF o haz clic", on_drop, multiple=False).pack(fill=tk.X, pady=(8, 12))
        row = ttk.Frame(inner)
        row.pack(fill=tk.X, pady=6)
        ttk.Entry(row, textvariable=self.comp_file).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row, text="Elegir PDF", command=lambda: self._ask_one(self.comp_file)).pack(side=tk.LEFT, padx=8)

        chooser = ttk.Frame(inner)
        chooser.pack(fill=tk.X, pady=4)
        ttk.Radiobutton(chooser, text="Sin pérdida (recomendado)", variable=self.comp_method, value="lossless").pack(
            anchor="w"
        )
        r = ttk.Frame(inner)
        r.pack(fill=tk.X, pady=2)
        ttk.Radiobutton(r, text="Rasterizar (pierde texto) DPI:", variable=self.comp_method, value="raster").pack(
            side=tk.LEFT
        )
        ttk.Entry(r, textvariable=self.comp_dpi, width=8).pack(side=tk.LEFT, padx=8)

        ttk.Button(
            inner,
            text="Comprimir → Guardar como...",
            style="Accent.TButton",
            command=lambda: self.controller.compress_pdf(
                self.comp_file.get().strip(), self.comp_method.get(), self.comp_dpi.get()
            ),
        ).pack(anchor="w", pady=8)

    # ---------- CONVERT ----------
    def _build_convert_view(self, parent):
        card = GlassCard(parent, "Convertir PDF / Imágenes")
        card.pack(fill=tk.BOTH, expand=True)
        inner = card.inner

        # PDF → Imágenes
        p2i = GlassCard(inner, "PDF → Imágenes")
        p2i.pack(fill=tk.X, pady=8)
        self.p2i_file = tk.StringVar()
        self.p2i_dpi = tk.IntVar(value=150)

        def on_drop_p2i(files):
            pdfs = [f for f in files if f.lower().endswith(".pdf")]
            if pdfs:
                self.p2i_file.set(pdfs[0])
                self._log(f"PDF para exportar: {pdfs[0]}")

        DropArea(p2i.inner, "Arrastra un PDF o haz clic", on_drop_p2i, multiple=False).pack(fill=tk.X, pady=(6, 10))
        r = ttk.Frame(p2i.inner)
        r.pack(fill=tk.X, pady=4)
        ttk.Entry(r, textvariable=self.p2i_file).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(r, text="Elegir PDF", command=lambda: self._ask_one(self.p2i_file)).pack(side=tk.LEFT, padx=8)
        r2 = ttk.Frame(p2i.inner)
        r2.pack(fill=tk.X, pady=2)
        ttk.Label(r2, text="DPI:").pack(side=tk.LEFT)
        ttk.Entry(r2, textvariable=self.p2i_dpi, width=8).pack(side=tk.LEFT, padx=6)
        ttk.Button(
            p2i.inner,
            text="Exportar → Elegir carpeta",
            style="Accent.TButton",
            command=lambda: self.controller.pdf_to_images(self.p2i_file.get().strip(), self.p2i_dpi.get()),
        ).pack(anchor="w", pady=6)

        # Imágenes → PDF
        i2p = GlassCard(inner, "Imágenes → PDF")
        i2p.pack(fill=tk.X, pady=8)
        self.i2p_files = []

        def on_drop_i2p(files):
            imgs = [
                f
                for f in files
                if os.path.splitext(f.lower())[1] in (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")
            ]
            if imgs:
                self.i2p_files.extend(imgs)
                self._log(f"Agregadas {len(imgs)} imágenes")

        DropArea(i2p.inner, "Arrastra imágenes o haz clic", on_drop_i2p, multiple=True).pack(
            fill=tk.X, pady=(6, 10)
        )
        ttk.Button(
            i2p.inner,
            text="Crear PDF → Guardar como...",
            style="Accent.TButton",
            command=lambda: self.controller.images_to_pdf(self.i2p_files),
        ).pack(anchor="w", pady=6)

    # ---------- ALL ----------
    def _build_all_tabs(self, parent):
        nb = ttk.Notebook(parent)
        nb.pack(expand=True, fill=tk.BOTH)

        fdc = ttk.Frame(nb, padding=8)
        nb.add(fdc, text="Fusionar/Dividir/Comprimir")
        self._build_merge_view(fdc, key="ALL_MERGE")  # instancia independiente
        self._build_split_view(fdc)
        self._build_compress_view(fdc)

        conv = ttk.Frame(nb, padding=8)
        nb.add(conv, text="Convertir")
        self._build_convert_view(conv)

    # ---------- Helpers ----------
    def _ask_one(self, tk_var):
        f = tk.filedialog.askopenfilename(title="Selecciona archivo")
        if f:
            tk_var.set(f)
