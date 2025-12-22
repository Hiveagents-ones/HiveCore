from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from ..models import SystemConfig, SystemAnnouncement, ThirdPartyService
from ..schemas import (
    ConfigCreate,
    ConfigUpdate,
    ConfigResponse,
    ConfigBatchUpdate,
    SystemConfigResponse
)
from ..database import get_db

router = APIRouter(prefix="/api/config", tags=["config"])

@router.get("/", response_model=List[ConfigResponse])
def get_configs(
    is_public: bool = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取系统配置列表"""
    query = db.query(SystemConfig)
    if is_public is not None:
        query = query.filter(SystemConfig.is_public == is_public)
    configs = query.offset(skip).limit(limit).all()
    return configs

@router.get("/{config_id}", response_model=ConfigResponse)
def get_config(config_id: int, db: Session = Depends(get_db)):
    """获取单个配置项"""
    config = db.query(SystemConfig).filter(SystemConfig.id == config_id).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    return config

@router.post("/", response_model=ConfigResponse, status_code=status.HTTP_201_CREATED)
def create_config(config: ConfigCreate, db: Session = Depends(get_db)):
    """创建新的配置项"""
    existing = db.query(SystemConfig).filter(SystemConfig.key == config.key).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configuration key already exists"
        )
    
    db_config = SystemConfig(
        key=config.key,
        value=config.value,
        description=config.description,
        is_public=config.is_public,
        type="string"
    )
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config

@router.put("/{config_id}", response_model=ConfigResponse)
def update_config(
    config_id: int,
    config_update: ConfigUpdate,
    db: Session = Depends(get_db)
):
    """更新配置项"""
    db_config = db.query(SystemConfig).filter(SystemConfig.id == config_id).first()
    if not db_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    
    update_data = config_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_config, field, value)
    
    db.commit()
    db.refresh(db_config)
    return db_config

@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_config(config_id: int, db: Session = Depends(get_db)):
    """删除配置项"""
    db_config = db.query(SystemConfig).filter(SystemConfig.id == config_id).first()
    if not db_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    db.delete(db_config)
    db.commit()
    return None

@router.post("/batch-update", response_model=List[ConfigResponse])
def batch_update_configs(
    batch_update: ConfigBatchUpdate,
    db: Session = Depends(get_db)
):
    """批量更新配置项"""
    updated_configs = []
    
    for key, value in batch_update.configs.items():
        config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        if config:
            config.value = str(value)
            updated_configs.append(config)
        else:
            new_config = SystemConfig(
                key=key,
                value=str(value),
                type="string",
                is_public=False
            )
            db.add(new_config)
            updated_configs.append(new_config)
    
    db.commit()
    for config in updated_configs:
        db.refresh(config)
    
    return updated_configs

@router.get("/system/all", response_model=SystemConfigResponse)
def get_system_config(db: Session = Depends(get_db)):
    """获取系统完整配置"""
    # 获取平台服务费率
    fee_rate_config = db.query(SystemConfig).filter(
        SystemConfig.key == "platform_fee_rate"
    ).first()
    platform_fee_rate = float(fee_rate_config.value) if fee_rate_config else 0.0
    
    # 获取默认头像
    avatar_config = db.query(SystemConfig).filter(
        SystemConfig.key == "default_avatar"
    ).first()
    default_avatar = avatar_config.value if avatar_config else ""
    
    # 获取最新公告
    announcement = db.query(SystemAnnouncement).filter(
        SystemAnnouncement.is_active == True,
        SystemAnnouncement.start_time <= datetime.utcnow(),
        SystemAnnouncement.end_time >= datetime.utcnow()
    ).order_by(SystemAnnouncement.created_at.desc()).first()
    
    # 获取第三方服务密钥
    services = db.query(ThirdPartyService).filter(
        ThirdPartyService.is_active == True
    ).all()
    third_party_keys = {
        service.name: service.api_key or ""
        for service in services
    }
    
    # 获取其他自定义配置
    custom_configs = db.query(SystemConfig).filter(
        SystemConfig.is_public == True
    ).all()
    custom_settings = {
        config.key: config.value
        for config in custom_configs
        if config.key not in ["platform_fee_rate", "default_avatar"]
    }
    
    return SystemConfigResponse(
        platform_fee_rate=platform_fee_rate,
        default_avatar=default_avatar,
        announcement=announcement.content if announcement else None,
        third_party_keys=third_party_keys,
        custom_settings=custom_settings
    )

@router.post("/backup", status_code=status.HTTP_200_OK)
def backup_configs(db: Session = Depends(get_db)):
    """备份系统配置"""
    configs = db.query(SystemConfig).all()
    backup_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "configs": [
            {
                "key": config.key,
                "value": config.value,
                "description": config.description,
                "type": config.type,
                "is_public": config.is_public
            }
            for config in configs
        ]
    }
    return backup_data

@router.post("/restore", status_code=status.HTTP_200_OK)
def restore_configs(backup_data: Dict[str, Any], db: Session = Depends(get_db)):
    """恢复系统配置"""
    if "configs" not in backup_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid backup data format"
        )
    
    for config_data in backup_data["configs"]:
        config = db.query(SystemConfig).filter(
            SystemConfig.key == config_data["key"]
        ).first()
        
        if config:
            config.value = config_data.get("value", "")
            config.description = config_data.get("description", "")
            config.type = config_data.get("type", "string")
            config.is_public = config_data.get("is_public", False)
        else:
            new_config = SystemConfig(
                key=config_data["key"],
                value=config_data.get("value", ""),
                description=config_data.get("description", ""),
                type=config_data.get("type", "string"),
                is_public=config_data.get("is_public", False)
            )
            db.add(new_config)
    
    db.commit()
    return {"message": "Configuration restored successfully"}
