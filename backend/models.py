"""
SQLAlchemy ORM models for the Smart Campus Store.
Supports batch-level inventory tracking with expiry dates.
"""
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date,
    ForeignKey, Enum as SQLEnum, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base
import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    STAFF = "staff"


class User(Base):
    """Application users with role-based access."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default="staff")
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())


class ItemCategory(str, enum.Enum):
    SOFT_DRINKS = "Soft Drinks"
    CANNED = "Canned"
    DAIRY = "Dairy"
    BAKING_GOODS = "Baking Goods"
    FROZEN_FOODS = "Frozen Foods"
    FRUITS_VEGETABLES = "Fruits & Vegetables"
    SNACK_FOODS = "Snack Foods"
    HOUSEHOLD = "Household"
    HEALTH_HYGIENE = "Health and Hygiene"


class TransactionType(str, enum.Enum):
    SALE = "sale"
    WASTAGE = "wastage"
    RESTOCK = "restock"


class Product(Base):
    """Master product catalog — one entry per unique product."""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False)
    fat_content = Column(String(20), default="Regular")
    weight = Column(Float, default=0.0)
    mrp = Column(Float, nullable=False)
    barcode = Column(String(50), unique=True, nullable=True, index=True)
    min_stock = Column(Integer, default=10)
    image_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    batches = relationship("Batch", back_populates="product", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="product", cascade="all, delete-orphan")

    @property
    def total_stock(self):
        return sum(b.quantity for b in self.batches if b.quantity > 0)


class Batch(Base):
    """
    Batch-level inventory — each purchase/restock creates a new batch.
    Enables per-batch expiry tracking and FIFO selling.
    """
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    batch_number = Column(String(50), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    cost_price = Column(Float, default=0.0)
    manufacture_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=False)
    received_date = Column(DateTime, server_default=func.now())

    product = relationship("Product", back_populates="batches")

    @property
    def expiry_status(self):
        """🔴 expired/≤7 days, 🟡 ≤15 days, 🟢 fresh"""
        from datetime import date
        days_left = (self.expiry_date - date.today()).days
        if days_left <= 0:
            return "expired"
        elif days_left <= 7:
            return "critical"
        elif days_left <= 15:
            return "warning"
        else:
            return "fresh"

    @property
    def days_until_expiry(self):
        from datetime import date
        return (self.expiry_date - date.today()).days


class Transaction(Base):
    """Sales, wastage, and restock records."""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)
    transaction_type = Column(String(20), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    transaction_date = Column(DateTime, server_default=func.now())
    notes = Column(Text, nullable=True)

    product = relationship("Product", back_populates="transactions")
    batch = relationship("Batch")


class Supplier(Base):
    """Suppliers assigned to specific categories."""
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False, unique=True)  # One primary supplier per category for simplicity
    contact_email = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)


class PurchaseOrder(Base):
    """Auto-generated PO drafts when stock is low."""
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=50)
    status = Column(String(20), default="draft")  # draft, sent, received
    created_at = Column(DateTime, server_default=func.now())
    predicted_stockout_date = Column(Date, nullable=True)

    supplier = relationship("Supplier")
    product = relationship("Product")
