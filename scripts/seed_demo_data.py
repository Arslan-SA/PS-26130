"""
UdyamSetu AI — Demo Data & Accounts Seeder Script
Seeds canonical departments, approvals, statutory dependencies,
and SIH Evaluator demo user accounts into the database.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.approval import Approval
from app.models.business import Business, EntityType, MSMECategory
from app.models.business_profile import BusinessProfile, IndustryScale, PollutionCategory
from app.models.department import Department
from app.models.user import User, UserRole
from app.services.dependency_engine import DependencyEngineService
from app.services.requirement_engine import RequirementEngineService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("udyamsetu.seeder")

DEMO_PASSWORD = "Enterprise@2026"


async def seed_demo_data():
    logger.info("Connecting to database to seed default catalogs and demo accounts...")

    async with AsyncSessionLocal() as session:
        # 1. Seed Departments & Approvals
        logger.info("1/4 Seeding statutory departments and approvals catalog...")
        await RequirementEngineService.seed_default_catalog(session)

        # 2. Seed Statutory Dependencies
        logger.info("2/4 Seeding approval dependencies...")
        await DependencyEngineService.seed_default_dependencies(session)

        # Lookup department IDs for officer/inspector mapping
        spcb_dept = (await session.execute(select(Department).where(Department.code == "SPCB"))).scalar_one_or_none()
        fire_dept = (await session.execute(select(Department).where(Department.code == "FIRE"))).scalar_one_or_none()

        hashed_pwd = get_password_hash(DEMO_PASSWORD)

        # 3. Seed Demo Users
        logger.info("3/4 Seeding SIH Evaluator Demo Accounts...")
        users_to_seed = [
            {
                "email": "rajesh.patel@bharatsteel.com",
                "full_name": "Rajesh Patel",
                "role": UserRole.INDUSTRY_USER,
                "phone": "+91 98765 43210",
                "designation": "Managing Director",
                "department_id": None,
            },
            {
                "email": "officer.verma@spcb.gov.in",
                "full_name": "Dr. A. K. Verma",
                "role": UserRole.DEPARTMENT_OFFICER,
                "phone": "+91 98220 12345",
                "designation": "Senior Environmental Engineer",
                "department_id": spcb_dept.id if spcb_dept else None,
            },
            {
                "email": "inspector.sharma@fire.gov.in",
                "full_name": "Vikram Sharma",
                "role": UserRole.INSPECTOR,
                "phone": "+91 98110 54321",
                "designation": "Divisional Fire Safety Inspector",
                "department_id": fire_dept.id if fire_dept else None,
            },
            {
                "email": "admin.super@udyamsetu.gov.in",
                "full_name": "Super Administrator",
                "role": UserRole.ADMIN,
                "phone": "+91 98000 00001",
                "designation": "National Single Window Lead",
                "department_id": None,
            },
        ]

        created_users = {}
        for u_data in users_to_seed:
            stmt = select(User).where(User.email == u_data["email"])
            existing_user = (await session.execute(stmt)).scalar_one_or_none()
            if not existing_user:
                user = User(
                    email=u_data["email"],
                    hashed_password=hashed_pwd,
                    full_name=u_data["full_name"],
                    role=u_data["role"],
                    phone=u_data["phone"],
                    designation=u_data["designation"],
                    department_id=u_data["department_id"],
                    is_verified=True,
                    is_active=True,
                )
                session.add(user)
                await session.flush()
                await session.refresh(user)
                logger.info(f"   Created demo user: {user.email} ({user.role.value})")
                created_users[user.email] = user
            else:
                logger.info(f"   User already exists: {existing_user.email}")
                created_users[existing_user.email] = existing_user

        # 4. Seed Demo Business & Profile for Rajesh Patel
        logger.info("4/4 Seeding Demo Business & Profile for Rajesh Patel...")
        rajesh = created_users.get("rajesh.patel@bharatsteel.com")
        if rajesh:
            stmt_biz = select(Business).where(Business.user_id == rajesh.id)
            existing_biz = (await session.execute(stmt_biz)).scalar_one_or_none()

            if not existing_biz:
                biz = Business(
                    user_id=rajesh.id,
                    legal_name="Bharat Steel & Alloys Pvt Ltd",
                    trade_name="Bharat Steel",
                    entity_type=EntityType.PRIVATE_LIMITED,
                    pan="AAACB1234F",
                    gstin="27AAACB1234F1Z5",
                    udyam_number="UDYAM-MH-01-0012345",
                    cin="U27100MH2020PTC345678",
                    msme_category=MSMECategory.MEDIUM,
                    website="https://bharatsteel.example.com",
                    is_verified=True,
                )
                session.add(biz)
                await session.flush()
                await session.refresh(biz)

                profile = BusinessProfile(
                    business_id=biz.id,
                    nic_code="24101",
                    manufacturing_activity="Hot and cold rolling of stainless steel billets and flat sheets",
                    products_services="Stainless Steel Flat Sheets, Alloy Wire Rods",
                    industry_scale=IndustryScale.MEDIUM_SCALE,
                    pollution_category=PollutionCategory.RED,
                    state="Maharashtra",
                    district="Raigad",
                    city="Taloja",
                    pincode="410208",
                    full_address="Plot No. E-42, MIDC Industrial Area, Taloja, Raigad, Maharashtra 410208",
                    plot_number="Plot No. E-42",
                    industrial_area="MIDC Taloja",
                    latitude=19.0657,
                    longitude=73.1162,
                    total_employees=75,
                    plant_machinery_investment=185000000.0,
                    annual_turnover=620000000.0,
                    land_area_sqm=12500.0,
                    power_requirement_kw=2800.0,
                    water_requirement_kld=85.0,
                    contact_person="Rajesh Patel",
                    contact_phone="+91 98765 43210",
                    contact_email="rajesh.patel@bharatsteel.com",
                    profile_completeness=100,
                    is_profile_complete=True,
                )
                session.add(profile)
                await session.flush()

                # Generate requirements for this demo business
                reqs = await RequirementEngineService.generate_requirements_for_business(session, biz.id)
                logger.info(f"   Created business '{biz.legal_name}' with {len(reqs)} statutory clearance requirements.")
            else:
                logger.info(f"   Business already exists for user: {existing_biz.legal_name}")

        await session.commit()
        logger.info("✅ Database seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
