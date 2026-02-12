"""
Unit tests for SQLAlchemy ORM models.
Tests model creation, computed properties, and expiry status logic.
"""
import pytest
from datetime import date, timedelta
from backend.models import Product, Batch, Transaction, Supplier, PurchaseOrder


class TestProductModel:
    """Tests for the Product ORM model."""

    def test_create_product(self, db):
        """Product can be created with required fields."""
        product = Product(
            item_id="UNIT001",
            name="Unit Test Product",
            category="Dairy",
            mrp=50.0,
        )
        db.add(product)
        db.commit()
        db.refresh(product)

        assert product.id is not None
        assert product.item_id == "UNIT001"
        assert product.name == "Unit Test Product"
        assert product.category == "Dairy"
        assert product.mrp == 50.0

    def test_default_values(self, db):
        """Product defaults are applied correctly."""
        product = Product(item_id="UNIT002", name="Defaults", category="Dairy", mrp=10.0)
        db.add(product)
        db.commit()
        db.refresh(product)

        assert product.fat_content == "Regular"
        assert product.weight == 0.0
        assert product.min_stock == 10
        assert product.image_url is None
        assert product.barcode is None

    def test_total_stock_no_batches(self, db, sample_product):
        """Total stock is 0 when no batches exist."""
        assert sample_product.total_stock == 0

    def test_total_stock_with_batches(self, db, sample_product_with_batches):
        """Total stock sums only batches with quantity > 0."""
        product, batches = sample_product_with_batches
        # 50 + 20 + 10 = 80
        assert product.total_stock == 80

    def test_total_stock_excludes_zero_quantity(self, db):
        """Batches with 0 quantity are excluded from total_stock."""
        product = Product(item_id="UNIT003", name="Zero Qty", category="Dairy", mrp=10.0)
        db.add(product)
        db.commit()

        batch = Batch(
            product_id=product.id,
            batch_number="B-003-01",
            quantity=0,
            cost_price=5.0,
            expiry_date=date.today() + timedelta(days=30),
        )
        db.add(batch)
        db.commit()

        db.refresh(product)
        assert product.total_stock == 0

    def test_low_stock_detection(self, db, sample_product):
        """Product correctly reports low stock status."""
        assert sample_product.total_stock < sample_product.min_stock  # 0 < 10


class TestBatchModel:
    """Tests for the Batch ORM model and expiry status logic."""

    def test_create_batch(self, db, sample_product):
        """Batch can be created and linked to a product."""
        batch = Batch(
            product_id=sample_product.id,
            batch_number="B-001",
            quantity=100,
            cost_price=30.0,
            expiry_date=date.today() + timedelta(days=90),
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)

        assert batch.id is not None
        assert batch.product_id == sample_product.id
        assert batch.quantity == 100

    def test_expiry_status_fresh(self, db, sample_product):
        """Batch with > 15 days left is 'fresh'."""
        batch = Batch(
            product_id=sample_product.id,
            batch_number="B-FRESH",
            quantity=10,
            cost_price=5.0,
            expiry_date=date.today() + timedelta(days=30),
        )
        db.add(batch)
        db.commit()
        assert batch.expiry_status == "fresh"

    def test_expiry_status_warning(self, db, sample_product):
        """Batch with 8-15 days left is 'warning'."""
        batch = Batch(
            product_id=sample_product.id,
            batch_number="B-WARN",
            quantity=10,
            cost_price=5.0,
            expiry_date=date.today() + timedelta(days=12),
        )
        db.add(batch)
        db.commit()
        assert batch.expiry_status == "warning"

    def test_expiry_status_critical(self, db, sample_product):
        """Batch with 1-7 days left is 'critical'."""
        batch = Batch(
            product_id=sample_product.id,
            batch_number="B-CRIT",
            quantity=10,
            cost_price=5.0,
            expiry_date=date.today() + timedelta(days=3),
        )
        db.add(batch)
        db.commit()
        assert batch.expiry_status == "critical"

    def test_expiry_status_expired(self, db, sample_product):
        """Batch with 0 or negative days left is 'expired'."""
        batch = Batch(
            product_id=sample_product.id,
            batch_number="B-EXP",
            quantity=10,
            cost_price=5.0,
            expiry_date=date.today() - timedelta(days=1),
        )
        db.add(batch)
        db.commit()
        assert batch.expiry_status == "expired"

    def test_days_until_expiry(self, db, sample_product):
        """days_until_expiry returns correct number of days."""
        days_ahead = 45
        batch = Batch(
            product_id=sample_product.id,
            batch_number="B-DAYS",
            quantity=10,
            cost_price=5.0,
            expiry_date=date.today() + timedelta(days=days_ahead),
        )
        db.add(batch)
        db.commit()
        assert batch.days_until_expiry == days_ahead

    def test_days_until_expiry_negative(self, db, sample_product):
        """days_until_expiry is negative for expired batches."""
        batch = Batch(
            product_id=sample_product.id,
            batch_number="B-NEG",
            quantity=10,
            cost_price=5.0,
            expiry_date=date.today() - timedelta(days=10),
        )
        db.add(batch)
        db.commit()
        assert batch.days_until_expiry == -10


class TestTransactionModel:
    """Tests for the Transaction ORM model."""

    def test_create_sale_transaction(self, db, sample_product):
        """Sale transaction is created correctly."""
        tx = Transaction(
            product_id=sample_product.id,
            transaction_type="sale",
            quantity=5,
            unit_price=45.0,
            total_amount=225.0,
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)

        assert tx.id is not None
        assert tx.transaction_type == "sale"
        assert tx.total_amount == 225.0

    def test_create_wastage_transaction(self, db, sample_product):
        """Wastage transaction is created correctly."""
        tx = Transaction(
            product_id=sample_product.id,
            transaction_type="wastage",
            quantity=3,
            unit_price=45.0,
            total_amount=135.0,
            notes="Expired batch",
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)

        assert tx.transaction_type == "wastage"
        assert tx.notes == "Expired batch"

    def test_create_restock_transaction(self, db, sample_product):
        """Restock transaction is created correctly."""
        tx = Transaction(
            product_id=sample_product.id,
            transaction_type="restock",
            quantity=100,
            unit_price=30.0,
            total_amount=3000.0,
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)

        assert tx.transaction_type == "restock"
        assert tx.quantity == 100


class TestSupplierModel:
    """Tests for the Supplier ORM model."""

    def test_create_supplier(self, db):
        """Supplier can be created."""
        supplier = Supplier(
            name="Test Supplier",
            category="Dairy",
            contact_email="test@supplier.com",
            phone="1234567890",
        )
        db.add(supplier)
        db.commit()
        db.refresh(supplier)

        assert supplier.id is not None
        assert supplier.name == "Test Supplier"
        assert supplier.category == "Dairy"


class TestPurchaseOrderModel:
    """Tests for the PurchaseOrder ORM model."""

    def test_create_purchase_order(self, db, sample_product, sample_supplier):
        """Purchase order can be created and linked to supplier + product."""
        po = PurchaseOrder(
            supplier_id=sample_supplier.id,
            product_id=sample_product.id,
            quantity=100,
            status="draft",
            predicted_stockout_date=date.today() + timedelta(days=2),
        )
        db.add(po)
        db.commit()
        db.refresh(po)

        assert po.id is not None
        assert po.status == "draft"
        assert po.quantity == 100


class TestStockValueCalculation:
    """Tests for stock value computation logic."""

    def test_stock_value_single_batch(self, db, sample_product):
        """Stock value = quantity × cost_price for a single batch."""
        batch = Batch(
            product_id=sample_product.id,
            batch_number="B-VAL-01",
            quantity=100,
            cost_price=30.0,
            expiry_date=date.today() + timedelta(days=60),
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)

        stock_value = batch.quantity * batch.cost_price
        assert stock_value == 3000.0

    def test_stock_value_multiple_batches(self, db, sample_product_with_batches):
        """Total stock value sums across all batches with qty > 0."""
        product, batches = sample_product_with_batches

        total_value = sum(b.quantity * b.cost_price for b in batches if b.quantity > 0)
        # 50*30 + 20*32 + 10*28 = 1500 + 640 + 280 = 2420
        assert total_value == 2420.0
