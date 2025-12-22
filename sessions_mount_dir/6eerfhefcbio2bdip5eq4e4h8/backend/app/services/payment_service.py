import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_

from ..core.cache import CacheManager
from ..core.database import get_db
from ..models.payment import Payment, PaymentStatus, PaymentMethod
from ..models.member import Member
from ..core.config import settings

logger = logging.getLogger(__name__)

class PaymentService:
    """支付服务，处理会员缴费和支付记录"""
    
    def __init__(self):
        self.cache = CacheManager()
        self.cache_key_prefix = "payment:"
        self.member_cache_prefix = "member:"
        
    async def create_payment(
        self,
        member_id: int,
        amount: float,
        method: PaymentMethod,
        description: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Payment:
        """创建支付记录"""
        if not db:
            db = next(get_db())
            
        try:
            # 创建支付记录
            payment = Payment(
                member_id=member_id,
                amount=amount,
                method=method,
                status=PaymentStatus.PENDING,
                description=description,
                created_at=datetime.utcnow()
            )
            
            db.add(payment)
            await db.commit()
            await db.refresh(payment)
            
            # 缓存支付记录
            cache_key = f"{self.cache_key_prefix}{payment.id}"
            await self.cache.set(cache_key, payment.to_dict(), ttl=3600)
            
            # 清除会员相关缓存
            await self._clear_member_cache(member_id)
            
            logger.info(f"创建支付记录成功: {payment.id}")
            return payment
            
        except Exception as e:
            await db.rollback()
            logger.error(f"创建支付记录失败: {e}")
            raise
            
    async def update_payment_status(
        self,
        payment_id: int,
        status: PaymentStatus,
        transaction_id: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Optional[Payment]:
        """更新支付状态"""
        if not db:
            db = next(get_db())
            
        try:
            # 更新数据库
            stmt = (
                update(Payment)
                .where(Payment.id == payment_id)
                .values(
                    status=status,
                    transaction_id=transaction_id,
                    updated_at=datetime.utcnow()
                )
                .returning(Payment)
            )
            
            result = await db.execute(stmt)
            payment = result.scalar_one_or_none()
            
            if payment:
                await db.commit()
                
                # 更新缓存
                cache_key = f"{self.cache_key_prefix}{payment_id}"
                payment_data = payment.to_dict()
                await self.cache.set(cache_key, payment_data, ttl=3600)
                
                # 如果支付成功，更新会员状态
                if status == PaymentStatus.SUCCESS:
                    await self._update_member_membership(payment.member_id, db)
                    
                # 清除会员相关缓存
                await self._clear_member_cache(payment.member_id)
                
                logger.info(f"更新支付状态成功: {payment_id} -> {status}")
                return payment
            else:
                logger.warning(f"支付记录不存在: {payment_id}")
                return None
                
        except Exception as e:
            await db.rollback()
            logger.error(f"更新支付状态失败: {e}")
            raise
            
    async def get_payment(
        self,
        payment_id: int,
        db: Optional[AsyncSession] = None
    ) -> Optional[Payment]:
        """获取支付记录"""
        # 先从缓存获取
        cache_key = f"{self.cache_key_prefix}{payment_id}"
        cached_data = await self.cache.get(cache_key)
        
        if cached_data:
            return Payment.from_dict(cached_data)
            
        # 缓存未命中，从数据库获取
        if not db:
            db = next(get_db())
            
        try:
            stmt = select(Payment).where(Payment.id == payment_id)
            result = await db.execute(stmt)
            payment = result.scalar_one_or_none()
            
            if payment:
                # 缓存结果
                await self.cache.set(cache_key, payment.to_dict(), ttl=3600)
                
            return payment
            
        except Exception as e:
            logger.error(f"获取支付记录失败: {e}")
            return None
            
    async def get_member_payments(
        self,
        member_id: int,
        limit: int = 50,
        offset: int = 0,
        db: Optional[AsyncSession] = None
    ) -> List[Payment]:
        """获取会员支付历史"""
        # 检查缓存
        cache_key = f"{self.member_cache_prefix}{member_id}:payments:{limit}:{offset}"
        cached_data = await self.cache.get(cache_key)
        
        if cached_data:
            return [Payment.from_dict(p) for p in cached_data]
            
        # 从数据库获取
        if not db:
            db = next(get_db())
            
        try:
            stmt = (
                select(Payment)
                .where(Payment.member_id == member_id)
                .order_by(Payment.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            
            result = await db.execute(stmt)
            payments = result.scalars().all()
            
            # 缓存结果
            payments_data = [p.to_dict() for p in payments]
            await self.cache.set(cache_key, payments_data, ttl=1800)
            
            return list(payments)
            
        except Exception as e:
            logger.error(f"获取会员支付历史失败: {e}")
            return []
            
    async def get_expiring_members(
        self,
        days: int = 30,
        db: Optional[AsyncSession] = None
    ) -> List[Member]:
        """获取即将到期的会员"""
        if not db:
            db = next(get_db())
            
        try:
            expiry_date = datetime.utcnow() + timedelta(days=days)
            
            stmt = (
                select(Member)
                .where(
                    and_(
                        Member.membership_end <= expiry_date,
                        Member.membership_end > datetime.utcnow(),
                        Member.is_active == True
                    )
                )
                .order_by(Member.membership_end.asc())
            )
            
            result = await db.execute(stmt)
            members = result.scalars().all()
            
            return list(members)
            
        except Exception as e:
            logger.error(f"获取即将到期会员失败: {e}")
            return []
            
    async def _update_member_membership(
        self,
        member_id: int,
        db: AsyncSession
    ) -> None:
        """更新会员会籍状态"""
        try:
            # 获取会员信息
            stmt = select(Member).where(Member.id == member_id)
            result = await db.execute(stmt)
            member = result.scalar_one_or_none()
            
            if member:
                # 延长会籍时间（假设支付金额对应一个月）
                if member.membership_end:
                    member.membership_end += timedelta(days=30)
                else:
                    member.membership_end = datetime.utcnow() + timedelta(days=30)
                    
                member.is_active = True
                member.updated_at = datetime.utcnow()
                
                await db.commit()
                logger.info(f"更新会员会籍成功: {member_id}")
                
        except Exception as e:
            logger.error(f"更新会员会籍失败: {e}")
            raise
            
    async def _clear_member_cache(self, member_id: int) -> None:
        """清除会员相关缓存"""
        try:
            # 清除支付历史缓存
            pattern = f"{self.member_cache_prefix}{member_id}:payments:*"
            # 这里简化处理，实际应该使用SCAN命令
            await self.cache.delete(f"{self.member_cache_prefix}{member_id}:payments:50:0")
            
        except Exception as e:
            logger.error(f"清除会员缓存失败: {e}")
            
    async def get_payment_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Union[int, float]]:
        """获取支付统计数据"""
        if not db:
            db = next(get_db())
            
        try:
            # 默认查询最近30天
            if not start_date:
                start_date = datetime.utcnow() - timedelta(days=30)
            if not end_date:
                end_date = datetime.utcnow()
                
            # 检查缓存
            cache_key = f"payment_stats:{start_date.date()}:{end_date.date()}"
            cached_stats = await self.cache.get(cache_key)
            
            if cached_stats:
                return cached_stats
                
            # 查询数据库
            stmt = select(Payment).where(
                and_(
                    Payment.created_at >= start_date,
                    Payment.created_at <= end_date
                )
            )
            
            result = await db.execute(stmt)
            payments = result.scalars().all()
            
            # 计算统计数据
            total_count = len(payments)
            total_amount = sum(p.amount for p in payments)
            success_count = sum(1 for p in payments if p.status == PaymentStatus.SUCCESS)
            success_amount = sum(p.amount for p in payments if p.status == PaymentStatus.SUCCESS)
            
            stats = {
                "total_count": total_count,
                "total_amount": float(total_amount),
                "success_count": success_count,
                "success_amount": float(success_amount),
                "success_rate": float(success_count / total_count * 100) if total_count > 0 else 0.0
            }
            
            # 缓存结果
            await self.cache.set(cache_key, stats, ttl=3600)
            
            return stats
            
        except Exception as e:
            logger.error(f"获取支付统计失败: {e}")
            return {}
            
    async def batch_update_payment_status(
        self,
        payment_ids: List[int],
        status: PaymentStatus,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, int]:
        """批量更新支付状态"""
        if not db:
            db = next(get_db())
            
        success_count = 0
        failed_count = 0
        
        try:
            for payment_id in payment_ids:
                try:
                    payment = await self.update_payment_status(
                        payment_id=payment_id,
                        status=status,
                        db=db
                    )
                    if payment:
                        success_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    logger.error(f"批量更新支付状态失败 {payment_id}: {e}")
                    failed_count += 1
                    
            return {
                "success": success_count,
                "failed": failed_count,
                "total": len(payment_ids)
            }
            
        except Exception as e:
            logger.error(f"批量更新支付状态失败: {e}")
            raise

# 创建全局支付服务实例
payment_service = PaymentService()
