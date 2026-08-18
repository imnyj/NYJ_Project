# -*- coding: utf-8 -*-
import sys
import os
sys.path.append('/home/imnyj/Command/core')
from lock_manager import LockManager
from audit_logger import AuditLogger

class ProjectFileManager:
    def __init__(self, agent_id='antigravity_manager'):
        self.agent_id = agent_id
        self.lm = LockManager()
        self.logger = AuditLogger()

    def write_file(self, filepath, content, description='Created or modified file'):
        filepath = os.path.abspath(filepath)
        if self.lm.acquire(filepath, self.agent_id):
            try:
                # Ensure parent directories exist
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.logger.log_action(self.agent_id, 'MODIFY' if os.path.exists(filepath) else 'CREATE', filepath, description)
                print(f'[SUCCESS] Written to {filepath}')
            finally:
                self.lm.release(filepath, self.agent_id)
        else:
            print(f'[ERROR] Failed to acquire lock for {filepath}')
