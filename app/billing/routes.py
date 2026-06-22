from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user

from app.core.models import Organization, Subscription, Invoice, PaymentEvent
from app.services.billing_service import BillingService
from app.services.base import ServiceError, ValidationError, NotFoundError

billing_bp = Blueprint("billing", __name__)


@billing_bp.route("/")
@login_required
def index():
    org = current_user.current_organization
    if not org:
        flash("Please create or select an organization first.", "error")
        return redirect(url_for("organizations.create"))

    subscription = org.active_subscription
    invoices = Invoice.query.filter_by(organization_id=org.id).order_by(Invoice.created_at.desc()).limit(12).all()

    return render_template(
        "billing/index.html",
        org=org,
        subscription=subscription,
        invoices=invoices,
        plans=current_app.config["STRIPE_PLANS"],
    )


@billing_bp.route("/create-checkout-session/<price_id>", methods=["POST"])
@login_required
def create_checkout_session(price_id):
    org = current_user.current_organization
    if not org:
        flash("No organization selected.", "error")
        return redirect(url_for("billing.index"))

    success_url = url_for("billing.success", _external=True)
    cancel_url = url_for("billing.index", _external=True)

    try:
        checkout_url = BillingService.create_checkout_session(
            org.id, price_id, success_url, cancel_url
        )
        return redirect(checkout_url)
    except (ServiceError, ValidationError) as e:
        flash(e.message, "error")
        return redirect(url_for("billing.index"))


@billing_bp.route("/success")
@login_required
def success():
    flash("Subscription setup complete! Welcome aboard.", "success")
    return redirect(url_for("billing.index"))


@billing_bp.route("/customer-portal")
@login_required
def customer_portal():
    org = current_user.current_organization
    if not org:
        flash("No organization selected.", "error")
        return redirect(url_for("billing.index"))

    return_url = url_for("billing.index", _external=True)

    try:
        portal_url = BillingService.create_customer_portal_session(org.id, return_url)
        return redirect(portal_url)
    except (ServiceError, ValidationError, NotFoundError) as e:
        flash(e.message, "error")
        return redirect(url_for("billing.index"))


@billing_bp.route("/webhook", methods=["POST"])
def webhook():
    import stripe
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature")

    if not sig_header:
        return {"error": "Missing signature"}, 400

    try:
        result = BillingService.handle_webhook(payload, sig_header)
        return result, 200
    except ServiceError as e:
        current_app.logger.error(f"Webhook error: {e.message}")
        return {"error": e.message}, 400


@billing_bp.route("/history")
@login_required
def history():
    org = current_user.current_organization
    if not org:
        flash("No organization selected.", "error")
        return redirect(url_for("billing.index"))

    invoices = Invoice.query.filter_by(organization_id=org.id).order_by(Invoice.created_at.desc()).all()
    events = PaymentEvent.query.filter_by(organization_id=org.id).order_by(PaymentEvent.created_at.desc()).limit(50).all()

    return render_template("billing/history.html", invoices=invoices, events=events, org=org)
