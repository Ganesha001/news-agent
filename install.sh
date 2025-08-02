#!/bin/bash

# News Agent Installation Script
# This script helps you set up the News Agent quickly

set -e

echo "🚀 News Agent Installation Script"
echo "=================================="

# Check if Python 3.8+ is installed
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Error: Python 3.8 or higher is required. Found: $python_version"
    exit 1
fi

echo "✅ Python version: $python_version"

# Create virtual environment
echo "🔧 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p data

# Set up environment file
if [ ! -f .env ]; then
    echo "⚙️ Setting up environment file..."
    cp env.template .env
    echo "📝 Please edit .env file with your API keys and preferences"
    echo "   Required: OPENAI_API_KEY, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN"
    echo "   Optional: NEWSGUARD_API_KEY"
else
    echo "✅ Environment file already exists"
fi

# Make CLI executable
chmod +x cli.py

echo ""
echo "🎉 Installation completed!"
echo ""
echo "📖 Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Configure config/config.yaml if needed"
echo "3. Test the installation:"
echo "   source venv/bin/activate"
echo "   python cli.py config"
echo "   python cli.py test-fetch"
echo ""
echo "🚀 To run the news agent:"
echo "   source venv/bin/activate"
echo "   python cli.py run"
echo ""
echo "📚 For more information, see README.md" 