/**
 * Visual Diff Viewer for SATTVA AI AGENT.
 */

class DiffViewer {
  constructor() {
    this.diffContainer = document.getElementById("diff-viewer-content");
    this.fileTag = document.getElementById("diff-filename-tag");
    this.currentDiffText = "";

    const copyBtn = document.getElementById("btn-copy-diff");
    if (copyBtn) {
      copyBtn.addEventListener("click", () => this.copyDiff());
    }
  }

  showDiff(diffText, filename = "") {
    this.currentDiffText = diffText || "";
    if (!diffText || !diffText.trim()) {
      this.diffContainer.innerHTML = '<div class="empty-state">No diff generated for this operation.</div>';
      return;
    }

    if (filename) {
      this.fileTag.textContent = filename;
    }

    const lines = diffText.split("\n");
    let html = "";

    lines.forEach((line) => {
      let cls = "diff-line";
      if (line.startsWith("---") || line.startsWith("+++") || line.startsWith("@@")) {
        cls += " hdr";
      } else if (line.startsWith("+")) {
        cls += " add";
      } else if (line.startsWith("-")) {
        cls += " del";
      }
      
      const safeText = line
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
      html += `<div class="${cls}">${safeText || " "}</div>`;
    });

    this.diffContainer.innerHTML = html;
  }

  async copyDiff() {
    if (!this.currentDiffText) return;
    const ok = await (window.copyToClipboard ? window.copyToClipboard(this.currentDiffText) : navigator.clipboard.writeText(this.currentDiffText));
    const btn = document.getElementById("btn-copy-diff");
    if (btn) {
      const origHtml = btn.innerHTML;
      btn.textContent = "Copied! ✔";
      setTimeout(() => { btn.innerHTML = origHtml; }, 1500);
    }
  }
}

window.diffViewer = new DiffViewer();
