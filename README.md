# PRIME RESERVE BANK — Online Banking Web Application
## Complete College Demonstration Project

### 1. Project Overview
**PRIME RESERVE BANK** is a fully functional, highly secure educational web application simulating a modern Indian digital banking portal. It is built using the exact technology stack required for your college project:
- **Frontend**: HTML5, CSS3, Bootstrap 5, Vanilla JavaScript, Chart.js, Bootstrap Icons.
- **Backend**: Python 3.10+, Django 5+.
- **Database**: MySQL (with PyMySQL & SQLite dual-engine support).
- **PDF Generation**: ReportLab.
- **Version Control**: Git & GitHub.

> [!IMPORTANT]
> **EDUCATIONAL DEMONSTRATION NOTICE**  
> This project is designed strictly for academic evaluation and demonstration. It **does NOT** connect to any real bank account, real UPI payment gateways, or external financial systems. All account balances, transfers, bills, and transactions are **100% simulated** within the database.

---

### 2. Project Folder Structure
```text
Online banking web application/
│
├── manage.py
├── requirements.txt
├── README.md
├── .gitignore
├── .env.example
│
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── accounts/
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── forms.py
│   └── services.py
│
├── banking/
│   ├── admin.py
│   ├── models.py
│   ├── views.py
│   └── urls.py
│
├── transfers/
│   ├── services.py
│   ├── forms.py
│   ├── views.py
│   └── urls.py
│
├── transactions/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── pdf_generator.py
│
├── beneficiaries/
│   ├── models.py
│   ├── views.py
│   └── urls.py
│
├── upi/
│   ├── models.py
│   ├── views.py
│   └── urls.py
│
├── bills/
│   ├── models.py
│   ├── views.py
│   └── urls.py
│
├── finance/
│   ├── models.py
│   ├── views.py
│   └── urls.py
│
├── dashboard/
│   ├── views.py
│   └── urls.py
│
├── templates/
│   ├── base.html
│   ├── base_auth.html
│   ├── base_dashboard.html
│   ├── home.html
│   ├── auth/
│   ├── dashboard/
│   ├── account/
│   ├── transfers/
│   ├── beneficiaries/
│   ├── transactions/
│   ├── bills/
│   ├── upi/
│   ├── finance/
│   └── profile/
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
└── media/
    └── profile_photos/
```

---

### 3. Python Requirements (`requirements.txt`)
```text
Django>=5.0.0
PyMySQL>=1.1.0
reportlab>=4.0.0
pillow>=10.0.0
python-dotenv>=1.0.0
cryptography>=42.0.0
qrcode>=7.4.0
```

---

### 4. Environment Configuration (`.env.example`)
```env
SECRET_KEY=django-insecure-prime-reserve-bank-secret-key-change-in-production
DEBUG=True
DB_ENGINE=mysql
DB_NAME=prime_reserve_bank_db
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_PORT=3306

# Optional Email Configuration for OTP/Alerts
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
```

---

### 5. Core MySQL Database Models

```python
from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    cif_number = models.CharField(max_length=20, unique=True)
    mobile_number = models.CharField(max_length=15, unique=True)
    address = models.TextField()
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    pincode = models.CharField(max_length=10)
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    kyc_status = models.CharField(max_length=20, default='VERIFIED')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.cif_number})"

class BankAccount(models.Model):
    ACCOUNT_TYPES = (
        ('SAVINGS', 'Prime Savings Account'),
        ('CURRENT', 'Prime Current Account'),
        ('SALARY', 'Prime Corporate Salary Account'),
        ('FIXED_DEPOSIT', 'Prime Fixed Deposit Account'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bank_accounts')
    account_number = models.CharField(max_length=16, unique=True)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='SAVINGS')
    branch = models.ForeignKey('accounts.Branch', on_delete=models.PROTECT, related_name='accounts')
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, default='ACTIVE')
    transaction_pin_hash = models.CharField(max_length=128, blank=True)
    nominee_name = models.CharField(max_length=100, blank=True, default='')
    daily_transfer_limit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('100000.00'))
    opening_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.account_number} - {self.user.username} (₹{self.balance:,.2f})"

class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('BANK_TRANSFER', 'Bank Account Transfer (IMPS/NEFT)'),
        ('UPI_TRANSFER', 'UPI Transfer'),
        ('MOBILE_TRANSFER', 'Mobile Number Transfer'),
        ('SELF_TRANSFER', 'Self Account Transfer'),
        ('BILL_PAYMENT', 'Utility Bill Payment'),
        ('RECHARGE', 'Mobile / DTH Recharge'),
        ('CREDIT', 'Account Credit / Deposit'),
        ('DEBIT', 'Account Debit / Withdrawal'),
    )
    STATUS_CHOICES = (
        ('SUCCESS', 'Success'),
        ('PENDING', 'Pending'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    )
    transaction_id = models.CharField(max_length=32, unique=True, editable=False)
    reference_number = models.CharField(max_length=32, unique=True, editable=False)
    sender_account = models.ForeignKey(BankAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_transactions')
    receiver_account = models.ForeignKey(BankAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_transactions')
    sender_name = models.CharField(max_length=150)
    receiver_name = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    transaction_type = models.CharField(max_length=25, choices=TRANSACTION_TYPES, default='BANK_TRANSFER')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='SUCCESS')
    category = models.CharField(max_length=20, default='TRANSFER')
    remarks = models.CharField(max_length=255, blank=True, default="Fund Transfer")
    sender_balance_after = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    receiver_balance_after = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.reference_number} | ₹{self.amount} | {self.status}"
```

---

### 6. Secure Transaction Logic (`transaction.atomic`)
To prevent race conditions, double spending, and negative balances, all balance updates are wrapped in `transaction.atomic()` with row-level locking (`select_for_update`):

```python
from django.db import transaction
from decimal import Decimal
from banking.models import BankAccount
from transactions.models import Transaction

def execute_fund_transfer(sender_acc_id, receiver_acc_id, amount, remarks='Fund Transfer'):
    amount = Decimal(str(amount))
    if amount <= Decimal('0.00'):
        raise ValueError("Transfer amount must be greater than zero.")

    with transaction.atomic():
        # Lock accounts for update
        sender = BankAccount.objects.select_for_update().get(id=sender_acc_id)
        receiver = BankAccount.objects.select_for_update().get(id=receiver_acc_id)
        
        if sender.status != 'ACTIVE':
            raise ValueError("Sender account is not active.")

        if sender.balance < amount:
            raise ValueError("Insufficient balance in source account.")
            
        # Debit sender
        sender.balance -= amount
        sender.save(update_fields=['balance', 'updated_at'])
        
        # Credit receiver
        receiver.balance += amount
        receiver.save(update_fields=['balance', 'updated_at'])
        
        # Create immutable transaction audit log
        txn = Transaction.objects.create(
            sender_account=sender,
            receiver_account=receiver,
            sender_name=sender.user.get_full_name(),
            receiver_name=receiver.user.get_full_name(),
            amount=amount,
            transaction_type='BANK_TRANSFER',
            status='SUCCESS',
            remarks=remarks,
            sender_balance_after=sender.balance,
            receiver_balance_after=receiver.balance
        )
        return txn
```

---

### 7. Installation & Setup Guide

1. **Clone or Navigate to Repository**:
   ```bash
   cd "Online banking web application"
   ```

2. **Create and Activate Virtual Environment**:
   ```bash
   python3 -m venv venv
   # On macOS/Linux:
   source venv/bin/activate
   # On Windows:
   venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Database**:
   - Copy `.env.example` to `.env`.
   - Set MySQL credentials (or leave default SQLite fallback for local demonstration).

5. **Run Migrations**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Seed Initial Demo Data**:
   ```bash
   python manage.py seed_demo_data
   ```

7. **Run Development Server**:
   ```bash
   python manage.py runserver
   ```
   Open your browser at **`http://127.0.0.1:8000/`**.

---

### 8. Quick Demo Credentials

| Role | Username | Password | Default PIN | Live Balance | Access URL |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Customer (Aarav)** | `demo_user` | `Demo@12345` | `1234` | ₹1,15,450.00 | `/login/` -> 1-Click Login |
| **Customer (Priya)** | `priya_sharma` | `Demo@12345` | `1234` | ₹95,200.00 | `/login/` -> 1-Click Login |
| **Customer (Rahul)** | `rahul_verma` | `Demo@12345` | `1234` | ₹62,750.00 | `/login/` -> 1-Click Login |
| **Bank Manager / Admin** | `admin` | `Admin@12345` | — | Total Overview | `/dashboard/manager-overview/` |

---

### 9. Academic Project Features Checklist

- [x] **Customer NetBanking Portal**: Light, modern UI with 1-click test logins, statements, and cards.
- [x] **Bank Manager / Admin Monitor**: Central overview of all customer balances and real-time transaction audit feeds.
- [x] **Atomic Transactions**: Double-entry ledger with `select_for_update()` row locking.
- [x] **Simulated UPI & Dynamic QR**: Instant QR payment generation with UPI handle support.
- [x] **Utility Bill Payments**: Electricity, Mobile Recharge, Water, Gas, Broadband simulations.
- [x] **Loans & Deposits**: Personal, Home, Education loans with EMI calculator + FD/RD investments.
- [x] **ReportLab PDF Generator**: Printable PDF account statements with bank seal.
- [x] **Security**: Session timeout, password hashing, transaction PIN verification, and audit logs.

---

### 10. Disclaimer
*This website is a college educational project for demonstration purposes only. It is not connected to any real banking institution, payment gateway, or financial system.*
