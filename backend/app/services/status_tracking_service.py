"""
Approval Status Tracking & Audit Service (Fragment 56).
Maintains an immutable historical audit log of statutory clearance lifecycle transitions,
capturing timestamps, actors, remarks, and official reference numbers.
"""

from typing import List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.approval_requirement import ApprovalRequirement, RequirementStatus
from app.models.approval_status_history import ApprovalStatusHistory


class StatusTrackingService:
    """Service managing status transitions and audit history for approval requirements."""

    @staticmethod
    async def record_status_transition(
        session: AsyncSession,
        requirement_id: str,
        to_status: RequirementStatus,
        user_id: Optional[str] = None,
        remarks: Optional[str] = None,
        reference_number: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Tuple[ApprovalRequirement, ApprovalStatusHistory]:
        """
        Record a lifecycle status transition on an approval requirement and persist
        an immutable audit history entry.
        """
        stmt = select(ApprovalRequirement).where(ApprovalRequirement.id == requirement_id)
        req = (await session.execute(stmt)).scalar_one_or_none()
        if not req:
            raise NotFoundError("Approval requirement not found", details={"requirement_id": requirement_id})

        from_status = req.status
        req.status = to_status
        if notes is not None:
            req.notes = notes

        history = ApprovalStatusHistory(
            requirement_id=req.id,
            business_id=req.business_id,
            from_status=from_status,
            to_status=to_status,
            changed_by_user_id=user_id,
            remarks=remarks or notes,
            reference_number=reference_number,
        )
        session.add(history)
        await session.commit()
        await session.refresh(req)
        await session.refresh(history)

        return req, history

    @staticmethod
    async def get_history_for_requirement(
        session: AsyncSession,
        requirement_id: str,
    ) -> List[ApprovalStatusHistory]:
        """Retrieve complete transition history for a specific requirement ordered newest first."""
        stmt = (
            select(ApprovalStatusHistory)
            .where(ApprovalStatusHistory.requirement_id == requirement_id)
            .order_by(ApprovalStatusHistory.created_at.desc())
        )
        return list((await session.execute(stmt)).scalars().all())

    @staticmethod
    async def get_history_for_business(
        session: AsyncSession,
        business_id: str,
    ) -> List[ApprovalStatusHistory]:
        """Retrieve enterprise-wide statutory approval transition log ordered newest first."""
        stmt = (
            select(ApprovalStatusHistory)
            .where(ApprovalStatusHistory.business_id == business_id)
            .order_by(ApprovalStatusHistory.created_at.desc())
        )
        return list((await session.execute(stmt)).scalars().all())
