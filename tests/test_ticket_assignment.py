"""Tests de l'affectation automatique de technicien : sélection ALÉATOIRE.

Un technicien actif est choisi au hasard ; techniciens inactifs exclus ;
aucun technicien actif → `None`.
"""
import uuid
from collections import Counter

import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from app.models.role import Role
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import TicketAutoCreate
from app.schemas.user import UserCreate
from app.services.ticket_assignment import pick_technician
from app.services.ticket_service import TicketService
from app.services.user_service import UserService
from app.utils.constants import RoleName
from conftest import unique_email


@pytest_asyncio.fixture
async def world(db_session, role_ids):
    """Un client + un pool de techniciens, en isolant les vrais comptes technicien de dev."""

    us = UserService(db_session)

    pre_existing = (
        await db_session.execute(
            select(User)
            .join(Role, Role.id == User.role_id)
            .where(Role.name == RoleName.TECHNICIEN.value, User.is_active.is_(True))
        )
    ).scalars().all()
    pre_existing_ids = [u.id for u in pre_existing]
    for u in pre_existing:
        u.is_active = False
    if pre_existing:
        await db_session.commit()

    client = await us.create_user(
        UserCreate(email=unique_email("asgn.client"), password="ValidPass1", role_id=role_ids["client"])
    )

    techs: list[User] = []
    for i in range(3):
        tech = User(
            email=unique_email(f"asgn.tech{i}"),
            hashed_password="x",
            role_id=role_ids["technicien"],
            is_active=True,
        )
        db_session.add(tech)
        techs.append(tech)
    await db_session.commit()
    for tech in techs:
        await db_session.refresh(tech)

    yield {"client": client, "techs": techs}

    await db_session.execute(delete(Ticket).where(Ticket.client_id == client.id))
    await db_session.commit()
    for tech in techs:
        row = await db_session.get(User, tech.id)
        if row is not None:
            await db_session.delete(row)
    client_row = await db_session.get(User, client.id)
    if client_row is not None:
        await db_session.delete(client_row)
    await db_session.commit()

    for uid in pre_existing_ids:
        row = await db_session.get(User, uid)
        if row is not None:
            row.is_active = True
    if pre_existing_ids:
        await db_session.commit()


@pytest.mark.asyncio
async def test_picks_one_of_the_active_technicians(db_session, world):
    tech_ids = {t.id for t in world["techs"]}

    chosen = await pick_technician(db_session)

    assert chosen in tech_ids


@pytest.mark.asyncio
async def test_selection_is_random_every_active_technician_can_be_chosen(db_session, world):
    """Sur un grand nombre de tirages, chaque technicien actif est choisi au moins une fois.

    3 techniciens, 60 tirages : rater un technicien a une probabilité
    ~3·(2/3)^60 ≈ 10^-10 — non-flaky en pratique.
    """

    tech_ids = {t.id for t in world["techs"]}
    counts = Counter([await pick_technician(db_session) for _ in range(60)])

    assert set(counts) == tech_ids  # les 3, aucun autre
    assert all(counts[tid] > 0 for tid in tech_ids)


@pytest.mark.asyncio
async def test_inactive_technicians_are_excluded(db_session, world):
    techs = world["techs"]
    for tech in techs[1:]:
        tech.is_active = False
    await db_session.commit()

    chosen = {await pick_technician(db_session) for _ in range(15)}

    assert chosen == {techs[0].id}  # seul actif


@pytest.mark.asyncio
async def test_returns_none_when_no_active_technician(db_session, world):
    for tech in world["techs"]:
        tech.is_active = False
    await db_session.commit()

    assert await pick_technician(db_session) is None


@pytest.mark.asyncio
async def test_auto_created_ticket_is_assigned_to_an_active_technician(db_session, world):
    service = TicketService(db_session)
    tech_ids = {t.id for t in world["techs"]}

    ticket = await service.create_ticket(
        world["client"], TicketAutoCreate(title="Panne", description="Description.")
    )

    assert ticket.assigned_technician_id in tech_ids


__all__: list[str] = []
