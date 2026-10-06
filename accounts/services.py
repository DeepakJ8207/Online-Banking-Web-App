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

        # In this educational project, we display demo OTP and log it to console
        logger.info(f"[PRIME RESERVE BANK DEMO OTP] Purpose: {purpose} | Destination: {phone_number or email} | OTP Code: {otp_obj.otp_code}")

        # Send email OTP
        if email:
            try:
                purpose_display = purpose.replace('_', ' ').title()
                subject = f"PRIME RESERVE BANK — Security OTP for {purpose_display}"
                body = f"""Dear Customer,

Your One Time Password (OTP) for {purpose_display} is: {otp_obj.otp_code}

This OTP is valid for 10 minutes. Please enter this code on the screen to complete your security verification.

Important Security Advice:
Prime Reserve Bank officers will NEVER ask you for your Password, OTP, or UPI PIN. Do not share this code with anyone.

Sincerely,
Prime Reserve Bank Central Security
"""
                html_message = f"""
                <div style="font-family: Arial, sans-serif; max-width: 540px; margin: auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background: #ffffff;">
                    <div style="text-align: center; margin-bottom: 20px;">
                        <h2 style="color: #0b1f3a; margin: 0; font-size: 22px;">PRIME RESERVE BANK</h2>
                        <p style="color: #64748b; font-size: 13px; margin-top: 4px;">Security Verification Portal</p>
                    </div>
                    <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; text-align: center; margin-bottom: 20px;">
                        <p style="color: #475569; font-size: 14px; margin: 0 0 10px 0;">Your One-Time Password for <strong>{purpose_display}</strong> is:</p>
                        <div style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #2563eb; font-family: monospace; padding: 10px; background: #ffffff; border-radius: 6px; display: inline-block; border: 1px dashed #cbd5e1;">
                            {otp_obj.otp_code}
                        </div>
                        <p style="color: #94a3b8; font-size: 12px; margin: 10px 0 0 0;">Valid for 10 minutes. Do not share with anyone.</p>
                    </div>
                    <p style="color: #64748b; font-size: 13px; line-height: 1.5;">
                        If you did not initiate this request, please immediately contact Prime Reserve Bank customer support.
                    </p>
                    <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
                    <p style="color: #94a3b8; font-size: 11px; text-align: center; margin: 0;">
                        © 2026 Prime Reserve Bank • Automated Security Dispatch
                    </p>
                </div>
                """
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@primereservebank.demo'),
                    recipient_list=[email],
                    html_message=html_message,
                    fail_silently=True
                )
            except Exception as e:
                logger.warning(f"Email OTP dispatch failed: {e}")

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
