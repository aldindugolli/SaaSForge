from datetime import UTC, datetime

import stripe
from flask import current_app

from app.core.extensions import cache_service, db
from app.core.models import (
    AuditLog,
    Invoice,
    Organization,
    PaymentEvent,
    PlanType,
    Subscription,
    SubscriptionStatus,
)
from app.services.base import NotFoundError, ServiceError, ValidationError


class BillingService:
    @staticmethod
    def _get_stripe():
        stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]
        return stripe

    @staticmethod
    def create_checkout_session(organization_id: str, price_id: str, success_url: str, cancel_url: str) -> str:
        stripe = BillingService._get_stripe()
        org = Organization.query.get(organization_id)
        if not org:
            raise NotFoundError("Organization not found.")

        try:
            checkout_session = stripe.checkout.Session.create(
                mode="subscription",
                line_items=[{"price": price_id, "quantity": 1}],
                client_reference_id=organization_id,
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={"organization_id": organization_id},
                customer_email=org.owner.email if not org.active_subscription or not org.active_subscription.stripe_customer_id else None,
            )
            return checkout_session.url
        except stripe.error.StripeError as e:
            raise ServiceError(f"Stripe error: {str(e)}")

    @staticmethod
    def create_customer_portal_session(organization_id: str, return_url: str) -> str:
        stripe = BillingService._get_stripe()
        org = Organization.query.get(organization_id)
        if not org:
            raise NotFoundError("Organization not found.")

        subscription = org.active_subscription
        if not subscription or not subscription.stripe_customer_id:
            raise ValidationError("No active subscription found.")

        try:
            session = stripe.billing_portal.Session.create(
                customer=subscription.stripe_customer_id,
                return_url=return_url,
            )
            return session.url
        except stripe.error.StripeError as e:
            raise ServiceError(f"Stripe error: {str(e)}")

    @staticmethod
    def handle_webhook(payload: bytes, sig_header: str) -> dict:
        stripe = BillingService._get_stripe()
        webhook_secret = current_app.config["STRIPE_WEBHOOK_SECRET"]

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except ValueError:
            raise ServiceError("Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise ServiceError("Invalid signature")

        handler = BillingService._get_webhook_handler(event.type)
        if handler:
            handler(event)

        # Store the event
        PaymentEvent(
            stripe_event_id=event.id,
            type=event.type,
            status="processed",
            data=event.data.object,
        )
        db.session.commit()

        return {"status": "success", "event": event.type}

    @staticmethod
    def _get_webhook_handler(event_type: str):
        handlers = {
            "checkout.session.completed": BillingService._handle_checkout_completed,
            "customer.subscription.created": BillingService._handle_subscription_created,
            "customer.subscription.updated": BillingService._handle_subscription_updated,
            "customer.subscription.deleted": BillingService._handle_subscription_deleted,
            "invoice.paid": BillingService._handle_invoice_paid,
            "invoice.payment_failed": BillingService._handle_invoice_payment_failed,
        }
        return handlers.get(event_type)

    @staticmethod
    def _handle_checkout_completed(event):
        session = event.data.object
        organization_id = session.get("client_reference_id") or session.metadata.get("organization_id")
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")

        if not organization_id:
            return

        org = Organization.query.get(organization_id)
        if not org:
            return

        # Get subscription details from Stripe
        stripe.Subscription.retrieve(subscription_id)

        sub = org.active_subscription
        if sub:
            sub.stripe_subscription_id = subscription_id
            sub.stripe_customer_id = customer_id
        else:
            sub = Subscription(
                organization_id=organization_id,
                stripe_subscription_id=subscription_id,
                stripe_customer_id=customer_id,
                plan=PlanType.PRO.value,
                status=SubscriptionStatus.ACTIVE.value,
                current_period_start=datetime.fromtimestamp(session.get("created", 0), tz=UTC),
            )
            db.session.add(sub)

        org.subscription_tier = PlanType.PRO.value
        org.max_members = 5

        AuditLog(
            action="billing.checkout_completed",
            organization_id=organization_id,
            resource_type="subscription",
            resource_id=sub.id,
        )

        cache_service.invalidate_analytics()
        cache_service.invalidate_org_data(str(organization_id))

    @staticmethod
    def _handle_subscription_created(event):
        pass  # Handled by checkout.completed

    @staticmethod
    def _handle_subscription_updated(event):
        sub_data = event.data.object
        sub = Subscription.query.filter_by(
            stripe_subscription_id=sub_data.get("id")
        ).first()
        if not sub:
            return

        sub.status = sub_data.get("status")
        if sub_data.get("current_period_start"):
            sub.current_period_start = datetime.fromtimestamp(sub_data["current_period_start"], tz=UTC)
        if sub_data.get("current_period_end"):
            sub.current_period_end = datetime.fromtimestamp(sub_data["current_period_end"], tz=UTC)

        sub.stripe_price_id = sub_data.get("items", {}).get("data", [{}])[0].get("price", {}).get("id") if sub_data.get("items", {}).get("data") else None

        # Update plan based on price
        price_id = sub.stripe_price_id
        if price_id == current_app.config.get("STRIPE_PRO_PRICE_ID"):
            sub.plan = PlanType.PRO.value
            sub.organization.max_members = 5
        elif price_id == current_app.config.get("STRIPE_BUSINESS_PRICE_ID"):
            sub.plan = PlanType.BUSINESS.value
            sub.organization.max_members = 100

        sub.organization.subscription_tier = sub.plan
        db.session.commit()
        cache_service.invalidate_analytics()
        cache_service.invalidate_org_data(str(sub.organization_id))

    @staticmethod
    def _handle_subscription_deleted(event):
        sub_data = event.data.object
        sub = Subscription.query.filter_by(
            stripe_subscription_id=sub_data.get("id")
        ).first()
        if not sub:
            return

        sub.status = SubscriptionStatus.CANCELED.value
        sub.canceled_at = datetime.now(UTC)
        sub.ended_at = datetime.fromtimestamp(sub_data.get("ended_at", 0), tz=UTC) if sub_data.get("ended_at") else datetime.now(UTC)

        sub.organization.subscription_tier = PlanType.FREE.value
        sub.organization.max_members = 1
        db.session.commit()
        cache_service.invalidate_analytics()
        cache_service.invalidate_org_data(str(sub.organization_id))

    @staticmethod
    def _handle_invoice_paid(event):
        invoice_data = event.data.object
        sub_id = invoice_data.get("subscription")

        sub = Subscription.query.filter_by(stripe_subscription_id=sub_id).first()
        if not sub:
            return

        invoice = Invoice(
            subscription_id=sub.id,
            organization_id=sub.organization_id,
            stripe_invoice_id=invoice_data.get("id"),
            amount_due=invoice_data.get("amount_due", 0),
            amount_paid=invoice_data.get("amount_paid", 0),
            currency=invoice_data.get("currency", "usd"),
            status=invoice_data.get("status", "paid"),
            description=invoice_data.get("description"),
            pdf_url=invoice_data.get("invoice_pdf"),
            paid_at=datetime.now(UTC),
        )
        db.session.add(invoice)

    @staticmethod
    def _handle_invoice_payment_failed(event):
        invoice_data = event.data.object
        sub_id = invoice_data.get("subscription")

        sub = Subscription.query.filter_by(stripe_subscription_id=sub_id).first()
        if not sub:
            return

        sub.status = SubscriptionStatus.PAST_DUE.value
        db.session.commit()

    @staticmethod
    def get_subscription_usage(organization_id: str) -> dict:
        org = Organization.query.get(organization_id)
        if not org:
            raise NotFoundError("Organization not found.")

        return {
            "members": {"used": org.member_count, "limit": org.max_members},
            "plan": org.plan,
            "status": org.subscription_status,
        }
