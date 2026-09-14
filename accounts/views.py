from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.core.paginator import Paginator
from .models import CustomerProfile, Branch, OTPVerification, LoginAttempt, AuditLog, Notification
from .forms import (
    UserLoginForm, RegistrationStep1Form, RegistrationStep2Form,
    RegistrationStep3Form, RegistrationStep4Form,
    ForgotPasswordStep1Form, ForgotPasswordStep2Form, ForgotPasswordStep3Form,
    ProfileUpdateForm, PasswordChangeCustomForm
)
from .services import log_audit_event, send_notification, OTPService
from banking.models import BankAccount
import logging

logger = logging.getLogger(__name__)

def home_view(request):
    """
    Public Landing Page for PRIME RESERVE BANK.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    return render(request, 'home.html')

def login_view(request):
    """
    Secure Internet Banking Login with rate limiting and session management.
    """
    if request.user.is_authenticated:
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

                # Successful login
                login(request, user)
                if not remember_me:
                    request.session.set_expiry(1800) # 30 mins
                else:
                    request.session.set_expiry(1209600) # 2 weeks

                # Reset failed login count
                if hasattr(user, 'profile'):
                    user.profile.failed_login_count = 0
                    user.profile.save(update_fields=['failed_login_count'])

                LoginAttempt.objects.create(username=username, is_successful=True, ip_address=request.META.get('REMOTE_ADDR'))
                log_audit_event("LOGIN", f"User logged in successfully from IP {request.META.get('REMOTE_ADDR')}", user=user, request=request)
                
                messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
                next_url = request.GET.get('next') or 'dashboard:home'
                return redirect(next_url)
            else:
                # Failed login
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
    5-Step Internet Banking Registration Wizard.
    Verifies Account -> CIF -> Mobile -> Demo OTP -> Creates Credentials.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    step = int(request.session.get('reg_step', 1))
    generated_demo_otp = None

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'reset':
            request.session.pop('reg_step', None)
            request.session.pop('reg_account_number', None)
            request.session.pop('reg_cif', None)
            request.session.pop('reg_mobile', None)
            return redirect('accounts:register')

        if step == 1:
            form1 = RegistrationStep1Form(request.POST)
            if form1.is_valid():
                acc_num = form1.cleaned_data['account_number'].strip()
                cif = form1.cleaned_data['cif_number'].strip()

                # Verify account and CIF match in database
                account = BankAccount.objects.filter(account_number=acc_num).first()
                if not account:
                    messages.error(request, "Account number not found in Prime Reserve Bank records.")
                elif not hasattr(account.user, 'profile') or account.user.profile.cif_number != cif:
                    messages.error(request, "CIF Number does not match the provided account number.")
                elif account.user.is_active and account.user.has_usable_password() and account.user.username not in [f"temp_{acc_num}", ""]:
                    messages.warning(request, "Internet Banking is already activated for this account. Please log in or use Forgot Password.")
                    return redirect('accounts:login')
                else:
                    request.session['reg_account_number'] = acc_num
                    request.session['reg_cif'] = cif
                    request.session['reg_step'] = 2
                    return redirect('accounts:register')

        elif step == 2:
            form2 = RegistrationStep2Form(request.POST)
            if form2.is_valid():
                mobile = form2.cleaned_data['registered_mobile'].strip()
                acc_num = request.session.get('reg_account_number')
                account = BankAccount.objects.filter(account_number=acc_num).first()
                
                if account and account.user.profile.phone_number == mobile:
                    request.session['reg_mobile'] = mobile
                    # Generate OTP
                    otp_obj = OTPService.generate_and_dispatch(
                        purpose='REGISTRATION',
                        user=account.user,
                        phone_number=mobile,
                        request=request
                    )
                    request.session['demo_reg_otp'] = otp_obj.otp_code
                    request.session['reg_step'] = 3
                    messages.success(request, f"One Time Password (OTP) has been sent to registered mobile {mobile[-4:].rjust(10, '*')}")
                    return redirect('accounts:register')
                else:
                    messages.error(request, "Mobile number does not match bank records for this account.")

        elif step == 3:
            form3 = RegistrationStep3Form(request.POST)
            if form3.is_valid():
                otp_code = form3.cleaned_data['otp_code'].strip()
                mobile = request.session.get('reg_mobile')
                acc_num = request.session.get('reg_account_number')
                account = BankAccount.objects.filter(account_number=acc_num).first()

                is_valid, msg = OTPService.verify_otp(
                    purpose='REGISTRATION',
                    otp_code=otp_code,
                    user=account.user if account else None,
                    phone_number=mobile
                )
                if is_valid:
                    request.session['reg_step'] = 4
                    messages.success(request, "Mobile number verified! Now create your login credentials.")
                    return redirect('accounts:register')
                else:
                    messages.error(request, msg)

        elif step == 4:
            form4 = RegistrationStep4Form(request.POST)
            if form4.is_valid():
                username = form4.cleaned_data['username'].strip()
                password = form4.cleaned_data['password']
                acc_num = request.session.get('reg_account_number')
                account = BankAccount.objects.filter(account_number=acc_num).first()

                if account:
                    user = account.user
                    user.username = username
                    user.set_password(password)
                    user.is_active = True
                    user.save()

                    profile = user.profile
                    profile.is_internet_banking_active = True
                    profile.failed_login_count = 0
                    profile.is_locked = False
                    profile.save()

                    # Set default transaction PIN 1234 if not set
                    if not account.transaction_pin_hash:
                        account.set_transaction_pin('1234')
                        account.save()

                    log_audit_event("REGISTRATION", f"Internet banking activated with username '{username}'", user=user, request=request)
                    send_notification(user, "Internet Banking Activated", "Your Prime Reserve Bank Internet Banking registration is complete!", "SUCCESS")

                    # Clear session
                    request.session.pop('reg_step', None)
                    request.session.pop('reg_account_number', None)
                    request.session.pop('reg_cif', None)
                    request.session.pop('reg_mobile', None)
                    request.session.pop('demo_reg_otp', None)

                    messages.success(request, "Registration successful! You can now log in with your credentials.")
                    return redirect('accounts:login')
                else:
                    messages.error(request, "Registration session expired. Please start again.")
                    return redirect('accounts:register')

    # Prepare GET context
    step = int(request.session.get('reg_step', 1))
    form1 = RegistrationStep1Form(initial={'account_number': request.session.get('reg_account_number', ''), 'cif_number': request.session.get('reg_cif', '')})
    form2 = RegistrationStep2Form(initial={'registered_mobile': request.session.get('reg_mobile', '')})
    form3 = RegistrationStep3Form()
    form4 = RegistrationStep4Form()
    demo_otp = request.session.get('demo_reg_otp')

    return render(request, 'auth/register.html', {
        'step': step,
        'form1': form1,
        'form2': form2,
        'form3': form3,
        'form4': form4,
        'demo_otp': demo_otp,
        'reg_account_number': request.session.get('reg_account_number'),
        'reg_mobile': request.session.get('reg_mobile')
    })


def forgot_password_view(request):
    """
    Forgot Password workflow with OTP verification.
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
                mobile = form1.cleaned_data['registered_mobile'].strip()

                user = User.objects.filter(username__iexact=ident).first()
                if not user:
                    profile = CustomerProfile.objects.filter(cif_number=ident).first()
                    user = profile.user if profile else None

                if user and hasattr(user, 'profile') and user.profile.phone_number == mobile:
                    request.session['forgot_user_id'] = user.id
                    otp_obj = OTPService.generate_and_dispatch(
                        purpose='PASSWORD_RESET',
                        user=user,
                        phone_number=mobile,
                        request=request
                    )
                    request.session['demo_forgot_otp'] = otp_obj.otp_code
                    request.session['forgot_step'] = 2
                    messages.success(request, f"OTP has been dispatched to {mobile[-4:].rjust(10, '*')}")
                    return redirect('accounts:forgot_password')
                else:
                    messages.error(request, "No matching record found with given username/CIF and mobile number.")

        elif step == 2:
            form2 = ForgotPasswordStep2Form(request.POST)
            if form2.is_valid():
                otp_code = form2.cleaned_data['otp_code'].strip()
                user_id = request.session.get('forgot_user_id')
                user = User.objects.filter(id=user_id).first()

                is_valid, msg = OTPService.verify_otp(
                    purpose='PASSWORD_RESET',
                    otp_code=otp_code,
                    user=user
                )
                if is_valid:
                    request.session['forgot_step'] = 3
                    messages.success(request, "OTP verified! Please create a new password.")
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
                        user.profile.save()

                    log_audit_event("PASSWORD_RESET", "Password reset successfully using OTP", user=user, request=request)
                    send_notification(user, "Password Reset Successful", "Your Internet Banking password was updated.", "SECURITY")

                    request.session.pop('forgot_step', None)
                    request.session.pop('forgot_user_id', None)
                    request.session.pop('demo_forgot_otp', None)

                    messages.success(request, "Password updated successfully! Please log in with your new password.")
                    return redirect('accounts:login')

    step = int(request.session.get('forgot_step', 1))
    return render(request, 'auth/forgot_password.html', {
        'step': step,
        'form1': ForgotPasswordStep1Form(),
        'form2': ForgotPasswordStep2Form(),
        'form3': ForgotPasswordStep3Form(),
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
    Update Customer Contact & Address Details, upload profile photo.
    """
    profile, _ = CustomerProfile.objects.get_or_create(
        user=request.user,
        defaults={'cif_number': f"CIF{request.user.id:08d}", 'phone_number': f"98765{request.user.id:05d}"}
    )

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.email = form.cleaned_data['email']
            request.user.save()

            form.save()
            log_audit_event("PROFILE_UPDATE", "Customer profile contact information updated", user=request.user, request=request)
            send_notification(request.user, "Profile Updated", "Your profile details were updated successfully.", "INFO")
            messages.success(request, "Profile updated successfully.")
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(instance=profile, initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email
        })

    return render(request, 'profile/update_profile.html', {'form': form, 'profile': profile})


@login_required
def change_password_view(request):
    """
    Change Account Password with current password verification.
    """
    if request.method == 'POST':
        form = PasswordChangeCustomForm(request.POST)
        if form.is_valid():
            curr_pwd = form.cleaned_data['current_password']
            new_pwd = form.cleaned_data['new_password']

            if not request.user.check_password(curr_pwd):
                messages.error(request, "Incorrect current password.")
            else:
                request.user.set_password(new_pwd)
                request.user.save()
                update_session_auth_hash(request, request.user)

                log_audit_event("PASSWORD_CHANGE", "Password changed successfully from profile settings", user=request.user, request=request)
                send_notification(request.user, "Security Alert: Password Changed", "Your password was changed successfully.", "SECURITY")
                messages.success(request, "Password updated successfully.")
                return redirect('accounts:profile')
    else:
        form = PasswordChangeCustomForm()

    return render(request, 'profile/change_password.html', {'form': form})


@login_required
def notifications_view(request):
    """
    Notification center with mark-all-read support.
    """
    if request.GET.get('mark_all_read') == 'true':
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        messages.success(request, "All notifications marked as read.")
        return redirect('accounts:notifications')

    notif_list = Notification.objects.filter(user=request.user)
    paginator = Paginator(notif_list, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'dashboard/notifications.html', {'page_obj': page_obj})


@login_required
def audit_logs_view(request):
    """
    View user's security and activity audit trail.
    """
    logs = AuditLog.objects.filter(user=request.user)
    paginator = Paginator(logs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'dashboard/audit_logs.html', {'page_obj': page_obj})
