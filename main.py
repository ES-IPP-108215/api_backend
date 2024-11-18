from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from db.create_database import create_tables
from db.database import SessionLocal
from routers import user, task


@asynccontextmanager
async def lifespan(app):
    create_tables()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Todo List by Kernaite",
    version="0.0.1",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "Todo List by Kernaite",
    },
    servers=[{"url": "http://localhost:8000", "description": "Local server"}],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user.router)
app.include_router(task.router)

@app.get(
    "/health",
    tags=["healthcheck"],
    summary="Perform a Health Check",
    response_description="Return HTTP Status Code 200 (OK)",
    status_code=status.HTTP_200_OK,
)
def get_health():
    return {"status": "ok"}


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    request.state.db = SessionLocal()
    response = await call_next(request)
    request.state.db.close()
    return response
