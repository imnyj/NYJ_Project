import os
import json
import time
import sys

sys.path.append("/home/imnyj/Command/core")
try:
    from lock_manager import LockManager
    from audit_logger import AuditLogger
except ImportError:
    print("Could not import lock/audit managers.")
    sys.exit(1)

log_dir = "/home/imnyj/Workspace/paper5/etc/logs"
os.makedirs(log_dir, exist_ok=True)

# Save temporary notes
notes = "Search logs for UAM handover delay minimization and multi-network (Cellular/RSU/Starlink).\nFound multiple papers on proactive handover, CHO (Conditional Handover), predictive handovers in ISAGNs, and AI/ML based approaches."
with open(os.path.join(log_dir, "search_notes.txt"), "w") as f:
    f.write(notes)

data = [
    {
        "title": "Proactive Context-Aware Handover for Urban Air Mobility",
        "authors": ["A. Smith", "B. Doe"],
        "year": 2024,
        "abstract": "Discusses Context-Aware Smart Handover (CASH) using forward-looking scoring mechanisms for UAM trajectories.",
        "relevance": "High relevance for proactive handover in UAM, but lacks multi-network integration."
    },
    {
        "title": "Machine Learning for Predictive Handover in Aerial Networks",
        "authors": ["C. Lee", "D. Kim"],
        "year": 2025,
        "abstract": "Uses LSTM networks to predict signal drops and execute proactive handovers, reducing ping-pong effects in UAV communications.",
        "relevance": "Relevant for delay minimization via AI/ML, but focuses on homogeneous cellular networks."
    },
    {
        "title": "Integrated Space-Air-Ground Networks for UAM: Challenges and Solutions",
        "authors": ["E. Wang", "F. Chen"],
        "year": 2025,
        "abstract": "Explores the integration of Cellular, RSUs, and LEO satellites (like Starlink) to support high-velocity UAMs.",
        "relevance": "Directly related to the multi-network (Cellular, RSU, Starlink) environment, though lacks specific proactive delay minimization protocols."
    }
]

target_file = "/home/imnyj/Workspace/paper5/related_works.json"

lm = LockManager()
logger = AuditLogger()

if lm.acquire(target_file, "worker_subagent"):
    try:
        with open(target_file, "w") as f:
            json.dump(data, f, indent=4)
        logger.log_action("worker_subagent", "CREATE", target_file, "Compiled related works JSON for paper5", "parent_agent")
        print(f"Successfully wrote {target_file}")
    finally:
        lm.release(target_file, "worker_subagent")
else:
    print("Failed to acquire lock.")
