"""Webhook management routes for customers to manage their webhook endpoints."""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.services.decorators import org_required
from app.services.webhook_service import CustomerWebhookService, WebhookDeliveryStatus

webhooks_bp = Blueprint("webhooks", __name__, template_folder="../templates/webhooks")


@webhooks_bp.route("/")
@login_required
@org_required
def index():
    org = current_user.current_organization
    endpoints = CustomerWebhookService.get_endpoints(org.id)
    return render_template("webhooks/index.html", endpoints=endpoints,
                           event_types=CustomerWebhookService.EVENT_TYPES)


@webhooks_bp.route("/create", methods=["POST"])
@login_required
@org_required
def create():
    org = current_user.current_organization
    url = request.form.get("url", "").strip()
    events = request.form.getlist("events")
    description = request.form.get("description", "").strip()

    if not url:
        flash("Webhook URL is required.", "error")
        return redirect(url_for("webhooks.index"))
    if not events:
        flash("Select at least one event type.", "error")
        return redirect(url_for("webhooks.index"))

    endpoint = CustomerWebhookService.register_endpoint(
        organization_id=org.id,
        url=url,
        events=events,
        description=description or None,
    )

    flash(f"Webhook endpoint created. Secret: {endpoint.secret}", "success")
    return redirect(url_for("webhooks.index"))


@webhooks_bp.route("/<endpoint_id>/update", methods=["POST"])
@login_required
@org_required
def update(endpoint_id):
    org = current_user.current_organization
    url = request.form.get("url", "").strip()
    events = request.form.getlist("events")
    description = request.form.get("description", "").strip()

    endpoint = CustomerWebhookService.update_endpoint(
        endpoint_id=endpoint_id,
        organization_id=org.id,
        url=url or None,
        events=events or None,
        description=description or None,
    )

    if not endpoint:
        flash("Endpoint not found.", "error")
    else:
        flash("Webhook endpoint updated.", "success")

    return redirect(url_for("webhooks.index"))


@webhooks_bp.route("/<endpoint_id>/toggle", methods=["POST"])
@login_required
@org_required
def toggle(endpoint_id):
    org = current_user.current_organization
    endpoint = CustomerWebhookService.update_endpoint(
        endpoint_id=endpoint_id,
        organization_id=org.id,
        is_active=not request.form.get("is_active", "false") == "true",
    )
    if endpoint:
        flash(f"Endpoint {'activated' if endpoint.is_active else 'deactivated'}.", "success")
    return redirect(url_for("webhooks.index"))


@webhooks_bp.route("/<endpoint_id>/delete", methods=["POST"])
@login_required
@org_required
def delete(endpoint_id):
    org = current_user.current_organization
    if CustomerWebhookService.delete_endpoint(endpoint_id, org.id):
        flash("Webhook endpoint deleted.", "success")
    else:
        flash("Endpoint not found.", "error")
    return redirect(url_for("webhooks.index"))


@webhooks_bp.route("/<endpoint_id>/test", methods=["POST"])
@login_required
@org_required
def test(endpoint_id):
    org = current_user.current_organization
    result = CustomerWebhookService.test_endpoint(endpoint_id, org.id)
    if result["status"] == "not_found":
        flash("Endpoint not found.", "error")
    elif result["status"] == "delivered":
        flash("Test webhook delivered successfully!", "success")
    else:
        flash(f"Test webhook failed: {result.get('error', 'unknown error')}", "error")
    return redirect(url_for("webhooks.delivery_history", endpoint_id=endpoint_id))


@webhooks_bp.route("/<endpoint_id>/deliveries")
@login_required
@org_required
def delivery_history(endpoint_id):
    org = current_user.current_organization
    endpoint = CustomerWebhookService.get_endpoints(org.id)
    endpoint_obj = next((e for e in endpoint if e.id == endpoint_id), None)

    if not endpoint_obj:
        flash("Endpoint not found.", "error")
        return redirect(url_for("webhooks.index"))

    deliveries = CustomerWebhookService.get_delivery_history(endpoint_id, org.id)
    return render_template("webhooks/deliveries.html",
                           endpoint=endpoint_obj, deliveries=deliveries,
                           WebhookDeliveryStatus=WebhookDeliveryStatus)


@webhooks_bp.route("/deliveries/<delivery_id>/retry", methods=["POST"])
@login_required
@org_required
def retry_delivery(delivery_id):
    org = current_user.current_organization
    result = CustomerWebhookService.retry_delivery(delivery_id, org.id)
    if result["status"] == "not_found":
        flash("Delivery not found.", "error")
    elif result["status"] == "already_delivered":
        flash("Already delivered.", "info")
    elif result["status"] == "delivered":
        flash("Delivery retry succeeded!", "success")
    else:
        flash(f"Retry failed: {result.get('error', 'unknown')}", "error")
    return redirect(request.referrer or url_for("webhooks.index"))
