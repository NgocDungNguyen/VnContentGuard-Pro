#!/bin/bash
set -e

echo "📦 Installing dependencies with pre-built wheels only..."
pip install --upgrade pip setuptools wheel

# Try to install with only binary wheels first (faster, safer)
pip install --only-binary :all: -r requirements.txt 2>/dev/null || {
    echo "⚠️ Some packages require compilation, installing with build support..."
    pip install -r requirements.txt --no-cache-dir
}

echo "✅ Dependencies installed successfully!"
