import pytest
from app.services.subscription_service import calculate_discounted_duration

class TestSubscriptionService:
    def test_calculate_discounted_duration_with_half_year_promotion(self):
        """Test that a 6-month subscription with half-year promotion returns 7 months."""
        assert calculate_discounted_duration(6, "half_year_plus_one_month") == 7

    def test_calculate_discounted_duration_without_promotion(self):
        """Test that a 6-month subscription without promotion returns 6 months."""
        assert calculate_discounted_duration(6, None) == 6

    def test_calculate_discounted_duration_with_year_promotion(self):
        """Test that a 12-month subscription with year promotion returns 14 months."""
        assert calculate_discounted_duration(12, "year_plus_two_months") == 14

    def test_calculate_discounted_duration_invalid_promotion(self):
        """Test that invalid promotion returns original duration."""
        assert calculate_discounted_duration(6, "invalid_promotion") == 6

    def test_calculate_discounted_duration_partial_month(self):
        """Test that fractional months are handled correctly."""
        assert calculate_discounted_duration(3, "half_year_plus_one_month") == 3