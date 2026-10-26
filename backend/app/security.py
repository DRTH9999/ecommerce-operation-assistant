import base64
import hashlib
import hmac
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from . import models as m
from .db import get_conn

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return 'scrypt$' + base64.b64encode(salt).decode() + '$' + base64.b64encode(digest).decode()


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt, stored = encoded.split('$')
        if algorithm != 'scrypt':
            return False
        digest = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=16384, r=8, p=1, dklen=32)
        return hmac.compare_digest(digest, base64.b64decode(stored))
    except (ValueError, TypeError):
        return False


def public_user(user):
    return {k: v for k, v in user.items() if k not in {'password_hash', 'token_version'}}


def issue_token(user, request):
    now = datetime.now(UTC)
    return jwt.encode({'sub': str(user['id']), 'ver': user['token_version'], 'iat': now,
                       'exp': now + timedelta(minutes=request.app.state.settings.access_token_minutes)},
                      request.app.state.signing_key, algorithm='HS256')


def current_user(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
                 conn=Depends(get_conn)):
    if credentials is None:
        raise HTTPException(401, '请先登录', headers={'WWW-Authenticate': 'Bearer'})
    try:
        payload = jwt.decode(credentials.credentials, request.app.state.signing_key, algorithms=['HS256'])
        user = conn.execute(select(m.users).where(m.users.c.id == int(payload['sub']))).mappings().first()
        if not user or user['status'] != 'active' or user['token_version'] != payload.get('ver'):
            raise ValueError('invalid user')
        return dict(user)
    except (jwt.InvalidTokenError, KeyError, ValueError, TypeError):
        raise HTTPException(401, '登录已过期，请重新登录', headers={'WWW-Authenticate': 'Bearer'})


def permission(*roles):
    def check(user=Depends(current_user)):
        if user['role'] not in roles:
            raise HTTPException(403, '当前角色没有执行此操作的权限')
        return user
    return check


writer = permission('admin', 'operator')
admin = permission('admin')
# 独立声明，避免关键权限日后跟随普通编辑权限意外放宽。
confirm_ads = permission('admin', 'operator')
manage_experiments = permission('admin', 'operator')


class LoginLimiter:
    def __init__(self):
        self.entries = defaultdict(deque)
        self.lock = threading.Lock()

    def check(self, key):
        with self.lock:
            now = time.monotonic()
            queue = self.entries[key]
            while queue and queue[0] < now - 60:
                queue.popleft()
            if len(queue) >= 10:
                raise HTTPException(429, '登录尝试过于频繁，请一分钟后重试')
            queue.append(now)
            if len(self.entries) > 10000:
                self.entries = defaultdict(deque, {k: v for k, v in self.entries.items() if v and v[-1] > now - 60})
