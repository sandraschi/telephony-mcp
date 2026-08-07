set windows-shell := ["powershell.exe", "-NoProfile", "-Command"]
import 'scripts/just/fleet.just'

# SOTA Fleet-Standard Justfile

set shell := ["powershell", "-c"]

# Open the interactive recipe dashboard in the browser
default:
    @just --list

# --- Operations --- ---

# Start the server (Canonical)
run:
    uv run -m telephony_mcp

# START REPOSITORY: Standard Headless-Aware Startup
start:
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./start.ps1

# --- Quality Gates --- ---

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

# --- Maintenance --- ---

# CLEAN: Purge artifacts and caches
clean:
    @Remove-Item -Recurse -Force .venv, .pytest_cache, .ruff_cache -ErrorAction SilentlyContinue
    @Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force

# Bootstrap: install dev deps + pre-commit hook
bootstrap:
    uv sync --group dev
    uv run pre-commit install
    Write-Host "Pre-commit hooks installed." -ForegroundColor Green