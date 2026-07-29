import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from config import settings
from services.cloud_storage import cloud_storage
import os


class AuditService:
    def __init__(self):
        self.use_cloud = cloud_storage.is_cloud_enabled
        if not self.use_cloud:
            self.logger = self._setup_logger()

    def _setup_logger(self):
        os.makedirs(settings.LOG_DIR, exist_ok=True)
        log_file = settings.LOG_DIR / "audit.json"
        logger = logging.getLogger("audit")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = RotatingFileHandler(
                log_file, maxBytes=10 * 1024 * 1024, backupCount=5
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
            logger.addHandler(handler)
        return logger

    def log(self, user: str, action: str, details: dict):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user,
            "action": action,
            "details": details,
        }

        if self.use_cloud:
            cloud_storage.log_audit(user, action, details)
        else:
            self.logger.info(json.dumps(entry))

    def get_recent_logs(self, limit: int = 100) -> list:
        if self.use_cloud:
            return cloud_storage.get_audit_logs(limit)

        # Fallback: read from local file
        log_file = settings.LOG_DIR / "audit.json"
        if not log_file.exists():
            return []

        entries = []
        with open(log_file, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except:
                        continue
        return entries[-limit:]
