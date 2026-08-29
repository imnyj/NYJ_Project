---
name: auto-backup-and-push
description: "파일 백업 및 5시간 유휴 시 1회성 GitHub 강제 업로드를 수행하는 프로토콜"
---
# Auto-Backup & GitHub Push Protocol

1. **파일 백업 (File Backup)**
   - 더 이상 사용되지 않는 모의(Mock) 코드나 이전 버전의 스크립트, 결과 파일들은 삭제하는 대신 항상 프로젝트 폴더 내 `backup/` 디렉토리로 이동(`mv`)시켜야 한다.

2. **5시간 유휴 강제 푸시 (5-Hour Idle Force Push)**
   - 5시간 타이머 알림을 받으면, `skill-crafter` 등을 활용해 스스로 배운 점을 스킬로 업데이트한다.
   - 모든 로컬 작업 내역을 깃허브에 강제 푸시한다:
     `git add .`
     `git commit -m "Auto-upgrade and backup after 5hr idle"`
     `git push -u origin main --force`
   - 이 작업은 "최초 1회"만 수행되며, 완료 후 타이머는 재생성하지 않는다.
