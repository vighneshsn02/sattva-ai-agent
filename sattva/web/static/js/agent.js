function safeRenderMarkdown(text) {
  if (!text) return "";
  if (typeof marked !== "undefined" && typeof marked.parse === "function") {
    try {
      return marked.parse(text);
    } catch (e) {
      console.warn("marked parse error:", e);
    }
  }
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  html = html.replace(/```([\w-]*)\n([\s\S]*?)```/g, (m, lang, code) => {
    return `<pre><code>${code}</code></pre>`;
  });
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(/^### (.*$)/gim, "<h3>$1</h3>");
  html = html.replace(/^## (.*$)/gim, "<h2>$1</h2>");
  html = html.replace(/^# (.*$)/gim, "<h1>$1</h1>");
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  html = html.replace(/^\s*-\s+(.*$)/gim, "<li>$1</li>");
  html = html.replace(/\n\n/g, "<br/><br/>");
  return html;
}
window.safeRenderMarkdown = safeRenderMarkdown;

class AgentController {
  constructor() {
    this.messagesContainer = document.getElementById("chat-messages-container");
    this.inputBox = document.getElementById("chat-input");
    this.sendBtn = document.getElementById("btn-send-message");
    this.mode = "agent"; // "agent" or "ask"
    this.currentSessionId = null;
    this.ws = null;
    this.currentAssistantBubble = null;
    this.currentAssistantText = "";

    this.initEvents();
    this.connectWebSocket();
  }

  initEvents() {
    this.sendBtn.addEventListener("click", () => this.sendMessage());
    this.inputBox.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });

    // Auto-resize textarea
    this.inputBox.addEventListener("input", () => {
      this.inputBox.style.height = "auto";
      this.inputBox.style.height = `${Math.min(this.inputBox.scrollHeight, 140)}px`;
    });

    // Mode Toggle
    document.getElementById("btn-mode-agent").addEventListener("click", () => this.setMode("agent"));
    document.getElementById("btn-mode-ask").addEventListener("click", () => this.setMode("ask"));

    // Quick prompt cards
    document.querySelectorAll(".quick-prompt-card").forEach((card) => {
      card.addEventListener("click", () => {
        const prompt = card.dataset.prompt;
        this.inputBox.value = prompt;
        this.sendMessage();
      });
    });

    // Quick tags
    document.querySelectorAll(".suggestion-tag").forEach((tag) => {
      tag.addEventListener("click", () => {
        const text = tag.dataset.tag;
        if (text === "/scan") {
          this.inputBox.value = "Scan the codebase and give me a complete summary of files, architecture, and tech stack.";
        } else {
          this.inputBox.value += (this.inputBox.value ? " " : "") + text;
        }
        this.inputBox.focus();
      });
    });
  }

  setMode(newMode) {
    this.mode = newMode;
    document.getElementById("btn-mode-agent").classList.toggle("active", newMode === "agent");
    document.getElementById("btn-mode-ask").classList.toggle("active", newMode === "ask");
    document.getElementById("status-mode-label").textContent = `Mode: ${newMode === "agent" ? "Autonomous Agent" : "Ask & Explain"}`;
  }

  connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/ws/agent`;

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log("[Sattva WS] Connected to agent backend.");
    };

    this.ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === "event") {
          this.handleAgentEvent(payload.event_type, payload.data, payload.session_id);
        } else if (payload.type === "pull_progress") {
          if (window.modelManager) {
            window.modelManager.handlePullProgress(payload.data);
          }
        }
      } catch (err) {
        console.error("Error parsing WS message:", err);
      }
    };

    this.ws.onclose = () => {
      console.log("[Sattva WS] Closed. Reconnecting in 2s...");
      setTimeout(() => this.connectWebSocket(), 2000);
    };
  }

  sendMessage() {
    const message = this.inputBox.value.trim();
    if (!message) return;

    // Hide welcome card if present
    const welcome = document.getElementById("welcome-card");
    if (welcome) welcome.style.display = "none";

    // Append User Message Bubble
    this.appendUserMessage(message);
    this.inputBox.value = "";
    this.inputBox.style.height = "auto";

    // Send to WebSocket
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        action: "chat",
        message: message,
        mode: this.mode,
        model: window.modelManager ? window.modelManager.activeModel : undefined,
        session_id: this.currentSessionId,
      }));
    } else {
      alert("WebSocket connection not ready. Please wait a moment.");
    }
  }

  appendUserMessage(text) {
    const row = document.createElement("div");
    row.className = "message-row user-row";
    row.innerHTML = `<div class="user-bubble">${this.escapeHtml(text)}</div>`;
    this.messagesContainer.appendChild(row);
    this.scrollToBottom();
  }

  handleAgentEvent(eventType, data, sessionId) {
    if (sessionId) {
      this.currentSessionId = sessionId;
    }

    if (eventType === "start") {
      this.currentAssistantText = "";
      const row = document.createElement("div");
      row.className = "message-row assistant-row";
      const bubble = document.createElement("div");
      bubble.className = "assistant-bubble";
      row.appendChild(bubble);
      this.messagesContainer.appendChild(row);
      this.currentAssistantBubble = bubble;
    }

    else if (eventType === "thought_chunk") {
      const chunk = data.chunk || "";
      this.currentAssistantText += chunk;
      if (this.currentAssistantBubble) {
        this.currentAssistantBubble.innerHTML = safeRenderMarkdown(this.currentAssistantText);
      }
      this.scrollToBottom();
    }

    else if (eventType === "tool_start") {
      const toolName = data.tool;
      const args = data.arguments || {};
      const card = document.createElement("div");
      card.className = "tool-step-card";
      card.id = `tool-card-${Date.now()}`;
      
      const argsSummary = Object.entries(args).map(([k, v]) => `${k}="${this.escapeHtml(String(v)).slice(0, 60)}"`).join(" ");
      card.innerHTML = `
        <div class="tool-step-header">
          <span class="tool-name-badge">⚡ ${toolName} <span style="font-weight:400; color:var(--text-muted);">(${argsSummary})</span></span>
          <span class="tool-step-status running">● Running...</span>
        </div>
        <div class="tool-step-body" style="display:none;"></div>
      `;
      this.messagesContainer.appendChild(card);
      this.scrollToBottom();
      this.lastToolCard = card;
    }

    else if (eventType === "tool_end") {
      const toolName = data.tool;
      const success = data.success;
      const message = data.message || "";
      const result = data.result || {};

      if (this.lastToolCard) {
        const statusEl = this.lastToolCard.querySelector(".tool-step-status");
        if (statusEl) {
          statusEl.className = `tool-step-status ${success ? "success" : "failed"}`;
          statusEl.textContent = success ? "✔ Completed" : "✘ Failed";
        }
        const bodyEl = this.lastToolCard.querySelector(".tool-step-body");
        if (bodyEl) {
          bodyEl.style.display = "block";
          bodyEl.textContent = message;
        }

        // Toggle collapse on header click
        const headerEl = this.lastToolCard.querySelector(".tool-step-header");
        if (headerEl && bodyEl) {
          headerEl.onclick = () => {
            bodyEl.style.display = bodyEl.style.display === "none" ? "block" : "none";
          };
        }
      }

      // Check if diff returned, update diff viewer
      if (result.data && result.data.diff) {
        if (window.diffViewer) {
          window.diffViewer.showDiff(result.data.diff, result.data.path || toolName);
        }
      }

      // Refresh file tree if files/folders were touched
      if (["create_file", "edit_file", "delete_file_or_folder", "create_folder"].includes(toolName)) {
        if (window.fileExplorer) {
          window.fileExplorer.refresh();
        }
      }

      this.scrollToBottom();
    }

    else if (eventType === "done") {
      this.scrollToBottom();
      if (window.sessionManager) {
        window.sessionManager.loadSessionsList();
      }
    }
  }

  scrollToBottom() {
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  }

  escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }
}

window.agentController = new AgentController();
