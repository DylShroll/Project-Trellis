import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.modules.auth.schemas import UserCreate
from app.core.security import hash_password, create_access_token


# ── Helpers ────────────────────────────────────────────────────────────────────

async def create_other_user(db: AsyncSession) -> User:
    return await UserRepository().create(
        db,
        UserCreate(email="other@example.com", password="password123", display_name="Other User"),
        hash_password("password123"),
    )


# ── Plot CRUD ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_plot(client: AsyncClient, test_user: User, auth_headers: dict) -> None:
    response = await client.post("/api/v1/garden/", json={
        "display_name": "Jamie",
        "relationship_tag": "close_friend",
    }, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["display_name"] == "Jamie"
    assert data["relationship_tag"] == "close_friend"
    assert data["stories"] == []


@pytest.mark.asyncio
async def test_list_plots(client: AsyncClient, test_user: User, auth_headers: dict) -> None:
    # Create two plots
    await client.post("/api/v1/garden/", json={"display_name": "Alice"}, headers=auth_headers)
    await client.post("/api/v1/garden/", json={"display_name": "Bob"}, headers=auth_headers)

    response = await client.get("/api/v1/garden/", headers=auth_headers)
    assert response.status_code == 200
    plots = response.json()
    assert len(plots) == 2


@pytest.mark.asyncio
async def test_get_plot(client: AsyncClient, test_user: User, auth_headers: dict) -> None:
    create_resp = await client.post("/api/v1/garden/", json={"display_name": "Carrie"}, headers=auth_headers)
    plot_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/garden/{plot_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["display_name"] == "Carrie"


@pytest.mark.asyncio
async def test_update_plot(client: AsyncClient, test_user: User, auth_headers: dict) -> None:
    create_resp = await client.post("/api/v1/garden/", json={"display_name": "Sam"}, headers=auth_headers)
    plot_id = create_resp.json()["id"]

    response = await client.patch(f"/api/v1/garden/{plot_id}", json={
        "display_name": "Samantha",
        "relationship_tag": "family",
    }, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["display_name"] == "Samantha"
    assert response.json()["relationship_tag"] == "family"


@pytest.mark.asyncio
async def test_delete_plot(client: AsyncClient, test_user: User, auth_headers: dict) -> None:
    create_resp = await client.post("/api/v1/garden/", json={"display_name": "TempPerson"}, headers=auth_headers)
    plot_id = create_resp.json()["id"]

    response = await client.delete(f"/api/v1/garden/{plot_id}", headers=auth_headers)
    assert response.status_code == 204

    # Confirm it's gone
    get_resp = await client.get(f"/api/v1/garden/{plot_id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_get_nonexistent_plot(client: AsyncClient, test_user: User, auth_headers: dict) -> None:
    response = await client.get("/api/v1/garden/00000000-0000-0000-0000-000000000000", headers=auth_headers)
    assert response.status_code == 404


# ── Authorization boundaries ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cannot_access_other_users_plot(
    client: AsyncClient, test_user: User, auth_headers: dict, db: AsyncSession
) -> None:
    # Create a plot as test_user
    create_resp = await client.post("/api/v1/garden/", json={"display_name": "My Friend"}, headers=auth_headers)
    plot_id = create_resp.json()["id"]

    # Create other_user and their token
    other_user = await create_other_user(db)
    other_token = create_access_token(str(other_user.id))
    other_headers = {"Authorization": f"Bearer {other_token}"}

    # other_user cannot access test_user's plot
    response = await client.get(f"/api/v1/garden/{plot_id}", headers=other_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cannot_delete_other_users_plot(
    client: AsyncClient, test_user: User, auth_headers: dict, db: AsyncSession
) -> None:
    create_resp = await client.post("/api/v1/garden/", json={"display_name": "My Friend"}, headers=auth_headers)
    plot_id = create_resp.json()["id"]

    other_user = await create_other_user(db)
    other_headers = {"Authorization": f"Bearer {create_access_token(str(other_user.id))}"}

    response = await client.delete(f"/api/v1/garden/{plot_id}", headers=other_headers)
    assert response.status_code == 404


# ── Sub-resources ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_story(client: AsyncClient, test_user: User, auth_headers: dict) -> None:
    create_resp = await client.post("/api/v1/garden/", json={"display_name": "Alex"}, headers=auth_headers)
    plot_id = create_resp.json()["id"]

    response = await client.post(f"/api/v1/garden/{plot_id}/stories", json={
        "content": "Alex once told me about their summer in Portugal.",
    }, headers=auth_headers)
    assert response.status_code == 201
    assert "Portugal" in response.json()["content"]


@pytest.mark.asyncio
async def test_add_and_resolve_curiosity(
    client: AsyncClient, test_user: User, auth_headers: dict
) -> None:
    create_resp = await client.post("/api/v1/garden/", json={"display_name": "Jordan"}, headers=auth_headers)
    plot_id = create_resp.json()["id"]

    add_resp = await client.post(f"/api/v1/garden/{plot_id}/curiosities", json={
        "question": "What did Jordan want to be as a kid?",
    }, headers=auth_headers)
    assert add_resp.status_code == 201
    curiosity_id = add_resp.json()["id"]
    assert add_resp.json()["is_resolved"] is False

    resolve_resp = await client.post(
        f"/api/v1/garden/{plot_id}/curiosities/{curiosity_id}/resolve",
        headers=auth_headers,
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["is_resolved"] is True


@pytest.mark.asyncio
async def test_add_milestone(client: AsyncClient, test_user: User, auth_headers: dict) -> None:
    create_resp = await client.post("/api/v1/garden/", json={"display_name": "Morgan"}, headers=auth_headers)
    plot_id = create_resp.json()["id"]

    response = await client.post(f"/api/v1/garden/{plot_id}/milestones", json={
        "title": "Birthday",
        "date": "1990-06-15",
        "is_recurring": True,
    }, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Birthday"
    assert data["is_recurring"] is True
