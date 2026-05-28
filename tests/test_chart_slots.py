import uuid

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from models.round import RoundState
from models.score_column import ScoreColumn
from tests.helpers import (
    create_category_in_db,
    create_chart_in_db,
    create_chart_slot_in_db,
    create_round_in_db,
    create_score_table_in_db,
    create_tournament_in_db,
    create_user_in_db,
    get_auth_headers,
)


def create_editable_chart_slot_context(
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
    chart = create_chart_in_db(session, score_table, song_name="Chart A", level=10)
    return organizer, tournament, category, round, score_table, chart


# ---------------------------------------------------------------------------
# GET /chart_slots/
# ---------------------------------------------------------------------------


def test_list_chart_slots(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    _, _, _, _, score_table, chart_a = create_editable_chart_slot_context(session)
    chart_b = create_chart_in_db(session, score_table, song_name="Chart B", level=12)
    slot_a = create_chart_slot_in_db(session, score_table, chart=chart_a, order_index=0)
    slot_b = create_chart_slot_in_db(
        session,
        score_table,
        chart=chart_b,
        order_index=1,
        description="Chart B description",
    )

    headers = get_auth_headers(client, "user@example.com", "mypassword123")
    response = client.get("/chart_slots/", headers=headers)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    assert {item["id"] for item in data} == {str(slot_a.id), str(slot_b.id)}
    assert sorted(item["order_index"] for item in data) == [0, 1]
    assert data[0]["description"] is None
    assert data[1]["description"] == "Chart B description"


def test_list_chart_slots_empty(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.get("/chart_slots/", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_list_chart_slots_unauthorized(client: TestClient):
    response = client.get("/chart_slots/")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# POST /chart_slots/
# ---------------------------------------------------------------------------


def test_create_chart_slot(session: Session, client: TestClient):
    _, _, _, _, score_table, chart = create_editable_chart_slot_context(session)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/chart_slots/",
        json={"score_table_id": str(score_table.id), "chart_id": str(chart.id)},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["score_table_id"] == str(score_table.id)
    assert data["chart_id"] == str(chart.id)
    assert data["order_index"] == 0
    assert data["description"] is None

    created_slot = session.get(ScoreColumn, uuid.UUID(data["id"]))
    assert created_slot is not None
    assert created_slot.order_index == 0
    assert created_slot.description is None


def test_create_chart_slot_without_chart(session: Session, client: TestClient):
    _, _, _, _, score_table, _ = create_editable_chart_slot_context(session)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/chart_slots/",
        json={
            "score_table_id": str(score_table.id),
            "description": "Custom chart",
        },
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["score_table_id"] == str(score_table.id)
    assert data["chart_id"] is None
    assert data["order_index"] == 0
    assert data["description"] == "Custom chart"


def test_create_chart_slot_score_table_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/chart_slots/",
        json={
            "score_table_id": "00000000-0000-0000-0000-000000000000",
            "chart_id": None,
        },
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_chart_slot_forbidden(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    _, _, _, _, score_table, chart = create_editable_chart_slot_context(session)

    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")
    response = client.post(
        "/chart_slots/",
        json={"score_table_id": str(score_table.id), "chart_id": str(chart.id)},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_chart_slot_chart_not_found(session: Session, client: TestClient):
    _, _, _, _, score_table, _ = create_editable_chart_slot_context(session)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/chart_slots/",
        json={
            "score_table_id": str(score_table.id),
            "chart_id": "00000000-0000-0000-0000-000000000000",
        },
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_chart_slot_appends_to_existing_slots(
    session: Session, client: TestClient
):
    _, _, _, _, score_table, first_chart = create_editable_chart_slot_context(session)
    second_chart = create_chart_in_db(
        session, score_table, song_name="Chart B", level=12
    )
    create_chart_slot_in_db(session, score_table, chart=first_chart, order_index=0)

    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")
    response = client.post(
        "/chart_slots/",
        json={"score_table_id": str(score_table.id), "chart_id": str(second_chart.id)},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["order_index"] == 1
    assert data["chart_id"] == str(second_chart.id)


def test_create_chart_slot_unauthenticated(session: Session, client: TestClient):
    _, _, _, _, score_table, chart = create_editable_chart_slot_context(session)

    response = client.post(
        "/chart_slots/",
        json={"score_table_id": str(score_table.id), "chart_id": str(chart.id)},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# GET /chart_slots/{chart_slot_id}
# ---------------------------------------------------------------------------


def test_get_chart_slot(session: Session, client: TestClient):
    _, _, _, _, score_table, chart = create_editable_chart_slot_context(session)
    chart_slot = create_chart_slot_in_db(
        session, score_table, chart=chart, order_index=0
    )

    response = client.get(f"/chart_slots/{chart_slot.id}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] == str(chart_slot.id)
    assert data["score_table_id"] == str(score_table.id)
    assert data["chart_id"] == str(chart.id)
    assert data["order_index"] == 0


def test_get_chart_slot_not_found(client: TestClient):
    response = client.get("/chart_slots/00000000-0000-0000-0000-000000000000")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# PATCH /chart_slots/{chart_slot_id}
# ---------------------------------------------------------------------------


def test_update_chart_slot(session: Session, client: TestClient):
    _, _, _, _, score_table, chart_a = create_editable_chart_slot_context(session)
    chart_b = create_chart_in_db(session, score_table, song_name="Chart B", level=12)
    chart_slot = create_chart_slot_in_db(
        session, score_table, chart=chart_a, order_index=0
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.patch(
        f"/chart_slots/{chart_slot.id}",
        json={"chart_id": str(chart_b.id)},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] == str(chart_slot.id)
    assert data["score_table_id"] == str(score_table.id)
    assert data["chart_id"] == str(chart_b.id)
    assert data["order_index"] == 0


def test_update_chart_slot_chart_not_found(session: Session, client: TestClient):
    _, _, _, _, score_table, chart = create_editable_chart_slot_context(session)
    chart_slot = create_chart_slot_in_db(
        session, score_table, chart=chart, order_index=0
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.patch(
        f"/chart_slots/{chart_slot.id}",
        json={"chart_id": "00000000-0000-0000-0000-000000000000"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_chart_slot_chart_not_in_score_table(
    session: Session, client: TestClient
):
    _, _, _, round, score_table, chart = create_editable_chart_slot_context(session)
    chart_slot = create_chart_slot_in_db(
        session, score_table, chart=chart, order_index=0
    )

    other_score_table = create_score_table_in_db(session, round=round)
    other_chart = create_chart_in_db(
        session, other_score_table, song_name="Other", level=9
    )

    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")
    response = client.patch(
        f"/chart_slots/{chart_slot.id}",
        json={"chart_id": str(other_chart.id)},
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_update_chart_slot_forbidden(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    _, _, _, _, score_table, chart = create_editable_chart_slot_context(session)
    chart_slot = create_chart_slot_in_db(
        session, score_table, chart=chart, order_index=0
    )
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.patch(
        f"/chart_slots/{chart_slot.id}",
        json={"chart_id": str(chart.id)},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_update_chart_slot_as_super_admin(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    _, _, _, _, score_table, chart_a = create_editable_chart_slot_context(session)
    chart_b = create_chart_in_db(session, score_table, song_name="Chart B", level=12)
    chart_slot = create_chart_slot_in_db(
        session, score_table, chart=chart_a, order_index=0
    )
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.patch(
        f"/chart_slots/{chart_slot.id}",
        json={"chart_id": str(chart_b.id)},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["chart_id"] == str(chart_b.id)


def test_update_chart_slot_unauthenticated(session: Session, client: TestClient):
    _, _, _, _, score_table, chart = create_editable_chart_slot_context(session)
    chart_slot = create_chart_slot_in_db(
        session, score_table, chart=chart, order_index=0
    )

    response = client.patch(
        f"/chart_slots/{chart_slot.id}",
        json={"chart_id": str(chart.id)},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# DELETE /chart_slots/{chart_slot_id}
# ---------------------------------------------------------------------------


def test_delete_chart_slot(session: Session, client: TestClient):
    _, _, _, _, score_table, chart_a = create_editable_chart_slot_context(session)
    chart_b = create_chart_in_db(session, score_table, song_name="Chart B", level=12)
    chart_c = create_chart_in_db(session, score_table, song_name="Chart C", level=14)
    slot_a = create_chart_slot_in_db(session, score_table, chart=chart_a, order_index=0)
    slot_b = create_chart_slot_in_db(session, score_table, chart=chart_b, order_index=1)
    slot_c = create_chart_slot_in_db(session, score_table, chart=chart_c, order_index=2)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(f"/chart_slots/{slot_b.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert session.get(ScoreColumn, slot_b.id) is None
    assert session.get(ScoreColumn, slot_a.id).order_index == 0
    assert session.get(ScoreColumn, slot_c.id).order_index == 1


def test_delete_chart_slot_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.delete(
        "/chart_slots/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Chart slot not found"


def test_delete_chart_slot_forbidden(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    _, _, _, _, score_table, chart = create_editable_chart_slot_context(session)
    chart_slot = create_chart_slot_in_db(
        session, score_table, chart=chart, order_index=0
    )
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.delete(f"/chart_slots/{chart_slot.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "You are not allowed to delete this chart slot"


def test_delete_chart_slot_forbidden_when_round_finished(
    session: Session, client: TestClient
):
    create_user_in_db(session, email="organizer@example.com", password="mypassword123")
    _, _, _, _, score_table, chart = create_editable_chart_slot_context(
        session, round_state=RoundState.FINISHED
    )
    chart_slot = create_chart_slot_in_db(
        session, score_table, chart=chart, order_index=0
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(f"/chart_slots/{chart_slot.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_chart_slot_as_super_admin(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    _, _, _, _, score_table, chart = create_editable_chart_slot_context(
        session, round_state=RoundState.FINISHED
    )
    chart_slot = create_chart_slot_in_db(
        session, score_table, chart=chart, order_index=0
    )
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.delete(f"/chart_slots/{chart_slot.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert session.get(ScoreColumn, chart_slot.id) is None


def test_delete_chart_slot_unauthenticated(session: Session, client: TestClient):
    _, _, _, _, score_table, chart = create_editable_chart_slot_context(session)
    chart_slot = create_chart_slot_in_db(
        session, score_table, chart=chart, order_index=0
    )

    response = client.delete(f"/chart_slots/{chart_slot.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
