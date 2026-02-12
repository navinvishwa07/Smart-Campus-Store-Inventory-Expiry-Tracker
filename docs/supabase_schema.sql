-- ============================================================
-- Smart Campus Store — Supabase PostgreSQL Schema
-- Run this in: Supabase → SQL Editor → New Query → Run
-- 
-- NOTE: The backend uses SQLAlchemy's `create_all()` which
-- auto-creates tables on first startup. This SQL is provided
-- as a reference and for manual setup if needed.
-- ============================================================

-- ────────────────────────────────────────────────────────────
-- TABLE: products
-- Master product catalog. One entry per unique product.
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS products (
    id              SERIAL        PRIMARY KEY,
    item_id         VARCHAR(20)   NOT NULL UNIQUE,
    name            VARCHAR(200)  NOT NULL,
    category        VARCHAR(50)   NOT NULL,
    fat_content     VARCHAR(20)   DEFAULT 'Regular',
    weight          DOUBLE PRECISION DEFAULT 0.0,
    mrp             DOUBLE PRECISION NOT NULL,
    barcode         VARCHAR(50)   UNIQUE,
    min_stock       INTEGER       DEFAULT 10,
    image_url       VARCHAR(500),
    created_at      TIMESTAMPTZ   DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_products_item_id  ON products (item_id);
CREATE INDEX IF NOT EXISTS ix_products_barcode  ON products (barcode);
CREATE INDEX IF NOT EXISTS ix_products_category ON products (category);


-- ────────────────────────────────────────────────────────────
-- TABLE: batches
-- Batch-level inventory tracking. Each restock creates a new
-- batch with its own quantity, cost price, and expiry date.
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS batches (
    id                SERIAL        PRIMARY KEY,
    product_id        INTEGER       NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    batch_number      VARCHAR(50)   NOT NULL,
    quantity          INTEGER       NOT NULL DEFAULT 0,
    cost_price        DOUBLE PRECISION DEFAULT 0.0,
    manufacture_date  DATE,
    expiry_date       DATE          NOT NULL,
    received_date     TIMESTAMPTZ   DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_batches_product_id  ON batches (product_id);
CREATE INDEX IF NOT EXISTS ix_batches_expiry_date ON batches (expiry_date);


-- ────────────────────────────────────────────────────────────
-- TABLE: transactions
-- Records all inventory movements: sales, wastage, restocks.
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS transactions (
    id                 SERIAL        PRIMARY KEY,
    product_id         INTEGER       NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    batch_id           INTEGER       REFERENCES batches(id),
    transaction_type   VARCHAR(20)   NOT NULL,
    quantity           INTEGER       NOT NULL,
    unit_price         DOUBLE PRECISION DEFAULT 0.0,
    total_amount       DOUBLE PRECISION DEFAULT 0.0,
    transaction_date   TIMESTAMPTZ   DEFAULT NOW(),
    notes              TEXT
);

CREATE INDEX IF NOT EXISTS ix_transactions_product_id ON transactions (product_id);
CREATE INDEX IF NOT EXISTS ix_transactions_type       ON transactions (transaction_type);
CREATE INDEX IF NOT EXISTS ix_transactions_date       ON transactions (transaction_date);


-- ────────────────────────────────────────────────────────────
-- TABLE: suppliers
-- Registered suppliers, one per product category.
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS suppliers (
    id              SERIAL        PRIMARY KEY,
    name            VARCHAR(100)  NOT NULL,
    category        VARCHAR(50)   NOT NULL UNIQUE,
    contact_email   VARCHAR(100),
    phone           VARCHAR(20)
);


-- ────────────────────────────────────────────────────────────
-- TABLE: purchase_orders
-- ML-generated purchase order drafts.
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS purchase_orders (
    id                       SERIAL        PRIMARY KEY,
    supplier_id              INTEGER       NOT NULL REFERENCES suppliers(id),
    product_id               INTEGER       NOT NULL REFERENCES products(id),
    quantity                 INTEGER       NOT NULL DEFAULT 50,
    status                   VARCHAR(20)   DEFAULT 'draft',
    created_at               TIMESTAMPTZ   DEFAULT NOW(),
    predicted_stockout_date  DATE
);

CREATE INDEX IF NOT EXISTS ix_purchase_orders_status ON purchase_orders (status);


-- ────────────────────────────────────────────────────────────
-- OPTIONAL: Enable Row Level Security (RLS)
-- Uncomment if you want Supabase-level access control
-- ────────────────────────────────────────────────────────────
-- ALTER TABLE products        ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE batches         ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE transactions    ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE suppliers       ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE purchase_orders ENABLE ROW LEVEL SECURITY;


-- ────────────────────────────────────────────────────────────
-- FUNCTION: Auto-update updated_at timestamp
-- ────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
