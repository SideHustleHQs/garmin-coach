from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import DB_PATH, init_db
from api.routes import router

app = FastAPI(title="Garmin Coach API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db(DB_PATH)


app.include_router(router)
