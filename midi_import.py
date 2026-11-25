import json
import os
import threading
import time
from collections import Counter
from dataclasses import dataclass, field
from tkinter import filedialog

import customtkinter as ctk
import mido

MIDI_EXTENSIONS = (".mid", ".midi")

BG = "#0B0D14"
SIDEBAR = "#121526"
BUTTON_BASE = "#3B426A"
ACCENT = "#6C7CFF"
SUCCESS = "#3FBAC2"
WARNING = "#FFB347"
DANGER = "#FF5555"
TEXT = "#E6E8EF"
HOVER_COLOR = "#1E2240"
SELECTED_COLOR = "#2A2F55"

# Lyre range: C3 (48) .. B5 (83), same as midi_main.py
LYRE_LOW = 48
LYRE_HIGH = 83
# semitone inside the octave -> scale degree (white keys only)
NATURAL_DEGREES = {0: 0, 2: 1, 4: 2, 5: 3, 7: 4, 9: 5, 11: 6}

# Same order as KEY_LAYOUT in main.py: index 0 = "q" ... index 20 = "m"
KEY_ORDER = [
    "q", "w", "e", "r", "t", "y", "u",
    "a", "s", "d", "f", "g", "h", "j",
    "z", "x", "c", "v", "b", "n", "m",
]

NOTE_LABELS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
GM_FAMILIES = [
    "Piano", "Chromatic Percussion", "Organ", "Guitar", "Bass", "Strings",
    "Ensemble", "Brass", "Reed", "Pipe", "Synth Lead", "Synth Pad",
    "Synth Effects", "Ethnic", "Percussive", "Sound Effects",
]


def pitch_label(pitch):
    return f"{NOTE_LABELS[pitch % 12]}{pitch // 12 - 1}"


@dataclass
class MidiChannel:
    number: int                                   # 0-15 (shown as 1-16)
    track_names: list = field(default_factory=list)
    program: int = -1
    notes: list = field(default_factory=list)     # (time_ms, pitch)

    @property
    def is_drums(self):
        return self.number == 9


@dataclass
class MidiInfo:
    duration: float
    channels: list


def load_midi(path):
    """Parse a MIDI file and group the notes by channel."""
    mid = mido.MidiFile(path)

    track_names = {}
    for track in mid.tracks:
        name = ""
        for msg in track:
            if msg.type == "track_name":
                name = msg.name.strip()
                break
        used = {m.channel for m in track if not m.is_meta and hasattr(m, "channel")}
        for ch in used:
            names = track_names.setdefault(ch, [])
            if name and name not in names:
                names.append(name)

    channels = {}
    elapsed = 0.0
    for msg in mid:  # iterating a MidiFile yields delta times in seconds (tempo aware)
        elapsed += msg.time
        if msg.is_meta or not hasattr(msg, "channel"):
            continue
        channel = channels.setdefault(msg.channel, MidiChannel(msg.channel))
        if msg.type == "program_change" and channel.program < 0:
            channel.program = msg.program
        elif msg.type == "note_on" and msg.velocity > 0:
            channel.notes.append((int(elapsed * 1000), msg.note))

    result = []
    for number in sorted(channels):
        channel = channels[number]
        if not channel.notes:
            continue
        channel.track_names = track_names.get(number, [])
        result.append(channel)
    return MidiInfo(duration=elapsed, channels=result)


def find_best_transpose(pitches):
    """Pick the transpose (in semitones) that fits the most notes on white keys,
    then the most notes inside the Lyre range."""
    counts = Counter(pitches)
    best_score, best_shift = None, 0
    for shift in range(-36, 37):
        naturals = sum(c for p, c in counts.items() if (p + shift) % 12 in NATURAL_DEGREES)
        in_range = sum(c for p, c in counts.items() if LYRE_LOW <= p + shift <= LYRE_HIGH)
        score = (naturals, in_range, -abs(shift))
        if best_score is None or score > best_score:
            best_score, best_shift = score, shift
    return best_shift


def fit_to_range(pitch):
    """Fold a pitch by octaves until it is inside the Lyre range."""
    while pitch < LYRE_LOW:
        pitch += 12
    while pitch > LYRE_HIGH:
        pitch -= 12
    return pitch


def pick_white_neighbour(pitch, prev_pitch, next_pitch, taken, usage, total):
    """Choose the white key (one semitone down or up) that fits a black-key note best."""
    best, best_cost = None, None
    for candidate in (pitch - 1, pitch + 1):
        cost = 0.0
        if candidate < LYRE_LOW or candidate > LYRE_HIGH:
            cost += 100
        # a repeated note (or two notes on the same key) is the worst result
        if candidate == prev_pitch or candidate == next_pitch or candidate in taken:
            cost += 3
        # keep the melody direction (prev -> note -> next)
        if prev_pitch is not None and next_pitch is not None:
            low, high = sorted((prev_pitch, next_pitch))
            if low <= pitch <= high and not low <= candidate <= high:
                cost += 1
        # prefer the neighbour that the song already uses a lot
        cost -= 0.5 * usage[candidate % 12] / total
        if best_cost is None or cost < best_cost:
            best, best_cost = candidate, cost
    return best


def snap_channel(notes, usage, total):
    """notes: [(time_ms, pitch)] of ONE channel, already transposed and fitted to the range.
    Returns ([(time_ms, pitch)], snapped_count) where every pitch is a white key."""
    groups = {}
    for time_ms, pitch in notes:
        groups.setdefault(time_ms, []).append(pitch)
    times = sorted(groups)

    result = []
    snapped = 0
    prev_final = []
    for index, time_ms in enumerate(times):
        pitches = groups[time_ms]
        next_raw = groups[times[index + 1]] if index + 1 < len(times) else []
        taken = {p for p in pitches if p % 12 in NATURAL_DEGREES}
        final = []
        for pitch in pitches:
            if pitch % 12 in NATURAL_DEGREES:
                final.append(pitch)
                continue
            prev_pitch = min(prev_final, key=lambda q: abs(q - pitch), default=None)
            next_pitch = min(next_raw, key=lambda q: abs(q - pitch), default=None)
            chosen = pick_white_neighbour(pitch, prev_pitch, next_pitch, taken, usage, total)
            taken.add(chosen)
            final.append(chosen)
            snapped += 1
        result.extend((time_ms, p) for p in final)
        prev_final = final
    return result, snapped


def convert_notes(channel_notes, transpose, snap_sharps):
    """channel_notes: one [(time_ms, pitch)] list per channel
    -> ([(time_ms, key_index)], dropped_count, snapped_count)"""
    fitted = [[(t, fit_to_range(p + transpose)) for t, p in notes] for notes in channel_notes]
    usage = Counter(p % 12 for notes in fitted for _, p in notes if p % 12 in NATURAL_DEGREES)
    total = max(sum(usage.values()), 1)

    result = set()
    dropped = 0
    snapped = 0
    for notes in fitted:
        if snap_sharps:
            notes, count = snap_channel(notes, usage, total)
            snapped += count
        for time_ms, p in notes:
            semitone = p % 12                          # LYRE_LOW is a multiple of 12
            if semitone not in NATURAL_DEGREES:
                dropped += 1
                continue
            octave_row = (p - LYRE_LOW) // 12          # 0 = bottom row (z), 2 = top row (q)
            result.add((time_ms, (2 - octave_row) * 7 + NATURAL_DEGREES[semitone]))
    return sorted(result), dropped, snapped


class MidiImportDialog(ctk.CTkToplevel):
    def __init__(self, parent, midi_path, midi_info, sheets_dir, number=1, total=1):
        super().__init__(parent)
        self.app = parent
        self.midi_path = midi_path
        self.sheets_dir = sheets_dir
        self.number = number
        self.total = total
        self.channel_map = {ch.number: ch for ch in midi_info.channels}
        self.channel_vars = {}
        self.preview_buttons = {}
        self.preview_token = 0
        self.previewing = None      # channel number, "selection" or None
        self.saved_name = None
        self.snapped_count = 0

        self.title("Import MIDI" if total == 1 else f"Import MIDI ({number}/{total})")
        self.geometry("640x720")
        self.resizable(False, False)
        self.configure(fg_color=BG)
        self.transient(parent)
        self.grab_set()
        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - 640) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 720) // 2
        self.geometry(f"640x720+{max(px, 0)}+{max(py, 0)}")

        self._build(midi_info)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<Escape>", lambda e: self._close())
        self._refresh_info()

    # ---------------- UI ----------------

    def _build(self, midi_info):
        minutes, seconds = divmod(int(midi_info.duration), 60)
        file_name = os.path.basename(self.midi_path)

        ctk.CTkLabel(self, text=f"🎼  {file_name}", text_color=TEXT,
                     font=ctk.CTkFont("Segoe UI", 16, "bold")).pack(pady=(16, 0))
        subtitle = f"{minutes}:{seconds:02d}  ·  {len(self.channel_map)} channels with notes"
        if self.total > 1:
            subtitle = f"File {self.number} of {self.total}  ·  " + subtitle
        ctk.CTkLabel(self, text=subtitle, text_color="#8890aa",
                     font=ctk.CTkFont("Segoe UI", 12)).pack()
        ctk.CTkLabel(self, text="Not sure which channel is which? Press ▶ to listen to it alone.",
                     text_color="#666a8a", font=ctk.CTkFont("Segoe UI", 11)).pack(pady=(4, 8))

        list_frame = ctk.CTkScrollableFrame(self, fg_color=BG, height=290)
        list_frame.pack(fill="x", padx=16)

        for number, channel in self.channel_map.items():
            self._build_channel_row(list_frame, number, channel)

        options = ctk.CTkFrame(self, fg_color=SIDEBAR, corner_radius=10)
        options.pack(fill="x", padx=16, pady=(10, 4))

        self.auto_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(options, text="Auto transpose", variable=self.auto_var,
                        text_color=TEXT, command=self._on_option_change).pack(side="left", padx=12, pady=10)
        ctk.CTkLabel(options, text="Semitones:", text_color="#8890aa").pack(side="left", padx=(8, 4))
        self.transpose_box = ctk.CTkComboBox(options, values=[str(i) for i in range(-24, 25)],
                                             width=80, state="disabled",
                                             command=lambda v: self._refresh_info())
        self.transpose_box.set("0")
        self.transpose_box.pack(side="left")
        self.snap_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(options, text="Smart-snap sharps", variable=self.snap_var,
                        text_color=TEXT, command=self._on_option_change).pack(side="left", padx=14)

        self.info_label = ctk.CTkLabel(self, text="", text_color="#8890aa", font=ctk.CTkFont("Segoe UI", 11))
        self.info_label.pack(pady=(4, 0))

        name_row = ctk.CTkFrame(self, fg_color="transparent")
        name_row.pack(fill="x", padx=16, pady=(8, 0))
        ctk.CTkLabel(name_row, text="Name:", text_color=TEXT).pack(side="left", padx=(0, 8))
        self.name_entry = ctk.CTkEntry(name_row, width=420)
        self.name_entry.insert(0, os.path.splitext(os.path.basename(self.midi_path))[0])
        self.name_entry.pack(side="left", fill="x", expand=True)

        self.preview_btn = ctk.CTkButton(self, text="▶  Preview selected", height=38,
                                         fg_color=HOVER_COLOR, hover_color=SELECTED_COLOR, text_color=TEXT,
                                         command=self._toggle_selection_preview)
        self.preview_btn.pack(fill="x", padx=16, pady=(12, 6))

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=16, pady=(0, 6))
        ctk.CTkButton(bottom, text="💾  Add to Library", height=40, fg_color=ACCENT, hover_color="#5566dd",
                      text_color=TEXT, font=ctk.CTkFont("Segoe UI", 13, "bold"),
                      command=self._add_to_library).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(bottom, text="📤  Export File…", height=40, fg_color=HOVER_COLOR,
                      hover_color=SELECTED_COLOR, text_color=TEXT,
                      command=self._export_file).pack(side="left", fill="x", expand=True, padx=(6, 0))

        self.status_label = ctk.CTkLabel(self, text="", text_color=SUCCESS, font=ctk.CTkFont("Segoe UI", 12))
        self.status_label.pack()

    def _build_channel_row(self, parent, number, channel):
        var = ctk.BooleanVar(value=not channel.is_drums)
        self.channel_vars[number] = var

        row = ctk.CTkFrame(parent, fg_color=SIDEBAR, corner_radius=10)
        row.pack(fill="x", pady=3, padx=2)

        ctk.CTkCheckBox(row, text="", variable=var, width=24,
                        command=self._on_option_change).pack(side="left", padx=(12, 0), pady=12)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=8, pady=6)

        track_name = ", ".join(channel.track_names) if channel.track_names else "unnamed"
        if channel.is_drums:
            title = f"Channel {number + 1} — Drums / percussion"
            detail = f"{len(channel.notes)} hits · not pitched, usually leave off"
        else:
            family = GM_FAMILIES[channel.program // 8] if channel.program >= 0 else "Unknown instrument"
            pitches = [p for _, p in channel.notes]
            title = f"Channel {number + 1} — {track_name}"
            detail = (f"{family} · {len(channel.notes)} notes · "
                      f"{pitch_label(min(pitches))}–{pitch_label(max(pitches))}")

        ctk.CTkLabel(info, text=title, text_color=TEXT, anchor="w",
                     font=ctk.CTkFont("Segoe UI", 13, "bold")).pack(fill="x")
        ctk.CTkLabel(info, text=detail, text_color="#8890aa", anchor="w",
                     font=ctk.CTkFont("Segoe UI", 11)).pack(fill="x")

        button = ctk.CTkButton(row, text="▶", width=44, height=34, fg_color=BUTTON_BASE,
                               hover_color=ACCENT, text_color=TEXT,
                               command=lambda c=channel: self._toggle_channel_preview(c))
        button.pack(side="right", padx=12)
        self.preview_buttons[number] = button

    # ---------------- conversion helpers ----------------

    def _selected_numbers(self):
        return [n for n, var in self.channel_vars.items() if var.get()]

    def _resolve_transpose(self, numbers):
        if not self.auto_var.get():
            return int(self.transpose_box.get())
        pitches = [p for n in numbers for _, p in self.channel_map[n].notes]
        return find_best_transpose(pitches) if pitches else 0

    def _build_events(self, numbers, transpose):
        events, dropped, snapped = convert_notes(
            [self.channel_map[n].notes for n in numbers], transpose, self.snap_var.get())
        self.snapped_count = snapped
        return events, dropped

    def _on_option_change(self):
        self.transpose_box.configure(state="disabled" if self.auto_var.get() else "readonly")
        self._refresh_info()

    def _refresh_info(self):
        numbers = self._selected_numbers()
        if not numbers:
            self.info_label.configure(text="No channel selected")
            return
        transpose = self._resolve_transpose(numbers)
        events, dropped = self._build_events(numbers, transpose)
        mode = "auto" if self.auto_var.get() else "manual"
        self.info_label.configure(
            text=f"Transpose: {transpose:+d} ({mode})  ·  {len(events)} notes  ·  "
                 f"{self.snapped_count} snapped  ·  {dropped} skipped (sharps)")

    # ---------------- preview ----------------

    def _toggle_channel_preview(self, channel):
        if self.previewing == channel.number:
            self._stop_preview()
            return
        reference = self._selected_numbers() or [channel.number]
        self._start_preview([channel.number], self._resolve_transpose(reference), channel.number)

    def _toggle_selection_preview(self):
        if self.previewing == "selection":
            self._stop_preview()
            return
        numbers = self._selected_numbers()
        if not numbers:
            self.status_label.configure(text="Select at least one channel", text_color=WARNING)
            return
        self._start_preview(numbers, self._resolve_transpose(numbers), "selection")

    def _start_preview(self, numbers, transpose, tag):
        self._stop_preview()
        events, _ = self._build_events(numbers, transpose)
        if not events:
            self.status_label.configure(text="No playable notes in this selection", text_color=WARNING)
            return
        self.previewing = tag
        self._update_preview_buttons()
        token = self.preview_token
        threading.Thread(target=self._preview_worker, args=(events, token), daemon=True).start()

    def _stop_preview(self):
        self.preview_token += 1
        self.previewing = None
        self._update_preview_buttons()

    def _update_preview_buttons(self):
        for number, button in self.preview_buttons.items():
            button.configure(text="⏹" if self.previewing == number else "▶")
        self.preview_btn.configure(
            text="⏹  Stop" if self.previewing == "selection" else "▶  Preview selected")

    def _preview_worker(self, events, token):
        start = time.perf_counter()
        for time_ms, index in events:
            while token == self.preview_token:
                remaining = time_ms / 1000 - (time.perf_counter() - start)
                if remaining <= 0:
                    break
                time.sleep(min(remaining, 0.01))
            if token != self.preview_token:
                return
            self.app.press_key(KEY_ORDER[index])   # plays sound + animates the button
        try:
            self.after(0, lambda: self._finish_preview(token))
        except Exception:
            pass

    def _finish_preview(self, token):
        if token == self.preview_token:
            self.previewing = None
            self._update_preview_buttons()

    # ---------------- save / export ----------------

    def _build_sheet(self):
        numbers = self._selected_numbers()
        if not numbers:
            self.status_label.configure(text="Select at least one channel", text_color=WARNING)
            return None
        events, _ = self._build_events(numbers, self._resolve_transpose(numbers))
        if not events:
            self.status_label.configure(text="Nothing playable in the selection", text_color=WARNING)
            return None
        first = events[0][0]  # trim leading silence
        name = self.name_entry.get().strip() or "midi_song"
        return name, [{
            "name": name,
            "source": "midi",
            "notes": [[index, time_ms - first] for time_ms, index in events],
        }]

    @staticmethod
    def _safe_filename(name):
        cleaned = "".join(c for c in name if c not in '<>:"/\\|?*').strip()
        return cleaned or "midi_song"

    def _add_to_library(self):
        built = self._build_sheet()
        if not built:
            return
        name, sheet = built
        base = self._safe_filename(name)
        file_name = f"{base}.json"
        counter = 2
        while os.path.exists(os.path.join(self.sheets_dir, file_name)):
            file_name = f"{base} ({counter}).json"
            counter += 1
        try:
            with open(os.path.join(self.sheets_dir, file_name), "w", encoding="utf-8") as f:
                json.dump(sheet, f, ensure_ascii=False)
        except Exception as e:
            self.status_label.configure(text=f"Save failed: {str(e)[:40]}", text_color=DANGER)
            return
        self.saved_name = file_name
        self._close()

    def _export_file(self):
        built = self._build_sheet()
        if not built:
            return
        name, sheet = built
        path = filedialog.asksaveasfilename(
            parent=self, title="Export sheet", defaultextension=".json",
            initialfile=self._safe_filename(name),
            filetypes=[("JSON", "*.json"), ("TXT", "*.txt"), ("GENSHINSHEET", "*.genshinsheet")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(sheet, f, ensure_ascii=False)
            self.status_label.configure(text="✓ Exported", text_color=SUCCESS)
        except Exception as e:
            self.status_label.configure(text=f"Export failed: {str(e)[:40]}", text_color=DANGER)

    def _close(self):
        self._stop_preview()
        self.destroy()