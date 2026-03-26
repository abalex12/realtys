"""
Email utilities for Addis Realty.
In development (EMAIL_BACKEND=console), emails print to the terminal.
In production, configure SMTP in settings.py.
"""
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
import uuid


def send_verification_email(user, request=None):
    """Generate a fresh token and send the verification email."""
    token = uuid.uuid4()
    user.email_verification_token = token
    user.email_verification_sent_at = timezone.now()
    user.save(update_fields=['email_verification_token', 'email_verification_sent_at'])

    site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
    verify_url = f"{site_url}/accounts/verify-email/{token}/"

    subject = "Verify your email – Addis Realty"
    message = (
        f"Hi {user.first_name or user.username},\n\n"
        f"Thank you for registering on Addis Realty!\n\n"
        f"Please verify your email address by clicking the link below:\n\n"
        f"{verify_url}\n\n"
        f"This link expires in 24 hours.\n\n"
        f"If you did not create an account, you can safely ignore this email.\n\n"
        f"— Addis Realty Team\n"
        f"Addis Ababa, Ethiopia"
    )
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Could not send verification email: {e}")
        return False


def send_listing_approved_email(listing):
    """Notify the listing owner that their listing was approved."""
    user = listing.owner
    if not user.email:
        return
    site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
    listing_url = f"{site_url}/listings/{listing.slug}/"

    subject = f"✅ Your listing has been approved – Addis Realty"
    message = (
        f"Hi {user.first_name or user.username},\n\n"
        f"Great news! Your listing has been approved and is now live on Addis Realty.\n\n"
        f"Listing: {listing.title}\n"
        f"Price: ETB {listing.price:,}\n"
        f"Area: {listing.area_display}\n\n"
        f"View your listing:\n{listing_url}\n\n"
        f"Potential buyers and renters can now contact you directly on {listing.phone_number}.\n\n"
        f"— Addis Realty Team"
    )
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")


def send_listing_rejected_email(listing):
    """Notify the listing owner that their listing was rejected."""
    user = listing.owner
    if not user.email:
        return
    site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
    edit_url = f"{site_url}/dashboard/edit/{listing.slug}/"

    subject = f"⚠️ Your listing needs attention – Addis Realty"
    message = (
        f"Hi {user.first_name or user.username},\n\n"
        f"Your listing '{listing.title}' was not approved at this time.\n\n"
        f"Reason: {listing.rejection_reason or 'Please review our listing guidelines.'}\n\n"
        f"You can edit and resubmit your listing here:\n{edit_url}\n\n"
        f"If you have questions, please contact our support team.\n\n"
        f"— Addis Realty Team"
    )
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")


def send_password_reset_email(user, reset_url):
    """Send password reset link."""
    subject = "Reset your password – Addis Realty"
    message = (
        f"Hi {user.first_name or user.username},\n\n"
        f"You requested a password reset for your Addis Realty account.\n\n"
        f"Click the link below to set a new password:\n\n"
        f"{reset_url}\n\n"
        f"This link expires in 24 hours. If you did not request a reset, ignore this email.\n\n"
        f"— Addis Realty Team"
    )
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
