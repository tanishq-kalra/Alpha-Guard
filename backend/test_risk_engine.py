"""
Alpha-Guard — Risk Engine Tests
================================
Validates the Altman Z-Score calculation against known financial profiles.
"""

import numpy as np
import pytest
from models import FinancialData, MonteCarloInput
from risk_engine import (
    ZScoreNotApplicable,
    calculate_altman_z_score,
    classify_zone,
    run_monte_carlo_simulation,
)


class TestAltmanZScore:
    """Test suite for Altman Z-Score calculation."""

    def _make_financials(self, **overrides) -> FinancialData:
        """Create a FinancialData instance with sensible defaults."""
        defaults = {
            "ticker": "TEST",
            "total_assets": 1_000_000,
            "current_assets": 500_000,
            "current_liabilities": 200_000,
            "retained_earnings": 300_000,
            "ebit": 150_000,
            "market_cap": 2_000_000,
            "total_liabilities": 400_000,
            "revenue": 800_000,
        }
        defaults.update(overrides)
        return FinancialData(**defaults)

    def test_safe_zone_company(self):
        """A financially healthy company should score in the Safe Zone (> 2.99)."""
        data = self._make_financials(
            total_assets=1_000_000,
            current_assets=600_000,
            current_liabilities=200_000,
            retained_earnings=400_000,
            ebit=200_000,
            market_cap=3_000_000,
            total_liabilities=300_000,
            revenue=900_000,
        )
        result = calculate_altman_z_score(data)

        assert result.zone == "Safe", f"Expected Safe zone, got {result.zone} (score={result.score})"
        assert result.score > 2.99
        assert result.ticker == "TEST"
        assert result.interpretation is not None

    def test_distress_zone_company(self):
        """A financially distressed company should score in the Distress Zone (< 1.81)."""
        data = self._make_financials(
            total_assets=1_000_000,
            current_assets=100_000,
            current_liabilities=500_000,
            retained_earnings=-200_000,
            ebit=-50_000,
            market_cap=100_000,
            total_liabilities=800_000,
            revenue=300_000,
        )
        result = calculate_altman_z_score(data)

        assert result.zone == "Distress", f"Expected Distress zone, got {result.zone} (score={result.score})"
        assert result.score < 1.81

    def test_gray_zone_company(self):
        """A company with moderate metrics should fall in the Gray Zone (1.81 - 2.99)."""
        data = self._make_financials(
            total_assets=1_000_000,
            current_assets=350_000,
            current_liabilities=250_000,
            retained_earnings=150_000,
            ebit=80_000,
            market_cap=800_000,
            total_liabilities=500_000,
            revenue=600_000,
        )
        result = calculate_altman_z_score(data)

        assert result.zone == "Gray", f"Expected Gray zone, got {result.zone} (score={result.score})"
        assert 1.81 <= result.score <= 2.99

    def test_component_ratios_are_correct(self):
        """Verify that individual component ratios are calculated correctly."""
        data = self._make_financials(
            total_assets=1_000_000,
            current_assets=400_000,
            current_liabilities=200_000,
            retained_earnings=300_000,
            ebit=150_000,
            market_cap=2_000_000,
            total_liabilities=400_000,
            revenue=800_000,
        )
        result = calculate_altman_z_score(data)
        c = result.components

        # X1 = (400k - 200k) / 1M = 0.2
        assert abs(c.x1_working_capital_to_total_assets - 0.2) < 1e-6
        # X2 = 300k / 1M = 0.3
        assert abs(c.x2_retained_earnings_to_total_assets - 0.3) < 1e-6
        # X3 = 150k / 1M = 0.15
        assert abs(c.x3_ebit_to_total_assets - 0.15) < 1e-6
        # X4 = 2M / 400k = 5.0
        assert abs(c.x4_market_cap_to_total_liabilities - 5.0) < 1e-6
        # X5 = 800k / 1M = 0.8
        assert abs(c.x5_revenue_to_total_assets - 0.8) < 1e-6

    def test_manual_score_calculation(self):
        """Verify the weighted sum matches hand-calculated Z-Score."""
        data = self._make_financials(
            total_assets=1_000_000,
            current_assets=400_000,
            current_liabilities=200_000,
            retained_earnings=300_000,
            ebit=150_000,
            market_cap=2_000_000,
            total_liabilities=400_000,
            revenue=800_000,
        )
        result = calculate_altman_z_score(data)

        # Manual: 1.2*0.2 + 1.4*0.3 + 3.3*0.15 + 0.6*5.0 + 1.0*0.8
        #       = 0.24 + 0.42 + 0.495 + 3.0 + 0.8 = 4.955
        assert abs(result.score - 4.955) < 0.01, f"Expected ~4.955, got {result.score}"

    def test_zero_total_assets_raises_error(self):
        """Zero total assets should be rejected by Pydantic validation (gt=0)."""
        with pytest.raises(Exception):
            FinancialData(
                ticker="FAIL",
                total_assets=0,  # Pydantic gt=0 constraint rejects this
                current_assets=0,
                current_liabilities=0,
                retained_earnings=0,
                ebit=0,
                market_cap=1,
                total_liabilities=1,
                revenue=0,
            )

    def test_negative_retained_earnings(self):
        """Companies with negative retained earnings should still compute correctly."""
        data = self._make_financials(retained_earnings=-500_000)
        result = calculate_altman_z_score(data)

        assert result.components.x2_retained_earnings_to_total_assets < 0
        assert isinstance(result.score, float)


class TestModelSelection:
    """Altman variant selection and the Z'' model."""

    BASE = {
        "ticker": "TEST",
        "total_assets": 1_000_000,
        "current_assets": 500_000,
        "current_liabilities": 200_000,
        "retained_earnings": 300_000,
        "ebit": 150_000,
        "market_cap": 2_000_000,
        "total_liabilities": 400_000,
        "revenue": 800_000,
    }

    def _data(self, **overrides) -> FinancialData:
        return FinancialData(**{**self.BASE, **overrides})

    def test_manufacturer_uses_original_model(self):
        result = calculate_altman_z_score(self._data(sic_code=3571))
        assert result.model == "original"
        assert result.x4_basis == "market"
        assert result.weights["x5"] == 1.0

    def test_non_manufacturer_uses_z_double_prime(self):
        result = calculate_altman_z_score(self._data(sic_code=7372))
        assert result.model == "z_double_prime"
        assert result.x4_basis == "book"
        # X4 = book equity / liabilities = (1.0M - 0.4M) / 0.4M = 1.5
        assert abs(result.components.x4_market_cap_to_total_liabilities - 1.5) < 1e-9
        # 6.56*0.3 + 3.26*0.3 + 6.72*0.15 + 1.05*1.5 = 1.968 + 0.978 + 1.008 + 1.575
        assert abs(result.score - 5.529) < 1e-6
        assert result.safe_threshold == 2.60

    def test_missing_market_cap_uses_z_double_prime(self):
        result = calculate_altman_z_score(self._data(market_cap=None))
        assert result.model == "z_double_prime"

    def test_yahoo_sourced_data_uses_z_double_prime(self):
        result = calculate_altman_z_score(self._data(sector="Technology"))
        assert result.model == "z_double_prime"

    def test_manual_input_keeps_original_model(self):
        assert calculate_altman_z_score(self._data()).model == "original"

    def test_explicit_model_override(self):
        result = calculate_altman_z_score(self._data(sic_code=3571, z_model="z_double_prime"))
        assert result.model == "z_double_prime"

    def test_original_model_requires_market_cap(self):
        with pytest.raises(ValueError):
            calculate_altman_z_score(self._data(market_cap=None, z_model="original"))

    @pytest.mark.parametrize("overrides", [{"sic_code": 6021}, {"sector": "Financial Services"}])
    def test_financial_companies_rejected(self, overrides):
        with pytest.raises(ZScoreNotApplicable):
            calculate_altman_z_score(self._data(**overrides))

    def test_z_double_prime_zones(self):
        assert classify_zone(2.7, "z_double_prime")[0] == "Safe"
        assert classify_zone(2.0, "z_double_prime")[0] == "Gray"
        assert classify_zone(1.0, "z_double_prime")[0] == "Distress"


class TestMonteCarlo:

    def _params(self, **overrides) -> MonteCarloInput:
        return MonteCarloInput(**{
            "ticker": "TEST", "num_simulations": 2_000, "time_horizon_years": 5,
            "initial_revenue": 1e9, "seed": 42, **overrides,
        })

    def test_seed_makes_runs_reproducible(self):
        a = run_monte_carlo_simulation(self._params())
        b = run_monte_carlo_simulation(self._params())
        assert a.mean_final_revenue == b.mean_final_revenue

    def test_output_shapes(self):
        result = run_monte_carlo_simulation(self._params())
        assert len(result.sample_paths) == 6  # year 0..5
        assert len(result.histogram) == 20
        assert sum(h["count"] for h in result.histogram) == 2_000
        assert result.sample_paths[0]["median"] == 1e9

    def test_percentile_bands_are_ordered(self):
        for row in run_monte_carlo_simulation(self._params()).sample_paths:
            assert row["p5"] <= row["p25"] <= row["median"] <= row["p75"] <= row["p95"]

    def test_zero_volatility_is_deterministic_growth(self):
        result = run_monte_carlo_simulation(self._params(revenue_growth_std=0.0, revenue_growth_mean=0.05))
        assert result.probability_of_decline == 0.0
        assert abs(result.median_final_revenue - 1e9 * np.exp(0.25)) < 1

    def test_billion_scale_histogram_labels(self):
        label = run_monte_carlo_simulation(self._params()).histogram[-1]["range"]
        assert label.endswith("B")
