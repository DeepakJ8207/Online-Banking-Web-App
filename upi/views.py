from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
import io
import qrcode
from .models import UPIAccount, UPITransaction
from .forms import CreateUPIForm, ChangeUPIPINForm
from banking.models import BankAccount
from accounts.services import log_audit_event, send_notification

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
