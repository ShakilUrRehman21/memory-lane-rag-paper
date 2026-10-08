from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db
from app.api.routes_documents import router as documents_router
from app.api.routes_query import router as query_router
from app.api.routes_timeline import router as timeline_router
from app.api.routes_changes import router as changes_router
from app.api.routes_versions import router as versions_router
from app.api.routes_graph import router as graph_router
from app.api.routes_research import router as research_router
from app.api.routes_users import router as users_router
from app.api.routes_auth import router as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables & folders exist
    init_db()
    yield
    # Shutdown

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Temporal Retrieval-Augmented Generation System for Longitudinal Reasoning & Historical Change Detection",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(users_router, prefix=settings.API_PREFIX)
app.include_router(documents_router, prefix=settings.API_PREFIX)
app.include_router(query_router, prefix=settings.API_PREFIX)
app.include_router(timeline_router, prefix=settings.API_PREFIX)
app.include_router(changes_router, prefix=settings.API_PREFIX)
app.include_router(versions_router, prefix=settings.API_PREFIX)
app.include_router(graph_router, prefix=settings.API_PREFIX)
app.include_router(research_router, prefix=settings.API_PREFIX)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

# Mount production frontend static files if built
frontend_dist = settings.BASE_DIR / "frontend" / "dist"
if frontend_dist.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

