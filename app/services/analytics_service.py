from datetime import UTC, datetime, timedelta

from sqlalchemy import func

from app.core.extensions import cache, db
from app.core.models import Invoice, Organization, PlanType, Subscription, SubscriptionStatus, User

_ANALYTICS_TTL = 300


class AnalyticsService:
    _cache_prefix = "analytics"

    @staticmethod
    def _cache_key(name: str, **params) -> str:
        if params:
            parts = [f"{k}={v}" for k, v in sorted(params.items())]
            return f"{name}:{':'.join(parts)}"
        return name

    @staticmethod
    def get_user_growth(days: int = 30) -> list:
        ck = AnalyticsService._cache_key("user_growth", days=days)
        cached = cache.get(AnalyticsService._cache_prefix, ck)
        if cached is not None:
            return cached
        from sqlalchemy import func
        start_date = datetime.now(UTC) - timedelta(days=days)
        results = (
            db.session.query(func.date(User.created_at).label("date"), func.count(User.id).label("count"))
            .filter(User.created_at >= start_date)
            .group_by(func.date(User.created_at))
            .order_by(func.date(User.created_at))
            .all()
        )
        val = [{"date": str(r.date), "count": r.count} for r in results]
        cache.set(AnalyticsService._cache_prefix, ck, val, _ANALYTICS_TTL)
        return val

    @staticmethod
    def get_revenue_growth(days: int = 90) -> list:
        ck = AnalyticsService._cache_key("revenue_growth", days=days)
        cached = cache.get(AnalyticsService._cache_prefix, ck)
        if cached is not None:
            return cached
        from sqlalchemy import func
        start_date = datetime.now(UTC) - timedelta(days=days)
        results = (
            db.session.query(
                func.date(Invoice.paid_at).label("date"),
                func.sum(Invoice.amount_paid).label("revenue"),
            )
            .filter(Invoice.paid_at >= start_date, Invoice.status == "paid")
            .group_by(func.date(Invoice.paid_at))
            .order_by(func.date(Invoice.paid_at))
            .all()
        )
        val = [{"date": str(r.date), "revenue": float(r.revenue or 0) / 100} for r in results]
        cache.set(AnalyticsService._cache_prefix, ck, val, _ANALYTICS_TTL)
        return val

    @staticmethod
    def get_subscription_distribution() -> dict:
        ck = "subscription_distribution"
        cached = cache.get(AnalyticsService._cache_prefix, ck)
        if cached is not None:
            return cached
        results = (
            db.session.query(
                Subscription.plan,
                func.count(Subscription.id).label("count"),
            )
            .filter(Subscription.status.in_(["active", "trialing"]))
            .group_by(Subscription.plan)
            .all()
        )
        distribution = {PlanType.FREE.value: 0, PlanType.PRO.value: 0, PlanType.BUSINESS.value: 0}
        for r in results:
            distribution[r.plan] = r.count
        cache.set(AnalyticsService._cache_prefix, ck, distribution, _ANALYTICS_TTL)
        return distribution

    @staticmethod
    def get_dashboard_stats() -> dict:
        ck = "dashboard_stats"
        cached = cache.get(AnalyticsService._cache_prefix, ck)
        if cached is not None:
            return cached
        now = datetime.now(UTC)
        thirty_days_ago = now - timedelta(days=30)

        total_users = User.query.count()
        active_users = User.query.filter(User.last_login_at >= thirty_days_ago).count()
        total_orgs = Organization.query.count()
        total_subscriptions = Subscription.query.filter(
            Subscription.status.in_(["active", "trialing"])
        ).count()

        total_revenue_result = db.session.query(
            func.coalesce(func.sum(Invoice.amount_paid), 0)
        ).filter(Invoice.status == "paid").scalar()
        total_revenue = float(total_revenue_result) / 100 if total_revenue_result else 0

        pro_count = Subscription.query.filter_by(plan=PlanType.PRO.value).filter(
            Subscription.status.in_(["active", "trialing"])
        ).count()
        business_count = Subscription.query.filter_by(plan=PlanType.BUSINESS.value).filter(
            Subscription.status.in_(["active", "trialing"])
        ).count()
        mrr = (pro_count * 29) + (business_count * 99)

        canceled_30d = Subscription.query.filter(
            Subscription.status == SubscriptionStatus.CANCELED.value,
            Subscription.canceled_at >= thirty_days_ago,
        ).count()
        churn_rate = round((canceled_30d / max(total_subscriptions, 1)) * 100, 2)

        users_30d_ago = User.query.filter(User.created_at < thirty_days_ago).count()
        user_growth = ((total_users - users_30d_ago) / max(users_30d_ago, 1)) * 100

        val = {
            "total_users": total_users,
            "active_users": active_users,
            "total_organizations": total_orgs,
            "total_subscriptions": total_subscriptions,
            "total_revenue": total_revenue,
            "mrr": mrr,
            "churn_rate": churn_rate,
            "user_growth": round(user_growth, 1),
            "pro_count": pro_count,
            "business_count": business_count,
            "free_count": total_subscriptions - pro_count - business_count,
        }
        cache.set(AnalyticsService._cache_prefix, ck, val, _ANALYTICS_TTL)
        return val

    @staticmethod
    def get_user_analytics(user_id: str) -> dict:
        ck = AnalyticsService._cache_key("user", user_id=user_id)
        cached = cache.get(AnalyticsService._cache_prefix, ck)
        if cached is not None:
            return cached
        user = User.query.get(user_id)
        if not user:
            return {}
        val = {
            "login_count": user.login_count,
            "last_login": user.last_login_at.isoformat() if user.last_login_at else None,
            "member_since": user.created_at.isoformat() if user.created_at else None,
            "email_verified": user.email_verified,
            "organizations_count:": len(user.organizations),
        }
        cache.set(AnalyticsService._cache_prefix, ck, val, _ANALYTICS_TTL)
        return val

    @staticmethod
    def get_trial_conversion_stats(days: int = 90) -> dict:
        ck = AnalyticsService._cache_key("trial_conversion", days=days)
        cached = cache.get(AnalyticsService._cache_prefix, ck)
        if cached is not None:
            return cached

        start_date = datetime.now(UTC) - timedelta(days=days)

        total_trials = db.session.query(func.count(Subscription.id)).filter(
            Subscription.status == SubscriptionStatus.TRIALING.value,
            Subscription.created_at >= start_date,
        ).scalar() or 0

        converted = db.session.query(func.count(Subscription.id)).filter(
            Subscription.plan.in_([PlanType.PRO.value, PlanType.BUSINESS.value]),
            Subscription.status == SubscriptionStatus.ACTIVE.value,
            Subscription.created_at >= start_date,
        ).scalar() or 0

        expired = db.session.query(func.count(Subscription.id)).filter(
            Subscription.status.in_([
                SubscriptionStatus.CANCELED.value,
                SubscriptionStatus.INCOMPLETE_EXPIRED.value,
            ]),
            Subscription.created_at >= start_date,
        ).scalar() or 0

        conversion_rate = round((converted / max(total_trials, 1)) * 100, 2)

        trend = (
            db.session.query(
                func.date(Subscription.created_at).label("date"),
                func.count(Subscription.id).label("count"),
            )
            .filter(
                Subscription.status == SubscriptionStatus.TRIALING.value,
                Subscription.created_at >= start_date,
            )
            .group_by(func.date(Subscription.created_at))
            .order_by(func.date(Subscription.created_at))
            .all()
        )

        val = {
            "total_trials": total_trials,
            "converted": converted,
            "expired": expired,
            "conversion_rate": conversion_rate,
            "trend": [{"date": str(r.date), "count": r.count} for r in trend],
        }

        cache.set(AnalyticsService._cache_prefix, ck, val, _ANALYTICS_TTL)
        return val

    @staticmethod
    def invalidate():
        cache.invalidate_pattern("analytics:*")
