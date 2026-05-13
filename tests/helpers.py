from fastapi.testclient import TestClient
from sqlmodel import Session

from models.category import Category
from models.chart import Chart, Mode
from models.player import Player
from models.song import Song
from models.tournament import Tournament
from models.tournament_organizer import TournamentOrganizer
from models.user import User
from routers.users import get_password_hash


def create_user_in_db(
    session: Session,
    email: str = "user@example.com",
    password: str = "securepassword123",
    is_super_admin: bool = False,
) -> User:
    """Creates a user directly in the test database."""
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        is_super_admin=is_super_admin,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_auth_headers(client: TestClient, email: str, password: str) -> dict:
    """Logs in and returns Authorization headers with the access token."""
    response = client.post("/token", data={"username": email, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_player_in_db(
    session: Session,
    user: User | None = None,
    nickname: str = "TestPlayer",
    guest_tournament: Tournament | None = None,
) -> Player:
    """Creates a player directly in the test database."""
    player = Player(
        nickname=nickname,
        user_id=user.id if user else None,
        guest_tournament_id=guest_tournament.id if guest_tournament else None,
    )
    session.add(player)
    session.commit()
    session.refresh(player)
    return player


def create_song_in_db(
    session: Session,
    name: str = "Test Song",
    title_url: str | None = None,
) -> Song:
    """Creates a song directly in the test database."""
    song = Song(name=name, title_url=title_url)
    session.add(song)
    session.commit()
    session.refresh(song)
    return song


def create_chart_in_db(
    session: Session,
    song: Song,
    mode: Mode = Mode.SINGLE,
    level: int = 1,
    player_count: int = 1,
) -> Chart:
    """Creates a chart directly in the test database."""
    chart = Chart(
        song_id=song.id,
        mode=mode,
        level=level,
        player_count=player_count,
    )
    session.add(chart)
    session.commit()
    session.refresh(chart)
    return chart


def create_category_in_db(
    session: Session,
    tournament: Tournament,
    name: str = "Test Category",
) -> Category:
    """Creates a category directly in the test database."""
    category = Category(name=name, tournament_id=tournament.id)
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


def create_tournament_in_db(
    session: Session,
    organizer: User | None = None,
    name: str = "Test Tournament",
) -> Tournament:
    """Creates a tournament in the test database, optionally with an organizer."""
    tournament = Tournament(name=name)
    session.add(tournament)
    session.commit()
    session.refresh(tournament)

    if organizer:
        link = TournamentOrganizer(tournament_id=tournament.id, user_id=organizer.id)
        session.add(link)
        session.commit()

    return tournament


def add_organizer_to_tournament(
    session: Session,
    tournament: Tournament,
    user: User,
) -> None:
    """Adds a user as an organizer to an existing tournament."""
    link = TournamentOrganizer(tournament_id=tournament.id, user_id=user.id)
    session.add(link)
    session.commit()
