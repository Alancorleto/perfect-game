import uuid
from fastapi import APIRouter, HTTPException
from models.chart import Chart
from models.set_chart import SetChartLink
from sqlmodel import Field, SQLModel, select, Relationship
from models.set import Set, SetCreate, SetResult, SetResultScore
from models.round import Round
from database import SessionDep

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
    
    repeat_index = len([link for link in db_set.chart_links if link.chart_id == chart_id])
    
    order_index = len(db_set.chart_links)

    set_chart_link = SetChartLink(
        set=db_set,
        chart=db_chart,
        repeat_index=repeat_index,
        order_index=order_index,
    )
    
    db_set.chart_links.append(set_chart_link)
    
    session.add(set_chart_link)
    session.commit()
    session.refresh(set_chart_link)
    
    return set_chart_link


@router.get("/{set_id}/results", response_model=list[SetResult])
def get_set_results(set_id: uuid.UUID, session: SessionDep):
    """Get the results for a specific set."""
    db_set = session.get(Set, set_id)
    if not db_set:
        raise HTTPException(status_code=404, detail="Set not found")
    
    results: list[SetResult] = []
    
    chart_links = sorted(db_set.chart_links, key=lambda link: link.order_index)
    
    for player_link in sorted(db_set.round.player_links, key=lambda link: link.order_index):
        player = player_link.player
        set_result: SetResult = SetResult(
            player_id=player.id,
            order_index=player_link.order_index,
            scores=[],
            total_score=0,
        )
        for chart_link in chart_links:
            set_result_score = SetResultScore(chart_id=chart_link.chart_id, repeat_index=chart_link.repeat_index, score=0, score_id=None)
            score_links = [score_link for score_link in db_set.round.score_links if score_link.score.chart_id == chart_link.chart_id and score_link.repeat_index == chart_link.repeat_index and score_link.score.player_id == player.id]
            
            if any(score_links):
                score = score_links[0].score
                set_result_score.score = score.value
                set_result_score.score_id = score.id
                set_result.total_score += score.value
            
            set_result.scores.append(set_result_score)
        
        results.append(set_result)

    results.sort(key=lambda r: (-r.total_score, r.order_index))

    return results