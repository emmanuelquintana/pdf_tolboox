# ui/main_view.py
# -*- coding: utf-8 -*-
import os
import subprocess
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from ui.widgets import GlassCard, DropArea, SUPPORTS_DND

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

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class PDFToolboxApp(BaseClass):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.title(f"{APP_NAME} {VERSION}")
        self.geometry("1100x800")
        self.minsize(900, 650)

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
        self.sidebar.grid_rowconfigure(8, weight=1) # Spacer

        lbl = ctk.CTkLabel(self.sidebar, text=APP_NAME, font=ctk.CTkFont(size=20, weight="bold"))
        lbl.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.nav_buttons = {}
        
        btn_config = [
            ("Unir PDF", "MERGE"),
            ("Dividir PDF", "SPLIT"),
            ("Comprimir", "COMPRESS"),
            ("Convertir", "CONVERT"),
            ("Rotar PDF", "ROTATE"),
            ("Seguridad", "PASSWORD")
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
        self.theme_switch.grid(row=9, column=0, padx=20, pady=20, sticky="s")

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

        # Compress
        self.views["COMPRESS"] = self._create_view_frame()
        self._build_compress_view(self.views["COMPRESS"])

        # Convert
        self.views["CONVERT"] = self._create_view_frame()
        self._build_convert_view(self.views["CONVERT"])

        # Rotate
        self.views["ROTATE"] = self._create_view_frame()
        self._build_rotate_view(self.views["ROTATE"])

        # Password
        self.views["PASSWORD"] = self._create_view_frame()
        self._build_password_view(self.views["PASSWORD"])

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

    def _toggle_theme(self):
        mode = "Dark" if self.theme_switch.get() == "Dark" else "Light"
        ctk.set_appearance_mode(mode)

    # ================= VISTAS =================

    # ---------- MERGE ----------
    def _build_merge_view(self, parent):
        card = GlassCard(parent, "Unir PDFs")
        card.pack(fill="both", expand=True)

        listbox = tk.Listbox(
            card.inner, 
            bg="#2b2b2b", 
            fg="white", 
            selectbackground="#3b82f6", 
            relief="flat",
            highlightthickness=0
        )
        listbox.pack(fill="both", expand=True, pady=(0, 10))

        files_state = []

        def update_list():
            listbox.delete(0, tk.END)
            for f in files_state:
                listbox.insert(tk.END, os.path.basename(f))

        def on_drop(files):
            pdfs = [f for f in files if f.lower().endswith(".pdf")]
            if not pdfs: return
            files_state.extend(pdfs)
            update_list()

        DropArea(card.inner, "Arrastra PDFs aquí", on_drop, multiple=True).pack(fill="x", pady=10)

        btn_row = ctk.CTkFrame(card.inner, fg_color="transparent")
        btn_row.pack(fill="x")

        def run_merge():
            self.controller.merge_pdfs(list(files_state))
            files_state.clear()
            update_list()
        
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
        self.i2p_files = []
        
        lbl_count = ctk.CTkLabel(i2p, text="0 imágenes seleccionadas")
        lbl_count.pack(pady=5)

        def on_drop_imgs(files):
            valid = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            self.i2p_files.extend(valid)
            lbl_count.configure(text=f"{len(self.i2p_files)} imágenes seleccionadas")

        DropArea(i2p, "Arrastra Imágenes", on_drop_imgs, multiple=True).pack(fill="x", pady=10)
        
        def clear_imgs():
            self.i2p_files.clear()
            lbl_count.configure(text="0 imágenes seleccionadas")

        btn_row = ctk.CTkFrame(i2p, fg_color="transparent")
        btn_row.pack()
        ctk.CTkButton(btn_row, text="Crear PDF", command=lambda: self.controller.images_to_pdf(list(self.i2p_files))).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="Limpiar", command=clear_imgs, fg_color="transparent", border_width=1).pack(side="left", padx=5)


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


    # ---------- PASSWORD ----------
    def _build_password_view(self, parent):
        card = GlassCard(parent, "Remover Contraseña")
        card.pack(fill="both", expand=True)

        self.pass_file = tk.StringVar()
        self.pass_txt = tk.StringVar()

        DropArea(card.inner, "Arrastra PDF Protegido", lambda f: self.pass_file.set(f[0] if f else ""), multiple=False).pack(fill="x", pady=10)
        ctk.CTkEntry(card.inner, textvariable=self.pass_file, placeholder_text="Archivo...").pack(fill="x", pady=5)

        ctk.CTkLabel(card.inner, text="Contraseña:").pack(anchor="w", pady=(10, 0))
        ctk.CTkEntry(card.inner, textvariable=self.pass_txt, show="*").pack(fill="x", pady=(5, 15))

        ctk.CTkButton(
            card.inner, 
            text="Desbloquear PDF", 
            command=lambda: self.controller.remove_password(self.pass_file.get(), self.pass_txt.get())
        ).pack(anchor="w")

if __name__ == "__main__":
    # Test run
    pass
