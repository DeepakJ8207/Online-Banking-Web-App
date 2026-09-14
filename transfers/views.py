from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from banking.models import BankAccount
from beneficiaries.models import Beneficiary
from transactions.models import Transaction
from upi.models import UPIAccount, UPITransaction
from accounts.models import CustomerProfile
from .forms import BankTransferForm, MobileTransferForm, UPITransferForm, SelfTransferForm
from .services import TransferService
from accounts.services import log_audit_event

@login_required
def transfer_home_view(request):
    """
    Payments and Transfers central portal.
    """
    accounts = BankAccount.objects.filter(user=request.user, status='ACTIVE')
    beneficiaries = Beneficiary.objects.filter(user=request.user, is_active=True)[:6]
    recent_transfers = Transaction.objects.filter(
        Q(sender_account__user=request.user) | Q(receiver_account__user=request.user)
    )[:5]

    return render(request, 'transfers/transfer_home.html', {
        'accounts': accounts,
        'beneficiaries': beneficiaries,
        'recent_transfers': recent_transfers
    })


@login_required
def bank_transfer_view(request):
    """
    Transfer funds to any Bank Account via IMPS / NEFT simulation.
    """
    prefill_bene_id = request.GET.get('bene_id')
    initial_data = {}
    if prefill_bene_id:
        bene = Beneficiary.objects.filter(id=prefill_bene_id, user=request.user).first()
        if bene:
            initial_data = {
                'beneficiary': bene.id,
                'receiver_account_number': bene.account_number,
                'receiver_ifsc': bene.ifsc_code,
                'receiver_name': bene.beneficiary_name
            }

    if request.method == 'POST':
        form = BankTransferForm(request.POST, user=request.user)
        if form.is_valid():
            sender_acc = form.cleaned_data['sender_account']
            receiver_acc_no = form.cleaned_data['receiver_account_number'].strip()
            receiver_ifsc = form.cleaned_data['receiver_ifsc'].strip().upper()
            receiver_name = form.cleaned_data['receiver_name'].strip()
            amount = form.cleaned_data['amount']
            remarks = form.cleaned_data.get('remarks') or 'Bank Transfer'
            txn_pin = form.cleaned_data['transaction_pin']

            # Verify transaction PIN
            if not sender_acc.check_transaction_pin(txn_pin):
                messages.error(request, "Invalid Transaction PIN.")
                return render(request, 'transfers/bank_transfer.html', {'form': form})

            # Execute Transfer
            success, msg, txn = TransferService.execute_transfer(
                sender_account_id=sender_acc.id,
                amount=amount,
                transfer_type='BANK_TRANSFER',
                receiver_account_number=receiver_acc_no,
                receiver_ifsc=receiver_ifsc,
                receiver_name=receiver_name,
                remarks=remarks,
                category='TRANSFER',
                user=request.user,
                request=request
            )

            if success and txn:
                messages.success(request, f"₹{amount:,.2f} transferred successfully to {receiver_name}!")
                return redirect('transfers:receipt', transaction_id=txn.transaction_id)
            else:
                messages.error(request, msg)
    else:
        form = BankTransferForm(user=request.user, initial=initial_data)

    return render(request, 'transfers/bank_transfer.html', {'form': form})


@login_required
def mobile_transfer_view(request):
    """
    Transfer funds instantly to any registered Mobile Number.
    """
    if request.method == 'POST':
        form = MobileTransferForm(request.POST, user=request.user)
        if form.is_valid():
            sender_acc = form.cleaned_data['sender_account']
            mobile = form.cleaned_data['mobile_number'].strip()
            amount = form.cleaned_data['amount']
            remarks = form.cleaned_data.get('remarks') or 'Mobile Quick Transfer'
            txn_pin = form.cleaned_data['transaction_pin']

            if not sender_acc.check_transaction_pin(txn_pin):
                messages.error(request, "Invalid Transaction PIN.")
                return render(request, 'transfers/mobile_transfer.html', {'form': form})

            # Check if mobile exists in Prime Reserve Bank
            dest_profile = CustomerProfile.objects.filter(phone_number=mobile).first()
            receiver_acc_no = None
            receiver_name = f"Mobile {mobile}"

            if dest_profile:
                dest_account = BankAccount.objects.filter(user=dest_profile.user, status='ACTIVE').first()
                if dest_account:
                    receiver_acc_no = dest_account.account_number
                    receiver_name = dest_profile.user.get_full_name() or dest_profile.user.username

            success, msg, txn = TransferService.execute_transfer(
                sender_account_id=sender_acc.id,
                amount=amount,
                transfer_type='MOBILE_TRANSFER',
                receiver_account_number=receiver_acc_no,
                receiver_name=receiver_name,
                remarks=remarks,
                category='TRANSFER',
                user=request.user,
                request=request
            )

            if success and txn:
                messages.success(request, f"₹{amount:,.2f} sent successfully to {receiver_name}!")
                return redirect('transfers:receipt', transaction_id=txn.transaction_id)
            else:
                messages.error(request, msg)
    else:
        form = MobileTransferForm(user=request.user)

    return render(request, 'transfers/mobile_transfer.html', {'form': form})


@login_required
def upi_transfer_view(request):
    """
    Transfer funds to any Virtual Payment Address (UPI ID).
    """
    prefill_vpa = request.GET.get('upi_id', '')
    if request.method == 'POST':
        form = UPITransferForm(request.POST, user=request.user)
        if form.is_valid():
            sender_acc = form.cleaned_data['sender_account']
            target_vpa = form.cleaned_data['upi_id'].strip().lower()
            amount = form.cleaned_data['amount']
            remarks = form.cleaned_data.get('remarks') or 'UPI Payment'
            upi_pin = form.cleaned_data['upi_pin']

            # Check sender's UPI PIN
            user_upi = UPIAccount.objects.filter(user=request.user, bank_account=sender_acc).first()
            if user_upi and not user_upi.check_pin(upi_pin):
                messages.error(request, "Invalid UPI PIN.")
                return render(request, 'transfers/upi_transfer.html', {'form': form})
            elif not user_upi and not sender_acc.check_transaction_pin(upi_pin):
                messages.error(request, "Invalid PIN.")
                return render(request, 'transfers/upi_transfer.html', {'form': form})

            # Check if destination UPI exists
            dest_upi = UPIAccount.objects.filter(upi_id__iexact=target_vpa, is_active=True).first()
            receiver_acc_no = None
            receiver_name = target_vpa

            if dest_upi:
                receiver_acc_no = dest_upi.bank_account.account_number
                receiver_name = f"{dest_upi.user.get_full_name() or dest_upi.user.username} ({target_vpa})"

            success, msg, txn = TransferService.execute_transfer(
                sender_account_id=sender_acc.id,
                amount=amount,
                transfer_type='UPI_TRANSFER',
                receiver_account_number=receiver_acc_no,
                receiver_name=receiver_name,
                remarks=remarks,
                category='TRANSFER',
                user=request.user,
                request=request
            )

            if success and txn:
                UPITransaction.objects.create(
                    transaction=txn,
                    sender_upi_id=user_upi.upi_id if user_upi else f"{request.user.username}@primereserve",
                    receiver_upi_id=target_vpa,
                    npci_simulated_ref=f"NPCI{txn.reference_number}"
                )
                messages.success(request, f"UPI transfer of ₹{amount:,.2f} to {target_vpa} completed successfully!")
                return redirect('transfers:receipt', transaction_id=txn.transaction_id)
            else:
                messages.error(request, msg)
    else:
        form = UPITransferForm(user=request.user, initial={'upi_id': prefill_vpa})

    return render(request, 'transfers/upi_transfer.html', {'form': form})


@login_required
def self_transfer_view(request):
    """
    Transfer money between logged-in user's own accounts.
    """
    if request.method == 'POST':
        form = SelfTransferForm(request.POST, user=request.user)
        if form.is_valid():
            from_acc = form.cleaned_data['from_account']
            to_acc = form.cleaned_data['to_account']
            amount = form.cleaned_data['amount']
            remarks = form.cleaned_data.get('remarks') or 'Self Account Transfer'
            txn_pin = form.cleaned_data['transaction_pin']

            if not from_acc.check_transaction_pin(txn_pin):
                messages.error(request, "Invalid Transaction PIN.")
                return render(request, 'transfers/self_transfer.html', {'form': form})

            success, msg, txn = TransferService.execute_transfer(
                sender_account_id=from_acc.id,
                amount=amount,
                transfer_type='SELF_TRANSFER',
                receiver_account_number=to_acc.account_number,
                receiver_name=f"My {to_acc.get_account_type_display()} ({to_acc.masked_account_number()})",
                remarks=remarks,
                category='TRANSFER',
                user=request.user,
                request=request
            )

            if success and txn:
                messages.success(request, f"Self-transfer of ₹{amount:,.2f} completed successfully!")
                return redirect('transfers:receipt', transaction_id=txn.transaction_id)
            else:
                messages.error(request, msg)
    else:
        form = SelfTransferForm(user=request.user)

    return render(request, 'transfers/self_transfer.html', {'form': form})


@login_required
def transfer_receipt_view(request, transaction_id):
    """
    Printable & downloadable transaction receipt confirmation.
    """
    txn = get_object_or_404(
        Transaction,
        Q(sender_account__user=request.user) | Q(receiver_account__user=request.user),
        transaction_id=transaction_id
    )
    is_sender = (txn.sender_account and txn.sender_account.user == request.user)
    return render(request, 'transfers/receipt.html', {
        'txn': txn,
        'is_sender': is_sender
    })
