from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from .models import BillerCategory, Biller, BillPayment
from .forms import BillPaymentForm
from banking.models import BankAccount
from transfers.services import TransferService
from accounts.services import log_audit_event, send_notification

@login_required
def bills_home_view(request):
    """
    Utility Bill Payments and Mobile Recharges Hub.
    """
    categories = BillerCategory.objects.all()
    recent_payments = BillPayment.objects.filter(user=request.user)[:5]

    return render(request, 'bills/bills_home.html', {
        'categories': categories,
        'recent_payments': recent_payments
    })


@login_required
def pay_bill_view(request, category_code=None):
    """
    Pay utility bill or mobile recharge.
    """
    category = None
    if category_code:
        category = get_object_or_404(BillerCategory, code__iexact=category_code)

    if request.method == 'POST':
        form = BillPaymentForm(request.POST, user=request.user, category_code=category.code if category else None)
        if form.is_valid():
            sender_acc = form.cleaned_data['source_account']
            biller = form.cleaned_data['biller']
            consumer_no = form.cleaned_data['consumer_number'].strip()
            amount = form.cleaned_data['amount']
            txn_pin = form.cleaned_data['transaction_pin']

            # Check transaction PIN
            if not sender_acc.check_transaction_pin(txn_pin):
                messages.error(request, "Invalid Transaction PIN.")
                return render(request, 'bills/pay_bill.html', {'form': form, 'category': category})

            # Determine transaction type
            txn_type = 'RECHARGE' if biller.category.code == 'MOBILE_RECHARGE' else 'BILL_PAYMENT'

            success, msg, txn = TransferService.execute_transfer(
                sender_account_id=sender_acc.id,
                amount=amount,
                transfer_type=txn_type,
                receiver_name=f"{biller.name} ({consumer_no})",
                remarks=f"Bill Payment: {biller.name} - Ref {consumer_no}",
                category='BILLS',
                user=request.user,
                request=request
            )

            if success and txn:
                bill_payment = BillPayment.objects.create(
                    user=request.user,
                    bank_account=sender_acc,
                    biller=biller,
                    consumer_number=consumer_no,
                    amount=amount,
                    transaction=txn,
                    biller_status='SUCCESS'
                )

                log_audit_event("BILL_PAYMENT", f"Paid ₹{amount} for {biller.name} (Consumer No: {consumer_no})", user=request.user, request=request)
                send_notification(request.user, "Bill Payment Successful", f"₹{amount:,.2f} paid for {biller.name} ({consumer_no}). Receipt No: {bill_payment.receipt_number}", "SUCCESS")
                messages.success(request, f"Payment of ₹{amount:,.2f} for {biller.name} successful!")
                return redirect('bills:receipt', receipt_number=bill_payment.receipt_number)
            else:
                messages.error(request, msg)
    else:
        form = BillPaymentForm(user=request.user, category_code=category.code if category else None)

    return render(request, 'bills/pay_bill.html', {
        'form': form,
        'category': category
    })


@login_required
def bill_receipt_view(request, receipt_number):
    """
    Printable and downloadable Bill Payment Receipt.
    """
    bill = get_object_or_404(BillPayment, receipt_number=receipt_number, user=request.user)
    return render(request, 'bills/receipt.html', {'bill': bill})
