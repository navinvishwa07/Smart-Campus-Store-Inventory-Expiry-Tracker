"""
Integration and Unit tests for the ML Seasonal Engine.
"""
from backend.ml_engine import seasonal_analyzer

def test_ml_prediction_sanity():
    """ML Engine should return sensible predictions format."""
    pred = seasonal_analyzer.predict_demand("Dairy", 5)
    
    assert "predicted_demand" in pred
    assert pred["month"] == 5
    assert pred["category"] == "Dairy"
    assert pred["predicted_demand"] >= 0

def test_ml_heuristic_fallback():
    """Unknown categories should use heuristics (confidence 0.5)."""
    pred = seasonal_analyzer.predict_demand("UnknownCategory", 1)
    
    assert pred["confidence"] == 0.5
    assert pred["predicted_demand"] > 0

def test_ml_insights_format():
    """Insights should return list of dict components."""
    # Ensure analyzer has at least some data (heuristic)
    dummy_data = {
        "Dairy": {
            "model": None, # Mock
            "data_points": 10,
        }
    }
    # We won't mock internals, just call public API which handles empty state
    insights = seasonal_analyzer.get_category_insights()
    
    # Even if empty, it should be a list
    assert isinstance(insights, list)

def test_ml_training_does_not_crash():
    """Training with empty list should be safe."""
    seasonal_analyzer.train_from_transactions([])
    # If we reached here, no exception was raised
    assert True
