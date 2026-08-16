"""
Search tools for SATTVA AI AGENT (Regex Grep, Glob File Finder).
"""

import os
import re
import fnmatch
from pathlib import Path
from typing import Dict, Any, List, Optional
from sattva.tools.base import BaseTool, ToolResult
from sattva.tools.file_ops import _resolve_path, _is_ignored


class SearchCodeTool(BaseTool):
    name = "search_code"
    description = "Search for a string pattern or regex across files in the workspace."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The text or regex to search for.",
            },
            "path": {
                "type": "string",
                "description": "Target directory or file to search within (optional, defaults to workspace root).",
                "default": ".",
            },
            "is_regex": {
                "type": "boolean",
                "description": "Whether query is a regular expression. Default is false.",
                "default": False,
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Whether search is case-sensitive. Default is false.",
                "default": False,
            },
            "file_pattern": {
                "type": "string",
                "description": "Optional glob filter for file names, e.g. '*.py' or '*.js'.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of matching lines to return. Default is 50.",
                "default": 50,
            },
        },
        "required": ["query"],
    }

    async def execute(
        self,
        query: str,
        path: str = ".",
        is_regex: bool = False,
        case_sensitive: bool = False,
        file_pattern: Optional[str] = None,
        max_results: int = 50,
        **kwargs,
    ) -> ToolResult:
        try:
            target = _resolve_path(self.workspace_path, path)
            workspace = Path(self.workspace_path).resolve()
            if not target.exists():
                return ToolResult(success=False, error=f"Path not found: '{path}'")

            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                pattern = re.compile(query if is_regex else re.escape(query), flags)
            except re.error as err:
                return ToolResult(success=False, error=f"Invalid regular expression: {str(err)}")

            ignored = [".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", "*.pyc"]
            matches = []

            def search_in_file(fp: Path):
                if max_results and len(matches) >= max_results:
                    return
                try:
                    rel_path = str(fp.relative_to(workspace)).replace("\\", "/")
                    content = fp.read_text(encoding="utf-8", errors="ignore")
                    for line_num, line in enumerate(content.splitlines(), start=1):
                        if pattern.search(line):
                            matches.append({
                                "file": rel_path,
                                "line_number": line_num,
                                "line_content": line.strip(),
                            })
                            if len(matches) >= max_results:
                                break
                except Exception:
                    pass

            if target.is_file():
                search_in_file(target)
            else:
                for root, dirs, files in os.walk(target):
                    curr_path = Path(root)
                    if _is_ignored(curr_path, workspace, ignored):
                        dirs[:] = []
                        continue
                    dirs[:] = [d for d in dirs if not _is_ignored(curr_path / d, workspace, ignored)]

                    for f in files:
                        if file_pattern and not fnmatch.fnmatch(f, file_pattern):
                            continue
                        fp = curr_path / f
                        if not _is_ignored(fp, workspace, ignored):
                            search_in_file(fp)
                            if len(matches) >= max_results:
                                break
                    if len(matches) >= max_results:
                        break

            if not matches:
                return ToolResult(
                    success=True,
                    data={"matches": [], "count": 0},
                    message=f"No matches found for '{query}'.",
                )

            formatted_lines = [f"Found {len(matches)} matches for '{query}':"]
            for m in matches:
                formatted_lines.append(f"  {m['file']}:{m['line_number']}  ->  {m['line_content']}")

            return ToolResult(
                success=True,
                data={"matches": matches, "count": len(matches)},
                message="\n".join(formatted_lines),
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Search failed: {str(e)}")


class FindFilesTool(BaseTool):
    name = "find_files"
    description = "Find files matching a glob pattern (e.g. '*.py', '**/*.tsx', 'test_*.py')."
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Glob pattern to match file names against.",
            },
            "root_dir": {
                "type": "string",
                "description": "Directory to search within (defaults to workspace root).",
                "default": ".",
            },
        },
        "required": ["pattern"],
    }

    async def execute(self, pattern: str, root_dir: str = ".", **kwargs) -> ToolResult:
        try:
            target = _resolve_path(self.workspace_path, root_dir)
            workspace = Path(self.workspace_path).resolve()
            if not target.exists() or not target.is_dir():
                return ToolResult(success=False, error=f"Invalid directory: '{root_dir}'")

            ignored = [".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"]
            found = []

            for root, dirs, files in os.walk(target):
                curr = Path(root)
                if _is_ignored(curr, workspace, ignored):
                    dirs[:] = []
                    continue
                dirs[:] = [d for d in dirs if not _is_ignored(curr / d, workspace, ignored)]

                for f in files:
                    fp = curr / f
                    if _is_ignored(fp, workspace, ignored):
                        continue
                    rel = str(fp.relative_to(workspace)).replace("\\", "/")
                    if fnmatch.fnmatch(f, pattern) or fnmatch.fnmatch(rel, pattern):
                        found.append(rel)

            if not found:
                return ToolResult(success=True, data={"files": []}, message=f"No files matched pattern '{pattern}'.")

            res_lines = [f"Found {len(found)} files matching '{pattern}':"] + [f"- `{f}`" for f in found]
            return ToolResult(success=True, data={"files": found, "count": len(found)}, message="\n".join(res_lines))
        except Exception as e:
            return ToolResult(success=False, error=f"File search failed: {str(e)}")
