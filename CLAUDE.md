# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an autonomous coding agent system with a React-based UI. It uses the Claude Agent SDK to build complete applications over multiple sessions using a two-agent pattern:

1. **Initializer Agent** - First session reads an app spec and creates features in a SQLite database
2. **Coding Agent** - Subsequent sessions implement features one by one, marking them as passing

## Commands

### Quick Start (Recommended)

```bash
# Windows - launches CLI menu
start.bat

# macOS/Linux
./start.sh

# Launch Web UI (serves pre-built React app)
start_ui.bat      # Windows
./start_ui.sh     # macOS/Linux
```

### Python Backend (Manual)

```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run the main CLI launcher
python start.py

# Run agent directly for a project (use absolute path or registered name)
python autonomous_agent_demo.py --project-dir C:/Projects/my-app
python autonomous_agent_demo.py --project-dir my-app  # if registered

# YOLO mode: rapid prototyping without browser testing
python autonomous_agent_demo.py --project-dir my-app --yolo

# Parallel mode: run multiple agents simultaneously (2-10 agents)
python autonomous_agent_demo.py --project-dir my-app --num-agents 3
python autonomous_agent_demo.py --project-dir my-app --num-agents 5 --yolo
```

### YOLO Mode (Rapid Prototyping)

YOLO mode skips all testing for faster feature iteration:

```bash
# CLI
python autonomous_agent_demo.py --project-dir my-app --yolo

# UI: Toggle the lightning bolt button before starting the agent
```

**What's different in YOLO mode:**
- No regression testing (blocks `feature_get_for_regression` tool)
- No Playwright MCP server (browser automation disabled)
- Features marked passing after lint/type-check succeeds
- Faster iteration for prototyping

**Implementation details:**
- `client.py` removes `feature_get_for_regression` from allowed tools
- `YOLO_MODE=true` environment variable passed to feature MCP server
- MCP server returns error if regression tool is called (defense-in-depth)
- YOLO mode prompt does not instruct agent to run regression tests

**What's the same:**
- Lint and type-check still run to verify code compiles
- Feature MCP server for tracking progress
- All other development tools available

**When to use:** Early prototyping when you want to quickly scaffold features without verification overhead. Switch back to standard mode for production-quality development.

### Parallel Mode (Multiple Agents)

Parallel mode allows running multiple autonomous agents simultaneously to accelerate development:

```bash
# Run 3 agents in parallel
python autonomous_agent_demo.py --project-dir my-app --num-agents 3

# Parallel + YOLO mode for maximum speed
python autonomous_agent_demo.py --project-dir my-app --num-agents 5 --yolo
```

**How it works:**
- Each agent runs in its own git worktree (isolated filesystem)
- All agents share the same `features.db` (coordinated task queue)
- Features are atomically claimed using database-level locking
- Each agent has a unique `AGENT_ID` environment variable
- Agents coordinate through the `assigned_agent_id` database field

**Architecture:**
- `parallel_agents.py` - `ParallelAgentOrchestrator` manages multiple agent processes
- `worktree.py` - `WorktreeManager` handles git worktree creation and cleanup
- `parallel_agent_runner.py` - Entry point for individual parallel agents
- `.worktrees/agent_*/` - Isolated working directories for each agent (git-ignored)

**Feature coordination:**
- `feature_get_next` auto-claims features for the calling agent
- `feature_claim_next` provides atomic claiming with database locks
- `feature_release` releases features back to the queue
- `feature_mark_passing` clears agent assignment on completion

**Implementation details:**
- SQLAlchemy's `.with_for_update()` prevents race conditions
- Shared `features.db` via symlink or `PROJECT_DIR` environment variable
- Each agent's `AGENT_ID` is auto-detected from environment
- Worktrees are merged back to main branch on completion

**When to use:** Accelerate development on large feature sets where work can be parallelized (2-10 agents recommended).

### React UI (in ui/ directory)

```bash
cd ui
npm install
npm run dev      # Development server (hot reload)
npm run build    # Production build (required for start_ui.bat)
npm run lint     # Run ESLint
```

**Note:** The `start_ui.bat` script serves the pre-built UI from `ui/dist/`. After making UI changes, run `npm run build` in the `ui/` directory.

## Architecture

### Core Python Modules

- `start.py` - CLI launcher with project creation/selection menu
- `autonomous_agent_demo.py` - Entry point for running the agent
- `agent.py` - Agent session loop using Claude Agent SDK
- `client.py` - ClaudeSDKClient configuration with security hooks and MCP servers
- `security.py` - Bash command allowlist validation (ALLOWED_COMMANDS whitelist)
- `prompts.py` - Prompt template loading with project-specific fallback
- `progress.py` - Progress tracking, database queries, webhook notifications
- `registry.py` - Project registry for mapping names to paths (cross-platform)
- `parallel_agents.py` - ParallelAgentOrchestrator for managing multiple agent processes
- `worktree.py` - WorktreeManager for git worktree creation and cleanup
- `parallel_agent_runner.py` - Entry point for individual parallel agents

### Project Registry

Projects can be stored in any directory. The registry maps project names to paths using SQLite:
- **All platforms**: `~/.autocoder/registry.db`

The registry uses:
- SQLite database with SQLAlchemy ORM
- POSIX path format (forward slashes) for cross-platform compatibility
- SQLite's built-in transaction handling for concurrency safety

### Server API (server/)

The FastAPI server provides REST endpoints for the UI:

- `server/routers/projects.py` - Project CRUD with registry integration
- `server/routers/features.py` - Feature management
- `server/routers/agent.py` - Agent control (start/stop/pause/resume)
- `server/routers/filesystem.py` - Filesystem browser API with security controls
- `server/routers/spec_creation.py` - WebSocket for interactive spec creation

### Feature Management

Features are stored in SQLite (`features.db`) via SQLAlchemy. The agent interacts with features through an MCP server:

- `mcp_server/feature_mcp.py` - MCP server exposing feature management tools
- `api/database.py` - SQLAlchemy models (Feature table with priority, type, category, name, description, steps, passes, in_progress, label, assigned_agent_id)

MCP tools available to the agent:
- `feature_get_stats` - Progress statistics
- `feature_get_next` - Get highest-priority pending feature (auto-claims in parallel mode)
- `feature_get_for_regression` - Random passing features for regression testing
- `feature_mark_passing` - Mark feature complete (clears agent assignment)
- `feature_skip` - Move feature to end of queue
- `feature_create_bulk` - Initialize all features (used by initializer)
- `feature_claim_next` - Atomically claim next feature (parallel mode)
- `feature_release` - Release feature back to queue (parallel mode)

### React UI (ui/)

- Tech stack: React 18, TypeScript, TanStack Query, Tailwind CSS v4, Radix UI
- `src/App.tsx` - Main app with project selection, kanban board, agent controls
- `src/hooks/useWebSocket.ts` - Real-time updates via WebSocket
- `src/hooks/useProjects.ts` - React Query hooks for API calls
- `src/lib/api.ts` - REST API client
- `src/lib/types.ts` - TypeScript type definitions
- `src/components/FolderBrowser.tsx` - Server-side filesystem browser for project folder selection
- `src/components/NewProjectModal.tsx` - Multi-step project creation wizard

### Project Structure for Generated Apps

Projects can be stored in any directory (registered in `~/.autocoder/registry.db`). Each project contains:
- `prompts/app_spec.txt` - Application specification (XML format)
- `prompts/initializer_prompt.md` - First session prompt
- `prompts/coding_prompt.md` - Continuation session prompt
- `features.db` - SQLite database with feature test cases
- `.agent.lock` - Lock file to prevent multiple agent instances

### Security Model

Defense-in-depth approach configured in `client.py`:
1. OS-level sandbox for bash commands
2. Filesystem restricted to project directory only
3. Bash commands validated against `ALLOWED_COMMANDS` in `security.py`

## Claude Code Integration

- `.claude/commands/create-spec.md` - `/create-spec` slash command for interactive spec creation
- `.claude/skills/frontend-design/SKILL.md` - Skill for distinctive UI design
- `.claude/templates/` - Prompt templates copied to new projects

## Key Patterns

### Prompt Loading Fallback Chain

1. Project-specific: `{project_dir}/prompts/{name}.md`
2. Base template: `.claude/templates/{name}.template.md`

### Agent Session Flow

1. Check if `features.db` has features (determines initializer vs coding agent)
2. Create ClaudeSDKClient with security settings
3. Send prompt and stream response
4. Auto-continue with 3-second delay between sessions

### Real-time UI Updates

The UI receives updates via WebSocket (`/ws/projects/{project_name}`):
- `progress` - Test pass counts
- `agent_status` - Running/paused/stopped/crashed
- `log` - Agent output lines (streamed from subprocess stdout)
- `feature_update` - Feature status changes

### Design System

The UI uses a **neobrutalism** design with Tailwind CSS v4:
- CSS variables defined in `ui/src/styles/globals.css` via `@theme` directive
- Custom animations: `animate-slide-in`, `animate-pulse-neo`, `animate-shimmer`
- Color tokens: `--color-neo-pending` (yellow), `--color-neo-progress` (cyan), `--color-neo-done` (green)
