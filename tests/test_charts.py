from unittest.mock import AsyncMock, patch

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from models.chart import Mode
from models.score_column import ScoreTable
from models.user import User
from tests.helpers import (
    create_category_in_db,
    create_chart_in_db,
    create_round_in_db,
    create_score_column_in_db,
    create_score_table_in_db,
    create_tournament_in_db,
    create_user_in_db,
    get_auth_headers,
)


def create_chart_context_in_db(session: Session, organizer: User) -> ScoreTable:
    tournament = create_tournament_in_db(session, organizer=organizer)
    category = create_category_in_db(session, tournament=tournament)
    round = create_round_in_db(session, category=category)
    score_table = create_score_table_in_db(session, round=round)
    score_column = create_score_column_in_db(session, score_table=score_table)
    return score_column


# ---------------------------------------------------------------------------
# GET /charts/
# ---------------------------------------------------------------------------


def test_list_charts(session: Session, client: TestClient):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    score_column = create_chart_context_in_db(session, user)
    create_chart_in_db(
        session,
        song_name="Song A",
        mode=Mode.SINGLE,
        level=10,
        score_column=score_column,
    )
    create_chart_in_db(
        session,
        song_name="Song B",
        mode=Mode.DOUBLE,
        level=15,
        score_column=score_column,
    )

    headers = get_auth_headers(client, "user@example.com", "mypassword123")
    response = client.get("/charts/", headers=headers)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    levels = [c["level"] for c in data]
    song_names = [c["song_name"] for c in data]
    assert 10 in levels
    assert 15 in levels
    assert "Song A" in song_names
    assert "Song B" in song_names


def test_list_charts_empty(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.get("/charts/", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


# ---------------------------------------------------------------------------
# GET /charts/titles
# ---------------------------------------------------------------------------


def test_fuzzy_search_titles_exact_match(session: Session, client: TestClient):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    score_column = create_chart_context_in_db(session, user)
    chart = create_chart_in_db(session, song_name="My Song", score_column=score_column)
    chart.title_url = "https://example.com/my-song.png"
    session.add(chart)
    session.commit()

    headers = get_auth_headers(client, "user@example.com", "mypassword123")
    response = client.get(
        "/charts/titles",
        params={"search": "My Song"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == ["https://example.com/my-song.png"]


def test_fuzzy_search_titles_is_case_and_punctuation_insensitive(
    session: Session, client: TestClient
):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    score_column = create_chart_context_in_db(session, user)
    chart = create_chart_in_db(
        session,
        song_name="Canción del Corazón!",
        score_column=score_column,
    )
    chart.title_url = "https://example.com/cancion.png"
    session.add(chart)
    session.commit()

    headers = get_auth_headers(client, "user@example.com", "mypassword123")
    response = client.get(
        "/charts/titles",
        params={"search": "cancion del corazon!!!"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == ["https://example.com/cancion.png"]


def test_fuzzy_search_titles_query_parameter_case_and_punctuation_insensitive(
    session: Session, client: TestClient
):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    score_column = create_chart_context_in_db(session, user)
    chart = create_chart_in_db(
        session,
        song_name="cancion del corazon",
        score_column=score_column,
    )
    chart.title_url = "https://example.com/cancion.png"
    session.add(chart)
    session.commit()

    headers = get_auth_headers(client, "user@example.com", "mypassword123")
    response = client.get(
        "/charts/titles",
        params={"search": "Canción del Corazón!"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == ["https://example.com/cancion.png"]


def test_fuzzy_search_titles_matches_approximate_typos(
    session: Session, client: TestClient
):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    score_column = create_chart_context_in_db(session, user)
    chart = create_chart_in_db(session, song_name="My Song", score_column=score_column)
    chart.title_url = "https://example.com/my-song.png"
    session.add(chart)
    session.commit()

    headers = get_auth_headers(client, "user@example.com", "mypassword123")
    response = client.get(
        "/charts/titles",
        params={"search": "my sng"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == ["https://example.com/my-song.png"]


def test_fuzzy_search_titles_orders_results_by_best_match_first(
    session: Session, client: TestClient
):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    score_column = create_chart_context_in_db(session, user)
    exact = create_chart_in_db(session, song_name="My Song", score_column=score_column)
    exact.title_url = "https://example.com/exact.png"
    session.add(exact)
    score_column = create_chart_context_in_db(session, user)
    close = create_chart_in_db(session, song_name="My Sng", score_column=score_column)
    close.title_url = "https://example.com/close.png"
    session.add(close)
    score_column = create_chart_context_in_db(session, user)
    more_distant = create_chart_in_db(
        session, song_name="My Long Song", score_column=score_column
    )
    more_distant.title_url = "https://example.com/distant.png"
    session.add(more_distant)

    session.commit()

    headers = get_auth_headers(client, "user@example.com", "mypassword123")
    response = client.get(
        "/charts/titles",
        params={"search": "My Song"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [
        "https://example.com/exact.png",
        "https://example.com/close.png",
        "https://example.com/distant.png",
    ]


def test_fuzzy_search_titles_excludes_charts_without_title_url(
    session: Session, client: TestClient
):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    score_column = create_chart_context_in_db(session, user)
    chart_with_title = create_chart_in_db(
        session, song_name="Song With Title", score_column=score_column
    )
    chart_with_title.title_url = "https://example.com/with-title.png"
    session.add(chart_with_title)

    chart_without_title = create_chart_in_db(
        session, song_name="Song Without Title", score_column=score_column
    )
    session.add(chart_without_title)
    session.commit()

    headers = get_auth_headers(client, "user@example.com", "mypassword123")
    response = client.get(
        "/charts/titles",
        params={"search": "song"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == ["https://example.com/with-title.png"]


def test_fuzzy_search_titles_returns_empty_list_when_no_match(
    session: Session, client: TestClient
):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    score_column = create_chart_context_in_db(session, user)
    chart = create_chart_in_db(
        session, song_name="Completely Different Song", score_column=score_column
    )
    chart.title_url = "https://example.com/different.png"
    session.add(chart)
    session.commit()

    headers = get_auth_headers(client, "user@example.com", "mypassword123")
    response = client.get(
        "/charts/titles",
        params={"search": "zzzzzzzz"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_fuzzy_search_titles_does_not_match_title_url_contents(
    session: Session, client: TestClient
):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    score_column = create_chart_context_in_db(session, user)
    chart = create_chart_in_db(
        session,
        song_name="Unrelated Song",
        score_column=score_column,
    )
    chart.title_url = "https://example.com/my-song.png"
    session.add(chart)
    session.commit()

    headers = get_auth_headers(client, "user@example.com", "mypassword123")
    response = client.get(
        "/charts/titles",
        params={"search": "my song"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


# ---------------------------------------------------------------------------
# GET /charts/{chart_id}
# ---------------------------------------------------------------------------


def test_get_chart(session: Session, client: TestClient):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    score_column = create_chart_context_in_db(session, user)
    chart = create_chart_in_db(
        session,
        song_name="My Song",
        mode=Mode.DOUBLE,
        level=18,
        player_count=2,
        score_column=score_column,
    )

    headers = get_auth_headers(client, "user@example.com", "mypassword123")
    response = client.get(f"/charts/{chart.id}", headers=headers)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] == str(chart.id)
    assert data["mode"] == "double"
    assert data["level"] == 18
    assert data["player_count"] == 2
    assert data["song_name"] == "My Song"


def test_get_chart_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.get(
        "/charts/00000000-0000-0000-0000-000000000000", headers=headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /charts/
# ---------------------------------------------------------------------------


def test_create_chart(session: Session, client: TestClient):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    score_column = create_chart_context_in_db(session, organizer=user)
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/charts/",
        json={
            "song_name": "New Chart Song",
            "mode": "single_performance",
            "level": 20,
            "player_count": 1,
        },
        params={"score_column_id": str(score_column.id)},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] is not None
    assert data["mode"] == "single_performance"
    assert data["level"] == 20
    assert data["player_count"] == 1
    assert data["song_name"] == "New Chart Song"


def test_create_chart_with_defaults(session: Session, client: TestClient):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    score_column = create_chart_context_in_db(session, organizer=user)
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/charts/",
        json={
            "song_name": "Default Chart Song",
        },
        params={"score_column_id": str(score_column.id)},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["mode"] == "single"
    assert data["level"] == 1
    assert data["player_count"] == 1
    assert data["song_name"] == "Default Chart Song"


def test_create_chart_invalid_mode(session: Session, client: TestClient):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    score_column = create_chart_context_in_db(session, organizer=user)
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/charts/",
        json={"song_name": "Invalid Mode Song", "mode": "invalid", "level": 10},
        params={"score_column_id": str(score_column.id)},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_create_chart_invalid_level(session: Session, client: TestClient):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    score_column = create_chart_context_in_db(session, organizer=user)
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/charts/",
        json={"song_name": "Invalid Level Song", "level": 0},
        params={"score_column_id": str(score_column.id)},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_create_chart_invalid_player_count(session: Session, client: TestClient):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    score_column = create_chart_context_in_db(session, organizer=user)
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/charts/",
        json={"song_name": "Invalid Player Count Song", "player_count": 0},
        params={"score_column_id": str(score_column.id)},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ---------------------------------------------------------------------------
# PATCH /charts/{chart_id}
# ---------------------------------------------------------------------------


def test_update_chart(session: Session, client: TestClient):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    score_column = create_chart_context_in_db(session, user)
    chart = create_chart_in_db(
        session,
        song_name="Update Song",
        mode=Mode.SINGLE,
        level=8,
        score_column=score_column,
    )

    headers = get_auth_headers(client, "user@example.com", "mypassword123")
    response = client.patch(
        f"/charts/{chart.id}",
        json={"mode": "double_performance", "level": 17, "player_count": 2},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["mode"] == "double_performance"
    assert data["level"] == 17
    assert data["player_count"] == 2
    assert data["song_name"] == "Update Song"


def test_update_chart_partial(session: Session, client: TestClient):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    score_column = create_chart_context_in_db(session, user)
    chart = create_chart_in_db(
        session,
        song_name="Partial Update Song",
        mode=Mode.COOP,
        level=12,
        player_count=3,
        score_column=score_column,
    )

    headers = get_auth_headers(client, "user@example.com", "mypassword123")
    response = client.patch(f"/charts/{chart.id}", json={"level": 16}, headers=headers)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["mode"] == "coop"
    assert data["level"] == 16
    assert data["player_count"] == 3


def test_update_chart_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.patch(
        "/charts/00000000-0000-0000-0000-000000000000",
        json={"level": 12},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_chart_invalid_mode(session: Session, client: TestClient):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    score_column = create_chart_context_in_db(session, user)
    chart = create_chart_in_db(
        session, song_name="Invalid Update Song", score_column=score_column
    )

    headers = get_auth_headers(client, "user@example.com", "mypassword123")
    response = client.patch(
        f"/charts/{chart.id}", json={"mode": "invalid"}, headers=headers
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ---------------------------------------------------------------------------
# DELETE /charts/{chart_id}
# ---------------------------------------------------------------------------


def test_delete_chart(session: Session, client: TestClient):
    user = create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    score_column = create_chart_context_in_db(session, user)
    chart = create_chart_in_db(
        session, song_name="Delete Chart", score_column=score_column
    )
    chart_id = chart.id

    headers = get_auth_headers(client, "admin@example.com", "mypassword123")
    response = client.delete(f"/charts/{chart_id}", headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = client.get(f"/charts/{chart_id}", headers=headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_chart_not_found(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.delete(
        "/charts/00000000-0000-0000-0000-000000000000", headers=headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /charts/{chart_id}/title
# ---------------------------------------------------------------------------


def test_upload_chart_title(session: Session, client: TestClient):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    score_column = create_chart_context_in_db(session, user)
    chart = create_chart_in_db(
        session, song_name="Test Song", score_column=score_column
    )

    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    with patch(
        "routers.charts.upload_image",
        new=AsyncMock(return_value="https://example.com/chart-title.png"),
    ):
        response = client.post(
            f"/charts/{chart.id}/title",
            files={"title_file": ("title.png", b"fake image bytes", "image/png")},
            headers=headers,
        )

    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["title_url"] == "https://example.com/chart-title.png"


def test_upload_chart_title_not_found(client: TestClient):
    response = client.post(
        "/charts/00000000-0000-0000-0000-000000000000/title",
        files={"title_file": ("title.png", b"fake image bytes", "image/png")},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
