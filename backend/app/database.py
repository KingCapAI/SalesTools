import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import get_settings

settings = get_settings()

# For SQLite, create the data directory if it doesn't exist
if "sqlite" in settings.database_url:
    db_path = settings.database_url.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

# Create engine - check_same_thread=False needed for SQLite with FastAPI
connect_args = {"check_same_thread": False} if "sqlite" in settings.database_url else {}
engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,  # Helps with database connection reliability
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for getting database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations(engine):
    """Run manual migrations for SQLite (add new columns if they don't exist)."""
    from sqlalchemy import text, inspect

    inspector = inspect(engine)

    # Migration: Add design_type and reference_hat_path to designs table
    if 'designs' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('designs')]

        with engine.connect() as conn:
            if 'design_type' not in columns:
                conn.execute(text(
                    "ALTER TABLE designs ADD COLUMN design_type VARCHAR(50) DEFAULT 'ai_generated' NOT NULL"
                ))
                conn.commit()
                print("Migration: Added design_type column to designs table")

            if 'reference_hat_path' not in columns:
                conn.execute(text(
                    "ALTER TABLE designs ADD COLUMN reference_hat_path VARCHAR(500)"
                ))
                conn.commit()
                print("Migration: Added reference_hat_path column to designs table")

            if 'crown_color' not in columns:
                conn.execute(text(
                    "ALTER TABLE designs ADD COLUMN crown_color VARCHAR(100)"
                ))
                conn.commit()
                print("Migration: Added crown_color column to designs table")

            if 'visor_color' not in columns:
                conn.execute(text(
                    "ALTER TABLE designs ADD COLUMN visor_color VARCHAR(100)"
                ))
                conn.commit()
                print("Migration: Added visor_color column to designs table")

            if 'structure' not in columns:
                conn.execute(text(
                    "ALTER TABLE designs ADD COLUMN structure VARCHAR(50)"
                ))
                conn.commit()
                print("Migration: Added structure column to designs table")

            if 'closure' not in columns:
                conn.execute(text(
                    "ALTER TABLE designs ADD COLUMN closure VARCHAR(50)"
                ))
                conn.commit()
                print("Migration: Added closure column to designs table")

            if 'logo_path' not in columns:
                conn.execute(text(
                    "ALTER TABLE designs ADD COLUMN logo_path VARCHAR(500)"
                ))
                conn.commit()
                print("Migration: Added logo_path column to designs table")

            if 'selected_version_id' not in columns:
                conn.execute(text(
                    "ALTER TABLE designs ADD COLUMN selected_version_id VARCHAR(36)"
                ))
                conn.commit()
                print("Migration: Added selected_version_id column to designs table")

    # Migration: Add batch_number and is_selected to design_versions table
    if 'design_versions' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('design_versions')]

        with engine.connect() as conn:
            if 'batch_number' not in columns:
                conn.execute(text(
                    "ALTER TABLE design_versions ADD COLUMN batch_number INTEGER"
                ))
                conn.commit()
                print("Migration: Added batch_number column to design_versions table")

            if 'is_selected' not in columns:
                conn.execute(text(
                    "ALTER TABLE design_versions ADD COLUMN is_selected BOOLEAN DEFAULT FALSE NOT NULL"
                ))
                conn.commit()
                print("Migration: Added is_selected column to design_versions table")

    # Migration: Add Stripe columns to orders table
    if 'orders' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('orders')]

        with engine.connect() as conn:
            if 'stripe_session_id' not in columns and 'stripe_checkout_session_id' not in columns:
                conn.execute(text(
                    "ALTER TABLE orders ADD COLUMN stripe_checkout_session_id VARCHAR(255)"
                ))
                conn.commit()
                print("Migration: Added stripe_checkout_session_id column to orders table")

            if 'stripe_payment_intent_id' not in columns:
                conn.execute(text(
                    "ALTER TABLE orders ADD COLUMN stripe_payment_intent_id VARCHAR(255)"
                ))
                conn.commit()
                print("Migration: Added stripe_payment_intent_id column to orders table")


    # Migration: Split name → first_name + last_name, add shipping accounts to store_users
    if 'store_users' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('store_users')]

        with engine.connect() as conn:
            if 'first_name' not in columns:
                conn.execute(text(
                    "ALTER TABLE store_users ADD COLUMN first_name VARCHAR(255) NOT NULL DEFAULT ''"
                ))
                conn.commit()
                print("Migration: Added first_name column to store_users table")

            if 'last_name' not in columns:
                conn.execute(text(
                    "ALTER TABLE store_users ADD COLUMN last_name VARCHAR(255) NOT NULL DEFAULT ''"
                ))
                conn.commit()
                print("Migration: Added last_name column to store_users table")

                # Migrate existing name data to first_name/last_name
                if 'name' in columns:
                    conn.execute(text(
                        "UPDATE store_users SET first_name = SUBSTR(name, 1, INSTR(name || ' ', ' ') - 1), "
                        "last_name = CASE WHEN INSTR(name, ' ') > 0 THEN SUBSTR(name, INSTR(name, ' ') + 1) ELSE '' END"
                    ))
                    conn.commit()
                    print("Migration: Migrated name data to first_name/last_name")

            if 'website' not in columns:
                conn.execute(text(
                    "ALTER TABLE store_users ADD COLUMN website VARCHAR(500)"
                ))
                conn.commit()
                print("Migration: Added website column to store_users table")

            if 'ups_account_number' not in columns:
                conn.execute(text(
                    "ALTER TABLE store_users ADD COLUMN ups_account_number VARCHAR(100)"
                ))
                conn.commit()
                print("Migration: Added ups_account_number column to store_users table")

            if 'fedex_account_number' not in columns:
                conn.execute(text(
                    "ALTER TABLE store_users ADD COLUMN fedex_account_number VARCHAR(100)"
                ))
                conn.commit()
                print("Migration: Added fedex_account_number column to store_users table")

            if 'tax_exemption_path' not in columns:
                conn.execute(text(
                    "ALTER TABLE store_users ADD COLUMN tax_exemption_path VARCHAR(500)"
                ))
                conn.commit()
                print("Migration: Added tax_exemption_path column to store_users table")


def _migrate_cross_entity_links(engine, inspector):
    """Add cross-entity linking columns, sew-out approval type, and new order statuses."""
    from sqlalchemy import text

    # Orders: cross-linking fields
    if 'orders' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('orders')]
        with engine.connect() as conn:
            new_cols = {
                'source_quote_id': "VARCHAR(36)",
                'source_sample_request_id': "VARCHAR(36)",
                'order_type': "VARCHAR(50) DEFAULT 'standard' NOT NULL",
                'linked_production_order_id': "VARCHAR(36)",
            }
            for col_name, col_def in new_cols.items():
                if col_name not in columns:
                    conn.execute(text(f"ALTER TABLE orders ADD COLUMN {col_name} {col_def}"))
                    conn.commit()
                    print(f"Migration: Added {col_name} column to orders table")

    # Order items: art_id and design_request_id
    if 'order_items' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('order_items')]
        with engine.connect() as conn:
            if 'art_id' not in columns:
                conn.execute(text("ALTER TABLE order_items ADD COLUMN art_id VARCHAR(100)"))
                conn.commit()
                print("Migration: Added art_id column to order_items table")
            if 'design_request_id' not in columns:
                conn.execute(text("ALTER TABLE order_items ADD COLUMN design_request_id VARCHAR(36)"))
                conn.commit()
                print("Migration: Added design_request_id column to order_items table")

    # Quotes: cross-linking fields
    if 'quotes' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('quotes')]
        with engine.connect() as conn:
            if 'linked_sample_request_id' not in columns:
                conn.execute(text("ALTER TABLE quotes ADD COLUMN linked_sample_request_id VARCHAR(36)"))
                conn.commit()
                print("Migration: Added linked_sample_request_id column to quotes table")
            if 'linked_design_request_id' not in columns:
                conn.execute(text("ALTER TABLE quotes ADD COLUMN linked_design_request_id VARCHAR(36)"))
                conn.commit()
                print("Migration: Added linked_design_request_id column to quotes table")

    # Design requests: linked_quote_id
    if 'design_requests' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('design_requests')]
        with engine.connect() as conn:
            if 'linked_quote_id' not in columns:
                conn.execute(text("ALTER TABLE design_requests ADD COLUMN linked_quote_id VARCHAR(36)"))
                conn.commit()
                print("Migration: Added linked_quote_id column to design_requests table")

    # Mockup approvals: approval_type
    if 'mockup_approvals' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('mockup_approvals')]
        with engine.connect() as conn:
            if 'approval_type' not in columns:
                conn.execute(text("ALTER TABLE mockup_approvals ADD COLUMN approval_type VARCHAR(50) DEFAULT 'mockup' NOT NULL"))
                conn.commit()
                print("Migration: Added approval_type column to mockup_approvals table")


def _migrate_sample_requests(engine, inspector):
    """Migrate sample_requests to versioned multi-line-item system."""
    import uuid as _uuid
    from datetime import datetime as _dt
    from sqlalchemy import text

    if 'sample_requests' not in inspector.get_table_names():
        return

    columns = [col['name'] for col in inspector.get_columns('sample_requests')]

    with engine.connect() as conn:
        # Add new columns to sample_requests
        new_cols = {
            'current_version': "INTEGER DEFAULT 0",
            'factory_reference_number': "VARCHAR(255)",
            'bc_sales_order_number': "VARCHAR(100)",
            'bc_purchase_order_number': "VARCHAR(100)",
            'purchasing_assignee_id': "VARCHAR(36)",
        }
        for col_name, col_def in new_cols.items():
            if col_name not in columns:
                conn.execute(text(f"ALTER TABLE sample_requests ADD COLUMN {col_name} {col_def}"))
                conn.commit()
                print(f"Migration: Added {col_name} column to sample_requests table")

        # Migrate existing flat samples into line items (one-time)
        # Only run if sample_line_items table exists (created by create_all) and has no rows yet
        if 'sample_line_items' in inspector.get_table_names():
            existing_line_items = conn.execute(text("SELECT COUNT(*) FROM sample_line_items")).scalar()
            if existing_line_items == 0:
                # Find samples that have product_id set (old flat format)
                old_samples = conn.execute(text(
                    "SELECT id, product_id, variant_id, hat_color, sample_type, quantity, "
                    "front_decoration, left_decoration, right_decoration, back_decoration, visor_decoration, "
                    "front_logo_path, left_logo_path, right_logo_path, back_logo_path, visor_logo_path, "
                    "decoration_notes, status, requested_by_id "
                    "FROM sample_requests WHERE product_id IS NOT NULL"
                )).fetchall()

                if old_samples:
                    # Status mapping: old → new
                    status_map = {
                        'pending': 'submitted',
                        'approved': 'approved',
                        'in_production': 'in_production',
                        'shipped': 'sample_complete',
                        'delivered': 'customer_approved',
                        'rejected': 'rejected',
                    }

                    for row in old_samples:
                        sample_id = row[0]
                        line_item_id = str(_uuid.uuid4())
                        now = _dt.utcnow().isoformat()

                        # Create SampleLineItem
                        conn.execute(text(
                            "INSERT INTO sample_line_items "
                            "(id, sample_request_id, line_number, product_id, variant_id, hat_color, "
                            "sample_type, quantity, front_decoration, left_decoration, right_decoration, "
                            "back_decoration, visor_decoration, front_logo_path, left_logo_path, "
                            "right_logo_path, back_logo_path, visor_logo_path, decoration_notes, "
                            "line_status, created_at, updated_at) "
                            "VALUES (:id, :sr_id, 1, :prod, :var, :color, :stype, :qty, "
                            ":fd, :ld, :rd, :bd, :vd, :flp, :llp, :rlp, :blp, :vlp, :dn, "
                            "'pending', :now, :now)"
                        ), {
                            "id": line_item_id, "sr_id": sample_id,
                            "prod": row[1], "var": row[2], "color": row[3],
                            "stype": row[4] or "blank", "qty": row[5] or 1,
                            "fd": row[6], "ld": row[7], "rd": row[8], "bd": row[9], "vd": row[10],
                            "flp": row[11], "llp": row[12], "rlp": row[13], "blp": row[14], "vlp": row[15],
                            "dn": row[16], "now": now,
                        })

                        # Create initial SampleVersion
                        version_id = str(_uuid.uuid4())
                        conn.execute(text(
                            "INSERT INTO sample_versions "
                            "(id, sample_request_id, version_number, created_by_id, change_summary, created_at) "
                            "VALUES (:id, :sr_id, 1, :user_id, 'Initial submission (migrated)', :now)"
                        ), {"id": version_id, "sr_id": sample_id, "user_id": row[18], "now": now})

                        # Create SampleActivity
                        activity_id = str(_uuid.uuid4())
                        conn.execute(text(
                            "INSERT INTO sample_activities "
                            "(id, sample_request_id, user_id, action, description, created_at) "
                            "VALUES (:id, :sr_id, :user_id, 'migrated', 'Sample migrated to new versioned system', :now)"
                        ), {"id": activity_id, "sr_id": sample_id, "user_id": row[18], "now": now})

                        # Update status and current_version
                        old_status = row[17] or 'pending'
                        new_status = status_map.get(old_status, 'submitted')
                        conn.execute(text(
                            "UPDATE sample_requests SET status = :status, current_version = 1 WHERE id = :id"
                        ), {"status": new_status, "id": sample_id})

                    conn.commit()
                    print(f"Migration: Migrated {len(old_samples)} existing samples to new line-item format")


def _migrate_decoration_sizes(engine, inspector):
    """Add per-location decoration size columns to all line-item tables."""
    from sqlalchemy import text

    size_columns = [
        'front_decoration_size', 'left_decoration_size',
        'right_decoration_size', 'back_decoration_size',
        'visor_decoration_size',
    ]
    tables = ['order_items', 'quote_line_items', 'sample_line_items']

    for table in tables:
        if table not in inspector.get_table_names():
            continue
        columns = [col['name'] for col in inspector.get_columns(table)]
        with engine.connect() as conn:
            for col_name in size_columns:
                if col_name not in columns:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} VARCHAR(255)"))
                    conn.commit()
                    print(f"Migration: Added {col_name} column to {table} table")


def _migrate_order_design_link(engine, inspector):
    """Add linked_design_request_id column to orders table."""
    from sqlalchemy import text

    if 'orders' not in inspector.get_table_names():
        return
    columns = [col['name'] for col in inspector.get_columns('orders')]
    if 'linked_design_request_id' not in columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE orders ADD COLUMN linked_design_request_id VARCHAR(36)"))
            conn.commit()
            print("Migration: Added linked_design_request_id column to orders table")


def _migrate_sample_discount(engine, inspector):
    """Add discount_amount column to sample_requests table."""
    from sqlalchemy import text

    if 'sample_requests' not in inspector.get_table_names():
        return
    columns = [col['name'] for col in inspector.get_columns('sample_requests')]
    if 'discount_amount' not in columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE sample_requests ADD COLUMN discount_amount INTEGER NOT NULL DEFAULT 0"))
            conn.commit()
            print("Migration: Added discount_amount column to sample_requests table")


def _migrate_order_item_hat_color(engine, inspector):
    """Add hat_color column to order_items table."""
    from sqlalchemy import text

    if 'order_items' not in inspector.get_table_names():
        return
    columns = [col['name'] for col in inspector.get_columns('order_items')]
    if 'hat_color' not in columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE order_items ADD COLUMN hat_color VARCHAR(255)"))
            conn.commit()
            print("Migration: Added hat_color column to order_items table")


def init_db():
    """Initialize database tables."""
    from . import models  # Import models to register them
    from sqlalchemy import inspect
    Base.metadata.create_all(bind=engine)
    run_migrations(engine)
    _migrate_sample_requests(engine, inspect(engine))
    _migrate_cross_entity_links(engine, inspect(engine))
    _migrate_decoration_sizes(engine, inspect(engine))
    _migrate_order_design_link(engine, inspect(engine))
    _migrate_sample_discount(engine, inspect(engine))
    _migrate_order_item_hat_color(engine, inspect(engine))
