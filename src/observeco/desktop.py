"""Native desktop window for ObserveCo dashboard using pywebview.

Architecture:
  Wraps the ObserveCo dashboard server in a native macOS window with
  system tray integration. The dashboard server is started as a background
  thread, then pywebview creates a native window pointing at localhost.

  Requirements:
    pip install pywebview  # or: pip install "observeco[desktop]"

  Platform notes:
    macOS: Full native window with system tray (tested)
    Linux: Requires GTK, tray may not work on all DEs
    Windows: Supported by pywebview but untested in ObserveCo

  Graceful fallback: If pywebview is not installed, prints a clear
  message and opens the dashboard in the default browser instead.
"""

from __future__ import annotations

import logging
import os
import threading
import time

logger = logging.getLogger(__name__)

# Window dimensions
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
WINDOW_TITLE = "ObserveCo · Fleet Dashboard"
DASHBOARD_PORT = 9119
DASHBOARD_HOST = "127.0.0.1"


def _start_server(port: int, host: str, shared: str | None = None) -> None:
    """Start the ObserveCo dashboard server in a background thread."""
    from observeco.dashboard.server import serve

    serve(host=host, port=port, no_browser=True, shared=shared)


def launch(
    port: int = DASHBOARD_PORT,
    host: str = DASHBOARD_HOST,
    shared: str | None = None,
    no_tray: bool = False,
) -> None:
    """Launch the ObserveCo desktop app.

    Starts the dashboard server in a background thread, then opens
    a native pywebview window. Falls back to browser if pywebview
    is not installed.

    Args:
        port: Dashboard server port.
        host: Dashboard bind address.
        shared: Path to shared SQLite DB.
        no_tray: Skip system tray icon.
    """
    try:
        import webview  # type: ignore[import-untyped]
    except ImportError:
        print(
            "Desktop mode requires pywebview.\n"
            "Install: pip install 'observeco[desktop]'\n"
            "Falling back to browser..."
        )
        from observeco.dashboard.server import serve

        serve(host=host, port=port, no_browser=False, shared=shared)
        return

    # Start server in background thread
    server_thread = threading.Thread(
        target=_start_server,
        args=(port, host, shared),
        daemon=True,
    )
    server_thread.start()

    # Wait for server to be ready
    import urllib.request
    url = f"http://{host}:{port}"
    for _ in range(20):
        try:
            urllib.request.urlopen(f"{url}/api/agent-count", timeout=1)
            break
        except Exception:
            time.sleep(0.5)

    # System tray menu
    tray = None
    if not no_tray:
        tray = {
            "text": WINDOW_TITLE,
            "menu": [
                {"text": "Open Dashboard", "action": lambda: _open_window(webview, url)},
                {"text": "Show Token", "action": lambda: _show_token(url)},
                {"text": "Restart Server", "action": lambda: _restart_server(port, host, shared)},
                webview.MenuSeparator(),
                {"text": "Quit", "action": lambda: _quit(webview)},
            ],
        }

    # Create window
    window = webview.create_window(
        title=WINDOW_TITLE,
        url=url,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        resizable=True,
        fullscreen=False,
        min_size=(800, 600),
        text_select=True,
        confirm_close=True,
    )

    # Store window reference for tray actions
    _window_ref["window"] = window

    try:
        webview.start(
            gui=None,
            debug=False,
            http_server=False,  # We run our own uvicorn server
            tray=tray,
            private_mode=False,  # Keep session for token persistence
        )
    except KeyboardInterrupt:
        pass


# Module-level window reference for tray callbacks
_window_ref: dict = {}


def _open_window(webview_module, url: str) -> None:
    """Open or focus the dashboard window."""
    win = _window_ref.get("window")
    if win and hasattr(win, "show"):
        win.show()
    else:
        import webbrowser
        webbrowser.open(url)


def _show_token(url: str) -> None:
    """Print the dashboard access token."""
    from observeco.dashboard.auth import load_or_generate_secret

    secret = load_or_generate_secret()
    print(f"Dashboard access token: {secret}")
    print(f"Use with: curl -H 'X-ObserveCo-Token: {secret}' {url}/api/agents")


def _restart_server(port: int, host: str, shared: str | None) -> None:
    """Restart the dashboard server thread."""
    logger.info("Restarting dashboard server...")
    # The daemon thread will be replaced on next start
    t = threading.Thread(target=_start_server, args=(port, host, shared), daemon=True)
    t.start()


def _quit(webview_module) -> None:
    """Quit the desktop application."""
    try:
        webview_module.destroy_window()
    except Exception:
        pass
    os._exit(0)
