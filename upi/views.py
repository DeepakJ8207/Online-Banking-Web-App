from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
import io
import qrcode
from .models import UPIAccount, UPITransaction
from .forms import CreateUPIForm, ChangeUPIPINForm, ForgotUPIPINForm
from banking.models import BankAccount
from accounts.services import log_audit_event, send_notification, OTPService

@login_required
def upi_home_view(request):
    """
    Simulated UPI Central Portal.
    """
    upi_accounts = UPIAccount.objects.filter(user=request.user)
    primary_upi = upi_accounts.filter(is_primary=True).first() or upi_accounts.first()
    
    # Recent UPI transactions
    recent_upi_txns = UPITransaction.objects.filter(
        transaction__sender_account__user=request.user
    ).select_related('transaction')[:5]

    return render(request, 'upi/upi_home.html', {
        'upi_accounts': upi_accounts,
        'primary_upi': primary_upi,
        'recent_upi_txns': recent_upi_txns
    })


@login_required
def create_upi_view(request):
    """
    Create a new UPI Handle / Virtual Payment Address (VPA).
    """
    if request.method == 'POST':
        form = CreateUPIForm(request.POST, user=request.user)
        if form.is_valid():
            bank_acc = form.cleaned_data['bank_account']
            handle = form.cleaned_data['custom_handle']
            pin = form.cleaned_data['upi_pin']
            full_vpa = f"{handle}@primereserve"

            # Check if this is the first UPI handle (make primary)
            is_first = not UPIAccount.objects.filter(user=request.user).exists()

            upi_obj = UPIAccount.objects.create(
                user=request.user,
                bank_account=bank_acc,
                upi_id=full_vpa,
                is_primary=is_first
            )
            upi_obj.set_pin(pin)
            upi_obj.save()

            log_audit_event("UPI_CREATE", f"Created new UPI ID {full_vpa}", user=request.user, request=request)
            send_notification(request.user, "New UPI ID Created", f"Your new UPI ID {full_vpa} has been created and linked to A/c {bank_acc.masked_account_number()}.", "SUCCESS")
            messages.success(request, f"UPI ID '{full_vpa}' created and linked successfully!")
            return redirect('upi:home')
    else:
        form = CreateUPIForm(user=request.user)

    return render(request, 'upi/create_upi.html', {'form': form})


@login_required
def upi_qr_view(request, upi_id):
    """
    Display Dynamic QR Code for selected UPI ID.
    """
    upi_obj = get_object_or_404(UPIAccount, upi_id=upi_id, user=request.user)
    cust_name = request.user.get_full_name() or request.user.username
    upi_payload = f"upi://pay?pa={upi_obj.upi_id}&pn={cust_name}&cu=INR&tn=PrimeReserveDemo"

    return render(request, 'upi/qr_code.html', {
        'upi_obj': upi_obj,
        'upi_payload': upi_payload
    })


@login_required
def upi_qr_image_view(request, upi_id):
    """
    Generates dynamic PNG QR code for the UPI handle.
    """
    upi_obj = get_object_or_404(UPIAccount, upi_id=upi_id, user=request.user)
    cust_name = request.user.get_full_name() or request.user.username
    upi_payload = f"upi://pay?pa={upi_obj.upi_id}&pn={cust_name}&cu=INR&tn=PrimeReserveDemo"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(upi_payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0d2346", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return HttpResponse(buffer.getvalue(), content_type='image/png')


@login_required
def change_upi_pin_view(request, upi_id):
    """
    Update UPI PIN for a specific handle.
    """
    upi_obj = get_object_or_404(UPIAccount, upi_id=upi_id, user=request.user)

    if request.method == 'POST':
        form = ChangeUPIPINForm(request.POST)
        if form.is_valid():
            old_pin = form.cleaned_data['old_pin']
            new_pin = form.cleaned_data['new_pin']

            if not upi_obj.check_pin(old_pin):
                messages.error(request, "Incorrect current UPI PIN.")
            else:
                upi_obj.set_pin(new_pin)
                upi_obj.save(update_fields=['upi_pin_hash'])
                log_audit_event("PASSWORD_CHANGE", f"Changed UPI PIN for {upi_obj.upi_id}", user=request.user, request=request)
                messages.success(request, f"UPI PIN for {upi_obj.upi_id} updated successfully!")
                return redirect('upi:home')
    else:
        form = ChangeUPIPINForm()

    return render(request, 'upi/change_pin.html', {'form': form, 'upi_obj': upi_obj})


@login_required
def forgot_upi_pin_view(request, upi_id):
    """
    Reset UPI PIN via Email OTP if user forgot their current PIN.
    Enforces 4-digit UPI PIN.
    """
    upi_obj = get_object_or_404(UPIAccount, upi_id=upi_id, user=request.user)
    masked_email = request.user.profile.masked_email() if hasattr(request.user, 'profile') else request.user.email

    # Resend OTP Action
    if request.method == 'POST' and request.POST.get('action') == 'resend_otp':
        OTPService.generate_and_dispatch(
            purpose='UPI_PIN_RESET',
            user=request.user,
            email=request.user.email,
            phone_number=request.user.profile.phone_number if hasattr(request.user, 'profile') else '',
            request=request
        )
        messages.success(request, f"New OTP verification code sent to {masked_email}")
        return redirect('upi:forgot_pin', upi_id=upi_obj.upi_id)

    # Initial dispatch on fresh entry
    session_flag = f'upi_otp_dispatched_{upi_obj.id}'
    if request.method == 'GET':
        OTPService.generate_and_dispatch(
            purpose='UPI_PIN_RESET',
            user=request.user,
            email=request.user.email,
            phone_number=request.user.profile.phone_number if hasattr(request.user, 'profile') else '',
            request=request
        )
        request.session[session_flag] = True
        messages.info(request, f"Security OTP dispatched to your registered email: {masked_email}")

    if request.method == 'POST':
        form = ForgotUPIPINForm(request.POST)
        if form.is_valid():
            otp_code = form.cleaned_data['otp_code']
            new_pin = form.cleaned_data['new_pin']

            is_valid, msg = OTPService.verify_otp(
                purpose='UPI_PIN_RESET',
                otp_code=otp_code,
                user=request.user,
                email=request.user.email
            )
            if not is_valid:
                messages.error(request, msg)
            else:
                upi_obj.set_pin(new_pin)
                upi_obj.save(update_fields=['upi_pin_hash'])
                request.session.pop(session_flag, None)
                log_audit_event("PASSWORD_CHANGE", f"Reset UPI PIN via OTP for {upi_obj.upi_id}", user=request.user, request=request)
                send_notification(request.user, "UPI PIN Reset Successful", f"Your 4-digit UPI PIN for {upi_obj.upi_id} was reset successfully.", "SECURITY")
                messages.success(request, f"UPI PIN for {upi_obj.upi_id} has been reset to 4 digits successfully!")
                return redirect('upi:home')
    else:
        form = ForgotUPIPINForm()

    return render(request, 'upi/forgot_pin.html', {
        'form': form,
        'upi_obj': upi_obj,
        'masked_email': masked_email,
    })
