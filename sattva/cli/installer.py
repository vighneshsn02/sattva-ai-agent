"""
Cross-Platform Global System Installer for SATTVA AI AGENT.
Installs `sattva` as a system-wide command and automatically manages PATH on Windows, Linux, and macOS.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def get_user_bin_dir() -> Path:
    """Return user-specific binary directory for global command wrappers."""
    if sys.platform.startswith("win"):
        user_bin = Path.home() / ".sattva" / "bin"
    else:
        user_bin = Path.home() / ".local" / "bin"
    user_bin.mkdir(parents=True, exist_ok=True)
    return user_bin


def is_in_path(directory: Path) -> bool:
    """Check if directory is in system PATH."""
    dir_str = str(directory.resolve()).lower()
    path_env = os.environ.get("PATH", "").lower()
    return dir_str in path_env


def add_to_windows_path(directory: Path) -> bool:
    """Add directory to Windows User Environment PATH permanently via PowerShell."""
    try:
        dir_str = str(directory.resolve())
        ps_script = f"""
        $targetDir = "{dir_str}"
        $currentPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)
        if (-not ($currentPath -split ';' | Where-Object {{ $_ -eq $targetDir }})) {{
            $newPath = "$currentPath;$targetDir"
            [Environment]::SetEnvironmentVariable("Path", $newPath, [EnvironmentVariableTarget]::User)
            Write-Host "PATH_UPDATED"
        }} else {{
            Write-Host "ALREADY_IN_PATH"
        }}
        """
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True,
            text=True,
        )
        # Also update current process env
        os.environ["PATH"] = f"{dir_str};" + os.environ.get("PATH", "")
        return proc.returncode == 0
    except Exception as e:
        console.print(f"[yellow]Warning: Could not automatically set User PATH: {e}[/yellow]")
        return False


def add_to_unix_path(directory: Path) -> bool:
    """Add directory to Unix shell configuration (.bashrc, .zshrc)."""
    dir_str = str(directory.resolve())
    export_line = f'\nexport PATH="{dir_str}:$PATH"\n'
    home = Path.home()
    rc_files = [home / ".bashrc", home / ".zshrc", home / ".profile"]
    updated = False

    for rc in rc_files:
        if rc.exists():
            content = rc.read_text(encoding="utf-8", errors="replace")
            if dir_str not in content:
                with open(rc, "a", encoding="utf-8") as f:
                    f.write(export_line)
                updated = True
    return updated


def create_global_wrappers(repo_root: Path, user_bin: Path) -> List[Path]:
    """Generate platform-specific wrapper scripts so `sattva` can be invoked from any directory."""
    python_exe = sys.executable
    main_py = repo_root / "sattva" / "main.py"
    created = []

    if sys.platform.startswith("win"):
        # 1. sattva.cmd
        cmd_path = user_bin / "sattva.cmd"
        cmd_content = f'@echo off\r\n"{python_exe}" "{main_py}" %*\r\n'
        cmd_path.write_text(cmd_content, encoding="utf-8")
        created.append(cmd_path)

        # 2. sattva.bat
        bat_path = user_bin / "sattva.bat"
        bat_content = f'@echo off\r\n"{python_exe}" "{main_py}" %*\r\n'
        bat_path.write_text(bat_content, encoding="utf-8")
        created.append(bat_path)

        # 3. sattva (for bash in git bash / msys / wsl)
        sh_path = user_bin / "sattva"
        sh_content = f'#!/usr/bin/env sh\n"{python_exe}" "{main_py}" "$@"\n'
        sh_path.write_text(sh_content, encoding="utf-8")
        created.append(sh_path)

    else:
        # Unix / macOS shell script
        sh_path = user_bin / "sattva"
        sh_content = f'#!/usr/bin/env bash\nexec "{python_exe}" "{main_py}" "$@"\n'
        sh_path.write_text(sh_content, encoding="utf-8")
        try:
            sh_path.chmod(0o755)
        except Exception:
            pass
        created.append(sh_path)

    return created


def run_global_installer():
    """Execute complete global installation and PATH registration."""
    console.print("\n[bold cyan]⚡ SATTVA AI AGENT — Global System-Wide CLI Installer[/bold cyan]")
    console.print("[dim]Registering `sattva` as a globally available command on your machine...[/dim]\n")

    repo_root = Path(__file__).parent.parent.parent.resolve()
    user_bin = get_user_bin_dir()

    # 1. Install package via pip in editable mode
    console.print("[bold yellow]Step 1:[/bold yellow] Installing sattva package via pip in editable mode...")
    try:
        pip_proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", str(repo_root)],
            capture_output=True,
            text=True,
        )
        if pip_proc.returncode == 0:
            console.print("[bold green]✔ Package installed successfully with pip entrypoints.[/bold green]")
        else:
            console.print(f"[yellow]Pip editable install returned non-zero code. Falling back to global wrappers.[/yellow]")
    except Exception as e:
        console.print(f"[yellow]Pip notice: {e}[/yellow]")

    # 2. Create Global Wrappers
    console.print("\n[bold yellow]Step 2:[/bold yellow] Generating system wrappers in ~/.sattva/bin...")
    wrappers = create_global_wrappers(repo_root, user_bin)
    for w in wrappers:
        console.print(f"  [green]✔[/green] Created: [cyan]{w}[/cyan]")

    # 3. Configure PATH
    console.print("\n[bold yellow]Step 3:[/bold yellow] Verifying and updating system PATH environment variable...")
    if not is_in_path(user_bin):
        if sys.platform.startswith("win"):
            add_to_windows_path(user_bin)
            console.print(f"  [bold green]✔ Added {user_bin} to Windows User PATH permanently.[/bold green]")
        else:
            add_to_unix_path(user_bin)
            console.print(f"  [bold green]✔ Added {user_bin} to ~/.bashrc and ~/.zshrc.[/bold green]")
    else:
        console.print(f"  [bold green]✔ {user_bin} is already present in PATH.[/bold green]")

    # Summary table
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan")
    table.add_column(style="white")
    table.add_row("Command:", "[bold green]sattva[/bold green]")
    table.add_row("Wrapper Path:", f"[cyan]{user_bin}[/cyan]")
    table.add_row("Status:", "[bold green]Ready for global use from any directory![/bold green]")
    table.add_row("Try it now:", "[bold yellow]sattva --version[/bold yellow] or [bold yellow]sattva \"your prompt\"[/bold yellow]")

    console.print()
    console.print(Panel(table, title="[bold white]INSTALLATION COMPLETE[/bold white]", border_style="green"))
    console.print("[dim]Note: If running in an existing open terminal, you can immediately use `sattva` or open a new terminal window.[/dim]\n")


if __name__ == "__main__":
    run_global_installer()
