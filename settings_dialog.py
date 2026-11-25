import customtkinter as ctk
import datetime
import json
import os
import webbrowser
import threading
import sys

from theme import *

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    requests = None
    HAS_REQUESTS = False


def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS # type: ignore
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


GITHUB_RAW_VERSION_URL = (
    "https://raw.githubusercontent.com/MERT-CKR/Genshin-AutoLyrePlayer/main/settings.json"
)
GITHUB_REPO_URL   = "https://github.com/MERT-CKR/Genshin-AutoLyrePlayer"
DISCORD_URL       = "https://discord.gg/luvica0"
GITHUB_SPONSORS   = "https://github.com/sponsors/MERT-CKR"

KEY_LAYOUT = [
    ["q", "w", "e", "r", "t", "y", "u"],
    ["a", "s", "d", "f", "g", "h", "j"],
    ["z", "x", "c", "v", "b", "n", "m"],
]

ICON_GITHUB    = "⌥"
ICON_DISCORD   = "◈"
ICON_SOPONSORS = "🤍"
ICON_SAVE      = "💾"
ICON_RESET     = "↺"

WINDOW_WIDTH = 780
WINDOW_HEIGHT = 660


# ══════════════════════════════════════════════════════════════════════════════
# helpers shared with main.py
# ══════════════════════════════════════════════════════════════════════════════
def parse_version(text):
    """'3.10' -> (3, 10). Compares numerically, so 3.10 is newer than 3.5."""
    parts = []
    for chunk in str(text).strip().lstrip("vV").split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def is_newer_version(remote, local):
    remote_parts, local_parts = parse_version(remote), parse_version(local)
    size = max(len(remote_parts), len(local_parts))
    remote_parts += (0,) * (size - len(remote_parts))
    local_parts += (0,) * (size - len(local_parts))
    return remote_parts > local_parts


def fetch_remote_version(timeout=5):
    """Version string from the settings.json on GitHub. Raises on any failure."""
    if not HAS_REQUESTS or requests is None:
        raise RuntimeError("'requests' module not installed")
    response = requests.get(GITHUB_RAW_VERSION_URL, timeout=timeout)
    response.raise_for_status()
    return str(response.json()["settings"][0]["version"])


def load_settings(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["settings"][0] if "settings" in data else {}
    except Exception:
        return {}


def load_bundled_info() -> dict:
    """Version and changelog always come from the settings.json shipped with the app."""
    try:
        with open(resource_path("settings.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["settings"][0]
    except Exception:
        return {}


def save_settings(path: str, new_keys: dict) -> bool:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "keys" in new_keys and new_keys["keys"]:
            data["settings"][0]["keys"] = new_keys["keys"]
        if "target_window" in new_keys:
            data["settings"][0]["target_window"] = new_keys["target_window"]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Save error: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
class WindowPickerDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_select):
        super().__init__(parent)
        begin_draw(self)
        self.on_select = on_select
        self.title("Select Game Window")
        self.geometry("420x380")
        self.resizable(False, False)
        self.configure(fg_color=BG)
        self.transient(parent)
        self.grab_set()

        px = parent.winfo_x() + (parent.winfo_width() - 420) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 380) // 2
        self.geometry(f"420x380+{max(px, 0)}+{max(py, 0)}")

        ctk.CTkLabel(self, text="Select the game window:", font=ctk.CTkFont("Segoe UI", 13),
                     text_color=TEXT).pack(pady=(20, 8))

        self.listbox = ctk.CTkScrollableFrame(self, fg_color=SIDEBAR, height=240, **SCROLL_STYLE)
        self.listbox.pack(fill="x", padx=20)

        self.selected_var = ctk.StringVar()
        self._load_windows()
        ctk.CTkButton(self, text="✓ Select", width=160, height=38, fg_color=ACCENT,
                      hover_color=ACCENT_HOVER, text_color=ON_ACCENT,
                      command=self._confirm).pack(pady=14)
        end_draw(self)

    def _load_windows(self):
        try:
            import pygetwindow as gw
            windows = sorted([w.title for w in gw.getAllWindows() if w.title.strip()])

            for title in windows:
                row = ctk.CTkFrame(self.listbox, fg_color="transparent")
                row.pack(fill="x", pady=1)
                ctk.CTkRadioButton(row, text=title, variable=self.selected_var, value=title,
                                   text_color=TEXT, font=ctk.CTkFont("Segoe UI", 11),
                                   **RADIO_STYLE).pack(anchor="w", padx=10, pady=3)

        except Exception as e:
            ctk.CTkLabel(self.listbox, text=f"Error: {e}", text_color=DANGER).pack()

    def _confirm(self):
        val = self.selected_var.get()
        if val:
            self.on_select(val)
            self.destroy()


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent, settings_path: str):
        super().__init__(parent)
        self.withdraw()                    # built once at startup, then only shown/hidden
        self._opening = False
        self.parent_window = parent

        self.settings_path = settings_path
        self.settings      = load_settings(settings_path)
        bundled = load_bundled_info()
        self.settings["version"] = bundled.get("version", self.settings.get("version", "?"))
        self.settings["changelog"] = bundled.get("changelog", self.settings.get("changelog", ""))
        self.key_entries   = {}   # key_name → CTkEntry widget

        # ── window ─────────────────────────────────────────────────────────
        self.title("Settings")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)
        self.configure(fg_color=BG)
        self.transient(parent)

        self._build()
        self.protocol("WM_DELETE_WINDOW", self.hide)
        self.bind("<Escape>", lambda e: self.hide())
        self.bind("<Unmap>", self._on_minimize)
        self.bind("<Map>", self._on_restore)

    def show(self):
        self._refresh()
        begin_draw(self)                   # invisible while it is mapped and drawn...
        self.update_idletasks()
        parent = self.parent_window
        px = parent.winfo_x() + (parent.winfo_width()  - WINDOW_WIDTH) // 2
        py = parent.winfo_y() + (parent.winfo_height() - WINDOW_HEIGHT) // 2
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{max(px, 0)}+{max(py, 0)}")
        self._opening = True
        self.deiconify()
        end_draw(self)                     # ...then everything appears at once
        self._opening = False
        self.lift()
        self.focus_set()

    def _on_minimize(self, event=None):
        if event is not None and event.widget is not self:
            return
        if self.state() == "withdrawn":          # closed with hide(), not minimized
            return
        try:
            self.attributes("-alpha", 0.0)       # invisible while minimized / being restored
        except Exception:
            pass

    def _on_restore(self, event=None):
        if event is not None and event.widget is not self:
            return
        if self._opening:                        # show() already handles its own fade-in
            return
        self.update()                            # let every widget finish drawing while invisible
        self.after(40, lambda: self.attributes("-alpha", 1.0))

    def hide(self):
        self.withdraw()

    def _refresh(self):
        """Re-read the saved settings every time the window is shown."""
        self.settings = load_settings(self.settings_path)
        bundled = load_bundled_info()
        self.settings["version"] = bundled.get("version", self.settings.get("version", "?"))
        self.settings["changelog"] = bundled.get("changelog", self.settings.get("changelog", ""))
        self._window_label.configure(text=f"Target: {self.settings.get('target_window') or 'Not set'}")
        saved_keys = self.settings.get("keys", "").split()
        flat_defaults = [key for row in KEY_LAYOUT for key in row]
        for index, key in enumerate(flat_defaults):
            entry = self.key_entries[key]
            entry.delete(0, "end")
            entry.insert(0, (saved_keys[index] if index < len(saved_keys) else key).upper())
            entry.configure(border_color=BORDER)
        self._keybind_status.configure(text="")

    def _build(self):
        header = ctk.CTkFrame(self, fg_color=SIDEBAR, corner_radius=0, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="⚙  Settings",
            font=ctk.CTkFont("Segoe UI", 20, "bold"),
            text_color=TEXT
        ).pack(side="left", padx=24, pady=14)

        ver = self.settings.get("version", "?")
        ctk.CTkLabel(
            header,
            text=f"v{ver}",
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=MUTED,
            fg_color=CARD,
            corner_radius=8,
            padx=10, pady=4
        ).pack(side="right", padx=20)

        self.tabview = ctk.CTkTabview(
            self,
            fg_color=BG,
            segmented_button_fg_color=SIDEBAR,
            segmented_button_selected_color=ACCENT_SOFT,
            segmented_button_selected_hover_color=SELECTED_COLOR,
            segmented_button_unselected_color=SIDEBAR,
            segmented_button_unselected_hover_color=HOVER_COLOR,
            text_color=TEXT,
        )
        self.tabview.pack(fill="both", expand=True, padx=16, pady=(8, 0))

        self.tabview.add("🎹  Key Bindings")
        self.tabview.add("🌐  About")
        self.tabview.add("🔄  Updates")

        self._build_keybindings(self.tabview.tab("🎹  Key Bindings"))
        self._build_about(self.tabview.tab("🌐  About"))
        self._build_updates(self.tabview.tab("🔄  Updates"))

    # ══════════════════════════════════════════════════════════════════════════
    # 1. KEY BINDINGS TAB
    # ══════════════════════════════════════════════════════════════════════════
    def _build_keybindings(self, tab):
        current_keys_str = self.settings.get("keys", "q w e r t y u a s d f g h j z x c v b n m")
        current_keys     = current_keys_str.split()

        flat_defaults = []
        for row in KEY_LAYOUT:
            flat_defaults.extend(row)

        ctk.CTkLabel(
            tab,
            text="Click any box and type a key to rebind. Press Save to apply.",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=MUTED
        ).pack(pady=(10, 6))

        grid_frame = ctk.CTkFrame(tab, fg_color=SIDEBAR, corner_radius=12)
        grid_frame.pack(padx=20, pady=(4, 12))
        ctk.CTkFrame(grid_frame, fg_color="transparent", height=8).grid(row=3, column=0, columnspan=7)

        for r, row in enumerate(KEY_LAYOUT):
            for c, default_key in enumerate(row):
                flat_idx = r * 7 + c
                current_binding = current_keys[flat_idx] if flat_idx < len(current_keys) else default_key

                cell = ctk.CTkFrame(grid_frame, fg_color="transparent", width=76, height=92)
                cell.grid(row=r, column=c, padx=6, pady=0)
                cell.grid_propagate(False)

                ctk.CTkLabel(
                    cell,
                    text=default_key.upper(),
                    font=ctk.CTkFont("Segoe UI", 9),
                    text_color=SUBTLE
                ).place(relx=0.5, y=4, anchor="n")

                # square key cap (small corner radius instead of a pill)
                entry = ctk.CTkEntry(
                    cell,
                    width=64,
                    height=64,
                    corner_radius=12,
                    fg_color=CARD,
                    border_color=BORDER,
                    border_width=2,
                    text_color=TEXT,
                    font=ctk.CTkFont("Segoe UI", 15, "bold"),
                    justify="center"
                )
                entry.insert(0, current_binding.upper())
                entry.place(relx=0.5, rely=0.64, anchor="center")

                def make_validate(e=entry, dk=default_key, idx=flat_idx):
                    def on_key(event, ent=e, i=idx):
                        if event.keysym in ("Tab", "Return", "Escape"):
                            return
                        char = event.char
                        if char and char.isprintable() and len(char) == 1:
                            ent.delete(0, "end")
                            ent.insert(0, char.upper())
                            ent.configure(border_color=ACCENT)
                            next_key = flat_defaults[i + 1] if i + 1 < len(flat_defaults) else None
                            if next_key and next_key in self.key_entries:
                                self.after(10, lambda: self.key_entries[next_key].focus_set())
                        return "break"
                    e.bind("<KeyPress>", on_key)
                    e.bind("<FocusIn>",  lambda ev, en=e: en.configure(border_color=ACCENT))
                    e.bind("<FocusOut>", lambda ev, en=e: en.configure(border_color=BORDER))
                make_validate()

                self.key_entries[default_key] = entry

        btn_row = ctk.CTkFrame(tab, fg_color="transparent")
        btn_row.pack(pady=12)

        ctk.CTkButton(
            btn_row,
            text=f"{ICON_RESET}  Reset to Default",
            width=160, height=38,
            font=ctk.CTkFont("Segoe UI", 13),
            command=self._reset_keys,
            **NEUTRAL_BUTTON
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btn_row,
            text=f"{ICON_SAVE}  Save Keys",
            width=160, height=38,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color=ON_ACCENT,
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            command=self._save_keys
        ).pack(side="left", padx=8)

        self._keybind_status = ctk.CTkLabel(
            tab, text="", text_color=SUCCESS, font=ctk.CTkFont("Segoe UI", 12)
        )
        self._keybind_status.pack()

        btn_row2 = ctk.CTkFrame(tab, fg_color="transparent")
        btn_row2.pack(pady=(4, 0))

        ctk.CTkButton(btn_row2, text="🎮  Select Game Window", width=190, height=36,
                      font=ctk.CTkFont("Segoe UI", 12),
                      command=self._open_window_picker, **NEUTRAL_BUTTON).pack(side="left", padx=4)

        ctk.CTkButton(btn_row2, text="📂  Open Sheets Folder", width=190, height=36,
                      font=ctk.CTkFont("Segoe UI", 12),
                      command=self._open_sheets_dir, **NEUTRAL_BUTTON).pack(side="left", padx=4)

        self._window_label = ctk.CTkLabel(
            tab, text=f"Target: {self.settings.get('target_window') or 'Not set'}",
            font=ctk.CTkFont("Segoe UI", 11), text_color=SUBTLE
        )
        self._window_label.pack()

    def _reset_keys(self):
        for key, entry in self.key_entries.items():
            entry.delete(0, "end")
            entry.insert(0, key.upper())
            entry.configure(border_color=BORDER)
        self._keybind_status.configure(text="↺ Defaults restored (not saved yet)", text_color=WARNING)

    def _save_keys(self):
        flat_defaults = []
        for row in KEY_LAYOUT:
            flat_defaults.extend(row)

        new_bindings = []
        for key in flat_defaults:
            val = self.key_entries[key].get().strip().lower()
            new_bindings.append(val if val else key)

        new_keys_str = " ".join(new_bindings)
        ok = save_settings(self.settings_path, {"keys": new_keys_str})

        if ok:
            self.settings["keys"] = new_keys_str
            self._keybind_status.configure(text="✓ Saved successfully!", text_color=SUCCESS)
        else:
            self._keybind_status.configure(text="❌ Save failed – check file permissions", text_color=DANGER)

        self.after(3000, lambda: self._keybind_status.configure(text=""))

    # ══════════════════════════════════════════════════════════════════════════
    # 2. ABOUT TAB
    # ══════════════════════════════════════════════════════════════════════════
    def _build_about(self, tab):
        from PIL import Image
        from customtkinter import CTkImage

        def load_icon(filename, size):
            try:
                return CTkImage(Image.open(resource_path(f"assets/{filename}")), size=size)
            except Exception:
                return None

        gh_img = load_icon("github.png", size=(50, 50))
        dc_img = load_icon("discord.png", size=(59, 50))
        ver = self.settings.get("version", "?")

        # ── footer first, so it stays anchored to the bottom ───────────────
        footer = ctk.CTkFrame(tab, fg_color="transparent")
        footer.pack(side="bottom", fill="x", pady=(0, 16))
        ctk.CTkFrame(footer, fg_color=DIVIDER, height=1).pack(fill="x", padx=60, pady=(0, 10))
        ctk.CTkLabel(footer, text="Made by Mert Çakır",
                     font=ctk.CTkFont("Segoe UI", 12, "bold"), text_color=MUTED).pack()
        ctk.CTkLabel(footer,
                     text=f"© {datetime.datetime.now().year} • Licensed under Apache License Version 2.0",
                     font=ctk.CTkFont("Segoe UI", 9), text_color=SUBTLE).pack(pady=(3, 0))

        # ── title + version ────────────────────────────────────────────────
        ctk.CTkLabel(tab, text="Genshin Auto Instrument Player",
                     font=ctk.CTkFont("Segoe UI", 30, "bold"), text_color=TEXT).pack(pady=(22, 6))
        # ctk.CTkLabel(tab, text=f"v{ver}", font=ctk.CTkFont("Segoe UI", 11, "bold"),
        #              text_color=ACCENT, fg_color=ACCENT_SOFT, corner_radius=8,
        #              padx=12, pady=3).pack()

        # ── description ────────────────────────────────────────────────────
        ctk.CTkLabel(tab,
                     text="An open-source auto-player for Genshin Impact's in-game instruments.\n"
                          "Select a sheet, pick an instrument, and let it play.",
                     font=ctk.CTkFont("Segoe UI", 12), text_color=MUTED,
                     justify="center").pack(pady=(14, 18))

        # ── link cards (2) ─────────────────────────────────────────────────
        links_frame = ctk.CTkFrame(tab, fg_color="transparent")
        links_frame.pack()

        links = [
            {"icon": "⌥", "img": gh_img, "label": "Source Code", "sub": "Source code & releases",
             "url": GITHUB_REPO_URL, "color": "#2ea043"},
            {"icon": "◈", "img": dc_img, "label": "Discord", "sub": "Ask Developer",
             "url": DISCORD_URL, "color": "#5865F2"},
        ]

        for link in links:
            card = ctk.CTkFrame(links_frame, fg_color=SIDEBAR, corner_radius=14,
                                width=180, height=126)
            card.pack(side="left", padx=10, pady=4)
            card.pack_propagate(False)

            if link["img"]:
                ctk.CTkLabel(card, image=link["img"], text="").place(relx=0.5, y=18, anchor="n")
            else:
                ctk.CTkLabel(card, text=link["icon"], font=ctk.CTkFont("Segoe UI", 32),
                             text_color=link["color"]).place(relx=0.5, y=18, anchor="n")

            ctk.CTkLabel(card, text=link["label"], font=ctk.CTkFont("Segoe UI", 13, "bold"),
                         text_color=TEXT).place(relx=0.5, y=77, anchor="n")
            ctk.CTkLabel(card, text=link["sub"], font=ctk.CTkFont("Segoe UI", 10),
                         text_color=SUBTLE).place(relx=0.5, y=99, anchor="n")

            for widget in card.winfo_children():
                widget.bind("<Button-1>", lambda e, u=link["url"]: webbrowser.open(u))
            card.bind("<Button-1>", lambda e, u=link["url"]: webbrowser.open(u))
            try:
                card.configure(cursor="hand2")
            except Exception:
                pass

        # ── changelog box ──────────────────────────────────────────────────
        changelog = self.settings.get("changelog", "")
        if changelog:
            box = ctk.CTkFrame(tab, fg_color=SIDEBAR, corner_radius=12)
            box.pack(padx=40, pady=(22, 0), fill="x")
            ctk.CTkLabel(box, text=f"✨  What's new in v{ver}",
                         font=ctk.CTkFont("Segoe UI", 12, "bold"),
                         text_color=TEXT).pack(pady=(12, 4))
            ctk.CTkLabel(box, text=changelog, font=ctk.CTkFont("Segoe UI", 11),
                         text_color=MUTED, wraplength=460,
                         justify="center").pack(padx=16, pady=(0, 12))

    # ══════════════════════════════════════════════════════════════════════════
    # 3. UPDATES TAB
    # ══════════════════════════════════════════════════════════════════════════
    def _build_updates(self, tab):
        self._update_frame = tab

        self._update_status_label = ctk.CTkLabel(
            tab,
            text="Check if a new version is available on GitHub.",
            font=ctk.CTkFont("Segoe UI", 13),
            text_color=MUTED
        )
        self._update_status_label.pack(pady=(40, 16))

        self._update_detail = ctk.CTkLabel(
            tab,
            text="",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=TEXT,
            wraplength=480,
            justify="center"
        )
        self._update_detail.pack(pady=(0, 20))

        self._check_btn = ctk.CTkButton(
            tab,
            text="🔍  Check for Updates",
            width=200, height=42,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color=ON_ACCENT,
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            command=self._check_updates
        )
        self._check_btn.pack()

        self._open_gh_btn = ctk.CTkButton(
            tab,
            text="⌥  Open GitHub Releases",
            width=200, height=38,
            font=ctk.CTkFont("Segoe UI", 12),
            command=lambda: webbrowser.open(GITHUB_REPO_URL + "/releases"),
            **NEUTRAL_BUTTON
        )
        self._open_gh_btn.pack(pady=(10, 0))

        ver = self.settings.get("version", "?")
        ctk.CTkLabel(
            tab,
            text=f"Current version: v{ver}",
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=SUBTLE
        ).pack(pady=(30, 0))

    def _open_window_picker(self):
        def on_select(title):
            save_settings(self.settings_path, {
                "keys": self.settings.get("keys", ""),
                "target_window": title
            })
            self.settings["target_window"] = title
            self._window_label.configure(text=f"Target: {title}")
        WindowPickerDialog(self, on_select)

    def _open_sheets_dir(self):
        import subprocess
        sheets_dir = os.path.join(os.path.dirname(self.settings_path), "sheets")
        try:
            os.makedirs(sheets_dir, exist_ok=True)
            subprocess.Popen(f'explorer.exe "{sheets_dir}"')
            self._keybind_status.configure(text="✓ Opened in Explorer", text_color=SUCCESS)
        except Exception as e:
            self._keybind_status.configure(text=f"❌ Error: {str(e)[:30]}", text_color=DANGER)
        self.after(3000, lambda: self._keybind_status.configure(text=""))

    def _check_updates(self):
        if not HAS_REQUESTS:
            self._update_status_label.configure(
                text="⚠  'requests' module not installed.",
                text_color=WARNING
            )
            return

        self._check_btn.configure(text="⏳  Checking...", state="disabled")
        self._update_status_label.configure(text="Fetching version from GitHub...", text_color=MUTED)
        self._update_detail.configure(text="")

        threading.Thread(target=self._fetch_version, daemon=True).start()

    def _fetch_version(self):
        try:
            remote = fetch_remote_version()
            local  = str(self.settings.get("version", "0"))

            if is_newer_version(remote, local):
                self.after(0, lambda: self._show_update_result(
                    f"🎉  New version available: v{remote}",
                    SUCCESS, show_open=True
                ))
            else:
                self.after(0, lambda: self._show_update_result(
                    f"✓  You're up to date! (v{local})",
                    SUCCESS, show_open=False
                ))
        except Exception as e:
            message = f"❌  Could not reach GitHub: {str(e)[:60]}"
            self.after(0, lambda m=message: self._show_update_result(m, DANGER, show_open=False))
        finally:
            self.after(0, lambda: self._check_btn.configure(
                text="🔍  Check for Updates", state="normal"
            ))

    def _show_update_result(self, msg, color, show_open):
        self._update_status_label.configure(text=msg, text_color=color)
        if show_open:
            self._update_detail.configure(
                text="Click 'Open GitHub Releases' below to download the latest version.",
                text_color=MUTED
            )