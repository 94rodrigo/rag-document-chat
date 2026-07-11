from fastapi import APIRouter

from app.api.v1 import auth, billing, conversations, documents, users

api_router = APIRouter(prefix="/api")
v1 = APIRouter(prefix="/v1")

v1.include_router(auth.router)
v1.include_router(users.router)
v1.include_router(documents.router)
v1.include_router(conversations.router)
v1.include_router(billing.router)

api_router.include_router(v1)
