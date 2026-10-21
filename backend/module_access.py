"""Explicit grants for opt-in business modules. Public contracts remain public."""
from uuid import uuid4

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError

from backend.auth.routes import require_authenticated
from backend.auth.service import AuthUnavailable, utcnow
from backend.models import AuthUser, AuthSession, ModuleConfigRecord, UserModuleGrant, UserModuleGrantEvent
from backend.user_management import UserManagementService, UserDenied, UserConflict, UserMissing

CORE_IDS = frozenset({'auth','authentication','core','platform','users','sessions','audit','settings'})


def assignable(detail):
    return detail.access_mode == 'assigned' and not detail.required and detail.id not in CORE_IDS


class GrantInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    granted: bool
    expected_granted: bool


class GrantItem(BaseModel):
    module_id: str
    name: str
    enabled: bool
    granted: bool


class GrantPage(BaseModel):
    items: list[GrantItem]
    next_after_module: str | None


class ModuleAccessService:
    def __init__(self, registry, database, auth_service=None):
        self.registry, self.database = registry, database
        self.auth_service = auth_service
        self.users = UserManagementService(database)

    def target(self, session, user_id):
        row = session.execute(select(AuthUser.active).where(AuthUser.id == user_id)).first()
        if row is None: raise UserMissing()
        if not row.active: raise UserDenied()

    def detail(self, module_id):
        detail = self.registry.detail(module_id)
        if detail is None or not assignable(detail): raise UserDenied()
        return detail

    def enabled(self, session, detail):
        row = session.get(ModuleConfigRecord, detail.id)
        return row.enabled if row and row.enabled is not None else detail.status == 'enabled'

    def page(self, actor_id, user_id, limit=20, after=None, *, own=False):
        if type(limit) is not int or not 1 <= limit <= 50: raise ValueError('Invalid page limit')
        # Own reads still recheck active state and storage in the same transaction.
        if self.database is None: raise AuthUnavailable()
        context = self.database.transaction() if own else self.users.transaction(actor_id)
        try:
            with context as session:
                if own and actor_id != user_id: raise UserDenied()
                self.target(session, user_id)
                candidates = sorted((d for d in self.registry.manifests() if assignable(d) and (after is None or d.id > after)), key=lambda d:d.id)
                # Probe the required storage even when the current registry is public-only.
                session.execute(select(UserModuleGrant.user_id).where(UserModuleGrant.user_id==user_id).limit(1))
                items=[]
                for detail in candidates:
                    granted = session.get(UserModuleGrant,(user_id,detail.id)) is not None
                    enabled = self.enabled(session,detail)
                    if own and (not granted or not enabled): continue
                    items.append(GrantItem(module_id=detail.id,name=detail.name,enabled=enabled,granted=granted))
                    if len(items)>limit: break
                return GrantPage(items=items[:limit],next_after_module=items[limit-1].module_id if len(items)>limit else None)
        except SQLAlchemyError: raise AuthUnavailable() from None

    def save(self, actor_id, user_id, module_id, value, session_key=None):
        value=GrantInput.model_validate(value)
        detail=self.detail(module_id)
        with self.users.transaction(actor_id,write=True) as session:
            # HTTP callers always supply the hashed session key. Recheck and lock
            # it inside the write transaction, so a waiting/revoked session fails.
            if session_key is not None:
                current=session.get(AuthSession,session_key,with_for_update=True)
                if self.auth_service is None or not self.auth_service._valid(current) or current.user_id!=actor_id:
                    raise UserDenied()
            self.target(session,user_id)
            existing=session.get(UserModuleGrant,(user_id,module_id))
            current=existing is not None
            if current==value.granted:
                return GrantItem(module_id=module_id,name=detail.name,enabled=self.enabled(session,detail),granted=current)
            if current!=value.expected_granted: raise UserConflict()
            if value.granted:
                session.add(UserModuleGrant(user_id=user_id,module_id=module_id,created_at=utcnow()))
            else:
                session.execute(delete(UserModuleGrant).where(UserModuleGrant.user_id==user_id,UserModuleGrant.module_id==module_id))
            session.add(UserModuleGrantEvent(id=str(uuid4()),actor_id=actor_id,user_id=user_id,
                module_id=module_id,action='granted' if value.granted else 'revoked',created_at=utcnow()))
            session.flush()
            return GrantItem(module_id=module_id,name=detail.name,enabled=self.enabled(session,detail),granted=value.granted)

    def check(self, user_id, module_id):
        detail=self.detail(module_id)
        if self.database is None: raise AuthUnavailable()
        try:
            with self.database.transaction() as session:
                self.target(session,user_id)
                if not self.enabled(session,detail):
                    raise HTTPException(404,'Module not available',headers={'Cache-Control':'no-store'})
                if session.get(UserModuleGrant,(user_id,module_id)) is None: raise UserDenied()
        except SQLAlchemyError: raise AuthUnavailable() from None


def require_module_access(module_id):
    def check(request: Request,identity=Depends(require_authenticated)):
        request.app.state.module_access.check(identity.id,module_id)
        return identity
    return check
