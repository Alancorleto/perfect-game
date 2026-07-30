import uuid
from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel
from sqlmodel import Field, Relationship, SQLModel

from models.player import Player
from models.player_row import PlayerRow
from models.round import Round
from models.user import User
from models.score_grade import ScoreGrade


if TYPE_CHECKING:
    from models.score_column import ScoreColumn
    from models.score import Score


class ScoreTableFormat(Enum):
    SCORE_SUM = "score_sum"
    BATTLE = "battle"
    CUSTOM_SET = "custom_set"


class PlayerStanding(BaseModel):
    id: uuid.UUID
    nickname: str
    country_code: str
    order_index: int = 0


class ResultScore(BaseModel):
    id: uuid.UUID | None = None
    value: int = 0
    grade: ScoreGrade | None = None
    stage_pass: bool = False

    @classmethod
    def from_score(cls, score: "Score") -> "ResultScore":
        return cls(
            id=score.id,
            value=score.value,
            grade=score.grade,
            stage_pass=score.stage_pass,
        )


class Result(BaseModel):
    player_order_index: int = 0
    score: ResultScore
    place: int = -1


class ColumnResults(BaseModel):
    score_column_id: uuid.UUID
    results: list[Result] = []

    @classmethod
    def from_score_column(cls, score_column: "ScoreColumn", player_rows: list["PlayerRow"]) -> "ColumnResults":
        column_results = cls(score_column_id=score_column.id)

        player_id_to_order_index = {
            player_row.player.id: player_row.order_index for player_row in player_rows
        }

        for score in score_column.scores:
            player_order_index = player_id_to_order_index[score.player_id]
            result = Result(
                player_order_index=player_order_index,
                score=ResultScore.from_score(score),
                place=-1,
            )

            column_results.results.append(result)

        column_results._sort()
        column_results._assign_places()

        return column_results

    def is_tie(self) -> bool:
        if len(self.results) == 0:
            return False
        return all(result.score.value == self.results[0].score.value for result in self.results)

    def _sort(self):
        self.results.sort(key=lambda r: (-r.score.value, r.player_order_index))

    def _assign_places(self):
        if len(self.results) > 0:
            self.results[0].place = 1

        for i in range(1, len(self.results)):
            result = self.results[i]
            previous_result = self.results[i - 1]

            if result.score.value == previous_result.score.value:
                result.place = previous_result.place
            else:
                result.place = i + 1


class TotalResult(BaseModel):
    player_order_index: int = 0
    score: int = 0
    place: int = -1


class Results(BaseModel):
    player_standings: list[PlayerStanding] = []
    columns_results: list[ColumnResults] = []
    total_results: list[TotalResult] = []

    def populate_total_results(self, format: ScoreTableFormat) -> None:
        for player_standing in self.player_standings:
            self.total_results.append(
                TotalResult(player_order_index=player_standing.order_index)
            )

        for column_results in self.columns_results:
            # Skip tie columns in battle format
            if format == ScoreTableFormat.BATTLE and column_results.is_tie():
                continue

            for result in column_results.results:
                total_result = self.total_results[result.player_order_index]

                if format == ScoreTableFormat.SCORE_SUM:
                    total_result.score += result.score.value
                elif format == ScoreTableFormat.BATTLE:
                    total_result.score += len(column_results.results) - result.place

        self._sort_total_results()
        self._assign_final_places()

    def _sort_total_results(self) -> None:
        self.total_results.sort(key=lambda tr: (-tr.score, tr.player_order_index))

    def _assign_final_places(self) -> None:
        if len(self.total_results) > 0:
            self.total_results[0].place = 1

        for i in range(1, len(self.total_results)):
            result = self.total_results[i]
            previous_result = self.total_results[i - 1]

            if result.score == previous_result.score:
                result.place = previous_result.place
            else:
                result.place = i + 1

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

    def get_results(self) -> Results:
        results = Results()

        results.player_standings = [
            PlayerStanding(
                id=player_row.player.id,
                nickname=player_row.player.nickname,
                country_code=player_row.player.country_code,
                order_index=player_row.order_index,
            )
            for player_row in self.player_rows
        ]

        results.player_standings.sort(key=lambda ps: ps.order_index)

        score_columns = self.get_score_columns_by_order()

        for score_column in score_columns:
            column_results = ColumnResults.from_score_column(score_column, self.player_rows)
            results.columns_results.append(column_results)

        results.populate_total_results(self.format)

        return results

    def get_qualifying_players(self) -> list[Player]:
        if self.qualifiers_count is None:
            return self.get_players_by_order()

        results = self.get_results()
        qualifying_players_order_indexes = [
            total_result.player_order_index
            for total_result in results.total_results
            if total_result.place <= self.qualifiers_count
        ]

        players_by_order = self.get_players_by_order()
        qualifying_players = [
            players_by_order[order_index]
            for order_index in qualifying_players_order_indexes
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
