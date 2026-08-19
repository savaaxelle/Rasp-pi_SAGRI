#!/usr/bin/env bash
#
# Run this ONCE on the Raspberry Pi itself (not on a dev machine) —
# a venv built elsewhere won't work here, since packages like numpy /
# tensorflow are compiled for a specific OS + CPU architecture.
#
# Usage:
#   cd /path/to/this/project
#   bash setup.sh

set -e

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "[SETUP] Creating virtual environment in ./venv ..."
    python3 -m venv venv
else
    echo "[SETUP] ./venv already exists, reusing it."
fi

echo "[SETUP] Upgrading pip..."
venv/bin/pip install --upgrade pip

echo "[SETUP] Installing dependencies from requirements.txt..."
venv/bin/pip install -r requirements.txt

echo
echo "[SETUP] Done."
echo "[SETUP] Run a service manually with, e.g.:"
echo "        venv/bin/python3 run_raspi_all.py"
echo "[SETUP] Or install deploy/sagri.service (see its comments) to"
echo "        start it automatically on boot."
