from pathlib import Path
import sqlite3


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    role TEXT NOT NULL DEFAULT 'admin',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS partners (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    partner_type TEXT NOT NULL,
    name TEXT NOT NULL,
    phone TEXT,
    contact_name TEXT,
    address TEXT,
    note TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(partner_type, name)
);

CREATE TABLE IF NOT EXISTS warehouses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    note TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    warehouse_id INTEGER NOT NULL,
    location_code TEXT NOT NULL,
    note TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(warehouse_id, location_code),
    FOREIGN KEY(warehouse_id) REFERENCES warehouses(id)
);

CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_code TEXT NOT NULL UNIQUE,
    item_name TEXT NOT NULL,
    item_type TEXT NOT NULL,
    category TEXT,
    unit TEXT NOT NULL DEFAULT '件',
    sku TEXT,
    barcode TEXT,
    spec TEXT,
    default_warehouse_id INTEGER,
    default_location_id INTEGER,
    platform_sku TEXT,
    supplier_id INTEGER,
    lead_days INTEGER NOT NULL DEFAULT 0,
    is_producible INTEGER NOT NULL DEFAULT 0,
    is_packaging INTEGER NOT NULL DEFAULT 0,
    safety_stock REAL NOT NULL DEFAULT 0,
    purchase_price REAL NOT NULL DEFAULT 0,
    cost_price REAL NOT NULL DEFAULT 0,
    sale_price REAL NOT NULL DEFAULT 0,
    is_sellable INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(default_warehouse_id) REFERENCES warehouses(id),
    FOREIGN KEY(default_location_id) REFERENCES locations(id),
    FOREIGN KEY(supplier_id) REFERENCES partners(id)
);

CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movement_no TEXT NOT NULL UNIQUE,
    movement_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    row_version INTEGER NOT NULL DEFAULT 0,
    reversed_movement_no TEXT,
    voided_at TEXT,
    voided_by TEXT,
    item_id INTEGER NOT NULL,
    warehouse_id INTEGER NOT NULL,
    quantity REAL NOT NULL,
    unit_cost REAL NOT NULL DEFAULT 0,
    source_type TEXT,
    source_no TEXT,
    document_id INTEGER,
    partner_id INTEGER,
    note TEXT,
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY(item_id) REFERENCES items(id),
    FOREIGN KEY(warehouse_id) REFERENCES warehouses(id),
    FOREIGN KEY(document_id) REFERENCES documents(id),
    FOREIGN KEY(partner_id) REFERENCES partners(id)
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_no TEXT NOT NULL UNIQUE,
    document_type TEXT NOT NULL,
    source_channel TEXT NOT NULL DEFAULT 'manual',
    partner_id INTEGER,
    status TEXT NOT NULL DEFAULT 'confirmed',
    row_version INTEGER NOT NULL DEFAULT 0,
    reversed_from_id INTEGER,
    reversed_document_no TEXT,
    voided_at TEXT,
    voided_by TEXT,
    total_amount REAL NOT NULL DEFAULT 0,
    paid_amount REAL NOT NULL DEFAULT 0,
    note TEXT,
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(partner_id) REFERENCES partners(id)
);

CREATE TABLE IF NOT EXISTS sales_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no TEXT NOT NULL UNIQUE,
    source_channel TEXT NOT NULL DEFAULT 'manual',
    platform TEXT,
    shop_name TEXT,
    customer_id INTEGER,
    customer_name TEXT,
    status TEXT NOT NULL DEFAULT 'pending_review',
    row_version INTEGER NOT NULL DEFAULT 0,
    reversed_order_no TEXT,
    warehouse_id INTEGER,
    total_amount REAL NOT NULL DEFAULT 0,
    locked_at TEXT,
    shipped_at TEXT,
    logistics_company TEXT,
    tracking_no TEXT,
    note TEXT,
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(customer_id) REFERENCES partners(id),
    FOREIGN KEY(warehouse_id) REFERENCES warehouses(id)
);

CREATE TABLE IF NOT EXISTS production_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    production_no TEXT NOT NULL UNIQUE,
    finished_item_id INTEGER NOT NULL,
    warehouse_id INTEGER NOT NULL,
    quantity REAL NOT NULL,
    production_type TEXT,
    production_line TEXT,
    operator_name TEXT,
    note TEXT,
    created_by TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(finished_item_id) REFERENCES items(id),
    FOREIGN KEY(warehouse_id) REFERENCES warehouses(id)
);

CREATE TABLE IF NOT EXISTS sales_order_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sales_order_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    quantity REAL NOT NULL,
    sale_price REAL NOT NULL DEFAULT 0,
    line_amount REAL NOT NULL DEFAULT 0,
    shipped_quantity REAL NOT NULL DEFAULT 0,
    FOREIGN KEY(sales_order_id) REFERENCES sales_orders(id),
    FOREIGN KEY(item_id) REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS stock_locks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    warehouse_id INTEGER NOT NULL,
    quantity REAL NOT NULL,
    source_type TEXT NOT NULL,
    source_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'locked',
    created_at TEXT NOT NULL,
    released_at TEXT,
    FOREIGN KEY(item_id) REFERENCES items(id),
    FOREIGN KEY(warehouse_id) REFERENCES warehouses(id)
);

CREATE TABLE IF NOT EXISTS after_sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    after_sale_no TEXT NOT NULL UNIQUE,
    sales_order_id INTEGER,
    tracking_no TEXT,
    item_id INTEGER,
    quantity REAL NOT NULL DEFAULT 1,
    return_quality TEXT NOT NULL DEFAULT 'good',
    status TEXT NOT NULL DEFAULT 'pending',
    stock_movement_id INTEGER,
    note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(sales_order_id) REFERENCES sales_orders(id),
    FOREIGN KEY(item_id) REFERENCES items(id),
    FOREIGN KEY(stock_movement_id) REFERENCES stock_movements(id)
);

CREATE TABLE IF NOT EXISTS platform_settlements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    settlement_no TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'active',
    row_version INTEGER NOT NULL DEFAULT 0,
    reversed_settlement_no TEXT,
    voided_at TEXT,
    voided_by TEXT,
    platform TEXT,
    amount REAL NOT NULL DEFAULT 0,
    commission REAL NOT NULL DEFAULT 0,
    freight REAL NOT NULL DEFAULT 0,
    refund_amount REAL NOT NULL DEFAULT 0,
    net_amount REAL NOT NULL DEFAULT 0,
    settled_at TEXT,
    note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS document_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    warehouse_id INTEGER NOT NULL,
    quantity REAL NOT NULL,
    unit_price REAL NOT NULL DEFAULT 0,
    line_amount REAL NOT NULL DEFAULT 0,
    note TEXT,
    FOREIGN KEY(document_id) REFERENCES documents(id),
    FOREIGN KEY(item_id) REFERENCES items(id),
    FOREIGN KEY(warehouse_id) REFERENCES warehouses(id)
);

CREATE TABLE IF NOT EXISTS account_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_no TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'active',
    row_version INTEGER NOT NULL DEFAULT 0,
    reversed_entry_no TEXT,
    voided_at TEXT,
    voided_by TEXT,
    partner_id INTEGER NOT NULL,
    account_type TEXT NOT NULL,
    direction TEXT NOT NULL,
    amount REAL NOT NULL,
    source_type TEXT,
    source_no TEXT,
    note TEXT,
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY(partner_id) REFERENCES partners(id)
);

CREATE TABLE IF NOT EXISTS operation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    summary TEXT NOT NULL,
    detail TEXT,
    created_by TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bom_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    finished_item_id INTEGER NOT NULL,
    component_item_id INTEGER NOT NULL,
    quantity REAL NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(finished_item_id) REFERENCES items(id),
    FOREIGN KEY(component_item_id) REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS return_inbounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tracking_no TEXT NOT NULL UNIQUE,
    order_no TEXT,
    item_id INTEGER,
    raw_product_name TEXT,
    raw_sku TEXT,
    customer_name TEXT,
    quantity REAL NOT NULL DEFAULT 1,
    status TEXT NOT NULL,
    stock_movement_id INTEGER,
    raw_payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(item_id) REFERENCES items(id),
    FOREIGN KEY(stock_movement_id) REFERENCES stock_movements(id)
);

CREATE INDEX IF NOT EXISTS idx_items_type ON items(item_type);
CREATE INDEX IF NOT EXISTS idx_stock_item_warehouse ON stock_movements(item_id, warehouse_id);
CREATE INDEX IF NOT EXISTS idx_account_partner ON account_entries(partner_id);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type);
CREATE INDEX IF NOT EXISTS idx_sales_orders_status ON sales_orders(status);
CREATE INDEX IF NOT EXISTS idx_production_orders_item ON production_orders(finished_item_id);
CREATE INDEX IF NOT EXISTS idx_stock_locks_item ON stock_locks(item_id, warehouse_id, status);
CREATE INDEX IF NOT EXISTS idx_locations_warehouse ON locations(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_operation_logs_entity ON operation_logs(entity_type, entity_id, created_at);
"""


def ensure_directories(config: dict) -> None:
    Path(config["DATABASE_PATH"]).parent.mkdir(parents=True, exist_ok=True)
    Path(config["EXPORT_DIR"]).mkdir(parents=True, exist_ok=True)


def get_connection(database_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(database_path: str) -> None:
    with get_connection(database_path) as conn:
        conn.executescript(SCHEMA_SQL)
        _run_migrations(conn)
        conn.commit()


def _run_migrations(conn: sqlite3.Connection) -> None:
    migrations = {
        "users": {"role": "TEXT NOT NULL DEFAULT 'admin'"},
        "stock_movements": {
            "document_id": "INTEGER",
            "status": "TEXT NOT NULL DEFAULT 'active'",
            "row_version": "INTEGER NOT NULL DEFAULT 0",
            "reversed_movement_no": "TEXT",
            "voided_at": "TEXT",
            "voided_by": "TEXT",
            "updated_at": "TEXT",
        },
        "sales_orders": {
            "source_channel": "TEXT NOT NULL DEFAULT 'manual'",
            "row_version": "INTEGER NOT NULL DEFAULT 0",
            "reversed_order_no": "TEXT",
        },
        "items": {
            "default_location_id": "INTEGER",
            "platform_sku": "TEXT",
            "supplier_id": "INTEGER",
            "lead_days": "INTEGER NOT NULL DEFAULT 0",
            "is_producible": "INTEGER NOT NULL DEFAULT 0",
            "is_packaging": "INTEGER NOT NULL DEFAULT 0",
        },
        "documents": {
            "source_channel": "TEXT NOT NULL DEFAULT 'manual'",
            "row_version": "INTEGER NOT NULL DEFAULT 0",
            "reversed_from_id": "INTEGER",
            "reversed_document_no": "TEXT",
            "voided_at": "TEXT",
            "voided_by": "TEXT",
        },
        "account_entries": {
            "status": "TEXT NOT NULL DEFAULT 'active'",
            "row_version": "INTEGER NOT NULL DEFAULT 0",
            "reversed_entry_no": "TEXT",
            "voided_at": "TEXT",
            "voided_by": "TEXT",
            "updated_at": "TEXT",
        },
        "platform_settlements": {
            "status": "TEXT NOT NULL DEFAULT 'active'",
            "row_version": "INTEGER NOT NULL DEFAULT 0",
            "reversed_settlement_no": "TEXT",
            "voided_at": "TEXT",
            "voided_by": "TEXT",
            "updated_at": "TEXT",
        },
    }
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS operation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            summary TEXT NOT NULL,
            detail TEXT,
            created_by TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_operation_logs_entity ON operation_logs(entity_type, entity_id, created_at)")
    for table_name, columns in migrations.items():
        existing = {
            row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        for column_name, column_type in columns.items():
            if column_name not in existing:
                conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
