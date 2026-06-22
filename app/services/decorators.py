from functools import wraps
from flask import abort, request, jsonify
from flask_login import current_user
from app.core.models import Role, Membership


def require_role(role: Role):
    """Require a specific role or higher in the current organization."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)

            org = current_user.current_organization
            if not org:
                abort(403, description="No organization selected.")

            membership = Membership.query.filter_by(
                user_id=current_user.id,
                organization_id=org.id,
            ).first()
            if not membership:
                abort(403, description="Not a member of this organization.")

            roles = [Role.OWNER.value, Role.ADMIN.value, Role.MEMBER.value]
            required_idx = roles.index(role.value)
            user_idx = roles.index(membership.role)

            if user_idx > required_idx:
                abort(403, description=f"Requires {role.value} role or higher.")

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_owner(f):
    """Require the user to be the organization owner."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)

        org = current_user.current_organization
        if not org:
            abort(403, description="No organization selected.")

        if org.owner_id != current_user.id:
            abort(403, description="Organization owner required.")

        return f(*args, **kwargs)
    return decorated_function


def require_admin(f):
    """Require the user to be a site admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if not current_user.is_admin:
            abort(403, description="Admin access required.")
        return f(*args, **kwargs)
    return decorated_function


def require_email_verified(f):
    """Require the user's email to be verified."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if not current_user.email_verified:
            if request.headers.get("HX-Request"):
                from flask import render_template
                return render_template("components/error_toast.html", message="Please verify your email address first.")
            abort(403, description="Please verify your email address first.")
        return f(*args, **kwargs)
    return decorated_function


def require_active_subscription(f):
    """Require the organization to have an active subscription."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)

        org = current_user.current_organization
        if not org:
            abort(403, description="No organization selected.")

        sub = org.active_subscription
        if not sub or not sub.is_active:
            if request.headers.get("HX-Request"):
                from flask import render_template
                return render_template("components/error_toast.html", message="Active subscription required.")
            abort(403, description="Active subscription required.")

        return f(*args, **kwargs)
    return decorated_function


def org_required(f):
    """Ensure user has an organization selected."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)

        if not current_user.current_organization:
            from flask import redirect, url_for
            return redirect(url_for("organizations.create"))

        return f(*args, **kwargs)
    return decorated_function
