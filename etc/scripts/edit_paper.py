import sys
sys.path.append("/home/imnyj/Command/core")
from lock_manager import LockManager
from audit_logger import AuditLogger

lm = LockManager()
logger = AuditLogger()
filepath = "/home/imnyj/papers/paper1/paper/draft/main.tex"
agent_id = "editor_agent"

if lm.acquire(filepath, agent_id):
    try:
        with open(filepath, "r") as f:
            content = f.read()
        
        target = r"""As shown in Figure~\ref{fig:G4} (G4), we analyze the trade-off between the fine-tuning queue size and local performance. Increasing the fine-tuning queue size decreases the number of local updates, causing model staleness, which slightly worsens the final converged MAE. More importantly, accumulating larger snapshot queues causes the Memory Burden (MB) on the RSU to spike during the update phase. A queue size of 5000 was chosen as the optimal sweet spot because it safely avoids the 2\,GB (2048\,MB) physical RAM limit of the RSU edge devices, unlike queue sizes of 6000 or greater which cause out-of-memory (OOM) failures."""
        
        replacement = r"""As shown in Figure~\ref{fig:G4} (G4), we analyze the trade-off between the fine-tuning queue size and local prediction stability. A queue size of 4000 is selected as the optimal operating parameter based on three analytical justifications. First, this value represents the knee of the curve regarding cost-effectiveness; the marginal gain in stability (variance reduction) drops significantly when scaling past 4000. Second, to ensure statistical confidence, a queue size of 4000 is the first point where the MAE variance (standard deviation) drops below 1.0 (to 0.94), preventing erratic model updates. Third, this configuration provides an adequate ITS SLA margin. According to ITS recommended standards, caching and model updates should occur every 15--60 minutes \cite{its_standard}. Accumulating a queue of 4000 snapshots takes approximately 34 minutes, placing the update frequency safely in the middle of this interval and providing a safety margin against varying traffic density."""
        
        if target in content:
            new_content = content.replace(target, replacement)
            with open(filepath, "w") as f:
                f.write(new_content)
            logger.log_action(agent_id, "MODIFY", filepath, "Updated Trade-off Analysis of Queue Size per G4 analysis.", "main agent")
            print("Edit successful.")
        else:
            print("Target string not found in the file.")
            
    finally:
        lm.release(filepath, agent_id)
        print("Lock released.")
else:
    print("Failed to acquire lock.")
