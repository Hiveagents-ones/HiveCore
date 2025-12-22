from fastapi import APIRouter, Depends, HTTPException
from fastapi import status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from ..database import get_db, Member
from ..middleware.security import JWTBearer, check_permissions
from fastapi import BackgroundTasks
from fastapi import Request
import json
import redis
import aiokafka

router = APIRouter(
    dependencies=[Depends(JWTBearer())],
    prefix="/api/v1/members",
    tags=["members"],
    responses={
        404: {"description": "Member not found"},
        400: {"description": "Invalid request"},
        409: {"description": "Conflict with existing data"}
    },
)

@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED, summary="Create new member", dependencies=[Depends(check_permissions(['members:create']))])
# Cache key format for member data
_MEMBER_CACHE_KEY = "member:{member_id}"
_MEMBERS_LIST_CACHE_KEY = "members:list"
def create_member(
    background_tasks: BackgroundTasks,
    name: str,
    phone: str,
    email: str,
    db: Session = Depends(get_db)
):
    """
    注册新会员
    """
    # 检查手机号或邮箱是否已存在
    existing_member = db.query(Member).filter(
        (Member.phone == phone) | (Member.email == email)
    ).first()
    
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone or email already registered"
        )
    
    new_member = Member(
        name=name,
        phone=phone,
        email=email,
        join_date=datetime.now()
    )
    
    db.add(new_member)
    db.commit()
    db.refresh(new_member)
    
    # Publish member creation event
    background_tasks.add_task(
        publish_member_event,
        event_type="member_created",
        member_id=new_member.id,
        data={
            "name": name,
            "phone": phone,
            "email": email
        }
    )
    
    return {"message": "Member created successfully", "member_id": new_member.id}

@router.get("/", response_model=List[dict], summary="List all members", dependencies=[Depends(check_permissions(['members:read']))])
def get_all_members(db: Session = Depends(get_db)):
    """
    获取所有会员列表
    需要权限: members:read
    """
    """
    获取所有会员列表
    """
    members = db.query(Member).all()
    return [
        {
            "id": member.id,
            "name": member.name,
            "phone": member.phone,
            "email": member.email,
            "join_date": member.join_date
        }
        for member in members
    ]

@router.get("/{member_id}", response_model=dict, summary="Get member details", dependencies=[Depends(check_permissions(['members:read']))])
def get_member(member_id: int, db: Session = Depends(get_db)):
    """
    获取单个会员详细信息
    需要权限: members:read
    """
    """
    获取单个会员详细信息
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    
    if not member:
        raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Member not found"
    )
    
    return {
        "id": member.id,
        "name": member.name,
        "phone": member.phone,
        "email": member.email,
        "join_date": member.join_date
    }

@router.put("/{member_id}", response_model=dict, summary="Update member information", dependencies=[Depends(check_permissions(['members:update']))])
def update_member(
    background_tasks: BackgroundTasks,
    member_id: int,
    name: str = None,
    phone: str = None,
    email: str = None,
    db: Session = Depends(get_db)
):
    """
    更新会员信息
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    if name:
        member.name = name
    if phone:
        # 检查手机号是否已被其他会员使用
        if db.query(Member).filter(Member.phone == phone, Member.id != member_id).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Phone already in use by another member"
            )
        member.phone = phone
    if email:
        # 检查邮箱是否已被其他会员使用
        if db.query(Member).filter(Member.email == email, Member.id != member_id).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already in use by another member"
            )
        member.email = email
    
    db.commit()
    db.refresh(member)
    
    # Publish member update event
    background_tasks.add_task(
        publish_member_event,
        event_type="member_updated",
        member_id=member_id,
        data={
            "name": name,
            "phone": phone,
            "email": email
        }
    )
    
    return {"message": "Member updated successfully"}

@router.delete("/{member_id}", response_model=dict, summary="Delete member", dependencies=[Depends(check_permissions(['members:delete']))])
def delete_member(member_id: int, db: Session = Depends(get_db)):
    """
    注销会员
    需要权限: members:delete
    """
    """
    注销会员
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    db.delete(member)
    db.commit()
    
    return {"message": "Member deleted successfully"}

def get_current_member(request: Request, db: Session = Depends(get_db)) -> Member:
    """
    Dependency to get current member from JWT token
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        Member: The authenticated member
        
    Raises:
        HTTPException: 401 if unauthorized or member not found
    """
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )
    
    try:
        payload = decode_jwt(token.split(" ")[1])
        member_id = payload.get("sub")
        if not member_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
            
        member = db.query(Member).filter(Member.id == member_id).first()
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )
            
        return member
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
# Redis connection pool
redis_pool = redis.ConnectionPool(
    host='localhost', 
    port=6379, 
    db=0,
    decode_responses=True
)

async def publish_member_event(event_type: str, member_id: int, data: dict):
    """
    Publish member events to Kafka and update Redis cache with enhanced real-time sync
    
    Args:
        event_type: Type of member event (member_created|member_updated|member_deleted)
        member_id: ID of the member
        data: Member data dictionary
    """
    """
    Publish member events to Kafka and update Redis cache
    """
    # 1. Update Redis cache
    redis_conn = redis.Redis(connection_pool=redis_pool)
    cache_key = f"member:{member_id}"
    
    if event_type == "member_created" or event_type == "member_updated":
        redis_conn.hset(cache_key, mapping=data)
        redis_conn.expire(cache_key, 3600)  # Cache for 1 hour
    elif event_type == "member_deleted":
        redis_conn.delete(cache_key)
    
    # 2. Publish to Kafka for async processing
    producer = aiokafka.AIOKafkaProducer(
        bootstrap_servers='localhost:9092',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    await producer.start()
    try:
        event = {
            "event_type": event_type,
            "member_id": member_id,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        await producer.send_and_wait("member_events", event)
    finally:
        await producer.stop()