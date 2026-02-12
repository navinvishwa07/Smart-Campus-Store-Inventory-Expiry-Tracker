# 🤖 ML Insights & Forecasting Documentation

The **Smart Campus Store** uses a built-in Machine Learning engine to analyze sales trends and automate inventory decisions. This guide explains how to interpret the **ML Insights Window** and how the underlying system works.

---

## 🧠 How It Works

The system uses **Polynomial Regression** (via `scikit-learn`) to detect seasonal patterns in your sales history. It doesn't just look at "average sales" — it understands that:
- **Soft Drinks** sell more in **Summer** (April-June).
- **Exam Supplies** sell more in **March/November**.
- **Snacks** peak during **Festive Seasons**.

### Data Sources
1.  **Historical CSV**: On startup, the system trains on `medium_sales_dataset.csv` (if present) to establish baseline patterns.
2.  **Real-Time Transactions**: Every new sale recorded in the app refines the model, making it smarter over time.

---

## 📈 Seasonal Demand Chart

Located in the **ML Insights** page, this interactive chart shows the **predicted demand quantity** for each month of the year.

### How to Use
- **Y-Axis**: Predicted quantity to be sold.
- **X-Axis**: Months (Jan - Dec).
- **Lines**: Each colored line represents a product category (e.g., Dairy, Snacks).
- **Filter**: Use the dropdown at the top to focus on a specific category (e.g., "Show only Soft Drinks").

### Strategic Value
- **Plan Ahead**: If you see a spike for "Soft Drinks" in May, you know to stock up *before* May.
- **Reduce Wastage**: If demand drops for "Dairy" in Winter, reduce your orders to prevent expiry.

---

## 📦 Automated Purchase Orders (Smart Restock)

The system doesn't just show charts; it takes action.

### The Algorithm
Every day (and after major transactions), the system runs this check:
```python
if current_stock < predicted_demand_for_next_30_days:
    risk_level = "High"
    generate_draft_po()
```

### The "Drafts" Section
Below the chart, you will see **Automated Purchase Order Drafts**.
- These are **recommendations**, not automatic purchases.
- **Action**: You can review these drafts, adjust quantities, and send them to suppliers (simulated).
- **Trigger**: Defines the "Stock-Out Risk" date (e.g., "Stock out predicted within 48h").

---

## 🔍 Technical Details

- **Model**: Polynomial Regression (Degree 2).
- **Library**: Scikit-Learn.
- **Training Frequency**:
    - **Initial**: Application startup.
    - **Adaptive**: Retrains periodically as new transaction data accumulates.
- **Confidence Score**: The system calculates a confidence score based on the volume of data points. Categories with few sales use **heuristic fallbacks** (market-standard patterns) until enough data is gathered.

---

## ❓ FAQ

**Q: Why is the chart empty?**
A: The ML model needs data. Ensure `medium_sales_dataset.csv` is in the root folder, or record some transactions in the POS to start training.

**Q: Can I turn off auto-ordering?**
A: Yes, the system only creates *Drafts*. It never sends orders without your approval.

**Q: accuracy?**
A: The model improves with time. Initial accuracy depends on the quality of the CSV dataset.
