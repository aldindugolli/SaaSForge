from datetime import UTC

import click
from flask.cli import with_appcontext

from app.core.extensions import db
from app.core.models import (
    FeatureFlag,
    Membership,
    Organization,
    PlanType,
    Role,
    Subscription,
    SubscriptionStatus,
    User,
)


@click.command("seed-data")
@with_appcontext
def seed_data():
    """Seed the database with example data."""
    from datetime import datetime as dt
    from datetime import timedelta

    # Check if data already exists
    if User.query.first():
        click.echo("Data already exists. Skipping seed.")
        return

    # Create admin user
    admin = User(
        id="admin-001",
        email="admin@saasforge.com",
        name="Admin User",
        email_verified=True,
        is_admin=True,
        is_active=True,
    )
    admin.set_password("Admin123!")
    db.session.add(admin)

    # Create demo user
    demo = User(
        id="demo-001",
        email="demo@saasforge.com",
        name="Demo User",
        email_verified=True,
        is_active=True,
    )
    demo.set_password("Demo123!")
    db.session.add(demo)

    db.session.flush()

    # Create organizations
    admin_org = Organization(
        id="org-admin",
        name="SaaSForge Admin",
        slug="saasforge-admin",
        owner_id=admin.id,
        subscription_tier=PlanType.BUSINESS.value,
        max_members=100,
    )

    demo_org = Organization(
        id="org-demo",
        name="Demo Company",
        slug="demo-company",
        owner_id=demo.id,
        subscription_tier=PlanType.PRO.value,
        max_members=5,
    )
    db.session.add_all([admin_org, demo_org])
    db.session.flush()

    # Create memberships
    db.session.add(Membership(id="mem-admin", user_id=admin.id, organization_id=admin_org.id, role=Role.OWNER.value, is_current=True))
    db.session.add(Membership(id="mem-demo", user_id=demo.id, organization_id=demo_org.id, role=Role.OWNER.value, is_current=True))
    db.session.flush()

    # Create subscriptions
    db.session.add(Subscription(
        organization_id=admin_org.id,
        plan=PlanType.BUSINESS.value,
        status=SubscriptionStatus.ACTIVE.value,
        current_period_start=dt.now(UTC),
        current_period_end=dt.now(UTC) + timedelta(days=30),
    ))
    db.session.add(Subscription(
        organization_id=demo_org.id,
        plan=PlanType.PRO.value,
        status=SubscriptionStatus.ACTIVE.value,
        current_period_start=dt.now(UTC),
        current_period_end=dt.now(UTC) + timedelta(days=30),
    ))

    # Create feature flags
    flags = [
        FeatureFlag(name="New Dashboard", key="new_dashboard", enabled=True, scope="global"),
        FeatureFlag(name="Beta API", key="beta_api", enabled=False, scope="global"),
        FeatureFlag(name="Dark Mode", key="dark_mode", enabled=True, scope="global"),
    ]
    db.session.add_all(flags)

    db.session.commit()
    click.echo("Seed data created successfully!")
    click.echo("  Admin: admin@saasforge.com / Admin123!")
    click.echo("  Demo:  demo@saasforge.com / Demo123!")


@click.command("create-admin")
@click.argument("email")
@click.argument("password")
@click.argument("name")
@with_appcontext
def create_admin(email, password, name):
    """Create an admin user."""
    if User.query.filter_by(email=email).first():
        click.echo(f"User {email} already exists.")
        return

    user = User(
        email=email,
        name=name,
        email_verified=True,
        is_admin=True,
        is_active=True,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f"Admin user {email} created successfully!")


@click.command("list-routes")
@with_appcontext
def list_routes():
    """List all registered routes."""
    from flask import current_app

    rules = []
    for rule in current_app.url_map.iter_rules():
        methods = ",".join(sorted(rule.methods - {"HEAD", "OPTIONS"}))
        rules.append((rule.rule, methods, rule.endpoint))

    click.echo(f"{'Route':<50} {'Methods':<20} {'Endpoint':<30}")
    click.echo("-" * 100)
    for route, methods, endpoint in sorted(rules):
        click.echo(f"{route:<50} {methods:<20} {endpoint:<30}")


@click.command("seed-demo-data")
@with_appcontext
def seed_demo_data():
    """Seed comprehensive demo data for the demo environment."""
    from app.services.demo_service import create_seed_data

    result = create_seed_data()
    click.echo(f"Demo data created: {len(result)} records.")
    click.echo("  Admin: admin@saasforge.com / Admin123!")
    click.echo("  Demo:  demo@saasforge.com / Demo123!")
    click.echo("  Manager: manager@saasforge.com / Manager123!")
    click.echo("  Member:  member@saasforge.com / Member123!")


@click.command("schedule-jobs")
@with_appcontext
def schedule_jobs():
    """Schedule recurring background jobs."""
    from datetime import datetime, timedelta

    from app.core.models import JobRecord
    from app.jobs import (
        cleanup_expired_data_job,
        generate_weekly_report_job,
        process_analytics_job,
    )
    from app.services.job_scheduler import JobScheduler

    now = datetime.now(UTC)

    hourly = JobRecord.query.filter_by(name="Hourly Analytics Refresh", status="scheduled").first()
    if not hourly:
        JobScheduler.enqueue_in(timedelta(hours=1), "Hourly Analytics Refresh", process_analytics_job)
        click.echo("Scheduled hourly analytics refresh.")

    daily = JobRecord.query.filter_by(name="Daily Cleanup", status="scheduled").first()
    if not daily:
        next_daily = now.replace(hour=2, minute=0, second=0, microsecond=0)
        if next_daily <= now:
            next_daily += timedelta(days=1)
        JobScheduler.enqueue_at(next_daily, "Daily Cleanup", cleanup_expired_data_job)
        click.echo("Scheduled daily cleanup (02:00 UTC).")

    weekly = JobRecord.query.filter_by(name="Weekly Report", status="scheduled").first()
    if not weekly:
        next_weekly = now + timedelta(weeks=1)
        JobScheduler.enqueue_at(next_weekly, "Weekly Report", generate_weekly_report_job)
        click.echo("Scheduled weekly report.")

    click.echo("Done.")
