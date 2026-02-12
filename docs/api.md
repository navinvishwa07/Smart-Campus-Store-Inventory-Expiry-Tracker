# 🌐 Smart Campus Store API Reference

Base URL: `http://localhost:8000/api`

## Authentication
Currently open for local use (No Auth).

---

## 📦 Products

### `GET /products`
List all products.
- **Query Params**:
  - `category`: Filter by category.
  - `search`: Search by name or barcode.
  - `low_stock`: Boolean (true/false) to filter low stock items.

### `GET /products/{id}`
Get a single product with its batches.

### `POST /products`
Create a new product.
- **Body**:
  ```json
  {
    "item_id": "ITM001",
    "name": "Amul Milk 500ml",
    "category": "Dairy",
    "mrp": 30.0,
    "barcode": "890126201001",
    "min_stock": 10
  }
  ```

### `GET /products/barcode/{barcode}`
Lookup product by barcode.
- **Returns**: Product object and `batch_info` (status, quantity).

---

## 🏷️ Batches (Inventory)

### `POST /batches`
Add stock (Restock or New Batch).
- **Body**:
  ```json
  {
    "product_id": 1,
    "quantity": 100,
    "cost_price": 25.0,
    "expiry_date": "2024-12-31"
  }
  ```

### `GET /batches/expiring`
List batches expiring within N days.
- **Query**: `days=30` (default)
- **Returns**: List of `ExpiryAlert` objects.

---

## 💳 Transactions (POS)

### `POST /transactions`
Record a Sale, Wastage, or Restock.
- **Body**:
  ```json
  {
    "product_id": 1,
    "transaction_type": "sale",  // sale, wastage, restock
    "quantity": 5,
    "unit_price": 30.0
  }
  ```

### `GET /transactions`
List transaction history.

---

## 📊 Analytics & Dashboard

### `GET /dashboard`
Comprehensive dashboard JSON (KPIs, Active Alerts, Recent Sales).

### `GET /analytics/revenue`
Revenue timeline (last 30 days).
- **Format**: `[{ date, revenue, cost, profit }, ...]`

### `GET /analytics/wastage`
Categorized wastage breakdown.

### `GET /ml/seasonal`
Get category-wise seasonal demand predictions for the current/future month.

### `GET /purchase-orders`
List auto-generated PO drafts (status `draft`).
- **Use**: Review suggested restocks.

---

## 🛠️ Errors

Standard HTTP Codes:
- `200 OK`: Success
- `400 Bad Request`: Validation error / Logical error (e.g., negative stock)
- `404 Not Found`: Resource missing
- `422 Validation Error`: Pydantic field validation failed
