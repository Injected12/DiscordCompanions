#!/bin/bash

# D10 Discord Bot - Linux startup script
echo "Starting D10 Discord Bot..."
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3.8 or higher."
    echo "On Ubuntu/Debian systems, use: sudo apt update && sudo apt install python3 python3-pip"
    exit 1
fi

# Check Python version (need 3.8+)
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Your Python version is too old. Please install Python 3.8 or higher."
    exit 1
fi

# Install required packages
echo "Checking and installing required packages..."
pip3 install -U discord.py python-dotenv asyncio aiohttp flask flask-sqlalchemy gunicorn psycopg2-binary

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file with required environment variables..."
    cat > .env << EOF
# Discord Bot Configuration
DISCORD_TOKEN=
DISCORD_SERVER_ID=
DISCORD_STAFF_ROLE_ID=
DISCORD_STATUS_ROLE_ID=
DISCORD_VOUCH_ROLE_ID=
DISCORD_VOUCH_CHANNEL_ID=

# PostgreSQL Database Configuration
PGDATABASE=discord_bot
PGUSER=postgres
PGPASSWORD=
PGHOST=localhost
PGPORT=5432
EOF
    echo "Please edit the .env file and add your Discord token and other credentials"
    echo "Then run this script again"
    exit 1
fi

# Check if token is set
TOKEN=$(grep -oP 'DISCORD_TOKEN=\K.+' .env)
if [ -z "$TOKEN" ]; then
    echo "DISCORD_TOKEN is not set in .env file. Please edit the file and add your Discord bot token."
    exit 1
fi

# Load environment variables
export $(grep -v '^#' .env | xargs)

echo ""
echo "Starting the bot..."
echo "(Press Ctrl+C to stop the bot)"
echo ""

# Run the bot
python3 bot_main.py

# When finished
echo ""
echo "The bot has stopped."