from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from accounts.models import Branch, CustomerProfile, OTPVerification
from banking.models import BankAccount
from upi.models import UPIAccount
from decimal import Decimal

class UPIServicesTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.branch = Branch.objects.create(
            branch_name="Mumbai Main", branch_code="PRM001", ifsc_code="PRMB0001001",
            address="Fort", city="Mumbai", state="Maharashtra", pincode="400001", contact_number="022-22661001"
        )
        self.user = User.objects.create_user(username='upitestuser', password='Password@123', email='upitest@bank.demo')
        self.profile = CustomerProfile.objects.create(
            user=self.user, cif_number="98765432102", phone_number="9876543212", kyc_status="VERIFIED"
        )
        self.account = BankAccount.objects.create(
            user=self.user, account_number="10010020030046", branch=self.branch,
            balance=Decimal('50000.00'), status='ACTIVE'
        )
        self.upi = UPIAccount.objects.create(
            user=self.user,
            bank_account=self.account,
            upi_id="upitest@primereserve"
        )
        self.upi.set_pin("1234")
        self.upi.save()
        self.client.force_login(self.user)

    def test_change_upi_pin_requires_4_digits(self):
        # Reject 6 digits
        res = self.client.post(reverse('upi:change_pin', kwargs={'upi_id': self.upi.upi_id}), {
            'old_pin': '1234',
            'new_pin': '123456',
            'confirm_new_pin': '123456'
        })
        self.assertEqual(res.status_code, 200)
        self.upi.refresh_from_db()
        self.assertTrue(self.upi.check_pin('1234'))

        # Accept valid 4 digits
        res_ok = self.client.post(reverse('upi:change_pin', kwargs={'upi_id': self.upi.upi_id}), {
            'old_pin': '1234',
            'new_pin': '5678',
            'confirm_new_pin': '5678'
        }, follow=True)
        self.assertEqual(res_ok.status_code, 200)
        self.upi.refresh_from_db()
        self.assertTrue(self.upi.check_pin('5678'))

    def test_forgot_upi_pin_flow_with_otp(self):
        # GET request triggers OTP dispatch
        res_get = self.client.get(reverse('upi:forgot_pin', kwargs={'upi_id': self.upi.upi_id}))
        self.assertEqual(res_get.status_code, 200)
        self.assertContains(res_get, "Forgot UPI PIN")
        self.assertContains(res_get, "Reset 4-digit UPI PIN")

        # Verify OTP was created
        otp_obj = OTPVerification.objects.filter(purpose='UPI_PIN_RESET', user=self.user, is_used=False).latest('created_at')
        self.assertIsNotNone(otp_obj)

        # POST with valid OTP and new 4-digit PIN
        res_post = self.client.post(reverse('upi:forgot_pin', kwargs={'upi_id': self.upi.upi_id}), {
            'otp_code': otp_obj.otp_code,
            'new_pin': '9876',
            'confirm_new_pin': '9876'
        }, follow=True)
        self.assertEqual(res_post.status_code, 200)
        self.assertRedirects(res_post, reverse('upi:home'))

        self.upi.refresh_from_db()
        self.assertTrue(self.upi.check_pin('9876'))
