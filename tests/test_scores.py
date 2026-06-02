from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.helpers import (
    add_player_to_score_table_in_db,
    create_chart_in_db,
    create_event_in_db,
    create_player_in_db,
    create_round_in_db,
    create_score_column_in_db,
    create_score_in_db,
    create_score_table_in_db,
    create_tournament_in_db,
    create_user_in_db,
    get_auth_headers,
)


def score_payload(player_id: str, score_column_id: str, **overrides):
    payload = {
        "player_id": player_id,
        "score_column_id": score_column_id,
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


def create_score_context(session: Session):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)
    round = create_round_in_db(session, tournament=tournament)
    score_table = create_score_table_in_db(session, round=round)
    player = create_player_in_db(session, nickname="PlayerA")
    score_column = create_score_column_in_db(session, score_table=score_table)
    chart = create_chart_in_db(session, score_column=score_column, song_name="Song A")
    add_player_to_score_table_in_db(session, score_table=score_table, player=player)
    return (
        organizer,
        event,
        tournament,
        round,
        score_table,
        player,
        chart,
        score_column,
    )


# ---------------------------------------------------------------------------
# GET /scores/
# ---------------------------------------------------------------------------


def test_list_scores(session: Session, client: TestClient):
    organizer, event, _, _, score_table, player_a, chart, score_column = (
        create_score_context(session)
    )
    user_b = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player_b = create_player_in_db(session, nickname="PlayerB", user=user_b)
    add_player_to_score_table_in_db(session, score_table=score_table, player=player_b)

    create_score_in_db(
        session, player=player_a, score_column=score_column, value=900000
    )
    create_score_in_db(
        session, player=player_b, score_column=score_column, value=850000
    )

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
    _, _, _, _, _, player, chart, score_column = create_score_context(session)
    score = create_score_in_db(
        session, player=player, score_column=score_column, value=900000
    )

    response = client.get(f"/scores/{score.id}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] == str(score.id)
    assert data["value"] == 900000
    assert data["player"]["id"] == str(player.id)
    assert data["score_column"]["id"] == str(score_column.id)


def test_get_score_not_found(client: TestClient):
    response = client.get("/scores/00000000-0000-0000-0000-000000000000")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /scores/
# ---------------------------------------------------------------------------


def test_create_score(session: Session, client: TestClient):
    _, _, _, _, score_table, player, chart, _ = create_score_context(session)
    score_column = create_score_column_in_db(
        session, score_table=score_table, order_index=1
    )
    create_chart_in_db(session, score_column=score_column, song_name="Song B")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/scores/",
        json=score_payload(str(player.id), str(score_column.id)),
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] is not None
    assert data["value"] == 950000
    assert data["grade"] == "S"
    assert data["player"]["id"] == str(player.id)
    assert data["score_column"]["id"] == str(score_column.id)


def test_create_score_player_not_found(session: Session, client: TestClient):
    _, _, _, _, _, _, chart, score_column = create_score_context(session)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/scores/",
        json=score_payload(
            "00000000-0000-0000-0000-000000000000",
            str(score_column.id),
        ),
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_score_score_column_not_found(session: Session, client: TestClient):
    _, _, _, _, _, player, chart, _ = create_score_context(session)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/scores/",
        json=score_payload(
            str(player.id),
            "00000000-0000-0000-0000-000000000000",
        ),
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_score_in_score_table_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    _, _, _, _, _, player, chart, score_column = create_score_context(session)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.post(
        "/scores/",
        json=score_payload(str(player.id), str(score_column.id)),
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_score_player_not_in_score_table(session: Session, client: TestClient):
    _, _, _, _, _, _, chart, score_column = create_score_context(session)
    other_player = create_player_in_db(session, nickname="OtherPlayer")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/scores/",
        json=score_payload(str(other_player.id), str(score_column.id)),
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_create_score_chart_not_in_score_table(session: Session, client: TestClient):
    organizer, _, _, round, score_table, player, _, score_column = create_score_context(
        session
    )

    # Make sure it does not trigger the score column restriction
    score_column.chart = None
    session.commit()

    other_score_table = create_score_table_in_db(
        session,
        round,
    )
    other_score_column = create_score_column_in_db(
        session, score_table=other_score_table
    )
    other_chart = create_chart_in_db(
        session, score_column=other_score_column, song_name="Other Song"
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/scores/",
        json=score_payload(str(player.id), str(score_column.id)),
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK


def test_create_score_duplicate_for_player_and_score_column(
    session: Session, client: TestClient
):
    _, _, _, _, _, player, chart, score_column = create_score_context(session)
    create_score_in_db(session, player=player, score_column=score_column)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/scores/",
        json=score_payload(str(player.id), str(score_column.id)),
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_create_score_unauthenticated(session: Session, client: TestClient):
    _, _, _, _, _, player, chart, score_column = create_score_context(session)

    response = client.post(
        "/scores/",
        json=score_payload(str(player.id), str(score_column.id)),
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_score_invalid_negative_value(session: Session, client: TestClient):
    _, _, _, _, _, player, chart, score_column = create_score_context(session)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/scores/",
        json=score_payload(
            str(player.id),
            str(score_column.id),
            value=-1,
        ),
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_create_score_invalid_grade(session: Session, client: TestClient):
    _, _, _, _, _, player, _, score_column = create_score_context(session)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/scores/",
        json=score_payload(str(player.id), str(score_column.id), grade="INVALID"),
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ---------------------------------------------------------------------------
# PATCH /scores/{score_id}
# ---------------------------------------------------------------------------


def test_update_score(session: Session, client: TestClient):
    _, _, _, _, _, player, chart, score_column = create_score_context(session)
    score = create_score_in_db(session, player=player, score_column=score_column)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.patch(
        f"/scores/{score.id}",
        json={"value": 990000, "grade": "SSS", "stage_pass": False},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["value"] == 990000
    assert data["grade"] == "SSS"
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
    _, _, _, _, _, player, chart, score_column = create_score_context(session)
    score = create_score_in_db(session, player=player, score_column=score_column)
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
    _, _, _, _, _, player, chart, score_column = create_score_context(session)
    score = create_score_in_db(session, player=player, score_column=score_column)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.patch(
        f"/scores/{score.id}",
        json={"value": 990000},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["value"] == 990000


def test_update_score_unauthenticated(session: Session, client: TestClient):
    _, _, _, _, _, player, chart, score_column = create_score_context(session)
    score = create_score_in_db(session, player=player, score_column=score_column)

    response = client.patch(f"/scores/{score.id}", json={"value": 990000})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_update_score_invalid_negative_value(session: Session, client: TestClient):
    _, _, _, _, _, player, chart, score_column = create_score_context(session)
    score = create_score_in_db(session, player=player, score_column=score_column)
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
    _, _, _, _, _, player, chart, score_column = create_score_context(session)
    score = create_score_in_db(session, player=player, score_column=score_column)
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
    _, _, _, _, _, player, chart, score_column = create_score_context(session)
    score = create_score_in_db(session, player=player, score_column=score_column)
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
    _, _, _, _, _, player, chart, score_column = create_score_context(session)
    score = create_score_in_db(session, player=player, score_column=score_column)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.delete(f"/scores/{score.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_delete_score_unauthenticated(session: Session, client: TestClient):
    _, _, _, _, _, player, chart, score_column = create_score_context(session)
    score = create_score_in_db(session, player=player, score_column=score_column)

    response = client.delete(f"/scores/{score.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_delete_chart_cascade(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")
    _, _, _, _, _, player, chart, score_column = create_score_context(session)
    score = create_score_in_db(session, player=player, score_column=score_column)

    response = client.delete(f"/charts/{chart.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = client.get(f"/scores/{score.id}", headers=headers)
    assert get_response.status_code == status.HTTP_200_OK


def test_delete_player_cascade(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    _, _, _, _, _, player, chart, score_column = create_score_context(session)
    score = create_score_in_db(session, player=player, score_column=score_column)

    headers = get_auth_headers(client, "admin@example.com", "mypassword123")
    response = client.delete(f"/players/{player.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = client.get(f"/scores/{score.id}", headers=headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_score_column_cascade(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    _, _, _, _, score_table, player, chart, score_column = create_score_context(session)
    score = create_score_in_db(session, player=player, score_column=score_column)

    headers = get_auth_headers(client, "admin@example.com", "mypassword123")
    response = client.delete(f"/score_columns/{score_column.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = client.get(f"/scores/{score.id}", headers=headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND
