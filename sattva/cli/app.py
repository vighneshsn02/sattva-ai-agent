"""
Rich-based Interactive CLI and Direct Query Runner for SATTVA AI AGENT.
Supports Single-Agent ReAct, Multi-Agent Team Orchestration, and Ask modes.
"""

import asyncio
import os
import sys
import webbrowser
from pathlib import Path
from typing import Optional, List, Dict, Any

# Ensure UTF-8 stdout on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from rich.prompt import Prompt

from sattva.config import Config, CONFIG_DIR
from sattva.ollama_client import OllamaClient
from sattva.agent.engine import SattvaAgent, AgentEvent
from sattva.agent.session import Session
from sattva.agent.multi_agent import (
    MultiAgentOrchestrator,
    MultiAgentEvent,
    AgentRole,
    ROLE_METADATA,
)
from sattva.tools import create_default_registry


BANNER = r"""
[bold cyan]   ____     _  _____ _____ _   _     _         _    ___     _     ____ _____ _   _ _____ 
  / ___|   / \|_   _|_   _| | | |   / \       / \  |_ _|   / \   / ___| ____| \ | |_   _|
  \___ \  / _ \ | |   | | | | | |  / _ \     / _ \  | |   / _ \ | |  _|  _| |  \| | | |  
   ___) |/ ___ \| |   | | | |_| | / ___ \   / ___ \ | |  / ___ \| |_| | |___| |\  | | |  
  |____//_/   \_\_|   |_|  \___/ /_/   \_\ /_/   \_\___|/_/   \_\\____|_____|_| \_| |_|  [/bold cyan]
[dim italic]       * Autonomous Local AI Coding Assistant & Multi-Agent Team Powered by Ollama *[/dim italic]
"""

VERSION = "1.1.0"


class SattvaCLI:
    def __init__(self, workspace_path: Optional[str] = None, model: Optional[str] = None, mode: str = "agent"):
        self.console = Console(highlight=False)
        self.workspace_path = str(Path(workspace_path or os.getcwd()).resolve())
        self.config = Config(self.workspace_path)
        self.model = model or self.config.default_model
        self.mode = mode.lower() if mode.lower() in ["agent", "ask", "multi"] else "agent"

        self.agent = SattvaAgent(config=self.config, workspace_path=self.workspace_path, model=self.model)
        self.orchestrator = MultiAgentOrchestrator(config=self.config, workspace_path=self.workspace_path, model=self.model)
        self.session = Session(model=self.model, workspace_path=self.workspace_path)

    async def initialize(self):
        """Check Ollama connectivity and print welcome banner."""
        self.console.clear()
        self.console.print(BANNER)

        health = await self.agent.ollama.check_health()
        if health["online"]:
            status_text = f"[bold green][Online][/bold green] (v{health['version']}, {health['latency_ms']}ms)"
        else:
            status_text = f"[bold red][Offline][/bold red] ({health.get('error', 'Check if `ollama serve` is running')})"

        mode_labels = {
            "agent": "[green]SINGLE AGENT (ReAct Loop)[/green]",
            "multi": "[bold cyan]MULTI-AGENT TEAM (Planner, Coder, Tester, Reviewer, Security)[/bold cyan]",
            "ask": "[yellow]ASK / EXPLAIN (Fast Chat)[/yellow]",
        }

        info_table = Table.grid(padding=(0, 2))
        info_table.add_column(style="bold yellow")
        info_table.add_column(style="white")
        info_table.add_row("Ollama Status:", status_text)
        info_table.add_row("Active Model:", f"[bold magenta]{self.model}[/bold magenta]")
        info_table.add_row("Workspace:", f"[blue]{self.workspace_path}[/blue]")
        info_table.add_row("Active Mode:", mode_labels.get(self.mode, self.mode.upper()))
        info_table.add_row("Quick Tips:", "[dim]Type /help for slash commands, /mode multi for agent team, /web for browser UI[/dim]")

        self.console.print(Panel(info_table, title="[bold white]SATTVA AI READY[/bold white]", border_style="cyan"))
        self.console.print()

    async def run_loop(self):
        """Main REPL loop."""
        await self.initialize()

        while True:
            try:
                mode_tag = f"[bold cyan]multi[/bold cyan]" if self.mode == "multi" else (f"[bold green]agent[/bold green]" if self.mode == "agent" else "[bold yellow]ask[/bold yellow]")
                self.console.print(f"[bold cyan]sattva[/bold cyan] [{mode_tag}] [dim]({self.model})[/dim] > ", end="")
                user_input = input().strip()

                if not user_input:
                    continue

                if user_input.startswith("/"):
                    should_continue = await self.handle_slash_command(user_input)
                    if not should_continue:
                        break
                    continue

                # Run query
                await self.execute_query(user_input)

            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[yellow]Exiting SATTVA AI AGENT. Namaste![/yellow]")
                break
            except Exception as e:
                self.console.print(f"\n[bold red]Error:[/bold red] {e}")

    async def execute_query(self, query: str):
        """Dispatch query to Single Agent or Multi-Agent Team based on active mode."""
        if self.mode == "multi":
            await self.execute_multi_agent(query)
        else:
            await self.execute_single_agent(query)

    async def execute_single_agent(self, query: str):
        """Execute query in single-agent ReAct mode."""
        self.console.print()
        try:
            async for event in self.agent.run(
                user_message=query,
                session=self.session,
                mode=self.mode,
            ):
                if event.event_type == "thought_chunk":
                    chunk = event.data.get("chunk", "")
                    self.console.print(chunk, end="", highlight=False)
                    sys.stdout.flush()

                elif event.event_type == "tool_start":
                    tool_name = event.data.get("tool")
                    args = event.data.get("arguments", {})
                    self.console.print(f"\n[bold yellow]⚡ [Tool Call][/bold yellow] [cyan]{tool_name}[/cyan] with args:")
                    for k, v in args.items():
                        preview = str(v)
                        if len(preview) > 100:
                            preview = preview[:100] + "..."
                        self.console.print(f"   [dim]- {k}:[/dim] [white]{preview}[/white]")

                elif event.event_type == "tool_end":
                    tool_name = event.data.get("tool")
                    success = event.data.get("success")
                    diff = event.data.get("result", {}).get("data", {}).get("diff") if isinstance(event.data.get("result"), dict) else None

                    if success:
                        self.console.print(f"[bold green]✔ [{tool_name} completed][/bold green]")
                        if diff:
                            self.console.print(Panel(Syntax(diff, "diff", theme="monokai"), title="Unified Diff Preview", border_style="green"))
                    else:
                        err = event.data.get("result", {}).get("error", "Failed")
                        self.console.print(f"[bold red]✘ [{tool_name} failed][/bold red]: {err}")
                    self.console.print()

                elif event.event_type == "error":
                    self.console.print(f"\n[bold red]Agent Error:[/bold red] {event.data.get('message')}")

                elif event.event_type == "done":
                    self.console.print("\n[dim]────────────────────────────────────────────────────────────[/dim]\n")

        except Exception as e:
            self.console.print(f"\n[bold red]Execution error:[/bold red] {e}")

    async def execute_multi_agent(self, query: str):
        """Execute query in Multi-Agent Orchestration mode with parallel execution, sandbox, and verification."""
        self.console.print()
        team_panel = Table.grid(padding=(0, 2))
        team_panel.add_column(style="bold cyan")
        team_panel.add_column(style="white")
        team_panel.add_row("⚡ Orchestrator:", "Task DAG & Synthesis")
        team_panel.add_row("🧭 Planner:", "Architecture & Decomposition")
        team_panel.add_row("💻 Coder:", "Sandboxed Implementation")
        team_panel.add_row("🧪 Tester:", "Automated Verification")
        team_panel.add_row("🧐 Reviewer:", "Quality & Anti-patterns")
        team_panel.add_row("🛡️ Security:", "Secrets & OWASP Audit")

        self.console.print(Panel(team_panel, title="[bold cyan]🚀 SATTVA MULTI-AGENT TEAM ENGAGED[/bold cyan]", border_style="cyan"))
        self.console.print()

        try:
            async for event in self.orchestrator.run(
                user_message=query,
                session=self.session,
            ):
                ev_type = event.event_type
                role = event.role
                role_meta = ROLE_METADATA.get(role, {})
                icon = role_meta.get("icon", "🤖")
                title = role_meta.get("title", "Agent")
                color = role_meta.get("color", "white")

                if ev_type == "pipeline_stage":
                    stage = event.data.get("stage", "")
                    st_title = event.data.get("title", stage)
                    self.console.print(f"\n[bold {color}]▶ [{icon} {title.upper()}] — {st_title}[/bold {color}]")

                elif ev_type == "agent_thought":
                    chunk = event.data.get("chunk", "")
                    self.console.print(chunk, end="", highlight=False)
                    sys.stdout.flush()

                elif ev_type == "agent_tool_start":
                    tool_name = event.data.get("tool")
                    args = event.data.get("arguments", {})
                    task_id = event.data.get("task_id", "")
                    self.console.print(f"\n[bold yellow]⚡ [{icon} {title}] Tool: [cyan]{tool_name}[/cyan] ({task_id})[/bold yellow]")

                elif ev_type == "agent_tool_end":
                    tool_name = event.data.get("tool")
                    success = event.data.get("success")
                    msg = event.data.get("message", "")
                    if success:
                        self.console.print(f"[bold green]✔ [{tool_name} OK][/bold green] [dim]{msg[:80]}[/dim]")
                    else:
                        self.console.print(f"[bold red]✘ [{tool_name} FAILED][/bold red]: {msg}")

                elif ev_type == "diff_ready":
                    diff = event.data.get("diff")
                    file_name = event.data.get("file", "Modified File")
                    if diff:
                        self.console.print(Panel(Syntax(diff, "diff", theme="monokai"), title=f"Staged Diff: {file_name}", border_style="green"))

                elif ev_type == "agent_completed":
                    c_data = event.data
                    if role == AgentRole.PLANNER:
                        tasks = c_data.get("tasks", [])
                        t_table = Table(title="Generated Multi-Agent Task Plan", border_style="blue")
                        t_table.add_column("Task ID", style="cyan")
                        t_table.add_column("Assigned Role", style="green")
                        t_table.add_column("Description", style="white")
                        t_table.add_column("Dependencies", style="dim")
                        for t in tasks:
                            r_meta = ROLE_METADATA.get(t.get("role", "coder"), {})
                            t_table.add_row(t.get("id", ""), f"{r_meta.get('icon', '🤖')} {t.get('role', '')}", t.get("title", ""), ", ".join(t.get("dependencies", [])) or "None")
                        self.console.print(t_table)
                        self.console.print()

                    elif role == AgentRole.SECURITY:
                        score = c_data.get("score", 100)
                        findings_cnt = c_data.get("findings_count", 0)
                        s_color = "green" if score >= 85 else ("yellow" if score >= 70 else "red")
                        self.console.print(f"\n[bold {s_color}]🛡️ Security Audit: {score}/100 ({findings_cnt} findings)[/bold {s_color}]")

                    elif role == AgentRole.REVIEWER:
                        score = c_data.get("score", 90)
                        verdict = c_data.get("verdict", "APPROVED")
                        self.console.print(f"[bold magenta]🧐 Code Review: {score}/100 [{verdict}][/bold magenta]")

                    elif role == AgentRole.TESTER:
                        passed = c_data.get("passed", 0)
                        failed = c_data.get("failed", 0)
                        t_status = "[bold green]All Tests Passed[/bold green]" if failed == 0 else f"[bold red]{failed} Tests Failed[/bold red]"
                        self.console.print(f"[bold yellow]🧪 Automated Tests: {t_status} ({passed} passed)[/bold yellow]")

                elif ev_type == "synthesis_chunk":
                    chunk = event.data.get("chunk", "")
                    self.console.print(chunk, end="", highlight=False)
                    sys.stdout.flush()

                elif ev_type == "error":
                    self.console.print(f"\n[bold red]Orchestrator Error:[/bold red] {event.data.get('error')}")

                elif ev_type == "done":
                    self.console.print("\n\n[bold cyan]✨ Multi-Agent Task Successfully Finished & Changes Merged![/bold cyan]")
                    self.console.print("[dim]────────────────────────────────────────────────────────────[/dim]\n")

        except Exception as e:
            self.console.print(f"\n[bold red]Multi-agent execution error:[/bold red] {e}")

    async def handle_slash_command(self, cmd_line: str) -> bool:
        """Handle slash commands in REPL."""
        parts = cmd_line.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ["/exit", "/quit", "/q"]:
            self.console.print("[yellow]Exiting SATTVA AI AGENT. Happy coding![/yellow]")
            return False

        elif cmd in ["/help", "/h", "/?"]:
            self.print_help()

        elif cmd in ["/models", "/list"]:
            await self.list_models()

        elif cmd in ["/model", "/m"]:
            if arg:
                self.model = arg
                self.agent.set_model(arg)
                self.orchestrator.set_model(arg)
                self.config.set("default_model", arg)
                self.console.print(f"[green]Switched active model to:[/green] [bold cyan]{arg}[/bold cyan]")
            else:
                await self.interactive_model_select()

        elif cmd in ["/pull"]:
            if not arg:
                self.console.print("[yellow]Usage: /pull <model-name> (e.g. /pull qwen2.5-coder:7b)[/yellow]")
            else:
                await self.pull_model(arg)

        elif cmd in ["/scan"]:
            await self.scan_codebase()

        elif cmd in ["/tree", "/files"]:
            await self.show_tree()

        elif cmd in ["/read"]:
            if not arg:
                self.console.print("[yellow]Usage: /read <file_path>[/yellow]")
            else:
                await self.read_file_cmd(arg)

        elif cmd in ["/run"]:
            if not arg:
                self.console.print("[yellow]Usage: /run <terminal_command>[/yellow]")
            else:
                await self.run_terminal_cmd(arg)

        elif cmd in ["/mode"]:
            if arg.lower() in ["agent", "ask", "multi"]:
                self.mode = arg.lower()
                self.console.print(f"[green]Mode set to:[/green] [bold cyan]{self.mode.upper()}[/bold cyan]")
            else:
                self.console.print("[yellow]Usage: /mode [agent | multi | ask][/yellow]")

        elif cmd in ["/init"]:
            self.init_workspace()

        elif cmd in ["/clear", "/reset"]:
            self.session.clear()
            self.console.print("[green]Chat session context reset.[/green]")

        elif cmd in ["/web"]:
            self.console.print("[bold cyan]Launching SATTVA Web UI...[/bold cyan]")
            import threading
            import uvicorn
            from sattva.web.server import app

            def start_server():
                uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

            t = threading.Thread(target=start_server, daemon=True)
            t.start()
            self.console.print("[green]Server started at http://localhost:8000[/green]")
            webbrowser.open("http://localhost:8000")

        else:
            self.console.print(f"[red]Unknown command: {cmd}. Type /help for available commands.[/red]")

        return True

    def init_workspace(self):
        """Initialize workspace with .sattva configuration."""
        ws_dir = Path(self.workspace_path) / ".sattva"
        ws_dir.mkdir(parents=True, exist_ok=True)
        cfg_file = ws_dir / "config.json"
        if not cfg_file.exists():
            cfg_file.write_text('{\n  "default_model": "' + self.model + '",\n  "max_iterations": 25\n}\n', encoding="utf-8")

        rules_file = ws_dir / "rules.md"
        if not rules_file.exists():
            rules_file.write_text("# Project Custom Rules\n- Maintain clean modular architecture\n- Write unit tests for new endpoints\n", encoding="utf-8")

        gitignore = ws_dir / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("sandboxes/\nsessions/\n", encoding="utf-8")

        self.console.print(Panel(f"[bold green]✔ Initialized SATTVA workspace in:[/bold green] [cyan]{self.workspace_path}/.sattva[/cyan]\n- Config: .sattva/config.json\n- Rules: .sattva/rules.md", border_style="green"))

    def print_help(self):
        table = Table(title="SATTVA AI AGENT - Slash Commands", border_style="cyan")
        table.add_column("Command", style="bold cyan")
        table.add_column("Description", style="white")

        table.add_row("/mode [agent|multi|ask]", "Switch between Single Agent, Multi-Agent Team, and Ask modes")
        table.add_row("/model [name]", "Switch or view active Ollama model")
        table.add_row("/models", "List all locally installed Ollama models")
        table.add_row("/pull <name>", "Download/pull a new model from Ollama library")
        table.add_row("/init", "Initialize .sattva config and project rules in current directory")
        table.add_row("/scan", "Perform deep codebase scan (symbols, stats, stack)")
        table.add_row("/tree", "Display workspace directory tree")
        table.add_row("/read <file>", "Read and view a file with syntax highlighting")
        table.add_row("/run <cmd>", "Execute a terminal command directly")
        table.add_row("/web", "Launch the modern Web UI in default browser")
        table.add_row("/clear", "Reset current chat session memory")
        table.add_row("/help", "Show this help table")
        table.add_row("/exit", "Quit SATTVA CLI")

        self.console.print(table)

    async def list_models(self):
        models = await self.agent.ollama.list_models()
        if not models:
            self.console.print("[yellow]No local models found or Ollama is offline.[/yellow]")
            return

        table = Table(title="Installed Ollama Models", border_style="magenta")
        table.add_column("Model Name", style="bold cyan")
        table.add_column("Size", style="green")
        table.add_column("Params", style="yellow")
        table.add_column("Quantization", style="blue")
        table.add_column("Active", style="bold green")

        for m in models:
            is_active = "[ACTIVE]" if m["name"] == self.model else ""
            table.add_row(
                m["name"],
                m["size"],
                m.get("parameter_size", "N/A"),
                m.get("quantization_level", "N/A"),
                is_active,
            )

        self.console.print(table)

    async def interactive_model_select(self):
        models = await self.agent.ollama.list_models()
        if not models:
            self.console.print("[red]No local models available.[/red]")
            return

        self.console.print("\n[bold]Select a model to switch to:[/bold]")
        for i, m in enumerate(models, start=1):
            cur = " [bold green](active)[/bold green]" if m["name"] == self.model else ""
            self.console.print(f"  {i}. [cyan]{m['name']}[/cyan] ({m['size']}){cur}")

        choice = Prompt.ask("\nEnter model number or name", default=self.model)
        if choice.isdigit() and 1 <= int(choice) <= len(models):
            selected = models[int(choice) - 1]["name"]
        else:
            selected = choice

        self.model = selected
        self.agent.set_model(selected)
        self.orchestrator.set_model(selected)
        self.config.set("default_model", selected)
        self.console.print(f"[bold green]Switched active model to:[/bold green] [cyan]{selected}[/cyan]\n")

    async def pull_model(self, model_name: str):
        self.console.print(f"[bold cyan]Pulling '{model_name}' from Ollama library...[/bold cyan]")
        try:
            async for progress in self.agent.ollama.pull_model_stream(model_name):
                status = progress.get("status", "")
                completed = progress.get("completed", 0)
                total = progress.get("total", 0)
                if total > 0:
                    pct = round((completed / total) * 100, 1)
                    print(f"\rStatus: {status} [{pct}%] - {round(completed/(1024**2), 1)}MB / {round(total/(1024**2), 1)}MB", end="")
                else:
                    print(f"\rStatus: {status}...", end="")
            self.console.print(f"\n[bold green]✔ Successfully pulled '{model_name}'![/bold green]")
        except Exception as e:
            self.console.print(f"\n[bold red]Failed to pull model:[/bold red] {e}")

    async def scan_codebase(self):
        self.console.print("[dim]Scanning codebase...[/dim]")
        res = await self.agent.tools.execute("scan_codebase", {"target_dir": "."})
        if res.success:
            self.console.print(Panel(Markdown(res.message), title="Codebase Intelligence Scan", border_style="cyan"))
        else:
            self.console.print(f"[red]{res.error}[/red]")

    async def show_tree(self):
        res = await self.agent.tools.execute("list_directory", {"dir_path": ".", "recursive": True, "max_depth": 3})
        if res.success:
            self.console.print(Panel(res.message, title="Directory Tree", border_style="blue"))
        else:
            self.console.print(f"[red]{res.error}[/red]")

    async def read_file_cmd(self, file_path: str):
        target = Path(self.workspace_path) / file_path
        if not target.exists():
            self.console.print(f"[red]File '{file_path}' does not exist.[/red]")
            return
        content = target.read_text(encoding="utf-8", errors="replace")
        ext = target.suffix.lstrip(".") or "txt"
        self.console.print(Panel(Syntax(content, ext, line_numbers=True, theme="monokai"), title=f"File: {file_path}", border_style="cyan"))

    async def run_terminal_cmd(self, command: str):
        self.console.print(f"[dim]Executing: {command}[/dim]")
        res = await self.agent.tools.execute("run_command", {"command": command})
        self.console.print(Panel(res.message, title=f"Terminal: {command}", border_style="yellow" if not res.success else "green"))


def main():
    cli = SattvaCLI()
    asyncio.run(cli.run_loop())


if __name__ == "__main__":
    main()
