# ui/main_view.py
# -*- coding: utf-8 -*-
import os
import subprocess
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageOps
from ui.widgets import GlassCard, DropArea, SUPPORTS_DND, DND_FILES, parse_dnd_files

# Intentar importar soporte DnD para la ventana principal
if SUPPORTS_DND:
    from tkinterdnd2 import TkinterDnD
    # Clase base híbrida
    class CTkDnD(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)
    BaseClass = CTkDnD
else:
    BaseClass = ctk.CTk

APP_NAME = "PDF Toolbox"
VERSION = "v2.0"
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")
IMAGE_PAGE_SIZE_OPTIONS = {
    "Tamaño original de imagen": "original",
    "A4 (297x210 mm)": "A4",
    "Carta (279x216 mm)": "Carta",
    "Legal (356x216 mm)": "Legal",
    "A3 (420x297 mm)": "A3",
    "A5 (210x148 mm)": "A5",
}

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class PDFToolboxApp(BaseClass):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.title(f"{APP_NAME} {VERSION}")
        self.geometry("1280x820")
        self.minsize(1100, 700)

        # Configurar grid principal
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Estado para vistas
        self.views = {}
        self.current_view = None

        # UI
        self._build_sidebar()
        self._build_content_area()
        self._build_toast()

        # Iniciar logger del controller
        self.controller.log = self.log_message
        self.controller.error_handler = self.show_error
        self.controller.on_success_action = self.show_success_modal
        self.controller.progress_handler = self.set_progress

        # Vista inicial
        self._show_view("MERGE")

    def show_success_modal(self, path):
        # Thread-safe UI update
        self.after(0, lambda: self._build_success_modal(path))

    def _build_success_modal(self, path):
        # TopLevel Window
        top = ctk.CTkToplevel(self)
        top.title("Operación Exitosa")
        top.geometry("400x200")
        top.resizable(False, False)
        top.attributes("-topmost", True)
        
        # Center relative to parent
        try:
            x = self.winfo_x() + (self.winfo_width() // 2) - 200
            y = self.winfo_y() + (self.winfo_height() // 2) - 100
            top.geometry(f"+{x}+{y}")
        except:
            pass

        ctk.CTkLabel(top, text="¡Proceso completado!", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 10))
        ctk.CTkLabel(top, text=f"Archivo guardado en:\n{os.path.basename(path)}", text_color="gray70").pack(pady=5)

        btn_frame = ctk.CTkFrame(top, fg_color="transparent")
        btn_frame.pack(pady=20)

        def open_loc():
            try:
                # Windows specific
                subprocess.Popen(f'explorer /select,"{os.path.normpath(path)}"')
            except Exception as e:
                print(f"Error opening explorer: {e}")
            top.destroy()

        ctk.CTkButton(btn_frame, text="Abrir Ubicación", command=open_loc).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cerrar", command=top.destroy, fg_color="transparent", border_width=1).pack(side="left", padx=10)

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(10, weight=1) # Spacer

        lbl = ctk.CTkLabel(self.sidebar, text=APP_NAME, font=ctk.CTkFont(size=20, weight="bold"))
        lbl.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.nav_buttons = {}
        
        btn_config = [
            ("Unir PDF", "MERGE"),
            ("Dividir PDF", "SPLIT"),
            ("Ordenar hojas", "ORGANIZE"),
            ("Comprimir", "COMPRESS"),
            ("Convertir", "CONVERT"),
            ("Imagen a PDF", "IMAGE_TO_PDF"),
            ("Rotar PDF", "ROTATE"),
            ("Seguridad", "PASSWORD"),
            ("Metadatos", "METADATA")
        ]

        for i, (text, key) in enumerate(btn_config, start=1):
            btn = ctk.CTkButton(
                self.sidebar, 
                text=text, 
                fg_color="transparent", 
                text_color=("gray10", "gray90"), 
                hover_color=("gray70", "gray30"),
                anchor="w",
                command=lambda k=key: self._show_view(k)
            )
            btn.grid(row=i, column=0, sticky="ew", padx=10, pady=5)
            self.nav_buttons[key] = btn

        # Selector de tema
        self.theme_switch = ctk.CTkSwitch(
            self.sidebar, 
            text="Modo Oscuro", 
            command=self._toggle_theme,
            onvalue="Dark", 
            offvalue="Light"
        )
        self.theme_switch.select() # Por defecto Dark
        self.theme_switch.grid(row=11, column=0, padx=20, pady=20, sticky="s")

        # Barra de progreso
        self.progress_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.progress_frame.grid(row=12, column=0, padx=10, pady=(0, 20), sticky="ew")
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=10)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=10)
        
        self.progress_lbl = ctk.CTkLabel(self.progress_frame, text="", font=ctk.CTkFont(size=10))
        self.progress_lbl.pack(pady=2)

    def _build_content_area(self):
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1) 
        # Las vistas se colocarán aquí con grid(sticky="nsew")

        # Inicializar vistas
        self._init_views()

    def _init_views(self):
        # Merge
        self.views["MERGE"] = self._create_view_frame()
        self._build_merge_view(self.views["MERGE"])
        
        # Split
        self.views["SPLIT"] = self._create_view_frame()
        self._build_split_view(self.views["SPLIT"])

        # Organize pages
        self.views["ORGANIZE"] = self._create_view_frame()
        self._build_organize_view(self.views["ORGANIZE"])

        # Compress
        self.views["COMPRESS"] = self._create_view_frame()
        self._build_compress_view(self.views["COMPRESS"])

        # Convert
        self.views["CONVERT"] = self._create_view_frame()
        self._build_convert_view(self.views["CONVERT"])

        # Imagen a PDF
        self.views["IMAGE_TO_PDF"] = self._create_view_frame()
        self._build_image_to_pdf_view(self.views["IMAGE_TO_PDF"])

        # Rotate
        self.views["ROTATE"] = self._create_view_frame()
        self._build_rotate_view(self.views["ROTATE"])

        # Password
        self.views["PASSWORD"] = self._create_view_frame()
        self._build_password_view(self.views["PASSWORD"])

        # Metadata
        self.views["METADATA"] = self._create_view_frame()
        self._build_metadata_view(self.views["METADATA"])

    def _create_view_frame(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent")
        f.grid(row=0, column=0, sticky="nsew")
        return f

    def _show_view(self, key):
        # Ocultar todas
        for k, v in self.views.items():
            v.grid_remove()
            self.nav_buttons[k].configure(fg_color="transparent")
        
        # Mostrar seleccionada
        if key in self.views:
            self.views[key].grid()
            self.nav_buttons[key].configure(fg_color=("gray75", "gray25"))
            self.current_view = key

    # ---------- Toast Notification ----------
    def _build_toast(self):
        self.toast_frame = ctk.CTkFrame(self, corner_radius=20, fg_color="#10b981", height=40)
        self.toast_lbl = ctk.CTkLabel(self.toast_frame, text="", text_color="white", padx=20)
        self.toast_lbl.pack(fill="both", expand=True)
        self.toast_timer = None

    def log_message(self, msg):
        # Thread-safe UI update
        self.after(0, lambda: self._show_toast(msg))

    def show_error(self, title, msg):
        self.after(0, lambda: messagebox.showerror(title, msg))

    def _show_toast(self, msg):
        # Cancelar timer anterior si existe
        if self.toast_timer:
            self.after_cancel(self.toast_timer)
        
        self.toast_lbl.configure(text=msg)
        # Mostrar en la parte inferior central flotando
        self.toast_frame.place(relx=0.5, rely=0.95, anchor="s")
        self.toast_frame.lift()
        
        # Ocultar después de 3s
        self.toast_timer = self.after(3000, self._hide_toast)

    def _hide_toast(self):
        self.toast_frame.place_forget()

    def set_progress(self, val, text=""):
        # val: 0.0 to 1.0
        self.after(0, lambda: self._update_progress_ui(val, text))

    def _update_progress_ui(self, val, text):
        self.progress_bar.set(val)
        self.progress_lbl.configure(text=text)
        if val >= 1.0 or val <= 0:
            self.progress_bar.configure(progress_color=["#3b82f6", "#1d4ed8"]) # Reset color
        else:
            self.progress_bar.configure(progress_color="#10b981") # Active color

    def _toggle_theme(self):
        mode = "Dark" if self.theme_switch.get() == "Dark" else "Light"
        ctk.set_appearance_mode(mode)

    # ================= VISTAS =================

    # ---------- MERGE ----------
    def _build_merge_view(self, parent):
        card = GlassCard(parent, "Unir PDFs")
        card.pack(fill="both", expand=True)

        # Contenedor para lista y controles de orden
        list_container = ctk.CTkFrame(card.inner, fg_color="transparent")
        list_container.pack(fill="both", expand=True, pady=(0, 10))

        listbox = tk.Listbox(
            list_container, 
            bg="#2b2b2b", 
            fg="white", 
            selectbackground="#3b82f6", 
            relief="flat",
            highlightthickness=0,
            font=("Segoe UI", 10)
        )
        listbox.pack(side="left", fill="both", expand=True)

        # Botones de orden laterales
        order_frame = ctk.CTkFrame(list_container, fg_color="transparent", width=40)
        order_frame.pack(side="left", padx=(10, 0), fill="y")

        files_state = []

        def update_list():
            curr_sel = listbox.curselection()
            listbox.delete(0, tk.END)
            for f in files_state:
                listbox.insert(tk.END, os.path.basename(f))
            lbl_count.configure(text=f"{len(files_state)} archivos seleccionados")
            if curr_sel:
                try: listbox.selection_set(curr_sel[0])
                except: pass

        def move_up():
            sel = listbox.curselection()
            if not sel or sel[0] == 0: return
            idx = sel[0]
            files_state[idx], files_state[idx-1] = files_state[idx-1], files_state[idx]
            update_list()
            listbox.selection_set(idx-1)

        def move_down():
            sel = listbox.curselection()
            if not sel or sel[0] == len(files_state) - 1: return
            idx = sel[0]
            files_state[idx], files_state[idx+1] = files_state[idx+1], files_state[idx]
            update_list()
            listbox.selection_set(idx+1)

        ctk.CTkButton(order_frame, text="▲", width=30, command=move_up).pack(pady=5)
        ctk.CTkButton(order_frame, text="▼", width=30, command=move_down).pack(pady=5)

        lbl_count = ctk.CTkLabel(card.inner, text="0 archivos seleccionados", font=ctk.CTkFont(size=12, slant="italic"))
        lbl_count.pack(anchor="e", pady=(0, 5))

        def on_drop(files):
            pdfs = [f for f in files if f.lower().endswith(".pdf")]
            if not pdfs: return
            files_state.extend(pdfs)
            update_list()

        DropArea(card.inner, "Arrastra PDFs aquí", on_drop, multiple=True).pack(fill="x", pady=10)

        btn_row = ctk.CTkFrame(card.inner, fg_color="transparent")
        btn_row.pack(fill="x")

        def run_merge():
            if not files_state: return
            self.controller.merge_pdfs(list(files_state))
            # No limpiamos automáticamente si el usuario quiere hacer otra acción con los mismos
            # o si falló. Pero usualmente en esta app se limpia tras éxito.
            # El controller actual pide el path, así que esperaremos al callback si quisiéramos limpiar.
        
        def clear():
            files_state.clear()
            update_list()

        ctk.CTkButton(btn_row, text="Fusionar PDFs", command=run_merge).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_row, text="Limpiar", command=clear, fg_color="transparent", border_width=1).pack(side="left")


    # ---------- SPLIT ----------
    def _build_split_view(self, parent):
        card = GlassCard(parent, "Dividir PDF")
        card.pack(fill="both", expand=True)

        self.split_file = tk.StringVar()
        self.split_range = tk.StringVar(value="1-")
        self.split_merge = tk.BooleanVar(value=False)

        def on_drop(files):
            if files: self.split_file.set(files[0])

        DropArea(card.inner, "Arrastra un PDF", on_drop, multiple=False).pack(fill="x", pady=10)

        ctk.CTkLabel(card.inner, text="Archivo seleccionado:", anchor="w").pack(fill="x")
        ctk.CTkEntry(card.inner, textvariable=self.split_file).pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(card.inner, text="Rango de páginas (ej. 1-3, 5):", anchor="w").pack(fill="x")
        ctk.CTkEntry(card.inner, textvariable=self.split_range).pack(fill="x", pady=(0, 10))

        ctk.CTkCheckBox(card.inner, text="Unir rango en un solo archivo", variable=self.split_merge).pack(anchor="w", pady=(0, 10))

        ctk.CTkButton(
            card.inner, 
            text="Dividir PDF", 
            command=lambda: self.controller.split_pdf(
                self.split_file.get(), 
                self.split_range.get(), 
                self.split_merge.get()
            )
        ).pack(anchor="w")


    # ---------- ORGANIZE PAGES ----------
    def _build_organize_view(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=0)
        parent.grid_rowconfigure(0, weight=1)

        self.pdf_page_items = []
        self.pdf_page_cards = {}
        self.pdf_page_thumbs = []
        self.pdf_page_thumb_cache = {}
        self.pdf_page_drag_index = None
        self.pdf_page_resize_job = None
        self.pdf_page_grid_cols = 0
        self._pdf_pages_last_signature = None

        gallery_shell = ctk.CTkFrame(parent, fg_color="#f7f8fb", corner_radius=0)
        gallery_shell.grid(row=0, column=0, sticky="nsew")
        gallery_shell.grid_rowconfigure(1, weight=1)
        gallery_shell.grid_columnconfigure(0, weight=1)

        topbar = ctk.CTkFrame(gallery_shell, fg_color="#f7f8fb", height=82, corner_radius=0)
        topbar.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 0))
        topbar.grid_columnconfigure(0, weight=1)

        title_block = ctk.CTkFrame(topbar, fg_color="transparent")
        title_block.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            title_block,
            text="Mesa de páginas",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#20232b",
        ).pack(anchor="w")
        self.pdf_page_count_lbl = ctk.CTkLabel(
            title_block,
            text="Sin páginas cargadas",
            font=ctk.CTkFont(size=12),
            text_color="#687183",
        )
        self.pdf_page_count_lbl.pack(anchor="w", pady=(2, 0))

        actions = ctk.CTkFrame(topbar, fg_color="transparent")
        actions.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(
            actions,
            text="Abrir PDF",
            width=94,
            height=42,
            corner_radius=8,
            fg_color="#ffffff",
            hover_color="#f0f2f7",
            text_color="#20232b",
            border_width=1,
            border_color="#dfe4ee",
            command=lambda: self._open_pdf_pages_dialog(replace=True),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="Añadir PDF",
            width=102,
            height=42,
            corner_radius=8,
            fg_color="#ffffff",
            hover_color="#f0f2f7",
            text_color="#20232b",
            border_width=1,
            border_color="#dfe4ee",
            command=lambda: self._open_pdf_pages_dialog(replace=False),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="Limpiar",
            width=76,
            height=36,
            corner_radius=8,
            fg_color="#ffffff",
            hover_color="#f0f2f7",
            text_color="#687183",
            border_width=1,
            border_color="#dfe4ee",
            command=self._clear_pdf_pages,
        ).pack(side="left")

        self.pdf_page_gallery = ctk.CTkScrollableFrame(
            gallery_shell,
            fg_color="#f7f8fb",
            corner_radius=0,
            scrollbar_button_color="#cfd6e3",
            scrollbar_button_hover_color="#bcc6d5",
        )
        self.pdf_page_gallery.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=(4, 0))
        self.pdf_page_gallery.bind("<Configure>", self._on_pdf_pages_gallery_resize, add="+")
        self._bind_pdf_page_scroll_tree(gallery_shell)
        self._bind_pdf_page_scroll_tree(self.pdf_page_gallery)

        self._register_pdf_pages_drop(gallery_shell)
        self._register_pdf_pages_drop(self.pdf_page_gallery)

        options = ctk.CTkFrame(parent, fg_color="#fbfbfd", corner_radius=0, width=330)
        options.grid(row=0, column=1, sticky="nsew")
        options.grid_propagate(False)
        options.grid_columnconfigure(0, weight=1)
        options.grid_rowconfigure(7, weight=1)
        ctk.CTkFrame(parent, fg_color="#e9342f", width=3, corner_radius=0).grid(row=0, column=1, sticky="nsw")

        ctk.CTkLabel(
            options,
            text="Orden final",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color="#20232b",
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=24, pady=(26, 18))

        ctk.CTkFrame(options, fg_color="#e5e7ed", height=1).grid(row=1, column=0, sticky="ew")

        stats = ctk.CTkFrame(options, fg_color="transparent")
        stats.grid(row=2, column=0, sticky="ew", padx=24, pady=(24, 8))
        stats.grid_columnconfigure((0, 1), weight=1, uniform="stats")

        page_stat = ctk.CTkFrame(stats, fg_color="#ffffff", corner_radius=8, border_width=1, border_color="#e5e8ef")
        page_stat.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        ctk.CTkLabel(page_stat, text="Páginas", font=ctk.CTkFont(size=12), text_color="#687183").pack(pady=(14, 2))
        self.pdf_pages_total_lbl = ctk.CTkLabel(page_stat, text="0", font=ctk.CTkFont(size=26, weight="bold"), text_color="#20232b")
        self.pdf_pages_total_lbl.pack(pady=(0, 14))

        source_stat = ctk.CTkFrame(stats, fg_color="#ffffff", corner_radius=8, border_width=1, border_color="#e5e8ef")
        source_stat.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        ctk.CTkLabel(source_stat, text="PDFs", font=ctk.CTkFont(size=12), text_color="#687183").pack(pady=(14, 2))
        self.pdf_pages_sources_lbl = ctk.CTkLabel(source_stat, text="0", font=ctk.CTkFont(size=26, weight="bold"), text_color="#20232b")
        self.pdf_pages_sources_lbl.pack(pady=(0, 14))

        ctk.CTkLabel(
            options,
            text="Herramientas",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#303744",
            anchor="w",
        ).grid(row=3, column=0, sticky="ew", padx=24, pady=(24, 10))

        ctk.CTkButton(
            options,
            text="Restaurar orden original",
            height=42,
            corner_radius=8,
            fg_color="#ffffff",
            hover_color="#f0f2f7",
            text_color="#303744",
            border_width=1,
            border_color="#dfe4ee",
            command=self._sort_pdf_pages_original,
        ).grid(row=4, column=0, sticky="ew", padx=24)

        ctk.CTkLabel(
            options,
            text="Salida sin rasterizar",
            font=ctk.CTkFont(size=12),
            text_color="#687183",
            anchor="w",
        ).grid(row=5, column=0, sticky="ew", padx=24, pady=(18, 0))

        ctk.CTkButton(
            options,
            text="Guardar PDF",
            height=70,
            corner_radius=9,
            fg_color="#e9342f",
            hover_color="#c92d29",
            font=ctk.CTkFont(size=21, weight="bold"),
            command=self._run_pdf_page_organizer,
        ).grid(row=8, column=0, sticky="sew", padx=24, pady=(18, 18))

        self._refresh_pdf_pages_gallery()

    def _bind_pdf_page_scroll_tree(self, widget):
        try:
            widget.bind("<MouseWheel>", self._on_pdf_pages_mousewheel)
            widget.bind("<Button-4>", self._on_pdf_pages_mousewheel)
            widget.bind("<Button-5>", self._on_pdf_pages_mousewheel)
        except Exception:
            pass

        for child in getattr(widget, "winfo_children", lambda: [])():
            self._bind_pdf_page_scroll_tree(child)

    def _on_pdf_pages_mousewheel(self, event):
        if getattr(self, "current_view", None) != "ORGANIZE":
            return

        canvas = getattr(getattr(self, "pdf_page_gallery", None), "_parent_canvas", None)
        if canvas is None:
            return

        if getattr(event, "num", None) == 4:
            units = -3
        elif getattr(event, "num", None) == 5:
            units = 3
        else:
            delta = getattr(event, "delta", 0)
            units = int(-delta / 120) if delta else 0
            if units == 0 and delta:
                units = -1 if delta > 0 else 1

        if units:
            canvas.yview_scroll(units, "units")
        return "break"

    def _register_pdf_pages_drop(self, widget):
        if not SUPPORTS_DND or DND_FILES is None:
            return
        try:
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._on_pdf_pages_drop)
        except Exception:
            pass

    def _on_pdf_pages_drop(self, event):
        self._add_pdf_page_files(parse_dnd_files(event.data, multiple=True), replace=False)

    def _open_pdf_pages_dialog(self, replace=False):
        files = filedialog.askopenfilenames(
            title="Selecciona PDF",
            filetypes=[
                ("PDF", "*.pdf"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if files:
            self._add_pdf_page_files(list(files), replace=replace)

    def _add_pdf_page_files(self, files, replace=False):
        valid = [f for f in files if os.path.isfile(f) and f.lower().endswith(".pdf")]
        if not valid:
            self.show_error(APP_NAME, "Selecciona PDFs válidos")
            return

        if replace:
            self.pdf_page_items.clear()
            self.pdf_page_thumb_cache.clear()

        added = 0
        for path in valid:
            page_count = self.controller.get_pdf_page_count(path)
            if page_count <= 0:
                continue
            for page_index in range(page_count):
                self.pdf_page_items.append({
                    "path": path,
                    "page_index": page_index,
                    "source_name": os.path.basename(path),
                })
                added += 1

        if added == 0:
            self._refresh_pdf_pages_gallery()
            return

        if len(valid) != len(files):
            self.log_message("Se omitieron archivos no compatibles")

        self._pdf_pages_last_signature = None
        self._refresh_pdf_pages_gallery()

    def _sort_pdf_pages_original(self):
        self.pdf_page_items.sort(key=lambda item: (item["source_name"].lower(), item["page_index"]))
        self._pdf_pages_last_signature = None
        self._refresh_pdf_pages_gallery()

    def _clear_pdf_pages(self):
        self.pdf_page_items.clear()
        self._pdf_pages_last_signature = None
        self._refresh_pdf_pages_gallery()

    def _remove_pdf_page(self, index):
        if 0 <= index < len(self.pdf_page_items):
            self.pdf_page_items.pop(index)
            self._pdf_pages_last_signature = None
            self._refresh_pdf_pages_gallery()

    def _on_pdf_pages_gallery_resize(self, _event=None):
        if self.pdf_page_resize_job:
            self.after_cancel(self.pdf_page_resize_job)
        self.pdf_page_resize_job = self.after(120, self._refresh_pdf_pages_gallery)

    def _update_pdf_pages_scrollregion(self):
        canvas = getattr(getattr(self, "pdf_page_gallery", None), "_parent_canvas", None)
        if canvas is not None:
            canvas.configure(scrollregion=canvas.bbox("all"))

    def _pdf_page_columns(self):
        width = max(1, self.pdf_page_gallery.winfo_width())
        return max(2, min(7, width // 168))

    def _pdf_pages_signature(self):
        return tuple((item["path"], item["page_index"]) for item in self.pdf_page_items)

    def _refresh_pdf_pages_gallery(self):
        if not hasattr(self, "pdf_page_gallery"):
            return

        cols = self._pdf_page_columns()
        signature = self._pdf_pages_signature()
        if cols == self.pdf_page_grid_cols and signature == self._pdf_pages_last_signature:
            self._update_pdf_page_count()
            return

        self.pdf_page_grid_cols = cols
        self._pdf_pages_last_signature = signature
        self.pdf_page_cards = {}
        self.pdf_page_thumbs = []

        for child in self.pdf_page_gallery.winfo_children():
            child.destroy()

        if not self.pdf_page_items:
            empty = ctk.CTkFrame(
                self.pdf_page_gallery,
                fg_color="#ffffff",
                corner_radius=8,
                border_width=1,
                border_color="#dfe3eb",
            )
            empty.grid(row=0, column=0, columnspan=cols, sticky="nsew", padx=24, pady=48, ipady=44)
            self._register_pdf_pages_drop(empty)
            ctk.CTkLabel(
                empty,
                text="Arrastra PDFs aquí",
                font=ctk.CTkFont(size=22, weight="bold"),
                text_color="#202124",
            ).pack(pady=(10, 6))
            ctk.CTkLabel(
                empty,
                text="Abre un PDF para acomodar, eliminar o añadir páginas antes de guardar.",
                font=ctk.CTkFont(size=13),
                text_color="#69707f",
                wraplength=420,
            ).pack(pady=(0, 16))
            ctk.CTkButton(
                empty,
                text="Abrir PDF",
                height=42,
                corner_radius=8,
                fg_color="#e9342f",
                hover_color="#c92d29",
                command=lambda: self._open_pdf_pages_dialog(replace=True),
            ).pack()
            self._bind_pdf_page_scroll_tree(empty)
            self.after_idle(self._update_pdf_pages_scrollregion)
            self._update_pdf_page_count()
            return

        for index, item in enumerate(self.pdf_page_items):
            row, col = divmod(index, cols)
            card = self._create_pdf_page_card(self.pdf_page_gallery, item, index)
            card.grid(row=row, column=col, padx=7, pady=7, sticky="n")

        self.after_idle(self._update_pdf_pages_scrollregion)
        self._update_pdf_page_count()

    def _create_pdf_page_card(self, parent, item, index):
        card = ctk.CTkFrame(
            parent,
            fg_color="#ffffff",
            corner_radius=7,
            border_width=1,
            border_color="#e5e8ef",
            width=154,
            height=238,
        )
        card.grid_propagate(False)

        remove_btn = ctk.CTkButton(
            card,
            text="x",
            width=22,
            height=22,
            corner_radius=11,
            fg_color="#2f3540",
            hover_color="#ef312e",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda i=index: self._remove_pdf_page(i),
        )
        remove_btn.place(relx=1.0, x=-8, y=8, anchor="ne")

        thumb = self._make_pdf_page_thumb(item)
        self.pdf_page_thumbs.append(thumb)
        thumb_label = ctk.CTkLabel(card, image=thumb, text="")
        thumb_label.pack(pady=(18, 8))

        page_label = ctk.CTkLabel(
            card,
            text=f"Página {item['page_index'] + 1}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#303744",
        )
        page_label.pack(fill="x", padx=8)

        source_label = ctk.CTkLabel(
            card,
            text=self._short_pdf_page_name(item["source_name"]),
            font=ctk.CTkFont(size=10),
            text_color="#687183",
            wraplength=132,
            justify="left",
        )
        source_label.pack(fill="x", padx=8, pady=(2, 0))

        order_badge = ctk.CTkLabel(
            card,
            text=str(index + 1),
            width=26,
            height=20,
            corner_radius=10,
            fg_color="#f0f2f7",
            text_color="#69707f",
            font=ctk.CTkFont(size=10, weight="bold"),
        )
        order_badge.place(x=8, y=8)

        for widget in (card, thumb_label, page_label, source_label, order_badge):
            self.pdf_page_cards[widget] = index
            widget.bind("<ButtonPress-1>", lambda event, i=index: self._on_pdf_page_card_press(i, event))
            widget.bind("<ButtonRelease-1>", lambda event: self._on_pdf_page_card_release(event))

        self._bind_pdf_page_scroll_tree(card)
        return card

    def _make_pdf_page_thumb(self, item):
        key = (item["path"], item["page_index"])
        if key in self.pdf_page_thumb_cache:
            return self.pdf_page_thumb_cache[key]

        box_w, box_h = 116, 154
        canvas = Image.new("RGB", (box_w, box_h), "#f8f8fb")
        try:
            page_img = self.controller.render_pdf_page_thumbnail(item["path"], item["page_index"], box_w - 10, box_h - 10)
            page_img.thumbnail((box_w - 10, box_h - 10), Image.Resampling.LANCZOS)
            x = (box_w - page_img.width) // 2
            y = (box_h - page_img.height) // 2
            canvas.paste(page_img, (x, y))
        except Exception:
            pass

        image = ctk.CTkImage(light_image=canvas, dark_image=canvas, size=(box_w, box_h))
        self.pdf_page_thumb_cache[key] = image
        return image

    def _short_pdf_page_name(self, name):
        if len(name) <= 24:
            return name
        root, ext = os.path.splitext(name)
        return f"{root[:19]}...{ext}"

    def _on_pdf_page_card_press(self, index, _event):
        self.pdf_page_drag_index = index

    def _on_pdf_page_card_release(self, event):
        source = self.pdf_page_drag_index
        self.pdf_page_drag_index = None
        if source is None or source >= len(self.pdf_page_items):
            return

        target = self._pdf_page_index_at(event.x_root, event.y_root)
        if target is None or target == source or target >= len(self.pdf_page_items):
            return

        item = self.pdf_page_items.pop(source)
        self.pdf_page_items.insert(target, item)
        self._pdf_pages_last_signature = None
        self._refresh_pdf_pages_gallery()

    def _pdf_page_index_at(self, x_root, y_root):
        widget = self.winfo_containing(x_root, y_root)
        while widget is not None:
            if widget in self.pdf_page_cards:
                return self.pdf_page_cards[widget]
            widget = getattr(widget, "master", None)
        return None

    def _update_pdf_page_count(self):
        count = len(getattr(self, "pdf_page_items", []))
        sources = len({item["path"] for item in getattr(self, "pdf_page_items", [])})
        if count == 0:
            text = "Sin páginas cargadas"
        elif count == 1:
            text = "1 página lista para guardar"
        else:
            text = f"{count} páginas listas para guardar"
        self.pdf_page_count_lbl.configure(text=text)
        self.pdf_pages_total_lbl.configure(text=str(count))
        self.pdf_pages_sources_lbl.configure(text=str(sources))

    def _run_pdf_page_organizer(self):
        refs = [
            {"path": item["path"], "page_index": item["page_index"]}
            for item in self.pdf_page_items
        ]
        self.controller.organize_pdf_pages(refs)


    # ---------- COMPRESS ----------
    def _build_compress_view(self, parent):
        card = GlassCard(parent, "Comprimir PDF")
        card.pack(fill="both", expand=True)

        self.comp_file = tk.StringVar()
        self.comp_method = tk.StringVar(value="lossless")
        self.comp_dpi = tk.IntVar(value=150)

        def on_drop(files):
            if files: self.comp_file.set(files[0])

        DropArea(card.inner, "Arrastra un PDF", on_drop, multiple=False).pack(fill="x", pady=10)
        ctk.CTkEntry(card.inner, textvariable=self.comp_file, placeholder_text="Ruta del archivo...").pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(card.inner, text="Método de compresión:", anchor="w").pack(fill="x")
        ctk.CTkRadioButton(card.inner, text="Sin pérdida (Recomendado)", variable=self.comp_method, value="lossless").pack(anchor="w", pady=5)
        ctk.CTkRadioButton(card.inner, text="Rasterizar (Reduce calidad)", variable=self.comp_method, value="raster").pack(anchor="w", pady=5)

        ctk.CTkLabel(card.inner, text="DPI (para Raster):", anchor="w").pack(fill="x", pady=(10, 0))
        ctk.CTkSlider(card.inner, from_=72, to=300, variable=self.comp_dpi, number_of_steps=10).pack(fill="x")
        
        lbl_dpi = ctk.CTkLabel(card.inner, text="150")
        lbl_dpi.pack(anchor="e")
        # Update label on slide
        def update_lbl(val): lbl_dpi.configure(text=f"{int(val)}")
        # Bind no es directo en slider var trace, pero podemos usar command si quisiéramos. 
        # Simplificación: el user ve el slider.

        ctk.CTkButton(
            card.inner, 
            text="Comprimir", 
            command=lambda: self.controller.compress_pdf(
                self.comp_file.get(), 
                self.comp_method.get(), 
                self.comp_dpi.get()
            )
        ).pack(anchor="w", pady=10)


    # ---------- CONVERT ----------
    def _build_convert_view(self, parent):
        # Tabs internas
        tab = ctk.CTkTabview(parent)
        tab.pack(fill="both", expand=True)
        tab.add("PDF a Imágenes")
        tab.add("Imágenes a PDF")

        # PDF -> IMG
        p2i = tab.tab("PDF a Imágenes")
        self.p2i_file = tk.StringVar()
        DropArea(p2i, "Arrastra PDF", lambda f: self.p2i_file.set(f[0] if f else ""), multiple=False).pack(fill="x", pady=10)
        ctk.CTkEntry(p2i, textvariable=self.p2i_file).pack(fill="x", pady=5)
        ctk.CTkButton(p2i, text="Convertir a Imágenes", command=lambda: self.controller.pdf_to_images(self.p2i_file.get())).pack(pady=10)

        # IMG -> PDF
        i2p = tab.tab("Imágenes a PDF")
        i2p.grid_columnconfigure(0, weight=1)
        i2p.grid_rowconfigure(0, weight=1)
        shortcut = ctk.CTkFrame(i2p, fg_color="transparent")
        shortcut.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        shortcut.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            shortcut,
            text="El convertidor avanzado de imágenes a PDF ahora tiene miniaturas, orden por arrastre y opciones de página.",
            wraplength=560,
            justify="center",
            font=ctk.CTkFont(size=15),
        ).pack(pady=(90, 18))
        ctk.CTkButton(
            shortcut,
            text="Abrir Imagen a PDF",
            height=42,
            command=lambda: self._show_view("IMAGE_TO_PDF"),
        ).pack()

    # ---------- IMAGE TO PDF ----------
    def _build_image_to_pdf_view(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=0)
        parent.grid_rowconfigure(0, weight=1)

        self.image_pdf_files = []
        self.image_pdf_cards = {}
        self.image_pdf_thumbs = []
        self.image_pdf_thumb_cache = {}
        self.image_pdf_drag_index = None
        self.image_pdf_resize_job = None
        self.image_pdf_grid_cols = 0

        self.image_pdf_orientation = tk.StringVar(value="portrait")
        self.image_pdf_page_size = tk.StringVar(value=list(IMAGE_PAGE_SIZE_OPTIONS.keys())[0])
        self.image_pdf_margin = tk.StringVar(value="none")
        self.image_pdf_merge = tk.BooleanVar(value=True)
        self.image_pdf_option_tiles = []

        gallery_shell = ctk.CTkFrame(parent, fg_color="#f7f8fb", corner_radius=0)
        gallery_shell.grid(row=0, column=0, sticky="nsew")
        gallery_shell.grid_rowconfigure(1, weight=1)
        gallery_shell.grid_columnconfigure(0, weight=1)

        topbar = ctk.CTkFrame(gallery_shell, fg_color="#f7f8fb", height=82, corner_radius=0)
        topbar.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 0))
        topbar.grid_columnconfigure(0, weight=1)

        title_block = ctk.CTkFrame(topbar, fg_color="transparent")
        title_block.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            title_block,
            text="Mesa de imágenes",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#20232b",
        ).pack(anchor="w")
        self.image_pdf_count_lbl = ctk.CTkLabel(
            title_block,
            text="PDF listo para armar",
            font=ctk.CTkFont(size=12),
            text_color="#687183",
        )
        self.image_pdf_count_lbl.pack(anchor="w", pady=(2, 0))

        actions = ctk.CTkFrame(topbar, fg_color="transparent")
        actions.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(
            actions,
            text="A-Z",
            width=46,
            height=46,
            corner_radius=23,
            fg_color="#ffffff",
            hover_color="#f0f2f7",
            text_color="#20232b",
            border_width=1,
            border_color="#dfe4ee",
            command=self._sort_image_pdf_files,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="+",
            width=52,
            height=52,
            corner_radius=26,
            fg_color="#e9342f",
            hover_color="#c92d29",
            font=ctk.CTkFont(size=28, weight="normal"),
            command=self._open_image_pdf_dialog,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="Limpiar",
            width=74,
            height=36,
            corner_radius=18,
            fg_color="#ffffff",
            hover_color="#f0f2f7",
            text_color="#687183",
            border_width=1,
            border_color="#dfe4ee",
            command=self._clear_image_pdf_files,
        ).pack(side="left")

        self.image_pdf_gallery = ctk.CTkScrollableFrame(
            gallery_shell,
            fg_color="#f7f8fb",
            corner_radius=0,
            scrollbar_button_color="#cfd6e3",
            scrollbar_button_hover_color="#bcc6d5",
        )
        self.image_pdf_gallery.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=(4, 0))
        self.image_pdf_gallery.bind("<Configure>", self._on_image_pdf_gallery_resize, add="+")
        self._bind_image_pdf_scroll_tree(gallery_shell)
        self._bind_image_pdf_scroll_tree(self.image_pdf_gallery)

        self._register_image_pdf_drop(gallery_shell)
        self._register_image_pdf_drop(self.image_pdf_gallery)

        options = ctk.CTkFrame(parent, fg_color="#fbfbfd", corner_radius=0, width=360)
        options.grid(row=0, column=1, sticky="nsew")
        options.grid_propagate(False)
        options.grid_columnconfigure(0, weight=1)
        options.grid_rowconfigure(10, weight=1)
        ctk.CTkFrame(parent, fg_color="#e9342f", width=3, corner_radius=0).grid(row=0, column=1, sticky="nsw")

        ctk.CTkLabel(
            options,
            text="Ajustes de salida",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color="#20232b",
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=24, pady=(26, 18))

        ctk.CTkFrame(options, fg_color="#e5e7ed", height=1).grid(row=1, column=0, sticky="ew")

        ctk.CTkLabel(
            options,
            text="Orientación de página",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#303744",
            anchor="w",
        ).grid(row=2, column=0, sticky="ew", padx=24, pady=(20, 10))

        orientation_row = ctk.CTkFrame(options, fg_color="transparent")
        orientation_row.grid(row=3, column=0, sticky="ew", padx=24)
        orientation_row.grid_columnconfigure((0, 1), weight=1, uniform="orientation")
        self._create_image_pdf_option_tile(orientation_row, "Vertical", "portrait", self.image_pdf_orientation, 0, 0, "▯")
        self._create_image_pdf_option_tile(orientation_row, "Horizontal", "landscape", self.image_pdf_orientation, 0, 1, "▭")

        ctk.CTkLabel(
            options,
            text="Tamaño de página",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#303744",
            anchor="w",
        ).grid(row=4, column=0, sticky="ew", padx=24, pady=(28, 8))

        ctk.CTkComboBox(
            options,
            values=list(IMAGE_PAGE_SIZE_OPTIONS.keys()),
            variable=self.image_pdf_page_size,
            height=42,
            corner_radius=3,
            border_color="#9ca3af",
            button_color="#ffffff",
            button_hover_color="#f3f4f6",
            fg_color="#ffffff",
            text_color="#3f4652",
            dropdown_fg_color="#ffffff",
            dropdown_text_color="#3f4652",
        ).grid(row=5, column=0, sticky="ew", padx=24)

        self.image_pdf_size_hint = ctk.CTkLabel(
            options,
            text="Original conserva el ancho y alto de cada imagen.",
            font=ctk.CTkFont(size=11),
            text_color="#687183",
            anchor="w",
        )
        self.image_pdf_size_hint.grid(row=6, column=0, sticky="ew", padx=24, pady=(6, 0))

        ctk.CTkLabel(
            options,
            text="Margen",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#303744",
            anchor="w",
        ).grid(row=7, column=0, sticky="ew", padx=24, pady=(28, 10))

        margin_row = ctk.CTkFrame(options, fg_color="transparent")
        margin_row.grid(row=8, column=0, sticky="ew", padx=24)
        margin_row.grid_columnconfigure((0, 1, 2), weight=1, uniform="margin")
        self._create_image_pdf_option_tile(margin_row, "Sin\nmargen", "none", self.image_pdf_margin, 0, 0, "▣", height=118)
        self._create_image_pdf_option_tile(margin_row, "Pequeño", "small", self.image_pdf_margin, 0, 1, "□", height=118)
        self._create_image_pdf_option_tile(margin_row, "Grande", "large", self.image_pdf_margin, 0, 2, "▢", height=118)

        ctk.CTkCheckBox(
            options,
            text="Unir todas las imágenes en un único PDF",
            variable=self.image_pdf_merge,
            font=ctk.CTkFont(size=13),
            text_color="#303744",
            checkbox_width=24,
            checkbox_height=24,
            corner_radius=5,
            fg_color="#46c986",
            hover_color="#38b978",
            border_color="#46c986",
            checkmark_color="#ffffff",
        ).grid(row=9, column=0, sticky="w", padx=24, pady=(30, 0))

        ctk.CTkButton(
            options,
            text="Crear PDF   >",
            height=76,
            corner_radius=9,
            fg_color="#e9342f",
            hover_color="#c92d29",
            font=ctk.CTkFont(size=21, weight="bold"),
            command=self._run_image_pdf_conversion,
        ).grid(row=11, column=0, sticky="sew", padx=24, pady=(18, 18))

        self._refresh_image_pdf_option_tiles()
        self._refresh_image_pdf_gallery()

    def _create_image_pdf_option_tile(self, parent, text, value, variable, row, column, icon_text, height=104):
        tile = ctk.CTkFrame(parent, fg_color="#f4f4fa", corner_radius=8, border_width=1, border_color="#ececf4", height=height)
        tile.grid(row=row, column=column, sticky="nsew", padx=4)
        tile.grid_propagate(False)

        icon = ctk.CTkLabel(tile, text=icon_text, font=ctk.CTkFont(size=32, weight="bold"), text_color="#7d8190")
        icon.pack(pady=(18, 4))
        label = ctk.CTkLabel(tile, text=text, font=ctk.CTkFont(size=13), text_color="#7d8190")
        label.pack()

        def select(_event=None):
            variable.set(value)
            self._refresh_image_pdf_option_tiles()

        for widget in (tile, icon, label):
            widget.bind("<Button-1>", select)

        self.image_pdf_option_tiles.append((tile, icon, label, variable, value))

    def _refresh_image_pdf_option_tiles(self):
        for tile, icon, label, variable, value in getattr(self, "image_pdf_option_tiles", []):
            selected = variable.get() == value
            tile.configure(
                fg_color="#ffffff" if selected else "#f4f4fa",
                border_color="#e9342f" if selected else "#ececf4",
                border_width=2 if selected else 1,
            )
            icon.configure(text_color="#e9342f" if selected else "#7d8190")
            label.configure(text_color="#e9342f" if selected else "#7d8190")

    def _bind_image_pdf_scroll_tree(self, widget):
        try:
            widget.bind("<MouseWheel>", self._on_image_pdf_mousewheel)
            widget.bind("<Button-4>", self._on_image_pdf_mousewheel)
            widget.bind("<Button-5>", self._on_image_pdf_mousewheel)
        except Exception:
            pass

        for child in getattr(widget, "winfo_children", lambda: [])():
            self._bind_image_pdf_scroll_tree(child)

    def _on_image_pdf_mousewheel(self, event):
        if getattr(self, "current_view", None) != "IMAGE_TO_PDF":
            return

        canvas = getattr(getattr(self, "image_pdf_gallery", None), "_parent_canvas", None)
        if canvas is None:
            return

        if getattr(event, "num", None) == 4:
            units = -3
        elif getattr(event, "num", None) == 5:
            units = 3
        else:
            delta = getattr(event, "delta", 0)
            units = int(-delta / 120) if delta else 0
            if units == 0 and delta:
                units = -1 if delta > 0 else 1

        if units:
            canvas.yview_scroll(units, "units")
        return "break"

    def _register_image_pdf_drop(self, widget):
        if not SUPPORTS_DND or DND_FILES is None:
            return
        try:
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._on_image_pdf_drop)
        except Exception:
            pass

    def _on_image_pdf_drop(self, event):
        self._add_image_pdf_files(parse_dnd_files(event.data, multiple=True))

    def _open_image_pdf_dialog(self):
        files = filedialog.askopenfilenames(
            title="Selecciona imágenes",
            filetypes=[
                ("Imágenes", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if files:
            self._add_image_pdf_files(list(files))

    def _add_image_pdf_files(self, files):
        valid = [f for f in files if os.path.isfile(f) and f.lower().endswith(IMAGE_EXTENSIONS)]
        if not valid:
            self.show_error(APP_NAME, "Arrastra o selecciona imágenes válidas")
            return
        self.image_pdf_files.extend(valid)
        if len(valid) != len(files):
            self.log_message("Se omitieron archivos no compatibles")
        self._refresh_image_pdf_gallery()

    def _sort_image_pdf_files(self):
        self.image_pdf_files.sort(key=lambda f: os.path.basename(f).lower())
        self._image_pdf_last_count = None
        self._refresh_image_pdf_gallery()

    def _clear_image_pdf_files(self):
        self.image_pdf_files.clear()
        self._refresh_image_pdf_gallery()

    def _remove_image_pdf_file(self, index):
        if 0 <= index < len(self.image_pdf_files):
            self.image_pdf_files.pop(index)
            self._refresh_image_pdf_gallery()

    def _on_image_pdf_gallery_resize(self, _event=None):
        if self.image_pdf_resize_job:
            self.after_cancel(self.image_pdf_resize_job)
        self.image_pdf_resize_job = self.after(120, self._refresh_image_pdf_gallery)

    def _update_image_pdf_scrollregion(self):
        canvas = getattr(getattr(self, "image_pdf_gallery", None), "_parent_canvas", None)
        if canvas is not None:
            canvas.configure(scrollregion=canvas.bbox("all"))

    def _image_pdf_columns(self):
        width = max(1, self.image_pdf_gallery.winfo_width())
        return max(2, min(8, width // 160))

    def _refresh_image_pdf_gallery(self):
        if not hasattr(self, "image_pdf_gallery"):
            return

        cols = self._image_pdf_columns()
        if cols == self.image_pdf_grid_cols and getattr(self, "_image_pdf_last_count", None) == len(self.image_pdf_files):
            self._update_image_pdf_count()
            return

        self.image_pdf_grid_cols = cols
        self._image_pdf_last_count = len(self.image_pdf_files)
        self.image_pdf_cards = {}
        self.image_pdf_thumbs = []

        for child in self.image_pdf_gallery.winfo_children():
            child.destroy()

        if not self.image_pdf_files:
            empty = ctk.CTkFrame(
                self.image_pdf_gallery,
                fg_color="#ffffff",
                corner_radius=8,
                border_width=1,
                border_color="#dfe3eb",
            )
            empty.grid(row=0, column=0, columnspan=cols, sticky="nsew", padx=24, pady=48, ipady=44)
            self._register_image_pdf_drop(empty)
            ctk.CTkLabel(
                empty,
                text="Arrastra imágenes aquí",
                font=ctk.CTkFont(size=22, weight="bold"),
                text_color="#202124",
            ).pack(pady=(10, 6))
            ctk.CTkLabel(
                empty,
                text="Puedes soltarlas en cualquier orden y luego arrastrar las miniaturas para reordenarlas.",
                font=ctk.CTkFont(size=13),
                text_color="#69707f",
                wraplength=420,
            ).pack(pady=(0, 16))
            ctk.CTkButton(
                empty,
                text="Seleccionar imágenes",
                height=42,
                corner_radius=21,
                fg_color="#e9342f",
                hover_color="#c92d29",
                command=self._open_image_pdf_dialog,
            ).pack()
            self._bind_image_pdf_scroll_tree(empty)
            self.after_idle(self._update_image_pdf_scrollregion)
            self._update_image_pdf_count()
            return

        for index, path in enumerate(self.image_pdf_files):
            row, col = divmod(index, cols)
            card = self._create_image_pdf_card(self.image_pdf_gallery, path, index)
            card.grid(row=row, column=col, padx=7, pady=7, sticky="n")

        self.after_idle(self._update_image_pdf_scrollregion)
        self._update_image_pdf_count()

    def _create_image_pdf_card(self, parent, path, index):
        card = ctk.CTkFrame(
            parent,
            fg_color="#ffffff",
            corner_radius=7,
            border_width=1,
            border_color="#e5e8ef",
            width=146,
            height=214,
        )
        card.grid_propagate(False)

        remove_btn = ctk.CTkButton(
            card,
            text="x",
            width=22,
            height=22,
            corner_radius=11,
            fg_color="#2f3540",
            hover_color="#ef312e",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda i=index: self._remove_image_pdf_file(i),
        )
        remove_btn.place(relx=1.0, x=-8, y=8, anchor="ne")

        thumb = self._make_image_pdf_thumb(path)
        self.image_pdf_thumbs.append(thumb)
        thumb_label = ctk.CTkLabel(card, image=thumb, text="")
        thumb_label.pack(pady=(18, 8))

        name = self._short_image_pdf_name(os.path.basename(path))
        name_label = ctk.CTkLabel(
            card,
            text=name,
            font=ctk.CTkFont(size=11),
            text_color="#4b5563",
            wraplength=126,
            justify="left",
        )
        name_label.pack(fill="x", padx=8)

        order_badge = ctk.CTkLabel(
            card,
            text=str(index + 1),
            width=26,
            height=20,
            corner_radius=10,
            fg_color="#f0f2f7",
            text_color="#69707f",
            font=ctk.CTkFont(size=10, weight="bold"),
        )
        order_badge.place(x=8, y=8)

        for widget in (card, thumb_label, name_label, order_badge):
            self.image_pdf_cards[widget] = index
            widget.bind("<ButtonPress-1>", lambda event, i=index: self._on_image_pdf_card_press(i, event))
            widget.bind("<ButtonRelease-1>", lambda event: self._on_image_pdf_card_release(event))

        self._bind_image_pdf_scroll_tree(card)
        return card

    def _make_image_pdf_thumb(self, path):
        if path in self.image_pdf_thumb_cache:
            return self.image_pdf_thumb_cache[path]

        box_w, box_h = 112, 148
        try:
            with Image.open(path) as src:
                img = ImageOps.exif_transpose(src)
                if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                    img = img.convert("RGBA")
                else:
                    img = img.convert("RGB")
                img.thumbnail((box_w, box_h), Image.Resampling.LANCZOS)

                thumb = Image.new("RGB", (box_w, box_h), "#f8f8fb")
                x = (box_w - img.width) // 2
                y = (box_h - img.height) // 2
                if img.mode == "RGBA":
                    thumb.paste(img, (x, y), img.split()[-1])
                else:
                    thumb.paste(img, (x, y))
        except Exception:
            thumb = Image.new("RGB", (box_w, box_h), "#f8f8fb")

        image = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=(box_w, box_h))
        self.image_pdf_thumb_cache[path] = image
        return image

    def _short_image_pdf_name(self, name):
        if len(name) <= 23:
            return name
        root, ext = os.path.splitext(name)
        return f"{root[:18]}...{ext}"

    def _on_image_pdf_card_press(self, index, _event):
        self.image_pdf_drag_index = index

    def _on_image_pdf_card_release(self, event):
        source = self.image_pdf_drag_index
        self.image_pdf_drag_index = None
        if source is None or source >= len(self.image_pdf_files):
            return

        target = self._image_pdf_index_at(event.x_root, event.y_root)
        if target is None or target == source or target >= len(self.image_pdf_files):
            return

        item = self.image_pdf_files.pop(source)
        self.image_pdf_files.insert(target, item)
        self._image_pdf_last_count = None
        self._refresh_image_pdf_gallery()

    def _image_pdf_index_at(self, x_root, y_root):
        widget = self.winfo_containing(x_root, y_root)
        while widget is not None:
            if widget in self.image_pdf_cards:
                return self.image_pdf_cards[widget]
            widget = getattr(widget, "master", None)
        return None

    def _update_image_pdf_count(self):
        count = len(getattr(self, "image_pdf_files", []))
        text = "Sin imágenes en la mesa"
        if count == 1:
            text = "1 imagen seleccionada"
        elif count > 1:
            text = f"{count} imágenes seleccionadas"
        self.image_pdf_count_lbl.configure(text=text)

    def _run_image_pdf_conversion(self):
        page_size = IMAGE_PAGE_SIZE_OPTIONS.get(self.image_pdf_page_size.get(), "A4")
        self.controller.images_to_pdf(
            list(self.image_pdf_files),
            page_size=page_size,
            orientation=self.image_pdf_orientation.get(),
            margin=self.image_pdf_margin.get(),
            merge_output=self.image_pdf_merge.get(),
        )


    # ---------- ROTATE ----------
    def _build_rotate_view(self, parent):
        card = GlassCard(parent, "Rotar PDF")
        card.pack(fill="both", expand=True)

        self.rot_file = tk.StringVar()
        self.rot_angle = tk.IntVar(value=90)

        DropArea(card.inner, "Arrastra PDF", lambda f: self.rot_file.set(f[0] if f else ""), multiple=False).pack(fill="x", pady=10)
        ctk.CTkEntry(card.inner, textvariable=self.rot_file).pack(fill="x", pady=5)

        ctk.CTkLabel(card.inner, text="Ángulo de rotación (horario):").pack(anchor="w", pady=(10, 5))
        ctk.CTkSegmentedButton(card.inner, values=["90", "180", "270"], variable=self.rot_angle).pack(anchor="w")

        ctk.CTkButton(
            card.inner, 
            text="Rotar PDF", 
            command=lambda: self.controller.rotate_pdf(self.rot_file.get(), self.rot_angle.get())
        ).pack(anchor="w", pady=20)


    # ---------- SECURITY (PASSWORD) ----------
    def _build_password_view(self, parent):
        tab = ctk.CTkTabview(parent)
        tab.pack(fill="both", expand=True)
        tab.add("Proteger PDF")
        tab.add("Desbloquear PDF")

        # --- Proteger ---
        lock_p = tab.tab("Proteger PDF")
        self.lock_file = tk.StringVar()
        self.lock_pass = tk.StringVar()

        DropArea(lock_p, "Arrastra PDF para Proteger", lambda f: self.lock_file.set(f[0] if f else ""), multiple=False).pack(fill="x", pady=10)
        ctk.CTkEntry(lock_p, textvariable=self.lock_file, placeholder_text="Archivo...").pack(fill="x", pady=5)
        
        ctk.CTkLabel(lock_p, text="Nueva Contraseña:").pack(anchor="w", pady=(10, 0))
        ctk.CTkEntry(lock_p, textvariable=self.lock_pass, show="*").pack(fill="x", pady=(5, 15))
        
        ctk.CTkButton(
            lock_p, 
            text="Cifrar y Guardar", 
            command=lambda: self.controller.encrypt_pdf(self.lock_file.get(), self.lock_pass.get())
        ).pack(anchor="w")

        # --- Desbloquear ---
        unlock_p = tab.tab("Desbloquear PDF")
        self.pass_file = tk.StringVar()
        self.pass_txt = tk.StringVar()

        DropArea(unlock_p, "Arrastra PDF Protegido", lambda f: self.pass_file.set(f[0] if f else ""), multiple=False).pack(fill="x", pady=10)
        ctk.CTkEntry(unlock_p, textvariable=self.pass_file, placeholder_text="Archivo...").pack(fill="x", pady=5)

        ctk.CTkLabel(unlock_p, text="Contraseña Actual:").pack(anchor="w", pady=(10, 0))
        ctk.CTkEntry(unlock_p, textvariable=self.pass_txt, show="*").pack(fill="x", pady=(5, 15))

        ctk.CTkButton(
            unlock_p, 
            text="Desbloquear PDF", 
            command=lambda: self.controller.remove_password(self.pass_file.get(), self.pass_txt.get())
        ).pack(anchor="w")

    # ---------- METADATA ----------
    def _build_metadata_view(self, parent):
        card = GlassCard(parent, "Editor de Metadatos")
        card.pack(fill="both", expand=True)

        self.meta_file = tk.StringVar()
        self.meta_vars = {
            "title": tk.StringVar(),
            "author": tk.StringVar(),
            "subject": tk.StringVar(),
            "keywords": tk.StringVar(),
            "creator": tk.StringVar()
        }

        def load_meta(files):
            if not files: return
            path = files[0]
            self.meta_file.set(path)
            data = self.controller.get_metadata(path)
            for k, v in self.meta_vars.items():
                v.set(data.get(k, ""))
            self.log("Metadatos cargados")

        DropArea(card.inner, "Arrastra PDF para editar info", load_meta, multiple=False).pack(fill="x", pady=10)
        ctk.CTkEntry(card.inner, textvariable=self.meta_file, placeholder_text="Ruta del archivo...").pack(fill="x", pady=(0, 10))

        # Grid para campos
        fields_frame = ctk.CTkFrame(card.inner, fg_color="transparent")
        fields_frame.pack(fill="x", pady=10)
        fields_frame.grid_columnconfigure(1, weight=1)

        labels = ["Título:", "Autor:", "Asunto:", "Keywords:", "Creador:"]
        keys = ["title", "author", "subject", "keywords", "creator"]

        for i, (lbl_txt, key) in enumerate(zip(labels, keys)):
            ctk.CTkLabel(fields_frame, text=lbl_txt).grid(row=i, column=0, padx=(0, 10), pady=5, sticky="e")
            ctk.CTkEntry(fields_frame, textvariable=self.meta_vars[key]).grid(row=i, column=1, pady=5, sticky="ew")

        def save_meta():
            meta = {k: v.get() for k, v in self.meta_vars.items()}
            self.controller.save_metadata(self.meta_file.get(), meta)

        ctk.CTkButton(card.inner, text="Guardar Cambios", command=save_meta).pack(anchor="w", pady=20)

if __name__ == "__main__":
    # Test run
    pass
