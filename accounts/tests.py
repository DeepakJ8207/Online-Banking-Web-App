from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from accounts.models import Branch, CustomerProfile, OTPVerification
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
        self.assertEqual(self.client.get(reverse('accounts:update_profile')).status_code, 302)
        self.assertEqual(self.client.get(reverse('accounts:change_password')).status_code, 200)
        self.assertEqual(self.client.get(reverse('accounts:notifications')).status_code, 200)
        self.assertEqual(self.client.get(reverse('accounts:audit_logs')).status_code, 200)

    def test_admin_registration_and_customer_first_login_flow(self):
        admin = User.objects.create_superuser('superadmin', 'admin@bank.demo', 'Admin@12345')
        self.client.force_login(admin)

        # 1. Admin registers new customer
        res = self.client.post(reverse('admin_dashboard:create_customer'), {
            'first_name': 'Karan',
            'last_name': 'Mehta',
            'username': 'karan_mehta',
            'email': 'karan.mehta@example.com',
            'phone_number': '9811223344',
            'branch': self.branch.id,
            'account_type': 'SAVINGS',
            'initial_deposit': '20000.00',
            'initial_password': 'InitPassword@123'
        }, follow=True)
        self.assertEqual(res.status_code, 200)

        karan = User.objects.get(username='karan_mehta')
        self.assertTrue(karan.profile.is_first_login)
        self.assertFalse(karan.profile.has_set_upi_pin)

        # 2. Customer login step 1 (Password)
        c_client = Client()
        res_l1 = c_client.post(reverse('accounts:login'), {
            'username': 'karan_mehta',
            'password': 'InitPassword@123'
        }, follow=True)
        self.assertEqual(res_l1.status_code, 200)
        otp = c_client.session.get('demo_login_otp')
        self.assertIsNotNone(otp)

        # 3. Customer login step 2 (Email OTP) -> Redirect to First-Time Setup
        res_otp = c_client.post(reverse('accounts:login_otp'), {'otp_code': otp}, follow=True)
        self.assertEqual(res_otp.status_code, 200)
        self.assertEqual(res_otp.redirect_chain[-1][0], '/first-time-setup/')

        # 4. First-time Setup: Set UPI PIN
        res_setup = c_client.post(reverse('accounts:first_time_setup'), {
            'upi_pin': '9988',
            'confirm_upi_pin': '9988',
            'new_password': '',
            'confirm_new_password': ''
        }, follow=True)
        self.assertEqual(res_setup.status_code, 200)
        self.assertEqual(res_setup.redirect_chain[-1][0], '/dashboard/')

        karan.profile.refresh_from_db()
        self.assertFalse(karan.profile.is_first_login)
        self.assertTrue(karan.profile.has_set_upi_pin)
        self.assertTrue(karan.bank_accounts.first().check_transaction_pin('9988'))

    def test_forgot_password_email_otp_flow(self):
        c_client = Client()

        # Step 1: Identifier
        res1 = c_client.post(reverse('accounts:forgot_password'), {'identifier': 'testuser'}, follow=True)
        self.assertEqual(res1.status_code, 200)
        otp = c_client.session.get('demo_forgot_otp')
        self.assertIsNotNone(otp)

        # Step 2: Enter Email OTP
        res2 = c_client.post(reverse('accounts:forgot_password'), {'otp_code': otp}, follow=True)
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(c_client.session.get('forgot_step'), 3)

        # Step 3: Set New Password
        res3 = c_client.post(reverse('accounts:forgot_password'), {
            'new_password': 'UpdatedPass@123',
            'confirm_new_password': 'UpdatedPass@123'
        }, follow=True)
        self.assertEqual(res3.status_code, 200)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('UpdatedPass@123'))

    def test_multi_account_link_switch_and_remove(self):
        # Create second user
        user2 = User.objects.create_user('user_two', 'user2@bank.demo', 'Pass@12345', first_name='User', last_name='Two')
        CustomerProfile.objects.create(user=user2, cif_number='88888888888', phone_number='9811223399')
        BankAccount.objects.create(user=user2, account_number='1111222233334444', branch=self.branch, balance=Decimal('50000.00'))

        self.client.force_login(self.user)

        # 1. Profile update redirects to profile (disabled online)
        res_prof = self.client.get(reverse('accounts:update_profile'), follow=True)
        self.assertRedirects(res_prof, reverse('accounts:profile'))

        # 2. Step 1: Submit credentials to link second account -> redirects to OTP
        res_link = self.client.post(reverse('accounts:link_account'), {
            'username': 'user_two',
            'password': 'Pass@12345',
            'switch_now': '0'
        }, follow=True)
        self.assertEqual(res_link.status_code, 200)
        self.assertEqual(self.client.session.get('link_pending_user_id'), user2.id)

        # 3. Step 2: Verify OTP
        otp_obj = OTPVerification.objects.filter(purpose='LINK_ACCOUNT', user=user2, is_used=False).latest('created_at')
        res_otp = self.client.post(reverse('accounts:link_account_otp'), {
            'otp_code': otp_obj.otp_code
        }, follow=True)
        self.assertEqual(res_otp.status_code, 200)
        self.assertIn(user2.id, self.client.session.get('linked_user_ids', []))

        # 4. Switch account to user2
        res_switch = self.client.get(reverse('accounts:switch_account', kwargs={'user_id': user2.id}), follow=True)
        self.assertEqual(res_switch.status_code, 200)
        self.assertEqual(int(self.client.session['_auth_user_id']), user2.id)

        # 5. Remove linked account
        res_remove = self.client.post(reverse('accounts:remove_linked_account', kwargs={'user_id': self.user.id}), follow=True)
        self.assertEqual(res_remove.status_code, 200)
        self.assertNotIn(self.user.id, self.client.session.get('linked_user_ids', []))

    def test_change_password_forgot_via_otp(self):
        self.client.force_login(self.user)
        res_get = self.client.get(reverse('accounts:change_password_forgot'))
        self.assertEqual(res_get.status_code, 200)
        self.assertContains(res_get, "Reset Account Password")

        otp_obj = OTPVerification.objects.filter(purpose='PASSWORD_RESET', user=self.user, is_used=False).latest('created_at')
        res_post = self.client.post(reverse('accounts:change_password_forgot'), {
            'otp_code': otp_obj.otp_code,
            'new_password': 'BrandNewPass@2026',
            'confirm_password': 'BrandNewPass@2026'
        }, follow=True)
        self.assertEqual(res_post.status_code, 200)
        self.assertRedirects(res_post, reverse('accounts:profile'))

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('BrandNewPass@2026'))



