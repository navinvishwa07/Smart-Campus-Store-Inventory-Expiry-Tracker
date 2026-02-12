"""
Integration tests for FastAPI endpoints.
Tests complete workflows: Inventory management, Transactions, and Reporting.
"""
from datetime import date, timedelta

def test_root_endpoint(client):
    """Root endpoint should return index.html or welcome message."""
    response = client.get("/")
    assert response.status_code == 200


# ─── Product Workflow Tests ───

def test_create_product_api(client):
    """Test creating a new product via API."""
    data = {
        "item_id": "API001",
        "name": "API Test Product",
        "category": "Snack Foods",
        "mrp": 20.0,
        "barcode": "8880000000001",
        "min_stock": 5
    }
    response = client.post("/api/products", json=data)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["item_id"] == "API001"
    assert res_data["name"] == "API Test Product"
    assert res_data["id"] is not None

def test_create_duplicate_product_api(client, sample_product):
    """Duplicate item_id should fail."""
    data = {
        "item_id": sample_product.item_id,  # TEST001
        "name": "Duplicate",
        "category": "Dairy",
        "mrp": 50.0
    }
    response = client.post("/api/products", json=data)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

def test_get_product_list(client, sample_product):
    """List products endpoint."""
    response = client.get("/api/products")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["item_id"] == sample_product.item_id

def test_get_product_by_barcode(client, sample_product):
    """Get product by barcode scanner lookup."""
    response = client.get(f"/api/products/barcode/{sample_product.barcode}")
    assert response.status_code == 200
    assert response.json()["name"] == sample_product.name

def test_update_product_api(client, sample_product):
    """Update product details."""
    update_data = {"mrp": 55.0}
    response = client.put(f"/api/products/{sample_product.id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["mrp"] == 55.0

def test_delete_product_api(client, sample_product):
    """Delete product."""
    response = client.delete(f"/api/products/{sample_product.id}")
    assert response.status_code == 200
    
    # Verify deletion
    check = client.get(f"/api/products/{sample_product.id}")
    assert check.status_code == 404


# ─── Inventory Workflow (Stock Logic) ───

def test_restock_workflow(client, sample_product):
    """Test adding a batch (restock) via API."""
    batch_data = {
        "product_id": sample_product.id,
        "quantity": 50,
        "cost_price": 35.0,
        "expiry_date": str(date.today() + timedelta(days=100))
    }
    response = client.post("/api/batches", json=batch_data)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["quantity"] == 50
    assert res_data["batch_number"].startswith(f"B{sample_product.item_id}")

    # Verify stock updated in product list
    prod_res = client.get(f"/api/products/{sample_product.id}")
    assert prod_res.json()["total_stock"] == 50

def test_transaction_sale_logic(client, sample_product):
    """
    Test Sale Transaction:
    1. Add batch (Qty 50)
    2. Sell 10
    3. Verify stock is 40
    """
    # 1. Restock
    client.post("/api/batches", json={
        "product_id": sample_product.id,
        "quantity": 50,
        "cost_price": 20.0,
        "expiry_date": str(date.today() + timedelta(days=60))
    })

    # 2. Sell
    sale_data = {
        "product_id": sample_product.id,
        "transaction_type": "sale",
        "quantity": 10,
        "unit_price": 45.0
    }
    res = client.post("/api/transactions", json=sale_data)
    assert res.status_code == 200
    
    # 3. Verify Remaining Stock
    prod_res = client.get(f"/api/products/{sample_product.id}")
    assert prod_res.json()["total_stock"] == 40

def test_transaction_insufficient_stock(client, sample_product):
    """Selling more than available should fail."""
    # Stock is 0 initially
    sale_data = {
        "product_id": sample_product.id,
        "transaction_type": "sale",
        "quantity": 5,
        "unit_price": 45.0
    }
    res = client.post("/api/transactions", json=sale_data)
    assert res.status_code == 400
    assert "Insufficient stock" in res.json()["detail"]


# ─── Analytics & Reports ───

def test_dashboard_stats(client, sample_product_with_batches):
    """Dashboard should return aggregated stats."""
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()
    
    assert data["total_products"] >= 1
    # Sample has 3 batches: 50 + 20 + 10 = 80 total items
    assert data["total_stock_value"] > 0
    assert "expiry_alerts" in data
    assert "low_stock_count" in data

def test_dashboard_kpi(client):
    """Lightweight KPI endpoint."""
    response = client.get("/api/dashboard/kpi")
    assert response.status_code == 200
    data = response.json()
    assert "total_revenue" in data
    assert "total_wastage_loss" in data

def test_expiry_alerts_api(client, sample_product_with_batches):
    """Expiry endpoint should return critical/expired batches."""
    response = client.get("/api/batches/expiring?days=365")
    assert response.status_code == 200
    alerts = response.json()
    
    # Should find the expired and warning batches from the fixture
    statuses = [a["status"] for a in alerts]
    assert "expired" in statuses
    assert "warning" in statuses

def test_revenue_analytics(client):
    """Revenue analytics endpoint."""
    response = client.get("/api/analytics/revenue?days=30")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_wastage_report(client):
    """Wastage report endpoint."""
    response = client.get("/api/analytics/wastage")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ─── Suppliers & Purchase Orders ───

def test_supplier_flow(client):
    """Create supplier and list them."""
    data = {
        "name": "Integration Supplier",
        "category": "Frozen Foods",
        "contact_email": "supply@frozen.com",
        "phone": "555-0000"
    }
    res = client.post("/api/suppliers", json=data)
    assert res.status_code == 200
    
    list_res = client.get("/api/suppliers")
    assert len(list_res.json()) >= 1
