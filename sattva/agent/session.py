"""
Session Management and Persistence for SATTVA AI AGENT.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from sattva.config import CONFIG_DIR


SESSIONS_DIR = CONFIG_DIR / "sessions"


class Session:
    def __init__(
        self,
        session_id: Optional[str] = None,
        title: str = "New Chat",
        model: str = "qwen2.5-coder:7b",
        workspace_path: str = ".",
        messages: Optional[List[Dict[str, Any]]] = None,
    ):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.title = title
        self.model = model
        self.workspace_path = str(Path(workspace_path).resolve())
        self.messages: List[Dict[str, Any]] = messages or []
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

    def add_message(self, role: str, content: str, **extra) -> Dict[str, Any]:
        msg = {
            "id": str(uuid.uuid4())[:8],
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            **extra,
        }
        self.messages.append(msg)
        self.updated_at = datetime.now().isoformat()
        if len(self.messages) == 1 and role == "user":
            # Set title from first message
            clean_title = content.strip().split("\n")[0][:40]
            if clean_title:
                self.title = clean_title
        self.save()
        return msg

    def clear(self) -> None:
        self.messages = []
        self.updated_at = datetime.now().isoformat()
        self.save()

    def save(self) -> None:
        try:
            SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
            path = SESSIONS_DIR / f"{self.session_id}.json"
            data = {
                "session_id": self.session_id,
                "title": self.title,
                "model": self.model,
                "workspace_path": self.workspace_path,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
                "messages": self.messages,
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving session {self.session_id}: {e}")

    @classmethod
    def load(cls, session_id: str) -> Optional["Session"]:
        path = SESSIONS_DIR / f"{session_id}.json"
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            sess = cls(
                session_id=data.get("session_id"),
                title=data.get("title", "New Chat"),
                model=data.get("model", "qwen2.5-coder:7b"),
                workspace_path=data.get("workspace_path", "."),
                messages=data.get("messages", []),
            )
            sess.created_at = data.get("created_at", datetime.now().isoformat())
            sess.updated_at = data.get("updated_at", datetime.now().isoformat())
            return sess
        except Exception as e:
            print(f"Error loading session {session_id}: {e}")
            return None

    @classmethod
    def list_all(cls) -> List[Dict[str, Any]]:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        sessions = []
        for file in SESSIONS_DIR.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    sessions.append({
                        "session_id": data.get("session_id", file.stem),
                        "title": data.get("title", "Untitled Session"),
                        "model": data.get("model", ""),
                        "updated_at": data.get("updated_at", ""),
                        "workspace_path": data.get("workspace_path", ""),
                        "message_count": len(data.get("messages", [])),
                    })
            except Exception:
                pass
        return sorted(sessions, key=lambda x: x.get("updated_at", ""), reverse=True)

    @classmethod
    def delete(cls, session_id: str) -> bool:
        path = SESSIONS_DIR / f"{session_id}.json"
        if path.exists():
            try:
                path.unlink()
                return True
            except Exception:
                return False
        return False
