from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import BankAccount
from transactions.models import Transaction
from accounts.services import log_audit_event, send_notification

@login_required
def my_account_view(request):
    """
    Overview of all bank accounts belonging to the logged-in user.
    """
    accounts = BankAccount.objects.filter(user=request.user)
    profile = getattr(request.user, 'profile', None)
    return render(request, 'account/my_account.html', {
        'accounts': accounts,
        'profile': profile
    })


@login_required
def account_details_view(request, account_id):
    """
    Detailed information for a specific bank account.
    """
    account = get_object_or_404(BankAccount, id=account_id, user=request.user)
    
    # Recent transactions for this specific account
    recent_txns = Transaction.objects.filter(
        models_Q_sender_or_receiver(account)
    )[:10]

    return render(request, 'account/account_details.html', {
        'account': account,
        'recent_transactions': recent_txns
    })

def models_Q_sender_or_receiver(account):
    from django.db.models import Q
    return Q(sender_account=account) | Q(receiver_account=account)


@login_required
def change_pin_view(request, account_id):
    """
    Set or update 4-digit Transaction PIN.
    """
    account = get_object_or_404(BankAccount, id=account_id, user=request.user)

    if request.method == 'POST':
        old_pin = request.POST.get('old_pin', '').strip()
        new_pin = request.POST.get('new_pin', '').strip()
        confirm_pin = request.POST.get('confirm_pin', '').strip()

        if account.transaction_pin_hash and not account.check_transaction_pin(old_pin):
            messages.error(request, "Incorrect current Transaction PIN.")
        elif not (len(new_pin) == 4 and new_pin.isdigit()):
            messages.error(request, "New Transaction PIN must be exactly 4 numeric digits.")
        elif new_pin != confirm_pin:
            messages.error(request, "New PIN and confirmation PIN do not match.")
        else:
            account.set_transaction_pin(new_pin)
            account.save(update_fields=['transaction_pin_hash'])
            log_audit_event("PASSWORD_CHANGE", f"Transaction PIN updated for account {account.account_number}", user=request.user, request=request)
            send_notification(request.user, "Transaction PIN Changed", f"Transaction PIN for A/c {account.masked_account_number()} updated successfully.", "SECURITY")
            messages.success(request, "Transaction PIN updated successfully!")
            return redirect('banking:account_details', account_id=account.id)

    return render(request, 'account/change_pin.html', {'account': account})
