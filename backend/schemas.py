"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime


# ─── Product Schemas ───
class ProductBase(BaseModel):
    name: str
    category: str
    fat_content: str = "Regular"
    weight: float = 0.0
    mrp: float
    barcode: Optional[str] = None
    min_stock: int = 10
    image_url: Optional[str] = None


class ProductCreate(ProductBase):
    item_id: str


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    mrp: Optional[float] = None
    min_stock: Optional[int] = None
    barcode: Optional[str] = None


class BatchInfo(BaseModel):
    id: int
    batch_number: str
    quantity: int
    cost_price: float
    expiry_date: date
    manufacture_date: Optional[date] = None
    expiry_status: str
    days_until_expiry: int

    class Config:
        from_attributes = True


class ProductResponse(ProductBase):
    id: int
    item_id: str
    total_stock: int
    batches: List[BatchInfo] = []
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Batch Schemas ───
class BatchCreate(BaseModel):
    product_id: int
    quantity: int
    cost_price: float = 0.0
    manufacture_date: Optional[date] = None
    expiry_date: date


# ─── Transaction Schemas ───
class TransactionCreate(BaseModel):
    product_id: int
    batch_id: Optional[int] = None
    transaction_type: str  # sale, wastage, restock
    quantity: int
    unit_price: float = 0.0
    notes: Optional[str] = None


class TransactionResponse(BaseModel):
    id: int
    product_id: int
    batch_id: Optional[int] = None
    transaction_type: str
    quantity: int
    unit_price: float
    total_amount: float
    transaction_date: datetime
    notes: Optional[str] = None

    class Config:
        from_attributes = True


# ─── Analytics Schemas ───
class ExpiryAlert(BaseModel):
    product_id: int
    product_name: str
    item_id: str
    batch_id: int
    batch_number: str
    expiry_date: date
    days_left: int
    quantity: int
    status: str  # expired, critical, warning, fresh


class StockAlert(BaseModel):
    product_id: int
    product_name: str
    item_id: str
    current_stock: int
    min_stock: int
    category: str


class RevenueData(BaseModel):
    date: str
    revenue: float
    cost: float
    profit: float


class CategorySales(BaseModel):
    category: str
    total_sales: float
    total_quantity: int


class DashboardStats(BaseModel):
    total_products: int
    total_batches: int
    total_stock_value: float
    total_revenue: float
    total_wastage_loss: float
    expiring_soon: int
    low_stock_count: int
    expiry_alerts: List[ExpiryAlert] = []
    stock_alerts: List[StockAlert] = []
    category_sales: List[CategorySales] = []
    recent_transactions: List[TransactionResponse] = []


class SeasonalPattern(BaseModel):
    category: str
    month: int
    month_name: str
    predicted_demand: float
    confidence: float


# ─── New Models: Supplier & PO ───

class SupplierCreate(BaseModel):
    name: str
    category: str
    contact_email: Optional[str] = None
    phone: Optional[str] = None

class SupplierResponse(SupplierCreate):
    id: int
    class Config:
        from_attributes = True

class PurchaseOrderResponse(BaseModel):
    id: int
    supplier_id: int
    product_id: int
    quantity: int
    status: str
    created_at: datetime
    predicted_stockout_date: Optional[date] = None
    supplier_name: Optional[str] = None
    product_name: Optional[str] = None

    class Config:
        from_attributes = True
