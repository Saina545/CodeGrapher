#!/usr/bin/env bash
# CodeGrapher — Startup Script
set -e
cd "$(dirname "$0")"

echo "═══════════════════════════════════════════════"
echo "  CodeGrapher — AST Visual Explorer"
echo "  Powered by Ollama (local LLM)"
echo "═══════════════════════════════════════════════"

if ! command -v python3 &>/dev/null; then echo "ERROR: Python 3 required."; exit 1; fi

echo "→ Installing/Verifying dependencies..."
pip install -r backend/requirements.txt --quiet 2>/dev/null || true

echo ""
echo "  Ollama Settings:"
echo "  ─────────────────────────────────────────────"
echo "  Base URL : ${OLLAMA_BASE_URL:-http://localhost:11434}"
echo "  Model    : ${OLLAMA_MODEL:-llama3.2:1b}"
echo ""
echo "  Make sure Ollama is running:  ollama serve"
echo "  Pull model if needed:         ollama pull llama3.2:1b"
echo "═══════════════════════════════════════════════"
echo ""
echo "→ Starting on http://127.0.0.1:5000"
echo ""

python3 backend/app.py