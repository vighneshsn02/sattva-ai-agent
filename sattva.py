"""
SATTVA AI AGENT — Main Entry Point
"""

import sys
import os
import argparse
import asyncio

# Ensure package root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(
        description="SATTVA AI AGENT — Autonomous Local AI Coding Assistant powered by Ollama",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python sattva.py cli                 # Launch interactive CLI
  python sattva.py web                 # Launch Web UI in browser
  python sattva.py scan                # Scan current workspace directory
  python sattva.py models              # List installed local Ollama models
  python sattva.py --model llama3.2:3b # Run CLI with specific model
        """,
    )

    parser.add_argument("mode", nargs="?", default="cli", choices=["cli", "web", "scan", "models"], help="Mode to run (cli, web, scan, models)")
    parser.add_argument("--model", "-m", help="Specify default Ollama model")
    parser.add_argument("--workspace", "-w", help="Workspace path (defaults to current dir)")
    parser.add_argument("--port", "-p", type=int, default=8000, help="Web server port (default: 8000)")
    parser.add_argument("--host", default="127.0.0.1", help="Web server host (default: 127.0.0.1)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically in web mode")

    args = parser.parse_args()

    if args.mode == "web":
        from sattva_web import run_web
        run_web(host=args.host, port=args.port, open_browser=not args.no_browser)

    elif args.mode == "cli":
        from sattva.cli.app import SattvaCLI
        cli = SattvaCLI(workspace_path=args.workspace, model=args.model)
        asyncio.run(cli.run_loop())

    elif args.mode == "scan":
        from sattva.cli.app import SattvaCLI
        cli = SattvaCLI(workspace_path=args.workspace)
        asyncio.run(cli.scan_codebase())

    elif args.mode == "models":
        from sattva.cli.app import SattvaCLI
        cli = SattvaCLI(workspace_path=args.workspace)
        asyncio.run(cli.list_models())


if __name__ == "__main__":
    main()
