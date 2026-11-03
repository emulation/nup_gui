#!/usr/bin/env python3
"""NUP GUI - interfaz grafica para la herramienta de linea de comandos `nup`.

No reimplementa nada: arma los comandos y llama a `nup` por debajo.
Solo usa la libreria estandar (tkinter viene con el instalador de Python en Windows).
"""
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP_VERSION = "1.0"
EXE = "nup.exe" if os.name == "nt" else "nup"
# detecta porcentajes tipo "45%" o "45.2 %" en la salida del programa
PCT_RE = re.compile(r"(?<![\d.])(\d{1,3})(?:\.\d+)?\s*%")

# ---------- paleta ----------
BG = "#0e1018"       # fondo general
SIDE = "#141726"     # barra lateral
CARD = "#1a1e30"     # tarjetas
FIELD = "#12151f"    # campos de texto
BORDER = "#2b3150"
TEXT = "#e9ecff"
MUTED = "#8d96c0"
DIM = "#5f688f"
ACCENT = "#7c5cff"
ACCENT_H = "#9276ff"
CYAN = "#22d3ee"
OK = "#34d399"
ERR = "#f87171"
WARN = "#fbbf24"
TRACK = "#272c47"
LOGBG = "#0a0c13"
BTN2 = "#2a3050"
BTN2_H = "#363e68"

SCALE = 1.0
FAM = "TkDefaultFont"
MONO = "Courier"


def px(n):
    """Escala un tamaño en pixeles segun el DPI de la pantalla."""
    return int(round(n * SCALE))


def find_nup():
    """Busca el ejecutable de nup. Devuelve la lista de comando base."""
    found = shutil.which("nup")
    if found:
        return [os.path.abspath(found)]
    here = Path(sys.argv[0]).resolve().parent
    candidates = [
        Path(sys.executable).parent / EXE,
        here / EXE,
        here / "dist" / EXE,
        here / ".venv" / "Scripts" / EXE,
        here / ".venv" / "bin" / EXE,
    ]
    for c in candidates:
        if c.exists():
            return [str(c)]
    # ultimo recurso: modulo de Python (si nup esta instalado en este Python)
    return [sys.executable, "-m", "nup.cli"]


def rrect(cv, x1, y1, x2, y2, r, **kw):
    """Rectangulo con esquinas redondeadas dibujado en un canvas."""
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    pts = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return cv.create_polygon(pts, smooth=True, **kw)


# ---------- widgets personalizados ----------
class RoundButton(tk.Canvas):
    """Boton redondeado con efecto hover."""

    def __init__(self, parent, text, command, bg_parent, color=ACCENT, hover=ACCENT_H,
                 fg="#ffffff", height=38, size=10, bold=True, min_width=0):
        self.b_font = tkfont.Font(family=FAM, size=size, weight="bold" if bold else "normal")
        self.b_text = text
        self.b_cmd = command
        self.b_color = color
        self.b_hover = hover
        self.b_fg = fg
        self.b_over = False
        self.b_enabled = True
        self.b_w = max(px(min_width), self.b_font.measure(text) + px(36))
        self.b_h = px(height)
        super().__init__(parent, width=self.b_w, height=self.b_h, bg=bg_parent,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonRelease-1>", self._on_release)
        self._draw()

    def _draw(self):
        self.delete("all")
        if not self.b_enabled:
            fill, fg = "#232842", "#626a92"
        elif self.b_over:
            fill, fg = self.b_hover, self.b_fg
        else:
            fill, fg = self.b_color, self.b_fg
        rrect(self, 1, 1, self.b_w - 1, self.b_h - 1, px(10), fill=fill, outline=fill)
        self.create_text(self.b_w / 2, self.b_h / 2, text=self.b_text, fill=fg, font=self.b_font)

    def _on_enter(self, _e):
        self.b_over = True
        self._draw()

    def _on_leave(self, _e):
        self.b_over = False
        self._draw()

    def _on_release(self, e):
        if self.b_enabled and 0 <= e.x <= self.b_w and 0 <= e.y <= self.b_h:
            self.b_cmd()

    def set_enabled(self, flag):
        self.b_enabled = bool(flag)
        self.configure(cursor="hand2" if flag else "arrow")
        self._draw()


class ProgressBar(tk.Canvas):
    """Barra de progreso redondeada: determinada (0-100) o animada."""

    def __init__(self, parent, bg_parent):
        super().__init__(parent, height=px(14), bg=bg_parent, highlightthickness=0, bd=0)
        self.p_value = 0.0
        self.p_color = ACCENT
        self.p_anim = False
        self.p_pos = 0.0
        self.p_dir = 1
        self.p_job = None
        self.bind("<Configure>", lambda _e: self._draw())

    def _draw(self):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 8 or h < 4:
            return
        self.delete("all")
        r = h / 2
        rrect(self, 0, 0, w, h, r, fill=TRACK, outline=TRACK)
        if self.p_anim:
            seg = max(h * 2, w * 0.28)
            x1 = min(max(0, self.p_pos), w - seg)
            rrect(self, x1, 0, x1 + seg, h, r, fill=ACCENT, outline=ACCENT)
        elif self.p_value > 0:
            fw = max(h, w * self.p_value / 100.0)
            rrect(self, 0, 0, fw, h, r, fill=self.p_color, outline=self.p_color)

    def start(self):
        self.p_anim = True
        self.p_pos = 0.0
        self.p_dir = 1
        if self.p_job is None:
            self._tick()

    def _tick(self):
        if not self.p_anim:
            self.p_job = None
            return
        w = max(self.winfo_width(), 50)
        seg = max(px(14) * 2, w * 0.28)
        self.p_pos += self.p_dir * max(3.0, w * 0.012)
        if self.p_pos >= w - seg:
            self.p_pos = w - seg
            self.p_dir = -1
        elif self.p_pos <= 0:
            self.p_pos = 0.0
            self.p_dir = 1
        self._draw()
        self.p_job = self.after(16, self._tick)

    def stop(self):
        self.p_anim = False
        if self.p_job is not None:
            try:
                self.after_cancel(self.p_job)
            except Exception:  # noqa: BLE001
                pass
            self.p_job = None

    def set(self, value, color=ACCENT):
        self.stop()
        self.p_value = float(value)
        self.p_color = color
        self._draw()

    def reset(self):
        self.set(0)


class NavButton(tk.Frame):
    """Elemento de la barra lateral."""

    def __init__(self, parent, icon, text, command):
        super().__init__(parent, bg=SIDE, cursor="hand2")
        self.n_cmd = command
        self.n_active = False
        self.n_bar = tk.Frame(self, width=px(4), bg=SIDE)
        self.n_bar.pack(side="left", fill="y")
        self.n_lbl = tk.Label(self, text=f"{icon}   {text}", bg=SIDE, fg=MUTED,
                              font=(FAM, 11), anchor="w", padx=px(14), pady=px(11))
        self.n_lbl.pack(side="left", fill="x", expand=True)
        for w in (self, self.n_lbl, self.n_bar):
            w.bind("<Enter>", self._enter)
            w.bind("<Leave>", self._leave)
            w.bind("<Button-1>", lambda _e: self.n_cmd())

    def _paint(self, bg, fg, bar, bold):
        self.configure(bg=bg)
        self.n_lbl.configure(bg=bg, fg=fg, font=(FAM, 11, "bold" if bold else "normal"))
        self.n_bar.configure(bg=bar)

    def _enter(self, _e):
        if not self.n_active:
            self._paint("#1b2038", TEXT, "#1b2038", False)

    def _leave(self, _e):
        if not self.n_active:
            self._paint(SIDE, MUTED, SIDE, False)

    def set_active(self, flag):
        self.n_active = flag
        if flag:
            self._paint("#1f2547", TEXT, ACCENT, True)
        else:
            self._paint(SIDE, MUTED, SIDE, False)


# ---------- aplicacion ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        global SCALE, FAM, MONO
        try:
            SCALE = max(1.0, float(self.winfo_fpixels("1i")) / 96.0)
        except Exception:  # noqa: BLE001
            SCALE = 1.0
        fams = set(tkfont.families())
        FAM = next((f for f in ("Segoe UI", "Inter", "Helvetica Neue", "Ubuntu", "DejaVu Sans") if f in fams),
                   "TkDefaultFont")
        MONO = next((f for f in ("Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Menlo") if f in fams),
                    "Courier")

        self.title(f"NUP GUI v{APP_VERSION}")
        self.geometry(f"{px(1080)}x{px(800)}")
        self.minsize(px(940), px(720))
        self.configure(bg=BG)

        self.q = queue.Queue()
        self.proc = None
        self.running = False
        self.stopped = False
        self.run_buttons = []
        self.t_start = None
        self.t_end = None
        self.pct_seen = False
        self.last_pct = 0
        self.pages = {}
        self.navs = {}

        self._style()
        self._build()
        self.show_page("pack")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(60, self._poll)

    # ---------- estilos ttk ----------
    def _style(self):
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("Dark.TCombobox", fieldbackground=FIELD, background=BORDER, foreground=TEXT,
                     arrowcolor=TEXT, bordercolor=BORDER, lightcolor=FIELD, darkcolor=FIELD,
                     selectbackground=FIELD, selectforeground=TEXT, padding=px(4))
        st.map("Dark.TCombobox",
               fieldbackground=[("readonly", FIELD), ("disabled", FIELD)],
               foreground=[("readonly", TEXT)],
               selectbackground=[("readonly", FIELD)],
               selectforeground=[("readonly", TEXT)],
               bordercolor=[("focus", ACCENT)],
               arrowcolor=[("active", ACCENT)])
        self.option_add("*TCombobox*Listbox.background", FIELD)
        self.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        self.option_add("*TCombobox*Listbox.font", (FAM, 10))
        try:
            st.configure("Dark.Vertical.TScrollbar", background=BTN2, troughcolor=LOGBG,
                         bordercolor=LOGBG, lightcolor=BTN2, darkcolor=BTN2, gripcount=0)
            st.map("Dark.Vertical.TScrollbar", background=[("active", ACCENT)])
            st.layout("Dark.Vertical.TScrollbar", [
                ("Vertical.Scrollbar.trough", {
                    "sticky": "ns",
                    "children": [("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})],
                })
            ])
        except tk.TclError:
            pass

    # ---------- construccion ----------
    def _card(self, parent, pad=16):
        outer = tk.Frame(parent, bg=BORDER)
        inner = tk.Frame(outer, bg=CARD)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        body = tk.Frame(inner, bg=CARD)
        body.pack(fill="both", expand=True, padx=px(pad), pady=px(pad))
        return outer, body

    def _build(self):
        # --- barra lateral ---
        self.side = tk.Frame(self, bg=SIDE, width=px(230))
        self.side.pack(side="left", fill="y")
        self.side.pack_propagate(False)

        tk.Label(self.side, text=f"v{APP_VERSION}", bg=SIDE, fg=DIM, font=(FAM, 9)).pack(
            side="bottom", pady=px(14))
        logo = tk.Frame(self.side, bg=SIDE)
        logo.pack(fill="x", padx=px(22), pady=(px(26), px(22)))
        tk.Label(logo, text="NUP", bg=SIDE, fg=TEXT, font=(FAM, 28, "bold"), anchor="w").pack(fill="x")
        tk.Label(logo, text="NX Package Tool", bg=SIDE, fg=ACCENT_H, font=(FAM, 10), anchor="w").pack(fill="x")
        tk.Frame(self.side, bg=BORDER, height=1).pack(fill="x", padx=px(18), pady=(0, px(12)))

        # --- zona principal ---
        main = tk.Frame(self, bg=BG)
        main.pack(side="left", fill="both", expand=True, padx=px(18), pady=px(16))

        # programa nup
        c1, b1 = self._card(main, pad=12)
        c1.pack(fill="x")
        tk.Label(b1, text="PROGRAMA NUP", bg=CARD, fg=MUTED, font=(FAM, 8, "bold")).pack(side="left", padx=(0, px(12)))
        auto = find_nup()
        self.nup_var = tk.StringVar(value=auto[0] if len(auto) == 1 else "")
        e = self._entry(b1, self.nup_var)
        e.pack(side="left", fill="x", expand=True, ipady=px(6))
        RoundButton(b1, "Examinar", self._browse_nup, CARD, color=BTN2, hover=BTN2_H,
                    height=32, size=9, bold=False).pack(side="left", padx=(px(8), 0))

        # paginas
        c2, b2 = self._card(main, pad=18)
        c2.pack(fill="x", pady=(px(12), 0))
        self.page_host = tk.Frame(b2, bg=CARD)
        self.page_host.pack(fill="x")
        self.page_host.grid_columnconfigure(0, weight=1)
        self.page_host.grid_rowconfigure(0, weight=1)

        self._page_pack()
        self._page_extract()
        self._page_list()
        self._page_info()
        self._page_verify()

        # progreso + tiempos
        c3, b3 = self._card(main, pad=14)
        c3.pack(fill="x", pady=(px(12), 0))
        top = tk.Frame(b3, bg=CARD)
        top.pack(fill="x")
        self.status_lbl = tk.Label(top, text="Listo.", bg=CARD, fg=TEXT, font=(FAM, 11, "bold"), anchor="w")
        self.status_lbl.pack(side="left")
        self.pct_var = tk.StringVar(value="")
        tk.Label(top, textvariable=self.pct_var, bg=CARD, fg=ACCENT_H, font=(FAM, 11, "bold")).pack(side="right")
        self.pbar = ProgressBar(b3, CARD)
        self.pbar.pack(fill="x", pady=(px(8), px(10)))
        chips = tk.Frame(b3, bg=CARD)
        chips.pack(fill="x")
        self.t_in = tk.StringVar()
        self.t_out = tk.StringVar()
        self.t_dur = tk.StringVar()
        self._chip(chips, "INICIO", self.t_in, first=True)
        self._chip(chips, "FIN", self.t_out)
        self._chip(chips, "DURACIÓN", self.t_dur)
        self._reset_times()

        # salida
        c4, b4 = self._card(main, pad=12)
        c4.pack(fill="both", expand=True, pady=(px(12), 0))
        head = tk.Frame(b4, bg=CARD)
        head.pack(fill="x", pady=(0, px(8)))
        tk.Label(head, text="SALIDA", bg=CARD, fg=MUTED, font=(FAM, 8, "bold")).pack(side="left")
        RoundButton(head, "Limpiar", self._clear_log, CARD, color=BTN2, hover=BTN2_H,
                    height=30, size=9, bold=False).pack(side="right")
        self.stop_btn = RoundButton(head, "Detener", self._stop, CARD, color="#4a2433", hover="#65304a",
                                    fg=ERR, height=30, size=9, bold=False)
        self.stop_btn.pack(side="right", padx=(0, px(8)))
        self.stop_btn.set_enabled(False)

        box = tk.Frame(b4, bg=LOGBG)
        box.pack(fill="both", expand=True)
        self.log = tk.Text(box, wrap="word", state="disabled", height=8, bg=LOGBG, fg="#cdd5ff",
                           insertbackground=TEXT, relief="flat", bd=0, highlightthickness=0,
                           padx=px(12), pady=px(10), font=(MONO, 10), selectbackground="#3a3f6b")
        sb = ttk.Scrollbar(box, command=self.log.yview, style="Dark.Vertical.TScrollbar")
        self.log.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log.pack(side="left", fill="both", expand=True)
        self.log.tag_configure("cmd", foreground=CYAN, font=(MONO, 10, "bold"))
        self.log.tag_configure("info", foreground=MUTED)
        self.log.tag_configure("ok", foreground=OK)
        self.log.tag_configure("err", foreground=ERR)
        self.log.tag_configure("warn", foreground=WARN)

    def _chip(self, parent, caption, var, first=False):
        outer = tk.Frame(parent, bg=BORDER)
        outer.pack(side="left", fill="x", expand=True, padx=(0 if first else px(10), 0))
        inner = tk.Frame(outer, bg=FIELD)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Label(inner, text=caption, bg=FIELD, fg=DIM, font=(FAM, 8, "bold"), anchor="w").pack(
            fill="x", padx=px(12), pady=(px(6), 0))
        tk.Label(inner, textvariable=var, bg=FIELD, fg=TEXT, font=(FAM, 13, "bold"), anchor="w").pack(
            fill="x", padx=px(12), pady=(0, px(6)))

    def _reset_times(self):
        self.t_in.set("--:--:--")
        self.t_out.set("--:--:--")
        self.t_dur.set("00:00:00")

    # ---------- helpers de formulario ----------
    def _entry(self, parent, var):
        return tk.Entry(parent, textvariable=var, bg=FIELD, fg=TEXT, insertbackground=TEXT,
                        relief="flat", bd=0, highlightthickness=1, highlightbackground=BORDER,
                        highlightcolor=ACCENT, font=(FAM, 10), disabledbackground=FIELD,
                        selectbackground=ACCENT, selectforeground="#ffffff")

    def _label_row(self, parent, label, hint=""):
        top = tk.Frame(parent, bg=CARD)
        top.pack(fill="x")
        tk.Label(top, text=label, bg=CARD, fg=MUTED, font=(FAM, 9)).pack(side="left")
        if hint:
            tk.Label(top, text=hint, bg=CARD, fg=DIM, font=(FAM, 8)).pack(side="right")

    def _field(self, parent, label, var, browse=None, save=False, hint=""):
        f = tk.Frame(parent, bg=CARD)
        f.pack(fill="x", pady=(0, px(10)))
        self._label_row(f, label, hint)
        row = tk.Frame(f, bg=CARD)
        row.pack(fill="x", pady=(px(4), 0))
        e = self._entry(row, var)
        e.pack(side="left", fill="x", expand=True, ipady=px(7))
        if browse:
            RoundButton(row, "Examinar", lambda: self._browse(var, browse, save), CARD,
                        color=BTN2, hover=BTN2_H, height=34, size=9, bold=False).pack(
                side="left", padx=(px(8), 0))
        return e

    def _combo(self, parent, label, var, values, readonly=True, hint="", width=18):
        f = tk.Frame(parent, bg=CARD)
        f.pack(fill="x", pady=(0, px(10)))
        self._label_row(f, label, hint)
        cb = ttk.Combobox(f, textvariable=var, values=values, state="readonly" if readonly else "normal",
                          style="Dark.TCombobox", width=width, font=(FAM, 10))
        cb.pack(fill="x", pady=(px(4), 0), ipady=px(4))
        return cb

    def _check(self, parent, text, var):
        c = tk.Checkbutton(parent, text=text, variable=var, bg=CARD, fg=TEXT, selectcolor=FIELD,
                           activebackground=CARD, activeforeground=TEXT, relief="flat", bd=0,
                           highlightthickness=0, font=(FAM, 10), cursor="hand2", anchor="w")
        c.pack(fill="x", pady=(0, px(10)))
        return c

    def _columns(self, parent, n):
        cols = tk.Frame(parent, bg=CARD)
        cols.pack(fill="x")
        out = []
        for i in range(n):
            c = tk.Frame(cols, bg=CARD)
            c.pack(side="left", fill="x", expand=True, padx=(0, px(12) if i < n - 1 else 0))
            out.append(c)
        return out

    def _action(self, parent, text, cmd):
        b = RoundButton(parent, text, cmd, CARD, color=ACCENT, hover=ACCENT_H, height=42, size=11, min_width=170)
        b.pack(anchor="w", pady=(px(6), 0))
        self.run_buttons.append(b)
        return b

    def _make_page(self, key, icon, title, desc):
        page = tk.Frame(self.page_host, bg=CARD)
        page.grid(row=0, column=0, sticky="nsew")
        tk.Label(page, text=title, bg=CARD, fg=TEXT, font=(FAM, 17, "bold"), anchor="w").pack(fill="x")
        tk.Label(page, text=desc, bg=CARD, fg=MUTED, font=(FAM, 10), anchor="w", justify="left").pack(
            fill="x", pady=(px(2), px(14)))
        nav = NavButton(self.side, icon, title, lambda k=key: self.show_page(k))
        nav.pack(fill="x", pady=px(1))
        self.pages[key] = page
        self.navs[key] = nav
        return page

    def show_page(self, key):
        self.pages[key].tkraise()
        for k, n in self.navs.items():
            n.set_active(k == key)

    # ---------- paginas ----------
    def _page_pack(self):
        p = self._make_page("pack", "▣", "Empaquetar",
                            "Convierte una carpeta de dump (base, updates, DLC) en un único archivo .nup comprimido.")
        self.p_dir = tk.StringVar()
        self.p_out = tk.StringVar()
        self.p_level = tk.StringVar(value="(predeterminado)")
        self.p_tid = tk.StringVar()
        self.p_ver = tk.StringVar()
        self._field(p, "Carpeta del dump", self.p_dir, browse="dir")
        self._field(p, "Guardar como (.nup)", self.p_out, browse="file", save=True)
        c1, c2, c3 = self._columns(p, 3)
        self._combo(c1, "Nivel de compresión", self.p_level,
                    ["(predeterminado)"] + [str(n) for n in range(1, 11)], hint="1 rápido · 10 pequeño")
        self._field(c2, "Title ID (hex)", self.p_tid, hint="opcional")
        self._field(c3, "Versión visible", self.p_ver, hint="opcional")
        self._action(p, "Empaquetar", self._do_pack)
        self.p_dir.trace_add("write", self._suggest_out)

    def _suggest_out(self, *_):
        d = self.p_dir.get().strip().rstrip("/\\")
        if d and not self.p_out.get().strip():
            self.p_out.set(d + ".nup")

    def _do_pack(self):
        d, o = self.p_dir.get().strip(), self.p_out.get().strip()
        if not d or not o:
            return self._need("la carpeta del dump y el archivo de salida")
        args = ["pack", d, o]
        if self.p_level.get().strip().isdigit():
            args += ["--level", self.p_level.get().strip()]
        if self.p_tid.get().strip():
            args += ["--title-id", self.p_tid.get().strip()]
        if self.p_ver.get().strip():
            args += ["--display-version", self.p_ver.get().strip()]
        self._run(args)

    def _page_extract(self):
        p = self._make_page("extract", "⇩", "Desempaquetar",
                            "Extrae el contenido de un .nup a una carpeta, completo o solo una parte.")
        self.e_file = tk.StringVar()
        self.e_dest = tk.StringVar()
        self.e_pkg = tk.StringVar(value="(todos)")
        self.e_sub = tk.StringVar()
        self._field(p, "Archivo .nup", self.e_file, browse="open")
        self._field(p, "Carpeta destino", self.e_dest, browse="dir")
        c1, c2 = self._columns(p, 2)
        self._combo(c1, "Paquete", self.e_pkg, ["(todos)", "base", "update", "addon"])
        self._combo(c2, "Solo subcarpeta", self.e_sub, ["", "romfs", "exefs"], readonly=False, hint="opcional")
        self._action(p, "Desempaquetar", self._do_extract)

    def _do_extract(self):
        f, d = self.e_file.get().strip(), self.e_dest.get().strip()
        if not f or not d:
            return self._need("el archivo .nup y la carpeta destino")
        args = ["extract", f, d]
        if self.e_pkg.get() in ("base", "update", "addon"):
            args += ["--package", self.e_pkg.get()]
        if self.e_sub.get().strip():
            args += ["--subtree", self.e_sub.get().strip()]
        self._run(args)

    def _page_list(self):
        p = self._make_page("list", "☰", "Listar", "Muestra todos los archivos que contiene un .nup.")
        self.l_file = tk.StringVar()
        self._field(p, "Archivo .nup", self.l_file, browse="open")
        self._action(p, "Listar archivos", self._do_list)

    def _do_list(self):
        f = self.l_file.get().strip()
        if not f:
            return self._need("el archivo .nup")
        self._run(["list", f])

    def _page_info(self):
        p = self._make_page("info", "ⓘ", "Info", "Muestra la información general del contenedor: paquetes y metadatos.")
        self.i_file = tk.StringVar()
        self.i_tree = tk.BooleanVar(value=False)
        self._field(p, "Archivo .nup", self.i_file, browse="open")
        self._check(p, "Mostrar árbol de archivos (--tree)", self.i_tree)
        self._action(p, "Ver info", self._do_info)

    def _do_info(self):
        f = self.i_file.get().strip()
        if not f:
            return self._need("el archivo .nup")
        args = ["info", f]
        if self.i_tree.get():
            args.append("--tree")
        self._run(args)

    def _page_verify(self):
        p = self._make_page("verify", "✔", "Verificar",
                            "Comprueba la integridad: estructura del contenedor y SHA-256 de cada archivo.")
        self.v_file = tk.StringVar()
        self.v_fast = tk.BooleanVar(value=False)
        self._field(p, "Archivo .nup", self.v_file, browse="open")
        self._check(p, "Verificación rápida (--fast)", self.v_fast)
        self._action(p, "Verificar", self._do_verify)

    def _do_verify(self):
        f = self.v_file.get().strip()
        if not f:
            return self._need("el archivo .nup")
        args = ["verify", f]
        if self.v_fast.get():
            args.append("--fast")
        self._run(args)

    # ---------- utilidades de UI ----------
    def _browse(self, var, kind, save):
        if kind == "dir":
            p = filedialog.askdirectory()
        elif save:
            p = filedialog.asksaveasfilename(
                defaultextension=".nup", filetypes=[("NUP", "*.nup"), ("Todos", "*.*")])
        else:
            p = filedialog.askopenfilename(filetypes=[("NUP", "*.nup"), ("Todos", "*.*")])
        if p:
            var.set(os.path.normpath(p))

    def _browse_nup(self):
        p = filedialog.askopenfilename(
            filetypes=[("Ejecutable", "*.exe" if os.name == "nt" else "*"), ("Todos", "*.*")])
        if p:
            self.nup_var.set(os.path.normpath(p))

    def _need(self, what):
        messagebox.showwarning("Faltan datos", f"Indica {what}.")

    def _write(self, text, tag=None):
        self.log.configure(state="normal")
        if tag:
            self.log.insert("end", text, tag)
        else:
            self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_status(self, text, color=TEXT):
        self.status_lbl.configure(text=text, fg=color)

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        if not self.running:
            # sin nada ejecutándose: limpiar también estado, barra y tiempos
            self._set_status("Listo.", TEXT)
            self.pbar.reset()
            self.pct_var.set("")
            self.t_start = None
            self.t_end = None
            self.pct_seen = False
            self.last_pct = 0
            self._reset_times()

    def _set_busy(self, busy):
        self.running = busy
        for b in self.run_buttons:
            b.set_enabled(not busy)
        self.stop_btn.set_enabled(busy)

    def _on_close(self):
        try:
            if self.proc and self.proc.poll() is None:
                self.proc.terminate()
        except Exception:  # noqa: BLE001
            pass
        self.destroy()

    # ---------- ejecucion ----------
    def _base_cmd(self):
        custom = self.nup_var.get().strip().strip('"')
        return [custom] if custom else [sys.executable, "-m", "nup.cli"]

    def _run(self, args):
        if self.running:
            return
        cmd = self._base_cmd() + args
        if self.log.get("1.0", "end-1c").strip():
            self._write("\n")
        self._write("$ " + subprocess.list2cmdline(cmd) + "\n", "cmd")
        self._set_status("Ejecutando…", CYAN)
        self._set_busy(True)
        self.stopped = False
        self.t_start = datetime.now()
        self.t_end = None
        self.pct_seen = False
        self.last_pct = 0
        self.pct_var.set("")
        self.pbar.start()
        self._write(f"[inicio {self.t_start:%H:%M:%S}]\n", "info")
        self._refresh_time()
        threading.Thread(target=self._worker, args=(cmd,), daemon=True).start()

    def _worker(self, cmd):
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            self.proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                encoding="utf-8", errors="replace", env=env, creationflags=flags)
            for line in self.proc.stdout:
                self.q.put(("out", line))
            self.q.put(("done", self.proc.wait()))
        except Exception as e:  # noqa: BLE001
            self.q.put(("out", f"Error al ejecutar: {e}\n"))
            self.q.put(("done", -1))

    def _stop(self):
        if self.proc and self.proc.poll() is None:
            self.stopped = True
            self.proc.terminate()
            self._write("[detenido por el usuario]\n", "warn")

    def _poll(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "out":
                    low = val.lower()
                    tag = "err" if ("error" in low or "traceback" in low or "exception" in low) else None
                    self._write(val, tag)
                    for m in PCT_RE.finditer(val):
                        if int(m.group(1)) <= 100:
                            self._set_pct(int(m.group(1)))
                else:
                    self._finish(val)
        except queue.Empty:
            pass
        if self.running:
            self._refresh_time()
        self.after(60, self._poll)

    def _set_pct(self, pct):
        self.pct_seen = True
        self.last_pct = pct
        self.pbar.set(pct, ACCENT)
        self.pct_var.set(f"{pct}%")

    def _finish(self, code):
        self.t_end = datetime.now()
        self._set_busy(False)
        if code == 0:
            self.pbar.set(100, OK)
            self.pct_var.set("100%")
            self._set_status("Terminado correctamente.", OK)
            tag = "ok"
        elif self.stopped:
            self.pbar.set(self.last_pct if self.pct_seen else 0, WARN)
            self._set_status("Detenido por el usuario.", WARN)
            tag = "warn"
        else:
            self.pbar.set(self.last_pct if self.pct_seen else 0, ERR)
            self._set_status(f"Terminó con error (código {code}).", ERR)
            tag = "err"
        self._refresh_time()
        self._write(f"[fin {self.t_end:%H:%M:%S} - duración {self._duration()}]\n", tag)

    def _duration(self):
        if not self.t_start:
            return "00:00:00"
        end = self.t_end or datetime.now()
        secs = int((end - self.t_start).total_seconds())
        h, r = divmod(secs, 3600)
        m, s = divmod(r, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _refresh_time(self):
        if not self.t_start:
            return
        self.t_in.set(f"{self.t_start:%H:%M:%S}")
        self.t_out.set(f"{self.t_end:%H:%M:%S}" if self.t_end else "--:--:--")
        self.t_dur.set(self._duration())


def main():
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:  # noqa: BLE001
            pass
    App().mainloop()


if __name__ == "__main__":
    main()
