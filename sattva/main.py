"""
SATTVA AI AGENT — Master Global CLI Entry Point.
Provides global system-wide CLI command `sattva` with support for:
- `sattva` (Interactive REPL in current directory)
- `sattva <prompt>` (Direct prompt execution in current directory)
- `sattva multi <prompt>` (Direct Multi-Agent team execution)
- `sattva init` (Initialize .sattva workspace config & rules)
- `sattva web` (Launch Web UI)
- `sattva scan` (Scan current codebase)
- `sattva models` (List local Ollama models)
- `sattva pull <model>` (Pull Ollama model)
- `sattva install` (Global system-wide setup & PATH installer)
- `sattva --version` / `-v`
- `sattva --help` / `-h`
"""

import os
import sys
import argparse
import asyncio
from pathlib import Path

from sattva.cli.app import SattvaCLI, VERSION, BANNER


def print_version():
    print(f"SATTVA AI AGENT v{VERSION} — Local Autonomous AI Coding Assistant & Multi-Agent Team")


def main():
    # If called with no arguments, launch interactive CLI
    if len(sys.argv) == 1:
        cli = SattvaCLI(workspace_path=os.getcwd())
        asyncio.run(cli.run_loop())
        return

    # Check for simple flags
    if sys.argv[1] in ["--version", "-v", "version"]:
        print_version()
        return

    parser = argparse.ArgumentParser(
        prog="sattva",
        description="⚡ SATTVA AI AGENT — Autonomous Local AI Coding Assistant & Multi-Agent Team",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sattva                               # Launch interactive CLI in current directory
  sattva "create a snake game in python" # Execute prompt directly in current directory
  sattva multi "build a FastAPI auth API" # Execute with specialized Multi-Agent Team
  sattva init                          # Initialize .sattva workspace config & rules
  sattva web                           # Launch modern Web UI in default browser
  sattva scan                          # Perform AST codebase intelligence scan
  sattva models                        # List installed Ollama models
  sattva pull qwen2.5-coder:7b         # Download/pull model from Ollama library
  sattva install                       # Install and register `sattva` globally in system PATH
        """,
    )

    parser.add_argument("subcommand_or_prompt", nargs="*", help="Command or prompt to execute")
    parser.add_argument("--mode", choices=["agent", "multi", "ask"], default=None, help="Agent execution mode (agent, multi, ask)")
    parser.add_argument("--model", help="Specify local Ollama model")
    parser.add_argument("--workspace", "-w", default=os.getcwd(), help="Workspace path (defaults to current directory)")
    parser.add_argument("--web", action="store_true", help="Launch Web UI")
    parser.add_argument("--scan", action="store_true", help="Run codebase AST scan")
    parser.add_argument("--models", action="store_true", help="List installed Ollama models")
    parser.add_argument("--port", "-p", type=int, default=8000, help="Web server port (default: 8000)")
    parser.add_argument("--host", default="127.0.0.1", help="Web server host (default: 127.0.0.1)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser in web mode")
    parser.add_argument("--version", "-v", action="store_true", help="Show SATTVA version")

    args, unknown = parser.parse_known_args()

    if args.version:
        print_version()
        return

    # Handle flags
    if args.web:
        from sattva_web import run_web
        run_web(host=args.host, port=args.port, open_browser=not args.no_browser)
        return

    if args.scan:
        cli = SattvaCLI(workspace_path=args.workspace, model=args.model)
        asyncio.run(cli.scan_codebase())
        return

    if args.models:
        cli = SattvaCLI(workspace_path=args.workspace, model=args.model)
        asyncio.run(cli.list_models())
        return

    tokens = args.subcommand_or_prompt + unknown
    if not tokens:
        # Launch interactive REPL
        mode = args.mode or "agent"
        cli = SattvaCLI(workspace_path=args.workspace, model=args.model, mode=mode)
        asyncio.run(cli.run_loop())
        return

    cmd = tokens[0].lower()

    if cmd == "init":
        cli = SattvaCLI(workspace_path=args.workspace, model=args.model)
        cli.init_workspace()
        return

    if cmd == "web":
        from sattva_web import run_web
        run_web(host=args.host, port=args.port, open_browser=not args.no_browser)
        return

    if cmd == "scan":
        cli = SattvaCLI(workspace_path=args.workspace, model=args.model)
        asyncio.run(cli.scan_codebase())
        return

    if cmd == "models" or cmd == "list":
        cli = SattvaCLI(workspace_path=args.workspace, model=args.model)
        asyncio.run(cli.list_models())
        return

    if cmd == "pull":
        if len(tokens) < 2:
            print("Error: Please provide model name. Example: sattva pull qwen2.5-coder:7b")
            return
        cli = SattvaCLI(workspace_path=args.workspace, model=args.model)
        asyncio.run(cli.pull_model(tokens[1]))
        return

    if cmd in ["install", "setup"]:
        from sattva.cli.installer import run_global_installer
        run_global_installer()
        return

    if cmd == "multi":
        prompt = " ".join(tokens[1:]).strip()
        if not prompt:
            # Launch multi-agent REPL
            cli = SattvaCLI(workspace_path=args.workspace, model=args.model, mode="multi")
            asyncio.run(cli.run_loop())
            return
        cli = SattvaCLI(workspace_path=args.workspace, model=args.model, mode="multi")
        asyncio.run(cli.execute_multi_agent(prompt))
        return

    # Direct prompt execution
    prompt = " ".join(tokens).strip()
    mode = args.mode or "agent"
    cli = SattvaCLI(workspace_path=args.workspace, model=args.model, mode=mode)
    if mode == "multi":
        asyncio.run(cli.execute_multi_agent(prompt))
    else:
        asyncio.run(cli.execute_single_agent(prompt))


if __name__ == "__main__":
    main()
