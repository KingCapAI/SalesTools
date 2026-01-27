"""King Cap HQ - FastAPI Backend Application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import get_settings
from .database import init_db, SessionLocal
from .models import Team
from .routers import auth, customers, brands, designs, uploads, ai, users, quotes, design_quotes
from .routers.uploads import uploads_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    init_db()
    seed_default_data()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="King Cap HQ API",
    description="Internal dashboard API for King Cap sales team",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "https://kingcaphq.com",
        "https://www.kingcaphq.com",
        "https://kingcap-hub.pages.dev",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def seed_default_data():
    """Seed default teams and data."""
    db = SessionLocal()
    try:
        # Check if teams exist
        existing_teams = db.query(Team).count()
        if existing_teams == 0:
            # Create default teams
            teams = [
                Team(
                    name="sales",
                    allowed_apps=[
                        "ai-design-generator",
                        "quote-estimator",
                        "marketing-tools",
                        "policies",
                    ],
                ),
                Team(
                    name="finance",
                    allowed_apps=["quote-estimator", "policies"],
                ),
                Team(
                    name="marketing",
                    allowed_apps=["ai-design-generator", "marketing-tools", "policies"],
                ),
                Team(
                    name="admin",
                    allowed_apps=[
                        "ai-design-generator",
                        "quote-estimator",
                        "marketing-tools",
                        "policies",
                    ],
                ),
            ]
            for team in teams:
                db.add(team)
            db.commit()
            print("Default teams seeded successfully")
    finally:
        db.close()


# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(customers.router, prefix="/api")
app.include_router(brands.router, prefix="/api")
app.include_router(designs.router, prefix="/api")
app.include_router(design_quotes.router, prefix="/api")
app.include_router(uploads.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(quotes.router, prefix="/api")
app.include_router(uploads_router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "King Cap HQ API",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/debug/config")
async def debug_config():
    """Debug endpoint to check config values."""
    return {
        "frontend_url": settings.frontend_url,
        "backend_url": settings.backend_url,
    }
