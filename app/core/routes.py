from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user

from app.core.extensions import db
from app.services.auth_service import AuthService
from app.services.base import ValidationError

core_bp = Blueprint("core", __name__)


@core_bp.route("/")
def index():
    if current_user.is_authenticated:
        org = current_user.current_organization
        if org:
            return redirect(url_for("core.dashboard"))
        return redirect(url_for("organizations.create"))
    return render_template("landing.html")


@core_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@core_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        company = request.form.get("company", "").strip()
        location = request.form.get("location", "").strip()
        bio = request.form.get("bio", "").strip()
        website = request.form.get("website", "").strip()

        if name:
            current_user.name = name
        current_user.company = company
        current_user.location = location
        current_user.bio = bio
        current_user.website = website
        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("core.settings"))

    return render_template("settings.html")


@core_bp.route("/auth/change-password", methods=["POST"])
@login_required
def change_password():
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if new_password != confirm_password:
        flash("Passwords do not match.", "error")
        return redirect(url_for("core.settings"))

    try:
        AuthService.change_password(current_user, current_password, new_password)
        flash("Password changed successfully.", "success")
    except ValidationError as e:
        flash(e.message, "error")

    return redirect(url_for("core.settings"))
