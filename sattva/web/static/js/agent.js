function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

async function copyToClipboard(text) {
  if (!text) return false;
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (e) {
      console.warn("navigator.clipboard.writeText failed, falling back:", e);
    }
  }
  try {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.top = "0";
    textArea.style.left = "0";
    textArea.style.width = "2em";
    textArea.style.height = "2em";
    textArea.style.padding = "0";
    textArea.style.border = "none";
    textArea.style.outline = "none";
    textArea.style.boxShadow = "none";
    textArea.style.background = "transparent";
    textArea.style.opacity = "0";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    const successful = document.execCommand("copy");
    document.body.removeChild(textArea);
    return successful;
  } catch (err) {
    console.error("Fallback clipboard copy failed:", err);
    return false;
  }
}
window.copyToClipboard = copyToClipboard;

function formatCodeBlock(codeText, lang) {
  const rawLang = (lang || "").trim();
  const displayLang = rawLang ? rawLang.split(/\s+/)[0] : "code";
  const langClass = rawLang ? ` class="language-${escapeHtml(displayLang)}"` : "";
  const escapedCode = escapeHtml(codeText);

  return `<div class="code-block-wrapper"><div class="code-block-header"><span class="code-lang-label">${escapeHtml(displayLang)}</span><button type="button" class="code-copy-btn" title="Copy code to clipboard"><span class="copy-btn-icon">📋</span> <span class="copy-btn-text">Copy Code</span></button></div><pre><code${langClass}>${escapedCode}</code></pre></div>`;
}
window.formatCodeBlock = formatCodeBlock;

let markedConfigured = false;
function configureMarked() {
  if (markedConfigured || typeof marked === "undefined") return;
  try {
    const codeRenderer = function(arg1, arg2, arg3) {
      let codeText = "";
      let lang = "";
      if (arg1 && typeof arg1 === "object") {
        codeText = arg1.text !== undefined ? arg1.text : (arg1.raw || "");
        lang = arg1.lang || "";
      } else {
        codeText = typeof arg1 === "string" ? arg1 : "";
        lang = typeof arg2 === "string" ? arg2 : "";
      }
      return formatCodeBlock(codeText, lang);
    };

    if (typeof marked.use === "function") {
      marked.use({
        renderer: {
          code: codeRenderer
        }
      });
      markedConfigured = true;
    } else if (marked.Renderer) {
      const customRenderer = new marked.Renderer();
      customRenderer.code = codeRenderer;
      if (typeof marked.setOptions === "function") {
        marked.setOptions({ renderer: customRenderer });
        markedConfigured = true;
      }
    }
  } catch (err) {
    console.warn("Failed to configure marked code renderer:", err);
  }
}

// Configure marked immediately if already loaded
configureMarked();

function enhanceCodeBlocks(container) {
  if (!container) return;
  const preElements = container.querySelectorAll("pre");
  preElements.forEach((pre) => {
    if (pre.closest(".code-block-wrapper")) {
      return;
    }
    const code = pre.querySelector("code");
    let lang = "code";
    if (code) {
      const match = (code.className || "").match(/language-([\w-]+)/);
      if (match) lang = match[1];
    }
    const wrapper = document.createElement("div");
    wrapper.className = "code-block-wrapper";
    wrapper.innerHTML = `<div class="code-block-header"><span class="code-lang-label">${escapeHtml(lang)}</span><button type="button" class="code-copy-btn" title="Copy code to clipboard"><span class="copy-btn-icon">📋</span> <span class="copy-btn-text">Copy Code</span></button></div>`;
    pre.parentNode.insertBefore(wrapper, pre);
    wrapper.appendChild(pre);
  });
}
window.enhanceCodeBlocks = enhanceCodeBlocks;

function safeRenderMarkdown(text) {
  if (!text) return "";
  configureMarked();
  if (typeof marked !== "undefined") {
    try {
      if (typeof marked.parse === "function") {
        return marked.parse(text);
      } else if (typeof marked === "function") {
        return marked(text);
      }
    } catch (e) {
      console.warn("marked parse error:", e);
    }
  }

  const codeBlocks = [];
  let html = text.replace(/```([\w-]*)\n([\s\S]*?)```/g, (m, lang, code) => {
    const idx = codeBlocks.length;
    codeBlocks.push(formatCodeBlock(code, lang));
    return `__CODE_BLOCK_${idx}__`;
  });
  html = html.replace(/```([\w-]*)\n([\s\S]*)$/g, (m, lang, code) => {
    const idx = codeBlocks.length;
    codeBlocks.push(formatCodeBlock(code, lang));
    return `__CODE_BLOCK_${idx}__`;
  });

  html = html
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  html = html.replace(/`([^`]+)`/g, (m, inline) => `<code>${escapeHtml(inline)}</code>`);
  html = html.replace(/^### (.*$)/gim, "<h3>$1</h3>");
  html = html.replace(/^## (.*$)/gim, "<h2>$1</h2>");
  html = html.replace(/^# (.*$)/gim, "<h1>$1</h1>");
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  html = html.replace(/^\s*-\s+(.*$)/gim, "<li>$1</li>");
  html = html.replace(/\n\n/g, "<br/><br/>");

  html = html.replace(/__CODE_BLOCK_(\d+)__/g, (m, idx) => codeBlocks[parseInt(idx, 10)] || "");
  return html;
}
window.safeRenderMarkdown = safeRenderMarkdown;

// Global click delegation for all Copy Code buttons
document.addEventListener("click", async (e) => {
  const btn = e.target.closest(".code-copy-btn");
  if (btn) {
    e.preventDefault();
    e.stopPropagation();

    const wrapper = btn.closest(".code-block-wrapper");
    let codeText = "";

    if (wrapper) {
      const codeEl = wrapper.querySelector("pre code") || wrapper.querySelector("pre");
      if (codeEl) {
        codeText = codeEl.textContent || "";
      }
    }

    if (!codeText && btn.parentElement) {
      const pre = btn.parentElement.querySelector("pre") || btn.parentElement.nextElementSibling;
      if (pre) {
        codeText = pre.textContent || "";
      }
    }

    await copyToClipboard(codeText);

    if (btn._copyTimeout) {
      clearTimeout(btn._copyTimeout);
    }

    btn.classList.add("copied");
    btn.innerHTML = `<span class="copy-btn-icon">✓</span> <span class="copy-btn-text">Copied!</span>`;

    btn._copyTimeout = setTimeout(() => {
      btn.classList.remove("copied");
      btn.innerHTML = `<span class="copy-btn-icon">📋</span> <span class="copy-btn-text">Copy Code</span>`;
      btn._copyTimeout = null;
    }, 1500);
    return;
  }

  const msgBtn = e.target.closest(".msg-copy-btn");
  if (msgBtn) {
    e.preventDefault();
    e.stopPropagation();

    const row = msgBtn.closest(".assistant-row");
    let textToCopy = "";
    if (row) {
      const bubble = row.querySelector(".assistant-bubble");
      if (bubble) {
        textToCopy = bubble.innerText || bubble.textContent || "";
      }
    }

    await copyToClipboard(textToCopy);

    if (msgBtn._copyTimeout) {
      clearTimeout(msgBtn._copyTimeout);
    }

    msgBtn.classList.add("copied");
    msgBtn.innerHTML = `<span class="copy-btn-icon">✓</span> <span class="copy-btn-text">Copied!</span>`;

    msgBtn._copyTimeout = setTimeout(() => {
      msgBtn.classList.remove("copied");
      msgBtn.innerHTML = `<span class="copy-btn-icon">📋</span> <span class="copy-btn-text">Copy Response</span>`;
      msgBtn._copyTimeout = null;
    }, 1500);
  }
});

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
    const multiBtn = document.getElementById("btn-mode-multi");
    if (multiBtn) {
      multiBtn.addEventListener("click", () => this.setMode("multi"));
    }
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
    const btnAgent = document.getElementById("btn-mode-agent");
    const btnMulti = document.getElementById("btn-mode-multi");
    const btnAsk = document.getElementById("btn-mode-ask");

    if (btnAgent) btnAgent.classList.toggle("active", newMode === "agent");
    if (btnMulti) btnMulti.classList.toggle("active", newMode === "multi");
    if (btnAsk) btnAsk.classList.toggle("active", newMode === "ask");

    const modeLabels = {
      agent: "Autonomous Single Agent",
      multi: "Multi-Agent Team (Planner, Coder, Tester, Reviewer, Security)",
      ask: "Ask & Explain",
    };
    document.getElementById("status-mode-label").textContent = `Mode: ${modeLabels[newMode] || newMode}`;
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
        } else if (payload.type === "multi_event") {
          this.handleMultiAgentEvent(payload.event_type, payload.role, payload.role_meta, payload.data, payload.session_id);
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
      row.appendChild(header);
      row.appendChild(bubble);
      this.messagesContainer.appendChild(row);
      this.currentAssistantBubble = bubble;
    }

    else if (eventType === "thought_chunk") {
      const chunk = data.chunk || "";
      this.currentAssistantText += chunk;
      if (this.currentAssistantBubble) {
        this.currentAssistantBubble.innerHTML = safeRenderMarkdown(this.currentAssistantText);
        enhanceCodeBlocks(this.currentAssistantBubble);
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
      if (this.currentAssistantBubble) {
        enhanceCodeBlocks(this.currentAssistantBubble);
      }
      this.scrollToBottom();
      if (window.sessionManager) {
        window.sessionManager.loadSessionsList();
      }
    }
  }

  handleMultiAgentEvent(eventType, role, roleMeta, data, sessionId) {
    if (sessionId) {
      this.currentSessionId = sessionId;
    }

    const icon = roleMeta.icon || "🤖";
    const title = roleMeta.title || "Agent";
    const roleKey = role || "orchestrator";

    if (eventType === "pipeline_stage") {
      const stage = data.stage || "";
      const stTitle = data.title || stage;
      const banner = document.createElement("div");
      banner.className = "stage-pipeline-banner";
      banner.innerHTML = `
        <span class="stage-pipeline-icon">${icon}</span>
        <span class="stage-pipeline-title">${this.escapeHtml(stTitle)}</span>
        <span class="stage-pipeline-tag">${this.escapeHtml(stage)}</span>
      `;
      this.messagesContainer.appendChild(banner);
      this.scrollToBottom();
    }

    else if (eventType === "agent_start") {
      this.currentAssistantText = "";
      const row = document.createElement("div");
      row.className = "message-row assistant-row";
      
      const header = document.createElement("div");
      header.className = "message-header";
      header.innerHTML = `
        <div class="message-sender">
          <span class="role-badge ${roleKey}">${icon} ${this.escapeHtml(title.toUpperCase())}</span>
        </div>
        <div class="message-actions">
          <button type="button" class="msg-copy-btn" title="Copy response to clipboard">
            <span class="copy-btn-icon">📋</span> <span class="copy-btn-text">Copy</span>
          </button>
        </div>
      `;
      const bubble = document.createElement("div");
      bubble.className = "assistant-bubble";
      row.appendChild(header);
      row.appendChild(bubble);
      this.messagesContainer.appendChild(row);
      this.currentAssistantBubble = bubble;
      this.scrollToBottom();
    }

    else if (eventType === "agent_thought" || eventType === "synthesis_chunk") {
      const chunk = data.chunk || "";
      this.currentAssistantText += chunk;
      if (!this.currentAssistantBubble) {
        const row = document.createElement("div");
        row.className = "message-row assistant-row";
        const header = document.createElement("div");
        header.className = "message-header";
        header.innerHTML = `
          <div class="message-sender">
            <span class="role-badge ${roleKey}">${icon} ${this.escapeHtml(title.toUpperCase())}</span>
          </div>
        `;
        const bubble = document.createElement("div");
        bubble.className = "assistant-bubble";
        row.appendChild(header);
        row.appendChild(bubble);
        this.messagesContainer.appendChild(row);
        this.currentAssistantBubble = bubble;
      }
      this.currentAssistantBubble.innerHTML = safeRenderMarkdown(this.currentAssistantText);
      enhanceCodeBlocks(this.currentAssistantBubble);
      this.scrollToBottom();
    }

    else if (eventType === "agent_tool_start") {
      const toolName = data.tool;
      const args = data.arguments || {};
      const card = document.createElement("div");
      card.className = "tool-step-card";
      card.id = `tool-card-${Date.now()}`;
      
      card.innerHTML = `
        <div class="tool-step-header">
          <span class="tool-name-badge">
            <span class="role-badge ${roleKey}" style="margin-right:6px;">${icon} ${this.escapeHtml(title)}</span>
            ⚡ ${toolName}
          </span>
          <span class="tool-step-status running">● Running...</span>
        </div>
        <div class="tool-step-body" style="display:none;"></div>
      `;
      this.messagesContainer.appendChild(card);
      this.scrollToBottom();
      this.lastToolCard = card;
    }

    else if (eventType === "agent_tool_end") {
      const toolName = data.tool;
      const success = data.success;
      const message = data.message || "";

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
      }

      if (data.diff && window.diffViewer) {
        window.diffViewer.showDiff(data.diff, toolName);
      }
      this.scrollToBottom();
    }

    else if (eventType === "diff_ready") {
      if (data.diff && window.diffViewer) {
        window.diffViewer.showDiff(data.diff, data.file || "Staged Diff");
      }
      if (window.fileExplorer) {
        window.fileExplorer.refresh();
      }
    }

    else if (eventType === "agent_completed") {
      if (role === "planner" && data.tasks) {
        // Render task table
        const tableWrapper = document.createElement("div");
        tableWrapper.className = "multi-tasks-table-wrapper";
        let rows = "";
        data.tasks.forEach(t => {
          rows += `
            <tr>
              <td><code>${this.escapeHtml(t.id || "")}</code></td>
              <td><span class="role-badge ${t.role || 'coder'}">${t.role || 'coder'}</span></td>
              <td><strong>${this.escapeHtml(t.title || "")}</strong></td>
              <td>${this.escapeHtml((t.dependencies || []).join(", ") || "None")}</td>
            </tr>
          `;
        });
        tableWrapper.innerHTML = `
          <table class="multi-tasks-table">
            <thead>
              <tr><th>Task ID</th><th>Assigned Agent</th><th>Title</th><th>Dependencies</th></tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        `;
        this.messagesContainer.appendChild(tableWrapper);
      }
      else if (role === "security" && data.score !== undefined) {
        const grid = document.createElement("div");
        grid.className = "scorecard-grid";
        const valClass = data.score >= 85 ? "good" : (data.score >= 70 ? "warn" : "bad");
        grid.innerHTML = `
          <div class="scorecard-card">
            <div class="scorecard-header"><span>🛡️ SECURITY SCORE</span><span>${data.verdict || "SECURE"}</span></div>
            <div class="scorecard-val ${valClass}">${data.score}/100</div>
            <div style="font-size:11px; color:var(--text-muted);">${data.findings_count || 0} findings detected</div>
          </div>
        `;
        this.messagesContainer.appendChild(grid);
      }
      this.scrollToBottom();
    }

    else if (eventType === "done") {
      if (this.currentAssistantBubble) {
        enhanceCodeBlocks(this.currentAssistantBubble);
      }
      if (window.fileExplorer) {
        window.fileExplorer.refresh();
      }
      if (window.sessionManager) {
        window.sessionManager.loadSessionsList();
      }
      this.scrollToBottom();
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

