from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.http import HttpResponse, Http404
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from banking.models import BankAccount
from .models import Transaction
from .pdf_generator import generate_account_statement_pdf
from accounts.services import log_audit_event

@login_required
def transaction_history_view(request):
    """
    Searchable, filterable, paginated transaction history ledger.
    """
    user_accounts = BankAccount.objects.filter(user=request.user)
    account_id = request.GET.get('account')
    flow_type = request.GET.get('flow', 'ALL')  # ALL, CREDIT, DEBIT
    txn_type = request.GET.get('type', '')
    status = request.GET.get('status', '')
    q = request.GET.get('q', '').strip()
    from_date_str = request.GET.get('from_date', '')
    to_date_str = request.GET.get('to_date', '')
    min_amount = request.GET.get('min_amount', '')
    max_amount = request.GET.get('max_amount', '')

    selected_account = None
    if account_id:
        selected_account = user_accounts.filter(id=account_id).first()

    # Base query for all transactions where user's accounts are involved
    if selected_account:
        base_qs = Transaction.objects.filter(
            Q(sender_account=selected_account) | Q(receiver_account=selected_account)
        )
    else:
        base_qs = Transaction.objects.filter(
            Q(sender_account__user=request.user) | Q(receiver_account__user=request.user)
        )

    # Filter flow: Credit / Debit
    if flow_type == 'CREDIT':
        if selected_account:
            base_qs = base_qs.filter(receiver_account=selected_account)
        else:
            base_qs = base_qs.filter(receiver_account__user=request.user)
    elif flow_type == 'DEBIT':
        if selected_account:
            base_qs = base_qs.filter(sender_account=selected_account)
        else:
            base_qs = base_qs.filter(sender_account__user=request.user)

    # Filter Type
    if txn_type:
        base_qs = base_qs.filter(transaction_type=txn_type)

    # Filter Status
    if status:
        base_qs = base_qs.filter(status=status)

    # Filter Search Query
    if q:
        base_qs = base_qs.filter(
            Q(transaction_id__icontains=q) |
            Q(reference_number__icontains=q) |
            Q(sender_name__icontains=q) |
            Q(receiver_name__icontains=q) |
            Q(remarks__icontains=q)
        )

    # Date filters
    if from_date_str:
        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d')
            base_qs = base_qs.filter(timestamp__gte=from_date)
        except ValueError:
            pass

    if to_date_str:
        try:
            to_date = datetime.strptime(to_date_str, '%Y-%m-%d') + timedelta(days=1)
            base_qs = base_qs.filter(timestamp__lt=to_date)
        except ValueError:
            pass

    # Amount filters
    if min_amount:
        try:
            base_qs = base_qs.filter(amount__gte=Decimal(min_amount))
        except Exception:
            pass

    if max_amount:
        try:
            base_qs = base_qs.filter(amount__lte=Decimal(max_amount))
        except Exception:
            pass

    # Calculate summary metrics
    total_debits = Decimal('0.00')
    total_credits = Decimal('0.00')
    
    # User's debit totals
    debit_txns = base_qs.filter(sender_account__user=request.user, status='SUCCESS')
    if debit_txns.exists():
        total_debits = debit_txns.aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

    credit_txns = base_qs.filter(receiver_account__user=request.user, status='SUCCESS')
    if credit_txns.exists():
        total_credits = credit_txns.aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

    paginator = Paginator(base_qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'transactions/history.html', {
        'page_obj': page_obj,
        'user_accounts': user_accounts,
        'selected_account': selected_account,
        'flow_type': flow_type,
        'txn_type': txn_type,
        'status': status,
        'q': q,
        'from_date': from_date_str,
        'to_date': to_date_str,
        'min_amount': min_amount,
        'max_amount': max_amount,
        'total_debits': total_debits,
        'total_credits': total_credits,
        'total_count': paginator.count,
    })


@login_required
def transaction_detail_view(request, transaction_id):
    """
    Detailed single transaction view.
    """
    txn = get_object_or_404(
        Transaction,
        Q(sender_account__user=request.user) | Q(receiver_account__user=request.user),
        transaction_id=transaction_id
    )
    is_sender = (txn.sender_account and txn.sender_account.user == request.user)
    return render(request, 'transactions/detail.html', {'txn': txn, 'is_sender': is_sender})


@login_required
def download_statement_pdf_view(request):
    """
    Generates and downloads a ReportLab PDF account statement.
    """
    account_id = request.GET.get('account_id')
    user_accounts = BankAccount.objects.filter(user=request.user)

    if account_id:
        account = get_object_or_404(user_accounts, id=account_id)
    else:
        account = user_accounts.first()
        if not account:
            messages.error(request, "No active bank account found to generate statement.")
            return redirect('dashboard:home')

    # Parse date range
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')

    if from_date_str:
        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        except ValueError:
            from_date = (timezone.now() - timedelta(days=30)).date()
    else:
        from_date = (timezone.now() - timedelta(days=30)).date()

    if to_date_str:
        try:
            to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
        except ValueError:
            to_date = timezone.now().date()
    else:
        to_date = timezone.now().date()

    # Query account transactions
    txns = Transaction.objects.filter(
        Q(sender_account=account) | Q(receiver_account=account),
        timestamp__date__gte=from_date,
        timestamp__date__lte=to_date,
        status='SUCCESS'
    ).order_by('timestamp')

    pdf_content = generate_account_statement_pdf(account, txns, from_date, to_date)

    log_audit_event("STATEMENT_DOWNLOAD", f"Generated PDF account statement for A/c {account.account_number} ({from_date} to {to_date})", user=request.user, request=request)

    response = HttpResponse(pdf_content, content_type='application/pdf')
    filename = f"PRMB_Statement_{account.account_number}_{from_date}_{to_date}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
