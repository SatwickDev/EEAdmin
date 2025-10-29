import json
import os
from datetime import datetime

class DatabaseConnectionManager:
    """
    Manages database connection configurations stored in a JSON file.
    Supports listing, adding, updating, deleting, and testing connections.
    """

    def __init__(self, config_file='database_connections.json'):
        self.config_file = config_file
        self.connections = {}
        self.load_config()

    def load_config(self):
        """Load connection configurations from the JSON file."""
        if not os.path.exists(self.config_file):
            # Create an empty structure if the file doesn’t exist
            default_structure = {
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                },
                "connections": {}
            }
            with open(self.config_file, 'w') as f:
                json.dump(default_structure, f, indent=2)

        with open(self.config_file, 'r') as f:
            config = json.load(f)
            self.connections = config.get("connections", {})

    def save_config(self, config):
        """Save updated configuration back to JSON file."""
        config["metadata"]["updated_at"] = datetime.now().isoformat()
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)

    def list_connections(self):
        """Return a list of all connection definitions."""
        with open(self.config_file, 'r') as f:
            config = json.load(f)
        return [
            {
                "name": name,
                "display_name": conn.get("name"),
                "type": conn.get("type"),
                "description": conn.get("description", ""),
                "status": conn.get("status", "inactive"),
                "is_default": conn.get("is_default", False),
                "is_active": conn.get("status", "").lower() == "active"
            }
            for name, conn in config.get("connections", {}).items()
        ]

    def get_connection_info(self, connection_name):
        """Get full details of a specific connection."""
        with open(self.config_file, 'r') as f:
            config = json.load(f)
        return config.get("connections", {}).get(connection_name)

    def test_connection(self, connection_name):
        """
        Test the connection configuration.
        (In real usage, this would connect to the DB.)
        """
        info = self.get_connection_info(connection_name)
        if not info:
            return {
                "success": False,
                "connection_name": connection_name,
                "message": "Connection not found",
                "timestamp": datetime.now().isoformat()
            }

        # Simulated test
        try:
            db_type = info.get("type")
            cfg = info.get("config", {})

            # Add your actual DB connection logic here if needed
            print(f"🔗 Testing {db_type} connection for {connection_name}...")
            return {
                "success": True,
                "connection_name": connection_name,
                "message": "Connection successful",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "connection_name": connection_name,
                "message": f"Connection failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    def close_connection(self, connection_name):
        """
        Placeholder for closing active connections if used.
        (Currently, just logs — extend if you use actual DBs.)
        """
        print(f"🔒 Closing connection: {connection_name}")

    def close_all_connections(self):
        """Placeholder for cleanup."""
        print("🔒 All connections closed.")
