#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="${SCRIPT_DIR}/.venv"
PYTHON="${VENV_DIR}/bin/python"

PORT="${PORT:-8000}"
INSTALL_DEPS=0

ensure_venv() {
  if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment at .venv ..."
    python3 -m venv "$VENV_DIR"
  fi
}

install_deps() {
  echo "Installing dependencies..."
  "$PYTHON" -m pip install -r requirements.txt
}

print_help() {
  echo "Usage: ./run_dev.sh [--install] [--port <port>]"
  echo ""
  echo "Starts Story QA backend + dashboard with auto port fallback."
  echo ""
  echo "Options:"
  echo "  --install       Install/update Python dependencies first"
  echo "  --port <port>   Preferred port (default: 8000)"
  echo "  -h, --help      Show this help"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install)
      INSTALL_DEPS=1
      shift
      ;;
    --port)
      PORT="${2:-}"
      if [[ -z "$PORT" ]]; then
        echo "Missing value for --port"
        exit 1
      fi
      shift 2
      ;;
    -h|--help)
      print_help
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      print_help
      exit 1
      ;;
  esac
done

ensure_venv

if [[ "$INSTALL_DEPS" -eq 1 ]] || ! "$PYTHON" -c "import uvicorn" &>/dev/null; then
  install_deps
fi

find_free_port() {
  local start_port="$1"
  local probe_port="$start_port"
  while lsof -nP -iTCP:"$probe_port" -sTCP:LISTEN >/dev/null 2>&1; do
    probe_port=$((probe_port + 1))
  done
  echo "$probe_port"
}

FREE_PORT="$(find_free_port "$PORT")"
if [[ "$FREE_PORT" != "$PORT" ]]; then
  echo "Port $PORT is busy, using $FREE_PORT instead."
fi

echo "Starting Story QA on http://127.0.0.1:$FREE_PORT/dashboard"
"$PYTHON" -m uvicorn app.main:app --reload --port "$FREE_PORT"

