from django.contrib import admin
from .models import Branch, CustomerProfile, OTPVerification, LoginAttempt, AuditLog, Notification

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('branch_name', 'branch_code', 'ifsc_code', 'city', 'state', 'contact_number')
    search_fields = ('branch_name', 'branch_code', 'ifsc_code', 'city')
    list_filter = ('state', 'city')

@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'cif_number', 'phone_number', 'kyc_status', 'is_internet_banking_active', 'is_locked', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'cif_number', 'phone_number')
    list_filter = ('kyc_status', 'is_internet_banking_active', 'is_locked', 'gender')
    readonly_fields = ('cif_number', 'created_at', 'updated_at')

@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ('purpose', 'phone_number', 'email', 'otp_code', 'is_used', 'expires_at', 'created_at')
    search_fields = ('phone_number', 'email', 'otp_code')
    list_filter = ('purpose', 'is_used')
    readonly_fields = ('otp_code', 'created_at')

@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ('username', 'ip_address', 'is_successful', 'attempt_time')
    search_fields = ('username', 'ip_address')
    list_filter = ('is_successful',)

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'ip_address', 'description')
    search_fields = ('user__username', 'action', 'description', 'ip_address')
    list_filter = ('action', 'timestamp')
    readonly_fields = ('timestamp', 'user', 'action', 'description', 'ip_address')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    list_filter = ('notification_type', 'is_read')
