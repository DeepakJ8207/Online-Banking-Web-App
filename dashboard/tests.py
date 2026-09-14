from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
from banking.models import BankAccount, Branch
from transactions.models import Transaction

class DashboardAndManagerTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create Branch
        self.branch = Branch.objects.create(
            branch_name="Main Branch",
            branch_code="MAIN01",
            ifsc_code="PRMB0000001",
            address="123 Financial District",
            city="Mumbai",
            state="Maharashtra",
            pincode="400001"
        )
        
        # Create Customer
        self.customer = User.objects.create_user(
            username="test_customer",
            password="Password@123",
            first_name="Test",
            last_name="Customer",
            email="customer@test.com"
        )
        self.account = BankAccount.objects.create(
            user=self.customer,
            branch=self.branch,
            account_number="PRMB1002009999",
            account_type="SAVINGS",
            balance=Decimal("50000.00"),
            status="ACTIVE"
        )
        self.account.set_transaction_pin("1234")
        self.account.save()

        # Create Admin
        self.admin = User.objects.create_superuser(
            username="test_admin",
            password="AdminPassword@123",
            email="admin@test.com"
        )

    def test_customer_dashboard_access(self):
        self.client.login(username="test_customer", password="Password@123")
        response = self.client.get(reverse('dashboard:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "50,000")

    def test_customer_cannot_access_manager_overview(self):
        self.client.login(username="test_customer", password="Password@123")
        response = self.client.get(reverse('dashboard:admin_overview'))
        self.assertEqual(response.status_code, 302)  # Redirected to customer dashboard

    def test_admin_can_access_manager_overview(self):
        self.client.login(username="test_admin", password="AdminPassword@123")
        response = self.client.get(reverse('dashboard:admin_overview'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bank Manager")
        self.assertContains(response, "PRMB1002009999")
        self.assertContains(response, "50,000")

    def test_analytics_api(self):
        self.client.login(username="test_customer", password="Password@123")
        response = self.client.get(reverse('dashboard:analytics_api'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('monthly_labels', data)
        self.assertIn('category_labels', data)
