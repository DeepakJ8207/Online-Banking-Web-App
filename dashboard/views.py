from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q, Sum, Count
from datetime import timedelta
from decimal import Decimal
import random
import uuid
import logging
from django.core.mail import send_mail
from django.conf import settings

from banking.models import BankAccount
from transactions.models import Transaction
from beneficiaries.models import Beneficiary
from upi.models import UPIAccount
from accounts.models import CustomerProfile, Branch, AuditLog, Notification, OTPVerification
from accounts.forms import AdminCustomerRegistrationForm
from finance.models import FixedDeposit, RecurringDeposit, Loan, LoanProduct, LoanRepayment
from accounts.services import log_audit_event, send_notification

logger = logging.getLogger(__name__)


def generate_unique_cif():
    """Generates an 11-digit unique Customer Identification File (CIF) number."""
    while True:
        cif = f"98{random.randint(100000000, 999999999)}"
        if not CustomerProfile.objects.filter(cif_number=cif).exists():
            return cif


def generate_unique_account_number(branch=None):
    """Generates a 14-digit unique Bank Account Number."""
    prefix = branch.code if (branch and hasattr(branch, 'code') and branch.code) else "1001"
    prefix = (str(prefix) + "0000")[:4]
    while True:
        mid = random.randint(10000, 99999)
        suffix = random.randint(10000, 99999)
        acc_num = f"{prefix}{mid}{suffix}"[:14]
        if not BankAccount.objects.filter(account_number=acc_num).exists():
            return acc_num


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

    # Time-based greeting (Asia/Kolkata / local time)
    now_hour = timezone.localtime().hour
    if now_hour >= 21 or now_hour < 5:
        greeting = "Good Night"
    elif now_hour < 12:
        greeting = "Good Morning"
    elif now_hour < 17:
        greeting = "Good Afternoon"
    else:
        greeting = "Good Evening"

    # Financial Aggregations
    raw_balance = accounts.aggregate(total=Sum('balance'))['total'] or Decimal('0.00')
    total_balance = Decimal(f"{float(raw_balance):.2f}")

    # Current month credit and debit
    first_day_of_month = timezone.now().date().replace(day=1)
    
    raw_credits = Transaction.objects.filter(
        receiver_account__user=user,
        timestamp__date__gte=first_day_of_month,
        status='SUCCESS'
    ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
    monthly_credits = Decimal(f"{float(raw_credits):.2f}")

    raw_debits = Transaction.objects.filter(
        sender_account__user=user,
        timestamp__date__gte=first_day_of_month,
        status='SUCCESS'
    ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
    monthly_debits = Decimal(f"{float(raw_debits):.2f}")

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
def admin_overview_view(request, customer_form=None):
    """
    Dedicated Bank Manager / Custom Admin Overview Portal at /admin-dashboard/.
    Allows staff/admin to view all user balances, account statuses,
    live master transaction feed, FD & RD portfolios, and audit trails.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.warning(request, "Staff privileges required to access the Custom Admin Dashboard.")
        return redirect('dashboard:home')

    # Process any expired 7-day scheduled account deletions
    now = timezone.now()
    expired_accounts = BankAccount.objects.filter(is_scheduled_for_deletion=True, deletion_scheduled_for__lte=now)
    for exp_acc in expired_accounts:
        usr = exp_acc.user
        acct_num = exp_acc.account_number
        log_audit_event("AUTO_7DAY_ACCOUNT_DELETION", f"Account {acct_num} was automatically deleted upon expiry of 7-day notice period.", user=None)
        exp_acc.delete()
        if not usr.bank_accounts.exists() and not usr.is_staff and not usr.is_superuser:
            usr.delete()

    today = timezone.now().date()
    
    # 1. Bank Statistics
    total_customers = BankAccount.objects.values('user').distinct().count()
    total_accounts = BankAccount.objects.count()
    raw_deposits = BankAccount.objects.filter(status='ACTIVE').aggregate(total=Sum('balance'))['total'] or Decimal('0.00')
    total_deposits = Decimal(f"{float(raw_deposits):.2f}")
    
    today_transactions = Transaction.objects.filter(timestamp__date=today, status='SUCCESS')
    raw_volume = today_transactions.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    today_volume = Decimal(f"{float(raw_volume):.2f}")
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
    fixed_deposits = FixedDeposit.objects.select_related('user', 'linked_account').order_by('-created_at')[:50]
    recurring_deposits = RecurringDeposit.objects.select_related('user', 'linked_account').order_by('-created_at')[:50]
    raw_fd = FixedDeposit.objects.filter(status='ACTIVE').aggregate(s=Sum('principal_amount'))['s'] or Decimal('0.00')
    total_fd_volume = Decimal(f"{float(raw_fd):.2f}")
    raw_rd = RecurringDeposit.objects.filter(status='ACTIVE').aggregate(s=Sum('total_deposit'))['s'] or Decimal('0.00')
    total_rd_volume = Decimal(f"{float(raw_rd):.2f}")

    # 5. Loans
    active_loans = Loan.objects.select_related('user', 'loan_product', 'disbursal_account').order_by('-created_at')[:50]
    loan_products = LoanProduct.objects.filter(is_active=True)
    raw_loan = Loan.objects.filter(status='ACTIVE').aggregate(s=Sum('outstanding_balance'))['s'] or Decimal('0.00')
    total_loan_volume = Decimal(f"{float(raw_loan):.2f}")

    # 6. Audit Trail Feed
    audit_logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:30]

    # 7. Last registered customer info from session
    last_registered_customer = request.session.pop('last_registered_customer', None)
    customer_form = customer_form or AdminCustomerRegistrationForm()
    all_active_accounts = BankAccount.objects.filter(status='ACTIVE').select_related('user', 'branch').order_by('user__username')

    context = {
        'total_customers': total_customers,
        'total_accounts': total_accounts,
        'total_deposits': total_deposits,
        'today_volume': today_volume,
        'today_count': today_count,
        'total_transactions_count': total_transactions_count,
        'accounts': accounts_qs,
        'all_active_accounts': all_active_accounts,
        'transactions': recent_txs,
        'fixed_deposits': fixed_deposits,
        'recurring_deposits': recurring_deposits,
        'total_fd_volume': total_fd_volume,
        'total_rd_volume': total_rd_volume,
        'active_loans': active_loans,
        'loan_products': loan_products,
        'total_loan_volume': total_loan_volume,
        'audit_logs': audit_logs,
        'account_search': account_search,
        'tx_search': tx_search,
        'tx_status': tx_status,
        'tx_type': tx_type,
        'customer_form': customer_form,
        'last_registered_customer': last_registered_customer,
    }
    return render(request, 'dashboard/admin_overview.html', context)


@login_required
def admin_create_customer_view(request):
    """
    Handles in-branch customer creation submitted by Admin/Staff.
    Creates User, CustomerProfile, BankAccount, initial deposit Transaction,
    and dispatches full credentials via SMTP Email to the customer.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Staff privileges required to register customers.")
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = AdminCustomerRegistrationForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name'].strip()
            last_name = form.cleaned_data['last_name'].strip()
            username = form.cleaned_data['username'].strip()
            email = form.cleaned_data['email'].strip()
            phone_number = form.cleaned_data['phone_number'].strip()
            gender = form.cleaned_data.get('gender') or 'MALE'
            address = (form.cleaned_data.get('address') or '').strip()
            city = (form.cleaned_data.get('city') or '').strip()
            state = (form.cleaned_data.get('state') or '').strip()
            pincode = (form.cleaned_data.get('pincode') or '').strip()
            branch = form.cleaned_data['branch']
            account_type = form.cleaned_data['account_type']
            initial_deposit = form.cleaned_data['initial_deposit']
            initial_password = form.cleaned_data['initial_password']

            # Create User
            user = User.objects.create_user(
                username=username,
                email=email,
                password=initial_password,
                first_name=first_name,
                last_name=last_name
            )

            # Generate CIF & create Profile
            cif_number = generate_unique_cif()
            CustomerProfile.objects.create(
                user=user,
                cif_number=cif_number,
                phone_number=phone_number,
                gender=gender,
                address=address,
                city=city,
                state=state,
                pincode=pincode,
                kyc_status='VERIFIED',
                is_internet_banking_active=True,
                is_first_login=True,
                has_set_upi_pin=False
            )

            # Generate Account Number & create BankAccount
            account_number = generate_unique_account_number(branch)
            account = BankAccount.objects.create(
                user=user,
                account_number=account_number,
                account_type=account_type,
                balance=initial_deposit,
                branch=branch,
                status='ACTIVE'
            )

            # Record Initial Deposit Transaction
            Transaction.objects.create(
                transaction_type='DEPOSIT',
                amount=initial_deposit,
                status='SUCCESS',
                receiver_account=account,
                receiver_name=f"{first_name} {last_name}",
                remarks="Initial In-Branch Account Opening Deposit",
                reference_number=f"DEP-{uuid.uuid4().hex[:10].upper()}"
            )

            # Create notification
            send_notification(
                user=user,
                title="Welcome to Prime Reserve Bank!",
                message=f"Your {account.get_account_type_display()} #{account_number} has been opened with ₹{initial_deposit:,.2f} initial balance.",
                notification_type='ACCOUNT'
            )

            # Log Audit Trail
            log_audit_event(
                "CUSTOMER_ONBOARDED",
                f"Customer {username} (CIF: {cif_number}, A/c: {account_number}) registered by Manager {request.user.username}.",
                user=request.user
            )

            # Prepare Welcome & Credentials Email
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@primereservebank.demo')
            login_url = request.build_absolute_uri('/accounts/login/')
            subject = f"Welcome to Prime Reserve Bank — Account Credentials & Onboarding Details"
            
            body = f"""Dear {first_name} {last_name},

Welcome to Prime Reserve Bank! Your new bank account has been successfully opened and registered by our Central Branch Banking team.

ACCOUNT & SECURITY CREDENTIALS:
--------------------------------------------------
Customer Name      : {first_name} {last_name}
Customer ID (CIF)  : {cif_number}
Account Number     : {account_number}
Account Type       : {account.get_account_type_display()}
Branch / IFSC      : {branch.branch_name} ({branch.ifsc_code})
Initial Balance    : ₹{initial_deposit:,.2f}

LOGIN ACCESS DETAILS:
--------------------------------------------------
NetBanking User ID : {username}
Temporary Password : {initial_password}
Portal Login URL   : {login_url}

IMPORTANT NEXT STEPS (FIRST-TIME LOGIN):
1. Visit the Prime NetBanking portal at {login_url}
2. Log in using your User ID ({username}) and Temporary Password.
3. You will receive an Email OTP verification code to secure your session.
4. Set up your 6-Digit Secure UPI PIN for instant funds transfers.

SECURITY ADVISORY:
Prime Reserve Bank never asks for your passwords, OTP, or UPI PIN via phone or SMS. Please keep these credentials confidential.

Sincerely,
Prime Reserve Bank Onboarding & Operations
"""
            html_content = f"""
            <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;">
                <div style="background: linear-gradient(135deg, #0b1e36, #1e3a8a); padding: 30px; text-align: center; color: #ffffff;">
                    <div style="display: inline-block; background: #f59e0b; color: #0b1e36; font-size: 11px; font-weight: 800; padding: 4px 12px; border-radius: 20px; text-transform: uppercase; margin-bottom: 12px; letter-spacing: 1px;">Official Welcome Pack</div>
                    <h1 style="margin: 0; font-size: 24px; font-weight: 700; color: #ffffff;">Prime Reserve Bank</h1>
                    <p style="margin: 6px 0 0; font-size: 14px; opacity: 0.85;">Central Retail & Private Banking Infrastructure</p>
                </div>
                <div style="padding: 30px;">
                    <h2 style="font-size: 18px; color: #0b1e36; margin-top: 0;">Welcome, {first_name} {last_name}!</h2>
                    <p style="font-size: 14px; color: #475569; line-height: 1.6;">
                        Your Prime Reserve Bank account has been successfully opened and activated. Below are your official account details and secure NetBanking login credentials:
                    </p>
                    
                    <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin: 20px 0;">
                        <table style="width: 100%; font-size: 14px; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 6px 0; color: #64748b;">Customer CIF:</td>
                                <td style="padding: 6px 0; font-weight: 700; color: #0b1e36; font-family: monospace;">{cif_number}</td>
                            </tr>
                            <tr>
                                <td style="padding: 6px 0; color: #64748b;">Account Number:</td>
                                <td style="padding: 6px 0; font-weight: 700; color: #0b1e36; font-family: monospace; font-size: 16px;">{account_number}</td>
                            </tr>
                            <tr>
                                <td style="padding: 6px 0; color: #64748b;">Account Type:</td>
                                <td style="padding: 6px 0; font-weight: 600; color: #1e3a8a;">{account.get_account_type_display()}</td>
                            </tr>
                            <tr>
                                <td style="padding: 6px 0; color: #64748b;">Branch / IFSC:</td>
                                <td style="padding: 6px 0; color: #0b1e36;">{branch.branch_name} (<span style="font-family: monospace;">{branch.ifsc_code}</span>)</td>
                            </tr>
                            <tr>
                                <td style="padding: 6px 0; color: #64748b;">Opening Balance:</td>
                                <td style="padding: 6px 0; font-weight: 700; color: #10b981; font-size: 16px;">₹{initial_deposit:,.2f}</td>
                            </tr>
                        </table>
                    </div>

                    <div style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 15px; border-radius: 4px; margin-bottom: 24px;">
                        <div style="font-size: 13px; font-weight: 700; color: #1e40af; margin-bottom: 6px;">🔐 NETBANKING ACCESS CREDENTIALS</div>
                        <div style="font-size: 14px; color: #1e3a8a; margin-bottom: 4px;">User ID: <strong>{username}</strong></div>
                        <div style="font-size: 14px; color: #1e3a8a;">Temporary Password: <strong style="font-family: monospace; background: #dbeafe; padding: 2px 6px; border-radius: 4px;">{initial_password}</strong></div>
                    </div>

                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{login_url}" style="background: #1e3a8a; color: #ffffff; text-decoration: none; padding: 12px 30px; border-radius: 8px; font-weight: 700; font-size: 14px; display: inline-block;">Access NetBanking Portal</a>
                    </div>

                    <div style="background: #fffbeb; border: 1px solid #fef3c7; border-radius: 8px; padding: 15px; font-size: 12px; color: #92400e; line-height: 1.5;">
                        <strong>⚡ First-Time Security Setup:</strong><br>
                        Upon first login, an Email OTP will be sent to this email address for verification. You will also be prompted to generate your personalized 6-digit UPI PIN for seamless 24x7 transfers.
                    </div>
                </div>
                <div style="background: #f8fafc; padding: 20px; text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0;">
                    Prime Reserve Bank of India Ltd. • 24x7 Support: 1800-PRIME-BANK • Confidential & Encrypted
                </div>
            </div>
            """

            try:
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=from_email,
                    recipient_list=[email],
                    html_message=html_content,
                    fail_silently=False,
                )
                messages.success(
                    request,
                    f"Customer {first_name} {last_name} successfully registered! Account #{account_number} created with ₹{initial_deposit:,.2f} balance. Credentials sent to {email}."
                )
            except Exception as e:
                logger.error(f"Failed to send customer credentials email to {email}: {e}")
                messages.warning(
                    request,
                    f"Customer {first_name} {last_name} created successfully (Account #{account_number}), but email delivery failed: {e}"
                )

            request.session['last_registered_customer'] = {
                'name': f"{first_name} {last_name}",
                'username': username,
                'email': email,
                'cif': cif_number,
                'account_number': account_number,
                'branch': branch.branch_name,
                'initial_deposit': float(initial_deposit),
                'temporary_password': initial_password,
            }
            return redirect('admin_dashboard:overview')
        else:
            messages.error(request, "Please correct the errors in the customer registration form.")
            return admin_overview_view(request, customer_form=form)

    return redirect('admin_dashboard:overview')


@login_required
def admin_manage_account_action_view(request, account_id):
    """
    Advanced Account Management Actions:
    1. Suspend / Freeze account with reason + Email Notice
    2. Reactivate account + Email Notice
    3. Instant Permanent Account Deletion / Closure + Email Settlement Certificate
    4. 7-Day Auto-Deletion Notice + Scheduled Liquidation Email
    5. Cancel Scheduled Deletion + Email Notice
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Staff privileges required to manage accounts.")
        return redirect('dashboard:home')

    account = get_object_or_404(BankAccount, id=account_id)
    user = account.user
    customer_email = user.email
    customer_name = user.get_full_name() or user.username
    cif_no = user.profile.cif_number if hasattr(user, 'profile') else 'N/A'
    acct_no = account.account_number
    masked_acc = account.masked_account_number()
    current_balance = account.balance
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@primereservebank.demo')

    if request.method == 'POST':
        action_type = request.POST.get('action_type', '').strip()
        reason = request.POST.get('reason', '').strip() or 'Administrative Management Decision'

        # --- ACTION 1: SUSPEND / FREEZE ACCOUNT ---
        if action_type == 'suspend':
            account.status = 'BLOCKED'
            account.closure_reason = reason
            account.save(update_fields=['status', 'closure_reason', 'updated_at'])

            subject = f"PRIME RESERVE BANK — Notice: Account {masked_acc} Temporarily Suspended"
            body = f"""Dear {customer_name},

This is an official communication regarding your Prime Reserve Bank account {masked_acc} (CIF: {cif_no}).

Your bank account has been TEMPORARILY SUSPENDED / FROZEN by our Central Bank Operations team.

DETAILS OF SUSPENSION:
--------------------------------------------------
Account Number     : {acct_no}
Account Holder     : {customer_name}
Current Balance    : ₹{current_balance:,.2f}
Reason for Action  : {reason}
Effective Date     : {timezone.now().strftime('%d %B %Y, %I:%M %p')}

IMPACT ON YOUR SERVICES:
- Outgoing IMPS, NEFT, RTGS, and UPI fund transfers are temporarily restricted.
- Scheduled bill payments and standing instructions have been paused.
- Your funds (₹{current_balance:,.2f}) remain securely deposited in our vault.

HOW TO REACTIVATE YOUR ACCOUNT:
Please visit your nearest Prime Reserve Bank branch ({account.branch.branch_name}) along with your original KYC identity documents (PAN Card / Aadhaar Card) or contact our 24x7 helpline to resolve this suspension.

Sincerely,
Prime Reserve Bank Surveillance & Risk Operations
"""
            try:
                if customer_email:
                    send_mail(subject, body, from_email, [customer_email], fail_silently=True)
            except Exception as e:
                logger.warning(f"Suspension email failed: {e}")

            log_audit_event("ADMIN_SUSPEND_ACCOUNT", f"Admin {request.user.username} suspended A/c {acct_no} for {user.username}. Reason: {reason}", user=request.user, request=request)
            send_notification(user, "Account Suspended", f"Your bank account {masked_acc} has been suspended. Reason: {reason}", "ERROR")
            messages.warning(request, f"🔒 Account {masked_acc} has been suspended. Official suspension notice dispatched to {customer_email or 'customer'}.")

        # --- ACTION 2: REACTIVATE ACCOUNT ---
        elif action_type == 'reactivate':
            account.status = 'ACTIVE'
            account.is_scheduled_for_deletion = False
            account.deletion_scheduled_at = None
            account.deletion_scheduled_for = None
            account.closure_reason = ''
            account.save(update_fields=['status', 'is_scheduled_for_deletion', 'deletion_scheduled_at', 'deletion_scheduled_for', 'closure_reason', 'updated_at'])

            subject = f"PRIME RESERVE BANK — Notice: Account {masked_acc} Reactivated Successfully"
            body = f"""Dear {customer_name},

We are pleased to inform you that your Prime Reserve Bank account {masked_acc} (CIF: {cif_no}) has been REACTIVATED and is now in good standing.

DETAILS:
--------------------------------------------------
Account Number     : {acct_no}
Account Holder     : {customer_name}
Available Balance  : ₹{current_balance:,.2f}
Status             : ACTIVE
Reactivation Date  : {timezone.now().strftime('%d %B %Y, %I:%M %p')}

All your Internet Banking features, UPI payments, and fund transfer services have been fully restored.

Thank you for banking with Prime Reserve Bank.

Sincerely,
Prime Reserve Bank Central Operations
"""
            try:
                if customer_email:
                    send_mail(subject, body, from_email, [customer_email], fail_silently=True)
            except Exception as e:
                logger.warning(f"Reactivation email failed: {e}")

            log_audit_event("ADMIN_REACTIVATE_ACCOUNT", f"Admin {request.user.username} reactivated A/c {acct_no} for {user.username}", user=request.user, request=request)
            send_notification(user, "Account Reactivated", f"Your bank account {masked_acc} has been reactivated successfully.", "SUCCESS")
            messages.success(request, f"✅ Account {masked_acc} has been reactivated. Notice dispatched to {customer_email or 'customer'}.")

        # --- ACTION 3: SCHEDULE 7-DAY AUTO-DELETION ---
        elif action_type == 'schedule_delete':
            days = int(request.POST.get('schedule_days', 7))
            scheduled_date = timezone.now() + timedelta(days=days)
            account.is_scheduled_for_deletion = True
            account.deletion_scheduled_at = timezone.now()
            account.deletion_scheduled_for = scheduled_date
            account.closure_reason = reason
            account.status = 'BLOCKED'
            account.save(update_fields=['is_scheduled_for_deletion', 'deletion_scheduled_at', 'deletion_scheduled_for', 'closure_reason', 'status', 'updated_at'])

            formatted_deadline = scheduled_date.strftime('%d %B %Y')
            subject = f"PRIME RESERVE BANK — Urgent Notice: Scheduled Account Closure in {days} Days ({masked_acc})"
            body = f"""Dear {customer_name},

URGENT COMPLIANCE NOTICE FOR ACCOUNT: {masked_acc} (CIF: {cif_no})

Please be advised that your bank account has been SCHEDULED FOR AUTOMATIC CLOSURE & LIQUIDATION in {days} days on {formatted_deadline}.

CLOSURE DETAILS:
--------------------------------------------------
Account Number        : {acct_no}
Account Holder        : {customer_name}
Current Balance       : ₹{current_balance:,.2f}
Reason for Closure    : {reason}
Scheduled Final Date  : {formatted_deadline} (23:59 IST)

REQUIRED ACTIONS BEFORE THE DEADLINE:
1. Please withdraw or transfer your remaining balance of ₹{current_balance:,.2f} before {formatted_deadline}.
2. If you believe this notice was issued in error or wish to retain your account, please visit your branch ({account.branch.branch_name}) immediately with your valid KYC identification documents.
3. Upon reaching the deadline, the account and linked UPI VPAs will be liquidated and permanently closed.

Sincerely,
Prime Reserve Bank Account Management & Legal Compliance
"""
            try:
                if customer_email:
                    send_mail(subject, body, from_email, [customer_email], fail_silently=True)
            except Exception as e:
                logger.warning(f"Scheduled deletion email failed: {e}")

            log_audit_event("ADMIN_SCHEDULE_DELETE", f"Admin {request.user.username} scheduled A/c {acct_no} for deletion on {formatted_deadline}. Reason: {reason}", user=request.user, request=request)
            send_notification(user, "Scheduled for Deletion", f"Your account {masked_acc} is scheduled for automatic closure on {formatted_deadline}.", "SECURITY")
            messages.warning(request, f"⏳ Account {masked_acc} scheduled for automatic closure on {formatted_deadline}. 7-day notice email dispatched to {customer_email or 'customer'}.")

        # --- ACTION 4: CANCEL SCHEDULED DELETION ---
        elif action_type == 'cancel_schedule_delete':
            account.is_scheduled_for_deletion = False
            account.deletion_scheduled_at = None
            account.deletion_scheduled_for = None
            account.closure_reason = ''
            account.status = 'ACTIVE'
            account.save(update_fields=['is_scheduled_for_deletion', 'deletion_scheduled_at', 'deletion_scheduled_for', 'closure_reason', 'status', 'updated_at'])

            subject = f"PRIME RESERVE BANK — Notice: Scheduled Account Deletion Cancelled ({masked_acc})"
            body = f"""Dear {customer_name},

The scheduled closure & liquidation on your Prime Reserve Bank account {masked_acc} (CIF: {cif_no}) has been CANCELLED by our Branch Operations team.

Your account is now ACTIVE and in full normal standing.

Thank you for banking with Prime Reserve Bank.

Sincerely,
Prime Reserve Bank Central Operations
"""
            try:
                if customer_email:
                    send_mail(subject, body, from_email, [customer_email], fail_silently=True)
            except Exception as e:
                logger.warning(f"Cancel deletion email failed: {e}")

            log_audit_event("ADMIN_CANCEL_SCHEDULE_DELETE", f"Admin {request.user.username} cancelled scheduled deletion of A/c {acct_no}", user=request.user, request=request)
            send_notification(user, "Deletion Cancelled", f"Scheduled closure on {masked_acc} was cancelled. Your account is active.", "SUCCESS")
            messages.success(request, f"✅ Scheduled deletion on {masked_acc} was cancelled. Account is now Active.")

        # --- ACTION 5: INSTANT PERMANENT DELETION / CLOSURE ---
        elif action_type == 'delete_instant':
            settlement_method = request.POST.get('settlement_method', 'Counter Cash Settlement / Demand Draft')
            
            subject = f"PRIME RESERVE BANK — Account Closure & Final Settlement Certificate ({masked_acc})"
            body = f"""Dear {customer_name},

OFFICIAL ACCOUNT CLOSURE & FINAL SETTLEMENT CERTIFICATE

We hereby confirm that your bank account {masked_acc} (CIF: {cif_no}) has been PERMANENTLY CLOSED and settled on {timezone.now().strftime('%d %B %Y, %I:%M %p')}.

SETTLEMENT SUMMARY:
--------------------------------------------------
Account Number        : {acct_no}
Account Holder        : {customer_name}
CIF / Customer ID     : {cif_no}
Account Type          : {account.get_account_type_display()}
Final Disbursed Funds : ₹{current_balance:,.2f}
Settlement Method     : {settlement_method}
Reason for Closure    : {reason}
Closure Date          : {timezone.now().strftime('%d %B %Y')}

Linked digital services, debit cards, and UPI payment handles have been permanently decommissioned.

We thank you for the association with Prime Reserve Bank and wish you the best in your future financial endeavors.

Sincerely,
Prime Reserve Bank Branch Manager & Settlements Authority
"""
            try:
                if customer_email:
                    send_mail(subject, body, from_email, [customer_email], fail_silently=True)
            except Exception as e:
                logger.warning(f"Closure certificate email failed: {e}")

            log_audit_event("ADMIN_INSTANT_ACCOUNT_DELETE", f"Admin {request.user.username} permanently closed/deleted A/c {acct_no} for {user.username}. Balance settled: ₹{current_balance:,.2f}. Reason: {reason}", user=request.user, request=request)
            
            # Delete account and user if single account
            account.delete()
            if not user.bank_accounts.exists() and not user.is_staff and not user.is_superuser:
                user.delete()

            messages.success(request, f"🗑️ Account {acct_no} has been permanently closed and settled. Final settlement certificate dispatched to {customer_email or 'customer'}.")

    return redirect('admin_dashboard:overview')


@login_required
def admin_clear_all_customers_view(request):
    """
    Staff / Manager Action:
    Wipes all existing non-admin customer records, accounts, transactions, deposits, loans,
    and beneficiaries to start with a clean, empty state for fresh customer registrations.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Staff privileges required to clear customers.")
        return redirect('dashboard:home')

    if request.method == 'POST':
        # Delete all non-staff users
        non_staff_users = User.objects.filter(is_staff=False, is_superuser=False)
        count = non_staff_users.count()
        non_staff_users.delete()

        # Delete all remaining orphaned transactions & OTPs
        Transaction.objects.all().delete()
        OTPVerification.objects.all().delete()

        log_audit_event("ADMIN_CLEAR_ALL_CUSTOMERS", f"Admin {request.user.username} wiped all customer records ({count} users removed) for fresh start.", user=request.user, request=request)
        messages.success(request, f"✨ All {count} customer accounts, balances, and transactions have been successfully cleared! The system is now completely fresh.")
        return redirect('admin_dashboard:overview')

    return redirect('admin_dashboard:overview')


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
        account.status = 'BLOCKED'
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
    fd.save(update_fields=['status'])

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
        volume_data.append(round(float(vol), 2))

    # Credit vs Debit
    tot_credits = Transaction.objects.filter(transaction_type__in=['DEPOSIT', 'CREDIT', 'SALARY'], status='SUCCESS').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
    tot_debits = Transaction.objects.filter(transaction_type__in=['IMPS', 'NEFT', 'RTGS', 'UPI', 'BILL_PAYMENT'], status='SUCCESS').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

    return JsonResponse({
        'days_labels': days_labels,
        'volume_data': volume_data,
        'credit_total': round(float(tot_credits), 2),
        'debit_total': round(float(tot_debits), 2)
    })


@login_required
def admin_create_fd_view(request):
    """
    Staff / Manager Action: Open a new Fixed Deposit for any customer account.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Unauthorized.")
        return redirect('dashboard:home')

    if request.method == 'POST':
        account_id = request.POST.get('account_id')
        principal_raw = request.POST.get('principal_amount', '').strip()
        tenure_raw = request.POST.get('tenure_months', '12')
        interest_raw = request.POST.get('interest_rate', '7.5')
        funding_source = request.POST.get('funding_source', 'ACCOUNT_DEBIT')

        try:
            account = BankAccount.objects.get(id=account_id)
            principal = Decimal(principal_raw)
            tenure_months = int(tenure_raw)
            interest_rate = Decimal(interest_raw)

            if principal < Decimal('1000.00'):
                messages.error(request, "Minimum FD investment amount is ₹1,000.00.")
                return redirect('admin_dashboard:overview')

            if funding_source == 'ACCOUNT_DEBIT':
                if account.balance < principal:
                    messages.error(request, f"Insufficient account balance (₹{account.balance:,.2f}) to fund ₹{principal:,.2f} FD.")
                    return redirect('admin_dashboard:overview')
                account.balance -= principal
                account.save(update_fields=['balance', 'updated_at'])
                Transaction.objects.create(
                    transaction_type='DEBIT',
                    amount=principal,
                    status='SUCCESS',
                    sender_account=account,
                    sender_name=account.user.get_full_name() or account.user.username,
                    remarks=f"In-Branch Fixed Deposit Creation - #{account.account_number}"
                )

            # Compound calculation (quarterly compounding)
            rate = float(interest_rate) / 100.0
            t_years = float(tenure_months) / 12.0
            n = 4
            mat_val = float(principal) * ((1.0 + rate/n) ** (n * t_years))
            maturity_amount = Decimal(str(round(mat_val, 2)))
            interest_earned = maturity_amount - principal

            start_date = timezone.now().date()
            maturity_date = start_date + timedelta(days=tenure_months * 30)

            fd = FixedDeposit.objects.create(
                user=account.user,
                linked_account=account,
                principal_amount=principal,
                interest_rate=interest_rate,
                tenure_months=tenure_months,
                maturity_amount=maturity_amount,
                interest_earned=interest_earned,
                start_date=start_date,
                maturity_date=maturity_date,
                status='ACTIVE'
            )

            log_audit_event("ADMIN_CREATE_FD", f"Admin {request.user.username} created FD {fd.fd_number} (₹{principal:,.2f} @ {interest_rate}%) for {account.user.username}", user=request.user, request=request)
            send_notification(account.user, "New Fixed Deposit Opened", f"Your Fixed Deposit {fd.fd_number} of ₹{principal:,.2f} for {tenure_months} months has been opened.", "SUCCESS")

            messages.success(request, f"🎉 Fixed Deposit {fd.fd_number} created successfully for {account.user.username}! Principal: ₹{principal:,.2f}, Maturity: ₹{maturity_amount:,.2f}.")
        except Exception as e:
            logger.error(f"Error creating FD: {e}")
            messages.error(request, f"Failed to create Fixed Deposit: {e}")

    return redirect('admin_dashboard:overview')


@login_required
def admin_create_rd_view(request):
    """
    Staff / Manager Action: Open a new Recurring Deposit for any customer account.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Unauthorized.")
        return redirect('dashboard:home')

    if request.method == 'POST':
        account_id = request.POST.get('account_id')
        monthly_raw = request.POST.get('monthly_deposit', '').strip()
        tenure_raw = request.POST.get('tenure_months', '12')
        interest_raw = request.POST.get('interest_rate', '7.0')

        try:
            account = BankAccount.objects.get(id=account_id)
            monthly_deposit = Decimal(monthly_raw)
            tenure_months = int(tenure_raw)
            interest_rate = Decimal(interest_raw)

            if monthly_deposit < Decimal('500.00'):
                messages.error(request, "Minimum RD monthly installment is ₹500.00.")
                return redirect('admin_dashboard:overview')

            if account.balance < monthly_deposit:
                messages.error(request, f"Insufficient account balance (₹{account.balance:,.2f}) for first RD installment (₹{monthly_deposit:,.2f}).")
                return redirect('admin_dashboard:overview')

            account.balance -= monthly_deposit
            account.save(update_fields=['balance', 'updated_at'])
            Transaction.objects.create(
                transaction_type='DEBIT',
                amount=monthly_deposit,
                status='SUCCESS',
                sender_account=account,
                sender_name=account.user.get_full_name() or account.user.username,
                remarks=f"In-Branch RD Initial Installment - #{account.account_number}"
            )

            P = float(monthly_deposit)
            n = int(tenure_months)
            r = float(interest_rate) / 100.0
            total_dep = Decimal(str(P * n))
            mat_val = sum(P * ((1.0 + r/4.0)**(4.0 * (n - i + 1.0) / 12.0)) for i in range(1, n + 1))
            maturity_amount = Decimal(str(round(mat_val, 2)))
            interest_earned = maturity_amount - total_dep

            start_date = timezone.now().date()
            maturity_date = start_date + timedelta(days=tenure_months * 30)

            rd = RecurringDeposit.objects.create(
                user=account.user,
                linked_account=account,
                monthly_deposit=monthly_deposit,
                interest_rate=interest_rate,
                tenure_months=tenure_months,
                total_deposit=total_dep,
                maturity_amount=maturity_amount,
                interest_earned=interest_earned,
                start_date=start_date,
                maturity_date=maturity_date,
                status='ACTIVE'
            )

            log_audit_event("ADMIN_CREATE_RD", f"Admin {request.user.username} created RD {rd.rd_number} (₹{monthly_deposit:,.2f}/mo) for {account.user.username}", user=request.user, request=request)
            send_notification(account.user, "New Recurring Deposit Opened", f"Your Recurring Deposit {rd.rd_number} of ₹{monthly_deposit:,.2f}/month has been started.", "SUCCESS")

            messages.success(request, f"🎉 Recurring Deposit {rd.rd_number} created successfully for {account.user.username}! Monthly: ₹{monthly_deposit:,.2f}, Maturity: ₹{maturity_amount:,.2f}.")
        except Exception as e:
            logger.error(f"Error creating RD: {e}")
            messages.error(request, f"Failed to create Recurring Deposit: {e}")

    return redirect('admin_dashboard:overview')


@login_required
def admin_close_rd_view(request, rd_id):
    """
    Staff / Manager Action: Prematurely close or liquidate an active RD.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Unauthorized.")
        return redirect('dashboard:home')

    rd = get_object_or_404(RecurringDeposit, id=rd_id, status='ACTIVE')
    rd.status = 'CLOSED'
    rd.save(update_fields=['status'])

    # Refund total deposit back to linked account
    acc = rd.linked_account
    acc.balance += rd.monthly_deposit
    acc.save(update_fields=['balance', 'updated_at'])

    log_audit_event("ADMIN_RD_CLOSE", f"Admin closed RD {rd.rd_number}, refunded ₹{rd.monthly_deposit} to A/c {acc.account_number}", user=request.user, request=request)
    send_notification(rd.user, "Recurring Deposit Closed", f"Your Recurring Deposit {rd.rd_number} was closed and funds refunded to your account.", "INFO")
    messages.success(request, f"Recurring Deposit {rd.rd_number} closed successfully. Funds credited to customer account.")
    return redirect('admin_dashboard:overview')


@login_required
def admin_create_loan_view(request):
    """
    Staff / Manager Action: Issue and disburse a Loan to any customer account.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Unauthorized.")
        return redirect('dashboard:home')

    if request.method == 'POST':
        account_id = request.POST.get('account_id')
        product_id = request.POST.get('product_id')
        principal_raw = request.POST.get('principal_amount', '').strip()
        tenure_raw = request.POST.get('tenure_months', '12')

        try:
            account = BankAccount.objects.get(id=account_id)
            product = LoanProduct.objects.get(id=product_id)
            principal = Decimal(principal_raw)
            tenure_months = int(tenure_raw)

            if principal < Decimal('5000.00'):
                messages.error(request, "Minimum loan amount is ₹5,000.00.")
                return redirect('admin_dashboard:overview')

            # Calculate EMI
            annual_rate = float(product.interest_rate)
            r_monthly = (annual_rate / 12.0) / 100.0
            P = float(principal)
            n = tenure_months
            if r_monthly > 0:
                emi = P * r_monthly * ((1.0 + r_monthly)**n) / (((1.0 + r_monthly)**n) - 1.0)
            else:
                emi = P / n
            emi_dec = Decimal(str(round(emi, 2)))
            total_payable = emi_dec * Decimal(str(n))

            start_date = timezone.now().date()
            end_date = start_date + timedelta(days=tenure_months * 30)

            loan = Loan.objects.create(
                user=account.user,
                disbursal_account=account,
                loan_product=product,
                principal_amount=principal,
                interest_rate=product.interest_rate,
                tenure_months=tenure_months,
                monthly_emi=emi_dec,
                outstanding_balance=total_payable,
                total_amount_payable=total_payable,
                status='ACTIVE',
                start_date=start_date,
                end_date=end_date
            )

            # Disburse funds directly into customer account
            account.balance += principal
            account.save(update_fields=['balance', 'updated_at'])

            Transaction.objects.create(
                transaction_type='CREDIT',
                amount=principal,
                status='SUCCESS',
                receiver_account=account,
                receiver_name=account.user.get_full_name() or account.user.username,
                remarks=f"In-Branch Loan Disbursal Credit — {product.name} (#{loan.loan_account_number})"
            )

            log_audit_event("ADMIN_LOAN_DISBURSAL", f"Admin {request.user.username} disbursed {product.name} {loan.loan_account_number} (₹{principal:,.2f}) to A/c {account.account_number}", user=request.user, request=request)
            send_notification(account.user, "Loan Approved & Disbursed!", f"Your {product.name} #{loan.loan_account_number} of ₹{principal:,.2f} has been disbursed directly into your account.", "SUCCESS")

            messages.success(request, f"💸 Loan {loan.loan_account_number} ({product.name}) approved & ₹{principal:,.2f} disbursed directly to {account.user.username}'s account #{account.account_number}!")
        except Exception as e:
            logger.error(f"Error creating loan: {e}")
            messages.error(request, f"Failed to issue loan: {e}")

    return redirect('admin_dashboard:overview')


@login_required
def admin_close_loan_view(request, loan_id):
    """
    Staff / Manager Action: Settle / Close a customer Loan.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Unauthorized.")
        return redirect('dashboard:home')

    loan = get_object_or_404(Loan, id=loan_id)
    loan.status = 'CLOSED'
    loan.outstanding_balance = Decimal('0.00')
    loan.save(update_fields=['status', 'outstanding_balance'])

    log_audit_event("ADMIN_LOAN_CLOSE", f"Admin {request.user.username} closed loan {loan.loan_account_number}", user=request.user, request=request)
    send_notification(loan.user, "Loan Settled & Closed", f"Your loan {loan.loan_account_number} has been fully settled and closed in bank records.", "SUCCESS")
    messages.success(request, f"Loan {loan.loan_account_number} marked as CLOSED / Fully Settled.")
    return redirect('admin_dashboard:overview')


@login_required
def admin_adjust_balance_view(request, account_id):
    """
    Staff / Manager Action: Direct Credit or Debit adjustment on customer account balance.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Unauthorized.")
        return redirect('dashboard:home')

    account = get_object_or_404(BankAccount, id=account_id)

    if request.method == 'POST':
        adj_type = request.POST.get('adjustment_type', 'CREDIT')
        amount_raw = request.POST.get('amount', '0').strip()
        narration = request.POST.get('narration', 'Manager Account Balance Adjustment').strip() or 'Manager Discretionary Adjustment'

        try:
            amount = Decimal(amount_raw)
            if amount <= Decimal('0.00'):
                messages.error(request, "Adjustment amount must be greater than ₹0.00.")
                return redirect('admin_dashboard:overview')

            if adj_type == 'CREDIT':
                account.balance += amount
                account.save(update_fields=['balance', 'updated_at'])
                Transaction.objects.create(
                    transaction_type='CREDIT',
                    amount=amount,
                    status='SUCCESS',
                    receiver_account=account,
                    receiver_name=account.user.get_full_name() or account.user.username,
                    remarks=f"Manager Direct Deposit / Credit: {narration}"
                )
                send_notification(account.user, "Account Credited", f"Your account #{account.account_number} was credited with ₹{amount:,.2f}. Narration: {narration}", "SUCCESS")
                log_audit_event("ADMIN_BALANCE_CREDIT", f"Admin credited ₹{amount:,.2f} to A/c {account.account_number}. Narration: {narration}", user=request.user, request=request)
                messages.success(request, f"💵 Successfully credited ₹{amount:,.2f} to Account #{account.account_number}! New Balance: ₹{account.balance:,.2f}.")

            elif adj_type == 'DEBIT':
                if account.balance < amount:
                    messages.error(request, f"Insufficient balance (₹{account.balance:,.2f}) to debit ₹{amount:,.2f}.")
                    return redirect('admin_dashboard:overview')

                account.balance -= amount
                account.save(update_fields=['balance', 'updated_at'])
                Transaction.objects.create(
                    transaction_type='DEBIT',
                    amount=amount,
                    status='SUCCESS',
                    sender_account=account,
                    sender_name=account.user.get_full_name() or account.user.username,
                    remarks=f"Manager Direct Debit / Adjustment: {narration}"
                )
                send_notification(account.user, "Account Debited", f"Your account #{account.account_number} was debited with ₹{amount:,.2f}. Narration: {narration}", "INFO")
                log_audit_event("ADMIN_BALANCE_DEBIT", f"Admin debited ₹{amount:,.2f} from A/c {account.account_number}. Narration: {narration}", user=request.user, request=request)
                messages.success(request, f"💳 Successfully debited ₹{amount:,.2f} from Account #{account.account_number}! New Balance: ₹{account.balance:,.2f}.")

        except Exception as e:
            logger.error(f"Error adjusting balance: {e}")
            messages.error(request, f"Balance adjustment failed: {e}")

    return redirect('admin_dashboard:overview')

