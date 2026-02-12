"""
Seasonal demand pattern detection using ML.
Analyzes historical sales data to predict seasonal trends per category.
"""
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from typing import List, Dict
import calendar


class SeasonalAnalyzer:
    """Detects and predicts seasonal purchasing patterns."""

    def __init__(self):
        self.models: Dict[str, LinearRegression] = {}
        self.is_trained = False

    def train_from_csv(self, csv_path: str):
        """Train seasonal models from the provided sales dataset."""
        try:
            df = pd.read_csv(csv_path)
            self._train(df)
        except Exception as e:
            print(f"ML Training error: {e}")

    def train_from_transactions(self, transactions: list):
        """Train from database transaction records."""
        if not transactions:
            return

        data = []
        for t in transactions:
            data.append({
                "category": t.product.category if t.product else "Unknown",
                "month": t.transaction_date.month,
                "quantity": t.quantity,
                "amount": t.total_amount,
            })
        df = pd.DataFrame(data)
        self._train_from_sales(df)

    def _train(self, df: pd.DataFrame):
        """Train models from the original CSV dataset."""
        categories = df["Item_Type"].unique()

        for category in categories:
            cat_data = df[df["Item_Type"] == category]

            # Use outlet establishment year as time proxy for seasonality
            # Group by year to create time-series-like data
            yearly = cat_data.groupby("Outlet_Establishment_Year").agg({
                "Item_Outlet_Sales": "mean",
                "Item_MRP": "mean"
            }).reset_index()

            if len(yearly) < 3:
                continue

            X = yearly[["Outlet_Establishment_Year"]].values
            y = yearly["Item_Outlet_Sales"].values

            # Polynomial regression for trend detection
            poly = PolynomialFeatures(degree=2)
            X_poly = poly.fit_transform(X)

            model = LinearRegression()
            model.fit(X_poly, y)
            self.models[category] = {
                "model": model,
                "poly": poly,
                "mean_sales": cat_data["Item_Outlet_Sales"].mean(),
                "std_sales": cat_data["Item_Outlet_Sales"].std(),
                "data_points": len(cat_data)
            }

        self.is_trained = True

    def _train_from_sales(self, df: pd.DataFrame):
        """Train from actual sales transaction data."""
        categories = df["category"].unique()

        for category in categories:
            cat_data = df[df["category"] == category]
            monthly = cat_data.groupby("month").agg({
                "quantity": "sum",
                "amount": "sum"
            }).reset_index()

            if len(monthly) < 2:
                continue

            X = monthly[["month"]].values
            y = monthly["quantity"].values

            poly = PolynomialFeatures(degree=2)
            X_poly = poly.fit_transform(X)

            model = LinearRegression()
            model.fit(X_poly, y)
            self.models[category] = {
                "model": model,
                "poly": poly,
                "mean_sales": cat_data["quantity"].mean(),
                "std_sales": cat_data["quantity"].std(),
                "data_points": len(cat_data)
            }

        self.is_trained = True

    def _get_heuristic_prediction(self, category: str, month: int) -> float:
        """Fallback heuristics for when no data exists."""
        base_demand = 50.0  # arbitrary base
        cat = category.lower()
        multiplier = 1.0

        # 1. Beverages / Summer
        if "drink" in cat or "beverage" in cat or "juice" in cat or "cold" in cat:
            if 4 <= month <= 7:  # Apr-Jul
                multiplier = 1.8
            elif month in [12, 1, 2]:  # Winter
                multiplier = 0.6

        # 2. Ice Cream / Frozen
        elif "cream" in cat or "frozen" in cat:
            if 4 <= month <= 8:
                multiplier = 2.0
            else:
                multiplier = 0.5

        # 3. Stationery / Exams (Mar, Apr, Nov, Dec)
        elif "stationery" in cat or "book" in cat or "pen" in cat:
            if month in [3, 4, 11, 12]:
                multiplier = 1.5
            elif month == 6:  # New semester
                multiplier = 1.3

        # 4. Snacks / General
        elif "snack" in cat or "food" in cat:
            if month in [10, 11, 12]:  # Festive season
                multiplier = 1.2

        return round(base_demand * multiplier, 2)

    def predict_demand(self, category: str, month: int) -> Dict:
        """Predict demand for a category in a given month."""
        if category not in self.models:
            # Use heuristic
            pred = self._get_heuristic_prediction(category, month)
            return {
                "category": category,
                "month": month,
                "month_name": calendar.month_name[month],
                "predicted_demand": pred,
                "confidence": 0.5  # Medium confidence for heuristics
            }

        model_info = self.models[category]
        model = model_info["model"]
        poly = model_info["poly"]

        X_pred = poly.transform([[month]])
        prediction = max(0, model.predict(X_pred)[0])

        # Confidence based on data points
        confidence = min(1.0, model_info["data_points"] / 50)

        return {
            "category": category,
            "month": month,
            "month_name": calendar.month_name[month],
            "predicted_demand": round(prediction, 2),
            "confidence": round(confidence, 2)
        }

    def get_all_predictions(self) -> List[Dict]:
        """Get predictions for all categories across all months."""
        predictions = []
        for category in self.models:
            for month in range(1, 13):
                pred = self.predict_demand(category, month)
                predictions.append(pred)
        return predictions

    def get_category_insights(self) -> List[Dict]:
        """Get summary insights per category."""
        insights = []
        for category, info in self.models.items():
            monthly_preds = []
            for m in range(1, 13):
                pred = self.predict_demand(category, m)
                monthly_preds.append(pred["predicted_demand"])

            peak_month = np.argmax(monthly_preds) + 1
            low_month = np.argmin(monthly_preds) + 1

            insights.append({
                "category": category,
                "mean_demand": round(np.mean(monthly_preds), 2),
                "peak_month": calendar.month_name[peak_month],
                "low_month": calendar.month_name[low_month],
                "peak_demand": round(max(monthly_preds), 2),
                "low_demand": round(min(monthly_preds), 2),
                "volatility": round(np.std(monthly_preds), 2),
                "data_points": info["data_points"],
                "confidence": round(min(1.0, info["data_points"] / 50), 2)
            })
        return insights


# Global instance
seasonal_analyzer = SeasonalAnalyzer()
