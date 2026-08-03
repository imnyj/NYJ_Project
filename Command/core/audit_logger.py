import os
import json
import time

class AuditLogger:
    def __init__(self, log_file="/tmp/agent_audit.log"):
        self.log_file = log_file

    def log_action(self, agent_id, action_type, target_file, description, parent_id=None):
        log_entry = {
            "timestamp": time.time(),
            "agent_id": agent_id,
            "parent_id": parent_id,
            "action": action_type,
            "target": target_file,
            "description": description
        }
        
        with open(self.log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def trace_blame(self, target_file):
        # Read the log backwards to find the last agent who modified the file
        if not os.path.exists(self.log_file):
            return None
            
        with open(self.log_file, "r") as f:
            lines = f.readlines()
            
        for line in reversed(lines):
            try:
                entry = json.loads(line)
                if entry.get("target") == target_file and entry.get("action") in ["MODIFY", "CREATE"]:
                    return entry
            except json.JSONDecodeError:
                continue
        return None

if __name__ == "__main__":
    logger = AuditLogger()
    logger.log_action("worker_1", "MODIFY", "test.txt", "Added new function.", "manager_alpha")
    blame = logger.trace_blame("test.txt")
    print("Blame record:", blame)
