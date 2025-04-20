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

# Ask if user wants to use database or memory-based storage
echo "The bot can use either PostgreSQL or in-memory storage."
echo "In-memory storage is simpler but data is lost when the bot restarts."
echo "PostgreSQL storage requires a database but keeps data between restarts."
echo ""
read -p "Use PostgreSQL database? (y/n): " use_db

if [[ $use_db == "y" ]]; then
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
else
    echo "Using in-memory storage instead of PostgreSQL database."
    echo "Note: All data will be lost when the bot restarts."
    
    # Generate memory database files
    cat > memory_database.py << 'EOF'
"""
In-memory database implementation for D10 Discord Bot
"""
import uuid
import logging
import datetime
import copy
from typing import Dict, List, Any, Optional

# Set up logging
logger = logging.getLogger('d10-bot')

class MemoryDatabase:
    """
    In-memory database manager for D10 Discord Bot
    """
    def __init__(self):
        """Initialize the in-memory database"""
        self.collections = {
            'tickets': [],
            'welcome': [],
            'status': [],
            'roles': [],
            'voice_channels': [],
            'temp_voice_channels': [],
            'reports': [],
            'giveaways': [],
            'vouches': [],
            'slot_channels': []
        }
        logger.info("In-memory database initialized")

    def _setup_database(self) -> None:
        """
        No setup needed for in-memory database
        """
        pass

    def get(self, collection: str, filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Get items from a collection with optional filtering
        """
        try:
            if collection not in self.collections:
                self.collections[collection] = []
                
            # Return all items if no filter
            if not filter_dict:
                return copy.deepcopy(self.collections.get(collection, []))
            
            # Filter the items
            results = []
            for item in self.collections.get(collection, []):
                match = True
                for key, value in filter_dict.items():
                    if key not in item or item[key] != value:
                        match = False
                        break
                if match:
                    results.append(copy.deepcopy(item))
            
            return results
                
        except Exception as e:
            logger.error(f"In-memory database get error ({collection}): {e}", exc_info=True)
            return []

    def get_one(self, collection: str, filter_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get a single item from a collection with filtering
        """
        try:
            if collection not in self.collections:
                self.collections[collection] = []
                
            # Filter the items
            for item in self.collections.get(collection, []):
                match = True
                for key, value in filter_dict.items():
                    if key not in item or item[key] != value:
                        match = False
                        break
                if match:
                    return copy.deepcopy(item)
            
            return None
                
        except Exception as e:
            logger.error(f"In-memory database get_one error ({collection}): {e}", exc_info=True)
            return None

    def insert(self, collection: str, data: Dict[str, Any]) -> str:
        """
        Insert a new item into a collection
        """
        try:
            if collection not in self.collections:
                self.collections[collection] = []
            
            # Create a deep copy to avoid modifying the original
            item_data = copy.deepcopy(data)
            
            # Ensure we have an ID
            if 'id' not in item_data:
                item_data['id'] = str(uuid.uuid4())
            
            # Add the item to the collection
            self.collections[collection].append(item_data)
            
            return item_data['id']
                
        except Exception as e:
            logger.error(f"In-memory database insert error ({collection}): {e}", exc_info=True)
            raise

    def update(self, collection: str, id_value: str, data: Dict[str, Any]) -> bool:
        """
        Update an existing item in a collection
        """
        try:
            if collection not in self.collections:
                return False
            
            # Create a deep copy to avoid modifying the original
            update_data = copy.deepcopy(data)
            
            # Find the item by ID
            for i, item in enumerate(self.collections[collection]):
                if item.get('id') == id_value:
                    # Update all fields except ID
                    for key, value in update_data.items():
                        if key != 'id':
                            item[key] = value
                    return True
            
            return False
                
        except Exception as e:
            logger.error(f"In-memory database update error ({collection}): {e}", exc_info=True)
            return False

    def delete(self, collection: str, id_value: str) -> bool:
        """
        Delete an item from a collection
        """
        try:
            if collection not in self.collections:
                return False
            
            # Find the item by ID
            for i, item in enumerate(self.collections[collection]):
                if item.get('id') == id_value:
                    del self.collections[collection][i]
                    return True
            
            return False
                
        except Exception as e:
            logger.error(f"In-memory database delete error ({collection}): {e}", exc_info=True)
            return False

    def delete_many(self, collection: str, filter_dict: Dict[str, Any]) -> int:
        """
        Delete multiple items from a collection with filtering
        """
        try:
            if collection not in self.collections:
                return 0
            
            # Find items to delete
            items_to_delete = []
            for i, item in enumerate(self.collections[collection]):
                match = True
                for key, value in filter_dict.items():
                    if key not in item or item[key] != value:
                        match = False
                        break
                if match:
                    items_to_delete.append(i)
            
            # Delete the items (in reverse order to avoid index issues)
            items_to_delete.sort(reverse=True)
            for i in items_to_delete:
                del self.collections[collection][i]
            
            return len(items_to_delete)
                
        except Exception as e:
            logger.error(f"In-memory database delete_many error ({collection}): {e}", exc_info=True)
            return 0
EOF
    
    # Generate memory bot file
    cat > bot_memory.py << 'EOF'
"""
D10 Discord Bot - Core bot class using in-memory database
"""

import os
import logging
import datetime
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Union, List

from memory_database import MemoryDatabase

# Configure logging
logger = logging.getLogger('d10-bot')

class D10Bot(commands.Bot):
    """
    Main bot class with all core functionality
    """
    def __init__(self):
        """
        Initialize the bot with required intents and command prefix
        """
        # Enable all necessary intents
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.presences = True
        
        # Initialize the bot with prefix commands (!)
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None  # Disable default help command
        )
        
        # Initialize database
        self.db = MemoryDatabase()
        
        # Settings
        self.staff_role_id = self._get_role_id("DISCORD_STAFF_ROLE_ID")
        self.status_role_id = self._get_role_id("DISCORD_STATUS_ROLE_ID")
        self.vouch_role_id = self._get_role_id("DISCORD_VOUCH_ROLE_ID")
        self.vouch_channel_id = self._get_channel_id("DISCORD_VOUCH_CHANNEL_ID")
        
        # Anti-raid settings
        self.anti_raid_mode = False
        self.join_timestamps = []
        
        # Active tasks
        self.tasks = []
        
    def _get_role_id(self, env_var: str) -> int:
        """Get a role ID from environment variables"""
        try:
            return int(os.getenv(env_var, "0"))
        except (ValueError, TypeError):
            logger.warning(f"{env_var} not set or invalid, using 0")
            return 0
            
    def _get_channel_id(self, env_var: str) -> int:
        """Get a channel ID from environment variables"""
        try:
            return int(os.getenv(env_var, "0"))
        except (ValueError, TypeError):
            logger.warning(f"{env_var} not set or invalid, using 0")
            return 0

    async def setup_hook(self) -> None:
        """
        Hook that is called when the bot is initially setting up
        """
        logger.info("Setting up bot...")
        
        # Load all cog modules
        await self.load_cogs()
        
        # Sync commands with Discord
        guild_id = os.getenv("DISCORD_SERVER_ID")
        if guild_id:
            try:
                guild = discord.Object(id=int(guild_id))
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                logger.info(f"Synced {len(synced)} commands to guild: {guild_id}")
            except Exception as e:
                logger.error(f"Failed to sync commands: {e}", exc_info=True)
        else:
            logger.warning("DISCORD_SERVER_ID not set, skipping guild command sync")

    async def load_cogs(self) -> None:
        """
        Load all cog modules
        """
        # Define the cogs to load
        cog_names = [
            "tickets",
            "welcome",
            "status_tracker",
            "role_management",
            "admin",
            "voice_channels",
            "reports",
            "giveaway",
            "vouch",
            "slot_channels"
        ]
        
        # Load each cog
        for cog in cog_names:
            try:
                await self.load_extension(f"cogs.{cog}")
                logger.info(f"Loaded cog: cogs.{cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}", exc_info=True)

    async def on_ready(self) -> None:
        """
        Event handler for when the bot is ready
        """
        logger.info(f"Logged in as {self.user.name}#{self.user.discriminator} (ID: {self.user.id})")
        
        # Count connected guilds
        guild_count = len(self.guilds)
        logger.info(f"Connected to {guild_count} guilds")
        
        # Set the bot's status
        activity = discord.Activity(
            type=discord.ActivityType.watching, 
            name="the server | Use /help"
        )
        await self.change_presence(activity=activity, status=discord.Status.online)

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """
        Global error handler for command errors
        """
        if isinstance(error, commands.CommandNotFound):
            return
            
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: {error.param.name}")
            return
            
        if isinstance(error, commands.BadArgument):
            await ctx.send(f"Invalid argument: {str(error)}")
            return
            
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command.")
            return
            
        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f"I don't have the required permissions: {', '.join(error.missing_permissions)}")
            return
            
        # Log unexpected errors
        logger.error(f"Command error in {ctx.command}: {str(error)}", exc_info=True)
        await ctx.send("An unexpected error occurred. Please try again later.")

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        """
        Global error handler for application command errors
        """
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"This command is on cooldown. Try again in {error.retry_after:.1f} seconds.",
                ephemeral=True
            )
            return
            
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True
            )
            return
            
        if isinstance(error, app_commands.BotMissingPermissions):
            await interaction.response.send_message(
                f"I don't have the required permissions: {', '.join(error.missing_permissions)}",
                ephemeral=True
            )
            return
            
        # Log unexpected errors
        logger.error(f"App command error in {interaction.command.name}: {str(error)}", exc_info=True)
        
        # If interaction has not been responded to yet
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "An unexpected error occurred. Please try again later.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "An unexpected error occurred. Please try again later.",
                ephemeral=True
            )
EOF

    # Update main.py to use memory database
    cat > main.py << 'EOF'
"""
D10 Discord Bot - Main entry point (Linux-compatible)
"""

import os
import sys
import logging
import asyncio
import threading
import signal
from flask import Flask, jsonify, render_template_string
from dotenv import load_dotenv

# Use memory-based bot to avoid database connection issues
from bot_memory import D10Bot

# Load environment variables
load_dotenv()

# Configure logging with proper Linux paths
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "bot.log")),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("d10-bot")

# Setup signal handlers for graceful shutdown
def signal_handler(sig, frame):
    logger.info("Received shutdown signal, exiting gracefully...")
    sys.exit(0)

# Register signal handlers
try:
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
except (AttributeError, ValueError):
    # Some signals might not be available on all platforms
    pass

# Create Flask app
app = Flask(__name__)

# Simple landing page
@app.route("/")
def index():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>D10 Discord Bot</title>
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <style>
            body {
                padding: 40px;
                background-color: #1d1d1d;
                color: #f8f9fa;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
            }
            .status-card {
                background-color: #2d2d2d;
                border-radius: 5px;
                padding: 20px;
                margin-top: 20px;
            }
            .feature-list {
                margin-top: 30px;
            }
            .status-badge {
                padding: 5px 10px;
                border-radius: 3px;
                font-size: 14px;
                font-weight: bold;
            }
            .status-online {
                background-color: #28a745;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>D10 Discord Bot</h1>
            <p class="lead">A comprehensive Discord bot with moderation, tickets, roles, and more!</p>

            <div class="status-card">
                <h3>Bot Status</h3>
                <p>Bot is <span class="status-badge status-online">ONLINE</span></p>
            </div>

            <div class="feature-list">
                <h3>Features</h3>
                <ul>
                    <li>Ticket System</li>
                    <li>Welcome Messages</li>
                    <li>Status Tracking</li>
                    <li>Role Management</li>
                    <li>Slot Channels</li>
                    <li>Admin Commands</li>
                    <li>Voice Channel Management</li>
                    <li>Report/Praise System</li>
                    <li>Giveaways</li>
                    <li>Vouch System</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)

# API endpoint for bot status
@app.route("/api/status")
def status():
    return jsonify({
        "bot_name": "D10 Discord Bot",
        "status": "online"
    })

# Function to run the Flask app
def run_flask_app():
    # Use port 8080 when running directly through python
    app.run(host="0.0.0.0", port=8080)

# Function to run the Discord bot
def run_discord_bot():
    # Get the token from environment variables
    token = os.getenv("DISCORD_TOKEN")

    if not token:
        logger.error("DISCORD_TOKEN environment variable not set")
        return

    # Create and run bot
    bot = D10Bot()

    try:
        asyncio.run(bot.start(token))
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)

# Main entry point
if __name__ == "__main__":
    # Start the bot in a separate thread
    bot_thread = threading.Thread(target=run_discord_bot)
    bot_thread.daemon = True
    bot_thread.start()

    # Start the Flask app in the main thread
    run_flask_app()
EOF

    echo "✓ In-memory database setup complete"
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
ExecStart=$(pwd)/venv/bin/python3 main.py
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