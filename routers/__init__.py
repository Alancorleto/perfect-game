from fastapi import APIRouter
from sqlalchemy.event import api

from routers.categories import router as category_router
from routers.chart_columns import router as chart_column_router
from routers.charts import router as chart_router
from routers.players import router as player_router
from routers.rounds import router as round_router
from routers.score_columns import router as score_column_router
from routers.score_tables import router as score_table_router
from routers.scores import router as score_router
from routers.tournaments import router as tournament_router
from routers.users import router as user_router

api_router = APIRouter()
api_router.include_router(user_router)
api_router.include_router(player_router)
api_router.include_router(chart_router)
api_router.include_router(chart_column_router)
api_router.include_router(tournament_router)
api_router.include_router(category_router)
api_router.include_router(round_router)
api_router.include_router(score_table_router)
api_router.include_router(score_router)
api_router.include_router(score_column_router)
