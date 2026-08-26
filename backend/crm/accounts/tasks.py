import logging
import os

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from .models import CustomUser

logger = logging.getLogger(__name__)

OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES", "5"))
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "3"))


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def send_password_reset_otp_email(self, user_id, otp):
    """
    Send the password reset OTP email asynchronously.
    The OTP is generated in the view; only the plain code is passed here.
    """
    try:
        user = CustomUser.objects.get(pk=user_id)
    except CustomUser.DoesNotExist:
        logger.warning(
            "OTP email skipped: user %s no longer exists",
            user_id,
        )
        return False

    expiry_minutes = OTP_EXPIRY_MINUTES
    max_attempts = OTP_MAX_ATTEMPTS

    try:
        send_mail(
            subject="CRM Password Reset OTP",
            message=(
                f"Hello {user.username},\n\n"
                "We received a request to reset your CRM account password.\n"
                "Use the One-Time Password (OTP) below "
                "to reset it:\n\n"
                f"OTP: {otp}\n\n"
                f"This OTP is valid for "
                f"{expiry_minutes} minutes and can be used only once.\n"
                f"You have {max_attempts} attempts "
                "to enter it correctly.\n"
                "If you did not request this, you can safely ignore "
                "this email.\n"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        logger.info(
            "Password reset OTP email sent via Celery to user %s",
            user_id,
        )
        return True

    except Exception as exc:
        logger.exception(
            "OTP email failed for user %s",
            user_id,
        )
        raise self.retry(exc=exc)
