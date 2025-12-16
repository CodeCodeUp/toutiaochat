from fastapi import APIRouter

from app.api.v1 import articles, accounts, tasks, prompts

api_router = APIRouter()

api_router.include_router(articles.router)
api_router.include_router(accounts.router)
api_router.include_router(tasks.router)
api_router.include_router(prompts.router)
