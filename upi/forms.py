from django import forms
from banking.models import BankAccount
from .models import UPIAccount
import re

class CreateUPIForm(forms.Form):
    bank_account = forms.ModelChoiceField(
        queryset=BankAccount.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'}),
        label="Link Bank Account"
    )
    custom_handle = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'e.g. priya or sanjay.dev'}),
        label="Choose UPI Handle"
    )
    upi_pin = forms.CharField(
        max_length=4,
        min_length=4,
        widget=forms.PasswordInput(attrs={'class': 'form-control form-control-lg text-center', 'placeholder': 'Enter 4-digit PIN', 'maxlength': '4', 'pattern': '[0-9]{4}', 'inputmode': 'numeric'}),
        label="Set 4-Digit UPI PIN"
    )
    confirm_upi_pin = forms.CharField(
        max_length=4,
        min_length=4,
        widget=forms.PasswordInput(attrs={'class': 'form-control form-control-lg text-center', 'placeholder': 'Confirm 4-digit PIN', 'maxlength': '4', 'pattern': '[0-9]{4}', 'inputmode': 'numeric'}),
        label="Confirm 4-Digit UPI PIN"
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['bank_account'].queryset = BankAccount.objects.filter(user=user, status='ACTIVE')

    def clean_custom_handle(self):
        handle = self.cleaned_data.get('custom_handle', '').strip().lower()
        if not re.match(r'^[a-z0-9._-]+$', handle):
            raise forms.ValidationError("Handle can only contain lowercase letters, numbers, dots, and hyphens.")
        full_vpa = f"{handle}@primereserve"
        if UPIAccount.objects.filter(upi_id__iexact=full_vpa).exists():
            raise forms.ValidationError(f"UPI ID '{full_vpa}' is already registered. Please choose a different handle.")
        return handle

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('upi_pin')
        p2 = cleaned.get('confirm_upi_pin')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("UPI PINs do not match.")
        if p1 and not (len(p1) == 4 and p1.isdigit()):
            raise forms.ValidationError("UPI PIN must be exactly 4 numeric digits.")
        return cleaned


class ChangeUPIPINForm(forms.Form):
    old_pin = forms.CharField(
        max_length=6,
        widget=forms.PasswordInput(attrs={'class': 'form-control text-center', 'placeholder': 'Enter Current UPI PIN', 'inputmode': 'numeric'}),
        label="Current UPI PIN"
    )
    new_pin = forms.CharField(
        max_length=4,
        min_length=4,
        widget=forms.PasswordInput(attrs={'class': 'form-control text-center', 'placeholder': 'Enter 4-Digit PIN', 'maxlength': '4', 'pattern': '[0-9]{4}', 'inputmode': 'numeric'}),
        label="New 4-Digit UPI PIN"
    )
    confirm_new_pin = forms.CharField(
        max_length=4,
        min_length=4,
        widget=forms.PasswordInput(attrs={'class': 'form-control text-center', 'placeholder': 'Confirm 4-Digit PIN', 'maxlength': '4', 'pattern': '[0-9]{4}', 'inputmode': 'numeric'}),
        label="Confirm New UPI PIN"
    )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('new_pin')
        p2 = cleaned.get('confirm_new_pin')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("New UPI PINs do not match.")
        if p1 and not (len(p1) == 4 and p1.isdigit()):
            raise forms.ValidationError("New UPI PIN must be exactly 4 numeric digits.")
        return cleaned


class ForgotUPIPINForm(forms.Form):
    otp_code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control text-center font-monospace fs-4 tracking-widest',
            'placeholder': '••••••',
            'maxlength': '6',
            'pattern': '[0-9]{6}',
            'inputmode': 'numeric',
            'autocomplete': 'one-time-code',
            'autofocus': 'autofocus'
        }),
        label="Enter 6-Digit Email OTP"
    )
    new_pin = forms.CharField(
        max_length=4,
        min_length=4,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control text-center',
            'placeholder': 'Enter 4-Digit PIN',
            'maxlength': '4',
            'pattern': '[0-9]{4}',
            'inputmode': 'numeric'
        }),
        label="New 4-Digit UPI PIN"
    )
    confirm_new_pin = forms.CharField(
        max_length=4,
        min_length=4,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control text-center',
            'placeholder': 'Confirm 4-Digit PIN',
            'maxlength': '4',
            'pattern': '[0-9]{4}',
            'inputmode': 'numeric'
        }),
        label="Confirm New UPI PIN"
    )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('new_pin')
        p2 = cleaned.get('confirm_new_pin')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("New UPI PINs do not match.")
        if p1 and not (len(p1) == 4 and p1.isdigit()):
            raise forms.ValidationError("New UPI PIN must be exactly 4 numeric digits.")
        otp = cleaned.get('otp_code')
        if otp and not (len(otp) == 6 and otp.isdigit()):
            raise forms.ValidationError("OTP code must be 6 numeric digits.")
        return cleaned
