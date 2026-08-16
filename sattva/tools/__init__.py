"""
Tool definitions and registry for SATTVA AI AGENT.
"""

from sattva.tools.base import BaseTool, ToolResult, ToolRegistry
from sattva.tools.file_ops import (
    CreateFileTool,
    CreateFolderTool,
    ReadFileTool,
    DeleteFileOrFolderTool,
    ListDirectoryTool,
)
from sattva.tools.code_edit import (
    EditFileTool,
    InsertCodeTool,
)
from sattva.tools.scanner import (
    ScanCodebaseTool,
    CodebaseScanner,
)
from sattva.tools.search import (
    SearchCodeTool,
    FindFilesTool,
)
from sattva.tools.terminal import (
    RunCommandTool,
    RunTestsTool,
)


def create_default_registry(workspace_path: str) -> ToolRegistry:
    """Create a ToolRegistry with all standard Sattva AI coding tools pre-registered."""
    registry = ToolRegistry(workspace_path)
    
    # File & Directory
    registry.register(CreateFileTool)
    registry.register(CreateFolderTool)
    registry.register(ReadFileTool)
    registry.register(DeleteFileOrFolderTool)
    registry.register(ListDirectoryTool)
    
    # Code Editing
    registry.register(EditFileTool)
    registry.register(InsertCodeTool)
    
    # Codebase Intelligence & Search
    registry.register(ScanCodebaseTool)
    registry.register(SearchCodeTool)
    registry.register(FindFilesTool)
    
    # Execution
    registry.register(RunCommandTool)
    registry.register(RunTestsTool)
    
    return registry


__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolRegistry",
    "CreateFileTool",
    "CreateFolderTool",
    "ReadFileTool",
    "DeleteFileOrFolderTool",
    "ListDirectoryTool",
    "EditFileTool",
    "InsertCodeTool",
    "ScanCodebaseTool",
    "CodebaseScanner",
    "SearchCodeTool",
    "FindFilesTool",
    "RunCommandTool",
    "RunTestsTool",
    "create_default_registry",
]
