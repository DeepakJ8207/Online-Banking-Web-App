from django import forms
from banking.models import BankAccount
from .models import BillerCategory, Biller
from decimal import Decimal

class BillPaymentForm(forms.Form):
    source_account = forms.ModelChoiceField(
        queryset=BankAccount.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select form-select-lg', 'id': 'source-account'}),
        label="Pay From Account"
    )
    biller = forms.ModelChoiceField(
        queryset=Biller.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select form-select-lg', 'id': 'biller-select'}),
        label="Service Provider / Biller"
    )
    consumer_number = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Enter Consumer No. / Customer ID / Mobile No.', 'id': 'consumer-number'}),
        label="Consumer Identification"
    )
    amount = forms.DecimalField(
        min_value=Decimal('10.00'),
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'placeholder': '₹ 0.00', 'step': '1', 'id': 'bill-amount'}),
        label="Bill Amount (₹)"
    )
    transaction_pin = forms.CharField(
        max_length=6,
        widget=forms.PasswordInput(attrs={'class': 'form-control form-control-lg text-center', 'placeholder': 'Enter 4-digit PIN', 'id': 'bill-pin'}),
        label="Transaction PIN"
    )

    def __init__(self, *args, user=None, category_code=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['source_account'].queryset = BankAccount.objects.filter(user=user, status='ACTIVE')
        if category_code:
            self.fields['biller'].queryset = Biller.objects.filter(category__code=category_code, is_active=True)
