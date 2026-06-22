from authlib.integrations.flask_client import OAuth
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from app.core.extensions import db
from app.services.auth_service import AuthService
from app.services.base import PermissionError, ServiceError, ValidationError
from app.services.two_factor_service import TwoFactorService

auth_bp = Blueprint("auth", __name__)
oauth = OAuth()


def init_oauth(app):
    if app.config.get("GOOGLE_OAUTH_CLIENT_ID"):
        oauth.init_app(app)
        oauth.register(
            name="google",
            client_id=app.config["GOOGLE_OAUTH_CLIENT_ID"],
            client_secret=app.config["GOOGLE_OAUTH_CLIENT_SECRET"],
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("core.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        name = request.form.get("name", "").strip()

        try:
            user = AuthService.register(email, password, name)
            login_user(user, remember=True)
            flash("Account created successfully! Please check your email to verify.", "success")
            return redirect(url_for("core.dashboard"))
        except ValidationError as e:
            flash(e.message, "error")
        except ServiceError as e:
            flash(e.message, "error")

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("core.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        try:
            user = AuthService.login(
                email,
                password,
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string if request.user_agent else None,
            )
            if user.totp_enabled:
                session["2fa_user_id"] = user.id
                session["2fa_remember"] = remember
                return redirect(url_for("auth.two_factor_challenge"))
            login_user(user, remember=remember)
            next_page = request.args.get("next")
            flash("Welcome back!", "success")
            return redirect(next_page or url_for("core.dashboard"))
        except (ValidationError, PermissionError) as e:
            flash(e.message, "error")

    return render_template("auth/login.html")


@auth_bp.route("/2fa-challenge", methods=["GET", "POST"])
def two_factor_challenge():
    if current_user.is_authenticated:
        return redirect(url_for("core.dashboard"))

    user_id = session.get("2fa_user_id")
    if not user_id:
        flash("Please log in first.", "info")
        return redirect(url_for("auth.login"))

    from app.core.models import User
    user = db.session.get(User, user_id)
    if not user or not user.totp_enabled:
        session.pop("2fa_user_id", None)
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        code = request.form.get("code", "").strip()
        if not code:
            flash("Verification code is required.", "error")
            return render_template("auth/two_factor_challenge.html")

        valid = TwoFactorService.verify_code(user.totp_secret, code)
        if not valid:
            valid = TwoFactorService.verify_backup_code(user.totp_backup_codes, code)

        if valid:
            if valid is not True:
                if user.totp_backup_codes:
                    user.totp_backup_codes = [c for c in user.totp_backup_codes if c != code]
                    db.session.commit()
            login_user(user, remember=session.get("2fa_remember", False))
            session.pop("2fa_user_id", None)
            session.pop("2fa_remember", None)
            flash("Welcome back!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("core.dashboard"))
        else:
            flash("Invalid code. Try again.", "error")

    return render_template("auth/two_factor_challenge.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/verify-email/<token>")
def verify_email(token):
    try:
        AuthService.verify_email(token)
        flash("Email verified successfully!", "success")
    except ValidationError as e:
        flash(e.message, "error")
    return redirect(url_for("core.dashboard"))


@auth_bp.route("/resend-verification")
@login_required
def resend_verification():
    if current_user.email_verified:
        flash("Your email is already verified.", "info")
        return redirect(url_for("core.dashboard"))

    from itsdangerous import URLSafeTimedSerializer
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    current_user.email_verify_token = serializer.dumps(current_user.email)
    from app.core.extensions import db
    db.session.commit()

    from app.services.email_service import EmailService
    verify_url = url_for("auth.verify_email", token=current_user.email_verify_token, _external=True)
    EmailService.send_verification_email(current_user.email, verify_url)

    flash("Verification email sent. Please check your inbox.", "info")
    return redirect(url_for("core.dashboard"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        AuthService.send_password_reset(email)
        flash("If an account with that email exists, a password reset link has been sent.", "info")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("auth/reset_password.html", token=token)

        try:
            AuthService.reset_password(token, password)
            flash("Password has been reset. Please log in.", "success")
            return redirect(url_for("auth.login"))
        except ValidationError as e:
            flash(e.message, "error")

    return render_template("auth/reset_password.html", token=token)


@auth_bp.route("/google/login")
def google_login():
    if not current_app.config.get("GOOGLE_OAUTH_CLIENT_ID"):
        flash("Google login is not configured.", "error")
        return redirect(url_for("auth.login"))
    redirect_uri = url_for("auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/google/callback")
def google_callback():
    try:
        token = oauth.google.authorize_access_token()
        user_info = oauth.google.parse_id_token(token)
    except Exception:
        flash("Google login failed. Please try again.", "error")
        return redirect(url_for("auth.login"))

    google_id = user_info.get("sub")
    email = user_info.get("email", "")
    name = user_info.get("name", email.split("@")[0])

    from app.core.extensions import cache_service, db
    from app.core.models import User

    user = User.query.filter_by(google_id=google_id).first()
    if not user:
        user = User.query.filter_by(email=email).first()
        if user:
            user.google_id = google_id
        else:
            user = User(
                email=email,
                name=name,
                google_id=google_id,
                email_verified=True,
            )
            db.session.add(user)
            db.session.flush()

            import secrets

            from app.core.models import Membership, Organization, PlanType, Role

            org = Organization(
                name=f"{name}'s Workspace",
                slug=f"personal-{secrets.token_hex(4)}",
                owner_id=user.id,
                is_personal=True,
                subscription_tier=PlanType.FREE.value,
                max_members=1,
            )
            db.session.add(org)
            db.session.flush()

            Membership(
                user_id=user.id,
                organization_id=org.id,
                role=Role.OWNER.value,
                is_current=True,
            )

        db.session.commit()
        cache_service.invalidate_analytics()

    login_user(user, remember=True)
    flash("Logged in with Google!", "success")
    return redirect(url_for("core.dashboard"))
