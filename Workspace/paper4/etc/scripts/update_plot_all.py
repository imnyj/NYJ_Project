import sys
import re
sys.path.append('/home/imnyj/Command/core')
from lock_manager import LockManager
from audit_logger import AuditLogger

target_file = '/home/imnyj/Workspace/paper4/visualizer/plot_all.py'
agent_id = 'visualizer'

lm = LockManager()
if lm.acquire(target_file, agent_id):
    with open(target_file, 'r') as f:
        content = f.read()
    
    # Remove plt.title(...) calls
    content = re.sub(r'^[ \t]*plt\.title\(.*?\)\n', '', content, flags=re.MULTILINE)
    
    with open(target_file, 'w') as f:
        f.write(content)
        
    lm.release(target_file, agent_id)
    
    al = AuditLogger()
    al.log_action(agent_id, 'MODIFY', target_file, 'Removed all plt.title calls from plots for academic formatting.', 'parent')
    print("Successfully edited plot_all.py")
else:
    print("Failed to acquire lock")
