#!/bin/bash
set -e

echo "📦 Installing dependencies..."
pip install --upgrade pip setuptools wheel

# Install dependencies directly
pip install -r requirements.txt

echo "✅ Dependencies installed successfully!"
