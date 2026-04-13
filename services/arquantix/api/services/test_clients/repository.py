"""Repository for app_runtime_settings table."""
from typing import Any, Optional

from sqlalchemy.orm import Session

from .models import AppRuntimeSetting


class RuntimeSettingsRepository:

    @staticmethod
    def get_by_key(db: Session, key: str) -> Optional[AppRuntimeSetting]:
        return db.query(AppRuntimeSetting).filter(AppRuntimeSetting.key == key).first()

    @staticmethod
    def upsert(db: Session, key: str, value: Optional[str], metadata_: Optional[dict[str, Any]] = None) -> AppRuntimeSetting:
        existing = db.query(AppRuntimeSetting).filter(AppRuntimeSetting.key == key).first()
        if existing:
            existing.value = value
            if metadata_ is not None:
                existing.metadata_ = metadata_
            db.flush()
            return existing
        setting = AppRuntimeSetting(key=key, value=value, metadata_=metadata_ or {})
        db.add(setting)
        db.flush()
        return setting
