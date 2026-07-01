import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import db as db_module
from api.routes import router

app = FastAPI(title="Garmin Coach API")

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    os.environ.get("VERCEL_URL", ""),
    os.environ.get("FRONTEND_URL", ""),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in ALLOWED_ORIGINS if o],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["GET"],
    allow_headers=["*"],
)

db_module.init_db()

app.include_router(router)
