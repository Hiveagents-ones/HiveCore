from fastapi import Request, HTTPException, status
from typing import Callable, Optional, List, Dict, Any
from jose import JWTError, jwt
from app.core.config import settings
from app.models.user import User
from app.models.shop import Shop
from app.core.database import get_db
from sqlalchemy.orm import Session


class RBACMiddleware:
    def __init__(self, required_permissions: Optional[List[str]] = None):
        self.required_permissions = required_permissions or []

    async def __call__(self, request: Request, call_next: Callable):
        # Skip authentication for public endpoints
        if self._is_public_endpoint(request.url.path):
            response = await call_next(request)
            return response

        # Extract and verify JWT token
        token = self._extract_token(request)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            user_id: str = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )

        # Get user from database
        db: Session = next(get_db())
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        # Check permissions
        if self.required_permissions:
            user_permissions = self._get_user_permissions(user)
            if not all(perm in user_permissions for perm in self.required_permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )

        # Add user and shop context to request state
        request.state.user = user
        request.state.shop_id = self._get_user_shop_id(user)

        # Apply data access control for analytics endpoints
        if request.url.path.startswith("/api/analytics"):
            self._apply_data_access_control(request)

        response = await call_next(request)
        return response

    def _is_public_endpoint(self, path: str) -> bool:
        public_paths = [
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
            "/api/auth/login",
            "/api/auth/register",
            "/api/health",
        ]
        return any(path.startswith(p) for p in public_paths)

    def _extract_token(self, request: Request) -> Optional[str]:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                return None
            return token
        except ValueError:
            return None

    def _get_user_permissions(self, user: User) -> List[str]:
        # Get permissions based on user role
        permissions = []
        if user.role == "admin":
            permissions = ["read:all", "write:all", "delete:all"]
        elif user.role == "shop_owner":
            permissions = ["read:shop", "write:shop", "read:analytics"]
        elif user.role == "staff":
            permissions = ["read:shop", "write:bookings"]
        return permissions

    def _get_user_shop_id(self, user: User) -> Optional[str]:
        # Get shop ID for shop owners and staff
        if user.role in ["shop_owner", "staff"]:
            db: Session = next(get_db())
            shop = db.query(Shop).filter(Shop.owner_id == user.id).first()
            if shop:
                return str(shop.id)
        return None

    def _apply_data_access_control(self, request: Request):
        """Apply data access control for analytics endpoints"""
        user = request.state.user
        shop_id = request.state.shop_id

        # Only shop owners can access their shop's analytics
        if user.role == "shop_owner":
            if not shop_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Shop owner must be associated with a shop",
                )
            # Add shop_id filter to query parameters
            query_params = dict(request.query_params)
            query_params["shop_id"] = shop_id
            request._query_params = query_params

        # Admins can access all analytics
        elif user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only shop owners and admins can access analytics",
            )


def rbac(required_permissions: Optional[List[str]] = None):
    """Decorator to apply RBAC middleware to endpoints"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found",
                )
            
            middleware = RBACMiddleware(required_permissions)
            await middleware(request, lambda: None)
            return await func(*args, **kwargs)
        return wrapper
    return decorator