from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .security import verify_token

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[str]:
    """
    Dependency to get the current authenticated user.
    
    Args:
        credentials: The HTTP Bearer credentials from the request
        db: The database session
        
    Returns:
        The user ID if authentication is successful
        
    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    user_id = verify_token(token)
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id


async def get_current_active_user(
    current_user: str = Depends(get_current_user)
) -> str:
    """
    Dependency to get the current active user.
    
    Args:
        current_user: The current authenticated user
        
    Returns:
        The user ID if the user is active
        
    Raises:
        HTTPException: If the user is not active
    """
    # In a real application, you would check if the user is active in the database
    # For now, we'll just return the user ID
    return current_user
