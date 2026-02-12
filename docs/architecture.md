# 🏗️ System Architecture

## Overview
The Smart Campus Store is built as a monolithic application with a clear separation of concerns, designed for simplicity and ease of deployment. It combines a high-performance **FastAPI backend** with a responsive **Vanilla JS frontend**, served from a single origin.

---

## 🧩 Technology Stack

| Layer | Technology | Role |
|---|---|---|
| **Frontend** | Vanilla JavaScript (ES6+), HTML5, CSS3 | Validates inputs, renders UI, handles API calls |
| **Backend** | Python 3.12, FastAPI | REST API, Business Logic, ML Integration |
| **Database** | SQLite (Dev) / PostgreSQL (Prod) | Relational data persistence |
| **ORM** | SQLAlchemy 2.0 | Database abstraction and migrations |
| **ML Engine** | Scikit-learn, Pandas, NumPy | Seasonal forecasting and trend analysis |
| **Testing** | Pytest, Playwright | Unit, Integration, and End-to-End testing |

---

## 🏛️ High-Level Architecture

```mermaid
graph TD
    User[Store Manager] -->|Browser| Frontend[Frontend UI]
    Frontend -->|REST API| Backend[FastAPI Backend]
    
    subgraph "Backend Services"
        Backend -->|Query| DB[(SQLite Database)]
        Backend -->|Train/Predict| ML[ML Engine]
        ML -->|Read| History[Sales History (CSV/DB)]
    end
    
    subgraph "External Integrations"
        Scanner[Barcode Scanner] -->|Input| Frontend
    end
```

### Key Components

1.  **FastAPI Application (`backend/main.py`)**
    - Acts as the central controller.
    - Serves static frontend files (`/static`).
    - Exposes REST API endpoints (`/api/*`).
    - Manages database sessions per request.

2.  **ML Engine (`backend/ml_engine.py`)**
    - A specialized module for demand forecasting.
    - Trains on historical sales data (CSV or DB).
    - Uses **Polynomial Regression** to detect seasonal trends.
    - Provides predictions for:
        - Monthly demand per category.
        - Stock-out dates.
        - Purchase Order recommendations.

3.  **Database Layer (`backend/models.py`)**
    - **Products**: Core catalog.
    - **Batches**: Inventory units with expiry dates.
    - **Transactions**: Ledger of all stock movements.
    - **Suppliers**: Vendor directory.
    - **Purchase Orders**: Generated drafts for restocking.

4.  **Frontend (`frontend/`)**
    - **Single Page Application (SPA)** feel using vanilla JS based routing (hiding/showing sections).
    - **Chart.js** for visualizations.
    - **HTML5-QRCode** for browser-based barcode scanning.

---

## 🔄 Data Flow

### 1. Sales Transaction
1. User scans item on POS page.
2. Frontend calls `GET /api/products/barcode/{code}`.
3. Backend returns product details.
4. User confirms quantity.
5. Frontend calls `POST /api/transactions` (type='sale').
6. Backend:
    - Deducts stock from oldest batches (FIFO).
    - Creates Transaction record.
    - Checks for low stock → **Triggers Alert**.
    - Updates ML confidence if data points increase.

### 2. Auto-Restocking (ML Driven)
1. System runs daily check (`/api/cron/daily-check` or on-transaction).
2. ML Engine predicts demand for next 30 days.
3. If `current_stock < predicted_demand`:
    - Create `PurchaseOrder` (status='draft').
    - Notify user via Dashboard Alert.

---

## 📂 Project Structure

```
├── backend/
│   ├── main.py           # App entry point & routes
│   ├── models.py         # Database models
│   ├── schemas.py        # Pydantic schemas (Validation)
│   ├── database.py       # DB connection
│   ├── ml_engine.py      # Forecasting logic
│   ├── seed.py           # Initial data seeding
│   └── requirements.txt  # Python dependencies
├── frontend/
│   ├── index.html        # Main UI
│   ├── styles.css        # Styling
│   └── app.js            # Frontend logic
├── tests/
│   ├── backend/          # Pytest unit tests
│   ├── e2e/              # Playwright UI tests
│   └── conftest.py       # Test configuration
├── docs/                 # Documentation
└── .github/              # CI/CD Workflows
```
