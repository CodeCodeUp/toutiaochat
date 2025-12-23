from fastapi import APIRouter

from app.api.v1 import articles, accounts, tasks, prompts, ai_configs, workflows, workflow_configs

api_router = APIRouter()

api_router.include_router(articles.router)
api_router.include_router(accounts.router)
api_router.include_router(tasks.router)
api_router.include_router(prompts.router)
api_router.include_router(ai_configs.router)
api_router.include_router(workflows.router)
api_router.include_router(workflow_configs.router)
