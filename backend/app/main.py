"""King Cap HQ - FastAPI Backend Application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from .config import get_settings
from .database import init_db, SessionLocal
from .models import Team
from .routers import auth, customers, brands, designs, uploads, ai, users, quotes, design_quotes, custom_designs
from .routers.uploads import uploads_router
from .routers import store_auth, store_products, store_cart, store_orders, store_checkout, store_addresses
from .routers import admin_analytics, admin_cms, admin_customers, admin_pricing, sales, sample_requests, design_requests
from .routers import cms_public, shipping_agent
from .routers import purchasing, contact, sync, webhooks, store_returns, store_quotes
from .routers import social_media
from .services.store_seed_service import seed_store_data

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    init_db()
    seed_default_data()
    seed_store()
    seed_test_customer()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="King Cap HQ API",
    description="Internal dashboard API for King Cap sales team",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "https://kingcaphq.com",
        "https://www.kingcaphq.com",
        "https://kingcap-hub.pages.dev",
        "https://wearkingcap.com",
        "https://www.wearkingcap.com",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def seed_default_data():
    """Seed default teams and data."""
    db = SessionLocal()
    try:
        # First, ensure all existing teams have custom-design-builder
        existing_teams = db.query(Team).all()
        for team in existing_teams:
            if team.allowed_apps and "custom-design-builder" not in team.allowed_apps:
                team.allowed_apps = team.allowed_apps + ["custom-design-builder"]
        db.commit()

        # Check if teams exist
        if len(existing_teams) == 0:
            # Create default teams
            teams = [
                Team(
                    name="sales",
                    allowed_apps=[
                        "ai-design-generator",
                        "custom-design-builder",
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
                    allowed_apps=["ai-design-generator", "custom-design-builder", "marketing-tools", "policies"],
                ),
                Team(
                    name="admin",
                    allowed_apps=[
                        "ai-design-generator",
                        "custom-design-builder",
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


def seed_store():
    """Seed store product catalog and pricing data."""
    db = SessionLocal()
    try:
        seed_store_data(db)
    finally:
        db.close()


def seed_test_customer():
    """Seed a test salesperson and test customer for development."""
    from .models.store_user import StoreUser
    from .services.store_auth_service import hash_password

    db = SessionLocal()
    try:
        # Create test salesperson if not exists
        sales_email = "sales@kingcaphats.com"
        salesperson = db.query(StoreUser).filter(StoreUser.email == sales_email).first()
        if not salesperson:
            salesperson = StoreUser(
                email=sales_email,
                password_hash=hash_password("testpass123"),
                name="Test Salesperson",
                first_name="Test",
                last_name="Salesperson",
                role="salesperson",
                status="active",
            )
            db.add(salesperson)
            db.flush()
            print(f"Test salesperson created: {sales_email} / testpass123")

        # Create test customer if not exists
        cust_email = "jordan@acegolfclub.com"
        customer = db.query(StoreUser).filter(StoreUser.email == cust_email).first()
        if not customer:
            customer = StoreUser(
                email=cust_email,
                password_hash=hash_password("testpass123"),
                name="Ace Golf Club",
                first_name="Jordan",
                last_name="Palmer",
                phone="555-867-5309",
                company_name="Ace Golf Club",
                role="customer",
                status="active",
                salesperson_id=salesperson.id,
            )
            db.add(customer)
            print(f"Test customer created: {cust_email} / testpass123  (Ace Golf Club — Jordan Palmer)")

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Test data seed error (non-fatal): {e}")
    finally:
        db.close()


# Include routers - HQ internal
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(customers.router, prefix="/api")
app.include_router(brands.router, prefix="/api")
app.include_router(designs.router, prefix="/api")
app.include_router(design_quotes.router, prefix="/api")
app.include_router(custom_designs.router, prefix="/api")
app.include_router(uploads.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(quotes.router, prefix="/api")
app.include_router(uploads_router, prefix="/api")

# Include routers - Store (public e-commerce)
app.include_router(store_auth.router, prefix="/api")
app.include_router(store_products.router, prefix="/api")
app.include_router(store_cart.router, prefix="/api")
app.include_router(store_orders.router, prefix="/api")
app.include_router(store_checkout.router, prefix="/api")
app.include_router(store_addresses.router, prefix="/api")

# Include routers - Admin
app.include_router(admin_analytics.router, prefix="/api")
app.include_router(admin_cms.router, prefix="/api")
app.include_router(admin_customers.router, prefix="/api")
app.include_router(admin_pricing.router, prefix="/api")
app.include_router(shipping_agent.router, prefix="/api")

# Include routers - Purchasing Manager
app.include_router(purchasing.router, prefix="/api")

# Include routers - Contact Form
app.include_router(contact.router, prefix="/api")

# Include routers - CMS Public
app.include_router(cms_public.router, prefix="/api")

# Include routers - Sales & Samples
app.include_router(sales.router, prefix="/api")
app.include_router(sample_requests.router, prefix="/api")

# Include routers - Design Requests
app.include_router(design_requests.router, prefix="/api")

# Include routers - Sync Management (BC, Pipedrive, etc.)
app.include_router(sync.router, prefix="/api")

# Include routers - Returns & Customer Quotes
app.include_router(store_returns.router, prefix="/api")
app.include_router(store_quotes.router, prefix="/api")

# Include routers - Inbound Webhooks (Pipedrive, ShipStation, BC)
app.include_router(webhooks.router, prefix="/api")

# Include routers - Social Media Manager
app.include_router(social_media.router, prefix="/api")

# Serve uploaded files (local fallback — when R2 is configured, uploads.py redirects to R2)
uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
from .services.r2_service import _use_r2
if not _use_r2():
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


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
