# -*- coding: utf-8 -*-
import json, sys, os
sys.path.insert(0, "/home/imnyj/Command/core")
from lock_manager import LockManager
from audit_logger import AuditLogger

AGENT = "p2-librarian"
OUT = "/home/imnyj/Workspace/paper2/librarian"
lm, al = LockManager(), AuditLogger()
recs = json.load(open(os.path.join(OUT, "related_works.json")))
exec(open("/home/imnyj/.claude/jobs/894c9408/tmp/md_body.py").read().split("lm, al =")[0])
