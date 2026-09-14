from django.db import models
from banking.models import BankAccount
from decimal import Decimal
import uuid
from django.utils import timezone

class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = (
        ('BANK_TRANSFER', 'Bank Account Transfer (IMPS/NEFT)'),
        ('UPI_TRANSFER', 'UPI Transfer'),
        ('MOBILE_TRANSFER', 'Mobile Number Transfer'),
        ('SELF_TRANSFER', 'Self Account Transfer'),
        ('BILL_PAYMENT', 'Utility Bill Payment'),
        ('RECHARGE', 'Mobile / DTH Recharge'),
        ('CREDIT', 'Account Credit / Deposit'),
        ('DEBIT', 'Account Debit / Withdrawal'),
        ('FD_DEPOSIT', 'Fixed Deposit Investment'),
        ('LOAN_PAYMENT', 'Loan EMI Repayment'),
        ('INTEREST_CREDIT', 'Interest Credit'),
    )

    STATUS_CHOICES = (
        ('SUCCESS', 'Success'),
        ('PENDING', 'Pending'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    )

    CATEGORY_CHOICES = (
        ('TRANSFER', 'Funds Transfer'),
        ('BILLS', 'Bills & Utilities'),
        ('SALARY', 'Salary & Income'),
        ('SHOPPING', 'Shopping & Lifestyle'),
        ('INVESTMENT', 'Savings & Investments'),
        ('FOOD', 'Dining & Grocery'),
        ('LOAN', 'Loan & EMI'),
        ('OTHER', 'General / Other'),
    )

    transaction_id = models.CharField(max_length=32, unique=True, editable=False)
    reference_number = models.CharField(max_length=32, unique=True, editable=False)
    sender_account = models.ForeignKey(
        BankAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_transactions'
    )
    receiver_account = models.ForeignKey(
        BankAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_transactions'
    )
    sender_name = models.CharField(max_length=150)
    receiver_name = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=14, decimal_places=2, verbose_name="Transaction Amount (₹)")
    transaction_type = models.CharField(max_length=25, choices=TRANSACTION_TYPE_CHOICES, default='BANK_TRANSFER')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='SUCCESS')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='TRANSFER')
    remarks = models.CharField(max_length=255, blank=True, default="Fund Transfer")
    sender_balance_after = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    receiver_balance_after = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['reference_number']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['transaction_type']),
        ]

    def __str__(self):
        return f"{self.transaction_id} | ₹{self.amount:,.2f} | {self.get_transaction_type_display()} | {self.status}"

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            now_str = timezone.now().strftime('%Y%m%d')
            unique_part = uuid.uuid4().hex[:8].upper()
            self.transaction_id = f"TXN{now_str}{unique_part}"
        if not self.reference_number:
            now_str = timezone.now().strftime('%y%m%d%H%M')
            unique_part = uuid.uuid4().hex[:6].upper()
            self.reference_number = f"PRMB{now_str}{unique_part}"
        super().save(*args, **kwargs)
