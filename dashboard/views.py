from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q, Sum, Count
from datetime import timedelta
from decimal import Decimal
from banking.models import BankAccount
from transactions.models import Transaction
from beneficiaries.models import Beneficiary
from upi.models import UPIAccount
from accounts.models import AuditLog, Notification
from finance.models import FixedDeposit, RecurringDeposit, Loan
from accounts.services import log_audit_event, send_notification


@login_required
def dashboard_home_view(request):
    """
    Personalized Main Internet Banking Dashboard.
    """
    user = request.user
    accounts = BankAccount.objects.filter(user=user, status='ACTIVE')
    primary_account = accounts.first()

    # If admin user with no personal bank account logs into dashboard, redirect to Custom Admin Overview
    if (user.is_staff or user.is_superuser) and not primary_account:
        return redirect('admin_dashboard:overview')

    # Time-based greeting
    now_hour = timezone.localtime().hour
    if now_hour < 12:
        greeting = "Good Morning"
    elif now_hour < 17:
        greeting = "Good Afternoon"
    else:
        greeting = "Good Evening"

    # Financial Aggregations
    total_balance = accounts.aggregate(total=Sum('balance'))['total'] or Decimal('0.00')

    # Current month credit and debit
    first_day_of_month = timezone.now().date().replace(day=1)
    
    monthly_credits = Transaction.objects.filter(
        receiver_account__user=user,
        timestamp__date__gte=first_day_of_month,
        status='SUCCESS'
    ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

    monthly_debits = Transaction.objects.filter(
        sender_account__user=user,
        timestamp__date__gte=first_day_of_month,
        status='SUCCESS'
    ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

    # Recent Transactions
    recent_transactions = Transaction.objects.filter(
        Q(sender_account__user=user) | Q(receiver_account__user=user)
    ).order_by('-timestamp')[:6]

    # Quick Beneficiaries
    quick_beneficiaries = Beneficiary.objects.filter(user=user, is_active=True)[:4]

    # Last login info
    last_login_audit = AuditLog.objects.filter(user=user, action='LOGIN').order_by('-timestamp')
    last_login_time = last_login_audit[1].timestamp if last_login_audit.count() > 1 else timezone.now()

    # User's primary UPI
    primary_upi = UPIAccount.objects.filter(user=user, is_primary=True).first()

    return render(request, 'dashboard/dashboard.html', {
        'greeting': greeting,
        'accounts': accounts,
        'primary_account': primary_account,
        'total_balance': total_balance,
        'monthly_credits': monthly_credits,
        'monthly_debits': monthly_debits,
        'recent_transactions': recent_transactions,
        'quick_beneficiaries': quick_beneficiaries,
        'last_login_time': last_login_time,
        'primary_upi': primary_upi,
    })


@login_required
def dashboard_analytics_api(request):
    """
    Dynamic Chart.js Financial Analytics API generated from MySQL database for customer portal.
    """
    user = request.user
    today = timezone.now().date()

    # 1. Last 6 Months Income vs Expense
    months_labels = []
    income_data = []
    expense_data = []

    for i in range(5, -1, -1):
        month_target = (today.replace(day=1) - timedelta(days=i * 28)).replace(day=1)
        next_month = (month_target + timedelta(days=32)).replace(day=1)
        month_name = month_target.strftime('%b %Y')
        months_labels.append(month_name)

        inc = Transaction.objects.filter(
            receiver_account__user=user,
            timestamp__date__gte=month_target,
            timestamp__date__lt=next_month,
            status='SUCCESS'
        ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

        exp = Transaction.objects.filter(
            sender_account__user=user,
            timestamp__date__gte=month_target,
            timestamp__date__lt=next_month,
            status='SUCCESS'
        ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

        income_data.append(float(inc))
        expense_data.append(float(exp))

    # 2. Overall Credit vs Debit
    tot_credits = Transaction.objects.filter(
        receiver_account__user=user,
        status='SUCCESS'
    ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

    tot_debits = Transaction.objects.filter(
        sender_account__user=user,
        status='SUCCESS'
    ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

    # 3. Category-wise Spending Breakdown
    categories = ['TRANSFER', 'BILLS', 'SHOPPING', 'INVESTMENT', 'FOOD', 'LOAN', 'OTHER']
    category_labels = ['Transfers', 'Bills & Recharge', 'Shopping', 'Investments', 'Food & Dining', 'Loans & EMI', 'Other']
    category_values = []

    for cat in categories:
        val = Transaction.objects.filter(
            sender_account__user=user,
            category=cat,
            status='SUCCESS'
        ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
        category_values.append(float(val))

    # If all category values are 0, add demo distribution placeholder for visual beauty
    if sum(category_values) == 0:
        category_values = [40, 25, 15, 10, 5, 5, 0]

    return JsonResponse({
        'monthly_labels': months_labels,
        'monthly_income': income_data,
        'monthly_expense': expense_data,
        'credit_total': float(tot_credits),
        'debit_total': float(tot_debits),
        'category_labels': category_labels,
        'category_values': category_values
    })


@login_required
def admin_overview_view(request):
    """
    Dedicated Bank Manager / Custom Admin Overview Portal at /admin-dashboard/.
    Allows staff/admin to view all user balances, account statuses,
    live master transaction feed, FD & RD portfolios, and audit trails.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.warning(request, "Staff privileges required to access the Custom Admin Dashboard.")
        return redirect('dashboard:home')

    today = timezone.now().date()
    
    # 1. Bank Statistics
    total_customers = BankAccount.objects.values('user').distinct().count()
    total_accounts = BankAccount.objects.count()
    total_deposits = BankAccount.objects.filter(status='ACTIVE').aggregate(total=Sum('balance'))['total'] or Decimal('0.00')
    
    today_transactions = Transaction.objects.filter(timestamp__date=today, status='SUCCESS')
    today_volume = today_transactions.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    today_count = today_transactions.count()
    
    total_transactions_count = Transaction.objects.count()

    # 2. Customer Accounts & Balances with Search
    account_search = request.GET.get('account_q', '').strip()
    accounts_qs = BankAccount.objects.select_related('user', 'branch', 'user__profile').order_by('-balance')
    
    if account_search:
        accounts_qs = accounts_qs.filter(
            Q(account_number__icontains=account_search) |
            Q(user__username__icontains=account_search) |
            Q(user__first_name__icontains=account_search) |
            Q(user__last_name__icontains=account_search) |
            Q(user__email__icontains=account_search)
        )

    # 3. Master Transaction Feed with Filters & Search
    tx_search = request.GET.get('tx_q', '').strip()
    tx_status = request.GET.get('status', '').strip()
    tx_type = request.GET.get('type', '').strip()
    
    transactions_qs = Transaction.objects.select_related(
        'sender_account__user', 
        'receiver_account__user',
        'sender_account__branch'
    ).order_by('-timestamp')

    if tx_search:
        transactions_qs = transactions_qs.filter(
            Q(reference_number__icontains=tx_search) |
            Q(transaction_id__icontains=tx_search) |
            Q(sender_account__account_number__icontains=tx_search) |
            Q(receiver_account__account_number__icontains=tx_search) |
            Q(sender_account__user__username__icontains=tx_search) |
            Q(receiver_account__user__username__icontains=tx_search) |
            Q(sender_name__icontains=tx_search) |
            Q(receiver_name__icontains=tx_search) |
            Q(remarks__icontains=tx_search)
        )

    if tx_status:
        transactions_qs = transactions_qs.filter(status=tx_status)

    if tx_type:
        transactions_qs = transactions_qs.filter(transaction_type=tx_type)

    recent_txs = transactions_qs[:50]

    # 4. Fixed Deposits & Recurring Deposits
    fixed_deposits = FixedDeposit.objects.select_related('user', 'linked_account').order_by('-created_at')[:20]
    recurring_deposits = RecurringDeposit.objects.select_related('user', 'linked_account').order_by('-created_at')[:20]
    total_fd_volume = FixedDeposit.objects.filter(status='ACTIVE').aggregate(s=Sum('principal_amount'))['s'] or Decimal('0.00')

    # 5. Loans
    active_loans = Loan.objects.select_related('user', 'loan_product', 'disbursal_account').order_by('-created_at')[:20]

    # 6. Audit Trail Feed
    audit_logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:30]

    context = {
        'total_customers': total_customers,
        'total_accounts': total_accounts,
        'total_deposits': total_deposits,
        'today_volume': today_volume,
        'today_count': today_count,
        'total_transactions_count': total_transactions_count,
        'accounts': accounts_qs,
        'transactions': recent_txs,
        'fixed_deposits': fixed_deposits,
        'recurring_deposits': recurring_deposits,
        'total_fd_volume': total_fd_volume,
        'active_loans': active_loans,
        'audit_logs': audit_logs,
        'account_search': account_search,
        'tx_search': tx_search,
        'tx_status': tx_status,
        'tx_type': tx_type,
    }
    return render(request, 'dashboard/admin_overview.html', context)


@login_required
def admin_toggle_account_status_view(request, account_id):
    """
    Staff / Manager Action: Suspend or Activate a customer account.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Unauthorized.")
        return redirect('dashboard:home')

    account = get_object_or_404(BankAccount, id=account_id)
    if account.status == 'ACTIVE':
        account.status = 'FROZEN'
        msg = f"Account {account.masked_account_number()} has been suspended / frozen."
    else:
        account.status = 'ACTIVE'
        msg = f"Account {account.masked_account_number()} has been activated."

    account.save(update_fields=['status', 'updated_at'])
    log_audit_event("ADMIN_ACCOUNT_STATUS_CHANGE", f"Admin {request.user.username} toggled status of A/c {account.account_number} to {account.status}", user=request.user, request=request)
    send_notification(account.user, "Account Status Updated", f"Your bank account {account.masked_account_number()} status is now {account.status}.", "INFO")
    messages.success(request, msg)
    return redirect('admin_dashboard:overview')


@login_required
def admin_close_fd_view(request, fd_id):
    """
    Staff / Manager Action: Prematurely close or liquidate an active FD.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Unauthorized.")
        return redirect('dashboard:home')

    fd = get_object_or_404(FixedDeposit, id=fd_id, status='ACTIVE')
    fd.status = 'CLOSED'
    fd.save(update_fields=['status', 'updated_at'])

    # Refund principal back to linked account
    acc = fd.linked_account
    acc.balance += fd.principal_amount
    acc.save(update_fields=['balance', 'updated_at'])

    log_audit_event("ADMIN_FD_CLOSE", f"Admin closed FD {fd.fd_number}, refunded ₹{fd.principal_amount} to A/c {acc.account_number}", user=request.user, request=request)
    send_notification(fd.user, "Fixed Deposit Closed", f"Your Fixed Deposit {fd.fd_number} was closed and ₹{fd.principal_amount:,.2f} refunded to your account.", "INFO")
    messages.success(request, f"Fixed Deposit {fd.fd_number} closed successfully. Funds refunded to customer account.")
    return redirect('admin_dashboard:overview')


@login_required
def admin_analytics_api(request):
    """
    Dynamic analytics API for Custom Admin Dashboard Charts.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    today = timezone.now().date()
    days_labels = []
    volume_data = []

    for i in range(6, -1, -1):
        target_day = today - timedelta(days=i)
        day_str = target_day.strftime('%d %b')
        days_labels.append(day_str)

        vol = Transaction.objects.filter(
            timestamp__date=target_day,
            status='SUCCESS'
        ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
        volume_data.append(float(vol))

    # Credit vs Debit
    tot_credits = Transaction.objects.filter(transaction_type__in=['DEPOSIT', 'CREDIT', 'SALARY'], status='SUCCESS').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
    tot_debits = Transaction.objects.filter(transaction_type__in=['IMPS', 'NEFT', 'RTGS', 'UPI', 'BILL_PAYMENT'], status='SUCCESS').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

    return JsonResponse({
        'days_labels': days_labels,
        'volume_data': volume_data,
        'credit_total': float(tot_credits),
        'debit_total': float(tot_debits)
    })
