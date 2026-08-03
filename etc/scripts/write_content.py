import sys
sys.path.append('/home/imnyj')
from Command.core.lock_manager import LockManager
from Command.core.audit_logger import AuditLogger

filepath = sys.argv[1]
agent_id = sys.argv[2]
content_file = sys.argv[3]

lm = LockManager()
logger = AuditLogger()

if lm.acquire(filepath, agent_id):
    with open(content_file, 'r') as f:
        content = f.read()
    with open(filepath, 'w') as f:
        f.write(content)
    logger.log_action(agent_id, "CREATE/MODIFY", filepath, "Assembled and refined content")
    lm.release(filepath, agent_id)
    print("Success")
else:
    print("Failed to acquire lock")
