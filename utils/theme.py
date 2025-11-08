# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk

PALETTES = {
    "dark": dict(bg="#0b1220", fg="#e5e7eb", card="#101827", line="#334155",
                 caption="#9aa3af", hint="#7b8794", accent="#1f6feb",
                 accent_active="#3974ff", select="#1f6feb"),
    "light": dict(bg="#f7fafc", fg="#0b1220", card="#ffffff", line="#e2e8f0",
                  caption="#6b7280", hint="#6b7280", accent="#2563eb",
                  accent_active="#3b82f6", select="#2563eb"),
}

def apply_theme(root: tk.Tk, style: ttk.Style, theme_name="dark"):
    p = PALETTES[theme_name]
    root.configure(bg=p["bg"])
    style.configure(".", background=p["bg"], foreground=p["fg"])
    style.configure("Header.TLabel", background=p["bg"], foreground=p["fg"], font=("Segoe UI", 16, "bold"))
    style.configure("Caption.TLabel", foreground=p["caption"], background=p["bg"], font=("Segoe UI", 10))
    style.configure("Hint.TLabel", foreground=p["hint"], background=p["bg"], font=("Segoe UI", 9))

    style.configure("Sidebar.TFrame", background=p["card"])
    style.configure("Sidebar.TButton", padding=12, anchor="w", background=p["card"], foreground=p["fg"])
    style.map("Sidebar.TButton", background=[("active", p["line"])], foreground=[("!disabled", p["fg"])])

    style.configure("Accent.TButton", padding=12, relief="flat", background=p["accent"], foreground=p["fg"])
    style.map("Accent.TButton", background=[("active", p["accent_active"])])

    style.configure("Card.TFrame", relief="flat")
    style.configure("TNotebook", background=p["bg"])
    style.configure("TNotebook.Tab", padding=(12, 6), background=p["card"], foreground=p["fg"])
    style.map("TNotebook.Tab", background=[("selected", p["line"])])

    return p
