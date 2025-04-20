"""
D10 Discord Bot - Main entry point
"""

import os
import logging
import asyncio
import threading
from flask import Flask, jsonify, render_template_string
from bot import D10Bot
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("d10-bot")

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