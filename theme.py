"""Shared colors and widget styles. Change a color here and every window follows."""

APPEARANCE_MODE = "light"

# ---- surfaces ----
BG = "#F7F6F3"          # window background (warm porcelain)
SIDEBAR = "#EEEBF8"     # side panels and dialogs (lavender mist)
CARD = "#FFFFFF"        # cards, inputs, key caps
BORDER = "#D8D3EE"
DIVIDER = "#DDD9EE"

# ---- text ----
TEXT = "#1E1B2E"        # ink
MUTED = "#625E7A"
SUBTLE = "#8A86A6"
ON_ACCENT = "#FFFFFF"   # text on top of a colored button

# ---- accents ----
ACCENT = "#7F70F2"      # violet (softer)
ACCENT_HOVER = "#6E5FE0"
ACCENT_SOFT = "#E1DDFF"
PLAY_1 = ACCENT
PLAY_1_HOVER = ACCENT_HOVER
PLAY_2 = "#F07088"      # coral (softer)
PLAY_2_HOVER = "#DE5C75"

# ---- neutral controls ----
BUTTON_BASE = "#E4E0F5"
HOVER_COLOR = "#E7E3F7"
SELECTED_COLOR = "#D6D0F5"

# ---- status ----
SUCCESS = "#0E8F82"
WARNING = "#B86E00"
DANGER = "#D93B45"
DANGER_HOVER = "#B92F39"

# ---- ready-made widget styles (use with **) ----
from typing import Any, Dict

NEUTRAL_BUTTON: Dict[str, Any] = dict(fg_color=CARD, hover_color=HOVER_COLOR, text_color=TEXT,
                                      border_width=1, border_color=BORDER)
CHECKBOX_STYLE: Dict[str, Any] = dict(fg_color=ACCENT, hover_color=ACCENT_HOVER,
                                      border_color=SUBTLE, checkmark_color=ON_ACCENT)
RADIO_STYLE: Dict[str, Any] = dict(fg_color=ACCENT, hover_color=ACCENT_HOVER, border_color=SUBTLE)
ENTRY_STYLE: Dict[str, Any] = dict(fg_color=CARD, border_color=BORDER, text_color=TEXT)
COMBO_STYLE: Dict[str, Any] = dict(fg_color=CARD, border_color=BORDER, button_color=ACCENT_SOFT,
                                   button_hover_color=SELECTED_COLOR, text_color=TEXT,
                                   text_color_disabled=SUBTLE, dropdown_fg_color=CARD,
                                   dropdown_hover_color=HOVER_COLOR, dropdown_text_color=TEXT)
SCROLL_STYLE: Dict[str, Any] = dict(scrollbar_button_color=BORDER, scrollbar_button_hover_color=SUBTLE)



# ---- flicker-free window drawing ----
def begin_draw(window):
    """Call first thing in a window's __init__: keeps it invisible while its widgets are built."""
    try:
        window.attributes("-alpha", 0.0)
    except Exception:
        pass

def end_draw(window):
    """Lets every widget finish drawing while the window is still invisible, then shows it at once."""
    try:
        window.update()
    finally:
        try:
            window.attributes("-alpha", 1.0)
        except Exception:
            pass