from django import forms
from .models import Beneficiary
import re

class BeneficiaryForm(forms.ModelForm):
    confirm_account_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Re-enter account number'}),
        label="Confirm Account Number"
    )

    class Meta:
        model = Beneficiary
        fields = ['beneficiary_name', 'account_number', 'ifsc_code', 'bank_name', 'nickname', 'mobile_number', 'email']
        widgets = {
            'beneficiary_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full legal name'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '9 to 18 digit account number'}),
            'ifsc_code': forms.TextInput(attrs={'class': 'form-control text-uppercase', 'placeholder': 'e.g. PRMB0001001 or SBIN0001234'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Bank name'}),
            'nickname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional nickname (e.g. Mom, Landlord)'}),
            'mobile_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10-digit mobile number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'beneficiary@email.com'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['confirm_account_number'].initial = self.instance.account_number

    def clean_ifsc_code(self):
        ifsc = self.cleaned_data.get('ifsc_code', '').strip().upper()
        if not re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', ifsc):
            raise forms.ValidationError("Invalid IFSC Code format. Must be 11 alphanumeric characters (e.g. PRMB0001001).")
        return ifsc

    def clean(self):
        cleaned = super().clean()
        acc = cleaned.get('account_number')
        confirm_acc = cleaned.get('confirm_account_number')
        if acc and confirm_acc and acc != confirm_acc:
            raise forms.ValidationError({'confirm_account_number': "Account numbers do not match."})

        if self.user and acc:
            # Check user's own accounts
            if self.user.bank_accounts.filter(account_number=acc).exists():
                raise forms.ValidationError({'account_number': "You cannot add your own bank account as an external beneficiary. Use Self-Transfer."})
            # Check duplicate beneficiary
            existing = Beneficiary.objects.filter(user=self.user, account_number=acc)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError({'account_number': "A beneficiary with this account number already exists in your list."})

        return cleaned
