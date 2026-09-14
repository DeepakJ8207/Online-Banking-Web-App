from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from accounts.models import Branch, CustomerProfile
from banking.models import BankAccount
from beneficiaries.models import Beneficiary
from bills.models import BillerCategory, Biller
from finance.models import LoanProduct
from decimal import Decimal

class WebViewsIntegrationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.branch = Branch.objects.create(
            branch_name="Mumbai Main", branch_code="PRM001", ifsc_code="PRMB0001001",
            address="Fort", city="Mumbai", state="Maharashtra", pincode="400001", contact_number="022-22661001"
        )
        self.user = User.objects.create_user(username='testuser', password='Password@123', email='test@bank.demo')
        self.profile = CustomerProfile.objects.create(
            user=self.user, cif_number="98765432101", phone_number="9876543210", kyc_status="VERIFIED"
        )
        self.account = BankAccount.objects.create(
            user=self.user, account_number="10010020030045", branch=self.branch,
            balance=Decimal('100000.00'), status='ACTIVE'
        )
        self.account.set_transaction_pin('1234')
        self.account.save()

        self.category = BillerCategory.objects.create(code='ELECTRICITY', name='Electricity')
        self.biller = Biller.objects.create(category=self.category, name='Tata Power')
        self.loan_prod = LoanProduct.objects.create(name='Personal Loan', loan_type='PERSONAL', interest_rate=Decimal('10.50'))

    def test_public_views(self):
        # 1. Landing Page
        res = self.client.get(reverse('accounts:home'))
        self.assertEqual(res.status_code, 200)

        # 2. Login Page
        res = self.client.get(reverse('accounts:login'))
        self.assertEqual(res.status_code, 200)

        # 3. Register Page
        res = self.client.get(reverse('accounts:register'))
        self.assertEqual(res.status_code, 200)

        # 4. Forgot Password Page
        res = self.client.get(reverse('accounts:forgot_password'))
        self.assertEqual(res.status_code, 200)

        # 5. Calculators
        self.assertEqual(self.client.get(reverse('finance:emi_calculator')).status_code, 200)
        self.assertEqual(self.client.get(reverse('finance:fd_calculator')).status_code, 200)
        self.assertEqual(self.client.get(reverse('finance:rd_calculator')).status_code, 200)
        self.assertEqual(self.client.get(reverse('finance:sip_calculator')).status_code, 200)

    def test_authenticated_views(self):
        self.client.login(username='testuser', password='Password@123')

        # Dashboard
        res = self.client.get(reverse('dashboard:home'))
        self.assertEqual(res.status_code, 200)

        # Analytics API
        res = self.client.get(reverse('dashboard:analytics_api'))
        self.assertEqual(res.status_code, 200)
        self.assertIn('monthly_labels', res.json())

        # My Account & Details
        self.assertEqual(self.client.get(reverse('banking:my_account')).status_code, 200)
        self.assertEqual(self.client.get(reverse('banking:account_details', args=[self.account.id])).status_code, 200)

        # Transfers Hub & Views
        self.assertEqual(self.client.get(reverse('transfers:home')).status_code, 200)
        self.assertEqual(self.client.get(reverse('transfers:bank_transfer')).status_code, 200)
        self.assertEqual(self.client.get(reverse('transfers:mobile_transfer')).status_code, 200)
        self.assertEqual(self.client.get(reverse('transfers:upi_transfer')).status_code, 200)
        self.assertEqual(self.client.get(reverse('transfers:self_transfer')).status_code, 200)

        # Beneficiaries
        self.assertEqual(self.client.get(reverse('beneficiaries:list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('beneficiaries:add')).status_code, 200)

        # Transactions
        self.assertEqual(self.client.get(reverse('transactions:history')).status_code, 200)

        # PDF Statement Download
        res = self.client.get(reverse('transactions:download_statement') + f'?account_id={self.account.id}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/pdf')

        # Bills
        self.assertEqual(self.client.get(reverse('bills:home')).status_code, 200)
        self.assertEqual(self.client.get(reverse('bills:pay_category', args=['ELECTRICITY'])).status_code, 200)

        # UPI Hub & QR
        self.assertEqual(self.client.get(reverse('upi:home')).status_code, 200)
        self.assertEqual(self.client.get(reverse('upi:create')).status_code, 200)

        # Finance
        self.assertEqual(self.client.get(reverse('finance:home')).status_code, 200)
        self.assertEqual(self.client.get(reverse('finance:loans')).status_code, 200)
        self.assertEqual(self.client.get(reverse('finance:loan_apply')).status_code, 200)
        self.assertEqual(self.client.get(reverse('finance:deposits')).status_code, 200)
        self.assertEqual(self.client.get(reverse('finance:open_fd')).status_code, 200)
        self.assertEqual(self.client.get(reverse('finance:open_rd')).status_code, 200)

        # Profile & Settings
        self.assertEqual(self.client.get(reverse('accounts:profile')).status_code, 200)
        self.assertEqual(self.client.get(reverse('accounts:update_profile')).status_code, 200)
        self.assertEqual(self.client.get(reverse('accounts:change_password')).status_code, 200)
        self.assertEqual(self.client.get(reverse('accounts:notifications')).status_code, 200)
        self.assertEqual(self.client.get(reverse('accounts:audit_logs')).status_code, 200)
