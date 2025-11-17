#!/bin/bash
# Setup Script for Temporal Support Ticket Demo
# Run this to test everything from scratch

set -e  # Exit on any error

echo "Environment setup..."

echo "Creating venv"
python3 -m venv venv
echo "⚡ Installing Temporal Python SDK into venv"
venv/bin/pip install --upgrade pip
venv/bin/pip install temporalio
echo "Temporal Python SDK installed"

# Check for Temporal CLI
echo
echo "🔍 Checking Temporal CLI..."
if command -v temporal &> /dev/null; then
    echo "✅ Temporal CLI found: $(temporal --version)"
else
    echo "Temporal CLI not found"
    echo
    echo "Please install Temporal CLI:"
    echo "macOS:   brew install temporal"
    echo "Linux:   curl -sSf https://temporal.download/cli.sh | sh"
    echo "Windows: See https://docs.temporal.io/cli#install"
    echo
    echo "Or run Temporal Server with Docker:"
    echo "git clone https://github.com/temporalio/docker-compose.git temporal-docker"
    echo "cd temporal-docker && docker-compose up -d"
    echo
    read -p "Press Enter once Temporal is available..."
fi

# Test Temporal connection
echo
echo "Testing Temporal server connection..."
python3 -c "
import asyncio
from temporalio.client import Client

async def test_connection():
    try:
        client = await Client.connect('localhost:7233')
        print('✅ Successfully connected to Temporal server')
        return True
    except Exception as e:
        print(f'❌ Failed to connect to Temporal server: {e}')
        return False

if not asyncio.run(test_connection()):
    print()
    print('Please start Temporal server:')
    print('  temporal server start-dev')
    print('  (or use Docker as mentioned above)')
    exit(1)
"

echo
echo "Environment created"
echo "==================="
echo
echo "Your environment is ready. To run the demo:"
echo
echo "Terminal 1 - Start Temporal Server if it's not started already git@github.com:mmerrell/support-tracker.git (no venv needed):"
echo "  temporal server start-dev"
echo
echo "Terminal 2 - Start Worker (script activates venv):"
echo "  ./start_worker.sh"
echo
echo "Terminal 3 - Run Demo (script activates venv):"
echo "  ./run_demo.sh"
echo
