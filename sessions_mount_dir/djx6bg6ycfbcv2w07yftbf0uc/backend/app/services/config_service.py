from typing import Any, Dict, List, Optional, Union
import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet
from ..models import SystemConfig, SystemAnnouncement, ThirdPartyService
from ..schemas import ConfigCreate, ConfigUpdate, AnnouncementCreate, AnnouncementUpdate, ThirdPartyServiceCreate, ThirdPartyServiceUpdate

logger = logging.getLogger(__name__)

class ConfigService:
    def __init__(self, db: Session, encryption_key: Optional[str] = None):
        self.db = db
        self.cipher = Fernet(encryption_key.encode()) if encryption_key else None

    def _encrypt(self, value: str) -> str:
        if not self.cipher:
            return value
        return self.cipher.encrypt(value.encode()).decode()

    def _decrypt(self, value: str) -> str:
        if not self.cipher:
            return value
        return self.cipher.decrypt(value.encode()).decode()

    def _validate_config_type(self, value: Any, type_str: str) -> bool:
        try:
            if type_str == "string":
                return isinstance(value, str)
            elif type_str == "int":
                return isinstance(value, int)
            elif type_str == "float":
                return isinstance(value, float)
            elif type_str == "bool":
                return isinstance(value, bool)
            elif type_str == "json":
                json.loads(value) if isinstance(value, str) else json.dumps(value)
                return True
            return False
        except (ValueError, TypeError):
            return False

    def get_config(self, key: str) -> Optional[SystemConfig]:
        config = self.db.query(SystemConfig).filter(SystemConfig.key == key).first()
        if config and config.type == "json" and config.value:
            try:
                config.value = json.loads(config.value)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON for config key: {key}")
        return config

    def get_configs(self, public_only: bool = False) -> List[SystemConfig]:
        query = self.db.query(SystemConfig)
        if public_only:
            query = query.filter(SystemConfig.is_public == True)
        configs = query.all()
        for config in configs:
            if config.type == "json" and config.value:
                try:
                    config.value = json.loads(config.value)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON for config key: {config.key}")
        return configs

    def create_config(self, config_data: ConfigCreate) -> SystemConfig:
        if not self._validate_config_type(config_data.value, config_data.type):
            raise ValueError(f"Invalid value type for config: {config_data.key}")

        value = config_data.value
        if config_data.type == "json":
            value = json.dumps(value)
        elif config_data.type in ["int", "float", "bool"]:
            value = str(value)

        db_config = SystemConfig(
            key=config_data.key,
            value=value,
            description=config_data.description,
            type=config_data.type,
            is_public=config_data.is_public
        )
        self.db.add(db_config)
        self.db.commit()
        self.db.refresh(db_config)
        logger.info(f"Created config: {db_config.key}")
        return db_config

    def update_config(self, key: str, config_data: ConfigUpdate) -> Optional[SystemConfig]:
        db_config = self.get_config(key)
        if not db_config:
            return None

        if config_data.value is not None and not self._validate_config_type(config_data.value, db_config.type):
            raise ValueError(f"Invalid value type for config: {key}")

        update_data = config_data.dict(exclude_unset=True)
        if "value" in update_data:
            value = update_data["value"]
            if db_config.type == "json":
                value = json.dumps(value)
            elif db_config.type in ["int", "float", "bool"]:
                value = str(value)
            update_data["value"] = value

        for field, value in update_data.items():
            setattr(db_config, field, value)

        self.db.commit()
        self.db.refresh(db_config)
        logger.info(f"Updated config: {db_config.key}")
        return db_config

    def delete_config(self, key: str) -> bool:
        db_config = self.get_config(key)
        if not db_config:
            return False
        self.db.delete(db_config)
        self.db.commit()
        logger.info(f"Deleted config: {key}")
        return True

    def get_announcement(self, announcement_id: int) -> Optional[SystemAnnouncement]:
        return self.db.query(SystemAnnouncement).filter(SystemAnnouncement.id == announcement_id).first()

    def get_announcements(self, active_only: bool = False) -> List[SystemAnnouncement]:
        query = self.db.query(SystemAnnouncement)
        if active_only:
            now = datetime.utcnow()
            query = query.filter(
                SystemAnnouncement.is_active == True,
                SystemAnnouncement.start_time <= now,
                SystemAnnouncement.end_time >= now
            )
        return query.all()

    def create_announcement(self, announcement_data: AnnouncementCreate) -> SystemAnnouncement:
        db_announcement = SystemAnnouncement(
            title=announcement_data.title,
            content=announcement_data.content,
            is_active=announcement_data.is_active,
            start_time=announcement_data.start_time,
            end_time=announcement_data.end_time
        )
        self.db.add(db_announcement)
        self.db.commit()
        self.db.refresh(db_announcement)
        logger.info(f"Created announcement: {db_announcement.title}")
        return db_announcement

    def update_announcement(self, announcement_id: int, announcement_data: AnnouncementUpdate) -> Optional[SystemAnnouncement]:
        db_announcement = self.get_announcement(announcement_id)
        if not db_announcement:
            return None

        update_data = announcement_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_announcement, field, value)

        self.db.commit()
        self.db.refresh(db_announcement)
        logger.info(f"Updated announcement: {db_announcement.title}")
        return db_announcement

    def delete_announcement(self, announcement_id: int) -> bool:
        db_announcement = self.get_announcement(announcement_id)
        if not db_announcement:
            return False
        self.db.delete(db_announcement)
        self.db.commit()
        logger.info(f"Deleted announcement: {announcement_id}")
        return True

    def get_third_party_service(self, service_name: str) -> Optional[ThirdPartyService]:
        service = self.db.query(ThirdPartyService).filter(ThirdPartyService.name == service_name).first()
        if service:
            if service.api_key:
                service.api_key = self._decrypt(service.api_key)
            if service.secret_key:
                service.secret_key = self._decrypt(service.secret_key)
        return service

    def get_third_party_services(self, active_only: bool = False) -> List[ThirdPartyService]:
        query = self.db.query(ThirdPartyService)
        if active_only:
            query = query.filter(ThirdPartyService.is_active == True)
        services = query.all()
        for service in services:
            if service.api_key:
                service.api_key = self._decrypt(service.api_key)
            if service.secret_key:
                service.secret_key = self._decrypt(service.secret_key)
        return services

    def create_third_party_service(self, service_data: ThirdPartyServiceCreate) -> ThirdPartyService:
        db_service = ThirdPartyService(
            name=service_data.name,
            api_key=self._encrypt(service_data.api_key) if service_data.api_key else None,
            secret_key=self._encrypt(service_data.secret_key) if service_data.secret_key else None,
            endpoint=service_data.endpoint,
            is_active=service_data.is_active
        )
        self.db.add(db_service)
        self.db.commit()
        self.db.refresh(db_service)
        logger.info(f"Created third-party service: {db_service.name}")
        return db_service

    def update_third_party_service(self, service_name: str, service_data: ThirdPartyServiceUpdate) -> Optional[ThirdPartyService]:
        db_service = self.get_third_party_service(service_name)
        if not db_service:
            return None

        update_data = service_data.dict(exclude_unset=True)
        if "api_key" in update_data and update_data["api_key"]:
            update_data["api_key"] = self._encrypt(update_data["api_key"])
        if "secret_key" in update_data and update_data["secret_key"]:
            update_data["secret_key"] = self._encrypt(update_data["secret_key"])

        for field, value in update_data.items():
            setattr(db_service, field, value)

        self.db.commit()
        self.db.refresh(db_service)
        logger.info(f"Updated third-party service: {db_service.name}")
        return db_service

    def delete_third_party_service(self, service_name: str) -> bool:
        db_service = self.get_third_party_service(service_name)
        if not db_service:
            return False
        self.db.delete(db_service)
        self.db.commit()
        logger.info(f"Deleted third-party service: {service_name}")
        return True
