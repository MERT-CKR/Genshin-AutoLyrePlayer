from settings_dialog import (SettingsDialog, GITHUB_REPO_URL, fetch_remote_version,
                             is_newer_version, load_bundled_info)
from midi_import import MidiImportDialog, MIDI_EXTENSIONS, load_midi
from theme import *

import tkinter as tk
import tkinter.font as tkfont
import customtkinter as ctk
import os
import pygame
import time
import sys
import ctypes
import queue
import json
import threading
import pyautogui
import traceback
import webbrowser
import pygetwindow as gw

try:
    pygame.mixer.init()
    pygame.mixer.set_num_channels(64)
except Exception:
    print("Audio init failed")

pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False

# ================= CONSTANTS =================
BUTTON_SIZE = 70
BUTTON_CORNER = 35
HOLDER_SIZE = 90

UNSTABLE_INSTRUMENTS = ["LingeringEuphonia", "Ukulele"]

# Safety limit: key events closer than this are merged into one chord, so a very fast
# song can never flood the system with key presses (15 ms is below what the ear can separate).
MIN_EVENT_GAP_MS = 15

VK_ESCAPE = 0x1B
VK_SHIFT = 0x10

SHEET_EXTENSIONS = (".json", ".txt", ".genshinsheet", ".skysheet")


NOTE_NAMES = {
    "q": "C", "w": "D", "e": "E", "r": "F", "t": "G", "y": "A", "u": "B",
    "a": "C", "s": "D", "d": "E", "f": "F", "g": "G", "h": "A", "j": "B",
    "z": "C", "x": "D", "c": "E", "v": "F", "b": "G", "n": "A", "m": "B",
}

KEY_LAYOUT = [
    ["q", "w", "e", "r", "t", "y", "u"],
    ["a", "s", "d", "f", "g", "h", "j"],
    ["z", "x", "c", "v", "b", "n", "m"],
]

KEY_INDEX = {
    "q": 0, "w": 1, "e": 2, "r": 3, "t": 4, "y": 5, "u": 6,
    "a": 7, "s": 8, "d": 9, "f": 10, "g": 11, "h": 12, "j": 13,
    "z": 14, "x": 15, "c": 16, "v": 17, "b": 18, "n": 19, "m": 20
}

KEY_ORDER = [k for row in KEY_LAYOUT for k in row]

SKY_KEY_MAP = {
    "0": "z", "1": "x", "2": "c", "3": "v", "4": "b",
    "5": "n", "6": "m", "7": "a", "8": "s", "9": "d",
    "10": "f", "11": "g", "12": "h", "13": "j", "14": "q",
}


TEMPO_DICT = {0: 1, 1: 2, 2: 4, 3: 8}

NUMBERS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12",
           "13", "14", "15", "16", "17", "18", "19", "20"][::-1]
KEYS = ["q", "w", "e", "r", "t", "y", "u", "a", "s", "d", "f", "g", "h", "j",
        "z", "x", "c", "v", "b", "n", "m"][::-1]

ANIMATION_DURATION = 12


def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS # type: ignore
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")


def writable_path(filename):
    appdata = os.getenv("APPDATA") or os.path.expanduser("~")
    app_folder = os.path.join(appdata, "GenshinAutoPlayer")
    os.makedirs(app_folder, exist_ok=True)
    return os.path.join(app_folder, filename)


def display_name(file_name):
    """Library name without the sheet extension (.json, .txt, .genshinsheet, .skysheet)."""
    base, extension = os.path.splitext(file_name)
    return base if extension.lower() in SHEET_EXTENSIONS else file_name


def merge_close_events(events):
    """events: {time_ms: [keys]} -> same shape, but events closer than MIN_EVENT_GAP_MS
    are merged into a single chord (no note is dropped)."""
    merged = {}
    group_start = None
    for time_ms in sorted(events):
        if group_start is None or time_ms - group_start >= MIN_EVENT_GAP_MS:
            group_start = time_ms
            merged[group_start] = list(events[time_ms])
        else:
            for key in events[time_ms]:
                if key not in merged[group_start]:
                    merged[group_start].append(key)
    return merged


# ================= STOP KEYS (global, Windows) =================

def get_stop_key_combos():
    """(virtual_key, needs_shift) pairs that stop playback: ESC, plus the key that types '"'
    on every installed keyboard layout (it sits in a different place on each layout)."""
    combos = {(VK_ESCAPE, False)}
    try:
        user32 = ctypes.windll.user32
        user32.GetKeyboardLayoutList.argtypes = [ctypes.c_int, ctypes.c_void_p]
        user32.GetKeyboardLayoutList.restype = ctypes.c_int
        user32.VkKeyScanExW.argtypes = [ctypes.c_wchar, ctypes.c_void_p]
        user32.VkKeyScanExW.restype = ctypes.c_short
        count = user32.GetKeyboardLayoutList(0, None)
        layouts = (ctypes.c_void_p * count)()
        user32.GetKeyboardLayoutList(count, layouts)
        for layout in layouts:
            if not layout:
                continue
            result = user32.VkKeyScanExW('"', layout)
            if result == -1:
                continue
            virtual_key = result & 0xFF
            modifiers = (result >> 8) & 0xFF
            # skip: unavailable, needs Ctrl/Alt/AltGr, or collides with a note key (A-Z)
            if virtual_key == 0xFF or modifiers & ~1 or 0x41 <= virtual_key <= 0x5A:
                continue
            combos.add((virtual_key, bool(modifiers & 1)))
    except Exception:
        pass
    return combos


def stop_keys_pressed(user32, combos):
    """True while ESC (or the '"' key) is physically held down, whatever window has focus."""
    for virtual_key, needs_shift in combos:
        if user32.GetAsyncKeyState(virtual_key) & 0x8000:
            if not needs_shift or user32.GetAsyncKeyState(VK_SHIFT) & 0x8000:
                return True
    return False


# ================= ADMIN =================

def check_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def _proceed(win):
    win.destroy()
    params = " ".join([f'"{arg}"' for arg in sys.argv])
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, params, None, 1
    )
    sys.exit()

def request_admin_and_restart():
    ctk.set_appearance_mode(APPEARANCE_MODE)
    win = ctk.CTk()
    win.title("Administrator Required")
    width, height = 420, 200
    pos_x = (win.winfo_screenwidth() - width) // 2
    pos_y = (win.winfo_screenheight() - height) // 2
    win.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
    win.resizable(False, False)
    win.configure(fg_color=SIDEBAR)
    ctk.CTkLabel(win, text="Administrator Privileges Required",
                 font=ctk.CTkFont("Segoe UI", 15, "bold"), text_color=TEXT).pack(pady=(28, 8))
    ctk.CTkLabel(win,
                 text="Genshin Impact runs as Administrator.\n"
                      "To send inputs to the game, this app also needs\n"
                      "Administrator privileges. Click Proceed to restart.",
                 font=ctk.CTkFont("Segoe UI", 12), text_color=MUTED, justify="center").pack(pady=(0, 18))
    ctk.CTkButton(win, text="Proceed", width=220, height=38,
                  fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ON_ACCENT,
                  font=ctk.CTkFont("Segoe UI", 13, "bold"),
                  command=lambda: _proceed(win)).pack()
    win.mainloop()
    sys.exit()


# ================= HELPERS =================

def hex_to_rgb(color):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def mix_color(base, target, amount):
    amount = max(0.0, min(1.0, amount))
    r = int(base[0] + (target[0] - base[0]) * amount)
    g = int(base[1] + (target[1] - base[1]) * amount)
    b = int(base[2] + (target[2] - base[2]) * amount)
    return f"#{r:02x}{g:02x}{b:02x}"


def rounded_square_points(cx, cy, half, radius):
    """Polygon points for a rounded square, to be drawn with smooth=True."""
    x1, y1, x2, y2 = cx - half, cy - half, cx + half, cy + half
    r = min(radius, half)
    return [
        x1 + r, y1, x1 + r, y1, x2 - r, y1, x2 - r, y1,
        x2, y1, x2, y1 + r, x2, y1 + r, x2, y2 - r, x2, y2 - r,
        x2, y2, x2 - r, y2, x2 - r, y2, x1 + r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y2 - r, x1, y1 + r, x1, y1 + r,
        x1, y1,
    ]


class KeyPad(tk.Canvas):
    CELL = HOLDER_SIZE + 12
    DURATION = 0.28          # seconds
    FRAME_MS = 16
    CORNER = 26              # corner radius, bigger = rounder
    BORDER_WIDTH = 2
    BASE_RGB = hex_to_rgb(CARD)
    ACTIVE_RGB = hex_to_rgb(ACCENT_SOFT)
    BORDER_BASE_RGB = hex_to_rgb(BORDER)
    BORDER_ACTIVE_RGB = hex_to_rgb(ACCENT)
    BG_RGB = hex_to_rgb(BG)

    def __init__(self, parent, on_press):
        cols, rows = len(KEY_LAYOUT[0]), len(KEY_LAYOUT)
        super().__init__(parent, width=cols * self.CELL, height=rows * self.CELL,
                         bg=BG, highlightthickness=0, bd=0)
        self.on_press = on_press
        self.items = {}      # key -> (shape, ring, text, cx, cy)
        self.pulses = {}     # key -> start time
        self.loop_running = False
        self.rest_fill = mix_color(self.BASE_RGB, self.BASE_RGB, 0)
        self.rest_border = mix_color(self.BORDER_BASE_RGB, self.BORDER_BASE_RGB, 0)
        half = BUTTON_SIZE / 2

        for r, row in enumerate(KEY_LAYOUT):
            for c, key in enumerate(row):
                cx = c * self.CELL + self.CELL / 2
                cy = r * self.CELL + self.CELL / 2
                ring = self.create_polygon(rounded_square_points(cx, cy, half, self.CORNER),
                                           smooth=True, fill="", outline=BG, width=2,
                                           state="hidden")
                shape = self.create_polygon(rounded_square_points(cx, cy, half, self.CORNER),
                                            smooth=True, fill=self.rest_fill,
                                            outline=self.rest_border, width=self.BORDER_WIDTH)
                text = self.create_text(cx, cy, text=key.upper(), fill=TEXT,
                                        font=("Segoe UI", 18, "bold"))
                self.items[key] = (shape, ring, text, cx, cy)
                for item in (shape, text):
                    self.tag_bind(item, "<Button-1>", lambda e, k=key: self.on_press(k))

    def pulse(self, key):
        if key not in self.items:
            return
        self.pulses[key] = time.perf_counter()
        if not self.loop_running:
            self.loop_running = True
            self._tick()

    def _tick(self):
        now = time.perf_counter()
        finished = []
        for key, start in self.pulses.items():
            t = (now - start) / self.DURATION
            shape, ring, _, cx, cy = self.items[key]
            if t >= 1:
                self._set_shape(shape, cx, cy, 1.0, self.rest_fill, self.rest_border)
                self.itemconfigure(ring, state="hidden")
                finished.append(key)
                continue
            # quick pop up, smooth settle back
            scale = 1 + 0.17 * (1 - abs(2 * (t ** 0.6) - 1) ** 2)
            glow = (1 - t) ** 1.5
            self._set_shape(shape, cx, cy, scale,
                            mix_color(self.BASE_RGB, self.ACTIVE_RGB, glow),
                            mix_color(self.BORDER_BASE_RGB, self.BORDER_ACTIVE_RGB, glow))

            # expanding ring that fades out
            ring_half = BUTTON_SIZE / 2 * (1 + 0.55 * t)
            self.coords(ring, *rounded_square_points(cx, cy, ring_half, self.CORNER * (1 + 0.55 * t)))
            self.itemconfigure(ring, state="normal",
                               outline=mix_color(self.BORDER_ACTIVE_RGB, self.BG_RGB, t))
        for key in finished:
            del self.pulses[key]
        if self.pulses:
            self.after(self.FRAME_MS, self._tick)
        else:
            self.loop_running = False

    def _set_shape(self, shape, cx, cy, scale, fill, outline):
        half = BUTTON_SIZE / 2 * scale
        self.coords(shape, *rounded_square_points(cx, cy, half, self.CORNER * scale))
        self.itemconfigure(shape, fill=fill, outline=outline)


def rounded_rect_points(x1, y1, x2, y2, radius):
    """Polygon points for a rounded rectangle, to be drawn with smooth=True."""
    r = min(radius, (x2 - x1) / 2, (y2 - y1) / 2)
    return [
        x1 + r, y1, x1 + r, y1, x2 - r, y1, x2 - r, y1,
        x2, y1, x2, y1 + r, x2, y1 + r, x2, y2 - r, x2, y2 - r,
        x2, y2, x2 - r, y2, x2 - r, y2, x1 + r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y2 - r, x1, y1 + r, x1, y1 + r,
        x1, y1,
    ]


class MusicList(tk.Frame):
    """Virtualized song list: draws only the visible rows on one canvas,
    so scrolling never tears or lags, however many songs there are."""
    ROW_HEIGHT = 40
    ROW_GAP = 3
    PADDING = 4
    SCROLL_STEP = 1.2        # rows per mouse wheel notch

    def __init__(self, parent, on_select):
        super().__init__(parent, bg=SIDEBAR, highlightthickness=0, bd=0)
        self.on_select = on_select
        self.names = []
        self.empty_text = ""
        self.empty_color = MUTED
        self.selected = None
        self.hover = None
        self.offset = 0.0
        self.font = tkfont.Font(family="Segoe UI", size=10)

        self.canvas = tk.Canvas(self, bg=SIDEBAR, highlightthickness=0, bd=0)
        self.scrollbar = ctk.CTkScrollbar(self, command=self._on_scrollbar,
                                          fg_color="transparent",
                                          button_color=BORDER,
                                          button_hover_color=SUBTLE)
        self.scrollbar.pack(side="right", fill="y", padx=(0, 2))
        self.canvas.pack(side="left", fill="both", expand=True)

        self.canvas.bind("<Configure>", lambda e: self._redraw())
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Leave>", self._on_leave)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._on_wheel))
        self.scrollbar.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._on_wheel))
        self.canvas.bind("<Leave>", self._on_leave, add="+")

    # ---------- public ----------

    def set_items(self, names, empty_text="", empty_color=MUTED):
        self.names = list(names)
        self.empty_text = empty_text
        self.empty_color = empty_color
        self.selected = None
        self.hover = None
        self.offset = 0.0
        self._redraw()

    def select(self, name):
        self.selected = name
        self._redraw()

    # ---------- geometry ----------

    def _content_height(self):
        return len(self.names) * self.ROW_HEIGHT + self.PADDING * 2

    def _max_offset(self):
        return max(0.0, self._content_height() - self.canvas.winfo_height())

    def _row_at(self, y):
        position = y + self.offset - self.PADDING
        if position < 0:
            return None
        index = int(position // self.ROW_HEIGHT)
        return index if 0 <= index < len(self.names) else None

    def _fit(self, text, max_width):
        if self.font.measure(text) <= max_width:
            return text
        while text and self.font.measure(text + "…") > max_width:
            text = text[:-1]
        return text + "…"

    # ---------- drawing ----------

    def _redraw(self):
        canvas = self.canvas
        canvas.delete("all")
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if width <= 1:
            return

        if not self.names:
            canvas.create_text(width / 2, 40, text=self.empty_text, fill=self.empty_color,
                               font=self.font)
            self.scrollbar.set(0, 1)
            return

        self.offset = max(0.0, min(self.offset, self._max_offset()))
        first = max(0, int((self.offset - self.PADDING) // self.ROW_HEIGHT))
        last = min(len(self.names), int((self.offset + height) // self.ROW_HEIGHT) + 2)

        for index in range(first, last):
            name = self.names[index]
            y1 = index * self.ROW_HEIGHT + self.PADDING - self.offset
            y2 = y1 + self.ROW_HEIGHT - self.ROW_GAP
            if name == self.selected:
                fill = SELECTED_COLOR
            elif index == self.hover:
                fill = HOVER_COLOR
            else:
                fill = None
            if fill:
                canvas.create_polygon(rounded_rect_points(4, y1, width - 4, y2, 10),
                                      smooth=True, fill=fill, outline="")
            canvas.create_text(14, (y1 + y2) / 2, anchor="w", fill=TEXT, font=self.font,
                               text=self._fit(display_name(name), width - 28))

        total = self._content_height()
        if total <= height:
            self.scrollbar.set(0, 1)
        else:
            self.scrollbar.set(self.offset / total, (self.offset + height) / total)

    # ---------- events ----------

    def _on_wheel(self, event):
        if not self.names:
            return
        self.offset -= (event.delta / 120) * self.ROW_HEIGHT * self.SCROLL_STEP
        self._redraw()

    def _on_scrollbar(self, *args):
        total = self._content_height()
        if args[0] == "moveto":
            self.offset = float(args[1]) * total
        elif args[0] == "scroll":
            step = self.ROW_HEIGHT if args[2] == "units" else self.canvas.winfo_height()
            self.offset += int(args[1]) * step
        self._redraw()

    def _on_motion(self, event):
        index = self._row_at(event.y)
        if index != self.hover:
            self.hover = index
            self._redraw()

    def _on_leave(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        if self.hover is not None:
            self.hover = None
            self._redraw()

    def _on_click(self, event):
        index = self._row_at(event.y)
        if index is not None:
            name = self.names[index]
            self.selected = name
            self._redraw()
            self.on_select(name)

class InstrumentPicker(ctk.CTkFrame):
    """Instrument dropdown: stable instruments first, unstable ones last with a red "(unstable)" tag."""
    ROW_HEIGHT = 40          # generous estimate, used to size the popup

    def __init__(self, parent, values, unstable, command=None, width=230, enabled=True):
        super().__init__(parent, width=width, height=34, corner_radius=8,
                         fg_color=CARD, border_width=1, border_color=BORDER)
        self.pack_propagate(False)
        self.design_width = width
        self.command = command
        self.enabled = enabled
        self.unstable = set(unstable)
        stable_values = sorted((v for v in values if v not in self.unstable), key=str.lower)
        unstable_values = sorted((v for v in values if v in self.unstable), key=str.lower)
        self.values = stable_values + unstable_values
        self.value = self.values[0] if self.values else ""
        self.popup = None

        self.name_label = ctk.CTkLabel(self, text="", anchor="w", font=ctk.CTkFont("Segoe UI", 13),
                                       text_color=TEXT if enabled else SUBTLE)
        self.name_label.pack(side="left", padx=(12, 0))
        self.tag_label = ctk.CTkLabel(self, text="", text_color=DANGER,
                                      font=ctk.CTkFont("Segoe UI", 12, "bold"))
        self.tag_label.pack(side="left", padx=(6, 0))
        self.arrow_label = ctk.CTkLabel(self, text="▾", text_color=MUTED,
                                        font=ctk.CTkFont("Segoe UI", 14))
        self.arrow_label.pack(side="right", padx=(0, 10))
        for widget in (self, self.name_label, self.tag_label, self.arrow_label):
            widget.bind("<Button-1>", self._toggle)

        root = self.winfo_toplevel()
        root.bind("<Button-1>", self._on_root_click, add="+")
        root.bind("<Escape>", lambda e: self._close(), add="+")
        self.set(self.value)

    def get(self):
        return self.value

    def set(self, value):
        self.value = value
        self.name_label.configure(text=value)
        self.tag_label.configure(text="(unstable)" if value in self.unstable else "")

    def _toggle(self, event=None):
        if not self.enabled:
            return
        if self.popup is not None:
            self._close()
        else:
            self._open()

    def _open(self):
        root = self.winfo_toplevel()
        self.update_idletasks()
        x = self.winfo_rootx() - root.winfo_rootx()
        y = self.winfo_rooty() - root.winfo_rooty() + self.winfo_height() + 4
        list_height = min(len(self.values) * self.ROW_HEIGHT + 12, 320)

        popup = tk.Frame(root, bg=BORDER, bd=0, highlightthickness=0)   # 1px border look
        scroller = ctk.CTkScrollableFrame(popup, fg_color=CARD, corner_radius=0,
                                          width=self.design_width - 22, height=list_height,
                                          **SCROLL_STYLE)
        scroller.pack(padx=1, pady=1)
        for value in self.values:
            self._build_row(scroller, value)
        popup.place(x=x, y=y)
        popup.lift()
        self.popup = popup

    def _build_row(self, parent, value):
        selected = value == self.value
        row = ctk.CTkFrame(parent, fg_color=SELECTED_COLOR if selected else "transparent",
                           corner_radius=6, height=self.ROW_HEIGHT - 2)
        row.pack(fill="x", pady=1)
        name = ctk.CTkLabel(row, text=value, text_color=TEXT, anchor="w",
                            font=ctk.CTkFont("Segoe UI", 13))
        name.pack(side="left", padx=(10, 0), pady=3)
        widgets = [row, name]
        if value in self.unstable:
            tag = ctk.CTkLabel(row, text="(unstable)", text_color=DANGER,
                               font=ctk.CTkFont("Segoe UI", 12, "bold"))
            tag.pack(side="left", padx=(6, 0))
            widgets.append(tag)

        def on_enter(event, frame=row, is_selected=selected):
            if not is_selected:
                frame.configure(fg_color=HOVER_COLOR)

        def on_leave(event, frame=row, is_selected=selected):
            if not is_selected:
                frame.configure(fg_color="transparent")

        for widget in widgets:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
            widget.bind("<Button-1>", lambda e, v=value: self._select(v))

    def _select(self, value):
        self.set(value)
        self.after(10, self._close)          # let the click finish before the popup is destroyed
        if self.command:
            self.command(value)

    def _on_root_click(self, event):
        if self.popup is None:
            return
        path = str(event.widget)
        if path.startswith(str(self.popup)) or path.startswith(str(self)):
            return
        self._close()

    def _close(self):
        if self.popup is not None:
            try:
                self.popup.destroy()
            except Exception:
                pass
            self.popup = None


class ConfirmDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, message, on_confirm):
        super().__init__(parent)
        begin_draw(self)
        self.on_confirm = on_confirm
        self.result = False
        self.title(title)
        self.geometry("400x180")
        self.resizable(False, False)
        self.configure(fg_color=SIDEBAR)
        self.transient(parent)
        self.grab_set()
        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - 400) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 180) // 2
        self.geometry(f"400x180+{px}+{py}")
        ctk.CTkLabel(self, text=message, font=ctk.CTkFont(size=14),
                     text_color=TEXT, wraplength=350).pack(pady=(30, 20))
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Yes, Delete", width=140, height=40,
                      fg_color=DANGER, hover_color=DANGER_HOVER, text_color=ON_ACCENT,
                      font=ctk.CTkFont(size=13, weight="bold"),
                      command=self.confirm).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", width=140, height=40,
                      font=ctk.CTkFont(size=13), command=self.cancel,
                      **NEUTRAL_BUTTON).pack(side="left", padx=10)
        self.bind("<Escape>", lambda e: self.cancel())
        end_draw(self)

    def confirm(self):
        self.result = True
        self.on_confirm()
        self.destroy()

    def cancel(self):
        self.result = False
        self.destroy()


class StopHintDialog(ctk.CTkToplevel):
    def __init__(self, parent, settings_path, on_ok):
        super().__init__(parent)
        begin_draw(self)
        self.settings_path = settings_path
        self.on_ok = on_ok
        self.title("How to Stop")
        self.geometry("400x200")
        self.resizable(False, False)
        self.configure(fg_color=SIDEBAR)
        self.transient(parent)
        self.grab_set()
        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - 400) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 200) // 2
        self.geometry(f"400x200+{px}+{py}")
        ctk.CTkLabel(self, text="Music is about to start playing!",
                     font=ctk.CTkFont("Segoe UI", 14, "bold"), text_color=TEXT).pack(pady=(22, 6))
        ctk.CTkLabel(self,
                     text='To stop playback at any time, press  ESC  (or  "  ).\n'
                          "It works even while the game window has focus.",
                     font=ctk.CTkFont("Segoe UI", 12), text_color=MUTED,
                     justify="center", wraplength=360).pack(pady=(0, 14))
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=20)
        self.dont_show_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(bottom, text="Don't show again", variable=self.dont_show_var,
                        text_color=MUTED, font=ctk.CTkFont("Segoe UI", 11),
                        **CHECKBOX_STYLE).pack(side="left")
        ctk.CTkButton(bottom, text="OK, Start", width=110, height=34,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ON_ACCENT,
                      font=ctk.CTkFont("Segoe UI", 12, "bold"),
                      command=self._ok).pack(side="right")
        end_draw(self)

    def _ok(self):
        if self.dont_show_var.get():
            try:
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["settings"][0]["hide_stop_hint"] = True
                with open(self.settings_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
            except Exception:
                pass
        self.destroy()
        self.on_ok()


# ================= MAIN APP =================

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        begin_draw(self)
        self.title("Genshin Auto Instrument Player")
        self._center_window(1100, 600)
        self.resizable(False, False)
        self.configure(fg_color=BG)

        self.buttons = {}
        self.selected_music_name = None
        self.current_instrument = None
        self.sound_cache = {}
        self.key_queue = queue.Queue()
        self.processing = True
        self.is_playing = False
        self.play_thread = None
        self.current_bpm = None
        self._play_generation = 0        # bumped on every start/stop so stale threads can't touch the UI
        self._importing = False
        self.settings_dialog = None      # built once, then only shown/hidden (no rebuild lag)

        self.timer_start = 0
        self.timer_ms = 0

        self.sheets_dir = writable_path("sheets")
        self.sounds_dir = resource_path("key_sounds")
        self.settings_path = writable_path("settings.json")
        self._ensure_settings_file()
        self._copy_default_sheets_if_needed()

        self.after(5, self.process_key_queue)
        self.build_ui()
        self.bind("<Unmap>", self._on_minimize)
        self.bind("<Map>", self._on_restore)
        self.bind_all("<Delete>", self._on_delete_key)
        self.bind_all("<KeyPress>", self.on_key_press)
        end_draw(self)

        self.after(1200, self._prebuild_settings)
        # start the update check once the window is up (1.5 s), so its result can never arrive too early       
        self.after(1500, lambda: threading.Thread(target=self._check_for_update, daemon=True).start())

    def _on_minimize(self, event=None):
        if event is not None and event.widget is not self:
            return
        try:
            self.attributes("-alpha", 0.0)       # invisible while minimized / being restored
        except Exception:
            pass

    def _on_restore(self, event=None):
        if event is not None and event.widget is not self:
            return
        self.music_list._redraw()
        self.update()                            # let every widget finish drawing while invisible
        self.after(40, lambda: self.attributes("-alpha", 1.0))

    def _center_window(self, width, height):
        try:
            scale = self._get_window_scaling()
        except Exception:
            scale = 1.0
        x = max((self.winfo_screenwidth() - int(width * scale)) // 2, 0)
        y = max((self.winfo_screenheight() - int(height * scale)) // 2, 0)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _copy_default_sheets_if_needed(self):
        try:
            bundled_sheets = resource_path("sheets")

            if not os.path.exists(bundled_sheets):
                return

            for file in os.listdir(bundled_sheets):
                source = os.path.join(bundled_sheets, file)
                target = os.path.join(self.sheets_dir, file)

                if not os.path.exists(target):
                    import shutil
                    shutil.copy2(source, target)

        except Exception as e:
            print("Default sheet copy error:", e)

    def build_ui(self):
        try:
            from PIL import Image, ImageTk
            icon = ImageTk.PhotoImage(Image.open(resource_path("assets/logo.png")).resize((64, 64)))
            self.wm_iconbitmap()
            self.after(200, lambda: self.iconphoto(True, icon))  # type: ignore
            self._icon_ref = icon
        except Exception:
            pass
        self.main = ctk.CTkFrame(self, fg_color=BG)
        self.main.pack(fill="both", expand=True)
        self.build_sidebar()
        self.build_content()

    def _ensure_settings_file(self):
        os.makedirs(self.sheets_dir, exist_ok=True)
        if not os.path.exists(self.settings_path):
            default = {
                "settings": [{
                    "Default_keys": "q w e r t y u a s d f g h j z x c v b n m",
                    "language": "en",
                    "keys": "q w e r t y u a s d f g h j z x c v b n m",
                    "changelog": "",
                    "version": "3.0",
                    "target_window": "",
                    "hide_stop_hint": False
                }]
            }
            try:
                with open(self.settings_path, "w", encoding="utf-8") as f:
                    json.dump(default, f, indent=4)
            except Exception as e:
                # the UI does not exist yet at this point, so only log it
                print(f"Settings file error: {e}")

    def build_sidebar(self):
        sidebar = ctk.CTkFrame(self.main, width=230, fg_color=SIDEBAR, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        ctk.CTkLabel(sidebar, text="-🎵Library🎶-",
                     font=ctk.CTkFont(size=20, weight="bold"), text_color=TEXT).pack(pady=(20, 10))
        self.music_list = MusicList(sidebar, on_select=self.select_music)
        self.music_list.pack(fill="both", expand=True, padx=10, pady=5)
        self.refresh_music_list()
        self.status_label = ctk.CTkLabel(sidebar, text="Ready", text_color=MUTED,
                                          font=ctk.CTkFont(size=11))
        self.status_label.pack(pady=5)
        # shown only when a newer version exists (see _check_for_update)
        self.update_btn = ctk.CTkButton(sidebar, text="", height=36, fg_color=ACCENT,
                                        hover_color=ACCENT_HOVER, text_color=ON_ACCENT,
                                        font=ctk.CTkFont(size=12, weight="bold"),
                                        command=lambda: webbrowser.open(GITHUB_REPO_URL + "/releases"))
        self.add_sheet_btn = ctk.CTkButton(sidebar, text="📂 Add Sheet", height=36,
                                           command=self._add_sheet, **NEUTRAL_BUTTON)
        self.add_sheet_btn.pack(fill="x", padx=15, pady=(5, 2))
        ctk.CTkButton(sidebar, text="⚙ Settings", height=36,
                      command=self.open_settings, **NEUTRAL_BUTTON).pack(fill="x", padx=15, pady=(2, 15))

    def refresh_music_list(self):
        self.selected_music_name = None
        try:
            names = sorted(os.listdir(self.sheets_dir), key=str.lower)
        except FileNotFoundError:
            self.music_list.set_items([], "'sheets' folder not found", DANGER)
            return
        self.music_list.set_items(names, "No music files found")

    def _typing_in_entry(self):
        try:
            widget = self.focus_get()
            return widget is not None and widget.winfo_class() in ("Entry", "Text")
        except Exception:
            return False

    def _on_delete_key(self, event=None):
        if self._typing_in_entry():
            return
        if not self.selected_music_name:
            return
        if self.is_playing:
            return
        if self.focus_get() is None:
            return
        ConfirmDialog(
            self, "Delete Music",
            f"Are you sure you want to delete '{display_name(self.selected_music_name)}'?\n\nThis action cannot be undone.",
            lambda: self._perform_delete(self.selected_music_name)
        )

    def _perform_delete(self, name):
        try:
            os.remove(os.path.join(self.sheets_dir, name))
            if self.selected_music_name == name:
                self.selected_music_name = None
            self.refresh_music_list()
            self.update_status(f"Deleted: {display_name(name)}")
        except Exception as e:
            self.update_status(f"Delete error: {str(e)[:20]}")

    def select_music(self, name):
        self.selected_music_name = name
        display = display_name(name)

        if hasattr(self, '_status_after_id'):
            try:
                self.after_cancel(self._status_after_id)
            except Exception:
                pass

        if len(display) > 30:
            truncated = display[:40] + "..." if len(display) > 40 else display
            self.status_label.configure(text="Selected:")
            self.after(800, lambda: self.status_label.configure(text=truncated))
            self._status_after_id = self.after(2300, lambda: self.status_label.configure(text="DEL to delete"))
        else:
            self.status_label.configure(text=f"Selected: {display}")
            self._status_after_id = self.after(1500, lambda: self.status_label.configure(text="DEL to delete"))

    def build_content(self):
        content = ctk.CTkFrame(self.main, fg_color=BG, corner_radius=0)
        content.pack(side="right", fill="both", expand=True)
        top_bar = ctk.CTkFrame(content, fg_color="transparent", height=60)
        top_bar.pack(fill="x", padx=20, pady=15)
        ctk.CTkLabel(top_bar, text="Instrument:", text_color=TEXT,
                     font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 10))
        try:
            instruments = sorted(os.listdir(self.sounds_dir))
        except FileNotFoundError:
            instruments = []
        if instruments:
            self.instrument_box = InstrumentPicker(top_bar, values=instruments,
                                                   unstable=UNSTABLE_INSTRUMENTS,
                                                   command=self.change_instrument)
        else:
            self.instrument_box = InstrumentPicker(top_bar, values=["No instruments found"],
                                                   unstable=[], enabled=False)
        self.instrument_box.pack(side="left")

        if "Lyre" in instruments:
            self.instrument_box.set("Lyre")
            self.current_instrument = "Lyre"
        elif instruments:
            self.current_instrument = self.instrument_box.get()
            if self.current_instrument in UNSTABLE_INSTRUMENTS:
                self.update_status(f"{self.current_instrument} — Not stable, may have issues")

        if self.current_instrument:
            self._preload_instrument(self.current_instrument)

        self.bpm_label = ctk.CTkLabel(top_bar, text="", text_color=MUTED, font=ctk.CTkFont(size=12))
        self.bpm_label.pack(side="left", padx=15)
        self.play_indicator = ctk.CTkLabel(top_bar, text="", text_color=DANGER,
                                            font=ctk.CTkFont(size=12, weight="bold"))
        self.play_indicator.pack(side="left", padx=10)
        self.midi_btn = ctk.CTkButton(top_bar, text="🎼  Import MIDI", width=140, height=34,
                                corner_radius=10, fg_color=PLAY_1, hover_color=PLAY_1_HOVER,
                                text_color=ON_ACCENT, font=ctk.CTkFont(size=13, weight="bold"),
                                command=self.import_midi_button)
        self.midi_btn.pack(side="right")
        self.build_button_grid(content)
        self.build_play_controls(content)

    def build_button_grid(self, parent):
        self.buttons = {key: None for key in KEY_ORDER}   # only used for key lookups
        self.keypad = KeyPad(parent, lambda k: self.trigger_button(k, show_note=True))
        self.keypad.pack(pady=25)

    def build_play_controls(self, parent):
        play_container = ctk.CTkFrame(parent, fg_color=BG)
        play_container.pack(side="right", padx=40, pady=20)
        self.play_here_btn = ctk.CTkButton(play_container, text="Play Here", width=140, height=45,
                                            corner_radius=10, fg_color=PLAY_1, hover_color=PLAY_1_HOVER,
                                            text_color=ON_ACCENT, font=ctk.CTkFont(size=14, weight="bold"),
                                            command=self.play_here)
        self.play_here_btn.pack(side="left", padx=8)
        self.play_game_btn = ctk.CTkButton(play_container, text="Play at Game", width=140, height=45,
                                            corner_radius=10, fg_color=PLAY_2, hover_color=PLAY_2_HOVER,
                                            text_color=ON_ACCENT, font=ctk.CTkFont(size=14, weight="bold"),
                                            command=self.play_game)
        self.play_game_btn.pack(side="left", padx=8)

    def _show_note(self, key, note):
        label_text = f"🎵{note}"
        if not hasattr(self, "_note_labels"):
            self._note_labels = {}
        if key in self._note_labels:
            try:
                self._note_labels[key].configure(text=label_text)
            except Exception:
                pass
            return
        lbl = ctk.CTkLabel(self.play_indicator.master, text=label_text,
                            text_color=ACCENT, font=ctk.CTkFont(size=13, weight="bold"))
        lbl.pack(side="left", padx=4)
        self._note_labels[key] = lbl
        delay = int((ANIMATION_DURATION / 80) * 1000) + 100
        self.after(delay, lambda k=key: self._remove_note(k))

    def _remove_note(self, key):
        if hasattr(self, "_note_labels") and key in self._note_labels:
            try:
                self._note_labels[key].destroy()
            except Exception:
                pass
            del self._note_labels[key]

    # ================= IMPORT =================

    def _add_sheet(self):
        from tkinter import filedialog
        import shutil
        paths = filedialog.askopenfilenames(
            title="Select Sheet or MIDI Files",
            filetypes=[
                ("All supported", "*.json *.txt *.genshinsheet *.skysheet *.mid *.midi"),
                ("Sheet files", "*.json *.txt *.genshinsheet *.skysheet"),
                ("MIDI files", "*.mid *.midi"),
            ]
        )
        added = 0
        midi_paths = []
        for path in paths:
            if path.lower().endswith(MIDI_EXTENSIONS):
                midi_paths.append(path)
                continue
            try:
                shutil.copy2(path, os.path.join(self.sheets_dir, os.path.basename(path)))
                added += 1
            except Exception as e:
                self.update_status(f"Error: {str(e)[:20]}")
        added += self._import_midi_files(midi_paths)
        if added:
            self.refresh_music_list()
            self.update_status(f"{added} file(s) added")

    def _import_midi_files(self, paths):
        """Open the import dialog once per file, one after another. Returns how many were saved."""
        if self._importing or not paths:
            return 0
        unique = {}
        for path in paths:                       # the same file can never be queued twice
            unique.setdefault(os.path.normcase(os.path.abspath(path)), path)
        paths = list(unique.values())

        self._importing = True
        added = 0
        try:
            for number, path in enumerate(paths, 1):
                if self._import_midi_file(path, number, len(paths)):
                    added += 1
        finally:
            self._importing = False
        return added

    def _import_midi_file(self, path, number=1, total=1):
        try:
            midi_info = load_midi(path)
        except Exception as e:
            self.update_status(f"MIDI error: {str(e)[:20]}")
            return False
        if not midi_info.channels:
            self.update_status("MIDI has no notes")
            return False
        dialog = MidiImportDialog(self, path, midi_info, self.sheets_dir, number, total)
        self.wait_window(dialog)
        try:                                     # make sure no finished dialog can ever linger
            if dialog.winfo_exists():
                dialog.destroy()
        except Exception:
            pass
        return bool(dialog.saved_name)

    def import_midi_button(self):
        from tkinter import filedialog
        paths = filedialog.askopenfilenames(
            title="Select MIDI Files",
            filetypes=[("MIDI files", "*.mid *.midi")]
        )
        added = self._import_midi_files(list(paths))
        if added:
            self.refresh_music_list()
            self.update_status(f"{added} MIDI imported")

    # ================= UPDATE CHECK =================

    def _check_for_update(self):
        try:
            remote = fetch_remote_version()
            local = str(load_bundled_info().get("version", "0"))
            if is_newer_version(remote, local):
                self.after(0, lambda: self._show_update_banner(remote))
        except Exception:
            pass                                 # offline or GitHub unreachable: stay silent

    def _show_update_banner(self, version):
        self.update_btn.configure(text=f"🎉 New version v{version}")
        self.update_btn.pack(fill="x", padx=15, pady=(0, 4), before=self.add_sheet_btn)

    # ================= CORE =================

    def change_instrument(self, choice):
        self._preload_instrument(choice)
        self.current_instrument = choice
        if choice in UNSTABLE_INSTRUMENTS:
            self.update_status(f"{choice} — Not stable, may have issues")
        else:
            self.update_status(f"Instrument: {choice}")

    def _prebuild_settings(self):
        if self.settings_dialog is None:
            self.settings_dialog = SettingsDialog(self, self.settings_path)
        return self.settings_dialog

    def open_settings(self):
        self._prebuild_settings().show()

    def update_status(self, message):
        if hasattr(self, '_status_after_id'):
            try:
                self.after_cancel(self._status_after_id)
            except:
                pass

        self.status_label.configure(text=message)
        self._status_after_id = self.after(3000, lambda: self.status_label.configure(text="Ready"))

    def _should_show_stop_hint(self):
        try:
            with open(self.settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return not data["settings"][0].get("hide_stop_hint", False)
        except Exception:
            return True

    # ================= KEY HANDLING =================

    def on_key_press(self, event):
        """Keys pressed while this window has focus (the game uses the global watcher instead)."""
        if self._typing_in_entry():
            return

        if self.is_playing:
            if event.keysym == "Escape" or event.char == '"':
                self.stop_playback()
            return

        key = event.char.lower()
        if key in self.buttons:
            self.trigger_button(key, show_note=True)

    def press_key(self, key):
        """Called from worker threads: the sound plays right away (pygame is thread-safe),
        only the animation goes through the queue to the UI thread."""
        if key in self.buttons:
            self.play_sound(key)
            self.key_queue.put(key)

    def process_key_queue(self):
        try:
            while not self.key_queue.empty():
                key = self.key_queue.get_nowait()
                self.start_animation(key)
        except queue.Empty:
            pass
        if self.processing:
            self.after(5, self.process_key_queue)

    def trigger_button(self, key, show_note=False):
        self.play_sound(key)
        self.start_animation(key)
        if show_note and not self.is_playing:
            note = NOTE_NAMES.get(key, "")
            if note:
                self._show_note(key, note)

    def _get_sound(self, instrument, index):
        cache_key = (instrument, index)
        sound = self.sound_cache.get(cache_key)
        if sound is None:
            path = os.path.join(self.sounds_dir, instrument, f"{index}.mp3")
            if not os.path.exists(path):
                return None
            sound = pygame.mixer.Sound(path)
            self.sound_cache[cache_key] = sound
        return sound

    def _preload_instrument(self, instrument):
        def worker():
            for index in range(21):
                try:
                    self._get_sound(instrument, index)
                except Exception:
                    pass
        threading.Thread(target=worker, daemon=True).start()

    def play_sound(self, key):
        if not self.current_instrument:
            return
        index = KEY_INDEX.get(key)
        if index is None:
            return
        try:
            sound = self._get_sound(self.current_instrument, index)
            if sound:
                sound.play()
        except Exception as e:
            print(f"Error playing sound: {e}")

    # ================= ANIMATION =================

    def start_animation(self, key):
        self.keypad.pulse(key)

    # ================= PLAYBACK =================

    def _get_target_window(self):
        try:
            with open(self.settings_path, "r", encoding="utf-8") as f:
                s = json.load(f)
            return s["settings"][0].get("target_window", "")
        except Exception:
            return ""

    def _is_target_focused(self, target_title):
        try:
            active = gw.getActiveWindow()
            return active is not None and active.title == target_title
        except Exception:
            return False

    def _wait_for_focus(self, target_title):
        while not self._is_target_focused(target_title):
            if not self.is_playing:
                return False
            time.sleep(0.1)
        return True

    def _sleep(self, seconds):
        """Sleep that wakes up immediately when playback is stopped. False = stopped."""
        end = time.perf_counter() + seconds
        while self.is_playing:
            remaining = end - time.perf_counter()
            if remaining <= 0:
                return True
            time.sleep(min(remaining, 0.02))
        return False

    def play_here(self):
        if not self.selected_music_name:
            self.update_status("Please select a music file")
            return
        if self.is_playing:
            self.stop_playback()
            return
        self._maybe_show_hint(mode="here")

    def play_game(self):
        if not self.selected_music_name:
            self.update_status("Please select a music file")
            return
        if self.is_playing:
            self.stop_playback()
            return
        target = self._get_target_window()
        if not target:
            self.update_status("No window selected — set it in Settings")
            return
        windows = gw.getWindowsWithTitle(target)
        if not windows:
            self.update_status("Window not found: open the game first")
            return
        self._maybe_show_hint(mode="game")

    def _maybe_show_hint(self, mode):
        if self._should_show_stop_hint():
            StopHintDialog(self, self.settings_path, on_ok=lambda: self.start_playback(mode))
        else:
            self.start_playback(mode)

    def start_playback(self, mode):
        self.is_playing = True
        self._play_generation += 1
        generation = self._play_generation
        self.play_indicator.configure(text="PLAYING  ·  press ESC to stop")
        self.play_here_btn.configure(text="⏹ Stop", command=self.stop_playback)
        self.play_game_btn.configure(text="⏹ Stop", command=self.stop_playback)
        self._start_stop_watcher(generation)
        self.play_thread = threading.Thread(target=self._playback_worker, args=(mode, generation), daemon=True)
        self.play_thread.start()

    def stop_playback(self, message="Stopped"):
        self.is_playing = False
        self._play_generation += 1               # retires the worker and the stop-key watcher
        self.play_indicator.configure(text="")
        self.bpm_label.configure(text="")
        self.play_here_btn.configure(text="Play Here", command=self.play_here)
        self.play_game_btn.configure(text="Play at Game", command=self.play_game)
        self.update_status(message)

    def _finish_playback(self, generation, message):
        if generation == self._play_generation:  # ignore threads of an older playback
            self.stop_playback(message or "Stopped")

    def _start_stop_watcher(self, generation):
        """Own thread that polls ESC (and the '"' key) for the whole playback. It does not depend
        on window focus or on keyboard hooks, so it also works while the game is in front."""
        if not hasattr(ctypes, "windll"):
            return
        combos = get_stop_key_combos()

        def watcher():
            user32 = ctypes.windll.user32
            # ignore a key that is already held down (e.g. ESC that just closed a dialog)
            while generation == self._play_generation and stop_keys_pressed(user32, combos):
                time.sleep(0.01)
            while generation == self._play_generation and self.is_playing:
                if stop_keys_pressed(user32, combos):
                    self.is_playing = False      # every playback loop checks this flag
                    return
                time.sleep(0.005)

        threading.Thread(target=watcher, daemon=True).start()

    def _playback_worker(self, mode, generation):
        message = None
        try:
            path = os.path.join(self.sheets_dir, self.selected_music_name)  # type: ignore
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not data:
                raise ValueError("Empty music file")
            target_title = self._get_target_window() if mode == "game" else ""
            if "notes" in data[0]:
                self.current_bpm = None
                self.after(0, lambda: self.bpm_label.configure(text=""))
                self._play_notes_format(data[0]["notes"], mode, target_title)
            elif "columns" in data[0]:
                bpm = data[0].get("bpm", 120)
                self.current_bpm = bpm
                self.after(0, lambda: self.bpm_label.configure(text=f"{bpm} BPM"))
                self._play_columns_format(data[0]["columns"], bpm, mode, target_title)
            elif "songNotes" in data[0]:
                bpm = data[0].get("bpm", 120)
                self.current_bpm = bpm
                self.after(0, lambda: self.bpm_label.configure(text=f"{bpm} BPM"))
                self._play_song_notes_format(data[0]["songNotes"], mode, target_title)
            else:
                print(f"DEBUG: unknown format, keys={list(data[0].keys()) if isinstance(data, list) else data}")
                raise ValueError("Unknown format")
            if self.is_playing:                  # still playing at the end = the song finished by itself
                message = "Finished"
        except FileNotFoundError:
            message = "File not found"
        except json.JSONDecodeError:
            message = "Invalid JSON"
        except Exception as e:
            print(f"PLAYBACK ERROR:\n{traceback.format_exc()}")
            message = f"Error: {str(e)[:60]}"
        finally:
            try:
                self.after(0, lambda m=message: self._finish_playback(generation, m))
            except Exception:
                pass

    def _play_columns_format(self, columns, bpm, mode, target_title=""):
        bps = bpm / 60
        wait = 1 / bps
        min_wait = MIN_EVENT_GAP_MS / 1000
        for column in columns:
            if not self.is_playing:
                break
            if mode == "game" and target_title and not self._is_target_focused(target_title):
                self.after(0, lambda: self.update_status("Paused — focus lost"))
                if not self._wait_for_focus(target_title):
                    break
                self.after(0, lambda: self.update_status("Resumed"))
            tempo = TEMPO_DICT.get(column[0], 1)
            wait_time = max(wait / tempo, min_wait)
            if not column[1]:
                if not self._sleep(wait_time):
                    break
                continue
            keys_to_press = []
            for note in column[1]:
                note_num = str(note[0])
                if note_num in NUMBERS:
                    idx = NUMBERS.index(note_num)
                    keys_to_press.append(KEYS[idx])
            if not self.is_playing:
                break
            if mode == "here":
                for key in keys_to_press:
                    self.press_key(key)
            else:
                for key in keys_to_press:
                    pyautogui.press(key)
                    self.key_queue.put(key)
            if not self._sleep(wait_time):
                break

    def _send_keys(self, keys, mode):
        if not self.is_playing:
            return
        if mode == "here":
            for key in keys:
                self.press_key(key)
        else:
            for key in keys:
                pyautogui.keyDown(key)
            for key in keys:
                pyautogui.keyUp(key)
            for key in keys:
                self.key_queue.put(key)

    def _run_timeline(self, events, mode, target_title=""):
        """events: {time_ms: [keys]}. Plays them on a real-time clock. The game window focus is only
        checked right before a chord is sent (not every few ms), and playback pauses while it is lost."""
        events = merge_close_events(events)
        start = time.perf_counter()
        for note_time in sorted(events):
            while True:
                if not self.is_playing:
                    return
                remaining = note_time / 1000 - (time.perf_counter() - start)
                if remaining > 0:
                    time.sleep(min(remaining, 0.005))
                    continue
                if mode == "game" and target_title and not self._is_target_focused(target_title):
                    pause_start = time.perf_counter()
                    self.after(0, lambda: self.update_status("Paused — focus lost"))
                    if not self._wait_for_focus(target_title):
                        return
                    start += time.perf_counter() - pause_start   # don't skip notes after a pause
                    self.after(0, lambda: self.update_status("Resumed"))
                    continue
                break
            self._send_keys(events[note_time], mode)

    def _play_notes_format(self, notes, mode, target_title=""):
        events = {}
        for note in notes:
            index, time_ms = int(note[0]), int(note[1])
            if 0 <= index < len(KEY_ORDER):
                keys = events.setdefault(time_ms, [])
                if KEY_ORDER[index] not in keys:
                    keys.append(KEY_ORDER[index])
        self._run_timeline(events, mode, target_title)

    def _play_song_notes_format(self, notes, mode, target_title=""):
        if not notes:
            return

        first_time = min(note.get("time", 0) for note in notes)
        events = {}
        for note in notes:
            key_name = note.get("key", "")
            if "Key" not in key_name:
                continue
            key = SKY_KEY_MAP.get(key_name.split("Key")[-1])
            if not key:
                continue
            time_ms = note.get("time", 0) - first_time
            keys = events.setdefault(time_ms, [])
            if key not in keys:
                keys.append(key)
        self._run_timeline(events, mode, target_title)

    def destroy(self):
        self.processing = False
        self.is_playing = False
        self._play_generation += 1
        if self.play_thread and self.play_thread.is_alive():
            self.play_thread.join(timeout=1)
        super().destroy()


if __name__ == "__main__":
    try:
        ctypes.windll.winmm.timeBeginPeriod(1)
    except Exception:
        pass

    if not check_admin():
        request_admin_and_restart()
    ctk.set_appearance_mode(APPEARANCE_MODE)
    app = App()
    app.mainloop()