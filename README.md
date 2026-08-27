# ⚡ SATTVA AI AGENT

**SATTVA AI AGENT** is an autonomous, privacy-first **Local AI Coding Assistant & Multi-Agent Team** powered by [Ollama](https://ollama.com). It runs 100% locally on your machine with zero data leaving your system, featuring a specialized **Multi-Agent Orchestrator**, modern **Web Interface**, and an interactive **Rich CLI** globally executable from any directory.

---

## 🌟 Key Features

- 👥 **Multi-Agent Team Mode**:
  - ⚡ **Orchestrator**: Master coordinator managing execution DAG, parallel task dispatch, verification loop, and final executive synthesis.
  - 🧭 **Planner**: System Architect that deconstructs goals into modular, dependency-aware task graphs.
  - 💻 **Coder**: Senior Engineer executing surgical code edits in isolated sandboxes.
  - 🧪 **Tester**: QA & Test Automation Specialist creating test suites and validating functional correctness.
  - 🧐 **Reviewer**: Code Quality & Maintainability Specialist scoring architecture, style, and anti-patterns.
  - 🛡️ **Security**: AppSec Specialist auditing for secret leaks, OWASP Top 10 vulnerabilities, and insecure dependencies.
- ⚡ **Parallel Task Execution**: Concurrently runs independent subtasks across worker agents.
- 🧠 **Shared Context & Memory**: Central blackboard tracking task DAGs, symbol knowledge, artifacts, security findings, and test results.
- 📦 **Isolated Workspace Sandboxes**: Staged copy-on-write overlay preventing dirty state conflicts before verification approval.
- 🔄 **Automated Verification & Self-Healing Loop**: Multi-dimensional verification (Tests + Security + Review) with automated remediation cycles.
- 🌍 **Global System-Wide CLI (`sattva`)**: Install once and execute `sattva` or `sattva <prompt>` from any directory on Windows, Linux, and macOS.
- 🧠 **100% Local AI (Ollama Powered)**: Seamless offline inference with `qwen2.5-coder`, `deepseek-coder`, `llama3.2`, `falcon3`, `codellama`, etc.
- 🌐 **Modern Web Interface**: 3-panel dark-mode IDE layout with real-time multi-agent pipeline visualizer and WebSocket streaming.

---

## 🚀 Quick Installation & Setup

### 1. Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com/) running locally (`ollama serve` or Ollama desktop app)
- Pull your favorite coding model:
  ```bash
  ollama pull qwen2.5-coder:7b
  # or
  ollama pull llama3.2:3b
  ```

### 2. Install SATTVA Globally
Clone or download this repository, then run the 1-click global installer:

```bash
# Windows
python install.py
# or double-click install.bat

# Linux / macOS
chmod +x install.sh
./install.sh
```

The installer automatically installs SATTVA in editable mode, creates system wrappers, and configures your system `PATH`.

---

## 💻 Global CLI Usage

Once installed, you can invoke `sattva` from **any directory** on your machine:

```bash
# Launch interactive REPL in current directory
sattva

# Execute prompt directly in current directory (Autonomous Single Agent)
sattva "Create a python CLI tool to convert markdown to PDF"

# Execute with Multi-Agent Team (Planner -> Coder -> Tester -> Reviewer -> Security -> Orchestrator)
sattva multi "Build a FastAPI REST API with JWT authentication, SQLite, and pytest suite"

# Initialize workspace configuration (.sattva/config.json & rules.md)
sattva init

# Launch Web UI in your default browser
sattva web

# Scan codebase AST & tech stack
sattva scan

# List installed Ollama models
sattva models

# Pull a new model directly
sattva pull qwen2.5-coder:7b

# Check version
sattva --version

# View all options
sattva --help
```

---

## 🌐 Web Interface

Launch the Web UI by running:
```bash
sattva web
```
Open your browser at `http://localhost:8000`.

Toggle between:
- 🤖 **Single Agent**: Step-by-step autonomous ReAct agent loop.
- 👥 **Multi-Agent Team**: Full multi-agent orchestration with planning, sandboxing, security scanning, automated testing, code review, and synthesis.
- 💬 **Ask & Explain**: Fast conversational pair programming.

---

## ⌨️ CLI Slash Commands (Inside REPL)

| Command | Description |
|---|---|
| `/mode [agent\|multi\|ask]` | Switch between Single Agent, Multi-Agent Team, and Ask mode |
| `/model [name]` | Switch active Ollama model or select interactively |
| `/models` | List all locally installed Ollama models with sizes and quantization |
| `/pull <name>` | Download and pull a new model from Ollama library |
| `/init` | Initialize `.sattva` workspace config and rules in current folder |
| `/scan` | Run codebase AST intelligence scan and print statistics |
| `/tree` or `/files` | Display workspace directory tree |
| `/read <file>` | View a file with syntax highlighting |
| `/run <cmd>` | Execute a terminal command directly |
| `/web` | Launch the Web UI server in your default browser |
| `/clear` or `/reset` | Reset current session history |
| `/help` | Show command cheat sheet |
| `/exit` | Quit CLI |

---

## 🏗️ Architecture

```
sattva-ai/
├── sattva/
│   ├── main.py                # Master global CLI entry point
│   ├── config.py              # Configuration manager & workspace options
│   ├── ollama_client.py       # Async & Sync Ollama client with tool calling
│   ├── agent/
│   │   ├── engine.py          # Single-agent autonomous ReAct execution loop
│   │   ├── prompts.py         # Dynamic system prompts & workspace context
│   │   ├── session.py         # Session persistence and history manager
│   │   └── multi_agent/       # Multi-Agent Team Framework
│   │       ├── roles.py       # Specialized agent roles, metadata & prompts
│   │       ├── memory.py      # SharedContext blackboard & knowledge graph
│   │       ├── sandbox.py     # Isolated workspace sandboxes & staging
│   │       ├── agents.py      # Planner, Coder, Tester, Reviewer, Security
│   │       ├── verification.py# Automated verification & self-healing loop
│   │       └── orchestrator.py# Multi-agent master pipeline orchestrator
│   ├── tools/                 # File ops, code edit, scanner, search, terminal
│   ├── cli/
│   │   ├── app.py             # Rich interactive CLI REPL
│   │   └── installer.py       # Cross-platform global PATH installer
│   └── web/
│       ├── server.py          # FastAPI REST & WebSocket server
│       └── static/            # Frontend SPA with Multi-Agent Visualizer
├── install.py                 # 1-Click Global CLI installer
├── install.bat                # Windows installer script
├── install.sh                 # Linux / macOS installer script
├── pyproject.toml             # Package configuration & console scripts
└── README.md                  # Documentation
```

---

## 🔒 Privacy & Local Execution

SATTVA AI AGENT does **not** send any code, prompts, or workspace information to external cloud servers. All inference is processed locally through your local Ollama instance.
