-- ============================================================
-- Smart Campus Store — Database Schema (SQLite)
-- Generated from: backend/models.py (SQLAlchemy ORM)
-- Database File: campus_store.db
-- Generated: 2026-02-12
-- ============================================================


-- ────────────────────────────────────────────────────────────
-- TABLE: products
-- Master product catalog. One entry per unique product.
-- ────────────────────────────────────────────────────────────
CREATE TABLE products (
    id              INTEGER       NOT NULL,
    item_id         VARCHAR(20)   NOT NULL,
    name            VARCHAR(200)  NOT NULL,
    category        VARCHAR(50)   NOT NULL,
    fat_content     VARCHAR(20)   DEFAULT 'Regular',
    weight          FLOAT         DEFAULT 0.0,
    mrp             FLOAT         NOT NULL,
    barcode         VARCHAR(50),
    min_stock       INTEGER       DEFAULT 10,
    image_url       VARCHAR(500),
    created_at      DATETIME      DEFAULT (CURRENT_TIMESTAMP),
    updated_at      DATETIME      DEFAULT (CURRENT_TIMESTAMP),

    PRIMARY KEY (id)
);

CREATE INDEX        ix_products_id      ON products (id);
CREATE UNIQUE INDEX ix_products_item_id ON products (item_id);
CREATE UNIQUE INDEX ix_products_barcode ON products (barcode);


-- ────────────────────────────────────────────────────────────
-- TABLE: batches
-- Batch-level inventory tracking. Each restock creates a new
-- batch with its own quantity, cost price, and expiry date.
-- Enables FIFO selling and per-batch expiry monitoring.
-- ────────────────────────────────────────────────────────────
CREATE TABLE batches (
    id                INTEGER       NOT NULL,
    product_id        INTEGER       NOT NULL,
    batch_number      VARCHAR(50)   NOT NULL,
    quantity          INTEGER       NOT NULL  DEFAULT 0,
    cost_price        FLOAT         DEFAULT 0.0,
    manufacture_date  DATE,
    expiry_date       DATE          NOT NULL,
    received_date     DATETIME      DEFAULT (CURRENT_TIMESTAMP),

    PRIMARY KEY (id),
    FOREIGN KEY (product_id) REFERENCES products (id)
);

CREATE INDEX ix_batches_id ON batches (id);


-- ────────────────────────────────────────────────────────────
-- TABLE: transactions
-- Records all inventory movements: sales, wastage, restocks.
-- Each transaction links to a product and optionally a batch.
-- ────────────────────────────────────────────────────────────
CREATE TABLE transactions (
    id                 INTEGER       NOT NULL,
    product_id         INTEGER       NOT NULL,
    batch_id           INTEGER,
    transaction_type   VARCHAR(20)   NOT NULL,   -- 'sale' | 'wastage' | 'restock'
    quantity           INTEGER       NOT NULL,
    unit_price         FLOAT         DEFAULT 0.0,
    total_amount       FLOAT         DEFAULT 0.0,
    transaction_date   DATETIME      DEFAULT (CURRENT_TIMESTAMP),
    notes              TEXT,

    PRIMARY KEY (id),
    FOREIGN KEY (product_id) REFERENCES products (id),
    FOREIGN KEY (batch_id)   REFERENCES batches (id)
);

CREATE INDEX ix_transactions_id ON transactions (id);


-- ────────────────────────────────────────────────────────────
-- TABLE: suppliers
-- Registered suppliers, one per product category.
-- Used by ML engine to auto-generate purchase orders.
-- ────────────────────────────────────────────────────────────
CREATE TABLE suppliers (
    id              INTEGER       NOT NULL,
    name            VARCHAR(100)  NOT NULL,
    category        VARCHAR(50)   NOT NULL,
    contact_email   VARCHAR(100),
    phone           VARCHAR(20),

    PRIMARY KEY (id),
    UNIQUE (category)
);

CREATE INDEX ix_suppliers_id ON suppliers (id);


-- ────────────────────────────────────────────────────────────
-- TABLE: purchase_orders
-- ML-generated purchase order drafts. Auto-created when
-- stock-out is predicted within 48 hours.
-- ────────────────────────────────────────────────────────────
CREATE TABLE purchase_orders (
    id                       INTEGER       NOT NULL,
    supplier_id              INTEGER       NOT NULL,
    product_id               INTEGER       NOT NULL,
    quantity                 INTEGER       NOT NULL  DEFAULT 50,
    status                   VARCHAR(20)   DEFAULT 'draft',   -- 'draft' | 'sent' | 'received'
    created_at               DATETIME      DEFAULT (CURRENT_TIMESTAMP),
    predicted_stockout_date  DATE,

    PRIMARY KEY (id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers (id),
    FOREIGN KEY (product_id)  REFERENCES products (id)
);

CREATE INDEX ix_purchase_orders_id ON purchase_orders (id);
