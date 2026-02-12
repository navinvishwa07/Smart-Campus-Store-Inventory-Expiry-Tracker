"""
Shared pytest fixtures for the Smart Campus Store test suite.
Uses an in-memory SQLite database so tests never touch production data.
"""
import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import date, timedelta

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import Base, get_db
from backend.main import app
from backend.models import Product, Batch, Transaction, Supplier, PurchaseOrder


# ─── In-memory test DB ───
TEST_DATABASE_URL = "sqlite:///./test_campus_store.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Yield a test DB session and roll back on teardown."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Create all tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    """Provide a raw DB session for unit tests."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """FastAPI TestClient wired to the test database."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ─── Data Factory Helpers ───

@pytest.fixture
def sample_product(db):
    """Insert and return a single sample product."""
    product = Product(
        item_id="TEST001",
        name="Test Milk 500ml",
        category="Dairy",
        fat_content="Low Fat",
        weight=500.0,
        mrp=45.0,
        barcode="9900000000001",
        min_stock=10,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@pytest.fixture
def sample_product_with_batches(db, sample_product):
    """Insert a product with multiple batches (fresh, warning, expired)."""
    today = date.today()
    batches = [
        Batch(
            product_id=sample_product.id,
            batch_number="B-TEST001-01",
            quantity=50,
            cost_price=30.0,
            manufacture_date=today - timedelta(days=30),
            expiry_date=today + timedelta(days=60),  # Fresh
        ),
        Batch(
            product_id=sample_product.id,
            batch_number="B-TEST001-02",
            quantity=20,
            cost_price=32.0,
            manufacture_date=today - timedelta(days=90),
            expiry_date=today + timedelta(days=10),  # Warning (≤15 days)
        ),
        Batch(
            product_id=sample_product.id,
            batch_number="B-TEST001-03",
            quantity=10,
            cost_price=28.0,
            manufacture_date=today - timedelta(days=120),
            expiry_date=today - timedelta(days=5),  # Expired
        ),
    ]
    db.add_all(batches)
    db.commit()
    for b in batches:
        db.refresh(b)
    return sample_product, batches


@pytest.fixture
def sample_supplier(db):
    """Insert and return a sample supplier."""
    supplier = Supplier(
        name="Test Dairy Supplier",
        category="Dairy",
        contact_email="dairy@test.com",
        phone="9876543210",
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@pytest.fixture
def multiple_products(db):
    """Insert multiple products across categories for analytics tests."""
    products = [
        Product(item_id="MP001", name="Cola 500ml", category="Soft Drinks", mrp=40.0, barcode="1100000000001", min_stock=20),
        Product(item_id="MP002", name="Chips 100g", category="Snack Foods", mrp=30.0, barcode="1100000000002", min_stock=15),
        Product(item_id="MP003", name="Curd 200g", category="Dairy", mrp=25.0, barcode="1100000000003", min_stock=10),
        Product(item_id="MP004", name="Shampoo 200ml", category="Health and Hygiene", mrp=120.0, barcode="1100000000004", min_stock=5),
    ]
    db.add_all(products)
    db.commit()
    for p in products:
        db.refresh(p)
    return products
