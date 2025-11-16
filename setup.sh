#!/usr/bin/env bash
set -euo pipefail

# setup.sh for Git Bash (Windows) / Linux / macOS
# Usage: bash setup.sh
# This will:
#  - check python
#  - create .venv
#  - activate venv
#  - upgrade pip/setuptools/wheel
#  - install requirements.txt (if exist)
#  - create .env.example
#  - create scripts/verify_env.py
#  - run verification

echo
echo "=== START: setup environment (Git Bash) ==="
echo

# 1) Check python available
if command -v python >/dev/null 2>&1; then
  PYTHON_CMD=python
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD=python3
else
  echo "ERROR: Python not found in PATH. Install Python 3.10/3.11 and re-run."
  exit 1
fi

echo "Using python: $($PYTHON_CMD --version 2>&1)"

# 2) Create virtualenv (.venv) if not exists
VENV_DIR=".venv"
if [ -d "$VENV_DIR" ]; then
  echo "Virtualenv $VENV_DIR already exists. Skipping creation."
else
  echo "Creating virtualenv at .venv ..."
  $PYTHON_CMD -m venv "$VENV_DIR"
fi

# 3) Activate venv (works in Git Bash)
# On Windows Git Bash, activation script is under .venv/Scripts/activate
if [ -f "$VENV_DIR/Scripts/activate" ]; then
  # Git Bash compatible activation
  # shellcheck disable=SC1091
  source "$VENV_DIR/Scripts/activate"
elif [ -f "$VENV_DIR/bin/activate" ]; then
  source "$VENV_DIR/bin/activate"
else
  echo "ERROR: Could not find venv activate script. Path checked: $VENV_DIR/Scripts/activate and $VENV_DIR/bin/activate"
  exit 1
fi

echo "Virtualenv activated. Python: $(which python)"

# 4) Upgrade pip / setuptools / wheel
echo "Upgrading pip, setuptools, wheel ..."
python -m pip install --upgrade pip setuptools wheel

# 5) Install requirements.txt if exists
REQ_FILE="requirements.txt"
if [ -f "$REQ_FILE" ]; then
  echo "Installing dependencies from $REQ_FILE ..."
  pip install -r "$REQ_FILE"
else
  echo "Warning: $REQ_FILE not found. Creating minimal requirements.txt ..."
  cat > "$REQ_FILE" <<'EOF'
pandas
numpy
ta
matplotlib
python-telegram-bot
sqlalchemy
python-dotenv
pytest
EOF
  pip install -r "$REQ_FILE"
fi

# 6) Ensure scripts dir exists
mkdir -p scripts

# 7) Create .env.example if not exists
ENV_EX=".env.example"
if [ -f "$ENV_EX" ]; then
  echo "$ENV_EX already exists. Skipping."
else
  echo "Creating .env.example ..."
  cat > "$ENV_EX" <<'EOF'
# Example environment variables - DO NOT COMMIT real secrets into repo
TELEGRAM_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
DATA_PROVIDER_KEY=your_data_provider_key_here
EOF
fi

# 8) Create scripts/verify_env.py (idempotent)
VERIFY_PY="scripts/verify_env.py"
if [ -f "$VERIFY_PY" ]; then
  echo "$VERIFY_PY already exists. Skipping creation."
else
  echo "Creating $VERIFY_PY ..."
  cat > "$VERIFY_PY" <<'PY'
# Simple environment verification script
import sys
print("Python:", sys.version.split()[0])
try:
    import pandas as pd, numpy as np
    print("pandas:", pd.__version__)
    print("numpy:", np.__version__)
except Exception as e:
    print("Error importing pandas/numpy:", e)

try:
    import ta
    print("ta library: OK")
except Exception as e:
    print("Error importing ta:", e)

try:
    import telegram
    print("python-telegram-bot: OK")
except Exception as e:
    print("Error importing python-telegram-bot:", e)
PY
fi

# 9) Run verification
echo
echo "Running verification script..."
python "$VERIFY_PY"

echo
echo "=== DONE: Environment setup complete ==="
echo "Tips:"
echo " - Your venv is at .venv. Activate it with: source .venv/Scripts/activate (Git Bash) or source .venv/bin/activate (Unix)."
echo " - Do NOT commit .env or .venv to git. .gitignore should include them."
echo " - If you want to pin package versions, run: pip freeze > requirements.txt"
echo

# keep venv active in the same shell only if script is sourced
# If you run with 'bash setup.sh' the calling shell won't keep venv activated.
# To activate afterwards, run:
echo "To activate venv in this shell: source .venv/Scripts/activate"
