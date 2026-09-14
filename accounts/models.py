from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import random

class Branch(models.Model):
    branch_name = models.CharField(max_length=100)
    branch_code = models.CharField(max_length=10, unique=True)
    ifsc_code = models.CharField(max_length=15, unique=True)
    address = models.TextField()
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    pincode = models.CharField(max_length=10)
    contact_number = models.CharField(max_length=15)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Branches"
        ordering = ['branch_name']

    def __str__(self):
        return f"{self.branch_name} ({self.ifsc_code})"


class CustomerProfile(models.Model):
    KYC_STATUS_CHOICES = (
        ('VERIFIED', 'Verified'),
        ('PENDING', 'Pending Verification'),
        ('REJECTED', 'Rejected'),
    )
    GENDER_CHOICES = (
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('OTHER', 'Other'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    cif_number = models.CharField(max_length=15, unique=True, verbose_name="CIF / Customer ID")
    phone_number = models.CharField(max_length=15, unique=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='MALE')
    address = models.TextField(blank=True, default='')
    city = models.CharField(max_length=50, blank=True, default='')
    state = models.CharField(max_length=50, blank=True, default='')
    pincode = models.CharField(max_length=10, blank=True, default='')
    profile_photo = models.ImageField(upload_to='profile_photos/', default='profile_photos/default_avatar.png', blank=True)
    kyc_status = models.CharField(max_length=20, choices=KYC_STATUS_CHOICES, default='VERIFIED')
    is_internet_banking_active = models.BooleanField(default=True)
    failed_login_count = models.PositiveIntegerField(default=0)
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} (CIF: {self.cif_number})"

    def masked_phone(self):
        if len(self.phone_number) >= 10:
            return f"+91 {self.phone_number[:2]}******{self.phone_number[-2:]}"
        return self.phone_number


class OTPVerification(models.Model):
    PURPOSE_CHOICES = (
        ('REGISTRATION', 'Internet Banking Registration'),
        ('LOGIN', 'Login Verification'),
        ('TRANSFER', 'Funds Transfer Authorization'),
        ('PASSWORD_RESET', 'Forgot Password Reset'),
        ('PROFILE_UPDATE', 'Profile Details Update'),
        ('BENEFICIARY_ADD', 'Beneficiary Addition'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='otps')
    phone_number = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    otp_code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=30, choices=PURPOSE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"OTP for {self.purpose} - {self.phone_number or self.email} (Valid till {self.expires_at})"

    def is_valid(self):
        return not self.is_used and timezone.now() <= self.expires_at

    @classmethod
    def generate_otp(cls, purpose, user=None, phone_number='', email='', validity_minutes=10):
        code = str(random.randint(100000, 999999))
        expiry = timezone.now() + timedelta(minutes=validity_minutes)
        return cls.objects.create(
            user=user,
            phone_number=phone_number,
            email=email,
            otp_code=code,
            purpose=purpose,
            expires_at=expiry
        )


class LoginAttempt(models.Model):
    username = models.CharField(max_length=150)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    is_successful = models.BooleanField(default=False)
    attempt_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-attempt_time']

    def __str__(self):
        status = "Success" if self.is_successful else "Failed"
        return f"{self.username} - {status} at {self.attempt_time}"


class AuditLog(models.Model):
    ACTION_CHOICES = (
        ('LOGIN', 'User Login'),
        ('LOGOUT', 'User Logout'),
        ('REGISTRATION', 'User Registration'),
        ('PASSWORD_CHANGE', 'Password Changed'),
        ('PASSWORD_RESET', 'Password Reset via OTP'),
        ('PROFILE_UPDATE', 'Profile Updated'),
        ('TRANSFER', 'Funds Transfer'),
        ('UPI_TRANSFER', 'UPI Transfer'),
        ('BENEFICIARY_ADD', 'Beneficiary Added'),
        ('BENEFICIARY_EDIT', 'Beneficiary Updated'),
        ('BENEFICIARY_DELETE', 'Beneficiary Deleted'),
        ('BILL_PAYMENT', 'Utility Bill Payment'),
        ('LOAN_APPLY', 'Loan Application'),
        ('LOAN_EMI_PAYMENT', 'Loan EMI Payment'),
        ('FD_CREATE', 'Fixed Deposit Created'),
        ('RD_CREATE', 'Recurring Deposit Created'),
    )

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        uname = self.user.username if self.user else "System"
        return f"[{self.timestamp.strftime('%d-%m-%Y %H:%M')}] {uname} - {self.action}"


class Notification(models.Model):
    TYPE_CHOICES = (
        ('INFO', 'Information'),
        ('SUCCESS', 'Success'),
        ('WARNING', 'Warning'),
        ('SECURITY', 'Security Alert'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=150)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='INFO')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"
