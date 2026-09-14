from django.db import models
from django.contrib.auth.models import User
from banking.models import BankAccount
from transactions.models import Transaction
from django.contrib.auth.hashers import make_password, check_password

class UPIAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='upi_accounts')
    bank_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='linked_upi_handles')
    upi_id = models.CharField(max_length=60, unique=True, verbose_name="Virtual Payment Address (VPA)")
    upi_pin_hash = models.CharField(max_length=128, blank=True, help_text="Hashed 4-6 digit UPI PIN")
    is_primary = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    daily_limit = models.DecimalField(max_digits=12, decimal_places=2, default=50000.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "UPI Account / VPA"
        verbose_name_plural = "UPI Accounts / VPAs"
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f"{self.upi_id} -> {self.bank_account.masked_account_number()}"

    def set_pin(self, raw_pin):
        self.upi_pin_hash = make_password(str(raw_pin))

    def check_pin(self, raw_pin):
        if not self.upi_pin_hash:
            # Default demo UPI PIN is 1234
            return str(raw_pin) in ('1234', '123456')
        return check_password(str(raw_pin), self.upi_pin_hash)


class UPITransaction(models.Model):
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name='upi_metadata')
    sender_upi_id = models.CharField(max_length=60)
    receiver_upi_id = models.CharField(max_length=60)
    npci_simulated_ref = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"UPI: {self.sender_upi_id} -> {self.receiver_upi_id} (₹{self.transaction.amount})"
