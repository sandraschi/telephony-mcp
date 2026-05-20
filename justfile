set windows-shell := ["pwsh.exe", "-NoLogo", "-Command"]

# SOTA Fleet-Standard Justfile

set shell := ["powershell", "-c"]

# Open the interactive recipe dashboard in the browser
default:
    @pwsh.exe -NoProfile -ExecutionPolicy Bypass -File ../mcp-central-docs/scripts/just-dashboard.ps1 -Path .

# --- 🚀 Operations ---

# Start the server (Canonical)
run:
    uv run -m telephony_mcp

# START REPOSITORY: Standard Headless-Aware Startup
start:
    pwsh.exe -NoProfile -ExecutionPolicy Bypass -File ./start.ps1

# --- 🧪 Quality Gates ---

# LINT: Check for code quality issues
lint:
    uv run ruff check .

# FIX: Auto-repair linting issues
fix:
    uv run ruff check --fix .
    uv run ruff format .

# TEST: Run the test suite
test:
    uv run pytest

# --- 🧹 Maintenance ---

# CLEAN: Purge artifacts and caches
clean:
    @Remove-Item -Recurse -Force .venv, .pytest_cache, .ruff_cache -ErrorAction SilentlyContinue
    @Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
