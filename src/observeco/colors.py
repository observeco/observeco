"""Cross-platform terminal colors — colorama on Windows, ANSI passthrough on *nix."""

import os
import sys

try:
    import colorama
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False


def init_colors() -> None:
    """Initialize platform color support. Call once at CLI entry point."""
    if sys.platform == "win32" and HAS_COLORAMA:
        colorama.init()
    # On macOS/Linux, ANSI is natively supported — no init needed


def supports_color() -> bool:
    """Check if the terminal supports colored output.

    Respects NO_COLOR, CI env vars, and TTY detection.
    """
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("CI"):
        return False
    if not sys.stdout.isatty():
        return False
    if sys.platform == "win32" and not HAS_COLORAMA:
        return False
    return True


# ANSI escape sequences
_RESET = "\033[0m"
_DIM = "\033[2m"
_BRIGHT = "\033[1m"

_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RED = "\033[91m"
_CYAN = "\033[96m"
_GREY = "\033[90m"


class Color:
    """Namespace for color/style strings. No-op when color is unsupported."""

    RESET = _RESET
    DIM = _DIM
    BRIGHT = _BRIGHT
    GREEN = _GREEN
    YELLOW = _YELLOW
    RED = _RED
    CYAN = _CYAN
    GREY = _GREY


def _init_global_color_state() -> None:
    """Set up color support state."""
    global _COLOR_SUPPORTED
    _COLOR_SUPPORTED = supports_color()

    if not _COLOR_SUPPORTED:
        # Strip all ANSI codes
        for attr in ("RESET", "DIM", "BRIGHT", "GREEN", "YELLOW", "RED", "CYAN", "GREY"):
            setattr(Color, attr, "")


_COLOR_SUPPORTED = True
_init_global_color_state()
