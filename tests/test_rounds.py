from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from models.round import RoundState
from models.score_table import ScoreTableFormat
from tests.helpers import (
    add_player_to_score_table_in_db,
    create_category_in_db,
    create_chart_in_db,
    create_event_in_db,
    create_player_in_db,
    create_round_in_db,
    create_score_column_in_db,
    create_score_in_db,
    create_score_table_in_db,
    create_user_in_db,
    get_auth_headers,
)


def create_editable_round(
    session: Session, organizer_email: str, organizer_password: str
):
    organizer = create_user_in_db(
        session, email=organizer_email, password=organizer_password
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    round = create_round_in_db(session, category=category)
    return organizer, event, category, round


def create_score_table_with_players(
    session: Session,
    round,
    *,
    format: ScoreTableFormat = ScoreTableFormat.SCORE_SUM,
    qualifiers_count: int,
    players_scores: list[tuple[str, int]],
    score_table_order_index: int | None = None,
):
    score_table = create_score_table_in_db(
        session,
        round=round,
        qualifiers_count=qualifiers_count,
        format=format,
    )

    if score_table_order_index is not None:
        score_table.order_index = score_table_order_index
        session.add(score_table)
        session.commit()

    score_column = create_score_column_in_db(session, score_table=score_table)
    chart = create_chart_in_db(session, score_column=score_column)

    players = []
    for player_order_index, (nickname, score_value) in enumerate(players_scores):
        player = create_player_in_db(session, nickname=nickname)
        add_player_to_score_table_in_db(
            session,
            score_table=score_table,
            player=player,
            order_index=player_order_index,
        )
        create_score_in_db(
            session,
            player=player,
            score_column=score_column,
            value=score_value,
        )
        players.append(player)

    return score_table, chart, score_column, players


# ---------------------------------------------------------------------------
# GET /rounds/
# ---------------------------------------------------------------------------


def test_list_rounds(session: Session, client: TestClient):
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
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
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
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
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
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
    assert data["order_index"] == 0


def test_create_round_with_state(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
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
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
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
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.post(
        "/rounds/",
        json={"name": "Admin Round", "category_id": str(category.id)},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Admin Round"


def test_create_round_unauthenticated(session: Session, client: TestClient):
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)

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
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
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
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
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
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
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
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
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


def test_delete_round_empty(session: Session, client: TestClient):
    _, _, _, round = create_editable_round(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(f"/rounds/{round.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = client.get(f"/rounds/{round.id}", headers=headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_round_decreases_order_index(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session,
        email="organizer@example.com",
        password="mypassword123",
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    round_a = create_round_in_db(session, category=category)
    round_b = create_round_in_db(session, category=category)
    round_c = create_round_in_db(session, category=category)

    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")
    response = client.delete(f"/rounds/{round_b.id}", headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    session.refresh(round_a)
    assert round_a.order_index == 0
    session.refresh(round_c)
    assert round_c.order_index == 1


def test_delete_round_started(session: Session, client: TestClient):
    _, _, _, round = create_editable_round(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    client.post(f"/rounds/{round.id}/start", headers=headers)

    response = client.delete(f"/rounds/{round.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


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
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
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
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    round = create_round_in_db(session, category=category)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.delete(f"/rounds/{round.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_delete_round_unauthenticated(session: Session, client: TestClient):
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    round = create_round_in_db(session, category=category)

    response = client.delete(f"/rounds/{round.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_delete_category_cascade(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session,
        email="organizer@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    round = create_round_in_db(session, category=category)

    response = client.delete(f"/categories/{category.id}", headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = client.get(f"/rounds/{round.id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_event_cascade(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session,
        email="organizer@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    round = create_round_in_db(session, category=category)

    response = client.delete(f"/events/{event.id}", headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = client.get(f"/rounds/{round.id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# GET /rounds/{round_id}/score_tables
# ---------------------------------------------------------------------------


def test_list_score_tables_in_round(session: Session, client: TestClient):
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    round = create_round_in_db(session, category=category)
    score_table_a = create_score_table_in_db(session, round=round)
    score_table_b = create_score_table_in_db(session, round=round)

    response = client.get(f"/rounds/{round.id}/score_tables")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    ids = [s["id"] for s in data]
    assert str(score_table_a.id) in ids
    assert str(score_table_b.id) in ids
    assert data[0]["order_index"] == 0
    assert data[1]["order_index"] == 1


def test_list_score_tables_in_round_order_changed(session: Session, client: TestClient):
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    round = create_round_in_db(session, category=category)
    score_table_a = create_score_table_in_db(session, round=round)
    score_table_b = create_score_table_in_db(session, round=round)

    score_table_a.order_index = 1
    score_table_b.order_index = 0
    session.commit()

    response = client.get(f"/rounds/{round.id}/score_tables")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    assert data[0]["id"] == str(score_table_b.id)
    assert data[1]["id"] == str(score_table_a.id)


def test_list_score_tables_in_round_empty(session: Session, client: TestClient):
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    round = create_round_in_db(session, category=category)

    response = client.get(f"/rounds/{round.id}/score_tables")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_list_score_tables_in_round_not_found(client: TestClient):
    response = client.get("/rounds/00000000-0000-0000-0000-000000000000/score_tables")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# PUT /rounds/{round_id}/score_tables/{score_table_id}/order
# ---------------------------------------------------------------------------


def test_change_score_table_order_in_round(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    round = create_round_in_db(session, category=category)
    score_table_a = create_score_table_in_db(session, round=round)
    score_table_b = create_score_table_in_db(session, round=round)

    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/rounds/{round.id}/score_tables/{score_table_a.id}/order",
        json=[str(score_table_b.id), str(score_table_a.id)],
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    assert data[0]["id"] == str(score_table_b.id)
    assert data[1]["id"] == str(score_table_a.id)

    session.refresh(score_table_a)
    session.refresh(score_table_b)

    assert score_table_a.order_index == 1
    assert score_table_b.order_index == 0


def test_change_score_table_order_in_round_as_super_admin(
    session: Session, client: TestClient
):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    round = create_round_in_db(session, category=category)
    score_table_a = create_score_table_in_db(session, round=round)
    score_table_b = create_score_table_in_db(session, round=round)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.put(
        f"/rounds/{round.id}/score_tables/{score_table_a.id}/order",
        json=[str(score_table_b.id), str(score_table_a.id)],
        headers=headers,
    )

    session.refresh(score_table_a)
    session.refresh(score_table_b)

    assert response.status_code == status.HTTP_200_OK
    assert score_table_a.order_index == 1
    assert score_table_b.order_index == 0


def test_change_score_table_order_in_round_not_found(
    session: Session, client: TestClient
):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.put(
        "/rounds/00000000-0000-0000-0000-000000000000/score_tables/00000000-0000-0000-0000-000000000000/order",
        json=["00000000-0000-0000-0000-000000000000"],
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_change_score_table_order_in_round_unauthorized(
    session: Session, client: TestClient
):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    round = create_round_in_db(session, category=category)
    score_table_a = create_score_table_in_db(session, round=round)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.put(
        f"/rounds/{round.id}/score_tables/{score_table_a.id}/order",
        json=[str(score_table_a.id)],
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_change_score_table_order_in_round_unauthenticated(
    session: Session, client: TestClient
):
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    round = create_round_in_db(session, category=category)
    score_table_a = create_score_table_in_db(session, round=round)

    response = client.put(
        f"/rounds/{round.id}/score_tables/{score_table_a.id}/order",
        json=[str(score_table_a.id)],
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_change_score_table_order_in_round_count_mismatch(
    session: Session, client: TestClient
):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    round = create_round_in_db(session, category=category)
    score_table_a = create_score_table_in_db(session, round=round)
    create_score_table_in_db(session, round=round)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/rounds/{round.id}/score_tables/{score_table_a.id}/order",
        json=[str(score_table_a.id)],
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_change_score_table_order_in_round_repeated_score_table(
    session: Session, client: TestClient
):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    round = create_round_in_db(session, category=category)
    score_table_a = create_score_table_in_db(session, round=round)
    create_score_table_in_db(session, round=round)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/rounds/{round.id}/score_tables/{score_table_a.id}/order",
        json=[str(score_table_a.id), str(score_table_a.id)],
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_change_score_table_order_in_round_incorrect_score_table(
    session: Session, client: TestClient
):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    round = create_round_in_db(session, category=category)
    score_table_a = create_score_table_in_db(session, round=round)
    create_score_table_in_db(session, round=round)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/rounds/{round.id}/score_tables/{score_table_a.id}/order",
        json=[str(score_table_a.id), "00000000-0000-0000-0000-000000000000"],
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# DELETE /rounds/{round_id}/scores
# ---------------------------------------------------------------------------


def test_delete_all_scores_in_round(session: Session, client: TestClient):
    _, _, _, round = create_editable_round(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    score_table, _, _, _ = create_score_table_with_players(
        session=session,
        round=round,
        format=ScoreTableFormat.SCORE_SUM,
        qualifiers_count=1,
        players_scores=[
            ("player1", 100),
            ("player2", 200),
            ("player3", 300),
        ],
    )

    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")
    response = client.delete(f"/rounds/{round.id}/scores", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    session.refresh(score_table)

    assert score_table.score_columns[0].scores == []


def test_delete_all_scores_in_round_empty_score_table(
    session: Session, client: TestClient
):
    _, _, _, round = create_editable_round(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    score_table, _, _, _ = create_score_table_with_players(
        session=session,
        round=round,
        format=ScoreTableFormat.SCORE_SUM,
        qualifiers_count=1,
        players_scores=[],
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")
    response = client.delete(f"/rounds/{round.id}/scores", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    session.refresh(score_table)
    assert score_table.score_columns[0].scores == []


def test_delete_all_scores_in_round_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.delete(
        "/rounds/00000000-0000-0000-0000-000000000000/scores",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_all_scores_in_round_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    round = create_round_in_db(session, category=category)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.delete(f"/rounds/{round.id}/scores", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_all_scores_in_round_as_super_admin(
    session: Session, client: TestClient
):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    round = create_round_in_db(session, category=category)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.delete(f"/rounds/{round.id}/scores", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_delete_all_scores_in_round_unauthenticated(
    session: Session, client: TestClient
):
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    round = create_round_in_db(session, category=category)

    response = client.delete(f"/rounds/{round.id}/scores")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


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
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    round = create_round_in_db(session, category=category)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.post(f"/rounds/{round.id}/start", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_start_round_unauthenticated(session: Session, client: TestClient):
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
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


# ---------------------------------------------------------------------------
# GET /rounds/{round_id}/qualifying-players
# ---------------------------------------------------------------------------


def test_get_qualifying_players_in_round(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    round = create_round_in_db(session, category=category)

    score_table_a, _, _, score_table_a_players = create_score_table_with_players(
        session,
        round,
        qualifiers_count=1,
        players_scores=[
            ("Score Table A Player 1", 1000000),
            ("Score Table A Player 2", 950000),
        ],
    )

    score_table_b, _, _, score_table_b_players = create_score_table_with_players(
        session,
        round,
        qualifiers_count=2,
        players_scores=[
            ("Score Table B Player 1", 900000),
            ("Score Table B Player 2", 800000),
            ("Score Table B Player 3", 1000000),
        ],
    )

    response = client.get(f"/rounds/{round.id}/qualifying-players", headers=headers)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [player["nickname"] for player in data] == [
        score_table_a_players[0].nickname,
        score_table_b_players[2].nickname,
        score_table_b_players[0].nickname,
    ]
    assert [player["id"] for player in data] == [
        str(score_table_a_players[0].id),
        str(score_table_b_players[2].id),
        str(score_table_b_players[0].id),
    ]
    assert len(data) == 3


def test_get_qualifying_players_in_round_two_battles(
    session: Session, client: TestClient
):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    round = create_round_in_db(session, category=category)

    score_table_a, _, _, score_table_a_players = create_score_table_with_players(
        session,
        round,
        format=ScoreTableFormat.BATTLE,
        qualifiers_count=1,
        players_scores=[
            ("Score Table A Player 1", 950000),
            ("Score Table A Player 2", 1000000),
        ],
    )

    score_table_b, _, _, score_table_b_players = create_score_table_with_players(
        session,
        round,
        format=ScoreTableFormat.BATTLE,
        qualifiers_count=1,
        players_scores=[
            ("Score Table B Player 1", 900000),
            ("Score Table B Player 2", 800000),
        ],
    )

    response = client.get(f"/rounds/{round.id}/qualifying-players", headers=headers)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [player["nickname"] for player in data] == [
        score_table_a_players[1].nickname,
        score_table_b_players[0].nickname,
    ]
    assert [player["id"] for player in data] == [
        str(score_table_a_players[1].id),
        str(score_table_b_players[0].id),
    ]
    assert len(data) == 2


def test_get_qualifying_players_in_round_not_found(
    session: Session, client: TestClient
):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.get(
        "/rounds/00000000-0000-0000-0000-000000000000/qualifying-players",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_qualifying_players_in_round_unauthenticated(
    session: Session, client: TestClient
):
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    round = create_round_in_db(session, category=category)

    response = client.get(f"/rounds/{round.id}/qualifying-players")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
