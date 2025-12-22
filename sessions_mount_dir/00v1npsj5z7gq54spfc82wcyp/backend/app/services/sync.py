from typing import Optional, Dict, Any
from datetime import datetime
import json
import logging

from sqlalchemy.orm import Session
import redis
from fastapi import Depends
from fastapi import HTTPException, status

from .database import get_db
from .schemas.member import MemberCreate, MemberUpdate

logger = logging.getLogger(__name__)


class SyncService:
    _version_key_prefix = "sync_version:"
    """
    多端数据同步服务
    负责处理会员数据的跨服务同步和缓存管理
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client or redis.Redis(
            host='localhost', port=6379, db=0, decode_responses=True)

    async def sync_member_to_cache(self, member_id: int, db: Session = Depends(get_db), version: Optional[int] = None) -> bool:
    async def force_sync_member(self, member_id: int, db: Session = Depends(get_db)) -> bool:
    async def sync_member_with_retry(self, member_id: int, db: Session = Depends(get_db), max_retries: int = 3) -> bool:
        """
        带重试机制的会员数据同步

        Args:
            member_id: 会员ID
            db: 数据库会话
            max_retries: 最大重试次数

        Returns:
            bool: 同步是否成功
        """
        for attempt in range(max_retries):
            try:
                version = await self.get_member_version(member_id)
                return await self.sync_member_to_cache(member_id, db, version)
            except HTTPException as e:
                if e.status_code != status.HTTP_409_CONFLICT or attempt == max_retries - 1:
                    raise
                logger.warning(f"Sync conflict for member {member_id}, retrying... (attempt {attempt + 1}/{max_retries})")
                continue
        return False
        """
        强制同步会员数据到缓存，忽略版本冲突
        
        Args:
            member_id: 会员ID
            db: 数据库会话
            
        Returns:
            bool: 同步是否成功
        """
        return await self.sync_member_to_cache(member_id, db, None)
        """
        将会员数据同步到Redis缓存
        
        Args:
            member_id: 会员ID
            db: 数据库会话
            
        Returns:
            bool: 同步是否成功
        """
        try:
            from .routers.members import get_member
            member = get_member(db, member_id)
            if not member:
                return False
            if member.is_deleted:
                await self.invalidate_member_cache(member_id)
                return False
                
            member_data = {
                'id': member.id,
                'name': member.name,
                'phone': member.phone,
                'join_date': member.join_date.isoformat(),
                'membership_type': member.membership_type
            }
            
            self.redis.set(f'member:{member_id}', json.dumps(member_data))
            self.redis.expire(f'member:{member_id}', 3600)  # 缓存1小时
            
            # 更新版本号
            version_key = f"{self._version_key_prefix}member:{member_id}"
            current_version = self.redis.incr(version_key)
            if version is not None and version != current_version - 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Version conflict for member {member_id}. Current version: {current_version - 1}"
                )
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync member {member_id} to cache: {str(e)}")
            return False

    async def get_member_from_cache(self, member_id: int, include_version: bool = False) -> Optional[Dict[str, Any]]:
        """
        从Redis缓存获取会员数据
        
        Args:
            member_id: 会员ID
            
        Returns:
            Optional[Dict]: 会员数据字典，如果不存在则返回None
        """
        try:
            cached_data = self.redis.get(f'member:{member_id}')
            if not cached_data:
                return None
                
            member_data = json.loads(cached_data)
            member_data['join_date'] = datetime.fromisoformat(member_data['join_date'])
            
            if include_version:
                version_key = f"{self._version_key_prefix}member:{member_id}"
                version = self.redis.get(version_key)
                member_data['_version'] = int(version) if version else 0
            return member_data
            
        except Exception as e:
            logger.error(f"Failed to get member {member_id} from cache: {str(e)}")
            return None

    async def invalidate_member_cache(self, member_id: int) -> bool:
        """
        使会员缓存失效
        
        Args:
            member_id: 会员ID
            
        Returns:
            bool: 操作是否成功
        """
        try:
            self.redis.delete(f'member:{member_id}')
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate cache for member {member_id}: {str(e)}")
            return False
    async def get_member_version(self, member_id: int) -> int:
    async def check_member_conflict(self, member_id: int, client_version: int) -> bool:
        """
        检查会员数据版本冲突

        Args:
            member_id: 会员ID
            client_version: 客户端提供的版本号

        Returns:
            bool: True表示有冲突，False表示无冲突
        """
        try:
            if client_version < 0:
                return True

            server_version = await self.get_member_version(member_id)
            if server_version == 0:
                logger.warning(f"Member {member_id} version not found, treating as conflict")
                return True

            return server_version != client_version
        except Exception as e:
            logger.error(f"Failed to check conflict for member {member_id}: {str(e)}")
            return True
    async def check_member_conflict(self, member_id: int, client_version: int) -> bool:
        """
        检查会员数据版本冲突

        Args:
            member_id: 会员ID
            client_version: 客户端提供的版本号

        Returns:
            bool: True表示有冲突，False表示无冲突
        """
        try:
            if client_version < 0:
                return True

            server_version = await self.get_member_version(member_id)
            if server_version == 0:
                logger.warning(f"Member {member_id} version not found, treating as conflict")
                return True

            return server_version != client_version
        except Exception as e:
            logger.error(f"Failed to check conflict for member {member_id}: {str(e)}")
            return True
        """
        获取会员数据的当前版本号

        Args:
            member_id: 会员ID

        Returns:
            int: 当前版本号，如果不存在则返回0
        """
        try:
            version_key = f"{self._version_key_prefix}member:{member_id}"
            version = self.redis.get(version_key)
            return int(version) if version else 0
        except Exception as e:
            logger.error(f"Failed to get version for member {member_id}: {str(e)}")
            return 0

    async def check_member_conflict(self, member_id: int, client_version: int) -> bool:
        """
        检查会员数据版本冲突

        Args:
            member_id: 会员ID
            client_version: 客户端提供的版本号

        Returns:
            bool: True表示有冲突，False表示无冲突
        """
        try:
            if client_version < 0:
                return True

            server_version = await self.get_member_version(member_id)
            if server_version == 0:
                logger.warning(f"Member {member_id} version not found, treating as conflict")
                return True

            return server_version != client_version
        except Exception as e:
            logger.error(f"Failed to check conflict for member {member_id}: {str(e)}")
            return True
    async def check_member_conflict(self, member_id: int, client_version: int) -> bool:
        """
        检查会员数据版本冲突
        
        Args:
            member_id: 会员ID
            client_version: 客户端提供的版本号
            
        Returns:
            bool: True表示有冲突，False表示无冲突
        """
        try:
            server_version = await self.get_member_version(member_id)
            return server_version != client_version
        except Exception as e:
            logger.error(f"Failed to check conflict for member {member_id}: {str(e)}")
            return True
        """
        获取会员数据的当前版本号
        
        Args:
            member_id: 会员ID
            
        Returns:
            int: 当前版本号，如果不存在则返回0
        """
        try:
            version_key = f"{self._version_key_prefix}member:{member_id}"
            version = self.redis.get(version_key)
            return int(version) if version else 0
        except Exception as e:
            logger.error(f"Failed to get version for member {member_id}: {str(e)}")
            return 0

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
    async def check_member_conflict(self, member_id: int, client_version: int) -> bool:
        """
        检查会员数据版本冲突

        Args:
            member_id: 会员ID
            client_version: 客户端提供的版本号

        Returns:
            bool: True表示有冲突，False表示无冲突
        """
        try:
            if client_version < 0:
                return True
                
            server_version = await self.get_member_version(member_id)
            if server_version == 0:
                logger.warning(f"Member {member_id} version not found, treating as conflict")
                return True
                
            return server_version != client_version
        except Exception as e:
            logger.error(f"Failed to check conflict for member {member_id}: {str(e)}")
            return True