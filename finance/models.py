from django.db import models
from django.contrib.auth.models import User
from banking.models import BankAccount
from transactions.models import Transaction
from decimal import Decimal
import uuid
from django.utils import timezone
from datetime import timedelta

class LoanProduct(models.Model):
    LOAN_TYPE_CHOICES = (
        ('PERSONAL', 'Prime Personal Loan'),
        ('HOME', 'Prime Home Loan'),
        ('CAR', 'Prime Auto / Car Loan'),
        ('EDUCATION', 'Prime Education Loan'),
        ('GOLD', 'Prime Gold Loan'),
    )

    name = models.CharField(max_length=100)
    loan_type = models.CharField(max_length=20, choices=LOAN_TYPE_CHOICES)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Annual Interest Rate (%)")
    min_amount = models.DecimalField(max_digits=12, decimal_places=2, default=10000.00)
    max_amount = models.DecimalField(max_digits=12, decimal_places=2, default=5000000.00)
    min_tenure_months = models.PositiveIntegerField(default=6)
    max_tenure_months = models.PositiveIntegerField(default=84)
    processing_fee_percentage = models.DecimalField(max_digits=4, decimal_places=2, default=1.00)
    features = models.TextField(help_text="Key features and eligibility criteria separated by newlines")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['loan_type']

    def __str__(self):
        return f"{self.name} ({self.interest_rate}% p.a.)"


class Loan(models.Model):
    STATUS_CHOICES = (
        ('ACTIVE', 'Active Loan'),
        ('APPROVED', 'Approved'),
        ('PENDING', 'Under Verification'),
        ('CLOSED', 'Closed / Fully Repaid'),
        ('REJECTED', 'Rejected'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loans')
    disbursal_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='linked_loans')
    loan_product = models.ForeignKey(LoanProduct, on_delete=models.PROTECT, related_name='loans_issued')
    loan_account_number = models.CharField(max_length=24, unique=True, editable=False)
    principal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    tenure_months = models.PositiveIntegerField()
    monthly_emi = models.DecimalField(max_digits=12, decimal_places=2)
    outstanding_balance = models.DecimalField(max_digits=12, decimal_places=2)
    total_amount_payable = models.DecimalField(max_digits=12, decimal_places=2)
    total_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Loan {self.loan_account_number} - {self.loan_product.name} (₹{self.outstanding_balance:,.2f})"

    def save(self, *args, **kwargs):
        if not self.loan_account_number:
            uid = uuid.uuid4().hex[:6].upper()
            self.loan_account_number = f"LN-PRMB-{uid}"
        if not self.end_date and self.start_date and self.tenure_months:
            self.end_date = self.start_date + timedelta(days=self.tenure_months * 30)
        super().save(*args, **kwargs)


class LoanRepayment(models.Model):
    STATUS_CHOICES = (
        ('PAID', 'Paid'),
        ('DUE', 'Due'),
        ('OVERDUE', 'Overdue'),
    )

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='repayments')
    installment_number = models.PositiveIntegerField()
    due_date = models.DateField()
    emi_amount = models.DecimalField(max_digits=12, decimal_places=2)
    principal_component = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    interest_component = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    paid_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='DUE')
    transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='loan_repayment_logs')

    class Meta:
        ordering = ['installment_number']

    def __str__(self):
        return f"EMI #{self.installment_number} for Loan {self.loan.loan_account_number} - ₹{self.emi_amount}"


class FixedDeposit(models.Model):
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('MATURED', 'Matured'),
        ('CLOSED', 'Prematurely Closed'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fixed_deposits')
    linked_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='fd_accounts')
    fd_number = models.CharField(max_length=24, unique=True, editable=False)
    principal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Annual Interest Rate (%)")
    tenure_months = models.PositiveIntegerField()
    maturity_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_earned = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField(default=timezone.now)
    maturity_date = models.DateField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='ACTIVE')
    auto_renew = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"FD {self.fd_number} - ₹{self.principal_amount:,.2f} -> ₹{self.maturity_amount:,.2f}"

    def save(self, *args, **kwargs):
        if not self.fd_number:
            uid = uuid.uuid4().hex[:6].upper()
            self.fd_number = f"FD-PRMB-{uid}"
        super().save(*args, **kwargs)


class RecurringDeposit(models.Model):
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('MATURED', 'Matured'),
        ('CLOSED', 'Prematurely Closed'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_deposits')
    linked_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='rd_accounts')
    rd_number = models.CharField(max_length=24, unique=True, editable=False)
    monthly_deposit = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    tenure_months = models.PositiveIntegerField()
    total_deposit = models.DecimalField(max_digits=12, decimal_places=2)
    maturity_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_earned = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField(default=timezone.now)
    maturity_date = models.DateField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"RD {self.rd_number} - ₹{self.monthly_deposit:,.2f}/mo -> ₹{self.maturity_amount:,.2f}"

    def save(self, *args, **kwargs):
        if not self.rd_number:
            uid = uuid.uuid4().hex[:6].upper()
            self.rd_number = f"RD-PRMB-{uid}"
        super().save(*args, **kwargs)
