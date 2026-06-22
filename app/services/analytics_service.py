from typing import Optional
from datetime import datetime, timezone, timedelta

from sqlalchemy import func
from app.core.extensions import db
from app.core.models import User, Organization, Subscription, Invoice, AuditLog, PlanType, SubscriptionStatus


class AnalyticsService:
    @staticmethod
    def get_user_growth(days: int = 30) -> list:
        from sqlalchemy import func
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        date_col = func.date(User.created_at).label("date")
        results = (
            db.session.query(date_col, func.count(User.id).label("count"))
            .filter(User.created_at >= start_date)
            .group_by(func.date(User.created_at))
            .order_by(func.date(User.created_at))
            .all()
        )
        return [{"date": str(r.date), "count": r.count} for r in results]

    @staticmethod
    def get_revenue_growth(days: int = 90) -> list:
        from sqlalchemy import func
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
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
        return [{"date": str(r.date), "revenue": float(r.revenue or 0) / 100} for r in results]

    @staticmethod
    def get_subscription_distribution() -> dict:
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
        return distribution

    @staticmethod
    def get_dashboard_stats() -> dict:
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)

        total_users = User.query.count()
        active_users = User.query.filter(User.last_login_at >= thirty_days_ago).count()
        total_orgs = Organization.query.count()
        total_subscriptions = Subscription.query.filter(
            Subscription.status.in_(["active", "trialing"])
        ).count()

        # Revenue
        total_revenue_result = db.session.query(
            func.coalesce(func.sum(Invoice.amount_paid), 0)
        ).filter(Invoice.status == "paid").scalar()
        total_revenue = float(total_revenue_result) / 100 if total_revenue_result else 0

        # MRR - Monthly Recurring Revenue
        mrr_result = db.session.query(
            func.coalesce(func.sum(Subscription.quantity * 0), 0)
        ).filter(
            Subscription.status.in_(["active", "trialing"])
        ).scalar()

        # Approximate MRR based on plans
        pro_count = Subscription.query.filter_by(plan=PlanType.PRO.value).filter(
            Subscription.status.in_(["active", "trialing"])
        ).count()
        business_count = Subscription.query.filter_by(plan=PlanType.BUSINESS.value).filter(
            Subscription.status.in_(["active", "trialing"])
        ).count()
        mrr = (pro_count * 29) + (business_count * 99)

        # Churn rate (last 30 days)
        canceled_30d = Subscription.query.filter(
            Subscription.status == SubscriptionStatus.CANCELED.value,
            Subscription.canceled_at >= thirty_days_ago,
        ).count()
        churn_rate = round((canceled_30d / max(total_subscriptions, 1)) * 100, 2)

        # Growth
        users_30d_ago = User.query.filter(User.created_at < thirty_days_ago).count()
        user_growth = ((total_users - users_30d_ago) / max(users_30d_ago, 1)) * 100

        return {
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

    @staticmethod
    def get_user_analytics(user_id: str) -> dict:
        user = User.query.get(user_id)
        if not user:
            return {}

        return {
            "login_count": user.login_count,
            "last_login": user.last_login_at.isoformat() if user.last_login_at else None,
            "member_since": user.created_at.isoformat() if user.created_at else None,
            "email_verified": user.email_verified,
            "organizations_count:": len(user.organizations),
        }
