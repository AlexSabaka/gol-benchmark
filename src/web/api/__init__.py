"""API router aggregation."""
from fastapi import APIRouter

from src.web.api.metadata import router as metadata_router
from src.web.api.plugins import router as plugins_router
from src.web.api.models import router as models_router
from src.web.api.testsets import router as testsets_router
from src.web.api.execution import router as execution_router
from src.web.api.analysis import router as analysis_router
from src.web.api.matrix import router as matrix_router
from src.web.api.human_review import router as human_review_router
from src.web.api.prompts import router as prompts_router

api_router = APIRouter()
api_router.include_router(metadata_router, prefix="/metadata", tags=["metadata"])
api_router.include_router(plugins_router, prefix="/plugins", tags=["plugins"])
api_router.include_router(models_router, prefix="/models", tags=["models"])
api_router.include_router(testsets_router, prefix="/testsets", tags=["testsets"])
api_router.include_router(execution_router, prefix="/jobs", tags=["jobs"])
api_router.include_router(matrix_router, prefix="/matrix", tags=["matrix"])
api_router.include_router(analysis_router, prefix="/results", tags=["results"])
api_router.include_router(human_review_router, prefix="/human-review", tags=["human-review"])
api_router.include_router(prompts_router, prefix="/prompts", tags=["prompts"])
