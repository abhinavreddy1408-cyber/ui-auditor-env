#!/bin/bash

# run_tests.sh
# Automation script for the Local Testing Suite (Unix/Linux/Mac)

# Exit on any error
set -e

# Define project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "===================================================="
echo "🚀 Setting up Local Testing Suite..."
echo "===================================================="

# 1. Create virtual environment
if [ ! -d ".venv" ]; then
    echo "[1/3] Creating virtual environment..."
    python3 -m venv .venv
else
    echo "[1/3] Virtual environment already exists."
fi

# 2. Activate and install dependencies
echo "[2/3] Installing dependencies from requirements.txt..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 3. Run the test script
echo "[3/3] Running test_local.py..."
export PYTHONPATH="$PROJECT_ROOT"
python test_local.py

# Deactivate
deactivate

echo "===================================================="
echo "✅ Test run complete."
echo "===================================================="
