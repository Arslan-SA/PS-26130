"""
Next-Action Recommendation Engine (Fragment 55).
Dynamically computes prioritized, immediate statutory clearance tasks,
evaluating DAG unlocks, critical path bottlenecks, and department SLA tracking.
"""

from typing import Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import Approval
from app.models.approval_dependency import ApprovalDependency, DependencyType
from app.models.approval_requirement import ApprovalRequirement, RequirementStage, RequirementStatus
from app.schemas.approval import (
    ActionPriority,
    ActionType,
    NextActionItemRead,
    NextActionSummaryResponse,
)
from app.services.dependency_engine import DependencyEngineService


class NextActionEngineService:
    """Calculates dynamic priority queues of statutory clearance tasks."""

    @staticmethod
    async def compute_next_actions(
        session: AsyncSession,
        business_id: str,
    ) -> NextActionSummaryResponse:
        """
        Evaluate all active statutory requirements for a business and return
        a prioritized action list with rationale, critical path markers, and readiness states.
        """
        # 1. Fetch requirements and approvals
        stmt = (
            select(ApprovalRequirement, Approval)
            .join(Approval, ApprovalRequirement.approval_id == Approval.id)
            .where(ApprovalRequirement.business_id == business_id)
        )
        rows = (await session.execute(stmt)).all()
        active_rows = [
            (req, app) for req, app in rows if req.status != RequirementStatus.EXEMPTED
        ]

        if not active_rows:
            return NextActionSummaryResponse(
                business_id=business_id,
                total_clearances=0,
                ready_to_act_count=0,
                critical_path_actions_count=0,
                blocked_count=0,
                under_review_count=0,
                completed_count=0,
                top_immediate_action=None,
                actions=[],
            )

        code_to_req: Dict[str, ApprovalRequirement] = {app.code: req for req, app in active_rows}
        code_to_app: Dict[str, Approval] = {app.code: app for req, app in active_rows}
        approval_id_to_code: Dict[str, str] = {app.id: app.code for req, app in active_rows}
        all_codes = list(code_to_req.keys())
        sla_by_code = {code: req.sla_deadline_days for code, req in code_to_req.items()}

        # 2. Fetch mandatory dependency edges
        await DependencyEngineService.seed_default_dependencies(session)
        dep_stmt = select(ApprovalDependency).where(
            ApprovalDependency.dependency_type == DependencyType.MANDATORY_PREREQUISITE
        )
        dependencies = (await session.execute(dep_stmt)).scalars().all()

        dag_edges: List[Tuple[str, str]] = []
        for d in dependencies:
            if d.from_approval_code in code_to_req and d.to_approval_code in code_to_req:
                dag_edges.append((d.from_approval_code, d.to_approval_code))

        # 3. Critical path calculation & prerequisite unlocks
        _, critical_path = DependencyEngineService.calculate_critical_path(
            all_codes, dag_edges, sla_by_code
        )
        critical_path_set = set(critical_path)

        active_requirements = [req for req, _ in active_rows]
        unlock_statuses = await DependencyEngineService.evaluate_requirement_unlocks(
            session, active_requirements, approval_id_to_code
        )

        # 4. Generate prioritized actions
        actions: List[NextActionItemRead] = []

        for code in all_codes:
            req = code_to_req[code]
            app = code_to_app[code]
            unlock = unlock_statuses.get(code)
            is_unlocked = unlock.is_unlocked if unlock else True
            missing_prereqs = unlock.missing_prerequisites if unlock else []
            is_crit = code in critical_path_set

            if req.status == RequirementStatus.APPROVED:
                action_type = ActionType.DOWNLOAD_CERTIFICATE
                priority = ActionPriority.LOW
                priority_score = 10
                headline = f"Download Approval Certificate ({app.code})"
                rationale = (
                    f"Clearance granted by {app.department_code}. "
                    "Statutory approval certificate is verified and active."
                )

            elif req.status in (RequirementStatus.SUBMITTED, RequirementStatus.UNDER_REVIEW):
                action_type = ActionType.TRACK_SLA
                priority = ActionPriority.CRITICAL if is_crit else ActionPriority.MEDIUM
                priority_score = 90 if is_crit else 60
                headline = f"Track SLA for {app.title} ({app.code})"
                rationale = (
                    f"Application under official processing at {app.department_code}. "
                    f"Statutory turnaround SLA is {req.sla_deadline_days} working days."
                )

            elif not is_unlocked and missing_prereqs:
                action_type = ActionType.RESOLVE_PREREQUISITES
                priority = ActionPriority.LOW
                priority_score = 25
                headline = f"Prerequisites Pending for {app.title}"
                rationale = (
                    f"Application blocked pending mandatory prerequisite approval: "
                    f"{', '.join(missing_prereqs)}."
                )

            else:
                # Unlocked and NOT_STARTED or IN_PROGRESS
                if is_crit:
                    action_type = ActionType.APPLY_NOW
                    priority = ActionPriority.CRITICAL
                    stage_penalty = (
                        0 if req.stage == RequirementStage.PRE_ESTABLISHMENT
                        else (10 if req.stage == RequirementStage.PRE_COMMISSIONING else 20)
                    )
                    priority_score = 100 - stage_penalty
                    headline = f"Critical Path Action: Apply for {app.title}"
                    rationale = (
                        f"This clearance is on the project critical path ({req.sla_deadline_days} days SLA). "
                        "Immediate submission prevents postponement of commercial commissioning."
                    )
                elif req.status == RequirementStatus.IN_PROGRESS:
                    action_type = ActionType.PREPARE_DOCS
                    priority = ActionPriority.HIGH
                    priority_score = 80
                    headline = f"Complete Dossier & Documents for {app.title}"
                    rationale = (
                        f"Prerequisites satisfied. Finalize mandatory documentation "
                        f"to submit to {app.department_code}."
                    )
                else:
                    action_type = ActionType.APPLY_NOW
                    priority = ActionPriority.HIGH
                    priority_score = 75
                    headline = f"Apply for {app.title}"
                    rationale = (
                        f"Clearance unlocked. Ready to initiate filing and fee payment "
                        f"(₹{req.estimated_fee:,.0f})."
                    )

            actions.append(
                NextActionItemRead(
                    approval_code=app.code,
                    requirement_id=req.id,
                    approval_id=app.id,
                    title=app.title,
                    department_code=app.department_code,
                    stage=req.stage,
                    current_status=req.status,
                    action_type=action_type,
                    priority=priority,
                    priority_score=priority_score,
                    headline=headline,
                    rationale=rationale,
                    sla_days=req.sla_deadline_days,
                    estimated_fee=req.estimated_fee,
                    is_critical_path=is_crit,
                    is_unlocked=is_unlocked,
                    blocked_by=missing_prereqs,
                    target_url=f"/approvals/{req.id}",
                )
            )

        # 5. Order by priority score descending, then SLA descending
        actions.sort(key=lambda a: (a.priority_score, a.sla_days), reverse=True)

        ready_to_act = sum(
            1 for a in actions
            if a.action_type in (ActionType.APPLY_NOW, ActionType.PREPARE_DOCS, ActionType.PAY_FEES)
        )
        critical_count = sum(
            1 for a in actions
            if a.is_critical_path and a.action_type in (ActionType.APPLY_NOW, ActionType.PREPARE_DOCS, ActionType.TRACK_SLA)
        )
        blocked_count = sum(
            1 for a in actions
            if a.action_type == ActionType.RESOLVE_PREREQUISITES
        )
        under_review_count = sum(
            1 for a in actions
            if a.action_type == ActionType.TRACK_SLA
        )
        completed_count = sum(
            1 for a in actions
            if a.action_type == ActionType.DOWNLOAD_CERTIFICATE
        )
        top_action = actions[0] if actions else None

        return NextActionSummaryResponse(
            business_id=business_id,
            total_clearances=len(actions),
            ready_to_act_count=ready_to_act,
            critical_path_actions_count=critical_count,
            blocked_count=blocked_count,
            under_review_count=under_review_count,
            completed_count=completed_count,
            top_immediate_action=top_action,
            actions=actions,
        )
