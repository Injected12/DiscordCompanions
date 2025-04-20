# D10 Discord Bot - Linux Deployment Guide

This guide will help you deploy and run the D10 Discord Bot on a Linux server. The bot has been specifically modified to work well in a Linux environment with PostgreSQL database support.

## Prerequisites

- A Linux server (Ubuntu/Debian recommended)
- Python 3.8 or higher
- PostgreSQL database
- Discord Bot token and server details

## Setup Instructions

### 1. Install Required System Packages

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git postgresql postgresql-contrib
```

### 2. Clone the Repository

```bash
git clone https://github.com/YourUsername/D10DiscordBot.git
cd D10DiscordBot
```

### 3. Run the Setup Script

The included setup script will automatically create a virtual environment, install dependencies, and set up the necessary files for Linux:

```bash
chmod +x setup_linux.sh
./setup_linux.sh
```

Follow the prompts in the setup script. It will:
- Check if Python is installed
- Create a virtual environment
- Install required Python packages
- Set up the PostgreSQL database structure
- Copy the Linux-compatible files
- Create a `.env` file for your configuration

### 4. Configure the Bot

Edit the `.env` file with your Discord bot token and other credentials:

```bash
nano .env
```

Add the following information:

```
# Discord Bot Configuration
DISCORD_TOKEN=your_discord_bot_token
DISCORD_SERVER_ID=your_server_id
DISCORD_STAFF_ROLE_ID=your_staff_role_id
DISCORD_STATUS_ROLE_ID=your_status_role_id
DISCORD_VOUCH_ROLE_ID=your_vouch_role_id
DISCORD_VOUCH_CHANNEL_ID=your_vouch_channel_id

# PostgreSQL Database Configuration
PGDATABASE=discord_bot
PGUSER=postgres
PGPASSWORD=your_database_password
PGHOST=localhost
PGPORT=5432
```

### 5. Running the Bot

You can run the bot directly with:

```bash
./start.sh
```

### 6. Running as a Service (Recommended)

To keep the bot running in the background and automatically start when the server reboots, set up a systemd service:

1. Create a service file:

```bash
sudo nano /etc/systemd/system/discordbot.service
```

2. Add the following content (replace `your_username` with your actual username):

```
[Unit]
Description=D10 Discord Bot
After=network.target postgresql.service

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username/D10DiscordBot
ExecStart=/home/your_username/D10DiscordBot/venv/bin/python3 bot_main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

3. Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable discordbot
sudo systemctl start discordbot
```

4. Check the status:

```bash
sudo systemctl status discordbot
```

5. View logs:

```bash
sudo journalctl -u discordbot -f
```

## Database Management

The bot uses PostgreSQL for data storage. To access the database directly:

```bash
sudo -u postgres psql discord_bot
```

Common PostgreSQL commands:
- `\dt` - List all tables
- `\d tablename` - Describe a table
- `SELECT * FROM tablename;` - View all data in a table
- `\q` - Quit PostgreSQL shell

## Troubleshooting

### Bot Won't Start
- Check the logs in the `logs` directory
- Verify that all required environment variables are set in the `.env` file
- Ensure PostgreSQL is running with `sudo systemctl status postgresql`
- Test database connection with `psql -U postgres -d discord_bot`

### Database Issues
- Ensure PostgreSQL is installed and running
- Check database credentials in the `.env` file
- The tables should be created automatically when the bot first starts

### Permission Issues
- Make sure the user running the bot has permissions to access all required directories
- Check file permissions for the script files: `chmod +x start.sh setup_linux.sh`

## Updating the Bot

To update the bot with new changes:

1. Pull the latest changes:

```bash
git pull
```

2. Re-run the setup script:

```bash
./setup_linux.sh
```

3. Restart the bot:

```bash
sudo systemctl restart discordbot
```

## Features

The D10 Discord Bot includes:
- Ticket System
- Welcome Messages
- Status Tracking
- Role Management
- Slot Channels
- Admin Commands
- Voice Channel Management
- Report/Praise System
- Giveaways
- Vouch System

Each feature is implemented as a separate cog in the `cogs` directory, making the bot modular and extensible.