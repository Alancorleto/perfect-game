from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from models.set import SetFormat
from tests.helpers import (
    add_player_to_set_in_db,
    create_category_in_db,
    create_chart_slot_in_db,
    create_chart_with_song_in_db,
    create_player_in_db,
    create_round_in_db,
    create_score_in_db,
    create_set_in_db,
    create_tournament_in_db,
    create_user_in_db,
    get_auth_headers,
)


def create_editable_set(
    session: Session, organizer_email: str, organizer_password: str
):
    organizer = create_user_in_db(
        session, email=organizer_email, password=organizer_password
    )
    tournament = create_tournament_in_db(session, organizer=organizer)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    set = create_set_in_db(session, round=round)
    return organizer, tournament, category, round, set


# ---------------------------------------------------------------------------
# POST /sets/
# ---------------------------------------------------------------------------


def test_create_set(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    tournament = create_tournament_in_db(session, organizer=organizer)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/sets/",
        json={
            "round_id": str(round.id),
            "levels": "10-15",
            "qualifiers_count": 4,
            "format": "score_sum",
        },
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] is not None
    assert data["round_id"] == str(round.id)


def test_create_set_round_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/sets/",
        json={"round_id": "00000000-0000-0000-0000-000000000000"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_set_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.post(
        "/sets/",
        json={"round_id": str(round.id)},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_set_as_super_admin(session: Session, client: TestClient):
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
        "/sets/",
        json={"round_id": str(round.id)},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["round_id"] == str(round.id)


def test_create_set_unauthenticated(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)

    response = client.post("/sets/", json={"round_id": str(round.id)})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_set_invalid_qualifiers_count(session: Session, client: TestClient):
    _, _, _, round, _ = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/sets/",
        json={"round_id": str(round.id), "qualifiers_count": 0},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ---------------------------------------------------------------------------
# GET /sets/
# ---------------------------------------------------------------------------


def test_list_sets(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    set_a = create_set_in_db(session, round=round)
    set_b = create_set_in_db(session, round=round)

    response = client.get("/sets/")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    ids = [s["id"] for s in data]
    assert str(set_a.id) in ids
    assert str(set_b.id) in ids


def test_list_sets_empty(client: TestClient):
    response = client.get("/sets/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


# ---------------------------------------------------------------------------
# GET /sets/{set_id}
# ---------------------------------------------------------------------------


def test_get_set(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    set = create_set_in_db(session, round=round)

    response = client.get(f"/sets/{set.id}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] == str(set.id)
    assert data["round_id"] == str(round.id)


def test_get_set_not_found(client: TestClient):
    response = client.get("/sets/00000000-0000-0000-0000-000000000000")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# PATCH /sets/{set_id}
# ---------------------------------------------------------------------------


def test_update_set(session: Session, client: TestClient):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.patch(
        f"/sets/{set.id}",
        json={"levels": "12-18", "qualifiers_count": 2, "format": "custom_set"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(set.id)


def test_update_set_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.patch(
        "/sets/00000000-0000-0000-0000-000000000000",
        json={"levels": "12-18"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_set_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    set = create_set_in_db(session, round=round)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.patch(
        f"/sets/{set.id}",
        json={"levels": "12-18"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_update_set_as_super_admin(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    set = create_set_in_db(session, round=round)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.patch(
        f"/sets/{set.id}",
        json={"levels": "12-18"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK


def test_update_set_unauthenticated(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    set = create_set_in_db(session, round=round)

    response = client.patch(f"/sets/{set.id}", json={"levels": "12-18"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_update_set_invalid_format(session: Session, client: TestClient):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.patch(
        f"/sets/{set.id}",
        json={"format": "invalid"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ---------------------------------------------------------------------------
# DELETE /sets/{set_id}
# ---------------------------------------------------------------------------


def test_delete_set(session: Session, client: TestClient):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(f"/sets/{set.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_set_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.delete(
        "/sets/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_set_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    set = create_set_in_db(session, round=round)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.delete(f"/sets/{set.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_set_as_super_admin(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    set = create_set_in_db(session, round=round)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.delete(f"/sets/{set.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_delete_set_unauthenticated(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    set = create_set_in_db(session, round=round)

    response = client.delete(f"/sets/{set.id}")

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
    set = create_set_in_db(session, round=round)

    response = client.delete(f"/rounds/{round.id}", headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = client.get(f"/sets/{set.id}")
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
    set = create_set_in_db(session, round=round)

    response = client.delete(f"/tournaments/{tournament.id}", headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = client.get(f"/sets/{set.id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# GET /sets/{set_id}/charts
# ---------------------------------------------------------------------------


def test_list_charts_for_set(session: Session, client: TestClient):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    chart_a = create_chart_with_song_in_db(session, name="Song A")
    chart_b = create_chart_with_song_in_db(session, name="Song B")
    create_chart_slot_in_db(session, set=set, chart=chart_a, order_index=0)
    create_chart_slot_in_db(session, set=set, chart=chart_b, order_index=1)

    response = client.get(f"/sets/{set.id}/charts")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    names = [c["song"]["name"] for c in data]
    assert names[0] == "Song A"
    assert names[1] == "Song B"


def test_list_charts_for_set_empty(session: Session, client: TestClient):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )

    response = client.get(f"/sets/{set.id}/charts")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_list_charts_for_set_not_found(client: TestClient):
    response = client.get("/sets/00000000-0000-0000-0000-000000000000/charts")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /sets/{set_id}/charts
# ---------------------------------------------------------------------------


def test_add_chart_to_set(session: Session, client: TestClient):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    chart_a = create_chart_with_song_in_db(session, name="Song A")
    chart_b = create_chart_with_song_in_db(session, name="Song B")
    create_chart_slot_in_db(session, set=set, chart=chart_a, order_index=0)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        f"/sets/{set.id}/charts",
        params={"chart_id": str(chart_b.id)},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [c["song"]["name"] for c in data] == ["Song A", "Song B"]


def test_add_chart_to_set_not_found(session: Session, client: TestClient):
    chart = create_chart_with_song_in_db(session)
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/sets/00000000-0000-0000-0000-000000000000/charts",
        params={"chart_id": str(chart.id)},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_add_chart_to_set_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    set = create_set_in_db(session, round=round)
    chart = create_chart_with_song_in_db(session)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.post(
        f"/sets/{set.id}/charts",
        params={"chart_id": str(chart.id)},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_add_chart_to_set_chart_not_found(session: Session, client: TestClient):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        f"/sets/{set.id}/charts",
        params={"chart_id": "00000000-0000-0000-0000-000000000000"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_add_chart_to_set_unauthenticated(session: Session, client: TestClient):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    chart = create_chart_with_song_in_db(session)

    response = client.post(
        f"/sets/{set.id}/charts",
        params={"chart_id": str(chart.id)},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# PUT /sets/{set_id}/charts
# ---------------------------------------------------------------------------


def test_replace_chart_in_set(session: Session, client: TestClient):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    old_chart = create_chart_with_song_in_db(session, name="Old Song")
    new_chart = create_chart_with_song_in_db(session, name="New Song")
    create_chart_slot_in_db(session, set=set, chart=old_chart, order_index=0)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/sets/{set.id}/charts",
        params={"chart_order_index": 0, "new_chart_id": str(new_chart.id)},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 1
    assert data[0]["song"]["name"] == "New Song"


def test_replace_chart_in_set_slot_not_found(session: Session, client: TestClient):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    new_chart = create_chart_with_song_in_db(session, name="New Song")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/sets/{set.id}/charts",
        params={"chart_order_index": 0, "new_chart_id": str(new_chart.id)},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# PUT /sets/{set_id}/charts/order
# ---------------------------------------------------------------------------


def test_update_chart_order_in_set(session: Session, client: TestClient):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    chart_a = create_chart_with_song_in_db(session, name="Song A")
    chart_b = create_chart_with_song_in_db(session, name="Song B")
    create_chart_slot_in_db(session, set=set, chart=chart_a, order_index=0)
    create_chart_slot_in_db(session, set=set, chart=chart_b, order_index=1)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/sets/{set.id}/charts/order",
        json=[1, 0],
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [c["song"]["name"] for c in data] == ["Song B", "Song A"]


def test_update_chart_order_in_set_with_three_charts(
    session: Session, client: TestClient
):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    chart_a = create_chart_with_song_in_db(session, name="Song A")
    chart_b = create_chart_with_song_in_db(session, name="Song B")
    chart_c = create_chart_with_song_in_db(session, name="Song C")
    create_chart_slot_in_db(session, set=set, chart=chart_a, order_index=0)
    create_chart_slot_in_db(session, set=set, chart=chart_b, order_index=1)
    create_chart_slot_in_db(session, set=set, chart=chart_c, order_index=2)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/sets/{set.id}/charts/order",
        json=[2, 0, 1],
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [c["song"]["name"] for c in data] == ["Song C", "Song A", "Song B"]


def test_update_chart_order_in_set_wrong_count(session: Session, client: TestClient):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    chart = create_chart_with_song_in_db(session)
    create_chart_slot_in_db(session, set=set, chart=chart)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/sets/{set.id}/charts/order",
        json=[0, 1],
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_update_chart_order_in_set_invalid_order_index(
    session: Session, client: TestClient
):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    chart = create_chart_with_song_in_db(session)
    create_chart_slot_in_db(session, set=set, chart=chart)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/sets/{set.id}/charts/order",
        json=[1],
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# DELETE /sets/{set_id}/charts
# ---------------------------------------------------------------------------


def test_remove_chart_from_set(session: Session, client: TestClient):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    chart_a = create_chart_with_song_in_db(session, name="Song A")
    chart_b = create_chart_with_song_in_db(session, name="Song B")
    create_chart_slot_in_db(session, set=set, chart=chart_a, order_index=0)
    create_chart_slot_in_db(session, set=set, chart=chart_b, order_index=1)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(
        f"/sets/{set.id}/charts",
        params={"chart_order_index": 0},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [c["song"]["name"] for c in data] == ["Song B"]


def test_remove_chart_from_set_slot_not_found(session: Session, client: TestClient):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    chart_a = create_chart_with_song_in_db(session, name="Song A")
    chart_b = create_chart_with_song_in_db(session, name="Song B")
    create_chart_slot_in_db(session, set=set, chart=chart_a, order_index=0)
    create_chart_slot_in_db(session, set=set, chart=chart_b, order_index=1)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(
        f"/sets/{set.id}/charts",
        params={"chart_order_index": 2},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /sets/{set_id}/players/bulk
# ---------------------------------------------------------------------------


def test_bulk_add_players_to_set(session: Session, client: TestClient):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        f"/sets/{set.id}/players/bulk",
        json=[str(player_a.id), str(player_b.id)],
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [p["nickname"] for p in data] == ["PlayerA", "PlayerB"]


def test_bulk_add_players_to_set_skips_existing(session: Session, client: TestClient):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")
    add_player_to_set_in_db(session, set=set, player=player_a, order_index=0)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        f"/sets/{set.id}/players/bulk",
        json=[str(player_a.id), str(player_b.id)],
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [p["nickname"] for p in data] == ["PlayerA", "PlayerB"]


def test_bulk_add_players_to_set_player_not_found(session: Session, client: TestClient):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        f"/sets/{set.id}/players/bulk",
        json=["00000000-0000-0000-0000-000000000000"],
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_bulk_add_players_to_set_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    set = create_set_in_db(session, round=round)
    player = create_player_in_db(session, nickname="PlayerA")
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.post(
        f"/sets/{set.id}/players/bulk",
        json=[str(player.id)],
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# GET /sets/{set_id}/players
# ---------------------------------------------------------------------------


def test_list_players_in_set(session: Session, client: TestClient):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")
    add_player_to_set_in_db(session, set=set, player=player_a, order_index=0)
    add_player_to_set_in_db(session, set=set, player=player_b, order_index=1)

    response = client.get(f"/sets/{set.id}/players")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [p["nickname"] for p in data] == ["PlayerA", "PlayerB"]


def test_list_players_in_set_empty(session: Session, client: TestClient):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )

    response = client.get(f"/sets/{set.id}/players")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_list_players_in_set_not_found(client: TestClient):
    response = client.get("/sets/00000000-0000-0000-0000-000000000000/players")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# PUT /sets/{set_id}/players/order
# ---------------------------------------------------------------------------


def test_update_player_order_in_set(session: Session, client: TestClient):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")
    add_player_to_set_in_db(session, set=set, player=player_a, order_index=0)
    add_player_to_set_in_db(session, set=set, player=player_b, order_index=1)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/sets/{set.id}/players/order",
        json=[str(player_b.id), str(player_a.id)],
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [p["nickname"] for p in data] == ["PlayerB", "PlayerA"]


def test_update_player_order_in_set_wrong_count(session: Session, client: TestClient):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")
    add_player_to_set_in_db(session, set=set, player=player_a, order_index=0)
    add_player_to_set_in_db(session, set=set, player=player_b, order_index=1)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/sets/{set.id}/players/order",
        json=[str(player_a.id)],
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_update_player_order_in_set_player_not_found(
    session: Session, client: TestClient
):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    player = create_player_in_db(session, nickname="PlayerA")
    add_player_to_set_in_db(session, set=set, player=player, order_index=0)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/sets/{set.id}/players/order",
        json=["00000000-0000-0000-0000-000000000000"],
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_player_order_in_set_player_not_in_set(
    session: Session, client: TestClient
):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")
    add_player_to_set_in_db(session, set=set, player=player_a, order_index=0)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/sets/{set.id}/players/order",
        json=[str(player_b.id)],
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# DELETE /sets/{set_id}/players/{player_id}
# ---------------------------------------------------------------------------


def test_remove_player_from_set(session: Session, client: TestClient):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")
    add_player_to_set_in_db(session, set=set, player=player_a, order_index=0)
    add_player_to_set_in_db(session, set=set, player=player_b, order_index=1)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(
        f"/sets/{set.id}/players/{player_a.id}",
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [p["nickname"] for p in data] == ["PlayerB"]


def test_remove_player_from_set_player_not_in_set(session: Session, client: TestClient):
    _, _, _, _, set = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    player = create_player_in_db(session, nickname="PlayerA")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(
        f"/sets/{set.id}/players/{player.id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_remove_player_from_set_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    set = create_set_in_db(session, round=round)
    player = create_player_in_db(session, nickname="PlayerA")
    add_player_to_set_in_db(session, set=set, player=player)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.delete(f"/sets/{set.id}/players/{player.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# GET /sets/{set_id}/results
# ---------------------------------------------------------------------------


def test_get_set_results_score_sum(session: Session, client: TestClient):
    _, _, _, round, _ = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    set = create_set_in_db(session, round=round, format=SetFormat.SCORE_SUM)

    chart_a = create_chart_with_song_in_db(session, name="Song A")
    chart_b = create_chart_with_song_in_db(session, name="Song B")

    slot_a = create_chart_slot_in_db(session, set=set, chart=chart_a, order_index=0)
    slot_b = create_chart_slot_in_db(session, set=set, chart=chart_b, order_index=1)

    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")

    add_player_to_set_in_db(session, set=set, player=player_a, order_index=0)
    add_player_to_set_in_db(session, set=set, player=player_b, order_index=1)

    create_score_in_db(
        session, player=player_a, chart=chart_a, value=900000, chart_slot=slot_a
    )
    create_score_in_db(
        session, player=player_a, chart=chart_b, value=800000, chart_slot=slot_b
    )
    create_score_in_db(
        session, player=player_b, chart=chart_a, value=850000, chart_slot=slot_a
    )

    response = client.get(f"/sets/{set.id}/results")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [r["player_id"] for r in data] == [str(player_a.id), str(player_b.id)]
    assert data[0]["total_score"] == 1700000
    assert data[1]["total_score"] == 850000
    assert data[1]["results"][1]["score"] == 0
    assert data[1]["results"][1]["place"] == 2
    assert data[0]["place"] == 1
    assert data[1]["place"] == 2


def test_get_set_results_battle(session: Session, client: TestClient):
    _, _, _, round, _ = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    set = create_set_in_db(session, round=round, format=SetFormat.BATTLE)
    chart = create_chart_with_song_in_db(session, name="Battle Song")
    slot = create_chart_slot_in_db(session, set=set, chart=chart, order_index=0)

    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")

    add_player_to_set_in_db(session, set=set, player=player_a, order_index=0)
    add_player_to_set_in_db(session, set=set, player=player_b, order_index=1)

    create_score_in_db(
        session, player=player_a, chart=chart, value=900000, chart_slot=slot
    )
    create_score_in_db(
        session, player=player_b, chart=chart, value=850000, chart_slot=slot
    )

    response = client.get(f"/sets/{set.id}/results")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data[0]["player_id"] == str(player_a.id)
    assert data[0]["total_score"] == 1
    assert data[1]["total_score"] == 0
    assert data[0]["place"] == 1
    assert data[1]["place"] == 2


def test_get_set_results_battle_tie_scores_no_points(
    session: Session, client: TestClient
):
    _, _, _, round, _ = create_editable_set(
        session=session,
        organizer_email="organizer@example.com",
        organizer_password="mypassword123",
    )
    set = create_set_in_db(session, round=round, format=SetFormat.BATTLE)
    chart = create_chart_with_song_in_db(session, name="Tie Song")
    slot = create_chart_slot_in_db(session, set=set, chart=chart, order_index=0)

    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")

    add_player_to_set_in_db(session, set=set, player=player_a, order_index=0)
    add_player_to_set_in_db(session, set=set, player=player_b, order_index=1)

    create_score_in_db(
        session, player=player_a, chart=chart, value=900000, chart_slot=slot
    )
    create_score_in_db(
        session, player=player_b, chart=chart, value=900000, chart_slot=slot
    )

    response = client.get(f"/sets/{set.id}/results")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data[0]["total_score"] == 0
    assert data[1]["total_score"] == 0
    assert data[0]["results"][0]["is_tie"] is True
    assert data[1]["results"][0]["is_tie"] is True
    assert data[0]["place"] == 1
    assert data[1]["place"] == 1


def test_get_set_results_not_found(client: TestClient):
    response = client.get("/sets/00000000-0000-0000-0000-000000000000/results")

    assert response.status_code == status.HTTP_404_NOT_FOUND
