"""Unit tests for the business metrics service."""


class TestBusinessMetricsService:
    def test_get_mrr_returns_float(self, app, db):
        from app.services.business_metrics import BusinessMetricsService
        mrr = BusinessMetricsService.get_mrr()
        assert isinstance(mrr, float)

    def test_get_arr_returns_twelve_times_mrr(self, app, db):
        from app.services.business_metrics import BusinessMetricsService
        mrr = BusinessMetricsService.get_mrr()
        arr = BusinessMetricsService.get_arr()
        assert arr == mrr * 12

    def test_get_churn_rate_has_keys(self, app, db):
        from app.services.business_metrics import BusinessMetricsService
        churn = BusinessMetricsService.get_churn_rate(30)
        assert "churn_rate" in churn
        assert "period_days" in churn
        assert churn["period_days"] == 30

    def test_get_trial_conversion_has_keys(self, app, db):
        from app.services.business_metrics import BusinessMetricsService
        conv = BusinessMetricsService.get_trial_conversion_rate(30)
        assert "conversion_rate" in conv
        assert "total_trials" in conv

    def test_get_active_organizations_has_keys(self, app, db):
        from app.services.business_metrics import BusinessMetricsService
        orgs = BusinessMetricsService.get_active_organizations()
        assert "total" in orgs
        assert "by_tier" in orgs

    def test_get_growth_rate_has_keys(self, app, db):
        from app.services.business_metrics import BusinessMetricsService
        growth = BusinessMetricsService.get_growth_rate(30)
        assert "user_growth_pct" in growth
        assert "revenue_growth_pct" in growth

    def test_get_all_metrics_has_all_keys(self, app, db):
        from app.services.business_metrics import BusinessMetricsService
        metrics = BusinessMetricsService.get_all_metrics()
        assert "mrr" in metrics
        assert "arr" in metrics
        assert "churn" in metrics
        assert "ltv" in metrics
        assert "trial_conversion" in metrics
        assert "active_organizations" in metrics
        assert "growth" in metrics
        assert "revenue_trend" in metrics
