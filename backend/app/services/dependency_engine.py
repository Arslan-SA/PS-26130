"""
Clearance Dependency & DAG Engine (Fragment 51).
Implements Kahn's topological sort, cycle detection, critical path calculation,
and real-time prerequisite unlock evaluation for industrial approvals.
"""

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval_dependency import ApprovalDependency, DependencyType
from app.models.approval_requirement import ApprovalRequirement, RequirementStatus

DEFAULT_STATUTORY_DEPENDENCIES = [
    {
        "from_approval_code": "CTE_PCB",
        "to_approval_code": "CTO_PCB",
        "dependency_type": DependencyType.MANDATORY_PREREQUISITE,
        "description": "Consent to Establish is mandatory before trial runs or Consent to Operate under Water & Air Acts.",
        "enacted_statute": "Water Act 1974 & Air Act 1981",
    },
    {
        "from_approval_code": "CTE_PCB",
        "to_approval_code": "POWER_HT",
        "dependency_type": DependencyType.MANDATORY_PREREQUISITE,
        "description": "Power distribution utility requires valid CTE prior to substation transformer energization.",
        "enacted_statute": "Electricity Act, 2003",
    },
    {
        "from_approval_code": "FIRE_NOC",
        "to_approval_code": "FACTORY_LIC",
        "dependency_type": DependencyType.MANDATORY_PREREQUISITE,
        "description": "Directorate of Industrial Safety & Health mandates a valid Fire Safety NOC before factory license grant.",
        "enacted_statute": "Factories Act, 1948 - Section 6",
    },
    {
        "from_approval_code": "CTO_PCB",
        "to_approval_code": "FACTORY_LIC",
        "dependency_type": DependencyType.MANDATORY_PREREQUISITE,
        "description": "Active environmental Consent to Operate is required before commercial factory operating license is granted.",
        "enacted_statute": "Factories Act, 1948 & Water/Air Acts",
    },
    {
        "from_approval_code": "CGWA_GW",
        "to_approval_code": "CTE_PCB",
        "dependency_type": DependencyType.RECOMMENDED_PARALLEL,
        "description": "Groundwater extraction NOC can be processed simultaneously with CTE during pre-establishment.",
        "enacted_statute": "Environment (Protection) Act, 1986",
    },
]


@dataclass
class UnlockStatus:
    """Readiness evaluation for a specific clearance requirement."""
    approval_code: str
    is_unlocked: bool
    missing_prerequisites: List[str]


class DependencyEngineService:
    """Algorithms and service logic for the clearance DAG."""

    @staticmethod
    async def seed_default_dependencies(session: AsyncSession) -> None:
        """Seed default statutory dependencies into database idempotently."""
        for dep in DEFAULT_STATUTORY_DEPENDENCIES:
            stmt = select(ApprovalDependency).where(
                ApprovalDependency.from_approval_code == dep["from_approval_code"],
                ApprovalDependency.to_approval_code == dep["to_approval_code"],
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if not existing:
                record = ApprovalDependency(**dep)
                session.add(record)
        await session.commit()

    @staticmethod
    def detect_cycles(edges: List[Tuple[str, str]]) -> bool:
        """Return True if any directed cycles exist among the edges; False if strict DAG."""
        adj: Dict[str, List[str]] = defaultdict(list)
        nodes: Set[str] = set()
        for u, v in edges:
            adj[u].append(v)
            nodes.add(u)
            nodes.add(v)

        visited: Dict[str, int] = {n: 0 for n in nodes}  # 0: unvisited, 1: visiting, 2: visited

        def dfs(node: str) -> bool:
            visited[node] = 1
            for neighbor in adj.get(node, []):
                if visited[neighbor] == 1:
                    return True  # Back-edge detected -> cycle
                if visited[neighbor] == 0:
                    if dfs(neighbor):
                        return True
            visited[node] = 2
            return False

        for n in nodes:
            if visited[n] == 0:
                if dfs(n):
                    return True
        return False

    @staticmethod
    def topological_sort(nodes: List[str], edges: List[Tuple[str, str]]) -> List[str]:
        """
        Compute Kahn's topological ordering of clearances.
        Returns ordered sequence where all prerequisites appear before dependent clearances.
        """
        in_degree: Dict[str, int] = {n: 0 for n in nodes}
        adj: Dict[str, List[str]] = defaultdict(list)

        for u, v in edges:
            if u in in_degree and v in in_degree:
                adj[u].append(v)
                in_degree[v] += 1

        queue = deque([n for n in nodes if in_degree[n] == 0])
        order: List[str] = []

        while queue:
            curr = queue.popleft()
            order.append(curr)
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # If any node remains with in_degree > 0, there is a cycle
        if len(order) < len(nodes):
            # Append remaining nodes in arbitrary order
            remaining = [n for n in nodes if n not in order]
            order.extend(remaining)

        return order

    @staticmethod
    async def evaluate_requirement_unlocks(
        session: AsyncSession,
        requirements: List[ApprovalRequirement],
        code_by_approval_id: Dict[str, str],
    ) -> Dict[str, UnlockStatus]:
        """
        Evaluate which requirements are unlocked (ready for applicant submission)
        based on mandatory prerequisites and their current fulfillment status.
        """
        await DependencyEngineService.seed_default_dependencies(session)

        # Build status lookup by clearance code
        status_by_code: Dict[str, RequirementStatus] = {}
        for r in requirements:
            code = code_by_approval_id.get(r.approval_id)
            if code:
                status_by_code[code] = r.status

        # Query all mandatory dependencies
        stmt = select(ApprovalDependency).where(
            ApprovalDependency.dependency_type == DependencyType.MANDATORY_PREREQUISITE
        )
        dependencies = (await session.execute(stmt)).scalars().all()

        prereqs_by_code: Dict[str, List[str]] = defaultdict(list)
        for d in dependencies:
            prereqs_by_code[d.to_approval_code].append(d.from_approval_code)

        results: Dict[str, UnlockStatus] = {}
        for r in requirements:
            code = code_by_approval_id.get(r.approval_id)
            if not code:
                continue

            prereqs = prereqs_by_code.get(code, [])
            # An approval is blocked if any of its active prerequisites is NOT APPROVED
            missing = [
                p for p in prereqs
                if p in status_by_code and status_by_code[p] != RequirementStatus.APPROVED
            ]

            results[code] = UnlockStatus(
                approval_code=code,
                is_unlocked=len(missing) == 0,
                missing_prerequisites=missing,
            )

        return results

    @staticmethod
    def calculate_critical_path(
        nodes: List[str],
        edges: List[Tuple[str, str]],
        sla_by_code: Dict[str, int],
    ) -> Tuple[int, List[str]]:
        """
        Calculate longest execution path (critical turnaround path) through the DAG.
        Returns: (maximum_days, path_nodes)
        """
        order = DependencyEngineService.topological_sort(nodes, edges)
        adj: Dict[str, List[str]] = defaultdict(list)
        for u, v in edges:
            adj[u].append(v)

        dist: Dict[str, int] = {n: sla_by_code.get(n, 0) for n in nodes}
        parent: Dict[str, Optional[str]] = {n: None for n in nodes}

        for u in order:
            for v in adj[u]:
                cost = dist[u] + sla_by_code.get(v, 0)
                if cost > dist[v]:
                    dist[v] = cost
                    parent[v] = u

        if not dist:
            return 0, []

        max_node = max(dist, key=dist.get)
        max_days = dist[max_node]

        # Reconstruct path
        path: List[str] = []
        curr: Optional[str] = max_node
        while curr:
            path.append(curr)
            curr = parent[curr]
        path.reverse()

        return max_days, path
