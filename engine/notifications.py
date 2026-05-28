"""
PASS Notification Service
===========================
Handles email notifications for critical alerts, password resets,
and periodic summary reports to teachers, parents, and admins.
"""

from flask import current_app, render_template


def send_email(recipient, subject, body, html=None):
    """Send an email if Flask-Mail is configured."""
    mail_server = current_app.config.get("MAIL_SERVER")
    if not mail_server:
        return False

    try:
        from flask_mail import Message
        from app import mail

        msg = Message(subject, recipients=[recipient])
        msg.body = body
        if html:
            msg.html = html
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send email: {e}")
        return False


def notify_teacher_alert(teacher_email, student_name, alert_description, score):
    """Send alert notification to a teacher."""
    subject = f"[PASS ALERT] {student_name} — Needs Attention"
    body = (
        f"Dear Teacher,\n\n"
        f"PASS has detected a concern regarding {student_name}.\n\n"
        f"Current Credibility Score: {score}\n"
        f"Alert: {alert_description}\n\n"
        f"Please log in to the PASS dashboard for more details.\n\n"
        f"Regards,\nPASS System"
    )
    return send_email(teacher_email, subject, body)


def notify_parent_alert(parent_email, student_name, score, trend):
    """Send alert notification to a parent/guardian."""
    subject = f"[PASS] Update: {student_name}'s Academic Progress"
    body = (
        f"Dear Parent/Guardian,\n\n"
        f"Here is your child {student_name}'s latest academic update:\n\n"
        f"Credibility Score: {score}/100\n"
        f"Trend: {trend}\n\n"
        f"Log in to the PASS parent dashboard to see detailed breakdown.\n\n"
        f"Regards,\nPASS System"
    )
    return send_email(parent_email, subject, body)


def send_password_reset(email, reset_url, full_name):
    """Send password reset email."""
    subject = "PASS — Password Reset Request"
    body = (
        f"Hello {full_name},\n\n"
        f"Click the link below to reset your password:\n{reset_url}\n\n"
        f"This link expires in 24 hours.\n\n"
        f"If you did not request this, please ignore this email.\n\n"
        f"Regards,\nPASS Team"
    )
    return send_email(email, subject, body)
