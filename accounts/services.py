from django.utils import timezone
from .models import AuditLog, Notification, OTPVerification
from django.conf import settings
from django.core.mail import send_mail
import logging

logger = logging.getLogger(__name__)

def get_client_ip(request):
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def log_audit_event(action, description, user=None, request=None):
    try:
        ip = get_client_ip(request) if request else None
        AuditLog.objects.create(
            user=user if (user and user.is_authenticated) else None,
            action=action,
            description=description,
            ip_address=ip
        )
    except Exception as e:
        logger.error(f"Error recording audit log: {e}")

def send_notification(user, title, message, notification_type='INFO'):
    try:
        if user and user.is_authenticated:
            return Notification.objects.create(
                user=user,
                title=title,
                message=message,
                notification_type=notification_type
            )
    except Exception as e:
        logger.error(f"Error creating user notification: {e}")
    return None

class OTPService:
    @staticmethod
    def generate_and_dispatch(purpose, user=None, phone_number='', email='', request=None):
        if user and not phone_number and hasattr(user, 'profile'):
            phone_number = user.profile.phone_number
        if user and not email:
            email = user.email

        # Invalidate old active OTPs for the same purpose & phone/email
        OTPVerification.objects.filter(
            purpose=purpose,
            phone_number=phone_number,
            is_used=False
        ).update(is_used=True)

        otp_obj = OTPVerification.generate_otp(
            purpose=purpose,
            user=user,
            phone_number=phone_number,
            email=email,
            validity_minutes=10
        )

        # In a real bank, this calls an SMS / Email gateway
        # In this educational project, we display demo OTP and log it to console
        logger.info(f"[PRIME RESERVE BANK DEMO OTP] Purpose: {purpose} | Destination: {phone_number or email} | OTP Code: {otp_obj.otp_code}")

        # If email is provided, send simulated/local email
        if email and getattr(settings, 'EMAIL_HOST_USER', None):
            try:
                subject = f"PRIME RESERVE BANK - OTP for {purpose.replace('_', ' ').title()}"
                body = f"Dear Customer,\n\nYour One Time Password (OTP) for {purpose.replace('_', ' ').title()} is {otp_obj.otp_code}.\nThis OTP is valid for 10 minutes.\n\nDo not share this OTP with anyone.\n\nPrime Reserve Bank (Educational Project)"
                send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=True)
            except Exception as e:
                logger.warning(f"Email OTP send failed: {e}")

        return otp_obj

    @staticmethod
    def verify_otp(purpose, otp_code, user=None, phone_number='', email=''):
        query = OTPVerification.objects.filter(
            purpose=purpose,
            otp_code=str(otp_code).strip(),
            is_used=False,
            expires_at__gte=timezone.now()
        )
        if user:
            query = query.filter(user=user)
        elif phone_number:
            query = query.filter(phone_number=phone_number)
        elif email:
            query = query.filter(email=email)

        otp_record = query.first()
        if otp_record:
            otp_record.is_used = True
            otp_record.save(update_fields=['is_used'])
            return True, "OTP verified successfully."
        return False, "Invalid or expired OTP code. Please try again."
