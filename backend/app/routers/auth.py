from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from .. import models as m, schemas as s
from ..db import get_conn, insert, one, rows, update
from ..security import admin, current_user, hash_password, issue_token, public_user, verify_password

router = APIRouter(prefix='/api/v1', tags=['认证与用户'])


@router.post('/auth/login')
def login(data: s.Login, request: Request, conn=Depends(get_conn)):
    request.app.state.login_limiter.check((request.client.host if request.client else '', data.username))
    user = conn.execute(select(m.users).where(m.users.c.username == data.username)).mappings().first()
    if not user or not verify_password(data.password, user['password_hash']) or user['status'] != 'active':
        raise HTTPException(401, '用户名或密码错误，或账号已停用')
    user = update(conn, m.users, user['id'], {'last_login_at': m.utcnow()})
    return {'access_token': issue_token(user, request), 'token_type': 'bearer',
            'expires_in': request.app.state.settings.access_token_minutes * 60, 'user': public_user(user)}


@router.get('/auth/me')
def me(user=Depends(current_user)):
    return public_user(user)


@router.post('/auth/logout')
def logout(user=Depends(current_user), conn=Depends(get_conn)):
    update(conn, m.users, user['id'], {'token_version': user['token_version'] + 1})
    return {'message': '已退出登录'}


@router.get('/users')
def list_users(user=Depends(admin), conn=Depends(get_conn)):
    return [public_user(u) for u in rows(conn, m.users)]


@router.post('/users', status_code=201)
def create_user(data: s.UserCreate, user=Depends(admin), conn=Depends(get_conn)):
    values = data.model_dump(exclude={'password'})
    values['password_hash'] = hash_password(data.password)
    return public_user(insert(conn, m.users, values))


@router.patch('/users/{user_id}')
def patch_user(user_id: int, data: s.UserPatch, actor=Depends(admin), conn=Depends(get_conn)):
    target = one(conn, m.users, user_id)
    values = data.model_dump(exclude_unset=True)
    if user_id == actor['id'] and (values.get('status', 'active') != 'active' or values.get('role', 'admin') != 'admin'):
        raise HTTPException(409, '不能停用自己或移除自己的管理员角色')
    if password := values.pop('password', None):
        values['password_hash'] = hash_password(password)
    if any(key in values for key in ('password_hash', 'role', 'status')):
        values['token_version'] = target['token_version'] + 1
    return public_user(update(conn, m.users, user_id, values))
