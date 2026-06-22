from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.core.extensions import db
from app.core.models import AuditLog, Invitation
from app.services.base import NotFoundError, PermissionError, ServiceError, ValidationError
from app.services.decorators import require_owner
from app.services.org_service import OrganizationService

org_bp = Blueprint("organizations", __name__)


@org_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        slug = request.form.get("slug", "").strip()

        if not name:
            flash("Organization name is required.", "error")
            return render_template("organizations/create.html")

        try:
            org = OrganizationService.create(name, current_user, slug or None)
            flash(f"Organization '{org.name}' created successfully!", "success")
            return redirect(url_for("core.dashboard"))
        except (ValidationError, ServiceError) as e:
            flash(e.message, "error")

    return render_template("organizations/create.html")


@org_bp.route("/<org_id>/settings", methods=["GET", "POST"])
@login_required
def settings(org_id):
    from app.core.models import Organization
    org = Organization.query.get_or_404(org_id)

    if not current_user.belongs_to(org):
        flash("You are not a member of this organization.", "error")
        return redirect(url_for("core.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        website = request.form.get("website", "").strip()
        brand_color = request.form.get("brand_color", "").strip()

        if name:
            org.name = name
        org.description = description
        org.website = website
        if brand_color:
            org.brand_color = brand_color
        db.session.commit()
        flash("Organization settings updated.", "success")
        return redirect(url_for("organizations.settings", org_id=org.id))

    return render_template("organizations/settings.html", org=org)


@org_bp.route("/<org_id>/members")
@login_required
def members(org_id):
    from app.core.models import Organization
    org = Organization.query.get_or_404(org_id)
    if not current_user.belongs_to(org):
        flash("Access denied.", "error")
        return redirect(url_for("core.dashboard"))

    member_list = OrganizationService.get_members(org_id)
    invitations = Invitation.query.filter_by(
        organization_id=org_id, revoked=False, accepted_at=None
    ).all()

    return render_template(
        "organizations/members.html",
        org=org,
        members=member_list,
        invitations=invitations,
    )


@org_bp.route("/<org_id>/members/invite", methods=["POST"])
@login_required
def invite_member(org_id):
    email = request.form.get("email", "").strip()
    role = request.form.get("role", "member")

    try:
        OrganizationService.invite_member(org_id, email, role, current_user)
        flash(f"Invitation sent to {email}!", "success")
    except (ValidationError, ServiceError, PermissionError) as e:
        flash(e.message, "error")

    return redirect(url_for("organizations.members", org_id=org_id))


@org_bp.route("/<org_id>/members/<member_id>/remove", methods=["POST"])
@login_required
def remove_member(org_id, member_id):
    try:
        OrganizationService.remove_member(org_id, member_id, current_user)
        flash("Member removed.", "success")
    except (ValidationError, PermissionError) as e:
        flash(e.message, "error")

    return redirect(url_for("organizations.members", org_id=org_id))


@org_bp.route("/<org_id>/members/<member_id>/role", methods=["POST"])
@login_required
def update_member_role(org_id, member_id):
    role = request.form.get("role", "member")
    try:
        OrganizationService.update_member_role(org_id, member_id, role, current_user)
        flash("Role updated.", "success")
    except (ValidationError, PermissionError) as e:
        flash(e.message, "error")

    return redirect(url_for("organizations.members", org_id=org_id))


@org_bp.route("/switch/<org_id>", methods=["POST"])
@login_required
def switch(org_id):
    try:
        OrganizationService.switch_organization(current_user, org_id)
        flash("Switched organization.", "success")
    except PermissionError as e:
        flash(e.message, "error")

    return redirect(request.referrer or url_for("core.dashboard"))


@org_bp.route("/invitations/<token>/accept")
@login_required
def accept_invitation(token):
    try:
        org = OrganizationService.accept_invitation(token, current_user)
        flash(f"You've joined {org.name}!", "success")
        return redirect(url_for("core.dashboard"))
    except (ValidationError, NotFoundError) as e:
        flash(e.message, "error")
        return redirect(url_for("core.dashboard"))


@org_bp.route("/invitations/<invitation_id>/revoke", methods=["POST"])
@login_required
def revoke_invitation(invitation_id):
    try:
        OrganizationService.revoke_invitation(invitation_id, current_user)
        flash("Invitation revoked.", "success")
    except (PermissionError, NotFoundError) as e:
        flash(e.message, "error")

    return redirect(request.referrer or url_for("organizations.members", org_id=""))


@org_bp.route("/<org_id>/transfer", methods=["POST"])
@login_required
@require_owner
def transfer_ownership(org_id):
    new_owner_id = request.form.get("new_owner_id")
    try:
        OrganizationService.transfer_ownership(org_id, new_owner_id, current_user)
        flash("Ownership transferred.", "success")
    except (ValidationError, PermissionError) as e:
        flash(e.message, "error")

    return redirect(url_for("organizations.settings", org_id=org_id))


@org_bp.route("/<org_id>/activity")
@login_required
def activity(org_id):
    from app.core.models import Organization
    org = Organization.query.get_or_404(org_id)
    if not current_user.belongs_to(org):
        flash("Access denied.", "error")
        return redirect(url_for("core.dashboard"))

    page = request.args.get("page", 1, type=int)
    logs = AuditLog.query.filter_by(organization_id=org_id).order_by(
        AuditLog.created_at.desc()
    ).paginate(page=page, per_page=30, error_out=False)

    return render_template("organizations/activity.html", org=org, logs=logs)
