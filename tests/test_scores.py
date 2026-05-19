from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

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


def score_payload(player_id: str, chart_id: str, **overrides):
    payload = {
        "player_id": player_id,
        "chart_id": chart_id,
        "value": 950000,
        "perfect": 100,
        "great": 10,
        "good": 2,
        "bad": 1,
        "miss": 0,
        "max_combo": 113,
        "kcal": 12.5,
        "grade": "S",
        "stage_pass": True,
        "video_url": "https://example.com/video.mp4",
    }
    payload.update(overrides)
    return payload


def create_editable_score_context(session: Session):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    tournament = create_tournament_in_db(session, organizer=organizer)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    set = create_set_in_db(session, round=round)
    player = create_player_in_db(session, nickname="PlayerA")
    chart = create_chart_with_song_in_db(session, name="Song A")
    add_player_to_set_in_db(session, set=set, player=player)
    chart_slot = create_chart_slot_in_db(session, set=set, chart=chart, order_index=0)
    score = create_score_in_db(
        session, player=player, chart=chart, value=900000, chart_slot=chart_slot
    )
    return organizer, tournament, category, round, set, player, chart, chart_slot, score


# ---------------------------------------------------------------------------
# GET /scores/
# ---------------------------------------------------------------------------


def test_list_scores(session: Session, client: TestClient):
    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")
    chart_a = create_chart_with_song_in_db(session, name="Song A")
    chart_b = create_chart_with_song_in_db(session, name="Song B")
    create_score_in_db(session, player=player_a, chart=chart_a, value=900000)
    create_score_in_db(session, player=player_b, chart=chart_b, value=850000)

    response = client.get("/scores/")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    values = [s["value"] for s in data]
    player_names = [s["player"]["nickname"] for s in data]
    assert 900000 in values
    assert 850000 in values
    assert "PlayerA" in player_names
    assert "PlayerB" in player_names


def test_list_scores_empty(client: TestClient):
    response = client.get("/scores/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


# ---------------------------------------------------------------------------
# GET /scores/{score_id}
# ---------------------------------------------------------------------------


def test_get_score(session: Session, client: TestClient):
    player = create_player_in_db(session, nickname="PlayerA")
    chart = create_chart_with_song_in_db(session, name="Song A")
    score = create_score_in_db(session, player=player, chart=chart, value=900000)

    response = client.get(f"/scores/{score.id}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] == str(score.id)
    assert data["value"] == 900000
    assert data["player"]["id"] == str(player.id)
    assert data["chart"]["id"] == str(chart.id)


def test_get_score_not_found(client: TestClient):
    response = client.get("/scores/00000000-0000-0000-0000-000000000000")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /scores/
# ---------------------------------------------------------------------------


def test_create_score(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    player = create_player_in_db(session, nickname="PlayerA")
    chart = create_chart_with_song_in_db(session, name="Song A")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/scores/",
        json=score_payload(str(player.id), str(chart.id)),
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] is not None
    assert data["value"] == 950000
    assert data["grade"] == "S"
    assert data["player"]["id"] == str(player.id)
    assert data["chart"]["id"] == str(chart.id)


def test_create_score_in_set(session: Session, client: TestClient):
    _, _, _, _, set, player, chart, _, _ = create_editable_score_context(session)
    player_b = create_player_in_db(session, nickname="PlayerB")
    add_player_to_set_in_db(session, set=set, player=player_b, order_index=1)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/scores/",
        json=score_payload(
            str(player_b.id),
            str(chart.id),
            set_id=str(set.id),
            order_index=0,
            value=875000,
        ),
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["value"] == 875000
    assert data["player"]["id"] == str(player_b.id)


def test_create_score_player_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    chart = create_chart_with_song_in_db(session)
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/scores/",
        json=score_payload("00000000-0000-0000-0000-000000000000", str(chart.id)),
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_score_chart_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    player = create_player_in_db(session)
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/scores/",
        json=score_payload(str(player.id), "00000000-0000-0000-0000-000000000000"),
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_score_set_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    player = create_player_in_db(session)
    chart = create_chart_with_song_in_db(session)
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/scores/",
        json=score_payload(
            str(player.id),
            str(chart.id),
            set_id="00000000-0000-0000-0000-000000000000",
            order_index=0,
        ),
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_score_in_set_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    set = create_set_in_db(session, round=round)
    player = create_player_in_db(session)
    chart = create_chart_with_song_in_db(session)
    add_player_to_set_in_db(session, set=set, player=player)
    create_chart_slot_in_db(session, set=set, chart=chart)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.post(
        "/scores/",
        json=score_payload(
            str(player.id), str(chart.id), set_id=str(set.id), order_index=0
        ),
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_score_player_not_in_set(session: Session, client: TestClient):
    _, _, _, _, set, _, chart, _, _ = create_editable_score_context(session)
    other_player = create_player_in_db(session, nickname="OtherPlayer")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/scores/",
        json=score_payload(
            str(other_player.id), str(chart.id), set_id=str(set.id), order_index=0
        ),
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_create_score_chart_not_in_set(session: Session, client: TestClient):
    _, _, _, _, set, player, _, _, _ = create_editable_score_context(session)
    other_chart = create_chart_with_song_in_db(session, name="Other Song")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/scores/",
        json=score_payload(
            str(player.id), str(other_chart.id), set_id=str(set.id), order_index=0
        ),
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_create_score_duplicate_for_player_and_order_index(
    session: Session, client: TestClient
):
    _, _, _, _, set, player, chart, _, _ = create_editable_score_context(session)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/scores/",
        json=score_payload(
            str(player.id), str(chart.id), set_id=str(set.id), order_index=0
        ),
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_create_score_unauthenticated(session: Session, client: TestClient):
    player = create_player_in_db(session)
    chart = create_chart_with_song_in_db(session)

    response = client.post(
        "/scores/",
        json=score_payload(str(player.id), str(chart.id)),
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_score_invalid_negative_value(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    player = create_player_in_db(session)
    chart = create_chart_with_song_in_db(session)
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/scores/",
        json=score_payload(str(player.id), str(chart.id), value=-1),
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_create_score_invalid_grade(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    player = create_player_in_db(session)
    chart = create_chart_with_song_in_db(session)
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/scores/",
        json=score_payload(str(player.id), str(chart.id), grade="INVALID"),
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ---------------------------------------------------------------------------
# PATCH /scores/{score_id}
# ---------------------------------------------------------------------------


def test_update_score(session: Session, client: TestClient):
    _, _, _, _, _, _, _, _, score = create_editable_score_context(session)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.patch(
        f"/scores/{score.id}",
        json={"value": 990000, "grade": "SS", "stage_pass": False},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["value"] == 990000
    assert data["grade"] == "SS"
    assert data["stage_pass"] is False


def test_update_score_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.patch(
        "/scores/00000000-0000-0000-0000-000000000000",
        json={"value": 990000},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_score_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    set = create_set_in_db(session, round=round)
    player = create_player_in_db(session)
    chart = create_chart_with_song_in_db(session)
    chart_slot = create_chart_slot_in_db(session, set=set, chart=chart)
    score = create_score_in_db(
        session, player=player, chart=chart, chart_slot=chart_slot
    )
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.patch(
        f"/scores/{score.id}",
        json={"value": 990000},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_update_score_as_super_admin(session: Session, client: TestClient):
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
    player = create_player_in_db(session)
    chart = create_chart_with_song_in_db(session)
    chart_slot = create_chart_slot_in_db(session, set=set, chart=chart)
    score = create_score_in_db(
        session, player=player, chart=chart, chart_slot=chart_slot
    )
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.patch(
        f"/scores/{score.id}",
        json={"value": 990000},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["value"] == 990000


def test_update_score_unlinked_score_forbidden(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    player = create_player_in_db(session)
    chart = create_chart_with_song_in_db(session)
    score = create_score_in_db(session, player=player, chart=chart)
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.patch(
        f"/scores/{score.id}",
        json={"value": 990000},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_update_score_unauthenticated(session: Session, client: TestClient):
    _, _, _, _, _, _, _, _, score = create_editable_score_context(session)

    response = client.patch(f"/scores/{score.id}", json={"value": 990000})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_update_score_invalid_negative_value(session: Session, client: TestClient):
    _, _, _, _, _, _, _, _, score = create_editable_score_context(session)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.patch(
        f"/scores/{score.id}",
        json={"value": -1},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ---------------------------------------------------------------------------
# DELETE /scores/{score_id}
# ---------------------------------------------------------------------------


def test_delete_score(session: Session, client: TestClient):
    _, _, _, _, _, _, _, _, score = create_editable_score_context(session)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(f"/scores/{score.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_score_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.delete(
        "/scores/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_score_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    set = create_set_in_db(session, round=round)
    player = create_player_in_db(session)
    chart = create_chart_with_song_in_db(session)
    chart_slot = create_chart_slot_in_db(session, set=set, chart=chart)
    score = create_score_in_db(
        session, player=player, chart=chart, chart_slot=chart_slot
    )
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.delete(f"/scores/{score.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_score_as_super_admin(session: Session, client: TestClient):
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
    player = create_player_in_db(session)
    chart = create_chart_with_song_in_db(session)
    chart_slot = create_chart_slot_in_db(session, set=set, chart=chart)
    score = create_score_in_db(
        session, player=player, chart=chart, chart_slot=chart_slot
    )
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.delete(f"/scores/{score.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_delete_score_unlinked_score_forbidden(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    player = create_player_in_db(session)
    chart = create_chart_with_song_in_db(session)
    score = create_score_in_db(session, player=player, chart=chart)
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.delete(f"/scores/{score.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_score_unauthenticated(session: Session, client: TestClient):
    _, _, _, _, _, _, _, _, score = create_editable_score_context(session)

    response = client.delete(f"/scores/{score.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_delete_chart_cascade(session: Session, client: TestClient):
    create_user_in_db(session, email="admin@example.com", password="mypassword123")
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")
    chart = create_chart_with_song_in_db(session)
    score = create_score_in_db(
        session, player=create_player_in_db(session), chart=chart
    )

    response = client.delete(f"/charts/{chart.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = client.get(f"/scores/{score.id}", headers=headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND
