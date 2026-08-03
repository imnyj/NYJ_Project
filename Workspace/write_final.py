import sys
import os
import json
import time
sys.path.append('/home/imnyj')
from Command.core.lock_manager import LockManager
from Command.core.audit_logger import AuditLogger

def write_and_log(target_path, content, agent_id):
    lm = LockManager()
    logger = AuditLogger()
    
    if lm.acquire(target_path, agent_id):
        try:
            with open(target_path, 'w') as f:
                f.write(content)
            logger.log_action(agent_id, "CREATE/MODIFY", target_path, "Generated content from main agent")
            print(f"Successfully wrote and logged: {target_path}")
        finally:
            lm.release(target_path, agent_id)
    else:
        print(f"Failed to acquire lock for {target_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 write_final.py <target_path> <content_file>")
        sys.exit(1)
        
    target = sys.argv[1]
    content_file = sys.argv[2]
    
    with open(content_file, 'r') as f:
        content = f.read()
        
    write_and_log(target, content, "manager_main")
