from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from accounts.models import Branch
from decimal import Decimal
from django.contrib.auth.hashers import make_password, check_password

class BankAccount(models.Model):
    ACCOUNT_TYPE_CHOICES = (
        ('SAVINGS', 'Prime Savings Account'),
        ('CURRENT', 'Prime Current Account'),
        ('SALARY', 'Prime Corporate Salary Account'),
        ('FIXED_DEPOSIT', 'Prime Fixed Deposit Account'),
    )
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('DORMANT', 'Dormant'),
        ('BLOCKED', 'Blocked / Frozen'),
        ('CLOSED', 'Closed'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bank_accounts')
    account_number = models.CharField(max_length=16, unique=True, verbose_name="Account Number")
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES, default='SAVINGS')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='accounts')
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'), verbose_name="Available Balance (₹)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    transaction_pin_hash = models.CharField(max_length=128, blank=True, help_text="Hashed 4-digit PIN for transfer confirmation")
    nominee_name = models.CharField(max_length=100, blank=True, default='')
    nominee_relation = models.CharField(max_length=50, blank=True, default='')
    nominee_age = models.PositiveIntegerField(null=True, blank=True)
    daily_transfer_limit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('100000.00'))
    opening_date = models.DateField(default=timezone.now)
    is_scheduled_for_deletion = models.BooleanField(default=False)
    deletion_scheduled_at = models.DateTimeField(null=True, blank=True)
    deletion_scheduled_for = models.DateTimeField(null=True, blank=True)
    closure_reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def days_until_deletion(self):
        if self.is_scheduled_for_deletion and self.deletion_scheduled_for:
            delta = self.deletion_scheduled_for - timezone.now()
            return max(0, delta.days)
        return None


    def __str__(self):
        return f"{self.get_account_type_display()} - {self.masked_account_number()} (₹{self.balance:,.2f})"

    def masked_account_number(self):
        acc = str(self.account_number)
        if len(acc) >= 4:
            return f"XXXX XXXX {acc[-4:]}"
        return acc

    def set_transaction_pin(self, raw_pin):
        self.transaction_pin_hash = make_password(str(raw_pin))

    def check_transaction_pin(self, raw_pin):
        if not self.transaction_pin_hash:
            # If no PIN set, default demo PIN is 1234
            return str(raw_pin) == '1234'
        return check_password(str(raw_pin), self.transaction_pin_hash)


class AccountStatementRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='statement_requests')
    account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='statements')
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Statement for {self.account.account_number} ({self.start_date} to {self.end_date})"
