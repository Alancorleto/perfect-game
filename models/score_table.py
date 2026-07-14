import uuid
from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel
from sqlmodel import Field, Relationship, SQLModel

from models.player import Player
from models.player_row import PlayerRow
from models.round import Round
from models.user import User

if TYPE_CHECKING:
    from models.score_column import ScoreColumn


class ScoreTableFormat(Enum):
    SCORE_SUM = "score_sum"
    BATTLE = "battle"
    CUSTOM_SET = "custom_set"


class Result(BaseModel):
    player_id: uuid.UUID
    player_order_index: int
    score_column_id: uuid.UUID = None
    score_id: uuid.UUID | None = None
    score_value: int = 0
    place: int = -1
    is_tie: bool = False


class PlayerResults(BaseModel):
    player_id: uuid.UUID
    player: Player
    order_index: int
    results: list[Result] = []
    total_score: int = 0
    place: int = -1
    is_tie: bool = False


class ColumnResults(BaseModel):
    score_column_id: uuid.UUID
    results: list[Result] = []


class ScoreTableBase(SQLModel):
    qualifiers_count: int | None = Field(ge=1, default=None)
    order_index: int = Field(default=0)


class ScoreTable(ScoreTableBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    round_id: uuid.UUID = Field(foreign_key="round.id", ondelete="CASCADE")

    # This cannot be changed nor declared in creation, hence it's not in ScreTableBase.
    format: ScoreTableFormat = Field(default=ScoreTableFormat.SCORE_SUM)

    round: Round = Relationship(back_populates="score_tables")
    score_columns: list["ScoreColumn"] = Relationship(
        back_populates="score_table", cascade_delete=True
    )
    player_rows: list[PlayerRow] = Relationship(
        back_populates="score_table", cascade_delete=True
    )

    def can_be_edited_by(self, user: User) -> bool:
        return self.round.can_be_edited_by(user)

    def can_be_deleted(self, user: User) -> bool:
        return self.can_be_edited_by(user) and (
            user.is_super_admin
            or all(
                score_column.can_be_deleted(user) for score_column in self.score_columns
            )
        )

    def add_player(self, player: Player) -> None:
        order_index = len(self.player_rows)
        player_row = PlayerRow(score_table=self, player=player, order_index=order_index)
        self.player_rows.append(player_row)

    def get_players_by_order(self) -> list[Player]:
        sorted_player_rows = sorted(
            self.player_rows, key=lambda player_row: player_row.order_index
        )
        return [player_row.player for player_row in sorted_player_rows]

    def get_score_columns_by_order(self) -> list["ScoreColumn"]:
        return sorted(
            self.score_columns, key=lambda score_column: score_column.order_index
        )

    def get_results(self) -> list[PlayerResults]:
        score_columns = self.get_score_columns_by_order()

        chart_results_list: list[ColumnResults] = []
        for score_column in score_columns:
            chart_results = _populate_column_results(score_column)
            chart_results_list.append(chart_results)

        player_results_list: list[PlayerResults] = []
        for player_row in self.player_rows:
            player_results = _populate_player_results(player_row, chart_results_list)
            player_results_list.append(player_results)

        _sort_player_results(player_results_list)

        return player_results_list

    def get_qualifying_players(self) -> list[Player]:
        player_results_list = self.get_results()
        filtered_player_results = [
            player_results
            for player_results in player_results_list
            if player_results.place <= self.qualifiers_count
        ]
        qualifying_players = [
            player_results.player for player_results in filtered_player_results
        ]
        return qualifying_players


class ScoreTableCreate(ScoreTableBase):
    round_id: uuid.UUID


class ScoreTableUpdate(ScoreTableBase):
    levels: str | None = None
    qualifiers_count: int | None = Field(ge=1, default=1)
    format: ScoreTableFormat | None = Field(default=ScoreTableFormat.SCORE_SUM)


class ScoreTablePublic(ScoreTableBase):
    id: uuid.UUID
    round_id: uuid.UUID


def _populate_column_results(score_column: "ScoreColumn") -> ColumnResults:
    chart_results = ColumnResults(score_column_id=score_column.id, results=[])

    for score in score_column.scores:
        player_order_index = next(
            player_row.order_index
            for player_row in score_column.score_table.player_rows
            if player_row.player_id == score.player_id
        )
        result = Result(
            player_id=score.player_id,
            player_order_index=player_order_index,
            score_column_id=score_column.id,
            score_value=score.value,
            score_id=score.id,
        )

        chart_results.results.append(result)

    _sort_chart_results(chart_results)

    return chart_results


def _sort_chart_results(chart_results: ColumnResults):
    chart_results.results.sort(key=lambda r: (-r.score_value, r.player_order_index))

    if len(chart_results.results) > 0:
        chart_results.results[0].place = 1

    # Handle ties
    for i in range(1, len(chart_results.results)):
        result = chart_results.results[i]
        previous_result = chart_results.results[i - 1]

        if result.score_value == previous_result.score_value:
            result.is_tie = True
            previous_result.is_tie = True
            result.place = previous_result.place
        else:
            result.place = i + 1


def _populate_player_results(
    player_row: PlayerRow, column_results_list: list[ColumnResults]
) -> list[PlayerResults]:
    player = player_row.player
    score_table = player_row.score_table

    player_results = PlayerResults(
        player_id=player_row.player_id,
        player=player,
        order_index=player_row.order_index,
    )

    for column_results in column_results_list:
        result = _try_get_player_result(player.id, column_results.results)

        if not result:
            result = Result(
                player_id=player.id,
                player_order_index=player_row.order_index,
                score_column_id=column_results.score_column_id,
                place=len(column_results.results) + 1,
            )

        player_results.results.append(result)

    _calculate_player_total_score(player_results, score_table.format)

    return player_results


def _try_get_player_result(player_id: uuid.UUID, results: list[Result]) -> Result:
    for result in results:
        if result.player_id == player_id:
            return result
    return None


def _calculate_player_total_score(
    player_results: PlayerResults, score_table_format: ScoreTableFormat
):
    if score_table_format == ScoreTableFormat.SCORE_SUM:
        for result in player_results.results:
            player_results.total_score += result.score_value

    elif score_table_format == ScoreTableFormat.BATTLE:
        for result in player_results.results:
            if result.place == 1 and not result.is_tie and result.score_id is not None:
                player_results.total_score += 1


def _sort_player_results(results: list[PlayerResults]) -> list[PlayerResults]:
    results.sort(key=lambda x: (-x.total_score, x.order_index))

    if len(results) > 0:
        results[0].place = 1

    # Handle ties
    for i in range(1, len(results)):
        result = results[i]
        previous_result = results[i - 1]

        if result.total_score == previous_result.total_score:
            result.is_tie = True
            previous_result.is_tie = True
            result.place = previous_result.place
        else:
            result.place = i + 1

    return results
