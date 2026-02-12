"""
Smart Campus Store Inventory & Expiry Tracker — FastAPI Backend
Full REST API covering products, batches, transactions, analytics, and ML predictions.
"""
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, and_, case, literal
from datetime import date, datetime, timedelta
from typing import List, Optional
import os

from backend.database import get_db, init_db
from backend.models import Product, Batch, Transaction
from backend.schemas import (
    ProductCreate, ProductUpdate, ProductResponse,
    BatchCreate, BatchInfo,
    TransactionCreate, TransactionResponse,
    ExpiryAlert, StockAlert, DashboardStats,
    CategorySales, RevenueData, SeasonalPattern,
    SupplierCreate, SupplierResponse, PurchaseOrderResponse,
)
from backend.models import Product, Batch, Transaction, Supplier, PurchaseOrder
from backend.ml_engine import seasonal_analyzer

app = FastAPI(
    title="Smart Campus Store API",
    description="Inventory & Expiry Tracker for campus stores",
    version="1.0.0",
)

# CORS — allow frontend

# CORS — allow frontend
origins = os.getenv("CORS_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──── Startup ────
@app.on_event("startup")
def startup():
    init_db()
    # Train ML engine from CSV if available
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "medium_sales_dataset.csv")
    if os.path.exists(csv_path):
        seasonal_analyzer.train_from_csv(csv_path)
        print("✅ ML engine trained from CSV")
    # Try seeding database
    try:
        from backend.seed import seed_database
        seed_database()
        
        # Seed Suppliers if empty
        with next(get_db()) as db:
            if db.query(Supplier).count() == 0:
                print("Seeding suppliers for ML engine...")
                dummy_suppliers = [
                    Supplier(name="Fresh Farm Logistics", category="Fruits & Vegetables"),
                    Supplier(name="Daily Dairy Co.", category="Dairy"),
                    Supplier(name="Global Snacking Inc.", category="Snack Foods"),
                    Supplier(name="Frozen Fast Foods", category="Frozen Foods"),
                    Supplier(name="Generic Grocers Ltd.", category="Baking Goods"),
                    Supplier(name="Household Essentials", category="Household"),
                    Supplier(name="Beverage Distributors", category="Soft Drinks"),
                    Supplier(name="Canned Goods Supply", category="Canned"),
                    Supplier(name="HealthPlus Hygiene", category="Health and Hygiene"),
                ]
                db.add_all(dummy_suppliers)
                db.commit()
                print("✅ Suppliers seeded.")

    except Exception as e:
        print(f"Seed note: {e}")


# ──── Serve Frontend ────
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
def root():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Smart Campus Store API", "docs": "/docs"}


# ═══════════════════════════════════════════════════
# PRODUCTS
# ═══════════════════════════════════════════════════

@app.get("/api/products", response_model=List[ProductResponse])
def list_products(
    category: Optional[str] = None,
    search: Optional[str] = None,
    low_stock: bool = False,
    db: Session = Depends(get_db)
):
    """List all products with optional filters."""
    query = db.query(Product).options(joinedload(Product.batches))

    if category:
        query = query.filter(Product.category == category)
    if search:
        query = query.filter(
            (Product.name.ilike(f"%{search}%")) |
            (Product.item_id.ilike(f"%{search}%")) |
            (Product.barcode.ilike(f"%{search}%"))
        )

    products = query.order_by(Product.name).all()

    if low_stock:
        products = [p for p in products if p.total_stock < p.min_stock]

    return products


@app.get("/api/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).options(
        joinedload(Product.batches)
    ).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.post("/api/products", response_model=ProductResponse)
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    existing = db.query(Product).filter(Product.item_id == data.item_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Item ID already exists")
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@app.put("/api/products/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, data: ProductUpdate, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@app.delete("/api/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"message": "Product deleted"}


@app.get("/api/products/barcode/{barcode}", response_model=ProductResponse)
def get_by_barcode(barcode: str, db: Session = Depends(get_db)):
    """Look up product by barcode (for scanner)."""
    product = db.query(Product).options(
        joinedload(Product.batches)
    ).filter(Product.barcode == barcode).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found for barcode")
    return product


@app.get("/api/products/{product_id}/pulse")
def get_pulse_discount(product_id: int, db: Session = Depends(get_db)):
    """
    Pulse Engine: Check if a product has near-expiry batches.
    If any batch expires within 7 days → 20% automatic discount.
    """
    from datetime import date as dt_date
    product = db.query(Product).options(
        joinedload(Product.batches)
    ).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    today = dt_date.today()
    near_expiry_batches = []
    for b in product.batches:
        if b.quantity > 0:
            days_left = (b.expiry_date - today).days
            if 0 < days_left < 7:
                near_expiry_batches.append({
                    "batch_id": b.id,
                    "batch_number": b.batch_number,
                    "days_left": days_left,
                    "quantity": b.quantity,
                    "expiry_date": str(b.expiry_date),
                })

    has_discount = len(near_expiry_batches) > 0
    discount_pct = 20 if has_discount else 0
    original_price = product.mrp
    discounted_price = round(original_price * (1 - discount_pct / 100), 2) if has_discount else original_price

    return {
        "product_id": product.id,
        "product_name": product.name,
        "original_price": original_price,
        "has_discount": has_discount,
        "discount_pct": discount_pct,
        "discounted_price": discounted_price,
        "near_expiry_batches": near_expiry_batches,
        "reason": f"Flash Sale — {len(near_expiry_batches)} batch(es) expiring within 7 days" if has_discount else None,
    }


# ═══════════════════════════════════════════════════
# BATCHES
# ═══════════════════════════════════════════════════

@app.post("/api/batches", response_model=BatchInfo)
def create_batch(data: BatchCreate, db: Session = Depends(get_db)):
    """Add a new inventory batch (restock)."""
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    batch_count = db.query(Batch).filter(Batch.product_id == data.product_id).count()
    batch = Batch(
        product_id=data.product_id,
        batch_number=f"B{product.item_id}-{batch_count+1:02d}",
        quantity=data.quantity,
        cost_price=data.cost_price,
        manufacture_date=data.manufacture_date,
        expiry_date=data.expiry_date,
    )
    db.add(batch)

    # Also record as restock transaction
    tx = Transaction(
        product_id=data.product_id,
        batch_id=None,
        transaction_type="restock",
        quantity=data.quantity,
        unit_price=data.cost_price,
        total_amount=round(data.quantity * data.cost_price, 2),
    )
    db.add(tx)
    db.commit()
    db.refresh(batch)
    return batch


@app.get("/api/batches/expiring", response_model=List[ExpiryAlert])
def get_expiring_batches(days: int = 365, db: Session = Depends(get_db)):
    """Get list of batches expiring within N days."""
    cutoff = date.today() + timedelta(days=days)
    batches = db.query(Batch).options(
        joinedload(Batch.product)
    ).filter(
        Batch.expiry_date <= cutoff,
        Batch.quantity > 0
    ).order_by(Batch.expiry_date).all()
    
    alerts = []
    today = date.today()
    
    for b in batches:
        days_left = (b.expiry_date - today).days
        if days_left <= 0:
            status = "expired"
        elif days_left < 7:
            status = "critical"
        elif days_left <= 15:
            status = "warning"
        else:
            status = "good"
            
        alerts.append(ExpiryAlert(
            product_id=b.product.id,
            product_name=b.product.name,
            item_id=b.product.item_id,
            batch_id=b.id,
            batch_number=b.batch_number,
            expiry_date=b.expiry_date,
            days_left=days_left,
            quantity=b.quantity,
            status=status,
        ))
    return alerts


@app.get("/api/cron/daily-check")
def daily_cron_check(db: Session = Depends(get_db)):
    """Daily Cron Job: Check expiry dates & generate mobile alerts."""
    batches = db.query(Batch).filter(Batch.quantity > 0).options(joinedload(Batch.product)).all()
    alerts = []
    today = date.today()
    
    for b in batches:
        days = (b.expiry_date - today).days
        status = "good"
        if days <= 0: status = "expired"
        elif days < 7: status = "critical" # Red
        elif days <= 15: status = "warning" # Yellow
        
        # Only include non-good (Red/Yellow) in the push list?
        # User says "These alerts will push". implying active alerts.
        if status != "good":
            alerts.append({
                "product_name": b.product.name,
                "batch_number": b.batch_number,
                "expiry_date": str(b.expiry_date),
                "days_left": days,
                "status": status,
                "health_score": "Red" if status in ["expired", "critical"] else "Yellow"
            })
            
    return {
        "check_date": str(today),
        "total_batches_checked": len(batches),
        "alerts_generated": len(alerts),
        "mobile_sync_data": alerts
    }

@app.get("/api/batches/expiring", response_model=List[ExpiryAlert])
def get_expiring_batches(
    days: int = Query(default=60, ge=0),
    db: Session = Depends(get_db)
):
    """Get batches expiring within N days."""
    cutoff = date.today() + timedelta(days=days)
    batches = db.query(Batch).options(
        joinedload(Batch.product)
    ).filter(
        Batch.expiry_date <= cutoff,
        Batch.quantity > 0
    ).order_by(Batch.expiry_date).all()

    alerts = []
    for b in batches:
        days_left = (b.expiry_date - date.today()).days
        if days_left <= 0:
            status = "expired"
        elif days_left < 7:
            status = "critical"
        elif days_left <= 15:
            status = "warning"
        else:
            status = "good"

        alerts.append(ExpiryAlert(
            product_name=b.product.name,
            item_id=b.product.item_id,
            batch_id=b.id,
            batch_number=b.batch_number,
            expiry_date=b.expiry_date,
            days_left=days_left,
            quantity=b.quantity,
            status=status,
        ))
    return alerts


# ═══════════════════════════════════════════════════
# SUPPLIER MANAGEMENT & POs
# ═══════════════════════════════════════════════════

@app.get("/api/suppliers", response_model=List[SupplierResponse])
def list_suppliers(db: Session = Depends(get_db)):
    """List all registered suppliers."""
    return db.query(Supplier).all()

@app.post("/api/suppliers", response_model=SupplierResponse)
def create_supplier(data: SupplierCreate, db: Session = Depends(get_db)):
    supplier = Supplier(**data.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier

@app.get("/api/purchase-orders", response_model=List[PurchaseOrderResponse])
def list_purchase_orders(status: str = "draft", db: Session = Depends(get_db)):
    """List PO drafts generated by the ML engine."""
    pos = db.query(PurchaseOrder).options(
        joinedload(PurchaseOrder.supplier),
        joinedload(PurchaseOrder.product)
    ).filter(PurchaseOrder.status == status).order_by(desc(PurchaseOrder.created_at)).all()
    
    # Enrich response manually if needed, or rely on ORM
    results = []
    for po in pos:
        po_dict = po.__dict__.copy()
        if po.supplier: po_dict["supplier_name"] = po.supplier.name
        if po.product: po_dict["product_name"] = po.product.name
        results.append(po_dict)
    return results


# ═══════════════════════════════════════════════════
# TRANSACTIONS (POS)
# ═══════════════════════════════════════════════════

@app.post("/api/transactions", response_model=TransactionResponse)
def create_transaction(data: TransactionCreate, db: Session = Depends(get_db)):
    """Record a sale, wastage, or restock with Real-Time ML Stock Prediction."""
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # For sales — deduct from oldest batch (FIFO)
    if data.transaction_type == "sale":
        remaining = data.quantity
        batches = db.query(Batch).filter(
            Batch.product_id == data.product_id,
            Batch.quantity > 0
        ).order_by(Batch.expiry_date).all()

        for batch in batches:
            if remaining <= 0:
                break
            deduct = min(batch.quantity, remaining)
            batch.quantity -= deduct
            remaining -= deduct

        if remaining > 0:
            raise HTTPException(status_code=400, detail="Insufficient stock")

    elif data.transaction_type == "wastage":
        if data.batch_id:
            batch = db.query(Batch).filter(Batch.id == data.batch_id).first()
            if batch:
                batch.quantity = max(0, batch.quantity - data.quantity)
    
    # Create Transaction Record
    tx = Transaction(
        product_id=data.product_id,
        batch_id=data.batch_id,
        transaction_type=data.transaction_type,
        quantity=data.quantity,
        unit_price=data.unit_price or product.mrp,
        total_amount=round(data.quantity * (data.unit_price or product.mrp), 2),
        notes=data.notes,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    # ─── REAL-TIME ML TRIGGER: Stock-Out Prediction & Auto-PO ───
    if data.transaction_type == "sale":
        try:
            # 1. Calculate Average Daily Sales (Last 30 Days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_sales_qty = db.query(func.sum(Transaction.quantity)).filter(
                Transaction.product_id == data.product_id,
                Transaction.transaction_type == "sale",
                Transaction.transaction_date >= thirty_days_ago
            ).scalar() or 0
            
            # Simple moving average (smoothing factor)
            avg_daily_sales = recent_sales_qty / 30.0
            
            # 2. Predict Stock-Out Date
            current_stock = product.total_stock
            if avg_daily_sales > 0.1: # Threshold to avoid division by near-zero
                days_until_stockout = current_stock / avg_daily_sales
                
                # 3. Determine if critical (< 48 hours / 2 days)
                if days_until_stockout <= 2.0:
                    # Check if active PO exists
                    existing_po = db.query(PurchaseOrder).filter(
                        PurchaseOrder.product_id == data.product_id,
                        PurchaseOrder.status.in_(["draft", "sent"])
                    ).first()
                    
                    if not existing_po:
                        # Find Supplier for this category
                        supplier = db.query(Supplier).filter(Supplier.category == product.category).first()
                        if supplier:
                            # Auto-calculate order quantity (e.g., 7 days of stock)
                            order_qty = max(20, int(avg_daily_sales * 7)) # Min 20 units
                            predicted_date = date.today() + timedelta(days=int(days_until_stockout))

                            po = PurchaseOrder(
                                supplier_id=supplier.id,
                                product_id=product.id,
                                quantity=order_qty,
                                status="draft",
                                predicted_stockout_date=predicted_date
                            )
                            db.add(po)
                            db.commit()
                            print(f"🤖 ML Alert: Generated PO Draft for {product.name} (Stock out in {days_until_stockout:.1f} days)")
        except Exception as e:
            print(f"ML Trigger Error: {e}")

    return tx


@app.get("/api/transactions", response_model=List[TransactionResponse])
def list_transactions(
    transaction_type: Optional[str] = None,
    product_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(Transaction)
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)
    if product_id:
        query = query.filter(Transaction.product_id == product_id)
    return query.order_by(desc(Transaction.transaction_date)).limit(limit).all()


# ═══════════════════════════════════════════════════
# ANALYTICS & DASHBOARD
# ═══════════════════════════════════════════════════

@app.get("/api/dashboard", response_model=DashboardStats)
def get_dashboard(db: Session = Depends(get_db)):
    """Main dashboard overview with all key metrics."""
    products = db.query(Product).options(joinedload(Product.batches)).all()

    total_products = len(products)

    # Stock value from individual batch cost prices (accurate inventory valuation)
    total_stock_value = 0.0
    for p in products:
        for b in p.batches:
            if b.quantity > 0:
                total_stock_value += b.quantity * b.cost_price

    # Revenue from sales
    total_revenue = db.query(func.coalesce(func.sum(Transaction.total_amount), 0)).filter(
        Transaction.transaction_type == "sale"
    ).scalar()

    # Wastage loss
    total_wastage = db.query(func.coalesce(func.sum(Transaction.total_amount), 0)).filter(
        Transaction.transaction_type == "wastage"
    ).scalar()

    # ALL active batches (qty > 0) — same scope as Expiry Monitor (365 days)
    expiry_cutoff = date.today() + timedelta(days=365)
    all_batches = db.query(Batch).options(
        joinedload(Batch.product)
    ).filter(
        Batch.expiry_date <= expiry_cutoff,
        Batch.quantity > 0
    ).order_by(Batch.expiry_date).all()

    total_batches = len(all_batches)

    expiry_alerts = []
    expiring_soon_count = 0
    for b in all_batches:
        days_left = (b.expiry_date - date.today()).days
        if days_left <= 0:
            status = "expired"
        elif days_left < 7:
            status = "critical"
        elif days_left <= 15:
            status = "warning"
        else:
            status = "good"

        # Count at-risk batches (expired + critical + warning)
        if status != "good":
            expiring_soon_count += 1

        expiry_alerts.append(ExpiryAlert(
            product_id=b.product.id,
            product_name=b.product.name,
            item_id=b.product.item_id,
            batch_id=b.id,
            batch_number=b.batch_number,
            expiry_date=b.expiry_date,
            days_left=days_left,
            quantity=b.quantity,
            status=status,
        ))

    # Low stock alerts
    stock_alerts = []
    for p in products:
        if p.total_stock < p.min_stock:
            stock_alerts.append(StockAlert(
                product_id=p.id,
                product_name=p.name,
                item_id=p.item_id,
                current_stock=p.total_stock,
                min_stock=p.min_stock,
                category=p.category,
            ))

    # Category sales
    cat_sales_raw = db.query(
        Product.category,
        func.coalesce(func.sum(Transaction.total_amount), 0),
        func.coalesce(func.sum(Transaction.quantity), 0),
    ).join(Transaction, Transaction.product_id == Product.id).filter(
        Transaction.transaction_type == "sale"
    ).group_by(Product.category).all()

    category_sales = [
        CategorySales(category=c, total_sales=round(s, 2), total_quantity=int(q))
        for c, s, q in cat_sales_raw
    ]

    # Recent transactions
    recent = db.query(Transaction).order_by(
        desc(Transaction.transaction_date)
    ).limit(10).all()

    return DashboardStats(
        total_products=total_products,
        total_batches=total_batches,
        total_stock_value=round(total_stock_value, 2),
        total_revenue=round(float(total_revenue), 2),
        total_wastage_loss=round(float(total_wastage), 2),
        expiring_soon=expiring_soon_count,
        low_stock_count=len(stock_alerts),
        expiry_alerts=expiry_alerts,
        stock_alerts=stock_alerts,
        category_sales=category_sales,
        recent_transactions=recent,
    )


@app.get("/api/dashboard/kpi")
def get_dashboard_kpi(db: Session = Depends(get_db)):
    """Lightweight KPI-only endpoint for real-time polling (no heavy lists)."""
    products = db.query(Product).options(joinedload(Product.batches)).all()

    total_products = len(products)

    # Stock value from batch-level cost prices
    total_stock_value = 0.0
    total_batches = 0
    for p in products:
        for b in p.batches:
            if b.quantity > 0:
                total_stock_value += b.quantity * b.cost_price
                total_batches += 1

    total_revenue = db.query(func.coalesce(func.sum(Transaction.total_amount), 0)).filter(
        Transaction.transaction_type == "sale"
    ).scalar()

    total_wastage = db.query(func.coalesce(func.sum(Transaction.total_amount), 0)).filter(
        Transaction.transaction_type == "wastage"
    ).scalar()

    # Count at-risk batches
    expiry_cutoff = date.today() + timedelta(days=15)
    at_risk = db.query(func.count(Batch.id)).filter(
        Batch.expiry_date <= expiry_cutoff,
        Batch.quantity > 0
    ).scalar()

    low_stock = sum(1 for p in products if p.total_stock < p.min_stock)

    return {
        "total_products": total_products,
        "total_batches": total_batches,
        "total_stock_value": round(total_stock_value, 2),
        "total_revenue": round(float(total_revenue), 2),
        "total_wastage_loss": round(float(total_wastage), 2),
        "expiring_soon": at_risk,
        "low_stock_count": low_stock,
    }


@app.get("/api/analytics/revenue")
def revenue_analytics(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Daily revenue over the last N days."""
    from sqlalchemy import String, cast
    start_date = datetime.now() - timedelta(days=days)

    # Database-agnostic date grouping (works on both SQLite + PostgreSQL)
    day_expr = func.substr(cast(Transaction.transaction_date, String), 1, 10)

    sales = db.query(
        day_expr.label("day"),
        func.sum(Transaction.total_amount).label("total"),
    ).filter(
        Transaction.transaction_date >= start_date,
        Transaction.transaction_type == "sale"
    ).group_by(day_expr).all()

    wastages = db.query(
        day_expr.label("day"),
        func.sum(Transaction.total_amount).label("total"),
    ).filter(
        Transaction.transaction_date >= start_date,
        Transaction.transaction_type == "wastage"
    ).group_by(day_expr).all()

    # Combine results
    revenue_map = {r.day: float(r.total or 0) for r in sales}
    wastage_map = {w.day: float(w.total or 0) for w in wastages}
    all_days = sorted(set(list(revenue_map.keys()) + list(wastage_map.keys())))

    return [
        {
            "date": day,
            "revenue": round(revenue_map.get(day, 0), 2),
            "wastage": round(wastage_map.get(day, 0), 2),
            "net": round(revenue_map.get(day, 0) - wastage_map.get(day, 0), 2),
        }
        for day in all_days
    ]


@app.get("/api/analytics/wastage")
def wastage_report(db: Session = Depends(get_db)):
    """Wastage report by category."""
    results = db.query(
        Product.category,
        func.count(Transaction.id).label("incidents"),
        func.sum(Transaction.quantity).label("total_qty"),
        func.sum(Transaction.total_amount).label("total_loss"),
    ).join(Transaction, Transaction.product_id == Product.id).filter(
        Transaction.transaction_type == "wastage"
    ).group_by(Product.category).all()

    return [
        {
            "category": r.category,
            "incidents": r.incidents,
            "total_quantity": int(r.total_qty or 0),
            "total_loss": round(float(r.total_loss or 0), 2),
        }
        for r in results
    ]


@app.get("/api/analytics/categories")
def category_breakdown(db: Session = Depends(get_db)):
    """Category-wise stock and sales breakdown."""
    products = db.query(Product).options(joinedload(Product.batches)).all()

    categories = {}
    for p in products:
        cat = p.category
        if cat not in categories:
            categories[cat] = {"count": 0, "stock": 0, "value": 0}
        categories[cat]["count"] += 1
        categories[cat]["stock"] += p.total_stock
        categories[cat]["value"] += p.total_stock * p.mrp

    return [
        {
            "category": cat,
            "product_count": data["count"],
            "total_stock": data["stock"],
            "stock_value": round(data["value"], 2),
        }
        for cat, data in categories.items()
    ]


# ═══════════════════════════════════════════════════
# ML — SEASONAL PATTERNS
# ═══════════════════════════════════════════════════

@app.get("/api/ml/seasonal", response_model=List[SeasonalPattern])
def get_seasonal_predictions(
    category: Optional[str] = None,
    month: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get ML-predicted seasonal demand patterns."""
    # Get all categories from DB if not provided
    if category:
        target_cats = [category]
    else:
        cats = db.query(Product.category).distinct().all()
        target_cats = [c[0] for c in cats]

    target_months = [month] if month else range(1, 13)
    
    predictions = []
    for cat in target_cats:
        for m in target_months:
            # seasonal_analyzer now has heuristic fallback if not trained
            pred = seasonal_analyzer.predict_demand(cat, m)
            predictions.append(pred)

    return predictions


@app.get("/api/ml/insights")
def get_ml_insights():
    """Get ML-derived category insights (peak/low months, volatility)."""
    if not seasonal_analyzer.is_trained:
        return []
    return seasonal_analyzer.get_category_insights()


@app.get("/api/categories")
def list_categories(db: Session = Depends(get_db)):
    """List all unique categories."""
    cats = db.query(Product.category).distinct().all()
    return [c[0] for c in cats]
