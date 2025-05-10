"""
Configuration Manager
Handles the loading and saving of configuration files
"""

import os
import json


class ConfigManager:
    """
    Manages configuration files for the application.
    Loads and saves JSON configuration files.
    """

    def __init__(self, config_dir="configs"):
        """Initialize the configuration manager"""
        self.config_dir = config_dir
        os.makedirs(self.config_dir, exist_ok=True)

    def get_config_files(self):
        """
        Get list of available configuration files.
        Returns list of config names (without extensions).
        """
        if not os.path.exists(self.config_dir):
            return []

        config_files = []
        for filename in os.listdir(self.config_dir):
            if filename.endswith(".json"):
                config_files.append(filename[:-5])  # Remove .json extension

        return sorted(config_files)

    def load_config(self, name):
        """
        Load a configuration by name.
        Returns the configuration data as dict or None if not found.
        """
        config_path = os.path.join(self.config_dir, f"{name}.json")
        
        if not os.path.exists(config_path):
            return None
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            return config_data
        except Exception as e:
            print(f"Error loading config {name}: {str(e)}")
            return None

    def get_config_text(self, name):
        """
        Get the raw text content of a configuration file.
        Returns the configuration data as string or None if not found.
        """
        config_path = os.path.join(self.config_dir, f"{name}.json")
        
        if not os.path.exists(config_path):
            return None
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading config {name}: {str(e)}")
            return None

    def save_config(self, name, config_data):
        """
        Save a configuration.
        If config_data is a string, save it directly.
        If config_data is a dict, convert to JSON and save.
        Returns True if successful, False otherwise.
        """
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
            
        config_path = os.path.join(self.config_dir, f"{name}.json")
        
        try:
            if isinstance(config_data, dict):
                # If it's a dict, convert to JSON string
                config_text = json.dumps(config_data, indent=4)
            else:
                # Otherwise assume it's already a string
                config_text = config_data
                
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(config_text)
                
            return True
        except Exception as e:
            print(f"Error saving config {name}: {str(e)}")
            return False

    def delete_config(self, name):
        """
        Delete a configuration file.
        Returns True if successful, False otherwise.
        """
        config_path = os.path.join(self.config_dir, f"{name}.json")
        
        if not os.path.exists(config_path):
            return False
        
        try:
            os.remove(config_path)
            return True
        except Exception as e:
            print(f"Error deleting config {name}: {str(e)}")
            return False