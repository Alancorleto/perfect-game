import uuid

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from models.chart_column import ChartColumn
from models.round import RoundState
from tests.helpers import (
    create_category_in_db,
    create_chart_column_in_db,
    create_round_in_db,
    create_score_column_in_db,
    create_score_table_in_db,
    create_tournament_in_db,
    create_user_in_db,
    get_auth_headers,
)


def create_editable_chart_column_context(
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
    tournament = create_tournament_in_db(session, organizer=organizer)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category, state=round_state)
    score_table = create_score_table_in_db(session, round=round)
    score_column = create_score_column_in_db(session, score_table=score_table)

    return organizer, tournament, category, round, score_table, score_column


# ---------------------------------------------------------------------------
# GET /chart_columns/
# ---------------------------------------------------------------------------


def test_list_chart_columns(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    _, _, _, _, score_table, score_column_a = create_editable_chart_column_context(
        session
    )
    score_column_b = create_score_column_in_db(session, score_table=score_table)
    chart_column_a = create_chart_column_in_db(
        session,
        score_column=score_column_a,
        description=None,
    )
    chart_column_b = create_chart_column_in_db(
        session,
        score_column=score_column_b,
        description="Second chart column",
    )

    response = client.get("/chart_columns/")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    assert {item["id"] for item in data} == {
        str(chart_column_a.id),
        str(chart_column_b.id),
    }
    assert {item["score_column_id"] for item in data} == {
        str(score_column_a.id),
        str(score_column_b.id),
    }
    assert {item["description"] for item in data} == {
        None,
        "Second chart column",
    }


def test_list_chart_columns_empty(session: Session, client: TestClient):
    response = client.get("/chart_columns/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


# ---------------------------------------------------------------------------
# POST /chart_columns/
# ---------------------------------------------------------------------------


def test_create_chart_column(session: Session, client: TestClient):
    organizer, _, _, _, score_table, score_column = (
        create_editable_chart_column_context(session)
    )
    headers = get_auth_headers(client, organizer.email, "mypassword123")

    response = client.post(
        "/chart_columns/",
        json={
            "score_column_id": str(score_column.id),
            "description": "My chart column",
        },
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["score_column_id"] == str(score_column.id)
    assert data["description"] == "My chart column"
    assert session.get(ChartColumn, uuid.UUID(data["id"])) is not None


def test_create_chart_column_score_column_not_found(
    session: Session, client: TestClient
):
    create_user_in_db(session, email="organizer@example.com", password="mypassword123")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/chart_columns/",
        json={"score_column_id": "00000000-0000-0000-0000-000000000000"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_chart_column_forbidden(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    _, _, _, _, _, score_column = create_editable_chart_column_context(session)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.post(
        "/chart_columns/",
        json={"score_column_id": str(score_column.id)},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_chart_column_when_score_column_already_has_one(
    session: Session, client: TestClient
):
    organizer, _, _, _, _, score_column = create_editable_chart_column_context(session)
    create_chart_column_in_db(session, score_column)

    headers = get_auth_headers(client, organizer.email, "mypassword123")
    response = client.post(
        "/chart_columns/",
        json={"score_column_id": str(score_column.id)},
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_create_chart_column_unauthenticated(session: Session, client: TestClient):
    _, _, _, _, _, score_column = create_editable_chart_column_context(session)

    response = client.post(
        "/chart_columns/",
        json={"score_column_id": str(score_column.id)},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# GET /chart_columns/{chart_column_id}
# ---------------------------------------------------------------------------


def test_get_chart_column(session: Session, client: TestClient):
    _, _, _, _, _, score_column = create_editable_chart_column_context(session)
    chart_column = create_chart_column_in_db(
        session,
        score_column=score_column,
        description="Original",
    )

    response = client.get(f"/chart_columns/{chart_column.id}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] == str(chart_column.id)
    assert data["score_column_id"] == str(score_column.id)
    assert data["description"] == "Original"


def test_get_chart_column_not_found(client: TestClient):
    response = client.get("/chart_columns/00000000-0000-0000-0000-000000000000")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# PATCH /chart_columns/{chart_column_id}
# ---------------------------------------------------------------------------


def test_update_chart_column(session: Session, client: TestClient):
    organizer, _, _, _, _, score_column = create_editable_chart_column_context(session)
    chart_column = create_chart_column_in_db(
        session,
        score_column=score_column,
        description="Original",
    )

    headers = get_auth_headers(client, organizer.email, "mypassword123")
    response = client.patch(
        f"/chart_columns/{chart_column.id}",
        json={"description": "Updated description"},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] == str(chart_column.id)
    assert data["description"] == "Updated description"


def test_update_chart_column_forbidden(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    _, _, _, _, _, score_column = create_editable_chart_column_context(session)
    chart_column = create_chart_column_in_db(
        session,
        score_column=score_column,
        description="Original",
    )

    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")
    response = client.patch(
        f"/chart_columns/{chart_column.id}",
        json={"description": "Updated description"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_update_chart_column_as_super_admin(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    _, _, _, _, _, score_column = create_editable_chart_column_context(session)
    chart_column = create_chart_column_in_db(
        session,
        score_column=score_column,
        description="Original",
    )

    headers = get_auth_headers(client, "admin@example.com", "mypassword123")
    response = client.patch(
        f"/chart_columns/{chart_column.id}",
        json={"description": "Updated by admin"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["description"] == "Updated by admin"


def test_update_chart_column_not_found(session: Session, client: TestClient):
    organizer, _, _, _, _, _ = create_editable_chart_column_context(session)
    headers = get_auth_headers(client, organizer.email, "mypassword123")

    response = client.patch(
        "/chart_columns/00000000-0000-0000-0000-000000000000",
        json={"description": "Updated description"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_chart_column_unauthenticated(session: Session, client: TestClient):
    _, _, _, _, _, score_column = create_editable_chart_column_context(session)
    chart_column = create_chart_column_in_db(
        session,
        score_column=score_column,
        description="Original",
    )

    response = client.patch(
        f"/chart_columns/{chart_column.id}",
        json={"description": "Updated description"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# DELETE /chart_columns/{chart_column_id}
# ---------------------------------------------------------------------------


def test_delete_chart_column(session: Session, client: TestClient):
    organizer, _, _, _, _, score_column = create_editable_chart_column_context(session)
    chart_column = create_chart_column_in_db(
        session,
        score_column=score_column,
        description="Delete me",
    )

    headers = get_auth_headers(client, organizer.email, "mypassword123")
    response = client.delete(f"/chart_columns/{chart_column.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert session.get(ChartColumn, chart_column.id) is None


def test_delete_chart_column_forbidden_when_round_finished(
    session: Session, client: TestClient
):
    organizer, _, _, _, _, score_column = create_editable_chart_column_context(
        session, round_state=RoundState.FINISHED
    )
    chart_column = create_chart_column_in_db(
        session,
        score_column=score_column,
        description="Locked",
    )

    headers = get_auth_headers(client, organizer.email, "mypassword123")
    response = client.delete(f"/chart_columns/{chart_column.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_chart_column_as_super_admin_when_round_finished(
    session: Session, client: TestClient
):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    _, _, _, _, _, score_column = create_editable_chart_column_context(
        session, round_state=RoundState.FINISHED
    )
    chart_column = create_chart_column_in_db(
        session,
        score_column=score_column,
        description="Delete me",
    )

    headers = get_auth_headers(client, "admin@example.com", "mypassword123")
    response = client.delete(f"/chart_columns/{chart_column.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert session.get(ChartColumn, chart_column.id) is None


def test_delete_chart_column_not_found(session: Session, client: TestClient):
    organizer, _, _, _, _, _ = create_editable_chart_column_context(session)
    headers = get_auth_headers(client, organizer.email, "mypassword123")

    response = client.delete(
        "/chart_columns/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_chart_column_forbidden(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    _, _, _, _, _, score_column = create_editable_chart_column_context(session)
    chart_column = create_chart_column_in_db(
        session,
        score_column=score_column,
        description="Delete me",
    )
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.delete(f"/chart_columns/{chart_column.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_chart_column_unauthenticated(session: Session, client: TestClient):
    _, _, _, _, _, score_column = create_editable_chart_column_context(session)
    chart_column = create_chart_column_in_db(
        session,
        score_column=score_column,
        description="Delete me",
    )

    response = client.delete(f"/chart_columns/{chart_column.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
