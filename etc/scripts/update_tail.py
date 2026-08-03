file_path = '/home/imnyj/Workspace/House/ui/index.html'

lock = LockManager()
logger = AuditLogger()

if lock.acquire(file_path, "UI_Updater"):
    try:
        with open(file_path, 'w') as f:
            f.write(html_content)
        logger.log_action("UI_Updater", "MODIFY", file_path, "Updated UI to include Total Cash dynamic calculation and 4 Purchase Strategies.")
        print("Successfully updated UI.")
    finally:
        lock.release(file_path, "UI_Updater")
else:
    print("Could not acquire lock.")
