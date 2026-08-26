/**
 * Main Application Coordinator and Panels for SATTVA AI AGENT.
 */

class AppCoordinator {
  constructor() {
    this.initTabs();
    this.initTerminal();
    this.initSearch();
    this.initWorkspaceModal();
    this.initSettingsModal();
    this.initSessions();

    // Auto-load files and models on startup
    window.fileExplorer.refresh();
    window.modelManager.fetchModels();
  }

  initTabs() {
    // Left Sidebar Tabs
    document.querySelectorAll(".sidebar-tabs:not(.right-tabs) .sidebar-tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        document.querySelectorAll(".sidebar-tabs:not(.right-tabs) .sidebar-tab").forEach(t => t.classList.remove("active"));
        document.querySelectorAll(".sidebar-left .tab-panel").forEach(p => p.classList.remove("active"));

        tab.classList.add("active");
        const panelId = `panel-${tab.dataset.tab}`;
        const panel = document.getElementById(panelId);
        if (panel) panel.classList.add("active");

        if (tab.dataset.tab === "sessions") {
          this.loadSessionsList();
        }
      });
    });

    // Right Sidebar Tabs
    document.querySelectorAll(".right-tabs .sidebar-tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        document.querySelectorAll(".right-tabs .sidebar-tab").forEach(t => t.classList.remove("active"));
        document.querySelectorAll(".sidebar-right .rtab-panel").forEach(p => p.classList.remove("active"));

        tab.classList.add("active");
        const panelId = `rpanel-${tab.dataset.rtab}`;
        const panel = document.getElementById(panelId);
        if (panel) panel.classList.add("active");
      });
    });
  }

  initTerminal() {
    const input = document.getElementById("terminal-cmd-input");
    const btn = document.getElementById("btn-run-terminal");
    const output = document.getElementById("terminal-output-logs");

    const runCmd = async () => {
      const cmd = input.value.trim();
      if (!cmd) return;

      input.value = "";
      this.appendTerminalLog(`$ ${cmd}`, "cmd");

      try {
        const res = await fetch("/api/terminal/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ command: cmd }),
        });
        const json = await res.json();
        if (json.data) {
          if (json.data.stdout) this.appendTerminalLog(json.data.stdout, "stdout");
          if (json.data.stderr) this.appendTerminalLog(json.data.stderr, "stderr");
        } else if (json.error) {
          this.appendTerminalLog(json.error, "stderr");
        }
      } catch (err) {
        this.appendTerminalLog(`Terminal Error: ${err.message}`, "stderr");
      }
    };

    btn.addEventListener("click", runCmd);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") runCmd();
    });
  }

  appendTerminalLog(text, type = "stdout") {
    const output = document.getElementById("terminal-output-logs");
    const line = document.createElement("div");
    line.className = `terminal-line ${type}`;
    line.textContent = text;
    output.appendChild(line);
    output.scrollTop = output.scrollHeight;
  }

  initSearch() {
    const input = document.getElementById("search-query-input");
    const btn = document.getElementById("btn-do-search");
    const regexCheck = document.getElementById("search-regex-check");
    const caseCheck = document.getElementById("search-case-check");
    const list = document.getElementById("search-results-list");

    const doSearch = async () => {
      const query = input.value.trim();
      if (!query) return;

      list.innerHTML = '<div class="tree-loading">Searching codebase...</div>';
      try {
        const res = await fetch("/api/workspace/search", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query: query,
            is_regex: regexCheck.checked,
            case_sensitive: caseCheck.checked,
          }),
        });
        const json = await res.json();
        const matches = json.data?.matches || [];

        if (matches.length === 0) {
          list.innerHTML = `<div class="empty-state">No matches found for "${query}".</div>`;
          return;
        }

        list.innerHTML = "";
        matches.forEach((m) => {
          const item = document.createElement("div");
          item.className = "search-match-item";
          item.innerHTML = `
            <div class="search-match-file">${m.file}:${m.line_number}</div>
            <div class="search-match-content">${m.line_content}</div>
          `;
          item.addEventListener("click", () => {
            window.fileExplorer.loadFile(m.file);
          });
          list.appendChild(item);
        });
      } catch (err) {
        list.innerHTML = `<div class="empty-state">Search error: ${err.message}</div>`;
      }
    };

    btn.addEventListener("click", doSearch);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") doSearch();
    });
  }

  initWorkspaceModal() {
    const wsBadge = document.getElementById("workspace-badge");
    const modal = document.getElementById("modal-workspace");
    const closeBtn = document.getElementById("btn-close-ws-modal");
    const cancelBtn = document.getElementById("btn-cancel-ws");
    const confirmBtn = document.getElementById("btn-confirm-ws");
    const input = document.getElementById("ws-path-input");

    wsBadge.addEventListener("click", () => {
      input.value = document.getElementById("current-workspace-label").textContent;
      modal.classList.remove("hidden");
    });

    const closeModal = () => modal.classList.add("hidden");
    closeBtn.addEventListener("click", closeModal);
    cancelBtn.addEventListener("click", closeModal);

    confirmBtn.addEventListener("click", async () => {
      const p = input.value.trim();
      if (!p) return;
      try {
        const res = await fetch("/api/workspace/set_path", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ path: p }),
        });
        const json = await res.json();
        if (json.success) {
          document.getElementById("current-workspace-label").textContent = json.workspace_path;
          closeModal();
          window.fileExplorer.refresh();
        } else {
          alert(json.detail || "Failed to set workspace path.");
        }
      } catch (err) {
        alert(err.message);
      }
    });
  }

  initSettingsModal() {
    const modal = document.getElementById("modal-settings");
    const btn = document.getElementById("btn-settings-modal");
    const closeBtn = document.getElementById("btn-close-settings-modal");
    const saveBtn = document.getElementById("btn-save-settings");

    btn.addEventListener("click", () => modal.classList.remove("hidden"));
    closeBtn.addEventListener("click", () => modal.classList.add("hidden"));
    saveBtn.addEventListener("click", () => {
      modal.classList.add("hidden");
    });
  }

  initSessions() {
    document.getElementById("btn-new-chat").addEventListener("click", () => {
      window.agentController.currentSessionId = null;
      document.getElementById("chat-messages-container").innerHTML = `
        <div class="welcome-card" id="welcome-card">
          <div class="welcome-badge">⚡ LOCAL AI POWERED BY OLLAMA</div>
          <h1 class="welcome-title">SATTVA AI AGENT</h1>
          <p class="welcome-subtitle">
            Started a new clean session. SATTVA is ready to assist you.
          </p>
        </div>
      `;
    });
  }

  async loadSessionsList() {
    const container = document.getElementById("sessions-list-container");
    container.innerHTML = '<div class="tree-loading">Loading saved sessions...</div>';
    try {
      const res = await fetch("/api/sessions");
      const json = await res.json();
      const sessions = json.sessions || [];

      if (!sessions.length) {
        container.innerHTML = '<div class="empty-state">No saved chats yet.</div>';
        return;
      }

      container.innerHTML = "";
      sessions.forEach((s) => {
        const item = document.createElement("div");
        item.className = "session-item";
        if (window.agentController.currentSessionId === s.session_id) {
          item.classList.add("active");
        }
        item.innerHTML = `
          <div class="session-title">${s.title || "Untitled Session"}</div>
          <div class="session-meta">
            <span>${s.model || "Ollama"}</span>
            <span>${s.message_count || 0} msgs</span>
          </div>
        `;
        item.addEventListener("click", () => this.loadSession(s.session_id));
        container.appendChild(item);
      });
    } catch (err) {
      container.innerHTML = `<div class="empty-state">Error: ${err.message}</div>`;
    }
  }

  async loadSession(sessionId) {
    try {
      const res = await fetch(`/api/sessions/${sessionId}`);
      const json = await res.json();
      if (json.messages) {
        window.agentController.currentSessionId = sessionId;
        const container = document.getElementById("chat-messages-container");
        container.innerHTML = "";

        json.messages.forEach((msg) => {
          if (msg.role === "user") {
            window.agentController.appendUserMessage(msg.content);
          } else if (msg.role === "assistant") {
            const row = document.createElement("div");
            row.className = "message-row assistant-row";
            const header = document.createElement("div");
            header.className = "message-header";
            header.innerHTML = `
              <div class="message-sender">
                <span class="sender-icon">⚡</span>
                <span class="sender-name">SATTVA AI</span>
              </div>
              <div class="message-actions">
                <button type="button" class="msg-copy-btn" title="Copy response to clipboard">
                  <span class="copy-btn-icon">📋</span> <span class="copy-btn-text">Copy Response</span>
                </button>
              </div>
            `;
            const bubble = document.createElement("div");
            bubble.className = "assistant-bubble";
            bubble.innerHTML = window.safeRenderMarkdown ? window.safeRenderMarkdown(msg.content) : msg.content;
            row.appendChild(header);
            row.appendChild(bubble);
            container.appendChild(row);
            if (window.enhanceCodeBlocks) {
              window.enhanceCodeBlocks(bubble);
            }
          }
        });
        window.agentController.scrollToBottom();
      }
    } catch (err) {
      alert(`Failed to load session: ${err.message}`);
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  window.appCoordinator = new AppCoordinator();
  window.sessionManager = window.appCoordinator;
});
