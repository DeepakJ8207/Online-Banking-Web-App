from django import forms
from banking.models import BankAccount
from beneficiaries.models import Beneficiary
from decimal import Decimal
import re

class BankTransferForm(forms.Form):
    sender_account = forms.ModelChoiceField(
        queryset=BankAccount.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select form-select-lg', 'id': 'sender-account'}),
        label="Select Source Account"
    )
    beneficiary = forms.ModelChoiceField(
        queryset=Beneficiary.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'beneficiary-select'}),
        label="Choose Saved Beneficiary (Optional)"
    )
    receiver_account_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Beneficiary Account Number', 'id': 'receiver-acc'}),
        label="Beneficiary Account Number"
    )
    receiver_ifsc = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control text-uppercase', 'placeholder': 'e.g. PRMB0001001', 'id': 'receiver-ifsc'}),
        label="Bank IFSC Code"
    )
    receiver_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Beneficiary Account Holder Name', 'id': 'receiver-name'}),
        label="Beneficiary Name"
    )
    amount = forms.DecimalField(
        min_value=Decimal('1.00'),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'placeholder': '₹ 0.00', 'step': '0.01', 'id': 'transfer-amount'}),
        label="Transfer Amount (₹)"
    )
    remarks = forms.CharField(
        max_length=100,
        required=False,
        initial="Fund Transfer",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Remarks (e.g. Rent, College Fees, Gift)'}),
        label="Remarks / Description"
    )
    transaction_pin = forms.CharField(
        max_length=6,
        widget=forms.PasswordInput(attrs={'class': 'form-control form-control-lg text-center letter-spacing-lg', 'placeholder': 'Enter 4-digit PIN', 'id': 'txn-pin'}),
        label="Transaction PIN"
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['sender_account'].queryset = BankAccount.objects.filter(user=user, status='ACTIVE')
            self.fields['beneficiary'].queryset = Beneficiary.objects.filter(user=user, is_active=True)

    def clean_receiver_ifsc(self):
        ifsc = self.cleaned_data.get('receiver_ifsc', '').strip().upper()
        if not re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', ifsc):
            raise forms.ValidationError("Invalid IFSC Code format. Must be 11 characters (e.g. PRMB0001001).")
        return ifsc


class MobileTransferForm(forms.Form):
    sender_account = forms.ModelChoiceField(
        queryset=BankAccount.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'}),
        label="Select Source Account"
    )
    mobile_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Enter 10-digit registered mobile number'}),
        label="Recipient Mobile Number"
    )
    amount = forms.DecimalField(
        min_value=Decimal('1.00'),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'placeholder': '₹ 0.00', 'step': '0.01'}),
        label="Amount (₹)"
    )
    remarks = forms.CharField(
        max_length=100,
        required=False,
        initial="Quick Mobile Pay",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Remarks'}),
        label="Remarks"
    )
    transaction_pin = forms.CharField(
        max_length=6,
        widget=forms.PasswordInput(attrs={'class': 'form-control form-control-lg text-center', 'placeholder': 'Enter 4-digit PIN'}),
        label="Transaction PIN"
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['sender_account'].queryset = BankAccount.objects.filter(user=user, status='ACTIVE')


class UPITransferForm(forms.Form):
    sender_account = forms.ModelChoiceField(
        queryset=BankAccount.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'}),
        label="Select Source Account"
    )
    upi_id = forms.CharField(
        max_length=60,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'e.g. rahul@primereserve or priya@upi'}),
        label="Receiver UPI ID / VPA"
    )
    amount = forms.DecimalField(
        min_value=Decimal('1.00'),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'placeholder': '₹ 0.00', 'step': '0.01'}),
        label="Amount (₹)"
    )
    remarks = forms.CharField(
        max_length=100,
        required=False,
        initial="UPI Payment",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Remarks'}),
        label="Remarks"
    )
    upi_pin = forms.CharField(
        max_length=6,
        widget=forms.PasswordInput(attrs={'class': 'form-control form-control-lg text-center', 'placeholder': 'Enter UPI PIN'}),
        label="UPI PIN"
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['sender_account'].queryset = BankAccount.objects.filter(user=user, status='ACTIVE')

    def clean_upi_id(self):
        vpa = self.cleaned_data.get('upi_id', '').strip()
        if '@' not in vpa:
            raise forms.ValidationError("Invalid UPI ID. Format must be username@bankhandle (e.g. rahul@primereserve).")
        return vpa


class SelfTransferForm(forms.Form):
    from_account = forms.ModelChoiceField(
        queryset=BankAccount.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'}),
        label="From Account (Debit)"
    )
    to_account = forms.ModelChoiceField(
        queryset=BankAccount.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'}),
        label="To Account (Credit)"
    )
    amount = forms.DecimalField(
        min_value=Decimal('1.00'),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'placeholder': '₹ 0.00', 'step': '0.01'}),
        label="Amount (₹)"
    )
    remarks = forms.CharField(
        max_length=100,
        required=False,
        initial="Self Account Transfer",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Remarks'}),
        label="Remarks"
    )
    transaction_pin = forms.CharField(
        max_length=6,
        widget=forms.PasswordInput(attrs={'class': 'form-control form-control-lg text-center', 'placeholder': 'Enter 4-digit PIN'}),
        label="Transaction PIN"
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            qs = BankAccount.objects.filter(user=user, status='ACTIVE')
            self.fields['from_account'].queryset = qs
            self.fields['to_account'].queryset = qs

    def clean(self):
        cleaned = super().clean()
        from_acc = cleaned.get('from_account')
        to_acc = cleaned.get('to_account')
        if from_acc and to_acc and from_acc.id == to_acc.id:
            raise forms.ValidationError("Source and destination accounts must be different.")
        return cleaned
