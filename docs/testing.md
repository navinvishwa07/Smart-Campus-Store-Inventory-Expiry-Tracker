# 🧪 Testing Guide

This project includes both **Backend** (Unit/Integration) and **Frontend** (End-to-End) testing suites.

## Prerequisites

1.  **Python 3.12+**
2.  **Node.js 20+** (Install via `brew install node`)
3.  **Dependencies**:
    - Backend: `pip install -r backend/requirements.txt`
    - Playwright: `npm install && npx playwright install`

---

## 🐍 Backend Testing (Pytest)

Run these checks before committing backend changes.

### Running Tests
```bash
# Run all backend tests
pytest tests/backend

# Run specifically only unit tests
pytest tests/backend/test_models.py
```

### Coverage Reports
Generate a coverage report to see tested lines.
```bash
coverage run -m pytest tests/backend
coverage report -m
# Open HTML report (optional)
# coverage html && open htmlcov/index.html
```

### What's Covered?
- **Models**: Logic for expiry status, stock calculations, low stock detection.
- **API**: Full CRUD workflows, error handling, validation.
- **ML Engine**: Sanity checks on prediction format.

---

## 🎭 Frontend / E2E Testing (Playwright)

End-to-End tests simulate user interactions in a real browser (Chromium).

### Prerequisites
Wait for the backend server to be running locally (`port 8000`).
```bash
# Terminal 1: Start Backend
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Running Tests
```bash
# Terminal 2: Run Playwright
npx playwright test
```

### Viewing Results
- **Headless Mode**: Default. Results show in terminal.
- **UI Mode**: Interactive test runner.
    ```bash
    npx playwright test --ui
    ```
- **Show Report**: View HTML report after run.
    ```bash
    npx playwright show-report
    ```

### What's Covered?
- **Dashboard Load**: Verifies core UI elements render.
- **Add Product Flow**: Navigates through UI to create a product.
- **Form Validation**: Checks inputs.
- **Navigation**: Side menu links work correctly.

---

## 🤖 Continuous Integration (CI)

Every push to `main` triggers a GitHub Action workflow that:
1.  Installs Python & Node.
2.  Lints backend code (`flake8`).
3.  Runs Backend tests (`pytest`).
4.  Boots up the backend server.
5.  Runs E2E tests (`playwright`).

**Configuration**: `.github/workflows/ci.yml`
