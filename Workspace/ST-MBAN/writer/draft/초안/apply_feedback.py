import sys
import os

sys.path.append("/home/imnyj/Command/core")

from lock_manager import LockManager
from audit_logger import AuditLogger

lm = LockManager()
logger = AuditLogger()

target_file = "/home/imnyj/Workspace/paper1/writer/draft/초안/04_H_ST_MBAN.md"
agent_id = "worker_writer_c230"
parent_id = "8463b3f9-9c77-430b-80be-04a8b33f1fc6"

print("Acquiring lock...")
if lm.acquire(target_file, agent_id):
    try:
        print("Lock acquired. Reading file...")
        with open(target_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Apply edits based on feedback
        content = content.replace(
            "This projection maximizes the representation capacity of the model while deeply extracting the unique characteristics inherent to each domain.",
            "This projection maximizes the representation capacity of the model while extracting the unique characteristics of each domain."
        )

        content = content.replace(
            "Ultimately, this token-based multi-head attention fusion derives a comprehensive representation that fully reflects the dynamic context of the vehicle's mobility.",
            "Ultimately, this token-based multi-head attention fusion derives a comprehensive representation that reflects the dynamic context of the vehicle's mobility."
        )
        
        content = content.replace(
            "The architecture is specifically designed as a deterministic model to provide highly reliable point estimates for traffic dwell time prediction.",
            "The architecture is specifically designed as a deterministic model to provide reliable point estimates for traffic dwell time prediction."
        )

        content = content.replace(
            "This choice of loss function ensures that the model learns robustly even in the presence of extreme outliers",
            "This choice of loss function ensures that the model learns even in the presence of extreme outliers"
        )
        
        content = content.replace(
            "Following the construction of the feature vector within the Pending Data Table (PDT), the inference module is applied",
            "Following the construction of the feature vector within the Pending Data Table, the inference module is applied"
        )

        print("Writing updated content...")
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(content)

        print("Logging action...")
        logger.log_action(agent_id, "MODIFY", target_file, "Applied critic feedback: removed AI expressions and redundant acronym.", parent_id)
        
        print("Success!")
    finally:
        lm.release(target_file, agent_id)
        print("Lock released.")
else:
    print("Failed to acquire lock.")
