# 🏪 Smart Campus Store — Inventory & Expiry Tracker

[![CI Pipeline](https://github.com/navinvishwa07/Smart-Campus-Store/actions/workflows/ci.yml/badge.svg)](https://github.com/navinvishwa07/Smart-Campus-Store/actions/workflows/ci.yml)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688.svg)
![Playwright](https://img.shields.io/badge/Playwright-Test-green.svg)
![License MIT](https://img.shields.io/badge/license-MIT-blue.svg)

## Team name : Blue Whales 
##Team Members : Navin Vishwa, Balaa Ts, Armaan Sadat, Aayush Ramkumar

A complete **Inventory Management System** designed for campus stores to track stock levels, monitor expiry dates, and predict seasonal demand using Machine Learning.

---

## 🚀 Features

- **Dashboard**: Real-time overview of KPIs (Revenue, Low Stock, Wastage).
- **Inventory Management**: Add/Edit/Delete products with batch-level tracking.
- **Expiry Monitoring**: Color-coded alerts for expiring batches (🔴 Expired, 🟡 Warning, 🟢 Fresh).
- **POS / Sales**: Record transactions and deduct stock automatically (FIFO).
- **ML Forecasting**: Predicts demand for next month based on historical trends.
- **Reports**: Revenue vs. Wastage analysis, Purchase Order recommendations.
- **Responsive UI**: Works on desktop and tablets.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy (SQLite/PostgreSQL ready).
- **Frontend**: Vanilla JS, HTML5, CSS3 (Single Page App style).
- **Database**: SQLite (Development), PostgreSQL (Production ready).
- **Testing**: Pytest (Backend), Playwright (E2E).
- **ML Engine**: Scikit-Learn (Polynomial Regression).

---

## 📂 Project Structure

```
.
├── backend/            # FastAPI Application & Logic
│   ├── main.py         # Entry point, API Routes
│   ├── models.py       # DB Models
│   ├── ml_engine.py    # Forecasting Logic
│   └── requirements.txt
├── frontend/           # Static Frontend Assets
│   ├── index.html      # Main UI
│   ├── app.js          # Client-side Logic
│   └── styles.css      # Styling & Layout
├── tests/              # Test Suite
│   ├── backend/        # Pytest Unit/Integration Tests
│   └── e2e/            # Playwright End-to-End Tests
├── docs/               # Detailed Documentation
└── .github/            # CI/CD Workflows
```

---

## ⚡ Quick Start

### 1. Prerequisites
- **Python 3.12+**
- **Node.js 20+** (for frontend dependencies & tests)

### 2. Install Backend
```bash
# Create virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 3. Install Frontend Tools (for testing)
```bash
# Install Playwright & Test tools
npm install
npx playwright install
```

### 4. Run the Application
Start the backend server. The backend serves the frontend automatically at `http://localhost:8000`.

```bash
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Open **[http://localhost:8000](http://localhost:8000)** in your browser.

---

## 🧪 Running Tests

### Backend Unit Tests
```bash
# Run pytest suite
pytest tests/backend

# Run with coverage report
coverage run -m pytest tests/backend && coverage report -m
```

### End-to-End Tests
Ensure the backend is running (`port 8000`), then:
```bash
# Run Playwright tests
npx playwright test

# View HTML report
npx playwright show-report
```

For more details, see [docs/testing.md](docs/testing.md).

---

## 📚 Documentation

Detailed documentation is available in the [`docs/`](docs/) directory:

- [**System Architecture**](docs/architecture.md): High-level design & component breakdown.
- [**API Reference**](docs/api.md): Endpoints, request/response examples.
- [**Database Schema**](docs/schema.md): ER Diagram and table details.
- [**ML Insights Guide**](docs/ml_insights.md): How to read seasonal predictions.
- [**Deployment Guide**](docs/deployment.md): (Planned) Instructions for production.

---

## 🤖 ML Engine & Forecasting

The system analyzes past sales data to predict future demand.
1. **Training**: Happens at startup using `medium_sales_dataset.csv` or transaction history.
2. **Prediction**: Available via `/api/ml/seasonal` endpoint.
3. **Usage**: Auto-generates `PurchaseOrder` drafts when predicted demand exceeds current stock.

---

## 🤝 Contributing

1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

---

**License**: MIT
