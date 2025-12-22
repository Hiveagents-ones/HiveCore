from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from ..models import Merchant
from ..schemas import TokenData
from .database import get_db
from .config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def get_current_merchant(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Merchant:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        merchant_id: str = payload.get("sub")
        if merchant_id is None:
            raise credentials_exception
        token_data = TokenData(merchant_id=merchant_id)
    except JWTError:
        raise credentials_exception

    merchant = db.query(Merchant).filter(Merchant.id == token_data.merchant_id).first()
    if merchant is None:
        raise credentials_exception
    return merchant


def get_current_active_merchant(
    current_merchant: Merchant = Depends(get_current_merchant),
) -> Merchant:
    if not current_merchant.is_active:
        raise HTTPException(status_code=400, detail="Inactive merchant")
    return current_merchant


def get_optional_current_merchant(
    token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Optional[Merchant]:
    if token is None:
        return None
    try:
        return get_current_merchant(token, db)
    except HTTPException:
        return None
