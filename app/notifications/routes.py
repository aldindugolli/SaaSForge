from flask import Blueprint, jsonify, render_template
from flask_login import current_user, login_required

from app.services.notification_service import NotificationService

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("/")
@login_required
def index():
    notifications = NotificationService.get_user_notifications(current_user.id, limit=50)
    return render_template("notifications/index.html", notifications=notifications)


@notifications_bp.route("/unread-count")
@login_required
def unread_count():
    count = NotificationService.get_unread_count(current_user.id)
    return jsonify({"count": count})


@notifications_bp.route("/list")
@login_required
def list_notifications():
    notifications = NotificationService.get_user_notifications(current_user.id, limit=10)
    return render_template("components/notification_list.html", notifications=notifications)


@notifications_bp.route("/<notification_id>/read")
@login_required
def mark_read(notification_id):
    NotificationService.mark_as_read(notification_id, current_user.id)
    return "", 204


@notifications_bp.route("/read-all")
@login_required
def mark_all_read():
    NotificationService.mark_all_as_read(current_user.id)
    return "", 204
