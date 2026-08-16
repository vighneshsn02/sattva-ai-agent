"""
SATTVA AI AGENT — Web UI Server Runner
"""

import sys
import os
import argparse
import webbrowser
import uvicorn

# Ensure package root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sattva.web.server import app


def run_web(host: str = "127.0.0.1", port: int = 8000, open_browser: bool = True):
    print("\n" + "=" * 60)
    print("  ⚡ SATTVA AI AGENT — Web Server Starting")
    print(f"  🌐 URL: http://{host}:{port}")
    print("=" * 60 + "\n")

    if open_browser:
        import threading
        import time

        def open_tab():
            time.sleep(1.2)
            webbrowser.open(f"http://{host}:{port}")

        threading.Thread(target=open_tab, daemon=True).start()

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run SATTVA AI AGENT Web Interface")
    parser.add_argument("--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port number (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    args = parser.parse_args()

    run_web(host=args.host, port=args.port, open_browser=not args.no_browser)
