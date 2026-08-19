import os
import time
import shutil

class LockManager:
    def __init__(self, lock_dir="/tmp/agent_locks", backup_dir="/tmp/agent_backups"):
        self.lock_dir = lock_dir
        self.backup_dir = backup_dir
        os.makedirs(self.lock_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)

    def _get_lock_path(self, filepath):
        safe_name = os.path.abspath(filepath).replace('/', '_') + '.lock'
        return os.path.join(self.lock_dir, safe_name)

    def acquire(self, filepath, agent_id, timeout=300):
        lock_path = self._get_lock_path(filepath)
        start_time = time.time()
        
        while True:
            try:
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, 'w') as f:
                    f.write(agent_id)
                
                # Take snapshot
                if os.path.exists(filepath):
                    abs_filepath = os.path.abspath(filepath)
                    backup_dir = self.backup_dir
                    if "/Workspace/" in abs_filepath:
                        parts = abs_filepath.split('/')
                        try:
                            ws_idx = parts.index("Workspace")
                            if ws_idx + 1 < len(parts):
                                agent_dir = '/'.join(parts[:ws_idx+2])
                                backup_dir = os.path.join(agent_dir, "backup")
                        except ValueError:
                            pass
                    os.makedirs(backup_dir, exist_ok=True)
                    backup_path = os.path.join(backup_dir, f"{os.path.basename(filepath)}.{int(time.time())}.bak")
                    shutil.copy2(filepath, backup_path)
                return True
                
            except FileExistsError:
                if time.time() - start_time > timeout:
                    print(f"[{agent_id}] Timeout waiting for lock on {filepath}")
                    return False
                time.sleep(2)

    def release(self, filepath, agent_id):
        lock_path = self._get_lock_path(filepath)
        try:
            with open(lock_path, 'r') as f:
                current_owner = f.read().strip()
            
            if current_owner == agent_id:
                os.remove(lock_path)
                return True
            else:
                print(f"[{agent_id}] Cannot release lock owned by {current_owner}")
                return False
        except FileNotFoundError:
            return True

if __name__ == "__main__":
    import sys
    lm = LockManager()
    if len(sys.argv) >= 4 and sys.argv[1] == "acquire":
        target = sys.argv[2]
        agent = sys.argv[3]
        if lm.acquire(target, agent):
            print(f"[{agent}] Lock acquired on {target}")
            sys.exit(0)
        else:
            print(f"[{agent}] Failed to acquire lock on {target}")
            sys.exit(1)
    elif len(sys.argv) >= 4 and sys.argv[1] == "release":
        target = sys.argv[2]
        agent = sys.argv[3]
        if lm.release(target, agent):
            print(f"[{agent}] Lock released on {target}")
            sys.exit(0)
        else:
            print(f"[{agent}] Failed to release lock on {target}")
            sys.exit(1)
    else:
        if lm.acquire("test.txt", "worker_1"):
            print("Locked. Working...")
            time.sleep(1)
            lm.release("test.txt", "worker_1")
            print("Unlocked.")
