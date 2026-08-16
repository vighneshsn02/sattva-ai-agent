"""
Configuration management for SATTVA AI AGENT.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

DEFAULT_CONFIG: Dict[str, Any] = {
    "ollama_url": "http://localhost:11434",
    "default_model": "qwen2.5-coder:7b",
    "context_length": 8192,
    "temperature": 0.2,
    "max_iterations": 25,
    "auto_confirm_terminal": False,
    "theme": "dark",
    "ignored_patterns": [
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
        ".pytest_cache",
        ".idea",
        ".vscode",
        ".next",
        ".nuxt",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        "*.obj",
        "*.exe",
        "*.dll",
        "*.so",
        "*.dylib"
    ]
}

CONFIG_DIR = Path.home() / ".sattva"
CONFIG_FILE = CONFIG_DIR / "config.json"


class Config:
    def __init__(self, workspace_path: Optional[str] = None):
        self.workspace_path = Path(workspace_path or os.getcwd()).resolve()
        self.data: Dict[str, Any] = DEFAULT_CONFIG.copy()
        self.load()

    def load(self) -> None:
        """Load configuration from user home and workspace override."""
        # 1. User global config
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    user_cfg = json.load(f)
                    self.data.update(user_cfg)
            except Exception:
                pass

        # 2. Workspace local config (.sattva/config.json)
        local_cfg_file = self.workspace_path / ".sattva" / "config.json"
        if local_cfg_file.exists():
            try:
                with open(local_cfg_file, "r", encoding="utf-8") as f:
                    local_cfg = json.load(f)
                    self.data.update(local_cfg)
            except Exception:
                pass

    def save_global(self) -> None:
        """Save current configuration to global user home."""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"Error saving global config: {e}")

    def save_local(self) -> None:
        """Save current configuration to workspace .sattva/config.json."""
        try:
            local_dir = self.workspace_path / ".sattva"
            local_dir.mkdir(parents=True, exist_ok=True)
            with open(local_dir / "config.json", "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"Error saving local config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any, save: bool = True) -> None:
        self.data[key] = value
        if save:
            self.save_global()

    @property
    def ollama_url(self) -> str:
        return self.data.get("ollama_url", "http://localhost:11434").rstrip("/")

    @property
    def default_model(self) -> str:
        return self.data.get("default_model", "qwen2.5-coder:7b")

    @property
    def context_length(self) -> int:
        return int(self.data.get("context_length", 8192))

    @property
    def temperature(self) -> float:
        return float(self.data.get("temperature", 0.2))

    @property
    def max_iterations(self) -> int:
        return int(self.data.get("max_iterations", 25))

    @property
    def auto_confirm_terminal(self) -> bool:
        return bool(self.data.get("auto_confirm_terminal", False))

    @property
    def ignored_patterns(self) -> list:
        return self.data.get("ignored_patterns", DEFAULT_CONFIG["ignored_patterns"])
