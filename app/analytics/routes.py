from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from app.services.analytics_service import AnalyticsService
from app.services.decorators import org_required

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/")
@login_required
@org_required
def index():
    stats = AnalyticsService.get_dashboard_stats()
    return render_template("analytics/index.html", stats=stats)


@analytics_bp.route("/data/user-growth")
@login_required
def user_growth_data():
    days = request.args.get("days", 30, type=int)
    data = AnalyticsService.get_user_growth(days)
    return jsonify(data)


@analytics_bp.route("/data/revenue")
@login_required
def revenue_data():
    days = request.args.get("days", 90, type=int)
    data = AnalyticsService.get_revenue_growth(days)
    return jsonify(data)


@analytics_bp.route("/data/subscriptions")
@login_required
def subscription_data():
    data = AnalyticsService.get_subscription_distribution()
    return jsonify(data)


@analytics_bp.route("/data/stats")
@login_required
def stats_data():
    data = AnalyticsService.get_dashboard_stats()
    return jsonify(data)
