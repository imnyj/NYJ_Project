import sys
sys.path.append("/home/imnyj/Command/core")
from lock_manager import LockManager
from audit_logger import AuditLogger

target = "/home/imnyj/Workspace/paper2/idea/paper5_migration.md"
addition_path = "/home/imnyj/.claude/jobs/894c9408/tmp/migration_추가절.md"
agent_id = "p2-worker-setup"

lm = LockManager()
al = AuditLogger()

if not lm.acquire(target, agent_id, timeout=30):
    print("LOCK_FAILED")
    sys.exit(1)

try:
    with open(target, "r", encoding="utf-8") as f:
        content = f.read()

    heading = "## 3. 문헌 조사 항목"
    idx = content.index(heading)
    insert_pos = idx + len(heading)
    note = "\n\n이 절의 조사는 2026년 9월 4일 완료되었으며 결과는 /home/imnyj/Workspace/paper2/librarian/ 아래에 있습니다. 확보된 문헌은 34건이고 축별 분포는 UAM 통신 6건, SAGIN 수직 핸드오버 7건, 선제적 예측 5건, 강화학습 핸드오버 10건, 파라미터화 행동 강화학습 6건입니다."
    content = content[:insert_pos] + note + content[insert_pos:]

    with open(addition_path, "r", encoding="utf-8") as f:
        addition = f.read()

    if not content.endswith("\n"):
        content += "\n"
    content = content.rstrip("\n") + "\n" + addition

    with open(target, "w", encoding="utf-8") as f:
        f.write(content)

    al.log_action(agent_id, "MODIFY", target, "paper5_migration.md에 3절 문헌조사 완료 문장 삽입, 4/5/6절(이관 순서/원고 서식/폐기 분류 단서) 추가", "team-lead")
    print("OK")
finally:
    lm.release(target, agent_id)
