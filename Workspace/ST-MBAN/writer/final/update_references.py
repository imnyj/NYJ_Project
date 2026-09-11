import os
import sys
import shutil
import time

sys.path.append("/home/imnyj/Command/core")
from lock_manager import LockManager
from audit_logger import AuditLogger

filepath = "/home/imnyj/Workspace/paper1/writer/final/main.tex"
agent_id = "writer"

lm = LockManager()
if not lm.acquire(filepath, agent_id):
    print("Failed to acquire lock")
    sys.exit(1)

try:
    # Explicit backup as requested by user
    backup_dir = "/home/imnyj/Workspace/paper1/writer/final/backup/"
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = int(time.time())
    backup_path = os.path.join(backup_dir, f"main.tex.{timestamp}.bak")
    shutil.copy2(filepath, backup_path)
    print(f"Backed up to {backup_path}")

    # Read content
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replacements
    replacements = [
        (
            r"\emph{2018 2nd IEEE Advanced Information Management, Communicates, Electronic and Automation Control Conference (IMCEC)}, Xi'an, China, 2018.",
            r"\emph{2018 2nd IEEE Advanced Information Management, Communicates, Electronic and Automation Control Conference (IMCEC)}, Xi'an, China, pp. 1162--1166, 2018."
        ),
        (
            r"\emph{Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining}, ACM, pp. 785--794, 2016.",
            r"\emph{Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining}, San Francisco, CA, USA, pp. 785--794, 2016."
        ),
        (
            r"\emph{Advances in Neural Information Processing Systems}, Curran Associates, Inc., pp. 6638--6648, 2018.",
            r"\emph{Advances in Neural Information Processing Systems}, Montr\'eal, QC, Canada, pp. 6638--6648, 2018."
        ),
        (
            r"\emph{International Conference on Machine Learning}, PMLR, pp. 2690--2700, 2020.",
            r"\emph{International Conference on Machine Learning}, Vienna, Austria, pp. 2690--2700, 2020."
        ),
        (
            r"\emph{Advances in Neural Information Processing Systems}, Curran Associates, Inc., vol. 34, pp. 18932--18943, 2021.",
            r"\emph{Advances in Neural Information Processing Systems}, Virtual Event, pp. 18932--18943, 2021."
        ),
        (
            r"\emph{Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR)}, IEEE, pp. 770--778, 2016.",
            r"\emph{Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR)}, Las Vegas, NV, USA, pp. 770--778, 2016."
        ),
        (
            r"\emph{Proceedings of the 2014 Conference on Empirical Methods in Natural Language Processing (EMNLP)}, Association for Computational Linguistics, pp. 1724--1734, 2014.",
            r"\emph{Proceedings of the 2014 Conference on Empirical Methods in Natural Language Processing (EMNLP)}, Doha, Qatar, pp. 1724--1734, 2014."
        ),
        (
            r"\emph{The Twelfth International Conference on Learning Representations}, ICLR, 2024.",
            r"\emph{The Twelfth International Conference on Learning Representations}, Vienna, Austria, 2024."
        ),
        (
            r"\emph{The Twelfth International Conference on Learning Representations}, ICLR, 2023.",
            r"\emph{The Eleventh International Conference on Learning Representations}, Kigali, Rwanda, 2023."
        )
    ]

    for old_str, new_str in replacements:
        if old_str not in content:
            print(f"WARNING: String not found!\n{old_str}")
        content = content.replace(old_str, new_str)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
        
    # Audit log
    logger = AuditLogger()
    logger.log_action(agent_id, "MODIFY", filepath, "Updated IEEE reference formats")
    print("Modifications and audit log applied successfully.")

finally:
    lm.release(filepath, agent_id)
