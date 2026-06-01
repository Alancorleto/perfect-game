from fastapi import APIRouter
from sqlalchemy.event import api

from routers.categories import router as category_router
from routers.categories import tag_metadata as category_tag_metadata
from routers.chart_columns import router as chart_column_router
from routers.chart_columns import tag_metadata as chart_column_tag_metadata
from routers.charts import router as chart_router
from routers.charts import tag_metadata as chart_tag_metadata
from routers.players import router as player_router
from routers.players import tag_metadata as player_tag_metadata
from routers.rounds import router as round_router
from routers.rounds import tag_metadata as round_tag_metadata
from routers.score_columns import router as score_column_router
from routers.score_columns import tag_metadata as score_column_tag_metadata
from routers.score_tables import router as score_table_router
from routers.score_tables import tag_metadata as score_table_tag_metadata
from routers.scores import router as score_router
from routers.scores import tag_metadata as score_tag_metadata
from routers.tournaments import router as tournament_router
from routers.tournaments import tag_metadata as tournament_tag_metadata
from routers.users import router as user_router
from routers.users import tag_metadata as user_tag_metadata

api_router = APIRouter()
api_router.include_router(user_router)
api_router.include_router(player_router)
api_router.include_router(tournament_router)
api_router.include_router(category_router)
api_router.include_router(round_router)
api_router.include_router(score_table_router)
api_router.include_router(score_column_router)
api_router.include_router(score_router)
api_router.include_router(chart_column_router)
api_router.include_router(chart_router)


tag_metadata = [
    user_tag_metadata,
    player_tag_metadata,
    tournament_tag_metadata,
    category_tag_metadata,
    round_tag_metadata,
    score_table_tag_metadata,
    score_column_tag_metadata,
    score_tag_metadata,
    chart_column_tag_metadata,
    chart_tag_metadata,
]
