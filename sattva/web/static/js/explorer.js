/**
 * File Explorer and Codebase Scanner for SATTVA AI AGENT.
 */

class FileExplorer {
  constructor() {
    this.treeContainer = document.getElementById("file-tree-root");
    this.filterInput = document.getElementById("file-filter-input");
    this.currentFile = null;
    this.entries = [];

    this.initEvents();
  }

  initEvents() {
    this.filterInput.addEventListener("input", (e) => this.filterTree(e.target.value));
    document.getElementById("btn-refresh-files").addEventListener("click", () => this.refresh());
    document.getElementById("btn-new-file").addEventListener("click", () => this.promptNewFile());
    document.getElementById("btn-new-folder").addEventListener("click", () => this.promptNewFolder());
    document.getElementById("btn-save-file").addEventListener("click", () => this.saveCurrentFile());
    document.getElementById("btn-copy-code").addEventListener("click", () => this.copyEditorCode());
    document.getElementById("btn-run-scan").addEventListener("click", () => this.runCodebaseScan());
  }

  async refresh() {
    this.treeContainer.innerHTML = '<div class="tree-loading">Refreshing files...</div>';
    try {
      const res = await fetch("/api/workspace/files");
      const json = await res.json();
      if (json.success && json.data) {
        this.entries = json.data.entries || [];
        this.renderTree(this.entries);
      } else {
        this.treeContainer.innerHTML = `<div class="empty-state">${json.error || "No files found."}</div>`;
      }
    } catch (err) {
      this.treeContainer.innerHTML = `<div class="empty-state">Error loading files: ${err.message}</div>`;
    }
  }

  renderTree(entries) {
    if (!entries.length) {
      this.treeContainer.innerHTML = '<div class="empty-state">Workspace is empty.</div>';
      return;
    }

    this.treeContainer.innerHTML = "";
    entries.forEach((item) => {
      const row = document.createElement("div");
      row.className = "tree-item";
      row.dataset.path = item.path;
      row.dataset.type = item.type;
      row.style.paddingLeft = `${(item.depth || 1) * 12}px`;

      const icon = item.type === "directory" ? "📁" : this.getFileIcon(item.name);
      row.innerHTML = `<span class="tree-icon">${icon}</span> <span class="tree-label">${item.name}</span>`;

      row.addEventListener("click", () => {
        if (item.type === "file") {
          this.loadFile(item.path);
        }
      });

      this.treeContainer.appendChild(row);
    });
  }

  filterTree(query) {
    const q = query.toLowerCase().trim();
    const filtered = this.entries.filter(e => e.path.toLowerCase().includes(q));
    this.renderTree(filtered);
  }

  getFileIcon(filename) {
    if (filename.endsWith(".py")) return "🐍";
    if (filename.endsWith(".js") || filename.endsWith(".jsx")) return "🟨";
    if (filename.endsWith(".ts") || filename.endsWith(".tsx")) return "🔷";
    if (filename.endsWith(".html")) return "🌐";
    if (filename.endsWith(".css")) return "🎨";
    if (filename.endsWith(".json")) return "⚙️";
    if (filename.endsWith(".md")) return "📝";
    if (filename.endsWith(".sh") || filename.endsWith(".bat") || filename.endsWith(".ps1")) return "💻";
    return "📄";
  }

  async loadFile(filePath) {
    try {
      const res = await fetch(`/api/workspace/file?path=${encodeURIComponent(filePath)}`);
      const json = await res.json();
      if (json.success && json.data) {
        this.currentFile = filePath;
        document.getElementById("editor-filename").textContent = filePath;
        document.getElementById("code-editor-textarea").value = json.data.content || "";

        // Highlight active tree item
        document.querySelectorAll(".tree-item").forEach(el => {
          el.classList.toggle("active", el.dataset.path === filePath);
        });

        // Switch right tab to editor
        document.querySelector('[data-rtab="editor"]').click();
      }
    } catch (err) {
      alert(`Failed to load file: ${err.message}`);
    }
  }

  async saveCurrentFile() {
    if (!this.currentFile) {
      alert("No file currently selected.");
      return;
    }
    const content = document.getElementById("code-editor-textarea").value;
    try {
      const res = await fetch("/api/workspace/file", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: this.currentFile, content, overwrite: true }),
      });
      const json = await res.json();
      if (json.success) {
        const btn = document.getElementById("btn-save-file");
        btn.textContent = "Saved ✔";
        setTimeout(() => { btn.textContent = "Save"; }, 1500);
      } else {
        alert(`Error saving file: ${json.error}`);
      }
    } catch (err) {
      alert(`Save error: ${err.message}`);
    }
  }

  async promptNewFile() {
    const filename = prompt("Enter new file path (relative to workspace):");
    if (!filename) return;
    try {
      const res = await fetch("/api/workspace/file", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: filename, content: "", overwrite: false }),
      });
      const json = await res.json();
      if (json.success) {
        await this.refresh();
        this.loadFile(filename);
      } else {
        alert(json.error);
      }
    } catch (err) {
      alert(err.message);
    }
  }

  async promptNewFolder() {
    const foldername = prompt("Enter new folder path (relative to workspace):");
    if (!foldername) return;
    try {
      const res = await fetch("/api/workspace/folder", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: foldername }),
      });
      const json = await res.json();
      if (json.success) {
        await this.refresh();
      } else {
        alert(json.error);
      }
    } catch (err) {
      alert(err.message);
    }
  }

  copyEditorCode() {
    const val = document.getElementById("code-editor-textarea").value;
    navigator.clipboard.writeText(val);
    const btn = document.getElementById("btn-copy-code");
    btn.textContent = "Copied!";
    setTimeout(() => { btn.textContent = "Copy"; }, 1500);
  }

  async runCodebaseScan() {
    const container = document.getElementById("scan-results-container");
    container.innerHTML = '<div class="tree-loading">Scanning symbols & architecture...</div>';
    try {
      const res = await fetch("/api/workspace/scan");
      const json = await res.json();
      if (json.success && json.data) {
        const d = json.data;
        let html = `
          <div style="padding: 10px; font-size: 12px; display: flex; flex-direction: column; gap: 10px;">
            <div style="background: var(--bg-card); padding: 10px; border-radius: 6px;">
              <div><strong>Files:</strong> ${d.total_files} | <strong>LOC:</strong> ${d.total_lines}</div>
              <div><strong>Stack:</strong> ${(d.frameworks || []).join(", ") || "Standard"}</div>
            </div>
            <div><strong>Key Symbols:</strong></div>
        `;

        const syms = d.symbols || {};
        for (const [file, info] of Object.entries(syms)) {
          const classes = (info.classes || []).map(c => c.name).join(", ");
          const funcs = (info.functions || []).map(f => f.name).slice(0, 4).join(", ");
          html += `
            <div style="background: var(--bg-code); padding: 6px 8px; border-radius: 4px; border: 1px solid var(--border-subtle);">
              <div style="color: var(--accent-sky); font-weight:600;">${file}</div>
              ${classes ? `<div style="color: var(--text-muted); font-size: 11px;">Classes: ${classes}</div>` : ""}
              ${funcs ? `<div style="color: var(--text-muted); font-size: 11px;">Functions: ${funcs}</div>` : ""}
            </div>
          `;
        }
        html += "</div>";
        container.innerHTML = html;
      }
    } catch (err) {
      container.innerHTML = `<div class="empty-state">Scan failed: ${err.message}</div>`;
    }
  }
}

window.fileExplorer = new FileExplorer();
