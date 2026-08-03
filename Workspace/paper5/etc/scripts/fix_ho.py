import sys
import os

sys.path.append(os.path.abspath("/home/imnyj/Command/core"))
from lock_manager import LockManager
from audit_logger import AuditLogger

ho_path = "/home/imnyj/Workspace/paper5/handover_optimization.py"

lm = LockManager("/tmp/uam_locks", "/tmp/uam_backups")
al = AuditLogger("/home/imnyj/Workspace/paper5/audit_log.json")

if lm.acquire(ho_path, "gemini_agent", timeout=10):
    try:
        with open(ho_path, "r") as f:
            content = f.read()
        
        # Replace the problematic line
        target = "comm_env = CommunicationEnvironment(buildings=sim.env.buildings)"
        replacement = """model_buildings = [Building(building_id=b.id, x_min=b.x_min, x_max=b.x_max, y_min=b.y_min, y_max=b.y_max, height=b.height) for b in sim.env.buildings]
    comm_env = CommunicationEnvironment(buildings=model_buildings)"""
        
        if target in content:
            content = content.replace(target, replacement)
            with open(ho_path, "w") as f:
                f.write(content)
            al.log_action("gemini_agent", "MODIFY", ho_path, "Fixed building conversion in handover_optimization.py")
            print("Successfully updated handover_optimization.py")
        else:
            print("Target string not found!")
    finally:
        lm.release(ho_path, "gemini_agent")
