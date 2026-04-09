"""Seed store database with King Cap product data from existing pricing data."""

from datetime import datetime
from sqlalchemy.orm import Session
from ..models.store_product import Product, ProductCategory, ProductColorway, ProductVariant, DecorationOption
from ..models.store_pricing import PricingTier, PricingRule
from ..models.store_user import StoreUser
from ..services.store_auth_service import hash_password
from ..data.pricing import (
    DOMESTIC_STYLES,
    DOMESTIC_BLANK_PRICES,
    DOMESTIC_QUANTITY_BREAKS,
    DOMESTIC_FRONT_DECORATION_METHODS,
    DOMESTIC_ADDITIONAL_DECORATION_METHODS,
    OVERSEAS_DECORATION_METHODS,
)


# Product metadata for richer catalog
PRODUCT_DETAILS = {
    "100": {
        "description": "The Origin Cap is where it all starts. A clean, classic 6-panel cap perfect for any brand or occasion. Made with quality cotton twill and built to last.",
        "short_description": "Classic 6-panel cotton twill cap",
        "panel_count": 6, "crown_type": "structured", "closure_type": "snapback",
        "visor_type": "pre-curved", "material": "cotton_twill", "sweatband": "cotton",
        "profile": "mid", "is_trucker": False, "is_perforated": False,
    },
    "150-FT": {
        "description": "The Ace Foam Trucker combines classic foam front panels with a breathable mesh back. A timeless trucker silhouette that's always in style.",
        "short_description": "Foam front trucker cap",
        "panel_count": 5, "crown_type": "structured", "closure_type": "snapback",
        "visor_type": "pre-curved", "material": "foam_mesh", "sweatband": "cotton",
        "profile": "high", "is_trucker": True, "is_perforated": False,
    },
    "230": {
        "description": "The Buddy Cap is a versatile unstructured cap with a relaxed fit. Perfect for everyday wear with a laid-back, effortless vibe.",
        "short_description": "Unstructured relaxed fit cap",
        "panel_count": 6, "crown_type": "unstructured", "closure_type": "strapback",
        "visor_type": "pre-curved", "material": "cotton_twill", "sweatband": "cotton",
        "profile": "low", "is_trucker": False, "is_perforated": False,
    },
    "260": {
        "description": "The Crest Cap is our signature structured cap. Bold, confident, and built with premium materials. The crown jewel of our Classic collection.",
        "short_description": "Premium structured cap",
        "panel_count": 6, "crown_type": "structured", "closure_type": "snapback",
        "visor_type": "flat", "material": "cotton_twill", "sweatband": "cotton",
        "profile": "mid", "is_trucker": False, "is_perforated": False,
    },
    "260-T": {
        "description": "The Crest Trucker Cap combines the structured front of our Crest Cap with a breathable mesh back. Premium meets performance.",
        "short_description": "Structured trucker cap",
        "panel_count": 6, "crown_type": "structured", "closure_type": "snapback",
        "visor_type": "flat", "material": "cotton_mesh", "sweatband": "cotton",
        "profile": "mid", "is_trucker": True, "is_perforated": False,
    },
    "250": {
        "description": "The Ace Cap is a modern take on the classic 5-panel. Clean lines and a contemporary silhouette for those who appreciate minimalist design.",
        "short_description": "Modern 5-panel cap",
        "panel_count": 5, "crown_type": "structured", "closure_type": "snapback",
        "visor_type": "flat", "material": "cotton_twill", "sweatband": "cotton",
        "profile": "mid", "is_trucker": False, "is_perforated": False,
    },
    "250-T": {
        "description": "The Ace Trucker Cap delivers the clean 5-panel look with added breathability from the mesh back panels.",
        "short_description": "5-panel trucker cap",
        "panel_count": 5, "crown_type": "structured", "closure_type": "snapback",
        "visor_type": "flat", "material": "cotton_mesh", "sweatband": "cotton",
        "profile": "mid", "is_trucker": True, "is_perforated": False,
    },
    "360": {
        "description": "The Crest Comfort Cap features a 2-way stretch design and ultra-plush sweatband. Crafted from 100% recycled materials for sustainable style.",
        "short_description": "2-way stretch comfort cap with recycled materials",
        "panel_count": 6, "crown_type": "structured", "closure_type": "strapback",
        "visor_type": "pre-curved", "material": "recycled_polyester", "sweatband": "moisture_wicking",
        "profile": "mid", "is_trucker": False, "is_perforated": False,
    },
    "360-T": {
        "description": "The Crest Comfort Trucker brings our signature comfort technology to a trucker silhouette. Stretch fit meets mesh breathability.",
        "short_description": "Comfort trucker with stretch fit",
        "panel_count": 6, "crown_type": "structured", "closure_type": "strapback",
        "visor_type": "pre-curved", "material": "recycled_polyester_mesh", "sweatband": "moisture_wicking",
        "profile": "mid", "is_trucker": True, "is_perforated": False,
    },
    "460": {
        "description": "The Crest Sport Cap is built for action with water-repellent fabric, moisture-wicking sweatband, and floatable construction. Made from recycled materials.",
        "short_description": "Performance sport cap, water-repellent and floatable",
        "panel_count": 6, "crown_type": "structured", "closure_type": "snapback",
        "visor_type": "pre-curved", "material": "performance_polyester", "sweatband": "moisture_wicking",
        "profile": "mid", "is_trucker": False, "is_perforated": False,
    },
    "460-P": {
        "description": "The Crest Sport Cap-Perforated adds laser-cut perforations for maximum airflow. Perfect for high-intensity outdoor activities.",
        "short_description": "Perforated sport cap with maximum breathability",
        "panel_count": 6, "crown_type": "structured", "closure_type": "snapback",
        "visor_type": "pre-curved", "material": "performance_polyester", "sweatband": "moisture_wicking",
        "profile": "mid", "is_trucker": False, "is_perforated": True,
    },
    "450": {
        "description": "The Ace Sport Cap combines 5-panel modern style with sport performance features. Water-repellent, breathable, and built from recycled materials.",
        "short_description": "5-panel sport performance cap",
        "panel_count": 5, "crown_type": "structured", "closure_type": "snapback",
        "visor_type": "pre-curved", "material": "performance_polyester", "sweatband": "moisture_wicking",
        "profile": "mid", "is_trucker": False, "is_perforated": False,
    },
    "450-P": {
        "description": "The Ace Sport Cap-Perforated delivers the 5-panel silhouette with perforated panels for enhanced ventilation during any activity.",
        "short_description": "Perforated 5-panel sport cap",
        "panel_count": 5, "crown_type": "structured", "closure_type": "snapback",
        "visor_type": "pre-curved", "material": "performance_polyester", "sweatband": "moisture_wicking",
        "profile": "mid", "is_trucker": False, "is_perforated": True,
    },
}

# Default colorways for all caps
DEFAULT_COLORWAYS = [
    {"name": "Black", "crown_color": "#000000", "visor_color": "#000000"},
    {"name": "Navy", "crown_color": "#1B2A4A", "visor_color": "#1B2A4A"},
    {"name": "White", "crown_color": "#FFFFFF", "visor_color": "#FFFFFF"},
    {"name": "Charcoal", "crown_color": "#4A4A4A", "visor_color": "#4A4A4A"},
    {"name": "Red", "crown_color": "#CC0000", "visor_color": "#CC0000"},
    {"name": "Royal Blue", "crown_color": "#1338BB", "visor_color": "#1338BB"},
    {"name": "Forest Green", "crown_color": "#2D5A27", "visor_color": "#2D5A27"},
    {"name": "Khaki", "crown_color": "#C3B091", "visor_color": "#C3B091"},
]


def seed_store_data(db: Session):
    """Seed the store with product catalog, categories, and pricing tiers."""

    # Always ensure staff accounts exist
    _ensure_staff_accounts(db)

    # Always ensure pricing rules are seeded
    _ensure_pricing_rules(db)

    # Always ensure shipping rates exist
    _ensure_shipping_rates(db)

    # Check if products already seeded
    existing = db.query(Product).first()
    if existing:
        print("Store data already seeded, skipping")
        return

    print("Seeding store data...")

    # 1. Create categories (one per collection)
    categories = {}
    for slug, name, desc in [
        ("basic", "Basic", "Essential caps that deliver quality at an unbeatable price"),
        ("classic", "Classic", "Timeless designs crafted with 100% recycled materials"),
        ("comfort", "Comfort", "Elevated comfort with 2-way stretch and ultra-plush sweatband"),
        ("sport", "Sport", "Performance headwear built for action with eco-friendly materials"),
    ]:
        cat = ProductCategory(
            name=name,
            slug=slug,
            description=desc,
            sort_order=["basic", "classic", "comfort", "sport"].index(slug),
            is_active=True,
        )
        db.add(cat)
        db.flush()
        categories[name] = cat

    # 2. Create products from existing pricing data
    for style_number, style_info in DOMESTIC_STYLES.items():
        name = style_info["name"]
        collection = style_info["collection"]
        details = PRODUCT_DETAILS.get(style_number, {})

        # Convert lowest qty price to cents for base_price (DTC retail markup ~2.5x)
        wholesale_price = DOMESTIC_BLANK_PRICES.get(style_number, {}).get(24, 6.00)
        base_price_cents = int(wholesale_price * 250)  # 2.5x markup, in cents

        slug = name.lower().replace(" ", "-").replace("(", "").replace(")", "")

        product = Product(
            name=name,
            slug=slug,
            style_number=style_number,
            description=details.get("description", ""),
            short_description=details.get("short_description", ""),
            collection=collection,
            production_type="domestic",
            base_price=base_price_cents,
            panel_count=details.get("panel_count"),
            crown_type=details.get("crown_type"),
            closure_type=details.get("closure_type"),
            visor_type=details.get("visor_type"),
            material=details.get("material"),
            sweatband=details.get("sweatband"),
            profile=details.get("profile"),
            is_trucker=details.get("is_trucker", False),
            is_perforated=details.get("is_perforated", False),
            is_active=True,
            is_featured=style_number in ("260", "360", "460", "250"),
            is_customizable=True,
            min_order_qty=1,
            category_id=categories.get(collection, categories.get("Basic")).id if collection in categories else None,
        )
        db.add(product)
        db.flush()

        # 3. Add colorways
        for cw in DEFAULT_COLORWAYS:
            mesh_color = "#4A4A4A" if product.is_trucker else None
            colorway = ProductColorway(
                product_id=product.id,
                name=cw["name"],
                crown_color=cw["crown_color"],
                visor_color=cw["visor_color"],
                mesh_color=mesh_color,
                is_active=True,
                sort_order=DEFAULT_COLORWAYS.index(cw),
            )
            db.add(colorway)
            db.flush()

            # 4. Add variant for each colorway (OSFA size)
            variant = ProductVariant(
                product_id=product.id,
                colorway_id=colorway.id,
                size="OSFA",
                sku=f"KC-{style_number}-{cw['name'].upper().replace(' ', '-')}-OSFA",
                stock_qty=100,
                is_active=True,
            )
            db.add(variant)

        # 5. Add decoration options
        locations = ["front", "left", "right", "back", "visor"]
        for location in locations:
            methods = DOMESTIC_FRONT_DECORATION_METHODS if location == "front" else DOMESTIC_ADDITIONAL_DECORATION_METHODS
            for method in methods:
                dec_option = DecorationOption(
                    product_id=product.id,
                    location=location,
                    method=method,
                    is_available=True,
                    additional_cost=0,
                )
                db.add(dec_option)

    # 6. Create pricing tiers
    dtc_tier = PricingTier(
        name="DTC Retail",
        description="Standard direct-to-consumer pricing",
        tier_type="dtc",
        discount_pct=0,
        is_default=True,
    )
    db.add(dtc_tier)

    wholesale_tier = PricingTier(
        name="Wholesale Standard",
        description="Standard wholesale pricing with quantity breaks",
        tier_type="wholesale",
        discount_pct=0.40,  # 40% off retail
    )
    db.add(wholesale_tier)

    golf_tier = PricingTier(
        name="Golf Pro Shop",
        description="Golf pro shop pricing",
        tier_type="golf",
        discount_pct=0.35,  # 35% off retail
    )
    db.add(golf_tier)

    db.commit()
    print(f"Store data seeded: {len(DOMESTIC_STYLES)} products, 4 categories, 3 pricing tiers")


def _ensure_staff_accounts(db: Session):
    """Ensure admin and salesperson accounts exist (runs every startup)."""
    created = []

    admin_exists = db.query(StoreUser).filter(StoreUser.email == "admin@kingcap.com").first()
    if not admin_exists:
        db.add(StoreUser(
            email="admin@kingcap.com",
            password_hash=hash_password("KingCap2024!"),
            first_name="King Cap",
            last_name="Admin",
            role="admin",
            status="active",
            email_verified_at=datetime.utcnow(),
        ))
        created.append("admin@kingcap.com")

    sales_exists = db.query(StoreUser).filter(StoreUser.email == "sales@kingcap.com").first()
    if not sales_exists:
        db.add(StoreUser(
            email="sales@kingcap.com",
            password_hash=hash_password("KingCap2024!"),
            first_name="King Cap",
            last_name="Sales",
            role="salesperson",
            status="active",
            email_verified_at=datetime.utcnow(),
        ))
        created.append("sales@kingcap.com")

    pm_exists = db.query(StoreUser).filter(StoreUser.email == "purchasing@kingcap.com").first()
    if not pm_exists:
        db.add(StoreUser(
            email="purchasing@kingcap.com",
            password_hash=hash_password("KingCap2024!"),
            first_name="King Cap",
            last_name="Purchasing",
            role="purchasing_manager",
            status="active",
            email_verified_at=datetime.utcnow(),
        ))
        created.append("purchasing@kingcap.com")

    dm_exists = db.query(StoreUser).filter(StoreUser.email == "design@kingcap.com").first()
    if not dm_exists:
        db.add(StoreUser(
            email="design@kingcap.com",
            password_hash=hash_password("KingCap2024!"),
            first_name="King Cap",
            last_name="Design",
            role="design_manager",
            status="active",
            email_verified_at=datetime.utcnow(),
        ))
        created.append("design@kingcap.com")

    # Patch existing staff accounts missing email_verified_at
    staff_emails = ["admin@kingcap.com", "sales@kingcap.com", "purchasing@kingcap.com", "design@kingcap.com"]
    patched = db.query(StoreUser).filter(
        StoreUser.email.in_(staff_emails),
        StoreUser.email_verified_at.is_(None),
    ).all()
    for user in patched:
        user.email_verified_at = datetime.utcnow()

    if created or patched:
        db.commit()
        if created:
            print(f"Staff accounts created: {', '.join(created)}")
        if patched:
            print(f"Staff accounts verified: {', '.join(u.email for u in patched)}")


def _ensure_pricing_rules(db: Session):
    """Seed pricing rules from DOMESTIC_BLANK_PRICES for wholesale and golf tiers (idempotent)."""
    # Check if any rules already exist
    existing_count = db.query(PricingRule).count()
    if existing_count > 0:
        return

    # Need products and tiers to exist first
    products = db.query(Product).all()
    if not products:
        return

    wholesale_tier = db.query(PricingTier).filter(PricingTier.tier_type == "wholesale").first()
    golf_tier = db.query(PricingTier).filter(PricingTier.tier_type == "golf").first()
    if not wholesale_tier or not golf_tier:
        return

    # Build product lookup by style_number
    product_map = {p.style_number: p for p in products}

    qty_breaks = DOMESTIC_QUANTITY_BREAKS  # [24, 48, 72, 144, 576, 2500]
    rules_created = 0

    for style_number, prices in DOMESTIC_BLANK_PRICES.items():
        product = product_map.get(style_number)
        if not product:
            continue

        for i, qty in enumerate(qty_breaks):
            price_dollars = prices.get(qty)
            if price_dollars is None:
                continue
            price_cents = int(round(price_dollars * 100))
            max_qty = qty_breaks[i + 1] - 1 if i + 1 < len(qty_breaks) else None

            # Same blank prices for both wholesale and golf tiers
            # (tier discount_pct handles the final price difference)
            for tier in [wholesale_tier, golf_tier]:
                db.add(PricingRule(
                    pricing_tier_id=tier.id,
                    product_id=product.id,
                    min_qty=qty,
                    max_qty=max_qty,
                    price_per_unit=price_cents,
                ))
                rules_created += 1

    if rules_created:
        db.commit()
        print(f"Pricing rules seeded: {rules_created} rules across wholesale and golf tiers")


def _ensure_shipping_rates(db: Session):
    """Seed default overseas shipping rates if none exist."""
    from ..models.shipping import ShippingRate

    if db.query(ShippingRate).first():
        return

    rates = [
        ShippingRate(
            method="ocean_fcl",
            label="Ocean Freight - Full Container (20ft)",
            cost_per_unit=250000,  # $2,500
            unit_type="container",
            min_volume_cbm=13.0,
            max_volume_cbm=33.0,
            transit_days_min=28,
            transit_days_max=31,
            buffer_days=5,
        ),
        ShippingRate(
            method="ocean_fcl_40",
            label="Ocean Freight - Full Container (40ft)",
            cost_per_unit=400000,  # $4,000
            unit_type="container",
            min_volume_cbm=25.0,
            max_volume_cbm=67.0,
            transit_days_min=28,
            transit_days_max=31,
            buffer_days=5,
        ),
        ShippingRate(
            method="ocean_lcl",
            label="Ocean Freight - Less Than Container",
            cost_per_unit=10000,  # $100 per CBM
            unit_type="cbm",
            min_volume_cbm=0.1,
            max_volume_cbm=13.0,
            transit_days_min=30,
            transit_days_max=38,
            buffer_days=7,
        ),
        ShippingRate(
            method="air_freight",
            label="Air Freight - Express",
            cost_per_unit=550,  # $5.50 per kg
            unit_type="kg",
            transit_days_min=2,
            transit_days_max=8,
            buffer_days=2,
        ),
    ]
    for rate in rates:
        db.add(rate)
    db.commit()
    print("Default shipping rates seeded")
