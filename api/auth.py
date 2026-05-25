# -*- coding: utf-8 -*-
"""
auth.py - Authentification JWT pour l'API REST

Utilisation :
  - Endpoint POST /auth/login : obtenir un token
  - Header Authorization: Bearer <token> pour les endpoints sécurisés
"""

from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# =====================================================
# CONFIGURATION
# =====================================================

SECRET_KEY = "change_me_in_production"
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60

# Identifiants hardcodés (à remplacer par une vraie base d'utilisateurs)
CREDENTIALS = {
    "admin": "admin"  # username: password
}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# =====================================================
# CREATION DU TOKEN JWT
# =====================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crée un token JWT avec une date d'expiration"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


# =====================================================
# VERIFICATION DU TOKEN JWT
# =====================================================

def get_current_user(token: str = Depends(oauth2_scheme)):
    """Vérifie et décode le token JWT"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")

        if username is None:
            raise credentials_exception

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expiré",
        )
    except jwt.JWTError:
        raise credentials_exception

    return username


# =====================================================
# AUTHENTIFICATION (LOGIN)
# =====================================================

def authenticate_user(username: str, password: str):
    """Authentifie l'utilisateur avec login/password"""
    if username not in CREDENTIALS:
        return False

    if CREDENTIALS[username] != password:
        return False

    return True
