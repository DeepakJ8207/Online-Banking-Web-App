from django import forms
from django.contrib.auth.models import User
from decimal import Decimal
from .models import CustomerProfile, Branch, OTPVerification
from banking.models import BankAccount
import re

class UserLoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your User ID / Username',
            'autocomplete': 'username',
            'id': 'login-username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your Password',
            'autocomplete': 'current-password',
            'id': 'login-password'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'rememberMe'})
    )


class LoginOTPForm(forms.Form):
    otp_code = forms.CharField(
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-center tracking-widest letter-spacing-lg font-monospace fs-4 py-2',
            'placeholder': '••••••',
            'id': 'login-otp',
            'maxlength': '6',
            'autofocus': 'autofocus'
        }),
        help_text="Enter the 6-digit verification code sent to your registered email address"
    )


class FirstTimeSetupForm(forms.Form):
    upi_pin = forms.CharField(
        max_length=6,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg text-center tracking-widest font-monospace fs-4',
            'placeholder': '••••',
            'maxlength': '4',
            'id': 'upi-pin'
        }),
        help_text="Create a 4-digit security PIN for UPI transfers & ATM authorization"
    )
    confirm_upi_pin = forms.CharField(
        max_length=6,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg text-center tracking-widest font-monospace fs-4',
            'placeholder': '••••',
            'maxlength': '4',
            'id': 'confirm-upi-pin'
        }),
        help_text="Re-enter your 4-digit PIN"
    )
    new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'New Password (optional)',
            'id': 'setup-new-pwd'
        }),
        help_text="Optional: Update your temporary password to a personalized password"
    )
    confirm_new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Confirm New Password',
            'id': 'setup-confirm-pwd'
        })
    )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('upi_pin', '').strip()
        p2 = cleaned.get('confirm_upi_pin', '').strip()
        if p1 != p2:
            raise forms.ValidationError("UPI PINs do not match. Please re-enter carefully.")
        if not p1.isdigit() or len(p1) not in (4, 6):
            raise forms.ValidationError("UPI PIN must be 4 numeric digits (e.g. 1234).")

        new_pwd = cleaned.get('new_password')
        confirm_pwd = cleaned.get('confirm_new_password')
        if new_pwd:
            if new_pwd != confirm_pwd:
                raise forms.ValidationError("New passwords do not match.")
            if len(new_pwd) < 8:
                raise forms.ValidationError("New password must be at least 8 characters long.")
        return cleaned


class AdminCustomerRegistrationForm(forms.Form):
    """
    Used by Bank Manager / Admin to register a new customer in branch
    and dispatch official account credentials to the customer's email.
    """
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Aarav', 'id': 'adm-first-name'})
    )
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Sharma', 'id': 'adm-last-name'})
    )
    username = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. aarav_sharma', 'id': 'adm-username'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'customer@example.com', 'id': 'adm-email'}),
        help_text="Account credentials & login OTP will be sent to this email address"
    )
    phone_number = forms.CharField(
        max_length=10,
        min_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '10-digit mobile number',
            'id': 'adm-phone',
            'maxlength': '10',
            'pattern': r'[0-9]{10}',
            'inputmode': 'numeric',
            'oninput': "this.value = this.value.replace(/[^0-9]/g, '').slice(0, 10);"
        }),
        error_messages={
            'max_length': 'Mobile number cannot exceed 10 digits.',
            'min_length': 'Mobile number must be exactly 10 digits.',
            'required': 'Mobile number is required.'
        }
    )
    gender = forms.ChoiceField(
        choices=CustomerProfile.GENDER_CHOICES,
        required=False,
        initial='MALE',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'adm-gender'})
    )
    address = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Flat / House No., Street, Area', 'id': 'adm-address'}),
        label="Residential Address"
    )
    city = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Mumbai', 'id': 'adm-city'})
    )
    state = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Maharashtra', 'id': 'adm-state'})
    )
    pincode = forms.CharField(
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 400001',
            'id': 'adm-pincode',
            'maxlength': '6',
            'pattern': r'[0-9]{6}',
            'inputmode': 'numeric',
            'oninput': "this.value = this.value.replace(/[^0-9]/g, '').slice(0, 6);"
        })
    )
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(),
        empty_label="Select Branch",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'adm-branch'})
    )
    account_type = forms.ChoiceField(
        choices=[
            ('SAVINGS', 'Prime Savings Account'),
            ('CURRENT', 'Prime Current Account'),
            ('SALARY', 'Prime Corporate Salary Account')
        ],
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'adm-account-type'})
    )
    initial_deposit = forms.DecimalField(
        min_value=Decimal('500.00'),
        initial=Decimal('25000.00'),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '₹ Initial Deposit Amount', 'id': 'adm-deposit'})
    )
    initial_password = forms.CharField(
        initial="Prime@12345",
        widget=forms.TextInput(attrs={'class': 'form-control font-monospace', 'placeholder': 'Initial Temporary Password', 'id': 'adm-password'}),
        help_text="Temporary password dispatched to customer email"
    )

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose another.")
        if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
            raise forms.ValidationError("Username can only contain letters, numbers, dots, and underscores.")
        return username

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        digits = re.sub(r'\D', '', phone)
        if len(digits) != 10:
            raise forms.ValidationError("Mobile number must be exactly 10 digits (no more, no less).")
        if not re.match(r'^[6-9]\d{9}$', digits):
            raise forms.ValidationError("Please enter a valid 10-digit mobile number starting with 6, 7, 8, or 9.")
        if CustomerProfile.objects.filter(phone_number=digits).exists():
            raise forms.ValidationError("This mobile number is already registered with another customer.")
        return digits

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already registered with another user.")
        return email


class ForgotPasswordStep1Form(forms.Form):
    identifier = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter Username, CIF Number, or Registered Email',
            'id': 'forgot-identifier'
        }),
        help_text="We will send a 6-digit password reset OTP to your registered email address"
    )


class ForgotPasswordStep2Form(forms.Form):
    otp_code = forms.CharField(
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-center tracking-widest font-monospace fs-4',
            'placeholder': '••••••',
            'id': 'forgot-otp',
            'maxlength': '6'
        }),
        help_text="Enter the 6-digit OTP code sent to your registered email"
    )


class ForgotPasswordStep3Form(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter new password',
            'id': 'forgot-new-pwd'
        })
    )
    confirm_new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Confirm new password',
            'id': 'forgot-confirm-pwd'
        })
    )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('new_password')
        p2 = cleaned.get('confirm_new_password')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        if p1 and len(p1) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
        return cleaned


class ProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    phone_number = forms.CharField(
        max_length=10,
        min_length=10,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'maxlength': '10',
            'placeholder': '10-digit mobile number',
            'pattern': r'[0-9]{10}',
            'inputmode': 'numeric',
            'oninput': "this.value = this.value.replace(/[^0-9]/g, '').slice(0, 10);"
        }),
        error_messages={
            'max_length': 'Mobile number cannot exceed 10 digits.',
            'min_length': 'Mobile number must be exactly 10 digits.',
        }
    )

    class Meta:
        model = CustomerProfile
        fields = ['phone_number', 'date_of_birth', 'profile_photo']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'profile_photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        digits = re.sub(r'\D', '', phone)
        if len(digits) != 10:
            raise forms.ValidationError("Mobile number must be exactly 10 digits.")
        if not re.match(r'^[6-9]\d{9}$', digits):
            raise forms.ValidationError("Please enter a valid 10-digit mobile number starting with 6, 7, 8, or 9.")
        qs = CustomerProfile.objects.filter(phone_number=digits)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This mobile number is already registered with another customer.")
        return digits


class PasswordChangeCustomForm(forms.Form):
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Current Password'})
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New Password'})
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm New Password'})
    )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('new_password')
        p2 = cleaned.get('confirm_password')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("New passwords do not match.")
        if p1 and len(p1) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
        return cleaned


class ChangePasswordViaOTPForm(forms.Form):
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
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New Password'}),
        label="New Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm New Password'}),
        label="Confirm New Password"
    )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('new_password')
        p2 = cleaned.get('confirm_password')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("New passwords do not match.")
        if p1 and len(p1) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
        otp = cleaned.get('otp_code')
        if otp and not (len(otp) == 6 and otp.isdigit()):
            raise forms.ValidationError("OTP code must be 6 numeric digits.")
        return cleaned
