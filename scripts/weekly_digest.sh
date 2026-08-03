#!/bin/bash
DATE=$(date +%Y-%m-%d)
REPORT="/home/imnyj/reports/${DATE}_weekly_digest.md"
echo "# Weekly Research Digest ($DATE)" > "$REPORT"
echo "## Recent Commits" >> "$REPORT"
git -C /home/imnyj log --oneline -n 5 >> "$REPORT"
echo "" >> "$REPORT"
echo "## Open TODOs" >> "$REPORT"
grep -r "TODO" /home/imnyj/Workspace/paper1/writer/draft >> "$REPORT" || echo "No TODOs found." >> "$REPORT"
echo "Report generated at $REPORT"
