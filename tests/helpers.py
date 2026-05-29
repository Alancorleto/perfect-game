from fastapi.testclient import TestClient
from sqlmodel import Session

from models.category import Category
from models.chart import Chart, Mode
from models.chart_column import ChartColumn
from models.player import Player
from models.player_row import PlayerRow
from models.round import Round, RoundState
from models.score import Grade, Score
from models.score_column import ScoreColumn
from models.score_table import ScoreTable, ScoreTableFormat
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
    country_code: str = "AR",
    guest_tournament: Tournament | None = None,
) -> Player:
    """Creates a player directly in the test database."""
    player = Player(
        nickname=nickname,
        country_code=country_code,
        user_id=user.id if user else None,
        guest_tournament_id=guest_tournament.id if guest_tournament else None,
    )
    session.add(player)
    session.commit()
    session.refresh(player)
    return player


def create_chart_in_db(
    session: Session,
    song_name: str = "Song",
    mode: Mode = Mode.SINGLE,
    level: int = 1,
    player_count: int = 1,
    score_column: ScoreColumn | None = None,
    title_url: str | None = None,
) -> Chart:
    """Creates a chart directly in the test database."""
    chart = Chart(
        song_name=song_name,
        mode=mode,
        level=level,
        player_count=player_count,
        score_column=score_column,
        title_url=title_url,
    )
    session.add(chart)
    session.commit()
    session.refresh(chart)
    return chart


def create_category_in_db(
    session: Session,
    tournament: Tournament,
    name: str = "Test Category",
    auto_accept_join_requests: bool = False,
) -> Category:
    """Creates a category directly in the test database."""
    category = Category(
        name=name,
        tournament_id=tournament.id,
        auto_accept_join_requests=auto_accept_join_requests,
    )
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


def create_round_in_db(
    session: Session,
    category: Category,
    name: str | None = "Test Round",
    state: RoundState = RoundState.NOT_STARTED,
) -> Round:
    """Creates a round directly in the test database."""
    round = Round(
        name=name,
        state=state,
        category_id=category.id,
        order_index=len(category.rounds),
    )
    session.add(round)
    session.commit()
    session.refresh(round)
    return round


def create_score_table_in_db(
    session: Session,
    round: Round,
    levels: str | None = None,
    qualifiers_count: int | None = None,
    format: ScoreTableFormat = ScoreTableFormat.SCORE_SUM,
) -> ScoreTable:
    """Creates a score table directly in the test database."""
    score_table = ScoreTable(
        round_id=round.id,
        levels=levels,
        qualifiers_count=qualifiers_count,
        format=format,
        order_index=len(round.score_tables),
    )
    session.add(score_table)
    session.commit()
    session.refresh(score_table)
    return score_table


def create_score_column_in_db(
    session: Session,
    score_table: ScoreTable,
    order_index: int = 0,
    description: str | None = None,
) -> ScoreColumn:
    """Creates a score column directly in the test database."""
    score_column = ScoreColumn(
        score_table=score_table,
        order_index=order_index,
        description=description,
    )
    session.add(score_column)
    session.commit()
    session.refresh(score_column)
    return score_column


def create_chart_column_in_db(
    session: Session,
    score_column: ScoreColumn,
    description: str | None = None,
) -> ChartColumn:
    """Creates a chart column directly in the test database."""
    chart_column = ChartColumn(
        score_column=score_column,
        description=description,
    )
    session.add(chart_column)
    session.commit()
    session.refresh(chart_column)
    return chart_column


def add_player_to_score_table_in_db(
    session: Session,
    score_table: ScoreTable,
    player: Player,
    order_index: int = 0,
) -> PlayerRow:
    """Adds a player to a score table directly in the test database."""
    row = PlayerRow(
        score_table_id=score_table.id, player_id=player.id, order_index=order_index
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def create_score_in_db(
    session: Session,
    player: Player,
    score_column: ScoreColumn,
    value: int = 1000000,
) -> Score:
    """Creates a score directly in the test database."""
    score = Score(
        player_id=player.id,
        score_column_id=score_column.id,
        value=value,
        perfect=100,
        great=0,
        good=0,
        bad=0,
        miss=0,
        max_combo=100,
        kcal=10,
        grade=Grade.S,
        stage_pass=True,
    )
    session.add(score)
    session.commit()
    session.refresh(score)

    return score


def get_grade(score: int) -> str:
    if score >= 995000:
        return "SSS+"
    elif score >= 990000:
        return "SSS"
    elif score >= 985000:
        return "SS+"
    elif score >= 980000:
        return "SS"
    elif score >= 975000:
        return "S+"
    elif score >= 970000:
        return "S"
    elif score >= 960000:
        return "AAA+"
    elif score >= 950000:
        return "AAA"
    elif score >= 925000:
        return "AA+"
    elif score >= 900000:
        return "AA"
    elif score >= 825000:
        return "A+"
    elif score >= 750000:
        return "A"
    elif score >= 700000:
        return "B"
    elif score >= 600000:
        return "C"
    elif score >= 450000:
        return "D"
    else:
        return "F"


def create_tournament_in_db(
    session: Session,
    organizer: User | None = None,
    name: str = "Test Tournament",
    country_code: str = "AR",
) -> Tournament:
    """Creates a tournament in the test database, optionally with an organizer."""
    tournament = Tournament(name=name, country_code=country_code)
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
