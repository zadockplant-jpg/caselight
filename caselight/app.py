from __future__ import annotations

import os
import subprocess
import sys
import time
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk
from tkinter import font as tkfont
from typing import Any

from .engine import LightingEngine
from .model import (
    APP_NAME,
    APP_VERSION,
    BEAT_DIVISIONS,
    CHANNELS,
    COLOR_PRESETS,
    EFFECTS,
    MODES,
    MUSIC_STYLES,
    SPEEDS,
    THEMES,
    ZONES,
    clamp_number,
    normalize_hex,
)
from .startup import is_start_with_system_enabled, set_start_with_system
from .storage import StateStore

BASE = "#00212B"
BLACK = "#000000"
PANEL = "#101010"
PANEL_ALT = "#181818"
WHITE = "#FFFFFF"
MUTED = "#A0A0A0"
DIM = "#686868"
BORDER = "#303030"
CYAN = "#00E5FF"
VIOLET = "#8A5CFF"
PINK = "#FF2BA6"
RED = "#FF253A"


class CaseLightApp(tk.Tk):
    def __init__(self, *, minimized: bool = False, state_directory: Path | None = None) -> None:
        super().__init__(className=APP_NAME)
        self.store = StateStore(state_directory)
        self.state = self.store.load()
        self.title(f"{APP_NAME} • case lighting studio")
        self._set_window_icon()
        saved_geometry = self.state["window_geometry"]
        self.geometry("1180x760" if saved_geometry == "auto" else saved_geometry)
        self.minsize(980, 680)
        self.configure(bg=BASE)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._save_after: str | None = None
        self._brightness_after: str | None = None
        self._tap_times: list[float] = []
        self._nav_buttons: dict[str, ttk.Button] = {}
        self._pages: dict[str, ttk.Frame] = {}
        self._zone_vars: dict[str, dict[str, tk.StringVar]] = {}
        self._zone_swatches: dict[str, tk.Canvas] = {}
        self._meter_items: list[int] = []
        self._theme_buttons: dict[str, tk.Button] = {}
        self.status_var = tk.StringVar(value="Ready")
        self.status_detail_var = tk.StringVar(value="Shared state connected")
        self._create_variables()
        self._configure_styles()
        self._build_shell()
        self.engine = LightingEngine(
            self.state,
            self._save_state,
            self.store.directory,
            self._set_status,
            self._update_music_meter,
            lambda callback: self.after(0, callback),
        )
        if saved_geometry == "auto":
            self.after_idle(self._fit_initial_window)
        self.show_page("Home")
        self.after(250, self._ensure_current_os_startup)
        if self.state["restore_on_startup"]:
            self.after(900, self.engine.restore)
        if minimized:
            self.after(100, self.iconify)

    def _set_window_icon(self) -> None:
        resource_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
        icon_path = resource_root / "assets" / "caselight.png"
        try:
            self._window_icon = tk.PhotoImage(file=icon_path)
            self.iconphoto(True, self._window_icon)
        except tk.TclError:
            self._window_icon = None

    def _create_variables(self) -> None:
        state = self.state
        self.brightness_var = tk.DoubleVar(value=state["brightness"])
        self.brightness_label_var = tk.StringVar(value=f"{state['brightness']}%")
        self.restore_var = tk.BooleanVar(value=state["restore_on_startup"])
        self.startup_var = tk.BooleanVar(value=state["start_with_system"])
        self.theme_var = tk.StringVar(value=state["theme"])
        self.solid_var = tk.StringVar(value=f"#{state['solid_color']}")
        self.effect_var = tk.StringVar(value=state["effect"])
        self.bpm_var = tk.IntVar(value=state["tempo_bpm"])
        self.bpm_label_var = tk.StringVar(value=f"{state['tempo_bpm']} BPM")
        self.division_var = tk.StringVar(value=state["beat_division"])
        self.animation_fps_var = tk.IntVar(value=state["animation_fps"])
        music = state["music"]
        self.music_style_var = tk.StringVar(value=music["style"])
        self.sensitivity_var = tk.IntVar(value=music["sensitivity"])
        self.smoothing_var = tk.IntVar(value=music["smoothing"])
        self.minimum_glow_var = tk.IntVar(value=music["minimum_glow"])
        self.music_fps_var = tk.IntVar(value=music["fps"])
        self.bass_gain_var = tk.IntVar(value=music["bass_gain"])
        self.mid_gain_var = tk.IntVar(value=music["mid_gain"])
        self.treble_gain_var = tk.IntVar(value=music["treble_gain"])
        self.timer_minutes_var = tk.StringVar(value="15")
        self.timer_action_var = tk.StringVar(value="Turn off")
        self.data_path_var = tk.StringVar(value=str(self.store.directory))
        self.data_reason_var = tk.StringVar(value=self.store.location_reason)

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=BASE, foreground=WHITE, font=("Segoe UI", 10))
        style.configure("App.TFrame", background=BASE)
        style.configure("Sidebar.TFrame", background=BLACK)
        style.configure("Page.TFrame", background=BASE)
        style.configure("Card.TFrame", background=PANEL, relief="flat")
        style.configure("CardAlt.TFrame", background=PANEL_ALT, relief="flat")
        style.configure("TLabel", background=BASE, foreground=WHITE)
        style.configure("Muted.TLabel", background=BASE, foreground=MUTED)
        style.configure("Card.TLabel", background=PANEL, foreground=WHITE)
        style.configure("CardMuted.TLabel", background=PANEL, foreground=MUTED)
        style.configure("Title.TLabel", background=BASE, foreground=WHITE, font=("Segoe UI", 22, "bold"))
        style.configure("Hero.TLabel", background=PANEL, foreground=WHITE, font=("Segoe UI", 18, "bold"))
        style.configure("Section.TLabel", background=BASE, foreground=WHITE, font=("Segoe UI", 14, "bold"))
        style.configure("CardTitle.TLabel", background=PANEL, foreground=WHITE, font=("Segoe UI", 12, "bold"))
        style.configure("SidebarTitle.TLabel", background=BLACK, foreground=WHITE, font=("Segoe UI", 16, "bold"))
        style.configure("SidebarMeta.TLabel", background=BLACK, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("TButton", background=PANEL_ALT, foreground=WHITE, borderwidth=0, padding=(14, 9))
        style.map("TButton", background=[("active", VIOLET), ("pressed", PINK)], foreground=[("disabled", DIM)])
        style.configure("Accent.TButton", background=CYAN, foreground=BLACK, font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", WHITE), ("pressed", VIOLET)])
        style.configure("Danger.TButton", background=PINK, foreground=WHITE, font=("Segoe UI", 10, "bold"))
        style.map("Danger.TButton", background=[("active", RED)])
        style.configure("Nav.TButton", background=BLACK, foreground=MUTED, anchor="w", padding=(18, 12))
        style.map("Nav.TButton", background=[("active", PANEL_ALT)], foreground=[("active", WHITE)])
        style.configure(
            "NavActive.TButton",
            background=BASE,
            foreground=CYAN,
            anchor="w",
            padding=(18, 12),
            font=("Segoe UI", 10, "bold"),
        )
        style.configure("TCheckbutton", background=PANEL, foreground=WHITE, padding=4)
        style.map(
            "TCheckbutton",
            background=[("active", PANEL)],
            indicatorcolor=[("selected", CYAN), ("!selected", PANEL_ALT)],
        )
        style.configure(
            "TCombobox",
            fieldbackground=BLACK,
            background=PANEL_ALT,
            foreground=WHITE,
            arrowcolor=CYAN,
            bordercolor=BORDER,
            padding=6,
        )
        style.map("TCombobox", fieldbackground=[("readonly", BLACK)], foreground=[("readonly", WHITE)])
        style.configure(
            "TEntry", fieldbackground=BLACK, foreground=WHITE, insertcolor=WHITE, bordercolor=BORDER, padding=7
        )
        style.configure(
            "Horizontal.TScale", background=PANEL, troughcolor=BLACK, bordercolor=PANEL, lightcolor=CYAN, darkcolor=CYAN
        )

    def _build_shell(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        sidebar_width = max(205, tkfont.Font(self, family="Segoe UI", size=16, weight="bold").measure("CASELIGHT") + 40)
        sidebar = ttk.Frame(self, style="Sidebar.TFrame", width=sidebar_width)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.pack_propagate(False)
        ttk.Label(sidebar, text="CASELIGHT", style="SidebarTitle.TLabel").pack(anchor="w", padx=20, pady=(25, 0))
        ttk.Label(sidebar, text=f"LIGHTING STUDIO  •  {APP_VERSION}", style="SidebarMeta.TLabel").pack(
            anchor="w", padx=20, pady=(2, 24)
        )
        for name, glyph in (
            ("Home", "◆"),
            ("Effects", "◉"),
            ("Music", "▥"),
            ("Zones", "▦"),
            ("Timer", "◷"),
            ("Settings", "⚙"),
        ):
            button = ttk.Button(
                sidebar, text=f"{glyph}   {name}", style="Nav.TButton", command=lambda page=name: self.show_page(page)
            )
            button.pack(fill="x", padx=(8, 0), pady=2)
            self._nav_buttons[name] = button
        ttk.Frame(sidebar, style="Sidebar.TFrame").pack(fill="both", expand=True)
        ttk.Label(sidebar, text="048D : 5711", style="SidebarMeta.TLabel").pack(anchor="w", padx=20)
        ttk.Label(sidebar, text="RGB FUSION 2.0", style="SidebarMeta.TLabel").pack(anchor="w", padx=20, pady=(2, 22))

        main = ttk.Frame(self, style="App.TFrame", padding=(24, 18, 24, 12))
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)
        header = ttk.Frame(main, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        header.columnconfigure(0, weight=1)
        self.page_title_var = tk.StringVar(value="Home")
        ttk.Label(header, textvariable=self.page_title_var, style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(header, text="DETECT", command=lambda: self.engine.detect()).grid(row=0, column=1, padx=(10, 0))
        ttk.Button(header, text="ALL ON", style="Accent.TButton", command=self._restore_now).grid(
            row=0, column=2, padx=(10, 0)
        )
        ttk.Button(header, text="ALL OFF", style="Danger.TButton", command=lambda: self.engine.power_off()).grid(
            row=0, column=3, padx=(10, 0)
        )

        page_host = ttk.Frame(main, style="App.TFrame")
        page_host.grid(row=1, column=0, sticky="nsew")
        page_host.columnconfigure(0, weight=1)
        page_host.rowconfigure(0, weight=1)
        for name, builder in (
            ("Home", self._build_home),
            ("Effects", self._build_effects),
            ("Music", self._build_music),
            ("Zones", self._build_zones),
            ("Timer", self._build_timer),
            ("Settings", self._build_settings),
        ):
            container = ttk.Frame(page_host, style="Page.TFrame")
            container.grid(row=0, column=0, sticky="nsew")
            container.columnconfigure(0, weight=1)
            container.rowconfigure(0, weight=1)
            canvas = tk.Canvas(container, bg=BASE, bd=0, highlightthickness=0)
            scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.grid(row=0, column=0, sticky="nsew")
            scrollbar.grid(row=0, column=1, sticky="ns")
            page = ttk.Frame(canvas, style="Page.TFrame")
            window_item = canvas.create_window((0, 0), window=page, anchor="nw")
            page.bind("<Configure>", lambda _event, target=canvas: target.configure(scrollregion=target.bbox("all")))
            canvas.bind(
                "<Configure>",
                lambda event, target=canvas, item=window_item: target.itemconfigure(item, width=event.width),
            )
            canvas.bind("<Enter>", lambda _event, target=canvas: self._bind_page_scroll(target))
            canvas.bind("<Leave>", lambda _event: self._unbind_page_scroll())
            self._pages[name] = container
            builder(page)

        status = ttk.Frame(main, style="App.TFrame")
        status.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        self.status_dot = tk.Canvas(status, width=10, height=10, bg=BASE, bd=0, highlightthickness=0)
        self.status_dot.pack(side="left", padx=(0, 8))
        self.status_dot_item = self.status_dot.create_oval(1, 1, 9, 9, fill=CYAN, outline="")
        ttk.Label(status, textvariable=self.status_var).pack(side="left")
        ttk.Label(status, textvariable=self.status_detail_var, style="Muted.TLabel").pack(side="right")

    def _fit_initial_window(self) -> None:
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = min(round(screen_width * 0.92), max(1180, min(1900, round(screen_width * 0.66))))
        height = min(round(screen_height * 0.88), max(760, min(1200, round(screen_height * 0.78))))
        self.geometry(f"{width}x{height}")

    def _bind_page_scroll(self, canvas: tk.Canvas) -> None:
        self.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(-1 if event.delta > 0 else 1, "units"))
        self.bind_all("<Button-4>", lambda _event: canvas.yview_scroll(-1, "units"))
        self.bind_all("<Button-5>", lambda _event: canvas.yview_scroll(1, "units"))

    def _unbind_page_scroll(self) -> None:
        self.unbind_all("<MouseWheel>")
        self.unbind_all("<Button-4>")
        self.unbind_all("<Button-5>")

    def _card(self, parent: ttk.Frame, title: str, subtitle: str = "") -> ttk.Frame:
        card = ttk.Frame(parent, style="Card.TFrame", padding=18)
        ttk.Label(card, text=title, style="CardTitle.TLabel").pack(anchor="w")
        if subtitle:
            ttk.Label(card, text=subtitle, style="CardMuted.TLabel", wraplength=760).pack(anchor="w", pady=(3, 12))
        return card

    def _build_home(self, page: ttk.Frame) -> None:
        page.columnconfigure(0, weight=3)
        page.columnconfigure(1, weight=2)
        page.rowconfigure(1, weight=1)
        hero = self._card(
            page, "Make the whole case feel alive", "One clean control room for color, motion, music, and every boot."
        )
        hero.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        hero.columnconfigure(1, weight=1)
        controls = ttk.Frame(hero, style="Card.TFrame")
        controls.pack(fill="x", pady=(6, 0))
        ttk.Label(controls, text="MASTER BRIGHTNESS", style="CardMuted.TLabel").pack(side="left")
        ttk.Scale(
            controls, from_=0, to=100, variable=self.brightness_var, command=self._brightness_changed, length=360
        ).pack(side="left", fill="x", expand=True, padx=18)
        ttk.Label(controls, textvariable=self.brightness_label_var, style="Card.TLabel", width=5).pack(side="left")

        themes = self._card(page, "Scenes", "Three-zone palettes from quiet ambient color to full neon.")
        themes.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        theme_grid = ttk.Frame(themes, style="Card.TFrame")
        theme_grid.pack(fill="both", expand=True)
        for column in range(3):
            theme_grid.columnconfigure(column, weight=1)
        for index, (name, colors) in enumerate(THEMES.items()):
            button = tk.Button(
                theme_grid,
                text=f"{name}\n●  ●  ●",
                command=lambda selected=name: self._apply_theme(selected),
                bg=PANEL_ALT,
                fg=f"#{colors[0]}",
                activebackground=BASE,
                activeforeground=f"#{colors[1]}",
                relief="flat",
                bd=0,
                highlightthickness=1,
                highlightbackground=BORDER,
                font=("Segoe UI", 9, "bold"),
                padx=8,
                pady=8,
                cursor="hand2",
            )
            button.grid(row=index // 3, column=index % 3, sticky="ew", padx=4, pady=4)
            self._theme_buttons[name] = button

        colors = self._card(page, "Solid color", "A single precise color across every channel.")
        colors.grid(row=1, column=1, sticky="nsew", padx=(6, 0))
        swatches = ttk.Frame(colors, style="Card.TFrame")
        swatches.pack(fill="x")
        for index, (name, color) in enumerate(COLOR_PRESETS):
            button = tk.Button(
                swatches,
                text="",
                command=lambda value=color: self._apply_solid(value),
                bg=f"#{color}",
                activebackground=f"#{color}",
                width=4,
                height=2,
                relief="flat",
                bd=0,
                highlightthickness=2,
                highlightbackground=BLACK,
                cursor="hand2",
            )
            button.grid(row=index // 4, column=index % 4, padx=5, pady=5, sticky="ew")
            swatches.columnconfigure(index % 4, weight=1)
        custom = ttk.Frame(colors, style="Card.TFrame")
        custom.pack(fill="x", pady=(18, 0))
        ttk.Entry(custom, textvariable=self.solid_var, width=12).pack(side="left")
        ttk.Button(custom, text="PICK", command=self._pick_solid).pack(side="left", padx=8)
        ttk.Button(custom, text="APPLY", style="Accent.TButton", command=self._apply_custom_solid).pack(side="left")
        ttk.Separator(colors, orient="horizontal").pack(fill="x", pady=20)
        ttk.Checkbutton(
            colors,
            text="Restore the last look when CaseLight starts",
            variable=self.restore_var,
            command=self._toggle_restore,
        ).pack(anchor="w")

    def _build_effects(self, page: ttk.Frame) -> None:
        page.columnconfigure(0, weight=1)
        motion = self._card(
            page,
            "Motion engine",
            "Ambient sweeps and beat-locked animation. Hardware effects keep running after the app closes.",
        )
        motion.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        fields = ttk.Frame(motion, style="Card.TFrame")
        fields.pack(fill="x")
        self._field(
            fields,
            "EFFECT",
            lambda host: ttk.Combobox(host, textvariable=self.effect_var, values=EFFECTS, state="readonly", width=27),
            0,
        )
        self._field(
            fields,
            "BEAT DIVISION",
            lambda host: ttk.Combobox(
                host, textvariable=self.division_var, values=BEAT_DIVISIONS, state="readonly", width=16
            ),
            1,
        )
        self._field(
            fields,
            "REFRESH",
            lambda host: ttk.Spinbox(host, from_=2, to=12, textvariable=self.animation_fps_var, width=8),
            2,
        )
        actions = ttk.Frame(motion, style="Card.TFrame")
        actions.pack(fill="x", pady=(18, 0))
        ttk.Button(actions, text="START EFFECT", style="Accent.TButton", command=self._start_effect).pack(side="left")
        ttk.Button(actions, text="STOP", command=lambda: self.engine.stop_effect()).pack(side="left", padx=8)

        tempo = self._card(
            page, "Tempo lab", "Dial in a BPM or tap along. Tempo effects remain phase-locked to this clock."
        )
        tempo.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        bpm_row = ttk.Frame(tempo, style="Card.TFrame")
        bpm_row.pack(fill="x")
        ttk.Label(bpm_row, textvariable=self.bpm_label_var, style="Hero.TLabel", width=10).pack(side="left")
        ttk.Scale(bpm_row, from_=40, to=240, variable=self.bpm_var, command=self._bpm_changed, length=520).pack(
            side="left", fill="x", expand=True, padx=16
        )
        ttk.Button(bpm_row, text="TAP TEMPO", style="Accent.TButton", command=self._tap_tempo).pack(side="left")
        presets = ttk.Frame(tempo, style="Card.TFrame")
        presets.pack(fill="x", pady=(16, 0))
        for value in (60, 90, 120, 128, 140, 174):
            ttk.Button(presets, text=str(value), command=lambda bpm=value: self._set_bpm(bpm)).pack(
                side="left", padx=(0, 8)
            )

        note = self._card(
            page,
            "How tempo effects behave",
            "Tempo bounce flashes on every selected beat. Tempo chase advances one zone per beat. Tempo rainbow rotates the palette on the beat while preserving the three-zone spacing.",
        )
        note.grid(row=2, column=0, sticky="ew")

    def _field(
        self,
        parent: ttk.Frame,
        label: str,
        build_widget: Callable[[ttk.Frame], tk.Widget],
        column: int,
    ) -> None:
        host = ttk.Frame(parent, style="Card.TFrame")
        host.grid(row=0, column=column, sticky="ew", padx=(0, 18))
        parent.columnconfigure(column, weight=1)
        ttk.Label(host, text=label, style="CardMuted.TLabel").pack(anchor="w", pady=(0, 6))
        widget = build_widget(host)
        widget.pack(fill="x")

    def _build_music(self, page: ttk.Frame) -> None:
        page.columnconfigure(0, weight=1)
        visualizer = self._card(
            page, "Music visualizer", "System audio is sampled only while the visualizer is active."
        )
        visualizer.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        top = ttk.Frame(visualizer, style="Card.TFrame")
        top.pack(fill="x")
        self._field(
            top,
            "STYLE",
            lambda host: ttk.Combobox(
                host, textvariable=self.music_style_var, values=MUSIC_STYLES, state="readonly", width=22
            ),
            0,
        )
        self._field(
            top,
            "UPDATES / SECOND",
            lambda host: ttk.Spinbox(host, from_=2, to=12, textvariable=self.music_fps_var, width=10),
            1,
        )
        controls = ttk.Frame(visualizer, style="Card.TFrame")
        controls.pack(fill="x", pady=(18, 0))
        ttk.Button(controls, text="START VISUALIZER", style="Accent.TButton", command=self._start_music).pack(
            side="left"
        )
        ttk.Button(controls, text="STOP", command=lambda: self.engine.stop_music()).pack(side="left", padx=8)
        ttk.Label(controls, text="Linux: CAVA / PulseAudio    Windows: WASAPI loopback", style="CardMuted.TLabel").pack(
            side="right"
        )
        self.music_canvas = tk.Canvas(visualizer, height=160, bg=BLACK, bd=0, highlightthickness=0)
        self.music_canvas.pack(fill="x", pady=(18, 0))
        meter_colors = (PINK, VIOLET, CYAN)
        for index, (label, color) in enumerate(zip(("BASS", "MID", "TREBLE"), meter_colors)):
            left = 30 + index * 260
            self._meter_items.append(
                self.music_canvas.create_rectangle(left, 115, left + 190, 115, fill=color, outline="")
            )
            self.music_canvas.create_text(left + 95, 138, text=label, fill=WHITE, font=("Segoe UI", 9, "bold"))

        response = self._card(page, "Response shaping", "Tune how quickly the lights react and how gently they fade.")
        response.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        self._slider_row(response, "Sensitivity", self.sensitivity_var, 25, 250, "%")
        self._slider_row(response, "Smoothing", self.smoothing_var, 0, 95, "%")
        self._slider_row(response, "Minimum glow", self.minimum_glow_var, 0, 30, "%")

        gains = self._card(page, "Frequency balance", "Compensate for your speakers, room, and favorite kind of music.")
        gains.grid(row=2, column=0, sticky="ew")
        row = ttk.Frame(gains, style="Card.TFrame")
        row.pack(fill="x")
        for column, (label, variable, color) in enumerate(
            (
                ("BASS", self.bass_gain_var, PINK),
                ("MID", self.mid_gain_var, VIOLET),
                ("TREBLE", self.treble_gain_var, CYAN),
            )
        ):
            host = ttk.Frame(row, style="Card.TFrame")
            host.grid(row=0, column=column, sticky="ew", padx=(0, 18))
            row.columnconfigure(column, weight=1)
            tk.Label(host, text=label, bg=PANEL, fg=color, font=("Segoe UI", 9, "bold")).pack(anchor="w")
            ttk.Spinbox(host, from_=25, to=250, increment=5, textvariable=variable, width=9).pack(
                anchor="w", pady=(6, 0)
            )

    def _slider_row(self, parent: ttk.Frame, label: str, variable: tk.IntVar, low: int, high: int, suffix: str) -> None:
        row = ttk.Frame(parent, style="Card.TFrame")
        row.pack(fill="x", pady=4)
        ttk.Label(row, text=label, style="Card.TLabel", width=18).pack(side="left")
        ttk.Scale(row, from_=low, to=high, variable=variable).pack(side="left", fill="x", expand=True, padx=12)
        value = ttk.Label(row, text=f"{variable.get()}{suffix}", style="CardMuted.TLabel", width=7)
        value.pack(side="left")
        variable.trace_add(
            "write", lambda *_args, var=variable, output=value, unit=suffix: output.configure(text=f"{var.get()}{unit}")
        )

    def _build_zones(self, page: ttk.Frame) -> None:
        page.columnconfigure(0, weight=1)
        ttk.Label(
            page, text="Map each physical light group once, then shape it independently.", style="Muted.TLabel"
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))
        for row_index, (key, label, _default_channel, _default_color) in enumerate(ZONES, start=1):
            zone = self.state["zones"][key]
            variables = {
                "channel": tk.StringVar(value=zone["channel"]),
                "mode": tk.StringVar(value=zone["mode"]),
                "speed": tk.StringVar(value=zone["speed"]),
                "color": tk.StringVar(value=f"#{zone['color']}"),
            }
            self._zone_vars[key] = variables
            card = self._card(page, label, f"Logical channel {zone['channel']}")
            card.grid(row=row_index, column=0, sticky="ew", pady=(0, 10))
            line = ttk.Frame(card, style="Card.TFrame")
            line.pack(fill="x")
            swatch = tk.Canvas(
                line,
                width=58,
                height=42,
                bg=f"#{zone['color']}",
                bd=0,
                highlightthickness=1,
                highlightbackground=BORDER,
                cursor="hand2",
            )
            swatch.pack(side="left", padx=(0, 14))
            swatch.bind("<Button-1>", lambda _event, selected=key: self._pick_zone_color(selected))
            self._zone_swatches[key] = swatch
            for caption, field, values, width in (
                ("CHANNEL", "channel", CHANNELS, 10),
                ("MODE", "mode", MODES, 16),
                ("SPEED", "speed", SPEEDS, 11),
            ):
                host = ttk.Frame(line, style="Card.TFrame")
                host.pack(side="left", padx=(0, 14))
                ttk.Label(host, text=caption, style="CardMuted.TLabel").pack(anchor="w")
                ttk.Combobox(host, textvariable=variables[field], values=values, state="readonly", width=width).pack(
                    pady=(4, 0)
                )
            color_host = ttk.Frame(line, style="Card.TFrame")
            color_host.pack(side="left", fill="x", expand=True)
            ttk.Label(color_host, text="COLOR", style="CardMuted.TLabel").pack(anchor="w")
            entry = ttk.Entry(color_host, textvariable=variables["color"], width=12)
            entry.pack(anchor="w", pady=(4, 0))
            entry.bind("<FocusOut>", lambda _event, selected=key: self._refresh_zone_swatch(selected))
        actions = ttk.Frame(page, style="Page.TFrame")
        actions.grid(row=5, column=0, sticky="ew", pady=(2, 0))
        ttk.Button(actions, text="APPLY ALL ZONES", style="Accent.TButton", command=self._apply_zones).pack(
            side="right"
        )

    def _build_timer(self, page: ttk.Frame) -> None:
        page.columnconfigure(0, weight=1)
        timer = self._card(page, "Light timer", "Settle in, fall asleep, or restore the current scene after a break.")
        timer.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        row = ttk.Frame(timer, style="Card.TFrame")
        row.pack(fill="x")
        self._field(row, "MINUTES", lambda host: ttk.Entry(host, textvariable=self.timer_minutes_var, width=12), 0)
        self._field(
            row,
            "WHEN FINISHED",
            lambda host: ttk.Combobox(
                host,
                textvariable=self.timer_action_var,
                values=("Turn off", "Restore lights"),
                state="readonly",
                width=18,
            ),
            1,
        )
        actions = ttk.Frame(timer, style="Card.TFrame")
        actions.pack(fill="x", pady=(18, 0))
        ttk.Button(actions, text="START TIMER", style="Accent.TButton", command=self._start_timer).pack(side="left")
        ttk.Button(actions, text="CANCEL", command=lambda: self.engine.cancel_timer()).pack(side="left", padx=8)

        boot = self._card(
            page,
            "Every boot, same room",
            "These choices live in the shared profile, outside the app. When both operating systems run CaseLight from the same volume, they see the same last scene.",
        )
        boot.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        ttk.Checkbutton(
            boot,
            text="Restore my last lighting state when CaseLight opens",
            variable=self.restore_var,
            command=self._toggle_restore,
        ).pack(anchor="w", pady=3)
        ttk.Checkbutton(
            boot, text="Start CaseLight when I sign in", variable=self.startup_var, command=self._toggle_startup
        ).pack(anchor="w", pady=3)
        ttk.Label(
            boot,
            text="The shared preference is carried across systems; each OS gets its own small startup entry the next time CaseLight runs there.",
            style="CardMuted.TLabel",
            wraplength=780,
        ).pack(anchor="w", pady=(8, 0))

    def _build_settings(self, page: ttk.Frame) -> None:
        page.columnconfigure(0, weight=1)
        device = self._card(page, "Lighting hardware", "Gigabyte RGB Fusion 2.0 IT5711 • USB HID 048D:5711")
        device.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        row = ttk.Frame(device, style="Card.TFrame")
        row.pack(fill="x")
        ttk.Button(row, text="DETECT CONTROLLER", style="Accent.TButton", command=lambda: self.engine.detect()).pack(
            side="left"
        )
        if sys.platform.startswith("linux"):
            ttk.Button(row, text="INSTALL LINUX DEVICE ACCESS", command=self._install_linux_access).pack(
                side="left", padx=8
            )

        storage = self._card(
            page,
            "Shared state",
            "Atomic state and a recoverable backup live outside the application and build folders.",
        )
        storage.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(storage, textvariable=self.data_path_var, style="Card.TLabel", wraplength=800).pack(anchor="w")
        ttk.Label(storage, textvariable=self.data_reason_var, style="CardMuted.TLabel").pack(anchor="w", pady=(3, 12))
        actions = ttk.Frame(storage, style="Card.TFrame")
        actions.pack(fill="x")
        ttk.Button(actions, text="CHOOSE SHARED FOLDER", command=self._choose_data_folder).pack(side="left")
        ttk.Button(actions, text="OPEN FOLDER", command=self._open_data_folder).pack(side="left", padx=8)

        about = self._card(
            page,
            f"{APP_NAME} {APP_VERSION}",
            "The case-light module isolated from Speechless and rebuilt as a focused Linux + Windows controller.",
        )
        about.grid(row=2, column=0, sticky="ew")
        ttk.Label(
            about,
            text="Hardware updates use liquidctl. Linux visualization prefers CAVA and falls back to PulseAudio FFT. Windows visualization uses WASAPI loopback.",
            style="CardMuted.TLabel",
            wraplength=800,
        ).pack(anchor="w")

    def show_page(self, name: str) -> None:
        self._pages[name].tkraise()
        self.page_title_var.set(name)
        for page, button in self._nav_buttons.items():
            button.configure(style="NavActive.TButton" if page == name else "Nav.TButton")

    def _set_status(self, text: str, error: bool = False) -> None:
        self.status_var.set(text)
        self.status_dot.itemconfigure(self.status_dot_item, fill=RED if error else CYAN)

    def _save_state(self, state: dict[str, Any]) -> None:
        self.store.save(state)
        self.status_detail_var.set(f"State • {self.store.directory}")

    def _queue_save(self) -> None:
        if self._save_after:
            self.after_cancel(self._save_after)
        self._save_after = self.after(250, lambda: self._save_state(self.state))

    def _sync_state(self) -> None:
        self.state["brightness"] = clamp_number(self.brightness_var.get(), 0, 100, 80)
        self.state["theme"] = self.theme_var.get() if self.theme_var.get() in THEMES else self.state["theme"]
        self.state["solid_color"] = normalize_hex(self.solid_var.get(), self.state["solid_color"])
        self.state["effect"] = self.effect_var.get() if self.effect_var.get() in EFFECTS else self.state["effect"]
        self.state["tempo_bpm"] = clamp_number(self.bpm_var.get(), 40, 240, 120)
        self.state["beat_division"] = self.division_var.get() if self.division_var.get() in BEAT_DIVISIONS else "1 beat"
        self.state["animation_fps"] = clamp_number(self.animation_fps_var.get(), 2, 12, 5)
        music = self.state["music"]
        music["style"] = self.music_style_var.get() if self.music_style_var.get() in MUSIC_STYLES else "Spectrum"
        music["sensitivity"] = clamp_number(self.sensitivity_var.get(), 25, 250, 100)
        music["smoothing"] = clamp_number(self.smoothing_var.get(), 0, 95, 72)
        music["minimum_glow"] = clamp_number(self.minimum_glow_var.get(), 0, 30, 3)
        music["fps"] = clamp_number(self.music_fps_var.get(), 2, 12, 5)
        music["bass_gain"] = clamp_number(self.bass_gain_var.get(), 25, 250, 100)
        music["mid_gain"] = clamp_number(self.mid_gain_var.get(), 25, 250, 100)
        music["treble_gain"] = clamp_number(self.treble_gain_var.get(), 25, 250, 100)
        for key, variables in self._zone_vars.items():
            self.state["zones"][key].update(
                channel=variables["channel"].get(),
                mode=variables["mode"].get(),
                speed=variables["speed"].get(),
                color=normalize_hex(variables["color"].get(), self.state["zones"][key]["color"]),
            )

    def _brightness_changed(self, value: str) -> None:
        brightness = clamp_number(value, 0, 100, 80)
        self.brightness_label_var.set(f"{brightness}%")
        self.state["brightness"] = brightness
        self._queue_save()
        if self._brightness_after:
            self.after_cancel(self._brightness_after)
        if self.state.get("power_on"):
            self._brightness_after = self.after(450, self.engine.restore)

    def _apply_theme(self, name: str) -> None:
        self.theme_var.set(name)
        self._sync_state()
        self.engine.apply_theme(name)

    def _apply_solid(self, color: str) -> None:
        color = normalize_hex(color)
        self.solid_var.set(f"#{color}")
        self._sync_state()
        self.engine.apply_solid(color)

    def _pick_solid(self) -> None:
        selected = colorchooser.askcolor(color=self.solid_var.get(), title="Choose a case-light color", parent=self)
        if selected[1]:
            self.solid_var.set(selected[1].upper())

    def _apply_custom_solid(self) -> None:
        self._apply_solid(normalize_hex(self.solid_var.get()))

    def _start_effect(self) -> None:
        self._sync_state()
        self.engine.start_effect()

    def _bpm_changed(self, value: str) -> None:
        bpm = clamp_number(value, 40, 240, 120)
        self.bpm_label_var.set(f"{bpm} BPM")
        self.state["tempo_bpm"] = bpm
        self._queue_save()

    def _set_bpm(self, value: int) -> None:
        self.bpm_var.set(value)
        self._bpm_changed(str(value))

    def _tap_tempo(self) -> None:
        now = time.monotonic()
        self._tap_times = [stamp for stamp in self._tap_times if now - stamp < 3.0]
        self._tap_times.append(now)
        if len(self._tap_times) >= 2:
            intervals = [right - left for left, right in zip(self._tap_times, self._tap_times[1:])]
            bpm = clamp_number(60.0 / (sum(intervals) / len(intervals)), 40, 240, 120)
            self._set_bpm(bpm)
            self._set_status(f"Tapped {bpm} BPM")
        else:
            self._set_status("Tap again…")

    def _start_music(self) -> None:
        self._sync_state()
        self.engine.start_music()

    def _update_music_meter(self, bands: tuple[float, float, float]) -> None:
        if not hasattr(self, "music_canvas"):
            return
        for item, level in zip(self._meter_items, bands):
            coords = self.music_canvas.coords(item)
            if len(coords) == 4:
                self.music_canvas.coords(item, coords[0], 115 - max(0.0, min(1.0, level)) * 92, coords[2], 115)

    def _pick_zone_color(self, key: str) -> None:
        selected = colorchooser.askcolor(
            color=self._zone_vars[key]["color"].get(),
            title=f"Choose {self.state['zones'][key]['name']} color",
            parent=self,
        )
        if selected[1]:
            self._zone_vars[key]["color"].set(selected[1].upper())
            self._refresh_zone_swatch(key)

    def _refresh_zone_swatch(self, key: str) -> None:
        color = normalize_hex(self._zone_vars[key]["color"].get(), self.state["zones"][key]["color"])
        self._zone_vars[key]["color"].set(f"#{color}")
        self._zone_swatches[key].configure(bg=f"#{color}")

    def _apply_zones(self) -> None:
        self._sync_state()
        for key in self._zone_vars:
            self._refresh_zone_swatch(key)
        self.engine.apply_zones()

    def _start_timer(self) -> None:
        try:
            minutes = float(self.timer_minutes_var.get())
            if not 0.01 <= minutes <= 1440:
                raise ValueError
        except ValueError:
            self._set_status("Enter a timer from 0.01 to 1440 minutes", True)
            return
        self.engine.start_timer(minutes, self.timer_action_var.get())

    def _toggle_restore(self) -> None:
        self.state["restore_on_startup"] = bool(self.restore_var.get())
        self._save_state(self.state)

    def _toggle_startup(self) -> None:
        enabled = bool(self.startup_var.get())
        try:
            path = set_start_with_system(enabled)
            self.state["start_with_system"] = enabled
            self._save_state(self.state)
            self._set_status(f"Startup {'enabled' if enabled else 'disabled'} • {path}")
        except OSError as exc:
            self.startup_var.set(not enabled)
            self._set_status(f"Could not change startup: {exc}", True)

    def _ensure_current_os_startup(self) -> None:
        if self.state.get("start_with_system") and not is_start_with_system_enabled():
            try:
                set_start_with_system(True)
            except OSError as exc:
                self._set_status(f"Could not create this OS startup entry: {exc}", True)

    def _restore_now(self) -> None:
        self._sync_state()
        self.state["power_on"] = True
        if self.state["active_mode"] == "off":
            self.state["active_mode"] = self.state.get("last_active_mode", "theme")
        self.engine.restore()

    def _choose_data_folder(self) -> None:
        selected = filedialog.askdirectory(
            parent=self, title="Choose a shared CaseLight state folder", initialdir=str(self.store.directory.parent)
        )
        if not selected:
            return
        destination = Path(selected).expanduser().resolve()
        try:
            self._sync_state()
            self.store = self.store.move_to(destination, self.state)
            self.engine.state_directory = self.store.directory
            self.data_path_var.set(str(self.store.directory))
            self.data_reason_var.set("saved shared location")
            self._set_status("Shared state location updated")
        except (OSError, ValueError) as exc:
            self._set_status(f"Could not use that folder: {exc}", True)

    def _open_data_folder(self) -> None:
        self.store.directory.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(self.store.directory)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(self.store.directory)])
            else:
                subprocess.Popen(["xdg-open", str(self.store.directory)])
        except OSError as exc:
            self._set_status(f"Could not open state folder: {exc}", True)

    def _install_linux_access(self) -> None:
        if not messagebox.askyesno(
            "Administrator access required",
            "CaseLight will ask for an administrator password to install one udev rule for USB device 048D:5711. No other system files are changed. Continue?",
            parent=self,
        ):
            return
        root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
        script = root / "scripts" / "install-linux-device-access.sh"
        try:
            subprocess.Popen([str(script)])
            self._set_status("Device-access installer opened")
        except OSError as exc:
            self._set_status(f"Could not open installer: {exc}", True)

    def _close(self) -> None:
        try:
            self._sync_state()
            self.state["window_geometry"] = self.geometry()
            self._save_state(self.state)
        finally:
            self.engine.shutdown()
            self.destroy()


def run(*, minimized: bool = False, state_directory: Path | None = None) -> None:
    app = CaseLightApp(minimized=minimized, state_directory=state_directory)
    app.mainloop()
