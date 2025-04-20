#!/bin/bash

# D10 Discord Bot - Linux Setup Script
# This script will set up the bot for running on a Linux server

echo "=== D10 Discord Bot - Linux Setup ==="
echo ""

# Make sure we're in the correct directory
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
cd "$SCRIPT_DIR"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Installing now..."
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv
else
    echo "✓ Python 3 is installed"
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment exists"
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -U discord.py python-dotenv asyncio aiohttp flask flask-sqlalchemy gunicorn psycopg2-binary
echo "✓ Dependencies installed"

# Create logs directory
mkdir -p logs
echo "✓ Logs directory created"

# Set up PostgreSQL database
echo "Setting up PostgreSQL database..."
echo "NOTE: You need PostgreSQL installed. If it's not installed, run:"
echo "    sudo apt install postgresql postgresql-contrib"
echo ""

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "⚠️ PostgreSQL is not installed. Please install it manually."
    echo "Run: sudo apt install postgresql postgresql-contrib"
    echo ""
else
    echo "✓ PostgreSQL is installed"
    
    # Create database and user if they don't exist
    echo "To create a database and user, you'll need the PostgreSQL password."
    echo "If you haven't set a password yet, you might need to set one with:"
    echo "    sudo -u postgres psql -c \"ALTER USER postgres PASSWORD 'your_password';\""
    echo ""
    
    read -p "Create database discord_bot? (y/n): " create_db
    if [[ $create_db == "y" ]]; then
        sudo -u postgres psql -c "CREATE DATABASE discord_bot;" || echo "Database may already exist"
        echo "✓ Database created (or already exists)"
    fi
fi

# Copy Linux-compatible files
echo "Setting up Linux-compatible files..."
cp -f database_pg.py database.py
cp -f bot_linux.py bot.py

echo "✓ Linux-compatible files set up"

# Create/update .env file
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
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
    echo "✓ .env file created"
    echo "⚠️ Please edit the .env file and add your Discord token and other credentials"
else
    echo "✓ .env file exists"
fi

# Make start script executable
chmod +x start.sh
echo "✓ Start script is now executable"

echo ""
echo "=== Setup complete! ==="
echo ""
echo "To start the bot, run:"
echo "    ./start.sh"
echo ""
echo "If you're running this bot as a service, you might want to set up a systemd service."
echo "Here's an example systemd service file (save as /etc/systemd/system/discordbot.service):"
echo ""

cat << EOF
[Unit]
Description=D10 Discord Bot
After=network.target postgresql.service

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/python3 bot_main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo ""
echo "After creating the service file, run:"
echo "    sudo systemctl daemon-reload"
echo "    sudo systemctl enable discordbot"
echo "    sudo systemctl start discordbot"
echo ""
echo "To view logs:"
echo "    sudo journalctl -u discordbot -f"