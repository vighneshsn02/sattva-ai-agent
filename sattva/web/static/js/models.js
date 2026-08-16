/**
 * Ollama Models Manager and Switcher for SATTVA AI AGENT.
 */

class ModelManager {
  constructor() {
    this.selectEl = document.getElementById("model-select");
    this.statusDot = document.getElementById("ollama-status-dot");
    this.activeModel = "";

    this.initEvents();
  }

  initEvents() {
    this.selectEl.addEventListener("change", (e) => this.switchModel(e.target.value));
    document.getElementById("btn-refresh-models").addEventListener("click", () => this.fetchModels());
    
    // Pull Model Modal
    const pullModal = document.getElementById("modal-pull");
    document.getElementById("btn-pull-modal").addEventListener("click", () => {
      pullModal.classList.remove("hidden");
    });
    document.getElementById("btn-close-pull-modal").addEventListener("click", () => {
      pullModal.classList.add("hidden");
    });
    document.getElementById("btn-cancel-pull").addEventListener("click", () => {
      pullModal.classList.add("hidden");
    });
    document.getElementById("btn-confirm-pull").addEventListener("click", () => this.startPullModel());
  }

  async checkStatus() {
    try {
      const res = await fetch("/api/status");
      const data = await res.json();
      if (data.ollama && data.ollama.online) {
        this.statusDot.className = "status-dot";
        this.statusDot.title = `Ollama Online (v${data.ollama.version}, ${data.ollama.latency_ms}ms)`;
      } else {
        this.statusDot.className = "status-dot offline";
        this.statusDot.title = `Ollama Offline: ${data.ollama?.error || "Cannot connect"}`;
      }
      this.activeModel = data.active_model;
      document.getElementById("current-workspace-label").textContent = data.workspace_path || "Workspace";
    } catch (err) {
      this.statusDot.className = "status-dot offline";
    }
  }

  async fetchModels() {
    await this.checkStatus();
    try {
      const res = await fetch("/api/models");
      const data = await res.json();
      const models = data.models || [];
      this.activeModel = data.active || this.activeModel;

      this.selectEl.innerHTML = "";
      if (models.length === 0) {
        this.selectEl.innerHTML = '<option value="">No local models found</option>';
        return;
      }

      models.forEach((m) => {
        const opt = document.createElement("option");
        opt.value = m.name;
        opt.textContent = `${m.name} (${m.size})`;
        if (m.name === this.activeModel) {
          opt.selected = true;
        }
        this.selectEl.appendChild(opt);
      });
    } catch (err) {
      console.error("Error fetching models:", err);
    }
  }

  async switchModel(newModel) {
    if (!newModel) return;
    try {
      const res = await fetch("/api/models/switch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model: newModel }),
      });
      const data = await res.json();
      if (data.success) {
        this.activeModel = newModel;
        console.log(`Active model switched to ${newModel}`);
      }
    } catch (err) {
      alert(`Failed to switch model: ${err.message}`);
    }
  }

  async startPullModel() {
    const input = document.getElementById("pull-model-input");
    const modelName = input.value.trim();
    if (!modelName) return;

    const progressContainer = document.getElementById("pull-progress-container");
    const statusText = document.getElementById("pull-status-text");
    const progressFill = document.getElementById("pull-progress-fill");
    const confirmBtn = document.getElementById("btn-confirm-pull");

    progressContainer.classList.remove("hidden");
    confirmBtn.disabled = true;
    statusText.textContent = `Connecting to Ollama library for ${modelName}...`;

    if (window.agentController && window.agentController.ws) {
      window.agentController.ws.send(JSON.stringify({
        action: "pull_model",
        model_name: modelName,
      }));
    }
  }

  handlePullProgress(progress) {
    const statusText = document.getElementById("pull-status-text");
    const progressFill = document.getElementById("pull-progress-fill");
    const confirmBtn = document.getElementById("btn-confirm-pull");

    if (progress.status) {
      statusText.textContent = progress.status;
    }

    if (progress.total && progress.completed) {
      const pct = Math.round((progress.completed / progress.total) * 100);
      progressFill.style.width = `${pct}%`;
      statusText.textContent = `${progress.status} (${pct}%)`;
    }

    if (progress.status === "success") {
      statusText.textContent = "✔ Model pulled successfully!";
      confirmBtn.disabled = false;
      this.fetchModels();
      setTimeout(() => {
        document.getElementById("modal-pull").classList.add("hidden");
        document.getElementById("pull-progress-container").classList.add("hidden");
      }, 1500);
    }
  }
}

window.modelManager = new ModelManager();
