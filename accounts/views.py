from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Sum
from decimal import Decimal
from transactions.models import Transaction
from .models import CustomerProfile, Branch, OTPVerification, LoginAttempt, AuditLog, Notification
from .forms import (
    UserLoginForm, LoginOTPForm, FirstTimeSetupForm,
    ForgotPasswordStep1Form, ForgotPasswordStep2Form, ForgotPasswordStep3Form,
    ProfileUpdateForm, PasswordChangeCustomForm
)
from .services import log_audit_event, send_notification, OTPService
from banking.models import BankAccount
from upi.models import UPIAccount
import logging

logger = logging.getLogger(__name__)

def home_view(request):
    """
    Public Landing Page for PRIME RESERVE BANK.
    Passes real live customer metrics and transaction throughput.
    """
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect('dashboard:admin_overview')
        return redirect('dashboard:home')

    total_customers_count = BankAccount.objects.values('user').distinct().count()
    total_accounts_count = BankAccount.objects.count()
    total_deposits = BankAccount.objects.filter(status='ACTIVE').aggregate(s=Sum('balance'))['s'] or Decimal('0.00')
    total_tx_volume = Transaction.objects.filter(status='SUCCESS').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
    total_volume_processed = total_deposits + total_tx_volume
    branches_count = Branch.objects.count()

    context = {
        'total_customers_count': total_customers_count,
        'total_accounts_count': total_accounts_count,
        'total_deposits': total_deposits,
        'total_volume_processed': total_volume_processed,
        'branches_count': branches_count,
    }
    return render(request, 'home.html', context)


def login_view(request):
    """
    Step 1 of Login: Validates username and password.
    - Staff / Admin logs in directly.
    - Regular customers receive an Email OTP for 2-factor verification.
    """
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect('dashboard:admin_overview')
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username'].strip()
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data.get('remember_me', False)

            # Check if user exists & if locked
            user_obj = User.objects.filter(username__iexact=username).first()
            if user_obj and hasattr(user_obj, 'profile') and user_obj.profile.is_locked:
                messages.error(request, "Your Internet Banking account is temporarily locked due to repeated failed login attempts. Please contact branch or reset password.")
                return render(request, 'auth/login.html', {'form': form})

            user = authenticate(request, username=username, password=password)

            if user is not None:
                if not user.is_active:
                    messages.error(request, "This account is inactive. Please contact bank administration.")
                    return render(request, 'auth/login.html', {'form': form})

                # If staff/admin user, log in directly without OTP requirement
                if user.is_staff or user.is_superuser:
                    login(request, user)
                    if not remember_me:
                        request.session.set_expiry(1800)
                    else:
                        request.session.set_expiry(1209600)
                    log_audit_event("ADMIN_LOGIN", f"Admin {user.username} logged in successfully.", user=user, request=request)
                    messages.success(request, f"Welcome to Central Banking Admin, {user.get_full_name() or user.username}!")
                    return redirect('dashboard:admin_overview')

                # Customer Login -> Require Email OTP Verification
                otp_obj = OTPService.generate_and_dispatch(
                    purpose='LOGIN',
                    user=user,
                    email=user.email,
                    request=request
                )

                request.session['login_pending_user_id'] = user.id
                request.session['login_remember_me'] = remember_me
                request.session['demo_login_otp'] = otp_obj.otp_code

                masked_email = user.profile.masked_email() if hasattr(user, 'profile') else user.email
                messages.info(request, f"Security OTP dispatched to your registered email {masked_email}.")
                return redirect('accounts:login_otp')
            else:
                # Failed login tracking
                LoginAttempt.objects.create(username=username, is_successful=False, ip_address=request.META.get('REMOTE_ADDR'))
                if user_obj and hasattr(user_obj, 'profile'):
                    profile = user_obj.profile
                    profile.failed_login_count += 1
                    if profile.failed_login_count >= 5:
                        profile.is_locked = True
                        messages.error(request, "Account has been locked after 5 consecutive failed login attempts.")
                    else:
                        remaining = 5 - profile.failed_login_count
                        messages.error(request, f"Invalid username or password. {remaining} attempt(s) remaining before lockout.")
                    profile.save(update_fields=['failed_login_count', 'is_locked'])
                else:
                    messages.error(request, "Invalid username or password. Please check your credentials.")
    else:
        form = UserLoginForm()

    return render(request, 'auth/login.html', {'form': form})


def login_otp_view(request):
    """
    Step 2 of Login: Verifies the 6-digit Email OTP before granting session access.
    """
    user_id = request.session.get('login_pending_user_id')
    if not user_id:
        return redirect('accounts:login')

    user = User.objects.filter(id=user_id).first()
    if not user:
        request.session.pop('login_pending_user_id', None)
        return redirect('accounts:login')

    masked_email = user.profile.masked_email() if hasattr(user, 'profile') else user.email
    demo_otp = request.session.get('demo_login_otp')

    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Resend OTP
        if action == 'resend':
            otp_obj = OTPService.generate_and_dispatch(
                purpose='LOGIN',
                user=user,
                email=user.email,
                request=request
            )
            request.session['demo_login_otp'] = otp_obj.otp_code
            messages.success(request, f"A fresh OTP has been sent to {masked_email}.")
            return redirect('accounts:login_otp')

        form = LoginOTPForm(request.POST)
        if form.is_valid():
            otp_code = form.cleaned_data['otp_code'].strip()

            is_valid, msg = OTPService.verify_otp(
                purpose='LOGIN',
                otp_code=otp_code,
                user=user,
                email=user.email
            )

            if is_valid:
                # Login User
                login(request, user)
                remember_me = request.session.get('login_remember_me', False)
                if not remember_me:
                    request.session.set_expiry(1800)
                else:
                    request.session.set_expiry(1209600)

                # Reset lockout counter
                if hasattr(user, 'profile'):
                    user.profile.failed_login_count = 0
                    user.profile.save(update_fields=['failed_login_count'])

                LoginAttempt.objects.create(username=user.username, is_successful=True, ip_address=request.META.get('REMOTE_ADDR'))
                log_audit_event("LOGIN_WITH_OTP", f"User logged in successfully via Email OTP from IP {request.META.get('REMOTE_ADDR')}", user=user, request=request)

                # Cleanup temporary session keys
                request.session.pop('login_pending_user_id', None)
                request.session.pop('login_remember_me', None)
                request.session.pop('demo_login_otp', None)

                # Check if customer is logging in for the first time / needs UPI PIN generation
                profile = getattr(user, 'profile', None)
                if profile and (profile.is_first_login or not profile.has_set_upi_pin):
                    messages.info(request, f"Welcome to Internet Banking, {user.first_name or user.username}! Please generate your 4-digit UPI & Transaction PIN to complete setup.")
                    return redirect('accounts:first_time_setup')

                messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
                return redirect('dashboard:home')
            else:
                messages.error(request, msg)
    else:
        form = LoginOTPForm()

    return render(request, 'auth/login_otp.html', {
        'form': form,
        'user': user,
        'masked_email': masked_email,
        'demo_otp': demo_otp
    })


@login_required
def first_time_setup_view(request):
    """
    First-time Login Security Setup:
    Requires customer to generate a 4-digit UPI / Transaction PIN and optionally update their temporary password.
    """
    user = request.user
    profile = getattr(user, 'profile', None)

    # If already set up, redirect to dashboard
    if profile and not profile.is_first_login and profile.has_set_upi_pin:
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = FirstTimeSetupForm(request.POST)
        if form.is_valid():
            upi_pin = form.cleaned_data['upi_pin']
            new_pwd = form.cleaned_data.get('new_password')

            # 1. Update PIN on all linked Bank Accounts
            for acc in user.bank_accounts.all():
                acc.set_transaction_pin(upi_pin)
                acc.save(update_fields=['transaction_pin_hash', 'updated_at'])

            # 2. Update PIN on linked UPI Accounts
            for upi_acc in user.upi_accounts.all():
                upi_acc.set_pin(upi_pin)
                upi_acc.save(update_fields=['upi_pin_hash', 'updated_at'])

            # 3. Update Profile Status
            if profile:
                profile.is_first_login = False
                profile.has_set_upi_pin = True
                profile.save(update_fields=['is_first_login', 'has_set_upi_pin'])

            # 4. Update Password if provided
            if new_pwd:
                user.set_password(new_pwd)
                user.save()
                update_session_auth_hash(request, user)

            log_audit_event("FIRST_TIME_SETUP", "Customer generated UPI & Transaction PIN and completed first-time security setup.", user=user, request=request)
            send_notification(user, "Security Setup Complete", "Your 4-digit UPI & Transaction PIN has been set successfully.", "SUCCESS")

            messages.success(request, "🎉 First-time setup complete! Your UPI & Transaction PIN is active. Welcome to Prime Reserve Bank!")
            return redirect('dashboard:home')
    else:
        form = FirstTimeSetupForm()

    return render(request, 'auth/first_time_setup.html', {
        'form': form,
        'user': user
    })


def logout_view(request):
    """
    Secure Logout and session invalidation.
    """
    if request.user.is_authenticated:
        log_audit_event("LOGOUT", "User logged out securely.", user=request.user, request=request)
        logout(request)
        messages.info(request, "You have been logged out securely from Prime Reserve Bank.")
    return redirect('accounts:login')


def register_view(request):
    """
    Official Notice: In accordance with Prime Reserve Bank core banking rules,
    all new bank accounts must be registered in branch by a Bank Manager.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    return render(request, 'auth/register_notice.html')


def forgot_password_view(request):
    """
    Forgot Password workflow with Email OTP verification.
    Step 1: Enter Username or Registered Email -> Dispatches 6-digit OTP to Email.
    Step 2: Enter Email OTP.
    Step 3: Set New Password.
    """
    step = int(request.session.get('forgot_step', 1))

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'reset':
            request.session.pop('forgot_step', None)
            request.session.pop('forgot_user_id', None)
            request.session.pop('demo_forgot_otp', None)
            return redirect('accounts:forgot_password')

        if step == 1:
            form1 = ForgotPasswordStep1Form(request.POST)
            if form1.is_valid():
                ident = form1.cleaned_data['identifier'].strip()

                user = User.objects.filter(username__iexact=ident).first()
                if not user:
                    user = User.objects.filter(email__iexact=ident).first()
                if not user:
                    profile = CustomerProfile.objects.filter(cif_number=ident).first()
                    user = profile.user if profile else None

                if user and user.email:
                    request.session['forgot_user_id'] = user.id
                    otp_obj = OTPService.generate_and_dispatch(
                        purpose='PASSWORD_RESET',
                        user=user,
                        email=user.email,
                        request=request
                    )
                    request.session['demo_forgot_otp'] = otp_obj.otp_code
                    request.session['forgot_step'] = 2
                    masked = user.profile.masked_email() if hasattr(user, 'profile') else user.email
                    messages.success(request, f"Password reset OTP has been dispatched to your registered email: {masked}")
                    return redirect('accounts:forgot_password')
                else:
                    messages.error(request, "No matching customer account found with the provided identifier.")

        elif step == 2:
            form2 = ForgotPasswordStep2Form(request.POST)
            if form2.is_valid():
                otp_code = form2.cleaned_data['otp_code'].strip()
                user_id = request.session.get('forgot_user_id')
                user = User.objects.filter(id=user_id).first()

                is_valid, msg = OTPService.verify_otp(
                    purpose='PASSWORD_RESET',
                    otp_code=otp_code,
                    user=user,
                    email=user.email if user else ''
                )
                if is_valid:
                    request.session['forgot_step'] = 3
                    messages.success(request, "Email OTP verified! Please create a new password.")
                    return redirect('accounts:forgot_password')
                else:
                    messages.error(request, msg)

        elif step == 3:
            form3 = ForgotPasswordStep3Form(request.POST)
            if form3.is_valid():
                user_id = request.session.get('forgot_user_id')
                user = User.objects.filter(id=user_id).first()
                if user:
                    new_pwd = form3.cleaned_data['new_password']
                    user.set_password(new_pwd)
                    user.save()

                    if hasattr(user, 'profile'):
                        user.profile.failed_login_count = 0
                        user.profile.is_locked = False
                        user.profile.save(update_fields=['failed_login_count', 'is_locked'])

                    log_audit_event("PASSWORD_RESET", "Password reset successfully using Email OTP", user=user, request=request)
                    send_notification(user, "Password Reset Successful", "Your Internet Banking password was updated.", "SECURITY")

                    request.session.pop('forgot_step', None)
                    request.session.pop('forgot_user_id', None)
                    request.session.pop('demo_forgot_otp', None)

                    messages.success(request, "Password updated successfully! Please log in with your new password.")
                    return redirect('accounts:login')

    step = int(request.session.get('forgot_step', 1))
    user_id = request.session.get('forgot_user_id')
    user = User.objects.filter(id=user_id).first() if user_id else None
    masked_email = user.profile.masked_email() if (user and hasattr(user, 'profile')) else (user.email if user else '')

    return render(request, 'auth/forgot_password.html', {
        'step': step,
        'form1': ForgotPasswordStep1Form(),
        'form2': ForgotPasswordStep2Form(),
        'form3': ForgotPasswordStep3Form(),
        'masked_email': masked_email,
        'demo_otp': request.session.get('demo_forgot_otp')
    })


@login_required
def profile_view(request):
    """
    View Customer Profile, KYC status, and linked accounts.
    """
    profile = getattr(request.user, 'profile', None)
    accounts = request.user.bank_accounts.all()
    return render(request, 'profile/view_profile.html', {
        'profile': profile,
        'accounts': accounts
    })


@login_required
def update_profile_view(request):
    """
    Update Customer Profile details (phone, address, photo).
    """
    profile = get_object_or_404(CustomerProfile, user=request.user)
    
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            # Update User First/Last Name and Email
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.email = form.cleaned_data['email']
            request.user.save(update_fields=['first_name', 'last_name', 'email'])
            
            form.save()
            log_audit_event("PROFILE_UPDATE", "User updated personal profile details", user=request.user, request=request)
            messages.success(request, "Profile updated successfully!")
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(instance=profile, initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email
        })
    
    return render(request, 'profile/update_profile.html', {'form': form})


@login_required
def change_password_view(request):
    """
    Change user login password with current password verification.
    """
    if request.method == 'POST':
        form = PasswordChangeCustomForm(request.POST)
        if form.is_valid():
            curr_pwd = form.cleaned_data['current_password']
            new_pwd = form.cleaned_data['new_password']
            
            if not request.user.check_password(curr_pwd):
                messages.error(request, "Current password is incorrect.")
            else:
                request.user.set_password(new_pwd)
                request.user.save()
                update_session_auth_hash(request, request.user)
                log_audit_event("PASSWORD_CHANGE", "User changed account password successfully", user=request.user, request=request)
                send_notification(request.user, "Password Changed", "Your password was changed successfully.", "SECURITY")
                messages.success(request, "Password changed successfully!")
                return redirect('accounts:profile')
    else:
        form = PasswordChangeCustomForm()
        
    return render(request, 'profile/change_password.html', {'form': form})


@login_required
def notifications_view(request):
    """
    View all notifications & mark read.
    """
    if request.GET.get('mark_all_read') == 'true':
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return redirect('accounts:notifications')

    notif_list = Notification.objects.filter(user=request.user).order_by('-created_at')
    paginator = Paginator(notif_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'profile/notifications.html', {'page_obj': page_obj})


@login_required
def audit_logs_view(request):
    """
    User Security Audit Log viewer.
    """
    logs_list = AuditLog.objects.filter(user=request.user).order_by('-timestamp')
    paginator = Paginator(logs_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'profile/audit_logs.html', {'page_obj': page_obj})
