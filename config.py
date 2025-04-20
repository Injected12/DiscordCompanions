"""
Configuration management for the D10 Discord bot
"""

import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("d10-bot")

class Config:
    """
    Configuration manager for bot settings
    """
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file or create default if not exists
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"Loaded configuration from {self.config_file}")
                return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            
        # Default configuration
        default_config = {
            "ticket_system": {
                "enabled": True,
                "channel_id": None,
                "image_url": "https://imgur.com/HuSzeAX"
            },
            "welcome_system": {
                "enabled": True,
                "channel_id": None,
                "message": "Welcome {member} to the server! Join discord.gg/d10"
            },
            "status_tracking": {
                "enabled": True,
                "status_text": ".gg/d10"
            },
            "voice_channels": {
                "enabled": True,
                "category_id": None
            },
            "slot_channels": {
                "enabled": True,
                "category_id": None
            }
        }
        
        # Save the default config
        self.save_config(default_config)
        return default_config
        
    def save_config(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Save configuration to file
        """
        if config:
            self.config = config
            
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Saved configuration to {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
            
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value by key
        """
        keys = key.split('.')
        config = self.config
        
        for i, k in enumerate(keys[:-1]):
            if k not in config:
                config[k] = {}
            config = config[k]
            
        config[keys[-1]] = value
        self.save_config()
