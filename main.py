from settings_dialog import SettingsDialog

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
import pygetwindow as gw

try:
    pygame.mixer.init()
    pygame.mixer.set_num_channels(64)
except Exception:
    print("Audio init failed")

pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False

# ================= CONSTANTS =================
BG = "#0B0D14"
SIDEBAR = "#121526"
BUTTON_BASE = "#3B426A"
PLAY_1 = "#5E5CE6"
PLAY_2 = "#3FBAC2"
TEXT = "#E6E8EF"
HOVER_COLOR = "#1E2240"
SELECTED_COLOR = "#2A2F55"

BUTTON_SIZE = 70
BUTTON_CORNER = 35
HOLDER_SIZE = 90

UNSTABLE_INSTRUMENTS = ["LingeringEuphonia", "Ukulele"]

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

TEMPO_DICT = {0: 1, 1: 2, 2: 4, 3: 8}

NUMBERS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12",
           "13", "14", "15", "16", "17", "18", "19", "20"][::-1]
KEYS = ["q", "w", "e", "r", "t", "y", "u", "a", "s", "d", "f", "g", "h", "j",
        "z", "x", "c", "v", "b", "n", "m"][::-1]

ANIMATION_DURATION = 12
ANIMATION_FRAME_TIME = 1000 // 80
STOP_KEYS = {"escape", "\""}

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
    ctk.set_appearance_mode("dark")
    win = ctk.CTk()
    win.title("Administrator Required")
    win.geometry("420x200")
    win.resizable(False, False)
    win.configure(fg_color="#121526")
    ctk.CTkLabel(win, text="Administrator Privileges Required",
                 font=ctk.CTkFont("Segoe UI", 15, "bold"), text_color="#E6E8EF").pack(pady=(28, 8))
    ctk.CTkLabel(win,
                 text="Genshin Impact runs as Administrator.\n"
                      "To send inputs to the game, this app also needs\n"
                      "Administrator privileges. Click Proceed to restart.",
                 font=ctk.CTkFont("Segoe UI", 12), text_color="#8890aa", justify="center").pack(pady=(0, 18))
    ctk.CTkButton(win, text="Proceed", width=220, height=38,
                  fg_color="#6C7CFF", hover_color="#5566dd", text_color="#E6E8EF",
                  font=ctk.CTkFont("Segoe UI", 13, "bold"),
                  command=lambda: _proceed(win)).pack()
    win.mainloop()
    sys.exit()


# ================= HELPERS =================

class AnimationState:
    def __init__(self, button, key):
        self.button = button
        self.key = key
        self.step = 0


class ConfirmDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, message, on_confirm):
        super().__init__(parent)
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
                      fg_color="#ff5555", hover_color="#cc4444", text_color=TEXT,
                      font=ctk.CTkFont(size=13, weight="bold"),
                      command=self.confirm).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", width=140, height=40,
                      fg_color=HOVER_COLOR, hover_color=SELECTED_COLOR, text_color=TEXT,
                      font=ctk.CTkFont(size=13), command=self.cancel).pack(side="left", padx=10)
        self.bind("<Escape>", lambda e: self.cancel())

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
                     text='To stop playback at any time, press  ESC  or  "  on your keyboard.\n'
                          "Switch back to this window to use the Stop button.",
                     font=ctk.CTkFont("Segoe UI", 12), text_color="#8890aa",
                     justify="center", wraplength=360).pack(pady=(0, 14))
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=20)
        self.dont_show_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(bottom, text="Don't show again", variable=self.dont_show_var,
                        text_color="#666a8a", font=ctk.CTkFont("Segoe UI", 11)).pack(side="left")
        ctk.CTkButton(bottom, text="OK, Start", width=110, height=34,
                      fg_color="#6C7CFF", hover_color="#5566dd", text_color=TEXT,
                      font=ctk.CTkFont("Segoe UI", 12, "bold"),
                      command=self._ok).pack(side="right")

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
        self.title("Genshin Auto Instrument Player")
        self.geometry("1100x600")
        self.resizable(False, False)
        self.configure(fg_color=BG)

        self.buttons = {}
        self.selected_music = None
        self.selected_music_name = None
        self.music_items = {}
        self.current_instrument = None
        self.key_queue = queue.Queue()
        self.processing = True
        self.is_playing = False
        self.play_thread = None
        self.current_bpm = None

        self.timer_start = 0
        self.timer_ms = 0
        self.active_animations = []
        self.animation_loop_running = False

        
        self.sheets_dir = writable_path("sheets")
        self.sounds_dir = resource_path("key_sounds")
        self.settings_path = writable_path("settings.json")
        self._ensure_settings_file()
        self._copy_default_sheets_if_needed()
        self._ensure_settings_file()

        self.after(5, self.process_key_queue)
        self.build_ui()
        self.bind_all("<Delete>", self._on_delete_key)
        self.bind_all("<KeyPress>", self.on_key_press)


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
                self.update_status(f"Settings file error: {e}")

    def build_sidebar(self):
        sidebar = ctk.CTkFrame(self.main, width=230, fg_color=SIDEBAR)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        ctk.CTkLabel(sidebar, text="-🎵Library🎶-",
                     font=ctk.CTkFont(size=20, weight="bold"), text_color=TEXT).pack(pady=(20, 10))
        self.list_container = ctk.CTkScrollableFrame(sidebar, fg_color="transparent", width=200, height=360)
        self.list_container.pack(fill="both", expand=True, padx=10, pady=5)
        self.refresh_music_list()
        self.status_label = ctk.CTkLabel(sidebar, text="Ready", text_color="#888",
                                          font=ctk.CTkFont(size=11))
        self.status_label.pack(pady=5)
        ctk.CTkButton(sidebar, text="📂 Add Sheet", height=36, fg_color=HOVER_COLOR,
                      hover_color=SELECTED_COLOR, text_color=TEXT,
                      command=self._add_sheet).pack(fill="x", padx=15, pady=(5, 2))
        ctk.CTkButton(sidebar, text="⚙ Settings", height=36, fg_color=HOVER_COLOR,
                      hover_color=SELECTED_COLOR, text_color=TEXT,
                      command=self.open_settings).pack(fill="x", padx=15, pady=(2, 15))

    def refresh_music_list(self):
        self.selected_music = None        
        self.selected_music_name = None  
        for widget in self.list_container.winfo_children():
            widget.destroy()
        self.music_items.clear()
        try:
            music_list = os.listdir(self.sheets_dir)
            if not music_list:
                ctk.CTkLabel(self.list_container, text="No music files found",
                             text_color="#888").pack(pady=20)
                return
        except FileNotFoundError:
            ctk.CTkLabel(self.list_container, text="'sheets' folder not found",
                         text_color="#ff5555").pack(pady=20)
            return
        for item in sorted(music_list):
            self.create_music_item(self.list_container, item)

    def create_music_item(self, parent, name):
        item_frame = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=8)
        item_frame.pack(fill="x", pady=3)
        display_name = name.replace(".json", "").replace(".txt", "").replace(".genshinsheet", "")
        label = ctk.CTkLabel(item_frame, text=display_name, text_color=TEXT,
                             anchor="w", justify="left", wraplength=180)
        label.pack(fill="x", padx=10, pady=8)

        def on_enter(e, frame=item_frame):
            if frame != self.selected_music:
                frame.configure(fg_color=HOVER_COLOR)

        def on_leave(e, frame=item_frame):
            if frame != self.selected_music:
                frame.configure(fg_color="transparent")

        for widget in [item_frame, label]:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
            widget.bind("<Button-1>", lambda e, n=name, f=item_frame: self.select_music(n, f))

        self.music_items[name] = item_frame

    def _on_delete_key(self, event=None):
        if not self.selected_music_name:
            return
        if self.is_playing:
            return
        if self.focus_get() is None:
            return
        display = self.selected_music_name.replace(".json", "").replace(".txt", "").replace(".genshinsheet", "")
        ConfirmDialog(
            self, "Delete Music",
            f"Are you sure you want to delete '{display}'?\n\nThis action cannot be undone.",
            lambda: self._perform_delete(self.selected_music_name)
        )

    def _perform_delete(self, name):
        try:
            os.remove(os.path.join(self.sheets_dir, name))
            if self.selected_music_name == name:
                self.selected_music = None
                self.selected_music_name = None
            self.refresh_music_list()
            self.update_status(f"Deleted: {name.replace('.json', '')}")
        except Exception as e:
            self.update_status(f"Delete error: {str(e)[:20]}")

    def select_music(self, name, frame):
        if self.selected_music:
            try:
                self.selected_music.configure(fg_color="transparent")
            except Exception:
                pass
        self.selected_music = frame
        self.selected_music_name = name
        frame.configure(fg_color=SELECTED_COLOR)
        
        display = name.replace('.json', '').replace('.txt', '').replace('.genshinsheet', '')
        
        if hasattr(self, '_status_after_id'):
            try:
                self.after_cancel(self._status_after_id)
            except:
                pass
        
        if len(display) > 30:
            truncated = display[:40] + "..." if len(display) > 40 else display
            self.status_label.configure(text="Selected:")
            self._status_after_id = self.after(800, lambda: self.status_label.configure(text=truncated))
            self._status_after_id = self.after(2300, lambda: self.status_label.configure(text="DEL to delete"))
        else:
            self.status_label.configure(text=f"Selected: {display}")
            self._status_after_id = self.after(1500, lambda: self.status_label.configure(text="DEL to delete"))

    def build_content(self):
        content = ctk.CTkFrame(self.main, fg_color=BG)
        content.pack(side="right", fill="both", expand=True)
        top_bar = ctk.CTkFrame(content, fg_color="transparent", height=60)
        top_bar.pack(fill="x", padx=20, pady=15)
        ctk.CTkLabel(top_bar, text="Instrument:", text_color=TEXT,
                     font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 10))
        try:
            instruments = sorted(os.listdir(self.sounds_dir))
            if not instruments:
                instruments = ["No instruments found"]
        except FileNotFoundError:
            instruments = ["Sounds folder missing"]
        self.instrument_box = ctk.CTkComboBox(top_bar, values=instruments, width=180,
                                               state="readonly", command=self.change_instrument)
        self.instrument_box.pack(side="left")
        if "Lyre" in instruments:
            self.instrument_box.set("Lyre")
            self.current_instrument = "Lyre"
        elif instruments and instruments[0] not in ["No instruments found", "Sounds folder missing"]:
            self.instrument_box.set(instruments[0])
            self.current_instrument = instruments[0]
        self.bpm_label = ctk.CTkLabel(top_bar, text="", text_color="#888", font=ctk.CTkFont(size=12))
        self.bpm_label.pack(side="left", padx=15)
        self.play_indicator = ctk.CTkLabel(top_bar, text="", text_color="#ff5555",
                                            font=ctk.CTkFont(size=12, weight="bold"))
        self.play_indicator.pack(side="left", padx=10)
        self.build_button_grid(content)
        self.build_play_controls(content)

    def build_button_grid(self, parent):
        grid = ctk.CTkFrame(parent, fg_color=BG)
        grid.pack(pady=25)
        for r, row in enumerate(KEY_LAYOUT):
            for c, key in enumerate(row):
                holder = ctk.CTkFrame(grid, width=HOLDER_SIZE, height=HOLDER_SIZE, fg_color=BG)
                holder.grid(row=r, column=c, padx=6, pady=6)
                holder.grid_propagate(False)
                btn = ctk.CTkButton(holder, text=key.upper(), width=BUTTON_SIZE, height=BUTTON_SIZE,
                                    corner_radius=BUTTON_CORNER, fg_color=BUTTON_BASE,
                                    hover_color=BUTTON_BASE, font=ctk.CTkFont(size=18, weight="bold"),
                                    text_color=TEXT, command=lambda k=key: self.trigger_button(k))
                btn.place(relx=0.5, rely=0.5, anchor="center")
                self.buttons[key] = btn

    def build_play_controls(self, parent):
        play_container = ctk.CTkFrame(parent, fg_color=BG)
        play_container.pack(side="right", padx=40, pady=20)
        self.play_here_btn = ctk.CTkButton(play_container, text="Play Here", width=140, height=45,
                                            corner_radius=10, fg_color=PLAY_1, hover_color="#4B4ACF",
                                            text_color=TEXT, font=ctk.CTkFont(size=14, weight="bold"),
                                            command=self.play_here)
        self.play_here_btn.pack(side="left", padx=8)
        self.play_game_btn = ctk.CTkButton(play_container, text="Play at Game", width=140, height=45,
                                            corner_radius=10, fg_color=PLAY_2, hover_color="#2F9BA8",
                                            text_color=TEXT, font=ctk.CTkFont(size=14, weight="bold"),
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
                            text_color="#6C7CFF", font=ctk.CTkFont(size=13, weight="bold"))
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

    def _add_sheet(self):
        from tkinter import filedialog
        import shutil
        paths = filedialog.askopenfilenames(
            title="Select Sheet Files",
            filetypes=[
                ("Sheet files", "*.json *.txt *.genshinsheet"),
                ("JSON files", "*.json"),
                ("TXT files", "*.txt"),
                ("GENSHINSHEET files", "*.genshinsheet")
            ]
        )
        added = 0
        for path in paths:
            try:
                shutil.copy2(path, os.path.join(self.sheets_dir, os.path.basename(path)))
                added += 1
            except Exception as e:
                self.update_status(f"Error: {str(e)[:20]}")
        if added:
            self.refresh_music_list()
            self.update_status(f"{added} file(s) added")

    # ================= CORE =================

    def change_instrument(self, choice):
        self.current_instrument = choice
        if choice in UNSTABLE_INSTRUMENTS:
            self.update_status(f"{choice} — Not stable, may have issues")
        else:
            self.update_status(f"Instrument: {choice}")

    def open_settings(self):
        SettingsDialog(self, self.settings_path)

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
        """Klavye tuşlarını dinle"""
        if self.is_playing:
            # ESC stop
            import keyboard
            if keyboard.is_pressed('esc') or keyboard.is_pressed('"'):
                self.stop_playback()
                return
                
            key = event.keysym.lower()
            if key in STOP_KEYS or event.char in STOP_KEYS:
                self.stop_playback()
            return
        
        key = event.char.lower()
        if key in self.buttons:
            self.trigger_button(key)

    def press_key(self, key):
        if key in self.buttons:
            self.key_queue.put(key)

    def process_key_queue(self):
        try:
            while not self.key_queue.empty():
                key = self.key_queue.get_nowait()
                self.trigger_button(key)
        except queue.Empty:
            pass
        if self.processing:
            self.after(5, self.process_key_queue)

    def trigger_button(self, key):
        self.play_sound(key)
        self.start_animation(key)
        if not self.is_playing:
            note = NOTE_NAMES.get(key, "")
            if note:
                self._show_note(key, note)

    def play_sound(self, key):
        if not self.current_instrument:
            return
        index = KEY_INDEX.get(key)
        if index is None:
            return
        path = os.path.join(
            self.sounds_dir,
            self.current_instrument,
            f"{index}.mp3"
        )
        try:
            if os.path.exists(path):
                pygame.mixer.Sound(path).play()
        except Exception as e:
            self.update_status(f"Error playing sound: {e}")
            

    # ================= ANIMATION =================

    def start_animation(self, key):
        button = self.buttons.get(key)
        if not button:
            return
        for anim in self.active_animations:
            if anim.key == key:
                anim.step = 0
                return
        self.active_animations.append(AnimationState(button, key))
        if not self.animation_loop_running:
            self.animation_loop_running = True
            self.run_animation_loop()

    def run_animation_loop(self):
        if not self.active_animations:
            self.animation_loop_running = False
            return
        completed = []
        for anim in self.active_animations:
            self.update_animation(anim)
            if anim.step >= ANIMATION_DURATION:
                self.reset_button(anim.button)
                completed.append(anim)
        for anim in completed:
            self.active_animations.remove(anim)
        if self.active_animations:
            self.after(ANIMATION_FRAME_TIME, self.run_animation_loop)
        else:
            self.animation_loop_running = False

    def update_animation(self, anim):
        step = anim.step
        t = step / ANIMATION_DURATION
        scale = 1 + 0.17 * (1 - (2 * t - 1) ** 2)
        size = int(BUTTON_SIZE * scale)
        base = (59, 66, 106)
        active = (108, 124, 255)
        mix = min(step / (ANIMATION_DURATION / 2), 1)
        r = int(base[0] + (active[0] - base[0]) * mix)
        g = int(base[1] + (active[1] - base[1]) * mix)
        b = int(base[2] + (active[2] - base[2]) * mix)
        anim.button.configure(width=size, height=size, corner_radius=size // 2,
                               fg_color=f"#{r:02x}{g:02x}{b:02x}")
        anim.step += 1

    def reset_button(self, button):
        button.configure(width=BUTTON_SIZE, height=BUTTON_SIZE,
                         corner_radius=BUTTON_CORNER, fg_color=BUTTON_BASE)

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
        self.play_indicator.configure(text="PLAYING")
        self.play_here_btn.configure(text="⏹ Stop", command=self.stop_playback)
        self.play_game_btn.configure(text="⏹ Stop", command=self.stop_playback)
        self.play_thread = threading.Thread(target=self._playback_worker, args=(mode,), daemon=True)
        self.play_thread.start()

    def stop_playback(self):
        self.is_playing = False
        self.play_indicator.configure(text="")
        self.bpm_label.configure(text="")
        self.play_here_btn.configure(text="Play Here", command=self.play_here)
        self.play_game_btn.configure(text="Play at Game", command=self.play_game)
        self.update_status("Stopped")

    def _playback_worker(self, mode):
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
            else:
                raise ValueError("Unknown format")
        except FileNotFoundError:
            self.after(0, lambda: self.update_status("File not found"))
        except json.JSONDecodeError:
            self.after(0, lambda: self.update_status("Invalid JSON"))
        except Exception as e:
            self.after(0, lambda: self.update_status(f"Error: {str(e)[:30]}"))
            self.update_status(f"Playback error: {traceback.format_exc()}")
        finally:
            self.after(0, self.stop_playback)

    def _play_columns_format(self, columns, bpm, mode, target_title=""):
        bps = bpm / 60
        wait = 1 / bps
        for column in columns:
            if not self.is_playing:
                break
            if mode == "game" and target_title and not self._is_target_focused(target_title):
                self.after(0, lambda: self.update_status("Paused — focus lost"))
                if not self._wait_for_focus(target_title):
                    break
                self.after(0, lambda: self.update_status("Resumed"))
            tempo = TEMPO_DICT.get(column[0], 1)
            wait_time = wait / tempo
            if not column[1]:
                time.sleep(wait_time)
                continue
            keys_to_press = []
            for note in column[1]:
                note_num = str(note[0])
                if note_num in NUMBERS:
                    idx = NUMBERS.index(note_num)
                    keys_to_press.append(KEYS[idx])
            if mode == "here":
                for key in keys_to_press:
                    self.press_key(key)
            else:
                for key in keys_to_press:
                    pyautogui.press(key)
                    self.after(0, lambda k=key: self.start_animation(k))
            time.sleep(wait_time)

    def _play_notes_format(self, notes, mode, target_title=""):
        note_map = {}
        for note in notes:
            time_ms, note_num = note[1], note[0]
            note_str = str(note_num)
            if note_str in NUMBERS:
                idx = NUMBERS.index(note_str)
                note_map[time_ms] = KEYS[idx]
        sorted_times = sorted(note_map.keys())
        self._start_timer()
        for note_time in sorted_times:
            if not self.is_playing:
                break
            while self._get_timer_ms() < note_time:
                if not self.is_playing:
                    return
                if mode == "game" and target_title and not self._is_target_focused(target_title):
                    self.after(0, lambda: self.update_status("Paused — focus lost"))
                    if not self._wait_for_focus(target_title):
                        return
                    self.after(0, lambda: self.update_status("Resumed"))
                time.sleep(0.0005)
            key = note_map[note_time]
            if mode == "here":
                self.press_key(key)
            else:
                pyautogui.press(key)
                self.after(0, lambda k=key: self.start_animation(k))

    def _start_timer(self):
        now = time.time()
        self.timer_start = now
        self.timer_ms = int((now - int(now)) * 1000)

    def _get_timer_ms(self):
        elapsed = time.time() - self.timer_start
        return self.timer_ms + int(elapsed * 1000)

    def destroy(self):
        self.processing = False
        self.is_playing = False
        if self.play_thread and self.play_thread.is_alive():
            self.play_thread.join(timeout=1)
        super().destroy()


if __name__ == "__main__":
    if not check_admin():
        request_admin_and_restart()
    ctk.set_appearance_mode("dark")
    app = App()
    app.mainloop()