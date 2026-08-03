import sys
import os
import shutil

sys.path.append("/home/imnyj")
from Command.core.lock_manager import LockManager
from Command.core.audit_logger import AuditLogger

filepath = "/home/imnyj/Workspace/House/ui/index.html"
tmp_filepath = "/home/imnyj/Workspace/House/ui/index.tmp.html"
agent_id = "9bab3ccf-1ad1-4512-bd06-21842944ac25"
parent_id = "921dc5f5-8214-4a84-8db9-3610796dea9a"

lm = LockManager()
logger = AuditLogger()

if lm.acquire(filepath, agent_id):
    try:
        shutil.move(tmp_filepath, filepath)
        logger.log_action(agent_id, "CREATE/MODIFY", filepath, "Created premium real estate calculator UI", parent_id)
        print("Success: Lock acquired, file written, log appended.")
    finally:
        lm.release(filepath, agent_id)
else:
    print("Failed to acquire lock.")
