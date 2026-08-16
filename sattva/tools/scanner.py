"""
Codebase Scanner and AST Symbol Extractor for SATTVA AI AGENT.
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from sattva.tools.base import BaseTool, ToolResult
from sattva.tools.file_ops import _resolve_path, _is_ignored


class CodebaseScanner:
    def __init__(self, root_path: Path, ignored_patterns: Optional[List[str]] = None):
        self.root = root_path
        self.ignored = ignored_patterns or [
            ".git", "node_modules", "__pycache__", ".venv", "venv",
            "dist", "build", ".pytest_cache", ".idea", ".vscode",
            ".next", ".nuxt", "*.pyc", "*.exe", "*.dll"
        ]

    def scan(self) -> Dict[str, Any]:
        total_files = 0
        total_lines = 0
        total_bytes = 0
        extensions: Dict[str, int] = {}
        file_tree: List[str] = []
        key_symbols: Dict[str, Any] = {}
        detected_frameworks: List[str] = []

        for root, dirs, files in os.walk(self.root):
            curr_path = Path(root)
            if _is_ignored(curr_path, self.root, self.ignored):
                dirs[:] = []
                continue

            # Filter dirs in place
            dirs[:] = [d for d in dirs if not _is_ignored(curr_path / d, self.root, self.ignored)]

            for f in files:
                file_path = curr_path / f
                if _is_ignored(file_path, self.root, self.ignored):
                    continue

                total_files += 1
                try:
                    size = file_path.stat().st_size
                    total_bytes += size
                except Exception:
                    size = 0

                ext = file_path.suffix.lower() or "(no-ext)"
                extensions[ext] = extensions.get(ext, 0) + 1

                rel_str = str(file_path.relative_to(self.root)).replace("\\", "/")
                file_tree.append(rel_str)

                # Framework detection signals
                if f == "package.json":
                    detected_frameworks.append("Node.js / npm")
                elif f == "requirements.txt" or f == "pyproject.toml":
                    detected_frameworks.append("Python")
                elif f == "Cargo.toml":
                    detected_frameworks.append("Rust / Cargo")
                elif f == "go.mod":
                    detected_frameworks.append("Go")
                elif f == "Dockerfile" or f == "docker-compose.yml":
                    detected_frameworks.append("Docker")

                # Extract AST/symbols for supported code files
                if size < 500_000:  # Skip files > 500KB for speed
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        lines = len(content.splitlines())
                        total_lines += lines

                        if ext == ".py":
                            symbols = self._extract_python_symbols(content)
                            if symbols:
                                key_symbols[rel_str] = symbols
                        elif ext in [".js", ".jsx", ".ts", ".tsx", ".mjs"]:
                            symbols = self._extract_js_symbols(content)
                            if symbols:
                                key_symbols[rel_str] = symbols
                    except Exception:
                        pass

        detected_frameworks = list(set(detected_frameworks))

        return {
            "root": str(self.root),
            "total_files": total_files,
            "total_lines": total_lines,
            "total_bytes": total_bytes,
            "extensions": extensions,
            "frameworks": detected_frameworks,
            "file_list": file_tree,
            "symbols": key_symbols,
        }

    def _extract_python_symbols(self, code: str) -> Dict[str, Any]:
        classes = []
        functions = []
        imports = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                    classes.append({"name": node.name, "line": node.lineno, "methods": methods})
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Only top-level or module functions
                    functions.append({"name": node.name, "line": node.lineno, "is_async": isinstance(node, ast.AsyncFunctionDef)})
                elif isinstance(node, ast.Import):
                    for n in node.names:
                        imports.append(n.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
        except Exception:
            pass
        
        # Deduplicate top-level functions vs class methods
        class_method_names = {m for c in classes for m in c.get("methods", [])}
        top_functions = [f for f in functions if f["name"] not in class_method_names]

        return {
            "classes": classes,
            "functions": top_functions[:20],
            "imports": list(set(imports))[:15],
        }

    def _extract_js_symbols(self, code: str) -> Dict[str, Any]:
        functions = []
        classes = []
        # Match class ClassName
        for match in re.finditer(r"class\s+([A-Za-z0-9_$]+)", code):
            classes.append({"name": match.group(1)})
        # Match function functionName or const/let name = (...) =>
        for match in re.finditer(r"(?:function\s+([A-Za-z0-9_$]+)|(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)", code):
            fn_name = match.group(1) or match.group(2)
            if fn_name:
                functions.append({"name": fn_name})
        return {
            "classes": classes[:10],
            "functions": functions[:20],
        }


class ScanCodebaseTool(BaseTool):
    name = "scan_codebase"
    description = (
        "Scan the codebase structure, directory tree, code symbols (classes, functions), "
        "file types breakdown, and tech stack detection."
    )
    parameters = {
        "type": "object",
        "properties": {
            "target_dir": {
                "type": "string",
                "description": "Directory to scan (defaults to workspace root).",
                "default": ".",
            },
        },
    }

    async def execute(self, target_dir: str = ".", **kwargs) -> ToolResult:
        try:
            target = _resolve_path(self.workspace_path, target_dir)
            if not target.exists() or not target.is_dir():
                return ToolResult(success=False, error=f"Invalid scan directory: '{target_dir}'")

            scanner = CodebaseScanner(target)
            data = scanner.scan()

            # Format summary text
            ext_str = ", ".join(f"{ext}: {cnt}" for ext, cnt in sorted(data["extensions"].items(), key=lambda x: -x[1])[:8])
            frameworks_str = ", ".join(data["frameworks"]) or "Generic"
            size_mb = round(data["total_bytes"] / (1024 * 1024), 2)

            lines = [
                f"### Codebase Scan Summary ({target.name or 'Root'})",
                f"- **Total Files**: {data['total_files']} files",
                f"- **Total Lines of Code**: {data['total_lines']} lines",
                f"- **Total Size**: {size_mb} MB",
                f"- **Detected Tech Stack**: {frameworks_str}",
                f"- **File Types**: {ext_str or 'None'}",
                "",
                "#### File Structure (sample):",
            ]
            for f in data["file_list"][:30]:
                lines.append(f"- `{f}`")
            if len(data["file_list"]) > 30:
                lines.append(f"- ... and {len(data['file_list']) - 30} more files")

            if data["symbols"]:
                lines.append("\n#### Key Symbols:")
                for file, sym in list(data["symbols"].items())[:8]:
                    cls_list = [c["name"] for c in sym.get("classes", [])]
                    fn_list = [fn["name"] for fn in sym.get("functions", [])]
                    parts = []
                    if cls_list:
                        parts.append(f"Classes: {', '.join(cls_list)}")
                    if fn_list:
                        parts.append(f"Functions: {', '.join(fn_list[:5])}")
                    lines.append(f"- **{file}**: {' | '.join(parts)}")

            return ToolResult(
                success=True,
                data=data,
                message="\n".join(lines),
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to scan codebase: {str(e)}")
