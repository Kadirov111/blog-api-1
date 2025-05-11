import secrets
import datetime
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone


def generate_token():
    return secrets.token_urlsafe(32)


def send_verification_email(user):
    token = generate_token()
    expires = timezone.now() + datetime.timedelta(hours=24)

    user.verification_token = token
    user.verification_token_expires = expires
    user.save()

    verification_url = f"http://localhost:8000/auth/verify-email/?token={token}"

    send_mail(
        subject='Verify your email address',
        message=f'Please click the link to verify your email: {verification_url}',
        from_email=settings.EMAIL_HOST_USER if hasattr(settings, 'EMAIL_HOST_USER') else 'noreply@example.com',
        recipient_list=[user.email],
        fail_silently=False,
    )


def send_password_reset_email(user):
    token = generate_token()
    expires = timezone.now() + datetime.timedelta(hours=24)

    user.reset_password_token = token
    user.reset_password_token_expires = expires
    user.save()

    reset_url = f"http://localhost:8000/auth/password-reset/confirm/?token={token}"

    send_mail(
        subject='Reset your password',
        message=f'Please click the link to reset your password: {reset_url}',
        from_email=settings.EMAIL_HOST_USER if hasattr(settings, 'EMAIL_HOST_USER') else 'noreply@example.com',
        recipient_list=[user.email],
        fail_silently=False,
    )