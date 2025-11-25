from datetime import datetime, timedelta
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from config.settings import settings
from database.db import get_db
from models.user import User

security = HTTPBearer(auto_error=False)

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

active_user = {"username": None, "token": None}

def create_access_token(data: dict):
    global active_user
    username = data.get("sub")
    if active_user["username"] and active_user["username"] != username:
        active_user["username"] = None
        active_user["token"] = None
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    active_user["username"] = username
    active_user["token"] = token
    return token

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except ExpiredSignatureError:
        return {"__expired__": True}
    except JWTError:
        return None

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = credentials.credentials
    if active_user["token"] != token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User logged out or token invalid")
    decoded = decode_access_token(token)
    if decoded is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if isinstance(decoded, dict) and decoded.get("__expired__"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token_expired")
    username = decoded.get("sub")
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user