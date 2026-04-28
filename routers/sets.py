import uuid
from fastapi import APIRouter, HTTPException
from models.chart import Chart
from models.player import Player
from models.chart_slot import ChartSlot
from sqlmodel import Field, SQLModel, select, Relationship
from models.score import Score
from models.set import Set, SetCreate, SetFormat, SetResult, SetResultScore
from models.round import Round
from database import SessionDep
from models.set_player import SetPlayerLink

router = APIRouter(
    prefix="/sets",
    tags=["sets"]
)


@router.post("/", response_model=Set)
def create_set(set: SetCreate, session: SessionDep):
    """Create a new set for a round."""
    round = session.get(Round, set.round_id)
    if not round:
        raise HTTPException(status_code=404, detail="Round not found")
    
    db_set = Set.model_validate(set)
    session.add(db_set)
    session.commit()
    session.refresh(db_set)
    return db_set


@router.get("/{set_id}", response_model=Set)
def get_set(set_id: uuid.UUID, session: SessionDep):
    """Get a specific set."""
    db_set = session.get(Set, set_id)
    if not db_set:
        raise HTTPException(status_code=404, detail="Set not found")
    return db_set


@router.post("/{set_id}/charts")
async def add_chart_to_set(set_id: uuid.UUID, chart_id: uuid.UUID, session: SessionDep):
    """Add a chart to a set"""
    db_set = session.get(Set, set_id)
    if not db_set:
        raise HTTPException(status_code=404, detail="Set not found")
    
    db_chart = session.get(Chart, chart_id)
    if not db_chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    
    order_index = len(db_set.chart_slots)

    chart_slot = ChartSlot(
        set=db_set,
        chart=db_chart,
        order_index=order_index,
    )
    
    db_set.chart_slots.append(chart_slot)
    
    session.add(chart_slot)
    session.commit()
    session.refresh(chart_slot)
    
    return chart_slot


@router.post("/{set_id}/players/bulk")
async def bulk_add_players_to_set(set_id: uuid.UUID, player_ids: list[uuid.UUID], session: SessionDep):
    """Bulk add players to a set"""
    db_set = session.get(Set, set_id)
    if not db_set:
        raise HTTPException(status_code=404, detail="Set not found")
    
    # Filter out player IDs that are already in the set
    player_ids = filter(
        lambda pid: not any(link.player_id == pid for link in db_set.player_links),
        player_ids
    )

    previous_player_count = len(db_set.player_links)

    for i, player_id in enumerate(player_ids):
        db_player = session.get(Player, player_id)
        if not db_player:
            raise HTTPException(status_code=404, detail=f"Player with ID {player_id} not found")
        order_index = previous_player_count + i
        set_player_link = SetPlayerLink(set=db_set, player=db_player, order_index=order_index)
        db_set.player_links.append(set_player_link)
    
    session.add(db_set)
    session.commit()
    session.refresh(db_set)
    
    return db_set


@router.get("/{set_id}/results", response_model=list[SetResult])
def get_set_results(set_id: uuid.UUID, session: SessionDep):
    """Get the results for a specific set."""
    db_set = session.get(Set, set_id)
    if not db_set:
        raise HTTPException(status_code=404, detail="Set not found")
    
    results: list[SetResult] = []
    
    chart_slots = sorted(db_set.chart_slots, key=lambda link: link.order_index)
    
    # Precompute sorted scores for each chart slot to determine place indices
    sorted_scores: dict[uuid.UUID, list[tuple[int, Score]]] = _sort_chart_slot_scores(chart_slots)

    for player_link in db_set.player_links:
        player = player_link.player
        
        set_result: SetResult = SetResult(
            player_id=player.id,
            order_index=player_link.order_index,
            scores=[],
            total_score=0,
        )
        
        for chart_slot in chart_slots:
            set_result_score = SetResultScore(
                chart_id=chart_slot.chart_id,
                order_index=chart_slot.order_index,
                score=0,
                score_id=None
            )

            score = next(
                (
                    score_entry.score
                    for score_entry in chart_slot.score_entries
                    if score_entry.score.player_id == player.id
                ),
                None
            )
            
            if score:
                set_result_score.score = score.value
                set_result_score.score_id = score.id
                
                set_result_score.place = next(
                    i for i, s in sorted_scores[chart_slot.id]
                    if s.id == score.id
                )

                if db_set.format == SetFormat.SCORE_SUM:
                    set_result.total_score += score.value
                elif db_set.format == SetFormat.BATTLE:
                    max_score = max(score_entry.score.value for score_entry in chart_slot.score_entries)
                    if score.value == max_score:
                        set_result.total_score += 1
            else:
                set_result_score.place = len(sorted_scores[chart_slot.id]) + 1
            
            set_result.scores.append(set_result_score)
        
        results.append(set_result)

    results.sort(key=lambda r: (-r.total_score, r.order_index))

    return results


def _sort_chart_slot_scores(chart_slots: list[ChartSlot]) -> dict[uuid.UUID, list[tuple[int, Score]]]:
    sorted_scores: dict[uuid.UUID, list[tuple[int, Score]]] = {}
    
    for chart_slot in chart_slots:
        scores = [score_entry.score for score_entry in chart_slot.score_entries]
        scores.sort(key=lambda s: s.value, reverse=True)

        scores_enumerated = list(enumerate(scores, start=1))
        
        # Handle ties by assigning the same place index to tied scores
        for i in range(len(scores_enumerated) - 1):
            if scores_enumerated[i][1].value == scores_enumerated[i + 1][1].value:
                scores_enumerated[i + 1][0] = scores_enumerated[i][0]
        
        sorted_scores[chart_slot.id] = scores_enumerated
    
    return sorted_scores
