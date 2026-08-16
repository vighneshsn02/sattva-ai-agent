# ⚡ SATTVA AI AGENT

**SATTVA AI AGENT** is an autonomous, privacy-first **Local AI Coding Assistant** powered by [Ollama](https://ollama.com). It runs 100% locally on your machine with zero data leaves your system, featuring both a modern **Web Interface** and an interactive **Rich CLI**.

---

## 🌟 Key Features

- 🧠 **100% Local AI (Ollama Powered)**: Connects seamlessly to your local Ollama instance (`http://localhost:11434`). Supports all local coding models including `qwen2.5-coder`, `deepseek-coder`, `llama3.2`, `falcon3`, `gemma3`, `codellama`, etc.
- 🔄 **Dynamic Model Switching & Pulling**: Switch active AI models on the fly in both Web UI and CLI. Pull and download new models directly from the Ollama library with streaming progress.
- 🤖 **Autonomous Multi-Step ReAct Agent**: Performs autonomous multi-turn loops: inspects repositories -> creates directories & files -> edits code with exact matching -> runs tests & terminal commands -> observes results -> auto-fixes errors.
- 📁 **File & Workspace Management**:
  - `create_file`: Create and write code files with automatic parent directory generation.
  - `create_folder`: Create nested folder hierarchies.
  - `read_file`: Inspect entire files or specific line ranges.
  - `delete_file_or_folder`: Safely remove obsolete assets.
  - `list_directory`: Recursive workspace directory tree listing.
- ✍️ **Precision Code Editing & Visual Diffs**:
  - `edit_file`: Exact-match chunk replacements with whitespace normalization.
  - `insert_code`: Relative line/anchor code insertion.
  - Generates unified diffs (`+` additions in green, `-` removals in red) rendered visually in Web UI and CLI.
- 🔍 **Deep Codebase Intelligence**:
  - `scan_codebase`: AST symbol extraction (classes, methods, functions, imports) for Python and JavaScript/TypeScript, LOC metrics, file type breakdown, and tech stack detection.
  - `search_code`: Fast grep/regex searching across the codebase.
  - `find_files`: Glob pattern file matching (`*.py`, `src/**/*.ts`, etc.).
- 💻 **Terminal & Test Execution**:
  - `run_command`: Run shell commands (PowerShell / Bash) with stdout/stderr capture and timeout protection.
  - `run_tests`: Auto-detects and runs test runners (`pytest`, `npm test`, `cargo test`, `go test`).
- 🌐 **Web Interface**:
  - Clean, dark-mode 3-panel IDE layout.
  - Real-time WebSocket streaming of agent thoughts and interactive tool execution cards.
  - Built-in file explorer, live code viewer, visual diff inspector, interactive terminal logs, and codebase grep search.
- 📟 **Interactive CLI**:
  - Built with Python `rich` with syntax highlighting, live spinners, diff previews, and slash commands.

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com/) installed and running (`ollama serve` or Ollama desktop application)
- Any local model pulled, for example:
  ```bash
  ollama pull qwen2.5-coder:7b
  # or
  ollama pull llama3.2:3b
  ```

### 2. Installation
```bash
# Clone or navigate to repository
cd D:/sattva-ai

# Install dependencies
pip install -r requirements.txt
```

### 3. Launching

#### Option A: Windows Launcher Batch
Double-click `sattva.bat` or run:
```cmd
.\sattva.bat
```

#### Option B: Web UI
```bash
python sattva.py web
# or
python sattva_web.py
```
Open your browser at `http://localhost:8000`.

#### Option C: Interactive CLI
```bash
python sattva.py cli
# or
python sattva_cli.py
```

---

## ⌨️ CLI Slash Commands

| Command | Description |
|---|---|
| `/model [name]` | Switch active Ollama model or select interactively |
| `/models` | List all locally installed Ollama models with sizes and quantization |
| `/pull <name>` | Download and pull a new model from Ollama library |
| `/scan` | Run codebase AST intelligence scan and print statistics |
| `/tree` or `/files` | Display workspace directory tree |
| `/read <file>` | View a file with syntax highlighting |
| `/run <cmd>` | Execute a terminal command directly |
| `/mode [agent\|ask]` | Switch between Autonomous Agent mode and Ask/Chat mode |
| `/web` | Launch the Web UI server in your default browser |
| `/clear` or `/reset` | Reset current session history |
| `/help` | Show command cheat sheet |
| `/exit` | Quit CLI |

---

## 🏗️ Architecture

```
sattva-ai/
├── sattva/
│   ├── config.py              # Configuration manager & workspace options
│   ├── ollama_client.py       # Async & Sync Ollama REST & tool-calling client
│   ├── tools/
│   │   ├── base.py            # BaseTool class and ToolRegistry
│   │   ├── file_ops.py        # create_file, create_folder, read_file, delete, list_dir
│   │   ├── code_edit.py       # edit_file with unified diff generator, insert_code
│   │   ├── scanner.py         # scan_codebase (AST parser, LOC stats, symbols)
│   │   ├── search.py          # search_code (grep/regex), find_files (glob)
│   │   └── terminal.py        # run_command, run_tests
│   ├── agent/
│   │   ├── engine.py          # Autonomous ReAct agent multi-turn execution loop
│   │   ├── prompts.py         # Dynamic system prompt & workspace context injector
│   │   └── session.py         # Session persistence and history manager
│   ├── cli/
│   │   └── app.py             # Rich interactive CLI REPL
│   └── web/
│       ├── server.py          # FastAPI REST & WebSocket Agent backend
│       └── static/            # Frontend SPA (HTML5, Vanilla CSS Design System, JS)
├── sattva.py                  # Main CLI/Web dispatcher
├── sattva_cli.py              # Direct CLI runner
├── sattva_web.py              # Direct Web runner
├── sattva.bat                 # Windows Launcher
├── requirements.txt           # Dependencies
└── README.md                  # Documentation
```

---
/ vighnesh naik
## 🔒 Privacy & Local Execution

SATTVA AI AGENT does **not** send any code, prompts, or workspace information to external cloud servers. All inference is processed locally through your Ollama instance.
