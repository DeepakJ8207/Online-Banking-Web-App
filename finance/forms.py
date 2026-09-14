from django import forms
from banking.models import BankAccount
from .models import LoanProduct, Loan
from decimal import Decimal

class LoanApplicationForm(forms.Form):
    loan_product = forms.ModelChoiceField(
        queryset=LoanProduct.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select form-select-lg', 'id': 'loan-product-select'}),
        label="Select Loan Scheme"
    )
    disbursal_account = forms.ModelChoiceField(
        queryset=BankAccount.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'}),
        label="Disbursal & EMI Account"
    )
    principal_amount = forms.DecimalField(
        min_value=Decimal('10000.00'),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'placeholder': '₹ Required Loan Amount', 'id': 'loan-amount'}),
        label="Required Loan Amount (₹)"
    )
    tenure_months = forms.IntegerField(
        min_value=6,
        max_value=120,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Tenure in Months (e.g. 24)', 'id': 'loan-tenure'}),
        label="Loan Tenure (Months)"
    )
    purpose = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Purpose of Loan (e.g. Home Renovation, Education)'}),
        label="Purpose of Loan"
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['disbursal_account'].queryset = BankAccount.objects.filter(user=user, status='ACTIVE')


class LoanEMIPaymentForm(forms.Form):
    source_account = forms.ModelChoiceField(
        queryset=BankAccount.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'}),
        label="Pay From Bank Account"
    )
    transaction_pin = forms.CharField(
        max_length=6,
        widget=forms.PasswordInput(attrs={'class': 'form-control form-control-lg text-center', 'placeholder': 'Enter 4-digit PIN'}),
        label="Transaction PIN"
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['source_account'].queryset = BankAccount.objects.filter(user=user, status='ACTIVE')


class FixedDepositForm(forms.Form):
    TENURE_CHOICES = (
        (6, '6 Months (6.50% p.a.)'),
        (12, '12 Months / 1 Year (7.25% p.a.)'),
        (24, '24 Months / 2 Years (7.50% p.a.)'),
        (36, '36 Months / 3 Years (7.40% p.a.)'),
        (60, '60 Months / 5 Years (7.10% p.a.)'),
    )

    linked_account = forms.ModelChoiceField(
        queryset=BankAccount.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select form-select-lg', 'id': 'fd-account'}),
        label="Debit From Account"
    )
    principal_amount = forms.DecimalField(
        min_value=Decimal('5000.00'),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Minimum ₹5,000', 'id': 'fd-principal'}),
        label="Deposit Amount (₹)"
    )
    tenure_months = forms.ChoiceField(
        choices=TENURE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select form-select-lg', 'id': 'fd-tenure'}),
        label="Deposit Tenure & Interest Rate"
    )
    auto_renew = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'fd-renew'}),
        label="Auto-renew upon maturity"
    )
    transaction_pin = forms.CharField(
        max_length=6,
        widget=forms.PasswordInput(attrs={'class': 'form-control form-control-lg text-center', 'placeholder': 'Enter 4-digit PIN'}),
        label="Transaction PIN"
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['linked_account'].queryset = BankAccount.objects.filter(user=user, status='ACTIVE')


class RecurringDepositForm(forms.Form):
    RD_TENURE_CHOICES = (
        (6, '6 Months (6.25% p.a.)'),
        (12, '12 Months / 1 Year (7.00% p.a.)'),
        (24, '24 Months / 2 Years (7.25% p.a.)'),
        (36, '36 Months / 3 Years (7.15% p.a.)'),
        (60, '60 Months / 5 Years (6.85% p.a.)'),
    )

    linked_account = forms.ModelChoiceField(
        queryset=BankAccount.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select form-select-lg', 'id': 'rd-account'}),
        label="Monthly Auto-Debit Account"
    )
    monthly_deposit = forms.DecimalField(
        min_value=Decimal('500.00'),
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Minimum ₹500/month', 'id': 'rd-monthly'}),
        label="Monthly Deposit Amount (₹)"
    )
    tenure_months = forms.ChoiceField(
        choices=RD_TENURE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select form-select-lg', 'id': 'rd-tenure'}),
        label="Deposit Tenure"
    )
    transaction_pin = forms.CharField(
        max_length=6,
        widget=forms.PasswordInput(attrs={'class': 'form-control form-control-lg text-center', 'placeholder': 'Enter 4-digit PIN'}),
        label="Transaction PIN"
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['linked_account'].queryset = BankAccount.objects.filter(user=user, status='ACTIVE')
