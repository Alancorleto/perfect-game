from fastapi import APIRouter
from routers.players import router as player_router
from routers.tournaments import router as tournament_router
from routers.categories import router as category_router
from routers.rounds import router as round_router
from routers.songs import router as song_router
from routers.charts import router as chart_router
from routers.scores import router as score_router
from routers.sum_formats import router as sum_format_router

api_router = APIRouter()
api_router.include_router(player_router)
api_router.include_router(tournament_router)
api_router.include_router(category_router)
api_router.include_router(round_router)
api_router.include_router(song_router)
api_router.include_router(chart_router)
api_router.include_router(score_router)
api_router.include_router(sum_format_router)
