from django.db import models
from django.contrib.auth.models import User
from banking.models import BankAccount
from transactions.models import Transaction
import uuid
from django.utils import timezone

class BillerCategory(models.Model):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=30, unique=True)
    icon = models.CharField(max_length=50, default='bi-receipt', help_text='Bootstrap Icon class')
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Biller Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Biller(models.Model):
    category = models.ForeignKey(BillerCategory, on_delete=models.CASCADE, related_name='billers')
    name = models.CharField(max_length=100)
    service_area = models.CharField(max_length=100, default='National / All Regions')
    consumer_label = models.CharField(max_length=50, default='Consumer ID / Account No.')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.category.name})"


class BillPayment(models.Model):
    STATUS_CHOICES = (
        ('SUCCESS', 'Payment Successful'),
        ('PENDING', 'Processing'),
        ('FAILED', 'Failed'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bill_payments')
    bank_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='utility_bills')
    biller = models.ForeignKey(Biller, on_delete=models.CASCADE, related_name='payments')
    consumer_number = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction = models.OneToOneField(Transaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='bill_payment_info')
    receipt_number = models.CharField(max_length=32, unique=True, editable=False)
    biller_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUCCESS')
    payment_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f"Bill {self.receipt_number} - {self.biller.name} (₹{self.amount})"

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            now_str = timezone.now().strftime('%Y%m%d')
            uid = uuid.uuid4().hex[:6].upper()
            self.receipt_number = f"BILL-{now_str}-{uid}"
        super().save(*args, **kwargs)
