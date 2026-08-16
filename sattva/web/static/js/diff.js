/**
 * Visual Diff Viewer for SATTVA AI AGENT.
 */

class DiffViewer {
  constructor() {
    this.diffContainer = document.getElementById("diff-viewer-content");
    this.fileTag = document.getElementById("diff-filename-tag");
  }

  showDiff(diffText, filename = "") {
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
}

window.diffViewer = new DiffViewer();
