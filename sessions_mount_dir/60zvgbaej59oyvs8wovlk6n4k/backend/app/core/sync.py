import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from ..models.member import Member
from ..schemas.member import MemberCreate, MemberUpdate
from ..core.database import get_db
from ..security import encrypt_data, decrypt_data

logger = logging.getLogger(__name__)

class DataSync:
    """
    数据同步模块，负责与外部业务系统的数据拉取、比对和更新
    """
    
    def __init__(self, db: Session):
        self.db = db
        
    async def fetch_external_members(self) -> List[Dict[str, Any]]:
        """
        从外部系统拉取会员数据
        
        Returns:
            List[Dict]: 外部系统的会员数据列表
        """
        try:
            # 这里模拟从外部API获取数据
            # 实际项目中应该替换为真实的外部API调用
            external_data = [
                {
                    "external_id": "EXT001",
                    "name": "张三",
                    "phone": "13800138001",
                    "card_number": "VIP001",
                    "level": "gold",
                    "remaining_months": 12,
                    "last_updated": "2024-01-15T10:30:00"
                },
                {
                    "external_id": "EXT002",
                    "name": "李四",
                    "phone": "13800138002",
                    "card_number": "VIP002",
                    "level": "silver",
                    "remaining_months": 6,
                    "last_updated": "2024-01-16T14:20:00"
                }
            ]
            logger.info(f"成功从外部系统获取 {len(external_data)} 条会员数据")
            return external_data
        except Exception as e:
            logger.error(f"从外部系统获取数据失败: {str(e)}")
            raise HTTPException(status_code=500, detail="外部数据获取失败")
    
    def compare_data(self, external_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        比较外部数据与本地数据
        
        Args:
            external_data: 外部系统数据
            
        Returns:
            Dict: 包含新增、更新、删除的数据分类
        """
        result = {
            "new": [],
            "update": [],
            "unchanged": []
        }
        
        # 获取本地所有会员数据
        local_members = self.db.query(Member).all()
        local_dict = {member.external_id: member for member in local_members}
        
        for ext_member in external_data:
            external_id = ext_member.get("external_id")
            if not external_id:
                continue
                
            local_member = local_dict.get(external_id)
            
            if not local_member:
                # 新增会员
                result["new"].append(ext_member)
            else:
                # 检查是否需要更新
                if self._needs_update(local_member, ext_member):
                    result["update"].append(ext_member)
                else:
                    result["unchanged"].append(ext_member)
        
        # 检查本地有但外部没有的会员（标记为需要删除）
        result["delete"] = [
            member for member in local_members 
            if member.external_id not in [m.get("external_id") for m in external_data]
        ]
        
        return result
    
    def _needs_update(self, local_member: Member, external_data: Dict[str, Any]) -> bool:
        """
        判断是否需要更新本地数据
        """
        # 比较关键字段
        fields_to_compare = [
            "name", "phone", "card_number", "level", "remaining_months"
        ]
        
        for field in fields_to_compare:
            local_value = getattr(local_member, field)
            external_value = external_data.get(field)
            
            if local_value != external_value:
                return True
        
        return False
    
    async def sync_data(self) -> Dict[str, int]:
        """
        执行完整的数据同步流程
        
        Returns:
            Dict: 同步结果统计
        """
        try:
            # 1. 获取外部数据
            external_data = await self.fetch_external_members()
            
            # 2. 比较数据
            comparison_result = self.compare_data(external_data)
            
            # 3. 执行同步操作
            stats = {
                "created": 0,
                "updated": 0,
                "deleted": 0,
                "unchanged": 0
            }
            
            # 处理新增
            for new_member in comparison_result["new"]:
                # 加密敏感信息
                encrypted_phone = encrypt_data(new_member["phone"])
                encrypted_card_number = encrypt_data(new_member["card_number"])
                
                member_data = MemberCreate(
                    name=new_member["name"],
                    phone=encrypted_phone,
                    card_number=encrypted_card_number,
                    level=new_member["level"],
                    remaining_months=new_member["remaining_months"],
                    external_id=new_member["external_id"]
                )
                db_member = Member(**member_data.dict())
                self.db.add(db_member)
                stats["created"] += 1
            
            # 处理更新
            for update_member in comparison_result["update"]:
                local_member = self.db.query(Member).filter(
                    Member.external_id == update_member["external_id"]
                ).first()
                
                if local_member:
                    # 加密敏感信息
                    encrypted_phone = encrypt_data(update_member["phone"])
                    encrypted_card_number = encrypt_data(update_member["card_number"])
                    
                    update_data = MemberUpdate(
                        name=update_member["name"],
                        phone=encrypted_phone,
                        card_number=encrypted_card_number,
                        level=update_member["level"],
                        remaining_months=update_member["remaining_months"]
                    )
                    
                    for field, value in update_data.dict(exclude_unset=True).items():
                        setattr(local_member, field, value)
                    
                    local_member.updated_at = datetime.utcnow()
                    stats["updated"] += 1
            
            # 处理删除
            for delete_member in comparison_result["delete"]:
                self.db.delete(delete_member)
                stats["deleted"] += 1
            
            # 处理未变更
            stats["unchanged"] = len(comparison_result["unchanged"])
            
            # 提交事务
            self.db.commit()
            
            # 记录同步历史
            await self._log_sync_history(stats)
            
            logger.info(f"数据同步完成: {stats}")
            return stats
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"数据同步失败: {str(e)}")
            raise HTTPException(status_code=500, detail="数据同步失败")
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """
        获取同步状态信息
        
        Returns:
            Dict: 同步状态信息
        """
        try:
            total_members = self.db.query(Member).count()
            last_sync_time = datetime.utcnow().isoformat()
            
            return {
                "total_members": total_members,
                "last_sync_time": last_sync_time,
                "sync_enabled": True
            }
        except Exception as e:
            logger.error(f"获取同步状态失败: {str(e)}")
            raise HTTPException(status_code=500, detail="获取同步状态失败")


# 便捷函数
def get_sync_service(db: Session) -> DataSync:
    """
    获取数据同步服务实例
    """
    return DataSync(db)

    async def _log_sync_history(self, stats: Dict[str, int]) -> None:
        """
        记录同步历史
        """
        try:
            # 这里可以记录到数据库或日志系统
            logger.info(f"同步历史记录: {stats}")
            # 实际项目中可以保存到 sync_history 表
        except Exception as e:
            logger.error(f"记录同步历史失败: {str(e)}")

    async def validate_data_integrity(self) -> Dict[str, Any]:
        """
        验证数据完整性
        """
        try:
            # 检查必要字段
            invalid_members = self.db.query(Member).filter(
                (Member.phone.is_(None)) |
                (Member.card_number.is_(None)) |
                (Member.external_id.is_(None))
            ).count()

            # 检查重复数据
            duplicate_external_ids = self.db.query(Member.external_id).group_by(
                Member.external_id
            ).having(func.count(Member.external_id) > 1).count()

            return {
                "total_members": self.db.query(Member).count(),
                "invalid_members": invalid_members,
                "duplicate_external_ids": duplicate_external_ids,
                "integrity_score": max(0, 100 - invalid_members - duplicate_external_ids * 10)
            }
        except Exception as e:
            logger.error(f"数据完整性验证失败: {str(e)}")
            raise HTTPException(status_code=500, detail="数据完整性验证失败")

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
    def _needs_update(self, local_member: Member, external_data: Dict[str, Any]) -> bool:
        """
        判断是否需要更新本地数据
        """
        # 比较关键字段
        fields_to_compare = [
            "name", "phone", "card_number", "level", "remaining_months"
        ]

        for field in fields_to_compare:
            local_value = getattr(local_member, field)
            external_value = external_data.get(field)

            # 对于加密字段，需要先解密再比较
            if field in ["phone", "card_number"]:
                try:
                    local_value = decrypt_data(local_value)
                except Exception as e:
                    logger.warning(f"解密字段 {field} 失败: {str(e)}")
                    return True

            if local_value != external_value:
                logger.debug(f"字段 {field} 需要更新: 本地={local_value}, 外部={external_value}")
                return True

        # 检查最后更新时间
        try:
            external_last_updated = datetime.fromisoformat(external_data.get("last_updated", ""))
            if external_last_updated > local_member.updated_at:
                logger.debug(f"外部数据更新时间较新: {external_last_updated} > {local_member.updated_at}")
                return True
        except ValueError as e:
            logger.warning(f"解析外部更新时间失败: {str(e)}")
            return True

        return False

# [AUTO-APPENDED] Failed to insert:

            # 记录同步历史
            await self._log_sync_history(stats)

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
    def _needs_update(self, local_member: Member, external_data: Dict[str, Any]) -> bool:
        """
        判断是否需要更新本地数据
        """
        # 比较关键字段
        fields_to_compare = [
            "name", "phone", "card_number", "level", "remaining_months"
        ]

        for field in fields_to_compare:
            local_value = getattr(local_member, field)
            external_value = external_data.get(field)

            # 对于加密字段，需要先解密再比较
            if field in ["phone", "card_number"]:
                try:
                    local_value = decrypt_data(local_value)
                except Exception as e:
                    logger.warning(f"解密字段 {field} 失败: {str(e)}")
                    return True

            if local_value != external_value:
                logger.debug(f"字段 {field} 需要更新: 本地={local_value}, 外部={external_value}")
                return True

        # 检查最后更新时间
        try:
            external_last_updated = datetime.fromisoformat(external_data.get("last_updated", ""))
            if external_last_updated > local_member.updated_at:
                logger.debug(f"外部数据更新时间较新: {external_last_updated} > {local_member.updated_at}")
                return True
        except ValueError as e:
            logger.warning(f"解析外部更新时间失败: {str(e)}")
            return True

        return False

# [AUTO-APPENDED] Failed to insert:
    async def _log_sync_history(self, stats: Dict[str, int]) -> None:
        """
        记录同步历史
        """
        try:
            # 这里可以记录到数据库或日志系统
            logger.info(f"同步历史记录: {stats}")
            # 实际项目中可以保存到 sync_history 表
        except Exception as e:
            logger.error(f"记录同步历史失败: {str(e)}")

    async def validate_data_integrity(self) -> Dict[str, Any]:
        """
        验证数据完整性
        """
        try:
            # 检查必要字段
            invalid_members = self.db.query(Member).filter(
                (Member.phone.is_(None)) |
                (Member.card_number.is_(None)) |
                (Member.external_id.is_(None))
            ).count()

            # 检查重复数据
            duplicate_external_ids = self.db.query(Member.external_id).group_by(
                Member.external_id
            ).having(func.count(Member.external_id) > 1).count()

            return {
                "total_members": self.db.query(Member).count(),
                "invalid_members": invalid_members,
                "duplicate_external_ids": duplicate_external_ids,
                "integrity_score": max(0, 100 - invalid_members - duplicate_external_ids * 10)
            }
        except Exception as e:
            logger.error(f"数据完整性验证失败: {str(e)}")
            raise HTTPException(status_code=500, detail="数据完整性验证失败")

