"""Executive SaaS metrics: MRR, ARR, Churn, LTV, Trial Conversion, Growth Rate."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func

from app.core.extensions import db
from app.core.models import Invoice, Organization, Subscription, SubscriptionStatus, User


class BusinessMetricsService:
    """Enterprise SaaS business intelligence metrics."""

    @staticmethod
    def get_mrr() -> float:
        """Calculate Monthly Recurring Revenue."""
        pro_count = Subscription.query.filter(
            Subscription.plan == "pro",
            Subscription.status.in_(["active", "trialing"]),
        ).count()
        business_count = Subscription.query.filter(
            Subscription.plan == "business",
            Subscription.status.in_(["active", "trialing"]),
        ).count()
        return float((pro_count * 29) + (business_count * 99))

    @staticmethod
    def get_arr() -> float:
        """Calculate Annual Recurring Revenue (MRR × 12)."""
        return BusinessMetricsService.get_mrr() * 12

    @staticmethod
    def get_churn_rate(days: int = 30) -> dict:
        """Calculate churn rate over a period."""
        now = datetime.now(UTC)
        period_start = now - timedelta(days=days)

        # Subscriptions at start of period
        subs_before = Subscription.query.filter(
            Subscription.created_at < period_start,
            Subscription.status.in_(["active", "trialing", "past_due"]),
        ).count()

        # Canceled during period
        canceled = Subscription.query.filter(
            Subscription.status == SubscriptionStatus.CANCELED.value,
            Subscription.canceled_at >= period_start,
            Subscription.canceled_at <= now,
        ).count()

        # New subscriptions during period
        new_subs = Subscription.query.filter(
            Subscription.created_at >= period_start,
            Subscription.created_at <= now,
            Subscription.status.in_(["active", "trialing"]),
        ).count()

        denominator = subs_before + new_subs
        churn_rate = round((canceled / max(denominator, 1)) * 100, 2)

        # Net retention rate
        net_retention = round(
            ((denominator - canceled) / max(denominator, 1)) * 100, 2
        ) if denominator > 0 else 100.0

        return {
            "period_days": days,
            "subscribers_start": subs_before,
            "new_subscribers": new_subs,
            "canceled": canceled,
            "churn_rate": churn_rate,
            "net_retention_rate": net_retention,
        }

    @staticmethod
    def get_ltv() -> float:
        """Calculate Customer Lifetime Value (average)."""
        # Average monthly revenue per customer
        mrr = BusinessMetricsService.get_mrr()
        total_active = max(
            Subscription.query.filter(
                Subscription.status.in_(["active", "trialing"])
            ).count(), 1
        )
        avg_revenue_per_customer = mrr / total_active if mrr > 0 else 0

        # Average customer lifespan (months) = 1 / churn_rate
        churn = BusinessMetricsService.get_churn_rate(90)
        churn_rate_decimal = max(churn["churn_rate"] / 100, 0.01)
        avg_lifespan_months = 1 / churn_rate_decimal

        ltv = avg_revenue_per_customer * avg_lifespan_months
        return round(ltv, 2)

    @staticmethod
    def get_trial_conversion_rate(days: int = 90) -> dict:
        """Calculate trial-to-paid conversion rate."""
        now = datetime.now(UTC)
        start_date = now - timedelta(days=days)

        total_trials = Subscription.query.filter(
            Subscription.status == SubscriptionStatus.TRIALING.value,
            Subscription.created_at >= start_date,
        ).count()

        # Trials that converted to paid
        converted = Subscription.query.filter(
            Subscription.plan.in_(["pro", "business"]),
            Subscription.status == SubscriptionStatus.ACTIVE.value,
            Subscription.created_at >= start_date,
        ).count()

        # Trials that expired without converting
        expired = Subscription.query.filter(
            Subscription.status.in_([
                SubscriptionStatus.CANCELED.value,
                SubscriptionStatus.INCOMPLETE_EXPIRED.value,
                SubscriptionStatus.UNPAID.value,
            ]),
            Subscription.created_at >= start_date,
        ).count()

        still_trialing = max(total_trials - converted - expired, 0)

        return {
            "total_trials": total_trials,
            "converted": converted,
            "expired": expired,
            "still_trialing": still_trialing,
            "conversion_rate": round((converted / max(total_trials, 1)) * 100, 2),
            "expired_rate": round((expired / max(total_trials, 1)) * 100, 2),
        }

    @staticmethod
    def get_active_organizations() -> dict:
        """Get active organization metrics."""
        total = Organization.query.count()

        by_tier = (
            db.session.query(
                Organization.subscription_tier,
                func.count(Organization.id).label("count"),
            )
            .group_by(Organization.subscription_tier)
            .all()
        )

        new_this_month = Organization.query.filter(
            Organization.created_at >= datetime.now(UTC).replace(day=1)
        ).count()

        return {
            "total": total,
            "by_tier": {tier: count for tier, count in by_tier},
            "new_this_month": new_this_month,
        }

    @staticmethod
    def get_growth_rate(days: int = 30) -> dict:
        """Calculate user and revenue growth rates."""
        now = datetime.now(UTC)
        period_start = now - timedelta(days=days)
        prior_period_start = now - timedelta(days=days * 2)

        # User growth
        users_current = User.query.filter(
            User.created_at >= period_start
        ).count()
        users_prior = User.query.filter(
            User.created_at >= prior_period_start,
            User.created_at < period_start,
        ).count()
        user_growth = ((users_current - users_prior) / max(users_prior, 1)) * 100

        # Revenue growth
        revenue_current = db.session.query(
            func.coalesce(func.sum(Invoice.amount_paid), 0)
        ).filter(
            Invoice.status == "paid",
            Invoice.paid_at >= period_start,
        ).scalar() or 0

        revenue_prior = db.session.query(
            func.coalesce(func.sum(Invoice.amount_paid), 0)
        ).filter(
            Invoice.status == "paid",
            Invoice.paid_at >= prior_period_start,
            Invoice.paid_at < period_start,
        ).scalar() or 0

        revenue_growth = ((revenue_current - revenue_prior) / max(revenue_prior, 1)) * 100

        return {
            "period_days": days,
            "users_current": users_current,
            "users_prior": users_prior,
            "user_growth_pct": round(user_growth, 1),
            "revenue_current_cents": revenue_current,
            "revenue_prior_cents": revenue_prior,
            "revenue_growth_pct": round(revenue_growth, 1),
        }

    @staticmethod
    def get_revenue_trend(days: int = 180) -> list[dict]:
        """Get monthly revenue trend."""
        now = datetime.now(UTC)
        start_date = now - timedelta(days=days)

        try:
            results = (
                db.session.query(
                    func.date_trunc("month", Invoice.paid_at).label("month"),
                    func.count(Invoice.id).label("invoice_count"),
                    func.sum(Invoice.amount_paid).label("revenue_cents"),
                    func.count(func.distinct(Invoice.organization_id)).label("paying_orgs"),
                )
                .filter(
                    Invoice.status == "paid",
                    Invoice.paid_at >= start_date,
                )
                .group_by(func.date_trunc("month", Invoice.paid_at))
                .order_by(func.date_trunc("month", Invoice.paid_at))
                .all()
            )
            return [
                {
                    "month": str(r.month),
                    "invoices": r.invoice_count,
                    "revenue": float(r.revenue_cents or 0) / 100,
                    "paying_organizations": r.paying_orgs,
                }
                for r in results
            ]
        except Exception:
            return []

    @staticmethod
    def get_all_metrics() -> dict:
        """Get all business metrics in a single call."""
        mrr = BusinessMetricsService.get_mrr()
        churn = BusinessMetricsService.get_churn_rate(30)
        conversion = BusinessMetricsService.get_trial_conversion_rate(90)

        return {
            "mrr": mrr,
            "arr": mrr * 12,
            "churn": churn,
            "ltv": BusinessMetricsService.get_ltv(),
            "trial_conversion": conversion,
            "active_organizations": BusinessMetricsService.get_active_organizations(),
            "growth": BusinessMetricsService.get_growth_rate(30),
            "revenue_trend": BusinessMetricsService.get_revenue_trend(180),
        }
