import sys
import os

sys.path.append('/home/imnyj/Command')
from core.lock_manager import LockManager
from core.audit_logger import AuditLogger

sys.path.append('/home/imnyj/Workspace/paper4/etc/scripts')
from update_03_clean import update_03_system_model
from build_full_paper import build_full_paper

def apply_and_audit():
    lm = LockManager()
    logger = AuditLogger()
    agent_id = "worker_m6_revision"

    # File 1: 03_system_model.md
    file_03 = "/home/imnyj/Workspace/paper4/paper/03_system_model.md"
    print(f"Acquiring lock for {file_03}...")
    if not lm.acquire(file_03, agent_id):
        print(f"Failed to acquire lock for {file_03}")
        return False
    
    with open(file_03, 'r', encoding='utf-8') as f:
        orig_03 = f.read()
    
    rev_03 = update_03_system_model(orig_03)
    with open(file_03, 'w', encoding='utf-8') as f:
        f.write(rev_03)
    
    lm.release(file_03, agent_id)
    logger.log_action(agent_id, "MODIFY", file_03, "Reviewer 2 피드백 반영: Table III-1 렌더링 수정, 수식 표기 통일, 과장 표현 교정, 단락 최소 5문장 보강", "orchestrator_1")
    print(f"Successfully updated and logged {file_03}")

    # File 2: paper4_draft_korean.md
    file_full = "/home/imnyj/Workspace/paper4/paper/paper4_draft_korean.md"
    print(f"Acquiring lock for {file_full}...")
    if not lm.acquire(file_full, agent_id):
        print(f"Failed to acquire lock for {file_full}")
        return False
    
    rev_full = build_full_paper()
    with open(file_full, 'w', encoding='utf-8') as f:
        f.write(rev_full)
    
    lm.release(file_full, agent_id)
    logger.log_action(agent_id, "MODIFY", file_full, "Reviewer 2 피드백 반영: Table III-1 파이프 분할 복구, Nakagami 수식 수정, 수치 일관성 통일(PDR 73.41%/75.02%, 하드웨어 350K/3.8M MACs/1.2ms), 학술 문체 교정, 단락 5문장 보강, 수식 로만체 통일", "orchestrator_1")
    print(f"Successfully updated and logged {file_full}")

    return True

if __name__ == '__main__':
    success = apply_and_audit()
    assert success, "Apply and audit failed!"
