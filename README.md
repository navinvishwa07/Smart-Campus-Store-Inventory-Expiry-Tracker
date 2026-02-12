# 🏪 Smart Campus Store — Inventory & Expiry Tracker

A full-stack inventory management system with **ML-powered seasonal demand prediction**, **barcode scanning**, **expiry monitoring**, and **revenue analytics** — built for campus stores.

## 🚀 Quick Start

### Option 1: Docker (Recommended — No venv needed)
```bash
docker-compose up --build
```
Open [http://localhost:8000](http://localhost:8000)

### Option 2: Local Python
```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```
Open [http://localhost:8000](http://localhost:8000)

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📦 **Item Catalog** | 65+ products across 9 categories with batch-level tracking |
| ⏰ **Expiry Monitoring** | 🔴 ≤7 days, 🟡 ≤15 days, 🟢 Fresh — color-coded alerts |
| 📉 **Low-Stock Alerts** | Automatic alerts when stock falls below minimum threshold |
| 💰 **Revenue Tracking** | Daily revenue, category-wise sales, and net profit analytics |
| 📷 **Barcode Scanner** | Webcam-based barcode scanning with html5-qrcode |
| 🤖 **ML Insights** | Seasonal demand prediction using polynomial regression (scikit-learn) |
| 💳 **POS Integration** | Sale/wastage/restock transactions with FIFO stock deduction |
| 🗑️ **Wastage Reports** | Category-wise wastage analysis |

## 📂 Project Structure

```
├── backend/
│   ├── main.py          # FastAPI app + all API routes
│   ├── models.py        # SQLAlchemy ORM (Product, Batch, Transaction)
│   ├── schemas.py       # Pydantic request/response models
│   ├── database.py      # DB engine + session management
│   ├── seed.py          # Seeds 65+ products with batches
│   ├── ml_engine.py     # Seasonal pattern ML module
│   └── requirements.txt
├── frontend/
│   ├── index.html       # Dashboard UI
│   ├── styles.css       # Premium dark theme
│   └── app.js           # Frontend logic + charts
├── Dockerfile
├── docker-compose.yml
├── medium_sales_dataset.csv
└── README.md
```

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI, SQLAlchemy |
| Database | SQLite (Docker-portable) |
| Frontend | HTML5, CSS3, JavaScript, Chart.js |
| ML | scikit-learn, pandas, numpy |
| Scanner | html5-qrcode |
| Deploy | Docker, docker-compose |

## 👥 Team

| Role | Member | Responsibility |
|------|--------|---------------|
| Backend | Navin | API routes, expiry/stock logic, ML |
| Frontend | Balaa | Dashboard, charts, barcode UI |
| Database | Armaan/Aayush | Schema, seed data, queries |

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard` | Full dashboard stats |
| GET | `/api/products` | List all products |
| POST | `/api/products` | Add new product |
| GET | `/api/products/barcode/{code}` | Barcode lookup |
| POST | `/api/batches` | Add inventory batch |
| GET | `/api/batches/expiring?days=15` | Expiry alerts |
| POST | `/api/transactions` | Record sale/wastage |
| GET | `/api/analytics/revenue` | Revenue timeline |
| GET | `/api/analytics/wastage` | Wastage report |
| GET | `/api/ml/seasonal` | ML predictions |
| GET | `/api/ml/insights` | Category insights |

---
*Built with ❤️ for campus life*
