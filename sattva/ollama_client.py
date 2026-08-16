"""
Asynchronous and Synchronous Ollama Client with Tool Calling support for SATTVA AI AGENT.
"""

import json
import re
import time
import httpx
from typing import Dict, Any, List, Optional, AsyncGenerator, Callable


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def check_health(self) -> Dict[str, Any]:
        """Check if Ollama server is running and get latency & version."""
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/api/version")
                latency_ms = round((time.time() - start) * 1000, 1)
                if res.status_code == 200:
                    data = res.json()
                    return {
                        "online": True,
                        "version": data.get("version", "unknown"),
                        "latency_ms": latency_ms,
                        "url": self.base_url,
                    }
                return {
                    "online": False,
                    "error": f"HTTP {res.status_code}",
                    "latency_ms": latency_ms,
                    "url": self.base_url,
                }
        except Exception as e:
            return {
                "online": False,
                "error": str(e),
                "latency_ms": 0,
                "url": self.base_url,
            }

    async def list_models(self) -> List[Dict[str, Any]]:
        """List all available models in local Ollama instance."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    raw_models = data.get("models", [])
                    formatted = []
                    for m in raw_models:
                        name = m.get("name", "")
                        size_bytes = m.get("size", 0)
                        size_gb = round(size_bytes / (1024**3), 2) if size_bytes else 0
                        details = m.get("details", {})
                        formatted.append({
                            "name": name,
                            "tag": name.split(":")[-1] if ":" in name else "latest",
                            "size": f"{size_gb} GB" if size_gb > 0 else "Unknown",
                            "size_bytes": size_bytes,
                            "modified_at": m.get("modified_at", ""),
                            "family": details.get("family", ""),
                            "parameter_size": details.get("parameter_size", ""),
                            "quantization_level": details.get("quantization_level", ""),
                        })
                    return formatted
                return []
        except Exception as e:
            print(f"[Sattva Ollama] Error listing models: {e}")
            return []

    async def show_model(self, model_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific model."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(f"{self.base_url}/api/show", json={"name": model_name})
                if res.status_code == 200:
                    return res.json()
                return {}
        except Exception as e:
            return {"error": str(e)}

    async def pull_model_stream(self, model_name: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Pull a model from Ollama library with streaming progress events."""
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/pull",
                json={"name": model_name, "stream": True},
            ) as response:
                if response.status_code != 200:
                    yield {"status": "error", "error": f"HTTP {response.status_code}: {await response.aread()}"}
                    return

                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            payload = json.loads(line)
                            yield payload
                        except Exception:
                            pass

    async def chat_stream(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream chat responses from Ollama with support for tool calling.
        Yields chunk dictionaries with 'content', 'tool_calls', 'done', and stats.
        """
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools

        if options:
            payload["options"] = options

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        err_body = await response.aread()
                        yield {
                            "content": f"\n\n[Ollama Error {response.status_code}]: {err_body.decode('utf-8', 'ignore')}",
                            "done": True,
                            "error": True,
                        }
                        return

                    accumulated_content = ""
                    accumulated_tool_calls: List[Dict[str, Any]] = []

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            chunk = json.loads(line)
                        except Exception:
                            continue

                        msg = chunk.get("message", {})
                        chunk_content = msg.get("content", "")
                        chunk_tool_calls = msg.get("tool_calls", [])
                        is_done = chunk.get("done", False)

                        if chunk_content:
                            accumulated_content += chunk_content

                        if chunk_tool_calls:
                            accumulated_tool_calls.extend(chunk_tool_calls)

                        yield {
                            "content": chunk_content,
                            "accumulated": accumulated_content,
                            "tool_calls": chunk_tool_calls,
                            "done": is_done,
                            "total_duration": chunk.get("total_duration"),
                            "eval_count": chunk.get("eval_count"),
                            "eval_duration": chunk.get("eval_duration"),
                        }

            except httpx.ConnectError:
                yield {
                    "content": f"\n\n[Connection Error]: Could not connect to Ollama at {self.base_url}. Please ensure Ollama is running (`ollama serve`).",
                    "done": True,
                    "error": True,
                }
            except Exception as e:
                yield {
                    "content": f"\n\n[Error]: {str(e)}",
                    "done": True,
                    "error": True,
                }
