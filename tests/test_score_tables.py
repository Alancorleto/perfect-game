from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from models import score_column
from models.round import RoundState
from models.score_table import ScoreTableFormat
from tests.helpers import (
    add_player_to_score_table_in_db as add_player_to_score_table_in_db,
)
from tests.helpers import (
    create_category_in_db,
    create_chart_in_db,
    create_chart_slot_in_db,
    create_player_in_db,
    create_round_in_db,
    create_score_in_db,
    create_tournament_in_db,
    create_user_in_db,
    get_auth_headers,
)
from tests.helpers import (
    create_score_table_in_db as create_score_table_in_db,
)


def create_editable_score_table(
    session: Session, organizer_email: str, organizer_password: str
):
    organizer = create_user_in_db(
        session, email=organizer_email, password=organizer_password
    )
    tournament = create_tournament_in_db(session, organizer=organizer)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    score_table = create_score_table_in_db(session, round=round)
    return organizer, tournament, category, round, score_table


# ---------------------------------------------------------------------------
# GET /score_tables/
# ---------------------------------------------------------------------------


def test_create_score_table(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    tournament = create_tournament_in_db(session, organizer=organizer)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/score_tables/",
        json={
            "round_id": str(round.id),
            "qualifiers_count": 4,
            "format": "score_sum",
        },
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] is not None
    assert data["round_id"] == str(round.id)


def test_create_score_table_round_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/score_tables/",
        json={"round_id": "00000000-0000-0000-0000-000000000000"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_score_table_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.post(
        "/score_tables/",
        json={"round_id": str(round.id)},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_score_table_as_super_admin(session: Session, client: TestClient):
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

    response = client.post(
        "/score_tables/",
        json={"round_id": str(round.id)},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["round_id"] == str(round.id)


def test_create_score_table_unauthenticated(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)

    response = client.post("/score_tables/", json={"round_id": str(round.id)})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_score_table_invalid_qualifiers_count(
    session: Session, client: TestClient
):
    _, _, _, round, _ = create_editable_score_table(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/score_tables/",
        json={"round_id": str(round.id), "qualifiers_count": 0},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ---------------------------------------------------------------------------
# GET /score_tables/
# ---------------------------------------------------------------------------


def test_list_score_tables(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    score_table_a = create_score_table_in_db(session, round=round)
    score_table_b = create_score_table_in_db(session, round=round)

    response = client.get("/score_tables/")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    ids = [s["id"] for s in data]
    assert str(score_table_a.id) in ids
    assert str(score_table_b.id) in ids


def test_list_score_tables_empty(client: TestClient):
    response = client.get("/score_tables/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


# ---------------------------------------------------------------------------
# GET /score_tables/{score_table_id}
# ---------------------------------------------------------------------------


def test_get_score_table(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    score_table = create_score_table_in_db(session, round=round)

    response = client.get(f"/score_tables/{score_table.id}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] == str(score_table.id)
    assert data["round_id"] == str(round.id)


def test_get_score_table_not_found(client: TestClient):
    response = client.get("/score_tables/00000000-0000-0000-0000-000000000000")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# PATCH /score_tables/{score_table_id}
# ---------------------------------------------------------------------------


def test_update_score_table(session: Session, client: TestClient):
    _, _, _, _, score_table = create_editable_score_table(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.patch(
        f"/score_tables/{score_table.id}",
        json={"qualifiers_count": 2, "format": "custom_set"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(score_table.id)


def test_update_score_table_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.patch(
        "/score_tables/00000000-0000-0000-0000-000000000000",
        json={"qualifiers_count": 2, "format": "custom_set"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_score_table_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    score_table = create_score_table_in_db(session, round=round)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.patch(
        f"/score_tables/{score_table.id}",
        json={"qualifiers_count": 2, "format": "custom_set"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_update_score_table_as_super_admin(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    score_table = create_score_table_in_db(session, round=round)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.patch(
        f"/score_tables/{score_table.id}",
        json={"qualifiers_count": 2, "format": "custom_set"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK


def test_update_score_table_unauthenticated(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    score_table = create_score_table_in_db(session, round=round)

    response = client.patch(
        f"/score_tables/{score_table.id}",
        json={"qualifiers_count": 2, "format": "custom_set"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_update_score_table_invalid_format(session: Session, client: TestClient):
    _, _, _, _, score_table = create_editable_score_table(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.patch(
        f"/score_tables/{score_table.id}",
        json={"format": "invalid"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ---------------------------------------------------------------------------
# DELETE /score_tables/{score_table_id}
# ---------------------------------------------------------------------------


def test_delete_score_table_empty(session: Session, client: TestClient):
    _, _, _, _, score_table = create_editable_score_table(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(f"/score_tables/{score_table.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = client.get(f"/score_tables/{score_table.id}", headers=headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_score_table_with_score(session: Session, client: TestClient):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    player = create_player_in_db(session, user=user)

    _, _, _, round, score_table = create_editable_score_table(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )

    chart = create_chart_in_db(session, score_table, song_name="Song", level=10)

    chart_slot = create_chart_slot_in_db(session, score_table, chart=chart)

    round.state = RoundState.IN_PROGRESS
    session.commit()

    create_score_in_db(
        session,
        player=player,
        chart=chart,
        chart_slot=chart_slot,
        value=1_000_000,
    )

    response = client.delete(f"/score_tables/{score_table.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_score_table_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.delete(
        "/score_tables/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_score_table_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    score_table = create_score_table_in_db(session, round=round)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.delete(f"/score_tables/{score_table.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_score_table_as_super_admin(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    score_table = create_score_table_in_db(session, round=round)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.delete(f"/score_tables/{score_table.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_delete_score_table_unauthenticated(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    score_table = create_score_table_in_db(session, round=round)

    response = client.delete(f"/score_tables/{score_table.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_delete_round_cascade(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session,
        email="organizer@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")
    tournament = create_tournament_in_db(session, organizer=organizer)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    score_table = create_score_table_in_db(session, round=round)

    response = client.delete(f"/rounds/{round.id}", headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = client.get(f"/score_tables/{score_table.id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_tournament_cascade(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session,
        email="organizer@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")
    tournament = create_tournament_in_db(session, organizer=organizer)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    score_table = create_score_table_in_db(session, round=round)

    response = client.delete(f"/tournaments/{tournament.id}", headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = client.get(f"/score_tables/{score_table.id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# GET /score_tables/{score_table_id}/charts
# ---------------------------------------------------------------------------


def test_list_chart_slots_for_score_table(session: Session, client: TestClient):
    organizer, _, _, _, score_table = create_editable_score_table(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    chart_a = create_chart_in_db(session, score_table, song_name="Song A")
    chart_b = create_chart_in_db(session, score_table, song_name="Song B")
    create_chart_slot_in_db(session, score_table, chart=chart_a, order_index=0)
    create_chart_slot_in_db(session, score_table, chart=chart_b, order_index=1)

    response = client.get(f"/score_tables/{score_table.id}/chart_slots")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    names = [c["chart"]["song_name"] for c in data]
    assert names[0] == "Song A"
    assert names[1] == "Song B"


def test_list_charts_for_score_table_empty(session: Session, client: TestClient):
    _, _, _, _, score_table = create_editable_score_table(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )

    response = client.get(f"/score_tables/{score_table.id}/chart_slots")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_list_charts_for_score_table_not_found(client: TestClient):
    response = client.get(
        "/score_tables/00000000-0000-0000-0000-000000000000/chart_slots"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# PUT /score_tables/{score_table_id}/charts/order
# ---------------------------------------------------------------------------


def test_update_chart_order_in_score_table(session: Session, client: TestClient):
    organizer, _, _, _, score_table = create_editable_score_table(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    chart_a = create_chart_in_db(session, score_table, song_name="Song A")
    chart_b = create_chart_in_db(session, score_table, song_name="Song B")
    chart_slot_a = create_chart_slot_in_db(
        session, score_table, chart=chart_a, order_index=0
    )
    chart_slot_b = create_chart_slot_in_db(
        session, score_table, chart=chart_b, order_index=1
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/score_tables/{score_table.id}/chart_slots/order",
        json=[str(chart_slot_b.id), str(chart_slot_a.id)],
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [c["chart"]["song_name"] for c in data] == ["Song B", "Song A"]


def test_update_chart_order_in_score_table_with_three_charts(
    session: Session, client: TestClient
):
    organizer, _, _, _, score_table = create_editable_score_table(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    chart_a = create_chart_in_db(session, score_table, song_name="Song A")
    chart_b = create_chart_in_db(session, score_table, song_name="Song B")
    chart_c = create_chart_in_db(session, score_table, song_name="Song C")
    chart_slot_a = create_chart_slot_in_db(
        session, score_table, chart=chart_a, order_index=0
    )
    chart_slot_b = create_chart_slot_in_db(
        session, score_table, chart=chart_b, order_index=1
    )
    chart_slot_c = create_chart_slot_in_db(
        session, score_table, chart=chart_c, order_index=2
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/score_tables/{score_table.id}/chart_slots/order",
        json=[str(chart_slot_c.id), str(chart_slot_a.id), str(chart_slot_b.id)],
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [c["chart"]["song_name"] for c in data] == ["Song C", "Song A", "Song B"]


def test_update_chart_order_in_score_table_wrong_count(
    session: Session, client: TestClient
):
    organizer, _, _, _, score_table = create_editable_score_table(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    chart = create_chart_in_db(session, score_table)
    chart_slot = create_chart_slot_in_db(session, score_table, chart=chart)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/score_tables/{score_table.id}/chart_slots/order",
        json=[str(chart_slot.id), str(chart_slot.id)],
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_update_chart_order_in_score_table_fewer_chart_slots(
    session: Session, client: TestClient
):
    organizer, _, _, _, score_table = create_editable_score_table(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    chart_a = create_chart_in_db(session, score_table)
    chart_slot_a = create_chart_slot_in_db(session, score_table, chart=chart_a)
    chart_b = create_chart_in_db(session, score_table)
    create_chart_slot_in_db(session, score_table, chart=chart_b)

    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/score_tables/{score_table.id}/chart_slots/order",
        json=[str(chart_slot_a.id)],
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# POST /score_tables/{score_table_id}/players/bulk
# ---------------------------------------------------------------------------


def test_bulk_add_players_to_score_table(session: Session, client: TestClient):
    _, _, _, _, score_table = create_editable_score_table(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        f"/score_tables/{score_table.id}/players/bulk",
        json=[str(player_a.id), str(player_b.id)],
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [p["nickname"] for p in data] == ["PlayerA", "PlayerB"]


def test_bulk_add_players_to_score_table_skips_existing(
    session: Session, client: TestClient
):
    _, _, _, _, score_table = create_editable_score_table(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")
    add_player_to_score_table_in_db(
        session, score_table, player=player_a, order_index=0
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        f"/score_tables/{score_table.id}/players/bulk",
        json=[str(player_a.id), str(player_b.id)],
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [p["nickname"] for p in data] == ["PlayerA", "PlayerB"]


def test_bulk_add_players_to_score_table_player_not_found(
    session: Session, client: TestClient
):
    _, _, _, _, score_table = create_editable_score_table(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        f"/score_tables/{score_table.id}/players/bulk",
        json=["00000000-0000-0000-0000-000000000000"],
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_bulk_add_players_to_score_table_unauthorized(
    session: Session, client: TestClient
):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    score_table = create_score_table_in_db(session, round=round)
    player = create_player_in_db(session, nickname="PlayerA")
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.post(
        f"/score_tables/{score_table.id}/players/bulk",
        json=[str(player.id)],
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# GET /score_tables/{score_table_id}/players
# ---------------------------------------------------------------------------


def test_list_players_in_score_table(session: Session, client: TestClient):
    _, _, _, _, score_table = create_editable_score_table(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")
    add_player_to_score_table_in_db(
        session, score_table, player=player_a, order_index=0
    )
    add_player_to_score_table_in_db(
        session, score_table, player=player_b, order_index=1
    )

    response = client.get(f"/score_tables/{score_table.id}/players")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [p["nickname"] for p in data] == ["PlayerA", "PlayerB"]


def test_list_players_in_score_table_empty(session: Session, client: TestClient):
    _, _, _, _, score_table = create_editable_score_table(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )

    response = client.get(f"/score_tables/{score_table.id}/players")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_list_players_in_score_table_not_found(client: TestClient):
    response = client.get("/score_tables/00000000-0000-0000-0000-000000000000/players")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# PUT /score_tables/{score_table_id}/players/order
# ---------------------------------------------------------------------------


def test_update_player_order_in_score_table(session: Session, client: TestClient):
    _, _, _, _, score_table = create_editable_score_table(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")
    add_player_to_score_table_in_db(
        session, score_table, player=player_a, order_index=0
    )
    add_player_to_score_table_in_db(
        session, score_table, player=player_b, order_index=1
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/score_tables/{score_table.id}/players/order",
        json=[str(player_b.id), str(player_a.id)],
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [p["nickname"] for p in data] == ["PlayerB", "PlayerA"]


def test_update_player_order_in_score_table_wrong_count(
    session: Session, client: TestClient
):
    _, _, _, _, score_table = create_editable_score_table(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")
    add_player_to_score_table_in_db(
        session, score_table, player=player_a, order_index=0
    )
    add_player_to_score_table_in_db(
        session, score_table, player=player_b, order_index=1
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/score_tables/{score_table.id}/players/order",
        json=[str(player_a.id)],
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_update_player_order_in_score_table_player_not_found(
    session: Session, client: TestClient
):
    _, _, _, _, score_table = create_editable_score_table(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    player = create_player_in_db(session, nickname="PlayerA")
    add_player_to_score_table_in_db(session, score_table, player=player, order_index=0)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/score_tables/{score_table.id}/players/order",
        json=["00000000-0000-0000-0000-000000000000"],
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_player_order_in_score_table_player_not_in_score_table(
    session: Session, client: TestClient
):
    _, _, _, _, score_table = create_editable_score_table(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")
    add_player_to_score_table_in_db(
        session, score_table, player=player_a, order_index=0
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/score_tables/{score_table.id}/players/order",
        json=[str(player_b.id)],
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# DELETE /score_tables/{score_table_id}/players/{player_id}
# ---------------------------------------------------------------------------


def test_remove_player_from_score_table(session: Session, client: TestClient):
    _, _, _, _, score_table = create_editable_score_table(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")
    add_player_to_score_table_in_db(
        session, score_table, player=player_a, order_index=0
    )
    add_player_to_score_table_in_db(
        session, score_table, player=player_b, order_index=1
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(
        f"/score_tables/{score_table.id}/players/{player_a.id}",
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [p["nickname"] for p in data] == ["PlayerB"]


def test_remove_player_from_score_table_player_not_in_score_table(
    session: Session, client: TestClient
):
    _, _, _, _, score_table = create_editable_score_table(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    player = create_player_in_db(session, nickname="PlayerA")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(
        f"/score_tables/{score_table.id}/players/{player.id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_remove_player_from_score_table_unauthorized(
    session: Session, client: TestClient
):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    score_table = create_score_table_in_db(session, round=round)
    player = create_player_in_db(session, nickname="PlayerA")
    add_player_to_score_table_in_db(session, score_table, player=player)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.delete(
        f"/score_tables/{score_table.id}/players/{player.id}", headers=headers
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# GET /score_tables/{score_table_id}/results
# ---------------------------------------------------------------------------


def test_get_score_table_results_score_sum(session: Session, client: TestClient):
    organizer, _, _, round, _ = create_editable_score_table(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    score_table = create_score_table_in_db(
        session, round=round, format=ScoreTableFormat.SCORE_SUM
    )

    chart_a = create_chart_in_db(session, score_table, song_name="Song A")
    chart_b = create_chart_in_db(session, score_table, song_name="Song B")

    slot_a = create_chart_slot_in_db(session, score_table, chart=chart_a, order_index=0)
    slot_b = create_chart_slot_in_db(session, score_table, chart=chart_b, order_index=1)

    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")

    add_player_to_score_table_in_db(
        session, score_table, player=player_a, order_index=0
    )
    add_player_to_score_table_in_db(
        session, score_table, player=player_b, order_index=1
    )

    create_score_in_db(
        session, player=player_a, chart=chart_a, value=900000, chart_slot=slot_a
    )
    create_score_in_db(
        session, player=player_a, chart=chart_b, value=800000, chart_slot=slot_b
    )
    create_score_in_db(
        session, player=player_b, chart=chart_a, value=850000, chart_slot=slot_a
    )

    response = client.get(f"/score_tables/{score_table.id}/results")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [r["player_id"] for r in data] == [str(player_a.id), str(player_b.id)]
    assert data[0]["total_score"] == 1700000
    assert data[1]["total_score"] == 850000
    assert data[1]["results"][1]["score"] == 0
    assert data[1]["results"][1]["place"] == 2
    assert data[0]["place"] == 1
    assert data[1]["place"] == 2


def test_get_score_table_results_battle(session: Session, client: TestClient):
    organizer, _, _, round, _ = create_editable_score_table(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    score_table = create_score_table_in_db(
        session, round=round, format=ScoreTableFormat.BATTLE
    )
    chart = create_chart_in_db(session, score_table, song_name="Battle Song")
    slot = create_chart_slot_in_db(session, score_table, chart=chart, order_index=0)

    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")

    add_player_to_score_table_in_db(
        session, score_table, player=player_a, order_index=0
    )
    add_player_to_score_table_in_db(
        session, score_table, player=player_b, order_index=1
    )

    create_score_in_db(
        session, player=player_a, chart=chart, value=900000, chart_slot=slot
    )
    create_score_in_db(
        session, player=player_b, chart=chart, value=850000, chart_slot=slot
    )

    response = client.get(f"/score_tables/{score_table.id}/results")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data[0]["player_id"] == str(player_a.id)
    assert data[0]["total_score"] == 1
    assert data[1]["total_score"] == 0
    assert data[0]["place"] == 1
    assert data[1]["place"] == 2


def test_get_score_table_results_battle_tie_scores_no_points(
    session: Session, client: TestClient
):
    organizer, _, _, round, _ = create_editable_score_table(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    score_table = create_score_table_in_db(
        session, round=round, format=ScoreTableFormat.BATTLE
    )
    chart = create_chart_in_db(session, score_table, song_name="Tie Song")
    slot = create_chart_slot_in_db(session, score_table, chart=chart, order_index=0)

    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")

    add_player_to_score_table_in_db(
        session, score_table, player=player_a, order_index=0
    )
    add_player_to_score_table_in_db(
        session, score_table, player=player_b, order_index=1
    )

    create_score_in_db(
        session, player=player_a, chart=chart, value=900000, chart_slot=slot
    )
    create_score_in_db(
        session, player=player_b, chart=chart, value=900000, chart_slot=slot
    )

    response = client.get(f"/score_tables/{score_table.id}/results")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data[0]["total_score"] == 0
    assert data[1]["total_score"] == 0
    assert data[0]["results"][0]["is_tie"] is True
    assert data[1]["results"][0]["is_tie"] is True
    assert data[0]["place"] == 1
    assert data[1]["place"] == 1


def test_get_score_table_results_not_found(client: TestClient):
    response = client.get("/score_tables/00000000-0000-0000-0000-000000000000/results")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# GET /score_tables/{score_table_id}/possible-players
# ---------------------------------------------------------------------------


def test_list_possible_players_for_score_table_not_found(client: TestClient):
    response = client.get(
        "/score_tables/00000000-0000-0000-0000-000000000000/possible-players"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_list_possible_players_for_score_table_first_round_excludes_current_players(
    session: Session, client: TestClient
):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category, state=RoundState.NOT_STARTED)
    score_table = create_score_table_in_db(session, round=round)

    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")
    player_c = create_player_in_db(session, nickname="PlayerC")

    category.add_player(player_a)
    category.add_player(player_b)
    category.add_player(player_c)
    session.add(category)
    session.commit()

    add_player_to_score_table_in_db(
        session, score_table, player=player_b, order_index=0
    )

    response = client.get(f"/score_tables/{score_table.id}/possible-players")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [player["nickname"] for player in data] == ["PlayerA", "PlayerC"]


def test_list_possible_players_for_score_table_first_round_empty_when_all_are_in_score_table(
    session: Session, client: TestClient
):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category, state=RoundState.NOT_STARTED)
    score_table = create_score_table_in_db(session, round=round)

    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")

    category.add_player(player_a)
    category.add_player(player_b)
    session.add(category)
    session.commit()

    add_player_to_score_table_in_db(
        session, score_table, player=player_a, order_index=0
    )
    add_player_to_score_table_in_db(
        session, score_table, player=player_b, order_index=1
    )

    response = client.get(f"/score_tables/{score_table.id}/possible-players")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_list_possible_players_for_score_table_second_round_uses_previous_qualifiers(
    session: Session, client: TestClient
):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    first_round = create_round_in_db(session, category=category)
    second_round = create_round_in_db(session, category=category)

    first_score_table = create_score_table_in_db(
        session, round=first_round, qualifiers_count=1
    )
    second_score_table = create_score_table_in_db(session, round=second_round)

    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")
    player_c = create_player_in_db(session, nickname="PlayerC")

    category.add_player(player_a)
    category.add_player(player_b)
    category.add_player(player_c)
    session.add(category)
    session.commit()

    chart = create_chart_in_db(session, first_score_table)
    chart_slot = create_chart_slot_in_db(session, first_score_table, chart=chart)

    add_player_to_score_table_in_db(
        session, first_score_table, player=player_a, order_index=0
    )
    add_player_to_score_table_in_db(
        session, first_score_table, player=player_b, order_index=1
    )

    create_score_in_db(
        session, player=player_a, chart=chart, chart_slot=chart_slot, value=900000
    )
    create_score_in_db(
        session, player=player_b, chart=chart, chart_slot=chart_slot, value=800000
    )

    response = client.get(f"/score_tables/{second_score_table.id}/possible-players")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [player["nickname"] for player in data] == ["PlayerA"]


def test_list_possible_players_for_score_table_second_round_excludes_players_already_in_score_table(
    session: Session, client: TestClient
):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    first_round = create_round_in_db(session, category=category)
    second_round = create_round_in_db(session, category=category)

    first_score_table = create_score_table_in_db(
        session, round=first_round, qualifiers_count=1
    )
    second_score_table = create_score_table_in_db(session, round=second_round)

    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")

    category.add_player(player_a)
    category.add_player(player_b)
    session.add(category)
    session.commit()

    chart = create_chart_in_db(session, first_score_table)
    chart_slot = create_chart_slot_in_db(session, first_score_table, chart=chart)

    add_player_to_score_table_in_db(
        session, first_score_table, player=player_a, order_index=0
    )
    add_player_to_score_table_in_db(
        session, first_score_table, player=player_b, order_index=1
    )
    add_player_to_score_table_in_db(
        session, second_score_table, player=player_a, order_index=0
    )

    create_score_in_db(
        session, player=player_a, chart=chart, chart_slot=chart_slot, value=900000
    )
    create_score_in_db(
        session, player=player_b, chart=chart, chart_slot=chart_slot, value=800000
    )

    response = client.get(f"/score_tables/{second_score_table.id}/possible-players")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []
