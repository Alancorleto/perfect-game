from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from models.round import RoundState
from tests.helpers import (
    create_category_in_db,
    create_round_in_db,
    create_set_in_db,
    create_tournament_in_db,
    create_user_in_db,
    get_auth_headers,
)


def create_editable_round(
    session: Session, organizer_email: str, organizer_password: str
):
    organizer = create_user_in_db(
        session, email=organizer_email, password=organizer_password
    )
    tournament = create_tournament_in_db(session, organizer=organizer)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    return organizer, tournament, category, round


# ---------------------------------------------------------------------------
# GET /rounds/
# ---------------------------------------------------------------------------


def test_list_rounds(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    create_round_in_db(session, category=category, name="Round A")
    create_round_in_db(session, category=category, name="Round B")

    response = client.get("/rounds/")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    names = [r["name"] for r in data]
    assert "Round A" in names
    assert "Round B" in names


def test_list_rounds_empty(client: TestClient):
    response = client.get("/rounds/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


# ---------------------------------------------------------------------------
# GET /rounds/{round_id}
# ---------------------------------------------------------------------------


def test_get_round(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(
        session, category=category, name="My Round", state=RoundState.PAUSED
    )

    response = client.get(f"/rounds/{round.id}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] == str(round.id)
    assert data["name"] == "My Round"
    assert data["state"] == "paused"
    assert data["category_id"] == str(category.id)


def test_get_round_not_found(client: TestClient):
    response = client.get("/rounds/00000000-0000-0000-0000-000000000000")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /rounds/
# ---------------------------------------------------------------------------


def test_create_round(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    tournament = create_tournament_in_db(session, organizer=organizer)
    category = create_category_in_db(session, tournament=tournament)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/rounds/",
        json={"name": "New Round", "category_id": str(category.id)},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] is not None
    assert data["name"] == "New Round"
    assert data["state"] == "not_started"
    assert data["category_id"] == str(category.id)


def test_create_round_with_state(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    tournament = create_tournament_in_db(session, organizer=organizer)
    category = create_category_in_db(session, tournament=tournament)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/rounds/",
        json={
            "name": "In Progress Round",
            "state": "in_progress",
            "category_id": str(category.id),
        },
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["state"] == "in_progress"


def test_create_round_category_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/rounds/",
        json={
            "name": "New Round",
            "category_id": "00000000-0000-0000-0000-000000000000",
        },
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_round_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.post(
        "/rounds/",
        json={"name": "New Round", "category_id": str(category.id)},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_round_as_super_admin(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.post(
        "/rounds/",
        json={"name": "Admin Round", "category_id": str(category.id)},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Admin Round"


def test_create_round_unauthenticated(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)

    response = client.post(
        "/rounds/",
        json={"name": "New Round", "category_id": str(category.id)},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_round_missing_category_id(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/rounds/",
        json={"name": "New Round"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_create_round_invalid_state(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    tournament = create_tournament_in_db(session, organizer=organizer)
    category = create_category_in_db(session, tournament=tournament)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/rounds/",
        json={
            "name": "New Round",
            "state": "invalid",
            "category_id": str(category.id),
        },
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ---------------------------------------------------------------------------
# PATCH /rounds/{round_id}
# ---------------------------------------------------------------------------


def test_update_round(session: Session, client: TestClient):
    _, _, category, round = create_editable_round(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.patch(
        f"/rounds/{round.id}",
        json={"name": "Updated Round", "state": "paused"},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["name"] == "Updated Round"
    assert data["state"] == "paused"
    assert data["category_id"] == str(category.id)


def test_update_round_partial(session: Session, client: TestClient):
    _, _, _, round = create_editable_round(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.patch(
        f"/rounds/{round.id}",
        json={"name": "Renamed Round"},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["name"] == "Renamed Round"
    assert data["state"] == "not_started"


def test_update_round_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.patch(
        "/rounds/00000000-0000-0000-0000-000000000000",
        json={"name": "Updated Round"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_round_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.patch(
        f"/rounds/{round.id}",
        json={"name": "Hacked"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_update_round_as_super_admin(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.patch(
        f"/rounds/{round.id}",
        json={"name": "Admin Updated"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Admin Updated"


def test_update_round_unauthenticated(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)

    response = client.patch(f"/rounds/{round.id}", json={"name": "Updated"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_update_round_invalid_state(session: Session, client: TestClient):
    _, _, _, round = create_editable_round(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.patch(
        f"/rounds/{round.id}",
        json={"state": "invalid"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ---------------------------------------------------------------------------
# DELETE /rounds/{round_id}
# ---------------------------------------------------------------------------


def test_delete_round(session: Session, client: TestClient):
    _, _, _, round = create_editable_round(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(f"/rounds/{round.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = client.get(f"/rounds/{round.id}")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_round_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.delete(
        "/rounds/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_round_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.delete(f"/rounds/{round.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_round_as_super_admin(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.delete(f"/rounds/{round.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_delete_round_unauthenticated(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)

    response = client.delete(f"/rounds/{round.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# GET /rounds/{round_id}/sets
# ---------------------------------------------------------------------------


def test_list_sets_in_round(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    set_a = create_set_in_db(session, round=round)
    set_b = create_set_in_db(session, round=round)

    response = client.get(f"/rounds/{round.id}/sets")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    ids = [s["id"] for s in data]
    assert str(set_a.id) in ids
    assert str(set_b.id) in ids


def test_list_sets_in_round_empty(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)

    response = client.get(f"/rounds/{round.id}/sets")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_list_sets_in_round_not_found(client: TestClient):
    response = client.get("/rounds/00000000-0000-0000-0000-000000000000/sets")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /rounds/{round_id}/start
# ---------------------------------------------------------------------------


def test_start_round(session: Session, client: TestClient):
    _, _, _, round = create_editable_round(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(f"/rounds/{round.id}/start", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["state"] == "in_progress"


def test_start_round_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/rounds/00000000-0000-0000-0000-000000000000/start",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_start_round_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.post(f"/rounds/{round.id}/start", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_start_round_unauthenticated(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)

    response = client.post(f"/rounds/{round.id}/start")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_start_round_already_started(session: Session, client: TestClient):
    _, _, _, round = create_editable_round(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    round.state = RoundState.IN_PROGRESS
    session.add(round)
    session.commit()
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(f"/rounds/{round.id}/start", headers=headers)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# POST /rounds/{round_id}/cancel-start
# ---------------------------------------------------------------------------


def test_cancel_round_start(session: Session, client: TestClient):
    _, _, _, round = create_editable_round(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    round.state = RoundState.IN_PROGRESS
    session.add(round)
    session.commit()
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(f"/rounds/{round.id}/cancel-start", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["state"] == "not_started"


def test_cancel_round_start_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/rounds/00000000-0000-0000-0000-000000000000/cancel-start",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_cancel_round_start_when_not_in_progress(session: Session, client: TestClient):
    _, _, _, round = create_editable_round(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(f"/rounds/{round.id}/cancel-start", headers=headers)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# POST /rounds/{round_id}/pause
# ---------------------------------------------------------------------------


def test_pause_round(session: Session, client: TestClient):
    _, _, _, round = create_editable_round(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    round.state = RoundState.IN_PROGRESS
    session.add(round)
    session.commit()
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(f"/rounds/{round.id}/pause", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["state"] == "paused"


def test_pause_round_when_not_in_progress(session: Session, client: TestClient):
    _, _, _, round = create_editable_round(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(f"/rounds/{round.id}/pause", headers=headers)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# POST /rounds/{round_id}/unpause
# ---------------------------------------------------------------------------


def test_unpause_round(session: Session, client: TestClient):
    _, _, _, round = create_editable_round(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    round.state = RoundState.PAUSED
    session.add(round)
    session.commit()
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(f"/rounds/{round.id}/unpause", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["state"] == "in_progress"


def test_unpause_round_when_not_paused(session: Session, client: TestClient):
    _, _, _, round = create_editable_round(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(f"/rounds/{round.id}/unpause", headers=headers)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# POST /rounds/{round_id}/finish
# ---------------------------------------------------------------------------


def test_finish_round(session: Session, client: TestClient):
    _, _, _, round = create_editable_round(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    round.state = RoundState.IN_PROGRESS
    session.add(round)
    session.commit()
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(f"/rounds/{round.id}/finish", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["state"] == "finished"


def test_finish_round_when_not_in_progress(session: Session, client: TestClient):
    _, _, _, round = create_editable_round(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(f"/rounds/{round.id}/finish", headers=headers)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# POST /rounds/{round_id}/cancel-finish
# ---------------------------------------------------------------------------


def test_cancel_round_finish(session: Session, client: TestClient):
    _, _, _, round = create_editable_round(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    round.state = RoundState.FINISHED
    session.add(round)
    session.commit()
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(f"/rounds/{round.id}/cancel-finish", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["state"] == "in_progress"


def test_cancel_round_finish_when_not_finished(session: Session, client: TestClient):
    _, _, _, round = create_editable_round(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(f"/rounds/{round.id}/cancel-finish", headers=headers)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
