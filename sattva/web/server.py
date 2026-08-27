"""
FastAPI Web Server and Real-Time WebSocket Agent API for SATTVA AI AGENT.
Supports Single-Agent and Multi-Agent team execution.
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from sattva.config import Config
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


app = FastAPI(title="SATTVA AI AGENT API", version="1.1.0")

# Enable CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"

# Global state
config = Config()
agent = SattvaAgent(config=config)
orchestrator = MultiAgentOrchestrator(config=config, workspace_path=str(config.workspace_path), model=agent.model)


class ModelSwitchRequest(BaseModel):
    model: str


class PullModelRequest(BaseModel):
    model: str


class WorkspacePathRequest(BaseModel):
    path: str


class CreateFileRequest(BaseModel):
    path: str
    content: str
    overwrite: bool = True


class CreateFolderRequest(BaseModel):
    path: str


class RunTerminalRequest(BaseModel):
    command: str
    cwd: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    path: Optional[str] = "."
    is_regex: bool = False
    case_sensitive: bool = False


# API Endpoints
@app.get("/api/status")
async def get_status():
    health = await agent.ollama.check_health()
    return {
        "ollama": health,
        "active_model": agent.model,
        "workspace_path": agent.workspace_path,
        "temperature": config.temperature,
        "context_length": config.context_length,
    }


@app.get("/api/models")
async def get_models():
    models = await agent.ollama.list_models()
    return {"models": models, "active": agent.model}


@app.post("/api/models/switch")
async def switch_model(req: ModelSwitchRequest):
    agent.set_model(req.model)
    orchestrator.set_model(req.model)
    config.set("default_model", req.model)
    return {"success": True, "active_model": req.model}


@app.get("/api/multi/team")
async def get_multi_agent_team():
    """Return specialized agents metadata for Multi-Agent Mode."""
    team = []
    for role_enum, meta in ROLE_METADATA.items():
        team.append({
            "role": role_enum.value,
            "title": meta["title"],
            "icon": meta["icon"],
            "color": meta["color"],
            "description": meta["description"],
        })
    return {"team": team}


@app.get("/api/workspace/files")
async def get_workspace_files():
    res = await agent.tools.execute("list_directory", {"dir_path": ".", "recursive": True, "max_depth": 5})
    return res.to_dict()


@app.get("/api/workspace/file")
async def get_file_content(path: str = Query(...)):
    res = await agent.tools.execute("read_file", {"file_path": path})
    return res.to_dict()


@app.post("/api/workspace/file")
async def save_file_content(req: CreateFileRequest):
    res = await agent.tools.execute("create_file", {"file_path": req.path, "content": req.content, "overwrite": req.overwrite})
    return res.to_dict()


@app.delete("/api/workspace/file")
async def delete_file(path: str = Query(...)):
    res = await agent.tools.execute("delete_file_or_folder", {"target_path": path})
    return res.to_dict()


@app.post("/api/workspace/folder")
async def create_folder(req: CreateFolderRequest):
    res = await agent.tools.execute("create_folder", {"folder_path": req.path})
    return res.to_dict()


@app.get("/api/workspace/scan")
async def scan_workspace():
    res = await agent.tools.execute("scan_codebase", {"target_dir": "."})
    return res.to_dict()


@app.post("/api/workspace/search")
async def search_codebase(req: SearchRequest):
    res = await agent.tools.execute(
        "search_code",
        {
            "query": req.query,
            "path": req.path or ".",
            "is_regex": req.is_regex,
            "case_sensitive": req.case_sensitive,
        },
    )
    return res.to_dict()


@app.post("/api/workspace/set_path")
async def set_workspace_path(req: WorkspacePathRequest):
    p = Path(req.path).resolve()
    if not p.exists() or not p.is_dir():
        raise HTTPException(status_code=400, detail="Invalid directory path")
    agent.set_workspace(str(p))
    orchestrator.set_workspace(str(p))
    return {"success": True, "workspace_path": str(p)}


@app.get("/api/sessions")
async def list_sessions():
    return {"sessions": Session.list_all()}


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    sess = Session.load(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": sess.session_id,
        "title": sess.title,
        "model": sess.model,
        "workspace_path": sess.workspace_path,
        "messages": sess.messages,
    }


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    success = Session.delete(session_id)
    return {"success": success}


@app.post("/api/terminal/run")
async def run_terminal_command(req: RunTerminalRequest):
    res = await agent.tools.execute("run_command", {"command": req.command, "cwd": req.cwd or "."})
    return res.to_dict()


# Real-time WebSocket endpoint for autonomous agent and multi-agent execution
@app.websocket("/ws/agent")
async def agent_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            action = data.get("action")

            if action == "chat":
                user_msg = data.get("message", "")
                mode = data.get("mode", "agent")  # "agent", "multi", or "ask"
                model = data.get("model") or agent.model
                session_id = data.get("session_id")

                if model != agent.model:
                    agent.set_model(model)
                    orchestrator.set_model(model)

                session = Session.load(session_id) if session_id else Session(model=agent.model, workspace_path=agent.workspace_path)

                if mode == "multi":
                    # Run Multi-Agent Team pipeline
                    async for event in orchestrator.run(
                        user_message=user_msg,
                        session=session,
                    ):
                        role_val = event.role.value if event.role else None
                        role_meta = ROLE_METADATA.get(event.role, {}) if event.role else {}
                        await websocket.send_text(json.dumps({
                            "type": "multi_event",
                            "event_type": event.event_type,
                            "role": role_val,
                            "role_meta": role_meta,
                            "data": event.data,
                            "session_id": session.session_id,
                        }))
                else:
                    # Run Single Agent ReAct / Ask loop
                    async for event in agent.run(
                        user_message=user_msg,
                        session=session,
                        mode=mode,
                    ):
                        await websocket.send_text(json.dumps({
                            "type": "event",
                            "event_type": event.event_type,
                            "data": event.data,
                            "session_id": session.session_id,
                        }))

            elif action == "pull_model":
                model_name = data.get("model_name", "")
                async for progress in agent.ollama.pull_model_stream(model_name):
                    await websocket.send_text(json.dumps({
                        "type": "pull_progress",
                        "data": progress,
                    }))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({"type": "error", "error": str(e)}))
        except Exception:
            pass


# Mount static assets
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def root():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return HTMLResponse("<h1>SATTVA AI AGENT</h1><p>Web static files are initializing...</p>")
