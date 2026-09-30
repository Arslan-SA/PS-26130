"""
System Administrator portal and user governance endpoints.
Provides master control over system users, roles, audit logs, and global parameters.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.core.exceptions import NotFoundError
from app.models.user import User, UserRole
from app.schemas.user import UserResponse

router = APIRouter(prefix="/admin", tags=["System Administration Portal"])


class UserStatusUpdatePayload(BaseModel):
    is_active: bool


@router.get(
    "/system-overview",
    summary="Get System Admin macro tenant overview",
)
async def get_system_overview(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Returns global administrative counts and system health metrics."""
    total_users_stmt = select(func.count(User.id))
    active_users_stmt = select(func.count(User.id)).where(User.is_active == True)

    total_users = (await db.execute(total_users_stmt)).scalar() or 0
    active_users = (await db.execute(active_users_stmt)).scalar() or 0

    return {
        "admin_id": admin.id,
        "admin_name": admin.full_name,
        "total_registered_users": total_users,
        "active_users": active_users,
        "system_status": "healthy",
        "rbac_enforcement": "strict",
    }


@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="List registered users with optional role filtering",
)
async def list_users(
    role: Optional[UserRole] = Query(default=None, description="Filter users by RBAC role"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> List[UserResponse]:
    """Admin-only query of all registered users."""
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    stmt = stmt.order_by(User.created_at.desc())

    result = await db.execute(stmt)
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.patch(
    "/users/{user_id}/status",
    response_model=UserResponse,
    summary="Activate or deactivate a user account",
)
async def update_user_status(
    user_id: str,
    payload: UserStatusUpdatePayload,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Admin-only modification of user access activation state."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise NotFoundError(f"User with ID '{user_id}' not found.")

    user.is_active = payload.is_active
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)
