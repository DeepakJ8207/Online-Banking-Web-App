from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import math
from .models import LoanProduct, Loan, LoanRepayment, FixedDeposit, RecurringDeposit
from .forms import LoanApplicationForm, LoanEMIPaymentForm, FixedDepositForm, RecurringDepositForm
from banking.models import BankAccount
from transfers.services import TransferService
from accounts.services import log_audit_event, send_notification

def calculate_emi(principal, annual_rate, tenure_months):
    """
    Standard Financial EMI Formula: P * r * (1+r)^n / ((1+r)^n - 1)
    """
    P = float(principal)
    r = (float(annual_rate) / 12.0) / 100.0
    n = int(tenure_months)
    if r == 0:
        return Decimal(str(round(P / n, 2)))
    emi = (P * r * ((1 + r) ** n)) / (((1 + r) ** n) - 1)
    return Decimal(str(round(emi, 2)))


def finance_home_view(request):
    """
    Finance Hub: Loans, Deposits, Investments & Financial Calculators.
    """
    loan_products = LoanProduct.objects.filter(is_active=True)
    user_loans = []
    user_fds = []
    user_rds = []

    if request.user.is_authenticated:
        user_loans = Loan.objects.filter(user=request.user)
        user_fds = FixedDeposit.objects.filter(user=request.user)
        user_rds = RecurringDeposit.objects.filter(user=request.user)

    return render(request, 'finance/finance_home.html', {
        'loan_products': loan_products,
        'user_loans': user_loans,
        'user_fds': user_fds,
        'user_rds': user_rds
    })


def emi_calculator_view(request):
    """
    Interactive EMI Calculator with instant JavaScript calculation.
    """
    return render(request, 'finance/emi_calculator.html')


def fd_calculator_view(request):
    """
    Interactive Fixed Deposit Calculator.
    """
    return render(request, 'finance/fd_calculator.html')


def rd_calculator_view(request):
    """
    Interactive Recurring Deposit Calculator.
    """
    return render(request, 'finance/rd_calculator.html')


def sip_calculator_view(request):
    """
    Interactive SIP (Systematic Investment Plan) Calculator.
    """
    return render(request, 'finance/sip_calculator.html')


@login_required
def loans_list_view(request):
    """
    List user loans and available loan schemes.
    """
    user_loans = Loan.objects.filter(user=request.user)
    loan_products = LoanProduct.objects.filter(is_active=True)
    return render(request, 'finance/loans.html', {
        'user_loans': user_loans,
        'loan_products': loan_products
    })


@login_required
def loan_apply_view(request):
    """
    Apply for a simulated loan product. Disburses loan amount into selected account.
    """
    if request.method == 'POST':
        form = LoanApplicationForm(request.POST, user=request.user)
        if form.is_valid():
            product = form.cleaned_data['loan_product']
            disbursal_acc = form.cleaned_data['disbursal_account']
            principal = form.cleaned_data['principal_amount']
            tenure = form.cleaned_data['tenure_months']

            if principal < product.min_amount or principal > product.max_amount:
                messages.error(request, f"Loan amount must be between ₹{product.min_amount:,.2f} and ₹{product.max_amount:,.2f}")
                return render(request, 'finance/loan_apply.html', {'form': form})

            if tenure < product.min_tenure_months or tenure > product.max_tenure_months:
                messages.error(request, f"Tenure must be between {product.min_tenure_months} and {product.max_tenure_months} months.")
                return render(request, 'finance/loan_apply.html', {'form': form})

            # Calculate EMI
            emi = calculate_emi(principal, product.interest_rate, tenure)
            total_payable = emi * tenure

            # Create Loan record
            loan = Loan.objects.create(
                user=request.user,
                disbursal_account=disbursal_acc,
                loan_product=product,
                principal_amount=principal,
                interest_rate=product.interest_rate,
                tenure_months=tenure,
                monthly_emi=emi,
                outstanding_balance=total_payable,
                total_amount_payable=total_payable,
                status='ACTIVE'
            )

            # Generate repayment schedule
            due_date = timezone.now().date() + timedelta(days=30)
            monthly_interest_rate = (float(product.interest_rate) / 12.0) / 100.0
            remaining_principal = float(principal)

            for i in range(1, tenure + 1):
                interest_comp = round(remaining_principal * monthly_interest_rate, 2)
                principal_comp = round(float(emi) - interest_comp, 2)
                remaining_principal = max(0.0, remaining_principal - principal_comp)

                LoanRepayment.objects.create(
                    loan=loan,
                    installment_number=i,
                    due_date=due_date,
                    emi_amount=emi,
                    principal_component=Decimal(str(principal_comp)),
                    interest_component=Decimal(str(interest_comp)),
                    status='DUE'
                )
                due_date = due_date + timedelta(days=30)

            # Disburse loan funds into customer's bank account
            disbursal_acc.balance += principal
            disbursal_acc.save(update_fields=['balance', 'updated_at'])

            log_audit_event("LOAN_APPLY", f"Loan approved & disbursed: {loan.loan_account_number} for ₹{principal} to A/c {disbursal_acc.account_number}", user=request.user, request=request)
            send_notification(request.user, "Loan Approved & Disbursed", f"Your loan {loan.loan_account_number} of ₹{principal:,.2f} has been approved and credited to A/c {disbursal_acc.masked_account_number()}.", "SUCCESS")
            messages.success(request, f"Congratulations! Your loan of ₹{principal:,.2f} has been approved and credited to your account.")
            return redirect('finance:loan_detail', loan_id=loan.id)
    else:
        form = LoanApplicationForm(user=request.user)

    return render(request, 'finance/loan_apply.html', {'form': form})


@login_required
def loan_detail_view(request, loan_id):
    """
    View loan details, balance, and repayment schedule.
    """
    loan = get_object_or_404(Loan, id=loan_id, user=request.user)
    repayments = loan.repayments.all()
    next_due = repayments.filter(status='DUE').first()
    pay_form = LoanEMIPaymentForm(user=request.user)

    return render(request, 'finance/loan_detail.html', {
        'loan': loan,
        'repayments': repayments,
        'next_due': next_due,
        'pay_form': pay_form
    })


@login_required
def loan_pay_emi_view(request, loan_id):
    """
    Make a simulated EMI payment against active loan.
    """
    loan = get_object_or_404(Loan, id=loan_id, user=request.user, status='ACTIVE')
    repayment = loan.repayments.filter(status='DUE').first()

    if not repayment:
        messages.info(request, "No pending EMI due for this loan.")
        return redirect('finance:loan_detail', loan_id=loan.id)

    if request.method == 'POST':
        form = LoanEMIPaymentForm(request.POST, user=request.user)
        if form.is_valid():
            source_acc = form.cleaned_data['source_account']
            pin = form.cleaned_data['transaction_pin']

            if not source_acc.check_transaction_pin(pin):
                messages.error(request, "Invalid Transaction PIN.")
                return redirect('finance:loan_detail', loan_id=loan.id)

            success, msg, txn = TransferService.execute_transfer(
                sender_account_id=source_acc.id,
                amount=repayment.emi_amount,
                transfer_type='LOAN_PAYMENT',
                receiver_name=f"Loan Repayment ({loan.loan_account_number})",
                remarks=f"EMI #{repayment.installment_number} for Loan {loan.loan_account_number}",
                category='LOAN',
                user=request.user,
                request=request
            )

            if success and txn:
                repayment.paid_amount = repayment.emi_amount
                repayment.paid_date = timezone.now().date()
                repayment.status = 'PAID'
                repayment.transaction = txn
                repayment.save()

                loan.outstanding_balance = max(Decimal('0.00'), loan.outstanding_balance - repayment.emi_amount)
                loan.total_paid += repayment.emi_amount
                if loan.outstanding_balance <= Decimal('0.00'):
                    loan.status = 'CLOSED'
                loan.save()

                log_audit_event("LOAN_EMI_PAYMENT", f"Paid EMI #{repayment.installment_number} of ₹{repayment.emi_amount} for Loan {loan.loan_account_number}", user=request.user, request=request)
                send_notification(request.user, "EMI Payment Successful", f"EMI #{repayment.installment_number} of ₹{repayment.emi_amount:,.2f} for Loan {loan.loan_account_number} was paid successfully.", "SUCCESS")
                messages.success(request, f"EMI #{repayment.installment_number} of ₹{repayment.emi_amount:,.2f} paid successfully!")
            else:
                messages.error(request, msg)

    return redirect('finance:loan_detail', loan_id=loan.id)


@login_required
def deposits_view(request):
    """
    Fixed & Recurring Deposits dashboard.
    """
    fds = FixedDeposit.objects.filter(user=request.user)
    rds = RecurringDeposit.objects.filter(user=request.user)
    return render(request, 'finance/deposits.html', {
        'fds': fds,
        'rds': rds
    })


@login_required
def open_fd_view(request):
    """
    Open new Fixed Deposit.
    """
    if request.method == 'POST':
        form = FixedDepositForm(request.POST, user=request.user)
        if form.is_valid():
            linked_acc = form.cleaned_data['linked_account']
            principal = form.cleaned_data['principal_amount']
            tenure = int(form.cleaned_data['tenure_months'])
            auto_renew = form.cleaned_data.get('auto_renew', False)
            pin = form.cleaned_data['transaction_pin']

            if not linked_acc.check_transaction_pin(pin):
                messages.error(request, "Invalid Transaction PIN.")
                return render(request, 'finance/open_fd.html', {'form': form})

            # Determine rate based on tenure
            rates = {6: Decimal('6.50'), 12: Decimal('7.25'), 24: Decimal('7.50'), 36: Decimal('7.40'), 60: Decimal('7.10')}
            rate = rates.get(tenure, Decimal('7.00'))

            # Compound Interest Formula: A = P * (1 + r/n)^(n*t)
            r = float(rate) / 100.0
            t = tenure / 12.0
            n = 4 # quarterly compounding
            maturity_amount = Decimal(str(round(float(principal) * ((1 + r/n) ** (n * t)), 2)))
            interest_earned = maturity_amount - principal

            success, msg, txn = TransferService.execute_transfer(
                sender_account_id=linked_acc.id,
                amount=principal,
                transfer_type='FD_DEPOSIT',
                receiver_name=f"Prime Fixed Deposit Investment",
                remarks=f"FD Creation for {tenure} months @ {rate}% p.a.",
                category='INVESTMENT',
                user=request.user,
                request=request
            )

            if success and txn:
                start_d = timezone.now().date()
                mat_d = start_d + timedelta(days=tenure * 30)

                fd = FixedDeposit.objects.create(
                    user=request.user,
                    linked_account=linked_acc,
                    principal_amount=principal,
                    interest_rate=rate,
                    tenure_months=tenure,
                    maturity_amount=maturity_amount,
                    interest_earned=interest_earned,
                    start_date=start_d,
                    maturity_date=mat_d,
                    auto_renew=auto_renew,
                    status='ACTIVE'
                )

                log_audit_event("FD_CREATE", f"Created Fixed Deposit {fd.fd_number} for ₹{principal} ({tenure} months)", user=request.user, request=request)
                send_notification(request.user, "Fixed Deposit Created", f"Your FD {fd.fd_number} of ₹{principal:,.2f} has been created. Maturity Value: ₹{maturity_amount:,.2f}", "SUCCESS")
                messages.success(request, f"Fixed Deposit of ₹{principal:,.2f} created successfully!")
                return redirect('finance:fd_receipt', fd_id=fd.id)
            else:
                messages.error(request, msg)
    else:
        form = FixedDepositForm(user=request.user)

    return render(request, 'finance/open_fd.html', {'form': form})


@login_required
def fd_receipt_view(request, fd_id):
    """
    Fixed Deposit Creation Success Receipt Screen.
    """
    fd = get_object_or_404(FixedDeposit, id=fd_id, user=request.user)
    return render(request, 'finance/fd_receipt.html', {'fd': fd})


@login_required
def open_rd_view(request):
    """
    Open new Recurring Deposit.
    """
    if request.method == 'POST':
        form = RecurringDepositForm(request.POST, user=request.user)
        if form.is_valid():
            linked_acc = form.cleaned_data['linked_account']
            monthly = form.cleaned_data['monthly_deposit']
            tenure = int(form.cleaned_data['tenure_months'])
            pin = form.cleaned_data['transaction_pin']

            if not linked_acc.check_transaction_pin(pin):
                messages.error(request, "Invalid Transaction PIN.")
                return render(request, 'finance/open_rd.html', {'form': form})

            rates = {6: Decimal('6.25'), 12: Decimal('7.00'), 24: Decimal('7.25'), 36: Decimal('7.15'), 60: Decimal('6.85')}
            rate = rates.get(tenure, Decimal('7.00'))

            total_deposit = monthly * tenure
            P = float(monthly)
            n = tenure
            r = float(rate) / 100.0
            interest = P * n * (n + 1) / 24.0 * r
            maturity_amount = Decimal(str(round((P * n) + interest, 2)))
            interest_earned = maturity_amount - total_deposit

            # Debit first month installment
            success, msg, txn = TransferService.execute_transfer(
                sender_account_id=linked_acc.id,
                amount=monthly,
                transfer_type='FD_DEPOSIT',
                receiver_name="Prime Recurring Deposit Installment #1",
                remarks=f"RD Creation: 1st installment of ₹{monthly}",
                category='INVESTMENT',
                user=request.user,
                request=request
            )

            if success and txn:
                start_d = timezone.now().date()
                mat_d = start_d + timedelta(days=tenure * 30)

                rd = RecurringDeposit.objects.create(
                    user=request.user,
                    linked_account=linked_acc,
                    monthly_deposit=monthly,
                    interest_rate=rate,
                    tenure_months=tenure,
                    total_deposit=total_deposit,
                    maturity_amount=maturity_amount,
                    interest_earned=interest_earned,
                    start_date=start_d,
                    maturity_date=mat_d,
                    status='ACTIVE'
                )

                log_audit_event("RD_CREATE", f"Created Recurring Deposit {rd.rd_number} (₹{monthly}/mo)", user=request.user, request=request)
                send_notification(request.user, "Recurring Deposit Created", f"Your RD {rd.rd_number} (₹{monthly:,.2f}/mo) has been opened.", "SUCCESS")
                messages.success(request, f"Recurring Deposit created successfully!")
                return redirect('finance:rd_receipt', rd_id=rd.id)
            else:
                messages.error(request, msg)
    else:
        form = RecurringDepositForm(user=request.user)

    return render(request, 'finance/open_rd.html', {'form': form})


@login_required
def rd_receipt_view(request, rd_id):
    """
    Recurring Deposit Creation Success Receipt Screen.
    """
    rd = get_object_or_404(RecurringDeposit, id=rd_id, user=request.user)
    return render(request, 'finance/rd_receipt.html', {'rd': rd})

