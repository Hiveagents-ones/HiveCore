from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

from .core.cache import CacheManager
from .core.database import QueryOptimizer

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """基础CRUD类，包含缓存和分页优化"""
    
    def __init__(self, model: Type[ModelType], cache_prefix: str = ""):
        """
        CRUD基类初始化
        
        Args:
            model: SQLAlchemy模型类
            cache_prefix: 缓存键前缀
        """
        self.model = model
        self.cache_prefix = cache_prefix
        self.cache = CacheManager()
        self.default_ttl = 3600  # 默认缓存1小时
    
    async def get(
        self, 
        db: Session, 
        id: Any, 
        use_cache: bool = True
    ) -> Optional[ModelType]:
        """根据ID获取单个记录，支持缓存"""
        cache_key = f"{self.cache_prefix}:{id}" if self.cache_prefix else f"{self.model.__name__}:{id}"
        
        if use_cache:
            cached = await self.cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for {cache_key}")
                return db.query(self.model).get(cached["id"])
        
        try:
            obj = db.query(self.model).get(id)
            if obj and use_cache:
                await self.cache.set(cache_key, {"id": obj.id}, ttl=self.default_ttl)
            return obj
        except SQLAlchemyError as e:
            logger.error(f"Error getting {self.model.__name__} with id {id}: {e}")
            raise HTTPException(status_code=500, detail="Database error")
    
    async def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None
    ) -> List[ModelType]:
        """获取多个记录，支持分页和缓存"""
        cache_key = f"{self.cache_prefix}:multi:{skip}:{limit}" if self.cache_prefix else f"{self.model.__name__}:multi:{skip}:{limit}"
        
        if use_cache:
            cached = await self.cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for {cache_key}")
                return db.query(self.model).filter(self.model.id.in_(cached)).all()
        
        try:
            query = db.query(self.model)
            query = QueryOptimizer.with_pagination(query, page=skip//limit + 1, per_page=limit)
            objects = query.all()
            
            if objects and use_cache:
                ids = [obj.id for obj in objects]
                await self.cache.set(cache_key, ids, ttl=cache_ttl or self.default_ttl)
            
            return objects
        except SQLAlchemyError as e:
            logger.error(f"Error getting multiple {self.model.__name__}: {e}")
            raise HTTPException(status_code=500, detail="Database error")
    
    async def create(
        self, 
        db: Session, 
        *, 
        obj_in: CreateSchemaType,
        invalidate_cache: bool = True
    ) -> ModelType:
        """创建新记录，自动清除相关缓存"""
        try:
            obj_in_data = obj_in.dict()
            db_obj = self.model(**obj_in_data)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            
            if invalidate_cache:
                await self._invalidate_cache_pattern(f"{self.cache_prefix}:*")
            
            logger.info(f"Created {self.model.__name__} with id {db_obj.id}")
            return db_obj
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error creating {self.model.__name__}: {e}")
            raise HTTPException(status_code=500, detail="Database error")
    
    async def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
        invalidate_cache: bool = True
    ) -> ModelType:
        """更新记录，自动清除相关缓存"""
        try:
            if isinstance(obj_in, dict):
                update_data = obj_in
            else:
                update_data = obj_in.dict(exclude_unset=True)
            
            for field, value in update_data.items():
                setattr(db_obj, field, value)
            
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            
            if invalidate_cache:
                cache_key = f"{self.cache_prefix}:{db_obj.id}" if self.cache_prefix else f"{self.model.__name__}:{db_obj.id}"
                await self.cache.delete(cache_key)
                await self._invalidate_cache_pattern(f"{self.cache_prefix}:*")
            
            logger.info(f"Updated {self.model.__name__} with id {db_obj.id}")
            return db_obj
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error updating {self.model.__name__} with id {db_obj.id}: {e}")
            raise HTTPException(status_code=500, detail="Database error")
    
    async def remove(
        self, 
        db: Session, 
        *, 
        id: int,
        invalidate_cache: bool = True
    ) -> ModelType:
        """删除记录，自动清除相关缓存"""
        try:
            obj = db.query(self.model).get(id)
            if not obj:
                raise HTTPException(status_code=404, detail=f"{self.model.__name__} not found")
            
            db.delete(obj)
            db.commit()
            
            if invalidate_cache:
                cache_key = f"{self.cache_prefix}:{id}" if self.cache_prefix else f"{self.model.__name__}:{id}"
                await self.cache.delete(cache_key)
                await self._invalidate_cache_pattern(f"{self.cache_prefix}:*")
            
            logger.info(f"Deleted {self.model.__name__} with id {id}")
            return obj
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error deleting {self.model.__name__} with id {id}: {e}")
            raise HTTPException(status_code=500, detail="Database error")
    
    async def count(
        self,
        db: Session,
        *,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None
    ) -> int:
        """获取记录总数，支持缓存"""
        cache_key = f"{self.cache_prefix}:count" if self.cache_prefix else f"{self.model.__name__}:count"
        
        if use_cache:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached
        
        try:
            count = db.query(self.model).count()
            if use_cache:
                await self.cache.set(cache_key, count, ttl=cache_ttl or self.default_ttl)
            return count
        except SQLAlchemyError as e:
            logger.error(f"Error counting {self.model.__name__}: {e}")
            raise HTTPException(status_code=500, detail="Database error")
    
    async def _invalidate_cache_pattern(self, pattern: str) -> None:
        """清除匹配模式的缓存"""
        try:
            # 这里简化处理，实际应该使用SCAN命令
            # 由于CacheManager没有实现模式删除，这里仅作为示例
            logger.debug(f"Invalidating cache pattern: {pattern}")
        except Exception as e:
            logger.error(f"Error invalidating cache pattern {pattern}: {e}")

class PaymentCRUD(CRUDBase):
    """支付记录专用CRUD类"""
    
    def __init__(self, model: Type[ModelType]):
        super().__init__(model, cache_prefix="payment")
        self.default_ttl = 7200  # 支付记录缓存2小时
    
    async def get_by_member_id(
        self,
        db: Session,
        member_id: int,
        *,
        skip: int = 0,
        limit: int = 100,
        use_cache: bool = True
    ) -> List[ModelType]:
        """根据会员ID获取支付记录"""
        cache_key = f"payment:member:{member_id}:{skip}:{limit}"
        
        if use_cache:
            cached = await self.cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for {cache_key}")
                return db.query(self.model).filter(self.model.id.in_(cached)).all()
        
        try:
            query = db.query(self.model).filter(self.model.member_id == member_id)
            query = QueryOptimizer.with_pagination(query, page=skip//limit + 1, per_page=limit)
            objects = query.all()
            
            if objects and use_cache:
                ids = [obj.id for obj in objects]
                await self.cache.set(cache_key, ids, ttl=self.default_ttl)
            
            return objects
        except SQLAlchemyError as e:
            logger.error(f"Error getting payments for member {member_id}: {e}")
            raise HTTPException(status_code=500, detail="Database error")
    
    async def get_pending_payments(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        use_cache: bool = True
    ) -> List[ModelType]:
        """获取待支付记录"""
        cache_key = f"payment:pending:{skip}:{limit}"
        
        if use_cache:
            cached = await self.cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for {cache_key}")
                return db.query(self.model).filter(self.model.id.in_(cached)).all()
        
        try:
            query = db.query(self.model).filter(self.model.status == "pending")
            query = QueryOptimizer.with_pagination(query, page=skip//limit + 1, per_page=limit)
            objects = query.all()
            
            if objects and use_cache:
                ids = [obj.id for obj in objects]
                await self.cache.set(cache_key, ids, ttl=600)  # 待支付记录缓存10分钟
            
            return objects
        except SQLAlchemyError as e:
            logger.error(f"Error getting pending payments: {e}")
            raise HTTPException(status_code=500, detail="Database error")

class MembershipCRUD(CRUDBase):
    """会员记录专用CRUD类"""
    
    def __init__(self, model: Type[ModelType]):
        super().__init__(model, cache_prefix="membership")
        self.default_ttl = 3600  # 会员记录缓存1小时
    
    async def get_expiring_soon(
        self,
        db: Session,
        days: int = 30,
        *,
        skip: int = 0,
        limit: int = 100,
        use_cache: bool = True
    ) -> List[ModelType]:
        """获取即将到期的会员"""
        cache_key = f"membership:expiring:{days}:{skip}:{limit}"
        
        if use_cache:
            cached = await self.cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for {cache_key}")
                return db.query(self.model).filter(self.model.id.in_(cached)).all()
        
        try:
            from datetime import datetime, timedelta
            expiry_date = datetime.now() + timedelta(days=days)
            query = db.query(self.model).filter(
                self.model.expiry_date <= expiry_date,
                self.model.expiry_date >= datetime.now()
            )
            query = QueryOptimizer.with_pagination(query, page=skip//limit + 1, per_page=limit)
            objects = query.all()
            
            if objects and use_cache:
                ids = [obj.id for obj in objects]
                await self.cache.set(cache_key, ids, ttl=1800)  # 即将到期记录缓存30分钟
            
            return objects
        except SQLAlchemyError as e:
            logger.error(f"Error getting expiring memberships: {e}")
            raise HTTPException(status_code=500, detail="Database error")
    
    async def get_by_member_number(
        self,
        db: Session,
        member_number: str,
        use_cache: bool = True
    ) -> Optional[ModelType]:
        """根据会员编号获取会员信息"""
        cache_key = f"membership:number:{member_number}"
        
        if use_cache:
            cached = await self.cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for {cache_key}")
                return db.query(self.model).get(cached["id"])
        
        try:
            obj = db.query(self.model).filter(self.model.member_number == member_number).first()
            if obj and use_cache:
                await self.cache.set(cache_key, {"id": obj.id}, ttl=self.default_ttl)
            return obj
        except SQLAlchemyError as e:
            logger.error(f"Error getting membership by number {member_number}: {e}")
            raise HTTPException(status_code=500, detail="Database error")
