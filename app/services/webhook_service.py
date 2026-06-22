"""Webhook delivery system: reliable Stripe webhooks + customer-facing webhooks."""

import hashlib
import hmac
import json
import logging
import time
import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

import requests
from flask import current_app
from sqlalchemy import func

from app.core.extensions import db
from app.core.models import PaymentEvent

logger = logging.getLogger(__name__)


# ─── Webhook Status Enums ──────────────────────────────────────────────────────

class WebhookStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class WebhookDeliveryStatus(StrEnum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


# ─── Customer Webhook Endpoint Model ───────────────────────────────────────────

class CustomerWebhookEndpoint(db.Model):
    """A webhook endpoint registered by a customer to receive events."""

    __tablename__ = "customer_webhook_endpoints"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=False)
    url = db.Column(db.String(1024), nullable=False)
    secret = db.Column(db.String(128), nullable=False)
    events = db.Column(db.JSON, nullable=False, default=list)  # List of event types subscribed to
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    last_delivered_at = db.Column(db.DateTime, nullable=True)
    last_success_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC),
                           onupdate=lambda: datetime.now(UTC))

    organization = db.relationship("Organization", backref="webhook_endpoints")
    deliveries = db.relationship("WebhookDelivery", back_populates="endpoint",
                                 lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CustomerWebhookEndpoint {self.url} ({'active' if self.is_active else 'inactive'})>"


class WebhookDelivery(db.Model):
    """A delivery attempt for a customer webhook."""

    __tablename__ = "webhook_deliveries"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    endpoint_id = db.Column(db.String(36), db.ForeignKey("customer_webhook_endpoints.id"), nullable=False)
    event_type = db.Column(db.String(100), nullable=False)
    payload = db.Column(db.JSON, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=WebhookDeliveryStatus.PENDING.value)
    status_code = db.Column(db.Integer, nullable=True)
    response_body = db.Column(db.Text, nullable=True)
    attempt_count = db.Column(db.Integer, default=1, nullable=False)
    max_attempts = db.Column(db.Integer, default=5, nullable=False)
    next_retry_at = db.Column(db.DateTime, nullable=True)
    signature = db.Column(db.String(256), nullable=True)
    duration_ms = db.Column(db.Integer, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC),
                           onupdate=lambda: datetime.now(UTC))

    endpoint = db.relationship("CustomerWebhookEndpoint", back_populates="deliveries")

    __table_args__ = (
        db.Index("idx_webhook_deliveries_status", "status"),
        db.Index("idx_webhook_deliveries_next_retry", "next_retry_at"),
    )

    def __repr__(self):
        return f"<WebhookDelivery {self.event_type} ({self.status})>"


# ─── Webhook Event Log (for internal Stripe processing) ────────────────────────

class WebhookEventLog(db.Model):
    """Idempotent processing log for incoming Stripe webhooks."""

    __tablename__ = "webhook_event_logs"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    stripe_event_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    event_type = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=WebhookStatus.PENDING.value)
    attempt_count = db.Column(db.Integer, default=0, nullable=False)
    max_attempts = db.Column(db.Integer, default=3, nullable=False)
    last_error = db.Column(db.Text, nullable=True)
    processed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC),
                           onupdate=lambda: datetime.now(UTC))

    __table_args__ = (
        db.Index("idx_webhook_event_logs_status", "status"),
    )

    def __repr__(self):
        return f"<WebhookEventLog {self.event_type} ({self.status})>"


# ─── Stripe Webhook Processing Pipeline ────────────────────────────────────────

class StripeWebhookProcessor:
    """Reliable Stripe webhook processing with idempotency and retries."""

    @staticmethod
    def process_event(event_id: str, event_type: str, event_data: dict) -> dict:
        """Process a Stripe webhook event with idempotency guarantee."""
        # Check if already processed
        existing = WebhookEventLog.query.filter_by(stripe_event_id=event_id).first()
        if existing:
            if existing.status == WebhookStatus.COMPLETED.value:
                logger.info(f"Webhook {event_id} already processed, skipping")
                return {"status": "already_processed", "event": event_type}
            if existing.status == WebhookStatus.PROCESSING.value:
                logger.warning(f"Webhook {event_id} is currently processing")
                return {"status": "in_progress", "event": event_type}

        # Create or update processing log
        event_log = existing or WebhookEventLog(
            stripe_event_id=event_id,
            event_type=event_type,
        )
        event_log.status = WebhookStatus.PROCESSING.value
        event_log.attempt_count = (event_log.attempt_count or 0) + 1
        db.session.add(event_log)
        db.session.commit()

        try:
            # Process the event
            from app.services.billing_service import BillingService
            result = BillingService.handle_webhook_event(event_type, event_data)

            event_log.status = WebhookStatus.COMPLETED.value
            event_log.processed_at = datetime.now(UTC)
            db.session.commit()

            logger.info(f"Webhook {event_id} ({event_type}) processed successfully")
            return {"status": "completed", "event": event_type}

        except Exception as e:
            logger.error(f"Webhook {event_id} ({event_type}) failed: {e}")
            event_log.last_error = str(e)
            event_log.status = WebhookStatus.FAILED.value

            if event_log.attempt_count >= event_log.max_attempts:
                event_log.status = WebhookStatus.DEAD_LETTER.value
                logger.error(f"Webhook {event_id} moved to dead-letter queue")

            db.session.commit()
            raise

    @staticmethod
    def retry_failed_events(max_retries: int = 3) -> list[dict]:
        """Retry failed webhook events that haven't exceeded max attempts."""
        retried = []
        failed = WebhookEventLog.query.filter(
            WebhookEventLog.status.in_([WebhookStatus.FAILED.value]),
            WebhookEventLog.attempt_count < max_retries,
        ).all()

        for event_log in failed:
            try:
                # Re-fetch event data from PaymentEvent store
                payment_event = PaymentEvent.query.filter_by(
                    stripe_event_id=event_log.stripe_event_id
                ).first()
                if payment_event and payment_event.data:
                    StripeWebhookProcessor.process_event(
                        event_log.stripe_event_id,
                        event_log.event_type,
                        payment_event.data,
                    )
                    retried.append({"event_id": event_log.stripe_event_id, "status": "retried"})
            except Exception as e:
                retried.append({"event_id": event_log.stripe_event_id, "status": "failed", "error": str(e)})

        return retried

    @staticmethod
    def get_event_stats() -> dict:
        """Get webhook processing statistics."""
        total = WebhookEventLog.query.count()
        by_status = (
            db.session.query(
                WebhookEventLog.status,
                func.count(WebhookEventLog.id).label("count"),
            )
            .group_by(WebhookEventLog.status)
            .all()
        )

        dead_letter = WebhookEventLog.query.filter_by(
            status=WebhookStatus.DEAD_LETTER.value
        ).order_by(WebhookEventLog.updated_at.desc()).limit(20).all()

        return {
            "total": total,
            "by_status": {s.status: s.count for s in by_status},
            "dead_letter": [
                {"id": e.stripe_event_id, "type": e.event_type, "error": e.last_error,
                 "attempts": e.attempt_count, "updated_at": e.updated_at.isoformat() if e.updated_at else None}
                for e in dead_letter
            ],
        }


# ─── Customer Webhook Delivery ─────────────────────────────────────────────────

class CustomerWebhookService:
    """Deliver webhook events to customer-registered endpoints."""

    EVENT_TYPES = [
        "organization.created",
        "organization.updated",
        "member.invited",
        "member.removed",
        "member.role_changed",
        "subscription.created",
        "subscription.updated",
        "subscription.cancelled",
        "subscription.trial_ending",
        "invoice.paid",
        "invoice.payment_failed",
        "api_key.created",
        "api_key.revoked",
        "notification.created",
        "user.2fa_enabled",
        "user.2fa_disabled",
        "session.revoked",
    ]

    @staticmethod
    def register_endpoint(organization_id: str, url: str, events: list[str],
                          description: str | None = None) -> CustomerWebhookEndpoint:
        """Register a new webhook endpoint for a customer."""
        import secrets
        secret = secrets.token_hex(32)

        endpoint = CustomerWebhookEndpoint(
            organization_id=organization_id,
            url=url,
            secret=secret,
            events=events,
            description=description,
        )
        db.session.add(endpoint)
        db.session.commit()
        logger.info(f"Registered webhook endpoint for org {organization_id}: {url}")
        return endpoint

    @staticmethod
    def update_endpoint(endpoint_id: str, organization_id: str,
                        **kwargs) -> CustomerWebhookEndpoint | None:
        """Update a webhook endpoint."""
        endpoint = CustomerWebhookEndpoint.query.filter_by(
            id=endpoint_id, organization_id=organization_id
        ).first()
        if not endpoint:
            return None

        for key, value in kwargs.items():
            if hasattr(endpoint, key) and value is not None:
                setattr(endpoint, key, value)
        db.session.commit()
        return endpoint

    @staticmethod
    def delete_endpoint(endpoint_id: str, organization_id: str) -> bool:
        """Delete a webhook endpoint."""
        endpoint = CustomerWebhookEndpoint.query.filter_by(
            id=endpoint_id, organization_id=organization_id
        ).first()
        if not endpoint:
            return False
        db.session.delete(endpoint)
        db.session.commit()
        return True

    @staticmethod
    def get_endpoints(organization_id: str) -> list[CustomerWebhookEndpoint]:
        """Get all webhook endpoints for an organization."""
        return CustomerWebhookEndpoint.query.filter_by(
            organization_id=organization_id
        ).order_by(CustomerWebhookEndpoint.created_at.desc()).all()

    @staticmethod
    def get_delivery_history(endpoint_id: str, organization_id: str,
                             limit: int = 50) -> list[WebhookDelivery]:
        """Get delivery history for a webhook endpoint."""
        return (
            WebhookDelivery.query
            .join(CustomerWebhookEndpoint)
            .filter(
                CustomerWebhookEndpoint.id == endpoint_id,
                CustomerWebhookEndpoint.organization_id == organization_id,
            )
            .order_by(WebhookDelivery.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def _sign_payload(payload: dict, secret: str) -> str:
        """Create HMAC-SHA256 signature for webhook payload."""
        body = json.dumps(payload, sort_keys=True, default=str).encode()
        return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    @staticmethod
    def deliver_event(event_type: str, payload: dict, organization_id: str) -> list[dict]:
        """Deliver an event to all subscribed endpoints for an organization."""
        results = []
        endpoints = CustomerWebhookEndpoint.query.filter_by(
            organization_id=organization_id,
            is_active=True,
        ).all()

        for endpoint in endpoints:
            if event_type not in endpoint.events and "*" not in endpoint.events:
                continue

            delivery = WebhookDelivery(
                endpoint_id=endpoint.id,
                event_type=event_type,
                payload=payload,
                status=WebhookDeliveryStatus.PENDING.value,
            )
            db.session.add(delivery)
            db.session.commit()

            result = CustomerWebhookService._attempt_delivery(delivery, endpoint)
            results.append(result)

        return results

    @staticmethod
    def _attempt_delivery(delivery: WebhookDelivery,
                          endpoint: CustomerWebhookEndpoint) -> dict:
        """Attempt to deliver a webhook to a single endpoint."""
        import json
        payload = {
            "event": delivery.event_type,
            "id": delivery.id,
            "created_at": datetime.now(UTC).isoformat(),
            "data": delivery.payload,
        }

        signature = CustomerWebhookService._sign_payload(payload, endpoint.secret)
        body = json.dumps(payload, default=str)
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": f"sha256={signature}",
            "X-Webhook-Event": delivery.event_type,
            "X-Webhook-Delivery-ID": delivery.id,
        }

        start = time.time()
        try:
            resp = requests.post(
                endpoint.url,
                data=body,
                headers=headers,
                timeout=30,
            )
            duration = int((time.time() - start) * 1000)

            delivery.status_code = resp.status_code
            delivery.response_body = resp.text[:1000]
            delivery.duration_ms = duration
            delivery.signature = signature

            if 200 <= resp.status_code < 300:
                delivery.status = WebhookDeliveryStatus.DELIVERED.value
                endpoint.last_delivered_at = datetime.now(UTC)
                endpoint.last_success_at = datetime.now(UTC)
                db.session.commit()
                return {"delivery_id": delivery.id, "status": "delivered"}

            delivery.status = WebhookDeliveryStatus.FAILED.value
            delivery.error_message = f"HTTP {resp.status_code}"
            db.session.commit()
            return {"delivery_id": delivery.id, "status": "failed", "code": resp.status_code}

        except requests.RequestException as e:
            duration = int((time.time() - start) * 1000)
            delivery.status = WebhookDeliveryStatus.FAILED.value
            delivery.error_message = str(e)
            delivery.duration_ms = duration
            db.session.commit()
            return {"delivery_id": delivery.id, "status": "failed", "error": str(e)}

    @staticmethod
    def retry_delivery(delivery_id: str, organization_id: str) -> dict:
        """Retry a failed delivery."""
        delivery = (
            WebhookDelivery.query
            .join(CustomerWebhookEndpoint)
            .filter(
                WebhookDelivery.id == delivery_id,
                CustomerWebhookEndpoint.organization_id == organization_id,
            )
            .first()
        )
        if not delivery:
            return {"status": "not_found"}

        if delivery.status == WebhookDeliveryStatus.DELIVERED.value:
            return {"status": "already_delivered"}

        endpoint = CustomerWebhookEndpoint.query.get(delivery.endpoint_id)
        if not endpoint or not endpoint.is_active:
            return {"status": "endpoint_inactive"}

        delivery.attempt_count += 1
        delivery.status = WebhookDeliveryStatus.PENDING.value
        delivery.error_message = None
        db.session.commit()

        return CustomerWebhookService._attempt_delivery(delivery, endpoint)

    @staticmethod
    def test_endpoint(endpoint_id: str, organization_id: str) -> dict:
        """Send a test event to a webhook endpoint."""
        endpoint = CustomerWebhookEndpoint.query.filter_by(
            id=endpoint_id, organization_id=organization_id
        ).first()
        if not endpoint:
            return {"status": "not_found"}

        test_payload = {
            "test": True,
            "message": "This is a test webhook from SaaSForge",
            "timestamp": datetime.now(UTC).isoformat(),
        }

        delivery = WebhookDelivery(
            endpoint_id=endpoint.id,
            event_type="test.ping",
            payload=test_payload,
            status=WebhookDeliveryStatus.PENDING.value,
        )
        db.session.add(delivery)
        db.session.commit()

        return CustomerWebhookService._attempt_delivery(delivery, endpoint)
