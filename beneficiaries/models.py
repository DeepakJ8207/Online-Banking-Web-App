from django.db import models
from django.contrib.auth.models import User

class Beneficiary(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='beneficiaries')
    beneficiary_name = models.CharField(max_length=100, verbose_name="Beneficiary Full Name")
    account_number = models.CharField(max_length=20, verbose_name="Beneficiary Account Number")
    ifsc_code = models.CharField(max_length=15, verbose_name="IFSC Code")
    bank_name = models.CharField(max_length=100, verbose_name="Bank Name", default="PRIME RESERVE BANK")
    nickname = models.CharField(max_length=50, blank=True, verbose_name="Nickname")
    mobile_number = models.CharField(max_length=15, blank=True, verbose_name="Mobile Number")
    email = models.EmailField(blank=True, verbose_name="Email Address")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Beneficiaries"
        unique_together = ('user', 'account_number')
        ordering = ['beneficiary_name']

    def __str__(self):
        return f"{self.beneficiary_name} ({self.account_number} - {self.bank_name})"

    def masked_account_number(self):
        acc = str(self.account_number)
        if len(acc) >= 4:
            return f"XXXX XXXX {acc[-4:]}"
        return acc
