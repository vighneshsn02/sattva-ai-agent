"""
Code Editing Tools for SATTVA AI AGENT with smart matching and visual diff generation.
"""

import difflib
from pathlib import Path
from typing import Dict, Any, Optional, List
from sattva.tools.base import BaseTool, ToolResult
from sattva.tools.file_ops import _resolve_path


def _generate_diff(old_content: str, new_content: str, filename: str) -> str:
    """Generate a clean unified diff string."""
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        n=3,
    )
    return "".join(diff)


class EditFileTool(BaseTool):
    name = "edit_file"
    description = (
        "Edit a file by replacing an exact section of text (target_content) with new text (replacement_content). "
        "The target_content must match existing content in the file."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to edit.",
            },
            "target_content": {
                "type": "string",
                "description": "The exact existing text in the file to be replaced.",
            },
            "replacement_content": {
                "type": "string",
                "description": "The new text that should replace target_content.",
            },
            "allow_multiple": {
                "type": "boolean",
                "description": "Whether to replace all occurrences if target_content appears more than once. Default is false.",
                "default": False,
            },
        },
        "required": ["file_path", "target_content", "replacement_content"],
    }

    async def execute(
        self,
        file_path: str,
        target_content: str,
        replacement_content: str,
        allow_multiple: bool = False,
        **kwargs,
    ) -> ToolResult:
        try:
            target = _resolve_path(self.workspace_path, file_path)
            if not target.exists():
                return ToolResult(success=False, error=f"File '{file_path}' does not exist.")
            if target.is_dir():
                return ToolResult(success=False, error=f"'{file_path}' is a directory, not a file.")

            original_text = target.read_text(encoding="utf-8", errors="replace")

            # Try exact match first
            occurrences = original_text.count(target_content)

            # If no exact match, try normalized newline match
            normalized_orig = original_text.replace("\r\n", "\n")
            normalized_target = target_content.replace("\r\n", "\n")
            normalized_replacement = replacement_content.replace("\r\n", "\n")

            if occurrences == 0 and normalized_target in normalized_orig:
                original_text = normalized_orig
                target_content = normalized_target
                replacement_content = normalized_replacement
                occurrences = original_text.count(target_content)

            if occurrences == 0:
                # Find closest match to help agent auto-correct
                lines = original_text.splitlines()
                target_first_line = target_content.splitlines()[0] if target_content.splitlines() else ""
                possible_lines = [
                    f"Line {idx+1}: {line.strip()}"
                    for idx, line in enumerate(lines)
                    if target_first_line and target_first_line.strip() in line
                ]
                hint = ""
                if possible_lines:
                    hint = "\nSimilar lines found in file:\n" + "\n".join(possible_lines[:5])
                return ToolResult(
                    success=False,
                    error=f"Target content not found in '{file_path}'. Please ensure exact match including whitespace and indentation.{hint}",
                )

            if occurrences > 1 and not allow_multiple:
                return ToolResult(
                    success=False,
                    error=(
                        f"Target content was found {occurrences} times in '{file_path}'. "
                        "Please provide more surrounding context to match uniquely, or set allow_multiple=true."
                    ),
                )

            # Perform replacement
            if allow_multiple:
                new_text = original_text.replace(target_content, replacement_content)
            else:
                new_text = original_text.replace(target_content, replacement_content, 1)

            # Write back
            target.write_text(new_text, encoding="utf-8")

            # Generate diff
            diff_text = _generate_diff(original_text, new_text, file_path)

            return ToolResult(
                success=True,
                data={
                    "path": str(target.relative_to(Path(self.workspace_path).resolve())),
                    "occurrences_replaced": occurrences if allow_multiple else 1,
                    "diff": diff_text,
                },
                message=f"Successfully edited '{file_path}'.\n\nDiff:\n{diff_text or '(Content updated without visual diff)'}",
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to edit file '{file_path}': {str(e)}")


class InsertCodeTool(BaseTool):
    name = "insert_code"
    description = "Insert code into a file at a specific line number or relative to an existing text anchor."
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to modify.",
            },
            "content": {
                "type": "string",
                "description": "The code to insert.",
            },
            "line_number": {
                "type": "integer",
                "description": "1-based line number where code should be inserted (optional).",
            },
            "after_anchor": {
                "type": "string",
                "description": "Insert after this exact text line or snippet (optional).",
            },
            "before_anchor": {
                "type": "string",
                "description": "Insert before this exact text line or snippet (optional).",
            },
        },
        "required": ["file_path", "content"],
    }

    async def execute(
        self,
        file_path: str,
        content: str,
        line_number: Optional[int] = None,
        after_anchor: Optional[str] = None,
        before_anchor: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        try:
            target = _resolve_path(self.workspace_path, file_path)
            if not target.exists():
                return ToolResult(success=False, error=f"File '{file_path}' does not exist.")

            original_text = target.read_text(encoding="utf-8", errors="replace")
            lines = original_text.splitlines(keepends=True)

            if line_number is not None:
                idx = max(0, min(len(lines), line_number - 1))
                insertion = content if content.endswith("\n") else content + "\n"
                lines.insert(idx, insertion)
            elif after_anchor:
                anchor_norm = after_anchor.strip()
                match_idx = -1
                for i, l in enumerate(lines):
                    if anchor_norm in l:
                        match_idx = i
                        break
                if match_idx == -1:
                    return ToolResult(success=False, error=f"Anchor '{after_anchor}' not found in '{file_path}'.")
                insertion = content if content.endswith("\n") else content + "\n"
                lines.insert(match_idx + 1, insertion)
            elif before_anchor:
                anchor_norm = before_anchor.strip()
                match_idx = -1
                for i, l in enumerate(lines):
                    if anchor_norm in l:
                        match_idx = i
                        break
                if match_idx == -1:
                    return ToolResult(success=False, error=f"Anchor '{before_anchor}' not found in '{file_path}'.")
                insertion = content if content.endswith("\n") else content + "\n"
                lines.insert(match_idx, insertion)
            else:
                # Append to end of file
                insertion = content if content.endswith("\n") else "\n" + content + "\n"
                lines.append(insertion)

            new_text = "".join(lines)
            target.write_text(new_text, encoding="utf-8")
            diff_text = _generate_diff(original_text, new_text, file_path)

            return ToolResult(
                success=True,
                data={"path": file_path, "diff": diff_text},
                message=f"Inserted code into '{file_path}'.\n\nDiff:\n{diff_text}",
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to insert code into '{file_path}': {str(e)}")
