from typing import List, Optional, Dict, Tuple, Union, Generator
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.sql.expression import cast
from sqlalchemy import String
import redis
from datetime import datetime, timedelta
import json
from sqlalchemy import extract
import hashlib

from ..database import Member, MemberCard


class MemberQueryService:
    """
    High-performance member query service with caching and optimized database access
    """

    def __init__(self, db: Session, redis_client: Optional[redis.Redis] = None):
        """
        Initialize member query service with database session and optional Redis client
        
        Args:
            db: SQLAlchemy database session
            redis_client: Optional Redis client for distributed caching
        """
        self.db = db
        self.redis = redis_client
        self._member_cache = {}
        self._card_cache = {}
        self._query_cache = {}
        self._cache_ttl = 3600  # 1 hour cache TTL
        self._batch_size = 100  # Batch size for bulk operations

    def get_member_by_id(self, member_id: int) -> Optional[Member]:
        """
        Get member by ID with caching strategy:
        1. Check in-memory cache (LRU)
        2. Check Redis cache (with TTL)
        3. Query database with optimized loading if not found in caches
        """
        cache_key = f"member:{member_id}"
        
        # Check in-memory cache first
        if member_id in self._member_cache:
            return self._member_cache[member_id]
            
        # Check Redis cache if available
        if self.redis:
            cached_data = self.redis.get(cache_key)
            if cached_data:
                member = Member(**json.loads(cached_data))
                self._member_cache[member_id] = member
                return member
        """
        Get member by ID with basic information
        Args:
            member_id: Member ID to query
        Returns:
            Member object if found, None otherwise
        """
        if member_id in self._member_cache:
            return self._member_cache[member_id]
            
        # Database query with optimized loading
        member = self.db.query(Member).options(
            selectinload(Member.cards)
        ).filter(Member.id == member_id).execution_options(
            stream_results=True,
            yield_per=50,
            max_row_buffer=100
        ).first()
        
        if member:
            self._member_cache[member_id] = member
        return member

    def get_member_with_card(self, member_id: int) -> Optional[dict]:
        """
        Get member with their active card information including optimized caching
        
        Args:
            member_id: Member ID to query
            
        Returns:
            Dictionary with member and card info if found, None otherwise
        """
        """
        Get member with their active card information
        Args:
            member_id: Member ID to query
        Returns:
            Dictionary with member and card info if found, None otherwise
        """
        cache_key = f"{member_id}_active_card"
        if cache_key in self._card_cache:
            return self._card_cache[cache_key]
            
        member = self.db.query(Member).options(
            joinedload(Member.cards).filter(MemberCard.status == 'active')
        ).filter(Member.id == member_id).first()

        if member and member.cards:
            result = {
                'member': member,
                'card': member.cards[0]
            }
            self._card_cache[cache_key] = result
            return result
        return None

    def search_members(self, query: str, limit: int = 20, use_cache: bool = True) -> List[Member]:
        """
        Search members by name, phone or email with optimized caching
        Args:
            query: Search termch term
            limit: Maximum number of results to return
            use_cache: Whether to use query cache
        Returns:
            List of matching members
        """
        query = query.strip().lower()
        if not query:
            return []

        # Check query cache if enabled
        cache_key = f"member_search:{hashlib.md5(query.encode()).hexdigest()}"
        if use_cache:
            if query in self._query_cache:
                return self._query_cache[query][:limit]
            if self.redis:
                try:
                    cached = self.redis.get(cache_key)
                    if cached:
                        members = [Member(**m) for m in json.loads(cached)]
                        self._query_cache[query] = members
                        return members[:limit]
                except redis.RedisError:
                    pass

        # Optimized search with index hints
        search_filter = or_(
            cast(Member.name, String).ilike(f'%{query}%'),
            cast(Member.phone, String).ilike(f'%{query}%'),
            cast(Member.email, String).ilike(f'%{query}%')
        )it: Maximum number of results to return
        Returns:
            List of matching members
        """
        query = query.strip()
        # Check query cache if enabled
        if use_cache and query in self._query_cache:
            return self._query_cache[query][:limit]
        if not query:
            return []
            
        # Optimized search with index hints and parallel execution
        search_filter = or_(
            cast(Member.name, String).ilike(f'%{query}%'),
            cast(Member.phone, String).ilike(f'%{query}%'),
            cast(Member.email, String).ilike(f'%{query}%')
        )
        
        results = self.db.query(Member).options(
            selectinload(Member.cards)
        ).filter(search_filter).execution_options(
            stream_results=True,
            max_row_buffer=100,
            yield_per=50
        ).limit(limit).all()
        
        # Cache results if Redis is available
        if self.redis and results:
            serialized = [{
                'id': m.id,
                'name': m.name,
                'phone': m.phone,
                'email': m.email,
                'join_date': m.join_date.isoformat(),
                'is_active': m.is_active
            } for m in results]
            self.redis.setex(cache_key, 300, json.dumps(serialized))  # 5 minute cache for searches
        
        return results

    def get_active_members(self, join_date_from: Optional[date] = None, 
                          join_date_to: Optional[date] = None) -> List[Member]:
        """
        Get all active members with optional date range filtering
        Args:
            join_date_from: Optional start date for filtering
            join_date_to: Optional end date for filtering
        Returns:
            List of active members
        """
        query = self.db.query(Member).filter(Member.is_active == True)
        
        if join_date_from:
            query = query.filter(Member.join_date >= join_date_from)
        if join_date_to:
            query = query.filter(Member.join_date <= join_date_to)
            
        return query.order_by(Member.join_date.desc()).all()

    def get_members_with_expiring_cards(self, days_threshold: int = 30) -> List[dict]:
        """
        Get members with cards expiring within specified days threshold
        
        Args:
            days_threshold: Number of days to look ahead for expiring cards (default: 30)
            
        Returns:
            List of dictionaries containing member and card info
        """
        """
        Get members with cards expiring within the specified days
        Args:
            days_threshold: Number of days to look ahead for expiring cards
        Returns:
            List of dictionaries with member and card info
        """
        from datetime import timedelta
        from sqlalchemy import func
        
        expiry_date = func.current_date() + timedelta(days=days_threshold)
        
        results = self.db.query(Member, MemberCard).\
            join(MemberCard, Member.id == MemberCard.member_id).\
            filter(and_(
                MemberCard.status == 'active',
                MemberCard.expiry_date <= expiry_date,
                MemberCard.expiry_date >= func.current_date()
            )).all()
        
        return [{'member': m, 'card': c} for m, c in results]

    def get_member_count_by_status(self) -> dict:
        """
        Get count of members grouped by active/inactive status
        
        Returns:
            Dictionary with 'active' and 'inactive' counts
        """
        """
        Get count of members grouped by active/inactive status
        Returns:
            Dictionary with active and inactive counts
        """
        from sqlalchemy import func
        
        result = self.db.query(
            Member.is_active,
            func.count(Member.id)
        ).group_by(Member.is_active).all()
        
        return {
            'active': next((count for active, count in result if active), 0),
            'inactive': next((count for active, count in result if not active), 0)
        }
    def get_members_by_card_status(self, status: str) -> List[Member]:
        """
        Get members filtered by card status
        
        Args:
            status: Card status to filter by (e.g. 'active', 'expired')
            
        Returns:
            List of Member objects with matching card status
        """
        """
        Get members by their card status
        Args:
            status: Card status to filter by (e.g. 'active', 'expired')
        Returns:
            List of members with matching card status
        """
        return self.db.query(Member).options(
            joinedload(Member.cards)
        ).join(MemberCard).filter(
            MemberCard.status == status
        ).all()

    def get_members_with_multiple_cards(self) -> List[dict]:
        """
        Get members who have multiple active cards
        
        Returns:
            List of dictionaries containing member and card count info
        """
        """
        Get members who have multiple active cards
        Returns:
            List of dictionaries with member and card count info
        """
        from sqlalchemy import func

        subquery = self.db.query(
            MemberCard.member_id,
            func.count(MemberCard.id).label('card_count')
        ).filter(
            MemberCard.status == 'active'
        ).group_by(
            MemberCard.member_id
        ).having(
            func.count(MemberCard.id) > 1
        ).subquery()

        results = self.db.query(
            Member,
            subquery.c.card_count
        ).join(
            subquery, Member.id == subquery.c.member_id
        ).all()

        return [{'member': m, 'card_count': c} for m, c in results]
    def clear_cache(self, member_id: Optional[int] = None) -> None:
        """
        Clear cached member data from all cache layers
        Args:
            member_id: Specific member ID to clear, or None to clear all
        """
        """
        Clear cached member data
        
        Args:
            member_id: Specific member ID to clear, or None to clear all caches
        """
    def get_members_by_ids(self, member_ids: List[int]) -> Dict[int, Optional[Member]]:
        """
        Batch get members by IDs with optimized caching and database access
        Args:
            member_ids: List of member IDs to query
        Returns:
            Dictionary mapping member IDs to Member objects (None if not found)
        """
        if not member_ids:
            return {}
            
        result = {}
        remaining_ids = set()
        
        # Check in-memory cache first
        for member_id in member_ids:
            if member_id in self._member_cache:
                result[member_id] = self._member_cache[member_id]
            else:
                remaining_ids.add(member_id)
                
        if not remaining_ids:
            return result
            
        # Check Redis cache if available
        if self.redis:
            try:
                cache_keys = [f"member:{member_id}" for member_id in remaining_ids]
                cached_data = self.redis.mget(cache_keys)
                
                for member_id, data in zip(remaining_ids, cached_data):
                    if data:
                        member = Member(**json.loads(data))
                        self._member_cache[member_id] = member
                        result[member_id] = member
                        remaining_ids.remove(member_id)
            except redis.RedisError:
                pass
                
        if not remaining_ids:
            return result
            
        # Batch query from database
        members = self.db.query(Member).options(
            selectinload(Member.cards)
        ).filter(Member.id.in_(remaining_ids)).execution_options(
            stream_results=True,
            yield_per=self._batch_size,
            max_row_buffer=self._batch_size * 2
        ).all()
        
        # Update caches and build result
        for member in members:
            result[member.id] = member
            self._member_cache[member.id] = member
            
            if self.redis:
                try:
                    self.redis.setex(
                        f"member:{member.id}",
                        self._cache_ttl,
                        json.dumps(member.to_dict())
                    )
                except redis.RedisError:
                    pass
        
        # Set None for not found members
        for member_id in remaining_ids:
            if member_id not in result:
                result[member_id] = None
                
        return result
        """
        Clear cached member data
        Args:
            member_id: Specific member ID to clear, or None to clear all
        """
        if member_id:
            # Clear specific member cache
            self._member_cache.pop(member_id, None)
            if self.redis:
                self.redis.delete(f"member:{member_id}")
        else:
            # Clear all caches
            self._member_cache.clear()
            self._card_cache.clear()
            self._query_cache.clear()
            if self.redis:
                self.redis.flushdb()
                
    def get_members_by_birthday(self, month: int, day: int) -> List[Member]:
        """
        Get members whose birthday matches specified month and day
        
        Args:
            month: Birth month (1-12)
            day: Birth day (1-31)
            
        Returns:
            List of matching Member objects
        """
        """
        Get members whose birthday matches the specified month and day
        Args:
            month: Birth month (1-12)
            day: Birth day (1-31)
        Returns:
            List of matching members
        """
        return self.db.query(Member).filter(
            and_(
                extract('month', Member.birth_date) == month,
                extract('day', Member.birth_date) == day
            )
        ).all()
        
    def get_member_stats(self) -> Dict[str, Union[int, float]]:
        """
        Get aggregated member statistics
        
        Returns:
            Dictionary containing various member statistics including:
            - total_members
            - active_members
            - inactive_members
            - avg_membership_days
            - new_members_today
        """
        """
        Get aggregated member statistics
        Returns:
            Dictionary with various member statistics
        """
        from sqlalchemy import func, extract
        
        # Get counts
        total_members = self.db.query(func.count(Member.id)).scalar()
        active_members = self.db.query(func.count(Member.id)).filter(Member.is_active == True).scalar()
        
        # Get average membership duration
        avg_duration = self.db.query(
            func.avg(func.current_date() - Member.join_date)
        ).scalar()
        
        return {
            'total_members': total_members,
            'active_members': active_members,
            'inactive_members': total_members - active_members,
            'avg_membership_days': avg_duration.days if avg_duration else 0,
            'new_members_today': self.db.query(func.count(Member.id))
                .filter(func.date(Member.join_date) == func.current_date())
                .scalar() or 0
        }

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
    def get_member_by_id(self, member_id: int) -> Optional[Member]:
        """
        Get member by ID with optimized caching strategy:
        1. Check in-memory LRU cache
        2. Check Redis cache with TTL
        3. Query database with optimized loading if not found
        
        Args:
            member_id: Member ID to query
        Returns:
            Member object if found, None otherwise
        """
        cache_key = f"member:{member_id}"

        # Check in-memory cache first (fastest)
        if member_id in self._member_cache:
            return self._member_cache[member_id]

        # Check Redis cache if available
        if self.redis:
            try:
                cached_data = self.redis.get(cache_key)
                if cached_data:
                    member = Member(**json.loads(cached_data))
                    self._member_cache[member_id] = member
                    return member
            except redis.RedisError:
                pass  # Fall through to DB query

        # Database query with optimized loading
        member = self.db.query(Member).options(
            selectinload(Member.cards)
        ).filter(Member.id == member_id).execution_options(
            stream_results=True,
            yield_per=self._batch_size,
            max_row_buffer=self._batch_size * 2
        ).first()

        if member:
            self._member_cache[member_id] = member
            if self.redis:
                try:
                    self.redis.setex(
                        cache_key,
                        self._cache_ttl,
                        json.dumps(member.to_dict())
                    )
                except redis.RedisError:
                    pass
        return member

# [AUTO-APPENDED] Failed to replace, adding new code:
    def search_members(self, query: str, limit: int = 20, use_cache: bool = True) -> List[Member]:
        """
        Search members by name, phone or email with optimized caching
        Args:
            query: Search term
            limit: Maximum number of results to return
            use_cache: Whether to use query cache
        Returns:
            List of matching members
        """
        query = query.strip().lower()
        if not query:
            return []

        # Check query cache if enabled
        cache_key = f"member_search:{hashlib.md5(query.encode()).hexdigest()}"
        if use_cache:
            if query in self._query_cache:
                return self._query_cache[query][:limit]
            if self.redis:
                try:
                    cached = self.redis.get(cache_key)
                    if cached:
                        members = [Member(**m) for m in json.loads(cached)]
                        self._query_cache[query] = members
                        return members[:limit]
                except redis.RedisError:
                    pass

        # Optimized search with index hints
        search_filter = or_(
            cast(Member.name, String).ilike(f'%{query}%'),
            cast(Member.phone, String).ilike(f'%{query}%'),
            cast(Member.email, String).ilike(f'%{query}%')
        )

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
    def get_member_by_id(self, member_id: int) -> Optional[Member]:
        """
        Get member by ID with multi-level caching strategy:
        1. Check in-memory LRU cache (fastest)
        2. Check Redis cache with TTL (distributed)
        3. Query database with optimized loading if not found

        Args:
            member_id: Member ID to query
        Returns:
            Member object if found, None otherwise
        """
        cache_key = f"member:{member_id}"

        # Check in-memory cache first (fastest)
        if member_id in self._member_cache:
            return self._member_cache[member_id]

        # Check Redis cache if available
        if self.redis:
            try:
                cached_data = self.redis.get(cache_key)
                if cached_data:
                    member = Member(**json.loads(cached_data))
                    self._member_cache[member_id] = member
                    return member
            except redis.RedisError:
                pass  # Fall through to DB query

        # Database query with optimized loading
        member = self.db.query(Member).options(
            selectinload(Member.cards)
        ).filter(Member.id == member_id).execution_options(
            stream_results=True,
            yield_per=self._batch_size,
            max_row_buffer=self._batch_size * 2
        ).first()

        if member:
            self._member_cache[member_id] = member
            if self.redis:
                try:
                    self.redis.setex(
                        cache_key,
                        self._cache_ttl,
                        json.dumps(member.to_dict())
                    )
                except redis.RedisError:
                    pass
        return member