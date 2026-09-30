"""
Personalized Statutory Clearance Roadmap Service (Fragment 54).
Computes scheduled calendar start dates, SLA finish dates, parallel execution tracks,
and milestone phase groupings along the industrial lifecycle timeline.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import Approval
from app.models.approval_dependency import ApprovalDependency, DependencyType
from app.models.approval_requirement import ApprovalRequirement, RequirementStage, RequirementStatus
from app.services.dependency_engine import DependencyEngineService


@dataclass(frozen=True)
class RoadmapActivity:
    """Scheduled clearance activity on the timeline."""
    approval_code: str
    requirement_id: str
    title: str
    department_code: str
    stage: RequirementStage
    status: RequirementStatus
    sla_days: int
    estimated_fee: float
    start_day_offset: int
    finish_day_offset: int
    scheduled_start: date
    scheduled_finish: date
    is_critical: bool
    prerequisites: List[str]


@dataclass(frozen=True)
class RoadmapMilestone:
    """Milestone phase grouping (e.g. Pre-Establishment, Commissioning)."""
    phase_id: str
    title: str
    description: str
    start_day: int
    finish_day: int
    scheduled_start: date
    scheduled_finish: date
    activity_count: int
    total_estimated_fee: float


@dataclass(frozen=True)
class RoadmapPlan:
    """Complete personalized statutory clearance roadmap."""
    business_id: str
    base_start_date: date
    projected_commissioning_date: date
    total_calendar_days: int
    critical_path_days: int
    activities: List[RoadmapActivity]
    milestones: List[RoadmapMilestone]


class RoadmapService:
    """Service to schedule clearance activities and compute milestone timelines."""

    @staticmethod
    async def generate_roadmap(
        session: AsyncSession,
        business_id: str,
        start_date: Optional[date] = None,
    ) -> RoadmapPlan:
        """
        Generate a personalized Gantt-style schedule based on statutory SLAs,
        topological dependency sequencing, and parallel opportunity tracks.
        """
        base_date = start_date or date.today()

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
            return RoadmapPlan(
                business_id=business_id,
                base_start_date=base_date,
                projected_commissioning_date=base_date,
                total_calendar_days=0,
                critical_path_days=0,
                activities=[],
                milestones=[],
            )

        code_to_req = {app.code: req for req, app in active_rows}
        code_to_app = {app.code: app for req, app in active_rows}
        all_codes = list(code_to_req.keys())
        sla_by_code = {code: req.sla_deadline_days for code, req in code_to_req.items()}

        # 2. Fetch mandatory dependency edges
        await DependencyEngineService.seed_default_dependencies(session)
        dep_stmt = select(ApprovalDependency).where(
            ApprovalDependency.dependency_type == DependencyType.MANDATORY_PREREQUISITE
        )
        dependencies = (await session.execute(dep_stmt)).scalars().all()

        prereqs_map: Dict[str, List[str]] = {c: [] for c in all_codes}
        dag_edges: List[tuple[str, str]] = []
        for d in dependencies:
            if d.from_approval_code in code_to_req and d.to_approval_code in code_to_req:
                prereqs_map[d.to_approval_code].append(d.from_approval_code)
                dag_edges.append((d.from_approval_code, d.to_approval_code))

        # 3. Topological ordering
        order = DependencyEngineService.topological_sort(all_codes, dag_edges)
        critical_days, critical_path_list = DependencyEngineService.calculate_critical_path(
            all_codes, dag_edges, sla_by_code
        )
        critical_path_set = set(critical_path_list)

        # 4. Schedule forward pass: start_day = max(finish_day of prerequisites)
        start_offsets: Dict[str, int] = {}
        finish_offsets: Dict[str, int] = {}

        for code in order:
            prereqs = prereqs_map.get(code, [])
            if not prereqs:
                start_day = 0
            else:
                start_day = max(finish_offsets.get(p, 0) for p in prereqs)

            sla = sla_by_code.get(code, 30)
            start_offsets[code] = start_day
            finish_offsets[code] = start_day + sla

        max_day = max(finish_offsets.values()) if finish_offsets else 0
        commissioning_date = base_date + timedelta(days=max_day)

        # 5. Build RoadmapActivity list
        activities: List[RoadmapActivity] = []
        for code in order:
            req = code_to_req[code]
            app = code_to_app[code]
            s_day = start_offsets[code]
            f_day = finish_offsets[code]

            activities.append(
                RoadmapActivity(
                    approval_code=code,
                    requirement_id=req.id,
                    title=app.title,
                    department_code=app.department_code,
                    stage=req.stage,
                    status=req.status,
                    sla_days=req.sla_deadline_days,
                    estimated_fee=req.estimated_fee,
                    start_day_offset=s_day,
                    finish_day_offset=f_day,
                    scheduled_start=base_date + timedelta(days=s_day),
                    scheduled_finish=base_date + timedelta(days=f_day),
                    is_critical=code in critical_path_set,
                    prerequisites=prereqs_map.get(code, []),
                )
            )

        # 6. Group into Phase Milestones
        stage_names = [
            (RequirementStage.PRE_ESTABLISHMENT, "Phase 1: Pre-Establishment Clearances", "Mandatory consents before breaking ground"),
            (RequirementStage.PRE_COMMISSIONING, "Phase 2: Pre-Commissioning & Energization", "Consents for trial runs, power, and utility sync"),
            (RequirementStage.POST_COMMISSIONING, "Phase 3: Post-Commissioning & Factory Licenses", "Final operating permissions for commercial sales"),
        ]

        milestones: List[RoadmapMilestone] = []
        for stage_enum, title, desc in stage_names:
            stage_acts = [a for a in activities if a.stage == stage_enum]
            if stage_acts:
                m_start = min(a.start_day_offset for a in stage_acts)
                m_finish = max(a.finish_day_offset for a in stage_acts)
                m_fee = sum(a.estimated_fee for a in stage_acts)
                milestones.append(
                    RoadmapMilestone(
                        phase_id=stage_enum.value,
                        title=title,
                        description=desc,
                        start_day=m_start,
                        finish_day=m_finish,
                        scheduled_start=base_date + timedelta(days=m_start),
                        scheduled_finish=base_date + timedelta(days=m_finish),
                        activity_count=len(stage_acts),
                        total_estimated_fee=m_fee,
                    )
                )

        return RoadmapPlan(
            business_id=business_id,
            base_start_date=base_date,
            projected_commissioning_date=commissioning_date,
            total_calendar_days=max_day,
            critical_path_days=critical_days,
            activities=activities,
            milestones=milestones,
        )
