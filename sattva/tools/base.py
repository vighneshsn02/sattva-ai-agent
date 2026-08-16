"""
Base Tool class and Registry for SATTVA AI AGENT.
"""

import json
from typing import Dict, Any, Callable, List, Optional
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    success: bool
    data: Any = None
    error: Optional[str] = None
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "message": self.message,
        }

    def __str__(self) -> str:
        if not self.success:
            return f"Error: {self.error or 'Operation failed'}"
        if self.message:
            return self.message
        if isinstance(self.data, (dict, list)):
            return json.dumps(self.data, indent=2)
        return str(self.data)


class BaseTool:
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}

    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path

    async def execute(self, **kwargs) -> ToolResult:
        raise NotImplementedError

    def to_ollama_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def to_prompt_description(self) -> str:
        param_desc = []
        props = self.parameters.get("properties", {})
        required = self.parameters.get("required", [])
        for prop_name, prop_data in props.items():
            req_str = " (required)" if prop_name in required else " (optional)"
            param_desc.append(f"    - `{prop_name}` ({prop_data.get('type', 'any')}{req_str}): {prop_data.get('description', '')}")
        
        params_str = "\n".join(param_desc) if param_desc else "    (No parameters)"
        return f"### `{self.name}`\n{self.description}\n**Parameters:**\n{params_str}"


class ToolRegistry:
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.tools: Dict[str, BaseTool] = {}

    def register(self, tool_cls: type[BaseTool]) -> None:
        instance = tool_cls(self.workspace_path)
        self.tools[instance.name] = instance

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self.tools.get(name)

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        return [tool.to_ollama_schema() for tool in self.tools.values()]

    def get_tools_prompt_documentation(self) -> str:
        return "\n\n".join(tool.to_prompt_description() for tool in self.tools.values())

    async def execute(self, name: str, arguments: Dict[str, Any]) -> ToolResult:
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' is not registered. Available tools: {', '.join(self.tools.keys())}",
            )
        try:
            return await tool.execute(**arguments)
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' failed with exception: {str(e)}",
            )
