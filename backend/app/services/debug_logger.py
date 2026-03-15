import os
import datetime
import json
from typing import Any, Dict

class DebugLogger:
    """
    Dedicated debug logging system for KavachX.
    Records events to a local file for post-mortem analysis.
    """
    LOG_FILE = "kavachx_debug.log"

    @classmethod
    def log(cls, action: str, status: str, details: Any = None, error: str = None):
        """
        Log an event with timestamp and details.
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        entry = {
            "timestamp": timestamp,
            "action": action,
            "status": status,
            "details": details,
            "error": error
        }
        
        try:
            with open(cls.LOG_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"Failed to write to debug log: {e}")

    @classmethod
    def get_recent_logs(cls, limit: int = 100):
        """
        Retrieve recent logs.
        """
        if not os.path.exists(cls.LOG_FILE):
            return []
            
        logs = []
        try:
            with open(cls.LOG_FILE, "r") as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    logs.append(json.loads(line))
        except Exception as e:
            print(f"Failed to read debug log: {e}")
            
        return logs[::-1] # Newest first

# Global instance
debug_logger = DebugLogger()
