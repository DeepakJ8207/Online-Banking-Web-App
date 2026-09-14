from django.test import TestCase, Client
from django.contrib.auth.models import User
from decimal import Decimal
from accounts.models import Branch, CustomerProfile
from banking.models import BankAccount
from beneficiaries.models import Beneficiary
from transactions.models import Transaction
from transfers.services import TransferService
from finance.views import calculate_emi
from transactions.pdf_generator import generate_account_statement_pdf
from django.utils import timezone
from datetime import timedelta

class BankingCoreTestCase(TestCase):
    def setUp(self):
        # 1. Create Branch
        self.branch = Branch.objects.create(
            branch_name="Mumbai Main",
            branch_code="PRM001",
            ifsc_code="PRMB0001001",
            address="Fort",
            city="Mumbai",
            state="Maharashtra",
            pincode="400001",
            contact_number="022-22661001"
        )

        # 2. Create User A (Sender)
        self.user_a = User.objects.create_user(username='usera', password='Password@123', email='a@bank.demo')
        self.profile_a = CustomerProfile.objects.create(
            user=self.user_a, cif_number="98765432101", phone_number="9876543210", kyc_status="VERIFIED"
        )
        self.account_a = BankAccount.objects.create(
            user=self.user_a, account_number="10010020030001", branch=self.branch,
            balance=Decimal('50000.00'), status='ACTIVE'
        )
        self.account_a.set_transaction_pin('1234')
        self.account_a.save()

        # 3. Create User B (Receiver)
        self.user_b = User.objects.create_user(username='userb', password='Password@123', email='b@bank.demo')
        self.profile_b = CustomerProfile.objects.create(
            user=self.user_b, cif_number="98765432102", phone_number="9876543211", kyc_status="VERIFIED"
        )
        self.account_b = BankAccount.objects.create(
            user=self.user_b, account_number="10010020030002", branch=self.branch,
            balance=Decimal('10000.00'), status='ACTIVE'
        )
        self.account_b.set_transaction_pin('1234')
        self.account_b.save()

    def test_double_sided_atomic_transfer(self):
        """
        Tests that an atomic fund transfer correctly debits sender and credits receiver
        while creating an immutable transaction record.
        """
        transfer_amount = Decimal('5000.00')
        success, msg, txn = TransferService.execute_transfer(
            sender_account_id=self.account_a.id,
            amount=transfer_amount,
            transfer_type='BANK_TRANSFER',
            receiver_account_number=self.account_b.account_number,
            receiver_name="User B",
            remarks="Test Transfer"
        )

        self.assertTrue(success)
        self.assertIsNotNone(txn)

        # Reload balances from DB
        self.account_a.refresh_from_db()
        self.account_b.refresh_from_db()

        self.assertEqual(self.account_a.balance, Decimal('45000.00'))
        self.assertEqual(self.account_b.balance, Decimal('15000.00'))
        self.assertEqual(txn.status, 'SUCCESS')
        self.assertEqual(txn.sender_balance_after, Decimal('45000.00'))
        self.assertEqual(txn.receiver_balance_after, Decimal('15000.00'))

    def test_insufficient_balance_rejection(self):
        """
        Tests that a transfer greater than available balance is strictly rejected
        and balances remain completely unchanged.
        """
        transfer_amount = Decimal('100000.00')  # Account A only has 50k
        success, msg, txn = TransferService.execute_transfer(
            sender_account_id=self.account_a.id,
            amount=transfer_amount,
            receiver_account_number=self.account_b.account_number
        )

        self.assertFalse(success)
        self.assertIn("Insufficient balance", msg)

        # Check balances unchanged
        self.account_a.refresh_from_db()
        self.account_b.refresh_from_db()

        self.assertEqual(self.account_a.balance, Decimal('50000.00'))
        self.assertEqual(self.account_b.balance, Decimal('10000.00'))

    def test_negative_or_zero_transfer_rejection(self):
        """
        Tests that zero or negative transfer amounts are rejected.
        """
        success, msg, _ = TransferService.execute_transfer(self.account_a.id, Decimal('0.00'))
        self.assertFalse(success)

        success, msg, _ = TransferService.execute_transfer(self.account_a.id, Decimal('-500.00'))
        self.assertFalse(success)

    def test_emi_calculation(self):
        """
        Tests financial EMI formula calculation.
        """
        emi = calculate_emi(Decimal('100000.00'), Decimal('12.00'), 12)
        # 1 Lakh at 12% p.a. for 12 months is approx ₹8,885
        self.assertTrue(Decimal('8880') <= emi <= Decimal('8890'))

    def test_pdf_account_statement_generation(self):
        """
        Tests ReportLab PDF byte compilation.
        """
        from_date = (timezone.now() - timedelta(days=30)).date()
        to_date = timezone.now().date()
        txns = Transaction.objects.filter(sender_account=self.account_a)
        
        pdf_bytes = generate_account_statement_pdf(self.account_a, txns, from_date, to_date)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(len(pdf_bytes) > 500)
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))
