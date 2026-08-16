"""
File and Directory Operations for SATTVA AI AGENT.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from sattva.tools.base import BaseTool, ToolResult


def _resolve_path(workspace: str, relative_or_absolute: str) -> Path:
    """Safely resolve path within or relative to workspace."""
    p = Path(relative_or_absolute)
    if not p.is_absolute():
        p = Path(workspace) / p
    return p.resolve()


def _is_ignored(path: Path, workspace: Path, ignored_patterns: List[str]) -> bool:
    """Check if a path matches any ignore pattern."""
    try:
        rel = path.relative_to(workspace)
    except ValueError:
        return False
    parts = rel.parts
    for pattern in ignored_patterns:
        if pattern.startswith("*."):
            ext = pattern[1:]
            if path.name.endswith(ext):
                return True
        elif any(pattern == part or pattern in part for part in parts):
            return True
    return False


class CreateFileTool(BaseTool):
    name = "create_file"
    description = "Create a new file with specified content. Creates parent directories automatically if they do not exist."
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to create, relative to the workspace or absolute.",
            },
            "content": {
                "type": "string",
                "description": "Text content to write to the file.",
            },
            "overwrite": {
                "type": "boolean",
                "description": "Whether to overwrite the file if it already exists. Default is true.",
                "default": True,
            },
        },
        "required": ["file_path", "content"],
    }

    async def execute(self, file_path: str, content: str, overwrite: bool = True, **kwargs) -> ToolResult:
        try:
            target = _resolve_path(self.workspace_path, file_path)
            if target.exists() and not overwrite:
                return ToolResult(
                    success=False,
                    error=f"File '{file_path}' already exists and overwrite is set to false.",
                )
            
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            
            line_count = len(content.splitlines())
            byte_size = len(content.encode("utf-8"))
            return ToolResult(
                success=True,
                data={
                    "path": str(target.relative_to(Path(self.workspace_path).resolve())),
                    "lines": line_count,
                    "bytes": byte_size,
                },
                message=f"Successfully created file '{file_path}' ({line_count} lines, {byte_size} bytes).",
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to create file '{file_path}': {str(e)}")


class CreateFolderTool(BaseTool):
    name = "create_folder"
    description = "Create a directory / folder. Creates all parent directories if needed."
    parameters = {
        "type": "object",
        "properties": {
            "folder_path": {
                "type": "string",
                "description": "Path to the folder to create, relative to workspace or absolute.",
            },
        },
        "required": ["folder_path"],
    }

    async def execute(self, folder_path: str, **kwargs) -> ToolResult:
        try:
            target = _resolve_path(self.workspace_path, folder_path)
            target.mkdir(parents=True, exist_ok=True)
            return ToolResult(
                success=True,
                data={"path": str(target)},
                message=f"Successfully created directory '{folder_path}'.",
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to create folder '{folder_path}': {str(e)}")


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read the contents of a file. Supports optional line ranges for large files."
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to read.",
            },
            "start_line": {
                "type": "integer",
                "description": "1-based starting line number (optional).",
            },
            "end_line": {
                "type": "integer",
                "description": "1-based ending line number (optional).",
            },
        },
        "required": ["file_path"],
    }

    async def execute(self, file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None, **kwargs) -> ToolResult:
        try:
            target = _resolve_path(self.workspace_path, file_path)
            if not target.exists():
                return ToolResult(success=False, error=f"File not found: '{file_path}'")
            if target.is_dir():
                return ToolResult(success=False, error=f"'{file_path}' is a directory, not a file. Use list_directory instead.")

            content = target.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()
            total_lines = len(lines)

            s_line = max(1, start_line or 1)
            e_line = min(total_lines, end_line or total_lines) if total_lines > 0 else 1

            if s_line > total_lines and total_lines > 0:
                return ToolResult(
                    success=False,
                    error=f"Start line {s_line} exceeds file line count ({total_lines}).",
                )

            selected_lines = lines[s_line - 1:e_line]
            numbered_content = "\n".join(f"{i + s_line:4d} | {line}" for i, line in enumerate(selected_lines))

            return ToolResult(
                success=True,
                data={
                    "content": "\n".join(selected_lines),
                    "numbered_content": numbered_content,
                    "total_lines": total_lines,
                    "range": [s_line, e_line],
                    "path": str(target.relative_to(Path(self.workspace_path).resolve())),
                },
                message=f"File: {file_path} (Lines {s_line}-{e_line} of {total_lines}):\n\n{numbered_content}",
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to read file '{file_path}': {str(e)}")


class DeleteFileOrFolderTool(BaseTool):
    name = "delete_file_or_folder"
    description = "Delete a file or folder in the workspace."
    parameters = {
        "type": "object",
        "properties": {
            "target_path": {
                "type": "string",
                "description": "Path to the file or directory to delete.",
            },
            "recursive": {
                "type": "boolean",
                "description": "If deleting a non-empty directory, set to true. Default is true.",
                "default": True,
            },
        },
        "required": ["target_path"],
    }

    async def execute(self, target_path: str, recursive: bool = True, **kwargs) -> ToolResult:
        try:
            target = _resolve_path(self.workspace_path, target_path)
            if not target.exists():
                return ToolResult(success=False, error=f"Target path does not exist: '{target_path}'")

            # Safety check: prevent deleting root workspace
            workspace_root = Path(self.workspace_path).resolve()
            if target == workspace_root:
                return ToolResult(success=False, error="Cannot delete the workspace root directory.")

            if target.is_file() or target.is_symlink():
                target.unlink()
                return ToolResult(success=True, message=f"Deleted file '{target_path}'.")
            elif target.is_dir():
                if recursive:
                    shutil.rmtree(target)
                    return ToolResult(success=True, message=f"Deleted directory and its contents: '{target_path}'.")
                else:
                    target.rmdir()
                    return ToolResult(success=True, message=f"Deleted empty directory '{target_path}'.")
            return ToolResult(success=False, error=f"Unknown target type for '{target_path}'.")
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to delete '{target_path}': {str(e)}")


class ListDirectoryTool(BaseTool):
    name = "list_directory"
    description = "List files and subdirectories in a directory with metadata (size, item count, depth)."
    parameters = {
        "type": "object",
        "properties": {
            "dir_path": {
                "type": "string",
                "description": "Directory path to list (optional, defaults to workspace root).",
                "default": ".",
            },
            "recursive": {
                "type": "boolean",
                "description": "Whether to list recursively. Default is false.",
                "default": False,
            },
            "max_depth": {
                "type": "integer",
                "description": "Maximum recursive depth if recursive is true. Default is 3.",
                "default": 3,
            },
        },
    }

    async def execute(self, dir_path: str = ".", recursive: bool = False, max_depth: int = 3, **kwargs) -> ToolResult:
        try:
            target = _resolve_path(self.workspace_path, dir_path)
            workspace = Path(self.workspace_path).resolve()

            if not target.exists():
                return ToolResult(success=False, error=f"Directory does not exist: '{dir_path}'")
            if not target.is_dir():
                return ToolResult(success=False, error=f"'{dir_path}' is not a directory.")

            ignored = [".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"]
            entries = []

            def scan(current: Path, depth: int):
                if depth > max_depth:
                    return
                try:
                    for item in sorted(current.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                        if _is_ignored(item, workspace, ignored):
                            continue
                        rel_path = str(item.relative_to(workspace))
                        if item.is_dir():
                            child_count = len([c for c in item.iterdir() if not _is_ignored(c, workspace, ignored)])
                            entries.append({
                                "name": item.name,
                                "path": rel_path,
                                "type": "directory",
                                "children_count": child_count,
                                "depth": depth,
                            })
                            if recursive:
                                scan(item, depth + 1)
                        else:
                            size = item.stat().st_size
                            entries.append({
                                "name": item.name,
                                "path": rel_path,
                                "type": "file",
                                "size": size,
                                "depth": depth,
                            })
                except PermissionError:
                    pass

            scan(target, 1)

            # Format human readable tree
            lines = [f"Directory listing for: {dir_path} ({len(entries)} items):"]
            for e in entries:
                indent = "  " * (e.get("depth", 1) - 1)
                if e["type"] == "directory":
                    lines.append(f"{indent}📁 {e['name']}/ ({e.get('children_count', 0)} items)")
                else:
                    size_kb = round(e.get("size", 0) / 1024, 2)
                    lines.append(f"{indent}📄 {e['name']} ({size_kb} KB)")

            return ToolResult(
                success=True,
                data={"entries": entries, "count": len(entries)},
                message="\n".join(lines),
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to list directory '{dir_path}': {str(e)}")
