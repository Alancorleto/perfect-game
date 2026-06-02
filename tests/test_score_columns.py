import uuid

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from models.round import RoundState
from models.score_column import ScoreColumn
from tests.helpers import (
    create_category_in_db,
    create_chart_in_db,
    create_event_in_db,
    create_round_in_db,
    create_score_column_in_db,
    create_score_table_in_db,
    create_user_in_db,
    get_auth_headers,
)


def create_editable_score_column_context(
    session: Session,
    organizer_email: str = "organizer@example.com",
    organizer_password: str = "mypassword123",
    round_state: RoundState = RoundState.NOT_STARTED,
):
    organizer = create_user_in_db(
        session,
        email=organizer_email,
        password=organizer_password,
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    round = create_round_in_db(session, category=category, state=round_state)
    score_table = create_score_table_in_db(session, round=round)
    return organizer, event, category, round, score_table


# ---------------------------------------------------------------------------
# GET /score_columns/
# ---------------------------------------------------------------------------


def test_list_score_columns(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    _, _, _, _, score_table = create_editable_score_column_context(session)
    column_a = create_score_column_in_db(session, score_table, order_index=0)
    column_b = create_score_column_in_db(
        session,
        score_table,
        order_index=1,
        description="Chart B description",
    )
    create_chart_in_db(session, song_name="Chart A", level=10, score_column=column_a)
    create_chart_in_db(session, song_name="Chart B", level=12, score_column=column_b)

    headers = get_auth_headers(client, "user@example.com", "mypassword123")
    response = client.get("/score_columns/", headers=headers)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    assert {item["id"] for item in data} == {str(column_a.id), str(column_b.id)}
    assert sorted(item["order_index"] for item in data) == [0, 1]
    assert data[0]["description"] is None
    assert data[1]["description"] == "Chart B description"


def test_list_score_columns_empty(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.get("/score_columns/", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


# ---------------------------------------------------------------------------
# POST /score_columns/
# ---------------------------------------------------------------------------


def test_create_score_column(session: Session, client: TestClient):
    _, _, _, _, score_table = create_editable_score_column_context(session)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/score_columns/",
        json={"score_table_id": str(score_table.id)},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["score_table_id"] == str(score_table.id)
    assert data["order_index"] == 0
    assert data["description"] is None

    created_column = session.get(ScoreColumn, uuid.UUID(data["id"]))
    assert created_column is not None
    assert created_column.order_index == 0
    assert created_column.description is None


def test_create_score_column_score_table_not_found(
    session: Session, client: TestClient
):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/score_columns/",
        json={
            "score_table_id": "00000000-0000-0000-0000-000000000000",
        },
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_score_column_forbidden(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    _, _, _, _, score_table = create_editable_score_column_context(session)

    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")
    response = client.post(
        "/score_columns/",
        json={"score_table_id": str(score_table.id)},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_score_column_appends_to_existing_columns(
    session: Session, client: TestClient
):
    _, _, _, _, score_table = create_editable_score_column_context(session)

    create_score_column_in_db(session, score_table, order_index=0)

    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")
    response = client.post(
        "/score_columns/",
        json={"score_table_id": str(score_table.id)},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["order_index"] == 1


def test_create_score_column_unauthenticated(session: Session, client: TestClient):
    _, _, _, _, score_table = create_editable_score_column_context(session)

    response = client.post(
        "/score_columns/",
        json={"score_table_id": str(score_table.id)},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# GET /score_columns/{score_column_id}
# ---------------------------------------------------------------------------


def test_get_score_column(session: Session, client: TestClient):
    _, _, _, _, score_table = create_editable_score_column_context(session)
    score_column = create_score_column_in_db(session, score_table, order_index=0)

    response = client.get(f"/score_columns/{score_column.id}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] == str(score_column.id)
    assert data["score_table_id"] == str(score_table.id)
    assert data["order_index"] == 0


def test_get_score_column_not_found(client: TestClient):
    response = client.get("/score_columns/00000000-0000-0000-0000-000000000000")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# PATCH /score_columns/{score_column_id}
# ---------------------------------------------------------------------------


def test_update_score_column(session: Session, client: TestClient):
    _, _, _, _, score_table = create_editable_score_column_context(session)
    score_column = create_score_column_in_db(session, score_table, order_index=0)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.patch(
        f"/score_columns/{score_column.id}",
        json={"description": "Changed description"},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] == str(score_column.id)
    assert data["score_table_id"] == str(score_table.id)
    assert data["description"] == "Changed description"


def test_update_score_column_forbidden(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    _, _, _, _, score_table = create_editable_score_column_context(session)
    score_column = create_score_column_in_db(session, score_table, order_index=0)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.patch(
        f"/score_columns/{score_column.id}",
        json={"description": "Changed description"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_update_score_column_as_super_admin(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    _, _, _, _, score_table = create_editable_score_column_context(session)
    score_column = create_score_column_in_db(session, score_table, order_index=0)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.patch(
        f"/score_columns/{score_column.id}",
        json={"description": "Changed description"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["description"] == "Changed description"


def test_update_score_column_unauthenticated(session: Session, client: TestClient):
    _, _, _, _, score_table = create_editable_score_column_context(session)
    score_column = create_score_column_in_db(session, score_table, order_index=0)

    response = client.patch(
        f"/score_columns/{score_column.id}",
        json={"description": "Changed description"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# DELETE /score_columns/{score_column_id}
# ---------------------------------------------------------------------------


def test_delete_score_column(session: Session, client: TestClient):
    _, _, _, _, score_table = create_editable_score_column_context(session)
    column_a = create_score_column_in_db(session, score_table, order_index=0)
    column_b = create_score_column_in_db(session, score_table, order_index=1)
    column_c = create_score_column_in_db(session, score_table, order_index=2)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(f"/score_columns/{column_b.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert session.get(ScoreColumn, column_b.id) is None
    assert session.get(ScoreColumn, column_a.id).order_index == 0
    assert session.get(ScoreColumn, column_c.id).order_index == 1


def test_delete_score_column_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.delete(
        "/score_columns/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_score_column_forbidden(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    _, _, _, _, score_table = create_editable_score_column_context(session)
    score_column = create_score_column_in_db(session, score_table, order_index=0)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.delete(f"/score_columns/{score_column.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_score_column_forbidden_when_round_finished(
    session: Session, client: TestClient
):
    create_user_in_db(session, email="organizer@example.com", password="mypassword123")
    _, _, _, _, score_table = create_editable_score_column_context(
        session, round_state=RoundState.FINISHED
    )
    score_column = create_score_column_in_db(session, score_table, order_index=0)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(f"/score_columns/{score_column.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_score_column_as_super_admin(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    _, _, _, _, score_table = create_editable_score_column_context(
        session, round_state=RoundState.FINISHED
    )
    score_column = create_score_column_in_db(session, score_table, order_index=0)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.delete(f"/score_columns/{score_column.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert session.get(ScoreColumn, score_column.id) is None


def test_delete_score_column_unauthenticated(session: Session, client: TestClient):
    _, _, _, _, score_table = create_editable_score_column_context(session)
    score_column = create_score_column_in_db(session, score_table, order_index=0)

    response = client.delete(f"/score_columns/{score_column.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
