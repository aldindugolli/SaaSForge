from flask import current_app, render_template


class EmailService:
    @staticmethod
    def send_email(
        to: str,
        subject: str,
        html_body: str,
        from_email: str | None = None,
    ) -> bool:
        from_email = from_email or current_app.config.get("MAIL_DEFAULT_SENDER", "noreply@saasforge.com")

        # In development, just log the email
        if current_app.config.get("MAIL_SUPPRESS_SEND", True):
            current_app.logger.info(f"📧 Email to: {to}")
            current_app.logger.info(f"   Subject: {subject}")
            current_app.logger.info(f"   From: {from_email}")
            return True

        # In production, use SendGrid
        try:
            import sendgrid
            from sendgrid.helpers.mail import Content, Email, Mail, To

            sg = sendgrid.SendGridAPIClient(api_key=current_app.config["SENDGRID_API_KEY"])
            mail = Mail(
                from_email=Email(from_email),
                to_emails=To(to),
                subject=subject,
                html_content=Content("text/html", html_body),
            )
            response = sg.send(mail)
            return response.status_code in (200, 201, 202)
        except Exception as e:
            current_app.logger.error(f"Failed to send email to {to}: {e}")
            return False

    @staticmethod
    def send_verification_email(to: str, verify_url: str) -> bool:
        html = render_template("emails/verify_email.html", url=verify_url)
        return EmailService.send_email(to, "Verify your email address", html)

    @staticmethod
    def send_password_reset_email(to: str, reset_url: str) -> bool:
        html = render_template("emails/password_reset.html", url=reset_url)
        return EmailService.send_email(to, "Reset your password", html)

    @staticmethod
    def send_welcome_email(to: str, name: str) -> bool:
        html = render_template("emails/welcome.html", name=name)
        return EmailService.send_email(to, f"Welcome to SaaSForge, {name}!", html)

    @staticmethod
    def send_invitation_email(to: str, invited_by_name: str, org_name: str, invite_url: str) -> bool:
        html = render_template(
            "emails/invitation.html",
            invited_by=invited_by_name,
            organization=org_name,
            url=invite_url,
        )
        return EmailService.send_email(to, f"You've been invited to join {org_name}", html)

    @staticmethod
    def send_subscription_receipt(to: str, plan_name: str, amount: int, pdf_url: str | None = None) -> bool:
        html = render_template("emails/subscription_receipt.html", plan=plan_name, amount=amount)
        return EmailService.send_email(to, f"Receipt for {plan_name} plan", html)
